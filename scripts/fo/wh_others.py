# -*- coding: utf-8 -*-
"""ชุดที่ 3 4 5 — สต็อกสิ้นเดือน · ผู้ขาย · ทะเบียนสินค้า"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import wh_common as W
import db


# ══════════════════════════════════════════════ ③ สต็อกสิ้นเดือน ══
# FO ไม่มีตารางสำเร็จ -> ไล่สะสม QTY ตั้งแต่แถวแรกของฐาน
# ยอดก่อนปี 2025 ยุบเป็นก้อนเดียวชื่อ 2024-12 = ยอดยกมา
SQL_STOCK_FO = """
SELECT a.CompanyCode                 AS BU
     , a.INVENTLOCATIONID            AS Warehouse
     , a.[FO-ITEMNO]                 AS ItemId_FO
     , a.[ITEC-ITEMNO]               AS ItemId_ITEC
     , CASE WHEN a.DATEPHYSICAL < '{d1}' THEN '2024-12'
            ELSE CONVERT(varchar(7), a.DATEPHYSICAL, 120) END AS YearMonth
     , SUM(a.QTY)                    AS QtyMove
FROM PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)
WHERE a.DATEPHYSICAL < '{d2}'
  AND a.REFERENCECATEGORY <> 7          -- ตัดรายการปิดบัญชีถัวเฉลี่ย
  AND {wh}
GROUP BY a.CompanyCode, a.INVENTLOCATIONID, a.[FO-ITEMNO], a.[ITEC-ITEMNO],
         CASE WHEN a.DATEPHYSICAL < '{d1}' THEN '2024-12'
              ELSE CONVERT(varchar(7), a.DATEPHYSICAL, 120) END
"""

SQL_STOCK_ITEC = """
SELECT CONVERT(varchar(7), OnHandAsOf, 120) AS YearMonth
     , Branch                               AS Branch
     , Product                              AS ItemId_ITEC
     , SUM(CAST(Qty AS bigint))             AS Qty
FROM rpt.onhandendmonth_itec
WHERE Branch IN (4, 77) AND OnHandAsOf >= '2025-01-01' AND OnHandAsOf < '2026-01-01'
GROUP BY CONVERT(varchar(7), OnHandAsOf, 120), Branch, Product
"""


def stock():
    print("  ดึงความเคลื่อนไหวสะสม (FO) ...", flush=True)
    mv = W.cached("stock_fo_moves", lambda: db.query("fo", SQL_STOCK_FO.format(
        d1=W.FROM, d2=W.TO, wh=W.wh_filter("a"))))
    print("  ดึงสต็อกสิ้นเดือน (ITEC 2025) ...", flush=True)
    it = W.cached("stock_itec", lambda: db.query("itec", SQL_STOCK_ITEC))

    # ไล่สะสมต่อ (BU, คลัง, สินค้า) ตามลำดับเดือน
    mv = mv.sort_values(["BU", "Warehouse", "ItemId_FO", "YearMonth"])
    mv["Qty"] = mv.groupby(["BU", "Warehouse", "ItemId_FO"]).QtyMove.cumsum()
    mv = mv[mv.YearMonth >= "2025-01"].copy()
    mv["Source"] = "FO"

    it["BU"] = "com7"
    it["Warehouse"] = it.Branch.astype(str)
    it["Source"] = "ITEC"
    it = it.drop(columns=["Branch"])

    # com7 ปี 2025 ใช้ ITEC -> ตัดแถว FO ของ com7 ปี 2025 ออก
    mv = mv[~((mv.BU == "com7") & (mv.YearMonth < "2026-01"))]
    d = pd.concat([mv.drop(columns=["QtyMove"]), it], ignore_index=True)
    return _decorate(d)


# ══════════════════════════════════════════════════════ ④ ผู้ขาย ══
# ⚠️ ที่อยู่/ประเทศของผู้ขายในฐานนี้ "ว่างทั้งหมด"
#    logisticspostaladdress ต่อไม่ติดเพราะไม่มีตาราง dirpartylocation
#    จึงรายงาน "ต้นทาง" เป็น site + คลังปลายทางที่ผู้ขายส่งเข้าแทน
SQL_VENDOR = """
SELECT a.CompanyCode          AS BU
     , a.INVENTLOCATIONID     AS Warehouse
     , h.orderaccount         AS VendorCode
     , dp.name                AS VendorName
     , h.inventsiteid         AS VendorDefaultSite
     , COUNT_BIG(*)                   AS Lines
     , COUNT(DISTINCT a.[Ref.DocNum]) AS PO_Count
     , COUNT(DISTINCT a.[FO-ITEMNO])  AS SKU
     , SUM(a.QTY)                     AS Qty
     , CAST(SUM(a.RealCost) AS decimal(28,2)) AS Cost
     , CONVERT(varchar(10), MIN(a.DATEPHYSICAL), 120) AS FirstDate
     , CONVERT(varchar(10), MAX(a.DATEPHYSICAL), 120) AS LastDate
FROM PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)
LEFT JOIN D365FO_DATALAKE.dbo.purchtable h WITH (NOLOCK)
       ON h.purchid = a.[Ref.DocNum] AND h.dataareaid = a.CompanyCode
LEFT JOIN D365FO_DATALAKE.dbo.vendtable v WITH (NOLOCK)
       ON v.accountnum = h.orderaccount AND v.dataareaid = h.dataareaid
LEFT JOIN D365FO_DATALAKE.dbo.dirpartytable dp WITH (NOLOCK) ON dp.recid = v.party
WHERE a.REFERENCECATEGORY = 3
  AND a.DATEPHYSICAL >= '{d1}' AND a.DATEPHYSICAL < '{d2}'
  AND {wh}
GROUP BY a.CompanyCode, a.INVENTLOCATIONID, h.orderaccount, dp.name, h.inventsiteid
"""


def vendor():
    print("  ดึงผู้ขาย ...", flush=True)
    d = W.cached("vendor", lambda: db.query("fo", SQL_VENDOR.format(
        d1=W.FROM, d2=W.TO, wh=W.wh_filter("a"))))
    d["BU_Name"] = d.BU.map(W.BU_NAME)
    d["Warehouse_Name"] = [W.WAREHOUSES.get((x, y), "") for x, y in zip(d.BU, d.Warehouse)]
    return d.sort_values("Qty", ascending=False)


# ═══════════════════════════════════════════════ ⑤ ทะเบียนสินค้า ══
SQL_PRODUCT = """
SELECT i.itemid        AS ItemId_FO
     , i.dataareaid    AS BU
     , i.width         AS Width
     , i.height        AS Height
     , i.depth         AS Depth
     , i.grosswidth    AS GrossWidth
     , i.grossheight   AS GrossHeight
     , i.grossdepth    AS GrossDepth
     , i.netweight     AS NetWeight
     , i.taraweight    AS TaraWeight
     , i.unitvolume    AS UnitVolume
FROM D365FO_DATALAKE.dbo.inventtable i WITH (NOLOCK)
WHERE i.dataareaid IN ('com7','dou7','bnn')
"""


def product():
    print("  ดึงทะเบียนสินค้า ...", flush=True)
    d = W.cached("product", lambda: db.query("fo", SQL_PRODUCT))
    return _decorate(d, keys=("ItemId_FO", "BU"))


# ═════════════════════════════════════════════════════════════════
def _decorate(d, keys=("ItemId_FO", "BU")):
    """เติมหมวดทั้งสองชุด + ชื่อคลัง"""
    br = W.bridge_item().drop_duplicates(["ItemId_ITEC", "CompanyCode"])
    it = W.cat_itec().rename(columns={
        "ItemId": "ItemId_ITEC", "ItemName": "ItemName_ITEC",
        "CategoryName": "ITEC_Category", "SubCategoryName": "ITEC_SubCategory",
        "Brand": "Brand_ITEC"})
    fo = W.cat_fo().rename(columns={"GroupCategoryName": "FO_GroupCategory",
                                    "CompanyCode": "BU"})

    if "ItemId_ITEC" not in d.columns:
        b2 = br.rename(columns={"CompanyCode": "BU"}).drop_duplicates(["ItemId_FO", "BU"])
        d = d.merge(b2, on=["ItemId_FO", "BU"], how="left")
    if "ItemId_FO" not in d.columns:
        b2 = br.rename(columns={"CompanyCode": "BU", "ItemId_FO": "_fo"})
        d = d.merge(b2, on=["ItemId_ITEC", "BU"], how="left").rename(columns={"_fo": "ItemId_FO"})

    d = d.merge(it, on="ItemId_ITEC", how="left")
    d = d.merge(fo, on=["ItemId_FO", "BU"], how="left")
    d["BU_Name"] = d.BU.map(W.BU_NAME)
    if "Warehouse" in d.columns:
        d["Warehouse_Name"] = [W.WAREHOUSES.get((x, y), "") for x, y in zip(d.BU, d.Warehouse)]
    return d
