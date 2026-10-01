/* ══════════════════════════════════════════════════════════════════════════
   ผู้ขาย — ปริมาณรับเข้ารวมทั้งช่วง แยกบริษัท (ไม่แยกเดือน/คลัง)
   ──────────────────────────────────────────────────────────────────────────
   แก้จากฉบับเดิม 5 จุด (ดูท้ายไฟล์)  ·  ตรวจกับฐานจริง 2026-09-24
   เอกสาร: COM7-Knowledge-Base/02_System/D365 F&O/D365 F&O - Query Cookbook.md
   ══════════════════════════════════════════════════════════════════════════ */
DECLARE @from date = '2025-01-01';
DECLARE @to   date = '2026-08-31';

SELECT
      d.name                                      AS VendorName
    , h.orderaccount                              AS VendorCode
    , CASE a.CompanyCode WHEN 'com7' THEN 'COMSEVEN'
                         WHEN 'bnn'  THEN 'ADEPT'
                         WHEN 'dou7' THEN 'DOUBLESEVEN'
                         ELSE a.CompanyCode END   AS Company
    , COUNT(DISTINCT a.[Ref.DocNum])              AS Trans_PO
    , COUNT(DISTINCT a.[FO-ITEMNO])               AS SKU
    , CAST(SUM(CASE WHEN a.QTY > 0 THEN a.QTY ELSE 0 END) AS decimal(18,2))
                                                  AS Inbound_Qty
    , CAST(SUM(CASE WHEN a.QTY < 0 THEN -a.QTY ELSE 0 END) AS decimal(18,2))
                                                  AS Return_Qty
    , CAST(SUM(a.RealCost) AS decimal(28,2))      AS Cost

FROM        PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)      -- ① ขับจากตารางที่กรองแล้ว

LEFT JOIN   D365FO_DATALAKE.dbo.purchtable h WITH (NOLOCK)    -- ② purchtable ไม่ใช่ tb_PurchOrder
       ON   h.purchid    = a.[Ref.DocNum]
      AND   h.dataareaid = a.CompanyCode

LEFT JOIN   D365FO_DATALAKE.dbo.vendtable v WITH (NOLOCK)
       ON   v.accountnum = h.orderaccount
      AND   v.dataareaid = h.dataareaid

LEFT JOIN   D365FO_DATALAKE.dbo.dirpartytable d WITH (NOLOCK) -- ③ ชื่อผู้ขายอยู่ที่นี่
       ON   d.recid = v.party

WHERE       a.REFERENCECATEGORY = 3                           -- ⑤ Purchase order เท่านั้น
  AND       a.CompanyCode      IN ('com7','dou7','bnn')
  AND       a.INVENTLOCATIONID IN ('4','77','72006','72008','79001')
  AND       a.DATEPHYSICAL     >= @from
  AND       a.DATEPHYSICAL      < DATEADD(day, 1, @to)

GROUP BY    d.name, h.orderaccount, a.CompanyCode
ORDER BY    Company, Inbound_Qty DESC;

/* ── แก้อะไรไปบ้าง ────────────────────────────────────────────────────────
 ① ขับจาก Transaction_FO แทน dirpartytable
    เดิมเริ่มจาก dirpartytable 114,573 แถว แล้ว join ลงมา — ตัวกรองอยู่ปลายทาง
    ทำให้เครื่องต้องกาง join ก่อนค่อยตัดทิ้ง ช้าโดยไม่จำเป็น

 ② purchtable แทน tb_PurchOrder
    🔴 tb_PurchOrder ไม่มี com7 เลยแม้แต่แถวเดียว (ทดสอบ PO ปี 2026: 0% จาก 4.5M แถว)
    purchtable มีครบทุก BU · (purchid, dataareaid) ไม่ซ้ำทั้ง 2,603,821 คีย์

 ③ ชื่อผู้ขายมาจาก dirpartytable.name
    vendtable มี 225 คอลัมน์ แต่ไม่มีคอลัมน์ name — ต้องผ่าน vendtable.party
    อย่าใช้ bpc_nameeng: ว่าง 98.2% (com7) · 99.7% (bnn)

 ④ join tm_Warehouse ต้องมี SysCompanyId
    เลขคลัง 5 ตัวที่ใช้อยู่ยังไม่ซ้ำข้ามบริษัท จึงยังไม่พัง
    แต่ทั้งฐานมีคลัง 3,690 แห่งจาก 22 บริษัท เลขซ้ำกันได้ — กันไว้ก่อน

 ⑤ REFERENCECATEGORY = 3
    เดิมไม่กรองประเภท ในขอบเขตนี้มี Transfer 14.2 ล้านแถว · Sales order 2.4 ล้าน
    บังเอิญไม่ชนเพราะเลขเอกสารคนละรูปแบบ (JN* กับ PO*) แต่ทำให้ช้าและเสี่ยง

 ⑥ QTY > 0 แทน QTY >= 0  —  ไม่มีแถวไหน QTY = 0 ทั้งตาราง ผลเท่ากันแต่ตรงความหมาย
    และแยก Return_Qty ออกมา จะได้เห็นของที่คืนผู้ขาย (157,035 แถวทั้งตาราง)

 ⑦ dou7 ใช้ 79001 (Warehouse กลาง) ไม่ใช่ 79006 — ยืนยัน 2026-09-24
    79001 รับเข้า 1,436,194 ชิ้น = 98.3% ของ dou7
    79006 WHOLESALE ADEPT YA รับแค่ 14,485 ชิ้น = 1.0% จึงตัดออก
   ─────────────────────────────────────────────────────────────────────── */
