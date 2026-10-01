SELECT 
YEAR(a.DATEPHYSICAL) as 'YEAR'
,MONTH(a.DATEPHYSICAL) as 'MONTH'
,d.name as 'VendorName'
,case when a.companycode = 'com7' then 'COMSEVEN'
	  when a.companycode = 'bnn'  then 'ADEPT'
	  when a.companycode  = 'dou7' then 'DOUBLESEVEN'
	  ELSE '' END AS 'Company'
	  ,substring(w.Name,charindex(':',w.Name)+1,len(w.Name)) as 'WarehouseName'
	  ,COUNT(DISTINCT a.[Ref.DocNum])  as 'Trans_PO'
,cast(sum(case when a.QTY >= 0 Then a.QTY Else 0 end)as decimal(15,2)) as 'Inbond_Amount'
  FROM [D365FO_DATALAKE].[dbo].[dirpartytable] d 
  Left join [D365FO_DATALAKE].[dbo].[vendtable] v on v.party = d.recid
  left join [D365FO_DATALAKE].[dbo].[purchtable] h on h.orderaccount = v.accountnum and h.dataareaid = v.dataareaid
  left join [PROJECT_1].[dbo].[Transaction_FO] a on a.[Ref.DocNum] = h.purchid and a.CompanyCode = h.dataareaid
  Left join [syndpdev001].[dbo].[tm_Warehouse] w on w.[WarehouseId] = a.[INVENTLOCATIONID]
  where 
  a.CompanyCode in ('com7','dou7','bnn') and 
  a.INVENTLOCATIONID in ('4','77','72006','72008','79006') and 
  a.DATEPHYSICAL between '2025-01-01' and '2026-08-31' 
  Group by YEAR(a.DATEPHYSICAL) ,MONTH(a.DATEPHYSICAL),d.name,a.companycode,w.Name
  order by  YEAR(a.DATEPHYSICAL), MONTH(a.DATEPHYSICAL),d.name,a.companycode,w.Name