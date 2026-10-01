# -*- coding: utf-8 -*-
"""ของใช้ร่วมของรายงานคลัง — ขอบเขต · สะพานหมวดสินค้า

ขอบเขตงาน (ยืนยันกับผู้ขอเมื่อ 2026-09-24)
    com7  4     ID4 : คลังสินค้า (สำนักงานใหญ่)
    com7  77    ID77 : E-Commerce Warehouse
    dou7  79001 Warehouse (กลาง)        <- คลังหลัก (ยืนยัน 2026-09-24)
    bnn   72008 ADEPT YAS
    bnn   72006 ADEPTWH-ONLINE

    ช่วงเวลา 2025-01-01 ถึง 2026-08-31
    com7 ปี 2025 เอาจาก ITEC · ปี 2026 เอาจาก FO · dou7/bnn เอาจาก FO ทั้งหมด
"""
import sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd                                   # noqa: E402
import db                                             # noqa: E402

OUT = Path(__file__).resolve().parent / "_out"
CACHE = Path(__file__).resolve().parent / "_cache"

FROM, TO = "2025-01-01", "2026-09-01"        # TO คือขอบบน ไม่รวมวันนั้น
SPLIT = "2026-01-01"                          # com7 เปลี่ยนจาก ITEC เป็น FO ตรงนี้

WAREHOUSES = {
    ("com7", "4"):     "ID4 : คลังสินค้า (สำนักงานใหญ่)",
    ("com7", "77"):    "ID77 : E-Commerce Warehouse",
    ("dou7", "79001"): "Warehouse (กลาง)",
    ("bnn",  "72008"): "ADEPT YAS",
    ("bnn",  "72006"): "ADEPTWH-ONLINE",
}
ITEC_BRANCHES = [4, 77]                       # สาขาฝั่ง ITEC ที่ตรงกับคลัง com7

BU_NAME = {"com7": "COM7", "dou7": "Double7", "bnn": "Adept"}


def wh_filter(alias="a"):
    """เงื่อนไข SQL ของคลังในขอบเขต"""
    parts = [f"({alias}.CompanyCode = '{bu}' AND {alias}.INVENTLOCATIONID = '{wh}')"
             for bu, wh in WAREHOUSES]
    return "(" + " OR ".join(parts) + ")"


def cached(name, fn):
    """ดึงครั้งเดียวแล้วเก็บไว้ — คิวรีบางตัวใช้เวลาเป็นนาที"""
    CACHE.mkdir(exist_ok=True)
    p = CACHE / f"{name}.parquet"
    if p.exists():
        print(f"  ใช้แคช {name}", flush=True)
        return pd.read_parquet(p)
    d = fn()
    d.to_parquet(p, index=False)
    print(f"  เก็บแคช {name} ({len(d):,} แถว)", flush=True)
    return d


# ── สะพานหมวดสินค้า ──────────────────────────────────────────────────
# ปัญหา: com7 ปี 2025 มาจาก ITEC (หมวดชุดหนึ่ง) ปี 2026 มาจาก FO (อีกชุด)
# ทางออก: สร้างตารางแปลงรหัส แล้วเติมหมวด "ทั้งสองชุด" ให้ทุกแถว
#         ไม่ว่าข้อมูลจะมาจากระบบไหน ผู้ใช้จึงเทียบข้ามปีได้

def bridge_item():
    """ITEC-ITEMNO <-> FO-ITEMNO — จาก Transaction_FO เอง (ผูกกัน 1:1)"""
    def go():
        return db.query("fo", """
SELECT DISTINCT [ITEC-ITEMNO] AS ItemId_ITEC, [FO-ITEMNO] AS ItemId_FO, CompanyCode
FROM PROJECT_1.dbo.Transaction_FO WITH (NOLOCK)
WHERE [ITEC-ITEMNO] IS NOT NULL AND DATEPHYSICAL >= '2024-01-01'
""")
    return cached("bridge_item", go)


def cat_itec():
    """หมวดฝั่ง ITEC"""
    def go():
        return db.query("itec", """
SELECT ItemId, ItemName, CategoryName, SubCategoryName, Brand
FROM rpt.dim_item_itec
""")
    return cached("cat_itec", go)


def cat_fo():
    """หมวดฝั่ง FO — 1 สินค้า 1 บริษัท 1 แถว (ยุบซ้ำด้วย RecId ล่าสุด)"""
    def go():
        return db.query("fo_raw", """
WITH item AS (
    SELECT ItemId, SysCompanyId, DefaultDimension, ItemName, Brand,
           ROW_NUMBER() OVER (PARTITION BY ItemId, SysCompanyId ORDER BY RecId DESC) AS rn
    FROM dbo.tm_Item WITH (NOLOCK)
    WHERE SysSourceRef = 'FO' AND ItemId IS NOT NULL
)
SELECT i.ItemId AS ItemId_FO, i.SysCompanyId AS CompanyCode,
       i.ItemName AS ItemName_FO, i.Brand AS Brand_FO,
       c.GroupCategoryName, c.CategoryName AS FO_CategoryName,
       c.SubCategoryName AS FO_SubCategoryName
FROM item i
LEFT JOIN dbo.tm_FinDimValueSet c WITH (NOLOCK)
       ON c.FinancialDim = i.DefaultDimension AND c.SysSourceRef = 'FO'
WHERE i.rn = 1
""")
    return cached("cat_fo", go)
