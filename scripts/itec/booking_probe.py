# -*- coding: utf-8 -*-
"""สำรวจตารางยอดจอง — read-only

    python scripts/itec/booking_probe.py

rpt.booking_list  ข้อมูลดิบ ยอดจองทุกสินค้า แต่ละสาขา
ci.npi_iphone     กรองเฉพาะกลุ่ม iPhone
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
import db                                                     # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 300)
pd.set_option("display.max_colwidth", 40)

TABLES = [("rpt", "booking_list"), ("ci", "npi_iphone")]

for sch, tb in TABLES:
    print("=" * 80)
    print(f"  {sch}.{tb}")
    print("=" * 80)
    try:
        cols = db.columns("itec", sch, tb)
        n = db.query("itec", f"SELECT COUNT_BIG(*) AS n FROM [{sch}].[{tb}]")["n"][0]
        print(f"{len(cols)} คอลัมน์ · {n:,} แถว\n")
        print(cols.to_string(index=False))
        print("\n── 3 แถวแรก ──")
        print(db.query("itec", f"SELECT TOP 3 * FROM [{sch}].[{tb}]").to_string(index=False))
    except Exception as e:
        print("❌", str(e).splitlines()[0][:160])
    print()
