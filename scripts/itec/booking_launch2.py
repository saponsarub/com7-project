# -*- coding: utf-8 -*-
"""หาวันเปิดจอง/วันขายจริงจากข้อมูล แล้วนับยอดจองช่วงเปิดตัว — read-only

⚠️ รอบแรกใช้ MIN(clean_finishdate) เป็นวันขายวันแรก ซึ่งผิด
   เพราะมีลูกค้าบางรายรับเครื่องทันทีในวันจอง (เครื่องรุ่นเก่าที่มีสต็อก)
   ทำให้ได้ช่วงแค่ 1-3 วัน ทั้งที่จริงต้องเป็น 6-7 วัน
   รอบนี้ใช้ "วันที่มีการรับเครื่องมากที่สุด" แทน ซึ่งคือวันวางขายจริง
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
import db                                                     # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 200)
Q = lambda s: db.query("itec", s)                             # noqa: E731


def head(t):
    print("\n" + "=" * 78)
    print(" " + t)
    print("=" * 78)


# ต้องตัด DUMMY ออกก่อน — เป็นข้อมูลทดสอบที่ปนอยู่ใน rpt
EXCL = "AND b.Model NOT LIKE 'DUMMY%'"

head("① วันเปิดจองจริง — วันแรกที่มียอดเกิน 100 รายการ")
print("(วันที่มี 1-2 รายการก่อนหน้าคือรายการทดสอบ ไม่ใช่วันเปิดจริง)")
print(Q(f"""
WITH d AS (
    SELECT clean_iPhone_model AS m, clean_bookdate AS วันที่,
           DATENAME(weekday, clean_bookdate) AS วัน, COUNT_BIG(*) AS จอง
    FROM   ci.npi_iphone b
    WHERE  clean_iPhone_model <> 'iPhone-' {EXCL}
    GROUP  BY clean_iPhone_model, clean_bookdate)
SELECT m AS รุ่น, MIN(วันที่) AS วันแรกที่มีข้อมูล,
       MIN(CASE WHEN จอง >= 100 THEN วันที่ END) AS เปิดจองจริง,
       MIN(CASE WHEN จอง >= 100 THEN วัน END) AS วัน
FROM   d GROUP BY m ORDER BY m""").to_string(index=False))

head("② วันขายวันแรก — วันที่มีการรับเครื่องมากที่สุด")
print(Q(f"""
WITH d AS (
    SELECT clean_iPhone_model AS m, clean_finishdate AS วันที่,
           DATENAME(weekday, clean_finishdate) AS วัน, COUNT_BIG(*) AS รับเครื่อง,
           ROW_NUMBER() OVER (PARTITION BY clean_iPhone_model ORDER BY COUNT_BIG(*) DESC) AS rk
    FROM   ci.npi_iphone b
    WHERE  clean_iPhone_model <> 'iPhone-' AND clean_finishdate IS NOT NULL {EXCL}
    GROUP  BY clean_iPhone_model, clean_finishdate, DATENAME(weekday, clean_finishdate))
SELECT m AS รุ่น, วันที่ AS ขายวันแรก, วัน, รับเครื่อง
FROM   d WHERE rk = 1 ORDER BY m""").to_string(index=False))

head("③ สรุปเทียบกับตารางที่ได้มา")
print(Q(f"""
WITH op AS (
    SELECT clean_iPhone_model AS m, MIN(clean_bookdate) AS d_open
    FROM  (SELECT clean_iPhone_model, clean_bookdate, COUNT_BIG(*) AS n
           FROM   ci.npi_iphone b WHERE clean_iPhone_model <> 'iPhone-' {EXCL}
           GROUP  BY clean_iPhone_model, clean_bookdate) x
    WHERE n >= 100 GROUP BY clean_iPhone_model),
sa AS (
    SELECT m, วันที่ AS d_sale FROM (
        SELECT clean_iPhone_model AS m, clean_finishdate AS วันที่,
               ROW_NUMBER() OVER (PARTITION BY clean_iPhone_model ORDER BY COUNT_BIG(*) DESC) AS rk
        FROM   ci.npi_iphone b
        WHERE  clean_iPhone_model <> 'iPhone-' AND clean_finishdate IS NOT NULL {EXCL}
        GROUP  BY clean_iPhone_model, clean_finishdate) y WHERE rk = 1)
SELECT op.m AS รุ่น, op.d_open AS เปิดจอง, DATENAME(weekday, op.d_open) AS วัน_เปิด,
       sa.d_sale AS ขายวันแรก, DATENAME(weekday, sa.d_sale) AS วัน_ขาย,
       DATEDIFF(day, op.d_open, sa.d_sale) AS ห่าง
FROM   op JOIN sa ON sa.m = op.m ORDER BY op.m""").to_string(index=False))

head("④ ยอดจองช่วงเปิดตัว (เปิดจอง -> ขายวันแรก)")
print(Q(f"""
WITH op AS (
    SELECT clean_iPhone_model AS m, MIN(clean_bookdate) AS d_open
    FROM  (SELECT clean_iPhone_model, clean_bookdate, COUNT_BIG(*) AS n
           FROM   ci.npi_iphone b WHERE clean_iPhone_model <> 'iPhone-' {EXCL}
           GROUP  BY clean_iPhone_model, clean_bookdate) x
    WHERE n >= 100 GROUP BY clean_iPhone_model),
sa AS (
    SELECT m, วันที่ AS d_sale FROM (
        SELECT clean_iPhone_model AS m, clean_finishdate AS วันที่,
               ROW_NUMBER() OVER (PARTITION BY clean_iPhone_model ORDER BY COUNT_BIG(*) DESC) AS rk
        FROM   ci.npi_iphone b
        WHERE  clean_iPhone_model <> 'iPhone-' AND clean_finishdate IS NOT NULL {EXCL}
        GROUP  BY clean_iPhone_model, clean_finishdate) y WHERE rk = 1)
SELECT op.m AS รุ่น, op.d_open AS เปิดจอง, sa.d_sale AS ขายวันแรก,
       DATEDIFF(day, op.d_open, sa.d_sale) AS ห่าง,
       COUNT_BIG(*) AS ใบจอง, SUM(b.booking_qty) AS ชิ้น,
       CAST(SUM(b.srp) / 1000000.0 AS decimal(12,1)) AS มูลค่า_ล้านบาท,
       COUNT(DISTINCT b.booking_branch) AS สาขา
FROM   ci.npi_iphone b
JOIN   op ON op.m = b.clean_iPhone_model
JOIN   sa ON sa.m = b.clean_iPhone_model
WHERE  b.clean_bookdate BETWEEN op.d_open AND sa.d_sale {EXCL}
GROUP  BY op.m, op.d_open, sa.d_sale ORDER BY op.m""").to_string(index=False))

head("⑤ เทียบแบบยุติธรรม — 3 วันแรกนับจากวันเปิดจอง (ทุกรุ่นเท่ากัน)")
print("iPhone 18 ยังขายไม่ครบรอบ จึงเทียบช่วงยาวไม่ได้ ใช้ 3 วันแรกแทน")
print(Q(f"""
WITH op AS (
    SELECT clean_iPhone_model AS m, MIN(clean_bookdate) AS d_open
    FROM  (SELECT clean_iPhone_model, clean_bookdate, COUNT_BIG(*) AS n
           FROM   ci.npi_iphone b WHERE clean_iPhone_model <> 'iPhone-' {EXCL}
           GROUP  BY clean_iPhone_model, clean_bookdate) x
    WHERE n >= 100 GROUP BY clean_iPhone_model)
SELECT op.m AS รุ่น, op.d_open AS เปิดจอง,
       COUNT_BIG(*) AS ใบจอง_3วัน, SUM(b.booking_qty) AS ชิ้น,
       CAST(SUM(b.srp) / 1000000.0 AS decimal(12,1)) AS มูลค่า_ล้านบาท,
       COUNT(DISTINCT b.booking_branch) AS สาขา
FROM   ci.npi_iphone b JOIN op ON op.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, op.d_open, b.clean_bookdate) BETWEEN 0 AND 2 {EXCL}
GROUP  BY op.m, op.d_open ORDER BY op.m""").to_string(index=False))
