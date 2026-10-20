# K2 Overview

ระบบเช่าซื้ออุปกรณ์ IT ของ **TFF — บริษัท ธันเดอร์ ฟินฟิน จำกัด** · ฐานข้อมูล `HPCOM7` (MSSQL)
หน้านี้เป็นสารบัญของทุกโน้ตที่ขึ้นต้นด้วย `K2 -`

---

## ใครสร้าง K2

> **ที่มา:** แจ้งด้วยวาจาจากทีมภายใน **2026-09-02** — ยังไม่มีเอกสารยืนยัน

**K2 เป็นระบบที่ทีม dev ของบริษัทเขียนขึ้นเอง (in-house) ไม่ใช่ product จาก vendor** · ฐานข้อมูลอยู่ **on-premise**

> เรื่องชื่อ: ทีมเรียก "K2" ทั้งระบบและฐานข้อมูล ส่วนชื่อฐาน MSSQL จริงคือ `HPCOM7` — ในเอกสารเรื่องการย้าย ICI มีการเขียนว่า `IDS (K2)` ซึ่ง **น่าจะหมายถึง IDS = ชื่อโปรแกรม · K2 = ฐานข้อมูลของมัน** `[อนุมาน — ยังไม่ยืนยัน]` → [[Source System Issues]]

### ทำไมเรื่องนี้สำคัญ

| ผล | รายละเอียด |
|---|---|
| **อธิบายได้ว่าทำไมแทบไม่มี FK** | 542 ตาราง มี FK แค่ **16 ตัว** — ระบบที่โตขึ้นเองตามงานที่เพิ่มมา มักไม่บังคับ integrity ที่ระดับฐาน `[อนุมาน]` → [[SQL & Source Schemas]] |
| **ไม่มีเอกสารจาก vendor ให้ขอ** | เอกสารที่เชื่อถือได้มีทางเดียวคือจาก **ทีม dev / MIS-Fintech** — ตรงกับที่รอ "เอกสารยืนยัน" อยู่ → [[K2 Issues]] |
| **schema เปลี่ยนได้ทุกครั้งที่ dev deploy** | ไม่มี release note ของ vendor ให้ตาม pipeline จึงเสี่ยง schema drift ต้องมีคนคอยแจ้งหรือมี monitoring |
| **ขยายรับธุรกิจใหม่ได้เรื่อย ๆ** | อธิบายว่าทำไม K2 รับงาน EV ได้ และทำไม ICI ถึงย้ายเข้ามาได้ — เพราะทีม dev แก้เองได้ ไม่ต้องซื้อ module `[อนุมาน]` |
| **ไม่มีค่า subscription** | ตรงกับเหตุผลที่ย้าย ICI ออกจาก P&O → [[Other Systems]] |
| **คนตอบคำถาม schema คือทีม dev** | ไม่ใช่ vendor support — มีผลกับว่าจะถามใครเวลาติด |

---

## Where to start

| อยากรู้ | เปิด |
|---|---|
| **ขอที่อยู่ของลูกค้าคนนี้** / ค้นจากชื่อ / ดูสัญญา | [[K2 - Query Cookbook]] |
| **กฎธุรกิจ** — วันชำระ · งวดไหนจ่ายแล้ว · OD · ผู้ค้ำ | [[K2 - Business Rules]] |
| **ทำหนังสือบอกเลิกสัญญา** — ดึงอะไรจากไหน · คัดใครบ้าง | [[K2 - Termination Letter Mapping]] |
| **วิธีคิด + SQL ทำหนังสือบอกเลิก ทีละขั้น** | [[K2 - Termination Letter How-To]] |
| **ค่าปรับ · ค่าติดตาม · การตัดรับชำระ** คิดยังไง | [[K2 - Fee Policy]] |
| **คัดใครเข้าเกณฑ์บอกเลิกสัญญา** — ตรรกะ + SQL ทีละบรรทัด | [[K2 - OD6 Selection Logic]] |
| **แต่ละ field คืออะไร** — ตารางแกน 10 ตัว | [[K2 - Data Dictionary]] |
| ตารางไหนเก็บอะไร มีกี่แถว · ชั้นความสำคัญ | [[K2 - Table Inventory]] |
| ลูกค้าเก็บที่ไหน · เลขบัตร · ที่อยู่ 5 ชุด | [[K2 - Customer & Address]] |
| สัญญาเช่าซื้อ · สถานะ · บัญชี GL | [[K2 - Contract & Account]] |
| ค่างวด · ใบแจ้งหนี้ · การรับชำระ | [[K2 - Payment & Invoice]] |
| หนี้ค้าง · การมอบหมายทวงถาม | [[K2 - Collection & OD]] |
| รหัสสถานะ · จังหวัด · แบรนด์ · ธนาคาร | [[K2 - Master & Setup]] |

---

## What K2 does

ลูกค้าเดินเข้าร้านในเครือ COM7 (Studio7 / BaNANA) เลือกเครื่อง → ขอสินเชื่อเช่าซื้อกับ TFF → K2 คือระบบที่รับใบเสนอราคา อนุมัติ ทำสัญญา ออกใบแจ้งหนี้รายงวด รับชำระ ลงบัญชี และติดตามหนี้

```
QUOTATION  ──►  APPLICATION  ──►  CONTRACT  ──►  CUSTOMER_CARD  ──►  INVOICE  ──►  REPAYMENT  ──►  ACCOUNT
 801,188         410,306          288,205        5,816,540          4,396,632     5,205,081      25,977,656
ใบเสนอราคา       ใบคำขอสินเชื่อ      สัญญาเช่าซื้อ     ตารางผ่อนรายงวด      ใบแจ้งหนี้       การรับชำระ      ลงบัญชี GL

PROSPECT_CUSTOMER ─┘                    │
   800,283                              └──►  COLLECTION_OD  ──►  COLLECTION_OD_ASSIGNMENT
ผู้สนใจก่อนเป็นลูกค้า                              15,653,423             98,477
                                        snapshot หนี้ค้างรายวัน      มอบหมายให้ collector

PERSON (404,749) ──1:1──► ADDRESS (403,283)
ข้อมูลบุคคล                ที่อยู่ 4 ชุด + ที่ทำงาน  (รวม 5 ชุดในแถวเดียว)
```

**สิ่งที่ปล่อยกู้คือเครื่อง** — `MT_CATEGORY` มีแค่ Smart Phone · Tablet · Laptop
`MT_BRAND` = Apple · Samsung · Xiaomi · Vivo · OPPO · Realme (+ Apple UFicon)

---

## Verified numbers

| | | |
|---|---:|---|
| Tables | **542** | schema `dbo` ทั้งหมด ไม่มี schema อื่น |
| ตารางที่ใช้จริง | **364** | หลังตัด backup/temp/test/zero-row |
| Views | **165** | อ่าน definition ไม่ได้ (ไม่มีสิทธิ์) |
| **Foreign keys** | **16** | จาก 542 ตาราง — แทบไม่มี relation ประกาศไว้ |
| สัญญาทั้งหมด | 288,205 | ตั้งแต่ 2020-07-15 |
| บุคคลในระบบ | 404,749 | มีสัญญาจริง 288,195 |
| **เลขบัตรที่ไม่ซ้ำ** | **343,249** | จาก 404,627 แถวที่มีเลขบัตร |
| สัญญาที่ยังเดินอยู่ | 93,214 | สถานะ "ลูกหนี้ปกติ" |
| หนี้ค้าง snapshot ล่าสุด | ~120,579 สัญญา/วัน | `COLLECTION_OD` วันที่ 2026-08-26 |

### Contracts per year

| ปี              |   สัญญาใหม่ |
| --------------- | ----------: |
| 2020            |       1,768 |
| 2021            |      28,725 |
| 2022            |      29,730 |
| 2023            |      27,121 |
| 2024            |      81,476 |
| 2025            | **102,809** |
| 2026 (ถึง ส.ค.) |      16,567 |

โต 3 เท่าในปี 2024 แล้วโตต่อในปี 2025 · ปี 2026 ชะลอลงชัดเจน `[อนุมาน]`

### Product lines — `CONTRACT.PROJECT_TYPE`

| ค่า | สัญญา |
|---|---:|
| NULL | 187,410 |
| **UFUND** | 95,758 |
| PARTNER | 3,818 |
| UFICON | 1,181 |
| SolarCell | 37 |
| UPHONE | 2 |

NULL คือสัญญาเก่าก่อนที่จะมีฟิลด์นี้ `[อนุมาน]` — **ห้ามใช้ `PROJECT_TYPE` แบ่งกลุ่มโดยไม่จัดการ NULL**

`COLLECTION_OD.PRODUCT_TYPE` แบ่งอีกแบบและครบกว่า: **Student 73,209 · Personal 47,370** (สัญญาที่มีหนี้ค้าง ณ 2026-08-26)
→ **UFund เป็นสินเชื่อเครื่องสำหรับนักศึกษาเป็นหลัก** สอดคล้องกับที่ `PERSON` มี `STUDENT_ID`, `UNIVERSITY_NAME`, `FACULTY_NAME`, `MT_FACULTY` (39,475 แถว), `MT_UNIVERSITY_NAME` (1,149)

### Selling partners — `SETUP_PARTNER`

| บริษัท | สัญญา |
|---|---:|
| บริษัท คอมเซเว่น จำกัด (มหาชน) | 283,144 |
| บริษัท ยูฟิคอน จำกัด | 2,968 |
| บริษัท เอส พี วี ไอ จำกัด (มหาชน) | 1,885 |
| บริษัท ไพร์ม โซลูชั่น แอนด์ เซอร์วิส จำกัด | 1 |
| NULL | 208 |

`SETUP_COMPANY` id 121 = **บริษัท ธันเดอร์ ฟินฟิน จำกัด** เลขนิติบุคคล `0105558011806` ทุนจดทะเบียน 150,000,000 บาท จดทะเบียน 2015-06-21

> ITOS สะกด **"ธันเดอร์ ฟิน ฟิน"** (มีเว้นวรรค) K2 สะกด **"ธันเดอร์ ฟินฟิน"** — เป็นตัวอย่างจริงของปัญหา standardization ที่ [[Data Standardization & Quality]] พูดถึง

---

## Junk-table exclusion rules

178 ตารางจาก 542 ถูกตัดออกจาก inventory ด้วยกฎนี้ (เขียนไว้ใน `scripts\k2\k2_survey.py`):

| กฎ | ตัวอย่าง |
|---|---|
| row = 0 | `CUSTOMER_CARD_AR`, `MT_UPHONE_PERCENT_SRP_DG` |
| ลงท้าย `_BACKUP` `_Backup` `_BK` `_BAK` | `CUSTOMER_CARD_BACKUP`, `TTP_VAT_RPT_BAK` |
| ลงท้าย `_TEMP` `_TMP` `_TEST` `_DEMO` `_OLD` | `CUSTOMER_CARD_TEMP`, `CUSTOMER_CARD_TEST` |
| ลงท้ายวันที่ `_yymmdd` `_yyyymmdd` `_yyyy_n` | `CUSTOMER_CARD_220116`, `PROSPECT_CUSTOMER_20220105`, `REPORT_CUSTOMER_CARD_2023_3` |

`CUSTOMER_CARD` อย่างเดียวมีฝาแฝด 8 ตัว — **การเลือกตารางด้วยชื่ออย่างเดียวจะหยิบผิดตัวได้ง่ายมาก** ให้ยึด [[K2 - Table Inventory]]

---

## System-level observations

**ไม่มี foreign key** — 16 ตัวจาก 542 ตาราง ความสัมพันธ์ทุกอย่างในโฟลเดอร์นี้มาจากการ **ทดสอบ join จริงแล้วนับแถว** ไม่ใช่จาก metadata ถ้าจะสร้าง ER diagram อัตโนมัติจากฐานนี้จะได้แค่ 16 เส้น

**ทำ incremental ได้** — `PERSON`, `CONTRACT`, `APPLICATION`, `QUOTATION`, `REPAYMENT` มี `CREATE_DATE` และ `UPDATE_DATE` ครบ (`PERSON.UPDATE_DATE` ล่าสุด 2026-08-26 14:06)
> แก้ข้อสรุปเดิมใน [[ITOS Overview]] ที่บอกว่า "ดึง incremental ด้วย timestamp จาก K2 ไม่ได้" — ข้อสรุปนั้นมาจากดู `COLLECTION_OD_ASSIGNMENT` ตารางเดียวซึ่งเป็น extract ไม่ใช่ตารางต้นทาง **ตารางต้นทางมี timestamp**

**collation เป็น `SQL_Latin1_General_CP1_CI_AS`** ทั้งฐาน แม้คอลัมน์จะเป็น `nvarchar` — เก็บภาษาไทยได้ปกติ แต่ต้องใส่ `N''` นำหน้า literal ทุกครั้งที่เทียบภาษาไทย และตอน UNION กับ ITOS ต้อง `COLLATE DATABASE_DEFAULT` ตามที่ [[SQL & Source Schemas]] เขียนไว้

**สิทธิ์ที่ user `sapon.s` ไม่มี** — `VIEW SERVER STATE` (อ่าน `sys.dm_db_index_usage_stats` ไม่ได้ จึงบอกไม่ได้ว่าตารางไหน application อ่านจริง ต่างจากที่ทำกับ ITOS ได้) และ `VIEW DEFINITION` (อ่าน SQL ของ view 165 ตัวไม่ได้)

**`MS_Description` ไม่มีทั้งฐาน** เหมือน ITOS — ไม่มี data dictionary ในฐาน

---

## Typos already in production

นอกจาก `PRODUDCT_ID` และ `PRINCIPLE` ที่ vault บันทึกไว้แล้ว survey เจอเพิ่ม:

| ที่ควรเป็น | ที่มีจริง | อยู่ที่ |
|---|---|---|
| `IMPORT` | `BANK_IMPRORT` | ชื่อตาราง |
| `VOUCHER_NO` | `VOURCHER_NO` | `ACCOUNT` |
| `ACCOUNT_DESCRIPTION` | `ACCOUNT_DESCIPTION` | `ACCOUNT`, `ACCOUNT_RECEIVABLE` |
| `CONTRACT_NUMBER` | `CONTARCT_NUMBER` | `CONTACT_DEBT_COLLECTION` |
| `LIVING_TIME` | `A1_LIVEING_TIME` | `ADDRESS` (ทั้ง 5 ชุด) |
| `MOO` (หมู่) | `A1_MOI` | `ADDRESS` (ทั้ง 5 ชุด) |
| `GUARANTOR` | `GAURANTOR_FLAG` | `NCAP_INFORMATION` |

ต้อง map ให้ถูกที่ Bronze แก้ต้นทางไม่ได้แล้ว

---

## ที่มาของข้อมูลในโฟลเดอร์ K2

ตัวเลขและชื่อคอลัมน์ทุกอย่างมาจากการ query ฐาน `HPCOM7` โดยตรงเมื่อ 2026-08-26 (สิทธิ์ read-only)
ยกเว้น [[K2 - Business Rules]] ที่มาจากเอกสารความรู้ของทีม แล้วตรวจกับฐานจริงทุกข้อ

| ไฟล์ดิบใน `_raw/` | เนื้อหา |
|---|---|
| `tables.csv` | ทุกตาราง + จำนวนแถว + วันที่สร้าง/แก้ |
| `columns.csv` | ทุกคอลัมน์ + ชนิดข้อมูล |
| `indexes.csv` · `foreign_keys.csv` | index และ foreign key 16 ตัว |
| `views.csv` | รายชื่อ view 165 ตัว |
| [[samples-masked]] | ตัวอย่างข้อมูลที่ mask PII แล้ว |
| [[team-knowledge-K2-Database]] | เอกสารความรู้ต้นฉบับจากทีม |

สคริปต์ที่ใช้ดึง: `scripts/k2/k2_survey.py` · `scripts/k2/k2_samples.py`

## สถานะการเลิกใช้ K2

| ช่วงเวลา | สถานะ |
|---|---|
| ปัจจุบัน | migration K2 → ITOS **ยังไม่เสร็จ** |
| สิ้นปี 2026 | เป้าหมาย migrate ครบ **100%** |
| ถึงราว **Q1/2027** | K2 อาจใช้**คู่ขนาน**กับ ITOS |
| หลังจากนั้น | K2 เป็น **Historical / Legacy Source** · ITOS เป็น **Primary Source** |

**ข้อยกเว้น: UFUND Student** — ข้อมูลกลุ่มนี้อาจต้องอยู่บน K2 ต่อไป
เพราะยังไม่มี Credit History / Risk Assessment (นักศึกษายังไม่มีรายได้ประจำ)
และถ้าบริษัท IPO ต้องเก็บประวัติย้อนหลังให้ครบเพื่อรองรับการตรวจสอบจาก ธปท.

**ไม่ว่าอย่างไรก็ต้อง ingest K2 เข้า S3** — ทั้งเพื่อข้อมูลย้อนหลังและเพื่อกลุ่ม Student
→ [[2026-08-27 UFUND K2 และ ITOS]]

### ข้อมูลที่ K2 ไม่มีแล้ว

**NCB** — หยุดเก็บตั้งแต่ **08/2025** · ปัจจุบันอยู่ที่ ITOS เท่านั้น → [[ITOS Overview]]

---

## เชื่อมกับโน้ตอื่น

[[ITOS Overview]] · [[System Inventory]] · [[UFUND]] · [[Customer Identity]] · [[K2 + ITOS Integration]] · [[SQL & Source Schemas]] · [[K2 Issues]] · [[K2 + ITOS - Storage Sizing]]
