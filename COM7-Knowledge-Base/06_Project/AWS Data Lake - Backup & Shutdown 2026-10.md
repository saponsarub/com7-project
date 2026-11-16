# AWS Data Lake (603238661233) — สำรอง · คู่มือ · การปิดระบบ 2026-10

> ตัวเต็ม + โค้ดทั้งหมดอยู่ที่ `D:\AWS_Backup\603238661233_2026-10-30\` (เครื่อง Sapon · ไม่อยู่ใน git) · เกี่ยวข้อง: [[Glue Jobs (ap-southeast-7)]] · [[Reconcile Pipeline - Overview]] · [[AWS Data Lake Proposal Review 2026-10]]

> ⚠️ **เก็บเป็นความลับ** — โฟลเดอร์นี้มีค่าตั้งของ Lambda (environment variables), สคริปต์ที่อ้างชื่อ secret / connection,
> รายชื่อผู้รับอีเมลแจ้งเตือน และสิทธิ์ IAM · เก็บในเครื่องหรือที่เก็บภายในที่จำกัดสิทธิ์ · ห้ามใส่ git / แชร์สาธารณะ
> ไม่มีค่า secret (รหัสผ่าน / key) อยู่ในโฟลเดอร์นี้ — ค่าจริงยังอยู่ใน AWS Secrets Manager

**สถานะล่าสุด (ตรวจ 2–6 พ.ย. 2026): ลบแล้วทั้งหมด** — S3 ทุก bucket (~1.75 TB) · DMS · NAT · EC2 VPN · Glue · Lambda · Step Functions · Redshift · RDS snapshot · Secrets · IAM role ของโครงการ · QuickSight unsubscribe แล้ว · ค่าใช้จ่าย ≈ 0 · เหลือเอง: KMS key (รอลบ 7 วัน) · ของฟรี (Athena workgroup, Glue DB `default`, role ระบบ/SSO — **ห้ามลบ** `AWSReservedSSO_*`, `OrganizationAccountAccessRole`) · ⬜ DataZone domain (Singapore/Sydney) ลบใน console · ⬜ ฝั่ง Azure: Entra app `aws-glue-adls-reader`

**เหตุผล:** SSOT ไม่ผ่าน POC และงบประมาณ → ย้ายเป็นเครื่อง PC + MySQL ([[Decisions|D-21]])

สถานะเดิม 30 ต.ค. ~16:00: ปิดการทำงานแบบเปิดกลับได้ (§9) · §10–11 ด้านล่างเป็นแผนก่อนลบ — **ทำครบแล้ว**

---

## 1. ภาพรวมระบบ (อนุมานจากโค้ดและค่าตั้ง)

```
 on-prem SQL Server (ITEC · K2 · MSSQL COM7)
        │  ผ่าน WireGuard VPN (EC2 Goldintegrate-WireGuard-VPN) + NAT Gateway
        ▼
 ┌─ DMS full-load ทุกคืน 23:30 (task-fullload-combined-v1 บน dms-server-gold) ─► S3 bronze (Parquet)
 │        └─ EventBridge "DMS task เสร็จ" ─► Step Functions com7-dms-ingestion-pipeline
 │                  ├─ Lambda com7-dms-validate (ตรวจครบ / นับแถวจาก Parquet footer)
 │                  ├─ Glue: bronze→silver item ─► silver→gold dim_item
 │                  ├─ Glue: bronze→gold dim_branch
 │                  └─ Glue: bronze→gold fact_sales_enriched (join item + branch)
 │
 ├─ Reconcile ทุกคืน 23:30 (จ–ส) + ลึกวันอาทิตย์ ─► Step Functions com7-reconcile-pipeline
 │        ├─ Glue com7-reconcile-generic (ต่อ SQL Server ตรงผ่าน JDBC → diff → MERGE ลง Iceberg)
 │        └─ Glue com7-iceberg-maintenance (compact / expire snapshot)
 │
 ├─ 23:00 Lambda com7-bronze-backup: copy bronze → bucket backup (versioned) + manifest
 ├─ 23:30 Lambda test-ses-googlesheet: Google Sheets → S3 CSV + log + อีเมลรายงาน (SES)
 │        └─ async ► Lambda com7-rowcount-googlesheet (นับแถวจริงกลับเข้า log)
 └─ ap-southeast-1 (งาน mis-tan): Lambda ทุก 5 นาที Google Sheet → CDC → S3 · Glue ทุกชั่วโมง MERGE → Iceberg

 ชั้นข้อมูล:  bronze (DMS) → silver (ทำความสะอาด, Iceberg) → gold (dim/fact สำหรับรายงาน, Iceberg) · Glue Catalog + Athena
 แจ้งเตือน:   SNS com7-data-pipeline-alerts · com7-reconcile-alerts · googlesheet-ev1
```

รันล่าสุดก่อนปิด: pipeline หลักรันสำเร็จทุกคืนจนถึง 29 ต.ค. 23:30 (reconcile · DMS ingestion · bronze backup · Google Sheet ingest)

---

## 2. ในโฟลเดอร์นี้มีอะไร

| ที่อยู่ | เนื้อหา |
|---|---|
| `<region>/lambda/<ชื่อ>/` | `code.zip` (โค้ดที่ deploy อยู่) · `src/` (แตกไฟล์ให้อ่าน) · `config.json` (runtime, env vars, role, layer) · `policy.json` · `triggers.json` · `layers/` |
| `<region>/lambda/functions_summary.json` | runtime · memory · role · log ล่าสุด |
| `<region>/glue/jobs/<ชื่อ>/` | สคริปต์ · `job.json` (ค่าตั้งทั้งหมด, arguments) · `extra/` (shared.zip ฯลฯ) |
| `<region>/glue/jobs_runtime_summary.json` | Glue version · worker · รันล่าสุด · error ล่าสุด |
| `<region>/glue/` | `crawlers.json` · `triggers.json` · `workflows.json` · `connections.json` (ไม่มีรหัส) · `catalog/<db>.json` (โครงตารางทุกตาราง) |
| `<region>/orchestration/` | Step Functions (definition เต็ม) · EventBridge rules + targets · Scheduler (`eventbridge_schedules_full.json` = สร้างใหม่ได้ทันที) |
| `<region>/dms/` | task (settings + table mappings) · endpoint (ไม่มีรหัส) · replication instance |
| `<region>/network.json` | VPC · subnet · route table · NAT · endpoint · EIP · security group · EC2 |
| `<region>/dynamodb/` · `sns_topics.json` · `athena.json` · `redshift_serverless.json` · `rds_snapshots.json` · `log_groups.json` | ค่าตั้ง / รายการ |
| `<region>/secrets_metadata_NO_VALUES.json` | ชื่อ secret + วันที่ใช้ล่าสุด (**ไม่มีค่า**) |
| `_account/iam_roles_used.json` | 20 role ที่ Lambda / Glue / Step Functions ใช้ (trust + policy ครบ) |
| `_account/s3_buckets.json` | 35 bucket: region · versioning · lifecycle · policy · โฟลเดอร์ชั้นบน |
| `_account/quicksight/summary.json` | QuickSight: ไม่มี dashboard / dataset (มี analysis 1 อันที่ถูกลบไปแล้ว) |
| `inventory.json` | ทรัพยากรที่มีค่าใช้จ่าย ณ ก่อนปิด |
| `_shutdown/actions.json` | ทุกอย่างที่ปิด + สถานะก่อนปิด (ใช้เปิดกลับ) |
| `SHUTDOWN_PLAN.md` | แผนเดิม + ตารางค่าใช้จ่าย |

---

## 3. Lambda — แต่ละตัวทำอะไร

| ชื่อ (region) | ทำอะไร | เรียกโดย | อ่าน → เขียน | สถานะก่อนปิด |
|---|---|---|---|---|
| **com7-dms-validate** (7) | ตรวจว่า DMS full-load จบจริง: task จบเพราะโหลดเสร็จ (ไม่ใช่มีคนหยุด) · ทุกตารางถึง "Table completed" · นับแถวในไฟล์ Parquet (อ่าน footer ด้วย range GET) เทียบกับที่ DMS รายงาน (ยอมคลาด `ROW_TOLERANCE`) · ตอบ pass/fail ให้ Step Functions | EventBridge (DMS จบ → อีเมล SNS) และ Step Functions `com7-dms-ingestion-pipeline` | DMS API + S3 bronze → SNS | ใช้งานทุกคืน (29 ต.ค.) |
| **com7-bronze-backup** (7) | 23:00 คัดลอก `dms/` ใน bronze ไป bucket backup (versioning = ทุกรอบได้ version ใหม่) + manifest บอก version ต้นทาง/ปลายทาง · `{"dryRun":true}` ดูอย่างเดียว · ไม่ลบ / ไม่เขียน bronze | Scheduler `com7-bronze-backup-nightly` | `com7data-bronze` → `com7data-backup` + SNS | ใช้งานทุกคืน |
| **test-ses-googlesheet** v2.4.2 (7) | ดึงหลาย tab จาก Google Sheets (service account ใน Secrets Manager) → CSV ลง `google-sheet-extract` · retry tab ที่พลาด · เขียน log แบ่ง year/month/day · ส่งอีเมลรายงาน HTML ผ่าน SES · เรียก rowcount แบบ async | Scheduler `ingest-googlesheet` 23:30 | Google Sheets → S3 + log + SES | ใช้งานทุกคืน (ชื่อมี test แต่เป็นตัวจริง) |
| **com7-rowcount-googlesheet** v2.1.0 (7) | นับแถว CSV จริงบน S3 (ใช้ csv reader — เซลล์ที่ขึ้นบรรทัดใหม่ไม่นับเกิน) แล้วเติมกลับเข้า log ของ ingest | ถูกเรียกจาก test-ses-googlesheet | S3 CSV → S3 log | ใช้งาน |
| **com7-snapshot-intake-poc** (7) | POC: รับ event DMS → ตรวจ task ที่อนุญาต → จองรอบใน DynamoDB `com7-snapshot-control-poc` → copy ไฟล์ bronze (ระบุ VersionId) ไปเป็น snapshot + manifest | Step Functions `com7-snapshot-observer-poc` | bronze → `com7data-snapshot-poc` | POC (ล่าสุด 11 ก.ย.) |
| **mis-test-api** (7) | ทดสอบ: ดึง JSON จาก api.restful-api.dev แล้วเก็บลง S3 | มือ | API → `mis-tan-test-bucket/api-store/` | ทดสอบ (11 ก.ย.) |
| **mis-test-lambda** (7) | สคริปต์ Glue (Google Sheet → S3) ที่ถูกวางใน Lambda — import awsglue ซึ่ง Lambda ไม่มี **ใช้งานไม่ได้** | มือ | – | เสีย / ทดสอบ |
| **mis-tan-dev-gsheet-cdc** (1) | ทุก 5 นาที: อ่าน Google Sheet ทั้งหมด → เทียบ snapshot ล่าสุดด้วย key + row hash → เขียน CDC (I/U/D) เป็น JSONL ลง S3 + อัปเดต snapshot · ไม่มีการเปลี่ยน = ไม่เขียน · ตั้งค่าผ่าน Terraform | EventBridge rule ทุก 5 นาที | Google Sheet → `mis-tan-elt` (state/ + cdc/) | ทำงานอยู่ (งาน mis-tan) |

---

## 4. Glue jobs — แต่ละตัวทำอะไร

### 4.1 pipeline หลัก (ap-southeast-7 · ใช้งานจริง)
| Job | ทำอะไร | อ่าน → เขียน | Worker | รันล่าสุด |
|---|---|---|---|---|
| **com7-reconcile-generic** (2,179 บรรทัด) | "CDC ฝั่งปลายทาง" สำหรับ SQL Server ที่ไม่มี CDC/log: นับแถวทั้งสองฝั่ง → อ่าน source แบบแบ่งช่วงขนานกัน (เพราะ WireGuard หลุดเป็นระยะ) → diff ตาม primary key → MERGE insert/update/delete ลง Iceberg · มีขั้นตามหาแถวที่ถูกลบ, audit การลบ, จัดประเภทความล้มเหลว (link ล่ม = retry ได้ · ข้อมูลไม่ตรง = ไม่ retry) · ตารางที่ดูแลกำหนดใน `s3://com7data-artifacts-…/reconcile/reconcile_tables.json` | SQL Server (JDBC ผ่าน VPN) → `com7data-fact-sales-itec` Iceberg (`com7_reconcile`) | G.2X×10 | 29 ต.ค. ✅ |
| **com7-iceberg-maintenance** | ตาราง reconcile เป็น merge-on-read → job นี้ rewrite data files / position deletes / manifests แล้ว expire snapshot (remove orphan เปิดเองเท่านั้น) | Iceberg reconcile | G.2X×10 | 29 ต.ค. ✅ |
| **etl-bronze-to-silver-itec-item** | ทำความสะอาดสินค้า DMS → silver `itec_item` | bronze → silver | G.1X×2 | 29 ต.ค. ✅ |
| **etl-silver-to-gold-dim-item** | silver item → gold `dim_item` | silver → gold | G.1X×2 | 29 ต.ค. ✅ |
| **etl-dms-dim-branch-to-gold** | สาขาจริงจาก DMS → gold `dim_branch` (แทน stub เดิมที่ทำให้ชื่อสาขา/ภาค/จังหวัดเป็น NULL) | bronze `dms/dim/branch_itec/` → gold | G.1X×2 | 29 ต.ค. ✅ |
| **etl-dms-fact-sales-to-gold** | ยอดขายระดับรายการ (SalesId) join dim_item + dim_branch → `fact_sales_enriched` (ใช้เวลานานสุด ~22 นาที) | bronze `dms/rpt/fact_sales_itec/` → gold | G.1X×2 | 29 ต.ค. ✅ |

### 4.2 เส้นทางเก่า / ทางเลือก (ap-southeast-7)
| Job | ทำอะไร | รันล่าสุด |
|---|---|---|
| etl-bronze-to-silver-itec-sale · etl-silver-to-gold-fact-sales | เส้นทางยอดขายแบบไฟล์ (pipeline `com7-data-ingestion-pipeline`) → gold `fact_sales` + `dim_date` | ส.ค.–ก.ย. |
| etl-bronze-to-silver-item | ทำความสะอาดสินค้าละเอียด: หมวดหลัก ~12 หมวด · แบรนด์ · รุ่น (เช่น iPhone 15 Pro Max) · ความจุ/สี · ตัดสินค้า Demo/Promo/Service | 1 ก.ย. |
| etl-bronze-to-silver-branch | ทำความสะอาดสาขา: ชื่อ · ช่องทาง ONLINE/STORE · เปิดอยู่ไหม · แบรนด์ร้าน (Banana, Studio7, …) · ในห้าง/เดี่ยว · จังหวัดไทย 77 · ภาคตาม สสช. | 1 ก.ย. |
| itec-raw-to-bronze | CSV ดิบ → bronze (Glue 4.0) | 1 ก.ย. |
| etl-cdc-apply-itec-item-test | ทดลอง MERGE ไฟล์ CDC ของ DMS เข้า silver + watermark | ❌ AccessDenied (27 ส.ค.) |

### 4.3 POC / ทดลอง (ap-southeast-7)
| Job | ทำอะไร | รันล่าสุด |
|---|---|---|
| com7-poc-group-checksum | ตรวจ "ค่าเปลี่ยนแต่จำนวนแถวเท่าเดิม" ที่ reconcile มองไม่เห็น: ทำ signature รายเดือน (SalesCrDatetime) ทั้งสองฝั่งแล้วเทียบ | 18 ก.ย. ✅ |
| com7-snapshot-branch-diff-poc | diff แบบมี key ระหว่าง snapshot 2 รอบ (สาขา/สินค้า) → INSERT/UPDATE/DELETE | 14 ก.ย. ✅ |
| com7-snapshot-fact-diff-poc | diff แบบ multiset ของ fact_sales (ไม่มี key แท้ มีแถวซ้ำจริง) ด้วย SHA-256 · ตรวจสมดุลจำนวน | 14 ก.ย. ✅ |
| com7-ai-data-preparation-test | (notebook) เตรียมข้อมูลฝึก demand forecasting จาก `fact_sales_enriched` | ไม่เคยรัน |
| adls-pilot-test · adls-copy-staging-pilot | ทดลองดึงไฟล์จาก Azure Data Lake (ADLS Gen2) ด้วย secret `com7/adls/glue-reader` → S3 (ข้ามไฟล์ที่มีแล้ว) | 14 ต.ค. |
| ev7-leads | Google Sheet leads EV7 → S3 CSV (แก้จากโค้ด Lambda ให้รันใน Glue ได้) | 2 ก.ย. ✅ |
| mis-tan-glue-test · mis-test- · mis-test-api-get-data | ทดลอง (Google Sheet, chart, Excel PO) | ❌ ทั้งหมด |

### 4.4 region อื่น
| Job | ทำอะไร | รันล่าสุด |
|---|---|---|
| mis-tan-dev-cdc-merge (ap-southeast-1) | อ่าน CDC (JSONL) จาก Lambda gsheet-cdc → MERGE upsert/delete เข้า Iceberg · ใช้ job bookmark | **รันทุกชั่วโมงและขึ้น FAILED** (`SystemExit: 0` = ไม่มีไฟล์ใหม่แต่ถูกนับเป็นล้มเหลว) — เสียเงินฟรีทุกชั่วโมง |
| fact_sales- (ap-southeast-1) | สร้างตาราง Iceberg `test-sale-com.fact_sales` จาก Parquet | 22 ก.ย. |
| mis-tan-ex-job (ap-southeast-2) | ตัวอย่างสอนของ AWS (Medicare) | ❌ |

---

## 5. Orchestration

**Step Functions (ap-southeast-7)**
| ชื่อ | ขั้นตอน | ล่าสุด |
|---|---|---|
| com7-dms-ingestion-pipeline | รอ DMS นิ่ง → `com7-dms-validate` → แยกตาม dataset (item / sale / fact_sales / all) → `all` = dim 3 ตัวขนานกัน แล้วตาม fact_sales_enriched → แจ้งผลทาง EventBridge | 29 ต.ค. ✅ |
| com7-reconcile-pipeline | ทีละตาราง (Map): `com7-reconcile-generic` → อ่านประเภทความล้มเหลว → link ล่ม = รอแล้วลองใหม่ (สูงสุด 4) · ข้อมูลไม่ตรง / ค่าเพี้ยน = แจ้ง SNS ทันที → สุดท้าย `com7-iceberg-maintenance` | 29 ต.ค. ✅ |
| com7-data-ingestion-pipeline | ไฟล์ที่อัปโหลด: ผล GuardDuty สแกน → ย้ายเข้า bronze หรือ quarantine → เลือก ETL ตามชื่อไฟล์ (item / sale) | 26 ส.ค. |
| com7-snapshot-observer-poc | intake → มี baseline ไหม → diff มิติ | 11 ก.ย. |

**ตารางเวลา (EventBridge Scheduler, เวลาไทย)** — ปิดแล้วทั้งหมด
| ชื่อ | เวลา | สั่งอะไร |
|---|---|---|
| com7-bronze-backup-nightly | ทุกวัน 23:00 | Lambda com7-bronze-backup |
| com7-dms-fullload-combined-nightly | ทุกวัน 23:30 | เริ่ม DMS task-fullload-combined-v1 (reload) |
| com7-reconcile-nightly | จ–ส 23:30 | reconcile-pipeline (fact_sales_itec, dim_item_itec, dim_branch_itec) |
| com7-reconcile-weekly-deep | อา 23:30 | reconcile-pipeline แบบลึก |
| ingest-googlesheet | ทุกวัน 23:30 (เฉพาะปี 2026) | Lambda test-ses-googlesheet |

**EventBridge rules** (ปิดแล้ว): DMS โหลดเสร็จ → pipeline (3 ตัว) · GuardDuty สแกนไฟล์ → pipeline · เหตุการณ์ pipeline → SNS · snapshot POC · (ap-southeast-1) ทุก 5 นาที → gsheet-cdc
ยังเปิด: `DO-NOT-DELETE-AmazonGuardDutyMalwareProtectionS3-*` 2 ตัว (AWS จัดการเอง · คิดเงินเฉพาะตอนมีไฟล์อัปโหลดให้สแกน)

---

## 6. DMS (ap-southeast-7)
- Instance **dms-server-gold** (r6i.large · ≈ 6 USD/วัน) — task ทั้ง 7 เป็น full-load และหยุดอยู่ (ถูกปลุกโดย schedule ทุกคืน)
- Task: `task-fullload-combined-v1` (dim.item_itec · branch_itec · mem_itec · rpt.fact_sales_itec · fact_bank_itec — ตัวที่รันทุกคืน) · `task-fullload-bronze-dim` · `task-fullload-bronze-v1` · `task-fullload-fact-sales-itec` · `task-fullload-v3` (rpt.fact_% + onhandendmonth_itec) · `task-reconcile-fact-sales-incr` / `-keys`
- Source: SQL Server ITEC · K2 (HPCOM7) · MSSQL COM7 · Target: S3 bronze / fact-sales-itec / ingestion / itec / itos / test
- ap-southeast-2: instance **test1** (t3.medium · ≈ 2.7 USD/วัน, ไม่มี task) · serverless config `migrateitos`
- ไฟล์: `<region>/dms/tasks.json` (settings + table mappings ครบ — สร้าง task ใหม่ได้) · `endpoints.json` (ไม่มีรหัส — รหัสอยู่ใน secret)

## 7. เครือข่าย (ap-southeast-7)
- **EC2 `Goldintegrate-WireGuard-VPN`** (t3.small, EIP (IP อยู่ใน backup)) = อุโมงค์ไป on-prem ที่ DMS และ reconcile ใช้ต่อ SQL Server · **หยุดแล้ว** (ดิสก์และ IP อยู่ครบ)
- **NAT Gateway `com7-reconcile-nat`** (EIP (IP อยู่ใน backup)) — ทางออกอินเทอร์เน็ตของ Glue ใน VPC สำหรับ reconcile · ยังอยู่ (≈ 1.2 USD/วัน)
- VPC endpoint: S3 gateway 2 (ฟรี) · STS interface 1 · PrivateLink ไป `vpce-svc-…` 3 ตัว (+1 ที่ Sydney) — เป็นบริการของ account อื่น ไม่ได้แตะ
- รายละเอียดครบใน `ap-southeast-7/network.json` (route table ชี้ไป NAT อยู่ที่ไหน · security group)

## 8. ข้อมูลและของอื่น ๆ
**S3 (ไม่ได้แตะ)** ~1.75 TB: `com7data-bronze` 959 GB (dms/ + detail-sale/) · `com7data-backup` 418 GB · `com7data-gold` 181 GB · `test-connection-dms` 82 GB · `com7-gold-sale-us-test` 53 GB (us-east-1) · `com7data-snapshot-poc` 28 GB · `com7data-fact-sales-itec` 16 GB · `com7data-artifacts` 9 GB (มี `reconcile/reconcile_tables.json` = รายการตาราง reconcile) · ที่เหลือเล็ก — รายละเอียด `_account/s3_buckets.json`

**Glue Catalog (ap-southeast-7)**: `com7_gold` (dim_branch, dim_date, dim_item, fact_sales, fact_sales_enriched) · `com7_silver` (dim_branch, dim_item, itec_item, itec_sale) · `com7_reconcile` (dim_branch_itec, dim_item_itec, fact_sales_itec, reconcile_delete_audit) · `com7_dms_verify` · `com7_change_detection_poc` · `googlesheet-raw` + `default` (EV7, Grab, Lineman จาก Google Sheets) · `bronze_adls` · อื่น ๆ — โครงตารางครบใน `glue/catalog/`

**DynamoDB**: `com7-snapshot-control-poc` (9 แถว, on-demand ≈ 0) — สำรองทั้งข้อมูลแล้ว
**SNS**: com7-data-pipeline-alerts (2 ผู้รับ) · com7-reconcile-alerts (1) · googlesheet-ev1 (1)
**Secrets Manager** (ชื่อเท่านั้น): `com7/reconcile/mssql-source` · `com7/google-sheets/service-account` · `com7/adls/glue-reader` · `mssqldb-250` · `glue!…-Sqlserver-connection-…` · `mis-test-gg-sheet-key` · `mis-tan-dev-gsheet-sa` (ap-southeast-1) · และตัวทดสอบ
**Redshift Serverless**: workgroup 4 (mis-com7, data-team-workgroup, default ×2) — idle ไม่คิดเงิน compute
**RDS**: ไม่มี instance · manual snapshot 5 ตัว (~640 GB)
**QuickSight** (ap-southeast-1, บัญชี "mis-tan", Enterprise): user 4 คน · ไม่มี dashboard / dataset / Q topic
**IAM**: 20 role ที่ใช้ (`_account/iam_roles_used.json`) — เช่น com7-glue-reconcile-role, com7-glue-etl-role, com7-stepfunctions-pipeline-role, com7-reconcile-sfn-role

---

## 9. สิ่งที่ปิดไปแล้ว (30 ต.ค. 2026) — เปิดกลับได้ทุกข้อ

| # | ปิดอะไร | วิธีเปิดกลับ |
|---|---|---|
| 1 | EventBridge Scheduler 5 ตัว → DISABLED | Console › EventBridge › Schedules › Enable · หรือ `aws scheduler update-schedule … --state ENABLED` (ค่าครบใน `eventbridge_schedules_full.json`) |
| 2 | EventBridge rules 7 ตัว (6 ที่ ap-southeast-7 + gsheet-cdc ทุก 5 นาทีที่ ap-southeast-1) → DISABLED | `aws events enable-rule --name <ชื่อ> --region <region>` |
| 3 | Glue trigger `mis-tan-dev-cdc-merge-schedule` (ทุกชั่วโมง) → หยุด | `aws glue start-trigger --name … --region ap-southeast-1` |
| 4 | Glue crawler `Test-ev` (ทุกวัน 12:54) → ปิด schedule | `aws glue start-crawler-schedule --crawler-name Test-ev` |
| 5 | Lambda ทั้ง 8 ตัว → reserved concurrency = 0 (เรียกแล้วไม่ทำงาน) | `aws lambda delete-function-concurrency --function-name <ชื่อ>` (เดิมไม่มีการตั้ง) |
| 6 | EC2 WireGuard VPN → stopped | `aws ec2 start-instances --instance-ids i-0148955a073da2118 --region ap-southeast-7` (IP เดิม) |
| 7 | QuickSight user ที่เป็น ADMIN_PRO → ADMIN (Pro user เป็นตัวเปิดค่า Amazon Q in QuickSight ≈ 8 USD/วัน · ไม่มี Q topic อยู่แล้ว) | ตั้ง role กลับเป็น ADMIN_PRO ใน QuickSight › Manage users |

บันทึกการกระทำ + สถานะก่อนปิด: `_shutdown/actions.json`
Glue job, Step Functions, Lambda ที่ไม่มีใครเรียก **ไม่มีค่าใช้จ่าย** — จึงไม่ต้องลบ

## 10. รายการที่เคยเสียเงิน — ลบครบแล้ว 2 พ.ย. 2026

| ≈ USD/วัน | อะไร | ทางเลือก |
|---|---|---|
| 6.00 | DMS `dms-server-gold` (หยุดไม่ได้ ต้องลบ: ลบ task 7 ตัวก่อน แล้วลบ instance) | ค่าตั้งสำรองครบ → สร้างใหม่ได้ ~15 นาที |
| 2.69 | DMS `test1` (Sydney) | ลบได้เลย |
| 3.61 | QuickSight user 4 คน (Enterprise ×4) | ลบ user ที่ไม่ใช้ · หรือ Unsubscribe ทั้งบัญชี (ไม่มี asset ให้เสีย) — บัญชีชื่อ mis-tan มี user คนอื่น ต้องตกลงกันก่อน |
| 1.20 | NAT Gateway `com7-reconcile-nat` | ลบได้ (เก็บ EIP ไว้ถ้า IP ถูก whitelist) · สร้างใหม่แล้วแก้ route table |
| 1.10 | S3 ~1.75 TB | เก็บ · ย้ายเป็น Glacier Deep Archive (≈ 2 USD/เดือน) · ลบ — หัวหน้าตัดสินใจ |
| 0.48 | Public IPv4 (EIP 2 ตัว + Sydney) | release เมื่อแน่ใจว่าไม่ใช้ IP เดิมแล้ว |
| 0.28 | Interface endpoint (STS + PrivateLink 3+1) | STS ลบได้ · PrivateLink ถามเจ้าของบริการก่อน |
| ~0.5 | CloudWatch custom metrics | ลดเองเมื่อไม่มีงานรัน |
| 0.06 | EBS 20 GB ของ VPN | ลบพร้อม terminate EC2 |
| 0.14 | Secrets 10 ตัว · KMS key 1 ตัว | ลบหลังสุด (secret มีช่วงกู้คืน 7–30 วัน) |
| – | RDS snapshot 5 ตัว · Redshift Serverless 4 workgroup | ลบเมื่อแน่ใจว่าไม่ต้องใช้ข้อมูล |

ก่อนปิด ≈ 27 USD/วัน · หลังปิดรอบนี้ ≈ 15–16 USD/วัน (ถ้าค่า Q หยุดตามคาด — เช็กบิล 1–2 วัน) · ลบ DMS + NAT เพิ่ม ≈ 6 USD/วัน · + QuickSight ≈ 2 USD/วัน · + S3 → เกือบ 0

## 11. ถ้าจะเปิดระบบกลับ (ลำดับ)
1. Start EC2 VPN → รอ WireGuard ต่อติด · (ถ้าลบ NAT ไปแล้ว: สร้างใหม่ใน subnet เดิมด้วย EIP เดิม แล้วแก้ route table ตาม `network.json`)
2. (ถ้าลบ DMS ไปแล้ว) สร้าง replication instance + task จาก `dms/*.json`
3. ลบ concurrency 0 ของ Lambda
4. Enable EventBridge rules → แล้วค่อย Enable schedules (rules ต้องพร้อมก่อน งานคืนแรกถึงจะต่อกันครบ)
5. ap-southeast-1: start Glue trigger + enable rule gsheet-cdc (ถ้าเจ้าของงาน mis-tan ต้องการ)
