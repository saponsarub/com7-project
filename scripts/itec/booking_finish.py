# -*- coding: utf-8 -*-
"""ดูการกระจายวันรับเครื่องรอบวันเปิดตัว — ใช้ตัดสินว่าวันขายวันแรกคือวันไหน"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
import db                                                     # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 200)

print(db.query("itec", """
SELECT clean_iPhone_model                    AS รุ่น,
       clean_finishdate                      AS วันรับเครื่อง,
       DATENAME(weekday, clean_finishdate)   AS วัน,
       COUNT_BIG(*)                          AS รับเครื่อง
FROM   ci.npi_iphone
WHERE  clean_iPhone_model IN ('iPhone-15','iPhone-16','iPhone-17')
  AND  MONTH(clean_finishdate) = 9
  AND  DAY(clean_finishdate) BETWEEN 14 AND 26
  AND  YEAR(clean_finishdate) = YEAR(clean_bookdate)
  AND  Model NOT LIKE 'DUMMY%'
GROUP  BY clean_iPhone_model, clean_finishdate, DATENAME(weekday, clean_finishdate)
ORDER  BY รุ่น, วันรับเครื่อง""").to_string(index=False))
