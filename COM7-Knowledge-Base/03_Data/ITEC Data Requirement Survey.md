# ITEC Data Requirement Survey

สำรวจว่า **ฟิลด์ 77 ตัว** ที่โครงการ Data Lake ต้องการจากธุรกิจค้าปลีก มีอยู่ใน ITEC หรือไม่

**ที่มา:** `Copy of ITEC data requirement_reply1.xlsx` sheet `retail` — คำตอบจากเจ้าของระบบ ITEC
**รับเข้า vault:** 2026-08-28

ใช้คู่กับ → [[ITEC Overview]] · [[ITEC-MIS - Data Dictionary]] · แบบเดียวกันฝั่ง K2 → [[K2 Customer Field Survey]]

---

## เกณฑ์ให้คะแนน

| รหัส | ความหมาย |
|:--:|---|
| **1** | มีตรงๆ |
| **2** | ไม่มีตรงๆ แต่ทดแทนได้ |
| **3** | ไม่มีเลย |
| *(ว่าง)* | **ยังไม่ได้ตอบ** |

---

## ผลรวม

| หมวด | 1 มี | 2 ทดแทน | 3 ไม่มี | ไม่ตอบ | รวม | ความพร้อม |
|---|---:|---:|---:|---:|---:|---|
| **sale** | 12 | 0 | 0 | 0 | 12 | **100%** |
| **branch** | 14 | 1 | 7 | 0 | 22 | 68% |
| **item** | 13 | 3 | 5 | 0 | 21 | 76% |
| **after sale service** | 0 | 0 | 9 | 0 | 9 | **0%** |
| **logistic** | 0 | 0 | 0 | **13** | 13 | **ไม่มีคำตอบ** |
| **รวม** | **39** | **4** | **21** | **13** | **77** | 56% |

**อ่านผล**

- **การขายพร้อม 100%** — ทุกฟิลด์ที่ต้องการมีครบ
- **บริการหลังการขายเป็นศูนย์** — ไม่มีสักฟิลด์ใน 9 ตัว
- **โลจิสติกส์ไม่มีคำตอบเลยทั้ง 13 ฟิลด์** พร้อมคำถามกลับว่า *"Logistic หมายถึงขนส่งของขั้นตอนไหน"*
- ที่เหลือติดเรื่อง **ข้อมูลพนักงาน** ซึ่งอยู่ที่ฝ่ายบุคคล ไม่ใช่ ITEC

---

## sale — พร้อม 100% (12/12)

| ฟิลด์ | ความหมาย | ตรงกับที่พบในฐาน |
|---|---|---|
| receipt/slip code | เลขใบเสร็จ | `dim_sales_header_itec.TAX_Invoice` · `DocRef` ⚠️ ขาด 22.7% |
| customer member id | รหัสระบุตัวตนลูกค้า | `dim_mem_itec.crmid` ⚠️ ว่าง 43% |
| item list in receipt/slip | รายการสินค้าตามใบเสร็จ | `fact_sales_itec` |
| payment method | สด / บัตร / QR | `fact_bank_itec.TYPE` + `ci.trn_category_ITEC` |
| branch code | รหัสสาขา | `fact_sales_itec.SalesBranch` |
| sale channel | หน้าร้าน / ออนไลน์ / แอป | `clean_branch.SALE_CHANNEL` ⚠️ มีแค่ Physical / Online |
| promotion code | รหัสโปรโมชัน | ⚠️ **ไม่พบใน 23 view** |
| sale date time | วันเวลาตามใบเสร็จ | `fact_sales_itec.SalesCrDatetime` |
| **credit card no** | **เลขบัตรเครดิต** | `ci.creditcard_trn_bank.BANK_CC_NO` 🔴 |
| credit card bank code / name | ธนาคาร | `ci.trn_category_ITEC.BANK_NAME` |
| employee id | รหัสพนักงานขาย | `fact_sales_itec.SalesOfficerId` |

### 🔴 `credit card no` — ต้องหยุดคุยก่อน

ผู้ตอบระบุ **"จริงๆอยากได้ทุกตัว"** และหมายเหตุว่า *"ตามที่ถูกคีย์เข้ามาในระบบ"*

**เลขบัตรเครดิตเต็มใบอยู่ภายใต้ PCI-DSS ไม่ใช่แค่ PDPA** — การนำเข้า Data Lake มีข้อห้ามชัดเจน

| ต้องทำ | ทำไม |
|---|---|
| **ห้าม ingest เลขบัตรเต็มเข้า S3** | PCI-DSS ห้ามเก็บ PAN โดยไม่มีมาตรการควบคุมระดับสูง |
| ใช้ `LAST 4-DIGIT` + `FIRST 6-DIGIT` (BIN) แทน | ตอบโจทย์ analytics ได้เกือบทั้งหมด — รู้ธนาคาร ประเภทบัตร และจับคู่รายการได้ |
| ถ้าต้องเชื่อมรายการ ใช้ `APPROVAL CODE` + `TERMINAL ID` + วันที่ | เป็นคีย์ที่ระบบ reconcile ใช้อยู่แล้ว ไม่ต้องใช้เลขบัตร |
| ต้องได้ความเห็น legal / DPO ก่อน | ไม่ใช่การตัดสินใจของทีมข้อมูล |

→ [[Consent & PDPA]] · [[ITEC Issues]]

### ⚠️ `sale channel` — ผู้ตอบเองก็ไม่แน่ใจ

หมายเหตุระบุ *"ยังไม่แน่ใจในส่วนของ App"*
ตรวจจากฐานแล้ว `clean_branch.SALE_CHANNEL` มีแค่ **Physical 3,181 · Online 24** — **ไม่มีช่องทาง App แยก**
ความไม่แน่ใจนั้นถูกต้อง

### ⚠️ `promotion code` ตอบว่ามี แต่หาไม่เจอ

ค้นทั้ง 297 คอลัมน์ใน 23 view พบแค่ `ci.clean_item_category_itec.IS_Promotion` (flag 0/1)
และ `Sale_Type = 'Promotion Sale'` — **ทั้งคู่ไม่ใช่รหัสโปรโมชัน**
→ ต้องถามว่ารหัสโปรโมชันอยู่ตารางไหน

---

## item — 76% (13 มี · 3 ทดแทน · 5 ไม่มี)

### ทดแทนได้ 3 ฟิลด์

| ฟิลด์ | วิธีทดแทน | ตรวจแล้ว |
|---|---|---|
| first sold date | `MIN(SalesCrDatetime)` group by product | ✅ ทำได้ |
| last sold date | `MAX(SalesCrDatetime)` group by product | ✅ ทำได้ |
| **product active status** | `EOLStatus` ในตาราง **`Product`** | ⚠️ **ไม่มีตาราง `Product` ใน 23 view ที่เข้าถึงได้** |

### ไม่มี 5 ฟิลด์

| ฟิลด์ | ความหมาย | ผลกระทบ |
|---|---|---|
| **product spec** | CPU · RAM · GPU · ขนาดหน้าจอ | **สูง** — วิเคราะห์ตามสเปกไม่ได้ ต้องแกะจากชื่อสินค้า |
| **product sub type** | ประเภทย่อยของอุปกรณ์เสริม | กลาง — มี `Sub_Product_Dimension` ในชั้น `ci` อาจใช้แทนได้ |
| first introduction date | วันขึ้นชั้นวันแรก | กลาง — ต่างจาก first sold date |
| product lot | สินค้าอยู่ lot ไหน | กลาง — ตามรอยปัญหาคุณภาพสินค้าไม่ได้ |
| device mag id | เลข MAG | ต่ำ |

> **`product sub type` อาจตอบผิด** — `ci.clean_item_category_itec` มี `Sub_Product_Dimension` อยู่แล้ว
> ควรตรวจซ้ำว่าใช้แทนได้ไหม

### มีแต่มีเงื่อนไข

| ฟิลด์ | เงื่อนไข |
|---|---|
| device emei id | **เฉพาะสินค้าที่ใส่ SIM** |
| device activation date | **เฉพาะ Apple** — ⚠️ ไม่พบคอลัมน์ใน 23 view |

---

## branch — 68% (14 มี · 1 ทดแทน · 7 ไม่มี)

### มีครบและตรงกับที่ probe เจอ

`open date` · `close date` · `active status` · `branch code` · `branch name` · `branch location` ·
`branch brand` · `province` · `region` · `lat-long` · `branch type` · `branch inventory` ·
**`nearby competitors`** (= `dim_branch_itec.BuildingCompetitor`) · `branch manager name`

| ทดแทนได้ | วิธี |
|---|---|
| floor plan (พื้นที่ ตร.ม. / ชั้น) | **ต้องแกะจาก `Address`** — เป็นข้อความอิสระ ต้องทำ parsing |

### ⚠️ `active status` ตอบว่ามี แต่ค่าในฐานผิดปกติ

`ci.clean_branch.BRANCH_STATUS` → **InActive 3,155 · Active เพียง 50**
สำหรับเครือที่มีร้านทั่วประเทศ ตัวเลข 50 น้อยผิดปกติมาก
→ ต้องถามว่าฟิลด์นี้หมายถึงอะไร หรือควรใช้ `ClosedDate IS NULL` แทน

### ⚠️ `branch manager name` ตอบว่ามี แต่หาไม่เจอ

ไม่พบคอลัมน์ที่มีคำว่า `manager` ใน 297 คอลัมน์ของ 23 view
แต่หมายเหตุของ `employee id` บอกว่า *"มีแค่ชื่อของ RSM, ASM, BSM"* → **ข้อมูลนี้น่าจะอยู่ตารางที่ยังไม่เปิดให้เห็น**

### ไม่มี 7 ฟิลด์ — ส่วนใหญ่เป็นข้อมูลพนักงาน

| ฟิลด์ | หมายเหตุจากผู้ตอบ |
|---|---|
| employee id | มีแค่ชื่อ RSM · ASM · BSM |
| employee name | — |
| employee start date | — |
| employee status | **ต้องขอที่ฝ่ายบุคคล** |
| branch assist manager name | — |
| nearby branch | — (คำนวณเองได้จาก lat-long) |
| warehouse inventory | — |

> **`nearby branch` คำนวณได้เอง** จาก `Latitude` / `Longitude` ที่มีอยู่แล้ว ไม่ต้องขอจากต้นทาง
> **ข้อมูลพนักงาน 4 ฟิลด์เป็นของฝ่ายบุคคล ไม่ใช่ ITEC** → ต้องเปิดเส้นทางขอข้อมูลกับ HR แยกต่างหาก
> **`warehouse inventory`** — `onhandendmonth_itec` มี `TransferingTo` และมีสาขาชื่อ `E-Commerce Warehouse` อาจครอบคลุมบางส่วน ควรตรวจซ้ำ

---

## after sale service — 0 จาก 9 ⚠️

`case open date` · `case type` · `list of task` · `case desc` · `estimated service time` ·
`case log activity` · `case deliver/close date` · `case status` · `responsible employee`

**ไม่มีสักฟิลด์เดียวใน ITEC**

**แต่ธุรกิจนี้มีอยู่จริง** — `ci.clean_branch.SHOP_BRAND` มี **iCare 61 สาขา** และยอดขายปี 2026 = 291 ล้านบาท
และ `dim_item_itec.CategoryName` มี **Apple Service 7,280 รายการ · Service 5,070 รายการ**

→ **ข้อมูลเคสบริการอยู่ในระบบของ iCare ไม่ใช่ ITEC** — ต้อง survey ระบบ iCare แยก (Timeline 1.1.6.2 · P.Pui)

**ผลกระทบ:** Gap Review เคยจัดให้ **"ข้อมูลวงจรชีวิตอุปกรณ์" เป็นช่องว่างอันดับ 1** — ผลสำรวจนี้ยืนยันว่ายังปิดไม่ได้
→ [[Customer Identity]] · [[System Inventory]]

---

## logistic — ไม่มีคำตอบทั้ง 13 ฟิลด์ ⚠️

`freight id` · `start/arrival date time` · `departure/arrival location` · `lat-long ทั้งสองฝั่ง` ·
`transport cost` · `truck plate id` · `mileage departure/arrival` · `gas price` · `list item in transit`

**ผู้ตอบไม่ได้กรอกช่อง Available เลย** และเขียนคำถามกลับมาแทน:

> **"Logistic หมายถึงขนส่งของขั้นตอนไหน"**

### คำถามนี้ถูกต้องและต้องตอบก่อน

โลจิสติกส์ในธุรกิจค้าปลีกมีอย่างน้อย 3 ขั้นตอนที่ต่างกันโดยสิ้นเชิง:

| ขั้นตอน | จาก → ถึง | ใครดูแล |
|---|---|---|
| 1. Supplier → คลัง | ผู้ผลิต/ผู้นำเข้า → คลังกลาง | จัดซื้อ |
| 2. คลัง → สาขา | คลังกลาง → หน้าร้าน (การโอนย้ายสต็อก) | คลัง/ปฏิบัติการ |
| 3. สาขา/คลัง → ลูกค้า | จัดส่งคำสั่งซื้อออนไลน์ | e-commerce |

**เบาะแสจากฐานข้อมูล:** `rpt.fact_trans_fo` มี `Transaction_Type = 'Transfer'` **100,456,283 แถว**
(เกือบเท่า Sales order) และ `Transfer order shipment` / `Transfer order receive` อีก ~9 ล้านแถว
→ **ขั้นตอนที่ 2 มีข้อมูลอยู่ใน D365 แล้ว** แต่เป็นระดับ "ของเคลื่อนจากไหนไปไหน" ไม่ใช่ระดับ "รถคันไหน วิ่งกี่ไมล์"

**ต้องนิยาม scope ก่อนถามใหม่** — ถ้าต้องการระดับรถ/ทะเบียน/น้ำมัน นั่นเป็นระบบ TMS ที่ยังไม่รู้ว่ามีหรือไม่

---

## สรุปสิ่งที่ต้องทำต่อ

| ลำดับ | เรื่อง | ใคร |
|:--:|---|---|
| 1 | **หยุดคำขอเลขบัตรเครดิตเต็มใบ** จนกว่า legal/DPO จะตอบ · เสนอใช้ BIN + 4 ตัวท้ายแทน | Data + legal |
| 2 | **นิยาม scope ของ logistic** ให้ชัด แล้วส่งแบบสำรวจกลับไปใหม่ | Data |
| 3 | **ส่ง survey หลังการขายไปที่ระบบ iCare** ไม่ใช่ ITEC | Data + P.Pui |
| 4 | **เปิดเส้นทางขอข้อมูลพนักงานกับฝ่ายบุคคล** (5 ฟิลด์) | Data + HR |
| 5 | ถามว่า **`promotion code`** และ **`branch manager name`** อยู่ตารางไหน — ไม่พบใน 23 view | เจ้าของระบบ ITEC |
| 6 | ถามว่า **ตาราง `Product` (`EOLStatus`)** เข้าถึงได้ยังไง — ไม่อยู่ใน 23 view | เจ้าของระบบ ITEC |
| 7 | ตรวจซ้ำว่า **`product sub type`** ใช้ `Sub_Product_Dimension` แทนได้ไหม | Data |
| 8 | ยืนยันความหมายของ **`BRANCH_STATUS`** (Active 50 จาก 3,205) | เจ้าของระบบ ITEC |
| 9 | `nearby branch` **คำนวณเองจาก lat-long** ไม่ต้องขอ | Data |

---

## ข้อสังเกตสำคัญ: คำตอบอ้างถึงฟิลด์ที่เรามองไม่เห็น

มี **4 ฟิลด์ที่ตอบว่า "มี" แต่หาไม่เจอใน 23 view** ที่เราเข้าถึงได้:

| ฟิลด์ | อ้างถึง |
|---|---|
| product active status | ตาราง **`Product`** คอลัมน์ `EOLStatus` |
| promotion code | ไม่ระบุ |
| branch manager name | ไม่ระบุ |
| device activation date | ไม่ระบุ (เฉพาะ Apple) |

**แปลว่า ITEC มีข้อมูลมากกว่าที่ 23 view เปิดให้เห็น** — ผู้ตอบเห็นตารางจริง เราเห็นแค่ชั้น reporting

→ ต้องขอ **รายการตารางจริงของ ITEC** หรือขอสิทธิ์เพิ่ม ไม่งั้นเราจะออกแบบ pipeline บนภาพที่ไม่ครบ
→ [[ITEC Issues]]

---

## เชื่อมกับโน้ตอื่น

[[ITEC Overview]] · [[ITEC-MIS - Data Dictionary]] · [[ITEC Issues]] · [[Retail]] · [[K2 Customer Field Survey]] · [[Customer Identity]] · [[Consent & PDPA]] · [[System Inventory]]
