# -*- coding: utf-8 -*-
"""ตรวจว่า ci.npi_iphone กรอง iPhone ออกมาถูกไหม — read-only

    python scripts/itec/booking_check.py

ตรวจ 2 ทางเสมอ
  ① มีอะไรใน ci ที่ไม่น่าจะใช่ iPhone   (false positive)
  ② มี iPhone ใน rpt ที่ตกหล่นไม่เข้า ci (false negative)  <- มักเป็นปัญหาใหญ่กว่า
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
import db                                                     # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 120)
pd.set_option("display.max_colwidth", 46)
Q = lambda s: db.query("itec", s)                             # noqa: E731


def head(t):
    print("\n" + "=" * 78)
    print(" " + t)
    print("=" * 78)


# ───────────────────────────────────────────────── ขอบเขตข้อมูล ──
head("ขอบเขตข้อมูลของสองตาราง")
print(Q("""
SELECT 'rpt.booking_list' AS ตาราง, COUNT_BIG(*) AS แถว,
       MIN(booking_datetime) AS เริ่ม, MAX(booking_datetime) AS ล่าสุด,
       COUNT(DISTINCT booking_branch) AS สาขา
FROM   rpt.booking_list
UNION ALL
SELECT 'ci.npi_iphone', COUNT_BIG(*), MIN(booking_datetime), MAX(booking_datetime),
       COUNT(DISTINCT booking_branch)
FROM   ci.npi_iphone""").to_string(index=False))

# ───────────────────────────────────────────── category_name ใน rpt ──
head("category_name ใน rpt.booking_list (15 อันดับ)")
print(Q("""
SELECT TOP 15 category_name, COUNT_BIG(*) AS แถว
FROM   rpt.booking_list GROUP BY category_name ORDER BY COUNT_BIG(*) DESC""").to_string(index=False))

# ───────────────────────────────────── ① false positive ใน ci ──
head("① ใน ci มีอะไรที่ไม่ใช่ iPhone ไหม")
print(Q("""
SELECT category_name, COUNT_BIG(*) AS แถว
FROM   ci.npi_iphone GROUP BY category_name ORDER BY COUNT_BIG(*) DESC""").to_string(index=False))
print("\nแถวที่ product_name ไม่มีคำว่า iphone เลย:")
print(Q("""
SELECT TOP 20 booking_branch, category_name, Model, product_name, clean_iPhone_model
FROM   ci.npi_iphone
WHERE  product_name NOT LIKE '%iphone%'""").to_string(index=False))

# ───────────────────────────────────── ② false negative ใน rpt ──
head("② iPhone ใน rpt ที่ตกหล่นไม่เข้า ci")
print(Q("""
WITH rp AS (
    SELECT booking_id, booking_branch, product, category_name, Model, product_name
    FROM   rpt.booking_list
    WHERE  category_name = 'iPhone' OR product_name LIKE '%iphone%'
)
SELECT COUNT_BIG(*) AS iphone_ใน_rpt,
       SUM(CASE WHEN c.booking_id IS NULL THEN 1 ELSE 0 END) AS ตกหล่น
FROM   rp
LEFT   JOIN ci.npi_iphone c
       ON  c.booking_id = rp.booking_id
       AND c.booking_branch = rp.booking_branch
       AND c.product = rp.product""").to_string(index=False))
print("\nตัวอย่างที่ตกหล่น:")
print(Q("""
WITH rp AS (
    SELECT booking_id, booking_branch, product, category_name, Model, product_name, booking_datetime
    FROM   rpt.booking_list
    WHERE  category_name = 'iPhone' OR product_name LIKE '%iphone%'
)
SELECT TOP 20 rp.booking_datetime, rp.category_name, rp.Model, rp.product_name
FROM   rp
LEFT   JOIN ci.npi_iphone c
       ON  c.booking_id = rp.booking_id AND c.booking_branch = rp.booking_branch
       AND c.product = rp.product
WHERE  c.booking_id IS NULL
ORDER  BY rp.booking_datetime DESC""").to_string(index=False))

# ─────────────────────────────────── ③ คอลัมน์ที่ ci สร้างเพิ่ม ──
head("③ คอลัมน์ที่ ci แกะออกมา ถูกไหม — เทียบสีกับชื่อสินค้า")
print(Q("""
SELECT TOP 25 clean_iPhone_model AS รุ่น, clean_iPhone_submodel AS ซับ,
       device_memory AS ความจุ, device_color AS สีที่แกะได้, product_name,
       COUNT_BIG(*) AS แถว
FROM   ci.npi_iphone
WHERE  product_name NOT LIKE '%' + device_color + '%'
GROUP  BY clean_iPhone_model, clean_iPhone_submodel, device_memory, device_color, product_name
ORDER  BY COUNT_BIG(*) DESC""").to_string(index=False))
print()
print(Q("""
SELECT SUM(CASE WHEN product_name LIKE '%' + device_color + '%' THEN 1 ELSE 0 END) AS สีตรง,
       SUM(CASE WHEN product_name NOT LIKE '%' + device_color + '%' THEN 1 ELSE 0 END) AS สีไม่ตรง,
       COUNT_BIG(*) AS รวม
FROM   ci.npi_iphone""").to_string(index=False))

# ─────────────────────────────────────────── ④ unique_key ซ้ำไหม ──
head("④ unique_key ซ้ำไหม (ถ้าซ้ำ ยอดจะถูกนับเกิน)")
print(Q("""
SELECT COUNT_BIG(*) AS แถวทั้งหมด, COUNT(DISTINCT unique_key) AS key_ไม่ซ้ำ,
       COUNT_BIG(*) - COUNT(DISTINCT unique_key) AS ซ้ำ
FROM   ci.npi_iphone""").to_string(index=False))

# ───────────────────────────────────── ⑤ รุ่นที่มีในข้อมูล ──
head("⑤ รุ่น iPhone ที่มีในข้อมูล")
print(Q("""
SELECT clean_iPhone_model AS รุ่น, COUNT_BIG(*) AS แถว,
       MIN(clean_bookdate) AS จองครั้งแรก, MAX(clean_bookdate) AS จองครั้งล่าสุด
FROM   ci.npi_iphone GROUP BY clean_iPhone_model ORDER BY clean_iPhone_model""").to_string(index=False))
