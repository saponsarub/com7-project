# ITEC Overview

ระบบค้าปลีกของ COM7 — เข้าถึงผ่าน **ฐาน MIS** ที่เปิดให้เฉพาะ **view** ไม่ให้แตะตารางจริง

| | |
|---|---|
| Server | `192.168.43.250,18963` |
| DBMS | **Microsoft SQL Server 2025** (17.0.1000.7) |
| ฐานข้อมูล | `_db1_3f9c2a7e-8b41-4d6f-9c25-1a7e5c0d2b8f` |
| สิ่งที่มองเห็น | **23 view · 297 คอลัมน์ · ไม่มี table เลย** |
| Schema | `rpt` (14 view) · `ci` (13 view) |
| ธุรกิจที่รองรับ | [[Retail]] — BaNANA · Studio7 · KingKong · BKK · iCare · TRUE by COM7 ฯลฯ |

**สำรวจจากฐานจริงเมื่อ 2026-08-28 ด้วยสิทธิ์ read-only**
พจนานุกรมรายฟิลด์ → [[ITEC - Data Dictionary]] · SQL ที่รันผ่านแล้ว → [[ITEC - Query Cookbook]]

---

## Where to start

| อยากรู้ | เปิด |
|---|---|
| แต่ละ view มีคอลัมน์อะไร ความหมายว่าอะไร | [[ITEC - Data Dictionary]] |
| ดึงยอดขาย · หาสินค้า · หาสาขา · เชื่อมลูกค้า | [[ITEC - Query Cookbook]] |
| ITEC เชื่อมกับ CRM ยังไง | [[CRM - Data Dictionary]] · หัวข้อ "เส้นทางเชื่อมลูกค้า" ด้านล่าง |
| คำถามที่ยังไม่มีคำตอบ | [[Source System Issues]] |

---

## โครงสร้างข้อมูล — star schema

```
                    ┌─────────────────────┐
                    │  rpt.fact_sales_itec │  79,828,304 แถว
                    │  บรรทัดขายรายชิ้น      │  2025-01-01 → 2026-08-09
                    └──────────┬──────────┘
       ┌───────────┬───────────┼───────────┬────────────┐
       ▼           ▼           ▼           ▼            ▼
  dim_item_itec  dim_branch  dim_mem    dim_officer  dim_sales_header
   216,009        3,205      22,042,404   35,763       8,987,607
   สินค้า          สาขา       ลูกค้า/สมาชิก  พนักงานขาย   หัวบิล/ใบกำกับ

  rpt.fact_bank_itec   18,294,666   ธุรกรรมบัตรฝั่ง ITEC (2023-01-01 → 2026-08-09)
  rpt.raw_bank_trans    7,060,688   ไฟล์ settlement ดิบจากธนาคาร
  rpt.fact_trans_fo   269,264,980   ธุรกรรมสต็อกจาก D365 F&O (2005-04-07 → 2026-12-19)
  rpt.onhandendmonth_itec 33,200,755  ยอดคงเหลือสิ้นเดือนรายเครื่อง (2025-01 → 2026-06)
```

### ชั้น `ci` — ข้อมูลที่ทำความสะอาด/สรุปแล้ว

| view | แถว | ทำอะไร |
|---|---:|---|
| `ci.clean_branch` | 3,205 | สาขาที่จัดหมวดแล้ว — แบรนด์ร้าน · ประเภท · ภูมิภาคไทย |
| `ci.clean_brand_itec` | 2,685 | แม็ปชื่อแบรนด์ดิบ → ชื่อมาตรฐาน |
| `ci.clean_category_ITEC` | 1,966 | แม็ปหมวดหมู่ดิบ → หมวดมาตรฐาน |
| `ci.clean_item_category_itec` | 216,009 | สินค้า + **72 flag** จำแนกประเภท + มิติสินค้า |
| `ci.monthly_item_sale_itec` | 7,268,065 | ยอดขายรายเดือน × สาขา × สินค้า |
| `ci.monthly_item_inventory_itec` | 18,070,548 | สต็อกรายเดือน × สาขา × สินค้า |
| `ci.integrated_sale_and_inventory` | 20,156,102 | รวมขาย + สต็อก + shelf life ไว้ด้วยกัน |
| `ci.creditcard_trn_itec` | 2,916,873 | ธุรกรรมบัตรฝั่ง ITEC เตรียม reconcile |
| `ci.creditcard_trn_bank` | 2,790,117 | ธุรกรรมบัตรฝั่งธนาคาร |
| `ci.creditcard_trn_summary` | 2,779,657 | ผลการจับคู่ + ธง split bill / หลายสาขา |
| `ci.trn_category_ITEC` | 44 | แม็ปวิธีชำระเงินฝั่ง ITEC |
| `ci.trn_category_BANK` | 38 | แม็ปวิธีชำระเงินฝั่งธนาคาร |
| `ci.thailand_map` | 77 | จังหวัด ไทย/อังกฤษ + ภูมิภาค |

> **`ci` = cleaned/integrated · `rpt` = reporting layer ที่ map ตรงกับระบบต้นทาง** `[อนุมาน]`

---

## ตัวเลขที่วัดได้จริง

|                      |             ค่า | หมายเหตุ                             |
| -------------------- | --------------: | ------------------------------------ |
| บรรทัดขายทั้งหมด     |  **79,828,304** | `fact_sales_itec`                    |
| บิลขายไม่ซ้ำ         |   **2,269,383** | `COUNT(DISTINCT SalesId)`            |
| สินค้าใน master      |     **216,009** | `dim_item_itec`                      |
| สาขา                 |       **3,205** | Active เพียง **50** · InActive 3,155 |
| พนักงานขาย           |          35,763 | Normal 6,995 · Cancel 28,768         |
| หัวบิล/ใบกำกับ       |       8,987,607 | `dim_sales_header_itec`              |
| ธุรกรรมสต็อกจาก D365 | **269,264,980** | view ใหญ่ที่สุด                      |

### ยอดขายรายปี (`Status = 0`)

| ปี | บรรทัด | จำนวนชิ้น | มูลค่า (บาท) |
|---|---:|---:|---:|
| 2025 | 64,642,548 | 67,871,979 | 236,494,082,308 |
| 2026 (ถึง 9 ส.ค.) | 13,659,434 | 39,354,446 | 69,357,025,836 |

> **[ต้องยืนยัน] ตัวเลข 236,000 ล้านบาทของปี 2025 สูงกว่ารายได้ที่ COM7 ประกาศต่อสาธารณะหลายเท่า**
> เป็นไปได้ว่ารวมธุรกรรมภายในกลุ่ม/โอนย้าย หรือ `SalesAmount` ไม่ใช่ยอดขายสุทธิ — **ห้ามใช้เป็นตัวเลขรายได้จนกว่าจะยืนยันกับเจ้าของระบบ**

---

## ⚠️ 4 กับดักที่ต้องรู้ก่อนใช้ข้อมูล

### 1. `fact_sales_itec.Status` — ต้องกรอง `= 0` เสมอ

| Status | บรรทัด | มูลค่ารวม | มูลค่าสูงสุดต่อบรรทัด |
|---:|---:|---:|---:|
| **0** | 78,301,982 | 305,851,108,143 | 1,144,785,568 |
| **1** | 1,526,322 | **7,831,115,816,063** | **837,948,011,738** |

Status 1 มีแค่ 1.9% ของบรรทัด แต่มูลค่ารวม **มากกว่า Status 0 ถึง 25 เท่า** และมีบรรทัดเดียวที่ 8.4 แสนล้านบาท
→ **ข้อมูลเสียหรือรายการทดสอบ ห้ามรวมในการวิเคราะห์** `[อนุมาน]`

### 2. สาขา Active มีแค่ 50 จาก 3,205

`BRANCH_STATUS` บอกว่า **InActive 3,155 · Active 50**
ถ้าจะนับสาขาที่เปิดจริง ต้องดู `ClosedDate IS NULL` หรือถามเจ้าของระบบว่าฟิลด์นี้หมายถึงอะไรกันแน่ — ตัวเลข 50 น้อยผิดปกติสำหรับเครือที่มีร้านทั่วประเทศ

### 3. `dim_mem_itec` ไม่ใช่ทะเบียนลูกค้า และ grain ไม่นิ่ง

- 22,042,404 แถว แต่มี `salesid` ไม่ซ้ำเพียง **3,003,828**
- 1 `salesid` มีได้ตั้งแต่ 1 ถึงหลายร้อยแถว (พบมากกว่า 580 รูปแบบจำนวนแถว)
- **ต้อง `SELECT DISTINCT salesid, salesbranch, crmid` ก่อน join ทุกครั้ง** ไม่งั้นยอดขายจะถูกคูณ

### 4. `memcode` มีรูปแบบปนกันจนใช้เป็นคีย์ไม่ได้

|            ความยาว |   จำนวนแถว | ขึ้นต้นด้วย 0 | เป็นตัวเลขล้วน |
| -----------------: | ---------: | ------------: | -------------: |
|                 13 | 13,869,950 |       150,934 |        180,077 |
|                 11 |  2,098,021 |       897,641 |         67,409 |
|                 12 |  1,580,170 |       544,854 |         66,975 |
|             **10** |  1,490,232 |     1,406,340 |  **1,351,390** |
|                 15 |  1,396,377 |        13,388 |            237 |
| อื่นๆ (16 ความยาว) |  1,607,654 |             — |              — |

ความยาว 10 ที่เป็นตัวเลขล้วนขึ้นต้นด้วย 0 = **เบอร์โทรศัพท์** (1.35 ล้านแถว)
ที่เหลือปนกันหลายรูปแบบ → **`memcode` เป็นช่องกรอกอิสระ ไม่ใช่รหัสที่มีรูปแบบเดียว**
→ ใช้ `crmid` เป็นคีย์แทน · ถ้าจำเป็นต้องใช้ `memcode` ต้องทำ pattern classification ก่อน

---

## เส้นทางเชื่อมลูกค้า — ITEC ↔ CRM

**`dim_mem_itec.crmid` คือรหัสสมาชิก CRM**

| | จำนวน | สัดส่วน |
|---|---:|---:|
| `crmid` รูปแบบ `M` + 12 ตัว (ตรงกับ `members.member_id`) | **12,590,750** | 57% |
| `crmid` เป็น `-` (placeholder ต้องถือเป็น NULL) | 42,613 | 0.2% |
| `crmid` เป็น NULL | 9,409,040 | 43% |

**เส้นทางเชื่อมมี 2 ทิศทาง — ยืนยันแล้วทั้งคู่**

```
ITEC                                    CRM
rpt.dim_mem_itec.crmid  ──────────────► members.member_id   (M + 12 ตัว)
rpt.dim_mem_itec.memcode ◄───────────── members.itec_cuscode (ต้องตรวจว่าตรงกับช่องไหน)
```

### ระบุตัวตนลูกค้าได้กี่ % ของยอดขาย

ทดสอบ join บิลขาย 200,000 บิลกับ `dim_mem_itec`:

| ผลลัพธ์ | จำนวน | สัดส่วน |
|---|---:|---:|
| **จับคู่ลูกค้าได้** | 178,454 | **89.2%** |
| จับคู่ไม่ได้ | 21,546 | 10.8% |

**89% ของบิลผูกกับลูกค้าได้** — เป็นตัวเลขที่ดีมากสำหรับงาน Customer 360 → [[Customer Identity]]

---

## คุณภาพการ join (ทดสอบจริง)

| จาก → ถึง                                   | คีย์                           | ตัวอย่างที่ทดสอบ |          ไม่จับคู่ |
| ------------------------------------------- | ------------------------------ | ---------------: | -----------------: |
| `fact_sales_itec` → `dim_item_itec`         | `ItemId`                       |          500,000 |       **0 (100%)** |
| `fact_sales_itec` → `dim_branch_itec`       | `SalesBranch` = `Branch`       |          500,000 |       **0 (100%)** |
| `fact_sales_itec` → `dim_officer_itec`      | `SalesOfficerId` = `OfficerID` |          200,000 |                  4 |
| `fact_sales_itec` → `dim_mem_itec`          | `SalesId` + `SalesBranch`      |          200,000 |     21,546 (10.8%) |
| `fact_sales_itec` → `dim_sales_header_itec` | `SalesId` + `SalesBranch`      |          200,000 | **45,364 (22.7%)** |

> **หัวบิลหายไป 22.7%** — บรรทัดขายที่ไม่มีเลขที่ใบกำกับภาษี ต้องถามว่าเป็นการขายประเภทไหน

`ci.clean_branch` กับ `rpt.dim_branch_itec` มี 3,205 แถวเท่ากันและจับคู่ครบ 100%

---

## ข้อมูลอะไรอยู่ที่ไหน

### แบรนด์ร้าน — `ci.clean_branch.SHOP_BRAND`

| แบรนด์      |  สาขา |     | แบรนด์   | สาขา |
| ----------- | ----: | --- | -------- | ---: |
| **BaNANA**  | 1,033 |     | True     |   70 |
| Franchise   |   715 |     | Event    |   67 |
| **Studio7** |   236 |     | iCare    |   61 |
| NA          |   170 |     | Xiaomi   |   52 |
| BeBe Phone  |   148 |     | Samsung  |   44 |
| Consign     |   133 |     | Oppo     |   35 |
| KingKong    |   125 |     | Bb+Bplay |   28 |
| BKK         |    85 |     | Huawei   |   27 |

อีก 14 แบรนด์: Online 22 · E-Quip 20 · VIVO 19 · Warehouse 15 · CaseClub 11 · Realme 10 · FCC 9 · Solar Cell 7 · EduProject 7 · Service 7 · Wholesale 5 · HeadOffice 5 · Honor 5 · GA 5

**ช่องทาง:** Physical 3,181 · Online 24
**ประเภททำเล:** In Mall 1,786 · Other & Stand Alone 1,320 · NA 75 · **In University 24**
**ภูมิภาค:** ภาคกลาง 1,712 · ตะวันออกเฉียงเหนือ 582 · ใต้ 425 · เหนือ 408 · ไม่ระบุ 78

> **In University 24 สาขา** เชื่อมโยงตรงกับกลุ่มเป้าหมายนักศึกษาของ [[UFUND]]

### แบรนด์สินค้า — `rpt.dim_item_itec.Brand`

APPLE **24,200** · (NULL) 11,745 · SAMSUNG 10,095 · FOX 5,831 · XIAOMI 5,390 · ASUS 5,329 ·
SERVICE 4,217 · SONY 3,685 · ACER 3,600 · OPPO 3,310 · LENOVO 2,742 · HP 2,623 · MSI 2,124 ·
KING KONG 2,055 · HUAWEI 1,944 · DELL 1,911 · LG 1,736 · CASE CLUB 1,689 · VIVO 1,563 · TRUE_IPHONE 1,539

> `Brand` เป็น NULL 11,745 รายการ (5.4%) — ต้องใช้ `ci.clean_brand_itec` ช่วยเติม

### มิติสินค้า — `ci.clean_item_category_itec`

| Main_Product_Dimension | รายการ |     | Main_Product_Dimension    | รายการ |
| ---------------------- | -----: | --- | ------------------------- | -----: |
| Accessory and Others   | 67,406 |     | Smart Watch               |  6,572 |
| **Smart Phone**        | 52,112 |     | Camera                    |  5,434 |
| PC                     | 19,581 |     | Adapter/Charger/Powerbank |  4,440 |
| Notebook               | 17,305 |     | Software                  |  1,055 |
| PC&Notebook Component  | 13,126 |     | Console Gaming            |    893 |
| Tablet                 |  9,942 |     | Insurance                 |    649 |
| Mouse&Keyboard         |  8,773 |     |                           |        |
| HeadSet&Earpiece       |  8,721 |     |                           |        |

**มิติอื่น:** `Sale_Type` = Normal Sale 201,437 · Promotion Sale 14,572
`Product_Dimension` = Normal Product 196,756 · **Demo Product 19,253**
`Product_Purpose` = Ordinary 205,577 · **Gaming 10,432**

### วิธีชำระเงิน — `ci.trn_category_ITEC` (44 แบบ)

| ประเภท | ตัวอย่าง |
|---|---|
| **Credit Card** | KTC · SCB · KBank · BAY · BBL · TTB · UOB · AEON · CITIBANK · AMEX — แยก "รูดเต็มจำนวน" กับ "รูดผ่อนชำระ" |
| **QR Code** | PromptPay (KBank · BBL) · QR VISA & Master (BBL) |
| **Payment Gateway** | ShopeePay · Alipay (KBank) · Robinhood · LINE MAN |
| **Personal Loan** | SG Finance+ · Samsung Finance+ · Pay Next Extra (ASEND) |
| Unknown | NPI 2024 · Ksher (ตู้ติดฟิล์ม) |

ฝั่งธนาคารมี 38 แบบใน `ci.trn_category_BANK` — โครงสร้างเดียวกัน ใช้จับคู่ reconcile

---

## `rpt.fact_trans_fo` — ข้อมูลจาก D365 F&O

view ใหญ่ที่สุด **269 ล้านแถว** ครอบคลุม **2005-04-07 ถึง 2026-12-19** (มีวันที่อนาคต)

### แยกตามบริษัท — `CompanyCode`

| บริษัท | ธุรกรรม | | บริษัท | ธุรกรรม |
|---|---:|---|---|---:|
| **com7** | 245,775,416 | | drl | 335,890 |
| **dou7** (Double7) | 12,700,266 | | gi + gi01–gi12 | ~197,000 |
| **bnn** (BaNANA) | 4,936,997 | | pss (Prime Solution) | 2,445 |
| **drph** | 3,612,265 | | nov (Novus) | 461 |
| lor | 1,703,745 | | | |

> **`drph` = Dr.Pharma มีข้อมูล 3.6 ล้านแถว** ทั้งที่ [[Group Structure]] ระบุว่าตัดออกจาก reference ปัจจุบัน
> → ต้องยืนยันว่าเป็นข้อมูลย้อนหลังของธุรกิจที่เลิกแล้ว หรือยังดำเนินการอยู่
> **`lor` และ `drl` ยังไม่รู้ว่าคือบริษัทอะไร**

### ประเภทธุรกรรม — `Transaction_Type`

Sales order 101,896,279 · **Transfer 100,456,283** · Purchase order 39,334,948 · Transaction 17,330,898 ·
Transfer order shipment 4,577,112 · Transfer order receive 4,542,654 · Weighted average inventory closing 1,022,850 ·
Counting 43,087 · Inventory adjustment 32,133 · Fixed assets 28,736

> **Transfer เกือบเท่า Sales order** — การโอนย้ายสต็อกระหว่างสาขาเป็นกิจกรรมหลักพอๆ กับการขาย
> เวลาคำนวณยอดขาย **ต้องกรอง `Transaction_Type = 'Sales order'`** ไม่งั้นนับซ้ำ

**สอดคล้องกับที่ประชุม ERP บอกว่า D365 เป็นระบบปลายทางที่ replicate จาก BU** → [[2026-08-26 ERP]]

---

## ⚠️ ข้อมูลอ่อนไหวในฐานนี้

| view | ฟิลด์ | ระดับ |
|---|---|---|
| `ci.creditcard_trn_bank` | `BANK_CC_NO` · `BANK_CREDIT_CARD_NO` · `BANK_CREDIT_CARD_NO2` · `BANK_FIRST6` · `BANK_LAST4` | 🔴 **เลขบัตรเครดิต — ห้าม ingest · PCI-DSS** |
| `rpt.raw_bank_trans` | `CC NO_` · `FIRST 6-DIGIT` · `LAST 4-DIGIT` | 🔴 **เลขบัตรเครดิต** |
| `ci.creditcard_trn_itec` | `ITEC_CUSTOMER_NAME` · `ITEC_CUSTOMER_INVOICE_NAME` · `ITEC_LAST4` | 🟠 ชื่อลูกค้า + 4 ตัวท้ายบัตร |
| `rpt.dim_mem_itec` | `Name` · `memcode` (มีเบอร์โทรปน) · `crmid` | 🟠 ชื่อและช่องทางติดต่อลูกค้า |
| `rpt.fact_bank_itec` | `LAST 4-DIGIT` · `APPROVAL CODE` | 🟡 |
| `rpt.dim_officer_itec` | `OfficerName` | 🟡 ข้อมูลพนักงาน |

**สคริปต์สำรวจในโปรเจกต์นี้ไม่แตะ view ที่มีเลขบัตรเลย** — นับแถวและอ่าน metadata เท่านั้น
กติกา → [[Consent & PDPA]]

---

## เทียบกับ K2

| | ITEC (MIS) | K2 (`HPCOM7`) |
|---|---|---|
| สิ่งที่เข้าถึงได้ | **view เท่านั้น 23 ตัว** | ตารางจริง 542 ตัว |
| โครงสร้าง | **star schema สะอาด** dim/fact ชัดเจน | ตารางดิบ · ไม่มี FK · มีตารางขยะ 178 ตัว |
| ชั้นทำความสะอาด | **มีอยู่แล้ว** (schema `ci`) | ไม่มี ต้องทำเอง |
| ขนาดใหญ่สุด | 269M (`fact_trans_fo`) | 239M (`CreditScrolling_Logs_Contract`) |
| ช่วงข้อมูลขาย | 2025-01 → ปัจจุบัน (สั้น) | 2020-07 → ปัจจุบัน |
| คำอธิบายในฐาน | ไม่มี | ไม่มี |

> **ITEC พร้อมกว่ามาก** — มีคนทำ dimensional model และชั้น clean ไว้แล้ว
> งานที่เหลือคือ **ยืนยันความหมายกับเจ้าของระบบ** ไม่ใช่สร้างโครงสร้างใหม่

---

## ที่มาของข้อมูลในหน้านี้

สำรวจฐานโดยตรงเมื่อ **2026-08-28** ด้วยสิทธิ์ read-only ของ user `mis_dtsci_s_sapon`
ทุกตัวเลขมาจากการ query จริง ไม่ใช่จากเอกสาร

| สคริปต์ | ทำอะไร |
|---|---|
| `scripts/itec/itec_probe.py` | หาว่าฐานไหน/สิ่งใดเข้าถึงได้ |
| `scripts/itec/itec_survey.py` | ดึงรายชื่อ view · คอลัมน์ · จำนวนแถว → `_raw/itec-views.csv` · `_raw/itec-columns.csv` |
| `scripts/itec/itec_profile.py` | โปรไฟล์ค่าจริงของ dimension |
| `scripts/itec/itec_joins.py` | ทดสอบเส้นทาง join และ grain |

ทุกสคริปต์อ่าน credential จาก env `MIS_USER` / `MIS_PWD` **ไม่ hardcode**

> 🔴 **รหัสผ่านของ user นี้ยังอยู่ใน git history** (commit `586cab2`, ไฟล์ `TESTCONNECT.py` เดิม) — **ควรเปลี่ยนรหัสผ่าน**

---

## เชื่อมกับโน้ตอื่น

[[ITEC - Data Dictionary]] · [[ITEC - Query Cookbook]] · [[Retail]] · [[CRM - Data Dictionary]] · [[Customer Identity]] · [[System Inventory]] · [[K2 Overview]] · [[Source System Issues]]
