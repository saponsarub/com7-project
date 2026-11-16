# AWS Data Lake - Pipeline & Data Layers

> สรุปก่อนปิดระบบ 2026-10-30 · ตัวอย่างข้อมูล (ปิดข้อมูลส่วนบุคคลแล้ว) อยู่ใน backup `D:\AWS_Backup\603238661233_2026-10-30\_data_samples\` (ไม่อยู่ใน git) · ดู [[AWS Data Lake - Backup & Shutdown 2026-10]] · [[ADLS Gen2 to S3]] · [[Reconcile Pipeline - Overview]]

> ตัวอย่างข้อมูลจริงชั้นละ 20 แถวอยู่ใน `_data_samples/` (CSV + `.schema.json` มีคอลัมน์ ชนิด จำนวนแถว ที่อยู่)
> **ข้อมูลส่วนบุคคลถูกปิดแล้ว** (ชื่อ เบอร์ อีเมล ที่อยู่ เลขบัตร ทะเบียน VIN → `***`) · ตารางสมาชิก `mem_itec` เก็บแค่โครงสร้าง
> ยังเป็นข้อมูลบริษัท (ยอดขาย ต้นทุน) — เก็บเป็นความลับ · นับแถว ณ 30 ต.ค. 2026 (ข้อมูลโหลดล่าสุด 29 ต.ค. 23:30)

## 1. ภาพรวม

```
 ITEC SQL Server (on-prem)                    Google Sheets (4 ไฟล์ 14 tab)        Azure ADLS Gen2 (pilot)
   │ WireGuard VPN                               │ Lambda 23:30                        │ Glue (มือ)
   ▼                                             ▼                                    ▼
 DMS full-load 23:30 ──► BRONZE (Parquet)     s3://google-sheet-extract (CSV)      s3://com7-raw-adls
   │                     com7data-bronze        + log · อีเมลรายงาน                  + bronze_adls (Iceberg)
   │ Step Functions        dms/dim/* · dms/rpt/*  │ Glue crawler
   │ com7-dms-ingestion    ▼                      ▼
   │                   SILVER (Iceberg)        Glue Catalog googlesheet-raw / default → Athena
   │                     com7_silver
   │                     ▼
   │                   GOLD (Iceberg) ─► Athena / BI
   │                     com7_gold
   │
   └─ Reconcile (Glue ต่อ SQL Server ตรง) ──► com7_reconcile (Iceberg สำเนาตรงต้นทาง + audit การลบ)
```

ทั้งสามเส้นทางของยอดขายในระบบ:
| เส้นทาง | ใช้ทำอะไร | สถานะ |
|---|---|---|
| **DMS → bronze → silver/gold** (`com7-dms-ingestion-pipeline`) | ตารางรายงานหลัก `com7_gold.*` | ใช้ทุกคืน |
| **Reconcile** (`com7-reconcile-pipeline`) | สำเนาต้นทางที่ตรวจทุกแถว ทั้ง insert/update/delete (ต้นทางไม่มี CDC) | ใช้ทุกคืน |
| ไฟล์ข้อความ ITEC_SALE.txt → silver itec_sale → gold fact_sales (`com7-data-ingestion-pipeline`) | ยอดขายรายเดือนแบบสรุป | เส้นทางแรกสุด (ส.ค.) — ยังมีข้อมูลค้าง |

---

## 2. BRONZE — สำเนาดิบจาก DMS (`s3://com7data-bronze-603238661233/dms/`, Parquet, versioning เปิด)

DMS ดึง **ทั้งตาราง** (full-load) ทุกคืนเขียนทับ · เพิ่มคอลัมน์ `_dms_ingestion_ts` (เวลาที่ DMS เขียน) · ชื่อคอลัมน์และชนิดตามต้นทางเป๊ะ (มีเว้นวรรค / `%` / `/` ในชื่อ)

| ตาราง (ต้นทาง) | แถว | ขนาด | คอลัมน์ | หมายเหตุ |
|---|---|---|---|---|
| `dim/item_itec` | 220,143 | 0.03 GB | ItemId · ItemName · CategoryName · SubCategoryName · Model/Series · Brand | ItemId ปนกันทั้งบาร์โค้ด EAN 13 หลัก รหัสภายใน และรหัสขึ้นต้น `##` / `**` (สินค้าเก่า/พิเศษ) |
| `dim/branch_itec` | 3,323 | <0.01 GB | Branch · BranchName · BranchType · Province · Region · Lat/Long · Address · Opened/ClosedDate · Status · BuildingCompetitor · UpdateDatetime | รวมคลัง/สาขาปิด ("ปิดUD-…") · Status ว่างทุกแถว |
| `rpt/fact_sales_itec` | **80,864,934** | 9.7 GB · 12 ไฟล์ | SalesId · SalesBranch · ItemId · SerialNo · SalesQty · SalesAmount · CostAmount · GPAmount · `GP %` · Status · SalesCrDatetime · SalesOfficerId | ระดับรายการขาย (ตั้งแต่ ม.ค. 2023) · Qty ติดลบ = คืนสินค้า |
| `rpt/fact_bank_itec` | 19,374,076 | 2.3 GB | SalesId · STORE ID · BookingId · TYPE (ช่องทางจ่าย) · LAST 4-DIGIT · APPROVAL CODE · TRANS AMT · TERMINAL ID · TRANS DATE | การชำระเงิน (ไม่มีเลขบัตรเต็ม) · ยังไม่มี ETL ใช้ |
| `dim/mem_itec` | 23,434,074 | 1.8 GB | salesid · salesbranch · memcode · crmid · Name | **ข้อมูลลูกค้า** — ไม่ได้เก็บตัวอย่าง · ยังไม่มี ETL ใช้ |
| `detail-sale/` (นอก dms/) | – | – | ไฟล์ ITEC_SALE.txt | ต้นทางของเส้นทางไฟล์ข้อความ |

ตัวอย่าง (fact_sales_itec): `SalesId=3333 · SalesBranch=596 · ItemId=8859703404132 · Qty=1 · SalesAmount=551.40 · CostAmount=164.00 · GPAmount=387.40 · GP%=236.21 · SalesCrDatetime=2023-01-05 11:19`
> GP% ในต้นทาง = กำไร ÷ **ต้นทุน** (จึงเกิน 100% ได้) — ชั้น gold เพิ่ม margin_pct = กำไร ÷ **ยอดขาย**

ก่อนเข้า silver: Lambda `com7-dms-validate` ตรวจว่า task จบเพราะโหลดเสร็จ · ทุกตาราง "Table completed" · จำนวนแถวในไฟล์ Parquet (อ่าน footer) = ที่ DMS รายงาน — ไม่ผ่าน = ไม่รัน ETL + แจ้ง SNS
และ 23:00 ทุกคืน `com7-bronze-backup` copy bronze ทั้งชุดไป `com7data-backup` (versioned + manifest) ก่อน DMS เขียนทับ

---

## 3. SILVER — ทำความสะอาด (`com7_silver`, Iceberg ใน `s3://com7data-silver-603238661233/`)

| ตาราง | แถว | ทำอะไรจาก bronze | คอลัมน์ที่เพิ่ม |
|---|---|---|---|
| `itec_item` (job `etl-bronze-to-silver-itec-item` · ใช้จริง) | 220,143 | แยกชนิดรหัสสินค้า (`item_id_type`: EAN / รหัสภายใน / OTHER) · ตัด suffix ออกเป็น `base_item_id` · จับสินค้า Demo / Service / Promo จากชื่อและหมวด → `product_status` (ACTIVE > DEMO > SERVICE > PROMO ใช้เลือกแถวเมื่อรหัสซ้ำ) · ตัวพิมพ์ใหญ่ ตัดช่องว่าง | base_item_id · item_id_type · item_id_suffix · is_valid_item_id · *_clean · is_demo · is_service · is_promo · product_status |
| `dim_item` (job `etl-bronze-to-silver-item` · ชุดละเอียด รันมือ 1 ก.ย.) | 216,009 | หมวดหลัก ~12 หมวด · หมวดย่อย · แบรนด์มาตรฐาน · สายรุ่น (เช่น iPhone 15 Pro Max) · รายละเอียดรุ่น (ความจุ/สี) · ตัด Demo/Promo/Service | clean_product_category · clean_subproduct_category · clean_brand · clean_model_line · clean_model_detail · is_actual_product |
| `dim_branch` (job `etl-bronze-to-silver-branch` · รันมือ) | 3,205 | ชื่อสาขาสะอาด · ช่องทาง ONLINE / STORE · เปิดอยู่ไหม · แบรนด์ร้านจาก prefix ชื่อ (BaNANA, Studio7, KingKong, Samsung, Xiaomi …) · ในห้าง / เดี่ยว (คำค้นชื่อห้าง) · จังหวัดไทย 77 · ภาคตาม สสช. 6 ภาค | clean_branchname · sale_channel · is_open · store_brand · location_type · province_th · region_nso |
| `itec_sale` (เส้นทางไฟล์ข้อความ) | 6,150,627 | ไฟล์ ITEC_SALE.txt (สรุปรายเดือน × สาขา × สินค้า) → ชนิดข้อมูลถูกต้อง · ปี/เดือน · คำนวณ margin · ธงคืนของ / ยอด 0 / ขาดทุน | sale_year · sale_month · margin_amt · margin_pct · is_return · is_zero_revenue · is_negative_margin |

ตัวอย่าง (dim_branch): `branch_id=2 · branch_name_original="สินค้าหายจากขนส่ง (ของโยก)" → clean_branchname="สินค้าหายจากขนส่ง" · sale_channel=STORE · province_th=กรุงเทพมหานคร · region_nso=ภาคกลาง`

---

## 4. GOLD — พร้อมทำรายงาน (`com7_gold`, Iceberg ใน `s3://com7data-gold-603238661233/detail-sale/`)

| ตาราง | แถว | มาจาก | หน้าตา |
|---|---|---|---|
| **`fact_sales_enriched`** (job `etl-dms-fact-sales-to-gold` ~22 นาที) | **80,864,934** | bronze fact_sales_itec ⨝ dim_item ⨝ dim_branch | 1 แถว = 1 รายการขาย: sales_id · เวลา/วัน/เดือน · สาขา (ชื่อ ภาค จังหวัด ช่องทาง) · สินค้า (ชื่อ แบรนด์ brand_group department category sub_category) · serial_no · พนักงานขาย · qty · cost · sale · gp_amt · gp_pct (เดิม) · margin_amt · margin_pct (÷ ยอดขาย, ยอด 0 = ว่าง) · is_return · is_zero_revenue · is_negative_margin (ขาดทุนที่ไม่ใช่การคืน) |
| `dim_item` (job `etl-silver-to-gold-dim-item`) | 220,143 | silver itec_item | item_id · base_item_id · item_name · **department** (Mobile, Computing, IT Accessories …) · category · sub_category · model_series · brand · **brand_group** (แบรนด์หลัก / Other) · product_status · is_valid_item_id |
| `dim_branch` (job `etl-dms-dim-branch-to-gold`) | 3,323 | bronze branch_itec (ตรง) | branch_id · branch_name · region · province · channel — แทน stub เดิมที่ทำให้ fact มีชื่อสาขาเป็น NULL |
| `fact_sales` (เส้นทางไฟล์ข้อความ) | 6,139,100 | silver itec_sale ⨝ dim_item | สรุปรายเดือน × สาขา × สินค้า + แบรนด์/หมวด |
| `dim_date` | 24 | สร้างขึ้น | รายเดือน 2025–2026 · ไตรมาส · ปีบัญชี (fiscal_year / fiscal_quarter) |

ตัวอย่าง (fact_sales_enriched): `2026-06-07 20:12 · สาขา BN-Central-Chiang Rai-1.1 (North, Chiang Rai, BaNANA) · สินค้า … department=Mobile category=Smartphone · qty 1 · cost 27.16 · sale 17.13 · gp -10.03 · margin_pct -58.55 · is_negative_margin=true`

---

## 5. RECONCILE — สำเนาตรงต้นทาง (`com7_reconcile`, Iceberg ใน `s3://com7data-fact-sales-itec-603238661233/iceberg/`)

ต้นทาง SQL Server ไม่มี CDC / transaction log → `com7-reconcile-generic` ทำ "CDC ฝั่งปลายทาง" เอง ทุกคืน:
1. นับแถวสองฝั่ง → 2. อ่านต้นทางแบบแบ่งช่วงขนานกัน (WireGuard หลุดเป็นระยะ ช่วงสั้นจบทัน) → 3. เทียบตาม primary key → INSERT ที่ขาด · UPDATE ที่เปลี่ยน (ตาม UpdateTime) · DELETE ที่หายจากต้นทาง (บันทึกลง audit ก่อนลบ) → 4. นับซ้ำต้องเท่ากัน
ตารางที่ดูแล: กำหนดใน `s3://com7data-artifacts-603238661233/reconcile/reconcile_tables.json`

| ตาราง | แถว | คอลัมน์เพิ่ม |
|---|---|---|
| `fact_sales_itec` | 80,864,934 | update_time · dms_ingestion_ts · reconciled_at · target_inserted_at / updated_at · target_last_operation (INSERT/UPDATE) · target_operation_run_id |
| `dim_item_itec` | 220,143 | เหมือนกัน |
| `dim_branch_itec` | 3,323 | เหมือนกัน |
| `reconcile_delete_audit` | 1,556,985 | ทุกแถวที่เคยถูกลบ: ตาราง · run · ทางลบ · primary key (JSON) · **ค่าก่อนลบทั้งแถว (JSON)** |

ตรงกับ bronze ทุกตาราง (80,864,934 / 220,143 / 3,323) = ข้อมูลสองเส้นทางสอดคล้องกัน ณ คืนสุดท้าย

---

## 6. Google Sheets pipeline

```
Google Sheets ──(service account ใน Secrets Manager com7/google-sheets/service-account)──► Lambda test-ses-googlesheet (23:30)
   ├─ ทุก tab → s3://google-sheet-extract/<prefix>/<ตาราง>/data.csv (เขียนทับ · bucket มี versioning = เก็บทุกรอบ)
   ├─ tab ที่พลาด retry สูงสุด 3 รอบ (เว้น 20 วิ) · ตรวจขนาดไฟล์บน S3 = ที่เขียน · header hash ตรวจคอลัมน์เปลี่ยน
   ├─ log ต่อ tab → s3://com7-ingest-logs-603238661233/ingest-log/source=google_sheet/year=/month=/day=
   │     └─ async ► Lambda com7-rowcount-googlesheet นับแถว CSV จริง (เซลล์มีขึ้นบรรทัดใหม่ไม่นับเกิน) เติมกลับเข้า log
   └─ อีเมลรายงาน HTML (SES) — สำเร็จ/พลาดกี่ tab · กี่แถว · ขนาด · เวลา
Glue crawler (ev7-googlesheet-csv · log-ingest-googlesheet · Test-ev ทุกวัน 12:54) → Glue Catalog `googlesheet-raw` / `default` → Athena
```

| Google Sheet | tab → ตาราง | เนื้อหา (ปิดข้อมูลส่วนตัวในตัวอย่างแล้ว) |
|---|---|---|
| **EV7 Main** | Query→ev7_query (120 คอลัมน์) · 2025→ev7_2025 · 2026→ev7_2026 (111) · Check · Filter · Event · Compare by puii | ใบสมัครคนขับ EV7: ผู้สมัคร ผู้ค้ำ ผู้แนะนำ ทะเบียนรถ VIN ใบขับขี่สาธารณะ สถานะ · งานอีเวนต์ |
| **Grab** | ชีต1→Grab · Clean→Grab_Clean | คนขับจาก Grab ที่สมัคร |
| **Lineman** | ชีต1→Lineman · Clean→Lineman_Clean | คนขับจาก Lineman |
| **GI** (prefix google-sheet-gi) | rawdataInteresting→GI_Interest · rawdataTestdrive→GI_Testdrive · rawdataBooking→GI_Booking | ลูกค้าสนใจ / ทดลองขับ / จอง (ชื่อ เบอร์ อีเมล เลขบัตร ที่อยู่ พนักงานขาย) |

> ⚠️ ข้อมูลชุดนี้คือ **ข้อมูลส่วนบุคคลจำนวนมาก** (เลขบัตรประชาชน เบอร์ ที่อยู่) — ถ้าเก็บต่อต้องดูแลตาม PDPA · ลบแล้วไม่กระทบต้นทาง (Google Sheets ยังอยู่)

งาน Google Sheet อื่น: `ev7-leads` (Glue, EV7 leads → S3) · ap-southeast-1 `mis-tan-dev-gsheet-cdc` (ทุก 5 นาที CDC) + `mis-tan-dev-cdc-merge` (ทุกชั่วโมง MERGE → Iceberg) — งานทดลองของทีม mis-tan

---

## 7. Azure ADLS Gen2 → S3 (pilot ต.ค. 2026)

เป้าหมาย: พิสูจน์ว่า Glue ใน ap-southeast-7 อ่าน Data Lake ฝั่ง Azure ของ COM7 (ที่ Azure Synapse ใช้ · D365 F&O ผ่าน Synapse Link, BC LS Retail, ITEC, Excel จาก SharePoint) ได้ → ย้ายมา S3 · รายละเอียดเต็มใน vault: `05_ETL/ADLS Gen2 to S3.md` · `ADLS Gen2 to S3 - Glue Pilot (staging).md` · `ADLS Gen2 to S3 - Console Runbook.md`

| | ค่า |
|---|---|
| ต้นทาง | tenant `com7erp.onmicrosoft.com` · storage account `stcom7dw001` (rg `rg-com7dw`) · container `staging` โฟลเดอร์ `training`, `csvtest` (ห้ามแตะ `staging/synapse` และ container `azure-webjobs-*` — Azure Function ใช้ร่วม) |
| สิทธิ์ | Entra app `aws-glue-adls-reader` (client secret อายุ 90 วัน) + role "Storage Blob Data Reader" บน container `staging` · ค่าเก็บใน AWS secret `com7/adls/glue-reader` (tenant_id · client_id · client_secret · account · container) |
| AWS | IAM role `com7-glue-adls-reader-role` · bucket `com7-raw-adls` (versioning) · Glue DB `bronze_adls` |
| job `adls-pilot-test` (Glue 5.0) | ตรวจ network ไป login.microsoftonline.com และ `<account>.dfs.core.windows.net` · สำรวจโฟลเดอร์ (จำนวนไฟล์ ขนาด นามสกุล มี Delta ไหม) · อ่าน `csvtest/PPW_Item` ผ่าน ABFS driver ของ Spark → สร้าง Iceberg `bronze_adls.ppw_item` (260 คอลัมน์) · รันล่าสุด 14 ต.ค. FAILED (ตารางเป้าหมายใน catalog) |
| job `adls-copy-staging-pilot` (Glue 5.1, Python) | copy ไฟล์ทั้งโฟลเดอร์ (`--FOLDER training`) ด้วย Azure SDK → `s3://com7-raw-adls/staging/training/` · ข้ามไฟล์ที่มีแล้วขนาดเท่ากัน (รันซ้ำได้) · 14 ต.ค. SUCCEEDED |
| ผลใน S3 | 12 ไฟล์ 1.2 MB · ตาราง `bronze_adls.pilot_training` (8 คอลัมน์) และ `ppw_item` |

**ต้องทำฝั่ง Azure เมื่อเลิกโครงการ** (AWS ทำแทนไม่ได้): ลบ client secret หรือลบ App registration `aws-glue-adls-reader` · ลบ role assignment "Storage Blob Data Reader" บน `staging` — ไม่งั้นคนที่มี secret ยังอ่าน ADLS ได้จนกว่า secret หมดอายุ
