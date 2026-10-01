DECLARE @from date = '2025-01-01';
DECLARE @to   date = '2026-08-31';

WITH item AS (          
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
      AND   bb.SysCompanyId = a.CompanyCode      
      AND   bb.rn           = 1

LEFT JOIN   syndpdev001.dbo.tm_FinDimValueSet cc WITH (NOLOCK)
       ON   cc.FinancialDim = bb.DefaultDimension
      AND   cc.SysSourceRef = 'FO'              

WHERE       a.CompanyCode      IN ('com7','dou7','bnn')
  AND       a.INVENTLOCATIONID IN ('4','77','72006','72008','79006')
  AND       a.DATEPHYSICAL     >= @from
  AND       a.DATEPHYSICAL      < DATEADD(day, 1, @to)   
  AND       a.REFERENCECATEGORY <> 7             

GROUP BY    a.CompanyCode, cc.GroupCategoryName, cc.CategoryName, cc.SubCategoryName
ORDER BY    a.CompanyCode, Amount DESC;
