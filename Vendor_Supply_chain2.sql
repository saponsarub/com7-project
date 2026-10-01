SELECT 
a.CompanyCode
,p.[VendorName]
,cast(sum(case when a.QTY >= 0 Then a.QTY Else 0 end)as decimal(15,2)) as 'Inbond (Sum)'
  FROM [syndpdev001].[dbo].[tb_PurchOrder] p
  Left join [PROJECT_1].[dbo].[Transaction_FO] a on a.[Ref.DocNum] = p.PurchId and a.CompanyCode = p.SysCompanyId and a.[FO-ITEMNO] = p.ItemId 
  where   a.CompanyCode in ('com7','dou7','bnn') and 
  a.INVENTLOCATIONID in ('4','77','72006','72008','79006') and 
  a.DATEPHYSICAL between '2025-01-01' and '2026-08-31' 
  Group by a.CompanyCode ,p.[VendorName]
  order by a.CompanyCode,p.[VendorName]

