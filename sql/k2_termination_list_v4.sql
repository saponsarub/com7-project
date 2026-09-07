/* =============================================================================
   K2 — รายชื่อสัญญาบอกเลิก · เวอร์ชัน 4 · 2026-08-31
   คัดจาก CUSTOMER_CARD ล้วน — ไม่ใช้ COLLECTION_OD ในการคัดอีกต่อไป

   ทำไมเปลี่ยน
   -----------
   v3 คัดด้วย COLLECTION_OD.CONTRACT_STATUS = 48 ซึ่งมี 2 ปัญหา
     1. อัปเดตช้า — snapshot แช่แข็ง คนที่จ่ายมาหลังวันคัดยังติดอยู่ในรายชื่อ
     2. ป้ายเหนียว — ขึ้น 48 แล้วไม่ลงแม้จ่ายลดลงมา
   ผลคือรอบ 8/2026 มี 204 จาก 617 รายที่ค้างจริงไม่ถึง 6 งวด

   v4 นับ "งวดที่ยังไม่มีใบเสร็จ และเลยวันครบกำหนดแล้ว" จากการ์ดตรง ๆ
   การ์ดอัปเดตทันทีที่รับชำระ จึงเป็นภาพ ณ วันที่รันเสมอ

   เกณฑ์คัด
   --------
     1. นับจำนวนงวดที่ค้าง (N_OD) ได้ >= @minod
     2. **ครบ OD6 ในรอบเดือนของ @cut** — ไม่ใช่ครบมาตั้งแต่รอบก่อน (@newonly = 1)
     3. สัญญายังไม่ถูกปิด/ขายหนี้/ตัดหนี้สูญ/บอกเลิกไปแล้ว

   ข้อ 2 สำคัญ — คนที่ครบ OD6 เดือนก่อนต้องอยู่ในรายชื่อของเดือนนั้นไปแล้ว ส่งซ้ำไม่ได้
   และเป็นตัวกันไม่ให้สัญญาที่ตายไปนานแล้วไหลกลับเข้ามาจากการนับรอบนอกสัญญา

   กรณี 1 · OD6 ปกติ — งวดค้างล่าสุดอยู่ในรอบเดือนปัจจุบัน (>= @cut)
        ค้างงวดสุดท้าย = งวดที่เลยกำหนดล่าสุด
        นับงวดค้าง    = งวดว่างในการ์ดที่ DUEDATE <= @asof
   กรณี 2 · สัญญาหมดอายุไปแล้ว — งวดค้างล่าสุดเก่ากว่า @cut
        ค้างงวดสุดท้าย = งวดสุดท้ายของสัญญา
        นับงวดค้าง    = **ในสัญญา + นอกสัญญา** ถึง @asof
                        สัญญาจบแล้วการ์ดไม่ออกงวดใหม่ ถ้านับแค่งวดว่างจะไม่ถึง 6
                        จึงนับรอบชำระที่ผ่านไปตั้งแต่งวดแรกที่ค้างจนถึง @asof

   ⚠ N_OD ใช้ **ตัดสินว่าเข้าเกณฑ์ 6 งวดไหม เท่านั้น** ไม่เอาไปแสดงและไม่เอาไปคิดเงิน

     ทุกช่องที่ออกหนังสือ — จำนวนงวดค้าง · งวดที่ครบ OD6 · วันที่เป็น OD6 ·
     ค่าเช่าซื้อค้าง · ค่าปรับ · ค่าติดตาม — **หยุดที่งวดสุดท้ายของสัญญา**
     เคสหมดสัญญานับถึงแค่เดือนสุดท้ายที่หมดสัญญา

     เหตุผล: K2 - Fee Policy ผูกค่าปรับกับ "งวดที่ค้างชำระ" ไม่ใช่เดือนที่ผ่านไป
     งวดที่ไม่มีอยู่ในสัญญาไม่มีค่างวด จึงไม่มีค่าปรับและไม่มีค่าติดตาม

   วันที่เป็น OD6 (แก้ 2026-09-04)
   ---------------------------------
   = วันถัดจากวันครบกำหนดของงวดค้างลำดับที่ 6  (+1 วัน)
     เพราะวันครบกำหนดลูกค้ายังมีสิทธิ์ชำระ สิทธิ์บอกเลิกจึงเกิดวันถัดไป
   เคสหมดสัญญา ใช้ "งวดแรกที่ค้าง + 5 เดือน + 1 วัน" ไม่ใช่วันสิ้นสุดสัญญา

   ค่าปรับ/ค่าติดตาม คิดตาม K2 - Fee Policy (เกณฑ์ A/B รวมค่าปรับ 100 ก่อนเทียบ 1,000)
   ============================================================================= */

DECLARE @asof  date = '2026-08-31';   -- นับงวดค้างถึงวันนี้
DECLARE @cut   date = '2026-08-01';   -- เส้นแบ่งกรณี 1 / กรณี 2
DECLARE @minod int  = 6;              -- ต้องค้างอย่างน้อยกี่งวดจึงออกหนังสือได้
DECLARE @round int  = 0;              -- 0 = ทุกรอบ · 1 = เฉพาะรอบวันที่ 1 · 16 = รอบวันที่ 16
DECLARE @newonly int = 1;             -- 1 = เอาเฉพาะคนที่ครบ OD6 ในเดือนของ @cut
                                      -- 0 = เอาทุกคนที่ค้างครบ 6 งวด ไม่ว่าครบเมื่อไหร่

WITH
/* 1) สรุปการ์ดผ่อนรายสัญญา + คัดเฉพาะที่ค้างครบเกณฑ์ (HAVING ตัดตั้งแต่ต้น) */
card AS (
    SELECT CONTRACT_ID,
           COUNT(*)                                                         AS N_CARD,
           MAX(INSTALL_NUM)                                                 AS LAST_INSTALL_NUM,
           MIN(DUEDATE)                                                     AS FIRST_DUE,
           MAX(DUEDATE)                                                     AS CONTRACT_LAST_DUE,
           MIN(CASE WHEN RECEIPT_NUMBER IS NULL THEN INSTALL_NUM END)       AS FIRST_UNPAID_NUM,
           MIN(CASE WHEN RECEIPT_NUMBER IS NULL THEN DUEDATE END)           AS FIRST_UNPAID_DUE,
           MAX(CASE WHEN RECEIPT_NUMBER IS NULL AND DUEDATE <= @asof
                    THEN INSTALL_NUM END)                                   AS LAST_PASTDUE_NUM,
           MAX(CASE WHEN RECEIPT_NUMBER IS NULL AND DUEDATE <= @asof
                    THEN DUEDATE END)                                       AS LAST_PASTDUE_DUE,
           SUM(CASE WHEN RECEIPT_NUMBER IS NULL AND DUEDATE <= @asof
                    THEN 1 ELSE 0 END)                                      AS N_PASTDUE,
           SUM(CASE WHEN RECEIPT_NUMBER IS NULL THEN 1 ELSE 0 END)          AS N_UNPAID,
           SUM(CASE WHEN RECEIPT_NUMBER IS NULL AND DUEDATE <= @asof
                    THEN INSTALL_AMT END)                                   AS OD_AMT_CARD,
           MAX(CASE WHEN RECEIPT_NUMBER IS NULL AND DUEDATE <= @asof
                    THEN PENALTY_AMT END)                                   AS PENALTY_CARD,
           MAX(CASE WHEN RECEIPT_NUMBER IS NULL AND DUEDATE <= @asof
                    THEN COLLECT_AMT END)                                   AS COLLECT_CARD,
           MAX(CASE WHEN RECEIPT_NUMBER IS NOT NULL THEN DUEDATE END)       AS LAST_PAID_DUE
    FROM CUSTOMER_CARD
    GROUP BY CONTRACT_ID
    /* กรองหยาบ ๆ ให้เหลือเฉพาะสัญญาที่มีงวดค้างอย่างน้อย 1 งวด
       เกณฑ์จริง (>= @minod) ไปตัดสินที่ picked เพราะต้องใช้ค่าที่ agg เสร็จแล้ว */
    HAVING SUM(CASE WHEN RECEIPT_NUMBER IS NULL AND DUEDATE <= @asof
                    THEN 1 ELSE 0 END) >= 1
),

/* 2) งวดที่ทำให้ครบ OD6 = งวดค้างเกินกำหนดลำดับที่ @minod
      ใช้ลำดับจริง จึงถูกต้องแม้งวดที่ค้างไม่ติดกัน */
od6 AS (
    SELECT CONTRACT_ID, INSTALL_NUM AS OD6_INSTALL_NUM, DUEDATE AS OD6_DUEDATE
    FROM (
        SELECT CONTRACT_ID, INSTALL_NUM, DUEDATE,
               ROW_NUMBER() OVER (PARTITION BY CONTRACT_ID ORDER BY INSTALL_NUM) AS od_rank
        FROM CUSTOMER_CARD
        WHERE RECEIPT_NUMBER IS NULL AND DUEDATE <= @asof
    ) z WHERE od_rank = @minod
),

/* 3) ระบุกรณี + นับจำนวนงวดที่ค้างจริง

   กรณี 1 · สัญญายังไม่จบ  → นับงวดว่างในการ์ด
   กรณี 2 · สัญญาจบไปแล้ว  → นับ "ในสัญญา + นอกสัญญา" ถึง @asof
            สัญญาจบแล้วการ์ดไม่ออกงวดใหม่ ถ้านับแค่งวดว่างจะไม่มีวันถึง 6
            จึงนับเป็นจำนวนรอบชำระที่ผ่านไปตั้งแต่งวดแรกที่ค้าง จนถึง @asof
            เช่น งวดแรกที่ค้าง 1 มี.ค. · สัญญาจบ 1 พ.ค. · asof 31 ส.ค.
                 ในสัญญา 3 งวด (มี.ค. เม.ย. พ.ค.) + นอกสัญญา 3 (มิ.ย. ก.ค. ส.ค.) = 6

   ตัวลบ DAY(@asof) < DAY(งวดแรกที่ค้าง) กันไม่ให้นับรอบที่ยังไม่ถึงกำหนดในเดือนนั้น
   เช่น สัญญาชำระวันที่ 16 แต่ asof เป็นวันที่ 10 — รอบเดือนนั้นยังไม่ครบกำหนด */
picked AS (
    SELECT cd.*,
           CASE WHEN cd.LAST_PASTDUE_DUE >= @cut THEN 1 ELSE 2 END AS CASE_NO,
           CASE WHEN cd.CONTRACT_LAST_DUE < @asof
                THEN DATEDIFF(month, cd.FIRST_UNPAID_DUE, @asof)
                     - CASE WHEN DAY(@asof) < DAY(cd.FIRST_UNPAID_DUE) THEN 1 ELSE 0 END
                     + 1
                ELSE cd.N_PASTDUE
           END AS N_OD
    FROM card cd
)

SELECT
    /* ---------- กรณีและตัวระบุ ---------- */
      p.CASE_NO                                     AS [กรณี]
    , CASE p.CASE_NO WHEN 1 THEN N'1 · OD6 ปกติ'
                     ELSE N'2 · สัญญาหมดอายุแล้ว' END AS [ชื่อกรณี]
    , CASE WHEN DAY(p.LAST_PASTDUE_DUE) = 16 THEN N'รอบวันที่ 16'
           ELSE N'รอบวันที่ 1' END                   AS [รอบ]
    , k.PERSON_ID                                   AS [รหัสลูกค้า]
    , pr.TAX_ID                                     AS [เลขบัตรประชาชน]

    /* ---------- ตาม Template จดหมายบอกเลิก ---------- */
    , k.CONTRACT_NUMBER                             AS [สัญญาเลขที่]
    , LTRIM(RTRIM(ISNULL(pf.Prefix_name, N'') + N' '
        + ISNULL(pr.FIRST_NAME, N'') + N' '
        + ISNULL(pr.LAST_NAME, N'')))               AS [ชื่อผู้ทำสัญญา]
    , k.CONTRACT_START                              AS [วันที่ทำสัญญา]
    , N'เช่าซื้อ ' + ISNULL(cat.CATEGORY_NAME, N'') AS [ประเภทสัญญา]
    , br.BRAND_NAME                                 AS [ยี่ห้อ]
    , pd.MODEL_NAME                                 AS [รุ่น/แบบ]
    , pd.MODEL_NUMBER                               AS [เครื่อง]
    , pd.SERIAL_NUMBER                              AS [Serial Number]
    , pd.HP_VAT_SUM                                 AS [ค่าเช่าซื้อรวมภาษีมูลค่าเพิ่ม]
    , pd.INSTALL_SUM                                AS [งวดละ (บาท)]
    , pd.INSTALL_NUM                                AS [จำนวนงวดเช่าซื้อ]
    , pd.FRIST_PAY_DATE                             AS [วันเริ่มชำระงวดแรก]
    , pd.DUEDATE_NUM                                AS [วันที่ชำระงวดต่อไป]

    /* ---------- ค้างชำระงวดแรก / งวดสุดท้าย — คิดตามกรณี ---------- */
    , p.FIRST_UNPAID_NUM                            AS [ค้างชำระงวดแรก]
    , p.FIRST_UNPAID_DUE                            AS [วันครบกำหนดงวดแรกที่ค้าง]
    , CASE WHEN p.CASE_NO = 1 THEN p.LAST_PASTDUE_NUM
                              ELSE p.LAST_INSTALL_NUM   END AS [ค้างชำระงวดสุดท้าย]
    , CASE WHEN p.CASE_NO = 1 THEN p.LAST_PASTDUE_DUE
                              ELSE p.CONTRACT_LAST_DUE  END AS [วันครบกำหนดงวดสุดท้ายที่ค้าง]

    /* งวดที่ครบ OD6 = งวดค้างเกินกำหนดลำดับที่ 6 จริง */
    , COALESCE(o6.OD6_INSTALL_NUM, p.LAST_INSTALL_NUM)
                                                    AS [งวดที่ครบ OD 6]

    /* ---------- จำนวนเงิน ----------
       ⚠ ทุกช่องในบล็อกนี้คิดจาก N_PASTDUE = งวดที่มีอยู่จริงในสัญญาเท่านั้น
         ไม่ใช่ N_OD ที่รวมรอบนอกสัญญา เพราะนโยบายผูกค่าธรรมเนียมกับ "งวด"
         "ค่าปรับ 100 บาท ต่องวดที่ค้างชำระในแต่ละงวด"          [Fee Policy ข้อ 1]
         และ Case B คิดจาก k × (ค่างวด + 100) โดย k = จำนวนงวด
         งวดที่ไม่มีอยู่ในสัญญาจึงไม่มีค่างวดให้คูณ                [Fee Policy ข้อ 2]
         N_OD ใช้แค่ตัดสินว่าเข้าเกณฑ์ 6 งวดไหม และแสดงในช่องนับงวด

       ค่างวดที่ค้าง : รวมจากการ์ดผ่อนจริง
       ค่าปรับ      : 100 บาท/งวด เพดาน 600 (OD6 ขึ้นไป)            [Fee Policy ข้อ 1]
       ค่าติดตาม    : ตัดสิน A/B จาก "ยอดค้างงวดแรก" = ค่างวด + ค่าปรับ 100
                      กรณี A  ค่างวด + 100 >  1,000 → 50,150,250,350,450
                      กรณี B  ค่างวด + 100 <= 1,000 → +100 ต่อลำดับงวดที่
                              ยอดสะสม k*(ค่างวด+100) > 1,000 · นับถึง OD5 แล้วหยุด
                      [Fee Policy ข้อ 2]
       ------------------------------------------------------------------ */
    , p.OD_AMT_CARD                                 AS [ค่าเช่าซื้อที่ค้างชำระ]

    , CAST(100 * (CASE WHEN p.N_PASTDUE >= 6 THEN 6 ELSE p.N_PASTDUE END)
           AS float)                                AS [ค่าเบี้ยปรับชำระล่าช้า]

    , CAST(CASE
        WHEN p.N_PASTDUE = 0 THEN 0
        WHEN ISNULL(pd.INSTALL_SUM, 0) + 100 > 1000
             THEN CASE WHEN p.N_PASTDUE >= 5 THEN 450
                       ELSE 50 + (p.N_PASTDUE - 1) * 100 END
        ELSE 100 *
             CASE WHEN (CASE WHEN p.N_PASTDUE > 5 THEN 5 ELSE p.N_PASTDUE END)
                       - (FLOOR(1000.0 / (ISNULL(pd.INSTALL_SUM,0) + 100)) + 1) + 1 > 0
                  THEN (CASE WHEN p.N_PASTDUE > 5 THEN 5 ELSE p.N_PASTDUE END)
                       - (FLOOR(1000.0 / (ISNULL(pd.INSTALL_SUM,0) + 100)) + 1) + 1
                  ELSE 0 END
      END AS float)                                 AS [ค่าติดตามทวงถามหนี้]

    , CAST(0 AS float)                              AS [ค่าใช้จ่ายอื่นที่บริษัทฯ มีสิทธิเรียกเก็บ]

    , ISNULL(p.OD_AMT_CARD,0)
      + 100 * (CASE WHEN p.N_PASTDUE >= 6 THEN 6 ELSE p.N_PASTDUE END)
      + CASE
          WHEN p.N_PASTDUE = 0 THEN 0
          WHEN ISNULL(pd.INSTALL_SUM, 0) + 100 > 1000
               THEN CASE WHEN p.N_PASTDUE >= 5 THEN 450
                         ELSE 50 + (p.N_PASTDUE - 1) * 100 END
          ELSE 100 *
               CASE WHEN (CASE WHEN p.N_PASTDUE > 5 THEN 5 ELSE p.N_PASTDUE END)
                         - (FLOOR(1000.0 / (ISNULL(pd.INSTALL_SUM,0) + 100)) + 1) + 1 > 0
                    THEN (CASE WHEN p.N_PASTDUE > 5 THEN 5 ELSE p.N_PASTDUE END)
                         - (FLOOR(1000.0 / (ISNULL(pd.INSTALL_SUM,0) + 100)) + 1) + 1
                    ELSE 0 END
        END                                         AS [รวมเป็นเงินทั้งสิ้น]

    /* วันที่เป็น OD6 = วันถัดจากวันครบกำหนดของงวดค้างลำดับที่ 6
       สิทธิ์บอกเลิกเกิดในวันถัดจากวันครบกำหนด เพราะวันครบกำหนดลูกค้ายังชำระได้
         งวดครบกำหนด 01/09/2026 → เป็น OD6 วันที่ 02/09/2026
         งวดครบกำหนด 16/09/2026 → เป็น OD6 วันที่ 17/09/2026

       เคสหมดสัญญา (งวดที่ 6 ไม่มีอยู่จริงในการ์ด)
         นับเป็นวันที่ครบ 6 รอบชำระ = งวดแรกที่ค้าง + 5 เดือน แล้ว +1 วัน
         ไม่ใช่วันสิ้นสุดสัญญา เพราะสัญญาจบไปก่อนที่จะครบ 6 งวด
         ใช้สูตรเดียวกับที่กรอง @newonly ข้างล่าง จึงตรงกันเสมอ */
    , DATEADD(day, 1,
        COALESCE(o6.OD6_DUEDATE,
                 DATEADD(month, @minod - 1, p.FIRST_UNPAID_DUE))
      )                                             AS [วันที่เป็น OD6]

    /* ⚠ จำนวนงวดที่ค้าง = งวดจริงในสัญญาเท่านั้น (ไม่ใช่ N_OD)
       เคสหมดสัญญานับถึงแค่เดือนสุดท้ายที่หมดสัญญา
       N_OD ที่รวมรอบนอกสัญญาใช้แค่ตัดสินว่าเข้าเกณฑ์ 6 งวดไหม ไม่เอาไปแสดง */
    , p.N_PASTDUE                                   AS [รวมจำนวนงวดที่ค้าง]

    /* ---------- ที่อยู่ตามทะเบียนบ้าน ---------- */
    , LTRIM(RTRIM(
        CASE WHEN NULLIF(LTRIM(RTRIM(a.A1_NO)),N'')       IS NULL THEN N'' ELSE N'เลขที่ ' + a.A1_NO + N' ' END
      + CASE WHEN NULLIF(LTRIM(RTRIM(a.A1_MOI)),N'')      IS NULL THEN N'' ELSE N'หมู่ที่ ' + a.A1_MOI + N' ' END
      + CASE WHEN NULLIF(LTRIM(RTRIM(a.A1_VILLAGE)),N'')  IS NULL THEN N'' ELSE N'หมู่บ้าน/โครงการ ' + a.A1_VILLAGE + N' ' END
      + CASE WHEN NULLIF(LTRIM(RTRIM(a.A1_BUILDING)),N'') IS NULL THEN N'' ELSE N'อาคาร ' + a.A1_BUILDING + N' ' END
      + CASE WHEN NULLIF(LTRIM(RTRIM(a.A1_FLOOR)),N'')    IS NULL THEN N'' ELSE N'ชั้น ' + a.A1_FLOOR + N' ' END
      + CASE WHEN NULLIF(LTRIM(RTRIM(a.A1_ROOM_NO)),N'')  IS NULL THEN N'' ELSE N'เลขที่ห้อง ' + a.A1_ROOM_NO + N' ' END
      + CASE WHEN NULLIF(LTRIM(RTRIM(a.A1_SOI)),N'')      IS NULL THEN N'' ELSE N'ซอย ' + a.A1_SOI + N' ' END
      + CASE WHEN NULLIF(LTRIM(RTRIM(a.A1_ROAD)),N'')     IS NULL THEN N'' ELSE N'ถนน ' + a.A1_ROAD + N' ' END
      ))                                            AS [เลขที่]
    , LTRIM(RTRIM(ISNULL(N'ตำบล' + sd.SUB_DISTRICT_NAME, N'') + N' '
                + ISNULL(N'อำเภอ' + di.DISTRICT_NAME, N''))) AS [แขวง/ตำบล/อำเภอ]
    , pv.PROVINCE_NAME                              AS [จังหวัด]
    , a.A1_POSTALCODE                               AS [รหัส ปณ.]

    /* ---------- คอลัมน์ตรวจสอบ ---------- */
    , p.N_CARD                                      AS _งวดทั้งหมดในการ์ด
    , p.FIRST_DUE                                   AS _งวดแรกครบกำหนด
    , p.CONTRACT_LAST_DUE                           AS _สัญญาสิ้นสุด
    , p.LAST_PAID_DUE                               AS _จ่ายล่าสุดถึงงวดวันที่
    , pay.LAST_REPAY_DATE                           AS _เงินเข้าจริงล่าสุดเมื่อ
    , pay.PAID_AFTER_CUT                            AS _งวดที่จ่ายหลังต้นเดือน
    , p.N_UNPAID                                    AS _งวดที่ยังไม่จ่ายทั้งหมด
    , p.N_UNPAID - p.N_PASTDUE                      AS _งวดที่ยังไม่ถึงกำหนด
    , p.N_PASTDUE                                   AS _งวดค้างที่อยู่ในสัญญา
    , p.N_OD - p.N_PASTDUE                          AS _รอบค้างนอกสัญญา
    , ISNULL(p.PENALTY_CARD, 0)                     AS _ค่าปรับที่ระบบคิดไว้ในการ์ด
    , ISNULL(p.COLLECT_CARD, 0)                     AS _ค่าติดตามที่ระบบคิดไว้ในการ์ด
    , o6.OD6_DUEDATE                                AS _วันครบกำหนดของงวดลำดับที่6
    , pd.INSTALL_SUM                                AS _ค่างวดใช้ตัดสินกรณี_A_B
    , k.STATUS_ID                                   AS _รหัสสถานะสัญญา
    , st.STA_NAME                                   AS _สถานะสัญญา

    /* COLLECTION_OD เก็บไว้เทียบอย่างเดียว — ไม่ได้ใช้คัดแล้ว */
    , od.EXTRACT_DATE                               AS _snapshot_ล่าสุด
    , od.CONTRACT_STATUS                            AS _สถานะใน_snapshot
    , TRY_CAST(od.NUMBER_OF_OD_INSTALLMENT AS int)  AS _ระบบนับกี่งวด
    , od.OD_AMOUNT                                  AS _ยอดค้างจาก_snapshot
    , p.OD_AMT_CARD - ISNULL(od.OD_AMOUNT,0)        AS _ผลต่างการ์ด_ลบ_snapshot

FROM       picked          p
JOIN       CONTRACT        k  ON k.CONTRACT_ID    = p.CONTRACT_ID
LEFT JOIN  od6             o6 ON o6.CONTRACT_ID   = p.CONTRACT_ID
JOIN       PERSON          pr ON pr.PERSON_ID     = k.PERSON_ID
LEFT JOIN  MT_STATUS       st ON st.HP_STA_ID     = k.STATUS_ID
LEFT JOIN  MT_PREFIX       pf ON pf.Prefix_ID     = TRY_CAST(pr.PREFIX AS int)
LEFT JOIN  PRODUCT         pd ON pd.PRODUCT_ID    = k.PRODUDCT_ID
LEFT JOIN  MT_BRAND        br ON br.BRAND_ID      = TRY_CAST(pd.PRODUCT_BAND AS int)
LEFT JOIN  MT_CATEGORY     cat ON cat.CATEGORY_ID = TRY_CAST(pd.PRODUCT_CATEGORY AS int)
LEFT JOIN  ADDRESS         a  ON a.PERSON_ID      = k.PERSON_ID
LEFT JOIN  MT_PROVINCE     pv ON pv.PROVINCE_ID   = TRY_CAST(a.A1_PROVINCE AS int)
LEFT JOIN  MT_DISTRICT     di ON di.DISTRICT_ID   = TRY_CAST(a.A1_DISTRICT AS int)
LEFT JOIN  MT_SUB_DISTRICT sd ON sd.SUB_DISTRICT_ID = TRY_CAST(a.A1_SUBDISTRICT AS int)
/* วันที่เงินเข้าจริงล่าสุด — การ์ดบอกไม่ได้ว่าจ่ายเมื่อไหร่ ต้องดูจาก REPAYMENT
   REPAY_TYPE = 2 ค่างวดเช่าซื้อ · STATUS_ID = 33 จ่ายแล้ว · REPAY_DATE = วันเงินเข้าจริง
   ใช้เช็คก่อนส่งหนังสือว่าลูกค้าเพิ่งจ่ายเข้ามาหรือเปล่า            [K2 - Payment & Invoice] */
OUTER APPLY (
    SELECT LAST_REPAY_DATE = MAX(rp.REPAY_DATE),
           PAID_AFTER_CUT  = SUM(CASE WHEN rp.REPAY_DATE >= @cut THEN 1 ELSE 0 END)
    FROM REPAYMENT rp
    WHERE rp.CONTRACT_ID = p.CONTRACT_ID
      AND rp.REPAY_TYPE = 2 AND rp.STATUS_ID = 33
) pay
OUTER APPLY (
    SELECT TOP 1 o.EXTRACT_DATE, o.CONTRACT_STATUS, o.NUMBER_OF_OD_INSTALLMENT, o.OD_AMOUNT
    FROM COLLECTION_OD o
    WHERE o.CONTRACT_ID = p.CONTRACT_ID AND o.EXTRACT_DATE <= @asof
    ORDER BY o.EXTRACT_DATE DESC
) od

/* ตัดสัญญาที่จบไปแล้ว — ออกหนังสือบอกเลิกซ้ำไม่ได้
   40 Close Contract · 49 Cancel Contract · 53 ปิดบัญชีล่วงหน้า
   54 บอกเลิกสัญญาแล้ว · 56 ขายหนี้ · 62/63 Write Off            [MT_STATUS] */
WHERE ISNULL(k.STATUS_ID, 0) NOT IN (40, 49, 53, 54, 56, 62, 63)
  AND p.N_OD >= @minod

  /* เอาเฉพาะคนที่ "ครบ OD6 ในรอบเดือนนี้" — ไม่เอาคนที่ครบมาตั้งแต่รอบก่อน ๆ
     คนที่ครบเดือนก่อนต้องอยู่ในรายชื่อของเดือนนั้นไปแล้ว ส่งซ้ำไม่ได้
     ตัวนี้กันสัญญาที่ตายไปนานแล้วไม่ให้ไหลกลับเข้ามาจากการนับรอบนอกสัญญา */
  AND ( @newonly = 0
        OR ( COALESCE(o6.OD6_DUEDATE,
                      DATEADD(month, @minod - 1, p.FIRST_UNPAID_DUE)) >= @cut
         AND COALESCE(o6.OD6_DUEDATE,
                      DATEADD(month, @minod - 1, p.FIRST_UNPAID_DUE)) <  DATEADD(month, 1, @cut) ) )

  AND (@round = 0 OR DAY(p.LAST_PASTDUE_DUE) = @round)

ORDER BY p.CASE_NO, p.N_OD DESC, k.CONTRACT_NUMBER;
