---
tags: [d365, sizing, s3, datalake]
date: 2026-10-15
source: syndpdev001 (โปรไฟล์ fo_raw · SQL Server 192.168.43.84)
---

# D365 F&O - Storage Sizing

ขนาดข้อมูล D365 ใน `syndpdev001` ที่ต้องย้ายขึ้น S3 **เฉพาะตาราง raw** · ไม่นับตารางสรุป ตารางซ้ำ และตาราง backup
วัดเมื่อ 2026-10-15 จาก `sys.allocation_units` และสุ่ม `TOP 50,000` แถวต่อตาราง เขียนเป็น Parquet zstd ใน memory (ไม่มีไฟล์ข้อมูลออกจากเครื่อง)

## สรุป

| กลุ่ม | ตาราง | แถว | ข้อมูล SQL | Index SQL | ย้ายขึ้น S3? |
|---|---:|---:|---:|---:|---|
| **raw** (`dbo.tb_*` · `dbo.tm_*`) | 31 | 892.5M | **233.6 GB** | 91.2 GB | ✅ → **Parquet ~28 GB** |
| สรุป (`vtb_*`) | 13 | 720.5M | 38.6 GB | 129.6 GB | ❌ สร้างใหม่ใน Silver/Gold ได้ |
| ซ้ำ / backup / tmp (`tmp.*` · `staging.*` · `*_bak` · `_test_*` · `_IndexBackupLog`) | 26 | 34.9M | 7.4 GB | 1.9 GB | ❌ |
| สิทธิ์ (`rls.UserAccess` · `MT_RLSUser*`) | 3 | 105 | ~0 | — | ❌ ใช้ IAM / Lake Formation แทน |

- ทั้ง DB: ข้อมูล 279.6 GB + index 222.7 GB ≈ 502 GB → ย้ายจริงแค่ raw **~28 GB Parquet (12% ของข้อมูล SQL)**
- Index ไม่ย้าย (Parquet ไม่มี index)
- `vtb_VoucherTransaction` คือตารางที่ใหญ่ที่สุดใน DB (columnstore 638M แถว · 157 GB รวม index) แต่เป็นตารางสรุป จึงไม่นับ

## รายตาราง raw

| ตาราง | แถว | SQL MB | Parquet MB (ประมาณ) |
|---|---:|---:|---:|
| tb_InventTrans | 211,129,158 | 84,948 | 13,531 |
| tb_SalesInvoice | 107,696,164 | 51,187 | 4,072 |
| tb_InventTransOrigin | 175,246,388 | 18,090 | 2,767 |
| tb_CustTrans | 67,005,994 | 15,513 | 2,213 |
| tb_InventJournalTrans | 57,339,638 | 23,126 | 2,046 |
| tm_InventDimension | 81,551,913 | 10,614 | 1,316 |
| tb_TaxTrans | 118,490,551 | 22,607 | 1,311 |
| tm_ItemSerial | 34,317,348 | 3,221 | 479 |
| tb_SalesInvoice_Other | 15,549,154 | 3,330 | 339 |
| tb_VendTrans | 3,503,769 | 1,018 | 138 |
| tm_FinDimValueCombination | 5,316,686 | 2,026 | 122 |
| tb_SalesPayment | 5,553,756 | 801 | 63 |
| tb_FATrans · tb_InventOnhand | 3.4M · 1.9M | 612 · 559 | 47 · 47 |
| อีก 17 ตาราง (Purch* · tm_Item · tm_Customer · tm_Vendor ฯลฯ) | ~4M | ~1,500 | ~110 |
| **รวม** | **892.5M** | **233.6 GB** | **~27.9 GB** |

`tb_VoucherTrans` มี 0 แถว · `tm_Item_bak` นับเป็น backup

## ยืนยันกับของจริง (2026-10-15)

| ทดสอบ | SQL | Parquet | เหลือ |
|---|---:|---:|---:|
| `tb_SalesPayment` แปลงทั้งตาราง zstd | 801 MB | 51 MB | 6.4% (ค่าประมาณจากตัวอย่างสูงไป 23%) |
| `tb_SalesInvoice_Other` แปลงทั้งตาราง zstd | 3,330 MB | 250 MB | 7.5% (ค่าประมาณสูงไป 35%) |
| ITEC `rpt.fact_sales_itec` ไฟล์ DMS จริงใน `com7data-bronze-.../dms/rpt/` | 6.3 GB [อนุมาน: DATALENGTH + overhead · เป็น view] | 8.8 GB | **140% — DMS เขียน Parquet แบบ UNCOMPRESSED · PLAIN ไม่มี dictionary** |
| ไฟล์ DMS 1 ไฟล์ เขียนใหม่ zstd | 808 MB (ไฟล์ DMS) | 172 MB | 21% ของไฟล์ DMS → ทั้งตาราง ~1.9 GB ≈ 30% ของ SQL |

| ITEC `com7_reconcile.fact_sales_itec` (Glue JDBC → Iceberg · ZSTD) snapshot ปัจจุบัน | 6.3 GB | **1.91 GB** (45 ไฟล์ · โฟลเดอร์รวม snapshot เก่า 2.10 GB) | **30%** |
| ITEC `com7_gold.fact_sales_enriched` (SNAPPY · 31 คอลัมน์) | — | 3.15 GB | — |

ไฟล์ DMS ใหญ่เพราะ: เพิ่มคอลัมน์ `_dms_ingestion_ts` เป็นข้อความ 30 byte/แถว (25% ของไฟล์) · ไม่บีบอัด · ไม่ใช้ dictionary → ทุกคอลัมน์กว้างเท่า SQL + ข้อความมีตัวบอกความยาวอีก 4 byte

→ ค่าประมาณ D365 ~28 GB น่าจะสูงกว่าจริง (เผื่อไว้แล้ว) · DMS endpoint ต้องตั้ง `CompressionType=GZIP` ไม่งั้นไฟล์ใหญ่กว่าต้นทาง
→ ตัวเลขทั้งหมดไม่รวม S3 versioning · หลายชั้น · snapshot ย้อนหลัง

## ถ้าเก็บเป็น CSV

วัดจากตัวอย่างเดียวกันใน 9 ตารางใหญ่ (97% ของข้อมูล raw):

| รูปแบบ | 9 ตาราง | เทียบ SQL | ประมาณทั้ง raw |
|---|---:|---:|---:|
| SQL (data ไม่รวม index) | 227.2 GB | 100% | 233.6 GB |
| CSV ไม่บีบอัด | 167.2 GB | 74% | **~172 GB** |
| CSV.gz | 28.3 GB | 12% | ~29 GB |
| Parquet zstd | 27.4 GB | 12% | ~28 GB |

- CSV ไม่บีบอัดเล็กกว่า SQL แค่ ~26% (ตัดช่องว่าง fixed-width กับ overhead ของ page/row ออก แต่เลขกลายเป็นตัวอักษร)
- CSV.gz ขนาดพอ ๆ กับ Parquet แต่ Athena ต้องอ่านทั้งไฟล์ทุกคอลัมน์ และ gzip แบ่งไฟล์อ่านขนานไม่ได้ → ค่า scan และเวลา query สูงกว่ามาก
- ถ้ารับเป็น CSV เข้ามา ให้เก็บเป็นชั้น landing ชั่วคราว แล้วแปลงเป็น Parquet/Iceberg ด้วย Glue

## ข้อควรรู้

- **ค่าประมาณ ±30%** — `TOP 50,000` ดึงหน้าแรก ๆ ของตาราง ไม่ใช่สุ่มจริง ถ้าข้อมูลเก่ากับใหม่หน้าตาต่างกันมาก ตัวเลขจะคลาด
- **มีข้อมูล BC LS ปนอยู่**: 41 ตาราง raw มีคอลัมน์ `SysSourceRef` (`FO` / `BCLS`) เช่น `tb_InventTrans` เป็น BCLS 2.81% · ถ้าย้ายเฉพาะ FO ขนาดจะลดลงเล็กน้อย ต้องตัดสินว่าจะแยกเป็นคนละ prefix หรือไม่
- นี่คือ DB `syndpdev001` บน SQL Server on-prem — [อนุมาน] เป็นสำเนาของ Synapse · ขนาดใน Azure Synapse จริง หรือไฟล์ Synapse Link ใน ADLS อาจต่างจากนี้ (ADLS ยังไม่มีสิทธิ์อ่าน ดู [[ADLS Gen2 to S3]])
- ไม่รวมการเก็บย้อนหลัง (snapshot รายวัน/รายเดือน) และสำเนาหลายชั้น (Bronze/Silver/Gold)

## เชื่อมโยง

[[D365 F&O Overview]] · [[K2 + ITOS - Storage Sizing]] · [[AWS Data Lake Proposal Review 2026-10]]
