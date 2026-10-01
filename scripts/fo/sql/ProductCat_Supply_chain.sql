/* ══════════════════════════════════════════════════════════════════════════
   หมวดสินค้า — ปริมาณเข้า/ออก แยกบริษัท · คลัง · ประเภทการเคลื่อนไหว
   ──────────────────────────────────────────────────────────────────────────
   🔴 เพิ่ม MovementType จากฉบับเดิม — เหตุผลอยู่ท้ายไฟล์ สำคัญมาก
   เอกสาร: COM7-Knowledge-Base/02_System/D365 F&O/D365 F&O - Query Cookbook.md
   ══════════════════════════════════════════════════════════════════════════ */
DECLARE @from date = '2025-01-01';
DECLARE @to   date = '2026-08-31';

WITH item AS (              -- 1 สินค้า 1 บริษัท ต้องได้ 1 แถวเท่านั้น
    SELECT ItemId, SysCompanyId, DefaultDimension,
           ROW_NUMBER() OVER (PARTITION BY ItemId, SysCompanyId
                              ORDER BY RecId DESC) AS rn
    FROM   syndpdev001.dbo.tm_Item WITH (NOLOCK)
    WHERE  SysSourceRef = 'FO' AND ItemId IS NOT NULL
)
SELECT
      CASE a.CompanyCode WHEN 'com7' THEN 'COMSEVEN'
                         WHEN 'bnn'  THEN 'ADEPT'
                         WHEN 'dou7' THEN 'DOUBLESEVEN'
                         ELSE a.CompanyCode END   AS Company
    , a.CompanyCode                               AS BU
    , a.INVENTLOCATIONID                          AS WarehouseId
    , LTRIM(SUBSTRING(w.Name, CHARINDEX(':', w.Name) + 1, LEN(w.Name)))
                                                  AS WarehouseName
    , CASE a.REFERENCECATEGORY
           WHEN 3  THEN 'PO ซื้อเข้า'
           WHEN 0  THEN 'SO ขาย'
           WHEN 6  THEN 'Transfer โอน'
           WHEN 21 THEN 'Transfer โอน'
           WHEN 22 THEN 'Transfer โอน'
           ELSE 'อื่น ๆ' END                      AS MovementType
    , ISNULL(cc.GroupCategoryName, '(ไม่มีหมวด)') AS GroupCategoryName
    , ISNULL(cc.CategoryName,      '(ไม่มีหมวด)') AS CategoryName
    , ISNULL(cc.SubCategoryName,   '(ไม่มีหมวด)') AS SubCategoryName
    , COUNT_BIG(*)                                AS Lines
    , COUNT(DISTINCT a.[FO-ITEMNO])               AS SKU
    , COUNT(DISTINCT a.[Ref.DocNum])              AS DocCount
    , CAST(SUM(CASE WHEN a.QTY > 0 THEN  a.QTY ELSE 0 END) AS decimal(18,2)) AS QtyIn
    , CAST(SUM(CASE WHEN a.QTY < 0 THEN -a.QTY ELSE 0 END) AS decimal(18,2)) AS QtyOut
    , CAST(SUM(a.RealCost) AS decimal(28,2))      AS CostNet

FROM        PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)

LEFT JOIN   item bb
       ON   bb.ItemId       = a.[FO-ITEMNO]
      AND   bb.SysCompanyId = a.CompanyCode       -- กันหมวดข้ามบริษัท
      AND   bb.rn           = 1

LEFT JOIN   syndpdev001.dbo.tm_FinDimValueSet cc WITH (NOLOCK)
       ON   cc.FinancialDim = bb.DefaultDimension
      AND   cc.SysSourceRef = 'FO'                -- ไม่ต้องกรอง CompanyName

LEFT JOIN   syndpdev001.dbo.tm_Warehouse w WITH (NOLOCK)
       ON   w.WarehouseId  = a.INVENTLOCATIONID
      AND   w.SysCompanyId = a.CompanyCode

WHERE       a.CompanyCode      IN ('com7','dou7','bnn')
  AND       a.INVENTLOCATIONID IN ('4','77','72006','72008','79001')
  AND       a.DATEPHYSICAL     >= @from
  AND       a.DATEPHYSICAL      < DATEADD(day, 1, @to)
  AND       a.REFERENCECATEGORY <> 7              -- ตัดรายการปิดบัญชีถัวเฉลี่ย

GROUP BY    a.CompanyCode, a.INVENTLOCATIONID, w.Name, a.REFERENCECATEGORY,
            cc.GroupCategoryName, cc.CategoryName, cc.SubCategoryName
ORDER BY    Company, WarehouseId, MovementType, Lines DESC;   -- SQL Server ใช้ alias ในนิพจน์ของ ORDER BY ไม่ได้

/* ── 🔴 ทำไมต้องมี MovementType ────────────────────────────────────────────
 คลังกลางไม่ได้ ขาย ให้ลูกค้า แต่ โอน ไปสาขา — ตัวเลขฟ้องชัดเจน

     COM7 คลัง 4   รับเข้า 15.3 ล้านชิ้น   แต่ถ้านับแค่ Sales จ่ายออก 0.9 ล้าน
     ITEC สาขา 4   Transfer-Out 8,424,259 แถว   ·   Sales 0 แถว

 ในขอบเขตนี้ (6 คลัง · 20 เดือน) สัดส่วนจริงคือ

     Transfer          14,200,047 แถว   <- ใหญ่สุด
     Purchase order     9,558,935
     Sales order        2,400,141
     Transaction          207,477

 ถ้ารวมทุกประเภทเป็นก้อนเดียว QtyIn/QtyOut จะปนกันจนอ่านไม่ออก
 ถ้านับแค่ PO+SO ของที่ผ่านคลังจะหายไปเกือบ 90%

 ── ที่คงไว้เหมือนเดิม ──────────────────────────────────────────────────
 · ROW_NUMBER() ไม่ใช่ DISTINCT — (ItemId, SysCompanyId) ยังซ้ำอยู่ 6 คีย์
 · ไม่กรอง cc.CompanyName — FinancialDim ไม่ซ้ำทั้งตาราง 719,054 ค่า
 · REFERENCECATEGORY <> 7 — Weighted average inventory closing ไม่ใช่การเคลื่อนไหว
 · >= @from AND < @to + 1 แทน BETWEEN

 ── ที่เพิ่ม ─────────────────────────────────────────────────────────────
 · join tm_Warehouse เพื่อได้ชื่อคลัง — ต้องมี SysCompanyId คู่เสมอ
 · dou7 ใช้ 79001 (Warehouse กลาง) 2,413,236 แถว — ยืนยัน 2026-09-24
   79006 WHOLESALE ADEPT YA ถูกตัดออก มีรับเข้าแค่ 14,485 ชิ้น = 1% ของ dou7
 · แยก QtyIn / QtyOut / DocCount / Lines / SKU ออกจากกัน

 ⚠️ หมวดฝั่ง FO ไม่ใช่ลำดับชั้นจริง — 345 จาก 487 หมวดชี้ไปหลายกลุ่ม
    Common อยู่ใต้ 67 กลุ่ม · iPhone 39 กลุ่ม
    ห้าม GROUP BY CategoryName เดี่ยว ๆ ต้องจับคู่ GroupCategoryName เสมอ
 ⚠️ com7 จัดสินค้า demo ทุกชนิดไว้ใต้กลุ่ม iPhone (แอร์ Xiaomi · หูฟัง Redmi ก็อยู่ในนั้น)
   ─────────────────────────────────────────────────────────────────────── */
