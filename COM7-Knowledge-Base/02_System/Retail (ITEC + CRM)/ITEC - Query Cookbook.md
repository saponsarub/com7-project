# ITEC - Query Cookbook

SQL ที่ **รันผ่านจริงกับฐาน MIS แล้ว** พร้อมเวลาที่ใช้และจำนวนแถวที่ได้
ทดสอบเมื่อ 2026-08-28 · โครงสร้าง → [[ITEC - Data Dictionary]] · ภาพรวม → [[ITEC Overview]]

---

## กฎ 4 ข้อที่ต้องทำทุกครั้ง

|   # | กฎ                                                         | เหตุผล                                                 |
| --: | ---------------------------------------------------------- | ------------------------------------------------------ |
|   1 | **`WHERE Status = 0`** เสมอใน `fact_sales_itec`            | Status 1 มียอดเสีย บรรทัดเดียว 8.4 แสนล้านบาท          |
|   2 | **`SELECT DISTINCT` ก่อน join `dim_mem_itec`**             | grain ไม่นิ่ง 1 บิลมีได้หลายร้อยแถว → ยอดจะถูกคูณ      |
|   3 | **ตัด `SHOP_BRAND = 'Audit'` ออกจากยอดขาย**                | เป็นสาขาบัญชีภายใน ไม่ใช่การขายจริง — ดูหัวข้อด้านล่าง |
|   4 | **ครอบชื่อคอลัมน์ด้วย `[ ]`** เมื่อมีช่องว่าง `/` หรือ `%` | เช่น `[GP %]` · `[Model/Series]` · `[TRANS DATE]`      |

### ⚠️ `SHOP_BRAND = 'Audit'` ทำให้ยอดขายบวมผิดปกติ

| SHOP_BRAND | บิล | ชิ้น | ยอด (บาท) |
|---|---:|---:|---:|
| BaNANA | 432,357 | 8,732,014 | 22,690,995,952 |
| **Audit** | **10,327** | **25,222,842** | **19,327,863,381** |
| Studio7 | 565,154 | 2,730,850 | 18,855,675,397 |
| Online | 613,305 | 749,408 | 2,930,147,912 |

สาขาเดียวชื่อ **`(73) FBI RETAIL- Cost`** มียอด 19,203,820,586 บาทจากเพียง 10,327 บิล
→ **เป็นรายการปรับปรุงทางบัญชี ไม่ใช่การขายหน้าร้าน** `[อนุมาน]` — ต้องยืนยันกับเจ้าของระบบ

---

## การเชื่อมต่อ

```python
import os, pyodbc
cn = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=192.168.43.250,18963;"
    "DATABASE=_db1_3f9c2a7e-8b41-4d6f-9c25-1a7e5c0d2b8f;"
    f"UID={os.environ['MIS_USER']};PWD={os.environ['MIS_PWD']};"
    "TrustServerCertificate=yes;", timeout=300)
```

**ห้าม hardcode รหัสผ่าน** — อ่านจาก env `MIS_USER` / `MIS_PWD`

---

## R1 · สินค้าขายดี 10 อันดับ

```sql
SELECT TOP 10 i.Brand, i.ItemName,
       SUM(CAST(f.SalesQty AS bigint)) AS qty,
       SUM(f.SalesAmount)              AS amount
FROM rpt.fact_sales_itec f
JOIN rpt.dim_item_itec  i ON i.ItemId = f.ItemId
WHERE f.Status = 0 AND f.SalesCrDatetime >= '2026-01-01'
GROUP BY i.Brand, i.ItemName
ORDER BY qty DESC;
```

**⏱ 0.38 วินาที**

| Brand         | สินค้า                                   |      ชิ้น |  ยอด (บาท) |
| ------------- | ---------------------------------------- | --------: | ---------: |
| SCREEN CARE   | Super7CarePlus (ในปีที่ 2+5)             | 5,007,817 | 28,774,811 |
| 7 SCREEN CARE | 7 Screen Care 180 Days                   | 1,478,092 |  9,103,034 |
| 7 SCREEN CARE | 7 Screen Care 1 Year                     | 1,287,695 | 15,244,615 |
| 7 SCREEN CARE | 7 Screen Care 90 Days                    | 1,005,568 |  4,439,917 |
| CYBER         | Cyber Care +                             |   710,220 | 10,675,458 |
| CYBER         | ProMax Cyber Care+ ประกันภัยไซเบอร์ 1 ปี |   496,758 | 13,735,544 |
| 7DEGREE       | PS 7Degrees Bluetooth Speaker SP-02      |   486,379 | 31,384,668 |
| 7 SCREEN CARE | 7 Screen Care 2 Year                     |   471,007 | 19,140,499 |
| 7DEGREE       | PS Mini Fan                              |   436,021 | 37,283,852 |
| SCREEN CARE   | ProMax Care                              |   404,291 | 12,308,214 |

> **สินค้าขายดีตามจำนวนชิ้นคือ "ประกันและบริการ" ไม่ใช่เครื่อง** — Screen Care · Cyber Care · ProMax Care
> เป็นสินค้าพ่วงที่ขายไปกับเครื่อง · แบรนด์ `7DEGREE` และ `SCREEN CARE` เป็น **house brand ของ COM7 เอง**
> ถ้าอยากได้อันดับของ "เครื่อง" ต้องกรอง `Main_Product_Dimension` ก่อน (ดู R3)

---

## R2 · ยอดขายแยกตามแบรนด์ร้าน

```sql
SELECT b.SHOP_BRAND,
       COUNT(DISTINCT f.SalesId)       AS bills,
       SUM(CAST(f.SalesQty AS bigint)) AS qty,
       SUM(f.SalesAmount)              AS amount
FROM rpt.fact_sales_itec f
JOIN ci.clean_branch    b ON b.Branch_ID = f.SalesBranch
WHERE f.Status = 0 AND f.SalesCrDatetime >= '2026-01-01'
GROUP BY b.SHOP_BRAND
ORDER BY amount DESC;
```

**⏱ 1.0 วินาที · 32 แถว**

| แบรนด์ร้าน | บิล | ชิ้น | ยอด (บาท) |
|---|---:|---:|---:|
| BaNANA | 432,357 | 8,732,014 | 22,690,995,952 |
| ~~Audit~~ ⚠️ | 10,327 | 25,222,842 | 19,327,863,381 |
| Studio7 | 565,154 | 2,730,850 | 18,855,675,397 |
| Online | 613,305 | 749,408 | 2,930,147,912 |
| Franchise | 30,330 | 291,553 | 1,953,323,084 |
| Event | 43,762 | 191,138 | 1,287,621,418 |
| Samsung | 38,587 | 227,252 | 698,337,325 |
| Xiaomi | 52,089 | 198,105 | 295,102,653 |
| iCare | 68,934 | 142,147 | 291,283,394 |
| Oppo | 10,335 | 72,172 | 146,658,631 |
| E-Quip | 13,849 | 32,420 | 140,646,844 |
| KingKong | 12,012 | 70,833 | 135,291,782 |
| Bb+Bplay | 15,363 | 27,844 | 101,284,480 |
| Wholesale | 70 | 27,451 | 82,224,596 |
| Huawei | 7,056 | 25,873 | 72,931,549 |

> **Studio7 มีบิลมากกว่า BaNANA (565k vs 432k) แต่ยอดใกล้เคียงกัน** — Studio7 ขายของแพงกว่าต่อชิ้น
> BaNANA ขาย 8.7 ล้านชิ้น ส่วน Studio7 ขาย 2.7 ล้านชิ้น = **ยอดต่อชิ้นของ Studio7 สูงกว่าประมาณ 2.7 เท่า**

เติม `AND b.SHOP_BRAND <> 'Audit'` เพื่อตัดรายการบัญชีภายในออก

---

## R3 · ยอดขายรายเดือนแยกตามมิติสินค้า

```sql
SELECT FORMAT(f.SalesCrDatetime,'yyyy-MM') AS ym,
       c.Main_Product_Dimension,
       SUM(f.SalesAmount) AS amount
FROM rpt.fact_sales_itec f
JOIN ci.clean_item_category_itec c ON c.ItemId = f.ItemId
WHERE f.Status = 0 AND f.SalesCrDatetime >= '2026-06-01'
GROUP BY FORMAT(f.SalesCrDatetime,'yyyy-MM'), c.Main_Product_Dimension
ORDER BY ym, amount DESC;
```

**⏱ 24.6 วินาที · 42 แถว** — ช้าเพราะ `clean_item_category_itec` คำนวณ flag 66 ตัวตอน query

| มิติสินค้า (มิ.ย. 2026) | ยอด (บาท) |
|---|---:|
| **Smart Phone** | 4,169,909,103 |
| Tablet | 929,197,285 |
| Notebook | 652,446,481 |
| Accessory and Others | 192,104,300 |
| Smart Watch | 172,009,443 |
| HeadSet&Earpiece | 97,823,026 |
| Mouse&Keyboard | 59,722,355 |
| PC | 48,198,172 |
| Adapter/Charger/Powerbank | 35,945,858 |
| Insurance | 34,050,452 |
| PC&Notebook Component | 32,032,436 |
| Console Gaming | 17,816,137 |
| Software | 10,550,059 |
| Camera | 8,319,961 |

ก.ค. 2026: Smart Phone 4,533,127,725 บาท

> **Smart Phone คิดเป็นราว 2 ใน 3 ของยอดขายทั้งหมด** — สอดคล้องกับตำแหน่งธุรกิจของ COM7

**ถ้าต้องการเร็วกว่านี้** ใช้ `ci.integrated_sale_and_inventory` ที่คำนวณมิติไว้แล้ว (ดู R10)

---

## R4 · ลูกค้าที่ซื้อมากที่สุด (เชื่อมกับ CRM)

```sql
SELECT TOP 10 m.crmid,
       COUNT(DISTINCT CONCAT(f.SalesBranch,'-',f.SalesId)) AS bills,
       SUM(f.SalesAmount) AS amount
FROM rpt.fact_sales_itec f
JOIN (SELECT DISTINCT salesid, salesbranch, crmid          -- ⚠️ DISTINCT บังคับ
      FROM rpt.dim_mem_itec
      WHERE crmid IS NOT NULL AND LEN(crmid) = 13) m       -- ตัด '-' และค่าเสียออก
  ON m.salesid = f.SalesId AND m.salesbranch = f.SalesBranch
WHERE f.Status = 0 AND f.SalesCrDatetime >= '2026-01-01'
GROUP BY m.crmid
ORDER BY amount DESC;
```

**⏱ 13.7 วินาที**

| crmid (mask) | บิล | ยอด (บาท) |
|---|---:|---:|
| `M0625119█████` | 10,861 | 165,135,016 |
| `M0625118█████` | 5,902 | 72,285,348 |
| `M0625115█████` | 4,218 | 39,685,884 |
| `M0424000█████` | 3,646 | 34,024,323 |
| `M0420098█████` | 2,204 | 26,707,025 |

> **10,861 บิลใน 8 เดือน = ~45 บิลต่อวัน** — ไม่ใช่ลูกค้าบุคคล น่าจะเป็นบัญชีองค์กร ตัวแทนจำหน่าย
> หรือรหัสที่พนักงานใช้เวลาลูกค้าไม่แจ้งสมาชิก `[อนุมาน]`
> **ต้องกรองบัญชีกลุ่มนี้ออกก่อนทำ analytics ลูกค้ารายบุคคล** → [[Customer Identity]]

**`crmid` มี prefix หลายแบบ:** `M06` · `M04` · `M01` · `M02` — ยังไม่ทราบว่าแปลว่าอะไร
เทียบกับเอกสาร CRM ที่ระบุรูปแบบ `M06xxxxxxx` → [[CRM - Data Dictionary]]

---

## R5 · สัดส่วนวิธีชำระเงิน

```sql
SELECT t.PAYMENT_TYPE, t.INSTALLMENT_TYPE,
       COUNT_BIG(*) AS trn, SUM(bk.[TRANS AMT]) AS amount
FROM rpt.fact_bank_itec bk
JOIN ci.trn_category_ITEC t ON t.TYPE = bk.TYPE
WHERE bk.[TRANS DATE] >= '2026-01-01'
GROUP BY t.PAYMENT_TYPE, t.INSTALLMENT_TYPE
ORDER BY amount DESC;
```

**⏱ 96 วินาที** — ช้าเพราะ `ci.trn_category_ITEC` เองก็เป็น view ที่ต้องคำนวณ

| วิธีชำระ | แบบ | รายการ | ยอด (บาท) |
|---|---|---:|---:|
| **QR Code** | Full Payment | **1,971,524** | 13,663,640,565 |
| **Credit Card** | **Installment** | 535,561 | 12,135,357,725 |
| Credit Card | Full Payment | 482,612 | 3,786,173,622 |
| **Personal Loan** | Full Payment | 76,657 | 1,491,145,269 |
| Payment Gateway | Full Payment | 59,289 | 970,311,514 |
| Unknown | Full Payment | 61 | 239,440 |

> **QR Code นำด้านจำนวนรายการ (63%) แต่บัตรเครดิตผ่อนชำระมียอดต่อรายการสูงกว่ามาก**
> QR = 6,930 บาท/รายการ · Credit Installment = **22,660 บาท/รายการ**
> → คนซื้อของแพงใช้บัตรผ่อน คนซื้อของถูกสแกน QR

---

## R6 · คู่แข่งของ UFUND ที่หน้าร้าน

```sql
SELECT t.BANK_NAME, t.INSTALLMENT_TYPE,
       COUNT_BIG(*) AS trn, SUM(bk.[TRANS AMT]) AS amount
FROM rpt.fact_bank_itec bk
JOIN ci.trn_category_ITEC t ON t.TYPE = bk.TYPE
WHERE bk.[TRANS DATE] >= '2026-01-01' AND t.PAYMENT_TYPE = 'Personal Loan'
GROUP BY t.BANK_NAME, t.INSTALLMENT_TYPE
ORDER BY amount DESC;
```

**⏱ 97 วินาที**

| ผู้ให้บริการ | รายการ | ยอด (บาท) |
|---|---:|---:|
| **Samsung Finance** | 76,657 | **1,491,145,269** |

> **Samsung Finance+ ปล่อยสินเชื่อ 1,491 ล้านบาทที่หน้าร้าน COM7 ในปี 2026 (ถึง ส.ค.)**
> เป็นยอดที่ [[UFUND]] ไม่ได้ — **คำถามเชิงธุรกิจที่ตอบได้จากข้อมูลนี้โดยตรง**
>
> `SG Finance+` และ `Pay Next Extra (ASEND)` มีอยู่ในตารางแม็ป แต่**ไม่พบธุรกรรมในปี 2026**
> → อาจเลิกใช้แล้ว หรือบันทึกช่องทางอื่น

---

## R7 · ตามรอยเครื่องจาก Serial Number

```sql
SELECT COUNT_BIG(*) AS rows_with_serial,
       COUNT(DISTINCT SerialNo) AS distinct_serial
FROM rpt.fact_sales_itec
WHERE Status = 0 AND SerialNo IS NOT NULL AND SerialNo <> ''
  AND SalesCrDatetime >= '2026-08-01';
```

**⏱ 1.4 วินาที** — ส.ค. 2026: 600,122 บรรทัดมี serial · serial ไม่ซ้ำ 136,077

> **บรรทัดมากกว่า serial ไม่ซ้ำ 4.4 เท่า** — serial เดียวปรากฏหลายบรรทัด
> อาจเป็นค่าซ้ำจากสินค้าที่ไม่มี serial จริง (เช่น ประกัน) หรือมีการคืน/เปลี่ยนเครื่อง — **ต้องตรวจก่อนใช้ตามรอยเครื่อง**

### ตามรอยเครื่องเต็มรูปแบบ

```sql
-- ขายเมื่อไหร่ ที่ไหน
SELECT f.SalesCrDatetime, b.CleanBranchName, i.ItemName, f.SalesAmount
FROM rpt.fact_sales_itec f
JOIN ci.clean_branch b ON b.Branch_ID = f.SalesBranch
JOIN rpt.dim_item_itec i ON i.ItemId = f.ItemId
WHERE f.SerialNo = ? AND f.Status = 0;

-- อยู่สาขาไหนบ้างก่อนถูกขาย
SELECT OnHandAsOf, Branch, Qty, TransferingTo
FROM rpt.onhandendmonth_itec
WHERE Serial = ? ORDER BY OnHandAsOf;

-- เคลื่อนไหวในระบบ ERP
SELECT DATEPHYSICAL, Transaction_Type, INVENTLOCATIONID, QTY, CompanyCode
FROM rpt.fact_trans_fo
WHERE INVENTSERIALID = ? ORDER BY DATEPHYSICAL;
```

---

## R8 · ธงความผิดปกติจากการ reconcile บัตร

```sql
SELECT Split_Bill, Multiple_Branch, Multiple_Customer_name, COUNT_BIG(*) AS n
FROM ci.creditcard_trn_summary
GROUP BY Split_Bill, Multiple_Branch, Multiple_Customer_name
ORDER BY n DESC;
```

**⏱ 142 วินาที**

| Split_Bill | Multiple_Branch | Multiple_Customer_name | รายการ |
|---|---|---|---:|
| Normal | Normal | Normal | 2,698,681 |
| **Potential Fraud** | Normal | Normal | 67,077 |
| **Potential Fraud** | Normal | **Potential Fraud** | 13,154 |
| **Potential Fraud** | **Potential Fraud** | Normal | 625 |
| **Potential Fraud** | **Potential Fraud** | **Potential Fraud** | 120 |

> **80,976 รายการ (2.9%) ถูกตั้งธง Potential Fraud** และ **120 รายการติดธงครบทั้ง 3 ตัว** — กลุ่มเสี่ยงสูงสุด
> ระบบตรวจจับนี้**มีอยู่แล้ว** ไม่ต้องสร้างใหม่ · view นี้**ไม่มีเลขบัตร** จึงใช้ได้ปลอดภัย
> → [[Analytics & AI]]

---

## R9 · สาขาที่มียอดขายสูงสุด

```sql
SELECT TOP 10 b.CleanBranchName, b.SHOP_BRAND, b.CLEAN_PROVINCE,
       SUM(f.SalesAmount) AS amount
FROM rpt.fact_sales_itec f
JOIN ci.clean_branch b ON b.Branch_ID = f.SalesBranch
WHERE f.Status = 0 AND f.SalesCrDatetime >= '2026-01-01'
GROUP BY b.CleanBranchName, b.SHOP_BRAND, b.CLEAN_PROVINCE
ORDER BY amount DESC;
```

**⏱ 0.51 วินาที**

| สาขา | แบรนด์ | จังหวัด | ยอด (บาท) |
|---|---|---|---:|
| ⚠️ (73) FBI RETAIL- Cost | Audit | Bangkok | 19,203,820,586 |
| ⚠️ E-Commerce Warehouse | Online | Samut Prakan | 2,925,741,892 |
| ⚠️ Wholesale- Edu & Enterprise | Event | Bangkok | 940,167,952 |
| **Studio 7-Future Park-Rangsit** | Studio7 | Pathum Thani | 675,993,154 |
| Studio 7-Central-Phuket | Studio7 | Phuket | 648,250,980 |
| Studio 7-Central-Ladprao | Studio7 | Bangkok | 594,588,452 |
| Studio 7-Mega-Bangna | Studio7 | **Trat** ⚠️ | 589,496,919 |
| Studio 7-Central-Westgate | Studio7 | Nonthaburi | 550,635,788 |
| Studio7-Central-Chiangmai Fest | Studio7 | Chiang Mai | 502,644,318 |
| Studio 7-Central-Pattaya | Studio7 | Chonburi | 480,666,392 |

> **3 อันดับแรกไม่ใช่หน้าร้าน** — บัญชีภายใน · คลังอีคอมเมิร์ซ · ขายส่งองค์กร
> **หน้าร้านจริงอันดับ 1 คือ Studio 7 Future Park Rangsit** และ 7 ใน 10 เป็น Studio7 ทั้งหมด
> ⚠️ **ข้อผิดพลาดในข้อมูล: "Studio 7-Mega-Bangna" ถูกระบุจังหวัดเป็น Trat** ทั้งที่เมกาบางนาอยู่สมุทรปราการ
> → ตัวอย่างจริงของปัญหาคุณภาพข้อมูล [[Data Standardization & Quality]]

---

## R10 · สินค้าที่ค้างสต็อกนานที่สุด

```sql
SELECT TOP 10 Brand, ItemName,
       AVG(CAST(SHELF_LIFE_DAY AS float)) AS avg_shelf,
       SUM(NO_OF_SALE_UNIT)               AS qty
FROM ci.integrated_sale_and_inventory
WHERE SHELF_LIFE_DAY IS NOT NULL AND NO_OF_SALE_UNIT > 0
  AND END_MONTH_DATE >= '2026-01-01'
GROUP BY Brand, ItemName
HAVING SUM(NO_OF_SALE_UNIT) > 100
ORDER BY avg_shelf DESC;
```

**⏱ 18.1 วินาที**

| Brand | สินค้า | วันเฉลี่ยบนชั้น | ชิ้นที่ขาย |
|---|---|---:|---:|
| APPLE | บริการสำหรับช่างเทคนิค-ซ่อมแซม | 26.2 | 53,070 |
| REALME | OL@ Realme Smartphone C63 | 26.0 | 516 |
| CASE CLUB | Personalised Artwork | 25.8 | 6,636 |
| COM7 | Transportation Fee 60 | 25.8 | 581 |
| 7DEGREE | PS Mini Fan | 23.8 | 443,350 |
| ICARE | ค่าบริการ Restore / Re-OS / Clean | 23.6 | 9,160 |
| COM7 | PS 7Degrees Touch Setbox 5 in 1 | 23.6 | 286,717 |

> `SHELF_LIFE_DAY` สูงสุดที่พบคือ ~26 วัน — **ดูเหมือนถูกจำกัดอยู่ในช่วง 1 เดือน**
> น่าจะคำนวณภายในเดือนเดียว ไม่ใช่อายุสะสมจริง `[อนุมาน]` — ต้องยืนยันนิยามกับเจ้าของระบบ
> รายการที่ติดอันดับหลายตัวเป็น**ค่าบริการ** ไม่ใช่สินค้าที่มีสต็อกจริง

---

## เชื่อมลูกค้า ITEC เข้ากับ UFUND

ยังทดสอบไม่ได้เพราะอยู่คนละ server แต่เส้นทางที่ควรใช้:

```
ITEC  rpt.dim_mem_itec.crmid
        ↓  (= member_id)
CRM   members.member_id → members.customer_master_id
        ↓
CRM   customer_master.citizen_no        ← เลขบัตรประชาชน
        ↓  (= TAX_ID)
K2    PERSON.TAX_ID → PERSON.PERSON_ID → CONTRACT
```

**ยังไม่ทดสอบ** — ต้องมี connection ไป CRM ก่อน → [[CRM Issues]] · [[Customer Identity]]

---

## หมายเหตุเรื่องความเร็ว

| ประเภท query | เวลา |
|---|---|
| join `fact_sales_itec` กับ dimension ธรรมดา | **< 1 วินาที** |
| group by บน `fact_sales_itec` ทั้งปี | 0.4–3 วินาที |
| แตะ `ci.clean_item_category_itec` | **18–66 วินาที** (คำนวณ flag 66 ตัว) |
| แตะ `ci.trn_category_*` | **28–97 วินาที** |
| แตะ `ci.creditcard_*` | **30–142 วินาที** |

> **view ในชั้น `ci` ช้ากว่า `rpt` มาก** เพราะเป็นการคำนวณสด ไม่ใช่ตารางที่ materialize ไว้
> ถ้าจะใช้บ่อย ควร materialize ที่ชั้น Bronze/Silver แทนการ query สดทุกครั้ง → [[ETL & Spark]]

---

## เชื่อมกับโน้ตอื่น

[[ITEC Overview]] · [[ITEC - Data Dictionary]] · [[CRM - Data Dictionary]] · [[K2 - Query Cookbook]] · [[Customer Identity]] · [[Analytics & AI]] · [[SQL & Source Schemas]]
