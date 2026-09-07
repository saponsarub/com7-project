# Library Reference

library ทั้งหมดที่ `scripts/lambda/googlesheet-to-s3/` ใช้ — ทั้งที่เรียกตรงและที่ติดมาเป็น dependency
พร้อมฟังก์ชันสำคัญที่**ยังไม่ได้ใช้แต่น่าจะได้ใช้** ในงานถัดไป

| ชั้น | library |
|---|---|
| stdlib | `json` `csv` `io` `os` `time` `datetime` `urllib` `email` |
| AWS | `boto3` (Lambda มีให้ ไม่ต้องแพ็ก) |
| Google | `google-auth` 2.57.0 |
| dependency ของ google-auth | `cryptography` 50.0.1 · `cffi` 2.1.1 · `pycparser` 3.0 · `pyasn1` 0.6.4 · `pyasn1_modules` 0.4.2 |
| dependency ของ requests | `requests` 2.34.2 · `urllib3` 2.7.0 · `certifi` 2026.7.22 · `idna` 3.19 · `charset_normalizer` 3.5.1 |

---

# Standard library

## `json`

https://docs.python.org/3/library/json.html

| ฟังก์ชัน | ใช้ในโค้ดไหม | ทำอะไร |
|---|---|---|
| `json.loads(s)` | ✅ | string → dict |
| `json.dumps(obj)` | ✅ | dict → string |
| `json.load(fp)` / `json.dump(obj, fp)` | ❌ | อ่าน/เขียนจาก file object ตรง ๆ |

**พารามิเตอร์ที่ควรรู้**

```python
json.dumps(obj, ensure_ascii=False)   # ภาษาไทยไม่กลายเป็น ก
json.dumps(obj, indent=2)             # อ่านง่ายตอน debug
json.dumps(obj, default=str)          # กัน "Object of type datetime is not JSON serializable"
json.dumps(obj, sort_keys=True)       # key เรียงเหมือนเดิมทุกครั้ง เทียบ diff ได้
```

**`default=str` ช่วยได้บ่อย** — `datetime`, `Decimal` (ที่ DynamoDB คืนมา) แปลงไม่ได้โดย default

## `csv`

https://docs.python.org/3/library/csv.html

| ฟังก์ชัน | ใช้ | ทำอะไร |
|---|---|---|
| `csv.writer(f)` | ✅ | เขียนจาก list |
| `csv.DictWriter(f, fieldnames=...)` | ✅ | เขียนจาก dict (ใช้ในไฟล์ log) |
| `csv.reader(f)` | ❌ | อ่านเป็น list |
| `csv.DictReader(f)` | ❌ | อ่านเป็น dict ใช้ header เป็น key |
| `csv.Sniffer()` | ❌ | เดา delimiter และว่ามี header ไหม |
| `csv.field_size_limit(n)` | ❌ | ขยายเพดานขนาด field (default 128 KB) |

**พารามิเตอร์ที่ควรรู้**

```python
csv.writer(f, lineterminator="\n")      # default เป็น \r\n → Athena ติดอักขระ CR
csv.writer(f, quoting=csv.QUOTE_ALL)    # ครอบทุกช่อง
csv.writer(f, quoting=csv.QUOTE_MINIMAL)  # default ครอบเฉพาะที่จำเป็น
csv.DictWriter(f, fieldnames=[...], extrasaction="ignore")  # key เกินไม่ error
csv.DictWriter(f, fieldnames=[...], restval="")             # key ขาดใส่ค่านี้
```

**ต้องเปิดไฟล์ด้วย `newline=""` เสมอ** ไม่งั้นบน Windows จะได้บรรทัดว่างคั่น

## `io`

https://docs.python.org/3/library/io.html

| | ใช้ | ทำอะไร |
|---|---|---|
| `io.StringIO()` | ✅ | ไฟล์ปลอมในหน่วยความจำสำหรับ text |
| `io.BytesIO()` | ❌ | ไฟล์ปลอมสำหรับ bytes — คู่กับ `s3.upload_fileobj()` |

```python
buf = io.BytesIO()
df.to_parquet(buf)
buf.seek(0)                                  # ต้อง seek กลับก่อนอ่าน
s3.upload_fileobj(buf, bucket, key)
```

## `os`

https://docs.python.org/3/library/os.html · https://docs.python.org/3/library/os.path.html

| | ใช้ | ทำอะไร |
|---|---|---|
| `os.environ.get(k, default)` | ✅ | อ่าน env var |
| `os.path.getsize(p)` | ✅ | ขนาดไฟล์ |
| `os.path.exists(p)` | ✅ | มีไฟล์ไหม |
| `os.remove(p)` | ✅ | ลบไฟล์ |
| `os.path.join` / `dirname` / `basename` / `abspath` | ✅ | จัดการ path |
| `os.makedirs(p, exist_ok=True)` | ❌ | สร้างโฟลเดอร์ |
| `os.listdir(p)` / `os.walk(p)` | ❌ | ไล่ไฟล์ |
| `os.statvfs("/tmp")` | ❌ | เช็คพื้นที่ `/tmp` ที่เหลือ |

**env var ที่ Lambda ใส่ให้เอง**

```
AWS_LAMBDA_FUNCTION_NAME     AWS_LAMBDA_FUNCTION_VERSION
AWS_LAMBDA_FUNCTION_MEMORY_SIZE   AWS_REGION
AWS_LAMBDA_LOG_GROUP_NAME    AWS_LAMBDA_LOG_STREAM_NAME
```

## `time` / `datetime`

https://docs.python.org/3/library/time.html · https://docs.python.org/3/library/datetime.html

| | ใช้ | ทำอะไร |
|---|---|---|
| `time.time()` | ✅ | epoch seconds — จับเวลาที่ใช้ |
| `time.perf_counter()` | ❌ | **แม่นกว่าสำหรับจับเวลา** ไม่กระโดดตามนาฬิการะบบ |
| `time.sleep(n)` | ❌ | หน่วง — ใน Lambda คือจ่ายเงินเปล่า |
| `datetime.now(tz)` | ✅ | เวลาปัจจุบันพร้อม timezone |
| `datetime.isoformat()` | ✅ | `2026-09-07T09:42:58+07:00` |
| `timezone(timedelta(hours=7))` | ✅ | เขต +07 |
| `datetime.fromisoformat(s)` | ❌ | แปลงกลับจาก string |
| `datetime.strptime(s, fmt)` | ❌ | แปลงจาก format อื่น |
| `datetime.astimezone(tz)` | ❌ | แปลง timezone |

**Lambda รันด้วย UTC เสมอ** — `datetime.now()` เปล่า ๆ จะได้ UTC ต้องใส่ `tz` ทุกครั้ง

**`zoneinfo` ใช้แทนได้** (Python 3.9+) แต่ใน Lambda ต้องแพ็ก `tzdata` ไปด้วย — ใช้ `timezone(timedelta(hours=7))` ง่ายกว่าเพราะไทยไม่มี DST

```python
from zoneinfo import ZoneInfo
datetime.now(ZoneInfo("Asia/Bangkok"))   # ต้องมี tzdata ใน package
```

## `urllib`

https://docs.python.org/3/library/urllib.request.html · https://docs.python.org/3/library/urllib.parse.html

| | ใช้ | ทำอะไร |
|---|---|---|
| `urllib.request.Request(url, headers=...)` | ✅ | ประกอบ request |
| `urllib.request.urlopen(req, timeout=n)` | ✅ | ยิง |
| `urllib.parse.quote(s)` | ✅ | escape สำหรับ path (`!` → `%21`) |
| `urllib.error.HTTPError` | ✅ | ดักเพื่ออ่าน error body |
| `urllib.parse.urlencode(dict)` | ❌ | dict → `a=1&b=2` สำหรับ query string หรือ POST body |
| `urllib.parse.quote_plus(s)` | ❌ | เหมือน `quote` แต่ช่องว่างเป็น `+` (สำหรับ query string) |
| `urllib.parse.urlparse(url)` | ❌ | แยก scheme/host/path |
| `urllib.error.URLError` | ❌ | ปัญหาเครือข่าย/DNS (คนละตัวกับ HTTPError) |

**`HTTPError` เป็น subclass ของ `URLError`** — ถ้าจะดักทั้งคู่ต้องเรียง `HTTPError` ก่อน

**ต้องใส่ `timeout=` เสมอ** ไม่ใส่จะรอไม่มีกำหนดจน Lambda หมดเวลา

**POST ทำได้** — ใส่ `data=` แล้วมันเปลี่ยนเป็น POST อัตโนมัติ

```python
body = urllib.parse.urlencode({"grant_type": "refresh_token"}).encode()
req = urllib.request.Request(url, data=body)   # มี data = POST
```

## `email.mime`

https://docs.python.org/3/library/email.mime.html

| | ใช้ | ทำอะไร |
|---|---|---|
| `MIMEMultipart(subtype)` | ✅ | ห่อหลายส่วน |
| `MIMEText(text, subtype, charset)` | ✅ | ข้อความ |
| `MIMEImage(data, _subtype)` | ✅ | รูป |
| `MIMEApplication(data)` | ❌ | **แนบไฟล์ทั่วไป** (xlsx, pdf, zip) |
| `msg.add_header(k, v, **params)` | ✅ | ใส่ header |
| `msg.as_bytes()` / `as_string()` | ✅ | ประกอบเป็นอีเมลจริง |

**subtype ของ multipart ต้องเลือกให้ถูก**

| subtype | ใช้เมื่อ |
|---|---|
| `alternative` | plain + html ของเนื้อหาเดียวกัน ให้ไคลเอนต์เลือก |
| `related` | html + รูปที่ html อ้างด้วย `cid:` |
| `mixed` | มีไฟล์แนบให้ดาวน์โหลด |

โครงที่ถูกเมื่อมีครบทั้งสาม

```
mixed
├── related
│   ├── alternative
│   │   ├── text/plain
│   │   └── text/html
│   └── image (cid:logo)
└── application (ไฟล์แนบ)
```

**แนบไฟล์**

```python
from email.mime.application import MIMEApplication
part = MIMEApplication(data)
part.add_header("Content-Disposition", "attachment", filename="report.xlsx")
```

---

# boto3

https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html

**Lambda มี boto3 ให้อยู่แล้ว ไม่ต้องแพ็กเข้า zip** — แต่เวอร์ชันตามที่ AWS อัปเดต ถ้าต้องการเวอร์ชันเจาะจงต้องแพ็กเอง

## S3

| | ใช้ | ทำอะไร |
|---|---|---|
| `upload_file(path, bucket, key, ExtraArgs=)` | ✅ | สตรีมจากดิสก์ · multipart อัตโนมัติ |
| `head_object(Bucket, Key)` | ✅ | ขอ metadata ยืนยันว่ามีไฟล์ |
| `put_object(Bucket, Key, Body=)` | ✅ | เขียนจากหน่วยความจำ (เหมาะกับไฟล์เล็ก) |
| `get_object(Bucket, Key)` | ❌ | อ่านไฟล์ — `["Body"].read()` |
| `upload_fileobj(fileobj, bucket, key)` | ❌ | อัปโหลดจาก `BytesIO` |
| `download_file(bucket, key, path)` | ❌ | ดาวน์โหลดลงดิสก์ |
| `list_objects_v2(Bucket, Prefix=)` | ❌ | ไล่ไฟล์ — **คืนทีละ 1,000 ต้องใช้ paginator** |
| `delete_object` / `delete_objects` | ❌ | ลบทีละไฟล์ / ทีละ 1,000 |
| `copy_object(CopySource=...)` | ❌ | คัดลอกฝั่ง S3 ไม่ผ่านเครื่องเรา |
| `generate_presigned_url(op, Params, ExpiresIn)` | ❌ | ลิงก์ชั่วคราว |

**`ExtraArgs` ที่ใช้บ่อย**

```python
ExtraArgs={
    "ContentType": "text/csv",
    "ServerSideEncryption": "aws:kms",
    "SSEKMSKeyId": "arn:aws:kms:...",
    "Metadata": {"run-id": run_id},
}
```

**paginator แทน `list_objects_v2` ตรง ๆ**

```python
for page in s3.get_paginator("list_objects_v2").paginate(Bucket=b, Prefix=p):
    for obj in page.get("Contents", []):
        ...
```

**presigned URL ที่สร้างจาก Lambda จะหมดอายุพร้อม credential ชั่วคราว** ไม่ใช่ตาม `ExpiresIn` ที่ตั้ง — ตั้งสั้น ๆ (12 ชม.) หรือใช้ CloudFront signed URL

## Secrets Manager

| | ใช้ | ทำอะไร |
|---|---|---|
| `get_secret_value(SecretId)` | ✅ | อ่าน — `["SecretString"]` หรือ `["SecretBinary"]` |
| `describe_secret(SecretId)` | ❌ | metadata (วันหมุนเวียนล่าสุด) |
| `put_secret_value` / `update_secret` | ❌ | เขียน |
| `list_secrets()` | ❌ | ไล่รายการ |

**`VersionStage`** — `AWSCURRENT` (default) · `AWSPREVIOUS` · `AWSPENDING` ใช้ตอน rotate

## SES

https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sesv2.html

**มี 2 API — v1 (`ses`) กับ v2 (`sesv2`) IAM action คนละตัว**

| API | ฟังก์ชัน | IAM action |
|---|---|---|
| v1 `ses` | `send_raw_email(Source, Destinations, RawMessage)` ✅ | `ses:SendRawEmail` |
| v1 `ses` | `send_email(...)` — ข้อความล้วน แนบไฟล์ไม่ได้ | `ses:SendEmail` |
| v2 `sesv2` | `send_email(Content={"Simple"\|"Raw"})` | `ses:SendEmail` |
| v2 `sesv2` | `create_email_identity` · `get_email_identity` · `get_account` | ตามชื่อ |

**ใส่ IAM ผิดตัวจะ AccessDenied** — `ses:SendEmail` ไม่ครอบ `ses:SendRawEmail`

## client ทั่วไป

| | ทำอะไร |
|---|---|
| `boto3.client("s3", region_name=..., config=...)` | สร้าง client แบบ low-level (ตรงกับ API) |
| `boto3.resource("s3")` | แบบ object-oriented — ไม่รองรับทุก service แล้ว |
| `botocore.config.Config` | ตั้ง retry / timeout / max connections |
| `botocore.exceptions.ClientError` | exception หลัก — `e.response["Error"]["Code"]` |

```python
from botocore.config import Config
cfg = Config(retries={"max_attempts": 5, "mode": "adaptive"},
             connect_timeout=5, read_timeout=60)
s3 = boto3.client("s3", config=cfg)
```

---

# google-auth

https://googleapis.dev/python/google-auth/latest/
https://google-auth.readthedocs.io/

| module | ใช้ | ทำอะไร |
|---|---|---|
| `google.oauth2.service_account.Credentials` | ✅ | credential จาก service account |
| `google.auth.transport.requests.Request` | ✅ | **ตัวส่ง HTTP** ที่ google-auth ใช้ไปแลก token (ไม่ใช่ HTTP request ไป Google) |
| `google.oauth2.credentials.Credentials` | ❌ | credential จาก OAuth user (refresh token) |
| `google.auth.default()` | ❌ | หา credential อัตโนมัติจาก env / metadata server |
| `google.auth.jwt` | ❌ | `encode()` / `decode()` JWT ตรง ๆ |
| `google.auth.crypt` | ❌ | signer/verifier ระดับล่าง |
| `google.auth.impersonated_credentials` | ❌ | สวมสิทธิ์ service account อื่น |
| `google.auth.transport.urllib3` | ❌ | transport ทางเลือกที่ไม่ต้องใช้ `requests` |

## `service_account.Credentials`

| classmethod | ใช้ | ทำอะไร |
|---|---|---|
| `from_service_account_info(dict, scopes=)` | ✅ | รับ dict (จาก Secrets Manager) |
| `from_service_account_file(path, scopes=)` | ❌ | รับ path ไฟล์ |

| method / property | ใช้ | ทำอะไร |
|---|---|---|
| `refresh(request)` | ✅ | สร้าง JWT → เซ็น → แลก access token |
| `.token` | ✅ | access token ที่ได้ |
| `.expiry` | ❌ | `datetime` ที่ token หมดอายุ |
| `.valid` | ❌ | ยังใช้ได้ไหม (มี token และยังไม่หมดอายุ) |
| `.expired` | ❌ | หมดอายุแล้วหรือยัง |
| `.service_account_email` | ❌ | client_email |
| `.with_scopes([...])` | ❌ | คืน credential ใหม่ที่ scope ต่างไป |
| `.with_subject(email)` | ❌ | **domain-wide delegation** — สวมสิทธิ์ผู้ใช้ใน Workspace |
| `.before_request(request, method, url, headers)` | ❌ | ใส่ Authorization header ให้อัตโนมัติ + refresh ถ้าหมดอายุ |

**`.valid` ใช้แทนการ refresh ทุกครั้งได้**

```python
if not creds.valid:
    creds.refresh(Request())
```

**scope ของ Google ที่เกี่ยวข้อง**

```
https://www.googleapis.com/auth/spreadsheets.readonly    อ่านชีต
https://www.googleapis.com/auth/spreadsheets             อ่าน+เขียน
https://www.googleapis.com/auth/drive.readonly           อ่านไฟล์ใน Drive (เปิดชีตด้วย "ชื่อ" ต้องใช้)
```

**Sheets API endpoint ที่ยังไม่ได้ใช้**

```
GET  /v4/spreadsheets/{id}                       metadata ทั้งไฟล์ (รายชื่อ tab ทั้งหมด)
GET  /v4/spreadsheets/{id}/values/{range}        ค่าใน range          ← ที่ใช้อยู่
GET  /v4/spreadsheets/{id}/values:batchGet       หลาย range ในครั้งเดียว
PUT  /v4/spreadsheets/{id}/values/{range}        เขียนทับ
POST /v4/spreadsheets/{id}/values/{range}:append เติมท้าย
```

**`batchGet` น่าจะเร็วกว่าที่ทำอยู่** — ตอนนี้ยิงทีละ tab (14 ครั้ง) ถ้าใช้ `ranges=` หลายค่าจะได้ในครั้งเดียวต่อชีต

```
/values:batchGet?ranges=Query!A:ZZ&ranges=2025!A:ZZ&ranges=2026!A:ZZ
```

---

# cryptography

https://cryptography.io/en/latest/

**ไม่ได้เรียกตรง ๆ ในโค้ด แต่ google-auth บังคับให้มี** — และเป็นตัวที่ทำให้ต้อง build package บน Linux เพราะมีโค้ด Rust/C คอมไพล์แล้ว

| module | ทำอะไร |
|---|---|
| `hazmat.primitives.asymmetric.rsa` · `padding` | RSA — สร้าง key, เซ็น, ตรวจ |
| `hazmat.primitives.hashes` | SHA256 ฯลฯ |
| `hazmat.primitives.serialization` | อ่าน/เขียน PEM, DER, PKCS8 |
| `hazmat.primitives.ciphers` | AES |
| `fernet.Fernet` | **เข้ารหัสแบบใช้ง่ายที่สุด** — symmetric ครบชุดในคลาสเดียว |
| `x509` | ใบรับรอง |
| `hazmat.primitives.kdf` | PBKDF2, scrypt — แฮชรหัสผ่าน |

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
token = Fernet(key).encrypt(b"secret")
```

**`hazmat` = hazardous materials** — ชื่อบอกว่าเป็น API ระดับล่างที่ใช้ผิดแล้วอันตราย ถ้าต้องเข้ารหัสข้อมูลให้ใช้ `Fernet` ก่อน

---

# requests

https://requests.readthedocs.io/

**ในโค้ดนี้ไม่ได้เรียกตรง ๆ** — `google.auth.transport.requests.Request` ใช้ข้างใน

| | ทำอะไร |
|---|---|
| `requests.get/post/put/delete(url, ...)` | ยิงแบบครั้งเดียว |
| `requests.Session()` | **ใช้ connection ซ้ำ เร็วกว่ามากถ้ายิงหลายครั้ง** |
| `r.json()` · `r.text` · `r.content` | อ่าน response |
| `r.raise_for_status()` | โยน exception ถ้า 4xx/5xx |
| `r.status_code` · `r.headers` | ข้อมูล response |

```python
s = requests.Session()
s.headers.update({"Authorization": f"Bearer {token}"})
r = s.get(url, timeout=30)
r.raise_for_status()
```

**พารามิเตอร์ที่ควรใส่เสมอ** — `timeout=` (ไม่ใส่ = รอไม่มีกำหนด) · `params=` แทนการต่อ query string เอง

## urllib3 · certifi · idna · charset_normalizer

ติดมากับ `requests` ทั้งชุด

| | ทำอะไร |
|---|---|
| `urllib3` | connection pool + retry ที่ requests ใช้ข้างใน · `urllib3.util.Retry` ตั้ง backoff ได้ |
| `certifi` | ชุด CA certificate — `certifi.where()` คืน path ไฟล์ `.pem` |
| `idna` | แปลงชื่อโดเมนที่ไม่ใช่ ASCII (`ไทย.com` → punycode) |
| `charset_normalizer` | เดา encoding ของ response ที่ไม่ระบุ charset |

## pyasn1 · pyasn1_modules · cffi · pycparser

| | ทำอะไร |
|---|---|
| `pyasn1` / `pyasn1_modules` | อ่านโครงสร้าง ASN.1/DER ที่ห่อ RSA key อยู่ |
| `cffi` | สะพานให้ Python เรียกโค้ด C — `cryptography` ใช้ |
| `pycparser` | parse C header ให้ `cffi` |

**ทั้ง 4 ตัวไม่มีเหตุให้เรียกตรง ๆ** แต่ต้องอยู่ใน package ไม่งั้น `cryptography` และ `google-auth` พัง

---

# ที่ยังไม่ได้ใช้แต่อาจได้ใช้

| library | ทำอะไร | ต้องแพ็กไหม |
|---|---|---|
| `gspread` | คุยกับ Google Sheets แบบ object — `gc.open_by_key(id).worksheet(t).get_all_values()` · โค้ดสั้นลงมาก | ต้อง |
| `openpyxl` | อ่าน/เขียน xlsx (สคริปต์ `k2_termination.py` ใช้อยู่) | ต้อง |
| `pandas` | `read_csv` / `to_parquet` — แต่หนักและกิน RAM สูง | ต้อง (ใหญ่มาก) |
| `pyarrow` | เขียน Parquet โดยไม่ต้องมี pandas | ต้อง |
| `pymssql` | ต่อ SQL Server โดยไม่ต้องมี ODBC driver — **มี manylinux wheel พร้อม FreeTDS ในตัว** | ต้อง |
| `pyodbc` | ต่อ SQL Server — **ต้องมี ODBC Driver 18 ระดับ OS ด้วย zip ธรรมดาไม่พอ** | ต้อง + container |

**`gspread` ไม่ได้ทำให้ zip เล็กลง** — มันลาก `google-auth` → `cryptography` มาเหมือนกัน ปัญหา packaging ยังเหมือนเดิม

---

## หลักที่ใช้ตัดสินใจ

| | |
|---|---|
| **stdlib ทำได้ อย่าเพิ่มของ** | `urllib` แทน `requests` ทำให้ zip เล็กลงและไม่มี dependency ให้ดูแล |
| **boto3 ไม่ต้องแพ็ก** | Lambda มีให้ · แพ็กเองเมื่อต้องการเวอร์ชันเจาะจงเท่านั้น |
| **ดูว่ามี native code ไหมก่อนเพิ่ม library** | ชื่อ wheel ลงท้าย `-any.whl` = ปลอดภัย · มีชื่อ OS = ต้อง build ให้ตรง |
| **ใส่ `timeout=` ทุกการเรียกเครือข่าย** | ไม่ใส่แล้ว Lambda จะตายเพราะหมดเวลาแทนที่จะได้ error ที่อ่านรู้เรื่อง |
