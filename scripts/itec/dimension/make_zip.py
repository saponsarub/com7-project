# -*- coding: utf-8 -*-
"""รวมไฟล์ที่ต้องอัปขึ้น Colab/Kaggle เป็น zip เดียว

    python make_zip.py

ไม่ใส่ _data/ เข้าไป — ไฟล์ CSV 36 MB ควรอัปแยกเป็น .csv.gz
"""
import sys
import zipfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = Path(__file__).parent
ZIP = HERE / "itec_dimension_scripts.zip"
FILES = ["dimension.py", "rules.yaml"]

missing = [f for f in FILES if not (HERE / f).exists()]
assert not missing, f"ไม่พบ {missing} · รัน Cell 3 ในโน้ตบุ๊กก่อนเพื่อสร้าง rules.yaml"

with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for f in FILES:
        z.write(HERE / f, f)

print(f"เขียน {ZIP}")
newest = datetime.min
for i in sorted(zipfile.ZipFile(ZIP).infolist(), key=lambda x: -x.file_size):
    print(f"  {i.file_size:>7,}  {i.filename}")
    newest = max(newest, datetime(*i.date_time))
print(f"\nรวม {ZIP.stat().st_size:,} bytes · ไฟล์ใหม่สุดแก้เมื่อ {newest:%Y-%m-%d %H:%M}")
print()
print("อัปขึ้น Colab/Kaggle 2 ไฟล์")
print(f"  1. {ZIP.name}")
print("  2. _data/dim_item_itec.csv.gz")
