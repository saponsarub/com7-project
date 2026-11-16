# -*- coding: utf-8 -*-
"""ทดสอบกติกา outzone ด้วยข้อมูลจำลอง (ไม่ใช้ข้อมูลจริง)   python scripts/taxi/outzone_test.py"""
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import outzone as oz

BKK = (13.7563, 100.5018)     # กรุงเทพฯ
NBI = (13.8621, 100.5144)     # นนทบุรี (ปริมณฑล)
AYA = (14.3532, 100.5689)     # อยุธยา (นอกเขต)
CNX = (18.7883, 98.9853)      # เชียงใหม่
T0 = datetime(2026, 11, 1, 8, 0)
_id = [0]


def pts(vin, where, start, hours, every_min=60, signal="A"):
    rows = []
    t = start
    while t <= start + timedelta(hours=hours):
        _id[0] += 1
        rows.append(dict(id=_id[0], vin=vin, plate=f"ท-{vin}", car_id=vin, gps_time=t,
                         lat=where[0], lon=where[1], signal=signal))
        t += timedelta(minutes=every_min)
    return rows


def run(rows, as_of, eng=None):
    eng = eng or oz.store(f"sqlite:///{tempfile.mktemp(suffix='.db')}")
    df = pd.DataFrame(rows)
    oz.append_log(eng, oz.normalize(df.assign(created_at=None)))
    with eng.begin() as c:
        oz.job_set(c, "extract_max_id", int(df["id"].max()))
    return eng, {a["vin"]: a for a in oz.analyze(eng, as_of, ZONE)}


ZONE = oz.Zone()
ok = True
def check(name, cond):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


assert ZONE.inside([BKK[1], NBI[1]], [BKK[0], NBI[0]]).all() and not ZONE.inside([AYA[1]], [AYA[0]]).any()

# 1 · ออกไปเชียงใหม่ 6 วัน → แจ้ง
r = pts("A1", BKK, T0, 10) + pts("A1", CNX, T0 + timedelta(hours=11), 6 * 24)
_, al = run(r, T0 + timedelta(days=6, hours=12))
check("1 นอกเขต 6 วัน → แจ้ง", "A1" in al and 120 < al["A1"]["hours_out"] < 150 and not al["A1"]["out_since_is_first_seen"])

# 2 · นอกเขต 4 วัน → ไม่แจ้ง
r = pts("A2", BKK, T0, 10) + pts("A2", AYA, T0 + timedelta(hours=11), 4 * 24)
_, al = run(r, T0 + timedelta(days=4, hours=12))
check("2 นอกเขต 4 วัน → ไม่แจ้ง", "A2" not in al)

# 3 · จุดกระโดดเข้าเขตจุดเดียวระหว่างทาง → ไม่รีเซ็ต
r = pts("A3", BKK, T0, 10) + pts("A3", CNX, T0 + timedelta(hours=11), 3 * 24) \
    + pts("A3", BKK, T0 + timedelta(hours=11 + 72, minutes=30), 0) + pts("A3", CNX, T0 + timedelta(hours=11 + 73), 3 * 24)
_, al = run(r, T0 + timedelta(days=6, hours=12))
check("3 จุดในเขตจุดเดียว ไม่นับว่ากลับ", "A3" in al and al["A3"]["hours_out"] > 140)

# 4 · กลับเข้าเขตจริง (หลายจุด) → รีเซ็ต
r = pts("A4", CNX, T0, 5 * 24) + pts("A4", BKK, T0 + timedelta(days=5, hours=1), 24)
_, al = run(r, T0 + timedelta(days=6, hours=2))
check("4 กลับเข้าเขต → ไม่แจ้ง", "A4" not in al)

# 5 · ข้อมูลหาย 4 วันขณะอยู่นอกเขต → ยังนับต่อ + ติดป้ายขาดสัญญาณ
r = pts("A5", BKK, T0, 10) + pts("A5", AYA, T0 + timedelta(hours=11), 24)
_, al = run(r, T0 + timedelta(days=6))
check("5 ขาดสัญญาณขณะอยู่นอกเขต → นับต่อ + stale", "A5" in al and al["A5"]["stale"])

# 6 · จุด signal V ในเขต ไม่นับว่ากลับ
r = pts("A6", BKK, T0, 10) + pts("A6", CNX, T0 + timedelta(hours=11), 3 * 24) \
    + pts("A6", BKK, T0 + timedelta(hours=11 + 72, minutes=10), 2, signal="V") + pts("A6", CNX, T0 + timedelta(hours=11 + 75), 3 * 24)
_, al = run(r, T0 + timedelta(days=6, hours=14))
check("6 จุด V ในเขต ไม่นับว่ากลับ", "A6" in al)

# 7 · ไม่เคยเห็นในเขตเลย → แจ้งแบบ "อย่างน้อย"
_, al = run(pts("A7", CNX, T0, 6 * 24), T0 + timedelta(days=6, hours=1))
check("7 ไม่เคยเห็นในเขต → out_since_is_first_seen", "A7" in al and al["A7"]["out_since_is_first_seen"])

# 8 · รันทีละวัน (incremental) ได้ผลเท่ารันทีเดียว + แจ้งซ้ำทุกวัน
full = pts("A8", BKK, T0, 10) + pts("A8", CNX, T0 + timedelta(hours=11), 8 * 24)
eng = oz.store(f"sqlite:///{tempfile.mktemp(suffix='.db')}")
days = []
for d in range(1, 9):
    cut = T0 + timedelta(days=d)
    chunk = [p for p in full if cut - timedelta(days=1) < p["gps_time"] <= cut] if d > 1 else [p for p in full if p["gps_time"] <= cut]
    _, al = run(chunk, cut, eng)
    days.append("A8" in al)
_, one = run(full, T0 + timedelta(days=8))
with eng.connect() as c:
    n_days = c.execute(oz.sa.select(oz.sa.func.count()).select_from(oz.t_alert).where(oz.t_alert.c.vin == "A8")).scalar()
check("8 incremental = full · แจ้งวันที่ 6,7,8", days == [False] * 5 + [True] * 3 and n_days == 3
      and abs(al["A8"]["hours_out"] - one["A8"]["hours_out"]) < 0.01)

# 9 · ข้อความ LINE
msg = oz.messages(list(one.values()), T0.date())
check("9 ข้อความ LINE ไม่เกิน 5,000 ตัว", msg and all(len(m) <= 5000 for m in msg))
print(msg[0])
print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
