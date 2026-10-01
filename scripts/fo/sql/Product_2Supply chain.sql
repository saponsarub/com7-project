/* ══════════════════════════════════════════════════════════════════════════
   ทะเบียนสินค้า — รหัสทั้งสองระบบ · หมวด · ขนาด/น้ำหนัก · ปริมาณที่เคลื่อนไหว
   ──────────────────────────────────────────────────────────────────────────
   🔴 ขนาด/น้ำหนักใน D365FO ว่างเปล่าทั้งระบบ — ดูท้ายไฟล์
   เอกสาร: COM7-Knowledge-Base/06_Project/Warehouse Consultant Data Request.md
   ══════════════════════════════════════════════════════════════════════════ */
DECLARE @from date = '2025-01-01';
DECLARE @to   date = '2026-08-31';

WITH item AS (
    SELECT ItemId, SysCompanyId, DefaultDimension, ItemName, Brand,
           ROW_NUMBER() OVER (PARTITION BY ItemId, SysCompanyId
                              ORDER BY RecId DESC) AS rn
    FROM   syndpdev001.dbo.tm_Item WITH (NOLOCK)
    WHERE  SysSourceRef = 'FO' AND ItemId IS NOT NULL
),
mv AS (                     -- ยุบความเคลื่อนไหวก่อน แล้วค่อยแปะทะเบียน
    SELECT a.CompanyCode, a.[FO-ITEMNO] AS ItemId_FO,
           MAX(a.[ITEC-ITEMNO])              AS ItemId_ITEC,
           COUNT_BIG(*)                      AS Lines,
           CAST(SUM(CASE WHEN a.REFERENCECATEGORY = 3 AND a.QTY > 0
                         THEN a.QTY ELSE 0 END) AS decimal(18,2)) AS PO_In,
           CAST(SUM(CASE WHEN a.REFERENCECATEGORY = 0 AND a.QTY < 0
                         THEN -a.QTY ELSE 0 END) AS decimal(18,2)) AS SO_Out,
           CAST(SUM(CASE WHEN a.REFERENCECATEGORY IN (6,21,22) AND a.QTY > 0
                         THEN a.QTY ELSE 0 END) AS decimal(18,2)) AS Transfer_In,
           CAST(SUM(CASE WHEN a.REFERENCECATEGORY IN (6,21,22) AND a.QTY < 0
                         THEN -a.QTY ELSE 0 END) AS decimal(18,2)) AS Transfer_Out
    FROM   PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)
    WHERE  a.CompanyCode      IN ('com7','dou7','bnn')
      AND  a.INVENTLOCATIONID IN ('4','77','72006','72008','79001')
      AND  a.DATEPHYSICAL     >= @from
      AND  a.DATEPHYSICAL      < DATEADD(day, 1, @to)
      AND  a.REFERENCECATEGORY <> 7
    GROUP BY a.CompanyCode, a.[FO-ITEMNO]
)
SELECT
      CASE mv.CompanyCode WHEN 'com7' THEN 'COMSEVEN'
                          WHEN 'bnn'  THEN 'ADEPT'
                          WHEN 'dou7' THEN 'DOUBLESEVEN'
                          ELSE mv.CompanyCode END AS Company
    , mv.ItemId_FO
    , mv.ItemId_ITEC
    , bb.ItemName                                 AS ItemName
    , bb.Brand                                    AS Brand
    , ISNULL(cc.GroupCategoryName, '(ไม่มีหมวด)') AS GroupCategoryName
    , ISNULL(cc.CategoryName,      '(ไม่มีหมวด)') AS CategoryName
    , ISNULL(cc.SubCategoryName,   '(ไม่มีหมวด)') AS SubCategoryName
    , mv.PO_In
    , mv.SO_Out
    , mv.Transfer_In
    , mv.Transfer_Out
    , mv.Lines
    -- 🔴 ทั้ง 6 คอลัมน์ข้างล่างเป็น 0 ทุกแถว — ฟิลด์มีอยู่แต่ไม่มีใครกรอก
    , it.width       AS Width
    , it.height      AS Height
    , it.depth       AS Depth
    , it.netweight   AS NetWeight
    , it.taraweight  AS TaraWeight
    , it.unitvolume  AS UnitVolume

FROM        mv

LEFT JOIN   item bb
       ON   bb.ItemId       = mv.ItemId_FO
      AND   bb.SysCompanyId = mv.CompanyCode
      AND   bb.rn           = 1

LEFT JOIN   syndpdev001.dbo.tm_FinDimValueSet cc WITH (NOLOCK)
       ON   cc.FinancialDim = bb.DefaultDimension
      AND   cc.SysSourceRef = 'FO'

LEFT JOIN   D365FO_DATALAKE.dbo.inventtable it WITH (NOLOCK)
       ON   it.itemid     = mv.ItemId_FO
      AND   it.dataareaid = mv.CompanyCode

ORDER BY    Company, mv.PO_In DESC;

/* ── 🔴 ขนาด/น้ำหนักไม่มีข้อมูลเลยทั้งระบบ ─────────────────────────────────
 ตรวจ D365FO_DATALAKE.dbo.inventtable ครบทุกบริษัท 360,823 แถว เมื่อ 2026-09-24

     width · height · depth · netweight · taraweight   ->  ไม่เป็นศูนย์  0 แถว
     grosswidth                                        ->  1 แถว (gi)
     unitvolume                                        ->  1 แถว (drph)

 ฝั่ง ITEC ยิ่งไม่มี — rpt.dim_item_itec มีแค่ 6 คอลัมน์
 (ItemId · ItemName · CategoryName · SubCategoryName · Model/Series · Brand)

 คงคอลัมน์ไว้เพื่อให้เห็นว่าฟิลด์มีอยู่จริง ถ้าวันหนึ่งมีคนกรอกจะได้ใช้ได้ทันที
 ถ้าต้องการขนาด/น้ำหนักจริงตอนนี้ ต้องเก็บใหม่หรือขอจากผู้ผลิต

 ── ItemId_ITEC ใช้ทำอะไร ────────────────────────────────────────────────
 เป็นสะพานไปฝั่ง ITEC — join กับ rpt.dim_item_itec.ItemId (= PRODUCT_ID ชั้น ci)
 ทดสอบแล้วติด 100.0% เมื่อนับเป็นแถว · 1 รหัส ITEC ผูกกับ 1 รหัส FO เสมอ
 ถ้า ItemId_ITEC = ItemId_FO แปลว่าสินค้านั้นไม่มีรหัสฝั่ง ITEC

 ── ทำไมต้องมี CTE mv ────────────────────────────────────────────────────
 ยุบ Transaction_FO ให้เหลือระดับสินค้าก่อน แล้วค่อย join ทะเบียน
 ถ้า join ก่อนยุบ เครื่องต้องลาก tm_Item และ inventtable ไปกับทุกแถวใน 26 ล้านแถว
   ─────────────────────────────────────────────────────────────────────── */
