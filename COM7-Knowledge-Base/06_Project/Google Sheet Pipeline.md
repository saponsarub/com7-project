# Google Sheet Pipeline

> **หมายเหตุที่มา:** แผนและสถาปัตยกรรมของ pipeline ดึงข้อมูลจาก Google Sheet เข้า lake · เขียน **2026-09-03** จากการทำจริงของ Phase 1
>
> ส่วนที่ยังไม่ได้ลงมือกำกับ `[อนุมาน]` และเป็นข้อเสนอ ยังไม่ผ่านการตกลงกับทีม

**เนื้อหาโค้ดและการแพ็กเกจ** → [[Google Sheet to S3 (Lambda)]] · [[Google Sheet to S3 - Code Walkthrough]]

---

## เป้าหมาย

ชีตที่ทีม EV7 คีย์มือ **7 tab** ต้องเข้ามาอยู่ใน lake ให้ Athena/Glue อ่านต่อได้ โดยไม่ต้องมีคนมา export เอง

| | |
|---|---|
| ต้นทาง | Google Sheet · Spreadsheet ID `1ZuZvelevthX1O0bcaWaWfMuh16zteZkbYim8OPgPwn4` |
| tab | `Query` · `2025` · `2026` · `Check` · `Filter` · `Event` · `Compare by puii` |
| ปลายทาง | `s3://google-sheet-extract/google-sheet-ev7/` |
| รอบ | ทุกวัน 23:00 น. (ก่อน Glue job รอบ 23:30 ที่ทีมตกลง → [[ETL & Spark]]) |

---

## Flow ปัจจุบัน — Phase 1

```
Google Sheet (7 tab)
      │
      │  EventBridge Scheduler  cron(0 23 * * ? *)  Asia/Bangkok
      ▼
┌──────────────────────────────────────────────┐
│  Lambda: test-ingest-googlesheet             │
│                                              │
│  1. Secrets Manager  → service account JSON  │
│  2. เซ็น JWT ครั้งเดียว → access token        │
│  3. วน 7 tab                                 │
│       ├─ Sheets API                          │
│       ├─ เขียน CSV ลง /tmp                    │
│       └─ upload_file → S3                    │
│  4. สรุปผล ok / failed                       │
└──────────────────┬───────────────────────────┘
                   ▼
┌─ BRONZE ─────────────────────────────────────┐
│  google-sheet-ev7/ev7_query/data.csv          │
│  google-sheet-ev7/ev7_2025/data.csv           │
│  google-sheet-ev7/ev7_2026/data.csv           │
│  ... (7 โฟลเดอร์)                             │
│                                               │
│  CSV ดิบ · เขียนทับทุกวัน · ห้ามแก้ด้วยมือ      │
└──────────────────┬───────────────────────────┘
                   │  Glue Crawler (Table level 3)
                   ▼
            Glue Data Catalog  →  Athena / Redshift Spectrum
```

**หนึ่ง tab = หนึ่งโฟลเดอร์ = หนึ่งตาราง** — เหตุผลอยู่ที่ [[Glue Crawler]] · [[Python Libraries]]

---

## Flow ปลายทาง

```
Google Sheet ─► BRONZE (CSV) ─► SILVER (Iceberg) ─► GOLD ─► BI / Athena
                ทับทุกวัน         สะอาด · type ถูก      มาร์ท
                ห้ามแก้           สร้างจากกฎ
```

| ชั้น | Format | แก้ได้ไหม |
|---|---|---|
| **Bronze** | CSV ตามต้นทาง | **ห้ามแก้ด้วยมือเด็ดขาด** — ต้องเป็นภาพสะท้อนต้นทางเป๊ะ ๆ |
| **Silver** | Iceberg | แก้ผ่าน**กฎใน ETL** เท่านั้น · `UPDATE`/`MERGE` ได้ |
| **Gold** | Parquet หรือตารางใน Redshift | สร้างใหม่จาก Silver ได้ตลอด |

### ทำไม Bronze ห้ามแก้

**Bronze คือของที่ลบทิ้งแล้วสร้างใหม่ได้เสมอ** ถ้าแก้ด้วยมือจะสร้างใหม่ไม่ได้อีก และเทียบกับต้นทางไม่ได้

**ตารางที่ Crawler สร้างใช้ `UPDATE` / `DELETE` ไม่ได้อยู่แล้ว** — external table บน CSV เป็น read-only โดยธรรมชาติ ไม่ใช่แค่เพราะข้อมูลถูกทับ

| Engine | ตาราง | `SELECT` | `UPDATE` / `DELETE` |
|---|---|---|---|
| Athena | External CSV (Hive) | ✅ | ❌ |
| **Athena** | **Iceberg** | ✅ | **✅** |
| Redshift Spectrum | External | ✅ | ❌ |
| Redshift | ตารางในตัว | ✅ | ✅ |

### อยากแก้ข้อมูล ทำที่ไหน

| สถานการณ์ | ทำ |
|---|---|
| คนคีย์ผิด | **แก้ในชีต** วันรุ่งขึ้นถูกเอง |
| ผิดซ้ำ ๆ เป็นแบบแผน | เขียน**กฎใน Bronze→Silver** |
| ต้องติ๊กสถานะรายแถว | ทำ Silver เป็น **Iceberg** แล้ว `UPDATE` |

---

## แผนเป็น Phase

### Phase 1 · Bronze

| งาน | สถานะ |
|---|---|
| Lambda ดึง 7 tab เขียนแยกโฟลเดอร์ | **เสร็จ · Test ผ่าน 2026-09-03** |
| แก้ปัญหา packaging (manylinux wheel) | เสร็จ → [[Google Sheet to S3 (Lambda)]] |
| IAM policy (Secrets Manager + S3 + SNS) | เสร็จ |
| รายงานผลเข้าอีเมลผ่าน SNS | **เสร็จ** |
| จัดโครงสร้าง S3 หนึ่งโฟลเดอร์หนึ่งตาราง | เสร็จ — เหลือล้างโฟลเดอร์เก่า |
| EventBridge Scheduler | ยังไม่ทำ |
| Glue Crawler ได้ 7 ตาราง | ยังไม่ทำ |

#### ผลการรันจริง 2026-09-03

| tab | ตาราง | แถว | ขนาด |
|---|---|---:|---:|
| Query | `ev7_query` | 17,225 | 38.9 MiB |
| 2026 | `ev7_2026` | 11,640 | 27.8 MiB |
| Compare by puii | `ev7_compare_by_puii` | 5,182 | 1.3 MiB |
| 2025 | `ev7_2025` | 4,337 | 10.3 MiB |
| Filter | `ev7_filter` | 2,419 | 701.3 KiB |
| Event | `ev7_event` | 1,558 | 401.6 KiB |
| Check | `ev7_check` | 11 | 110 B |
| **รวม** | | **42,372** | **79.4 MiB** |

| | |
|---|---|
| เวลาที่ใช้ | **16.3 วินาที** (timeout ตั้งไว้ 5 นาที) |
| Memory ที่ใช้จริง | **432 MB** (ตั้งไว้ 2048 MB) |
| ขนาดแถวเฉลี่ย | ~2.4 KB — **แถวกว้างมาก** |

**ทุก tab มีข้อมูลจริงหมด** — รวมถึง `Check` `Filter` `Event` `Compare by puii` ที่เดาไว้ว่าอาจเป็นช่องช่วยคำนวณ ต้องเปิดดูใน Phase 2 ว่าควรเข้า lake หรือไม่

#### บทเรียนเรื่อง memory

```
10240 MB -> 16.5 วินาที
 2048 MB -> 16.3 วินาที     เร็วเท่ากัน จ่ายน้อยลง 5 เท่า
```

**งานนี้ช้าเพราะรอ Google API ไม่ใช่เพราะ CPU** — เพิ่ม memory ไม่ช่วยอะไร `[วัดจริง]`

ใช้ `/tmp` ทำให้ peak memory อยู่แค่ 432 MB ทั้งที่ข้อมูลรวม 79 MB และไฟล์ใหญ่สุด 38.9 MB

**เกณฑ์ว่า Phase 1 จบ** — Lambda รันเองทุกวัน · Athena query ได้ทั้ง 7 ตาราง · มีคนรู้เมื่อ job พัง

### Phase 2 · สำรวจข้อมูล

**อย่าข้ามไปทำ Silver เลย** — ยังไม่รู้ว่าใน 7 tab มีคอลัมน์อะไร อันไหนใช้จริง อันไหนเป็นช่องช่วยคำนวณ

```sql
SELECT * FROM ev7_query LIMIT 20;
SELECT count(*) FROM ev7_query;
```

**ออกแบบ Silver โดยไม่เคยเห็นข้อมูลคือการเดา** `[อนุมาน]`

ผลที่ต้องได้: รู้ว่า tab ไหนควรเข้า lake จริง · คอลัมน์ไหนคือ key · มี PII ไหม

### Phase 3 · Silver

```sql
CREATE TABLE silver.ev7_leads
WITH (table_type = 'ICEBERG',
      location   = 's3://google-sheet-extract/silver/ev7_leads/',
      format     = 'PARQUET')
AS SELECT
    TRIM(lead_id)                  AS lead_id,
    TRIM(customer_name)            AS customer_name,
    NULLIF(TRIM(phone), '')        AS phone,
    TRY_CAST(created_date AS date) AS created_date,
    CURRENT_TIMESTAMP              AS _loaded_at
FROM bronze.ev7_query
WHERE lead_id IS NOT NULL;
```

รอบถัดไปใช้ `INSERT OVERWRITE` — **รันซ้ำกี่ครั้งผลเหมือนเดิม และถ้าพังกลางทางตารางเดิมยังอยู่ครบ**

**ใช้ Athena ไม่ใช้ Glue Spark** — ข้อมูลไม่กี่ MB เอา Spark มาใช้คือยกทัพมาแล้วไม่มีอะไรให้ทำ `[อนุมาน]`

**Iceberg ต้องบำรุงรักษา** — ตั้ง `OPTIMIZE` + `VACUUM` สัปดาห์ละครั้ง ไม่งั้นไฟล์พอกขึ้นเรื่อย ๆ

### Phase 4 · ต่อกันเป็นเส้นเดียว

พอมี Silver จะกลายเป็น **3 ขั้นที่พึ่งกัน** — ตอนนั้นค่อยย้ายมา Step Functions

```
EventBridge (1 อัน) ──► Step Functions
                          ├─ Lambda        (รอเสร็จ)
                          ├─ Glue Crawler  (รอเสร็จ)
                          └─ Athena INSERT OVERWRITE  (รอเสร็จ)
```

**EventBridge มีหน้าที่เดียวคือ "เริ่มงาน" ไม่ใช่ "จัดลำดับงาน"**

ย้ายทีหลังไม่ต้องแก้โค้ด Lambda เลย — แค่เปลี่ยน target ของ schedule เดิม

```bash
aws scheduler update-schedule --name ingest-googlesheet-daily \
  --schedule-expression 'cron(0 23 * * ? *)' \
  --schedule-expression-timezone 'Asia/Bangkok' \
  --flexible-time-window '{"Mode":"OFF"}' \
  --target '{"Arn":"arn:aws:states:ap-southeast-7:603238661233:stateMachine:googlesheet-pipeline","RoleArn":"..."}'
```

---

## ⚠️ ทำไมไม่นัดเวลาหลายอัน

```
❌  EventBridge 23:00 → Lambda
    EventBridge 23:15 → Crawler
    EventBridge 23:30 → Athena
```

**ถ้า Lambda พังตอน 23:00 — Crawler กับ Athena ยังรันอยู่ดี** แล้วสร้าง Silver จากข้อมูลเมื่อวานโดยไม่มีอะไรเตือน

**อันตรายกว่า pipeline พังไปเลย** เพราะรายงานยังออกมาหน้าตาปกติ

และเวลาเป็นการเดา — วันไหนชีตใหญ่ขึ้นจน Lambda ใช้ 20 นาที Crawler จะไปอ่านไฟล์ที่เขียนยังไม่เสร็จ

---

## เกณฑ์ตัดสินว่าเมื่อไหร่ควรเพิ่มอะไร

**เพิ่ม service เมื่อเจอปัญหาจริง ไม่ใช่เพิ่มเผื่อไว้** — ทุกตัวที่เพิ่มคือของที่ต้องตั้งค่า ให้สิทธิ์ ดูแล และเป็นอีกจุดที่พังได้

| เพิ่มเมื่อ | ใช้ | ตอนนี้ |
|---|---|---|
| งานขั้นเดียว | EventBridge + Lambda | ✅ **ใช้อยู่** |
| แจ้งเตือนตอนพัง | CloudWatch Alarm + SNS | ✅ ควรมี |
| กัน schedule ไม่ทำงานเงียบ ๆ | SQS เป็น **DLQ** (1 queue ไม่ต้องเขียนโค้ด) | ✅ ควรมี |
| **หลายขั้นที่ขั้นหลังต้องรอขั้นก่อนสำเร็จจริง** | **Step Functions** | ⬜ Phase 4 |
| ต้อง `UPDATE` รายแถว · สร้างตารางทับทุกวัน | **Iceberg** | ⬜ Phase 3 |
| ข้อมูลใหญ่เกิน Lambda (15 นาที / 10 GB) | Fargate หรือ Glue Spark | ⬜ ไม่น่าถึง |
| query ถี่ ๆ · dashboard ประจำ | Redshift | ⬜ → [[Redshift]] |
| งานเยอะจนต้องมีหลาย worker ช่วยกัน | SQS เป็นคิวจริง | ⬜ ไม่จำเป็น |

**SQS ไม่ต้องใช้เป็นคิว** — วันละครั้ง 7 tab ทำเรียงกันจบใน 1-2 นาที ไม่มีอะไรค้างคิว

**แตก 7 tab ให้ทำขนานกันไม่คุ้ม** — จะต้องเซ็น JWT 7 ครั้งแทนที่จะเป็นครั้งเดียว และ cold start 7 ตัว แลกกับเวลาที่ประหยัดได้ไม่กี่สิบวินาที

---

## พฤติกรรมข้อมูล

**เขียนทับทุกวัน ไม่ต่อเติม** — `upload_file` ไปที่ key เดิม = แทนที่ทั้ง object

| | |
|---|---|
| ✅ ข้อมูลตรงกับชีตเสมอ | ลบแถวในชีต แถวนั้นหายจาก S3 ด้วย |
| ❌ ไม่มีประวัติย้อนหลัง | อยากรู้ว่าเมื่อวานมีกี่ราย — ดูไม่ได้ |
| ❌ ชีตพัง ข้อมูลดีหายตาม | เช่นมีคนเผลอลบทั้ง tab |

**ทางแก้ที่ถูกที่สุด — เปิด S3 Versioning** ไม่ต้องแก้โค้ดเลย

```bash
aws s3api put-bucket-versioning --bucket google-sheet-extract \
  --versioning-configuration Status=Enabled
```

Crawler ยังเห็นแค่เวอร์ชันล่าสุด จึงไม่กระทบตาราง — ควรตั้ง lifecycle rule ลบเวอร์ชันเก่าเกิน 90 วันด้วย

### Crawler ต้องรันเมื่อไหร่

**Crawler เก็บแค่ schema + location ไม่ได้เก็บข้อมูล**

| เปลี่ยนอะไร | ต้อง crawl ใหม่ |
|---|---|
| ข้อมูลในไฟล์เปลี่ยน (ทับทุกวัน) | **ไม่ต้อง** — Athena อ่านไฟล์สดทุกครั้ง |
| **คอลัมน์ในชีตเปลี่ยน** | **ต้อง** — ไม่งั้นข้อมูลเลื่อนคอลัมน์เงียบ ๆ |
| เพิ่ม tab ใหม่ | ต้อง |

**แต่ควรตั้งให้รันอยู่ดี** เพราะ Google Sheet เป็นต้นทางที่คนแก้คอลัมน์ได้ตลอดโดยไม่บอกใคร → [[Data Standardization & Quality]] · ค่าใช้จ่าย ~$0.07/ครั้ง ≈ $2/เดือน

---

## ความเสี่ยง

| ความเสี่ยง | ผล | กันยังไง |
|---|---|---|
| **คนแก้คอลัมน์ในชีต** | ข้อมูลเลื่อนคอลัมน์แบบไม่มี error | crawl ทุกวัน + ตรวจ schema เป็นระยะ |
| **ชีตเป็น PII หรือเปล่ายังไม่ยืนยัน** | อาจต้องเข้ากติกา PDPA | ดูข้อมูลจริงใน Phase 2 → [[Consent & PDPA]] |
| job ไม่รันเงียบ ๆ | ข้อมูลค้างเก่าโดยไม่มีใครรู้ | DLQ + CloudWatch Alarm |
| service account key หลุด | อ่านชีตได้ | ใช้ scope `.readonly` แล้ว · เก็บใน Secrets Manager แล้ว |
| Google เปลี่ยน API | pipeline พัง | มี log บอกสาเหตุจาก Google แล้ว |

---

## ค่าใช้จ่ายประมาณการ

| Service | ต่อเดือน |
|---|---|
| Lambda (วันละครั้ง 1-2 นาที) | อยู่ใน free tier |
| S3 (ไม่กี่ MB) | หลักสตางค์ |
| EventBridge Scheduler | ฟรี |
| Glue Crawler (วันละครั้ง) | ~$2 |
| Athena (query ตอนสำรวจ) | $5/TB scan — ของเล็ก ≈ ฟรี |
| Step Functions (Phase 4) | ~180 transitions → **ฟรี** |

**ทั้ง pipeline น่าจะไม่ถึง $5/เดือน** `[อนุมาน]` — เทียบกับ Redshift cluster ทดสอบที่ลืมปิดแล้วเสีย $115 ใน 1.5 วัน → [[Redshift]]

---

## งานค้างและสิ่งที่ต้องตัดสินใจ

→ [[Pipeline Issues]]

---

## เชื่อมกับโน้ตอื่น

[[Google Sheet to S3 (Lambda)]] · [[Google Sheet to S3 - Code Walkthrough]] · [[Glue Crawler]] · [[Redshift]] · [[Athena Benchmark]] · [[ETL & Spark]] · [[Architecture]] · [[AWS Services]] · [[Data Standardization & Quality]] · [[Consent & PDPA]] · [[GI + EV7 to 7Club]] · [[Pipeline Issues]]
