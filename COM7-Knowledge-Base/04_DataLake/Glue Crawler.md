# Glue Crawler

> 🗄️ **2026-11-10 — เลิกใช้ AWS แล้ว** (ไม่ผ่าน POC และงบประมาณ) · แพลตฟอร์มใหม่ = เครื่อง PC on-prem + **MySQL** (concept SSOT เดิม) · ระบบใน AWS ปิดและลบแล้ว → [[AWS Data Lake - Backup & Shutdown 2026-10]] · เก็บเป็นประวัติ · บน MySQL ไม่ต้องมี crawler — schema กำหนดตอน CREATE TABLE

> **หมายเหตุที่มา:** บันทึกจากการทำจริงบน bucket `google-sheet-extract` เมื่อ **2026-09-03** — ทุกอาการและ error ที่เขียนไว้เจอเองกับ Crawler และ Redshift Spectrum ของบัญชี `603238661233`

Crawler สแกนไฟล์ใน S3 แล้วสร้างตารางใน **Glue Data Catalog** ซึ่ง [[Athena Benchmark|Athena]] · [[Redshift|Redshift Spectrum]] · Glue Job ใช้ร่วมกันทั้งหมด

---

## หลักการเดียวที่ต้องจำ

> **ตาราง 1 ตาราง = 1 โฟลเดอร์**

```
ตาราง sales/
├── 2026-01.csv    ┐
├── 2026-02.csv    ├── คอลัมน์เหมือนกัน = ต่อกันเป็นตารางเดียว
└── 2026-03.csv    ┘
```

Athena และ Spectrum อ่าน**ทั้งโฟลเดอร์**แล้วเอาไฟล์มาต่อกัน — **โฟลเดอร์คือขอบเขตของตาราง** ไม่ใช่ไฟล์

**ห้ามวางไฟล์คนละชุดข้อมูลไว้ใน prefix เดียวกัน** เพราะ Crawler จะไม่มีขอบเขตให้ใช้

---

## ปัญหาที่เจอจริง — `Parsed manifest is not a valid JSON object`

### อาการ

```
ERROR: Parsed manifest is not a valid JSON object.
code: 15003
context: s3://google-sheet-extract/google-sheet-ev7/leads-ev7-2025.csv
location: spectrum_manifest.cpp:50
```

### สาเหตุ

CSV คนละชุด 3 ไฟล์กองรวมกันใน prefix เดียว

```
s3://google-sheet-extract/google-sheet-ev7/
├── leads-ev7-2025.csv     ← คอลัมน์แบบ A
├── leads-ev7-2026.csv     ← คอลัมน์แบบ B
└── leads-ev7-Query.csv    ← คอลัมน์แบบ C
```

**เมื่อไฟล์ในโฟลเดอร์เดียวกันมี schema ไม่ตรงกัน Crawler จะสร้างตารางแยกรายไฟล์** และตั้ง `LOCATION` เป็นชื่อไฟล์

แล้ว AWS จองความหมายไว้ว่า **`LOCATION` ชี้ไปที่ไฟล์ = ไฟล์นั้นคือ manifest** (ไฟล์ JSON ที่ลิสต์ว่าข้อมูลจริงอยู่ไฟล์ไหน)

```json
{"entries": [
  {"url": "s3://bucket/data/part-001.csv"},
  {"url": "s3://bucket/data/part-002.csv"}
]}
```

Spectrum จึงเปิด CSV ขึ้นมาแล้วพยายาม parse เป็น JSON → ตาย

> **error นี้ไม่ได้แปลว่า CSV เสีย** แต่แปลว่า *"คาดว่าจะเจอ manifest แต่เจอ CSV"* — คือนิยามตารางชี้ผิดที่

### ⚠️ Athena ยอม แต่ Spectrum ไม่ยอม

ตารางที่ `LOCATION` เป็นไฟล์ **Athena มักอ่านได้ตามปกติ** จึงดูเหมือน Crawler ทำงานถูก แล้วมาพังตอนต่อ Redshift

**ทดสอบด้วย Athena อย่างเดียวไม่พอ ถ้าจะใช้ Spectrum ต่อ**

---

## Table level — บอก Crawler ว่าตารางอยู่ชั้นไหน

เป็นแค่การ**นับชั้นจาก bucket** ไม่ใช่เลขวิเศษ — เลขเปลี่ยนตามที่วางโฟลเดอร์

### โครงสร้างที่ผิด

```
s3:// google-sheet-extract / google-sheet-ev7 / leads-ev7-2025.csv
           ชั้น 1                 ชั้น 2              ชั้น 3  ← เป็น "ไฟล์"
```

ตั้ง `Table level = 3` → หยิบได้ **ไฟล์** → พังเหมือนเดิม

### โครงสร้างที่ถูก

```
s3:// google-sheet-extract / google-sheet-ev7 / leads-ev7-2025 / leads-ev7-2025.csv
           ชั้น 1                 ชั้น 2            ชั้น 3  ← เป็น "โฟลเดอร์"
```

ตั้ง `Table level = 3` → หยิบได้ **โฟลเดอร์** → ถูกต้อง

**คำสั่งเหมือนกันเป๊ะ ต่างแค่ชั้น 3 เป็นไฟล์หรือโฟลเดอร์**

### ทำไมไม่ตั้ง level 2

ชั้น 2 (`google-sheet-ev7/`) เป็นโฟลเดอร์จริง ตั้งได้ ไม่ error — แต่จะได้ **ตารางเดียวที่รวมทั้ง 3 ชุดข้อมูล** ที่คอลัมน์ไม่ตรงกัน

**ข้อมูลจะเลื่อนคอลัมน์แบบเงียบ ๆ ซึ่งอันตรายกว่า error** เพราะไม่มีอะไรเตือน

---

## ค่าที่ต้องตั้ง

| ค่า | ตั้งเป็น | เหตุผล |
|---|---|---|
| **S3 path** | `s3://bucket/prefix/` **โฟลเดอร์แม่ ปิดท้ายด้วย `/`** | ใส่ path เดียว ไม่ต้องเพิ่มทีละโฟลเดอร์ย่อย |
| **Table level** | เลขชั้นของโฟลเดอร์ที่เป็นตาราง (เคสนี้ = 3) | นับจาก bucket เป็น 1 |
| **Create a single schema for each S3 path** | ☑ ติ๊ก | กันไม่ให้แตกตารางอีกเมื่อไฟล์ใหม่ schema เพี้ยนนิดหน่อย |
| **Subsequent crawler runs** | Crawl all sub-folders | โหมด incremental **ไม่อัปเดต schema ของตารางเดิม** — อันตรายกับต้นทางที่คอลัมน์เปลี่ยนได้ |
| **Schema change policy** | Update in the database | ให้ schema ตามต้นทางล่าสุด |
| **Object deletion** | Ignore change and don't update | กันไฟล์หายชั่วคราวแล้วตารางโดนลบ |

### ตั้งผ่าน CLI แน่นอนกว่า Console

หน้า Console ของ Glue ย้ายที่บ่อย — `Table level` ซ่อนอยู่ใต้ **Step 4 → Output configuration → Advanced options → Grouping behavior for S3 data**

```bash
aws glue update-crawler \
  --name <crawler-name> \
  --targets '{"S3Targets":[{"Path":"s3://google-sheet-extract/google-sheet-ev7/"}]}' \
  --configuration '{"Version":1.0,"Grouping":{"TableGroupingPolicy":"CombineCompatibleSchemas","TableLevelConfiguration":3}}'

aws glue get-crawler --name <crawler-name> --query 'Crawler.Configuration' --output text
```

`TableGroupingPolicy: CombineCompatibleSchemas` = checkbox "Create a single schema for each S3 path"

---

## ลำดับการแก้ที่ถูกต้อง

**ย้ายไฟล์ → ลบตารางเก่า → ค่อย crawl**

ที่เสียเวลาไปหลายรอบเพราะแก้ที่ Glue ก่อนโดยที่ไฟล์ยังกองรวมกันอยู่ — **Table level ไม่ได้สร้างโฟลเดอร์ให้ มันแค่บอกว่าจะหยิบชั้นไหน**

### 1 · ย้ายไฟล์เข้าโฟลเดอร์ของตัวเอง

```bash
BUCKET=google-sheet-extract
PREFIX=google-sheet-ev7

aws s3 ls s3://$BUCKET/$PREFIX/ | awk '{print $4}' | grep '\.csv$' | while read f; do
  aws s3 cp "s3://$BUCKET/$PREFIX/$f" "s3://$BUCKET/$PREFIX/${f%.csv}/$f"
done
```

### 2 · ตรวจว่าครบก่อนลบ

```bash
aws s3 ls s3://$BUCKET/$PREFIX/ --recursive
```

### 3 · ลบต้นฉบับที่วางแบน ๆ

```bash
aws s3 ls s3://$BUCKET/$PREFIX/ | awk '{print $4}' | grep '\.csv$' | while read f; do
  aws s3 rm "s3://$BUCKET/$PREFIX/$f"
done
```

> **ใช้ `cp` แล้วค่อย `rm` ไม่ใช้ `mv`** — ถ้าพลาดกลางทางยังมีต้นฉบับให้กลับไป ไฟล์พวกนี้เป็นสำเนาเดียวที่มี

### 4 · ลบตารางเก่าใน Glue

Glue Console → Tables → เลือกตารางที่ `location` ลงท้าย `.csv` → Delete

**ข้ามไม่ได้** — ถ้าไม่ลบ Crawler จะไป *update* ของเดิมที่ location ผิด ไม่สร้างใหม่

### 5 · Run crawler แล้วเช็ค

```sql
SELECT tablename, location
FROM SVV_EXTERNAL_TABLES
WHERE schemaname = 'glue_schema';
```

```bash
aws glue get-tables --database-name default \
  --query 'TableList[].{name:Name,loc:StorageDescriptor.Location}' --output table
```

**`location` ต้องลงท้ายด้วย `/` ไม่ใช่ `.csv`**

---

## โครงสร้าง S3 ที่ควรใช้

```
s3://bucket/<โดเมน>/<ชุดข้อมูล>/<partition>/<ไฟล์>

s3://google-sheet-extract/google-sheet-ev7/leads/year=2026/leads.csv
                              │              │       │
                           โดเมน          ตาราง   partition
```

`year=2026` เขียนแบบนี้ Athena/Spectrum จะรู้จักเป็น **partition อัตโนมัติ** และ `WHERE year = 2026` จะตัดข้อมูลที่ scan ทิ้ง — [[Athena Benchmark]] วัดได้ว่าลด scan **94%**

> ต้องแก้ที่ต้นทางด้วย ไม่งั้นไฟล์ใหม่จะไปกองที่เดิมทุกเดือน → [[Google Sheet to S3 (Lambda)]] `S3_KEY`

---

## กับดักอื่นของ CSV

| กับดัก | อาการ | แก้ |
|---|---|---|
| **ไม่มี `skip.header.line.count`** | แถวหัวตารางกลายเป็นข้อมูล เช่น `lead_id = "lead_id"` | ตั้ง table property `skip.header.line.count = 1` |
| **BOM จาก `utf-8-sig`** | `﻿` ติดหน้าค่าแรกของแถวแรก | หายไปเองถ้า skip header |
| **Crawler เดา type ผิด** | วันที่กลายเป็น `string` · เลขขึ้นต้นด้วย 0 ถูกตัด | เขียน DDL เองแล้วตั้ง schema policy เป็น `LOG` ให้ Crawler ทำแค่เพิ่ม partition |

**Parquet ไม่มีปัญหาชุดนี้เลย** — มี schema และ type อยู่ในไฟล์ Crawler ไม่ต้องเดา จึงไม่แตกตารางมั่วและไม่มีเรื่อง header

---

## เชื่อมกับโน้ตอื่น

[[Redshift]] · [[Athena Benchmark]] · [[AWS Services]] · [[Architecture]] · [[ETL & Spark]] · [[Google Sheet to S3 (Lambda)]] · [[Data Standardization & Quality]] · [[Pipeline Issues]]
