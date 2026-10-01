# D365 F&O - Query Cookbook

SQL ที่รันได้จริง พร้อมเหตุผลว่าทำไมต้องเขียนแบบนั้น
ภาพรวม → [[D365 F&O Overview]] · พจนานุกรมคอลัมน์ → [[D365 F&O - Transaction_FO Dictionary]]

ทุกคิวรีในหน้านี้ **รันจริงแล้ว** เมื่อ 2026-09-23 พร้อมเวลาที่วัดได้
แบบเดียวกับ [[ITEC - Query Cookbook]] ฝั่ง ITEC

> ใส่ `WITH (NOLOCK)` เสมอ — เป็นฐาน production ของทีมอื่น

---

## แผนที่การเชื่อมตาราง

ที่มา: เอกสารอ้างอิงจาก MIS-ERP (2026-09-23) · **ตรวจสอบกับฐานจริงแล้วทุกเส้น**

```
                    PROJECT_1.dbo.Transaction_FO
                              │
        ┌─────────────────────┼──────────────────────┐
        │                     │                      │
  [FO-ITEMNO]           [Ref.DocNum]          [INVENTLOCATIONID]
   + CompanyCode                               + CompanyCode
        │                     │                      │
        ▼                     ▼                      ▼
   tm_Item.ItemId      purchtable.purchid     tm_Warehouse.WarehouseId
   + SysCompanyId       + dataareaid            + SysCompanyId
        │                     │
  [DefaultDimension]    [orderaccount]
        │                     │
        ▼                     ▼
 tm_FinDimValueSet      vendtable.accountnum
   .FinancialDim              │
        │                [party]
        ▼                     ▼
  GroupCategory        dirpartytable.recid
  ▸ Category                  │
  ▸ SubCategory               ▼
                        dirpartytable.name   ← ชื่อผู้ขาย
```

⚠️ **ผู้ขายใช้ `purchtable` ไม่ใช่ `tb_PurchOrder`** — `tb_PurchOrder` ไม่มี com7 · ดูสูตรที่ 4

| # | ตาราง | ฐาน | แถว | ใช้ทำอะไร |
|--:|---|---|--:|---|
| 1 | `Transaction_FO` | PROJECT_1 | 276,119,863 | ตารางหลัก · ความเคลื่อนไหวสต็อกทั้งหมด |
| 2 | `tm_Item` | syndpdev001 | 394,158 | รายละเอียดสินค้า · สะพานไปหมวด |
| 3 | `tm_FinDimValueSet` | syndpdev001 | 719,054 | Group / Category / SubCategory |
| 4 | `tm_Warehouse` | syndpdev001 | 3,690 | ชื่อคลัง · คลังพักระหว่างทาง |
| 5 | `tb_PurchOrder` | syndpdev001 | 586,218 | ใบสั่งซื้อ · ⚠️ **ไม่มี com7** |
| 6 | `purchtable` | D365FO_DATALAKE | 2,603,821 | **หัวใบสั่งซื้อ · ครบทุก BU** |
| 7 | `vendtable` | D365FO_DATALAKE | 22,620 | ทะเบียนผู้ขาย · ⚠️ ไม่มีคอลัมน์ชื่อ |
| 8 | `dirpartytable` | D365FO_DATALAKE | 114,573 | **ชื่อผู้ขาย** (`name`) |
| 9 | `inventtrans` | D365FO_DATALAKE | 289,817,143 | ต้นทางดิบ 105 คอลัมน์ · ดูหัวข้อท้ายไฟล์ |

### ⚠️ ข้อควรระวังของแต่ละเส้น

| เส้น | เอกสารเขียนว่า | ของจริง |
|---|---|---|
| `[FO-ITEMNO]` → `tm_Item.ItemId` | join ด้วย ItemId | ❌ **ต้องเติม `CompanyCode = SysCompanyId`** ไม่งั้นหมวดข้ามบริษัท |
| `tm_Item.DefaultDimension` → `FinancialDim` | เชื่อเอาได้เลย | ✅ `FinancialDim` ไม่ซ้ำทั้งตาราง 719,054 ค่า |
| `[Ref.DocNum]` → `tb_PurchOrder.PurchId` | ใช้ได้ | ❌ **ไม่มี com7 (0% จาก 4.5M แถว)** และแถวบาน +59% ที่ dou7 · ใช้ `purchtable` แทน |
| `[INVENTLOCATIONID]` → `tm_Warehouse` | join ตรง | ❌ **ต้องเติม `CompanyCode = SysCompanyId`** เลขคลังซ้ำข้าม BU |

---

# สูตรที่ 1 — หมวดสินค้าแยกตาม BU · ช่วงเวลา · คลัง

**ใช้บ่อยที่สุด** · รันจริง 900 กลุ่ม · 22 วินาที · ยอดตรงกับแถวจริงเป๊ะ

```sql
DECLARE @from date = '2025-01-01';
DECLARE @to   date = '2026-08-31';

WITH item AS (          -- ① 1 สินค้า 1 บริษัท ต้องได้ 1 แถวเท่านั้น
    SELECT ItemId, SysCompanyId, DefaultDimension,
           ROW_NUMBER() OVER (PARTITION BY ItemId, SysCompanyId
                              ORDER BY RecId DESC) AS rn
    FROM   syndpdev001.dbo.tm_Item WITH (NOLOCK)
    WHERE  SysSourceRef = 'FO'
      AND  ItemId IS NOT NULL
)
SELECT
      a.CompanyCode                                   AS BU
    , ISNULL(cc.GroupCategoryName, '(ไม่มีหมวด)')      AS GroupCategoryName
    , ISNULL(cc.CategoryName,      '(ไม่มีหมวด)')      AS CategoryName
    , ISNULL(cc.SubCategoryName,   '(ไม่มีหมวด)')      AS SubCategoryName
    , COUNT_BIG(*)                                    AS Amount
    , COUNT(DISTINCT a.[FO-ITEMNO])                   AS SKU
    , SUM(CASE WHEN a.QTY < 0 THEN -a.QTY ELSE 0 END) AS QtyOut
    , SUM(CASE WHEN a.QTY > 0 THEN  a.QTY ELSE 0 END) AS QtyIn
    , CAST(SUM(a.RealCost) AS decimal(28,2))          AS CostNet
FROM        PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)

LEFT JOIN   item bb
       ON   bb.ItemId       = a.[FO-ITEMNO]
      AND   bb.SysCompanyId = a.CompanyCode      -- ② กันหมวดข้ามบริษัท
      AND   bb.rn           = 1

LEFT JOIN   syndpdev001.dbo.tm_FinDimValueSet cc WITH (NOLOCK)
       ON   cc.FinancialDim = bb.DefaultDimension
      AND   cc.SysSourceRef = 'FO'               -- ③ ไม่ต้องกรอง CompanyName

WHERE       a.CompanyCode      IN ('com7','dou7','bnn')
  AND       a.INVENTLOCATIONID IN ('4','77','72006','72008','79006')
  AND       a.DATEPHYSICAL     >= @from
  AND       a.DATEPHYSICAL      < DATEADD(day, 1, @to)   -- ⑤
  AND       a.REFERENCECATEGORY <> 7             -- ④ ตัดรายการปิดบัญชีถัวเฉลี่ย

GROUP BY    a.CompanyCode, cc.GroupCategoryName, cc.CategoryName, cc.SubCategoryName
ORDER BY    a.CompanyCode, Amount DESC;
```

## ทำไมต้องเขียนแบบนี้ — 5 จุด

| # | เขียนแบบนี้ | เพราะ |
|--:|---|---|
| ① | `ROW_NUMBER()` ไม่ใช่ `SELECT DISTINCT` | `(ItemId, SysCompanyId)` **ยังซ้ำอยู่ 6 คีย์** (3 คีย์มี 2 แถว · 3 คีย์มี 3 แถว) `DISTINCT` เอาไม่อยู่ถ้า `DefaultDimension` ต่างกัน |
| ② | เติม `SysCompanyId = CompanyCode` | สินค้าตัวเดียวที่ขายหลายบริษัทมี `DefaultDimension` คนละค่า — ดูหัวข้อถัดไป |
| ③ | **ไม่กรอง** `cc.CompanyName` | `FinancialDim` ไม่ซ้ำทั้งตาราง กรองไปก็ไม่ช่วย แถมทำให้ dim ที่ชี้ไป `GI` / `TFF` หล่นหาย |
| ④ | `REFERENCECATEGORY <> 7` | `Weighted average inventory closing` ไม่ใช่การเคลื่อนไหวจริง · dou7 มี 358 แถวปนในตัวกรองนี้ |
| ⑤ | `>= @from AND < @to + 1` | `DATEPHYSICAL` ตอนนี้ไม่มีส่วนเวลา `BETWEEN` จึงยังปลอดภัย แต่ถ้าวันหนึ่งมีเวลาเข้ามา `BETWEEN` จะตัดวันสุดท้ายหาย |

> **บันทึกความซื่อสัตย์** — รันเทียบกับฉบับก่อนแก้แล้ว ได้ `Amount` **เท่ากันเป๊ะ 26,432,885**
> เพราะ 574 รหัสที่ซ้ำไม่มีรายการในคลัง 5 แห่งนั้นเลย
> แต่ถ้า**เอาตัวกรองคลังออก** ฉบับเก่าจะเฟ้อจริง: 94,120,175 → 94,153,608 (**+33,433 แถว · +0.036%**)

---

# ทำไม 1 สินค้าถึงมี DefaultDimension หลายค่า

**ไม่ใช่ข้อมูลสกปรก แต่เป็นการออกแบบ** — `DefaultDimension` ผูกกับบริษัทอยู่ในตัวมันเอง

| `SysCompanyId` ใน `tm_Item` | `CompanyName` ที่ dim ชี้ไป | dim ไม่ซ้ำ |
|---|---|--:|
| `com7` | COM7 | 1,949 |
| `bnn` | **Adept** | 279 |
| `dou7` | DOU7 | 230 |

ทุกเคสเป็นแบบนี้หมด ไม่มีข้อยกเว้น — **อยู่ 2 บริษัท = 2 dim** (573 รหัส) · **อยู่ 3 บริษัท = 3 dim** (1 รหัส)

```
ItemId 0000153922   NR@ Premium Xiaomi Smart Air Purifier 4 Compact
  com7   dim 5642244594   ขึ้นทะเบียน 2025-12-16
  bnn    dim 5642826605   ขึ้นทะเบียน 2026-04-06   ← ขายทีหลัง จึงลงทะเบียนทีหลัง
```

ผลกระทบเมื่อ join ผิด

| ผลลัพธ์ | รหัส |
|---|--:|
| 2 dim แต่ชี้หมวดเดียวกัน → แค่แถวซ้ำ `Amount` คูณ 2 | 560 |
| 2 dim แล้วได้**คนละหมวด** → หมวดผิดจริง | 14 |

---

# 🔴 คุณภาพของ taxonomy ฝั่ง F&O

ขนาด: **26 บริษัท · 126 GroupCategory · 487 Category · 3,122 SubCategory** (719,054 dim)

| บริษัท | dim | กลุ่มหมวด | หมวด | หมวดย่อย |
|---|--:|--:|--:|--:|
| COM7 | 657,363 | 103 | 366 | 2,525 |
| *(CompanyName ว่าง)* | 16,492 | 122 | 473 | 3,074 |
| DOU7 | 9,452 | 27 | 88 | 271 |
| DRPH | 7,867 | 29 | 77 | 225 |
| PRIME | 4,630 | 20 | 28 | 29 |
| TFF | 4,286 | 28 | 59 | 240 |
| GI | 3,343 | 34 | 88 | 155 |
| Adept | 2,039 | 46 | 86 | 279 |
| LOR | 1,792 | 14 | 28 | 60 |
| GI01–GI12 | 10,937 | ~25 | ~73 | ~135 |
| NOVUS · SKH · ITEC · C7H · GIH · ICI | 417 | ≤14 | ≤24 | ≤26 |

มีบริษัทที่ไม่เคยเห็นใน `Transaction_FO` — `PRIME` `TFF` `ITEC` `C7H` `NOVUS` `SKH` `GIH` `ICI`

## ① ไม่ใช่ลำดับชั้นจริง — `CategoryName` ลอยข้ามกลุ่ม

| `CategoryName` อยู่ใต้กี่ `GroupCategoryName` | จำนวนหมวด |
|--:|--:|
| 1 (สะอาด) | 173 |
| 2 | 112 |
| 3 | 60 |
| 4 | 39 |
| 5–10 | 69 |
| 11–39 | 18 |
| **67** | **1** |

**345 จาก 487 หมวด (71%) ชี้ไปมากกว่า 1 กลุ่ม**

| หมวด | อยู่ใต้กี่กลุ่ม | dim |
|---|--:|--:|
| `Common` | **67** | 11,056 |
| `iPhone` | 39 | 28,165 |
| `Service` | 35 | 3,961 |
| `Apple Watch` | 32 | 14,978 |
| `Apple Case & Protection` | 29 | 9,711 |
| `Smartphone` | 26 | 25,477 |
| `AION` | 23 | 2,343 |
| `IT Accessories` | 18 | 13,271 |
| `Adapter` | 16 | 14,137 |

> **ห้าม `GROUP BY CategoryName` เดี่ยว ๆ** ต้องจับคู่กับ `GroupCategoryName` เสมอ
> แม้จับคู่แล้วก็ยังต้องระวัง ดูข้อ ③

## ② ค่าว่าง

| ชั้น | dim ที่ว่าง | % |
|---|--:|--:|
| GroupCategoryName | 41,399 | 5.76 |
| CategoryName | 36,499 | 5.08 |
| SubCategoryName | 33,832 | 4.70 |

ใช้ `ISNULL(..., '(ไม่มีหมวด)')` เสมอ ไม่งั้นกลุ่มพวกนี้หายจากรายงานเงียบ ๆ

## ③ ข้อมูลเพี้ยนที่เจอจากผลจริง

**หมวดขัดกันเองในแถวเดียว**
```
bnn | Smartphone | TABLET | TABLET TCL      ← กลุ่มบอกมือถือ หมวดบอกแท็บเล็ต
```

**ชื่อหมวดมีอักขระขยะ**
```
ฺฺBBP                      ← com7 · 164,641 แถว · ขึ้นต้นด้วยพินทุไทยซ้ำ 2 ตัว
TABLET INFINIX.           ← มีจุดต่อท้าย
XIAOMI ACCESSORIESESSORIES ← ต่อท้ายซ้ำ แยกเป็นคนละหมวดกับ XIAOMI ACCESSORIES
```

**com7 ยัดของ demo ทุกชนิดลงกลุ่ม `iPhone`**

| ItemId | สินค้า | com7 จัดเป็น | bnn จัดเป็น |
|---|---|---|---|
| `0000159549` | Mijia Air Conditioner 18000 BTU | **iPhone** ▸ BTB Demo | Appliance ▸ Demo Xiaomi Eco |
| `0000159615` | Xiaomi Redmi Buds 8 Pro | **iPhone** ▸ BTB Demo | Accessories ▸ Demo Xiaomi Eco |
| `0000162044` | Redmi Watch 6 | **iPhone** ▸ BTB Demo | Smartwatch ▸ Demo Xiaomi Eco |

ทั้ง 14 รหัสเป็นรูปแบบเดียวกัน — **รายงานยอดกลุ่ม `iPhone` ของ com7 จะเฟ้อด้วยของที่ไม่ใช่ iPhone**

**ต้นทุนผิดปกติชัดเจน**
```
bnn | NOTHING SMARTPHONE    31,427 แถว · 145 SKU · CostNet 46,685,110,000 บาท
bnn | PREMIUM TABLET ALLDOCUBE   3,147 แถว  แต่  QtyOut 77,845
```

**ชื่อสินค้าขัดกันในรหัสเดียว**
```
0000162056   com7 -> Xiaomi Watch S5 46mm Silver
             bnn  -> Xiaomi Watch S5 46mm Black
```

**มี ItemId ชื่อ `ห้ามใช้`** — `ItemName` = "Fixed asset" โผล่ทั้ง bnn และ dou7

> ปัญหาชุดนี้เหมือนฝั่ง ITEC ตอนทำ [[ITEC Product Dimension]] — **หมวดที่คนคีย์เอง เชื่อดิบ ๆ ไม่ได้**
> ถ้าจะใช้ทำรายงานผู้บริหาร ควรมีชั้น mapping ของทีมข้อมูลคั่น

---

# สูตรที่ 2 — ต่อชื่อคลัง

```sql
SELECT      a.CompanyCode AS BU, a.INVENTLOCATIONID AS คลัง,
            w.Name AS ชื่อคลัง, w.SiteId, COUNT_BIG(*) AS n
FROM        PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)
LEFT JOIN   syndpdev001.dbo.tm_Warehouse w WITH (NOLOCK)
       ON   w.SysCompanyId = a.CompanyCode          -- ⚠️ ขาดไม่ได้
      AND   w.WarehouseId  = a.INVENTLOCATIONID
WHERE       a.DATEPHYSICAL >= '2026-01-01'
GROUP BY    a.CompanyCode, a.INVENTLOCATIONID, w.Name, w.SiteId
ORDER BY    n DESC;
```

เชื่อมติด 276 ล้านแถว พลาดแค่ **60 แถว** (`bnn` คลัง `00001`) · **28 วินาที**

`tm_Warehouse.InTransiteWarehouse` บอกคลังพักระหว่างทางของแต่ละ BU — com7/bnn/drl `99999` · dou7 `79998` · drph `69998` · lor `61998` · gi `62901`

---

# สูตรที่ 3 — ซื้อเข้าจากผู้ขาย (PO)

```sql
SELECT      a.CompanyCode AS BU, p.VendorAccount, p.VendorName,
            COUNT_BIG(*) AS แถว, COUNT(DISTINCT a.[Ref.DocNum]) AS ใบสั่งซื้อ,
            SUM(a.QTY) AS รับเข้า, CAST(SUM(a.RealCost) AS decimal(28,2)) AS ต้นทุน
FROM        PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)
LEFT JOIN   syndpdev001.dbo.tb_PurchOrder p WITH (NOLOCK)
       ON   p.PurchId      = a.[Ref.DocNum]
      AND   p.SysCompanyId = a.CompanyCode          -- ⚠️ ขาดไม่ได้
      AND   p.ItemId       = a.[FO-ITEMNO]          -- ⚠️ 1 PO มีหลายบรรทัด
WHERE       a.REFERENCECATEGORY = 3                 -- Purchase order
  AND       a.DATEPHYSICAL >= '2026-01-01'
GROUP BY    a.CompanyCode, p.VendorAccount, p.VendorName
ORDER BY    แถว DESC;
```

## 🔴 ข้อจำกัดใหญ่ — `tb_PurchOrder` ไม่มี com7

| BU | แถว | ใบสั่งซื้อไม่ซ้ำ | ไม่มี SerialId |
|---|--:|--:|--:|
| `drph` | 289,736 | 92,978 | **ทั้งหมด** |
| `lor` | 123,322 | 6,877 | **ทั้งหมด** |
| `dou7` | 47,993 | 14,011 | 8,340 |
| `bnn` | 38,189 | 4,456 | 31,962 |
| `drl` | 30,273 | 8,501 | 11,207 |
| **`com7`** | **0** | **0** | — |

ใบสั่งซื้อของ com7 อยู่ฐานไหน **ยังไม่รู้** — สงสัย `D365FO_COM7` หรือ `Com7_FO` `[อนุมาน]` ยังไม่ได้ตรวจ

⚠️ `SysSourceRef` ของ `tb_PurchOrder` เป็น `FO` ทั้ง 586,218 แถว **ไม่ต้องกรอง**
⚠️ `gi07` มีแถวที่ `PurchId` เก็บ **ชื่อบริษัทแทนเลขที่เอกสาร**

---

# สูตรที่ 4 — ผู้ขาย (vendor)

**ต่อ 3 ทอด** · รันจริง 572 ผู้ขาย · 18 วินาที · แถวรวมตรงกับแถวจริงเป๊ะ · ไม่มีแถวไหนหาชื่อไม่เจอ

```
Transaction_FO          purchtable           vendtable          dirpartytable
──────────────          ──────────           ─────────          ─────────────
[Ref.DocNum]    ──►     purchid
CompanyCode     ──►     dataareaid
                        orderaccount  ──►    accountnum
                        dataareaid    ──►    dataareaid
                                             party      ──►     recid
                                                                name  ← ชื่อผู้ขาย
```

```sql
SELECT
      a.CompanyCode                          AS BU
    , h.orderaccount                         AS VendorCode
    , d.name                                 AS VendorName
    , COUNT_BIG(*)                           AS แถว
    , COUNT(DISTINCT a.[Ref.DocNum])         AS ใบสั่งซื้อ
    , COUNT(DISTINCT a.[FO-ITEMNO])          AS SKU
    , SUM(a.QTY)                             AS รับเข้าสุทธิ
    , CAST(SUM(a.RealCost) AS decimal(28,2)) AS ต้นทุน
FROM        PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)

LEFT JOIN   D365FO_DATALAKE.dbo.purchtable h WITH (NOLOCK)      -- ทอด 1
       ON   h.purchid    = a.[Ref.DocNum]
      AND   h.dataareaid = a.CompanyCode

LEFT JOIN   D365FO_DATALAKE.dbo.vendtable v WITH (NOLOCK)       -- ทอด 2
       ON   v.accountnum = h.orderaccount
      AND   v.dataareaid = h.dataareaid

LEFT JOIN   D365FO_DATALAKE.dbo.dirpartytable d WITH (NOLOCK)   -- ทอด 3
       ON   d.recid = v.party

WHERE       a.REFERENCECATEGORY = 3                -- Purchase order เท่านั้น
  AND       a.DATEPHYSICAL >= '2026-01-01'

GROUP BY    a.CompanyCode, h.orderaccount, d.name
ORDER BY    แถว DESC;
```

ผลลัพธ์จริง (PO ปี 2026)

| BU | รหัส | ผู้ขาย | แถว | ต้นทุน |
|---|---|---|--:|--:|
| com7 | `V000076` | บริษัท แอปเปิ้ล เซาท์ เอเชีย (ประเทศไทย) จำกัด | 1,654,884 | 36,031,630,000 |
| dou7 | `V000458` | บริษัท ทรู มูฟ เอช ยูนิเวอร์แซล คอมมิวนิเคชั่น จำกัด | 471,240 | 2,668,826,000 |
| com7 | `V000085` | บริษัท ไทยซัมซุง อิเลคโทรนิคส์ จำกัด | 334,847 | 4,567,156,000 |
| com7 | `V005296` | XIAOMI TECHNOLOGY (THAILAND) LIMITED | 232,123 | 1,762,461,000 |

## 🔴 กับดัก 4 ข้อ

### ① `vendtable` **ไม่มีคอลัมน์ `name`**

มี 225 คอลัมน์ แต่ไม่มีชื่อผู้ขาย — D365 เก็บชื่อไว้ที่ `dirpartytable` (114,573 แถว) เชื่อมด้วย `vendtable.party = dirpartytable.recid`

เขียน `v.name` จะได้ `Msg 207 · Invalid column name 'name'`

### ② อย่าใช้ `bpc_nameeng`

ดูเหมือนชื่อภาษาอังกฤษ แต่ว่างเกือบหมด

| BU | ผู้ขาย | ไม่มีชื่ออังกฤษ |
|---|--:|--:|
| com7 | 7,970 | 7,825 (98.2%) |
| bnn | 5,922 | 5,906 (99.7%) |

`dirpartytable.name` ครบ **100% ทุก BU** ใช้ตัวนี้อย่างเดียว

### ③ 🔴 `tb_PurchOrder` ไม่มี com7 และทำให้แถวบานปลาย

เอกสาร MIS-ERP ชี้ให้ใช้ `tb_PurchOrder` — ใช้ได้กับทุก BU **ยกเว้นตัวที่ใหญ่ที่สุด**

ทดสอบ join จริงกับ PO ปี 2026

| BU | แถว | เชื่อมติด |
|---|--:|--:|
| **com7** | **4,517,192** | **0.0%** |
| dou7 · bnn · อีก 18 BU | — | 100% |

และเพราะ 1 ใบสั่งซื้อมีสินค้าตัวเดียวกันได้หลายบรรทัด แถวจึงบาน

```
dou7   แถวจริง 471,249  →  หลัง join tb_PurchOrder 748,969   (+59%)
bnn    แถวจริง 641,145  →  หลัง join tb_PurchOrder 642,067
```

`purchtable` ไม่มีปัญหานี้ — `(purchid, dataareaid)` **ไม่ซ้ำเลย ทั้ง 2,603,821 คีย์**

### ④ ไม่ต้องใส่ `UPPER()`

`dataareaid` สะกดทั้ง `com7` และ `COM7` ปนกันจริง แต่ **collation ของฐานนี้ไม่สนตัวพิมพ์**
พิสูจน์แล้ว — `WHERE v.dataareaid = 'com7'` คืนแถวที่แสดงเป็น `COM7` มาด้วย

ใส่ `UPPER()` จะ**ช้าลง** เพราะใช้ดัชนีไม่ได้ — เขียน `=` ตรง ๆ พอ

## จะใช้ตัวไหนดี

| กรณี | ใช้ |
|---|---|
| **ต้องการทุก BU รวม com7** | ✅ `purchtable` + `vendtable` + `dirpartytable` |
| ไม่สน com7 · อยากได้ `PurchStatus` `SerialId` | `tb_PurchOrder` — แต่ต้องยุบซ้ำก่อน join |
| อยากได้ราคาต่อหน่วยรายบรรทัด | `purchline` — ซ้ำหนัก สูงสุด **550 แถวต่อคีย์** `(purchid, dataareaid, itemid)` |

## ตารางจัดซื้อใน DATALAKE

| ตาราง | แถว | ครอบ com7 |
|---|--:|---|
| `bpc_purchaseorderreceipt_interface` | 33,863,991 | ยังไม่ได้ตรวจ |
| `vendpackingsliptrans` | 12,430,962 | ยังไม่ได้ตรวจ |
| `vendinvoicetrans` | 8,473,653 | ยังไม่ได้ตรวจ |
| **`purchline`** | 7,052,159 | ✅ 6,434,319 แถว |
| **`purchtable`** | 2,603,821 | ✅ 2,454,314 ใบ · 1,966 ผู้ขาย |
| **`vendtable`** | 22,620 | ✅ 7,970 ผู้ขาย |
| `dirpartytable` | 114,573 | ✅ ชื่อครบ 100% |

⚠️ `Com7_FO` และ `D365FO_COM7` **เปิดไม่ได้** — `tan-mis` ไม่มีสิทธิ์

---

# ทะเบียนคอลัมน์ที่ใช้จริง

รวมคอลัมน์ทุกตัวที่ SQL ชุด Supply Chain ใช้ · ตรวจกับฐานจริง 2026-09-24
ไฟล์ SQL อยู่ที่ `scripts/fo/sql/` — ทั้ง 4 ไฟล์รันผ่านแล้ว

| ไฟล์ | ได้อะไร | แถว | เวลา |
|---|---|--:|--:|
| `Vendor_Supply_chain.sql` | ผู้ขาย รายเดือน แยกคลัง | 2,337 | 25 วิ |
| `Vendor_Supply_chain2.sql` | ผู้ขาย สรุปรวมทั้งช่วง | 177 | 17 วิ |
| `ProductCat_Supply_chain.sql` | หมวดสินค้า แยกประเภทการเคลื่อนไหว | 4,152 | 35 วิ |
| `Product_2Supply chain.sql` | ทะเบียนสินค้า ระดับ SKU | 30,827 | 38 วิ |

## `PROJECT_1.dbo.Transaction_FO` — ตารางขับ

| คอลัมน์ | ใช้ทำอะไร |
|---|---|
| `CompanyCode` | **คีย์บังคับทุก join ที่ออกไปฐานอื่น** · กรอง BU · แปลงเป็นชื่อบริษัท |
| `INVENTLOCATIONID` | กรองคลัง · join `tm_Warehouse` |
| `DATEPHYSICAL` | กรองช่วง · แตก YEAR / MONTH |
| `REFERENCECATEGORY` | แยก MovementType · ตัดค่า 7 ทิ้ง |
| `[FO-ITEMNO]` | join `tm_Item` · นับ SKU |
| `[ITEC-ITEMNO]` | สะพานไปฝั่ง ITEC |
| `[Ref.DocNum]` | join `purchtable` · นับใบสั่งซื้อ |
| `QTY` | แยก QtyIn / QtyOut ด้วยเครื่องหมาย |
| `RealCost` | ต้นทุน — **อย่าใช้ `COSTAMOUNTPOSTED` เดี่ยว ๆ** |

## `syndpdev001.dbo.tm_Item` — ทะเบียนสินค้า

| คอลัมน์ | ใช้ทำอะไร |
|---|---|
| `ItemId` + `SysCompanyId` | **คีย์คู่** join กับ `[FO-ITEMNO]` + `CompanyCode` |
| `SysSourceRef` | ต้องกรอง `= 'FO'` — ตารางนี้ปน BCLS อยู่ 33,419 แถว |
| `DefaultDimension` | สะพานไปหมวดสินค้า |
| `RecId` | ใช้ใน `ROW_NUMBER()` เลือกแถวล่าสุด |
| `ItemName` · `Brand` | ชื่อและแบรนด์ |

⚠️ `(ItemId, SysCompanyId)` **ยังซ้ำอยู่ 6 คีย์** — ต้อง `ROW_NUMBER()` ไม่ใช่ `DISTINCT`

## `syndpdev001.dbo.tm_FinDimValueSet` — หมวดสินค้า

| คอลัมน์ | ใช้ทำอะไร |
|---|---|
| `FinancialDim` | join กับ `tm_Item.DefaultDimension` · **ไม่ซ้ำทั้งตาราง 719,054 ค่า** |
| `SysSourceRef` | กรอง `= 'FO'` |
| `GroupCategoryName` · `CategoryName` · `SubCategoryName` | หมวด 3 ชั้น |

⚠️ **ไม่ต้องกรอง `CompanyName`** — กรองไปจะทำให้ dim ที่ชี้ไป `GI` / `TFF` หล่นหาย
คอลัมน์อื่นที่ยังไม่ได้ใช้แต่มีอยู่ — `BusinessUnitName` `DepartmentName` `ChannelName` `VendorName` `MainAccountName`

## `syndpdev001.dbo.tm_Warehouse` — คลัง

| คอลัมน์ | ใช้ทำอะไร |
|---|---|
| `WarehouseId` + `SysCompanyId` | **คีย์คู่** join กับ `INVENTLOCATIONID` + `CompanyCode` |
| `Name` | ชื่อคลัง — ตัดคำนำหน้า `ID4 : ` ด้วย `SUBSTRING(..., CHARINDEX(':', ...)+1, ...)` |
| `InTransiteWarehouse` | คลังพักระหว่างทาง (ยังไม่ได้ใช้ในชุดนี้) |
| `SiteId` | ไซต์ |

## `D365FO_DATALAKE` — ฝั่งจัดซื้อและทะเบียน

| ตาราง | คอลัมน์ | ใช้ทำอะไร |
|---|---|---|
| `purchtable` | `purchid` + `dataareaid` | **คีย์คู่** join กับ `[Ref.DocNum]` + `CompanyCode` · ไม่ซ้ำทั้ง 2,603,821 คีย์ |
| | `orderaccount` | รหัสผู้ขาย |
| | `inventsiteid` | ไซต์เริ่มต้น |
| `vendtable` | `accountnum` + `dataareaid` | join กับ `orderaccount` |
| | `party` | สะพานไปชื่อผู้ขาย |
| `dirpartytable` | `recid` | join กับ `vendtable.party` |
| | `name` | **ชื่อผู้ขาย — ครบ 100%** |
| `inventtable` | `itemid` + `dataareaid` | join ทะเบียน |
| | `width` `height` `depth` `netweight` `taraweight` `unitvolume` | 🔴 **ว่างเปล่าทั้งระบบ** |

## 🔴 สิ่งที่แก้จากไฟล์ต้นฉบับ

| ไฟล์เดิมเขียนว่า | ปัญหาจริง | แก้เป็น |
|---|---|---|
| `FROM tb_PurchOrder` | **com7 หายทั้งหมด 0 แถว** | `D365FO_DATALAKE.dbo.purchtable` |
| `FROM dirpartytable` แล้ว join ลงมา | ตัวกรองอยู่ปลายทาง เครื่องกาง join ก่อนค่อยตัด | ขับจาก `Transaction_FO` |
| `w.WarehouseId = a.INVENTLOCATIONID` | ขาด `SysCompanyId` — เลขคลังซ้ำข้าม BU ได้ | เติมคีย์คู่ |
| ไม่กรอง `REFERENCECATEGORY` | ปน Transfer 14.2 ล้านแถว · Sales order 2.4 ล้าน | `= 3` สำหรับผู้ขาย |
| `BETWEEN @from AND @to` | ถ้าวันหนึ่ง `DATEPHYSICAL` มีเวลา วันสุดท้ายจะหาย | `>= @from AND < @to + 1` |
| `QTY >= 0` | ไม่มีแถวไหน QTY = 0 ทั้งตาราง | `QTY > 0` และแยก `Return_Qty` |
| รวมทุกประเภทเป็นก้อนเดียว | **ของที่ผ่านคลังหายเกือบ 90%** | เพิ่ม `MovementType` |
| `ORDER BY ... QtyIn + QtyOut DESC` | SQL Server ใช้ alias ในนิพจน์ของ ORDER BY ไม่ได้ | `ORDER BY ... Lines DESC` |

### ผลหลังแก้ — com7 กลับมา

| Company | Inbound_Qty เดิม | หลังแก้ |
|---|--:|--:|
| **COMSEVEN** | **0** | **23,387,895** |
| DOUBLESEVEN | 14,485 | 1,450,679 |
| ADEPT | 1,068,332 | 1,066,716 |

### สัดส่วนการเคลื่อนไหวจริงในขอบเขต 6 คลัง · 20 เดือน

| Company | PO ซื้อเข้า | SO ขาย | Transfer โอน |
|---|--:|--:|--:|
| COMSEVEN | 23,387,895 เข้า | 1,711,563 ออก | **23,711,253 ออก** |
| DOUBLESEVEN | 1,450,679 เข้า | 14,049 ออก | **1,433,837 ออก** |
| ADEPT | 1,066,716 เข้า | 951,861 ออก | 21,777 ออก |

**COM7 และ Double7 จ่ายออกด้วยการโอนเป็นหลัก ไม่ใช่การขาย** ส่วน Adept ขายจากคลังเองเป็นหลัก

---

# ฐานสำรอง — `D365FO_DATALAKE.dbo.inventtrans`

**289,817,143 แถว · 105 คอลัมน์** · มากกว่า `Transaction_FO` อยู่ **13,697,280 แถว**

นี่คือตาราง `InventTrans` ดิบของ D365 ที่ยังไม่ได้ตัดคอลัมน์ทิ้ง — `Transaction_FO` คือฉบับย่อ 20 คอลัมน์

## เมื่อไหร่ควรใช้ฐานนี้

| ต้องการ | ใช้ |
|---|---|
| งานประจำวัน · รายงานทั่วไป | ✅ `Transaction_FO` — เร็วกว่ามาก |
| เลขที่ใบกำกับ / ใบส่งของ | `invoiceid` · `packingslipid` |
| สถานะวงจรชีวิตรายการ | `statusissue` · `statusreceipt` |
| ชื่อสินค้าติดมาในแถวเดียวกัน | `itemname` · `itemgroupid` · `namealias` |
| การปิดบัญชีต้นทุน | `dateclosed` · `qtysettled` · `costamountsettled` |
| เลขบัญชีแยกประเภท | `voucher` · `voucherphysical` |
| ใครสร้าง/แก้ เมื่อไหร่ | `createdby` · `createddatetime` · `modifiedby` |

## 🔴 ช้ากว่ามาก — ต้องเลือกคอลัมน์ให้ตรงดัชนี

ตารางนี้มีดัชนีครอบแค่ชุดเดียว

```
inventtransid, inventtransorigin, inventdimid, packingslipid, itemid,
referencecategory, statusreceipt, statusissue, packingslipreturned,
dataareaid, datephysical, SinkModifiedOn
```

| คิวรี | เวลา |
|---|--:|
| `GROUP BY dataareaid` (อยู่ในดัชนี) | 73 วิ |
| `GROUP BY statusissue` (อยู่ในดัชนี) | 72 วิ |
| **`GROUP BY IsDelete` (ไม่อยู่ในดัชนี)** | **537 วิ** |

เทียบกับ `Transaction_FO` ที่ทำงานคล้ายกันใช้ 16–77 วินาที

## สิ่งที่ตรวจแล้ว

**`IsDelete` เป็น NULL ทั้ง 289,817,143 แถว** — ยังไม่ถูกใช้งาน ไม่ต้องกรอง

**`dataareaid` = `CompanyCode`** — 21 บริษัทเดียวกับ `Transaction_FO` สัดส่วนเท่ากัน (com7 91.49%)

**`statusissue` / `statusreceipt` บอกทิศทางและสถานะ**

| refcat | statusissue | statusreceipt | แถว | ความหมาย |
|--:|--:|--:|--:|---|
| 4 | 0 | 1 | 6,104,439 | ขาเข้า |
| 4 | **6** | 0 | 2,042,308 | สั่งแล้วยังไม่เคลื่อนไหว `[อนุมาน]` |
| 6 | 1 | 0 | 51,405,805 | ขาออกของการโอน |
| 6 | 0 | 1 | 51,405,804 | ขาเข้าของการโอน |
| 6 | **6** | 0 | 5,057,818 | สั่งโอนแล้วยังไม่ส่ง `[อนุมาน]` |
| 6 | 0 | **5** | 5,055,903 | รอรับ `[อนุมาน]` |
| 21 / 22 | 1↔0 | 0↔1 | 2.4M คู่ | ขาส่ง / ขารับ |

`[อนุมาน]` ค่า 5 และ 6 คือสถานะ **Ordered / OnOrder** ตามมาตรฐาน D365 — **ยังไม่ได้ยืนยันกับ MIS-ERP**
`[อนุมาน]` ส่วนต่าง 13.7 ล้านแถวน่าจะมาจากรายการสถานะเปิดพวกนี้ ที่ `Transaction_FO` ไม่ยกมา — **ยังไม่ได้พิสูจน์**

## ตารางใหญ่อื่นใน DATALAKE

| ตาราง | แถว | น่าจะใช้ทำอะไร |
|---|--:|---|
| `generaljournalaccountentry` | 623,884,558 | บัญชีแยกประเภท |
| `inventtransposting` | 468,189,036 | การลงบัญชีสต็อก |
| `inventtransorigin` | 246,507,745 | ต้นทางรายการ |
| `custinvoicetrans` | 118,062,321 | บรรทัดใบกำกับลูกค้า |
| `salesline` | 106,393,801 | บรรทัดใบสั่งขาย |
| `inventsum` | 85,515,703 | ยอดคงเหลือสรุป |
| `inventdim` | 80,660,986 | มิติสินค้า (`inventdimid`) |

**ทั้งหมดนี้ยังไม่ได้สำรวจ**

---

# กฎที่ใช้ได้กับทุกคิวรี

```sql
-- ① ข้อมูลจริงเริ่มปี 2020 ก่อนนั้นมี 4 แถวคีย์ผิด
AND a.DATEPHYSICAL >= '2020-01-01'

-- ② ตัดรายการปิดบัญชีถัวเฉลี่ย ไม่ใช่การเคลื่อนไหวจริง
AND a.REFERENCECATEGORY <> 7

-- ③ serial ที่ใช้ได้จริง
AND a.INVENTSERIALID IS NOT NULL
AND a.INVENTSERIALID NOT IN ('NULL', 'PENDING', '1234')
AND LEN(a.INVENTSERIALID) >= 8

-- ④ ตัดรายการที่ยังไม่ลงบัญชี (เฉพาะรายงานต้นทุน)
AND a.DATEFINANCIAL >= '1901-01-01'

-- ⑤ join กับตารางฝั่ง syndpdev001 ต้องมี CompanyCode เสมอ
AND x.SysCompanyId = a.CompanyCode
```

**การโอนต้องแยกตาม BU**

```sql
-- com7 — 2 ขา จบในวันเดียว
WHERE CompanyCode = 'com7' AND REFERENCECATEGORY = 6

-- BU อื่น — 4 ขา ผ่านคลังพัก คนละวัน
WHERE CompanyCode <> 'com7' AND REFERENCECATEGORY IN (21, 22)
```

**เช็กความสดก่อนส่งรายงานเสมอ** — `drph` ช้า 78 วัน · `gi04` ช้า 106 วัน · `drl` ตายไป 2 ปี

```sql
SELECT CompanyCode, MAX(Transorigin_Sinkdate) AS ไหลเข้าล่าสุด
FROM PROJECT_1.dbo.Transaction_FO WITH (NOLOCK)
WHERE CompanyCode IN ('com7','dou7','bnn') GROUP BY CompanyCode;
```

---

## เชื่อมโยง

[[D365 F&O Overview]] · [[D365 F&O - Transaction_FO Dictionary]]
[[ITEC - Query Cookbook]] · [[ITEC - Data Dictionary]] · [[ITEC Product Dimension]]
[[System Inventory]] · [[Environment Setup]] · [[Open Questions & Risks]]
