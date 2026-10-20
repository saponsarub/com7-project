# ADLS Gen2 to S3

วิธีย้ายข้อมูลจาก **Azure Data Lake Storage Gen2** (ที่ Azure Synapse ของ COM7 ใช้) ลง **Amazon S3** — ทุกวิธีที่ทำได้ พร้อมขั้นตอน ข้อจำกัด และวิธีที่แนะนำ
งานนี้คือ Pilot ข้อ 1 ใน Timeline (*"MS Synapse จาก D365 to AWS directly"*) และ PoC issue ข้อ 8 → [[Current Status]]

เขียน 2026-10-08 · ข้อเท็จจริงของบริการตรวจกับเอกสาร AWS/Microsoft วันเดียวกัน (ลิงก์ท้ายโน้ต) · **ยังไม่ได้ทดสอบกับ storage จริงของ COM7** · ข้อสันนิษฐานติด `[อนุมาน]`

---

## 1. ฝั่ง Azure ของ COM7 มีอะไร

ที่มา: คู่มือ Alphametrics ใน `D:\Azure\` (User manual 31 หน้า + Training material ส.ค. 2024) → [[Other Systems]]

```
                     ┌──────────────── Azure Synapse workspace: synw-com7dw-dev ────────────────┐
D365 F&O ──Synapse Link (profile stcom7dw001)──► ADLS Gen2 ──► Serverless SQL (lake database dataverse_com7_…)
BC LS Retail (D7) ─┐                              (ไฟล์)          │
ITEC SQL Server ───┼─ Synapse pipeline ──► ADLS Gen2 ──────────► Dedicated SQL pool syndpdev001
SharePoint Excel ──┘  (control table)       (เช่น D7/D7_Item)     schema raws: FO_ · BC_ · ITEC_ · MT_
                     └───────────────────────────────────────────────────────────────────────────┘
```

| ส่วน | รายละเอียด | ผลต่อการย้าย |
|---|---|---|
| Workspace | `synw-com7dw-dev` · ชื่อมี `dev` แต่ใช้งานจริง | — |
| Serverless SQL | `synw-com7dw-dev-ondemand.sql.azuresynapse.net` · lake database `dataverse_com7_…` = ตาราง D365 F&O ที่ Synapse Link sync มา | อ่านไฟล์ใน ADLS ผ่าน SQL ได้ (วิธี F) |
| Dedicated SQL pool | `syndpdev001` บน `synw-com7dw-dev.sql.azuresynapse.net` · schema `raws` | **ตั้งเวลาเปิด จ.–ศ. 09:00–18:00 · ส.–อา. ปิด** → job ที่ดึงผ่าน pool ต้องรันในช่วงนี้ |
| Synapse Link | profile `stcom7dw001` sync ตาราง D365 F&O ลง ADLS | `stcom7dw001` น่าจะเป็นชื่อ storage account `[อนุมาน — ขึ้นต้น st ตามธรรมเนียมตั้งชื่อ Azure]` |
| Pipeline แบบ control table | `cfg._bcls_control_table` · `cfg._itec_control_table` · `cfg._master_control_table` · ดึงแบบ watermark (`timestamp` / row version) | รายการตารางที่ sync อยู่ในตาราง cfg — ใช้เป็น inventory ได้ |
| Prefix ใน `raws` | `FO_` D365 F&O · `BC_` Business Central LS Retail · `ITEC_` · `MT_` ไฟล์ master จาก SharePoint | — |
| BC LS Retail | ตัวอย่างตาราง `raws.BC_D7_Trans_Sales_Entry` · ต้นทาง `D7$Item` | **Double7 ใช้ Dynamics 365 Business Central (LS Retail)** → [[Customer Main MVP]] |
| SharePoint | `/sites/COM7_Team/Shared Documents/Data Lake Source file/…` | ไฟล์ Excel master |
| สิทธิ์ | Entra ID + SQL login แยกตาม BU (`sqluser_com7` `sqluser_dou7` …) + Row-Level Security ตาม Company | ⚠️ ดูหัวข้อ 9 |

### Container ใน `stcom7dw001` (เห็นจาก portal 2026-10-12)

storage account **`stcom7dw001`** · resource group `rg-com7dw` · tenant `com7erp.onmicrosoft.com`

| Container | สร้าง | น่าจะเป็น | ย้าย |
|---|---|---|---|
| `dataverse-com7-unq2d732cdec37844069e7424ea2c121` | 2024-08-09 | Synapse Link for Dataverse → **D365 F&O** (คู่กับ lake database `dataverse_com7_…`) | ✅ เป้าหลัก |
| `landing` | 2024-04-12 | ไฟล์ขาเข้าจาก Synapse pipeline (BC LS · ITEC · SharePoint) `[อนุมาน — จากชื่อ]` | ✅ ต้องเปิดดู |
| `staging` | 2024-04-12 | พักไฟล์ระหว่างโหลดเข้า dedicated pool `[อนุมาน]` | ❓ |
| `power-platform-dataflows` | 2024-04-22 | ที่เก็บ Power Platform / Power BI dataflows `[อนุมาน]` | ❓ ถามเจ้าของ |
| `$logs` | 2024-04-12 | log ของ Storage Analytics | ❌ |
| `azure-webjobs-hosts` · `azure-webjobs-secrets` | 2024-06-19 | **Azure Functions** ใช้ storage นี้ร่วม — `-secrets` เก็บ key ของ function | ❌ ห้ามแตะ |

⚠️ **มี Azure Function ใช้ storage นี้** → **ห้าม rotate account key** (function พัง) · เพิกถอน SAS ด้วยการลบ stored access policy เท่านั้น · **ห้ามใช้ account-level SAS** (จะเห็น `azure-webjobs-secrets`) → SAS ระดับ container ทีละตัว · DataSync 1 task ต่อ 1 container

**ใน `staging`** (บัญชี `mis_system` อ่านได้): `csvtest` (2024-06-14) · `synapse` (2024-05-07 — ไฟล์ระบบ workspace ห้ามใช้) · `temp` · `tmp` · `training` (2024-08-01 — ตรงกับช่วงอบรม Alphametrics) → **ใช้ `training` / `csvtest` เป็นโฟลเดอร์ทดสอบรอบแรก** ของ [[ADLS Gen2 to S3 - Console Runbook]] `[อนุมาน — จากชื่อ ยังไม่ได้เห็นไฟล์]`

**Allow storage account key access = Enabled** (2026-10-12) → วิธี A (DataSync) ใช้ได้ถ้าคนที่มี `listKeys` สร้าง SAS ให้ · น่าจะเปิดไว้เพราะ Azure Function ใช้ key `[อนุมาน]` → ห้ามปิด/ห้าม rotate · บัญชี `mis_system` สร้าง App registration เองได้ (Users can register applications = Yes) → วิธี B ไม่ต้องรอ IT สร้าง app

**สิทธิ์ (2026-10-12):** บัญชี `mis_system@com7erp.onmicrosoft.com` เห็นรายชื่อ container ได้ แต่ **list ข้อมูลไม่ได้** ทั้งแบบ access key (`listKeys` ไม่มี — ถูกต้องแล้ว) และแบบ Entra ID → 🔴 **รอขอ role Storage Blob Data Reader** บน `dataverse-com7-…` และ `landing` จากเจ้าของ Azure · ห้ามขอ role ที่ดึง key ได้

### ยังไม่รู้ — ต้องเปิดดู storage จริงก่อนเลือกวิธี
- [x] ชื่อ storage account และ container ทั้งหมด → ตารางข้างบน
- [ ] **Synapse Link เขียนแบบ CSV หรือ Delta** — ดูว่ามีโฟลเดอร์ `_delta_log` หรือไฟล์ `model.json` (วิธีอ่านต่างกันมาก → หัวข้อ 7)
- [ ] ไฟล์จาก pipeline BCLS/ITEC เป็น CSV หรือ Parquet
- [ ] ขนาดรวม · จำนวนไฟล์ · โตวันละเท่าไร
- [ ] storage account ปิด public network ไหม (มี firewall / private endpoint) → มีผลกับวิธี A
- [ ] Azure region ของ storage — ข้อมูลข้ามประเทศไหม (PDPA) → [[Consent & PDPA]]

---

## 2. เลือกวิธี

| #     | วิธี                                                                 | ทำงานที่ไหน                      | ได้อะไร                  | เหมาะกับ                                        | ความยาก |
| ----- | -------------------------------------------------------------------- | -------------------------------- | ------------------------ | ----------------------------------------------- | ------- |
| **A** | **AWS DataSync (Enhanced mode)** ⭐                                   | AWS · ไม่ต้องมี agent            | ไฟล์ตามต้นฉบับ           | **คัดลอกทั้ง container ครั้งแรก + sync รายวัน** | ต่ำ     |
| B     | AWS Glue (Spark) อ่าน `abfss://`                                     | AWS                              | แปลงระหว่างทาง → Iceberg | ต้องแปลง Delta/CSV เป็น Iceberg ในขั้นเดียว     | กลาง    |
| C     | Synapse / ADF **Mapping data flow** sink S3                          | Azure                            | ไฟล์ที่แปลงแล้ว          | ทีม Azure เดิมดูแลต่อ · ฝั่ง Azure เป็นคน push  | กลาง    |
| D     | rclone บน EC2 / VM                                                   | VM                               | ไฟล์ตามต้นฉบับ           | งานครั้งเดียว · ทดสอบ · ข้อมูลไม่ใหญ่           | ต่ำ     |
| E     | Python (`azure-storage-file-datalake` + `boto3`)                     | Lambda / ECS / Glue Python shell | ไฟล์ · คุม logic เอง     | incremental แบบกำหนดเอง · ไฟล์ไม่มาก            | กลาง    |
| F     | ดึงผ่าน **Synapse SQL** (JDBC จาก Glue หรือ Athena federated + CTAS) | AWS ↔ Synapse                    | **ตาราง** ไม่ใช่ไฟล์     | อยากได้ `raws.*` ที่ล้าง/รวมแล้ว · ตารางไม่ใหญ่ | กลาง    |
| G     | **ข้าม ADLS** ดึงจากระบบต้นทางตรง                                    | AWS                              | ตารางจากต้นทาง           | **ระยะยาว** เมื่อจะเลิกใช้ Synapse              | สูง     |

**ทำไม่ได้ / อย่าเลือก**
| วิธี | เหตุผล |
|---|---|
| ADF / Synapse **Copy activity** เขียนลง S3 | connector Amazon S3 เป็น **source เท่านั้น** (เอกสาร Microsoft: Copy activity `source/-`) — sink ได้แค่ใน Mapping data flow |
| AzCopy ไป S3 | AzCopy คัดลอก **จาก** S3 **เข้า** Azure ได้ แต่ไม่รองรับทิศ Azure → S3 `[อนุมาน — ตามเอกสาร AzCopy ที่รองรับ S3 เป็น source เท่านั้น ยังไม่ได้ทดสอบ]` |
| Athena อ่านไฟล์ ADLS ตรง | connector ADLS Gen2 ของ Athena **ไม่อ่านไฟล์เอง** — ส่ง query ไปให้ Azure Synapse ประมวลผล (= วิธี F) |

### คำแนะนำสำหรับ COM7

```
ระยะสั้น (Pilot)   A: DataSync ── ADLS ──► s3://com7-raw-adls/ (ไฟล์ตามต้นฉบับ)  ──Glue──► Bronze Iceberg
                                                    ▲ ถ้าเป็น Delta: Glue อ่าน Delta แล้วเขียน Iceberg (หัวข้อ 7)
ระยะกลาง           F: เฉพาะตาราง raws.* ที่ต้องการแบบ "ล้างแล้ว" และต้นทางไม่มีทางอื่น
ระยะยาว            G: ดึงจากต้นทางตรง (F&O · BC LS · ITEC · SharePoint) แล้วเลิก Synapse
```
- **A ก่อน** เพราะไม่ต้องติดตั้งอะไร ได้สำเนาครบที่ตรวจย้อนได้ (ตรงกับหลัก Raw = ไม่แตะเนื้อใน ใน [[Medallion Layer Definition]]) และรันซ้ำแบบ incremental ได้
- **G เป็นเป้าระยะยาว** — ถ้าคัดลอกจาก ADLS ตลอดไป ต้องจ่าย Synapse + Azure egress ซ้อนกับ AWS และขึ้นกับ pipeline ของ vendor เดิม `[อนุมาน]`
- ITEC ไม่ต้องผ่าน ADLS — มีเส้นทาง DMS → S3 ของตัวเองแล้ว → [[Glue Connectivity]]

---

## 3. วิธี A — AWS DataSync (Enhanced mode) ⭐

> ขั้นตอนแบบคลิกผ่าน console ทีละช่อง + ประมาณการค่าใช้จ่าย → [[ADLS Gen2 to S3 - Console Runbook]]

DataSync รองรับ Azure Blob Storage **รวมถึง ADLS Gen2** ทั้งเป็นต้นทางและปลายทาง · **Azure Blob → S3 ในโหมด Enhanced ไม่ต้องใช้ agent**

### ขั้นที่ 1 · ฝั่ง Azure: สร้าง SAS token แบบอ่านอย่างเดียว

| ต้องการ | ระดับ container | ระดับ account |
|---|---|---|
| สิทธิ์ | **Read + List** | services: Blob · resource types: Container + Object · Read + List |
| tag ของ blob | ไม่ต้อง (ADLS Gen2 hierarchical namespace **คัดลอก tag ไม่ได้อยู่แล้ว**) | — |

```bash
# ใช้ stored access policy → เพิกถอน SAS ได้โดยไม่ต้องเปลี่ยน account key
az storage container policy create --account-name <storage> --container-name <container> \
  --name datasync-ro --permissions rl --expiry 2027-01-31T00:00Z --auth-mode key

az storage container generate-sas --account-name <storage> --name <container> \
  --policy-name datasync-ro --https-only --output tsv
```
- **DataSync ไม่รับ user delegation SAS** → ต้องเป็น SAS ที่เซ็นด้วย account key (service/account SAS)
- **SAS จำกัดเฉพาะโฟลเดอร์ไม่ได้** — ให้ทั้ง container แล้วใช้ `--subdirectory` ฝั่ง DataSync แทน
- SAS หมดอายุกลางทาง = task ล้ม (`Failed to open directory`) → อัปเดต location ด้วย token ใหม่แล้วรันใหม่
- ไฟล์ใน **archive tier** ต้อง rehydrate ก่อน · cold tier ไม่รองรับ

### ขั้นที่ 2 · เก็บ SAS ใน Secrets Manager
```bash
aws secretsmanager create-secret --region ap-southeast-7 \
  --name com7/adls/<container>/sas --secret-string '<sas-token-หลังเครื่องหมาย-?>'
```
ห้ามใส่ SAS ในโค้ด / tfvars / โน้ต

### ขั้นที่ 3 · สร้าง location ต้นทาง (ADLS) และปลายทาง (S3)
```bash
aws datasync create-location-azure-blob --region ap-southeast-7 \
  --container-url "https://<storage>.blob.core.windows.net/<container>" \
  --authentication-type SAS \
  --sas-configuration '{"Token":"<sas-token>"}' \
  --subdirectory "/<folder>"                      # ไม่ใส่ = ทั้ง container
  # (ทางเลือก) ระบุ secret ใน Secrets Manager แทน Token ตรง — ดู "Providing credentials for storage locations"

aws datasync create-location-s3 --region ap-southeast-7 \
  --s3-bucket-arn arn:aws:s3:::com7-raw-adls \
  --subdirectory /<container> \
  --s3-config BucketAccessRoleArn=arn:aws:iam::<acct>:role/datasync-s3-write
```
URL ใช้ endpoint **`blob.core.windows.net`** (ไม่ใช่ `dfs.core.windows.net`)

### ขั้นที่ 4 · สร้าง task + ตั้งเวลา
```bash
aws datasync create-task --region ap-southeast-7 \
  --task-mode ENHANCED \
  --source-location-arn <azure-loc-arn> --destination-location-arn <s3-loc-arn> \
  --name adls-<container>-to-s3 \
  --options VerifyMode=ONLY_FILES_TRANSFERRED,TransferMode=CHANGED,PreserveDeletedFiles=PRESERVE,LogLevel=TRANSFER \
  --schedule ScheduleExpression="cron(0 15 * * ? *)" \
  --cloud-watch-log-group-arn <log-group-arn>
  # --includes FilterType=SIMPLE_PATTERN,Value="/D7/*|/FO/*"    (ถ้าเอาเฉพาะบางโฟลเดอร์)
```
| option | ค่าที่แนะนำ | เพราะ |
|---|---|---|
| `TransferMode` | `CHANGED` | รอบถัดไปคัดลอกเฉพาะไฟล์ใหม่/เปลี่ยน = incremental ในตัว |
| `PreserveDeletedFiles` | `PRESERVE` | ไฟล์ที่ถูกลบฝั่ง Azure ไม่ลบที่ S3 — Raw ต้องเก็บประวัติ |
| `VerifyMode` | `ONLY_FILES_TRANSFERRED` | ตรวจ checksum ไฟล์ที่ย้าย |
| schedule | `cron(0 15 * * ? *)` = 22:00 น. ไทย | ให้จบก่อน ETL 23:30 ([[Decisions]] D-16) |

### ขั้นที่ 5 · network
- ไม่มี agent = DataSync เรียก ADLS ผ่าน **public endpoint ของ Azure**
- ถ้า storage account เปิด firewall / ปิด public access → ต้องเปิดให้ IP ของ DataSync หรือเปลี่ยนไปใช้ **agent** วางใน VNet ของ Azure (Hyper-V image บน Azure VM — มีสคริปต์ช่วย deploy ที่ `aws-samples/aws-datasync-deploy-agent-azure`) `[อนุมาน — ช่วง IP ของ DataSync Enhanced ต้องตรวจในเอกสาร network requirements]`
- **ข้อมูลวิ่งผ่านอินเทอร์เน็ต (TLS)** — ถ้าต้องการ private ต้องมี VPN/Interconnect ระหว่าง Azure VNet กับ AWS VPC และใช้ agent

### ขั้นที่ 6 · ตรวจผล
```bash
aws datasync start-task-execution --task-arn <task-arn>
aws datasync describe-task-execution --task-execution-arn <exec-arn> \
  --query "{status:Status,files:FilesTransferred,bytes:BytesTransferred,verified:FilesVerified}"
```
บันทึกตัวเลขนี้เป็น reconciliation log ทุกครั้ง ([[Decisions]] D-15)

### ข้อจำกัดที่ต้องรู้
- ไฟล์ใหญ่เกิน 5 TB หรือ metadata เกิน 2 KB ไม่ถูกย้าย
- tag ของ blob ไม่ถูกคัดลอกเมื่อ storage เป็น hierarchical namespace (ADLS Gen2) — ถ้าตั้งให้คัดลอก task จะล้ม
- ค่าใช้จ่าย: ค่า DataSync ต่อ GB + **ค่า egress ของ Azure** + ค่า request ฝั่ง Azure และ S3 (ไม่มีค่า VM เพราะไม่มี agent)

---

## 4. วิธี B — AWS Glue อ่าน `abfss://` แล้วเขียน S3 / Iceberg

> ทดสอบกับ container `staging` ด้วยค่าจริง → [[ADLS Gen2 to S3 - Glue Pilot (staging)]] · ขั้นตอนแบบ console (Entra app · IAM · Glue Studio) → [[ADLS Gen2 to S3 - Console Runbook#3. วิธี 2 — AWS Glue อ่าน `abfss://` แล้วเขียน Iceberg ผ่าน console]]

เหมาะเมื่ออยากแปลงในขั้นเดียว เช่น Delta (Synapse Link) → Iceberg Bronze
`[อนุมาน — ยังไม่ได้ทดสอบบน Glue · ต้องตรวจว่า Glue 5.0 มี hadoop-azure ในตัวไหม ถ้าไม่มีต้องแนบ jar]`

**ฝั่ง Azure:** สร้าง service principal (Entra app) ให้ role **Storage Blob Data Reader** เฉพาะ container · เก็บ client id/secret/tenant ใน Secrets Manager

```python
# Glue job · --datalake-formats iceberg,delta
# --extra-jars s3://<artifacts>/jars/hadoop-azure-<ver>.jar,s3://<artifacts>/jars/azure-storage-<ver>.jar (ถ้า Glue ไม่มีให้)
import json, boto3
from pyspark.sql import SparkSession
sec = json.loads(boto3.client("secretsmanager").get_secret_value(SecretId="com7/adls/sp")["SecretString"])
acct = "<storage>"
spark = SparkSession.builder.getOrCreate()
conf = spark.sparkContext._jsc.hadoopConfiguration()
base = f"{acct}.dfs.core.windows.net"
conf.set(f"fs.azure.account.auth.type.{base}", "OAuth")
conf.set(f"fs.azure.account.oauth.provider.type.{base}", "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
conf.set(f"fs.azure.account.oauth2.client.id.{base}", sec["client_id"])
conf.set(f"fs.azure.account.oauth2.client.secret.{base}", sec["client_secret"])
conf.set(f"fs.azure.account.oauth2.client.endpoint.{base}", f"https://login.microsoftonline.com/{sec['tenant_id']}/oauth2/token")

src = f"abfss://<container>@{base}/<path>"
df = spark.read.format("delta").load(src)            # หรือ .parquet / .csv ตามที่เจอจริง
df.writeTo("glue_catalog.bronze_fo.salestable").using("iceberg").createOrReplace()
```
- Glue ต้องออกอินเทอร์เน็ตได้ (NAT) เพื่อเรียก `*.dfs.core.windows.net` และ `login.microsoftonline.com`
- ทางเลือกที่ปลอดภัยกว่าคือ **A ก่อน แล้ว B อ่านจาก S3** — Glue ไม่ต้องถือ credential ของ Azure

---

## 5. วิธี C — Synapse / ADF Mapping data flow เขียนลง S3

ฝั่ง Azure เป็นคน **push** ข้อมูลออก · ใช้ได้กับ Synapse ของ COM7 เพราะเป็นความสามารถเดียวกับ ADF

1. **ฝั่ง AWS:** สร้าง IAM user (หรือใช้ temporary credentials) ที่มีแค่ `s3:PutObject` / `s3:ListBucket` บน prefix ปลายทาง
2. **ฝั่ง Azure:** เก็บ access key ใน **Azure Key Vault** → สร้าง linked service ชนิด `AmazonS3` อ้าง Key Vault
3. สร้าง **Mapping data flow**: source = dataset บน ADLS · sink = dataset บน Amazon S3 (Parquet/Delta/CSV)
4. เรียก data flow จาก pipeline + trigger ตามเวลา

| ข้อดี | ข้อเสีย |
|---|---|
| ทีม/vendor Azure เดิมทำต่อได้ · แปลงระหว่างทางได้ | **Copy activity ใช้ไม่ได้** ต้องเป็น data flow (รันบน Spark ของ Azure → มีค่า cluster) · ต้องฝาก access key ของ AWS ไว้ฝั่ง Azure · ขึ้นกับ Synapse ซึ่งจะถูกเลิก |

---

## 6. วิธี D และ E — rclone / Python script

### D · rclone (งานครั้งเดียว / ทดสอบ)
```ini
# ~/.config/rclone/rclone.conf
[adls]
type = azureblob
account = <storage>
sas_url = https://<storage>.blob.core.windows.net/<container>?<sas>   ; หรือใช้ service principal: tenant / client_id / client_secret
[s3]
type = s3
provider = AWS
env_auth = true          ; ใช้ IAM role ของ EC2 ไม่ใส่ key
region = ap-southeast-7
```
```bash
rclone lsd adls:                                   # ดูโฟลเดอร์
rclone size adls:<container>                       # ขนาดรวม + จำนวนไฟล์ (ใช้กรอกข้อ "ยังไม่รู้")
rclone copy adls:<container>/<path> s3:com7-raw-adls/<container>/<path> \
  --checksum --transfers 16 --s3-chunk-size 64M --log-file adls.log --dry-run   # ตัด --dry-run เมื่อพร้อม
```
- `copy` ไม่ลบที่ปลายทาง · `sync` ลบไฟล์ที่ไม่มีต้นทาง → **Raw ใช้ `copy`**
- รันบน EC2 ใน ap-southeast-7 ที่มี IAM role เขียน S3 · ตั้ง cron ได้

### E · Python (incremental ตาม last_modified)
```python
import json, boto3
from azure.storage.filedatalake import DataLakeServiceClient   # pip install azure-storage-file-datalake
from azure.identity import ClientSecretCredential

sec = json.loads(boto3.client("secretsmanager").get_secret_value(SecretId="com7/adls/sp")["SecretString"])
cred = ClientSecretCredential(sec["tenant_id"], sec["client_id"], sec["client_secret"])
fs = DataLakeServiceClient(f"https://{sec['account']}.dfs.core.windows.net", credential=cred) \
        .get_file_system_client("<container>")
s3 = boto3.client("s3")
BUCKET, WM_KEY = "com7-raw-adls", "_control/adls_watermark.json"

try:
    since = json.loads(s3.get_object(Bucket=BUCKET, Key=WM_KEY)["Body"].read())["last_modified"]
except s3.exceptions.NoSuchKey:
    since = "1970-01-01T00:00:00+00:00"

newest, n = since, 0
for p in fs.get_paths(path="<folder>", recursive=True):
    if p.is_directory or p.last_modified.isoformat() <= since:
        continue
    stream = fs.get_file_client(p.name).download_file()
    s3.upload_fileobj(stream, BUCKET, f"<container>/{p.name}")      # stream → multipart อัตโนมัติ
    newest, n = max(newest, p.last_modified.isoformat()), n + 1
s3.put_object(Bucket=BUCKET, Key=WM_KEY, Body=json.dumps({"last_modified": newest, "files": n}))
```
- เลื่อน watermark **หลัง** คัดลอกสำเร็จทั้งหมดเท่านั้น (หลักเดียวกับ [[Reconcile Pipeline - Glue Jobs]])
- Lambda จำกัด 15 นาที — ไฟล์เยอะใช้ ECS/Fargate หรือ Glue Python shell

---

## 7. รูปแบบไฟล์ — สิ่งที่ต้องจัดการหลังย้าย

### D365 F&O ผ่าน Synapse Link
Synapse Link for Dataverse เขียนได้ 2 แบบ — **ต้องเปิดดู container ว่าเป็นแบบไหน** `[อนุมาน — ชื่อ lake database "dataverse_com7_…" เป็นรูปแบบของ Synapse Link แต่ไม่รู้ว่าเลือก Delta หรือ CSV]`

| แบบ | หน้าตาใน ADLS | อ่านยังไงหลังย้ายถึง S3 |
|---|---|---|
| **Delta** | โฟลเดอร์ต่อตาราง + `_delta_log/` | Glue `--datalake-formats delta` อ่าน `spark.read.format("delta")` แล้วเขียน Iceberg · หรือ Athena อ่าน Delta ตรง |
| **CSV (CDM)** | `model.json` + โฟลเดอร์ต่อตาราง แบ่ง partition ตามเวลา · **CSV ไม่มี header** | อ่าน schema จาก `model.json` · แถวเป็นแบบ append มี `IsDelete` / `versionnumber` → ต้อง dedupe เอาเวอร์ชันล่าสุดต่อ `Id` และตัดแถวที่ `IsDelete = true` |

⚠️ กับดักเดิมของ D365 ยังอยู่ครบหลังย้าย → [[D365 F&O Overview]] (21 บริษัท · `'NULL'` เป็นข้อความ · ตัวพิมพ์ใหญ่/เล็กของ BU)

### BC LS Retail / ITEC (pipeline control table)
- ดึงแบบ watermark ตาม `timestamp` / row version → ไฟล์ใน ADLS อาจเป็น **ส่วนต่างรายรอบ** ไม่ใช่ snapshot เต็ม `[อนุมาน]`
- ถ้าใช่: ต้องรวมไฟล์ทุกรอบแล้ว dedupe ด้วยคีย์ใน `Control_Table_Table_Key` (เช่น `[No_]`) เอาแถวที่ `versionnumber` สูงสุด
- คีย์และ watermark ของแต่ละตารางอ่านได้จาก `cfg._bcls_control_table` / `cfg._itec_control_table` ใน `syndpdev001`

### ไฟล์ master จาก SharePoint (`MT_*`)
- ต้นทางจริงอยู่ SharePoint · ADLS เป็นแค่ทางผ่าน
- ระยะยาวดึงจาก SharePoint ตรง (Microsoft Graph API) — วิธีเดียวกับ [[Google Sheet to S3 (Lambda)]] `[อนุมาน]`

---

## 8. วิธี F — ดึงเป็นตารางผ่าน Synapse SQL

ใช้เมื่ออยากได้ `raws.*` ที่ Synapse รวม/ล้างไว้แล้ว แทนไฟล์ดิบ

**F1 · Glue JDBC → S3** (เหมือนดึง SQL Server ทั่วไป)
```python
df = (spark.read.format("jdbc")
      .option("url", "jdbc:sqlserver://synw-com7dw-dev.sql.azuresynapse.net:1433;databaseName=<db>;encrypt=true")
      .option("dbtable", "raws.BC_D7_Trans_Sales_Entry")
      .option("user", sec["user"]).option("password", sec["password"])     # จาก Secrets Manager
      .option("fetchsize", 20000).load())
df.writeTo("glue_catalog.bronze_bcls.d7_trans_sales_entry").using("iceberg").createOrReplace()
```
- serverless (`…-ondemand…`) อ่านไฟล์ใน ADLS ให้ · dedicated (`syndpdev001`) **ต้องอยู่ในช่วงเวลาที่ pool เปิด** (จ.–ศ. 09–18) ไม่งั้นต้อง resume (มีค่าใช้จ่าย)
- **ใช้ login ที่เห็นทุกบริษัท** — login ราย BU ติด Row-Level Security จะได้ข้อมูลไม่ครบโดยไม่มี error

**F2 · Athena connector "ADLS Gen2" + CTAS**
- connector ส่ง query ผ่าน JDBC ไปให้ **Azure Synapse** ประมวลผล (ไม่ได้อ่านไฟล์เอง) · ข้อมูลเกิน Lambda limit จะ spill ลง S3
- ตั้งค่าด้วย Glue connection ชนิด `DATALAKEGEN2` · credential ใน Secrets Manager · รองรับ AAD service principal (`authentication=ActiveDirectoryServicePrincipal`)
- คัดลอกลง S3 ด้วย CTAS จาก catalog federated `[อนุมาน — ยังไม่ได้ทดสอบ CTAS กับ connector นี้]`
- ข้อจำกัด: ช้าเมื่อมีหลาย query พร้อมกัน · โดน throttle · ต้อง cast วันที่ใน filter เอง → **เหมาะกับสำรวจ/ตารางเล็ก ไม่เหมาะกับ batch ใหญ่**

---

## 9. ความปลอดภัย

- **SAS อ่านอย่างเดียว (`rl`) · ระดับ container · มีวันหมดอายุ · ผูก stored access policy** เพื่อเพิกถอนได้ทันที
- service principal ให้แค่ **Storage Blob Data Reader** · ไม่ใช้ account key ในโค้ด
- credential ฝั่ง AWS อยู่ใน **Secrets Manager** · ฝั่ง Azure อยู่ใน **Key Vault** · ไม่ใส่ในไฟล์ / notebook / โน้ต
- S3 ปลายทาง: SSE · block public access · versioning (Raw) ตาม [[Medallion Layer Definition]]
- **PDPA:** ตรวจ Azure region ของ storage · การย้ายเข้า ap-southeast-7 ถ้าต้นทางอยู่นอกไทย ถือว่าข้อมูลกลับเข้าไทย แต่ควรให้ DPO รับทราบ `[อนุมาน]`
- ⚠️ **เอกสาร training ของ Alphametrics (`D:\Azure\COM7-02 Training material - Azure Synapse.pdf`) มีรหัสผ่าน SQL login ของทุก BU เขียนเป็นข้อความธรรมดา** → แจ้งเจ้าของ Synapse ให้เปลี่ยนรหัสทั้งหมด · จำกัดคนเข้าถึงไฟล์ · ห้ามคัดลอกรหัสลงที่ใด → [[Source System Issues]]

---

## 10. Checklist เริ่มงาน

- [ ] ขอสิทธิ์อ่าน storage account (Azure portal / Storage Explorer) จากเจ้าของ Synapse
- [ ] กรอกข้อ "ยังไม่รู้" ในหัวข้อ 1 — `rclone size` หรือ Storage Explorer
- [ ] ตัดสินใจรูปแบบ Synapse Link (Delta / CSV)
- [ ] สร้าง bucket `com7-raw-adls` (หรือ prefix ใต้ `com7-raw-files`) ตามโครงใน [[Medallion Layer Definition]]
- [ ] ทำ SAS + Secrets Manager + DataSync task (วิธี A) กับ container เล็กที่สุดก่อน
- [ ] เทียบจำนวนไฟล์/ขนาด ADLS ↔ S3 · บันทึก reconciliation log
- [ ] Glue job Bronze: Delta/CSV → Iceberg
- [ ] เริ่มวางแผนวิธี G (ต้นทางตรง) ต่อระบบ เพื่อเลิก Synapse
- [ ] แจ้งเรื่องรหัสผ่านในเอกสาร training

---

## แหล่งอ้างอิง

- AWS DataSync — [Configuring transfers with Microsoft Azure Blob Storage](https://docs.aws.amazon.com/datasync/latest/userguide/creating-azure-blob-location.html) (รองรับ ADLS Gen2 · Enhanced mode ไม่ต้องมี agent · SAS · ข้อจำกัด)
- Microsoft — [Copy and transform data in Amazon S3 (ADF & Synapse)](https://learn.microsoft.com/en-us/azure/data-factory/connector-amazon-simple-storage-service) (Copy activity เป็น source เท่านั้น · Mapping data flow เป็น sink ได้)
- AWS Athena — [Azure Data Lake Storage (ADLS) Gen2 connector](https://docs.aws.amazon.com/athena/latest/ug/connectors-adls-gen2.html) (ส่ง query ผ่าน Synapse · ไม่อ่านไฟล์ตรง)
- คู่มือ Alphametrics — `D:\Azure\` → [[Other Systems]]

## เชื่อมกับโน้ตอื่น

[[ADLS Gen2 to S3 - Console Runbook]] · [[ADLS Gen2 to S3 - Glue Pilot (staging)]] · [[Other Systems]] · [[D365 F&O Overview]] · [[Medallion Layer Definition]] · [[Glue Connectivity]] · [[Current Status]] · [[Source System Issues]] · [[Customer Main MVP]]
