# -*- coding: utf-8 -*-
"""ยอดจองรายวัน x รุ่นย่อย — ใช้ทำตัวเลือกช่วงวันใน dashboard"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
import db                                                     # noqa: E402

OUT = Path(__file__).parent / "_out"
pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 200)

d = db.query("itec", """
WITH L AS (SELECT * FROM (VALUES
    ('iPhone-15','2023-09-15'),('iPhone-16','2024-09-13'),
    ('iPhone-17','2025-09-12'),('iPhone-18','2026-09-12')) v(m, d_open))
SELECT b.clean_iPhone_model                                AS model,
       b.clean_iPhone_submodel                             AS submodel,
       DATEDIFF(day, L.d_open, b.clean_bookdate)           AS day_no,
       COUNT_BIG(*)                                        AS bookings,
       CAST(SUM(b.srp) / 1000000.0 AS decimal(12,2))       AS value_m
FROM   ci.npi_iphone b JOIN L ON L.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, L.d_open, b.clean_bookdate) BETWEEN 0 AND 6
  AND  b.Model NOT LIKE 'DUMMY%'
GROUP  BY b.clean_iPhone_model, b.clean_iPhone_submodel,
          DATEDIFF(day, L.d_open, b.clean_bookdate)
ORDER  BY model, submodel, day_no""")

d.to_csv(OUT / "booking_daily_sub.csv", index=False, encoding="utf-8-sig")
print(f"{len(d)} แถว -> booking_daily_sub.csv\n")

# ── พิมพ์เป็นตาราง cumulative ให้เอาไปใส่ dashboard ──
for metric, col in (("ใบจอง", "bookings"), ("มูลค่า(ลบ.)", "value_m")):
    print(f"── {metric} · สะสมถึงวันที่ N ──")
    piv = d.pivot_table(index=["model", "submodel"], columns="day_no",
                        values=col, aggfunc="sum", fill_value=0)
    piv = piv.reindex(columns=range(7), fill_value=0).cumsum(axis=1)
    print(piv.round(1).to_string())
    print()

print("── JS array (วางลงโค้ดได้เลย) ──")
for sm in ["Pro Max", "Pro", "Standard", "Plus"]:
    for col, key in (("bookings", "q"), ("value_m", "v")):
        rows = []
        for m in ["iPhone-15", "iPhone-16", "iPhone-17", "iPhone-18"]:
            s = d[(d.model == m) & (d.submodel == sm)].set_index("day_no")[col]
            s = s.reindex(range(7), fill_value=0).cumsum()
            rows.append("[" + ",".join(
                (f"{v:.1f}" if key == "v" else str(int(v))) for v in s) + "]")
        print(f'  {sm:9} {key}: [{", ".join(rows)}],')
