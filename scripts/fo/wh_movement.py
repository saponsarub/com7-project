# -*- coding: utf-8 -*-
"""ชุดที่ 1 และ 2 — รับเข้า / จ่ายออก รายวัน แยกตามหมวดสินค้า

⚠️ บทเรียนสำคัญ: คลังกลางไม่ได้ขายให้ลูกค้า แต่ "โอนไปสาขา"
   ITEC สาขา 4 มี Transfer-Out 8.4 ล้านแถว แต่ Sales 0 แถว
   ถ้านับแค่ Sales ของที่ออกจากคลังจะหายไปเกือบทั้งหมด
   จึงใส่ทั้งสองประเภท แล้วแยกด้วยคอลัมน์ MovementType
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import wh_common as W
import db

FROM, TO, SPLIT = W.FROM, W.TO, W.SPLIT

# refcat 3 = Purchase order · 0 = Sales order · 6 = Transfer · 21/22 = Transfer order
FO_KIND = {
    "inbound":  {"cats": "(3, 6, 21, 22)", "sign": "> 0"},
    "outbound": {"cats": "(0, 6, 21, 22)", "sign": "< 0"},
}
FO_LABEL = {3: "PO ซื้อเข้า", 0: "SO ขาย", 6: "Transfer โอน",
            21: "Transfer โอน", 22: "Transfer โอน"}

SQL_FO = """
SELECT CONVERT(date, a.DATEPHYSICAL)  AS [Date]
     , a.CompanyCode                  AS BU
     , a.INVENTLOCATIONID             AS Warehouse
     , a.REFERENCECATEGORY            AS RefCat
     , a.[FO-ITEMNO]                  AS ItemId_FO
     , a.[ITEC-ITEMNO]                AS ItemId_ITEC
     , SUM(a.QTY)                     AS Qty
     , COUNT_BIG(*)                   AS Lines
     , COUNT(DISTINCT a.[Ref.DocNum]) AS DocCount
FROM PROJECT_1.dbo.Transaction_FO a WITH (NOLOCK)
WHERE a.REFERENCECATEGORY IN {cats}
  AND a.QTY {sign}
  AND a.DATEPHYSICAL >= '{d1}' AND a.DATEPHYSICAL < '{d2}'
  AND {wh}
  AND NOT (a.CompanyCode = 'com7' AND a.DATEPHYSICAL < '{split}')
GROUP BY CONVERT(date, a.DATEPHYSICAL), a.CompanyCode, a.INVENTLOCATIONID,
         a.REFERENCECATEGORY, a.[FO-ITEMNO], a.[ITEC-ITEMNO]
"""

# ── ฝั่ง ITEC — เฉพาะ com7 ปี 2025 ─────────────────────────────────────
ITEC_IN = ("Buy (Local)", "Buy (Oversea)", "Consign from Supplier",
           "Return Goods to Supplier", "Return Consign from Supplier")
ITEC_IN_TR = ("Transfer-In",)
ITEC_OUT = ("Sales", "Return Sales")
ITEC_OUT_TR = ("Transfer-Out",)

ITEC_LABEL = {**{t: "PO ซื้อเข้า" for t in ITEC_IN},
              **{t: "SO ขาย" for t in ITEC_OUT},
              "Transfer-In": "Transfer โอน", "Transfer-Out": "Transfer โอน"}

# _tracking มี PO_Num · ตัวหลักไม่มี จึงใช้คนละตารางตามชนิดเอกสาร
SQL_ITEC = """
SELECT CONVERT(date, t.[Create Time]) AS [Date]
     , t.Branch                       AS Branch
     , t.Transaction_Type             AS TType
     , t.Product                      AS ItemId_ITEC
     , SUM(t.Qty)                     AS Qty
     , COUNT_BIG(*)                   AS Lines
     , COUNT(DISTINCT {doc})          AS DocCount
FROM dbo.{tbl} t WITH (NOLOCK)
WHERE t.Branch IN (4, 77)
  AND t.[Create Time] >= '{d1}' AND t.[Create Time] < '{d2}'
  AND t.Transaction_Type IN ({types})
GROUP BY CONVERT(date, t.[Create Time]), t.Branch, t.Transaction_Type, t.Product
"""


def _q(items):
    return ", ".join(f"'{x}'" for x in items)


def _fo(kind):
    k = FO_KIND[kind]
    d = db.query("fo", SQL_FO.format(cats=k["cats"], sign=k["sign"], d1=FROM, d2=TO,
                                     wh=W.wh_filter("a"), split=SPLIT))
    d["MovementType"] = d.RefCat.map(FO_LABEL)
    return d.drop(columns=["RefCat"])


def _itec(kind):
    """ขารับเข้าใช้ _tracking เพราะมี PO_Num · ขาโอน/ขายใช้ตัวหลัก"""
    parts = []
    if kind == "inbound":
        jobs = [("Transaction_ITEC_tracking", "t.PO_Num", ITEC_IN),
                ("Transaction_ITEC", "t.ID", ITEC_IN_TR)]
    else:
        jobs = [("Transaction_ITEC", "t.ID", ITEC_OUT + ITEC_OUT_TR)]
    for tbl, doc, types in jobs:
        parts.append(db.query("fo", SQL_ITEC.format(
            tbl=tbl, doc=doc, types=_q(types), d1=FROM, d2=SPLIT)))
    d = pd.concat(parts, ignore_index=True)
    d["BU"] = "com7"
    d["Warehouse"] = d.Branch.astype(str)   # สาขา ITEC 4/77 = คลัง FO 4/77
    d["MovementType"] = d.TType.map(ITEC_LABEL)
    return d.drop(columns=["Branch", "TType"])


def enrich(d):
    """เติมหมวดทั้งสองชุดให้ทุกแถว ไม่ว่ามาจากระบบไหน"""
    br = W.bridge_item().drop_duplicates(["ItemId_ITEC", "CompanyCode"])
    it = W.cat_itec().rename(columns={
        "ItemId": "ItemId_ITEC", "ItemName": "ItemName_ITEC",
        "CategoryName": "ITEC_Category", "SubCategoryName": "ITEC_SubCategory",
        "Brand": "Brand_ITEC"})
    fo = W.cat_fo().rename(columns={"GroupCategoryName": "FO_GroupCategory",
                                    "CompanyCode": "BU"})
    if "ItemId_FO" not in d.columns:
        d["ItemId_FO"] = pd.NA
    m = d.ItemId_FO.isna()
    if m.any():
        b = br.rename(columns={"CompanyCode": "BU", "ItemId_FO": "_fo"})
        d = d.merge(b, on=["ItemId_ITEC", "BU"], how="left")
        d.loc[m, "ItemId_FO"] = d.loc[m, "_fo"]
        d = d.drop(columns=["_fo"])
    d = d.merge(it, on="ItemId_ITEC", how="left")
    return d.merge(fo, on=["ItemId_FO", "BU"], how="left")


def build(kind):
    print(f"  ดึง FO ({kind}) ...", flush=True)
    a = W.cached(f"mv2_fo_{kind}", lambda: _fo(kind))
    print(f"  ดึง ITEC ({kind}) ...", flush=True)
    b = W.cached(f"mv2_itec_{kind}", lambda: _itec(kind))
    a["Source"], b["Source"] = "FO", "ITEC"
    d = enrich(pd.concat([a, b], ignore_index=True))
    d["Qty"] = d["Qty"].abs()               # อ่านง่าย — ทิศทางบอกด้วยชีตแล้ว
    d["BU_Name"] = d.BU.map(W.BU_NAME)
    d["Warehouse_Name"] = [W.WAREHOUSES.get((x, y), "")
                           for x, y in zip(d.BU, d.Warehouse)]
    return d
