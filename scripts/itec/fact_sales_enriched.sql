/* =============================================================================
   fact_sales_enriched — T-SQL บน ITEC-MIS (SQL Server 2025 · compat 170)

   แปลงจาก Glue job บน AWS (เลิกใช้ 2026-11) ตรรกะเหมือนเดิมทุกขั้น
     etl-bronze-to-silver-itec-item + etl-silver-to-gold-dim-item  → ci.dim_item
     etl-dms-dim-branch-to-gold                                    → ci.dim_branch
     etl-dms-fact-sales-to-gold                                    → ci.fact_sales_enriched
   ต้นทาง: rpt.dim_item_itec · rpt.dim_branch_itec · rpt.fact_sales_itec (ตัวเดียวกับที่ DMS เคยดึง)
   เวอร์ชัน Python ที่ให้ผลเหมือนกัน → scripts/itec/fact_sales_enriched.py

   ข้อควรรู้
   - ใช้ REGEXP_LIKE / REGEXP_REPLACE (มีตั้งแต่ SQL Server 2025) — regex แยกตัวพิมพ์เล็กใหญ่เหมือน Spark
   - ฐานนี้ collation Thai_CI_AS (ไม่แยกตัวพิมพ์) แต่ Spark แยก → จุดที่เทียบค่าดิบ/join ใช้ COLLATE Thai_BIN2
   - ต้นทางมีราคาผิดปกติ เช่น SOCIALCARE001 ต.ค. 2026 = 830,510 ล้านบาท 1 แถว
     ไม่กรองทิ้ง (ให้ตรงกับของเดิม) — ตอนรวมยอดควรกันแถว ABS(sale_amt) > 1,000,000 ไว้ตรวจก่อน
   - ส่วนที่ 1–3 เป็น VIEW (ข้อมูลสดเสมอ) · ส่วนที่ 4 (ไม่บังคับ) เก็บ fact เป็นตารางรายเดือนให้ query เร็วขึ้น
   ============================================================================= */


/* -----------------------------------------------------------------------------
   1. ci.dim_item — 1 แถวต่อ item_id (silver: ทำความสะอาด + สถานะ · gold: brand / department / category)
   ----------------------------------------------------------------------------- */
CREATE OR ALTER VIEW ci.dim_item
AS
WITH src AS (            -- trim ทุกคอลัมน์ และ 'NULL' (ตัวใหญ่เท่านั้น เหมือน Spark) → null
    SELECT IIF(TRIM(ItemId)          COLLATE Thai_BIN2 = 'NULL', NULL, TRIM(ItemId))          AS item_id,
           IIF(TRIM(ItemName)        COLLATE Thai_BIN2 = 'NULL', NULL, TRIM(ItemName))        AS item_name,
           IIF(TRIM(CategoryName)    COLLATE Thai_BIN2 = 'NULL', NULL, TRIM(CategoryName))    AS category_name,
           IIF(TRIM(SubCategoryName) COLLATE Thai_BIN2 = 'NULL', NULL, TRIM(SubCategoryName)) AS sub_category_name,
           IIF(TRIM([Model/Series])  COLLATE Thai_BIN2 = 'NULL', NULL, TRIM([Model/Series]))  AS model_series,
           IIF(TRIM(Brand)           COLLATE Thai_BIN2 = 'NULL', NULL, TRIM(Brand))           AS brand
    FROM rpt.dim_item_itec
),
flags AS (
    SELECT s.*,
           REGEXP_REPLACE(UPPER(TRIM(s.brand)), '\s+', ' ')         AS brand_clean,
           REGEXP_REPLACE(s.item_id, '(D7|-FA|-D|D)$', '')           AS base_item_id,   -- ตัด suffix demo / FA
           CASE WHEN REGEXP_LIKE(s.item_id, '["\s]') THEN 0
                WHEN LEN(s.item_id) < 3 THEN 0
                WHEN REGEXP_LIKE(CAST(s.item_id AS nvarchar(200)), N'[' + NCHAR(3584) + N'-' + NCHAR(3711) + N']') THEN 0  -- อักษรไทย
                ELSE 1 END                                               AS is_valid_item_id,
           CASE WHEN REGEXP_LIKE(s.item_name, '^D7@') OR REGEXP_LIKE(s.category_name, 'Demo') THEN 1 ELSE 0 END AS is_demo,
           CASE WHEN s.category_name COLLATE Thai_BIN2 IN ('Service', 'Smile')
                  OR REGEXP_REPLACE(UPPER(TRIM(s.brand)), '\s+', ' ') = 'SERVICE' THEN 1 ELSE 0 END             AS is_service,
           CASE WHEN s.category_name COLLATE Thai_BIN2 IN ('Promo Operator', 'Reserve') THEN 1 ELSE 0 END      AS is_promo
    FROM src s
),
silver AS (
    SELECT f.*,
           CASE WHEN is_demo = 1 THEN 'DEMO' WHEN is_service = 1 THEN 'SERVICE'
                WHEN is_promo = 1 THEN 'PROMO' ELSE 'ACTIVE' END        AS product_status,
           UPPER(TRIM(category_name))                                    AS category_clean,
           UPPER(TRIM(sub_category_name))                                AS sub_category_clean,
           REGEXP_REPLACE(item_name, '^D7@ ?', '')                       AS item_name_clean,
           -- dedup: ACTIVE > DEMO > SERVICE > PROMO แล้วเลือกแถวที่ข้อมูลครบกว่า
           ROW_NUMBER() OVER (
               PARTITION BY item_id COLLATE Thai_BIN2
               ORDER BY CASE WHEN is_demo = 1 THEN 2 WHEN is_service = 1 THEN 3 WHEN is_promo = 1 THEN 4 ELSE 1 END,
                        IIF(brand IS NULL, 0, 1) + IIF(model_series IS NULL, 0, 1)
                      + IIF(category_name IS NULL, 0, 1) + IIF(sub_category_name IS NULL, 0, 1) DESC
           ) AS rn
    FROM flags f
),
brand AS (
    SELECT s.*,
           CASE
             WHEN brand_clean IN ('APPLE', 'APPLE SERVICE') OR REGEXP_LIKE(brand_clean, '^TRUE.IPHONE|^TRUE.IPAD') THEN 'Apple'
             WHEN brand_clean IN ('SAMSUNG', 'TRUE-SAMSUNG', 'TRUE_SAMSUNG') THEN 'Samsung'
             WHEN brand_clean IN ('XIAOMI', 'TRUE-XIAOMI', 'TRUE_XIAOMI') THEN 'Xiaomi'
             WHEN brand_clean IN ('OPPO', 'TRUE-OPPO', 'TRUE_OPPO') THEN 'Oppo'
             WHEN brand_clean IN ('VIVO', 'TRUE-VIVO', 'TRUE_VIVO') THEN 'Vivo'
             WHEN brand_clean IN ('REALME', 'TRUE-REALME', 'TRUE_REALME') THEN 'Realme'
             WHEN brand_clean IN ('HUAWEI', 'TRUE-HUAWEI', 'TRUE_HUAWEI') THEN 'Huawei'
             WHEN brand_clean IN ('HONOR', 'TRUE-HONOR') THEN 'Honor'
             WHEN brand_clean IN ('HP', 'HYPER X') THEN 'HP'
             WHEN brand_clean = 'ASUS' THEN 'Asus'
             WHEN brand_clean = 'ACER' THEN 'Acer'
             WHEN brand_clean = 'LENOVO' THEN 'Lenovo'
             WHEN brand_clean = 'DELL' THEN 'Dell'
             WHEN brand_clean = 'MSI' THEN 'MSI'
             WHEN brand_clean = 'GIGABYTE' THEN 'Gigabyte'
             WHEN brand_clean = 'SONY' THEN 'Sony'
             WHEN brand_clean = 'LG' THEN 'LG'
             WHEN brand_clean = 'MICROSOFT' THEN 'Microsoft'
             WHEN brand_clean = 'INTEL' THEN 'Intel'
             WHEN brand_clean = 'LOGITECH' THEN 'Logitech'
             WHEN brand_clean = 'JBL' THEN 'JBL'
             WHEN brand_clean = 'CORSAIR' THEN 'Corsair'
             WHEN brand_clean = 'KINGSTON' THEN 'Kingston'
             WHEN brand_clean = 'WESTERN' THEN 'Western Digital'
             WHEN brand_clean = 'TOSHIBA' THEN 'Toshiba'
             WHEN brand_clean = 'PHILIPS' THEN 'Philips'
             WHEN brand_clean = 'BELKIN' THEN 'Belkin'
             WHEN brand_clean = 'FOX' THEN 'Fox'
             WHEN brand_clean = 'ANITECH' THEN 'Anitech'
             WHEN brand_clean = 'ELECOM' THEN 'Elecom'
             WHEN brand_clean IN ('NEOLUTION', 'NUBWO') THEN 'Neolution'
             WHEN brand_clean = 'KING KONG' THEN 'King Kong'
             WHEN brand_clean = 'CASE CLUB' THEN 'Case Club'
             WHEN brand_clean = 'TECHPRO' THEN 'TechPro'
             WHEN brand_clean IN ('TRUEMOVE', 'TRUE', 'TRUEMOVEH') THEN 'TrueMove'
             WHEN brand_clean = 'AIS' THEN 'AIS'
             WHEN brand_clean = 'DTAC' THEN 'DTAC'
             WHEN brand_clean = 'COM7' THEN 'COM7'
             WHEN brand_clean IN ('NULL', '-', 'XX', 'OTHER') OR brand_clean IS NULL THEN 'Unknown'
             ELSE brand_clean
           END AS brand_std
    FROM silver s
    WHERE rn = 1
)
SELECT
    item_id,
    base_item_id,
    item_name_clean AS item_name,
    CASE
      WHEN category_clean IN ('NOTEBOOK', 'PREMIUM NOTEBOOK', 'DESKTOP', 'MAC') THEN 'Computing'
      WHEN category_clean IN ('GRAPHIC CARD', 'MAINBOARD', 'CPU', 'RAM FOR PC', 'COMPUTER CASES', 'COOLING SYSTEM',
                              'POWER SUPPLY', 'INTERNAL HARDDRIVE', 'SOLID STATE DRIVE INTERNAL (SSD)', 'OPTICAL DRIVE',
                              'FLASH DRIVE AND MEMORY CARD') THEN 'PC Components'
      WHEN category_clean IN ('SMARTPHONE', 'PREMIUM SMARTPHONE', 'IPHONE') THEN 'Mobile'
      WHEN category_clean IN ('IPAD', 'TABLET SMARTPHONE') THEN 'Tablet'
      WHEN category_clean IN ('HEADPHONE', 'SPEAKER', 'AUDIO & VISUAL') THEN 'Audio'
      WHEN category_clean IN ('GAMING GEAR', 'CONSOLE AND GAMING GADGET') THEN 'Gaming'
      WHEN category_clean IN ('MONITOR', 'PRINTER', 'NETWORK', 'SOFTWARE') THEN 'Peripherals'
      WHEN category_clean IN ('CASES', 'BEBEPHONE', 'SMARTPHONE ACC', 'FILM FOR MOBILE AND TABLET', 'MOBILE CABLE', 'BAG',
                              'CASE CLUB', 'APPLE CASE & PROTECTION', 'APPLE ACC FOR WATCH', 'APPLE') THEN 'Accessories'
      WHEN category_clean IN ('MOUSE & KEYBOARDS', 'KEYBOARD', 'IT ACCESSORIES', 'ADAPTER', 'POWER BANK',
                              'EXTERNAL HARDDRIVE') THEN 'IT Accessories'
      WHEN category_clean IN ('CAMERA', 'SMARTWATCH', 'APPLE WATCH', 'GADGET', 'SMART LIVING', 'XIAOMI ECO',
                              'SMALL APPLIANCE', 'HOME APPLIANCE', 'HEALTH & SPORT', 'OUTDOOR ACTIVITIES') THEN 'Lifestyle & IoT'
      ELSE 'Other'
    END AS department,
    CASE
      WHEN category_clean IN ('NOTEBOOK', 'PREMIUM NOTEBOOK') THEN 'Notebook'
      WHEN category_clean = 'DESKTOP' THEN 'Desktop'
      WHEN category_clean = 'MAC' THEN 'Mac'
      WHEN category_clean IN ('SMARTPHONE', 'PREMIUM SMARTPHONE') THEN 'Smartphone'
      WHEN category_clean = 'IPHONE' THEN 'iPhone'
      WHEN category_clean = 'IPAD' THEN 'iPad'
      WHEN category_clean = 'TABLET SMARTPHONE' THEN 'Tablet'
      WHEN category_clean = 'HEADPHONE' THEN 'Headphone'
      WHEN category_clean = 'SPEAKER' THEN 'Speaker'
      WHEN category_clean = 'AUDIO & VISUAL' THEN 'Audio & Visual'
      WHEN category_clean = 'GAMING GEAR' THEN 'Gaming Gear'
      WHEN category_clean = 'CONSOLE AND GAMING GADGET' THEN 'Console & Gaming'
      WHEN category_clean = 'MONITOR' THEN 'Monitor'
      WHEN category_clean = 'PRINTER' THEN 'Printer'
      WHEN category_clean = 'NETWORK' THEN 'Network'
      WHEN category_clean = 'CAMERA' THEN 'Camera'
      WHEN category_clean IN ('SMARTWATCH', 'APPLE WATCH') THEN 'Smartwatch'
      WHEN category_clean IN ('CASES', 'BEBEPHONE', 'CASE CLUB', 'APPLE CASE & PROTECTION') THEN 'Phone Case'
      WHEN category_clean IN ('SMARTPHONE ACC', 'FILM FOR MOBILE AND TABLET', 'MOBILE CABLE') THEN 'Phone Accessories'
      WHEN category_clean IN ('MOUSE & KEYBOARDS', 'KEYBOARD') THEN 'Mouse & Keyboard'
      WHEN category_clean IN ('GRAPHIC CARD', 'MAINBOARD', 'CPU', 'RAM FOR PC') THEN 'PC Core Components'
      WHEN category_clean IN ('COMPUTER CASES', 'COOLING SYSTEM', 'POWER SUPPLY') THEN 'PC Case & Cooling'
      WHEN category_clean IN ('INTERNAL HARDDRIVE', 'EXTERNAL HARDDRIVE', 'SOLID STATE DRIVE INTERNAL (SSD)',
                              'FLASH DRIVE AND MEMORY CARD') THEN 'Storage'
      WHEN category_clean IN ('POWER BANK', 'ADAPTER') THEN 'Power & Charging'
      WHEN category_clean IN ('XIAOMI ECO', 'SMART LIVING', 'GADGET') THEN 'Smart Living'
      WHEN category_clean IN ('SMALL APPLIANCE', 'HOME APPLIANCE') THEN 'Home Appliance'
      WHEN category_clean = 'BAG' THEN 'Bag'
      WHEN category_clean = 'SOFTWARE' THEN 'Software'
      ELSE category_clean
    END AS category,
    sub_category_clean AS sub_category,
    model_series,
    brand_std AS brand,
    CASE
      WHEN brand_std IN ('Apple', 'Samsung', 'HP', 'Lenovo', 'Dell', 'Asus', 'Acer', 'Xiaomi') THEN brand_std
      WHEN brand_std IN ('Sony', 'JBL') THEN 'Sony'
      WHEN brand_std IN ('Oppo', 'Realme', 'Vivo') THEN 'BBK Electronics'
      WHEN brand_std IN ('TrueMove', 'AIS', 'DTAC') THEN 'Telco'
      ELSE 'Other'
    END AS brand_group,
    product_status,
    CAST(is_valid_item_id AS bit) AS is_valid_item_id
FROM brand;
GO


/* -----------------------------------------------------------------------------
   2. ci.dim_branch — 1 แถวต่อ branch_id · BranchType ใช้เป็น channel (รูปแบบร้าน / แบรนด์ร้าน)
   ----------------------------------------------------------------------------- */
CREATE OR ALTER VIEW ci.dim_branch
AS
WITH src AS (
    SELECT TRY_CAST(Branch AS int)          AS branch_id,
           NULLIF(TRIM(BranchName), '')     AS branch_name,
           NULLIF(TRIM(Region), '')         AS region,
           CASE WHEN TRIM(Province) IN (N'กรุงเทพฯ', N'กรุงเทพ', N'กรุงเทพมหานคร') THEN 'Bangkok'
                ELSE NULLIF(TRIM(Province), '') END AS province,   -- รวมกรุงเทพที่สะกดหลายแบบ
           NULLIF(TRIM(BranchType), '')     AS channel
    FROM rpt.dim_branch_itec
),
ranked AS (
    SELECT s.*,
           ROW_NUMBER() OVER (
               PARTITION BY branch_id
               ORDER BY IIF(branch_name IS NULL, 0, 1) + IIF(region IS NULL, 0, 1)
                      + IIF(province IS NULL, 0, 1) + IIF(channel IS NULL, 0, 1) DESC,
                        IIF(branch_name IS NULL, 1, 0), branch_name
           ) AS rn
    FROM src s
)
SELECT branch_id, branch_name, region, province, channel
FROM ranked
WHERE rn = 1;
GO


/* -----------------------------------------------------------------------------
   3. ci.fact_sales_enriched — 1 แถว = 1 รายการขาย · join สินค้า + สาขา (LEFT — ไม่ทิ้งยอดขาย)
      กรองช่วงเวลาด้วย sales_datetime เสมอ ข้อมูลทั้งหมด ~80 ล้านแถว
   ----------------------------------------------------------------------------- */
CREATE OR ALTER VIEW ci.fact_sales_enriched
AS
WITH f AS (
    SELECT SalesId                              AS sales_id,
           SalesBranch                          AS branch_id,
           TRIM(ItemId)                         AS product_id,
           SerialNo                             AS serial_no,
           SalesQty                             AS sales_qty,
           SalesAmount                          AS sale_dec,
           CostAmount                           AS cost_dec,
           CAST(GPAmount AS float)              AS gp_amt,
           CAST([GP %] AS float)                AS gp_pct,
           Status                               AS status,
           SalesCrDatetime                      AS sales_datetime,
           SalesOfficerId                       AS sales_officer_id
    FROM rpt.fact_sales_itec
)
SELECT
    -- Transaction
    f.sales_id,
    f.sales_datetime,
    CAST(f.sales_datetime AS date)               AS sale_date,
    EOMONTH(f.sales_datetime)                    AS end_month_date,
    YEAR(f.sales_datetime)                       AS sale_year,
    MONTH(f.sales_datetime)                      AS sale_month,
    -- Branch
    f.branch_id, b.branch_name, b.region, b.province, b.channel,
    -- Product
    f.product_id, f.serial_no, i.item_name, i.brand, i.brand_group, i.department, i.category, i.sub_category,
    -- Sales officer
    f.sales_officer_id,
    -- Measures
    f.sales_qty,
    CAST(f.cost_dec AS float)                    AS cost_amt,
    CAST(f.sale_dec AS float)                    AS sale_amt,
    f.gp_amt,
    f.gp_pct,
    CAST(ROUND(f.sale_dec - f.cost_dec, 2) AS float) AS margin_amt,
    -- margin_pct: ยอดขาย 0 และทุน 0 = 0% จริง · ยอดขาย 0 แต่มีทุน = ไม่มีตัวหาร → NULL · ทุน NULL → NULL
    CAST(CASE WHEN f.sale_dec <> 0 THEN ROUND((f.sale_dec - f.cost_dec) / f.sale_dec * 100, 2)
              WHEN f.sale_dec = 0 AND f.cost_dec = 0 THEN 0
         END AS float)                           AS margin_pct,
    f.status,
    -- Flags
    CAST(IIF(f.sales_qty < 0 OR f.sale_dec < 0, 1, 0) AS bit)                        AS is_return,
    CAST(IIF(f.sale_dec = 0 AND f.sales_qty > 0, 1, 0) AS bit)                        AS is_zero_revenue,
    -- ขาดทุนวัดจาก margin_amt หลังปัด 2 ตำแหน่ง (เหมือนของเดิม: -0.001 ไม่นับว่าขาดทุน)
    CAST(IIF(ROUND(f.sale_dec - f.cost_dec, 2) < 0 AND f.sale_dec > 0
             AND NOT (f.sales_qty < 0 OR f.sale_dec < 0), 1, 0) AS bit)               AS is_negative_margin
FROM f
LEFT JOIN ci.dim_item   i ON i.item_id = f.product_id COLLATE Thai_BIN2
LEFT JOIN ci.dim_branch b ON b.branch_id = f.branch_id;
GO


/* -----------------------------------------------------------------------------
   ตัวอย่างใช้งาน
   ----------------------------------------------------------------------------- */
-- ยอดรายเดือนตาม department (กันรายการราคาผิดปกติออก)
-- SELECT sale_year, sale_month, department, SUM(sale_amt) AS sale, SUM(margin_amt) AS margin
-- FROM ci.fact_sales_enriched
-- WHERE sales_datetime >= '2026-01-01' AND sales_datetime < '2026-11-01' AND ABS(sale_amt) <= 1000000
-- GROUP BY sale_year, sale_month, department;


/* -----------------------------------------------------------------------------
   4. (ไม่บังคับ) เก็บ fact เป็นตาราง — query เร็วกว่า view มาก · รันทับทีละเดือน
      EXEC ci.load_fact_sales_enriched '2023-01-01', '2026-12-01';   -- โหลดครั้งแรก (~47 เดือน)
      EXEC ci.load_fact_sales_enriched;                               -- ค่าเริ่มต้น: เดือนก่อน + เดือนนี้ (รอบประจำวัน)
   ----------------------------------------------------------------------------- */
IF OBJECT_ID('ci.fact_sales_enriched_tbl', 'U') IS NULL
BEGIN
    SELECT TOP (0) * INTO ci.fact_sales_enriched_tbl FROM ci.fact_sales_enriched;
    CREATE CLUSTERED INDEX cix_fact_sales_enriched ON ci.fact_sales_enriched_tbl (sale_year, sale_month, sales_datetime);
END;
GO

CREATE OR ALTER PROCEDURE ci.load_fact_sales_enriched
    @since date = NULL,   -- วันแรกของเดือนแรก (ค่าเริ่มต้น = ต้นเดือนที่แล้ว)
    @until date = NULL    -- ไม่รวมวันนี้ (ค่าเริ่มต้น = ต้นเดือนหน้า)
AS
BEGIN
    SET NOCOUNT ON;
    SET @since = DATEFROMPARTS(YEAR(COALESCE(@since, DATEADD(month, -1, GETDATE()))),
                               MONTH(COALESCE(@since, DATEADD(month, -1, GETDATE()))), 1);
    SET @until = COALESCE(@until, DATEADD(day, 1, EOMONTH(GETDATE())));

    -- dim ซ้ำ = ยอดเบิ้ล → หยุดก่อนเขียน
    IF EXISTS (SELECT item_id COLLATE Thai_BIN2 FROM ci.dim_item GROUP BY item_id COLLATE Thai_BIN2 HAVING COUNT(*) > 1)
        THROW 50001, 'ci.dim_item has duplicate item_id', 1;
    IF EXISTS (SELECT branch_id FROM ci.dim_branch GROUP BY branch_id HAVING COUNT(*) > 1)
        THROW 50002, 'ci.dim_branch has duplicate branch_id', 1;

    DECLARE @m date = @since, @next date, @expected bigint, @loaded bigint;
    WHILE @m < @until
    BEGIN
        SET @next = DATEADD(month, 1, @m);
        SELECT @expected = COUNT_BIG(*) FROM rpt.fact_sales_itec WHERE SalesCrDatetime >= @m AND SalesCrDatetime < @next;

        BEGIN TRAN;
            DELETE FROM ci.fact_sales_enriched_tbl WHERE sale_year = YEAR(@m) AND sale_month = MONTH(@m);
            INSERT INTO ci.fact_sales_enriched_tbl WITH (TABLOCK)
            SELECT * FROM ci.fact_sales_enriched WHERE sales_datetime >= @m AND sales_datetime < @next;
            SET @loaded = @@ROWCOUNT;
            IF @loaded <> @expected
            BEGIN
                ROLLBACK;   -- อ่านไม่ครบหรือ join เบิ้ล → คงข้อมูลเดิมของเดือนนั้นไว้
                DECLARE @msg nvarchar(200) = CONCAT('row count mismatch ', FORMAT(@m, 'yyyy-MM'), ': source ', @expected, ', loaded ', @loaded);
                THROW 50003, @msg, 1;
            END;
        COMMIT;

        PRINT CONCAT(FORMAT(@m, 'yyyy-MM'), '  rows ', @loaded);
        SET @m = @next;
    END;
END;
GO
