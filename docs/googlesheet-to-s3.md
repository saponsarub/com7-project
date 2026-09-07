# Google Sheet → S3 (Lambda)

เอกสารอธิบายโค้ดทีละฟังก์ชัน — pipeline นี้มี **2 Lambda**

| | โค้ด | หน้าที่ |
|---|---|---|
| 1 | `scripts/lambda/googlesheet-to-s3/` | ดึงชีต → S3 → เขียน log → ส่งเมล |
| 2 | `scripts/lambda/googlesheet-rowcount/` | นับแถวจากไฟล์จริงบน S3 แล้วเติมกลับเข้า log |

| | |
|---|---|
| เวอร์ชัน | 2.4.0 |
| Runtime | Python 3.13 · x86_64 |
| Handler | `lambda_function.lambda_handler` |
| Timeout / Memory | 10 นาที / 2048 MB |
| ปลายทาง | `s3://google-sheet-extract/google-sheet-{ev7,gi}/<table>/data.csv` |

---

## ภาพรวม

```
EventBridge (23:30)
      ▼
┌─ Lambda 1 · ingest ────────────────────────────────────┐
│  Secrets Manager ──► Google OAuth (JWT)                │
│         ▼                                              │
│  Sheets API ──► CSV (/tmp) ──► S3 data                 │
│         │            วนทุกชีต/tab · ingest ได้ 3 รอบ     │
│         ▼                                              │
│  log CSV ──► S3 log   (S3_row_count ยังว่าง)            │
│  รายงาน  ──► SES                                        │
└────────────────┬───────────────────────────────────────┘
                 │ invoke async · ไม่รอผล
                 ▼
┌─ Lambda 2 · rowcount ──────────────────────────────────┐
│  อ่าน log ──► เช็ค Etag ──► get_object ──► csv.reader   │
│         └──► เขียนทับ log เติม S3_row_count             │
└────────────────────────────────────────────────────────┘
```

หลักการเดียวที่คุมทุกอย่าง — **หนึ่ง tab = หนึ่งโฟลเดอร์ = หนึ่งตาราง** เพื่อให้ Glue Crawler (`Table level = 3`) แยกตารางถูก

---

## ค่าคงที่

### `SOURCES`

รายการชีตทั้งหมด เพิ่มชีตใหม่ = เพิ่ม dict หนึ่งก้อน ไม่ต้องแตะโค้ดส่วนอื่น

```python
{
    "id":     "1ZuZ...",             # spreadsheet ID (ระหว่าง /d/ กับ /edit ใน URL)
    "label":  "EV7 Main",            # ชื่อที่แสดงในรายงาน/อีเมล
    "brand":  "ev7",                 # ev7 หรือ gi
    "prefix": "google-sheet-ev7",    # โฟลเดอร์ชั้นบนใน S3
    "tabs":   {"Query": "ev7_query"} # ชื่อ tab -> ชื่อโฟลเดอร์/ตาราง
}
```

**ทำไมชื่อตารางมี prefix `ev7_` / `gi_`** — กันชื่อขึ้นต้นด้วยตัวเลข (`2025`) ซึ่ง Athena ไม่รับ และกันชนกับ reserved word (`filter`, `check`, `event`)

**service account ตัวเดียวใช้ได้ทุกชีต** — แต่ต้อง share ชีตแต่ละไฟล์ให้ `client_email` เป็น Viewer แยกกัน ถ้าลืมจะได้ **404 ไม่ใช่ 403** เพราะ Google จงใจไม่บอกว่าไฟล์มีอยู่จริงไหม

### Environment variables

| ตัวแปร | default | ไม่ตั้งแล้วเป็นยังไง |
|---|---|---|
| `SES_FROM` `SES_TO` | ว่าง | ไม่ส่งอีเมล · job ยังทำงานปกติ |
| `SES_REGION` | `ap-southeast-1` | **SES ไม่มีที่ ap-southeast-7** |
| `LOG_BUCKET` | ว่าง | ไม่เขียน log · job ยังทำงานปกติ |
| `LOG_PREFIX` | `ingest-log/source=google_sheet/job=...` | — |
| `HTTP_TIMEOUT` | `90` | วินาทีต่อการเรียก Sheets API หนึ่งครั้ง |
| `HTTP_RETRY` | `3` | ยิงซ้ำทันทีกี่ครั้งเมื่อ timeout / 429 / 5xx |
| `INGEST_PASSES` | `3` | รอบ ingest ทั้งหมด (1 ปกติ + 2 ลองใหม่) |
| `PASS_WAIT` | `20` | พักกี่วินาทีก่อนรอบถัดไป |
| `JOB_TYPE` | `Fullload` | ลงในคอลัมน์ `Job_Type` ของ log |
| `ROWCOUNT_LAMBDA` | ว่าง | ชื่อ Lambda นับแถว · ไม่ตั้ง = ไม่เรียก |
| `AWS_LAMBDA_FUNCTION_NAME` | — | Lambda ใส่ให้เอง |

**แพตเทิร์นเดียวกันทั้งหมด: ไม่ตั้ง = ปิดฟีเจอร์นั้น ไม่ใช่พัง** เพราะข้อมูลขึ้น S3 สำเร็จไปแล้ว การส่งเมลหรือเขียน log ไม่ควรลากงานหลักล่ม

**ต้องคุมให้ `HTTP_TIMEOUT × HTTP_RETRY` ไม่กินเวลา Lambda จนหมด** — มี `time_left()` เป็น guard อีกชั้น

### boto3 client วางนอก handler

```python
secrets = boto3.client("secretsmanager")
s3 = boto3.client("s3")
ses = boto3.client("ses", region_name=SES_REGION) if SES_FROM else None
```

โค้ดนอก handler รันเฉพาะตอน **cold start** — เห็นเป็น `Init Duration: ~800 ms` ที่หายไปในรอบถัดมาเพราะ Lambda ใช้ container เดิม

---

## ฟังก์ชันทีละตัว

### `total_tabs(runs)`

นับ tab ทั้งหมดที่ตั้งใจจะดึงในรอบนี้ ใช้เป็นตัวหารในบรรทัด `12 of 14 tabs`

### `time_left()`

วินาทีที่ Lambda เหลือ อ่านจาก `CONTEXT.get_remaining_time_in_millis()`

```python
CONTEXT = None          # handler ตั้งค่าให้ตอนเริ่ม

def time_left():
    try:
        return CONTEXT.get_remaining_time_in_millis() / 1000
    except Exception:
        return 900       # ตอนรันบนเครื่อง ไม่มี context
```

**ใช้เป็น guard ก่อน retry ทุกจุด** — ถ้าเวลาเหลือไม่พอสำหรับอีกรอบ จะเลิก retry แล้วรายงานว่า tab นั้นพัง **แทนที่จะดันจน Lambda ตายทั้งงาน**

```python
if time_left() > wait + HTTP_TIMEOUT + 30:
    time.sleep(wait); continue
print(f"  no retry {tab} - Lambda เหลือ {time_left():.0f}s ไม่พอ")
```

`+30` คือเผื่อเวลาเขียน CSV · อัปโหลด · เขียน log · ส่งเมล หลังจากนั้น

### `get_access_token()`

```python
secret_response = secrets.get_secret_value(SecretId=SECRET_NAME)
credentials = json.loads(secret_response["SecretString"])
creds = service_account.Credentials.from_service_account_info(credentials, scopes=[...])
creds.refresh(Request())
```

อ่าน service account JSON จาก Secrets Manager แล้วแลกเป็น access token

**ข้างในเกิดอะไรขึ้น** — Google ไม่รับ private key ตรง ๆ `refresh()` จะสร้าง **JWT** ที่มี `iss` (client_email), `scope`, `aud`, `exp` แล้ว**เซ็นด้วย RS256** ส่งไปแลก access token อายุ 1 ชั่วโมง

**ขั้นตอนเซ็นนี่เองที่บังคับให้ต้องมี `cryptography`** ซึ่งเป็น native code → ต้อง build package บน Linux เท่านั้น

**เซ็นครั้งเดียวใช้ได้ทุกชีต** — เรียกก่อนเข้าลูป ไม่ใช่ต่อชีต

`scope` เป็น `spreadsheets.readonly` — token หลุดก็แก้ชีตต้นทางไม่ได้

**ห้ามฝัง key ใน zip** ใครอ่านโค้ดฟังก์ชันได้ก็ได้กุญแจไปด้วย

### `fetch_tab(sheet_id, tab, token, client_email)`

```python
url = ".../spreadsheets/" + sheet_id + "/values/" + urllib.parse.quote(tab + "!A:ZZ")
```

- `A:ZZ` = 702 คอลัมน์ เผื่อไว้เกินพอ
- `quote()` แปลง `!` → `%21` และรองรับชื่อ tab ภาษาไทย (`ชีต1` → `%E0%B8%8A...`)

**บล็อก `except HTTPError` สำคัญ** — `urlopen` ทิ้ง response body ของ Google ทำให้เห็นแค่ `HTTP Error 400: Bad Request` ทั้งที่ Google ส่งคำอธิบายจริงมาด้วย ต้องดักเองแล้ว print ก่อน `raise` ต่อ

```python
print("Google API says:", e.read().decode("utf-8", "replace"))
print("Spreadsheet ID used:", sheet_id)
print("Service account:", client_email)
```

**retry ในตัว** — วนสูงสุด `HTTP_RETRY` ครั้ง backoff 2s → 4s

| อาการ | retry ไหม |
|---|---|
| `TimeoutError` · `URLError` | ✅ |
| HTTP **429** เกิน quota | ✅ |
| HTTP **500/502/503/504** ฝั่ง Google | ✅ |
| HTTP 400 (range ผิด) · 403 · 404 | ❌ ลองใหม่ก็ผิดเหมือนเดิม |

ทุกจุดที่จะ retry ต้องผ่าน `time_left()` ก่อน

> **`HTTPError` เป็น subclass ของ `URLError`** ต้องดัก `HTTPError` ก่อนเสมอ ไม่งั้น 400 จะไปโดน retry

### `write_csv(values, path)` → `(bytes, rows)`

```python
with open(path, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f, lineterminator=chr(10))
    writer.writerow(headers)
    for i in range(1, len(values)):
        row = values[i]
        values[i] = None
        if len(row) < width:
            row = row + [""] * (width - len(row))
        writer.writerow(row[:width])
```

| จุด | เหตุผล |
|---|---|
| เขียนลง **`/tmp`** | `/tmp` มี 512 MB **แยกจาก memory ของฟังก์ชัน** ขนาดชีตแทบไม่กระทบ RAM |
| `utf-8-sig` | ใส่ BOM ให้ Excel เปิดภาษาไทยไม่เพี้ยน |
| `lineterminator=chr(10)` | บังคับ LF — default ของ `csv` คือ CRLF ทำให้ Athena ติดอักขระ CR ท้ายคอลัมน์สุดท้าย |
| `csv.writer` | escape `"` และ `,` ให้เอง |
| `values[i] = None` | ปล่อย reference ทีละแถว ไม่ถือทั้งชุดค้างไว้ |
| เติมช่องที่ขาด | **Google ตัดช่องว่างท้ายแถวทิ้ง** ถ้าไม่เติม คอลัมน์จะเลื่อนตอน Athena อ่าน |

**วัดจริง 50,000 แถว × 12 คอลัมน์** — ต่อ string ใน RAM ใช้ 38.8 MB · เขียนทีละแถวลงไฟล์ใช้ 0.3 MB (ต่างกัน 130 เท่า)

คืน `rows` ที่เขียนจริงด้วยเพื่อเทียบกับต้นทางใน log (`rows_match`)

### `human_size(n)`

แปลง bytes → KB/MB/GB ฐาน 1024 ให้ตรงกับที่ S3 console แสดง

### `group_by_source(items, runs)`

จัดรายการตามชีต **คงลำดับตามที่ประกาศไว้ใน `SOURCES`** ไม่ใช่เรียงตามตัวอักษร — คนอ่านจะเห็นลำดับเดิมทุกวัน

### `build_report(...)` — รายงาน plain text

จัดตารางด้วยช่องว่าง ใช้ได้เพราะทุกค่าเป็น ASCII (ชื่อตาราง ตัวเลข หน่วย) **ไม่มีภาษาไทยในตาราง** จึงไม่มีปัญหาเรื่องความกว้างของสระ

จัดกลุ่มตามชีตพร้อม subtotal — **ชีตเดียวจะไม่มีหัวข้อกลุ่มและ subtotal** หน้าตาเหมือนเวอร์ชันก่อนหลายชีต

### `esc(text)`

escape `& < > "` — ค่าจากชีตไม่ควรกลายเป็น HTML tag

### `build_html(...)` — รายงาน HTML

| ข้อจำกัดของอีเมล | สิ่งที่ทำ |
|---|---|
| ตัด `<style>` ใน `<head>` ทิ้ง | ใช้ **inline style** ทุกที่ |
| ไม่รองรับ flex/grid | ใช้ **`<table>` layout** |
| Gmail บล็อก `data:` URI | โลโก้แนบเป็น attachment อ้างด้วย **`cid:logo`** |
| emoji encoding เพี้ยน | ใช้ **HTML entity** (`&#9989;` แทน ✅) |

`max-width: 880px` · แถบเขียวคั่นต่อชีต · แถวที่พังพื้นแดง + ❌ · subtotal ปิดท้ายทุกกลุ่ม

**ดูหน้าตาก่อนส่ง** — `make_preview.py` แปลง `cid:` เป็น `data:` URI แล้วเซฟเป็น `preview.html` เปิดเบราว์เซอร์ได้ (อีเมลจริงยังใช้ `cid:` เหมือนเดิม)

### `build_log_rows(...)` / `write_log(rows)`

log แบบ **หนึ่งแถวต่อหนึ่งตารางต่อหนึ่งรอบ · 34 คอลัมน์**

```
s3://<LOG_BUCKET>/<LOG_PREFIX>/year=2026/month=09/day=07/<Job_No>.csv
```

**21 คอลัมน์แรกเรียงตาม schema กลางของแผนก** เพื่อให้รวมกับ pipeline อื่นในตารางเดียวกันได้

| คอลัมน์ | มาจาก |
|---|---|
| `Date_key` | `started_at` → `20260907` |
| `Job_No` | `context.aws_request_id` (UUID) |
| `Datetime_key` `Job_Start_Datetime` | `started_at` |
| `Job_End_Datetime` | `finished_at` |
| `Job_Type` | env `JOB_TYPE` default `Fullload` |
| `Source_Type` | `google_sheet` |
| `Table_Name` / `Sheet_Name` | ปลายทาง / tab ต้นทาง |
| `Table_row count` | จำนวนแถวที่ Google ส่งมา |
| `Size_MB` | `bytes` ÷ 1048576 |
| `Job_Start_Datetime` `Job_End_Datetime` `Job_status` `Duration_min` | **ของ tab ในแถวนั้น ไม่ใช่ของทั้ง job** — หนึ่งแถว = หนึ่งตาราง ทุกช่องจึงต้องอธิบายตารางนั้น |

| **`Step_Function_Name` `Server_Name` `Port` `DB_Name`** | **ว่าง** — ไม่มีความหมายกับต้นทางที่เป็น HTTPS API |
| **`Threat_scan_Malware`** | **ว่าง** — ยังไม่มีบริการ scan (ดูหัวข้อท้าย) |
| **`S3_row_count` `Status_row_count`** | **ว่างตอนแรก** — Lambda 2 มาเติม |

**13 คอลัมน์ต่อท้าย** — ของเดิมที่ยังจำเป็น

| คอลัมน์ | ทำไมต้องเก็บ |
|---|---|
| `Write_Mode` `Column_count` | **D-15 บังคับ** แต่ไม่มีใน schema กลาง |
| `Table_status` | ผลรายตาราง (`Job_status` เป็นของทั้ง job) |
| `Run_status` `Run_Duration_min` | ผลรวม**ทั้งรอบ** (`SUCCESS` / `PARTIAL` / `FAILED`) — `Job_*` เป็นของแถวนั้น จึงต้องมีช่องระดับรอบแยก |
| `Table_Duration_sec` | เท่ากับ `Duration_min` แต่หน่วยวินาที อ่านง่ายกว่าตอน debug |
| `Header_Hash` | md5 ของหัวตาราง 16 ตัวแรก · **จับ schema drift ที่จำนวนคอลัมน์เท่าเดิมแต่สลับ/เปลี่ยนชื่อ** |
| `Target_Bucket` `S3_Key` | Lambda 2 ใช้หาไฟล์ · `S3_Key` อย่างเดียวไม่พอ |
| `Etag` | Lambda 2 ใช้เช็คว่าไฟล์ยังเป็นตัวเดิม |
| `Rows_Written` `Passes` `Source_Id` `Job_Version` | ตรวจสอบย้อนหลัง |

**เลือก CSV ไม่ใช่ JSON** — โครงสร้างแบน Crawler อ่านเป็นตารางได้เลยไม่ต้อง unnest และ D-15 ระบุว่า MIS เป็นผู้รับซึ่งเปิดด้วย Excel

**ใส่ BOM (`utf-8-sig`) + `ContentType: text/csv; charset=utf-8`** — ไม่มี BOM แล้ว Excel อ่านภาษาไทย (`ชีต1`) ไม่ออก · BOM อยู่ในบรรทัด header ซึ่ง Athena ข้ามด้วย `skip.header.line.count = 1`

**ต้องแยกถังจากถังข้อมูล** ไม่งั้น Glue Crawler ที่สแกนถังข้อมูลจะไปเจอ log แล้วสร้างตารางมั่ว

> ⚠️ `Table_row count` **มีช่องว่างในชื่อ** ตาม schema กลาง — ตอน query ใน Athena ต้องครอบ `"Table_row count"` ทุกครั้ง

---

## Lambda 2 · `googlesheet-rowcount`

**1.9 KB** เพราะใช้แค่ stdlib + boto3 ที่ Lambda มีให้ — แก้โค้ดใน Console ได้เลย

ถูกเรียกแบบ **async** จาก `write_log()` หลังเขียน log สำเร็จ

```python
lam.invoke(
    FunctionName=ROWCOUNT_LAMBDA,
    InvocationType="Event",              # ไม่รอผล ไม่กินเวลา job หลัก
    Payload=json.dumps({"log_bucket": LOG_BUCKET, "log_key": key}).encode(),
)
```

### `count_rows(bucket, key)`

```python
body = s3.get_object(Bucket=bucket, Key=key)["Body"]
text = io.TextIOWrapper(body, encoding="utf-8-sig", newline="")
return max(sum(1 for _ in csv.reader(text)) - 1, 0)
```

**ต้องอ่านผ่าน `csv.reader` ห้ามนับ `
`** — เซลล์ที่อยู่ที่คนพิมพ์ขึ้นบรรทัดใหม่ในชีตจะถูกครอบด้วย `"` แล้วเก็บ newline ไว้ข้างใน นับ newline ตรง ๆ จะได้เกินจริง

```csv
lead_id,address
1,"123 ถนนสุขุมวิท
แขวงคลองเตย"          ← 1 แถว แต่ 2 newline
```

### `lambda_handler(event, context)`

1. อ่าน log CSV จาก S3
2. วนทุกแถวที่ `Table_status = ok`
3. **`head_object` เช็ค `Etag` ก่อน** — ไม่ตรงแปลว่าไฟล์ถูกทับหลัง ingest → ใส่ `STALE` ไม่นับ
4. ข้ามไฟล์ที่เกิน `MAX_BYTES` (default 200 MB) → `SKIPPED_TOO_LARGE`
5. นับแถว → เติม `S3_row_count` และ `Status_row_count`
6. เขียนทับ log เดิมที่ key เดียวกัน

**ค่าใน `Status_row_count`**

| ค่า | หมายถึง |
|---|---|
| `MATCH` | ต้นทาง = ปลายทาง |
| `MISMATCH` | ไม่ตรง — ข้อมูลหายระหว่างทาง |
| `STALE` | ไฟล์ถูกทับแล้ว นับไปก็ไม่ตรงกับ log แถวนี้ |
| `SKIPPED_TOO_LARGE` | ไฟล์ใหญ่เกินเพดาน |
| `ERROR: ...` | อ่านไฟล์ไม่ได้ |

### การเชื่อม 2 ตัว

**ใช้ direct invoke** — Lambda 1 ยิงต่อแบบ async หลังเขียน log เสร็จ

```python
lam.invoke(FunctionName=ROWCOUNT_LAMBDA,
           InvocationType="Event",          # ไม่รอผล ไม่กินเวลา job นี้
           Payload=json.dumps({"log_bucket": ..., "log_key": ...}).encode())
```

ไม่ตั้ง `ROWCOUNT_LAMBDA` = ไม่เรียก · log จะมี `S3_row_count` ว่างไว้

**`parse_event()` ใน Lambda 2 รับได้ 2 แบบ** — payload ตรง กับ S3 Event Notification (`Records[0].s3`) จึงเปลี่ยนวิธีเชื่อมได้โดยไม่ต้องแก้โค้ด

| วิธีเชื่อม | จุดที่ต้อง config | พังแล้วรู้ไหม |
|---|---|---|
| **direct invoke** (ใช้อยู่) | env + IAM invoke = **3 จุด** | เห็น `ROWCOUNT INVOKE FAILED` ใน log ของ Lambda 1 |
| S3 Event Notification | + bucket notification + lambda resource policy = **5 จุด** | เงียบถ้าลืม `add-permission` |

**เลือก direct invoke เพราะจุดที่พลาดได้น้อยกว่าและพังแล้วเห็น** — ข้อเสียคือ Lambda 1 ต้องรู้ชื่อ Lambda 2 ซึ่งยอมรับได้สำหรับ pipeline 2 ขั้น

ถ้าวันหนึ่งอยากแยกขาดจริง: ลบ env `ROWCOUNT_LAMBDA` → ตั้ง S3 notification บน prefix `ingest-log/` → `aws lambda add-permission` ให้ `s3.amazonaws.com` · **โค้ดไม่ต้องแตะ**

### กันนับซ้ำ

```python
todo = [r for r in rows if r["Job_status"] == "SUCCESS" and not r["S3_row_count"]]
if not todo:
    return {"statusCode": 200, "skipped": "already counted"}
```

จำเป็นทั้งสองวิธีเชื่อม — กันคนกดรันซ้ำมือ และกัน loop ถ้าเปลี่ยนไปใช้ S3 event

### ทำไมแยกเป็น Lambda ที่ 2

| | |
|---|---|
| ✅ ไม่ทำให้ job หลักช้าลง | ข้อมูล 110 MB ถ้าโหลดกลับมานับในตัวเดิมจะเพิ่มเวลาเกือบเท่าตัว |
| ✅ พังแยกกัน | นับไม่ได้ก็ยังมี log และไฟล์ครบ |
| ⚠️ อีเมลออกก่อน `S3_row_count` มีค่า | |
| ⚠️ ต้องดู CloudWatch 2 log group | |

---

## Build

```powershell
pip install --target lambda-build --platform manylinux2014_x86_64 --implementation cp `
            --python-version 3.13 --only-binary=:all: google-auth requests
```

`cryptography` เป็น native code ผูกกับ OS — `pip install` บน Windows จะได้ `.pyd` ที่ Lambda อ่านไม่ออก **ต้อง build เป็น Linux wheel เท่านั้น**

ตรวจก่อน deploy: ต้องไม่มี `.pyd` `.dll` `.exe` และ `.so` ต้องลงท้ายด้วย `linux-gnu` หรือ `abi3`

---

## ที่ยังไม่ได้ทำ

- [ ] `values:batchGet` — รวมทุก tab ของชีตเดียวกันเป็นคำขอเดียว (14 → 4) แก้ต้นเหตุที่ tab ท้าย ๆ timeout
- [ ] `Threat_scan_Malware` — ต้องตัดสินใจระดับโครงการ · GuardDuty Malware Protection for S3 (PoC บันทึกว่า scan ทุก object ~3,500 USD/เดือน) หรือ Macie ที่ยังไม่เปิดที่ ap-southeast-7
- [ ] EventBridge Scheduler 23:30 น. (`cron(0 23 * * ? *)` timezone `Asia/Bangkok`) + DLQ
- [ ] เพิ่ม path `google-sheet-gi/` ให้ Glue Crawler
- [ ] CloudWatch metric filter จับ `MISMATCH` และ `ROWCOUNT INVOKE FAILED`
- [ ] `NEXT_RUN` ยัง hard-code เป็น `"Tomorrow 23:30 (UTC+7)"`
- [ ] error ถาวร (400/403/404) ยังถูกยกไป pass 2-3 ทั้งที่แก้ไม่ได้
- [ ] `rows_delta` เทียบกับรอบก่อน · null rate · duplicate count

---

## ประวัติเวอร์ชัน

| เวอร์ชัน | เปลี่ยนอะไร |
|---|---|
| 1.2.2 | ดึงทุก tab ในรอบเดียว · แยกโฟลเดอร์ตามตาราง · รายงาน HTML + SES |
| 1.3.x | เขียน log ลง S3 (JSON → CSV) · ขยายความกว้างอีเมล |
| 1.4.0 | **รองรับหลายชีต** — `SOURCES` แทน `SPREADSHEET_ID` เดี่ยว · อีเมลจัดกลุ่มตามชีต |
| 1.5.x | ใส่ชีต Grab · Lineman · GI ครบ 4 ชีต 14 tabs |
| 1.6.x | เอาชื่อชีตจาก Google ออกจากรายงาน ใช้ `label` แทน · ลบ `fetch_sheet_title` |
| 1.7-1.9 | โลโก้ EV7/GI · แยกคอลัมน์ Table/Source tab · font stack JetBrains Mono |
| 1.10.x | **retry ใน `fetch_tab`** + `time_left()` guard |
| 1.11.0 | **ingest หลายรอบ** (`ingest_tab` + pass loop) |
| 1.11.1 | log ใส่ BOM ให้ Excel อ่านภาษาไทยได้ |
| 2.0.0 | **log เปลี่ยนเป็น schema กลางของแผนก** · ตรวจไบต์ปลายทางหลังอัปโหลด · `Header_Hash` · `Etag` · `Tab_Duration_sec` · เรียก **Lambda 2 นับแถวจาก S3** |
| 2.1.0 | แยกเวลาเป็นราย tab |
| 2.3.0 | ลองเปลี่ยนเป็น S3 Event Notification |
| **2.2.0** | **`Job_Start_Datetime` `Job_End_Datetime` `Job_status` `Duration_min` เป็นของ tab ในแถวนั้น** ตามเจตนาเดิมของ schema · ย้ายผลรวมทั้งรอบไป `Run_status` / `Run_Duration_min` · Lambda 2 อ่าน `Job_status = SUCCESS` |
| **2.4.0** | **กลับมาใช้ direct invoke** — จุด config น้อยกว่า และพังแล้วเห็นใน log · Lambda 2 ยังรับ S3 event ได้ เปลี่ยนวิธีเชื่อมโดยไม่ต้องแก้โค้ด |
