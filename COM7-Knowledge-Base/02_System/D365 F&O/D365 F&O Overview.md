# D365 F&O Overview

**ความเคลื่อนไหวสต็อกของทุก BU รวมที่เดียว — 276 ล้านแถว · 21 บริษัท · ปี 2020 ถึงปัจจุบัน**

สำรวจฐานจริง 2026-09-23
พจนานุกรมราย 20 คอลัมน์ → [[D365 F&O - Transaction_FO Dictionary]]
SQL ที่รันได้จริง + แผนที่ join → [[D365 F&O - Query Cookbook]]
ระบบพี่น้อง → [[ITEC Overview]] · สารบัญระบบ → [[System Inventory]]

> ⚠️ `MIN(DATEPHYSICAL)` ตอบ 2005-04-07 แต่**ก่อนปี 2020 มีแค่ 4 แถว** ซึ่งเป็นรายการคีย์ย้อนหลัง
> ใช้ `WHERE DATEPHYSICAL >= '2020-01-01'` เสมอ

> **ห้ามเดา** ไม่รู้เขียนว่าไม่รู้ · ข้อสันนิษฐานทำเครื่องหมาย `[อนุมาน]`
> credential อ่านจาก env `FO_USER` / `FO_PWD` เท่านั้น — ดู [[Environment Setup]]

---

## ต่อยังไง

```python
import db
df = db.query("fo",     "SELECT TOP 10 * FROM dbo.Transaction_FO")   # ปลายทาง เรียบเรียงแล้ว
df = db.query("fo_raw", "SELECT TOP 10 * FROM dbo.tb_InventTrans")   # ต้นทาง ยังไม่กรอง
```

| profile | ฐาน | ใช้เมื่อไหร่ |
|---|---|---|
| `fo` | `PROJECT_1` | **ใช้ตัวนี้เป็นหลัก** · 83 ตาราง · 1,241 ล้านแถว |
| `fo_raw` | `syndpdev001` | ต้องการฟิลด์ที่ `Transaction_FO` ไม่ได้ยกมา · 73 ตาราง · 1,621 ล้านแถว |

ทั้งสองอยู่เซิร์ฟเวอร์เดียวกัน — **join ข้ามฐานได้ตรง ๆ** ด้วยชื่อเต็ม 3 ส่วน

```sql
FROM PROJECT_1.dbo.Transaction_FO t
JOIN syndpdev001.dbo.tm_Warehouse w
  ON w.SysCompanyId = t.CompanyCode AND w.WarehouseId = t.INVENTLOCATIONID
```

---

## ตารางที่ต้องรู้จัก

| ตาราง | ฐาน | แถว | คืออะไร |
|---|---|--:|---|
| `Transaction_FO` | PROJECT_1 | 276,119,863 | **ตารางหลัก** · 1 แถว = 1 ความเคลื่อนไหวสต็อก |
| `Transaction_ITEC` | PROJECT_1 | 341,084,896 | ฝั่ง ITEC คู่ขนาน · 8 คอลัมน์ · ยังไม่ได้สำรวจ |
| `Transaction_ITEC_tracking` | PROJECT_1 | 341,226,094 | เหมือนบน + สาวกลับต้นทุน/PO · 19 คอลัมน์ · ยังไม่ได้สำรวจ |
| `tb_InventTrans` | syndpdev001 | 211,129,158 | ต้นทางของ `Transaction_FO` |
| `tm_Warehouse` | syndpdev001 | 3,690 | ชื่อคลัง + **คลังพักระหว่างทาง** |
| `tb_PurchOrder` | syndpdev001 | 586,218 | ใบสั่งซื้อ · ผู้ขาย · สถานะ |
| `tm_Item` | syndpdev001 | 394,158 | ทะเบียนสินค้า · สะพานไปหมวด |
| `tm_FinDimValueSet` | syndpdev001 | 719,054 | **หมวดสินค้า 3 ชั้น** Group ▸ Category ▸ Sub |
| `inventtrans` | D365FO_DATALAKE | 289,817,143 | ต้นทางดิบ **105 คอลัมน์** · ช้ากว่ามาก |

### แผนที่การเชื่อม

```
                    PROJECT_1.dbo.Transaction_FO
                              │
        ┌─────────────────────┼──────────────────────┐
  [FO-ITEMNO]           [Ref.DocNum]          [INVENTLOCATIONID]
   + CompanyCode                               + CompanyCode
        ▼                     ▼                      ▼
   tm_Item.ItemId    tb_PurchOrder.PurchId    tm_Warehouse.WarehouseId
   + SysCompanyId     (⚠️ ไม่มี com7)          + SysCompanyId
        │
  [DefaultDimension] ──► tm_FinDimValueSet.FinancialDim
                          └─► GroupCategory ▸ Category ▸ SubCategory
```

⚠️ **ทุกเส้นที่ไปฝั่ง `syndpdev001` ต้องเติม `SysCompanyId = CompanyCode`** ไม่งั้นข้อมูลข้ามบริษัท
รายละเอียด + SQL เต็ม → [[D365 F&O - Query Cookbook]]

### คอลัมน์ของ `Transaction_FO`

| # | คอลัมน์ | ชนิด | หมายเหตุ |
|--:|---|---|---|
| 1 | `FO-ITEMNO` | varchar(80) | รหัสสินค้าฝั่ง F&O · ไม่มีค่าว่างเลย · 116,794 ค่าไม่ซ้ำ |
| 2 | `ITEC-ITEMNO` | varchar(160) | รหัสสินค้าฝั่ง ITEC · 110,245 ค่าไม่ซ้ำ · ว่าง 190,705 แถว |
| 3 | `INVENTSERIALID` | varchar(160) | 🔴 ดูกับดักข้อ 3 |
| 4 | `INVENTBATCHID` | varchar(160) | ว่าง 98.2% — ไม่ได้ใช้ |
| 5 | `INVENTLOCATIONID` | varchar(40) | = `WarehouseId` · 2,887 ค่าไม่ซ้ำ · ไม่มีค่าว่าง |
| 6 | `DATEPHYSICAL` | datetime2 | **วันทำรายการจริง** · ไม่มีค่าว่าง |
| 7 | `DATEFINANCIAL` | datetime2 | วันลงบัญชี · เป็นปี 1900 อยู่ 0.37% |
| 8 | `REFERENCECATEGORY` | bigint | รหัสตัวเลขของ `Transaction_Type` — 1:1 เป๊ะ |
| 9 | `Transaction_Type` | varchar(200) | 10 ค่า · ดูกับดักข้อ 6 |
| 10 | `Ref.DocNum` | varchar(400) | เลขที่เอกสาร · ว่าง 1,024,420 แถว |
| 11 | `QTY` | decimal(38,6) | บวก = เข้า · ลบ = ออก (มีข้อยกเว้น) |
| 12 | `costamountstd` | decimal(38,6) | ต้นทุนมาตรฐาน |
| 13 | `COSTAMOUNTPOSTED` | decimal(38,6) | ต้นทุนที่ลงบัญชี |
| 14 | `COSTAMOUNTADJUSTMENT` | decimal(38,6) | ปรับทีหลัง · 97–99% เป็น 0 |
| 15 | `RealCost` | decimal(38,6) | **ใช้ตัวนี้** = posted + adjustment |
| 16 | `InventTrans_RECID` | bigint | **ไม่ซ้ำทั้งตาราง** = grain ของตาราง |
| 17 | `TransOrigin_RECID` | bigint | ซ้ำได้ · 234,021,681 ค่าไม่ซ้ำ |
| 18 | `inventdimid` | varchar(400) | 74 ล้านค่าไม่ซ้ำ · ยังไม่รู้ว่าใช้ทำอะไร |
| 19 | `Transorigin_Sinkdate` | datetime2 | วันที่ข้อมูลไหลเข้า — ใช้วัดความสด |
| 20 | `CompanyCode` | varchar(16) | **ตัวเดียวที่บอก BU ได้** |

ดัชนีมี 2 ตัว — `(INVENTSERIALID, ITEC-ITEMNO, INVENTLOCATIONID, CompanyCode, DATEPHYSICAL)` และ `(FO-ITEMNO, CompanyCode)`
เขียน `WHERE` ให้เริ่มจากคอลัมน์ซ้ายสุดของดัชนีจะเร็วกว่ามาก

> รายละเอียดเต็มทุกคอลัมน์ — การกระจายค่า · ความยาว · ค่าปลอม · สูตรสำเร็จ
> → **[[D365 F&O - Transaction_FO Dictionary]]**

---

## 🔴 กับดัก 8 ข้อ — อ่านก่อนเขียนคิวรีทุกครั้ง

### 1. ไม่ใช่ 3 BU — มี 21 บริษัท

บรีฟเดิมบอก `com7` `bnn` `dou7` แต่ของจริงมี **21 CompanyCode**

| BU | แถว | % | ช่วงข้อมูล |
|---|--:|--:|---|
| `com7` | 251,653,202 | 91.14 | 2005-04-07 → 2026-09-21 |
| `dou7` | 13,369,482 | 4.84 | 2020-11-02 → 2026-09-22 |
| `bnn` | 5,183,648 | 1.88 | 2021-08-03 → 2026-09-22 |
| `drph` | 3,612,265 | 1.31 | 2022-11-28 → 2026-06-30 |
| `lor` | 1,745,719 | 0.63 | 2023-04-28 → 2026-12-19 |
| `drl` | 335,890 | 0.12 | 2020-06-01 → **2024-01-05 (ตาย)** |
| `gi` + `gi01`–`gi12` | 216,401 | 0.08 | 2023-12 → 2026-09 |
| `pss` · `nov` | 3,256 | 0.00 | เล็กมาก |

- `com7` = COMSEVEN (หลัก) · `bnn` = Adept · `dou7` = Double7 — ยืนยันจากบรีฟ
- ชื่อเต็มของ `drph` `lor` `drl` `pss` `nov` `gi*` **ยังไม่รู้** ต้องถาม MIS-ERP
- **`drl` หยุดส่งข้อมูลตั้งแต่ ม.ค. 2024** — ถ้าไม่ได้ตั้งใจดูย้อนหลัง ให้ตัดทิ้ง

### 2. 🔴 การโอนสต็อกมี **2 รูปแบบคนละเรื่อง** — เขียนคิวรีเดียวครอบไม่ได้

นี่คือข้อที่พังง่ายที่สุด **`com7` ไม่มีแถว `Transfer order shipment` แม้แต่แถวเดียว**

**com7 — 2 ขา จบในวันเดียว** (`Transaction_Type = 'Transfer'`)

```
JN26000829375  Transfer  คลัง    4  QTY -1   2026-08-01   ← ออกจากต้นทาง
JN26000829375  Transfer  คลัง 2540  QTY +1   2026-08-01   ← เข้าปลายทาง
```

**dou7 · drph · lor · bnn · drl — 4 ขา ผ่านคลังพัก คนละวัน**

```
TO72607-1621  Transfer order shipment  79998  +1   2026-08-01  ← เข้าคลังพัก
TO72607-1621  Transfer order shipment  70108  -1   2026-08-01  ← ออกจากต้นทาง
TO72607-1621  Transfer order receive   79998  -1   2026-08-11  ← ออกจากคลังพัก
TO72607-1621  Transfer order receive   71001  +1   2026-08-11  ← เข้าปลายทาง
```

ตรวจแล้วกับข้อมูลจริงเดือน ส.ค. 2026

| รูปแบบ | ชุดที่เข้าเกณฑ์ |
|---|--:|
| com7 · 2 แถว ยอดสุทธิ 0 | 19,915 จาก ~20,000 |
| dou7 · 4 แถว 2 ประเภท ยอดสุทธิ 0 | 51,983 จาก 56,686 |
| dou7 · 2 แถว (ส่งแล้วยังไม่รับ) | 4,665 |

**คลังพักระหว่างทางของแต่ละ BU** — มาจาก `tm_Warehouse.InTransiteWarehouse` ไม่ต้องเดา

| BU | คลังพัก |
|---|---|
| `com7` · `bnn` · `drl` | `99999` |
| `dou7` | `79998` |
| `drph` | `69998` |
| `lor` | `61998` |
| `gi` ทั้งตระกูล | `62901` |

**ของค้างระหว่างทาง** — ส่งแล้วปลายทางยังไม่รับ

| BU | ค้าง | จากทั้งหมด |
|---|--:|--:|
| `dou7` | 10,199 | 2,058,628 |
| `drph` | 421 | 22,715 |
| `bnn` | 205 | 58,677 |
| `lor` | 5 | 1,889 |

### 3. 🔴 `INVENTSERIALID` เก็บ **ข้อความ `'NULL'`** 116 ล้านแถว

ไม่ใช่ค่าว่างจริง เป็นตัวอักษร 4 ตัว — `WHERE INVENTSERIALID IS NULL` จับไม่ได้

| สภาพ | แถว | % |
|---|--:|--:|
| ข้อความ `'NULL'` | 116,195,794 | 42.08 |
| NULL จริง | 7,285,193 | 2.64 |
| **รวมใช้ไม่ได้** | **123,480,987** | **44.72** |

โผล่ทุกปีตั้งแต่ 2020 ถึง 2026 · เกือบทั้งหมดเป็น `com7` · `bnn` มี 4,606 แถว

```sql
-- ต้องเขียนแบบนี้เสมอ
WHERE INVENTSERIALID IS NOT NULL AND INVENTSERIALID <> 'NULL'
```

`Transfer order shipment` / `receive` **ไม่มีปัญหานี้เลย** (0 แถว) มีแต่ NULL จริง

**ซ้ำร้าย ยังมี serial ปลอมอีกชั้น** — `'PENDING'` ถูกใช้ **120,726 ครั้ง ข้าม 3,847 สินค้า** (เฉพาะ com7 ปี 2026)
รวมถึงเลขหลักเดียว `1` `2` `3` และ `1234` — serial จริงต้องผูกกับสินค้าตัวเดียว

```sql
AND INVENTSERIALID NOT IN ('PENDING', '1234') AND LEN(INVENTSERIALID) >= 8
```

### 4. 🔴 `FO-ITEMNO` **บอก BU ไม่ได้**

บรีฟเดิมบอกว่ารหัสสินค้าบอก BU ด้วย — จริงแค่ 2 ตระกูล ที่เหลือปนกันหมด

| ขึ้นต้นด้วย | ไปหา BU ไหนบ้าง | เชื่อได้ไหม |
|---|---|---|
| `D2*` | `drph` เท่านั้น (3,612,265) | ✅ |
| `GI-*` | `gi` + `gi01`–`gi12` — **12 บริษัท** | ⚠️ บอกได้แค่ตระกูล |
| `D0-9*` | `drl` 335,890 · `bnn` 22,028 | ❌ |
| `N*` | `bnn` 97,409 · `nov` 791 | ❌ |
| `P*` | `bnn` 5,319 · `pss` 2,465 · `lor` 327 | ❌ |
| ตัวเลขอื่น | `com7` 251.6M · `lor` 1.7M · อีก 3 BU | ❌ |
| อักษรอื่น | `dou7` 13.4M · `bnn` 5.0M · `com7` 3 | ❌ |

> **ใช้คอลัมน์ `CompanyCode` เท่านั้น** อย่าแกะจากรหัสสินค้า
> รหัสขึ้นต้น `84` ยาว 14 หลักมีแค่ 7,824 แถว ไม่ใช่รูปแบบหลักของ com7 อย่างที่เคยเข้าใจ

### 4.5 🔴 หมวดสินค้าอยู่คนละฐาน และไม่ใช่ลำดับชั้นจริง

`Transaction_FO` **ไม่มีคอลัมน์หมวดสินค้า** ต้องเดินสองต่อ

```
[FO-ITEMNO] + CompanyCode -> tm_Item -> DefaultDimension -> tm_FinDimValueSet
```

ขนาด: **26 บริษัท · 126 GroupCategory · 487 Category · 3,122 SubCategory**

🔴 **345 จาก 487 หมวด (71%) ชี้ไปมากกว่า 1 กลุ่ม** — `Common` โผล่ใต้ **67 กลุ่ม** · `iPhone` 39 กลุ่ม
**ห้าม `GROUP BY CategoryName` เดี่ยว ๆ** ต้องจับคู่ `GroupCategoryName` เสมอ

🔴 **com7 ยัดของ demo ทุกชนิดลงกลุ่ม `iPhone`** — แอร์ Xiaomi และหูฟัง Redmi ก็อยู่ในนั้น
ค่าว่าง ~5% ทั้งสามชั้น · มีชื่อหมวดที่มีอักขระขยะ (`ฺฺBBP` 164,641 แถว)

รายละเอียด + ตัวอย่าง → [[D365 F&O - Query Cookbook]]

### 5. 🔴 BCLS ใช้ตัวพิมพ์ใหญ่ FO ใช้ตัวพิมพ์เล็ก

ใน `tb_InventTrans` ต้นทาง

```
FO   com7  dou7  bnn  drph  lor        ← ตัวเล็ก
BCLS DOU7  DRPH  LOR                   ← ตัวใหญ่ บริษัทเดียวกัน
```

join โดยไม่ทำตัวพิมพ์ให้ตรงกันจะได้แถวหาย — ใช้ `UPPER()` ทั้งสองฝั่ง

`tb_InventTrans` ทั้งหมด 211,129,158 แถว · **`SysSourceRef = 'FO'` 205,194,481 แถว (97.19%)** · BCLS 5,934,677 (2.81%)
ตารางอ้างอิงอื่นไม่ต้องกรอง — `tm_Warehouse` และ `tb_PurchOrder` เป็น FO ทั้งหมด
มีแต่ `tm_Item` ที่ปน (FO 360,739 · BCLS 33,419)

### 6. QTY บวก/ลบ **ไม่ได้แปลว่า เข้า/ออก เสมอไป**

กฎ "ลบ = outbound · บวก = inbound" ใช้ได้ แต่มีข้อยกเว้น

| ประเภท | refcat | แถว | QTY บวก | QTY ลบ |
|---|--:|--:|--:|--:|
| Sales order | 0 | 104,836,743 | **145,047** | 104,691,696 |
| Transfer | 6 | 102,811,609 | 51,405,804 | 51,405,805 |
| Purchase order | 3 | 40,237,824 | 40,080,789 | **157,035** |
| Transaction | 4 | 17,461,345 | 6,104,439 | 11,356,906 |
| Transfer order shipment | 21 | 4,840,126 | 2,420,063 | 2,420,063 |
| Transfer order receive | 22 | 4,803,170 | 2,401,585 | 2,401,585 |
| **Weighted average inventory closing** | 7 | 1,024,414 | 512,207 | 512,207 |
| Counting | 13 | 43,087 | 316 | 42,771 |
| Inventory adjustment | 5 | 32,285 | 12,376 | 19,909 |
| Fixed assets | 20 | 29,260 | 0 | 29,260 |

- Sales order ที่ QTY บวก = **รับคืน/ยกเลิกบิล**
- Purchase order ที่ QTY ลบ = **คืนของให้ผู้ขาย**
- **`Weighted average inventory closing` ไม่ใช่การเคลื่อนไหวของจริง** เป็นรายการปิดบัญชีต้นทุนถัวเฉลี่ย — ต้องตัดทิ้งทุกครั้งที่นับสต็อก
- ไม่มีแถวไหน QTY = 0 เลย
- `REFERENCECATEGORY` เป็นรหัสตัวเลขของ `Transaction_Type` แบบ **1:1 เป๊ะ** — ใช้แทนกันได้ กรองด้วยตัวเลขเร็วกว่า

### 7. ต้นทุนต้องใช้ `RealCost`

มี 4 คอลัมน์ ต่างกันดังนี้

```
RealCost = COSTAMOUNTPOSTED + COSTAMOUNTADJUSTMENT
```

ตรวจทั้งเดือน ก.ย. 2026 · **3,313,167 แถว ตรงหมด ไม่มีข้อยกเว้น**

| คอลัมน์ | คืออะไร |
|---|---|
| `costamountstd` | ต้นทุนมาตรฐาน — เกือบเท่า posted เสมอ |
| `COSTAMOUNTPOSTED` | ต้นทุนที่ลงบัญชีตอนทำรายการ |
| `COSTAMOUNTADJUSTMENT` | ปรับทีหลัง — **97–99% เป็น 0** |
| `RealCost` | **ใช้ตัวนี้** ต้นทุนสุดท้ายหลังปรับ |

⚠️ `Sales order` มี `RealCost = 0` อยู่ **15,414,871 แถว (14.7%)** — ยังไม่รู้สาเหตุ

⚠️ **ขาโอนของ com7 ต้นทุนสองฝั่งไม่เท่ากัน** ตัวอย่างจริง `-15,173.39` กับ `+14,979.37`
`[อนุมาน]` มีการตีราคาใหม่ตอนโอน — QTY หักล้างกันพอดี แต่ต้นทุนไม่

### 8. ความสดของข้อมูลไม่เท่ากันทุก BU

`Transorigin_Sinkdate` = วันที่ข้อมูลไหลเข้า (เทียบ ณ 2026-09-23)

| BU | ไหลเข้าล่าสุด | สภาพ |
|---|---|---|
| com7 · dou7 · bnn · lor · gi ส่วนใหญ่ | 2026-09-22 | ✅ สดรายวัน |
| `gi09` | 2026-09-21 | ✅ |
| `gi06` | 2026-09-07 | ⚠️ ช้า 16 วัน |
| `pss` | 2026-09-04 | ⚠️ ช้า 19 วัน |
| `nov` | 2026-08-26 | ⚠️ ช้า 28 วัน |
| **`drph`** | 2026-07-07 | 🔴 **ช้า 78 วัน** |
| **`gi04`** | 2026-06-09 | 🔴 ช้า 106 วัน |
| **`drl`** | 2024-08-12 | 🔴 **ตายไปแล้ว 2 ปี** |

---

## สะพานเชื่อมไป ITEC

`ITEC-ITEMNO` → `rpt.dim_item_itec.ItemId` (= `PRODUCT_ID` ฝั่ง `ci`) → [[ITEC - Data Dictionary]]

ทดสอบกับ com7 ปี 2026 · 35,418 คู่รหัส

| วัดแบบ | ผล |
|---|---|
| นับเป็นรหัส | 35,354 / 35,418 = **99.8%** |
| นับเป็นแถว | 35,829,914 / 35,830,100 = **100.0%** |
| 1 `ITEC-ITEMNO` ผูกกับ `FO-ITEMNO` | **1 ตัวเสมอ** ไม่มีแตกแขนง |

**รหัสที่เชื่อมไม่ติด 64 ตัว มีลักษณะร่วมกันอย่างเดียว** — `ITEC-ITEMNO` เท่ากับ `FO-ITEMNO` เป๊ะ (ทุกตัวเป็นเลข 14 หลักขึ้นต้น `84`)

> `[อนุมาน]` เมื่อสินค้าไม่มีรหัสฝั่ง ITEC ระบบจะคัดลอกรหัส F&O มาใส่แทน
> ใช้เป็นกฎตรวจได้: `WHERE [ITEC-ITEMNO] = [FO-ITEMNO]` คือของที่ไม่มีคู่ฝั่ง ITEC

⚠️ `ITEC-ITEMNO` **ไม่ใช่บาร์โค้ด EAN อย่างเดียว** เคยเข้าใจผิด — เป็นรหัสสินค้า ITEC ซึ่งปนกันหลายแบบ

```
0000157849  ->  01 035 0070        (มีช่องว่างในรหัส)
0000044837  ->  7654236780100      (13 หลัก แบบ EAN)
0000156933  ->  CYBERCARE01        (ตัวอักษร)
            ->  SERVICE DELIVERY FEE - SIZE M/L PT   (ยาว 34 ตัว)
            ->  ปิดการใช้งาน 84220020090083          (ภาษาไทยปนตัวเลข)
```

ความยาวพบตั้งแต่ 1 ถึง 35 ตัวอักษร — **ห้ามสมมติความยาว ห้าม cast เป็นตัวเลข**

### 🔴 `rpt.fact_trans_fo` ฝั่ง ITEC เป็นกระจกเงาที่ **ช้า 45 วัน**

ฐาน MIS มี view ชื่อ `rpt.fact_trans_fo` ซึ่งคือตารางเดียวกันนี้ — สะดวกเพราะ join กับ dimension ของ ITEC ได้ในเซิร์ฟเวอร์เดียว **แต่ตามหลัง**

| | ต้นทาง `PROJECT_1` | กระจกเงา `rpt.fact_trans_fo` |
|---|--:|--:|
| แถว | 276,119,863 | 269,264,980 |
| ส่วนต่าง | — | **ขาด 6,854,883 แถว** |
| com7 ไหลเข้าล่าสุด | 2026-09-22 | **2026-08-09** |

> ต้องการข้อมูลสด → ใช้ profile `fo`
> ต้องการ join กับ dimension ITEC ง่าย ๆ และรับความช้าได้ → ใช้ `rpt.fact_trans_fo`

---

## การเชื่อมคลัง — เกือบสมบูรณ์

`INVENTLOCATIONID` = `WarehouseId` ต้องใช้ **คู่กับ `CompanyCode`** เพราะเลขคลังซ้ำข้าม BU

```sql
JOIN syndpdev001.dbo.tm_Warehouse w
  ON w.SysCompanyId = t.CompanyCode AND w.WarehouseId = t.INVENTLOCATIONID
```

ทดสอบทั้ง 276 ล้านแถว — **เชื่อมไม่ติดแค่ 60 แถว** (`bnn` คลัง `00001`)

`tm_Warehouse` มี 3,690 คลัง จาก **22 บริษัท** — มี `skh` และ `gih` ที่ไม่มีใน `Transaction_FO`
`Name` เก็บชื่อสาขาเต็ม เช่น `ID417 : Studio 7(Ustore)-CMU-Chiangmai`
com7 ถือคลังมากที่สุด 3,021 จาก 3,690

---

## ใบสั่งซื้อ (PO → inbound)

`Transaction_Type = 'Purchase order'` · `Ref.DocNum` = เลขที่ใบสั่งซื้อ → `tb_PurchOrder.PurchId`

`tb_PurchOrder` 586,218 แถว · 29 คอลัมน์ · **`SysSourceRef` เป็น `FO` ทั้งหมด ไม่ต้องกรอง**

ฟิลด์ที่ใช้บ่อย: `PurchId` · `ItemId` · `SerialId` · `VendorAccount` · `VendorName` · `PurchStatus` · `SiteId` · `WarehouseId` · `PurchPrice` · `LineAmount` · `Quantity`

🔴 **`tb_PurchOrder` ไม่มี `com7` เลยแม้แต่แถวเดียว** — มีแต่ drph, lor, dou7, bnn, drl, gi*, pss, **skh**, nov
ใบสั่งซื้อของ com7 อยู่ที่ไหน **ยังไม่รู้** — น่าจะอยู่ `D365FO_COM7` หรือ `Com7_FO` `[อนุมาน]` ยังไม่ได้ตรวจ

| BU | แถว | ใบสั่งซื้อไม่ซ้ำ | ไม่มี SerialId |
|---|--:|--:|--:|
| `drph` | 289,736 | 92,978 | **289,736 (ทั้งหมด)** |
| `lor` | 123,322 | 6,877 | 123,322 (ทั้งหมด) |
| `dou7` | 47,993 | 14,011 | 8,340 |
| `bnn` | 38,189 | 4,456 | 31,962 |
| `drl` | 30,273 | 8,501 | 11,207 |

สถานะ: `Invoiced` · `Open order` · `Received` · `Canceled`

⚠️ คุณภาพข้อมูล — `gi07` มีแถวที่ `PurchId` เก็บ **ชื่อบริษัทแทนเลขที่เอกสาร**

---

## เรื่องที่ตรวจแล้วว่า **ไม่ใช่ปัญหา**

| เคยกังวล | ผลตรวจจริง |
|---|---|
| PII ชื่อลูกค้าใน `Ref.DocNum` | **4 แถว** จาก 104.8 ล้าน · ค่าไม่ซ้ำ 1 ค่า — เป็นข้อมูลเพี้ยน ไม่ใช่รูปแบบของระบบ |
| วันที่อนาคต | **4 แถว** (`lor`, 2026-12) — ไม่กระทบภาพรวม |
| `Ref.DocNum` ว่าง | 1,024,420 แถว = `Weighted average inventory closing` ทั้งหมด + `Counting` 6 แถว · อธิบายได้ |
| `DATEFINANCIAL` เป็นปี 1900 | 1,030,091 แถว (0.37%) · ส่วนใหญ่เป็น PO ที่รับของแล้วแต่ยังไม่วางบิล |
| `FO-ITEMNO` ว่าง | **0 แถว** |
| `INVENTLOCATIONID` ว่าง | **0 แถว** |
| `DATEPHYSICAL` ว่าง | **0 แถว** |
| `RealCost` ว่าง | **0 แถว** (แต่เป็น 0 ได้ ดูกับดักข้อ 7) |

`INVENTBATCHID` ว่าง 271,245,408 แถว (**98.2%**) — ธุรกิจนี้ไม่ได้ใช้ batch ถือว่าปกติ

---

## ยังไม่รู้ / ต้องทำต่อ

- [ ] ชื่อเต็มของ BU: `drph` `lor` `drl` `pss` `nov` `skh` `gih` `gi01`–`gi12`
- [ ] ใบสั่งซื้อของ `com7` อยู่ฐานไหน (`D365FO_COM7` · `Com7_FO` ยังไม่ได้เปิดดู)
- [ ] `Transaction_ITEC` 341M และ `Transaction_ITEC_tracking` 341M — ยังไม่ได้สำรวจ
- [ ] `D365FO_DATALAKE` — ตารางใหญ่อีก 6 ตัว (`generaljournalaccountentry` 623M · `inventtransposting` 468M · `salesline` 106M · `inventdim` 80M) ยังไม่ได้แตะ
- [ ] `statusissue` / `statusreceipt` ค่า 5 และ 6 แปลว่าอะไรแน่ — เดาว่า Ordered / OnOrder ต้องให้ MIS-ERP ยืนยัน
- [ ] ส่วนต่าง 13.7 ล้านแถวระหว่าง DATALAKE กับ `Transaction_FO` — น่าจะเป็นรายการสถานะเปิด ยังไม่ได้พิสูจน์
- [ ] `CostNet` ของ `bnn ▸ NOTHING SMARTPHONE` = 46.7 พันล้านบาท จาก 145 SKU — ตัวเลขเป็นไปไม่ได้
- [ ] บริษัทใน `tm_FinDimValueSet` ที่ไม่มีใน `Transaction_FO` — `PRIME` `TFF` `ITEC` `C7H` `NOVUS` `SKH` `GIH` `ICI`
- [ ] ทำไม `Sales order` 14.7% มี `RealCost = 0`
- [ ] `drph` หยุดไหลตั้งแต่ ก.ค. 2026 — ตั้งใจหรือ pipeline พัง
- [ ] `Transaction_Type = 'Transaction'` (17.5M แถว) หมายถึงอะไร — ชื่อกว้างเกินจะเดา
- [ ] `inventdimid` มี 74 ล้านค่าไม่ซ้ำ ยาว 17 ตัวเป๊ะทุกแถว (`#00000001500166C8`) ชี้ไป `tm_InventDimension` — ยังไม่ได้แกะว่าเก็บมิติอะไร
- [ ] `Transaction_FO` มี 276.1M แถว แต่ `tb_InventTrans` ฝั่ง FO มีแค่ 205.2M — ส่วนต่าง 70.9M มาจากไหน `syndpdev001` น่าจะเป็นสำเนาไม่ครบ `[อนุมาน]`

---

## เชื่อมโยง

[[ITEC Overview]] · [[ITEC - Data Dictionary]] · [[ITEC - Query Cookbook]]
[[System Inventory]] · [[Environment Setup]] · [[Data Standardization & Quality]]
[[Open Questions & Risks]]
