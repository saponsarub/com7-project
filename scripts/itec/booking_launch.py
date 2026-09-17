# -*- coding: utf-8 -*-
"""ยอดจองช่วงเปิดตัว iPhone รายปี + ตรวจวันที่ที่ได้มา — read-only

    python scripts/itec/booking_launch.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
import db                                                     # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 48)
Q = lambda s: db.query("itec", s)                             # noqa: E731


def head(t):
    print("\n" + "=" * 78)
    print(" " + t)
    print("=" * 78)


# ───────────────── ตกหล่นเฉพาะ category_name = 'iPhone' เป๊ะ ๆ ──
head("① rpt ที่ category_name='iPhone' เป๊ะ ๆ แต่ไม่เข้า ci")
print(Q("""
SELECT COUNT_BIG(*) AS rpt_iphone, SUM(CASE WHEN c.booking_id IS NULL THEN 1 ELSE 0 END) AS ตกหล่น
FROM   rpt.booking_list r
LEFT   JOIN ci.npi_iphone c
       ON c.booking_id=r.booking_id AND c.booking_branch=r.booking_branch AND c.product=r.product
WHERE  r.category_name = 'iPhone'""").to_string(index=False))
print("\nตกหล่นเป็นรุ่นอะไรบ้าง:")
print(Q("""
SELECT TOP 20 r.Model, COUNT_BIG(*) AS แถว,
       MIN(r.booking_datetime) AS แรกสุด, MAX(r.booking_datetime) AS ล่าสุด
FROM   rpt.booking_list r
LEFT   JOIN ci.npi_iphone c
       ON c.booking_id=r.booking_id AND c.booking_branch=r.booking_branch AND c.product=r.product
WHERE  r.category_name='iPhone' AND c.booking_id IS NULL
GROUP  BY r.Model ORDER BY COUNT_BIG(*) DESC""").to_string(index=False))

# ─────────────────────── รุ่นที่แกะไม่ออก ──
head("② แถวที่ clean_iPhone_model แกะไม่ออก (ค่าเป็น 'iPhone-')")
print(Q("""
SELECT TOP 15 Model, product_name, COUNT_BIG(*) AS แถว
FROM   ci.npi_iphone WHERE clean_iPhone_model = 'iPhone-'
GROUP  BY Model, product_name ORDER BY COUNT_BIG(*) DESC""").to_string(index=False))

# ─────────────── วันจองจริงของแต่ละรุ่น เทียบกับที่ได้มา ──
head("③ วันเปิดจองจริงในข้อมูล เทียบกับตารางที่ได้มา")
print(Q("""
SELECT clean_iPhone_model AS รุ่น, MIN(clean_bookdate) AS จองวันแรก,
       MIN(clean_finishdate) AS รับเครื่องวันแรก,
       DATEDIFF(day, MIN(clean_bookdate), MIN(clean_finishdate)) AS ห่าง_วัน,
       COUNT_BIG(*) AS จองทั้งหมด
FROM   ci.npi_iphone
WHERE  clean_iPhone_model <> 'iPhone-'
GROUP  BY clean_iPhone_model ORDER BY clean_iPhone_model""").to_string(index=False))

print("\n── ยอดจอง 12 วันแรกของแต่ละรุ่น (ดูว่าวันไหนคือวันเปิดจองจริง) ──")
print(Q("""
WITH f AS (
    SELECT clean_iPhone_model AS m, MIN(clean_bookdate) AS d0
    FROM   ci.npi_iphone WHERE clean_iPhone_model <> 'iPhone-'
    GROUP  BY clean_iPhone_model)
SELECT b.clean_iPhone_model AS รุ่น,
       DATEDIFF(day, f.d0, b.clean_bookdate) AS วันที่,
       b.clean_bookdate AS วันที่จริง,
       DATENAME(weekday, b.clean_bookdate) AS วัน,
       COUNT_BIG(*) AS จอง
FROM   ci.npi_iphone b JOIN f ON f.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, f.d0, b.clean_bookdate) BETWEEN 0 AND 11
GROUP  BY b.clean_iPhone_model, DATEDIFF(day, f.d0, b.clean_bookdate),
          b.clean_bookdate, DATENAME(weekday, b.clean_bookdate)
ORDER  BY b.clean_iPhone_model, วันที่""").to_string(index=False))

# ─────────────────── ยอดจองช่วงเปิดตัว ──
head("④ ยอดจองช่วงเปิดตัว — นับจากวันจองแรกถึงวันรับเครื่องแรกของแต่ละรุ่น")
print(Q("""
WITH f AS (
    SELECT clean_iPhone_model AS m, MIN(clean_bookdate) AS d_open,
           MIN(clean_finishdate) AS d_sale
    FROM   ci.npi_iphone WHERE clean_iPhone_model <> 'iPhone-'
    GROUP  BY clean_iPhone_model)
SELECT f.m AS รุ่น, f.d_open AS เปิดจอง, f.d_sale AS ขายวันแรก,
       DATEDIFF(day, f.d_open, f.d_sale) AS ห่าง,
       COUNT_BIG(*) AS จองในช่วง,
       SUM(b.booking_qty) AS ชิ้น,
       COUNT(DISTINCT b.booking_branch) AS สาขา,
       COUNT(DISTINCT b.MemberCode) AS ลูกค้า
FROM   ci.npi_iphone b JOIN f ON f.m = b.clean_iPhone_model
WHERE  b.clean_bookdate BETWEEN f.d_open AND f.d_sale
GROUP  BY f.m, f.d_open, f.d_sale ORDER BY f.m""").to_string(index=False))

print("\n── แยกตามรุ่นย่อย ──")
print(Q("""
WITH f AS (
    SELECT clean_iPhone_model AS m, MIN(clean_bookdate) AS d_open,
           MIN(clean_finishdate) AS d_sale
    FROM   ci.npi_iphone WHERE clean_iPhone_model <> 'iPhone-'
    GROUP  BY clean_iPhone_model)
SELECT f.m AS รุ่น, b.clean_iPhone_submodel AS ซับ, COUNT_BIG(*) AS จอง
FROM   ci.npi_iphone b JOIN f ON f.m = b.clean_iPhone_model
WHERE  b.clean_bookdate BETWEEN f.d_open AND f.d_sale
GROUP  BY f.m, b.clean_iPhone_submodel ORDER BY f.m, COUNT_BIG(*) DESC""").to_string(index=False))
