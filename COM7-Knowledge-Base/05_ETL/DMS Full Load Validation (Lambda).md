# DMS Full Load Validation (Lambda)

> ตรวจว่างาน **DMS full-load** จบจริงและข้อมูลปลายทางครบ ก่อนจะปล่อยให้ ETL ตัวถัดไปทำงาน

| | |
|---|---|
| หน้าที่ | ตรวจ task + ตรวจจำนวนแถวฝั่ง S3 → แจ้งผล / เปิดประตูให้ ETL |
| ผู้เรียก | **EventBridge** (task เข้าสถานะปลายทาง) · **Step Functions** (gate ก่อน ETL) |
| แจ้งเตือน | SNS `com7-data-pipeline-alerts` |
| นับแถวปลายทาง | อ่าน **Parquet footer** ไม่อ่านข้อมูลจริง |

---

## ทำไมฟังก์ชันเดียวรับสองผู้เรียก

งานที่ต้องทำเหมือนกันเกือบทั้งหมด **แยกเป็นสองตัวคือต้องดูแลตรรกะซ้ำสองชุด** ซึ่งจะเพี้ยนจากกันเมื่อแก้ที่เดียว

| | EventBridge | Step Functions |
|---|---|---|
| ขอบเขต | **ทั้ง task** ครอบคลุม task ที่ warehouse ยังไม่มี ETL ด้วย | **dataset เดียว** |
| ส่งอีเมล | ✅ | ❌ **state machine ส่งเองที่ละเอียดกว่า** |
| คืนค่าให้ตัดสินใจ | ไม่ได้ใช้ | `passed` ให้ state machine แตกกิ่ง |
| `sourceRows` ที่คืน | รวมทั้ง task | **เฉพาะ table ของ dataset นั้น** |

**สองอีเมลต่อหนึ่ง load คือวิธีสอนให้คนตั้ง filter ทิ้ง** — จึงยอมให้ path เดียวส่ง

การสลับโหมดดูจาก event ไม่ใช่ flag แยก

```python
gate_mode = bool(dataset or source_path)
notify = event.get("notify", not gate_mode)   # default ตามโหมด
```

**default เป็น "แจ้ง" เพราะฝั่ง EventBridge เป็นฝั่งที่ไม่มี flag ติดมา** — ถ้า default เป็นเงียบแล้วลืมตั้ง จะเงียบหายทั้งระบบ ซึ่งแย่กว่าส่งเกิน

`sourceRows` เป็นตัวที่ ETL เอาไปกระทบยอด **จึงต้องเป็นของ table นั้นตัวเดียว** — ยัดผลรวมของ table ที่ไม่เกี่ยวไปให้ จะกระทบยอดไม่มีวันตรง

---

## ตรวจอะไรบ้าง

| # | check | ทำไมต้องมี |
|---|---|---|
| 1 | migration type เป็น `full-load` | path นี้ไม่รองรับ CDC · ตรรกะนับแถวใช้กับ CDC ไม่ได้ |
| 2 | task ถึงสถานะปลายทาง **และหยุดเพราะโหลดจบ** | `stopped` เฉย ๆ ไม่พอ **คนกดหยุดเองก็ `stopped`** |
| 3 | ทุก table ที่เลือกไว้เป็น `Table completed` | |
| 4 | ปลายทางมีไฟล์ **และจำนวนแถวตรงกับที่ DMS บอก** | |
| 5 | (gate mode) prefix ที่ ETL จะอ่าน เป็นของ table ที่ task นี้โหลดจริง | กัน config ชี้ผิดที่แล้ว ETL อ่านข้อมูลเก่าไปทั้งรอบ |

`OK_STOP_REASONS` รับสองรูปแบบ เพราะ DMS เขียน `StopReason` ไม่เหมือนกันทุกเวอร์ชัน — บางครั้งมีคำว่า `Stop Reason` นำหน้าซ้ำ

---

## อ่าน Parquet footer แทนการอ่านข้อมูล

**นี่คือหัวใจของตัวนี้** — ได้จำนวนแถวจริงโดยไม่ต้องโหลดไฟล์ ไม่ต้องมี `pyarrow` ไม่ต้องแพ็ก layer

```
ไฟล์ Parquet
┌──────────────────┬───────────────┬────────────┬──────┐
│      data        │  FileMetaData │ footer_len │ PAR1 │
└──────────────────┴───────────────┴────────────┴──────┘
                                     4 bytes     4 bytes
```

| ขั้น | ทำอะไร |
|---|---|
| 1 | `Range="bytes=-8"` ดึง 8 ไบต์สุดท้าย |
| 2 | เช็ค magic `PAR1` · ไม่ตรง = ไม่ใช่ Parquet |
| 3 | `struct.unpack("<i", tail[0:4])` ได้ความยาว footer |
| 4 | `Range` ดึงเฉพาะ footer มา |
| 5 | ไล่ Thrift compact หา **field 3 = `num_rows` ชนิด i64** |

**ประหยัดมหาศาล** — ไฟล์ 500 MB อ่านจริงแค่ไม่กี่ KB

### Thrift compact ที่ต้องรู้แค่ 3 อย่าง

| | |
|---|---|
| **field header 1 ไบต์** | 4 บิตบน = ระยะห่างจาก field id ก่อนหน้า · 4 บิตล่าง = ชนิด · `delta == 0` แปลว่า id เขียนตรง ๆ ตามหลัง |
| **zigzag** | จำนวนเต็มมีเครื่องหมายถูกพับให้เป็นบวกก่อนเข้ารหัส varint · `(n >> 1) ^ -(n & 1)` คลายกลับ |
| **ข้าม field ที่ไม่สนใจ** | `_skip_thrift_field` ต้องรู้ความยาวของทุกชนิดเพื่อเลื่อนตำแหน่งให้ถูก · list / map / struct ต้องไล่ลงไปข้างในด้วย |

FileMetaData เรียงเป็น field 1 = version · **field 2 = schema (list ของ struct)** · field 3 = num_rows — จึงต้องข้าม list ของ struct ให้เป็นก่อนถึงจะถึงตัวเลข

---

## สามสถานะ ไม่ใช่สอง

**บทเรียนที่แพงที่สุดของตัวนี้** — EventBridge ส่ง event มาก่อนที่ `DescribeReplicationTasks` จะรายงานว่า `stopped`

> วัดจริงในงานรอบกลางคืน **หน่วง 28 วินาที และ 44 วินาที**

ตั้งเวลารอแบบตายตัวสั้น ๆ จะรายงานว่างานที่สมบูรณ์ดีเป็น **failure**

```python
is_success = status == "stopped" and finished_ok
is_failure = status == "failed" or (status == "stopped" and not finished_ok)
is_pending = not is_success and not is_failure
```

**`pending` ไม่ใช่ failure — คือยังไม่รู้** คนละความหมาย และต้องสื่อสารคนละแบบ

| สถานะ | อีเมล |
|---|---|
| success | ✅ สำเร็จ |
| **pending + ข้อมูลตรงครบ** | ⏳ **ยังไม่สรุป ไม่ต้องทำอะไร** |
| failure | ❌ ไม่สำเร็จ |

และแยก **verdict ของข้อมูล** ออกจาก **verdict ของสถานะ task**

```python
data_checks = [c for c in checks if c["name"] != "Task finished a full load"]
data_ok = all(c["passed"] for c in data_checks)
```

**ทุก table ตรงกันหมด เหลือแค่ DMS ยังไม่พลิกสถานะ — เรียกว่ามีปัญหาคือผิด**

### รอแบบอิงเวลาที่เหลือจริง

```python
RESERVE_MS = 45_000       # กันไว้ให้งาน S3 กับ publish
POLL_INTERVAL_S = 5
if remaining_ms() < RESERVE_MS + POLL_INTERVAL_S * 1000:
    break
```

หลักเดียวกับ `time_left()` ใน [[Google Sheet to S3 (Lambda)]] — **อย่าตั้งเวลารอเป็นค่าคงที่ ให้ถามว่าเหลือเวลาเท่าไหร่**

---

## สี่คำตอบ ไม่ใช่สอง

ตอนเทียบจำนวนแถว การมีแค่ "ตรง / ไม่ตรง" ทำให้ข้อมูลหายแบบไม่มีใครรู้

| เงื่อนไข | ผล | ผ่านไหม |
|---|---|---|
| DMS 0 แถว และ S3 0 ไฟล์ | `— empty on both sides` | ✅ |
| S3 ไม่มีไฟล์ | `❌ NO TARGET FILES` | ❌ |
| มีไฟล์แต่นับไม่ได้ | `⚠️ UNCOUNTABLE` | ✅ |
| ต่างกันไม่เกิน tolerance | `✅ MATCH` | ✅ |
| ต่างเกิน tolerance | `❌ MISMATCH (drift ±n)` | ❌ |

**การเหมาว่า target ว่าง = ไม่เกี่ยว คือทางที่ข้อมูลหายแล้วไม่มีใครรู้**

`UNCOUNTABLE` มีเพราะถ้า endpoint เขียนเป็น CSV จะนับแถวแบบถูก ๆ ไม่ได้ — **ต้องบอกว่านับไม่ได้ ไม่ใช่ทำเป็นว่าตรงกัน**

---

## ฟังก์ชัน

| ฟังก์ชัน | หน้าที่ |
|---|---|
| `_read_varint` · `_zigzag_decode` | ถอดตัวเลข Thrift compact |
| `_skip_thrift_field` · `_skip_thrift_struct` | เลื่อนข้าม field ที่ไม่สนใจให้ตำแหน่งถูก |
| `_parquet_row_count(bucket, key)` | `num_rows` ของไฟล์เดียว · อ่านไม่ได้คืน `None` |
| `_split_s3_uri` | `s3://bucket/prefix` → `(bucket, prefix)` |
| `_schema_table_from_path` | DMS เขียนที่ `<bucketFolder>/<schema>/<table>/` **สองส่วนท้ายคือตัวระบุ** |
| `_endpoint_s3_info(arn)` | ดึง `BucketName` / `BucketFolder` จาก target endpoint |
| `_scan_prefix(bucket, prefix)` | นับไฟล์ · ไบต์ · แถวรวม · จำนวนที่นับไม่ได้ |
| `_all_table_statistics(arn)` | `describe_table_statistics` วน `Marker` จนครบ |
| `_human(n)` | bytes → KiB / MiB ฐาน 1024 |
| `_publish(subject, body)` | ส่ง SNS · **พังแล้ว print แทน ไม่ยอมให้ล้มทั้งงาน** |
| `lambda_handler` | ประกอบทั้งหมด |

`_publish` ตัด subject ที่ 100 ตัวอักษรเพราะ **SNS จำกัดไว้เท่านั้น** ยาวเกินคือ error

`_all_table_statistics` ต้องวน `Marker` เพราะ **หน้าเดียวได้ไม่ครบเมื่อ task มี table เยอะ** — อ่านหน้าเดียวแล้วสรุปคือรายงานว่าครบทั้งที่ยังไม่ครบ

---

## Environment variables

| ตัวแปร | default | ความหมาย |
|---|---|---|
| `SNS_TOPIC_ARN` | ARN ของ `com7-data-pipeline-alerts` | ปลายทางแจ้งเตือน |
| `ROW_TOLERANCE` | `0` | ยอมให้ต่างกี่แถวก่อนตัดสินว่าไม่ผ่าน |

`tolerance` รับจาก event ก่อน แล้วค่อยตกไปที่ env — ให้ dataset ที่รู้ว่ามี drift ประจำตั้งค่าของตัวเองได้โดยไม่กระทบตัวอื่น

```python
tolerance = int(event.get("tolerance", os.environ.get("ROW_TOLERANCE", "0")))
```

**`int()` ครอบไว้เพราะ env var เป็น string เสมอ** → [[Google Sheet to S3 (Lambda)]]

## IAM

| Action | ใช้ทำอะไร |
|---|---|
| `dms:DescribeReplicationTasks` | สถานะ task |
| `dms:DescribeTableStatistics` | จำนวนแถวต่อ table |
| `dms:DescribeEndpoints` | หา bucket ปลายทาง |
| `s3:ListBucket` | ไล่ไฟล์ใน prefix |
| `s3:GetObject` | **อ่าน footer ด้วย Range** |
| `sns:Publish` | แจ้งเตือน |

---

## ข้อสังเกตที่ควรตามต่อ

| # | เรื่อง | ทำไมสำคัญ |
|---|---|---|
| 1 | **`_scan_prefix` ไม่มี `try/except`** | ตัวอื่นมีหมด · `list_objects_v2` เจอ `AccessDenied` จะโยนออกนอก handler → **ไม่มีอีเมล ไม่รู้ว่าพัง** และ EventBridge จะ retry ซ้ำอีก 2 ครั้งเงียบ ๆ เหมือนเคส `MarshalError` ใน [[Google Sheet to S3 (Lambda)]] |
| 2 | `non_parquet` รวมสองเรื่องเป็นตัวเดียว | ไฟล์ที่ไม่ใช่ Parquet จริง ๆ กับ Parquet ที่ footer เสีย นับรวมกัน · ข้อความ `UNCOUNTABLE (n non-parquet)` จะบอกผิดถ้าเป็นกรณีหลัง |
| 3 | นับได้บางไฟล์ในโฟลเดอร์เดียวกัน | ถ้ามีทั้งไฟล์ที่นับได้และนับไม่ได้ `rows > 0` จะไปเข้าทาง MATCH / MISMATCH **โดยไม่บอกว่ามีไฟล์ที่นับไม่ได้ปนอยู่** |
| 4 | `check("Target reachable", True, ...)` | ผ่านทุกครั้งที่อ่าน endpoint config ได้ **ไม่ได้ทดสอบว่าเข้าถึง bucket ได้จริง** |
| 5 | 2 API call ต่อไฟล์ | `get_object` + `head_object` · ไฟล์เยอะจะช้าและเปลืองทั้ง request และเวลา Lambda · ดึงท้ายไฟล์มาทีเดียว ~64 KB แล้วตัดเอาน่าจะพอ `[อนุมาน ยังไม่ได้วัด]` |
| 6 | pending ทำให้ `passed=False` | ใน gate mode แปลว่า **DMS ช้า = ETL ไม่ได้รัน** · state machine ควรใช้ `dataChecksPassed` ประกอบ ไม่ใช่ดู `passed` อย่างเดียว |
| 7 | polling กินเวลา Lambda | DMS ไม่อัปเดตสถานะ = รันยาวจนเกือบหมดเวลาทุกครั้ง · Lambda คิดเงินตาม memory × duration |

---

## เชื่อมกับโน้ตอื่น

[[Google Sheet to S3 (Lambda)]] · [[Architecture]] · [[AWS Services]] · [[ETL & Spark]] · [[Network & VPN]] · [[Snapshot Change Detection (ITEC DMS)]] · [[Pipeline Issues]]
