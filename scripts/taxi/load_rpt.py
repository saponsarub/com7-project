# -*- coding: utf-8 -*-
"""แปลง smarttaxi.rpt (ผลลัพธ์ SSMS แบบ fixed-width) เป็น parquet

    python scripts/taxi/load_rpt.py [path_to_rpt]

.rpt คือไฟล์ที่ SSMS เขียนตอนเลือก "Results to File"
  บรรทัด 1 = ชื่อคอลัมน์ · บรรทัด 2 = ขีด ---- บอกความกว้างแต่ละคอลัมน์
  ท้ายไฟล์มี "(N rows affected)" และ "Completion time" ต้องตัดทิ้ง
  ค่าว่างเขียนเป็นสตริง 'NULL'
"""
import re
import sys
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else r"D:\Taxi\smarttaxi.rpt")
OUT = Path(__file__).resolve().parent / "_out" / "smarttaxi.parquet"

with open(SRC, encoding="utf-8-sig") as f:
    hdr = f.readline().rstrip("\r\n")
    dash = f.readline().rstrip("\r\n")
spans = [(m.start(), m.end()) for m in re.finditer(r"-+", dash)]
names = [hdr[a:b].strip() for a, b in spans]

print(f"อ่าน {SRC} ...", flush=True)
df = pd.read_fwf(SRC, colspecs=spans, names=names, skiprows=2, dtype=str,
                 encoding="utf-8-sig", na_values=["NULL"], keep_default_na=False)
# ตัดบรรทัดท้ายไฟล์ที่ไม่ใช่ข้อมูล
df = df[df["ID"].str.fullmatch(r"\d+", na=False)]

ren = {c: c.replace("SMARTTAXI_", "").lower() for c in df.columns}
ren["SMARTTAXI_REFISTER_ID"] = "plate"          # ทะเบียนรถ (ชื่อคอลัมน์ต้นทางสะกดผิด)
ren["SMARTTAXI_BODYCAR_NUMBER"] = "vin"
ren["SMARTTAXI_ID_CAR"] = "car_id"
ren["SMARTTAXI_LA_GOOGLE"] = "lat"
ren["SMARTTAXI_LONG_GOOGLE"] = "lon"
ren["SMARTTAXI_FAST"] = "speed"
df = df.rename(columns=ren)

df["id"] = df["id"].astype("int64")
for c in ["lat", "lon", "speed", "direction"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["gps_time"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")
df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
df = df.drop(columns=["date", "time", "updated_by", "updated_at"])

OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(OUT, index=False)
print(f"เขียน {OUT} · {len(df):,} แถว · {len(df.columns)} คอลัมน์")
print(df.dtypes.to_string())
