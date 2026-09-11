# -*- coding: utf-8 -*-
"""เทียบผลจาก Python กับผลจาก SQL เดิม ทีละ ItemId

ด่านที่ห้ามข้าม - strict ต้องได้ 0% ต่าง ก่อนจะมีสิทธิ์บอกว่าที่ต่างทีหลังคือของที่ดีขึ้น

    $env:MIS_USER="..."; $env:MIS_PWD="..."
    python scripts/itec/category/reconcile.py <path ไป ci_item_category.sql>
"""
import os
import sys
from pathlib import Path

import pandas as pd

import mapper as M

sys.stdout.reconfigure(encoding="utf-8")

KEYS = ["Main_Product_Dimension", "Sub_Product_Dimension"]
OUT = Path(__file__).parent / "category_diff.csv"


def connect():
    import pyodbc
    user, pwd = os.environ.get("MIS_USER"), os.environ.get("MIS_PWD")
    if not user or not pwd:
        sys.exit('ต้องตั้ง credential ก่อน:  $env:MIS_USER="..."; $env:MIS_PWD="..."')
    server = os.environ.get("MIS_SERVER", "192.168.43.250,18963")
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};"
        f"UID={user};PWD={pwd};TrustServerCertificate=yes;", timeout=30)


def compare(old, new, label):
    cmp = old[["ItemId"] + KEYS].merge(new[["ItemId"] + KEYS], on="ItemId",
                                       suffixes=("_old", "_new"))
    print(f"\n---------- {label} ----------")
    print(f"เทียบได้ {len(cmp):,} / {len(old):,} แถว")

    diffs = {}
    for k in KEYS:
        d = cmp[cmp[f"{k}_old"] != cmp[f"{k}_new"]]
        diffs[k] = d
        pct = len(d) / len(cmp) if len(cmp) else 0
        print(f"  {k:24} ต่าง {len(d):>7,}  ({pct:.2%})")
        if len(d):
            top = (d.groupby([f"{k}_old", f"{k}_new"]).size()
                    .sort_values(ascending=False).head(10))
            for (o, n), c in top.items():
                print(f"       {c:>7,}  {o}  ->  {n}")
    return diffs


def main():
    sql_path = Path(sys.argv[1] if len(sys.argv) > 1
                    else Path.home() / "Downloads" / "ci_item_category.sql")
    cn = connect()
    old = pd.read_sql(sql_path.read_text(encoding="utf-8", errors="replace"), cn)
    src = pd.read_sql(M.SQL_EXTRACT, cn)
    print(f"SQL เดิม {len(old):,} แถว · ข้อมูลดิบ {len(src):,} แถว")

    strict = M.run(src, strict=True)
    d1 = compare(old, strict, "strict - ต้องได้ 0% ทั้งสองคอลัมน์")

    loose = M.run(src, strict=False)
    d2 = compare(old, loose, "whole_word + แก้บั๊ก PC/Notebook - ต่างได้ แต่ต้องอธิบายได้")

    keep = d2[KEYS[0]].merge(src[["ItemId", "ItemName", "CategoryName",
                                  "SubCategoryName"]], on="ItemId", how="left")
    keep.to_csv(OUT, index=False, encoding="utf-8-sig")   # BOM ไม่งั้น Excel อ่านไทยเป็นขยะ
    print(f"\nรายการที่ต่าง -> {OUT}")

    if len(d1[KEYS[0]]) or len(d1[KEYS[1]]):
        sys.exit("strict ยังไม่ตรงของเดิม - แปลงกฎผิด ต้องแก้ก่อนไปต่อ")


if __name__ == "__main__":
    main()
