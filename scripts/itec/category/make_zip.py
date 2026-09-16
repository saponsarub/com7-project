# -*- coding: utf-8 -*-
"""รวมสคริปต์เป็น zip สำหรับอัปขึ้น Colab

zip เป็นสำเนา ไม่ใช่ตัวจริง - แก้โค้ดแล้วต้องรันตัวนี้ใหม่ทุกครั้งก่อนอัป

    python make_zip.py
"""
import sys
import zipfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass          # Jupyter/Colab ไม่มีเมธอดนี้ และไม่ต้องใช้

HERE = Path(__file__).parent
OUT = Path(__file__).parent / "itec_category_scripts.zip"   # อยู่โฟลเดอร์เดียวกัน หาง่าย

# ทุกไฟล์ที่ notebook เรียกใช้ · ลำดับตามความสำคัญ
FILES = [
    "type_platform.py",      # Cell 6 import ตรง ๆ
    "type_platform.yaml",    # กฎที่แก้เองได้
    "itec_mapper.py",        # predict_all / explore_flags ใช้
    "rules.py",
    "item_keywords.yaml",
    "predict_all.py",        # Cell C
    "explore_flags.py",      # Cell B
    "benchmark_models.py",   # Cell D
    "extract_keywords.py",
]



def main():
    missing = [f for f in FILES if not (HERE / f).exists()]
    if missing:
        sys.exit(f"ไม่พบไฟล์: {missing}")

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in FILES:
            z.write(HERE / f, f)

    print(f"เขียน {OUT}")
    newest = max((HERE / f).stat().st_mtime for f in FILES)
    for f in FILES:
        p = HERE / f
        t = datetime.fromtimestamp(p.stat().st_mtime).strftime("%m-%d %H:%M")
        print(f"  {p.stat().st_size:>6,}  {t}  {f}")
    print(f"\nรวม {OUT.stat().st_size:,} bytes · "
          f"ไฟล์ใหม่สุดแก้เมื่อ "
          f"{datetime.fromtimestamp(newest).strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
