# -*- coding: utf-8 -*-
"""EV7 Taxi — แจ้งเตือนรถอยู่นอกเขต กทม. + ปริมณฑล ติดต่อกันเกิน 120 ชม. (5 วัน)

Requirement (ทีม EV7 · 2026-11-10)
  1. ดึง log GPS ของ Taxi จาก K2 ไปเก็บที่ server ใหม่ (ระหว่างรอ server ฝากไว้ที่ K2 ได้)
  2. วิเคราะห์วันละครั้ง ว่ารถออกนอกเขต กทม. และปริมณฑลเกิน 5 วัน (120 ชม.) ไหม
     ถ้าเกิน ยิง alert ไป LINE OA ทุกวันจนกว่ารถจะกลับเข้าเขต (ไม่มีค่าปรับแล้ว)

คำสั่ง
  python scripts/taxi/outzone.py extract                 ดึงแถวใหม่จาก K2 → ev_gps_log
  python scripts/taxi/outzone.py load-parquet [path]     (dev) เติม ev_gps_log จาก smarttaxi.parquet
  python scripts/taxi/outzone.py analyze [--as-of ...]   อัปเดตสถานะรายคัน + สร้างรายการแจ้งเตือนของวัน
  python scripts/taxi/outzone.py notify  [--send]        ส่ง LINE (ไม่ใส่ --send = แสดงข้อความเฉยๆ)
  python scripts/taxi/outzone.py daily   [--send]        extract → analyze → notify  (ตั้ง Task Scheduler วันละครั้ง)
  python scripts/taxi/outzone.py report  [--send]        อีเมลรายงานรถที่อยู่นอกเขตตอนนี้ทุกคัน (ทดสอบแทน LINE)
  python scripts/taxi/outzone.py hourly  [--send]        extract → analyze → report  (ตั้ง Task Scheduler ทุกชั่วโมง)
  python scripts/taxi/outzone.py status                  ดูสถานะล่าสุด

env
  EV_STORE_URL      ที่เก็บ (SQLAlchemy URL) · default = SQLite ใน scripts/taxi/_out/outzone/
                    server ใหม่ (MySQL)  mysql+pymysql://user:pwd@host/db
                    ฝากบน K2 ชั่วคราว   mssql+pyodbc://...  (ต้องได้สิทธิ์ CREATE TABLE ก่อน)
  EV_SRC_PROFILE    profile ใน scripts/db.py ของฐานต้นทาง (default ev7 — ฐาน EV7 · env EV7DB_USER / EV7DB_PWD)
  EV_SRC_TABLE      ตาราง GPS ต้นทาง = dbo.EV7_SMARTTAXI_TRACKING (ฐาน EV7 · ~650k แถว/วัน · PK ID)
  EV_GEO_PROVINCE   ขอบเขตจังหวัด (default D:\\Master\\geo\\province.geojson)
  EV_EXEMPT_FILE    ไฟล์ VIN/ทะเบียนที่ยกเว้น (บรรทัดละ 1 ค่า) — เช่นรถที่ฐานอยู่นอกเขตโดยได้รับอนุญาต
  LINE_CHANNEL_TOKEN · LINE_TO   ใช้ตอน --send เท่านั้น (ห้ามเขียนลงไฟล์)
  MAIL_USER · MAIL_APP_PASSWORD · MAIL_TO   อีเมล (report/hourly --send) ผ่าน Gmail SMTP · ดู mail_report.py
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape
from shapely.ops import unary_union
import sqlalchemy as sa

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = Path(__file__).resolve().parent
OUT = HERE / "_out" / "outzone"

# ── กติกา (ปรับได้ที่เดียว) ───────────────────────────────────────────
ZONE_PROV = ["10", "11", "12", "13", "73", "74"]   # กทม. สมุทรปราการ นนทบุรี ปทุมธานี นครปฐม สมุทรสาคร
LIMIT_H = 120          # อยู่นอกเขตติดต่อกันเกินกี่ชั่วโมงถึงแจ้ง (LINE รายวัน)
REPORT_MIN_H = 5       # อีเมลรายชั่วโมง: แสดงเฉพาะรถที่อยู่นอกเขตเกินกี่ชั่วโมง (ตรงกับแท็บ Outside ในเว็บ)
RETURN_N = 2           # ต้องเจอจุดในเขตติดกันกี่จุดถึงนับว่ากลับเข้าเขต (กันจุด GPS กระโดด)
STALE_H = 24           # ไม่มีข้อมูลเกินกี่ ชม. ให้ติดป้าย "ขาดสัญญาณ" (ยังนับเวลาต่อ)
TH_BBOX = (97.3, 5.5, 105.7, 20.5)                # lon_min, lat_min, lon_max, lat_max
BATCH = 200_000

SRC_COLS = {   # คอลัมน์ต้นทาง (ตาม export smarttaxi.rpt) → ชื่อในที่เก็บ
    "ID": "id", "SMARTTAXI_ID_CAR": "car_id", "SMARTTAXI_BODYCAR_NUMBER": "vin",
    "SMARTTAXI_REFISTER_ID": "plate", "SMARTTAXI_HEADER_CENTER": "center",
    "SMARTTAXI_CM_METER": "meter", "SMARTTAXI_CM_ENGINE": "engine", "SMARTTAXI_CM_BATTERY": "battery",
    "SMARTTAXI_SIGNAL_GPS": "signal", "SMARTTAXI_LA_GOOGLE": "lat", "SMARTTAXI_LONG_GOOGLE": "lon",
    "SMARTTAXI_FAST": "speed", "SMARTTAXI_DIRECTION": "direction", "CREATED_AT": "created_at",
}
LOG_COLS = ["id", "car_id", "vin", "plate", "center", "gps_time", "lat", "lon", "speed", "direction",
            "signal", "meter", "engine", "battery", "created_at"]

# ── ที่เก็บ ─────────────────────────────────────────────────────────
md = sa.MetaData()
S = lambda n=64: sa.String(n)
t_log = sa.Table("ev_gps_log", md,
    sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
    sa.Column("car_id", S(32)), sa.Column("vin", S(32), index=True), sa.Column("plate", S(32)),
    sa.Column("center", S(64)), sa.Column("gps_time", sa.DateTime, index=True),
    sa.Column("lat", sa.Float), sa.Column("lon", sa.Float), sa.Column("speed", sa.Float),
    sa.Column("direction", sa.Float), sa.Column("signal", S(4)), sa.Column("meter", S(4)),
    sa.Column("engine", S(4)), sa.Column("battery", S(4)), sa.Column("created_at", sa.DateTime),
    sa.Column("loaded_at", sa.DateTime))
t_state = sa.Table("ev_zone_state", md,
    sa.Column("vin", S(32), primary_key=True), sa.Column("plate", S(32)), sa.Column("car_id", S(32)),
    sa.Column("out_since", sa.DateTime),            # NULL = อยู่ในเขต
    sa.Column("out_since_is_first_seen", sa.Boolean),  # True = ไม่เคยเห็นในเขตเลย → เวลาจริงอาจนานกว่านี้
    sa.Column("last_inside_at", sa.DateTime), sa.Column("last_seen", sa.DateTime),
    sa.Column("last_lat", sa.Float), sa.Column("last_lon", sa.Float), sa.Column("last_inside", sa.Boolean),
    sa.Column("in_run", sa.Integer), sa.Column("updated_at", sa.DateTime))
t_alert = sa.Table("ev_zone_alert", md,
    sa.Column("as_of_date", sa.Date, primary_key=True), sa.Column("vin", S(32), primary_key=True),
    sa.Column("plate", S(32)), sa.Column("car_id", S(32)), sa.Column("out_since", sa.DateTime),
    sa.Column("out_since_is_first_seen", sa.Boolean), sa.Column("hours_out", sa.Float),
    sa.Column("last_seen", sa.DateTime), sa.Column("last_province", S(128)),
    sa.Column("last_lat", sa.Float), sa.Column("last_lon", sa.Float), sa.Column("stale", sa.Boolean),
    sa.Column("created_at", sa.DateTime), sa.Column("sent_at", sa.DateTime))
t_job = sa.Table("ev_job_state", md, sa.Column("k", S(64), primary_key=True), sa.Column("v", S(64)))


def store(url=None):
    url = url or os.environ.get("EV_STORE_URL")
    if not url:
        OUT.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{(OUT / 'ev_outzone.db').as_posix()}"
    eng = sa.create_engine(url, future=True)
    md.create_all(eng)
    return eng


def job_get(eng, k, default=None):
    with eng.connect() as c:
        v = c.execute(sa.select(t_job.c.v).where(t_job.c.k == k)).scalar()
    return default if v is None else v


def job_set(c, k, v):
    c.execute(t_job.delete().where(t_job.c.k == k))
    c.execute(t_job.insert().values(k=k, v=str(v)))


# ── เขต ─────────────────────────────────────────────────────────────
class Zone:
    def __init__(self, path=None):
        path = path or os.environ.get("EV_GEO_PROVINCE", r"D:\Master\geo\province.geojson")
        g = json.load(open(path, encoding="utf-8"))
        self.prov_geom, self.prov_name, self.prov_name_en = [], [], []
        zone = []
        for f in g["features"]:
            p = f["properties"]; geom = shape(f["geometry"])
            self.prov_geom.append(geom)
            self.prov_name.append(p.get("province_name_th") or p.get("province_name_en"))
            self.prov_name_en.append((p.get("province_name_en") or p.get("province_name_th") or "").title().replace("Changwat ", ""))
            if str(p["province_code"]) in ZONE_PROV:
                zone.append(geom)
        assert len(zone) == len(ZONE_PROV), f"เจอจังหวัดในเขต {len(zone)} จาก {len(ZONE_PROV)}"
        self.zone = unary_union(zone)
        shapely.prepare(self.zone)
        self.tree = shapely.STRtree(self.prov_geom)

    def inside(self, lon, lat):
        return shapely.contains_xy(self.zone, np.asarray(lon, float), np.asarray(lat, float))

    def province(self, lon, lat, en=False):
        if lon is None or lat is None or pd.isna(lon):
            return None
        hit = self.tree.query(shapely.Point(lon, lat), predicate="intersects")
        if not len(hit):
            return "Outside Thailand / sea" if en else "นอกประเทศ/ทะเล"
        return (self.prov_name_en if en else self.prov_name)[hit[0]]


# ── 1. ดึงข้อมูล ────────────────────────────────────────────────────
def normalize(df):
    """แปลงเป็นคอลัมน์มาตรฐานของ ev_gps_log"""
    df = df.copy()
    if "gps_time" not in df:
        d, t = df.pop("SMARTTAXI_DATE"), df.pop("SMARTTAXI_TIME")
        df["gps_time"] = pd.to_datetime(d.astype(str).str[:10] + " " + t.astype(str).str[:8], errors="coerce")
    df = df.rename(columns=SRC_COLS)
    # ชื่อคอลัมน์ใน smarttaxi.parquet (load_rpt.py ตัด SMARTTAXI_ แล้วทำตัวเล็ก)
    df = df.rename(columns={k: v for k, v in {"signal_gps": "signal", "header_center": "center", "cm_meter": "meter",
                                              "cm_engine": "engine", "cm_battery": "battery"}.items() if v not in df})
    for c in LOG_COLS:
        if c not in df:
            df[c] = None
    df = df[LOG_COLS]
    for c in ["lat", "lon", "speed", "direction"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["car_id", "vin", "plate", "center", "signal", "meter", "engine", "battery"]:
        df[c] = df[c].astype("string").str.strip()
    df["id"] = df["id"].astype("int64")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["loaded_at"] = datetime.now().replace(microsecond=0)
    return df


def append_log(eng, df):
    if df.empty:
        return 0
    df.to_sql("ev_gps_log", eng, if_exists="append", index=False, chunksize=20_000)
    return len(df)


def extract(eng):
    sys.path.insert(0, str(HERE.parent))
    import db
    table = os.environ.get("EV_SRC_TABLE")
    if not table:
        raise SystemExit("ยังไม่ได้ตั้ง EV_SRC_TABLE (ชื่อตาราง GPS บน K2) — ต้องถามทีม K2/EV7 ว่าอยู่ฐานไหน")
    cn = db.connect(os.environ.get("EV_SRC_PROFILE", "ev7"), timeout=600)
    wm = int(job_get(eng, "extract_max_id", 0))
    # ตารางจริงสะกด SMARTTAXI_REGISTER_ID · ไฟล์ export (.rpt) สะกด REFISTER → map ให้เป็นชื่อเดียวกัน
    live = {r[0] for r in cn.cursor().execute(f"SELECT TOP 0 * FROM {table}").description}
    sel = [f"SMARTTAXI_REGISTER_ID AS SMARTTAXI_REFISTER_ID" if c == "SMARTTAXI_REFISTER_ID" and c not in live and "SMARTTAXI_REGISTER_ID" in live else c
           for c in SRC_COLS]
    cols = ", ".join(sel + ["SMARTTAXI_DATE", "SMARTTAXI_TIME"])
    total = 0
    while True:
        df = pd.read_sql(f"SELECT TOP ({BATCH}) {cols} FROM {table} WITH (NOLOCK) WHERE ID > ? ORDER BY ID", cn, params=[wm])
        if df.empty:
            break
        df = normalize(df)
        with eng.begin() as c:
            df.to_sql("ev_gps_log", c, if_exists="append", index=False, chunksize=20_000)
            wm = int(df["id"].max()); job_set(c, "extract_max_id", wm)
        total += len(df)
        print(f"  extract +{len(df):,} → id {wm}", flush=True)
    print(f"extract: {total:,} แถวใหม่ · watermark id {wm}")
    return total


def load_parquet(eng, path):
    df = normalize(pd.read_parquet(path))
    wm = int(job_get(eng, "extract_max_id", 0))
    df = df[df["id"] > wm].sort_values("id")
    with eng.begin() as c:
        n = append_log(c, df)
        if n:
            job_set(c, "extract_max_id", int(df["id"].max()))
    print(f"load-parquet: {n:,} แถว")


# ── 2. วิเคราะห์ ─────────────────────────────────────────────────────
def load_state(eng):
    with eng.connect() as c:
        rows = c.execute(sa.select(t_state)).mappings().all()
    return {r["vin"]: dict(r) for r in rows}


def update_state(state, pts, zone, as_of):
    """ไล่จุดใหม่ทีละคันตามเวลา · คืน (state, สถิติ)"""
    st = {"points": len(pts), "valid": 0, "late": 0}
    if pts.empty:
        return state, st
    lon, lat = pts["lon"].to_numpy(float), pts["lat"].to_numpy(float)
    ok = ((pts["signal"] == "A").fillna(False).to_numpy()
          & ~np.isnan(lon) & ~np.isnan(lat)
          & (lon >= TH_BBOX[0]) & (lon <= TH_BBOX[2]) & (lat >= TH_BBOX[1]) & (lat <= TH_BBOX[3])
          & pts["gps_time"].notna().to_numpy()
          & (pts["gps_time"] <= as_of + timedelta(hours=1)).fillna(False).to_numpy()
          & (pts["gps_time"] >= pd.Timestamp("2020-01-01")).fillna(False).to_numpy())
    p = pts[ok].copy()
    st["valid"] = len(p)
    p["inside"] = zone.inside(p["lon"], p["lat"])
    p = p.sort_values(["vin", "gps_time", "id"])
    for vin, g in p.groupby("vin", sort=False):
        s = state.get(vin) or {"vin": vin, "out_since": None, "out_since_is_first_seen": False,
                                "last_inside_at": None, "last_seen": None, "in_run": 0}
        last = s["last_seen"]
        for t, ins, la, lo, plate, car in zip(g["gps_time"], g["inside"], g["lat"], g["lon"], g["plate"], g["car_id"]):
            t = t.to_pydatetime()
            if last is not None and t < last:
                st["late"] += 1          # จุดมาช้ากว่าที่ประมวลผลไปแล้ว — ไม่ย้อนแก้สถานะ
                continue
            if ins:
                s["in_run"] = (s["in_run"] or 0) + 1
                s["last_inside_at"] = t
                if s["in_run"] >= RETURN_N:
                    s["out_since"] = None; s["out_since_is_first_seen"] = False
            else:
                s["in_run"] = 0
                if s["out_since"] is None:
                    s["out_since"] = t
                    s["out_since_is_first_seen"] = s["last_inside_at"] is None
            last = t
            s.update(last_seen=t, last_lat=float(la), last_lon=float(lo), last_inside=bool(ins),
                     plate=None if pd.isna(plate) else plate, car_id=None if pd.isna(car) else car)
        state[vin] = s
    return state, st


def exempt_set():
    f = os.environ.get("EV_EXEMPT_FILE")
    if not f or not Path(f).exists():
        return set()
    return {ln.strip() for ln in open(f, encoding="utf-8") if ln.strip() and not ln.startswith("#")}


def build_alerts(state, zone, as_of):
    ex = exempt_set()
    out = []
    for s in state.values():
        if s["out_since"] is None or s["vin"] in ex or (s.get("plate") or "") in ex:
            continue
        h = (as_of - s["out_since"]).total_seconds() / 3600
        if h <= LIMIT_H:
            continue
        out.append(dict(as_of_date=as_of.date(), vin=s["vin"], plate=s.get("plate"), car_id=s.get("car_id"),
                        out_since=s["out_since"], out_since_is_first_seen=bool(s["out_since_is_first_seen"]),
                        hours_out=round(h, 1), last_seen=s["last_seen"],
                        last_province=zone.province(s.get("last_lon"), s.get("last_lat")),
                        last_lat=s.get("last_lat"), last_lon=s.get("last_lon"),
                        stale=(as_of - s["last_seen"]).total_seconds() / 3600 > STALE_H,
                        created_at=datetime.now().replace(microsecond=0), sent_at=None))
    return sorted(out, key=lambda a: -a["hours_out"])


def analyze(eng, as_of=None, zone=None):
    as_of = as_of or datetime.now().replace(microsecond=0)
    zone = zone or Zone()
    wm = int(job_get(eng, "analyze_max_id", 0))
    hi = int(job_get(eng, "extract_max_id", 0))
    state = load_state(eng)
    tot = {"points": 0, "valid": 0, "late": 0}
    q = sa.select(t_log.c.id, t_log.c.vin, t_log.c.plate, t_log.c.car_id, t_log.c.gps_time,
                  t_log.c.lat, t_log.c.lon, t_log.c.signal)
    lo = wm
    while lo < hi:                     # ทีละช่วง id กันกินหน่วยความจำ (จุดภายในช่วงเรียงตามเวลาต่อคันเอง)
        up = lo + 2_000_000
        with eng.connect() as c:
            pts = pd.read_sql(q.where(t_log.c.id > lo, t_log.c.id <= up), c)
        pts["gps_time"] = pd.to_datetime(pts["gps_time"])
        state, st = update_state(state, pts, zone, as_of)
        for k in tot: tot[k] += st[k]
        lo = up
    alerts = build_alerts(state, zone, as_of)
    now = datetime.now().replace(microsecond=0)
    with eng.begin() as c:
        c.execute(t_state.delete())
        if state:
            cols = [col.name for col in t_state.columns]
            c.execute(t_state.insert(), [{k: s.get(k) for k in cols} | {"updated_at": now} for s in state.values()])
        # วันเดียวกันรันซ้ำได้: แทนที่รายการที่ยังไม่ส่ง · ที่ส่งไปแล้วเก็บไว้
        sent = {r[0] for r in c.execute(sa.select(t_alert.c.vin).where(
            t_alert.c.as_of_date == as_of.date(), t_alert.c.sent_at.is_not(None)))}
        c.execute(t_alert.delete().where(t_alert.c.as_of_date == as_of.date(), t_alert.c.sent_at.is_(None)))
        new = [a for a in alerts if a["vin"] not in sent]
        if new:
            c.execute(t_alert.insert(), new)
        job_set(c, "analyze_max_id", hi)
        job_set(c, "analyze_as_of", as_of.isoformat(sep=" "))
    n_out = sum(1 for s in state.values() if s["out_since"] is not None)
    print(f"analyze as_of {as_of:%Y-%m-%d %H:%M} · จุดใหม่ {tot['points']:,} (ใช้ได้ {tot['valid']:,} · มาช้า {tot['late']:,})"
          f" · รถ {len(state):,} คัน · อยู่นอกเขตตอนนี้ {n_out:,} · เกิน {LIMIT_H} ชม. {len(alerts):,} คัน")
    return alerts


# ── 3. แจ้งเตือน ─────────────────────────────────────────────────────
def fmt_dur(h):
    d, hh = divmod(int(h), 24)
    return f"{d} วัน {hh} ชม."


def messages(alerts, as_of_date):
    """ข้อความ LINE — ⚠️ wording ชั่วคราว รอคุณหนุ่ม (ทีม EV7) ส่งให้ แล้วแก้ที่ฟังก์ชันนี้ที่เดียว"""
    if not alerts:
        return []
    head = (f"🚕 EV7 แจ้งเตือนรถอยู่นอกเขต กทม.และปริมณฑลเกิน {LIMIT_H // 24} วัน\n"
            f"ข้อมูล ณ {as_of_date:%d/%m/%Y} · {len(alerts)} คัน")
    lines = []
    for i, a in enumerate(alerts, 1):
        since = "อย่างน้อย " if a["out_since_is_first_seen"] else ""
        stale = f" · ⚠️ ขาดสัญญาณตั้งแต่ {a['last_seen']:%d/%m %H:%M}" if a["stale"] else ""
        lines.append(f"{i}. {a['plate'] or a['vin']} · {a['last_province'] or '-'} · นอกเขต {since}{fmt_dur(a['hours_out'])}"
                     f" (ตั้งแต่ {a['out_since']:%d/%m %H:%M}){stale}")
    msgs, cur = [], head
    for ln in lines:                  # LINE text ≤ 5,000 ตัวอักษรต่อข้อความ
        if len(cur) + len(ln) + 1 > 4800:
            msgs.append(cur); cur = ln
        else:
            cur += "\n" + ln
    msgs.append(cur)
    return msgs


def notify(eng, send=False, as_of_date=None):
    from line_push import push
    as_of_date = as_of_date or datetime.now().date()
    with eng.connect() as c:
        rows = [dict(r) for r in c.execute(sa.select(t_alert).where(
            t_alert.c.as_of_date == as_of_date, t_alert.c.sent_at.is_(None))
            .order_by(t_alert.c.hours_out.desc())).mappings()]
    msgs = messages(rows, as_of_date)
    if not msgs:
        print(f"notify {as_of_date}: ไม่มีรถที่ต้องแจ้ง"); return
    if not send:
        print(f"notify {as_of_date}: DRY-RUN ({len(rows)} คัน · {len(msgs)} ข้อความ) — ใส่ --send เพื่อส่งจริง\n")
        print("\n\n---\n\n".join(msgs)); return
    push(msgs)
    with eng.begin() as c:
        c.execute(t_alert.update().where(t_alert.c.as_of_date == as_of_date, t_alert.c.sent_at.is_(None))
                  .values(sent_at=datetime.now().replace(microsecond=0)))
    print(f"notify {as_of_date}: ส่งแล้ว {len(rows)} คัน · {len(msgs)} ข้อความ")


def add_dummy_contacts(rows):
    """⚠️ ข้อมูลสมมติสำหรับทดสอบหน้าตารายงานเท่านั้น — ข้อมูล GPS ไม่มีชื่อ/เบอร์คนขับ (จริงต้องมาจาก GI Core)
    ชื่อสุ่มจากรายการชื่อทั่วไป · เบอร์ขึ้นต้น 090-000 · อีเมลโดเมน example.com (โดเมนสงวนไว้สำหรับตัวอย่าง)
    จำนวนครั้งที่แจ้ง = จำลองว่าส่งทุกชั่วโมงตั้งแต่เกิน REPORT_MIN_H"""
    import random, zlib
    first = ["สมชาย", "สมศักดิ์", "วิชัย", "ประเสริฐ", "สุรชัย", "อนุชา", "ธนพล", "กิตติ", "ชัยวัฒน์", "ณัฐพล", "บุญมี", "สมพงษ์"]
    last = ["ใจดี", "รักษ์ดี", "มั่นคง", "ศรีสุข", "ทองดี", "แสงทอง", "บุญมา", "สุขใจ", "พูลผล", "เจริญยิ่ง"]
    for r in rows:
        rnd = random.Random(zlib.crc32(str(r["vin"]).encode()))
        n = rnd.randrange(10000)
        r.update(contact_name=f"{rnd.choice(first)} {rnd.choice(last)}", contact_phone=f"090-000-{n:04d}",
                 contact_email=f"driver{n:04d}@example.com",
                 alerts_sent=int(r["hours_out"] - REPORT_MIN_H) + 1)


def report(eng, send=False, as_of=None, test=True, dummy=False):
    """อีเมลรายงานรถที่อยู่นอกเขตตอนนี้ทุกคัน (ใช้แทน LINE ระหว่างทดสอบ) · อ่านจาก ev_zone_state หลัง analyze"""
    import mail_report as mr
    as_of = as_of or datetime.now().replace(microsecond=0)
    zone = Zone()
    ex = exempt_set()
    state = load_state(eng)
    with eng.connect() as c:
        data_to = c.execute(sa.select(sa.func.max(t_log.c.gps_time))).scalar()
    data_to = pd.Timestamp(data_to).to_pydatetime() if data_to else None
    rows = []
    for s in state.values():
        if s["out_since"] is None or s["vin"] in ex or (s.get("plate") or "") in ex:
            continue
        rows.append(dict(vin=s["vin"], plate=s.get("plate"), car_id=s.get("car_id"),
                         out_since=s["out_since"], out_since_is_first_seen=bool(s["out_since_is_first_seen"]),
                         hours_out=round(max(0, (as_of - s["out_since"]).total_seconds() / 3600), 1),
                         last_seen=s["last_seen"], last_lat=s.get("last_lat"), last_lon=s.get("last_lon"),
                         last_province=zone.province(s.get("last_lon"), s.get("last_lat"), en=True),
                         stale=(as_of - s["last_seen"]).total_seconds() / 3600 > STALE_H))
    n_out_all = len(rows)
    rows = [r for r in rows if r["hours_out"] > REPORT_MIN_H]
    rows.sort(key=lambda r: -r["hours_out"])
    if dummy:
        add_dummy_contacts(rows)
    summary = dict(as_of=as_of, data_to=data_to, cars=len(state), out_all=n_out_all, min_h=REPORT_MIN_H, out=len(rows),
                   over=sum(r["hours_out"] > LIMIT_H for r in rows), stale=sum(r["stale"] for r in rows))
    html = mr.build_html(rows, summary, LIMIT_H, test=test)
    text = mr.build_text(rows, summary, LIMIT_H)
    subject = (("[TEST] " if test else "") + f"EV7 · Outside Bangkok & Vicinity > {REPORT_MIN_H} h: {summary['out']:,} vehicles"
               f" ({summary['over']:,} over {LIMIT_H // 24} days) · {as_of:%d %b %Y %H:%M}")
    pv = mr.preview(html, OUT / "report_preview.html")
    print(f"report as_of {as_of:%Y-%m-%d %H:%M} · นอกเขต {summary['out']:,} คัน · เกิน {LIMIT_H} ชม. {summary['over']:,}"
          f" · preview {pv}")
    xlsx = mr.build_xlsx(rows, summary, LIMIT_H, dummy=dummy)
    (OUT / "report_preview.xlsx").write_bytes(xlsx)
    if not send:
        print("DRY-RUN — ใส่ --send เพื่อส่งอีเมลจริง"); return
    to = mr.send(subject, text, html, [(f"ev7_outzone_{as_of:%Y%m%d_%H%M}.xlsx", xlsx)])
    print(f"ส่งอีเมลแล้ว → {', '.join(to)}")


def status(eng):
    with eng.connect() as c:
        n = c.execute(sa.select(sa.func.count()).select_from(t_log)).scalar()
        rng = c.execute(sa.select(sa.func.min(t_log.c.gps_time), sa.func.max(t_log.c.gps_time))).one()
        st = pd.read_sql(sa.select(t_state), c)
        al = pd.read_sql(sa.select(t_alert.c.as_of_date, sa.func.count(), sa.func.count(t_alert.c.sent_at))
                         .group_by(t_alert.c.as_of_date).order_by(t_alert.c.as_of_date.desc()).limit(7), c)
    print(f"ev_gps_log {n:,} แถว · gps_time {rng[0]} → {rng[1]}")
    for k in ("extract_max_id", "analyze_max_id", "analyze_as_of"):
        print(f"  {k} = {job_get(eng, k)}")
    print(f"ev_zone_state {len(st):,} คัน · นอกเขตตอนนี้ {int(st['out_since'].notna().sum()) if len(st) else 0:,}")
    print("ev_zone_alert (วัน · รายการ · ส่งแล้ว):"); print(al.to_string(index=False) if len(al) else "  -")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["extract", "load-parquet", "analyze", "notify", "daily", "report", "hourly", "status"])
    ap.add_argument("path", nargs="?", default=str(HERE / "_out" / "smarttaxi.parquet"))
    ap.add_argument("--as-of", help="เวลาอ้างอิง 'YYYY-MM-DD HH:MM' (default = ตอนนี้)")
    ap.add_argument("--send", action="store_true", help="ส่ง LINE / อีเมลจริง")
    ap.add_argument("--dummy", action="store_true", help="report/hourly: ใส่ชื่อ เบอร์ อีเมลผู้ติดต่อ และจำนวนครั้งที่แจ้งแบบสมมติ (ทดสอบหน้าตา)")
    a = ap.parse_args()
    as_of = datetime.fromisoformat(a.as_of) if a.as_of else None
    eng = store()
    if a.cmd == "extract":
        extract(eng)
    elif a.cmd == "load-parquet":
        load_parquet(eng, a.path)
    elif a.cmd == "analyze":
        analyze(eng, as_of)
    elif a.cmd == "notify":
        notify(eng, a.send, as_of.date() if as_of else None)
    elif a.cmd == "daily":
        extract(eng); analyze(eng, as_of); notify(eng, a.send, as_of.date() if as_of else None)
    elif a.cmd == "report":
        report(eng, a.send, as_of, dummy=a.dummy)
    elif a.cmd == "hourly":                       # ทดสอบ: รายงานทางอีเมลทุกชั่วโมง (แทน LINE)
        if os.environ.get("EV_SRC_TABLE"):
            extract(eng)
        else:
            print("ข้าม extract — ยังไม่ได้ตั้ง EV_SRC_TABLE (ใช้ข้อมูลที่มีในที่เก็บ)")
        analyze(eng, as_of); report(eng, a.send, as_of, dummy=a.dummy)
    else:
        status(eng)


if __name__ == "__main__":
    main()
