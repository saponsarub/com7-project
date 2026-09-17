# -*- coding: utf-8 -*-
"""เจาะค่าผิดปกติที่เจอในรอบตรวจ — read-only"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
import db                                                     # noqa: E402

pd.set_option("display.width", 210)
pd.set_option("display.max_rows", 60)
pd.set_option("display.max_colwidth", 44)
Q = lambda s: db.query("itec", s)                             # noqa: E731


def head(t):
    print("\n" + "═" * 76)
    print(" " + t)
    print("═" * 76)


head("① booking_qty ผิดปกติ — ใครมี 653 ล้านชิ้น")
print(Q("""
SELECT TOP 12 booking_id, booking_branch, clean_bookdate, clean_iPhone_model AS รุ่น,
       booking_qty, CAST(srp AS int) AS srp, CAST(booking_amount AS int) AS มัดจำ,
       Model, book_shop_brand
FROM   ci.npi_iphone WHERE booking_qty > 10 OR booking_qty <= 0
ORDER  BY booking_qty DESC""").to_string(index=False))

print("\nการกระจายของ booking_qty")
print(Q("""
SELECT CASE WHEN booking_qty <= 0 THEN 'a. <= 0'
            WHEN booking_qty = 1 THEN 'b. 1'
            WHEN booking_qty BETWEEN 2 AND 5 THEN 'c. 2-5'
            WHEN booking_qty BETWEEN 6 AND 10 THEN 'd. 6-10'
            ELSE 'e. > 10' END AS ช่วง,
       COUNT_BIG(*) AS แถว
FROM   ci.npi_iphone GROUP BY CASE WHEN booking_qty <= 0 THEN 'a. <= 0'
            WHEN booking_qty = 1 THEN 'b. 1'
            WHEN booking_qty BETWEEN 2 AND 5 THEN 'c. 2-5'
            WHEN booking_qty BETWEEN 6 AND 10 THEN 'd. 6-10'
            ELSE 'e. > 10' END ORDER BY ช่วง""").to_string(index=False))

head("② มัดจำเกินราคาเครื่อง 40,189 แถว — เป็นแบบไหน")
print(Q("""
SELECT installment_type AS ประเภทจ่าย,
       COUNT_BIG(*) AS แถว,
       SUM(CASE WHEN booking_amount > srp THEN 1 ELSE 0 END) AS มัดจำเกินราคา,
       CAST(AVG(booking_amount) AS int) AS มัดจำเฉลี่ย,
       CAST(AVG(srp) AS int) AS ราคาเฉลี่ย
FROM   ci.npi_iphone GROUP BY installment_type ORDER BY แถว DESC""").to_string(index=False))
print("\nตัวอย่าง 10 แถวที่มัดจำเกินราคา")
print(Q("""
SELECT TOP 10 clean_bookdate, clean_iPhone_model AS รุ่น, clean_iPhone_submodel AS ซับ,
       installment_type AS จ่าย, CAST(srp AS int) AS srp,
       CAST(booking_amount AS int) AS มัดจำ, PayInfo
FROM   ci.npi_iphone WHERE booking_amount > srp ORDER BY booking_amount - srp DESC""").to_string(index=False))

head("③ ค่าผิดปกติพวกนี้อยู่ในช่วงเปิดตัวไหม")
print(Q("""
WITH L AS (SELECT * FROM (VALUES
    ('iPhone-15','2023-09-15','2023-09-22'),('iPhone-16','2024-09-13','2024-09-20'),
    ('iPhone-17','2025-09-12','2025-09-19'),('iPhone-18','2026-09-12','2026-09-18')) v(m,d_open,d_sale))
SELECT L.m AS รุ่น, COUNT_BIG(*) AS แถวในช่วง,
       SUM(CASE WHEN b.booking_qty <> 1 THEN 1 ELSE 0 END) AS qty_ไม่ใช่1,
       MAX(b.booking_qty) AS qty_สูงสุด,
       SUM(b.booking_qty) AS ผลรวม_qty
FROM   ci.npi_iphone b JOIN L ON L.m = b.clean_iPhone_model
WHERE  b.clean_bookdate BETWEEN L.d_open AND L.d_sale AND b.Model NOT LIKE 'DUMMY%'
GROUP  BY L.m ORDER BY L.m""").to_string(index=False))

head("④ อัตราจองแล้วมารับจริง")
print(Q("""
WITH L AS (SELECT * FROM (VALUES
    ('iPhone-15','2023-09-15','2023-09-22'),('iPhone-16','2024-09-13','2024-09-20'),
    ('iPhone-17','2025-09-12','2025-09-19'),('iPhone-18','2026-09-12','2026-09-18')) v(m,d_open,d_sale))
SELECT L.m AS รุ่น, COUNT_BIG(*) AS ใบจอง,
       SUM(CASE WHEN b.finish=1 THEN 1 ELSE 0 END) AS มารับ,
       CAST(100.0*SUM(CASE WHEN b.finish=1 THEN 1 ELSE 0 END)/COUNT_BIG(*) AS decimal(5,1)) AS อัตรา_pct
FROM   ci.npi_iphone b JOIN L ON L.m = b.clean_iPhone_model
WHERE  b.clean_bookdate BETWEEN L.d_open AND L.d_sale AND b.Model NOT LIKE 'DUMMY%'
GROUP  BY L.m ORDER BY L.m""").to_string(index=False))
