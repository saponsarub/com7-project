# ADLS Gen2 to S3 — Console Runbook (วิธี 1 DataSync · วิธี 2 Glue)

ขั้นตอนละเอียดแบบ **คลิกผ่าน console** ของ 2 วิธีหลักจาก [[ADLS Gen2 to S3]]
- **วิธี 1** = วิธี A · AWS DataSync (Enhanced mode) — คัดลอกไฟล์ตามต้นฉบับ
- **วิธี 2** = วิธี B · AWS Glue อ่าน `abfss://` แล้วเขียน Iceberg

เขียน 2026-10-12 · ราคาดึงจาก **AWS Price List API (ap-southeast-7)** และหน้า pricing ของ Azure วันเดียวกัน · ชื่อปุ่ม/ช่องตามเอกสาร AWS/Microsoft ปัจจุบัน — console อาจเปลี่ยนชื่อเล็กน้อย
**ยังไม่ได้ทดสอบกับ storage จริงของ COM7** · ข้อที่ไม่ได้ยืนยันติด `[อนุมาน]`

---

## 0. หลัก "ห้ามกระทบข้อมูลเดิม"

ทั้งสองวิธี **อ่านอย่างเดียว** ที่ Azure และ **เขียนเฉพาะที่ใหม่** ที่ AWS

| จุด | กติกา | ทำไม |
|---|---|---|
| สิทธิ์ฝั่ง Azure | SAS แค่ **Read + List** (วิธี 1) · role **Storage Blob Data Reader** (วิธี 2) · ไม่มี Write/Delete | ต่อให้ตั้งค่าผิด ก็เขียน/ลบ ADLS ไม่ได้ |
| ขอบเขตสิทธิ์ | ระดับ **container** ที่ต้องใช้เท่านั้น ไม่ใช่ทั้ง storage account | จำกัดความเสียหายถ้า credential หลุด |
| เพิกถอนได้ทันที | SAS ผูก **stored access policy** · client secret มีวันหมดอายุ | หยุดทุกอย่างได้ในคลิกเดียวโดยไม่ต้องหมุน account key (ซึ่งกระทบระบบอื่น) |
| Synapse / pipeline เดิม | **ไม่แตะ** — ไม่แก้ pipeline · ไม่ pause/resume SQL pool · ไม่เปลี่ยน tier ไฟล์ | Synapse ยังเป็นระบบที่ใช้งานอยู่ |
| network ฝั่ง Azure | **ไม่เปลี่ยน firewall เอง** — ถ้า storage ปิด public ให้เจ้าของเป็นคนตัดสินใจ | การเปิด firewall คือการเปลี่ยนความปลอดภัยของระบบเดิม |
| ปลายทาง AWS | **bucket ใหม่** `com7-raw-adls` · Glue database ใหม่ `bronze_adls` · ไม่เขียนทับ bucket/ตารางที่มีอยู่ | ไม่ไปทับงาน PoC เดิม (เช่น `com7_gold`) |
| ลบไฟล์ | DataSync เปิด **Keep deleted files** · S3 เปิด **Versioning** | ไฟล์ที่หายจากต้นทางไม่ถูกลบที่ปลายทาง · เขียนทับแล้วยังย้อนได้ |
| ทดสอบก่อน | รัน **โฟลเดอร์เล็ก 1 โฟลเดอร์** ก่อนทั้ง container | เห็นค่าใช้จ่าย/เวลาจริงก่อนจ่ายก้อนใหญ่ |
| เวลารัน | หลัง 22:00 หรือวันหยุด | ไม่แย่ง bandwidth/IO กับงานกลางวันของ Synapse `[อนุมาน — ผลกระทบจริงขึ้นกับขนาด]` |
| ค่าใช้จ่ายฝั่ง Azure | **egress คิดเงินที่ subscription Azure ของ COM7** ไม่ใช่ AWS | ต้องให้เจ้าของ Azure อนุมัติงบก่อน (หัวข้อ 4) |

---

## 1. เตรียมก่อนเริ่ม (ทั้งสองวิธี)

### 1.1 ขอจากเจ้าของ Azure (Alphametrics / ทีม Synapse)

| ขอ                                                                       | ใช้กับ              | หมายเหตุ                                                |
| ------------------------------------------------------------------------ | ------------------- | ------------------------------------------------------- |
| สิทธิ์ **Reader** บน storage account (ดูอย่างเดียว)                      | สำรวจขนาด · network | ไม่ต้องมีสิทธิ์อ่านข้อมูลในขั้นนี้                      |
| ชื่อ storage account · container · โฟลเดอร์ที่ต้องการ                    | ทุกขั้น             | น่าจะเป็น `stcom7dw001` `[อนุมาน]`                      |
| **ให้เจ้าของสร้าง SAS ให้** (วิธี 1) หรือ **service principal** (วิธี 2) | สิทธิ์อ่านข้อมูล    | ถ้าเราไม่มีสิทธิ์ทำเอง                                  |
| อนุมัติ **ค่า egress** (หัวข้อ 4)                                        | งบ                  | ฟรี 100 GB/เดือน ต่อทั้ง subscription — อาจถูกใช้ไปแล้ว |

### 1.2 สำรวจ storage ใน Azure portal (ไม่แตะข้อมูล)

1. https://portal.azure.com → ค้นหา **Storage accounts** → เลือก account
2. **Overview** → ดู
   - **Location** (region — ใช้ประเมิน egress และ PDPA)
   - **Hierarchical namespace: Enabled** = ADLS Gen2
3. เมนูซ้าย **Settings → Configuration** → ดู **Allow storage account key access**
   - **Enabled** → สร้าง SAS สำหรับ DataSync ได้
   - **Disabled** → ⛔ **วิธี 1 ใช้ไม่ได้** (DataSync ไม่รับ user delegation SAS) → ต้องขอเจ้าของเปิด หรือไปวิธี 2
4. **Security + networking → Networking** → ดู **Public network access**
   - **Enabled from all networks** → ใช้ได้ทั้งสองวิธี
   - **Enabled from selected virtual networks and IP addresses** หรือ **Disabled** → ⛔ หยุด คุยกับเจ้าของก่อน (ต้องเพิ่ม IP หรือใช้ agent/private link) **อย่าแก้เอง**
5. **Data storage → Containers** → เปิด container → ดูโครงโฟลเดอร์
   - Synapse Link: มี `_delta_log/` = Delta · มี `model.json` = CSV (CDM) → [[ADLS Gen2 to S3#7. รูปแบบไฟล์ — สิ่งที่ต้องจัดการหลังย้าย]]
6. ขนาดข้อมูล
   - ทั้ง account: **Monitoring → Metrics** → Metric namespace **Blob** → Metric **Blob Capacity** · **Blob Count**
   - รายโฟลเดอร์: Azure Storage Explorer → คลิกขวาโฟลเดอร์ → **Folder Statistics**
7. **Data management → Lifecycle management / Data protection** → ดูว่ามีไฟล์ใน **Archive / Cold tier** ไหม (DataSync คัดลอกไม่ได้ ต้อง rehydrate = เปลี่ยนข้อมูลเดิม → **ข้ามไฟล์กลุ่มนี้** อย่า rehydrate เอง)

จดผลลงตารางนี้ก่อนไปต่อ

| รายการ | ค่า |
|---|---|
| Storage account / Region | |
| Container / โฟลเดอร์ | |
| ขนาดรวม (GB) · จำนวนไฟล์ | |
| Allow storage account key access | |
| Public network access | |
| รูปแบบ (Delta / CSV / Parquet) | |

### 1.3 ฝั่ง AWS — สร้าง bucket ปลายทางใหม่

AWS console → region **Asia Pacific (Thailand) ap-southeast-7** → **S3 → Create bucket**

| ช่อง | ค่า |
|---|---|
| Bucket type | General purpose |
| Bucket name | `com7-raw-adls` (ต้องไม่ซ้ำทั้งโลก — ถ้าซ้ำเติม `-603238661233`) |
| Object Ownership | ACLs disabled |
| Block Public Access | **Block all public access ✓** |
| Bucket Versioning | **Enable** |
| Default encryption | SSE-S3 (หรือ SSE-KMS ถ้าทีมใช้ KMS — มีค่า KMS request เพิ่ม) |
| Tags | `project=adls-migration` · `owner=data-team` (ใช้แยกค่าใช้จ่ายใน Cost Explorer) |

→ **Create bucket**

ใช้ bucket ใหม่เพื่อให้ **ลบทิ้งได้ทั้งก้อนถ้ายกเลิก** โดยไม่กระทบอะไร

---

## 2. วิธี 1 — AWS DataSync (Enhanced mode) ผ่าน console

```
Azure portal                      AWS console (ap-southeast-7)
────────────                      ─────────────────────────────
Container ─ Access policy (rl) ─► DataSync: Location (Azure Blob)  ┐
          └ SAS token ──────────►            Location (S3)          ├► Task (Enhanced) ─► s3://com7-raw-adls/<container>/
                                             CloudWatch logs        ┘
```

### 2.1 Azure portal — สร้าง stored access policy (เพิกถอนได้)

1. Storage account → **Data storage → Containers** → คลิก container
2. เมนูซ้ายของ container → **Settings → Access policy**
3. ส่วน **Stored access policies** → **+ Add policy**

| ช่อง | ค่า |
|---|---|
| Identifier | `datasync-ro` |
| Permissions | **Read** · **List** (ไม่เลือกอย่างอื่น) |
| Start time | วันนี้ |
| Expiry time | ช่วงที่ต้องใช้ เช่น 3 เดือน |

4. **OK** → **Save** (ปุ่มด้านบน — ถ้าไม่กด Save นโยบายไม่ถูกบันทึก)

> ถ้า portal ไม่ให้สร้าง stored access policy บน account ที่เป็น hierarchical namespace ให้ข้ามไปสร้าง SAS แบบกำหนดสิทธิ์/วันหมดอายุตรง ๆ ในขั้น 2.2 และจดไว้ว่าเพิกถอนได้ด้วยการ rotate key เท่านั้น — **ต้องคุยกับเจ้าของก่อน** เพราะ rotate key กระทบทุกระบบที่ใช้ key `[อนุมาน — ยังไม่ได้ตรวจกับ account จริง]`

### 2.2 Azure portal — สร้าง SAS token

1. ใน container เดิม → **Settings → Shared access tokens**

| ช่อง | ค่า |
|---|---|
| Signing method | **Account key** (DataSync ไม่รับ User delegation key) |
| Signing key | Key 1 |
| Stored access policy | `datasync-ro` (สิทธิ์และวันหมดอายุจะล็อกตาม policy) |
| Allowed IP addresses | เว้นว่าง (ไม่รู้ IP ของ DataSync Enhanced) |
| Allowed protocols | **HTTPS only** |

2. **Generate SAS token and URL**
3. คัดลอก **Blob SAS token** (ส่วนหลัง `?` ขึ้นต้น `sp=rl&...` หรือ `si=datasync-ro&...`) — **แสดงครั้งเดียว** เก็บในที่ปลอดภัยชั่วคราว ไม่วางในแชต/อีเมล/โน้ต
4. คัดลอก **Blob SAS URL** ส่วนก่อน `?` = Container URL เช่น `https://<storage>.blob.core.windows.net/<container>` (ใช้ `blob.` ไม่ใช่ `dfs.`)

### 2.3 AWS console — สร้าง location ต้นทาง (Azure Blob)

**DataSync → Data transfer → Locations → Create location**

| ช่อง | ค่า |
|---|---|
| Location type | **Microsoft Azure Blob Storage** |
| Container URL | `https://<storage>.blob.core.windows.net/<container>` |
| Access tier when used as a destination | ไม่ต้องเลือก (เราใช้เป็นต้นทาง) |
| Folder | `/<โฟลเดอร์>` เพื่อจำกัดขอบเขต · เว้นว่าง = ทั้ง container |
| Agents | **ไม่ใช้ agent** (Enhanced mode Azure Blob → S3 ไม่ต้องมี) |
| SAS token | วาง token จาก 2.2 — หรือเลือก secret ใน Secrets Manager ที่เก็บ token ไว้ |
| Tags | `Name=adls-<container>-src` |

→ **Create location**

### 2.4 AWS console — สร้าง location ปลายทาง (S3)

**Locations → Create location**

| ช่อง | ค่า |
|---|---|
| Location type | **Amazon S3** |
| S3 URI | `s3://com7-raw-adls/<container>/` |
| S3 storage class | **Standard** (ไฟล์ Raw ที่ Glue จะอ่านต่อ) |
| IAM role | **Autogenerate** → DataSync สร้าง role ที่เขียนได้เฉพาะ bucket นี้ |

→ **Create location**

> ถ้าบัญชีของเราสร้าง IAM role ไม่ได้ (ปุ่ม Autogenerate error) ให้ admin สร้าง role ที่ trust `datasync.amazonaws.com` และมีสิทธิ์ `s3:GetBucketLocation` `s3:ListBucket` `s3:ListBucketMultipartUploads` บน bucket กับ `s3:*Object*` `s3:AbortMultipartUpload` `s3:ListMultipartUploadParts` บน `com7-raw-adls/*` เท่านั้น

### 2.5 AWS console — สร้าง task

**DataSync → Tasks → Create task**

**Step 1 · Configure source location** → Choose an existing location → location จาก 2.3
**Step 2 · Configure destination location** → existing → location จาก 2.4
**Step 3 · Configure settings**

| ส่วน | ช่อง | ค่า | เหตุผล |
|---|---|---|---|
| | Task name | `adls-<container>-to-s3` | |
| | **Task mode** | **Enhanced** | ไม่ต้องมี agent · เร็วกว่า |
| Data transfer configuration | Contents to scan | **Specific files, objects, and folders** → Using filters → Includes `/<โฟลเดอร์เล็ก>/*` (รอบทดสอบ) | ทดสอบเล็กก่อน |
| | Excludes | `*/_temporary/*` (ถ้ามี) | ไฟล์ชั่วคราวของ Spark |
| Transfer options | Transfer mode | **Transfer only data that has changed** | รอบต่อไป incremental อัตโนมัติ |
| | Verify data | **Verify only the data transferred** | ตรวจ checksum ไฟล์ที่ย้าย |
| | Bandwidth limit | **Set bandwidth limit** เช่น 200 MiB/s (ถ้าเจ้าของ Azure กังวลเรื่องโหลด) | ลดผลกระทบต้นทาง |
| Additional settings | **Keep deleted files** | **✓ เปิด** | ไฟล์ที่ถูกลบที่ Azure ไม่ถูกลบใน S3 |
| | **Overwrite files** | ✓ เปิด (S3 มี Versioning เก็บของเดิมให้) | ไฟล์ที่ถูกแก้ที่ Azure ได้เวอร์ชันใหม่ |
| | **Copy object tags** | **✗ ปิด** | ADLS Gen2 (hierarchical namespace) คัดลอก tag ไม่ได้ ถ้าเปิด task จะล้ม |
| Schedule | Frequency | **Not scheduled** (รอบแรกกดเอง) | |
| Task report | | **Summary only** → `s3://com7-raw-adls/_datasync-reports/` | ได้ไฟล์สรุปผลแต่ละรอบไว้ reconcile |
| Logging | Log level | **Log all transferred objects and files** (รอบทดสอบ) · ภายหลังลดเป็น **Log basic information** | |
| | CloudWatch log group | **Autogenerate** | |

**Step 4 · Review** → **Create task**

### 2.6 รอบทดสอบ (โฟลเดอร์เล็ก)

1. Tasks → เลือก task → **Start → Start with defaults**
2. แท็บ **History** → คลิก execution → ดู
   - Status: `Launching → Preparing → Transferring → Verifying → Success`
   - **Data transferred** · **Files transferred** · **Throughput** · **Duration**
3. ถ้า `Error`
   - `Failed to open directory` / 403 → SAS ผิด/หมดอายุ/สิทธิ์ไม่ครบ → ทำ 2.2 ใหม่แล้วแก้ location (Locations → เลือก → **Edit** → SAS token)
   - เกี่ยวกับ tag → ปิด **Copy object tags**
   - timeout / connection → network ฝั่ง Azure ถูกปิด → กลับไป 1.2 ข้อ 4
4. ตรวจผล
   - S3 → bucket → โฟลเดอร์ → เลือกทั้งหมด → **Actions → Calculate total size** → เทียบกับ Folder Statistics ฝั่ง Azure
   - เปิด task report ใน `_datasync-reports/`
5. คูณสัดส่วนเวลา/ข้อมูลของรอบทดสอบ → ประมาณเวลาและเงินของรอบเต็ม (หัวข้อ 4) แล้วขออนุมัติก่อนรอบเต็ม

### 2.7 รอบเต็ม + ตั้งเวลา

1. Task → **Edit** → Contents to scan → **Everything** (หรือ includes หลายโฟลเดอร์ที่ต้องการ)
2. **Start** → รอจบ → ตรวจแบบ 2.6 ข้อ 4
3. ตั้งเวลา: Task → **Edit** → **Schedule** → Custom `cron(0 15 * * ? *)` = 22:00 น. ไทย (DataSync ใช้ UTC)
   - **ค่า $0.55 ต่อรอบ** ไม่ขึ้นกับขนาด → ถ้าข้อมูลเปลี่ยนน้อย รายวันอาจแพงกว่าตัวข้อมูล พิจารณารายสัปดาห์
4. ลด Log level เป็น **Log basic information**

### 2.8 หยุด / ยกเลิก (ไม่กระทบข้อมูลเดิม)

| ต้องการ | ทำ |
|---|---|
| หยุดรอบที่กำลังรัน | Task → History → execution → **Cancel** (ไฟล์ที่คัดลอกแล้วยังอยู่ใน S3) |
| ตัดสิทธิ์ทันที | Azure → Container → Access policy → **ลบ `datasync-ro`** → Save → SAS ใช้ไม่ได้ทันที |
| เลิกถาวร | ลบ schedule → ลบ task → ลบ 2 locations → (ถ้าไม่ใช้ข้อมูล) ลบ bucket `com7-raw-adls` |

---

## 3. วิธี 2 — AWS Glue อ่าน `abfss://` แล้วเขียน Iceberg ผ่าน console

```
Entra ID app (service principal) ─ role "Storage Blob Data Reader" บน container
        │ client_id · secret · tenant
        ▼
Secrets Manager ──► Glue job (Spark · ไม่ผูก VPC connection) ── abfss://<container>@<storage>.dfs.core.windows.net/
                          │
                          └──► Iceberg: glue_catalog.bronze_adls.<table>  (s3://com7-raw-adls/iceberg/)
```

ใช้เมื่ออยากแปลง Delta/CSV → Iceberg ในขั้นเดียว · ถ้าทำวิธี 1 แล้ว **ทางที่ง่ายและปลอดภัยกว่าคือให้ Glue อ่านจาก S3** (ไม่ต้องมี credential Azure) — วิธี 2 จึงเหมาะกับ "ไม่อยากเก็บไฟล์ดิบซ้ำ" หรือ "ดึงบางตาราง"

`[อนุมาน — ยังไม่ได้ยืนยันว่า Glue 5.0 มี hadoop-azure (ABFS driver) ในตัว ขั้น 3.6 มีวิธีตรวจ]`

### 3.1 Azure portal — สร้าง service principal (App registration)

ต้องมีสิทธิ์สร้าง app ใน Entra ID — ถ้าไม่มี ให้ทีม Azure ทำให้

1. portal → **Microsoft Entra ID → App registrations → + New registration**
   - Name: `aws-glue-adls-reader`
   - Supported account types: **Single tenant**
   - Redirect URI: เว้นว่าง → **Register**
2. หน้า Overview จด **Application (client) ID** และ **Directory (tenant) ID**
3. **Certificates & secrets → Client secrets → + New client secret**
   - Description `glue` · Expires **90 days** หรือ **180 days**
   - **Add** → คัดลอก **Value** ทันที (แสดงครั้งเดียว — ไม่ใช่ Secret ID)

### 3.2 Azure portal — ให้สิทธิ์อ่านเฉพาะ container

1. Storage account → **Containers** → คลิก container → **Access Control (IAM)** (ระดับ container ไม่ใช่ระดับ account)
2. **+ Add → Add role assignment**
   - Role: **Storage Blob Data Reader** (อ่านอย่างเดียว · ห้ามเลือก Contributor/Owner)
   - Assign access to: **User, group, or service principal** → **+ Select members** → ค้น `aws-glue-adls-reader`
   - **Review + assign**
3. รอ ~5 นาทีให้สิทธิ์มีผล
4. ตรวจ: container → Access Control (IAM) → **Role assignments** ต้องเห็น app อยู่ใต้ Storage Blob Data Reader

> ถ้า storage ใช้ **ACL ระดับโฟลเดอร์** (POSIX ACL ของ ADLS Gen2) แทน RBAC — role ระดับ container ก็ยังให้สิทธิ์อ่านได้ เพราะ RBAC ถูกตรวจก่อน ACL · ไม่ต้องแก้ ACL ของไฟล์เดิม

### 3.3 AWS console — เก็บ credential ใน Secrets Manager

**Secrets Manager → Store a new secret**

| ช่อง | ค่า |
|---|---|
| Secret type | **Other type of secret** |
| Key/value | `tenant_id` · `client_id` · `client_secret` · `account` (ชื่อ storage) · `container` |
| Encryption key | aws/secretsmanager |
| Secret name | `com7/adls/glue-reader` |
| Rotation | ปิด (secret ฝั่ง Azure หมุนเอง — ตั้งปฏิทินเตือนก่อนหมดอายุ) |

### 3.4 AWS console — IAM role สำหรับ Glue (role ใหม่ ไม่แก้ role เดิม)

**IAM → Roles → Create role**
1. Trusted entity: **AWS service** → Use case **Glue**
2. Permissions: **AWSGlueServiceRole** (managed)
3. Role name: `com7-glue-adls-reader-role` → Create
4. เปิด role → **Add permissions → Create inline policy → JSON**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid": "ReadSecret", "Effect": "Allow", "Action": "secretsmanager:GetSecretValue",
     "Resource": "arn:aws:secretsmanager:ap-southeast-7:<acct>:secret:com7/adls/glue-reader-*"},
    {"Sid": "WriteNewBucketOnly", "Effect": "Allow",
     "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
     "Resource": ["arn:aws:s3:::com7-raw-adls", "arn:aws:s3:::com7-raw-adls/*"]},
    {"Sid": "ReadScripts", "Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"],
     "Resource": ["arn:aws:s3:::aws-glue-assets-<acct>-ap-southeast-7", "arn:aws:s3:::aws-glue-assets-<acct>-ap-southeast-7/*"]},
    {"Sid": "CatalogNewDbOnly", "Effect": "Allow", "Action": "glue:*Table*",
     "Resource": ["arn:aws:glue:ap-southeast-7:<acct>:catalog",
                  "arn:aws:glue:ap-southeast-7:<acct>:database/bronze_adls",
                  "arn:aws:glue:ap-southeast-7:<acct>:table/bronze_adls/*"]},
    {"Sid": "PassSelf", "Effect": "Allow", "Action": "iam:PassRole",
     "Resource": "arn:aws:iam::<acct>:role/com7-glue-adls-reader-role",
     "Condition": {"StringEquals": {"iam:PassedToService": "glue.amazonaws.com"}}}
  ]
}
```
- เขียนได้แค่ bucket ใหม่และ database ใหม่ → **แตะ `com7_gold` และ bucket เดิมไม่ได้แม้สคริปต์ผิด**
- `iam:PassRole` ให้ตัวเอง — แก้ปัญหาเดียวกับที่เจอตอนเปิด interactive session → [[Glue Jobs (ap-southeast-7)]]
- ถ้าบัญชีเปิด **Lake Formation** ต้อง grant สิทธิ์ database `bronze_adls` ให้ role นี้ด้วย

### 3.5 AWS console — สร้าง Glue database ใหม่

**Glue → Data Catalog → Databases → Add database**
- Name: `bronze_adls` · Location: `s3://com7-raw-adls/iceberg/` → **Create database**

### 3.6 ทดสอบใน Glue Studio notebook (ก่อนสร้าง job)

**Glue → ETL jobs → Notebooks → Notebook** → Engine **Spark (Python)** · IAM role `com7-glue-adls-reader-role` → Start

cell แรก (คุมค่าใช้จ่าย)
```python
%glue_version 5.0
%worker_type G.1X
%number_of_workers 2
%idle_timeout 20
%%configure
{"--datalake-formats": "iceberg,delta",
 "--conf": "spark.sql.catalog.glue_catalog=org.apache.iceberg.spark.SparkCatalog --conf spark.sql.catalog.glue_catalog.catalog-impl=org.apache.iceberg.aws.glue.GlueCatalog --conf spark.sql.catalog.glue_catalog.warehouse=s3://com7-raw-adls/iceberg/ --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"}
```

ตรวจว่ามี ABFS driver ไหม
```python
spark._jvm.java.lang.Class.forName("org.apache.hadoop.fs.azurebfs.SecureAzureBlobFileSystem")
```
- ไม่ error → ไปต่อ
- `ClassNotFoundException` → ต้องแนบ jar `hadoop-azure` (เวอร์ชันตรงกับ Hadoop ของ Glue) ไว้ใน S3 แล้วใส่ `--extra-jars` · ดู Hadoop version ด้วย `spark._jvm.org.apache.hadoop.util.VersionInfo.getVersion()`

ตั้ง credential แล้ว **list อย่างเดียว** (ยังไม่อ่านข้อมูล)
```python
import json, boto3
sec = json.loads(boto3.client("secretsmanager", region_name="ap-southeast-7")
                 .get_secret_value(SecretId="com7/adls/glue-reader")["SecretString"])
host = f"{sec['account']}.dfs.core.windows.net"
hc = spark.sparkContext._jsc.hadoopConfiguration()
hc.set(f"fs.azure.account.auth.type.{host}", "OAuth")
hc.set(f"fs.azure.account.oauth.provider.type.{host}", "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
hc.set(f"fs.azure.account.oauth2.client.id.{host}", sec["client_id"])
hc.set(f"fs.azure.account.oauth2.client.secret.{host}", sec["client_secret"])
hc.set(f"fs.azure.account.oauth2.client.endpoint.{host}", f"https://login.microsoftonline.com/{sec['tenant_id']}/oauth2/token")

root = f"abfss://{sec['container']}@{host}/"
fs = spark._jvm.org.apache.hadoop.fs.Path(root).getFileSystem(hc)
[str(s.getPath().getName()) for s in fs.listStatus(spark._jvm.org.apache.hadoop.fs.Path(root))][:50]
```
อ่านตารางเล็ก 1 ตาราง · นับแถว · ดู schema
```python
src = root + "<path ของตารางเล็ก>"
df = spark.read.format("delta").load(src)        # หรือ .parquet / .csv ตามที่เจอใน 1.2
df.printSchema(); df.count()
```
จบแล้ว `%stop_session` (ไม่งั้นนับเงินจนถึง idle timeout)

### 3.7 สร้าง Glue job

**Glue → ETL jobs → Script editor** → Engine **Spark** · Options **Start fresh** → Create script → วางสคริปต์นี้

```python
import sys, json, boto3
from awsglue.utils import getResolvedOptions
from pyspark.sql import SparkSession

args = getResolvedOptions(sys.argv, ["SECRET_ID", "SRC_PATH", "SRC_FORMAT", "TARGET_TABLE"])
spark = SparkSession.builder.getOrCreate()

sec = json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=args["SECRET_ID"])["SecretString"])
host = f"{sec['account']}.dfs.core.windows.net"
hc = spark.sparkContext._jsc.hadoopConfiguration()
hc.set(f"fs.azure.account.auth.type.{host}", "OAuth")
hc.set(f"fs.azure.account.oauth.provider.type.{host}", "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
hc.set(f"fs.azure.account.oauth2.client.id.{host}", sec["client_id"])
hc.set(f"fs.azure.account.oauth2.client.secret.{host}", sec["client_secret"])
hc.set(f"fs.azure.account.oauth2.client.endpoint.{host}", f"https://login.microsoftonline.com/{sec['tenant_id']}/oauth2/token")

target = f"glue_catalog.bronze_adls.{args['TARGET_TABLE']}"
# กันเขียนทับ: ตารางมีอยู่แล้ว → หยุด (รอบ incremental ค่อยเขียนแยกเป็น MERGE ภายหลัง)
if spark.catalog.tableExists(target):
    raise SystemExit(f"{target} มีอยู่แล้ว — ไม่เขียนทับ ลบเองหรือเปลี่ยนชื่อ TARGET_TABLE")

src = f"abfss://{sec['container']}@{host}/{args['SRC_PATH'].lstrip('/')}"
reader = spark.read.format(args["SRC_FORMAT"])
if args["SRC_FORMAT"] == "csv":
    reader = reader.option("header", "true")      # Synapse Link CSV ไม่มี header → ต้องใช้ schema จาก model.json แทน
df = reader.load(src)

n_src = df.count()
df.writeTo(target).using("iceberg").create()      # create() ไม่ทับของเดิม (ต่างจาก createOrReplace)
n_dst = spark.table(target).count()
print(f"[RECONCILE] source={n_src} target={n_dst}")
if n_src != n_dst:
    raise RuntimeError("จำนวนแถวไม่ตรง")
```

แท็บ **Job details**

| ช่อง | ค่า | เหตุผล |
|---|---|---|
| Name | `adls-to-bronze-<table>` | |
| IAM Role | `com7-glue-adls-reader-role` | |
| Glue version | 5.0 (หรือ 6.0 ถ้าทดสอบแล้วใช้ได้ — ถูกกว่า 30%) | |
| Worker type | G.1X | |
| Requested number of workers | 2 (ตารางเล็ก) → เพิ่มทีหลังตามขนาด | |
| Job bookmark | **Disable** | |
| Job timeout | 60 นาที (รอบแรก) | กันรันค้างกินเงิน |
| Number of retries | **0** | ไม่รันซ้ำอัตโนมัติจนกว่าจะรู้สาเหตุ |
| Connections | **ไม่เลือก** | job ที่ไม่ผูก VPC connection ออกอินเทอร์เน็ตได้เอง → ไม่ต้องมี NAT `[อนุมาน — ตรวจด้วยการรันจริง]` |
| Job parameters | `--datalake-formats` = `iceberg,delta` | |
| | `--conf` = (ค่าเดียวกับ `%%configure` ใน 3.6) | Iceberg catalog |
| | `--SECRET_ID` = `com7/adls/glue-reader` | |
| | `--SRC_PATH` = `<path ของตาราง>` | |
| | `--SRC_FORMAT` = `delta` / `parquet` / `csv` | |
| | `--TARGET_TABLE` = `<ชื่อตาราง>` | |

→ **Save** → **Run**

### 3.8 ติดตามและตรวจผล

- แท็บ **Runs** → Run status · Execution time · **DPU hours** (ใช้คำนวณเงินจริง)
- **Output logs** (CloudWatch `/aws-glue/jobs/output`) → หาบรรทัด `[RECONCILE]`
- **Athena** (workgroup ที่อ่านได้) → `SELECT COUNT(*) FROM bronze_adls.<table>`
- ถ้าล้ม
  - `ClassNotFoundException ... azurebfs` → ขาด jar (3.6)
  - `403` / `AuthorizationPermissionMismatch` → role ใน 3.2 ยังไม่มีผล หรือให้ผิด container
  - `UnknownHostException` / timeout → job ออกเน็ตไม่ได้ หรือ firewall Azure ปิด
  - `AccessDenied ... glue:CreateTable` → Lake Formation / inline policy

### 3.9 ตั้งเวลา (หลังทดสอบผ่าน)

**Glue → ETL jobs → Triggers → Add trigger** → Schedule · Custom `cron(30 15 * * ? *)` (22:30 ไทย) · เลือก job
สคริปต์ข้างบนสร้างตารางครั้งเดียว — รอบรายวันต้องเปลี่ยนเป็น `MERGE` ตามคีย์ (แบบ [[Reconcile Pipeline - Glue Jobs]]) ก่อนตั้งเวลา

### 3.10 หยุด / ยกเลิก

| ต้องการ | ทำ |
|---|---|
| หยุด job ที่กำลังรัน | Runs → เลือก run → **Stop job run** |
| ตัดสิทธิ์ Azure ทันที | Entra ID → App registrations → app → Certificates & secrets → **ลบ secret** (หรือลบ role assignment ใน 3.2) |
| เลิกถาวร | ลบ trigger → job → database `bronze_adls` → secret → role → app ใน Entra |

---

## 4. ค่าใช้จ่าย

### 4.1 ราคาต่อหน่วย (ap-southeast-7 · ดึง 2026-10-12)

| รายการ | ราคา | ใช้กับ |
|---|---|---|
| DataSync Enhanced — ข้อมูลที่คัดลอก | **$0.015 / GB** | วิธี 1 |
| DataSync Enhanced — ต่อรอบ (task execution) | **$0.55 / รอบ** | วิธี 1 |
| Glue ETL / interactive session (Glue 5.0) | **$0.44 / DPU-ชม.** · คิดเป็นวินาที ขั้นต่ำ 1 นาที | วิธี 2 |
| Glue ETL (Glue 6.0+) | **$0.308 / DPU-ชม.** | วิธี 2 |
| S3 Standard | **$0.0225 / GB-เดือน** (50 TB แรก) | ทั้งคู่ |
| S3 PUT / LIST | $0.0045 / 1,000 request | ทั้งคู่ |
| S3 GET | $0.0036 / 10,000 request | ทั้งคู่ |
| Secrets Manager | $0.40 / secret / เดือน | ทั้งคู่ |
| ข้อมูลเข้า AWS จากอินเทอร์เน็ต | **$0** | ทั้งคู่ |
| NAT Gateway (เฉพาะถ้า Glue ผูก VPC connection) | $0.05015 / ชม. + $0.05015 / GB | วิธี 2 |
| **Azure egress** (Asia · Microsoft network) | **100 GB แรก/เดือน ฟรี** · ถัดไป 10 TB **$0.12 / GB** · ถัดไป 40 TB $0.085 / GB | **ทั้งคู่ · บิลฝั่ง Azure** |
| Azure read / list operations (Hot) | ~$0.004–0.005 / 10,000 read · ~$0.065 / 10,000 list `[อนุมาน — ราคาทั่วไป ไม่ใช่ราคา region ของ COM7]` | ทั้งคู่ · บิลฝั่ง Azure |

**ตัวที่แพงที่สุดคือ Azure egress** — ราว 8 เท่าของค่า DataSync และจ่ายเท่ากันไม่ว่าเลือกวิธีไหน

### 4.2 ประมาณการ — คัดลอกครั้งแรก

สมมติ: ไฟล์ ~200,000 ไฟล์ต่อ TB · egress free tier ยังไม่ถูกใช้ · 1 USD ≈ 33 บาท `[อนุมาน]`

| ขนาด | วิธี 1 DataSync (AWS) | วิธี 2 Glue (AWS) | Azure egress (ทั้งคู่) | S3 เก็บ/เดือน | **รวมเดือนแรก (วิธี 1)** |
|---:|---:|---:|---:|---:|---:|
| 100 GB | $2.05 | ~$2–4 | $0 | $2.25 | **≈ $5 (≈ 170 บาท)** |
| 500 GB | $8.05 | ~$11–22 | $48 | $11.25 | **≈ $68 (≈ 2,200 บาท)** |
| 1 TB | $15.91 | ~$22–44 | $111 | $23 | **≈ $150 (≈ 5,000 บาท)** |
| 5 TB | $77.35 | ~$110–220 | $602 | $115 | **≈ $795 (≈ 26,000 บาท)** |

วิธีคิดวิธี 1 = `0.015 × GB + 0.55` · egress = `(GB − 100) × 0.12`
วิธี 2 = DPU-ชม. × $0.44 — **เดาจาก throughput ~100–200 GB/ชม. ที่ 10 DPU** (1 TB ≈ 5–10 ชม. × 10 DPU = 50–100 DPU-ชม.) `[อนุมาน — ต้องวัดจากรอบทดสอบ]` · Glue 6.0 ถูกลง 30% · ถ้าผูก VPC connection บวก NAT ≈ $51/TB
S3 request (PUT/LIST/GET) ≈ $1–5 ต่อ 1 ล้านไฟล์ — เล็กมากเทียบกับรายการอื่น

### 4.3 ประมาณการ — รายเดือนหลังจากนั้น (incremental)

สมมติ: ข้อมูลเปลี่ยนวันละ 5 GB (150 GB/เดือน)

| | รายวัน (30 รอบ) | รายสัปดาห์ (4 รอบ) |
|---|---:|---:|
| DataSync ต่อ GB (150 GB × $0.015) | $2.25 | $2.25 |
| DataSync ต่อรอบ | $16.50 | $2.20 |
| Azure egress (150 GB × $0.12 · ถ้า free tier หมดแล้ว) | $18.00 | $18.00 |
| S3 เพิ่มขึ้น (150 GB) | +$3.38/เดือน สะสม | +$3.38 |
| Secrets Manager + CloudWatch logs | ~$1 | ~$1 |
| **รวม** | **≈ $41/เดือน (≈ 1,350 บาท)** | **≈ $27/เดือน (≈ 890 บาท)** |

วิธี 2 รายวัน: ตาราง 1 ตาราง 2 DPU × 10 นาที ≈ $0.15/รอบ ≈ $4.4/เดือน ต่อตาราง (Glue 5.0) + egress เท่ากัน `[อนุมาน]`

### 4.4 คุมค่าใช้จ่าย

1. **AWS Budgets** → Create budget → Cost budget · $50 (หรือตามที่อนุมัติ) · filter tag `project=adls-migration` · แจ้งเตือนที่ 50% / 80% / 100%
2. Azure → **Cost Management → Budgets** บน resource group ของ storage (ให้เจ้าของ Azure ตั้ง) — เพราะ egress อยู่บิลฝั่ง Azure
3. รอบทดสอบเล็กก่อนเสมอ แล้วคูณสัดส่วน
4. Glue: ตั้ง `%idle_timeout` · job timeout · retries = 0 · ใช้ Glue 6.0 ถ้าใช้ได้ (ถูกกว่า 30%)
5. DataSync: ถ้าข้อมูลเปลี่ยนน้อย ใช้รายสัปดาห์ (ค่า $0.55/รอบ)

---

## 5. เทียบสองวิธี

| | วิธี 1 DataSync | วิธี 2 Glue |
|---|---|---|
| ได้อะไร | ไฟล์ตามต้นฉบับใน S3 (Raw) | ตาราง Iceberg (Bronze) ทันที |
| credential Azure | SAS อ่านอย่างเดียว ใส่ใน DataSync | service principal อยู่ใน Secrets Manager · Glue ถือ |
| ต้องเขียนโค้ด | ไม่ต้อง | ต้อง (สคริปต์ข้างบน) |
| incremental | มีในตัว (Transfer only changed) | ต้องเขียน MERGE เอง |
| ตรวจย้อน | มีไฟล์ดิบ · task report | ไม่มีไฟล์ดิบ — ผิดแล้วต้องดึงจาก Azure ใหม่ (เสีย egress อีกรอบ) |
| ค่า AWS ต่อ TB | ~$16 | ~$22–44 `[อนุมาน]` + เวลาพัฒนา |
| เวลาเตรียม | ~ครึ่งวัน | ~1–3 วัน (รวม jar/สิทธิ์ Entra) |
| เสี่ยงต่อข้อมูลเดิม | ต่ำ (Read+List) | ต่ำ (Blob Data Reader) |

**แนะนำ:** วิธี 1 ก่อน (ได้สำเนาดิบครบ · จ่าย egress ครั้งเดียว) แล้วให้ Glue อ่านจาก S3 ไปทำ Bronze — ใช้วิธี 2 เฉพาะตารางที่ไม่อยากเก็บไฟล์ดิบซ้ำ

---

## 6. Checklist

- [ ] 1.1 ขอสิทธิ์ Reader + อนุมัติงบ egress จากเจ้าของ Azure
- [ ] 1.2 กรอกตารางสำรวจ (key access · network · ขนาด · รูปแบบ)
- [ ] 1.3 สร้าง bucket `com7-raw-adls` (versioning · block public · tag)
- [ ] 4.4 ตั้ง AWS Budget + ขอ Azure budget
- [ ] วิธี 1: 2.1–2.5 → รอบทดสอบ 2.6 → ขออนุมัติรอบเต็ม → 2.7
- [ ] วิธี 2 (ถ้าจำเป็น): 3.1–3.6 → job 3.7 กับตารางเล็ก → ตรวจ 3.8
- [ ] บันทึกผลจริง (GB · ไฟล์ · เวลา · ค่าใช้จ่าย) กลับมาที่โน้ตนี้ แทนตัวเลขประมาณการ

## แหล่งอ้างอิง

- AWS DataSync — [Configuring transfers with Microsoft Azure Blob Storage](https://docs.aws.amazon.com/datasync/latest/userguide/creating-azure-blob-location.html) (ขั้นตอน console · SAS · ข้อจำกัด · Enhanced ไม่ต้องมี agent)
- AWS — [DataSync Enhanced mode adds Azure Blob … (2026-07)](https://aws.amazon.com/about-aws/whats-new/2026/07/aws-datasync-hdfs-azure-blob-hyper-v/)
- AWS — [DataSync pricing](https://aws.amazon.com/datasync/pricing/) · [Glue pricing](https://aws.amazon.com/glue/pricing/) · ราคา ap-southeast-7 จาก AWS Price List API (`aws pricing get-products`)
- Azure — [Bandwidth pricing](https://azure.microsoft.com/en-us/pricing/details/bandwidth/) (egress Asia)

## เชื่อมกับโน้ตอื่น

[[ADLS Gen2 to S3]] · [[Glue Jobs (ap-southeast-7)]] · [[Reconcile Pipeline - Glue Jobs]] · [[Medallion Layer Definition]] · [[Other Systems]] · [[Decisions]]
