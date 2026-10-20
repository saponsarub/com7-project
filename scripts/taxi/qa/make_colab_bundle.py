# -*- coding: utf-8 -*-
"""ทำชุดข้อมูลสำหรับรัน taxi_qa_colab.ipynb บน Google Colab

    python scripts/taxi/qa/make_colab_bundle.py                 ทะเบียนสมมติ EV-xxxx
    python scripts/taxi/qa/make_colab_bundle.py --real-plates   ทะเบียนจริง → taxi_qa_data_REAL.zip
                                                                (ถามตอบด้วยทะเบียนจริง · ข้อมูลส่วนบุคคล อัปโหลดเฉพาะที่ได้รับอนุมัติ)

ผลลัพธ์  D:\\Taxi\\colab\\taxi_qa_data.zip      ← อัปโหลดอันนี้ขึ้น Drive / Colab
         D:\\Taxi\\colab\\plate_map_LOCAL.csv   ← ตารางจับคู่ EV-xxxx ↔ ทะเบียนจริง · ห้ามอัปโหลด

ทำไมต้องแปลง: Colab / Google Drive = cloud ภายนอก · ทะเบียน + VIN + ตำแหน่ง เป็นข้อมูลส่วนบุคคล
  - ทะเบียน → รหัสสมมติ EV-0001 ... (สุ่มลำดับ ไม่เรียงตามทะเบียน)
  - 1 คัน = 1 VIN → รหัสสมมติ (คอลัมน์ car_id) · ตัด VIN / ศูนย์ / created_by ทิ้ง
  - พิกัดยังอยู่ (จำเป็นต่อการตอบคำถาม) → ยังถือเป็นข้อมูลอ่อนไหว ใช้ Drive ขององค์กรเท่านั้น
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

TAXI = Path(__file__).resolve().parent.parent
OUT = TAXI / "_out"
MASTER = Path(r"D:\Master")
DEST = Path(r"D:\Taxi\colab")
DEST.mkdir(parents=True, exist_ok=True)

cols = ["vin", "plate", "meter", "signal", "lat", "lon", "speed", "direction", "gps_time", "dist"]
d = pd.read_parquet(OUT / "points_clean.parquet", columns=cols)

# คีย์ประจำรถ = VIN (car_id ซ้ำกันได้ถึง 3 คัน — ดู build_dashboard.py)
cars = d[["vin", "plate"]].drop_duplicates("vin").sample(frac=1, random_state=20261014).reset_index(drop=True)
cars["pseudo"] = [f"EV-{i:04d}" for i in range(1, len(cars) + 1)]
m = dict(zip(cars.vin, cars.pseudo))
d["car_id"] = d.vin.map(m)
REAL = "--real-plates" in sys.argv
if not REAL:
    d["plate"] = d.car_id                               # ทะเบียนสมมติ = รหัสเดียวกัน
d = d.drop(columns="vin")                               # VIN ไม่ออกไปทั้งสองแบบ
cars[["pseudo", "vin", "plate"]].to_csv(DEST / "plate_map_LOCAL.csv", index=False, encoding="utf-8-sig")

tmp = DEST / "taxi_qa"
shutil.rmtree(tmp, ignore_errors=True)
tmp.mkdir()
d.to_parquet(tmp / "points.parquet", index=False)
shutil.copy(OUT / "dist_pip.geojson", tmp / "dist_pip.geojson")
shutil.copy(OUT / "ev_chargers_osm.json", tmp / "ev_chargers_osm.json")
shutil.copy(MASTER / "dim_province.csv", tmp / "dim_province.csv")

zp = DEST / ("taxi_qa_data_REAL.zip" if REAL else "taxi_qa_data.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in tmp.iterdir():
        z.write(f, f.name)
if not REAL:
    assert not d.plate.str.contains(r"[ก-ฮ]").any(), "ยังมีทะเบียนจริงหลุด"
else:
    print("⚠️ ชุดนี้มีทะเบียนจริง + ตำแหน่ง = ข้อมูลส่วนบุคคล · dataset ต้องเป็น Private · อัปโหลดเฉพาะที่ได้รับอนุมัติ")
print(f"{zp} · {zp.stat().st_size / 1e6:.1f} MB · {len(d):,} จุด · {len(cars):,} คัน")
print(f"ตารางจับคู่ (ห้ามอัปโหลด) → {DEST / 'plate_map_LOCAL.csv'}")
