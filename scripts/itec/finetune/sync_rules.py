# -*- coding: utf-8 -*-
"""ดึงกฎจัดหมวดจากโปรเจกต์ category มาไว้ที่นี่ + รวมเป็น zip สำหรับ Kaggle

โปรเจกต์นี้แยกจาก category แต่ยังต้องใช้ "กฎ" ชุดเดียวกันเพื่อสร้าง label
จึงคัดลอกมาตอน build ไม่ได้เขียนกฎซ้ำ - กฎมีที่เดียวคือ ../category/

    python sync_rules.py
"""
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = Path(__file__).parent
SRC = HERE.parent / "category"
ZIP = HERE / "itec_finetune_scripts.zip"

# ไฟล์ที่ต้องดึงมาจาก category - ห้ามแก้ที่นี่ แก้ที่ต้นทาง
FROM_CATEGORY = ["type_platform.py", "type_platform.yaml"]
# ไฟล์ของโปรเจกต์นี้เอง
OWN = ["finetune.py"]


def main():
    missing = [f for f in FROM_CATEGORY if not (SRC / f).exists()]
    if missing:
        sys.exit(f"ไม่พบใน {SRC}: {missing}")

    for f in FROM_CATEGORY:
        shutil.copy2(SRC / f, HERE / f)
        print(f"  คัดลอก  {f}  <-  ../category/")

    files = FROM_CATEGORY + OWN
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(HERE / f, f)

    print(f"\nเขียน {ZIP}")
    for f in files:
        p = HERE / f
        t = datetime.fromtimestamp(p.stat().st_mtime).strftime("%m-%d %H:%M")
        print(f"  {p.stat().st_size:>6,}  {t}  {f}")
    newest = max((HERE / f).stat().st_mtime for f in files)
    print(f"\nรวม {ZIP.stat().st_size:,} bytes · ไฟล์ใหม่สุดแก้เมื่อ "
          f"{datetime.fromtimestamp(newest).strftime('%Y-%m-%d %H:%M')}")
    print("\n⚠️ type_platform.* เป็นสำเนา - แก้กฎให้แก้ที่ ../category/ แล้วรันตัวนี้ใหม่")


if __name__ == "__main__":
    main()
