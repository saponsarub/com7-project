# ITEC - Data Dictionary

พจนานุกรมข้อมูลของ **23 view · 297 คอลัมน์** ในฐาน MIS
ภาพรวมระบบ → [[ITEC Overview]] · SQL ที่ใช้ได้จริง → [[ITEC - Query Cookbook]]

ชนิดข้อมูลและจำนวนแถวมาจากการ query ฐานจริงเมื่อ 2026-08-28
ไฟล์ดิบ: `_raw/itec-views.csv` · `_raw/itec-columns.csv`

---

## สารบัญ

|   # | View                                                                      |         แถว | คอลัมน์ | ประเภท       |
| --: | ------------------------------------------------------------------------- | ----------: | ------: | ------------ |
|   1 | [`rpt.fact_sales_itec`](#1-rptfact_sales_itec)                            |  79,828,304 |      12 | Fact         |
|   2 | [`rpt.fact_bank_itec`](#2-rptfact_bank_itec)                              |  18,294,666 |       8 | Fact         |
|   3 | [`rpt.fact_trans_fo`](#3-rptfact_trans_fo)                                | 269,264,980 |      20 | Fact         |
|   4 | [`rpt.onhandendmonth_itec`](#4-rptonhandendmonth_itec)                    |  33,200,755 |       6 | Fact         |
|   5 | [`rpt.raw_bank_trans`](#5-rptraw_bank_trans)                              |   7,060,688 |      11 | Fact (raw)   |
|   6 | [`rpt.dim_item_itec`](#6-rptdim_item_itec)                                |     216,009 |       6 | Dimension    |
|   7 | [`rpt.dim_branch_itec`](#7-rptdim_branch_itec)                            |       3,205 |      13 | Dimension    |
|   8 | [`rpt.dim_mem_itec`](#8-rptdim_mem_itec)                                  |  22,042,404 |       5 | Dimension    |
|   9 | [`rpt.dim_officer_itec`](#9-rptdim_officer_itec)                          |      35,763 |       7 | Dimension    |
|  10 | [`rpt.dim_sales_header_itec`](#10-rptdim_sales_header_itec)               |   8,987,607 |       6 | Dimension    |
|  11 | [`ci.clean_branch`](#11-ciclean_branch)                                   |       3,205 |      17 | Clean        |
|  12 | [`ci.clean_item_category_itec`](#12-ciclean_item_category_itec)           |     216,009 |      78 | Clean        |
|  13 | [`ci.clean_brand_itec`](#13-ciclean_brand_itec)                           |       2,685 |       2 | Mapping      |
|  14 | [`ci.clean_category_ITEC`](#14-ciclean_category_itec)                     |       1,966 |       4 | Mapping      |
|  15 | [`ci.thailand_map`](#15-cithailand_map)                                   |          77 |       4 | Mapping      |
|  16 | [`ci.trn_category_ITEC`](#16-citrn_category_itec)                         |          44 |       4 | Mapping      |
|  17 | [`ci.trn_category_BANK`](#17-citrn_category_bank)                         |          38 |       4 | Mapping      |
|  18 | [`ci.monthly_item_sale_itec`](#18-cimonthly_item_sale_itec)               |   7,268,065 |       8 | Aggregate    |
|  19 | [`ci.monthly_item_inventory_itec`](#19-cimonthly_item_inventory_itec)     |  18,070,548 |       5 | Aggregate    |
|  20 | [`ci.integrated_sale_and_inventory`](#20-ciintegrated_sale_and_inventory) |  20,156,102 |      25 | Aggregate    |
|  21 | [`ci.creditcard_trn_itec`](#21-cicreditcard_trn_itec)                     |   2,916,873 |      21 | 🔴 Reconcile |
|  22 | [`ci.creditcard_trn_bank`](#22-cicreditcard_trn_bank)                     |   2,790,117 |      18 | 🔴 Reconcile |
|  23 | [`ci.creditcard_trn_summary`](#23-cicreditcard_trn_summary)               |   2,779,657 |      13 | Reconcile    |

🔴 = มีเลขบัตรเครดิต · ห้าม ingest

---

# Fact views

## 1. `rpt.fact_sales_itec`

**บรรทัดขายรายชิ้น — view ที่สำคัญที่สุดของระบบ**
79,828,304 แถว · 2,269,383 บิลไม่ซ้ำ · ช่วงข้อมูล **2025-01-01 → 2026-08-09**

| ฟิลด์               | ชนิด      | คำอธิบาย                                                               |
| ------------------- | --------- | ---------------------------------------------------------------------- |
| `SalesId` 🔑        | int       | เลขที่บิลขาย — ใช้คู่กับ `SalesBranch` เสมอ ไม่ unique เดี่ยวๆ         |
| `SalesBranch` 🔑    | int       | รหัสสาขาที่ขาย → `dim_branch_itec.Branch`                              |
| `ItemId` 🔗         | varchar   | รหัสสินค้า → `dim_item_itec.ItemId` (จับคู่ได้ 100%)                   |
| `SerialNo`          | varchar   | หมายเลขเครื่อง — ใช้ตามรอยเครื่องรายตัว                                |
| `SalesQty`          | int       | จำนวนที่ขาย                                                            |
| `SalesAmount`       | numeric   | ยอดขาย                                                                 |
| `CostAmount`        | numeric   | ต้นทุน                                                                 |
| `GPAmount`          | numeric   | กำไรขั้นต้น = `SalesAmount − CostAmount`                               |
| `GP %`              | float     | อัตรากำไรขั้นต้น — **ชื่อคอลัมน์มีช่องว่างและ `%` ต้องครอบด้วย `[ ]`** |
| **`Status`**        | int       | **0 = ปกติ (78,301,982) · 1 = ผิดปกติ (1,526,322)**                    |
| `SalesCrDatetime`   | datetime2 | เวลาที่สร้างรายการ                                                     |
| `SalesOfficerId` 🔗 | int       | พนักงานขาย → `dim_officer_itec.OfficerID`                              |

> ⚠️ **`Status = 1` มียอดรวม 7.8 ล้านล้านบาท** (มากกว่า Status 0 ถึง 25 เท่า) และมีบรรทัดเดียวที่ 837,948,011,738 บาท
> **ต้องใส่ `WHERE Status = 0` ทุกครั้ง**

**Grain:** 1 แถว = 1 บรรทัดสินค้าในบิล (79.8M บรรทัด / 2.27M บิล ≈ **35 บรรทัดต่อบิล** — สูงผิดปกติ ต้องยืนยัน)

---

## 2. `rpt.fact_bank_itec`

**ธุรกรรมบัตรที่บันทึกฝั่ง ITEC** · 18,294,666 แถว · **2023-01-01 → 2026-08-09**

| ฟิลด์           | ชนิด    | คำอธิบาย                                       |
| --------------- | ------- | ---------------------------------------------- |
| `SalesId` 🔗    | int     | เชื่อมกลับไป `fact_sales_itec.SalesId`         |
| `STORE ID`      | int     | รหัสร้าน — ชื่อมีช่องว่าง ต้องครอบ `[ ]`       |
| `TYPE` 🔗       | varchar | วิธีชำระเงิน → `ci.trn_category_ITEC.TYPE`     |
| `LAST 4-DIGIT`  | varchar | 🟡 4 ตัวท้ายบัตร                               |
| `APPROVAL CODE` | varchar | รหัสอนุมัติจากธนาคาร — ใช้จับคู่กับ settlement |
| `TRANS AMT`     | decimal | ยอดรูด                                         |
| `TERMINAL ID`   | varchar | เครื่อง EDC                                    |
| `TRANS DATE`    | date    | วันที่รูด                                      |

---

## 3. `rpt.fact_trans_fo`

**ธุรกรรมสต็อกจาก Dynamics 365 F&O — view ใหญ่ที่สุด 269,264,980 แถว**
ช่วงข้อมูล **2005-04-07 → 2026-12-19** (มีวันที่ล่วงหน้า)

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `FO-ITEMNO` | varchar | รหัสสินค้าฝั่ง D365 |
| `ITEC-ITEMNO` 🔗 | varchar | รหัสสินค้าฝั่ง ITEC — **คีย์เชื่อมสองระบบ** |
| `INVENTSERIALID` | varchar | หมายเลขเครื่อง |
| `INVENTBATCHID` | varchar | เลข batch |
| `INVENTLOCATIONID` | varchar | คลัง/ที่เก็บ |
| `DATEPHYSICAL` | datetime2 | วันที่เคลื่อนไหวจริง (รับ/จ่ายของ) |
| `DATEFINANCIAL` | datetime2 | วันที่ลงบัญชี |
| `REFERENCECATEGORY` | bigint | รหัสหมวดอ้างอิงของ D365 |
| **`Transaction_Type`** | varchar | ประเภทธุรกรรม — ดูค่าด้านล่าง |
| `Ref.DocNum` | varchar | เลขที่เอกสารอ้างอิง |
| `QTY` | decimal | จำนวน |
| `costamountstd` | decimal | ต้นทุนมาตรฐาน |
| `COSTAMOUNTPOSTED` | decimal | ต้นทุนที่ลงบัญชีแล้ว |
| `COSTAMOUNTADJUSTMENT` | decimal | ปรับปรุงต้นทุน |
| `RealCost` | decimal | ต้นทุนจริง |
| `InventTrans_RECID` | bigint | RecId ของ D365 |
| `TransOrigin_RECID` | bigint | RecId ต้นทางของ D365 |
| `inventdimid` | varchar | มิติสินค้าคงคลังของ D365 |
| `Transorigin_Sinkdate` | datetime2 | เวลาที่ sync เข้ามา |
| **`CompanyCode`** | varchar | นิติบุคคล — ดูค่าด้านล่าง |

### ค่าใน `Transaction_Type`

| ค่า | แถว |
|---|---:|
| Sales order | 101,896,279 |
| **Transfer** | 100,456,283 |
| Purchase order | 39,334,948 |
| Transaction | 17,330,898 |
| Transfer order shipment | 4,577,112 |
| Transfer order receive | 4,542,654 |
| Weighted average inventory closing | 1,022,850 |
| Counting | 43,087 |
| Inventory adjustment | 32,133 |
| Fixed assets | 28,736 |

> **ต้องกรอง `Transaction_Type = 'Sales order'` ถ้าจะนับยอดขาย** — Transfer มีเกือบเท่ากันและไม่ใช่การขาย

### ค่าใน `CompanyCode`

com7 245,775,416 · dou7 12,700,266 · bnn 4,936,997 · **drph 3,612,265** · lor 1,703,745 ·
drl 335,890 · gi 71,399 · gi01–gi12 รวม ~126,000 · pss 2,445 · nov 461

> `drph` = Dr.Pharma · `pss` = Prime Solution · `nov` = Novus · **`lor` และ `drl` ยังไม่ทราบ**

---

## 4. `rpt.onhandendmonth_itec`

**ยอดคงเหลือสิ้นเดือน รายเครื่อง** · 33,200,755 แถว · **2025-01-01 → 2026-06-01**

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `OnHandAsOf` | date | วันที่ตัดยอด (ต้นเดือน) |
| `Branch` 🔗 | int | สาขา |
| `Product` 🔗 | varchar | รหัสสินค้า |
| `Serial` | varchar | หมายเลขเครื่อง |
| `TransferingTo` | int | สาขาปลายทางถ้ากำลังโอนย้าย |
| `Qty` | int | จำนวนคงเหลือ |

**มี Serial ระดับเครื่อง** → ตามรอยได้ว่าเครื่องไหนอยู่สาขาไหนเมื่อไหร่

---

## 5. `rpt.raw_bank_trans` 🔴

**ไฟล์ settlement ดิบจากธนาคาร** · 7,060,688 แถว

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `SET DATE` | date | วันที่ธนาคารโอนเงินเข้า |
| `TERMINAL ID` | varchar | เครื่อง EDC |
| `MERCHANT ID` | varchar | รหัสร้านค้าฝั่งธนาคาร |
| `APPROVAL CODE` | varchar | รหัสอนุมัติ |
| `TRANS DATE` | date | วันที่ทำรายการ |
| `TRANS AMT` | decimal | ยอด |
| `TYPE` | varchar | ประเภทรายการฝั่งธนาคาร |
| `LAST 4-DIGIT` | varchar | 🔴 |
| `FIRST 6-DIGIT` | varchar | 🔴 BIN — ระบุธนาคาร/ประเภทบัตรได้ |
| `STORE ID` | varchar | รหัสร้าน |
| **`CC NO_`** | varchar | 🔴 **เลขบัตรเครดิต — ห้าม ingest** |

---

# Dimension views

## 6. `rpt.dim_item_itec`

**Master สินค้า** · 216,009 แถว

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `ItemId` 🔑 | varchar | รหัสสินค้า |
| `ItemName` | varchar | ชื่อสินค้า |
| `CategoryName` | varchar | หมวดหมู่ดิบ |
| `SubCategoryName` | varchar | หมวดย่อยดิบ |
| `Model/Series` | varchar | รุ่น/ซีรีส์ — **ชื่อคอลัมน์มี `/` ต้องครอบ `[ ]`** |
| `Brand` | varchar | แบรนด์ — **NULL 11,745 รายการ (5.4%)** |

**Brand ยอดนิยม:** APPLE 24,200 · SAMSUNG 10,095 · FOX 5,831 · XIAOMI 5,390 · ASUS 5,329 · SONY 3,685 · ACER 3,600

**CategoryName ยอดนิยม:** Promo Operator 11,977 · Cases 11,018 · Notebook 10,279 · Computer Cases 9,413 ·
Bebephone 9,165 · BTB Demo 7,775 · Apple Service 7,280 · Reserve 6,696 · Bag 6,321 · IT Accessories 6,244 ·
Smartphone 5,844 · Headphone 5,482 · Mac 5,407

> **หมวดหมู่ดิบไม่เป็นมาตรฐาน** — มีทั้งอังกฤษ ("Smartphone") และไทย ("รายการส่งเสริมการขาย")
> ให้ใช้ `ci.clean_category_ITEC` แปลงก่อน

---

## 7. `rpt.dim_branch_itec`

**Master สาขา** · 3,205 แถว

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `Branch` 🔑 | int | รหัสสาขา |
| `BranchName` | varchar | ชื่อสาขา |
| `BranchType` | varchar | แบรนด์ร้าน — BaNANA 891 · Franchise 715 · Studio7 236 · NULL 170 · BeBe Phone 148 · Consign 133 · KingKong 125 · **BaNANA IT 100** · BKK 85 · True 70 |
| `Province` | varchar | จังหวัด (อังกฤษ) |
| `Region` | varchar | ภูมิภาค (อังกฤษ) |
| `Latitude` · `Longitude` | decimal | **พิกัดสาขา — ใช้ทำ geo analytics ได้** |
| `BuildingCompetitor` | varchar | คู่แข่งในอาคารเดียวกัน |
| `Address` | varchar | ที่อยู่ |
| `OpenedDate` · `ClosedDate` | datetime2 | วันเปิด/ปิดสาขา |
| `Status` | varchar | สถานะ |
| `UpdateDatetime` | datetime2 | เวลาแก้ไขล่าสุด |

> `BranchType` มีค่าที่ `ci.clean_branch.SHOP_BRAND` ไม่มี เช่น **BaNANA IT (100)** และ **BNN Index (31)**
> — ชั้น clean ยุบรวมเข้ากับ BaNANA `[อนุมาน]`

---

## 8. `rpt.dim_mem_itec`

**เชื่อมบิลขายกับลูกค้า** · 22,042,404 แถว · ⚠️ **ไม่ใช่ทะเบียนลูกค้า**

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `salesid` 🔑 | int | เลขที่บิล → `fact_sales_itec.SalesId` |
| `salesbranch` 🔑 | int | สาขา → `fact_sales_itec.SalesBranch` |
| `memcode` | varchar | 🟠 รหัสสมาชิก/ช่องทางติดต่อ — **รูปแบบปนกัน ใช้เป็นคีย์ไม่ได้** |
| **`crmid`** 🔗 | varchar | 🟠 **รหัสสมาชิก CRM → `members.member_id`** |
| `Name` | varchar | 🟠 ชื่อลูกค้า |

### สถิติที่วัดได้

| | จำนวน |
|---|---:|
| แถวทั้งหมด | 22,042,404 |
| `salesid` ไม่ซ้ำ | 3,003,828 |
| `memcode` ไม่ซ้ำ | 10,941,598 |
| `crmid` ไม่ซ้ำ | 6,016,959 |
| `crmid` เป็น NULL | 9,409,040 (43%) |
| `memcode` เป็น NULL | 0 |

### รูปแบบ `crmid`

| ความยาว | ตัวแรก | แถว | ความหมาย |
|---:|---|---:|---|
| 13 | `M` | **12,590,750** | **รหัสสมาชิก CRM** — รูปแบบเดียวกับ `members.member_id` |
| 1 | `-` | 42,613 | placeholder — **ต้องถือเป็น NULL** |
| 11 | `b` | 1 | ข้อมูลเสีย |

### รูปแบบ `memcode` — ปนกันมาก

| ความยาว | แถว | ตัวเลขล้วน | ตีความ |
|---:|---:|---:|---|
| 13 | 13,869,950 | 180,077 | ส่วนใหญ่มีตัวอักษรปน |
| 11 | 2,098,021 | 67,409 | |
| 12 | 1,580,170 | 66,975 | |
| **10** | 1,490,232 | **1,351,390** | **เบอร์โทรศัพท์** (ขึ้นต้น 0) |
| 15 | 1,396,377 | 237 | |
| อีก 16 ความยาว | 1,607,654 | — | ตั้งแต่ 1 ถึง 20 ตัวอักษร |

> **`memcode` เป็นช่องกรอกอิสระ** ไม่มีรูปแบบเดียว — พนักงานกรอกได้ทั้งเบอร์โทร รหัสสมาชิก และอย่างอื่น
> ถ้าต้องใช้ ต้องทำ pattern classification ก่อน → [[Data Standardization & Quality]]

### ⚠️ Grain ไม่นิ่ง

1 `salesid` มีได้ตั้งแต่ 1 ถึงหลายร้อยแถว — พบมากกว่า **580 รูปแบบจำนวนแถวต่อ salesid**

| แถวต่อ salesid | จำนวน salesid |
|---:|---:|
| 1 | 2,096,875 |
| 2 | 205,895 |
| 3 | 91,041 |
| 4 | 44,200 |
| 8–17 | ~280,000 |
| 33–38 | ~37,000 |

**ต้อง `SELECT DISTINCT salesid, salesbranch, crmid` ก่อน join เสมอ** ไม่งั้นยอดขายจะถูกคูณ

---

## 9. `rpt.dim_officer_itec`

**Master พนักงานขาย** · 35,763 แถว

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `OfficerID` 🔑 | int | รหัสพนักงาน |
| `OfficerName` | **int** | 🟡 ชื่อพนักงาน — **ชนิดเป็น int ทั้งที่ควรเป็นข้อความ ⚠️ ผิดปกติ** |
| `BeginWorkDate` · `EndWorkDate` | datetime2 | วันเริ่ม/สิ้นสุดงาน |
| `Status` | varchar | **Cancel 28,768 · Normal 6,995** |
| `CreatedDatetime` · `UpdatedDatetime` | datetime2 | |

> **พนักงาน Cancel มากกว่า Normal 4 เท่า** — สะท้อนอัตราการเข้าออกสูงของธุรกิจค้าปลีก `[อนุมาน]`
> `OfficerName` เป็น `int` เป็นความผิดปกติของ schema ที่ต้องถามเจ้าของระบบ

---

## 10. `rpt.dim_sales_header_itec`

**หัวบิล / ข้อมูลใบกำกับภาษี** · 8,987,607 แถว

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `SalesID` 🔑 | int | เลขที่บิล |
| `SalesBranch` 🔑 | int | สาขา |
| `DocRef` | varchar | เลขที่เอกสารอ้างอิง |
| `TAX_Invoice` | varchar | เลขที่ใบกำกับภาษี |
| `Invoice_Name` | varchar | 🟠 ชื่อผู้รับใบกำกับ |
| `Sales_Officer` 🔗 | int | พนักงานขาย |

> **บรรทัดขาย 22.7% ไม่มีหัวบิล** (ทดสอบ 200,000 บรรทัด ไม่จับคู่ 45,364)

---

# Clean views (schema `ci`)

## 11. `ci.clean_branch`

**สาขาที่จัดหมวดหมู่แล้ว** · 3,205 แถว · จับคู่กับ `dim_branch_itec` ครบ 100%

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `Branch_ID` 🔑 | int | รหัสสาขา |
| `BranchName` | varchar | ชื่อดิบ |
| `CleanBranchName` | nvarchar | **ชื่อที่ทำความสะอาดแล้ว** |
| `BranchType` | varchar | ประเภทดิบ |
| `Address` | varchar | ที่อยู่ |
| `OpenedDate` · `ClosedDate` | datetime2 | วันเปิด/ปิด |
| **`SALE_CHANNEL`** | varchar | **Physical 3,181 · Online 24** |
| **`SHOP_BRAND`** | varchar | แบรนด์ร้านมาตรฐาน 30 ค่า |
| **`SHOP_TYPE`** | varchar | **In Mall 1,786 · Other & Stand Alone 1,320 · NA 75 · In University 24** |
| `SHOP_TYPE_BRAND` | varchar | ประเภท + แบรนด์รวมกัน |
| **`BRANCH_STATUS`** | varchar | **InActive 3,155 · Active 50** ⚠️ |
| `CLEAN_PROVINCE` | varchar | จังหวัดมาตรฐาน |
| `Province_EN` · `Province_TH` | varchar/nvarchar | จังหวัด 2 ภาษา |
| `Region_EN` · `Region_TH` | varchar/nvarchar | ภูมิภาค — ภาคกลาง 1,712 · อีสาน 582 · ใต้ 425 · เหนือ 408 · NULL 78 |

### `SHOP_BRAND` ทั้ง 30 ค่า

BaNANA 1,033 · Franchise 715 · Studio7 236 · NA 170 · BeBe Phone 148 · Consign 133 · KingKong 125 ·
BKK 85 · True 70 · Event 67 · iCare 61 · Xiaomi 52 · Samsung 44 · Oppo 35 · Bb+Bplay 28 · Huawei 27 ·
Online 22 · E-Quip 20 · VIVO 19 · Warehouse 15 · CaseClub 11 · Realme 10 · FCC 9 · Solar Cell 7 ·
EduProject 7 · Service 7 · Wholesale 5 · HeadOffice 5 · Honor 5 · GA 5

> ⚠️ **`BRANCH_STATUS` Active แค่ 50 สาขา** — น้อยผิดปกติ ต้องถามว่าฟิลด์นี้หมายถึงอะไร

---

## 12. `ci.clean_item_category_itec`

**สินค้า + ระบบจำแนกอัตโนมัติ 72 ฟิลด์** · 216,009 แถว

### ฟิลด์ฐาน (6)

`ItemId` · `ItemName` · `CategoryName` · `SubCategoryName` · `Model/Series` · `Brand`
— เหมือน `dim_item_itec` ทุกอย่าง

### ฟิลด์จำแนกประเภท `IS_*` (66 ฟิลด์ · int 0/1)

สร้างจาก `CASE WHEN ItemName LIKE '%คำ%' OR CategoryName LIKE '%คำ%' OR SubCategoryName LIKE '%คำ%' THEN 1 ELSE 0 END`

| กลุ่ม | ฟิลด์ |
|---|---|
| **สถานะสินค้า** | `IS_Promotion` · `IS_Demo_Product` · `IS_Gaming` |
| **มือถือ/แท็บเล็ต** | `IS_Smartphone` · `IS_Mobile` · `IS_iPhone` · `IS_Galaxy` · `IS_iPad` · `IS_Tablet` |
| **สวมใส่/เสียง** | `IS_Watch` · `IS_Applewatch` · `IS_AirPod` · `IS_HeadSet` · `IS_HeadPhone` · `IS_EarPhone` · `IS_Earcap` · `IS_Speaker` · `IS_Microphone` |
| **คอมพิวเตอร์** | `IS_PC` · `IS_iMac` · `IS_Desktop` · `IS_Computer` · `IS_Notebook` · `IS_Macbook` · `IS_Monitor` |
| **ชิ้นส่วน** | `IS_GraphicCard` · `IS_PowerSupply` · `IS_Mainboard` · `IS_RAM` · `IS_CPU` · `IS_Cooling` · `IS_Harddisk` |
| **อุปกรณ์ต่อพ่วง** | `IS_Mouse` · `IS_Keyboard` · `IS_Printer` · `IS_Toner` · `IS_Cartridge` · `IS_Camera` |
| **ไฟ/สายชาร์จ** | `IS_Adapter` · `IS_Charger` · `IS_PowerBank` · `IS_Battery` · `IS_Pin` · `IS_Cable` · `IS_USB` |
| **เคส/ป้องกัน** | `IS_Case` · `IS_Casing` · `IS_Protect` · `IS_Bumper` · `IS_film` · `IS_Strap` · `IS_Stand` · `IS_Dock` |
| **เกม** | `IS_Playstation` · `IS_NintendoSwitch` · `IS_Nintendo_SwitchG` |
| **สื่อบันทึก** | `IS_Flashdrive` · `IS_SD` · `IS_Card` · `IS_Sim` |
| **บริการ/ประกัน** | `IS_Software` · `IS_AppleCare` · `IS_Insurance` · `IS_Care` |
| **อื่นๆ** | `IS_Gadget` · `IS_Accessory` · `IS_Buletooth` *(สะกดผิด)* |

> ⚠️ **`IS_Buletooth` สะกดผิด** (ควรเป็น `Bluetooth`) — ต้อง map ให้ถูกที่ Bronze
> ⚠️ **flag ซ้อนทับกันได้** — iPhone หนึ่งเครื่องติดทั้ง `IS_iPhone`, `IS_Smartphone`, `IS_Mobile`
> ⚠️ **จับด้วย LIKE จึงมี false positive** เช่น `IS_Pin` จะจับคำว่า "**pin**k" หรือ "s**pin**" ได้ด้วย

### ฟิลด์มิติสินค้า (6)

| ฟิลด์ | ค่าที่เป็นไปได้ |
|---|---|
| `Sale_Type` | Normal Sale 201,437 · Promotion Sale 14,572 |
| `Product_Dimension` | Normal Product 196,756 · Demo Product 19,253 |
| `Product_Purpose` | Ordinary 205,577 · Gaming 10,432 |
| **`Main_Product_Dimension`** | 14 ค่า — ดูตารางด้านล่าง |
| `Sub_Product_Dimension` | มิติย่อย |

### `Main_Product_Dimension` ทั้ง 14 ค่า

| ค่า | รายการ | | ค่า | รายการ |
|---|---:|---|---|---:|
| Accessory and Others | 67,406 | | Smart Watch | 6,572 |
| Smart Phone | 52,112 | | Camera | 5,434 |
| PC | 19,581 | | Adapter/Charger/Powerbank | 4,440 |
| Notebook | 17,305 | | Software | 1,055 |
| PC&Notebook Component | 13,126 | | Console Gaming | 893 |
| Tablet | 9,942 | | Insurance | 649 |
| Mouse&Keyboard | 8,773 | | | |
| HeadSet&Earpiece | 8,721 | | | |

---

## 13. `ci.clean_brand_itec`

**แม็ปแบรนด์ดิบ → แบรนด์มาตรฐาน** · 2,685 แถว

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `Brand` 🔑 | varchar | ชื่อดิบจาก `dim_item_itec.Brand` |
| `CLEAN_BRAND` | varchar | ชื่อมาตรฐาน |

**2,685 ชื่อดิบ** สำหรับแบรนด์จริงไม่กี่ร้อยแบรนด์ = ระดับความไม่เป็นมาตรฐานของข้อมูลต้นทาง

---

## 14. `ci.clean_category_ITEC`

**แม็ปหมวดหมู่ดิบ → หมวดมาตรฐาน** · 1,966 แถว

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `ITEC_CategoryName_RAW` 🔑 | nvarchar | หมวดดิบ |
| `ITEC_SubCategoryName_RAW` 🔑 | nvarchar | หมวดย่อยดิบ |
| `CLEAN_CATEGORY` | nvarchar | หมวดมาตรฐาน |
| `CLEAN_SUB_CATEGORY` | nvarchar | หมวดย่อยมาตรฐาน |

**คีย์เป็นคู่ (category + subcategory)** ไม่ใช่ฟิลด์เดียว

---

## 15. `ci.thailand_map`

**จังหวัดและภูมิภาคของไทย** · 77 แถว (ครบทุกจังหวัด)

`Province_EN` · `Province_TH` · `Region_EN` · `Region_TH`

ใช้เป็น master ภูมิศาสตร์กลางของ vault ได้ — ระบบอื่นก็ต้องใช้ → [[Data Standardization & Quality]]

---

## 16. `ci.trn_category_ITEC`

**แม็ปวิธีชำระเงินฝั่ง ITEC** · 44 แถว

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `TYPE` 🔑 | varchar | ข้อความดิบที่บันทึกในระบบ เช่น `KTC (รูดผ่อนชำระ)` |
| `PAYMENT_TYPE` | varchar | **Credit Card · QR Code · Payment Gateway · Personal Loan · Unknown** |
| `INSTALLMENT_TYPE` | varchar | **Full Payment · Installment** |
| `BANK_NAME` | varchar | KTC · SCB · KBANK · BAY · BBL · TTB · UOB · AEON · CITIBANK · AMEX · SHOPEE · ROBINHOOD · ASEND · SG Finance · Samsung Finance · Unknown |

### ตัวอย่างที่น่าสนใจ

| TYPE | PAYMENT_TYPE | INSTALLMENT | BANK |
|---|---|---|---|
| `QR PROMPTPAY (KBank)` | QR Code | Full Payment | KBANK |
| `ShopeePay` | Payment Gateway | Full Payment | SHOPEE |
| `Robinhood` | Payment Gateway | Full Payment | ROBINHOOD |
| `SG Finance+` | **Personal Loan** | Full Payment | SG Finance |
| `Samsung Finance+` | **Personal Loan** | Full Payment | Samsung Finance |
| `Pay Next Extra (ผ่อนชำระ)` | **Personal Loan** | Installment | ASEND |
| `Ksher (ตู้ติดฟิล์ม)` | Unknown | Full Payment | Unknown |

> **`PAYMENT_TYPE = 'Personal Loan'` คือคู่แข่งโดยตรงของ UFUND** — SG Finance+ · Samsung Finance+ · Pay Next Extra
> ลูกค้าที่ผ่อนผ่านผู้ให้บริการอื่นที่หน้าร้าน COM7 คือกลุ่มเป้าหมายของ [[UFUND]] ที่เสียไป → คุ้มค่าวิเคราะห์

---

## 17. `ci.trn_category_BANK`

**แม็ปวิธีชำระเงินฝั่งธนาคาร** · 38 แถว · โครงสร้างเหมือน `trn_category_ITEC`

ค่าฝั่งธนาคารเขียนคนละแบบ เช่น `SCB-Full Payment`, `BAY-GCS Installment`, `KBANK-Alipay Wechat`, `LINE MAN`
→ ต้องใช้ทั้งสองตารางคู่กันเวลา reconcile

**BAY มี 4 แบบผ่อน:** GCS · TCS · FCC · KCC — เป็นโปรแกรมผ่อนคนละตัวของกรุงศรี

---

# Aggregate views

## 18. `ci.monthly_item_sale_itec`

**ยอดขายรายเดือน × สาขา × สินค้า** · 7,268,065 แถว · **2025-01-31 → 2026-08-31**

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `END_MONTH_DATE` 🔑 | date | วันสิ้นเดือน |
| `SALE_MONTH_YEAR` | varchar | เดือน/ปี แบบข้อความ |
| `BRANCH_ID` 🔑 | int | สาขา |
| `PRODUCT_ID` 🔑 | varchar | สินค้า |
| `NO_OF_SALE_UNIT` | int | จำนวนที่ขาย |
| `PRODUCT_COST_AMT` | float | ต้นทุนรวม |
| `PRODUCT_SALE_AMT` | float | ยอดขายรวม |
| **`SHELF_LIFE_DAY`** | int | จำนวนวันที่สินค้าอยู่บนชั้นก่อนขายได้ |

`SHELF_LIFE_DAY` เป็นตัวชี้วัดการหมุนเวียนสินค้า — มีให้ใช้แล้วไม่ต้องคำนวณเอง

---

## 19. `ci.monthly_item_inventory_itec`

**สต็อกรายเดือน × สาขา × สินค้า** · 18,070,548 แถว

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `AS_OF_DATE` 🔑 | date | วันที่ตัดยอด |
| `STOCK_MONTH_YEAR` | varchar | เดือน/ปี |
| `BRANCH_ID` 🔑 | int | สาขา |
| `PRODUCT_ID` 🔑 | varchar | สินค้า |
| `NO_OF_INVENTORY_UNIT` | int | จำนวนคงเหลือ |

---

## 20. `ci.integrated_sale_and_inventory`

**รวมยอดขาย + สต็อก + มิติสินค้าไว้ที่เดียว** · 20,156,102 แถว
**เป็น view ที่พร้อมใช้ทำ analytics มากที่สุด**

| กลุ่ม | ฟิลด์ |
|---|---|
| **วันที่** | `AS_OF_DATE` · `STOCK_MONTH_YEAR` · `SALE_MONTH_YEAR` · `END_MONTH_DATE` · `MAIN_AS_OF_DATE` |
| **สาขา** | `BRANCH_ID_STOCK` · `BRANCH_ID_SALE` · `BRANCH_ID_MAIN` |
| **สินค้า** | `PRODUCT_ID_STOCK` · `PRODUCT_ID_SALE` · `PRODUCT_ID_MAIN` |
| **ตัวเลข** | `NO_OF_INVENTORY_UNIT` · `NO_OF_SALE_UNIT` · `PRODUCT_COST_AMT` · `PRODUCT_SALE_AMT` · `SHELF_LIFE_DAY` |
| **มิติ** | `category_itec` · `Subcategory_itec` · `ItemName` · `Brand` · `Sale_Type` · `Product_Dimension` · `Main_Product_Dimension` · `Sub_Product_Dimension` · `Product_Purpose` |

> มี `BRANCH_ID` และ `PRODUCT_ID` **3 ชุด** (STOCK / SALE / MAIN) เพราะเป็น full outer join ระหว่างฝั่งสต็อกกับฝั่งขาย
> **ให้ใช้ `_MAIN` เป็นตัวหลักเสมอ** — อีกสองชุดจะเป็น NULL เมื่อเดือนนั้นมีแต่ขายหรือมีแต่สต็อก `[อนุมาน]`

---

# Reconcile views — บัตรเครดิต

> 🔴 **สามตารางนี้มีเลขบัตรเครดิต ห้าม ingest เข้า Data Lake** อยู่ภายใต้ PCI-DSS ไม่ใช่แค่ PDPA
> สคริปต์สำรวจในโปรเจกต์นี้ไม่แตะข้อมูลในนี้เลย นับแถวและอ่าน metadata เท่านั้น

## 21. `ci.creditcard_trn_itec` 🔴

**ธุรกรรมบัตรฝั่ง ITEC** · 2,916,873 แถว

| ฟิลด์                                        | ชนิด        | คำอธิบาย                                 |
| -------------------------------------------- | ----------- | ---------------------------------------- |
| `ITEC_SALEID` 🔗                             | int         | เลขที่บิล                                |
| `ITEC_SALE_BRANCH`                           | int         | สาขา                                     |
| `ITEC_RAW_PAYMENT_TYPE`                      | varchar     | ข้อความวิธีชำระดิบ                       |
| `ITEC_PAYMENT_TYPE`                          | varchar     | ประเภทที่จัดหมวดแล้ว                     |
| `ITEC_INSTALLMENT_TYPE`                      | varchar     | เต็มจำนวน/ผ่อน                           |
| `ITEC_BANK_NAME`                             | varchar     | ธนาคาร                                   |
| `ITEC_LAST4`                                 | varchar     | 🔴 4 ตัวท้ายบัตร                         |
| `ITEC_APPROVAL_CODE`                         | varchar     | รหัสอนุมัติ                              |
| `ITEC_TERMINAL_ID`                           | varchar     | เครื่อง EDC                              |
| `ITEC_TRAN_AMT`                              | float       | ยอด                                      |
| `ITEC_TRN_DATE`                              | date        | วันที่                                   |
| `ITEC_DOCREF`                                | varchar     | เลขเอกสาร                                |
| `ITEC_TAX_INVOICE_NO`                        | varchar     | เลขใบกำกับภาษี                           |
| `ITEC_CUSTOMER_INVOICE_NAME`                 | varchar     | 🟠 ชื่อผู้รับใบกำกับ                     |
| `ITEC_CUSTOMER_NAME`                         | varchar     | 🟠 ชื่อลูกค้า                            |
| `ITEC_MEMBER_CODE`                           | varchar     | 🟠 รหัสสมาชิก                            |
| `ITEC_CRM_ID`                                | varchar     | 🟠 รหัส CRM                              |
| `ITEC_SALE_OFFICER_ID` · `_NAME` · `_STATUS` | int/varchar | พนักงานขาย                               |
| `ITEC_JOIN_KEY` 🔑                           | varchar     | **คีย์สังเคราะห์ไว้จับคู่กับฝั่งธนาคาร** |

### โปรไฟล์ค่าจริง (2026-08-28)

| | |
|---|---:|
| แถวทั้งหมด | 2,916,873 |
| `ITEC_SALEID` ไม่ซ้ำ | **702,355** |
| `ITEC_JOIN_KEY` ไม่ซ้ำ | 2,808,440 |
| ช่วงข้อมูล | **2025-01-01 → 2026-08-09** |

**เฉลี่ย 4.15 รายการบัตรต่อ 1 บิล** — สูงผิดปกติสำหรับการซื้อครั้งเดียว

#### มีแค่บัตรเครดิต ไม่มีช่องทางอื่น

| ประเภท | รายการ | ยอด (บาท) | เฉลี่ย/รายการ |
|---|---:|---:|---:|
| **Credit Card — Installment** | 1,536,115 | 33,640,081,545 | **21,899** |
| **Credit Card — Full Payment** | 1,380,758 | 10,611,382,330 | 7,685 |

> ⚠️ **ไม่มี QR Code · Payment Gateway · Personal Loan เลย** ทั้งที่ `ci.trn_category_ITEC` มีประเภทเหล่านั้น
> → view นี้ครอบคลุม**เฉพาะธุรกรรมบัตรเครดิต** ไม่ใช่ทุกวิธีชำระเงิน

#### ธนาคาร — มีแค่ 8 ราย

| ธนาคาร | รายการ | ยอด (บาท) |
|---|---:|---:|
| BAY | 477,355 | 9,385,022,883 |
| **BBL** | **1,043,782** | 8,985,025,064 |
| KBANK | 474,288 | 7,516,860,944 |
| KTC | 319,921 | 4,746,396,511 |
| SCB | 191,986 | 4,448,516,815 |
| UOB | 176,492 | 4,397,280,428 |
| TTB | 141,529 | 3,019,695,855 |
| AEON | 91,520 | 1,752,665,376 |

> **BBL มีรายการมากที่สุด (36%) แต่ยอดรวมน้อยกว่า BAY** — BBL รับรายการเล็ก BAY รับรายการใหญ่

#### ความครบของฟิลด์

| ฟิลด์ | ว่าง | สัดส่วน |
|---|---:|---:|
| `ITEC_LAST4` | 0 | 0% |
| `ITEC_APPROVAL_CODE` | 0 | 0% |
| `ITEC_TERMINAL_ID` | 10 | ~0% |
| `ITEC_MEMBER_CODE` | 297,134 | 10.2% |
| `ITEC_CUSTOMER_NAME` | 297,134 | 10.2% |
| `ITEC_TAX_INVOICE_NO` | 622,948 | 21.4% |
| **`ITEC_CRM_ID`** | **978,172** | **33.5%** |

> `ITEC_MEMBER_CODE` กับ `ITEC_CUSTOMER_NAME` ว่างจำนวนเท่ากันเป๊ะ (297,134) → **ว่างพร้อมกันเสมอ**
> = ธุรกรรมที่ลูกค้าไม่แจ้งตัวตนเลย `[อนุมาน]`

#### `ITEC_JOIN_KEY` ไม่ใช่รูปแบบตายตัว

| ความยาว | แถว | สัดส่วน |
|---:|---:|---:|
| **31** | 2,763,806 | **94.8%** |
| 32 | 63,318 | 2.2% |
| 30 | 29,741 | 1.0% |
| 33 | 13,278 | 0.5% |
| 41 | 12,796 | 0.4% |
| อีก 30 ความยาว (26–50+) | ~46,000 | 1.6% |

→ เป็นคีย์สังเคราะห์จากการต่อสตริง ความยาวจึงแปรตามค่าที่ประกอบ **ไม่ควรใช้ความยาวตรวจความถูกต้อง**

#### จับคู่กับฝั่งธนาคารได้ 83.9%

| | จำนวน | สัดส่วน |
|---|---:|---:|
| จับคู่ `BANK_JOIN_KEY` ได้ | 2,446,032 | **83.9%** |
| จับคู่ไม่ได้ | **470,841** | **16.1%** |

> **16% ของธุรกรรมบัตรฝั่ง ITEC หาคู่ในไฟล์ settlement ธนาคารไม่เจอ** — คือปัญหาที่ view นี้ถูกสร้างมาเพื่อแก้

#### จำนวนรายการบัตรต่อ 1 บิล

| รายการ/บิล | จำนวนบิล |
|---:|---:|
| 1 | 243,123 |
| 2 | 143,290 |
| 3 | 87,806 |
| 4 | 51,590 |
| 5 | 35,088 |
| 6–10 | 85,727 |
| 11–25 | ~40,000 |
| มากกว่า 25 | พบอีก 43 รูปแบบ |

> **มีเพียง 35% ของบิลที่มีรายการบัตรใบเดียว** — ที่เหลือรูดหลายครั้ง/หลายใบต่อบิล
> เชื่อมโยงกับธง `Split_Bill` ใน [`ci.creditcard_trn_summary`](#23-cicreditcard_trn_summary)

#### ตัวอย่างข้อมูล (mask แล้ว · TOP 5 ไม่ได้สุ่ม)

| ฟิลด์ | แถว 1 | แถว 3 | แถว 4 |
|---|---|---|---|
| `ITEC_SALEID` | 6871 | 6385 | 433 |
| `ITEC_SALE_BRANCH` | 1983 | 2471 | 2858 |
| `ITEC_RAW_PAYMENT_TYPE` | BBL (รูดเต็มจำนวน) | BBL (รูดเต็มจำนวน) | BBL (รูดเต็มจำนวน) |
| `ITEC_TRAN_AMT` | 790.00 | 790.00 | 790.00 |
| `ITEC_TRN_DATE` | 2025-10-21 | 2025-12-20 | 2026-01-29 |
| `ITEC_TERMINAL_ID` | 82214661 | 82213080 | 82244268 |
| `ITEC_DOCREF` | **NULL** | 6812-CH383-00160 | 6901-CH1559-00108 |
| `ITEC_TAX_INVOICE_NO` | **NULL** | 6812-BR383-00160 | 6901-BR1559-00106 |
| `ITEC_MEMBER_CODE` | `065…` (เบอร์โทร) | `M06…` | `2fb…` (คล้าย hex) |
| `ITEC_CRM_ID` | **ว่าง** | `M06…` | `M04…` |
| `ITEC_SALE_OFFICER_ID` | **NULL** | 32021 | 32802 |
| `ITEC_SALE_OFFICER_STATUS` | **NULL** | **Cancel** | Normal |

**สิ่งที่ตัวอย่างบอก**

1. **`ITEC_MEMBER_CODE` ปนหลายรูปแบบในตารางเดียวกัน** — เบอร์โทร (`065…`) · รหัสสมาชิก (`M06…`) · สตริงคล้าย hex (`2fb…`)
   ยืนยันปัญหาเดียวกับ `dim_mem_itec.memcode` → [[Data Standardization & Quality]]
2. **`ITEC_DOCREF` และ `ITEC_TAX_INVOICE_NO` ว่างพร้อมกัน** — ธุรกรรมที่ไม่ได้ออกใบกำกับ
3. **รูปแบบเลขเอกสาร** `YYMM-CHxxx-NNNNN` (DocRef) กับ `YYMM-BRxxx-NNNNN` (ใบกำกับ) — `CH` กับ `BR` ต่างกันแค่ 2 ตัว
   `6812` = ธ.ค. 2568 · `6901` = ม.ค. 2569 → **เข้ารหัสเป็นปี พ.ศ.** ไม่ใช่ ค.ศ.
4. **พนักงานขายที่สถานะ `Cancel` ยังผูกกับธุรกรรมอยู่** — ลาออกแล้วแต่ประวัติการขายยังอยู่ ต้องระวังตอนทำรายงานรายพนักงาน
5. TOP 5 ที่ได้เป็น BBL 790 บาททั้งหมด — เป็นผลของการเรียงทางกายภาพ **ไม่ใช่ตัวอย่างสุ่ม** อย่าตีความว่าเป็นค่าที่พบบ่อย

---

## 22. `ci.creditcard_trn_bank` 🔴

**ธุรกรรมบัตรฝั่งธนาคาร** · 2,790,117 แถว

| ฟิลด์                                                                                      | ชนิด    | คำอธิบาย                     |
| ------------------------------------------------------------------------------------------ | ------- | ---------------------------- |
| `BANK_SETTLEMENT_DATE`                                                                     | date    | วันที่เงินเข้า               |
| `BANK_TRAN_DATE`                                                                           | date    | วันที่รูด                    |
| `BANK_TERMINAL_ID` · `BANK_MERCHANT_ID` · `BANK_STORE_ID`                                  | varchar | รหัสเครื่อง/ร้าน             |
| `BANK_APPROVAL_CODE`                                                                       | varchar | รหัสอนุมัติ                  |
| `BANK_TRAN_AMT`                                                                            | float   | ยอด                          |
| `BANK_RAW_PAYMENT_TYPE` · `BANK_PAYMENT_TYPE` · `BANK_INSTALLMENT_TYPE` · `BANK_BANK_NAME` | varchar | วิธีชำระ                     |
| **`BANK_CC_NO`** · **`BANK_CREDIT_CARD_NO`** · **`BANK_CREDIT_CARD_NO2`**                  | varchar | 🔴 **เลขบัตรเครดิต 3 ฟิลด์** |
| `BANK_FIRST6` · `BANK_LAST4`                                                               | varchar | 🔴 BIN และ 4 ตัวท้าย         |
| `BANK_UNIQUE_KEY` · `BANK_JOIN_KEY` 🔑                                                     | varchar | คีย์จับคู่                   |

## 23. `ci.creditcard_trn_summary`

**ผลการจับคู่ ITEC ↔ ธนาคาร + ธงความผิดปกติ** · 2,779,657 แถว
**ไม่มีเลขบัตร — ใช้ได้ปลอดภัยกว่าสองตัวข้างบน**

| ฟิลด์ | ชนิด | คำอธิบาย |
|---|---|---|
| `BANK_JOIN_KEY` 🔑 | varchar | คีย์จับคู่ |
| `ITEC_CNT_TRN` | int | จำนวนรายการฝั่ง ITEC ที่จับคู่ได้ |
| `ITEC_CNT_BRANCH` | int | จำนวนสาขาที่เกี่ยวข้อง |
| `ITEC_CNT_CUST_NAME` | int | จำนวนชื่อลูกค้าที่ต่างกัน |
| `ITEC_CNT_INVOICE` | int | จำนวนใบกำกับ |
| `ITEC_CNT_INVOICE_NAME` | int | จำนวนชื่อผู้รับใบกำกับ |
| `ITEC_CNT_SALE_OFFICER_NAME` | int | จำนวนพนักงานขาย |
| **`Split_Bill`** | varchar | 🚩 แยกบิล |
| **`Multiple_Branch`** | varchar | 🚩 รูดข้ามหลายสาขา |
| **`Multiple_Customer_name`** | varchar | 🚩 ชื่อลูกค้าหลายชื่อในรายการเดียว |
| **`Multiple_InvoiceNo`** | varchar | 🚩 หลายใบกำกับ |
| **`Multiple_Invoice_Name`** | varchar | 🚩 หลายชื่อผู้รับ |
| **`Multiple_SaleOfficer`** | varchar | 🚩 หลายพนักงาน |

> ธงทั้ง 6 ตัวออกแบบมาเพื่อ**จับพฤติกรรมผิดปกติ / ทุจริต** เช่น แยกบิลเลี่ยงวงเงิน หรือรูดบัตรใบเดียวข้ามสาขา
> เป็น use case ที่พร้อมใช้อยู่แล้ว → [[Analytics & AI]]

---

## สรุปคีย์ที่ใช้ join ได้

| จาก | ถึง | คีย์ | คุณภาพ |
|---|---|---|---|
| `fact_sales_itec` | `dim_item_itec` | `ItemId` | ✅ 100% |
| `fact_sales_itec` | `dim_branch_itec` | `SalesBranch` = `Branch` | ✅ 100% |
| `fact_sales_itec` | `dim_officer_itec` | `SalesOfficerId` = `OfficerID` | ✅ ~100% |
| `fact_sales_itec` | `dim_mem_itec` | `SalesId` + `SalesBranch` | ⚠️ 89.2% · ต้อง DISTINCT ก่อน |
| `fact_sales_itec` | `dim_sales_header_itec` | `SalesId` + `SalesBranch` | ⚠️ 77.3% |
| `fact_sales_itec` | `fact_bank_itec` | `SalesId` | ยังไม่ทดสอบ |
| `dim_mem_itec` | CRM `members` | `crmid` = `member_id` | 57% มีค่า |
| `fact_trans_fo` | `dim_item_itec` | `ITEC-ITEMNO` = `ItemId` | ยังไม่ทดสอบ |
| `dim_branch_itec` | `ci.clean_branch` | `Branch` = `Branch_ID` | ✅ 100% |
| `ci.trn_category_ITEC` | `fact_bank_itec` | `TYPE` | ยังไม่ทดสอบ |

---

## เชื่อมกับโน้ตอื่น

[[ITEC Overview]] · [[ITEC - Query Cookbook]] · [[CRM - Data Dictionary]] · [[Customer Identity]] · [[Data Standardization & Quality]] · [[Consent & PDPA]] · [[K2 - Data Dictionary]] · [[ITEC Item Category Mapping (SQL to Python)]]
