# ADLS Gen2 to S3 — Glue Pilot (staging)

ทดสอบ **วิธี 2 (Glue)** จาก [[ADLS Gen2 to S3 - Console Runbook]] กับ container `staging` ด้วยค่าจริงของ COM7
เป้าหมาย: พิสูจน์ว่า Glue ใน ap-southeast-7 **อ่าน ADLS ของ COM7 ได้** (สิทธิ์ · network · driver) และวัดความเร็ว/ค่าใช้จ่ายจริง — **ยังไม่ใช่การย้ายข้อมูลจริง**

เขียน 2026-10-12 · สิทธิ์ AWS ของ `sapon.s@comseven.com` ตรวจแล้วว่าทำได้ทุกขั้น (`iam:CreateRole` · `s3:CreateBucket` · `secretsmanager:CreateSecret` · `glue:*` · `iam:PassRole`) · Lake Formation = โหมด IAM (`IAM_ALLOWED_PRINCIPALS`) ไม่ต้อง grant

---

## ค่าที่ใช้

| | ค่า |
|---|---|
| Azure tenant | `com7erp.onmicrosoft.com` |
| Storage account | `stcom7dw001` (rg `rg-com7dw`) · key access = Enabled · Azure Function ใช้ร่วม |
| Container | `staging` → โฟลเดอร์ทดสอบ **`training`** · สำรอง `csvtest` |
| ห้ามแตะ | `staging/synapse` (ไฟล์ระบบ) · container `azure-webjobs-*` |
| AWS account / region | `603238661233` · ap-southeast-7 |
| bucket ปลายทาง (ใหม่) | `com7-raw-adls` |
| Glue database (ใหม่) | `bronze_adls` |
| IAM role (ใหม่) | `com7-glue-adls-reader-role` |
| Secret (ใหม่) | `com7/adls/glue-reader` |
| Entra app (ใหม่) | `aws-glue-adls-reader` |

ทุกอย่างเป็นของใหม่ — ลบทิ้งได้ทั้งชุดโดยไม่กระทบระบบเดิม (ส่วน G)

```
Azure (portal)                         AWS (console · ap-southeast-7)
──────────────                         ──────────────────────────────
A1 App registration ─ client secret ─► B2 Secrets Manager
A3 role "Storage Blob Data Reader"         │
   บน container staging                    ▼
                                       C  Glue notebook ─ ทดสอบ: network · list · อ่าน
                                       D  Glue job ──► s3://com7-raw-adls/ · bronze_adls.*
```

---

## A · ฝั่ง Azure (portal.azure.com)

### A1 · สร้าง App registration
1. ค้นหา **Microsoft Entra ID** → เมนูซ้าย **Manage → App registrations** → **+ New registration**
2. กรอก
   - Name: `aws-glue-adls-reader`
   - Supported account types: **Accounts in this organizational directory only (com7erp only - Single tenant)**
   - Redirect URI: เว้นว่าง
3. **Register**
4. หน้า **Overview** จด
   - **Application (client) ID** → ใช้เป็น `client_id`
   - **Directory (tenant) ID** → ใช้เป็น `tenant_id`

### A2 · สร้าง client secret
1. ใน app → **Manage → Certificates & secrets** → แท็บ **Client secrets** → **+ New client secret**
2. Description `glue-pilot` · Expires **90 days** → **Add**
3. คัดลอกช่อง **Value** ทันที (แสดงครั้งเดียว · ช่อง *Secret ID* ไม่ใช่) → วางตรงใน B2 เลย ไม่พักไว้ในแชต/อีเมล/โน้ต
4. ลงปฏิทินเตือนก่อนหมดอายุ

### A3 · ให้สิทธิ์อ่าน container `staging`
1. ค้นหา **Storage accounts** → `stcom7dw001` → **Data storage → Containers** → คลิก **`staging`**
2. เมนูซ้ายของ container → **Access Control (IAM)** → **+ Add → Add role assignment**
   - เป็นสีเทา / error → ข้ามไป A3-ขอ
3. แท็บ **Role** → ค้น `Storage Blob Data Reader` → เลือก → **Next**
   - ⛔ ห้ามเลือก Contributor / Owner / Storage Blob Data Contributor
4. แท็บ **Members** → Assign access to **User, group, or service principal** → **+ Select members** → ค้น `aws-glue-adls-reader` → **Select** → **Review + assign** → **Review + assign**

**A3-ขอ** (ถ้าทำเองไม่ได้) ส่งเจ้าของ Azure:
> ขอกำหนด role **Storage Blob Data Reader** ให้ app `aws-glue-adls-reader` (client ID `<A1>`) **เฉพาะ container `staging`** ใน `stcom7dw001` (rg-com7dw) — อ่านอย่างเดียว ใช้ทดสอบดึงข้อมูลไป AWS Glue

### A4 · ตรวจ
- `staging` → **Access Control (IAM)** → แท็บ **Role assignments** → เห็น `aws-glue-adls-reader` ใต้ **Storage Blob Data Reader** · Scope **This resource**
- รอ ~5–10 นาทีก่อนทดสอบ (สิทธิ์ใช้เวลากระจาย)

---

## B · ฝั่ง AWS (console · มุมขวาบนเลือก **Asia Pacific (Thailand)**)

### B1 · S3 bucket ปลายทาง
**S3 → Create bucket**

| ช่อง                    | ค่า                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------- |
| Bucket type             | General purpose                                                                    |
| Bucket name             | `com7-raw-adls` (ถ้าชื่อซ้ำ → `com7-raw-adls-603238661233` แล้วแก้ทุกที่ในโน้ตนี้) |
| Object Ownership        | ACLs disabled                                                                      |
| Block all public access | ✓                                                                                  |
| Bucket Versioning       | **Enable**                                                                         |
| Default encryption      | SSE-S3                                                                             |
| Tags                    | `project` = `adls-migration` · `stage` = `pilot`                                   |

**Create bucket**

### B2 · Secret
**Secrets Manager → Store a new secret**
1. Secret type **Other type of secret** → Key/value pairs เพิ่ม 5 แถว

| Key             | Value          |     |
| --------------- | -------------- | --- |
| `tenant_id`     | จาก A1         |     |
| `client_id`     | จาก A1         |     |
| `client_secret` | จาก A2 (Value) |     |
| `account`       | `stcom7dw001`  |     |
| `container`     | `staging`      |     |
|                 |                |     |

2. Encryption key `aws/secretsmanager` → **Next**
3. Secret name `com7/adls/glue-reader` · Description `ADLS stcom7dw001 read-only (pilot)` · Tags `project=adls-migration` → **Next**
4. Rotation **ปิด** → **Next** → **Store**
5. เปิด secret → จด **Secret ARN**

### B3 · IAM role ให้ Glue
**IAM → Roles → Create role**
1. Trusted entity **AWS service** · Service or use case **Glue** → **Next**
2. Permissions policies ค้น `AWSGlueServiceRole` → ✓ → **Next**
3. Role name `com7-glue-adls-reader-role` · Tags `project=adls-migration` → **Create role**
4. เปิด role → **Add permissions → Create inline policy** → แท็บ **JSON** → วาง → **Next** → Policy name `adls-pilot` → **Create policy**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid": "ReadSecret", "Effect": "Allow", "Action": "secretsmanager:GetSecretValue",
     "Resource": "arn:aws:secretsmanager:ap-southeast-7:603238661233:secret:com7/adls/glue-reader-*"},
    {"Sid": "NewBucketOnly", "Effect": "Allow",
     "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetBucketLocation"],
     "Resource": ["arn:aws:s3:::com7-raw-adls", "arn:aws:s3:::com7-raw-adls/*"]},
    {"Sid": "GlueAssets", "Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
     "Resource": ["arn:aws:s3:::aws-glue-assets-603238661233-ap-southeast-7",
                  "arn:aws:s3:::aws-glue-assets-603238661233-ap-southeast-7/*"]},
    {"Sid": "CatalogNewDbOnly", "Effect": "Allow",
     "Action": ["glue:GetDatabase", "glue:GetTable", "glue:GetTables", "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable"],
     "Resource": ["arn:aws:glue:ap-southeast-7:603238661233:catalog",
                  "arn:aws:glue:ap-southeast-7:603238661233:database/bronze_adls",
                  "arn:aws:glue:ap-southeast-7:603238661233:table/bronze_adls/*"]},
    {"Sid": "PassSelf", "Effect": "Allow", "Action": "iam:PassRole",
     "Resource": "arn:aws:iam::603238661233:role/com7-glue-adls-reader-role",
     "Condition": {"StringEquals": {"iam:PassedToService": "glue.amazonaws.com"}}}
  ]
}
```
- เขียนได้แค่ `com7-raw-adls` กับ `bronze_adls` → ต่อให้สคริปต์ผิดก็แตะ `com7_gold` / bucket เดิมไม่ได้
- `PassSelf` กัน error `iam:PassRole` ตอนเปิด notebook (เคยเจอกับ `com7-glue-etl-role`)

### B4 · Glue database
**Glue → Data Catalog → Databases → Add database**
- Name `bronze_adls` · Location `s3://com7-raw-adls/iceberg/` · Description `ADLS pilot` → **Create database**

### B5 · งบเตือน
**Billing and Cost Management → Budgets → Create budget** → Use a template **Monthly cost budget** → ชื่อ `adls-pilot` · $20 · อีเมลแจ้ง → **Create budget**
(tag `project` ต้องเปิดใน **Cost allocation tags** ก่อนถึงกรองตาม tag ได้ — ใช้ budget รวมไปก่อน)

---

## C · ทดสอบใน Glue notebook

**Glue → ETL jobs → Notebooks → Notebook**
- Engine **Spark (Python)** · Options **Start fresh**
- IAM role **`com7-glue-adls-reader-role`** → **Create notebook**

รันทีละ cell — **แต่ละ cell คือ checkpoint** ถ้าไม่ผ่านให้หยุดดูตาราง "ถ้าไม่ผ่าน"

### C1 · ตั้ง session (cell แรก ก่อนโค้ดอื่น)
```python
%glue_version 5.0
%worker_type G.1X
%number_of_workers 2
%idle_timeout 15
%%configure
{
  "--additional-python-modules": "azure-identity,azure-storage-file-datalake",
  "--datalake-formats": "iceberg",
  "--conf": "spark.sql.catalog.glue_catalog=org.apache.iceberg.spark.SparkCatalog --conf spark.sql.catalog.glue_catalog.catalog-impl=org.apache.iceberg.aws.glue.GlueCatalog --conf spark.sql.catalog.glue_catalog.warehouse=s3://com7-raw-adls/iceberg/ --conf spark.sql.catalog.glue_catalog.io-impl=org.apache.iceberg.aws.s3.S3FileIO --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
}
```
`%idle_timeout 15` = ปิด session เองถ้าไม่ใช้ 15 นาที (กันเสียเงิน)
- **ต้องรัน cell นี้ก่อนโค้ดอื่นทุกครั้ง** — magic ตั้งค่ามีผลเฉพาะตอนเริ่ม session · ถ้าเคยรันโค้ดไปแล้ว ให้ `%stop_session` ก่อนแล้วรันใหม่
- ใส่ package ไว้ใน `%%configure` ที่เดียว (ไม่ใช้ `%additional_python_modules` แยก) — ถ้าใส่สองที่ `%%configure` อาจทับค่า `[อนุมาน]` · อาการคือ `ModuleNotFoundError: No module named 'azure'` ที่ C4

ตรวจหลังเริ่ม session (หลัง C2)
```python
import importlib.util
print({m: importlib.util.find_spec(m) is not None for m in ["azure.identity", "azure.storage.filedatalake"]})
```

### C2 · อ่าน secret
```python
import json, boto3
sec = json.loads(boto3.client("secretsmanager", region_name="ap-southeast-7")
                 .get_secret_value(SecretId="com7/adls/glue-reader")["SecretString"])
print({k: (v if k in ("account", "container") else "***") for k, v in sec.items()})
```
✅ ผ่าน = เห็น 5 key (ค่าลับเป็น `***`)

### C3 · network ออกไป Azure ได้ไหม
```python
import requests
for url in ["https://login.microsoftonline.com/", f"https://{sec['account']}.dfs.core.windows.net/"]:
    try:
        r = requests.get(url, timeout=10)
        print("OK ", r.status_code, url)      # 4xx ก็ถือว่าต่อได้ (ยังไม่ได้ส่ง credential)
    except Exception as e:
        print("FAIL", url, type(e).__name__)
```
✅ ผ่าน = ทั้งสองบรรทัดขึ้น `OK` (status 200/400/401 ก็ได้)

### C4 · login และ list โฟลเดอร์ (อ่านอย่างเดียว)
```python
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from collections import Counter

cred = ClientSecretCredential(sec["tenant_id"], sec["client_id"], sec["client_secret"])
fs = DataLakeServiceClient(f"https://{sec['account']}.dfs.core.windows.net", credential=cred) \
        .get_file_system_client(sec["container"])

def survey(folder):
    n, size, ext = 0, 0, Counter()
    for p in fs.get_paths(path=folder, recursive=True):
        if p.is_directory:
            continue
        n += 1; size += p.content_length or 0
        ext[p.name.rsplit(".", 1)[-1].lower() if "." in p.name.split("/")[-1] else "(ไม่มีนามสกุล)"] += 1
    delta = any(True for p in fs.get_paths(path=folder, recursive=True) if p.name.endswith("/_delta_log"))
    print(f"{folder}: {n:,} ไฟล์ · {size/1024**2:,.1f} MB · {dict(ext)} · delta={delta}")

for f in ["training", "csvtest"]:
    survey(f)
```
✅ ผ่าน = เห็นจำนวนไฟล์ ขนาด และชนิดไฟล์ → **จดลงตาราง "ผลทดสอบ" ท้ายโน้ต**

### C5 · Spark อ่าน `abfss://` ได้ไหม (ทาง A)
```python
try:
    spark._jvm.java.lang.Class.forName("org.apache.hadoop.fs.azurebfs.SecureAzureBlobFileSystem")
    ABFS = True
except Exception:
    ABFS = False
print("ABFS driver:", ABFS, "· Hadoop", spark._jvm.org.apache.hadoop.util.VersionInfo.getVersion())
```
- `True` → ไป C6 ทาง A
- `False` → ข้ามไป C6 ทาง B (ไม่ต้องหา jar — ใช้ Python SDK ที่ผ่าน C4 แล้วแทน)

### C6 · อ่านข้อมูล 1 โฟลเดอร์

**ทาง A — Spark อ่าน Azure ตรง** (ถ้า ABFS = True)
```python
host = f"{sec['account']}.dfs.core.windows.net"
hc = spark.sparkContext._jsc.hadoopConfiguration()
hc.set(f"fs.azure.account.auth.type.{host}", "OAuth")
hc.set(f"fs.azure.account.oauth.provider.type.{host}", "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
hc.set(f"fs.azure.account.oauth2.client.id.{host}", sec["client_id"])
hc.set(f"fs.azure.account.oauth2.client.secret.{host}", sec["client_secret"])
hc.set(f"fs.azure.account.oauth2.client.endpoint.{host}", f"https://login.microsoftonline.com/{sec['tenant_id']}/oauth2/token")

src = f"abfss://{sec['container']}@{host}/training/<ไฟล์หรือโฟลเดอร์จาก C4>"
df = spark.read.option("header", "true").csv(src)      # ถ้า C4 เจอ parquet → spark.read.parquet(src)
df.printSchema(); print(df.count())
```

**ทาง B — คัดลอกไฟล์ขึ้น S3 ด้วย Python แล้วให้ Spark อ่านจาก S3** (ใช้ได้เสมอ · ได้ไฟล์ดิบแบบวิธี 1 ด้วย)
```python
import time
s3 = boto3.client("s3")
BUCKET, PREFIX, FOLDER = "com7-raw-adls", "staging", "training"
t0, n, size = time.time(), 0, 0
for p in fs.get_paths(path=FOLDER, recursive=True):
    if p.is_directory:
        continue
    key = f"{PREFIX}/{p.name}"
    stream = fs.get_file_client(p.name).download_file()
    s3.upload_fileobj(stream, BUCKET, key)              # ไฟล์ใหญ่แตก multipart อัตโนมัติ
    n += 1; size += p.content_length or 0
sec_used = time.time() - t0
print(f"คัดลอก {n} ไฟล์ · {size/1024**2:,.1f} MB · {sec_used:,.0f} วินาที · {size/1024**2/max(sec_used,1):,.1f} MB/s")

df = spark.read.option("header", "true").csv(f"s3://{BUCKET}/{PREFIX}/{FOLDER}/<ไฟล์หรือโฟลเดอร์>")
df.printSchema(); print(df.count())
```
✅ ผ่าน = เห็น schema และจำนวนแถว · **จดความเร็ว MB/s** (ใช้ประเมินเวลา/เงินของรอบจริง)

### C7 · เขียน Iceberg (ไม่ทับของเดิม)
```python
target = "glue_catalog.bronze_adls.pilot_training"
if spark.catalog.tableExists(target):
    raise SystemExit(f"{target} มีอยู่แล้ว — ไม่เขียนทับ")
df.writeTo(target).using("iceberg").create()
print("source", df.count(), "· target", spark.table(target).count())
```
✅ ผ่าน = จำนวนแถวเท่ากัน

### C8 · ปิด session
```python
%stop_session
```

**บทเรียน C4:** `survey()` แบบเดิมไล่ทุกไฟล์สองรอบ — โฟลเดอร์ใหญ่ทำให้ cell ต่อ ๆ ไปรอคิวนาน (cell ขึ้น `[*]`) · ใช้ `itertools.islice(..., 2000)` จำกัดจำนวน และไล่รอบเดียว · กด ■ Interrupt ได้ถ้าค้าง

### ถ้าไม่ผ่าน

| ขั้น | อาการ | สาเหตุ / แก้ |
|---|---|---|
| เปิด notebook | `iam:PassRole` AccessDenied | ขาด statement `PassSelf` ใน B3 |
| C1 | ติดตั้ง module ไม่ได้ / ค้าง | Glue ออกอินเทอร์เน็ตไม่ได้ (ไป PyPI ไม่ถึง) → ดู C3 |
| C4 | `ModuleNotFoundError: No module named 'azure'` | (1) session เริ่มก่อนรัน C1 → `%stop_session` แล้วรัน C1 เป็น cell แรก · (2) ใส่ package นอก `%%configure` · (3) ออกเน็ตไม่ได้ → ดู C3 |
| C2 | `AccessDeniedException` | ชื่อ secret ไม่ตรง หรือ ARN ใน policy ไม่ตรง region |
| C3 | `FAIL` ทั้งสองบรรทัด | session ออกเน็ตไม่ได้ → ต้องใช้ Glue connection ชนิด Network + NAT (มีค่า NAT ~$1.2/วัน) `[อนุมาน — ปกติ session ที่ไม่ผูก connection ออกเน็ตได้]` |
| C3 | login ได้ แต่ `dfs` FAIL | firewall ของ storage ปิด → ถามเจ้าของ (Networking) |
| C4 | `ClientAuthenticationError` / `AADSTS7000215` | client secret ผิด (ใช้ Secret ID แทน Value) |
| C4 | `AuthorizationPermissionMismatch` (403) | role A3 ยังไม่มีผล (รอ 10 นาที) หรือให้ผิด container/ผิด role |
| C4 | `ResourceNotFound` | ชื่อโฟลเดอร์ผิด (ตัวพิมพ์เล็ก-ใหญ่มีผล) |
| C6-A | `ClassNotFoundException azurebfs` | ไม่มี driver → ใช้ทาง B |
| C7 | `AccessDenied glue:CreateTable` | database ไม่ใช่ `bronze_adls` หรือ policy B3 ไม่ครบ |

---

## D · ทำเป็น Glue job (หลัง C ผ่าน)

ใช้ **ทาง B** เป็น job คัดลอกไฟล์ดิบ (ไม่ขึ้นกับ driver · ได้ Raw ไว้ตรวจย้อน) แล้วค่อยมี job อ่านจาก S3 ทำ Bronze แยก

**Glue → ETL jobs → Script editor** → Engine **Python shell** (ถูกกว่า Spark สำหรับงานคัดลอกไฟล์) → Start fresh → วาง

```python
import sys, json, time, boto3
from botocore.exceptions import ClientError
from awsglue.utils import getResolvedOptions
from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient

args = getResolvedOptions(sys.argv, ["SECRET_ID", "FOLDER", "BUCKET", "PREFIX"])
sec = json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=args["SECRET_ID"])["SecretString"])
fs = DataLakeServiceClient(f"https://{sec['account']}.dfs.core.windows.net",
                           credential=ClientSecretCredential(sec["tenant_id"], sec["client_id"], sec["client_secret"])) \
        .get_file_system_client(sec["container"])
s3 = boto3.client("s3")

t0, n, size, skipped = time.time(), 0, 0, 0
for p in fs.get_paths(path=args["FOLDER"], recursive=True):
    if p.is_directory:
        continue
    key = f"{args['PREFIX']}/{p.name}"
    try:                                     # ข้ามไฟล์ที่มีแล้วและขนาดเท่ากัน = รันซ้ำได้ ไม่คัดลอกซ้ำ
        if s3.head_object(Bucket=args["BUCKET"], Key=key)["ContentLength"] == p.content_length:
            skipped += 1
            continue
    except ClientError:                      # 404 = ยังไม่มีใน S3 → คัดลอก
        pass
    s3.upload_fileobj(fs.get_file_client(p.name).download_file(), args["BUCKET"], key)
    n += 1; size += p.content_length or 0

print(f"[RECONCILE] copied={n} skipped={skipped} MB={size/1024**2:,.1f} seconds={time.time()-t0:,.0f}")
```

แท็บ **Job details**

| ช่อง                  | ค่า                                                                          |
| --------------------- | ---------------------------------------------------------------------------- |
| Name                  | `adls-copy-staging-pilot`                                                    |
| IAM Role              | `com7-glue-adls-reader-role`                                                 |
| Python version        | Python 3.9                                                                   |
| Data processing units | **1/16 DPU** (ไฟล์เล็ก) · ไฟล์เยอะ/ใหญ่ใช้ 1 DPU                             |
| Job timeout           | 30 นาที                                                                      |
| Number of retries     | 0                                                                            |
| Connections           | ไม่เลือก                                                                     |
| Job parameters        | `--additional-python-modules` = `azure-identity,azure-storage-file-datalake` |
|                       | `--SECRET_ID` = `com7/adls/glue-reader`                                      |
|                       | `--FOLDER` = `training`                                                      |
|                       | `--BUCKET` = `com7-raw-adls`                                                 |
|                       | `--PREFIX` = `staging`                                                       |

**Save → Run** → แท็บ **Runs** → ดู status · **Output logs** หาบรรทัด `[RECONCILE]`

> ทำไม Python shell: งานนี้คือคัดลอกไฟล์ ไม่ต้องใช้ Spark · 1/16 DPU = $0.0275/ชม. เทียบกับ Spark 2 DPU = $0.88/ชม. `[อนุมาน — Python shell ใช้ราคาต่อ DPU-ชม. เท่ากับ ETL ($0.44) ยังไม่ได้ดึงราคา Python shell ของ ap-southeast-7 แยก]`

---

## E · ตรวจผล

1. **S3** → `com7-raw-adls/staging/training/` → เลือกทั้งหมด → **Actions → Calculate total size** → เทียบกับ C4
2. **Athena** (Query editor · catalog `AwsDataCatalog`) → `SELECT COUNT(*) FROM bronze_adls.pilot_training;` → เทียบกับ C7
3. รันข้อ D ซ้ำ → ต้องได้ `copied=0 skipped=<ทั้งหมด>` (พิสูจน์ว่ารันซ้ำไม่คัดลอกซ้ำ)

## F · ค่าใช้จ่ายของ pilot

| รายการ | ประมาณ |
|---|---:|
| Glue notebook 2 DPU × ~1 ชม. (Glue 5.0 $0.44/DPU-ชม.) | ~$0.90 |
| Glue job Python shell 1/16 DPU × ไม่กี่นาที | < $0.05 |
| Secrets Manager (คิดตามวันจากเดือนละ $0.40) | < $0.40 |
| S3 (โฟลเดอร์ทดสอบไม่กี่ GB × $0.0225) | < $0.10 |
| Azure egress (อยู่ใน 100 GB ฟรี/เดือน ถ้าไม่ถูกใช้หมด) | ~$0 |
| **รวม** | **~$1.5 (≈ 50 บาท)** |

ลืมปิด notebook = $0.88/ชม. จนถึง idle timeout → ตั้ง `%idle_timeout 15` ไว้แล้ว

## G · เก็บกวาด / ยกเลิก

| ลำดับ | ที่ | ทำ |
|---:|---|---|
| 1 | Glue | ลบ job `adls-copy-staging-pilot` · ตาราง `bronze_adls.pilot_training` · database `bronze_adls` |
| 2 | S3 | Empty → Delete bucket `com7-raw-adls` (ถ้าไม่ใช้ต่อ) |
| 3 | Secrets Manager | Delete `com7/adls/glue-reader` (รอ 7 วันก่อนลบจริง) |
| 4 | IAM | ลบ role `com7-glue-adls-reader-role` |
| 5 | Azure | `staging` → IAM → ลบ role assignment · Entra → App registrations → `aws-glue-adls-reader` → **Delete** |
| 6 | Budgets | ลบ `adls-pilot` |

ตัดสิทธิ์ด่วน (secret หลุด): Entra → app → **Certificates & secrets → ลบ secret** — มีผลทันที

---

## ผลทดสอบ (กรอกหลังทำ)

| รายการ | ค่า |
|---|---|
| วันที่ทดสอบ | 2026-10-14 |
| C3 network (login / dfs) | ✅ ผ่าน (C4 login + list ได้ = ออกเน็ตได้ ไม่ต้องใช้ NAT · ติดตั้ง package จาก PyPI ได้) |
| C4 `training`: ไฟล์ · MB · ชนิด · delta | 1 ไฟล์ · ~0 MB · csv · ไม่ใช่ Delta → เล็กเกินใช้วัดผล |
| C4 `csvtest`: ไฟล์ · MB · ชนิด · delta | 18 ไฟล์ · 46.8 MB · csv · ไม่ใช่ Delta → **ใช้เป็นโฟลเดอร์ทดสอบหลัก** |
| C5 ABFS driver (Glue 5.0) | |
| C6 ทางที่ใช้ · ความเร็ว MB/s | |
| C7 จำนวนแถว source / target | |
| D `[RECONCILE]` | |
| DPU-hours จริง (แท็บ Runs) | |

## เชื่อมกับโน้ตอื่น

[[ADLS Gen2 to S3]] · [[ADLS Gen2 to S3 - Console Runbook]] · [[Glue Jobs (ap-southeast-7)]] · [[Medallion Layer Definition]]
