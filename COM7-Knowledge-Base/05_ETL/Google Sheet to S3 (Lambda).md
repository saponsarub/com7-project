# Google Sheet to S3 (Lambda)

> **หมายเหตุที่มา:** บันทึกจากการ deploy และรันจริงบน AWS account `603238661233` ระหว่าง **2026-09-02 ถึง 2026-09-07** — ทุกอาการ ตัวเลข และ error มาจาก CloudWatch log ของฟังก์ชันจริง ไม่ใช่เอกสาร

ดึงข้อมูลจาก Google Sheet ที่ทีมงานคีย์มือ ลงจอดเป็น CSV บน S3 ให้ Glue/Athena อ่านต่อ พร้อมเขียน log และส่งรายงานทางอีเมล

| | |
|---|---|
| สถานะ | **v2.4.2** · 4 ชีต 14 tabs · รันสำเร็จ 14/14 · 112,516 แถว · 110.7 MB · 41 วินาที |
| โค้ด | `scripts/lambda/googlesheet-to-s3/` · `scripts/lambda/googlesheet-rowcount/` |
| **เอกสารระดับโค้ด** | **`docs/googlesheet-to-s3.md`** — ผูกกับเวอร์ชัน อัปเดตพร้อมโค้ด |
| โน้ตนี้ | ตรรกะ · เหตุผลของทุกการตัดสินใจ · กับดักที่ใช้ซ้ำได้กับ pipeline อื่น |

---

## สถาปัตยกรรม

```
EventBridge (23:30)
      ▼
Lambda 1 · ingest
  Secrets Manager ──► Google OAuth (เซ็น JWT ครั้งเดียว)
  Sheets API ──► CSV (/tmp) ──► S3 data    วนทุกชีต/tab · ingest ซ้ำได้ 3 รอบ
  log CSV ──► S3 log   (S3_row_count ใส่แล้ว)
  รายงาน  ──► SES (ap-southeast-1)
      │ invoke async · ไม่รอผล
      ▼
Lambda 2 · rowcount
  อ่าน log ──► เช็ค Etag ──► csv.reader นับแถวจาก S3 ──► เขียนทับ log
```

**หลักการเดียวที่คุมทุกอย่าง — หนึ่ง tab = หนึ่งโฟลเดอร์ = หนึ่งตาราง** เพื่อให้ Glue Crawler (`Table level = 3`) แยกตารางถูก → [[Glue Crawler]]

### แหล่งข้อมูล

| ชีต      | brand | tabs                                                         | ปลายทาง                                                          |
| -------- | ----- | ------------------------------------------------------------ | ---------------------------------------------------------------- |
| EV7 Main | ev7   | 7 tabs                                                       | `google-sheet-ev7/ev7_*/`                                        |
| Grab     | ev7   | `Clean` · `ชีต1`                                             | `google-sheet-ev7/Grab_Clean/` · `Grab/`                         |
| Lineman  | ev7   | `Clean` · `ชีต1`                                             | `google-sheet-ev7/Lineman_Clean/` · `Lineman/`                   |
| GI       | gi    | `rawdataInteresting` · `rawdataTestdrive` · `rawdataBooking` | `google-sheet-gi/GI_Interest/` · `GI_Testdrive/` · `GI_Booking/` |

**service account ตัวเดียวใช้ได้ทุกชีต** แต่ต้อง share แต่ละไฟล์ให้ `client_email` แยกกัน — **ลืมแล้วได้ 404 ไม่ใช่ 403** เพราะ Google จงใจไม่บอกว่าไฟล์มีอยู่จริงไหม

**ข้อมูลทั้งหมดเป็นฝั่ง EV** เกี่ยวกับ [[GI + EV7 to 7Club]] โดยตรง

---

## ฟังก์ชันทั้งหมด — Lambda 1 (1,012 บรรทัด)

| ฟังก์ชัน                       | ทำอะไร                               | ตรรกะที่ต้องรู้                                                                                        |
| ------------------------------ | ------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `total_tabs(runs)`             | นับ tab ที่ตั้งใจดึงในรอบนี้         | ใช้เป็นตัวหารใน `12 of 14 tabs`                                                                        |
| `time_left()`                  | วินาทีที่ Lambda เหลือ               | อ่าน `CONTEXT.get_remaining_time_in_millis()` · รันบนเครื่องคืน 900 · **เป็น guard ก่อน retry ทุกจุด** |
| `get_access_token()`           | Secrets Manager → access token       | เซ็น JWT RS256 ครั้งเดียวใช้ได้ทุกชีต · token อายุ 1 ชม.                                               |
| `fetch_tab(...)`               | ดึง 1 tab จาก Sheets API             | retry ในตัว + ดัก error body ของ Google                                                                |
| `write_csv(values, path)`      | เขียน CSV ทีละแถวลง `/tmp`           | คืน `(bytes, จำนวนแถว)`                                                                                |
| `human_size(n)`                | bytes → KB/MB/GB ฐาน 1024            | ให้ตรงกับที่ S3 console แสดง                                                                           |
| `group_by_source(items, runs)` | จัดรายการตามชีต                      | **คงลำดับตาม `SOURCES`** ไม่เรียงตามตัวอักษร คนอ่านเห็นลำดับเดิมทุกวัน                                 |
| `build_report(...)`            | รายงาน plain text                    | จัดตารางด้วยช่องว่าง ใช้ได้เพราะทุกค่าเป็น ASCII                                                       |
| `esc(text)`                    | escape `& < > "`                     | ค่าจากชีตไม่ควรกลายเป็น HTML tag                                                                       |
| `build_html(...)`              | รายงาน HTML สำหรับ SES               | table layout + inline style                                                                            |
| `build_log_rows(...)`          | ประกอบ log 34 คอลัมน์                | หนึ่งแถวต่อหนึ่งตาราง                                                                                  |
| `write_log(rows)`              | เขียน log CSV ลง S3 + เรียก Lambda 2 | partition `year=/month=/day=`                                                                          |
| `send_report(report, html)`    | ส่งผ่าน SES                          | ส่งไม่ได้ไม่ทำให้ job พัง                                                                              |
| `build_mime(...)`              | ประกอบอีเมล multipart                | โลโก้ inline ด้วย `cid:`                                                                               |
| `ingest_tab(...)`              | ดึง 1 tab → เขียน S3 → คืน dict      | แยกออกมาเพราะ handler เรียกซ้ำหลายรอบ                                                                  |
| `jsonable(items)`              | แปลง datetime → string               | Lambda marshal ค่าที่ `return` เป็น JSON                                                               |
| `lambda_handler(...)`          | ตัวควบคุม                            | กรอง event → auth → วน pass → log → เมล                                                                |

### Lambda 2 · rowcount (171 บรรทัด)

| ฟังก์ชัน | ทำอะไร |
|---|---|
| `parse_event(event)` | รับได้ทั้ง payload ตรงและ S3 Event Notification |
| `count_rows(bucket, key)` | อ่านไฟล์จาก S3 นับแถวผ่าน `csv.reader` |
| `lambda_handler(...)` | อ่าน log → เช็ค Etag → นับ → เขียนทับ |

---

## ตรรกะสำคัญ 12 ข้อ

### 1 · boto3 client วางนอก handler

รันเฉพาะตอน **cold start** — เห็นเป็น `Init Duration ~800 ms` ที่หายไปในรอบถัดมาเพราะ Lambda ใช้ container เดิม

### 2 · credential อยู่ใน Secrets Manager ไม่ใช่ในโค้ด

ไฟล์ service account มี private key **ถ้าฝังใน zip ใครอ่านโค้ดฟังก์ชันได้ก็ได้กุญแจไปด้วย**

`scope` เป็น `spreadsheets.readonly` — token หลุดก็แก้ชีตต้นทางไม่ได้

### 3 · เซ็น JWT ครั้งเดียวใช้ได้ทุกชีต

เรียก `get_access_token()` **ก่อนเข้าลูป** ไม่ใช่ต่อชีต — token อายุ 1 ชั่วโมง งานทั้งรอบใช้ 41 วินาที

**ขั้นตอนเซ็น JWT นี่เองที่บังคับให้ต้องมี `cryptography`** ซึ่งเป็น native code → ต้อง build บน Linux เท่านั้น

### 4 · เขียน CSV ผ่าน `/tmp` ไม่ใช่ผ่าน RAM

**`/tmp` กับ memory เป็นคนละถัง ไม่ไหลข้ามกัน**

```
Memory (RAM)      128 – 10,240 MB    ตั้งแยก · คิดเงินแยก
Ephemeral (/tmp)  512 – 10,240 MB    ตั้งแยก · คิดเงินแยก
```

| เต็มฝั่งไหน | error | ไปกินอีกฝั่งไหม |
|---|---|---|
| `/tmp` | `OSError: [Errno 28] No space left on device` | ❌ |
| RAM | `Runtime.OutOfMemory` | ❌ |

**Lambda ไม่มี swap** — RAM เต็มคือถูกฆ่าทันที ไม่มี exception ไม่มี log ไม่รู้ว่าพังที่ tab ไหน จึงต้องสั่งย้ายเอง ระบบไม่ทำให้

> บน Linux ทั่วไป `/tmp` มักเป็น tmpfs ที่กิน RAM จริง **แต่ Lambda แยกออกมาเป็นทรัพยากรคนละก้อน** ถ้าไม่แยกจริง วิธีแก้ OOM รอบนั้นก็จะใช้ไม่ได้เลย

#### ทำไมไม่เก็บใน RAM ให้จบ

ตอนนี้ตั้ง memory 2048 MB ใช้จริง 444 MB — ทำใน RAM ล้วนก็คงพอ แต่ยังควรผ่าน `/tmp` เพราะ

| # | เหตุผล |
|---|---|
| 1 | **วัดจริง 50,000 แถว × 12 คอลัมน์** — ต่อ string ใน RAM 38.8 MB · เขียนทีละแถวลงไฟล์ 0.3 MB (**ต่างกัน 130 เท่า**) เพราะตอนต่อ string Python ถือทั้งอันเก่าและอันใหม่พร้อมกัน |
| 2 | **RAM ที่นับคือจุดสูงสุด ไม่ใช่ค่าเฉลี่ย** — ถ้าทำใน RAM จะมีของซ้อนกัน 3 ชุด (`values` + `StringIO` + `.encode()`) · 444 MB จะพุ่งเกิน 1 GB |
| 3 | **`/tmp` เต็มยังจับ exception ได้** tab อื่นรันต่อ log บันทึกได้ · RAM เต็มคือเงียบหาย |
| 4 | **`upload_file` ต้องการไฟล์อยู่แล้ว** ไม่ผ่านไฟล์ต้องใช้ `put_object` ซึ่งบังคับถือทั้งก้อนใน RAM → ย้อนกลับข้อ 2 |
| 5 | **ชีตเป็นของทีมอื่น โตขึ้นเองโดยไม่มีใครบอก** · `/tmp` โตได้ถึง 10 GB แทบไม่มีค่าใช้จ่าย · RAM โตแล้วจ่ายเพิ่มทุกวินาทีที่รัน |

```python
values[i] = None      # ปล่อย reference ทีละแถว ไม่ถือทั้งชุดค้างไว้
del values            # ปล่อยทั้งก้อนหลังเขียนไฟล์เสร็จ
```

#### กฎของ path

```
/tmp/out.csv
└──┘ └─────┘
 │      └── ชื่อไฟล์ · ตั้งเองได้ ไม่ต้องมีนามสกุลด้วยซ้ำ
 └── บังคับ · directory เดียวที่เขียนได้
```

| path | ผล |
|---|---|
| `/tmp/anything` | ✅ |
| `/tmp/csv/out.csv` | ✅ **แต่ต้อง `os.makedirs("/tmp/csv", exist_ok=True)` ก่อน** |
| `/data/out.csv` | ❌ Read-only file system |
| `out.csv` | ❌ **กับดัก** — path สัมพัทธ์อิงจาก `/var/task` ซึ่ง read-only |

`/tmp` มีอยู่แน่นอนไม่ต้องเช็คก่อนใช้ — AWS การันตีในเอกสาร runtime และเป็นธรรมเนียม Linux อยู่แล้ว

**รันบน Windows ไม่ได้** ถ้าจะทดสอบบนเครื่อง ใช้ `os.path.join(tempfile.gettempdir(), "out.csv")` ซึ่งคืน `/tmp` บน Lambda และ `%TEMP%` บน Windows

#### ต้องลบเอง

```python
finally:
    if os.path.exists(TMP_PATH):
        os.remove(TMP_PATH)
```

**`/tmp` อยู่ข้ามการเรียกใช้** — container ที่ยังอุ่นถูกใช้ซ้ำและไฟล์ยังอยู่ครบ

- ไม่ลบ → 14 tab สะสมกัน · ถ้าชีตโตขึ้นจะชน 512 MB
- อยู่ใน `finally` เพื่อลบแม้ตอน `raise` ออกไป ไม่งั้น tab ที่พังทิ้งขยะให้ tab ถัดไป
- ทุก tab ใช้ชื่อไฟล์เดียวกัน **ไม่ลบแล้วอาจอัปโหลดไฟล์ของ tab ก่อนหน้าโดยไม่รู้ตัว**

จุดสูงสุดของ `/tmp` จึงเท่ากับ **tab ที่ใหญ่ที่สุดตัวเดียว ไม่ใช่ 110.7 MB สะสม** — ดูจากคอลัมน์ `Size_MB` ใน log เรียงมาก→น้อย

#### ค่าใช้จ่าย

**512 MB แรกฟรี** จ่ายเฉพาะส่วนที่เกิน คิดจาก **ที่จองคูณเวลาที่รัน ไม่ใช่ที่เขียนจริง** — ตั้ง 10 GB แล้วเขียน 1 KB ก็จ่ายเท่ากัน

```
(ที่ตั้ง − 512 MB) × วินาที × จำนวนครั้ง × ราคาต่อ GB-s
```

ราคาที่ AWS ประกาศคือ **0.0000000309 USD/GB-s** สำหรับส่วนเกิน `[ราคา us-east-1 · ap-southeast-7 อาจไม่เท่ากัน ยังไม่ได้เช็ค]`

| ตั้งเท่าไหร่ | ค่าใช้จ่าย/เดือน (41 วิ × 30 ครั้ง) |
|---|---|
| **512 MB** (ปัจจุบัน) | **0** |
| 2,048 MB | ~0.00006 USD |
| 10,240 MB | ~0.00036 USD |

**ต่อให้ตั้งสูงสุดก็ไม่ถึง 0.1 บาท/เดือน** — เหตุผลที่ยังไม่ขยายไม่ใช่เรื่องราคา แต่เพราะยังไม่มีปัญหาให้แก้ จะรู้ตัวเองเมื่อเจอ `Errno 28`

**ถ้าเจอ `Errno 28` ให้ขยาย ephemeral storage ไม่ใช่ขยาย memory** — ขยายผิดฝั่งแล้วยังพังเหมือนเดิม

#### อย่าลด memory ลงเพราะเห็นว่าใช้แค่ 444 MB

Lambda ให้ CPU **ตามสัดส่วน memory** (≈1,769 MB = 1 vCPU เต็ม) ลดเหลือ 1024 MB จะได้ CPU ราวครึ่งเดียว งาน 41 วินาทีอาจกลายเป็น 70–80 วินาที

ประหยัดได้ไม่ถึงบาท/เดือน แต่เสี่ยง timeout — **ไม่คุ้ม เก็บ 2048 ไว้**

### 5 · `upload_file` ไม่ใช่ `put_object`

สตรีมจากดิสก์ · แบ่ง multipart อัตโนมัติ · `put_object` ต้องโหลดทั้งก้อนเข้า RAM ก่อน

### 6 · retry 2 ชั้น คนละอาการ

| ชั้น | ขอบเขต | เว้นระยะ | แก้ปัญหา |
|---|---|---|---|
| ใน `fetch_tab` | คำขอเดียว | 2-4 วินาที | สะดุดชั่วขณะ |
| pass ระดับ job | ทั้ง tab (fetch + write + upload) | 20 วินาที | **Google หน่วงเพราะยิงติดกันหลายคำขอ** |

อาการจริงคือ **tab ท้าย ๆ timeout** หลังยิงมาแล้ว 11 คำขอ — ต้องเว้นระยะให้ต้นทางหายหน่วง ไม่ใช่ยิงซ้ำทันที

**retry เฉพาะที่ควร retry** — `TimeoutError` · `URLError` · HTTP 429/500/502/503/504 · **ไม่ retry 400/403/404** เพราะลองใหม่ก็ผิดเหมือนเดิม

> `HTTPError` เป็น subclass ของ `URLError` ต้องดัก `HTTPError` ก่อนเสมอ

### 7 · guard ด้วยเวลาที่ Lambda เหลือ

ก่อน retry ทุกครั้งเช็ค `time_left()` — ไม่พอก็ยอมแพ้ tab นั้น **แทนที่จะดันจนตายทั้งงาน**

**เคยคำนวณพลาด** — ตั้ง timeout 180s × retry 3 = 540 วินาที เกิน Lambda timeout 300 วินาที **retry จะทำให้ตายแทนที่จะได้ผล** ลดเหลือ 90s แล้วเพิ่ม guard

### 8 · `try/except` อยู่ระดับ tab

tab เดียวพังไม่ลากทั้งงานล่ม เก็บไว้รายงานตอนท้าย

ตัด error เหลือ **120 ตัวอักษร** เพราะข้อความ exception อาจมีเนื้อข้อมูลติดมา และรายงานถูกส่งข้าม region

### 9 · ไม่ตั้ง env = ปิดฟีเจอร์ ไม่ใช่พัง

SES · log · rowcount ทุกตัวเป็น opt-in **เพราะข้อมูลขึ้น S3 สำเร็จไปแล้ว การส่งเมลหรือเขียน log ไม่ควรลากงานหลักล่ม**

### 10 · `finally` ลบ `/tmp` ทุกครั้ง

รายละเอียดอยู่ในข้อ 4 — สามอาการที่ต่างกันจากการไม่ลบ **พอกจนเต็ม · tab ที่พังทิ้งขยะให้ tab ถัดไป · อัปโหลดไฟล์ของ tab ก่อนหน้าโดยไม่รู้ตัว**

### 11 · ตรวจไบต์ปลายทางหลังอัปโหลด

```python
if head["ContentLength"] != size:
    raise Exception("อัปโหลดไม่ครบ")
```

`head_object` ถูกเรียกอยู่แล้ว — เก็บ `ContentLength` กับ `ETag` มาใช้ต่อ **ได้ฟรี**

### 12 · เลือกวิธีเชื่อม 2 Lambda ตามจำนวนจุดที่พลาดได้

| | direct invoke (ใช้อยู่) | S3 Event Notification |
|---|---|---|
| จุดที่ต้อง config | **3** | 5 |
| พังแล้วรู้ไหม | เห็น `ROWCOUNT INVOKE FAILED` ใน log | **เงียบ** ถ้าลืม `add-permission` |
| แยกขาดไหม | ตัวที่ 1 ต้องรู้ชื่อตัวที่ 2 | แยกขาด |

**เคยเปลี่ยนไป S3 Event แล้วถอยกลับ (v2.3.0 → v2.4.0)** — การแยกขาดเป็นข้อดีเชิงทฤษฎีสำหรับ pipeline แค่ 2 ขั้น ไม่คุ้มกับ config 2 จุดที่พลาดแล้วเงียบ

**บทเรียน: เลือกสถาปัตยกรรมตามจำนวนจุดที่พลาดได้ ไม่ใช่ตามความสวยของ diagram**

`parse_event()` ใน Lambda 2 รับได้ทั้ง 2 แบบ — เปลี่ยนวิธีเชื่อมภายหลังโดยไม่ต้องแก้โค้ด

---

## Library และการแพ็ก

### แยกเป็น Lambda Layer แล้ว (v2.4.2)

```
zip เดียว 5.92 MB   →  เกิน 3 MB · Console แก้โค้ดไม่ได้

Layer      5.89 MB   com7-googlesheet-deps    ตั้งครั้งเดียว
Function     38.9 KB  โค้ด + โลโก้ 4 ไฟล์       แก้ใน Console ได้
```

**โค้ดเรา 67 KB · library 19 MB** — `cryptography` ตัวเดียว 14 MB

| ที่อยู่ใน Lambda | มีอะไร |
|---|---|
| `/var/task/` | `lambda_function.py` + PNG 4 ไฟล์ |
| `/opt/python/` | library ทั้งหมดจาก layer |

**PNG ต้องอยู่กับโค้ด ไม่ใช่ layer** เพราะโค้ดหาไฟล์จาก `os.path.dirname(__file__)` = `/var/task` — `sys.path` ใช้ตอน `import` เท่านั้น **`open()` ไม่ได้ใช้ `sys.path`**

**เกณฑ์แบ่ง: ของที่เปลี่ยนพร้อมโค้ดอยู่กับโค้ด · ของที่นาน ๆ เปลี่ยนทีอยู่ layer**

### ทำไมต้อง build บน Linux

| แบบ | ตัวอย่าง | ย้ายข้ามเครื่อง |
|---|---|---|
| Pure Python | `google-auth` · `pyasn1` · `requests` | ได้ |
| **มี native code** | **`cryptography`** · `cffi` · `charset_normalizer` | **ไม่ได้** |

```
pip install --target lambda-build --platform manylinux2014_x86_64 --implementation cp --python-version 3.13 --only-binary=:all: google-auth requests
```

**ตรวจก่อน deploy** — ต้องไม่มี `.pyd` `.dll` `.exe` และ `.so` ต้องลงท้ายด้วย `linux-gnu` หรือ `abi3`

**3 ค่าต้องตรงกันเสมอ** — `--platform` ↔ Architecture · `--python-version` ↔ Runtime · ชื่อไฟล์+ฟังก์ชัน ↔ Handler

รายละเอียดทุก library และฟังก์ชันสำคัญ → [[Python Libraries]]

---

## Log

**34 คอลัมน์ · 21 ตัวแรกเรียงตาม schema กลางของแผนก** · 13 ตัวท้ายเป็นของเดิมที่ยังจำเป็น

```
s3://com7-ingest-logs-603238661233/ingest-log/source=google_sheet/job=.../
  year=2026/month=09/day=07/<Job_No>.csv
```

| ตกลงกันไว้ | ค่า |
|---|---|
| `Job_No` | UUID จาก `context.aws_request_id` — **ตัวเดียวกับ RequestId ใน CloudWatch และชื่อไฟล์ log** |
| `Job_Type` | `Fullload` |
| `Job_Start_Datetime` `Job_End_Datetime` `Job_status` `Duration_min` `Error_message` | **ของ tab ในแถวนั้น ไม่ใช่ของทั้งรอบ** (หนึ่งแถว = หนึ่งตาราง) |
| `Run_status` `Run_Duration_min` | ผลรวมทั้งรอบ |
| `Step_Function_Name` `Server_Name` `Port` `DB_Name` | ว่าง — ไม่มีความหมายกับต้นทางที่เป็น HTTPS API |
| `Threat_scan_Malware` | ว่าง — ยังไม่มีบริการ scan |

**คอลัมน์ที่ยืนยันว่าต้องเก็บแม้ schema กลางไม่มี**

| | ทำไม |
|---|---|
| `Write_Mode` · `Column_count` | **[[Decisions\|D-15]] บังคับ** |
| `Table_Duration_sec` | หน่วยวินาที อ่านง่ายกว่า `Duration_min` ตอน debug |
| `Header_Hash` | md5 หัวตาราง — **จับ schema drift ที่จำนวนคอลัมน์เท่าเดิมแต่สลับ/เปลี่ยนชื่อ** → [[Data Standardization & Quality]] |
| `Target_Bucket` · `S3_Key` · `Etag` | Lambda 2 ใช้หาไฟล์และยืนยันว่ายังเป็นตัวเดิม |

**เลือก CSV ไม่ใช่ JSON** — โครงสร้างแบน Crawler อ่านเป็นตารางได้เลยไม่ต้อง unnest และ D-15 ระบุว่า MIS เป็นผู้รับซึ่งเปิดด้วย Excel

**ต้องใส่ BOM** ไม่งั้น Excel อ่านภาษาไทย (`ชีต1`) ไม่ออก — ไบต์ในไฟล์เป็น UTF-8 ถูกต้องอยู่แล้ว ปัญหาอยู่ที่ตอนเปิด

**ต้องแยกถังจากถังข้อมูล** ไม่งั้น Crawler ที่สแกนถังข้อมูลจะไปเจอ log แล้วสร้างตารางมั่ว

> `Table_row count` มีช่องว่างในชื่อตาม schema กลาง — query ใน Athena ต้องครอบด้วยเครื่องหมายคำพูดทุกครั้ง

### บทเรียนใหญ่ที่สุดของ log

**`rows_match` เดิมเป็น `true` เสมอโดยโครงสร้าง** — `rows` กับ `rows_written` มาจาก `len(values)-1` ตัวเดียวกัน

D-15 ขอ *"ปลายทางได้ผลเท่ากับต้นทางไหม"* แต่คอลัมน์นี้ตอบไม่ได้

> **คอลัมน์ตรวจสอบที่คำนวณจากต้นทางเดียวกันไม่ใช่การตรวจสอบ — ต้องวัดจากปลายทางจริง**

| ชั้นการตรวจ | ต้นทุน | จับอะไรได้ |
|---|---|---|
| นับที่ `csv.writer` | ฟรี | bug ในลูป · แถวที่หลุด |
| เทียบ `ContentLength` หลังอัปโหลด | ฟรี | อัปโหลดไม่ครบ |
| **อ่านกลับจาก S3 แล้วนับ** | +เวลาเท่าตัว → **แยกเป็น Lambda 2** | ทุกกรณี |

**ต้องอ่านผ่าน `csv.reader` ห้ามนับ newline** — เซลล์ที่อยู่ที่คนพิมพ์ขึ้นบรรทัดใหม่ในชีตถูกครอบด้วยเครื่องหมายคำพูด การนับ newline จะได้เกินจริง

**เช็ค `Etag` ก่อนนับ** — ไฟล์ถูกทับหลัง ingest แล้วนับ จะได้เลขที่ไม่ตรงกับ log แถวนั้น → ใส่ `STALE` แทน

| `Status_row_count` | หมายถึง |
|---|---|
| `MATCH` / `MISMATCH` | ต้นทางเท่า/ไม่เท่าปลายทาง |
| `STALE` | ไฟล์ถูกทับแล้ว |
| `SKIPPED_TOO_LARGE` · `ERROR: ...` | ข้ามไป |

---

## กับดักที่เจอจริง

| กับดัก | อาการ |
|---|---|
| **Google ตัดช่องว่างท้ายแถวทิ้ง** | ไม่เติมให้ครบ คอลัมน์จะเลื่อนตอน Athena อ่าน |
| **`csv` default เป็น CRLF** | ต้องบังคับ LF ไม่งั้น Athena ติดอักขระ CR ท้ายคอลัมน์สุดท้าย |
| **`urlopen` ทิ้ง error body ของ Google** | เห็นแค่ `HTTP Error 400` ทั้งที่ Google บอกสาเหตุมาด้วย ต้องดักเอง |
| **404 ไม่ได้แปลว่าไฟล์ไม่มี** | service account ยังไม่ถูก share Google ตอบ 404 ไม่ใช่ 403 |
| **Spreadsheet ID ยาว 44 ตัวเสมอ** | นับความยาวคือวิธีจับ typo ที่เร็วที่สุด |
| **`/tmp` อยู่กับ container ที่ใช้ซ้ำ** | ไม่ลบจะพอกจนเจอ `No space left on device` |
| **`ses:SendRawEmail` คนละ action กับ `ses:SendEmail`** | ใส่ผิดตัวได้ AccessDenied |
| **Gmail บล็อก `data:` URI** | โลโก้ต้องแนบเป็น attachment อ้างด้วย `cid:` |
| **`overflow:hidden` + `border-radius` บน table** | โปรแกรมอีเมลตัดมุมไม่เหมือนกัน สีพื้นแถวสุดท้ายล้นออกนอกกรอบ — ย้ายมุมโค้งไปที่ cell แทน |
| **cell ที่มีแต่ `background` ไม่มี `padding`** | ยุบจนเห็นเป็นแถบขาว |
| **datetime ใน `return`** | `Runtime.MarshalError` — Lambda แปลงค่าที่ return เป็น JSON |
| **128 MB ให้ CPU น้อยมาก** | Lambda จัดสรร CPU ตามสัดส่วน memory · เพิ่มเป็น 1024 MB มักถูกลงเพราะเสร็จเร็วกว่า |

### MarshalError อันตรายกว่าที่เห็น

งานทำสำเร็จหมดแล้วแต่ Lambda ขึ้น **Failed** — พอผูก EventBridge **การเรียกแบบ async จะ retry อัตโนมัติอีก 2 ครั้ง** เท่ากับ ingest ทั้งชุดรัน 3 รอบทุกคืนโดยไม่มีใครรู้

---

## ปัญหาที่เจอจริง เรียงตามลำดับเวลา

| # | Error | สาเหตุ | วิธีแก้ |
|---|---|---|---|
| 1 | `Runtime.ImportModuleError` cryptography | build บน Windows + Python 3.14 | รีบิลด์ด้วย manylinux wheel |
| 2 | `AccessDeniedException` GetSecretValue | role ไม่มี policy | inline policy |
| 3 | `HTTP Error 404` | Spreadsheet ID พิมพ์เกิน (46 ตัว) | แก้ ID |
| 4 | `Task timed out after 3.00 seconds` | timeout default | ตั้ง 5 นาที |
| 5 | `Runtime.OutOfMemory` 127/128 MB | ถือข้อมูลซ้อนกัน 3 ชุด | เขียนผ่าน `/tmp` |
| 6 | `AccessDenied` PutObject `google-sheet-gi/` | policy ครอบแค่ prefix เดียว | เพิ่ม prefix |
| 7 | `TimeoutError` tab ท้าย ๆ | ยิง 14 คำขอติดกัน Google หน่วง | retry 2 ชั้น + guard เวลา |
| 8 | `Runtime.MarshalError` datetime | `tab_start` ใน `return` | `jsonable()` |
| 9 | log ภาษาไทยอ่านไม่ออก | ไม่มี BOM | `utf-8-sig` |
| 10 | Lambda 2 ตอบ `already counted` ทั้งที่ยังไม่นับ | guard แยกไม่ออกระหว่าง "นับครบ" กับ "หาแถวไม่เจอ" | แยก 2 กรณี + พิมพ์ค่าที่พบจริง |

---

## ค่าตั้งที่ใช้อยู่

| | Lambda 1 | Lambda 2 |
|---|---|---|
| Runtime | Python 3.13 · x86_64 | Python 3.13 · x86_64 |
| Memory / Timeout | 2048 MB / 10 นาที | 512 MB / 5 นาที |
| ใช้จริง | 444 MB · 41 วินาที | 98 MB · < 1 วินาที |
| Layer | `com7-googlesheet-deps` | ไม่มี (ใช้แค่ boto3) |

### Environment variables

`os.environ` คือ dict ที่ Python อ่านจากตัวแปรระบบตอน process เริ่ม — `.get(ชื่อ, ค่าสำรอง)` ทำงานเหมือน `.get()` ของ dict ทั่วไป ไม่มีก็คืนค่าสำรองแทนที่จะ `KeyError`

**ทำไมไม่เขียนค่าลงโค้ดตรง ๆ**

| เหตุผล | ตัวอย่างจริง |
|---|---|
| แก้ค่าโดยไม่ต้อง build ใหม่ | Console → Save 10 วินาที · แก้โค้ดต้อง build → upload → deploy |
| ไม่เอาข้อมูลจริงขึ้น git | `SES_TO` เป็นอีเมลคนจริง · `LOG_BUCKET` เป็นชื่อถังจริง |
| zip ก้อนเดียวรันได้หลาย environment | dev ชี้ถัง dev · prod ชี้ถัง prod |

**3 แบบที่ใช้ในโค้ดนี้**

```python
HTTP_TIMEOUT = int(os.environ.get("HTTP_TIMEOUT", "90"))          # มี default ใช้ได้เลย
LOG_BUCKET   = os.environ.get("LOG_BUCKET", "")                   # ไม่ตั้ง = ปิดฟีเจอร์
SES_TO = [x.strip() for x in os.environ.get("SES_TO", "").split(",") if x.strip()]
```

**env var เป็น string เสมอ** — Console มีแต่ช่องข้อความ ไม่มีชนิดตัวเลข ลืม `int()` แล้วเทียบค่าจะพังทันที · default จึงเขียนเป็น `"90"` ไม่ใช่ `90` ให้ `int()` รับได้ทั้งสองทาง

**Console กรอกได้บรรทัดเดียว** รายการหลายค่าจึงคั่นด้วย comma แล้วแตกในโค้ด

**AWS ใส่ให้เองไม่ต้องตั้ง** — `AWS_LAMBDA_FUNCTION_NAME` (โค้ดนี้ใช้เป็น `TASK_NAME`) · `AWS_REGION` · `AWS_LAMBDA_FUNCTION_MEMORY_SIZE` · `LAMBDA_TASK_ROOT` (= `/var/task` ที่โลโก้ PNG อยู่) · default ที่ใส่ไว้เป็นตัวสำรองสำหรับตอนรันบนเครื่อง

| ตัวแปร | default | ไม่ตั้งแล้วเป็นยังไง |
|---|---|---|
| `SES_FROM` `SES_TO` | ว่าง | ไม่ส่งอีเมล |
| `SES_REGION` | `ap-southeast-1` | **SES ไม่มีที่ ap-southeast-7** |
| `LOG_BUCKET` | ว่าง | ไม่เขียน log |
| `ROWCOUNT_LAMBDA` | ว่าง | ไม่เรียก Lambda 2 |
| `HTTP_TIMEOUT` / `HTTP_RETRY` | 90 / 3 | วินาทีต่อคำขอ · ยิงซ้ำกี่ครั้ง |
| `INGEST_PASSES` / `PASS_WAIT` | 3 / 20 | รอบ ingest · พักกี่วินาที |
| `JOB_TYPE` | `Fullload` | ลงในคอลัมน์ log |

**กับดัก 3 ข้อ**

| กับดัก | ผล |
|---|---|
| อ่านตอน import ครั้งเดียว | ตัวแปรอยู่ระดับโมดูล ไม่ได้อยู่ใน handler · แก้ที่ Console แล้ว container ที่ยังอุ่นใช้ค่าเก่า **กด Deploy เพื่อบังคับ container ใหม่** |
| `update-function-configuration` เขียนทับทั้งชุด | ตัวที่ไม่ใส่ในคำสั่งจะหายไป ต้องส่งครบทุกตัวทุกครั้ง |
| **ไม่ใช่ที่เก็บความลับ** | เห็นได้ในหน้า Console และผ่าน `GetFunctionConfiguration` · service account JSON จึงอยู่ใน Secrets Manager |

**env var เหมาะกับ "ชี้ไปที่ไหน / ปรับเท่าไหร่" ไม่ใช่ "กุญแจอะไร"**

### IAM

| Lambda | ต้องมีสิทธิ์ |
|---|---|
| 1 · ingest | `secretsmanager:GetSecretValue` · `s3:PutObject`/`GetObject` บน data + log · `ses:SendRawEmail` · `lambda:InvokeFunction` |
| 2 · rowcount | `s3:GetObject` บน data · `s3:GetObject`/`PutObject` บน log |

---

## การทดสอบ

```json
{"sources": ["Grab"]}
{"tabs": ["Query", "2026"]}
{}
```

กรองตามชีต · ตาม tab · หรือเอาทั้งหมด — ใช้ร่วมกันได้ · **กรองแล้วไม่เหลืออะไรจะ raise ทันที ไม่เงียบ**

**ดูหน้าตาอีเมลก่อนส่ง** — `make_preview.py` แปลง `cid:` เป็น `data:` URI แล้วเซฟเป็น `preview.html` เปิดเบราว์เซอร์ได้

---

## ตอนนี้มีซอร์ส 3 ที่ ต้องระวัง

```
C:\Users\Sapon.S\lambda_function.py                    ← แก้ที่นี่ที่เดียว
scripts\lambda\googlesheet-to-s3\lambda_function.py    ← copy ตอน build
Lambda Console (แก้ได้แล้วหลังมี layer)                  ← ต้อง Download กลับมาทับ
```

**เคยหลุดมาแล้วครั้งหนึ่ง** — paste ลงไฟล์ในรีโป แล้ว build ทับด้วยตัวบนเครื่องที่ยังไม่ได้แก้

---

## เชื่อมกับโน้ตอื่น

[[Google Sheet Pipeline]] · [[Google Sheet to S3 - Code Walkthrough]] · [[Glue Crawler]] · [[DMS Full Load Validation (Lambda)]] · [[Python Libraries]] · [[ETL & Spark]] · [[Decisions]] · [[AWS Services]] · [[Consent & PDPA]] · [[Data Standardization & Quality]] · [[GI + EV7 to 7Club]] · [[Pipeline Issues]]
