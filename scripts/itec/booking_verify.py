# -*- coding: utf-8 -*-
"""ตรวจความถูกต้องรอบสอง + ดึงข้อมูลสำหรับ dashboard ผู้บริหาร — read-only

    python scripts/itec/booking_verify.py

ผลลัพธ์ -> scripts/itec/_out/booking_*.csv  (ใช้สร้าง dashboard และ import Power BI)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
import db                                                     # noqa: E402

OUT = Path(__file__).parent / "_out"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 210)
pd.set_option("display.max_rows", 200)
Q = lambda s: db.query("itec", s)                             # noqa: E731

# วันเปิดตัวที่ยืนยันแล้วจากข้อมูล + ที่ผู้ใช้ให้มา
LAUNCH = """(VALUES
    ('iPhone-15','2023-09-15','2023-09-22'),
    ('iPhone-16','2024-09-13','2024-09-20'),
    ('iPhone-17','2025-09-12','2025-09-19'),
    ('iPhone-18','2026-09-12','2026-09-18')) AS L(m, d_open, d_sale)"""
CLEAN = "AND b.Model NOT LIKE 'DUMMY%'"


def head(t):
    print("\n" + "═" * 76)
    print(" " + t)
    print("═" * 76)


def save(df, name):
    p = OUT / f"booking_{name}.csv"
    df.to_csv(p, index=False, encoding="utf-8-sig")
    print(f"   💾 {p.name}  ({len(df):,} แถว)")
    return df


# ══════════════════════════════════════════════ ตรวจความถูกต้อง ══
head("A · ความครบถ้วนของข้อมูล — มี NULL ตรงไหนบ้าง")
print(Q(f"""
SELECT COUNT_BIG(*) AS แถว,
       SUM(CASE WHEN clean_bookdate  IS NULL THEN 1 ELSE 0 END) AS วันจอง_null,
       SUM(CASE WHEN booking_qty     IS NULL THEN 1 ELSE 0 END) AS จำนวน_null,
       SUM(CASE WHEN srp             IS NULL THEN 1 ELSE 0 END) AS srp_null,
       SUM(CASE WHEN booking_amount  IS NULL THEN 1 ELSE 0 END) AS มัดจำ_null,
       SUM(CASE WHEN book_shop_brand IS NULL THEN 1 ELSE 0 END) AS แบรนด์ร้าน_null,
       SUM(CASE WHEN MemberCode      IS NULL THEN 1 ELSE 0 END) AS สมาชิก_null
FROM   ci.npi_iphone b WHERE 1=1 {CLEAN}""").to_string(index=False))

head("B · ค่าผิดปกติ — จำนวน/ราคาที่เป็นไปไม่ได้")
print(Q(f"""
SELECT SUM(CASE WHEN booking_qty <= 0 THEN 1 ELSE 0 END)      AS จำนวน_ไม่บวก,
       SUM(CASE WHEN booking_qty > 10 THEN 1 ELSE 0 END)      AS จำนวนเกิน10,
       MAX(booking_qty)                                        AS จำนวนสูงสุด,
       SUM(CASE WHEN srp <= 0 THEN 1 ELSE 0 END)              AS srp_ไม่บวก,
       CAST(MIN(NULLIF(srp,0)) AS int)                        AS srp_ต่ำสุด,
       CAST(MAX(srp) AS int)                                   AS srp_สูงสุด,
       SUM(CASE WHEN booking_amount > srp THEN 1 ELSE 0 END)  AS มัดจำเกินราคา
FROM   ci.npi_iphone b WHERE 1=1 {CLEAN}""").to_string(index=False))

head("C · ลำดับเวลา — รับเครื่องก่อนจองได้ไหม")
print(Q(f"""
SELECT SUM(CASE WHEN clean_finishdate < clean_bookdate THEN 1 ELSE 0 END) AS รับก่อนจอง,
       SUM(CASE WHEN finish = 1 AND clean_finishdate IS NULL THEN 1 ELSE 0 END) AS ปิดงานแต่ไม่มีวันรับ,
       SUM(CASE WHEN finish = 0 AND clean_finishdate IS NOT NULL THEN 1 ELSE 0 END) AS มีวันรับแต่ไม่ปิดงาน
FROM   ci.npi_iphone b WHERE 1=1 {CLEAN}""").to_string(index=False))

head("D · ยอดรวมทั้ง 4 รุ่น เทียบ rpt ↔ ci (ต้องตรงกัน)")
print(Q("""
SELECT 'ci.npi_iphone' AS แหล่ง, COUNT_BIG(*) AS แถว, SUM(booking_qty) AS ชิ้น
FROM   ci.npi_iphone WHERE Model NOT LIKE 'DUMMY%'
UNION ALL
SELECT 'rpt (join กลับ)', COUNT_BIG(*), SUM(r.booking_qty)
FROM   rpt.booking_list r
JOIN   ci.npi_iphone c ON c.booking_id=r.booking_id
       AND c.booking_branch=r.booking_branch AND c.product=r.product
WHERE  r.Model NOT LIKE 'DUMMY%'""").to_string(index=False))

# ══════════════════════════════════════════ ข้อมูลสำหรับ dashboard ══
head("E · ดึงข้อมูลสำหรับ dashboard")

save(Q(f"""
SELECT L.m AS model, L.d_open AS open_date, L.d_sale AS sale_date,
       DATEDIFF(day, L.d_open, L.d_sale) AS window_days,
       COUNT_BIG(*) AS bookings, SUM(b.booking_qty) AS units,
       CAST(SUM(b.srp) AS bigint) AS value_thb,
       CAST(AVG(b.srp) AS int) AS avg_price,
       COUNT(DISTINCT b.booking_branch) AS branches,
       SUM(CASE WHEN b.finish = 1 THEN 1 ELSE 0 END) AS completed
FROM   ci.npi_iphone b JOIN {LAUNCH} ON L.m = b.clean_iPhone_model
WHERE  b.clean_bookdate BETWEEN L.d_open AND L.d_sale {CLEAN}
GROUP  BY L.m, L.d_open, L.d_sale ORDER BY L.m"""), "summary")

save(Q(f"""
SELECT L.m AS model, DATEDIFF(day, L.d_open, b.clean_bookdate) AS day_no,
       b.clean_bookdate AS book_date, DATENAME(weekday, b.clean_bookdate) AS weekday,
       COUNT_BIG(*) AS bookings, CAST(SUM(b.srp) AS bigint) AS value_thb
FROM   ci.npi_iphone b JOIN {LAUNCH} ON L.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, L.d_open, b.clean_bookdate) BETWEEN 0 AND 6 {CLEAN}
GROUP  BY L.m, DATEDIFF(day, L.d_open, b.clean_bookdate), b.clean_bookdate,
          DATENAME(weekday, b.clean_bookdate)
ORDER  BY L.m, day_no"""), "daily")

save(Q(f"""
SELECT L.m AS model, b.clean_iPhone_submodel AS submodel,
       COUNT_BIG(*) AS bookings, CAST(SUM(b.srp) AS bigint) AS value_thb
FROM   ci.npi_iphone b JOIN {LAUNCH} ON L.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, L.d_open, b.clean_bookdate) BETWEEN 0 AND 2 {CLEAN}
GROUP  BY L.m, b.clean_iPhone_submodel ORDER BY L.m, bookings DESC"""), "submodel")

save(Q(f"""
SELECT L.m AS model, b.device_memory AS memory,
       COUNT_BIG(*) AS bookings
FROM   ci.npi_iphone b JOIN {LAUNCH} ON L.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, L.d_open, b.clean_bookdate) BETWEEN 0 AND 2 {CLEAN}
GROUP  BY L.m, b.device_memory ORDER BY L.m, bookings DESC"""), "memory")

save(Q(f"""
SELECT L.m AS model, b.book_region_en AS region,
       COUNT_BIG(*) AS bookings, CAST(SUM(b.srp) AS bigint) AS value_thb,
       COUNT(DISTINCT b.booking_branch) AS branches
FROM   ci.npi_iphone b JOIN {LAUNCH} ON L.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, L.d_open, b.clean_bookdate) BETWEEN 0 AND 2
       AND b.book_region_en IS NOT NULL {CLEAN}
GROUP  BY L.m, b.book_region_en ORDER BY L.m, bookings DESC"""), "region")

save(Q(f"""
SELECT L.m AS model, b.book_shop_brand AS shop_brand,
       COUNT_BIG(*) AS bookings, CAST(SUM(b.srp) AS bigint) AS value_thb
FROM   ci.npi_iphone b JOIN {LAUNCH} ON L.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, L.d_open, b.clean_bookdate) BETWEEN 0 AND 2
       AND b.book_shop_brand IS NOT NULL {CLEAN}
GROUP  BY L.m, b.book_shop_brand ORDER BY L.m, bookings DESC"""), "shopbrand")

save(Q(f"""
SELECT L.m AS model, b.device_color AS color, COUNT_BIG(*) AS bookings
FROM   ci.npi_iphone b JOIN {LAUNCH} ON L.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, L.d_open, b.clean_bookdate) BETWEEN 0 AND 2
       AND b.clean_iPhone_submodel = 'Pro Max' {CLEAN}
GROUP  BY L.m, b.device_color ORDER BY L.m, bookings DESC"""), "color")

save(Q(f"""
SELECT L.m AS model, b.installment_type AS pay_type, COUNT_BIG(*) AS bookings
FROM   ci.npi_iphone b JOIN {LAUNCH} ON L.m = b.clean_iPhone_model
WHERE  DATEDIFF(day, L.d_open, b.clean_bookdate) BETWEEN 0 AND 2 {CLEAN}
GROUP  BY L.m, b.installment_type ORDER BY L.m, bookings DESC"""), "paytype")

print("\nเสร็จ — ไฟล์อยู่ที่", OUT)
