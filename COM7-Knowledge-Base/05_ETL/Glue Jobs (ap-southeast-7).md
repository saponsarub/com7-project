# Glue Jobs (ap-southeast-7)

สำรวจ Glue job ทั้งหมดในบัญชี `603238661233` region **ap-southeast-7** เมื่อ 2026-10-08 (อ่านอย่างเดียว ผ่าน AWS CLI)
มี 20 job · **ตัด notebook 3 ตัวและ job ที่ชื่อมี `test` 2 ตัว → เหลือ 15 job** · สคริปต์ดาวน์โหลดจาก S3 ตาม `ScriptLocation` ของแต่ละ job
ข้อสันนิษฐานติด `[อนุมาน]`

---

## ภาพรวม: มี 2 เส้นทางที่ทำข้อมูลชุดเดียวกัน (ยอดขาย ITEC)

```
                       ┌──────────── เส้นทาง A: DMS full load → Gold (ใช้งานจริง · BI อ่านจากนี่) ────────────┐
23:30  Scheduler com7-dms-fullload-combined-nightly ─► DMS task (reload-target) ─► s3://com7data-bronze-…/dms/
                       │   dim/item_itec · dim/branch_itec · rpt/fact_sales_itec   (Parquet)
~23:44  DMS เสร็จ ─► EventBridge rule com7-dms-combined-loaded ─► Step Functions com7-dms-ingestion-pipeline
                       │   Wait 60s → Lambda com7-dms-validate → dataset = "all"
                       │   ┌ Parallel ┬ etl-bronze-to-silver-itec-item ─► etl-silver-to-gold-dim-item
                       │   │          └ etl-dms-dim-branch-to-gold
                       │   └─► etl-dms-fact-sales-to-gold ─► com7_gold.fact_sales_enriched
                       │   ─► EventBridge (com7.data.pipeline) ─► SNS com7-data-pipeline-alerts
                       └──────────────────────────────────────────────────────────────────────────────────────┘
                       ┌──────────── เส้นทาง B: Reconcile (JDBC ตรง · MERGE เฉพาะส่วนต่าง) ──────────────────┐
23:30  Scheduler com7-reconcile-nightly (จ.–ส.) / com7-reconcile-weekly-deep (อา.)
        ─► Step Functions com7-reconcile-pipeline ─► com7-reconcile-generic (ทีละตาราง) ─► com7-iceberg-maintenance
        ─► com7_reconcile.{fact_sales_itec, dim_item_itec, dim_branch_itec} ใน s3://com7data-fact-sales-itec-…/
                       └──────────────────────────────────────────────────────────────────────────────────────┘
```
- **ไม่มี Glue trigger / workflow เลย** — ทุกอย่างสั่งด้วย EventBridge Scheduler + Step Functions
- เส้นทาง B คือ reconcile pipeline ตัวเดียวกับ [[Reconcile Pipeline - Overview]] (ตัวใน workshop เป็นรุ่น Terraform ของตัวนี้)
- **ทั้งสองเส้นทางเริ่ม 23:30 พร้อมกัน และอ่าน SQL Server ตัวเดียวกัน** (DMS full load + JDBC 64 slice)

## รายการ job (15)

| Job | สถานะ (30 run ล่าสุด) | อ่านจาก → เขียนลง | หน้าที่ |
|---|---|---|---|
| **etl-bronze-to-silver-itec-item** | ✅ ทุกคืน · ล่าสุด 10-07 | bronze `dms/dim/item_itec/` → `com7_silver.itec_item` | ตั้งชื่อคอลัมน์ (รองรับหลายชื่อ) · trim · `'NULL'`→null · จัดประเภท `item_id` (BARCODE / DEMO `D7` / FA / SERVICE / BUNDLE …) · ธง demo/service/promo · dedupe ต่อ `item_id` |
| **etl-silver-to-gold-dim-item** | ✅ ทุกคืน | silver `itec_item` → `com7_gold.dim_item` | map แบรนด์ (~40 แบรนด์ → `brand`, `brand_group`) · หมวด L1 `department` / L2 `category` · **เก็บทุก key** (เคยกรองแล้วทำให้ยอดขาย 10.48% ไม่มีชื่อสินค้า) · ตรวจว่า `item_id` ไม่ซ้ำ ไม่งั้น fail |
| **etl-dms-dim-branch-to-gold** | ✅ ทุกคืน | bronze `dms/dim/branch_itec/` → `com7_gold.dim_branch` | `BranchType` → `channel` · รวม "กรุงเทพฯ/กรุงเทพ/กรุงเทพมหานคร" → `Bangkok` · dedupe ต่อ `branch_id` · fail ถ้าชื่อสาขาว่างทั้งหมด |
| **etl-dms-fact-sales-to-gold** | ✅ ทุกคืน | bronze `dms/rpt/fact_sales_itec/` + gold dim_item + dim_branch → `com7_gold.fact_sales_enriched` | เปลี่ยนชื่อคอลัมน์ · ปี/เดือน/สิ้นเดือน · `margin_amt` / `margin_pct` (ยอดขาย 0 และต้นทุน 0 = 0%) · ธง `is_return` `is_zero_revenue` `is_negative_margin` · LEFT JOIN 2 dim · partition `sale_year, sale_month` |
| **com7-reconcile-generic** | ✅ ทุกคืน | SQL Server (JDBC ผ่าน connection `com7-onprem-mssql`) → `com7_reconcile.*` | เทียบ/ซ่อมแบบ MERGE + delete audit + deep verify → [[Reconcile Pipeline - Glue Jobs]] |
| **com7-iceberg-maintenance** | ✅ ทุกคืน | ตารางใน registry ของ reconcile | compaction · expire snapshot · **ไม่ครอบตาราง `com7_gold` / `com7_silver`** |
| etl-bronze-to-silver-itec-sale | ⏸ ล่าสุด 08-26 | ไฟล์ TSV `ITEC_SALE.txt` → `com7_silver.itec_sale` | เส้นทางไฟล์อัปโหลด (Step Functions `com7-data-ingestion-pipeline` ผ่าน GuardDuty) · ไม่ได้ใช้แล้ว `[อนุมาน]` |
| etl-silver-to-gold-fact-sales | ⏸ ล่าสุด 09-02 | silver `itec_sale` → `com7_gold.fact_sales` + `dim_date` (2025–2026) | รุ่นก่อนของ fact · ถูกแทนด้วย `fact_sales_enriched` `[อนุมาน]` |
| etl-bronze-to-silver-branch | ⏸ รันครั้งเดียว 09-01 | bronze `dms/dim/branch_itec/` → `com7_silver.dim_branch` | ถูกแทนด้วย `etl-dms-dim-branch-to-gold` `[อนุมาน]` |
| etl-bronze-to-silver-item | ⏸ รันครั้งเดียว 09-01 | bronze `dms/dim/item_itec/` → `com7_silver.dim_item` | ซ้ำกับ `etl-bronze-to-silver-itec-item` `[อนุมาน]` |
| itec-raw-to-bronze | ⏸ ล่าสุด 09-01 · Glue 4.0 | `s3://itecitem-raw/itec_item.csv` → `s3://itec-rawtobronze/bronze-itec/` (append) | prototype รุ่นแรก · bucket คนละชุดกับ `com7data-*` |
| ev7-leads | ⏸ ล่าสุด 09-02 · ไม่มี schedule | Google Sheet → `s3://google-sheet-extract/google-sheet-ev7/leads-ev7-2025.csv` | โค้ด Lambda ที่ deploy เป็น Glue job · **ใช้ G.1X × 10 worker เพื่อเรียก API ตัวเดียว** |
| com7-snapshot-branch-diff-poc | 🧪 POC 09-14 | snapshot ใน manifest → S3 changes | diff แบบมีคีย์ของ branch → [[Snapshot Change Detection (ITEC DMS)]] |
| com7-snapshot-fact-diff-poc | 🧪 POC 09-14 | snapshot → S3 changes | diff แบบ multiset ของ fact (ไม่มีคีย์ที่ unique) |
| com7-poc-group-checksum | 🧪 POC 09-18 | SQL Server + `com7_reconcile` | ต้นแบบของ deep verify (signature รายเดือน) ที่รวมเข้า reconcile-generic แล้ว |

## ปัญหาที่เจอ

> **บริบท: ทั้งหมดนี้คือช่วง PoC** (ผู้ใช้ยืนยัน 2026-10-08) — ข้อมูลเป็นชุด PoC ที่โหลดมาครั้งเดียว และการรันสองเส้นทางคู่กันคือการทดลองเทียบ **DMS full load กับ Glue JDBC**
> ปัญหาด้านล่างจึงเป็น **สิ่งที่ต้องแก้ก่อนขึ้น production** ไม่ใช่เหตุขัดข้องของระบบที่ใช้งานจริง

### 0. ข้อมูลหยุดที่ 2026-09-23 14:40 — ปกติสำหรับชุด PoC · บทเรียนสำหรับ production
- แถวล่าสุด `SalesId 3151142` · `SalesCrDatetime 2026-09-23 14:40:18` · DMS อ่าน 78,627,844 แถวทุกคืน และทั้งสองเส้นทางได้ 78,627,844 เท่ากัน
- **บทเรียน:** ทั้งสองเส้นทางรายงานสำเร็จทุกคืนแม้ข้อมูลไม่ขยับ เพราะตรวจแค่ "ครบตามต้นทาง" ไม่ได้ตรวจ "ล่าสุดคือวันไหน" → production ต้องมี **freshness check** (`MAX(sales_datetime)` เทียบวันนี้ แล้ว fail + alert)

### ผลเทียบ DMS vs Glue JDBC (จากระบบจริง 2026-10-08)
| | DMS full load (เส้นทาง A) | Glue JDBC reconcile (เส้นทาง B) |
|---|---|---|
| จำนวนแถว | 78,627,844 | 78,627,844 — **ตรงกัน** |
| โหลดต้นทาง | อ่านทั้งตารางทุกคืน | อ่านเฉพาะ slice ที่เปลี่ยน |
| ขนาดตาราง | 3.39 GB + ไฟล์ค้างสะสม (108 GB ในโฟลเดอร์) | 2.05 GB · เก็บ 5 snapshot |
| การตรวจ | Lambda เทียบ DMS rows ↔ S3 rows | count gate · deep verify · delete audit |
| ยังไม่ได้พิสูจน์ | — | พฤติกรรมกับข้อมูลที่เปลี่ยนทุกวัน (ชุด PoC ไม่เปลี่ยน) |

### ยอดขายเก่าถูกแก้ย้อนหลังไหม — ตรวจจริง 2026-10-08
Athena บน `com7_reconcile.fact_sales_itec` (เก็บ `update_time` ของต้นทาง ระดับวัน) · เทียบ `update_time` กับวันที่ขาย · 78,627,844 แถว · scan 539 MB

| แก้ครั้งล่าสุดหลังวันขาย | แถว | % |
|---|--:|--:|
| วันเดียวกัน | 72,306,293 | 92.0 |
| 1–7 วัน | 2,925,573 | 3.7 |
| 8–30 วัน | 374,832 | 0.5 |
| 31–90 วัน | 1,252,237 | 1.6 |
| **91–365 วัน** | **821,546** | **1.0** |
| **เกิน 1 ปี** | **947,363** | **1.2** |

- **แก้หลัง 3 เดือน 1,768,909 แถว (2.25%)** — เกือบทั้งหมด `status = 0`
- เกิด **ต่อเนื่องทุกเดือน** (15–26 วัน/เดือน) และเพิ่มขึ้น: 2024 ราว 30–50k/เดือน → 2026 ราว 40–100k/เดือน
- มี **ก้อนใหญ่รายวัน** ข้ามหลายร้อยสาขา เช่น 2026-04-28 แก้ 59,544 แถวของยอดขาย ต.ค. 2025–ม.ค. 2026 (810 สาขา) · 2026-05-27 แก้ 48,337 แถว ย้อนถึงยอดขาย ก.ย. 2023 → น่าจะเป็นงาน batch ฝั่งต้นทาง (เช่น ปรับต้นทุน) `[อนุมาน — ไม่รู้ว่าคอลัมน์ไหนเปลี่ยน]`
- ตัวเลขนี้เป็น **ขั้นต่ำ** — `update_time` เก็บแค่ครั้งล่าสุด และมองไม่เห็นการแก้ที่ไม่ขยับ `update_time`

**ผลต่อการเลือกวิธี:** สมมติฐาน "เดือนเก่าไม่เปลี่ยน → full load เฉพาะ 3 เดือนล่าสุด" **ใช้ไม่ได้** · ใช้ได้คือ full load ทั้งตาราง หรือ incremental ตาม `update_time` (reconcile) ซึ่งจับแถวกลุ่มนี้ได้เพราะ `update_time` ขยับ

#### แถวที่ถูกแก้ย้อนหลังเป็นแถวแบบไหน (profile 2026-10-08)

**เห็นได้แค่ว่าแถวที่ถูกแก้เป็นแถวแบบไหน** · ไม่รู้ว่าคอลัมน์ไหนเปลี่ยนหรือเปลี่ยนเพราะอะไร เพราะต้นทางไม่เก็บค่าเดิม

| มิติ | แถวที่แก้ >90 วัน | แถวอื่น |
|---|---|---|
| ต้นทุน = 0 | 21.8% | 14.4% |
| ยอดขาย = 0 | 24.6% | 20.6% |
| รายการคืน (qty < 0) | 0% | 0% |

- **สินค้า:** ส่วนใหญ่เป็นกลุ่มโทรศัพท์และของที่ขายพ่วงกับมือถือ ได้แก่ Smartphone 848k แถว · Phone Accessories 163k · PREMIUM TABLET 140k (ยอดเฉลี่ย ฿5) · iPhone 126k · SMILE (SERVICE) 65k · SIM CARD 56k · PROMO OPERATOR 40k (ยอด ฿0) · หมวดที่ถูกแก้ในสัดส่วนสูงสุดคือ SMILE 4.4% · SIM 4.2% · PROMO OPERATOR 3.8% · iPhone 3.2% · Smartphone 3.2%
- **ช่องทาง:** BaNANA 1.53M แถว (3.2%) · KingKong 7.2% (สัดส่วนสูงสุด) · Studio7 แค่ 0.3% ทั้งที่ขาย iPhone เหมือนกัน
- **วันที่แก้ก้อนใหญ่** (02-26 · 04-28 · 05-27 · 08-02) มีส่วนผสมแบบเดียวกันทุกครั้ง คือ Smartphone ~50% · iPhone · PREMIUM TABLET (บางวันยอด/ต้นทุน = 0 ครบ 100%) · SIM CARD (ยอด = 0 ~97%)
- **ระดับบิล:** 156,724 บิล — เกือบทั้งหมดแก้**แค่บางบรรทัด** มีเพียง 121 บิลที่แก้ทั้งบิล

`[อนุมาน]` รูปแบบนี้คล้ายรายการขายเครื่องพ่วงโปรโมชันค่าย (เครื่อง + SIM + PROMO OPERATOR + ของแถมที่เป็นศูนย์บาท) ที่ถูกปรับทีหลัง เช่นค่ายยืนยันหรือยกเลิกสิทธิ์ ปรับต้นทุนหรือส่วนลด หรือผูก IMEI ภายหลัง ยังไม่มีหลักฐานยืนยัน

**วิธีหาคำตอบจริง**
1. ถามเจ้าของ ITEC/MIS ว่าวันที่ 2026-02-26 · 04-28 · 05-27 · 08-02 มีงาน batch หรือ stored procedure อะไรที่ `UPDATE` ตารางขาย และงานรายวันอะไรที่ขยับ `UpdateTime`
2. เทียบ snapshot สองรอบ (DMS bronze backup หรือ MERGE ของ reconcile) เพื่อดูว่าคอลัมน์ไหนเปลี่ยน
3. ถ้าต้นทางมี audit/trigger log หรือ temporal table ให้ใช้แหล่งนั้น

### หลักฐานรอบ 2026-10-07 (ดึงจาก log / catalog / Step Functions)
| เวลา | เหตุการณ์ |
|---|---|
| 23:44:41 | DMS full load เสร็จ → Step Functions เริ่ม · Lambda ตรวจ DMS: ทุกตาราง `MATCH` |
| 23:45:47 | `AllItemSilver` + `AllBranchGold` เริ่ม (log: `[RECONCILE] skipped`) |
| 23:47:09 · 23:48:21 | สร้าง `dim_branch` · `dim_item` ใหม่ (Glue `CreateTime`) |
| 23:48:44 | `AllFactSalesEnriched` เริ่ม (log: `[RECONCILE] skipped`) |
| **23:57:41** | **DROP + CREATE `fact_sales_enriched` → ตารางว่าง** (metadata `00000`) |
| **00:10:00** | เขียนข้อมูลเสร็จ (metadata `00001`) → **ตารางว่างนาน ~12 นาที** |

### 🔴 1. `DROP TABLE` แล้ว `CREATE TABLE` ใหม่ทุกคืน
job เส้นทาง A ทุกตัว (และ job รุ่นเก่า) ทำแบบนี้:
```python
spark.sql(f"DROP TABLE IF EXISTS {TABLE}")          # Iceberg + Glue Catalog: ลบแค่ metadata ไฟล์ข้อมูลยังอยู่
spark.sql(f"CREATE TABLE IF NOT EXISTS {TABLE} (...) LOCATION '...'")
df.writeTo(TABLE).overwritePartitions()
```
ผล:
- **ไฟล์เก่าค้างใน S3 ทุกคืน** — `fact_sales_enriched` ใช้จริง 334 ไฟล์ / 3.39 GB แต่โฟลเดอร์ `data/` มี 9,351 ไฟล์ / **108 GB** (ตรวจ 2026-10-08) และโตทุกวัน
- **ระหว่าง DROP กับ write เสร็จ ไม่มีตาราง** — BI/Athena ที่ query ตอน ~23:45–23:50 จะ error หรือได้ตารางว่าง
- **ถ้า job ล้มหลัง DROP ตารางหายไปเลย** จนรอบถัดไปสำเร็จ — ขัดกับคอมเมนต์ในโค้ดที่ตั้งใจ "เก็บตารางเดิมไว้ถ้า reconcile ไม่ผ่าน" (การตรวจเกิดก่อน DROP จึงปลอดภัยเฉพาะกรณีจำนวนแถวไม่ตรง)
- **ไม่มี time travel** — มี snapshot เดียวเสมอ ย้อนดูข้อมูลเมื่อวานไม่ได้

แนวทางแก้: สร้างตารางครั้งเดียว แล้วใช้ `INSERT OVERWRITE` / `writeTo().overwritePartitions()` บนตารางเดิม (หรือ `CREATE OR REPLACE TABLE` ของ Iceberg ที่เก็บประวัติ) + เพิ่มตาราง gold/silver เข้า `com7-iceberg-maintenance` + ล้างไฟล์ค้างครั้งเดียวด้วย `remove_orphan_files` (ตอนไม่มี job เขียน)

### 🔴 2. เส้นทาง "all" ที่รันทุกคืน ไม่ส่ง `EXPECTED_ROWS`
- Step Functions ส่ง `--EXPECTED_ROWS` เฉพาะเส้นทางรายชุดข้อมูล (`item`, `sale`, `fact_sales`)
- เส้นทาง `all` (`AllItemSilver`, `AllBranchGold`, `AllFactSalesEnriched`) **ไม่ส่ง** → log ทุกคืนเขียน `[RECONCILE] skipped`
- การเทียบจำนวนแถวกับที่ DMS อ่านได้ (ที่ทุก job เขียนรองรับไว้แล้ว) **จึงไม่เคยทำงานในรอบปกติ** ([[Decisions]] D-15)
- แก้: ส่ง `$.validation.<dataset>.sourceRows` ใน 3 state นั้น `[อนุมาน — ต้องดูว่า com7-dms-validate คืนจำนวนแถวรายตารางในรูปแบบไหน]`

### 🟠 3. สองเส้นทางทำข้อมูลเดียวกันพร้อมกัน
- A (DMS full load ทั้งตาราง) และ B (reconcile JDBC) เริ่ม 23:30 อ่าน `fact.sales_itec` ตัวเดียวกัน → โหลดซ้อนบน SQL Server และ link VPN
- ผลลัพธ์อยู่คนละที่: `com7_gold.fact_sales_enriched` กับ `com7_reconcile.fact_sales_itec` — ต้องตัดสินว่าตัวไหนเป็นแหล่งจริงของ Gold
- B ถูกต้องกว่า (MERGE · ตรวจ count · deep verify · audit การลบ) ส่วน A ทำ enrich/dimension · ทางที่สะอาดคือให้ A อ่านจาก B แทนการ full load ซ้ำ `[อนุมาน]`

### 🟡 4. อื่น ๆ
- **ค่า default ในโค้ดผิด** — `etl-bronze-to-silver-itec-item` / `etl-silver-to-gold-dim-item` ใช้ `com7data-bronze` / `com7data-silver` (ไม่มีเลขบัญชีต่อท้าย) ทำงานได้เพราะ DefaultArguments ของ job ทับไว้ · ถ้ามีคนรันโดยไม่ส่ง argument จะพัง
- **`com7-reconcile-generic` ที่ใช้งานจริงเป็นรุ่นเก่ากว่า bundle ใน workshop** — ยังฝังค่า default (`REGISTRY_URI`, `TABLE`, `SECRET_ID`, `MODE=reconcile`) และไม่ตรวจ argument
- **registry ของ reconcile มีตาราง `_test_*` 3 ตัว** — ไม่ถูก schedule แต่ maintenance วนทำทุกตารางที่ `enabled`
- **job ที่ไม่ได้ใช้แล้ว 6 ตัว + POC 3 ตัว** — ควร archive เพื่อไม่ให้สับสนว่าตัวไหนจริง
- **`ev7-leads`** ใช้ Spark 10 worker กับงานเรียก API → ย้ายไป Lambda หรือ Glue Python shell
- **ไม่มี Glue job สำหรับ D365 F&O / K2 / ITOS / CRM** — ทุกอย่างตอนนี้คือ ITEC (ยอดขาย · สินค้า · สาขา) + EV7 leads

---

## ตาราง Glue Catalog ที่เกี่ยวข้อง

| database | ตาราง | เขียนโดย |
|---|---|---|
| `com7_silver` | `itec_item` · (`itec_sale` · `dim_item` · `dim_branch` จาก job เก่า) | เส้นทาง A |
| `com7_gold` | `dim_item` · `dim_branch` · **`fact_sales_enriched`** · (`fact_sales` · `dim_date` จาก job เก่า) | เส้นทาง A |
| `com7_reconcile` | `fact_sales_itec` · `dim_item_itec` · `dim_branch_itec` · `reconcile_delete_audit` | เส้นทาง B |

วิธีอ่าน `fact_sales_enriched` ใน notebook → `scripts/glue/read_fact_sales_enriched.ipynb`

## เชื่อมกับโน้ตอื่น

[[Reconcile Pipeline - Overview]] · [[Medallion Layer Definition]] · [[Snapshot Change Detection (ITEC DMS)]] · [[DMS Full Load Validation (Lambda)]] · [[ETL & Spark]] · [[Decisions]]
