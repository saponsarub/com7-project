# Google Sheet to S3 (Lambda)

> **หมายเหตุที่มา:** บันทึกจากการ deploy จริงบน AWS account `603238661233` เมื่อ 2026-09-02 — ทุกอาการที่เขียนไว้มาจาก CloudWatch log ของฟังก์ชันจริง ไม่ใช่เอกสาร

Pipeline เส้นเล็กที่สุดใน lake ตอนนี้ — ดึงข้อมูลจาก Google Sheet ที่ทีมงานคีย์มือ แล้วลงจอดเป็น CSV บน S3 เพื่อให้ Glue/Athena อ่านต่อได้

---

## Flow

```
EventBridge (23:30)
      ▼
Lambda 1 · ingest
  Secrets Manager ──► Google OAuth (JWT) ──► Sheets API ──► CSV (/tmp) ──► S3 data
  log CSV ──► S3 log  (S3_row_count ยังว่าง)
  รายงาน  ──► SES
      │ invoke async
      ▼
Lambda 2 · rowcount
  อ่าน log ──► เช็ค Etag ──► นับแถวจากไฟล์จริง ──► เขียนทับ log
```

**4 ชีต · 14 tabs** · v2.4.0 · รันสำเร็จ 14/14 ใน 32.8 วินาที (2026-09-07)

| ชีต | brand | tabs | ปลายทาง |
|---|---|---|---|
| EV7 Main | ev7 | 7 | `google-sheet-ev7/ev7_*/` |
| Grab | ev7 | `Clean` · `ชีต1` | `google-sheet-ev7/Grab_Clean/` · `Grab/` |
| Lineman | ev7 | `Clean` · `ชีต1` | `google-sheet-ev7/Lineman_Clean/` · `Lineman/` |
| GI | gi | `rawdataInteresting` · `rawdataTestdrive` · `rawdataBooking` | `google-sheet-gi/GI_Interest/` · `GI_Testdrive/` · `GI_Booking/` |

|                              |                                                       |
| ---------------------------- | ----------------------------------------------------- |
| Secret                       | `com7/google-sheets/service-account`                  |
| Lambda role                  | `test-ingest-googlesheet-role-mg3ktraq`               |
| Runtime                      | Python 3.13 · x86_64 · 1024 MB · 5 นาที               |
| **โค้ด**                     | `scripts/lambda/googlesheet-to-s3/lambda_function.py` |
| **เอกสารอธิบายทีละฟังก์ชัน** | `docs/googlesheet-to-s3.md`                           |

**หนึ่ง tab = หนึ่งโฟลเดอร์ = หนึ่งตาราง** เพื่อให้ Crawler แยกตารางถูก → [[Glue Crawler]]

**service account ตัวเดียวใช้ได้ทุกชีต** แต่ต้อง share แต่ละไฟล์ให้ `client_email` แยกกัน — ลืมแล้วได้ **404 ไม่ใช่ 403**

**ข้อมูลทั้งหมดเป็นฝั่ง EV** เกี่ยวกับ [[GI + EV7 to 7Club]] โดยตรง

---

## โครงโค้ด

**คำอธิบายทีละฟังก์ชันอยู่ที่ `docs/googlesheet-to-s3.md` ในรีโป** — โน้ตนี้เก็บเฉพาะข้อตัดสินใจและกับดักที่ใช้ซ้ำกับ pipeline อื่นได้

| จุด | เหตุผล |
|---|---|
| **boto3 client วางนอก handler** | รันเฉพาะ cold start · เห็นเป็น `Init Duration ~800 ms` ที่หายไปในรอบถัดมา |
| **credential อยู่ใน Secrets Manager** | ไฟล์ service account มี private key ถ้าฝังใน zip ใครอ่านโค้ดได้ก็ได้กุญแจ |
| **เซ็น JWT ครั้งเดียวใช้ได้ทุกชีต** | token อายุ 1 ชม. เรียกก่อนเข้าลูป ไม่ใช่ต่อชีต |
| **เขียน CSV ผ่าน `/tmp`** | `/tmp` 512 MB แยกจาก memory ของฟังก์ชัน — วัดจริง 50k แถว: ต่อ string ใน RAM 38.8 MB vs เขียนไฟล์ 0.3 MB |
| **`upload_file` ไม่ใช่ `put_object`** | สตรีมจากดิสก์ แบ่ง multipart อัตโนมัติ |
| **`try/except` อยู่ระดับ tab** | tab เดียวพังไม่ลากทั้งงานล่ม |
| **ไม่ตั้ง env = ปิดฟีเจอร์ ไม่ใช่พัง** | SES/log ส่งไม่ได้ไม่ควรลากงานหลักล่ม เพราะข้อมูลขึ้น S3 แล้ว |
| **retry 2 ชั้น** | ชั้นใน = ยิงซ้ำทันที (สะดุดชั่วขณะ) · ชั้นนอก = ทำใหม่ทั้งรอบหลังพัก 20 วินาที (ต้นทางหน่วงเพราะยิงติดกันหลายคำขอ) |
| **guard ด้วยเวลาที่ Lambda เหลือ** | ก่อน retry ทุกครั้งเช็ค `get_remaining_time_in_millis()` — ไม่พอก็ยอมแพ้ tab นั้น **แทนที่จะดันจนตายทั้งงาน** |

### กับดักที่เจอจริง

| กับดัก | อาการ |
|---|---|
| **Google ตัดช่องว่างท้ายแถวทิ้ง** | ไม่เติมให้ครบ คอลัมน์จะเลื่อนตอน Athena อ่าน |
| **`csv` default เป็น CRLF** | ต้องบังคับ LF ไม่งั้น Athena ติดอักขระ CR ท้ายคอลัมน์สุดท้าย |
| **`urlopen` ทิ้ง error body ของ Google** | เห็นแค่ `HTTP Error 400` ทั้งที่ Google บอกสาเหตุมาด้วย ต้องดักเอง |
| **`/tmp` อยู่กับ container ที่ใช้ซ้ำ** | ไม่ลบจะพอกจนเจอ `No space left on device` |
| **`ses:SendRawEmail` คนละ action กับ `ses:SendEmail`** | ใส่ผิดตัวได้ AccessDenied |
| **Gmail บล็อก `data:` URI** | โลโก้ต้องแนบเป็น attachment อ้างด้วย `cid:` |

---

## Packaging — ทำไมต้อง zip และทำไมต้อง Linux

**บทเรียนที่ใช้ซ้ำได้กับทุก Lambda ที่ต้องใช้ library นอก stdlib**

### ทำไมต้อง zip

Lambda ให้ Python มาแค่ **standard library + boto3** ไม่มี `google-auth`, `requests`, `cryptography` และไม่มี `pip install` บนเซิร์ฟเวอร์ให้เรียก — ต้องแพ็ก library ไปพร้อมโค้ด แล้ว Lambda จะแตก zip ลง `/var/task/` ซึ่งเป็น import path แรก

### ทำไมต้อง Linux

Library แบ่งเป็น 2 แบบ  

| แบบ                            | ตัวอย่าง                                           | ย้ายข้ามเครื่อง |
| ------------------------------ | -------------------------------------------------- | --------------- |
| Pure Python                    | `google-auth` · `pyasn1` · `requests`              | ได้             |
| **มี native code คอมไพล์แล้ว** | **`cryptography`** · `cffi` · `charset_normalizer` | **ไม่ได้**      |

`cryptography` มีโค้ด Rust/C คอมไพล์ไว้ ซึ่งผูกกับทั้ง **OS และเวอร์ชัน Python**

`pip install` บน Windows + Python 3.14 จะได้ `_cffi_backend.cp314-win_amd64.pyd` (นามสกุล `.pyd` คือ DLL ของ Windows) แต่ Lambda คือ Amazon Linux + Python 3.13 อ่านไฟล์นั้นไม่ออก

### คำสั่ง build ที่ถูกต้อง

```
pip install --target lambda-build --platform manylinux2014_x86_64 --implementation cp --python-version 3.13 --only-binary=:all: google-auth requests
```

| flag | หน้าที่ |
|---|---|
| `--platform manylinux2014_x86_64` | ดาวน์โหลด wheel ของ Linux x86_64 แทนของเครื่องตัวเอง |
| `--python-version 3.13` | ให้ตรงกับ runtime ของ Lambda |
| `--only-binary=:all:` | ห้าม pip build จาก source (ถ้า build จะได้ของ Windows อีก) |
| `--target` | ลงในโฟลเดอร์แทน site-packages |

**ตรวจว่า build ถูก** — ต้องไม่มี `.pyd` `.exe` `.dll` เหลือ และไฟล์ `.so` ต้องลงท้ายด้วย `linux-gnu` หรือ `abi3`

```
_cffi_backend.cpython-313-x86_64-linux-gnu.so     ถูก
cryptography/hazmat/bindings/_rust.abi3.so        ถูก
```

pip บน Windows ยังแถมโฟลเดอร์ `bin/` ที่มี `.exe` มาด้วย — ลบทิ้งได้

### 3 ค่าที่ต้องตรงกันเสมอ

| ตอน build                         | ตอนตั้งค่า Lambda                                          |
| --------------------------------- | ---------------------------------------------------------- |
| `--platform manylinux2014_x86_64` | Architecture = x86_64 (ถ้าใช้ Graviton ต้องเป็น `aarch64`) |
| `--python-version 3.13`           | Runtime = Python 3.13                                      |
| ชื่อไฟล์ `.py` + ชื่อฟังก์ชัน     | Handler = `lambda_function.lambda_handler`                 |

### zip ต้องใช้ path แบบ POSIX

ที่ใช้จริงคือ Python `zipfile` เขียน arcname ด้วยเครื่องหมาย `/` และตั้ง permission 755 ให้ไฟล์ `.so` — ปลอดภัยกว่าปล่อยให้เครื่องมือฝั่ง Windows จัดการ path ให้เอง

---

## ปัญหาที่เจอจริง 5 ข้อ

| #   | Error ที่ขึ้น                                                                                          | สาเหตุจริง                                             | วิธีแก้                     |
| --- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------ | --------------------------- |
| 1   | `Runtime.ImportModuleError: cannot import name 'exceptions' from 'cryptography.hazmat.bindings._rust'` | build บน Windows + Python 3.14                         | รีบิลด์ด้วย manylinux wheel |
| 2   | `AccessDeniedException` ตอน `GetSecretValue`                                                           | Lambda role ไม่มี policy                               | เพิ่ม inline policy         |
| 3   | `HTTP Error 404` จาก Sheets API                                                                        | Spreadsheet ID พิมพ์เกิน (46 ตัวอักษร แทนที่จะเป็น 44) | แก้ ID                      |
| 4   | `Task timed out after 3.00 seconds`                                                                    | timeout default 3 วินาที                               | ตั้ง 5 นาที                 |
| 5   | `Runtime.OutOfMemory` ที่ 127/128 MB                                                                   | ถือข้อมูลชุดเดียวซ้อนกัน 3 ชุด                         | เขียนผ่าน `/tmp` + `del`    |

### กับดักที่ควรจำ

**404 ของ Sheets API ไม่ได้แปลว่าไฟล์ไม่มี** — ถ้า service account ยังไม่ถูก share เข้าชีต Google จะตอบ 404 ไม่ใช่ 403 (จงใจไม่บอกว่าไฟล์มีจริงไหม) จึงแยกไม่ออกระหว่าง "ID ผิด" กับ "ไม่มีสิทธิ์" ต้องเช็กทั้งสองทาง

**`urlopen` ทิ้ง error body ของ Google** — Python ขึ้นแค่ `HTTP Error 404: Not Found` ทั้งที่ Google ส่งคำอธิบายมาใน body ต้องดักเองถึงจะเห็น

```python
except urllib.error.HTTPError as e:
    print("Google API says:", e.read().decode("utf-8", "replace"))
    print("Spreadsheet ID used:", SPREADSHEET_ID)
    print("Service account:", credentials.get("client_email"))
    raise
```

**Spreadsheet ID ของ Google ยาว 44 ตัวอักษรเสมอ** — นับความยาวก่อนคือวิธีจับ typo ที่เร็วที่สุด

**128 MB ให้ CPU น้อยมาก** — Lambda จัดสรร CPU ตามสัดส่วน memory การเพิ่มเป็น 1024 MB มักถูกลงด้วยซ้ำเพราะคิดค่าใช้จ่ายตาม GB-วินาที งานเสร็จเร็วกว่าหลายเท่า

---

## IAM policy ที่ต้องมี

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadGoogleServiceAccountSecret",
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
      "Resource": "arn:aws:secretsmanager:*:603238661233:secret:com7/google-sheets/service-account-*"
    },
    {
      "Sid": "WriteCsvToS3",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::google-sheet-extract/google-sheet-ev7/*"
    }
  ]
}
```

**ARN ของ secret มี suffix สุ่มต่อท้าย** ที่ AWS เติมให้ตอนสร้าง จึงต้องปิดท้ายด้วย `*` ไม่งั้นไม่ match

ถ้า secret เข้ารหัสด้วย customer-managed KMS key ต้องเพิ่ม `kms:Decrypt` ด้วย — เคสนี้ใช้ `aws/secretsmanager` จึงไม่ต้อง

---

## ค่าตั้งที่ใช้อยู่

| ค่า          | ตั้งเป็น                         |
| ------------ | -------------------------------- |
| Runtime      | Python 3.13                      |
| Architecture | x86_64                           |
| Handler      | `lambda_function.lambda_handler` |
| Timeout      | 5 นาที                           |
| Memory       | 1024 MB                          |

---

## log — ใช้ schema กลางของแผนกแล้ว

**34 คอลัมน์ · 21 ตัวแรกเรียงตาม schema กลาง** เพื่อให้รวมกับ pipeline อื่นในตารางเดียวกันได้ · 13 ตัวท้ายเป็นของเดิมที่ยังจำเป็น

```
s3://com7-ingest-logs-<account>/ingest-log/source=google_sheet/job=.../
  year=2026/month=09/day=07/<Job_No>.csv
```

| ตกลงกันไว้ | ค่า |
|---|---|
| `Job_No` | UUID จาก `aws_request_id` |
| `Job_Type` | `Fullload` |
| `Job_Start_Datetime` `Job_End_Datetime` `Job_status` `Duration_min` `Error_message` | **ของ tab ในแถวนั้น** ไม่ใช่ของทั้งรอบ |
| `Step_Function_Name` `Server_Name` `Port` `DB_Name` | ว่าง — ไม่มีความหมายกับต้นทางที่เป็น HTTPS API |
| `Threat_scan_Malware` | ว่าง — ยังไม่มีบริการ scan |

**คอลัมน์ที่ยืนยันว่าต้องเก็บไว้แม้ schema กลางไม่มี**

| | ทำไม |
|---|---|
| `Write_Mode` · `Column_count` | **[[Decisions\|D-15]] บังคับ** |
| `Run_status` · `Run_Duration_min` | **`Job_*` เป็นของ tab ในแถวนั้น** (หนึ่งแถว = หนึ่งตาราง) จึงต้องมีช่องผลรวมทั้งรอบแยกออกมา |
| `Table_Duration_sec` | เท่ากับ `Duration_min` แต่หน่วยวินาที อ่านง่ายกว่าตอน debug |
| `Header_Hash` | md5 หัวตาราง — **จับ schema drift ที่จำนวนคอลัมน์เท่าเดิมแต่สลับ/เปลี่ยนชื่อ** → [[Data Standardization & Quality]] |
| `Target_Bucket` · `S3_Key` · `Etag` | Lambda 2 ใช้หาไฟล์และยืนยันว่ายังเป็นตัวเดิม |

**เลือก CSV ไม่ใช่ JSON** เพราะโครงสร้างแบน Crawler อ่านเป็นตารางได้เลย และ D-15 ระบุว่า MIS เป็นผู้รับซึ่งเปิดด้วย Excel

**ต้องใส่ BOM** ไม่งั้น Excel อ่านภาษาไทย (`ชีต1`) ไม่ออก — ไบต์ในไฟล์เป็น UTF-8 ถูกต้องอยู่แล้ว ปัญหาอยู่ที่ตอนเปิด

**ต้องแยกถังจากถังข้อมูล** ไม่งั้น Crawler ที่สแกนถังข้อมูลจะไปเจอ log แล้วสร้างตารางมั่ว → [[Glue Crawler]]

> ⚠️ `Table_row count` มีช่องว่างในชื่อตาม schema กลาง — query ใน Athena ต้องครอบ `"Table_row count"` ทุกครั้ง

## Lambda ตัวที่ 2 — นับแถวจากไฟล์จริง

**ที่มา:** `rows_written` เดิมคำนวณจากต้นทาง (`len(values)-1`) จึงเท่ากับ `rows_source` เสมอ — **ไม่ได้ตอบ D-15 ว่าปลายทางเท่าต้นทางไหม**

**บทเรียนที่ใช้ซ้ำได้กับทุก pipeline: คอลัมน์ตรวจสอบที่คำนวณจากต้นทางเดียวกันไม่ใช่การตรวจสอบ** — ต้องวัดจากปลายทางจริง

| ชั้นการตรวจ | ต้นทุน | จับอะไรได้ |
|---|---|---|
| นับที่ `csv.writer` | ฟรี | bug ในลูป · แถวที่หลุด |
| **เทียบ `ContentLength` หลังอัปโหลด** | ฟรี (`head_object` เรียกอยู่แล้ว) | อัปโหลดไม่ครบ |
| **อ่านกลับจาก S3 แล้วนับ** | +เวลาเท่าตัว → **แยกเป็น Lambda 2** | ทุกกรณี |

**ต้องอ่านผ่าน `csv.reader` ห้ามนับ `
`** — เซลล์ที่อยู่ที่คนพิมพ์ขึ้นบรรทัดใหม่ในชีตถูกครอบด้วย `"` การนับ newline จะได้เกินจริง

**เช็ค `Etag` ก่อนนับ** — ไฟล์ถูกทับหลัง ingest แล้วนับ จะได้เลขที่ไม่ตรงกับ log แถวนั้น → ใส่ `STALE` แทน

| `Status_row_count`                 | หมายถึง                   |
| ---------------------------------- | ------------------------- |
| `MATCH` / `MISMATCH`               | ต้นทางเท่า/ไม่เท่าปลายทาง |
| `STALE`                            | ไฟล์ถูกทับแล้ว            |
| `SKIPPED_TOO_LARGE` · `ERROR: ...` | ข้ามไป                    |
|                                    |                           |

**เรียกแบบ async (`InvocationType="Event"`)** — job หลักยิงแล้วจบทันที ไม่ช้าลง

### เลือกวิธีเชื่อม 2 Lambda ยังไง

| | direct invoke (ใช้อยู่) | S3 Event Notification |
|---|---|---|
| จุดที่ต้อง config | **3** | 5 |
| พังแล้วรู้ไหม | เห็นใน log ของตัวที่ 1 | **เงียบ** ถ้าลืม `add-permission` |
| แยกขาดไหม | ตัวที่ 1 ต้องรู้ชื่อตัวที่ 2 | แยกขาด |

**เลือก direct invoke เพราะจุดที่พลาดได้น้อยกว่าและพังแล้วเห็น** — การแยกขาดเป็นข้อดีเชิงทฤษฎีสำหรับ pipeline แค่ 2 ขั้น ไม่คุ้มกับ config ที่เพิ่มมา 2 จุดซึ่งพลาดแล้วเงียบ

**บทเรียนที่ใช้ซ้ำได้: เลือกสถาปัตยกรรมตามจำนวนจุดที่พลาดได้ ไม่ใช่ตามความสวยของ diagram**

Lambda 2 เขียนให้รับได้ทั้ง 2 แบบ (`parse_event`) — เปลี่ยนวิธีเชื่อมภายหลังได้โดยไม่ต้องแก้โค้ด

**ข้อแลกเปลี่ยน** — อีเมลออกไปก่อน `S3_row_count` มีค่า และต้องดู CloudWatch 2 log group

---

## ข้อควรระวัง

**ไฟล์ปลายทางชื่อ `leads-ev7-2026.csv` น่าจะเป็นข้อมูลลูกค้าที่มี PII** ถ้าใช่ ต้องอยู่ใต้กติกาเดียวกับข้อมูลลูกค้าอื่นใน lake → [[Consent & PDPA]] · [[Customer Identity]] `[อนุมาน จากชื่อไฟล์ ยังไม่ได้ดูเนื้อข้อมูลจริง]`

**Google Sheet เป็นต้นทางที่ไม่มี schema บังคับ** — คนแก้ชีตเพิ่ม ลบ หรือสลับคอลัมน์เมื่อไหร่ก็ได้ และ pipeline จะไม่รู้ตัว เพราะโค้ดยึด `values[0]` เป็น header เสมอ ปัญหาชุดเดียวกับ [[Data Standardization & Quality]]

**ยังเป็น manual trigger** — ยังไม่ได้ผูก EventBridge schedule เข้ากับรอบ 23:30 น. ที่ทีมตกลงกันไว้

---

## เชื่อมกับโน้ตอื่น

[[Google Sheet to S3 - Code Walkthrough]] · [[ETL & Spark]] · [[Python Libraries]] · [[AWS Services]] · [[Architecture]] · [[GI + EV7 to 7Club]] · [[EV Systems]] · [[Consent & PDPA]] · [[Data Standardization & Quality]] · [[Pipeline Issues]]
