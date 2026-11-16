# -*- coding: utf-8 -*-
"""EV7 Taxi — ดึง GPS จากฐาน EV7 โดยตรง (incremental) เข้าที่เก็บของแอป + ตารางสรุปสำหรับเว็บ

    python scripts/taxi/ev7_sync.py sync [--max-rows N]     ดึงแถวใหม่ (ID > watermark) → upsert → อัปเดตตารางสรุป
    python scripts/taxi/ev7_sync.py init --from-days D     ที่เก็บใหม่: เริ่ม watermark ย้อนหลัง D วันโดยประมาณ (ไม่ดึงทั้ง 41M แถว)
    python scripts/taxi/ev7_sync.py status

ต้นทาง   ฐาน EV7 · dbo.EV7_SMARTTAXI_TRACKING · profile `ev7` (env EV7DB_USER / EV7DB_PWD)
         แถวเพิ่มอย่างเดียว (UPDATED_AT ว่างทุกแถว · ใส่โดย api.service) · ~650k แถว/วัน · PK = ID
         API poll ทุก ~4:40 นาที คืน "จุดล่าสุด" ของทุกคัน → รถที่ขาดสัญญาณส่งจุดเดิมซ้ำทุกรอบ
ที่เก็บ   env EV_APP_STORE_URL (SQLAlchemy) · default SQLite scripts/taxi/_out/ev7_app/ev7.db
         ใช้ MySQL บนเครื่อง SSOT ได้ เช่น mysql+pymysql://user:pwd@host/ev7_app

การรองรับข้อมูลอัปเดต
  1. ดึงเฉพาะ ID ใหม่ (watermark ใน ev_sync_state) ทีละ 200,000 แถว
  2. ev_points คีย์ (vin, gps_time) — จุดที่ส่งซ้ำไม่เพิ่มแถว แค่อัปเดต last_seen_at / seen_count
  3. คำนวณ ev_car_daily ใหม่เฉพาะ (vin, วัน) ที่มีจุดใหม่ — จุดที่มาช้าข้ามวันก็ถูกนับในวันของมัน
  4. ev_car_latest อัปเดตเฉพาะคันที่มีจุดใหม่ (จุดใหม่กว่าเท่านั้น)
"""
import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import sqlalchemy as sa

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import db                                   # noqa: E402

SRC_TABLE = os.environ.get("EV_SRC_TABLE", "dbo.EV7_SMARTTAXI_TRACKING")
BATCH = 200_000
GLITCH_KMH = 200
FUTURE_TOL = pd.Timedelta(minutes=10)        # gps_time เกินเวลาบันทึกเกินนี้ = นาฬิกาอุปกรณ์เพี้ยน
TH_BBOX = (5.5, 20.6, 97.3, 105.7)           # lat_min, lat_max, lon_min, lon_max
SRC = {"ID": "id", "SMARTTAXI_ID_CAR": "car_id", "SMARTTAXI_BODYCAR_NUMBER": "vin", "SMARTTAXI_REGISTER_ID": "plate",
       "SMARTTAXI_HEADER_CENTER": "center", "SMARTTAXI_CM_METER": "meter", "SMARTTAXI_CM_ENGINE": "engine",
       "SMARTTAXI_CM_BATTERY": "battery", "SMARTTAXI_SIGNAL_GPS": "signal", "SMARTTAXI_LA_GOOGLE": "lat",
       "SMARTTAXI_LONG_GOOGLE": "lon", "SMARTTAXI_FAST": "speed", "SMARTTAXI_DIRECTION": "direction", "CREATED_AT": "created_at"}

md = sa.MetaData()
S = lambda n: sa.String(n)                   # noqa: E731
t_points = sa.Table("ev_points", md,
    sa.Column("vin", S(32), primary_key=True), sa.Column("gps_time", sa.DateTime, primary_key=True),
    sa.Column("id", sa.BigInteger), sa.Column("car_id", S(16)), sa.Column("plate", S(32)), sa.Column("center", S(8)),
    sa.Column("lat", sa.Float), sa.Column("lon", sa.Float), sa.Column("speed", sa.Float), sa.Column("direction", sa.Float),
    sa.Column("signal", S(2)), sa.Column("meter", S(2)), sa.Column("engine", S(2)), sa.Column("battery", S(8)),
    sa.Column("first_seen_at", sa.DateTime), sa.Column("last_seen_at", sa.DateTime), sa.Column("seen_count", sa.Integer),
    sa.Index("ix_points_gps_time", "gps_time"))
t_latest = sa.Table("ev_car_latest", md,
    sa.Column("vin", S(32), primary_key=True), sa.Column("plate", S(32)), sa.Column("center", S(8)), sa.Column("car_id", S(16)),
    sa.Column("gps_time", sa.DateTime), sa.Column("lat", sa.Float), sa.Column("lon", sa.Float), sa.Column("speed", sa.Float),
    sa.Column("signal", S(2)), sa.Column("meter", S(2)), sa.Column("engine", S(2)), sa.Column("battery", S(8)),
    sa.Column("last_poll_at", sa.DateTime))
t_daily = sa.Table("ev_car_daily", md,
    sa.Column("vin", S(32), primary_key=True), sa.Column("day", sa.Date, primary_key=True),
    sa.Column("points", sa.Integer), sa.Column("km", sa.Float), sa.Column("drive_min", sa.Float), sa.Column("occupied_min", sa.Float),
    sa.Column("battery_min", sa.Float), sa.Column("battery_max", sa.Float), sa.Column("first_time", sa.DateTime), sa.Column("last_time", sa.DateTime),
    sa.Column("updated_at", sa.DateTime))
t_state = sa.Table("ev_sync_state", md, sa.Column("k", S(64), primary_key=True), sa.Column("v", S(64)))


def store():
    url = os.environ.get("EV_APP_STORE_URL")
    if not url:
        p = HERE / "_out" / "ev7_app"; p.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{(p / 'ev7.db').as_posix()}"
    eng = sa.create_engine(url, future=True)
    md.create_all(eng)
    return eng


def st_get(eng, k, default=None):
    with eng.connect() as c:
        v = c.execute(sa.select(t_state.c.v).where(t_state.c.k == k)).scalar()
    return default if v is None else v


def st_set(c, k, v):
    c.execute(t_state.delete().where(t_state.c.k == k)); c.execute(t_state.insert().values(k=k, v=str(v)))


# ── อ่านต้นทาง ─────────────────────────────────────────────────────
def fetch(cn, wm, n):
    cols = ", ".join(list(SRC) + ["SMARTTAXI_DATE", "SMARTTAXI_TIME"])
    cur = cn.cursor()
    cur.execute(f"SELECT TOP ({int(n)}) {cols} FROM {SRC_TABLE} WITH (NOLOCK) WHERE ID > ? ORDER BY ID", wm)
    df = pd.DataFrame.from_records(cur.fetchall(), columns=[c[0] for c in cur.description])
    if df.empty:
        return df
    df["gps_time"] = pd.to_datetime(df.pop("SMARTTAXI_DATE").astype(str).str[:10] + " " + df.pop("SMARTTAXI_TIME").astype(str).str[:8], errors="coerce")
    df = df.rename(columns=SRC)
    for c in ["lat", "lon", "speed", "direction"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["car_id", "vin", "plate", "center", "signal", "meter", "engine", "battery"]:
        df[c] = df[c].astype("string").str.strip()
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    return df


# ── upsert จุด (vin, gps_time) ─────────────────────────────────────
def upsert_points(c, df):
    """คืน (แถวใหม่, แถวซ้ำ) · จุดซ้ำอัปเดต last_seen_at / seen_count"""
    d = df.dropna(subset=["vin", "gps_time"])
    d = d[d.vin.str.len() > 0]
    g = d.sort_values("id").groupby(["vin", "gps_time"], as_index=False)
    batch = g.first().assign(first_seen_at=g.created_at.min().created_at.values, last_seen_at=g.created_at.max().created_at.values,
                             seen_count=g.size()["size"].values).drop(columns="created_at")
    keys = batch[["vin", "gps_time"]]
    lo, hi = batch.gps_time.min(), batch.gps_time.max()
    have = pd.read_sql(sa.select(t_points.c.vin, t_points.c.gps_time, t_points.c.seen_count, t_points.c.last_seen_at)
                       .where(t_points.c.gps_time.between(lo, hi), t_points.c.vin.in_(keys.vin.unique().tolist())), c)
    m = batch.merge(have, on=["vin", "gps_time"], how="left", suffixes=("", "_old"), indicator=True)
    new = m[m._merge == "left_only"][batch.columns]
    old = m[m._merge == "both"]
    if len(new):
        c.execute(t_points.insert(), new.astype(object).where(new.notna(), None).to_dict("records"))
    if len(old):
        upd = [{"b_vin": r.vin, "b_t": r.gps_time, "ls": max(r.last_seen_at, r.last_seen_at_old), "n": int(r.seen_count + r.seen_count_old)}
               for r in old.itertuples()]
        c.execute(t_points.update().where(t_points.c.vin == sa.bindparam("b_vin"), t_points.c.gps_time == sa.bindparam("b_t"))
                  .values(last_seen_at=sa.bindparam("ls"), seen_count=sa.bindparam("n")), upd)
    return len(new), int(len(d) - len(new)), new


# ── สรุปรายคันรายวัน (เฉพาะ vin/วัน ที่มีจุดใหม่) ──────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    r = np.pi / 180
    a = np.sin((lat2 - lat1) * r / 2) ** 2 + np.cos(lat1 * r) * np.cos(lat2 * r) * np.sin((lon2 - lon1) * r / 2) ** 2
    return 12742 * np.arcsin(np.sqrt(a))


def rebuild_daily(c, touched):
    if touched.empty:
        return 0
    lo, hi = pd.Timestamp(touched.day.min()), pd.Timestamp(touched.day.max()) + pd.Timedelta(days=1)
    p = pd.read_sql(sa.select(t_points.c.vin, t_points.c.gps_time, t_points.c.lat, t_points.c.lon, t_points.c.signal,
                              t_points.c.meter, t_points.c.engine, t_points.c.battery, t_points.c.first_seen_at)
                    .where(t_points.c.gps_time >= lo, t_points.c.gps_time < hi, t_points.c.vin.in_(touched.vin.unique().tolist())), c)
    p = p[p.gps_time <= p.first_seen_at + FUTURE_TOL]                    # ตัดเวลาอนาคต (นาฬิกาอุปกรณ์เพี้ยน)
    p["day"] = p.gps_time.dt.date
    p = p.merge(touched, on=["vin", "day"])
    p = p.sort_values(["vin", "gps_time"])
    ok = (p.signal == "A") & p.lat.between(*TH_BBOX[:2]) & p.lon.between(*TH_BBOX[2:])
    q = p[ok].copy()
    same = (q.vin == q.vin.shift()) & (q.day == q.day.shift())
    dt_h = (q.gps_time - q.gps_time.shift()).dt.total_seconds() / 3600
    km = haversine_km(q.lat.shift(), q.lon.shift(), q.lat, q.lon)
    km = np.where(same & (dt_h > 0) & (km / dt_h.replace(0, np.nan) < GLITCH_KMH) & (dt_h < 1), km, 0)
    gap_min = np.where(same & (dt_h < 0.5), dt_h * 60, 0)              # นับเวลาเฉพาะช่วงห่าง < 30 นาที
    q = q.assign(km=km, drive=np.where(q.engine.shift() == "0", gap_min, 0), occ=np.where(q.meter.shift() == "F", gap_min, 0),
                 bat=pd.to_numeric(q.battery, errors="coerce"))
    agg = p.groupby(["vin", "day"]).agg(points=("gps_time", "size"), first_time=("gps_time", "min"), last_time=("gps_time", "max"))
    agg = agg.join(q.groupby(["vin", "day"]).agg(km=("km", "sum"), drive_min=("drive", "sum"), occupied_min=("occ", "sum"),
                                                 battery_min=("bat", "min"), battery_max=("bat", "max"))).reset_index()
    agg["updated_at"] = datetime.now().replace(microsecond=0)
    keys = list(touched.itertuples(index=False, name=None))
    for i in range(0, len(keys), 500):
        part = keys[i:i + 500]
        c.execute(t_daily.delete().where(sa.tuple_(t_daily.c.vin, t_daily.c.day).in_(part)))
    c.execute(t_daily.insert(), agg.astype(object).where(agg.notna(), None).to_dict("records"))
    return len(agg)


def update_latest(c, new):
    new = new[new.gps_time <= new.first_seen_at + FUTURE_TOL]          # นาฬิกาอุปกรณ์เพี้ยน (เวลาอนาคต) ไม่ใช้เป็นตำแหน่งล่าสุด
    if new.empty:
        return 0
    last = new.sort_values("gps_time").groupby("vin").tail(1)
    cur = pd.read_sql(sa.select(t_latest.c.vin, t_latest.c.gps_time).where(t_latest.c.vin.in_(last.vin.tolist())), c)
    m = last.merge(cur, on="vin", how="left", suffixes=("", "_cur"))
    m = m[m.gps_time_cur.isna() | (m.gps_time > m.gps_time_cur)]
    if m.empty:
        return 0
    c.execute(t_latest.delete().where(t_latest.c.vin.in_(m.vin.tolist())))
    rows = m.rename(columns={"last_seen_at": "last_poll_at"})[[x.name for x in t_latest.columns]]
    c.execute(t_latest.insert(), rows.astype(object).where(rows.notna(), None).to_dict("records"))
    return len(m)


# ── คำสั่ง ─────────────────────────────────────────────────────────
def sync(eng, max_rows=None):
    cn = db.connect("ev7", timeout=600)
    wm = int(st_get(eng, "max_id", 0)); total = 0; t0 = time.time()
    while True:
        df = fetch(cn, wm, BATCH if not max_rows else min(BATCH, max_rows - total))
        if df.empty:
            break
        with eng.begin() as c:
            n_new, n_dup, new = upsert_points(c, df)
            touched = new.assign(day=new.gps_time.dt.date)[["vin", "day"]].drop_duplicates()
            n_day = rebuild_daily(c, touched)
            n_lat = update_latest(c, new)
            wm = int(df.id.max()); st_set(c, "max_id", wm); st_set(c, "synced_at", datetime.now().replace(microsecond=0))
        total += len(df)
        late = int((touched.day < pd.Timestamp.now().date()).sum()) if len(touched) else 0
        print(f"  +{len(df):,} แถว · จุดใหม่ {n_new:,} · ซ้ำ {n_dup:,} · สรุปรายวันที่คำนวณใหม่ {n_day:,} (วันก่อนหน้า {late:,}) · latest {n_lat:,} · id {wm:,} · {time.time() - t0:,.0f}s", flush=True)
        if max_rows and total >= max_rows:
            break
    print(f"sync: {total:,} แถว · watermark {wm:,} · {time.time() - t0:,.0f}s")


def init(eng, days):
    cn = db.connect("ev7", timeout=600); cur = cn.cursor()
    cur.execute(f"SELECT MAX(ID) FROM {SRC_TABLE} WITH (NOLOCK)"); mx = int(cur.fetchone()[0])
    start = max(mx - int(days * 650_000), 0)                 # ~650k แถว/วัน
    with eng.begin() as c:
        st_set(c, "max_id", start)
    print(f"init: watermark = {start:,} (ID ล่าสุด {mx:,} · ย้อนประมาณ {days} วัน)")


def status(eng):
    with eng.connect() as c:
        for t in ["ev_points", "ev_car_latest", "ev_car_daily"]:
            print(f"{t:<15}", c.execute(sa.text(f"SELECT COUNT(*) FROM {t}")).scalar())
        print(dict(c.execute(sa.select(t_state.c.k, t_state.c.v)).all()))
        print("gps range", c.execute(sa.text("SELECT MIN(gps_time), MAX(gps_time) FROM ev_points")).one())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["sync", "init", "status"])
    ap.add_argument("--from-days", type=float, default=2)
    ap.add_argument("--max-rows", type=int)
    a = ap.parse_args()
    eng = store()
    {"sync": lambda: sync(eng, a.max_rows), "init": lambda: init(eng, a.from_days), "status": lambda: status(eng)}[a.cmd]()


if __name__ == "__main__":
    main()
