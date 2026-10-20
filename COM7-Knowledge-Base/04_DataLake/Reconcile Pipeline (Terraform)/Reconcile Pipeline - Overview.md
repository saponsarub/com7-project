# Reconcile Pipeline - Overview

> **เริ่มอ่านที่นี่** — pipeline ที่ทำให้ตาราง Iceberg บน S3 **ตรงกับ SQL Server ต้นทางเสมอ** โดยไม่ต้องมี CDC
> ทำเป็น Terraform module พกไปลงบัญชีไหนก็ได้ · ทดลองครบวงจรใน sandbox เมื่อ 2026-10-05 แล้ว destroy หมด

ที่มา: `D:\aws-workshop\` (ไม่ได้อยู่ใน repo นี้)
- `reconcile-pipeline-terraform-portable-v1.0.0/` — Terraform หลัก (bundle v1.0.0)
- `source-simulator.yaml` — CloudFormation สร้าง SQL Server ต้นทางจำลอง (ไฟล์เดียวกับ `Downloads\source-simulator\` และใน bundle)
- `.agents/tasks/pipeline-iud-test-report.md` — รายงานทดสอบ INSERT/UPDATE/DELETE

---

## ชุดโน้ต

| อยากรู้                                                      | เปิด                                            |
| ------------------------------------------------------------ | ----------------------------------------------- |
| **ค่า / arg / ตัวแปรแต่ละตัวมาจากไหน · sys.argv เก็บที่ไหน** | [[Reconcile Pipeline - Arguments & Variables]]  |
| SQL Server จำลองสร้างยังไง (CloudFormation)                  | [[Reconcile Pipeline - Source Simulator]]       |
| Terraform แต่ละไฟล์สร้างอะไร                                 | [[Reconcile Pipeline - Terraform Modules]]      |
| Glue job เทียบ/ซ่อมข้อมูลยังไง (code)                        | [[Reconcile Pipeline - Glue Jobs]]              |
| Step Functions · ประเภทความล้มเหลว · alert                   | [[Reconcile Pipeline - Orchestration & Alerts]] |
| deploy / ทดสอบ / ลบ ทีละคำสั่ง + ปัญหาที่เจอ                 | [[Reconcile Pipeline - Runbook]]                |

---

## ทำไมต้องมี

ต้นทาง SQL Server **ไม่เปิด CDC และไม่ให้อ่าน transaction log** (เหตุผลเดียวกับ [[Decisions]] D-20 · [[Snapshot Change Detection (ITEC DMS)]])
→ ทำ "CDC ฝั่งปลายทาง" แทน: **เทียบสถานะสองฝั่งแล้ว MERGE เฉพาะส่วนต่าง** · ต้นทางโดนแค่ `SELECT`

ต่างจาก [[Snapshot Change Detection (ITEC DMS)]] ตรงที่ตัวนี้**ไม่ย้าย full snapshot ทุกรอบ** — อ่านเฉพาะ slice ที่เปลี่ยน (watermark) + นับแยกกลุ่มเพื่อหาแถวที่ถูกลบ

README เขียนว่า "It is the platform already running for COM7, parameterised" — คือ pipeline ที่รันจริงของ COM7 เอามาทำเป็นพารามิเตอร์ **แต่ module ไม่ได้ import ของจริง** (ของจริงสร้างด้วยมือ) ตาราง production ที่อ้างถึงมี 6 ตาราง (ไฟล์ `examples/com7-sales.tfvars` ที่ README อ้างถึง **ไม่มีอยู่ใน bundle**)

---

## ภาพรวม

```
┌─ CloudFormation (source-simulator.yaml) ─┐      ┌─ Terraform ─────────────────────────────────────────────┐
│ EC2 + Docker SQL Server 2022 Developer   │      │ EventBridge Scheduler ─► Step Functions                  │
│ DB ReconcileWorkshop                     │◄─JDBC┤    ─► Glue reconcile (ใน VPC, private subnet)           │
│ workshop.orders_reconcile_lab (6 แถว)    │ 1433 │         ─► S3 data: iceberg/ + _control/                │
│ Secret mssql-admin / mssql-source        │      │    ─► Glue maintenance (นอก VPC)                         │
│ SSM /<project>/source-ready = READY      │      │    ─► ล้ม → SNS email · CloudWatch alarm 2 ตัว           │
└──────────────────────────────────────────┘      │ Athena workgroup (readonly, cap 10 GB/query)            │
   สร้างก่อน · ลบทีหลัง                             └─────────────────────────────────────────────────────────┘
                                                     สร้างทีหลัง · **ลบก่อน**
```

### ของที่ Terraform สร้าง (~45 resource ใน managed-network mode)

| กลุ่ม | resource |
|---|---|
| Storage | S3 `data` (versioning) + `artifacts` · encryption · block public · lifecycle |
| Catalog | Glue database · Glue JDBC connection |
| Compute | Glue job `<project>-generic` (reconcile) · `<project>-iceberg-maintenance` |
| Orchestration | Step Functions `<project>-pipeline` · Scheduler `nightly` + `weekly-deep` |
| Alerting | SNS `<project>-alerts` + email · alarm `execution-failed` · `no-success-26h` |
| Identity | IAM role 3 ตัว (glue / sfn / scheduler) |
| Network (optional) | private subnet · route table · NAT + EIP · S3 gateway endpoint · Glue SG · ingress rule บน SG ต้นทาง |
| Secret | อ่าน secret เดิม (data source) **หรือ** สร้าง placeholder |
| Optional | Athena workgroup |

---

## รอบการทำงาน

| รอบ | เวลา (Asia/Bangkok) | input | ทำอะไร |
|---|---|---|---|
| nightly | 23:30 จันทร์–เสาร์ | `deepVerify=false, deepRepair=false` | อ่าน slice ที่ `UpdatedAt >= watermark − 2 วัน` → INSERT/UPDATE · count ไม่ตรง → หาแถวถูกลบเฉพาะกลุ่มที่ไม่ตรง |
| weekly deep | 23:30 อาทิตย์ | `deepVerify=true, deepRepair=true` | + เทียบ hash ทุกแถวรายกลุ่ม → ซ่อมแถวที่ค่าเพี้ยน / หายไป / เกินมา |

ตรงกับ [[Decisions]] D-16 (ETL 23:30) · ทุก run เขียน `_SUMMARY.json` = reconciliation log ตาม D-15

**ทำไมต้องมีรอบ deep** — แถวที่ถูกแก้โดย `UpdatedAt` ไม่ขยับ จะไม่เข้า slice ของรอบปกติ และจำนวนแถวก็เท่าเดิม → **รอบปกติมองไม่เห็นตลอดไป** · เคยเกิดจริงใน production 2026-09-25 (ต้นทาง restore ประวัติ 1 เดือนโดยไม่ขยับ watermark — ตาม README)

---

## ผลทดสอบ sandbox 2026-10-05 (us-east-1)

ตาราง `fact_orders` · Glue 5.0 G.2X × 10 · ทั้ง 7 เคส **PASS** · แต่ละรอบ 4–7 นาที

| เคส | ผล |
|---|---|
| baseline | 6 แถวตรง |
| insert 2001/1 | เข้า · count 7 |
| update 1001/1 | ค่าใหม่เข้า |
| delete 1002/1 | หาย · มีแถวใน `reconcile_delete_audit` พร้อม `row_before_json` |
| stale (แก้ Note ไม่ขยับ UpdatedAt) + รอบปกติ | **ไม่เจอ (ตามคาด)** |
| รอบ deep | เจอและซ่อม |
| reset + deep | กลับ baseline · 2001/1 ถูกลบผ่าน `deep_repair_delete` |

หลังทดสอบ destroy หมดแล้ว — ตรวจ (read-only) 2026-10-06: ไม่เหลือ stack / EC2 / NAT / EIP / Glue job ใน region นั้น · tfstate เหลือ 0 resource

---

## สิ่งที่ต้องจำ (สรุปจากทุกโน้ต)

1. **ลำดับลบ: destroy pipeline ก่อน แล้วค่อยลบ stack ต้นทาง** — pipeline เป็นเจ้าของ ingress rule บน SG ต้นทาง และอ่าน secret ของ stack ต้นทาง · รอบทดสอบลบสลับ → destroy พัง ต้องเคลียร์ด้วยมือ → [[Reconcile Pipeline - Runbook]]
2. **รหัสผ่านไม่เคยอยู่ใน tfvars / argv** — มีแค่**ชื่อ** secret · ค่าอยู่ใน Secrets Manager → [[Reconcile Pipeline - Arguments & Variables]]
3. **Glue job ตั้งต้นเป็น `--MODE verify` (dry run)** — กด Run ใน console จะไม่เขียนข้อมูล · ต้องส่ง `--MODE reconcile` เอง
4. **schedule ปิดไว้ก่อนเสมอ** — เปิดใน apply รอบที่สองหลัง smoke test + ยืนยันอีเมล SNS
5. **`column_map` เป็น list ไม่ใช่ map** — map จะโดนเรียงตามตัวอักษร ทำให้ลำดับคอลัมน์ปลายทางเพี้ยน
6. **ตารางเล็กไม่ควรมี watermark** — full compare ทุกคืนถูกกว่าและปิดจุดบอด
7. **bootstrap รันตอน `terraform apply`** — เครื่องที่รันต้องมี `python3` + AWS CLI v2 ใน PATH (Windows เคยพัง 2 รอบ)
8. NAT Gateway + public IPv4 **คิดเงินตลอดเวลาที่มีอยู่** — sandbox ใช้เสร็จต้อง destroy

## ข้อจำกัด

- SQL Server เท่านั้น · 1 source DB ต่อ 1 deployment (อีก DB = อีก `project` / อีก state)
- ไม่ import resource COM7 ที่มีอยู่ — ถ้าจะให้ Terraform ดูแลของจริงต้องทำ import แยก
- `enforce_ssl` มีผลกับ Glue Connection เท่านั้น — job สร้าง JDBC URL เองแบบ `encrypt=false` `[อนุมาน จากการอ่าน code — ยังไม่ทดสอบ]` → [[Reconcile Pipeline - Glue Jobs]]

---

## เชื่อมกับโน้ตอื่น

- [[Architecture]] · [[AWS Services]] · [[Network & VPN]] · [[Glue Connectivity]]
- [[ETL & Spark]] · [[Snapshot Change Detection (ITEC DMS)]] · [[Decisions]]
