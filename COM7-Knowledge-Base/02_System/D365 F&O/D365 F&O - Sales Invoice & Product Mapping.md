---
tags: [d365, sales, product, mapping, itec]
date: 2026-10-19
source: query ฐานจริง syndpdev001 / PROJECT_1 / ITEC MIS (2026-10-19) · งานยอดขายการ์ดจอปี 2026
---

# D365 F&O - Sales Invoice & Product Mapping

ดึง **ยอดขายเป็นเงิน** จาก D365 + ต่อหมวดสินค้าจาก ITEC · บทเรียนจากงานยอดขายการ์ดจอ ([[#ตัวอย่างงาน ยอดขายการ์ดจอปี 2026]])
ภาพรวมระบบ → [[D365 F&O Overview]] · ตาราง stock movement → [[D365 F&O - Transaction_FO Dictionary]]

> **ห้ามเดา** ไม่รู้เขียนว่าไม่รู้ · ข้อสันนิษฐานติด `[อนุมาน]`

## ใช้ตารางไหน

| ต้องการ | ใช้ | เหตุผล |
|---|---|---|
| **ยอดขายเป็นเงิน (ราคาขาย)** | `syndpdev001.dbo.tb_SalesInvoice` | มี `LineAmount` · `LineAmountTax` · เลขบิล · สาขา |
| จำนวน / ต้นทุน / serial | `PROJECT_1.dbo.Transaction_FO` | **ไม่มีราคาขาย** มีแค่ต้นทุน (`RealCost`) |
| หมวด / ชื่อสินค้าที่เชื่อถือได้ | ITEC `rpt.dim_item_itec` ผ่าน `tm_Item.ReferenceId` | ครบกว่า `FO_PRODUCT_MASTER_v3` (ดูด้านล่าง) |
| ชื่อสาขา | `syndpdev001.dbo.tm_Warehouse` | `WarehouseId` → `Name` |

**ความสด (ตรวจ 2026-10-19):** `tb_SalesInvoice` com7 ถึง **2026-10-17** · dou7 / lor / gi ถึง 2026-10-18 · ITEC `fact_sales_itec` **หยุด 2026-09-23** → ยอดขายล่าสุดใช้ D365

## `tb_SalesInvoice` — 1 แถว = 1 บรรทัดในใบขาย

| คอลัมน์ | ความหมาย |
|---|---|
| `SysCompanyId` | บริษัท (`com7` `dou7` `bnn` `lor` `gi*` …) · ตัวพิมพ์เล็ก |
| `InvoiceDate` · `InvoiceId` · `SalesId` | วันที่ใบขาย (date ไม่มีเวลา) · เลขใบขาย = **หน่วยบิล** · เลข SO |
| `ItemId` · `ItemName` · `ItemType` | รหัสสินค้า D365 (= `FO-ITEMNO`) · ชื่อ · Item / Service |
| `Quantity` | จำนวน · ติดลบ = คืน (การ์ดจอปี 2026 ไม่พบ) |
| **`LineAmount`** | **ยอดบรรทัด ไม่รวม VAT หลังหักส่วนลด** |
| **`LineAmountTax`** | VAT ของบรรทัด · ตรวจแล้ว (Line+Tax)/Line = **1.07** |
| `SalesPrice` | ราคาต่อชิ้น · **บางบริษัทเป็น 0** (dou7) → ใช้ `(LineAmount + LineAmountTax) / Quantity` แทน |
| `DiscountAmount` · `DiscountPercent` | ส่วนลด |
| `CustomerAccount` · `CustomerName` · `DeliveryName` | ⚠️ อาจเป็นข้อมูลลูกค้า — **ไม่ดึงถ้าไม่จำเป็น** (dou7 เป็น "Dummy Store") |
| `SiteId` · `WarehouseId` | site · คลัง/สาขา → `tm_Warehouse` |
| `LineNo` | ⚠️ ชนคำสงวน SQL → เขียน `[LineNo]` |

```sql
-- ยอดขายรวม VAT ต่อบรรทัด
SELECT InvoiceDate, InvoiceId, ItemId, Quantity,
       LineAmount,                                   -- ไม่รวม VAT
       LineAmount + LineAmountTax AS AmountInclVAT,
       (LineAmount + LineAmountTax) / NULLIF(Quantity, 0) AS UnitPriceInclVAT,
       WarehouseId
FROM syndpdev001.dbo.tb_SalesInvoice WITH (NOLOCK)
WHERE SysCompanyId = 'com7' AND InvoiceDate >= '2026-01-01'
```

ยอดเงินฝั่ง ITEC (`fact_sales_itec.SalesAmount`) เป็น **ไม่รวม VAT** · ตรงกับ `LineAmount` ระดับสตางค์ (ดูผลเทียบด้านล่าง)

## เชื่อมสินค้า D365 → ITEC

```
tb_SalesInvoice.ItemId = tm_Item.ItemId (+ SysCompanyId)  →  tm_Item.ReferenceId = rpt.dim_item_itec.ItemId
```

- `tm_Item.ReferenceId` = รหัส ITEC (บาร์โค้ด หรือรหัสเซ็ต เช่น `COMSETDIY2025-187`) · `[Search Name]` ค่าเดียวกัน
- จับคู่ได้ (ตามรหัสใน tm_Item): **com7 97.3%** · bnn 75.8% · dou7 56% · บริษัทอื่นแทบไม่ได้
- ใบขาย com7 กลุ่มการ์ดจอ/เซ็ตปี 2026 หาหมวดเจอ **100%**
- `tm_Item` มีรหัสซ้ำต่อบริษัท → `drop_duplicates(ItemId)` ก่อน join · คนละเซิร์ฟเวอร์กับ ITEC → ดึงสองฝั่งมา join ใน Python
- ตารางชั่วคราวบนเซิร์ฟเวอร์ D365 collation ต่างจากตารางจริง (`Thai_100_CI_AS_SC_UTF8` vs `Thai_CI_AS`) → `JOIN ... ON a.ItemId = b.ItemId COLLATE DATABASE_DEFAULT`

## 🔴 `FO_PRODUCT_MASTER_v3` ไม่ครบ — อย่าใช้กรองหมวดอย่างเดียว

`PROJECT_1.dbo.FO_PRODUCT_MASTER_v3` (ITEMNUMBER · FO-CategoryID/Name · FO-SubCategory · GroupCate_1–8)

| ปัญหา (ตรวจกับการ์ดจอขายปี 2026) | ผล |
|---|---|
| หมวด Graphic Card มี **2 รหัส**: `1807` และ `262` (หมวดเก่า) | กรอง `= '1807'` ตก 14 รหัส · 498 ชิ้น |
| **การ์ดจอรุ่นใหม่ไม่อยู่ใน master เลย** (RTX 5060 / 5050 / 5060 Ti หลายรุ่น · RTX 5080 / 5090 บางรุ่น) | ตก 59 รหัส · 513 ชิ้น |
| หมวด 1807 มีแค่ **820 รหัส** · ITEC Graphic Card ~1,650 รหัส | master ไม่ได้อัปเดตตามสินค้าใหม่ `[อนุมาน]` |

ผลจริง: คิวรี `Transaction_FO` + master หมวด 1807 ได้ **1,844 ชิ้น** · ผ่าน ITEC ได้ **2,855 ชิ้น** · 182 รหัสที่มีทั้งคู่ **ตรงกันทุกรหัส** → ต่างกันเพราะรายการรหัสล้วน ๆ
⚠️ `LEFT JOIN master` แล้วกรอง `p.[FO-CategoryID]` ใน `WHERE` = INNER JOIN → สินค้าที่ไม่อยู่ใน master หายเงียบ
ถ้าจำเป็นต้องใช้ master: กรอง `[FO-CategoryName] = 'Graphic Card'` แทนรหัส (ยังขาด 513 ชิ้นที่ไม่มีใน master)

## Computer Set — มี 3 รูปแบบในใบขาย

หา set ด้วย ITEC `SubCategoryName = 'COMPUTER SET'` (อยู่ใต้หมวด **Computer Cases**) หรือชื่อมี `Computer Set` / `Comset` / `PC Set` — **ชื่ออย่างเดียวไม่พอ** (221 บรรทัดปี 2026 ชื่อไม่มีคำว่า Computer Set เช่น `Comsetmall PC Set …` · `COMSETDIY2026-054 (NO CPU)`) · ตัดรายการ `ส่วนลด Com Set` / `ค่าประกอบคอมพิวเตอร์`

| รูปแบบ | ลักษณะในบิล | ตัวอย่าง | การ์ดจอ |
|---|---|---|---|
| **แยกบรรทัด** | หัวเซ็ตราคา 0 (`tm_Item.ItemGroupId = '200'` หรือรหัสลงท้าย `.1`) + ชิ้นส่วนเป็นบรรทัดราคาเต็ม | `E-QUIP 26021 (R5 5500GT \| RAM16GB/3200 \| SSD 500GB)` | เห็นเป็นบรรทัด · ราคาในเซ็ตถูกปันส่วน |
| **บรรทัดเดียว** | 1 บรรทัดราคารวมทั้งเซ็ต (`ItemGroupId = '100'`) | `INTEL ตัวตึง #2` · `SVOA Comset …` · `Comsetmall PC Set …` | ไม่เห็น · ต้องอ่านจากชื่อ (ถ้ามี) |
| **ไม่มีรหัสเซ็ตในบิล** | หน้าร้านคีย์ชิ้นส่วนทีละชิ้น | บิลที่ CPU + RAM + การ์ดจอตรงสเปก `E-QUIP 25102 (U9 285K \| RAM64GB/5600 \| SSD 2TB \| RTX5090)` | เป็นบรรทัดราคาเต็ม |

- **รหัสเซ็ต E-QUIP แทบไม่ถูกใช้ในใบขาย** — เซ็ต RTX 5090 ทั้ง 31 รหัส ขายในใบขายแค่ 1 ครั้งตลอดกาล (2025 · 0.01 บาท) ทั้ง D365 และ ITEC · ไม่มีความเคลื่อนไหวใน `Transaction_FO` → เป็นรหัสโปรโมชัน ไม่ใช่สินค้าจริงในคลัง `[อนุมาน]`
- **เซ็ตบรรทัดเดียวซื้อเข้าเป็นเครื่องสำเร็จ** (Purchase order ของตัวเซ็ต · ไม่มีการตัดสต็อกชิ้นส่วน) → **ไม่มีข้อมูลส่วนประกอบในระบบ** ต้องขอสเปก (BOM) จากทีมสินค้า
- สเปกในชื่อเซ็ต (ส่วนในวงเล็บคั่น `|`) ใช้จับคู่บิลที่ไม่มีรหัสเซ็ตได้ — ITEC มีชื่อเซ็ตแบบนี้ 1,119 รหัส

## ตัวอย่างงาน: ยอดขายการ์ดจอปี 2026

ไฟล์ส่ง: `Downloads/GPU_Sales_2026_Summary.xlsx` (4 แท็บ: วิธีคิด · ทั้งหมดตามช่วงราคา · data > 50,000 · data ทุกราคา) · รายละเอียดระดับบิล `GPU_over50k_Sales_2026.xlsx`

| | ชิ้น | มูลค่ารวม VAT |
|---|--:|--:|
| การ์ดจอทั้งหมด com7 (1 ม.ค. – 17 ต.ค. 2026) | 2,945 | 58.47 ล้าน |
| ราคาต่อชิ้น > 50,000 | 141 (4.8%) | 14.18 ล้าน (24.2%) |
| — 1) ซื้อเดี่ยว | 106 | 11.11 ล้าน |
| — 2) + ฮาร์ดแวร์อื่น | 21 | 1.94 ล้าน |
| — 3) Computer Set (รวมบิลที่ตรงสเปกเซ็ต `[อนุมาน]`) | 14 | 1.13 ล้าน |
| การ์ดจอขายเดี่ยว ทุกราคา | 1,686 | 38.81 ล้าน |

- **นิยามการ์ดจอ:** ITEC `CategoryName = 'Graphic Card'` + ชื่อเป็นการ์ดจอจริง (VGA / GeForce / Radeon / RTX / GTX / RX / ARC / Quadro) · ตัด SubCategory TV TUNER / SOUNDCARD / CAPTURE CARD / DEMO · ตรวจแล้วไม่มีการ์ดจอผิดหมวดในบิลปี 2026
- **แบ่งกรณีระดับบิล** (`InvoiceId`): มีชิ้นส่วนคอม (CPU · Mainboard · RAM · SSD/HDD · PSU · Case · Cooling) = กรณี 2 · จอ/เมาส์/คีย์บอร์ดไม่นับเป็นฮาร์ดแวร์
- **ราคาการ์ดจอในเซ็ต:** ใช้มัธยฐานราคาขายเดี่ยวของรุ่นเดียวกันปี 2026
- **เทียบ ITEC ม.ค.–ส.ค.:** การ์ดจอ > 50,000 (เกณฑ์ไม่รวม VAT แบบ ITEC) จำนวนและยอดตรงทุกเดือน
- **ข้อสังเกต:** ราคา ASUS ROG Astral RTX 5090 ขึ้นจาก 145,000 (พ.ค.–มิ.ย.) เป็น 219,000–239,000 (ต.ค.) · ต.ค. การ์ดจอ > 50,000 = 69% ของยอดการ์ดจอทั้งเดือน
- **ค้าง:** เซ็ตบรรทัดเดียวที่ชื่อไม่บอกรุ่นการ์ดจอและราคา > 50,000 — 13 รายการ 411 เครื่อง (SVOA Comset 360) รอสเปก
- **ชื่อสาขาใน `tm_Warehouse` บางสาขายังมี "(ยังไม่เปิด)"** แต่มียอดขาย (เช่น E-Quip-Central-Mahachai) → ชื่อในทะเบียนคลังไม่อัปเดต

## เชื่อมโยง

[[D365 F&O Overview]] · [[D365 F&O - Transaction_FO Dictionary]] · [[D365 F&O - Query Cookbook]] · [[ITEC - Data Dictionary]] · [[ITEC Product Dimension]] · [[Open Questions & Risks]]
