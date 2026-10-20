# -*- coding: utf-8 -*-
"""สร้าง Smart Taxi dashboard (ไฟล์ HTML เดียว เปิดได้เลย)

    python scripts/taxi/load_rpt.py            # ครั้งแรก: .rpt -> parquet
    python scripts/taxi/build_dashboard.py     # parquet -> HTML

ขั้นตอน
    1. load_points()   อ่านจุด GPS          ← วันหน้าเปลี่ยนเป็นอ่านจากฐานได้ที่นี่ที่เดียว
    2. clean()         ตัดจุดเสีย / ซ้ำ / กระโดด
    3. assign_area()   ใส่ จังหวัด/อำเภอ ให้ทุกจุด (point-in-polygon)
    4. encode()        แพ็กเป็นคอลัมน์ binary + gzip + base64
    5. render()        ฝังลง dashboard_template.html

═══════════════════════════════════════════════════════════════════════
 ความหมายของข้อมูล (ถอดจากการสำรวจ smarttaxi.rpt 2026-10-02)
═══════════════════════════════════════════════════════════════════════
    ⚠️ car_id ไม่ใช่รหัสรถ — เลขเดียวกันใช้ซ้ำใน 3 ศูนย์
       car_id 000001 = ทอ-2901 (yF) · ทอ-3000 (ux) · ทอ-5917 (0a) คนละคัน
       → คีย์ที่ถูกคือ VIN (vin) · รถจริงมี 4,162 คัน ไม่ใช่ 2,615
    ⚠️ ทะเบียนซ้ำ 4 ป้าย ผูกกับ VIN 2 ตัว (ทอ-5711 · ทอ-6258 · ทอ-6992 · ทอ-8347)
    header_center  0a / yF / ux = ศูนย์ (ยังไม่รู้ชื่อ) [อนุมาน]
    cm_meter       E = ว่าง · F = มีผู้โดยสาร
                   (F วิ่งเฉลี่ย 25 กม./ชม. median 15 · E median 0)
    cm_engine      0 = เครื่องทำงาน (เฉลี่ย 22.9 กม./ชม.)
                   1 = ดับ/จอด     (เฉลี่ย 0.2 กม./ชม.)   [อนุมาน จากความเร็ว]
                   2 = ไม่ทราบ
    signal_gps     A = พิกัดใช้ได้ · V = ไม่มีสัญญาณ (มาตรฐาน NMEA)
    ข้อมูลเป็นการ poll API ทุก ~4 นาที 40 วินาที แต่ละรอบคืน "จุดล่าสุด" ของทุกคัน
    → รถที่ขาดสัญญาณจะส่งจุดเก่าซ้ำทุกรอบ ต้อง dedupe ด้วย (vin, gps_time)
"""
import base64
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "_out"
PARQUET = OUT_DIR / "smarttaxi.parquet"
PROV_GEO = OUT_DIR / "prov_simple.geojson"      # สำหรับวาด (simplify 1.5%)
DIST_GEO = OUT_DIR / "dist_simple.geojson"      # สำหรับวาด
DIST_PIP = OUT_DIR / "dist_pip.geojson"         # สำหรับคำนวณ (simplify 12% แม่นกว่า)
TEMPLATE = HERE / "dashboard_template.html"
LOGO = Path(r"D:\Taxi\ev7logo.png")
WEB = HERE / "web"                               # ต้นฉบับหน้าเว็บ v2 (index.html + css/ + js/ + assets/)

# ── วิธีสั่ง ──────────────────────────────────────────────────────────────
#   เวอร์ชัน 2 (แยกไฟล์ · ต้นฉบับอยู่ที่ scripts/taxi/web/)
#     python scripts/taxi/build_dashboard.py --web D:\Taxi\dashboard            → โฟลเดอร์ เปิด index.html
#     python scripts/taxi/build_dashboard.py --bundle D:\Taxi\Taxi_dashboard_v2.html  → ไฟล์เดียวไว้ส่งต่อ
#     (ใส่ทั้งสองอย่างพร้อมกันได้)
#   เวอร์ชัน 1 (ไฟล์เดียวแบบเดิม)
#     python scripts/taxi/build_dashboard.py [ไฟล์ปลายทาง.html]
ARGS = sys.argv[1:]
def _opt(flag):
    if flag in ARGS:
        i = ARGS.index(flag)
        return Path(ARGS[i + 1]) if i + 1 < len(ARGS) else None
    return None
WEB_DIR, BUNDLE = _opt("--web"), _opt("--bundle")
_pos = [a for k, a in enumerate(ARGS) if not a.startswith("--") and (k == 0 or ARGS[k - 1] not in ("--web", "--bundle"))]
OUT_HTML = Path(_pos[0] if _pos else r"D:\Taxi\Taxi_dashboard.html")
if len(_pos) > 1:
    TEMPLATE = HERE / _pos[1]
V2 = bool(WEB_DIR or BUNDLE) or "v2" in TEMPLATE.name

TH_BBOX = (5.5, 20.6, 97.3, 105.7)              # lat_min, lat_max, lon_min, lon_max
GLITCH_KMH = 200                                # เร็วเกินนี้ทั้งขาเข้าและขาออก = จุดกระโดด
STALE_BEFORE_H = 1                              # จุดเก่ากว่ารอบดึงแรกเกินนี้ = ค้าง ไม่ใช่การวิ่ง


# ══════════════════════════════════════════════════════════════════════
#  1. load
# ══════════════════════════════════════════════════════════════════════
def load_points():
    """คืน DataFrame คอลัมน์มาตรฐาน — สคีมานี้คือสัญญากับส่วนที่เหลือ

        vin, plate, center, car_id, gps_time, created_at,
        lat, lon, speed, meter, engine, signal

    วันหน้าต่อฐาน: แทนที่ฟังก์ชันนี้ด้วย query ที่คืนคอลัมน์เดียวกัน เช่น
        SELECT SMARTTAXI_BODYCAR_NUMBER AS vin, SMARTTAXI_REFISTER_ID AS plate, ...
        FROM   <ตาราง smarttaxi>
        WHERE  CREATED_AT >= @from AND CREATED_AT < @to
    (ยังไม่ได้ทำ — ยังไม่ทราบชื่อฐาน/ตาราง)
    """
    d = pd.read_parquet(PARQUET)
    return d.rename(columns={"header_center": "center", "cm_meter": "meter",
                             "cm_engine": "engine", "signal_gps": "signal"})


# ══════════════════════════════════════════════════════════════════════
#  2. clean
# ══════════════════════════════════════════════════════════════════════
def haversine_km(lat1, lon1, lat2, lon2):
    r = np.pi / 180
    a = (np.sin((lat2 - lat1) * r / 2) ** 2
         + np.cos(lat1 * r) * np.cos(lat2 * r) * np.sin((lon2 - lon1) * r / 2) ** 2)
    return 12742 * np.arcsin(np.sqrt(a))


def clean(d):
    log = {"raw_rows": int(len(d))}
    d = d.dropna(subset=["vin", "gps_time"])
    d = d[d.vin.str.len() > 0]

    # จุดล่าสุดที่รู้ของทุกคัน (รวมคันที่ขาดสัญญาณนาน) — เก็บไว้ก่อนตัด
    last_known = (d.dropna(subset=["lat", "lon"]).sort_values("gps_time")
                  .groupby("vin").tail(1).set_index("vin"))

    d = d.dropna(subset=["lat", "lon"])
    d = d[d.lat.between(TH_BBOX[0], TH_BBOX[1]) & d.lon.between(TH_BBOX[2], TH_BBOX[3])]
    n0 = len(d)
    d = d[d.gps_time <= d.created_at + pd.Timedelta(minutes=10)]
    log["future_clock_rows"] = int(n0 - len(d))

    n0 = len(d)
    d = d.sort_values("created_at").drop_duplicates(["vin", "gps_time"])
    log["repeated_rows"] = int(n0 - len(d))

    w0 = d.created_at.min() - pd.Timedelta(hours=STALE_BEFORE_H)
    n0 = len(d)
    d = d[d.gps_time >= w0]
    log["stale_points"] = int(n0 - len(d))

    # จุดกระโดด: เร็วเกินจริงทั้งขาเข้าและขาออก
    d = d.sort_values(["vin", "gps_time"]).reset_index(drop=True)
    same_prev = d.vin.eq(d.vin.shift())
    same_next = d.vin.eq(d.vin.shift(-1))
    dk_prev = haversine_km(d.lat, d.lon, d.lat.shift(), d.lon.shift())
    dk_next = haversine_km(d.lat, d.lon, d.lat.shift(-1), d.lon.shift(-1))
    dh_prev = (d.gps_time - d.gps_time.shift()).dt.total_seconds() / 3600
    dh_next = (d.gps_time.shift(-1) - d.gps_time).dt.total_seconds() / 3600
    v_prev = dk_prev / dh_prev.clip(lower=1 / 120)
    v_next = dk_next / dh_next.clip(lower=1 / 120)
    glitch = (same_prev & same_next & (v_prev > GLITCH_KMH) & (v_next > GLITCH_KMH)
              & (dk_prev > 2) & (dk_next > 2))
    log["glitch_points"] = int(glitch.sum())
    d = d[~glitch].reset_index(drop=True)

    d["speed"] = d.speed.fillna(0).clip(0, 250)
    log["clean_points"] = int(len(d))
    log["signal_v_points"] = int((d.signal == "V").sum())
    return d, last_known, log


# ══════════════════════════════════════════════════════════════════════
#  3. point in polygon
# ══════════════════════════════════════════════════════════════════════
def assign_area(d):
    """ใส่ดัชนีอำเภอให้ทุกจุด · จังหวัดได้จากอำเภอ

    จุดที่ไม่ตกในอำเภอไหนเลย (ทะเล · ขอบที่ simplify ตัด) ใช้อำเภอที่ใกล้สุด
    ภายใน ~2 กม. ถ้าไกลกว่านั้นให้เป็น -1
    """
    import shapely
    from shapely import STRtree
    from shapely.geometry import shape

    g = json.load(open(DIST_PIP, encoding="utf-8"))["features"]
    dists = pd.DataFrame([f["properties"] for f in g])
    polys = [shape(f["geometry"]) for f in g]

    provs = (dists[["ppc", "pth", "pen"]].drop_duplicates("ppc")
             .sort_values("ppc").reset_index(drop=True))
    prov_idx = {pc: i for i, pc in enumerate(provs.ppc)}
    dists["pi"] = dists.ppc.map(prov_idx)

    tree = STRtree(polys)
    pts = shapely.points(d.lon.to_numpy(), d.lat.to_numpy())
    pi_, ti_ = tree.query(pts, predicate="within")
    di = np.full(len(d), -1, dtype=np.int32)
    di[pi_] = ti_
    miss = np.where(di < 0)[0]
    if len(miss):
        mi, mt = tree.query_nearest(pts[miss], max_distance=0.02, return_distance=False)
        di[miss[mi]] = mt
    d["dist"] = di
    print(f"  ระบุอำเภอได้ {np.mean(di >= 0):.2%} · ไม่ได้ {int((di < 0).sum()):,} จุด")
    return d, dists, provs


# ══════════════════════════════════════════════════════════════════════
#  4. encode
# ══════════════════════════════════════════════════════════════════════
def b64gz(arr_or_bytes):
    raw = arr_or_bytes if isinstance(arr_or_bytes, bytes) else arr_or_bytes.tobytes()
    return base64.b64encode(gzip.compress(raw, 9)).decode("ascii")


def encode(d, dists, provs, last_known, log):
    veh = (d.groupby("vin")
           .agg(plate=("plate", "last"), center=("center", "last"),
                car_id=("car_id", "last"), n=("vin", "size"))
           .reset_index())
    # คันที่ไม่มีจุดในช่วงนี้เลย ก็ต้องอยู่ในรายชื่อ (ขาดสัญญาณ)
    extra = last_known.loc[~last_known.index.isin(veh.vin)]
    veh = pd.concat([veh, pd.DataFrame({
        "vin": extra.index, "plate": extra.plate.values, "center": extra.center.values,
        "car_id": extra.car_id.values, "n": 0})], ignore_index=True)
    veh = veh.sort_values(["center", "plate"]).reset_index(drop=True)
    vidx = {v: i for i, v in enumerate(veh.vin)}

    dup = veh.plate.duplicated(keep=False)
    veh["disp"] = np.where(dup, veh.plate + " · " + veh.vin.str[-5:], veh.plate)
    lk = last_known.reindex(veh.vin)
    veh["last_gps"] = lk.gps_time.dt.strftime("%Y-%m-%d %H:%M").fillna("").values
    veh["last_lat"] = lk.lat.round(5).values
    veh["last_lon"] = lk.lon.round(5).values

    d["v"] = d.vin.map(vidx)
    d = d.sort_values(["v", "gps_time"]).reset_index(drop=True)
    t0 = d.gps_time.min().floor("min")
    t = ((d.gps_time - t0).dt.total_seconds()).to_numpy(np.float32)

    start = np.zeros(len(veh), np.int32)
    count = np.zeros(len(veh), np.int32)
    vc = d.v.value_counts()
    count[vc.index.to_numpy()] = vc.to_numpy()
    start[1:] = np.cumsum(count)[:-1]

    eng = d.engine.map({"0": 0, "1": 1, "2": 2}).fillna(3).astype(np.uint8).to_numpy()
    flags = ((d.meter == "F").to_numpy(np.uint8)
             | ((d.signal == "V").to_numpy(np.uint8) << 1)
             | (eng << 2))
    pos = np.empty(len(d) * 2, np.float32)
    pos[0::2] = d.lon.to_numpy(np.float32)
    pos[1::2] = d.lat.to_numpy(np.float32)
    dist = np.where(d.dist.to_numpy() < 0, 65535, d.dist.to_numpy()).astype(np.uint16)
    # ทิศหน้ารถ (องศาจากทิศเหนือ ตามเข็ม) — ใช้หมุนรูปรถ
    #   ค่า > 360 = เพี้ยน (เจอสูงสุด 300,926) · ตอนจอด (เร็ว < 3) มักเป็น 0 → ใช้ทิศล่าสุดตอนยังวิ่ง
    hd = d.direction.where(d.direction.between(0, 360))
    hd = hd.mask((d.speed < 3) & hd.eq(0))
    hd = hd.groupby(d.v).ffill().fillna(0)
    head = (np.round(hd.to_numpy() / 360 * 256) % 256).astype(np.uint8)

    cols = {
        "v": d.v.to_numpy(np.uint16), "t": t, "pos": pos,
        "spd": d.speed.round().to_numpy(np.uint8), "flg": flags.astype(np.uint8),
        "dist": dist, "head": head,
    }
    meta = {
        "t0": t0.strftime("%Y-%m-%dT%H:%M:%S"),
        "tmax": float(t.max()),
        "n": int(len(d)),
        "source": "smarttaxi.rpt",
        "pulled_from": d.created_at.min().strftime("%Y-%m-%d %H:%M"),
        "pulled_to": d.created_at.max().strftime("%Y-%m-%d %H:%M"),
        "clean": log,
    }
    vehicles = {
        "vin": veh.vin.tolist(), "plate": veh.disp.tolist(), "center": veh.center.tolist(),
        "car": veh.car_id.tolist(), "start": start.tolist(), "count": count.tolist(),
        "last": veh.last_gps.tolist(),
        "llat": [None if pd.isna(x) else float(x) for x in veh.last_lat],
        "llon": [None if pd.isna(x) else float(x) for x in veh.last_lon],
    }
    areas = {
        "prov": [{"pc": r.ppc, "th": r.pth, "en": r.pen} for r in provs.itertuples()],
        "dist": [{"pc": r.pc, "th": r.th, "en": r.en, "p": int(r.pi)} for r in dists.itertuples()],
    }
    return cols, meta, vehicles, areas


# ══════════════════════════════════════════════════════════════════════
#  4b. ลานจอด + ที่อยู่ (เฉพาะเวอร์ชัน 2)
# ══════════════════════════════════════════════════════════════════════
GEOCODE_CACHE = OUT_DIR / "geocode_cache.json"


def find_depots(d):
    """หาลานจอด — ตรรกะเดียวกับ computeDepots() ในหน้าเว็บ (ตรวจแล้วได้ 21 แห่ง/456 คันเท่ากัน)

    จุดจอด  = จุดต่อเนื่อง (สัญญาณ A) ห่างจุดแรกของช่วง ≤ 200 ม. · ช่องว่าง ≤ 30 นาที · ≥ 30 นาที
    ค้างคืน = ทับช่วง 00:00–05:00 ≥ 1 ชม. (เอาช่วงที่ทับนานสุดต่อคัน)
    ลานจอด  = จุดค้างคืน ≥ 5 คันอยู่ห่างกันไม่เกิน 200 ม.
    ใช้แค่หาพิกัดไปดึงที่อยู่ล่วงหน้า หน้าเว็บยังคำนวณลานจอดเองตามเดิม
    """
    v = d[d.signal != "V"].sort_values(["vin", "gps_time"])
    t0 = v.gps_time.min().normalize()
    nights = [(t0 + pd.Timedelta(days=k), t0 + pd.Timedelta(days=k, hours=5))
              for k in range((v.gps_time.max() - t0).days + 1)]
    best = []
    for _, g in v.groupby("vin", sort=False):
        t = g.gps_time.to_numpy(); la = g.lat.to_numpy(); lo = g.lon.to_numpy()
        i, n, top = 0, len(g), None
        while i < n:
            j = i
            while (j + 1 < n and (t[j + 1] - t[j]) / np.timedelta64(1, "s") <= 1800
                   and haversine_km(la[i], lo[i], la[j + 1], lo[j + 1]) <= 0.2):
                j += 1
            if (t[j] - t[i]) / np.timedelta64(1, "s") >= 1800:
                s, e = pd.Timestamp(t[i]), pd.Timestamp(t[j])
                ov = max(max(0, (min(e, b) - max(s, a)).total_seconds()) for a, b in nights)
                if ov >= 3600 and (top is None or ov > top[0]):
                    top = (ov, la[i], lo[i])
            i = j + 1
        if top:
            best.append(top[1:])
    if not best:
        return []
    la = np.array([b[0] for b in best]); lo = np.array([b[1] for b in best])
    dens = np.array([(haversine_km(la[i], lo[i], la, lo) <= 0.2).sum() for i in range(len(la))])
    lab = np.full(len(la), -1); deps = []
    for i in sorted(range(len(la)), key=lambda k: (-dens[k], k)):
        if lab[i] >= 0:
            continue
        m = (haversine_km(la[i], lo[i], la, lo) <= 0.2) & (lab < 0)
        if m.sum() < 5:
            continue
        lab[m] = len(deps)
        deps.append((float(la[m].mean()), float(lo[m].mean()), int(m.sum())))
    return deps


def geocode(places):
    """ดึงที่อยู่จาก OpenStreetMap Nominatim แล้วจำไว้ใน geocode_cache.json

    กติกา Nominatim: ไม่เกิน 1 ครั้ง/วินาที · ระบุตัวตนด้วย User-Agent
    เจอ 429 (ใช้เกิน) ให้หยุดทันที — จุดที่ยังไม่ได้จะลองใหม่ตอนสร้างไฟล์ครั้งหน้า
    """
    import time
    import urllib.error
    import urllib.request
    cache = json.loads(GEOCODE_CACHE.read_text(encoding="utf-8")) if GEOCODE_CACHE.exists() else {}
    out, asked = [], 0
    for lat, lon in places:
        k = f"{lat:.4f},{lon:.4f}"
        if k not in cache:
            url = ("https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=18&addressdetails=1"
                   f"&accept-language=th&lat={lat}&lon={lon}")
            req = urllib.request.Request(url, headers={"User-Agent": "EV7-SmartTaxi-Dashboard/2 (internal analytics)"})
            try:
                if asked:
                    time.sleep(1.2)
                asked += 1
                j = json.load(urllib.request.urlopen(req, timeout=30))
                a = j.get("address", {})
                name = j.get("name") or a.get("amenity") or a.get("shop") or a.get("building") or ""
                road = a.get("road") or a.get("pedestrian") or a.get("residential") or ""
                tambon = a.get("city") or a.get("town") or a.get("village") or a.get("suburb") or ""
                short = " · ".join(dict.fromkeys(x for x in (name, road, tambon) if x))
                cache[k] = {"name": name, "short": short, "full": j.get("display_name", "")}
            except urllib.error.HTTPError as e:
                print(f"  ⚠️ Nominatim ตอบ {e.code} — หยุดดึงที่อยู่ (ที่เหลือจะลองใหม่รอบหน้า)")
                break
            except Exception as e:
                print(f"  ⚠️ ดึงที่อยู่ไม่ได้: {e}")
                break
        if k in cache:
            out.append(dict(cache[k], lat=round(lat, 6), lon=round(lon, 6)))
    GEOCODE_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"  ที่อยู่: ได้ {len(out)}/{len(places)} จุด (ดึงใหม่ {asked} ครั้ง)")
    return out


# ══════════════════════════════════════════════════════════════════════
#  5. render
# ══════════════════════════════════════════════════════════════════════
CAR_IMG = Path(r"D:\Taxi\ev7.png")


def car_atlas(path=CAR_IMG, h=120):
    """รูปรถ EV7 สำหรับเป็นหมุดบนแผนที่ — ตัดขอบใส ย่อ แล้วต่อรุ่นกลับด้านไว้ข้างกัน

    รูปต้นฉบับเป็นมุมเฉียงด้านหน้า หันซ้าย (ไม่ใช่มุมบน) จึงหมุนตามทิศไม่ได้
    หน้าเว็บจะใช้ภาพตั้งตรง แล้วเลือก "หันซ้าย/หันขวา" ตามทิศที่รถวิ่งแทน
    คืน None ถ้าไม่มีไฟล์ — หน้าเว็บจะใช้รูปรถมุมบนที่วาดเองแทน
    """
    if not path.exists():
        return None
    import io as _io
    from PIL import Image, ImageOps
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox())
    w = round(im.width * h / im.height)
    im = im.resize((w, h), Image.LANCZOS)
    atlas = Image.new("RGBA", (w * 2, h), (0, 0, 0, 0))
    atlas.paste(im, (0, 0))                          # หันซ้าย (ตามต้นฉบับ)
    atlas.paste(ImageOps.mirror(im), (w, 0))         # หันขวา
    buf = _io.BytesIO()
    atlas.save(buf, "PNG", optimize=True)
    print(f"  รูปรถ EV7: {w}×{h} px · {len(buf.getvalue()) / 1024:.0f} KB")
    return {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), "w": w, "h": h}


def check_js(html):
    """ตรวจ syntax ของ <script> ใน template ด้วย node ก่อนเขียนไฟล์

    เคยพลาด: '\\n' ในสตริง JS กลายเป็นขึ้นบรรทัดจริงตอนแพตช์ → ทั้งหน้าค้างที่ "กำลังโหลด"
    ถ้าไม่มี node ในเครื่องจะข้ามไป (ไม่บังคับ)
    """
    import re
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        print("  (ไม่มี node — ข้ามการตรวจ syntax)")
        return
    js = "\n;\n".join(re.findall(r"<script>([\s\S]*?)</script>", html))
    r = subprocess.run([node, "-e", "new Function(require('fs').readFileSync(0,'utf8'))"],
                       input=js, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise SystemExit(f"❌ JS มี syntax error — ไม่เขียนไฟล์\n{r.stderr.strip()[-600:]}")
    print("  JS syntax ✓")


EV_CACHE = OUT_DIR / "ev_chargers_osm.json"


def ev_chargers():
    """สถานีชาร์จ EV ทั้งประเทศจาก OpenStreetMap (Overpass API) · จำไว้ใน ev_chargers_osm.json

    ดึงใหม่: ใส่ --refresh-ev หรือลบไฟล์ cache
    ⚠️ OSM มีแค่บางส่วน — ต.ค. 2026 ได้ 306 จุด ขณะที่ EVAT นับได้ 3,429 สถานี (สิ้นปี 2567)
       ใช้ดูภาพรวมได้ แต่ห้ามสรุปว่า "พื้นที่นี้ไม่มีจุดชาร์จ"
    คืน [[lat, lon, ชื่อ, ผู้ให้บริการ, หัวชาร์จ, จำนวนช่อง], ...]
    """
    import urllib.parse
    import urllib.request
    if EV_CACHE.exists() and "--refresh-ev" not in ARGS:
        el = json.loads(EV_CACHE.read_text(encoding="utf-8"))
    else:
        q = ('[out:json][timeout:120];area["ISO3166-1"="TH"][admin_level=2]->.th;'
             'nwr["amenity"="charging_station"](area.th);out center tags;')
        req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                                     data=urllib.parse.urlencode({"data": q}).encode(),
                                     headers={"User-Agent": "EV7-SmartTaxi-Dashboard/2 (internal analytics)"})
        try:
            el = json.load(urllib.request.urlopen(req, timeout=180))["elements"]
        except Exception as e:                              # ไม่มีเน็ต / Overpass ล่ม → สร้างหน้าได้ แค่ไม่มีชั้นนี้
            print(f"  ⚠️ ดึงสถานีชาร์จไม่ได้ ({type(e).__name__} {getattr(e, 'code', '')}) — ข้ามชั้นนี้ · 429/504 = Overpass ไม่ว่าง ลองใหม่ภายหลัง")
            return []
        EV_CACHE.write_text(json.dumps(el, ensure_ascii=False), encoding="utf-8")
    out = []
    for e in el:
        c = e if "lat" in e else e.get("center")
        if not c:
            continue
        t = e.get("tags", {})
        sockets = sorted({k.split(":")[1] for k in t if k.startswith("socket:") and k.count(":") == 1})
        out.append([round(c["lat"], 5), round(c["lon"], 5),
                    t.get("name") or t.get("name:th") or t.get("name:en") or "",
                    t.get("operator") or t.get("brand") or "",
                    ", ".join(sockets), t.get("capacity", "")])
    return out


def make_payload(cols, meta, vehicles, areas, places=None, ev=None):
    """ข้อมูลทั้งหมดที่หน้าเว็บใช้ เป็นสตริง JSON"""
    prov_geo = json.load(open(PROV_GEO, encoding="utf-8"))
    dist_geo = json.load(open(DIST_GEO, encoding="utf-8"))
    for f in dist_geo["features"]:                    # เหลือแค่คีย์ที่ใช้
        f["properties"] = {"pc": f["properties"]["pc"]}
    for f in prov_geo["features"]:
        f["properties"] = {"pc": f["properties"]["pc"]}

    payload = {
        "meta": meta, "vehicles": vehicles, "areas": areas, "places": places or [], "ev": ev or [],
        "car": car_atlas() if V2 else None,
        "cols": {k: b64gz(v) for k, v in cols.items()},
        "dtype": {"v": "u16", "t": "f32", "pos": "f32", "spd": "u8", "flg": "u8", "dist": "u16", "head": "u8"},
        "geo": {"prov": b64gz(json.dumps(prov_geo, ensure_ascii=False,
                                          separators=(",", ":")).encode("utf-8")),
                "dist": b64gz(json.dumps(dist_geo, ensure_ascii=False,
                                          separators=(",", ":")).encode("utf-8"))},
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def logo_uri():
    return "data:image/png;base64," + base64.b64encode(LOGO.read_bytes()).decode()


def render(payload):
    """เวอร์ชัน 1 — ฝังทุกอย่างลง template ไฟล์เดียว"""
    html = TEMPLATE.read_text(encoding="utf-8")
    check_js(html)
    html = html.replace("/*__EMBEDDED_DATA__*/null", payload)
    html = html.replace("__LOGO_DATA_URI__", logo_uri())
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"เขียน {OUT_HTML} · {OUT_HTML.stat().st_size / 1e6:.1f} MB")


# ── เวอร์ชัน 2: ต้นฉบับแยกไฟล์ที่ scripts/taxi/web/ ─────────────────────────
import re as _re
LINK_CSS = _re.compile(r'<link rel="stylesheet" href="((?:css)/[^"]+)">')
LOCAL_JS = _re.compile(r'<script src="((?:js|data)/[^"]+)"></script>')


def data_js(payload):
    return ("// สร้างโดย scripts/taxi/build_dashboard.py — ห้ามแก้มือ · มีข้อมูลรถ (ทะเบียน · VIN · ตำแหน่ง)\n"
            "window.TAXI_DATA = " + payload + ";\n")


def web_js(index_html):
    """JS ของแอปทั้งหมด ต่อกันตามลำดับใน index.html — ไว้ตรวจ syntax / ชื่อซ้ำ"""
    srcs = [m for m in LOCAL_JS.findall(index_html) if m.startswith("js/")]
    return "".join(f"<script>{(WEB / s).read_text(encoding='utf-8')}</script>\n" for s in srcs)


def write_web(out_dir, payload):
    """คัดลอกต้นฉบับเว็บไปปลายทาง + เขียน data/taxi-data.js  → เปิด index.html ได้เลย"""
    import shutil
    index = (WEB / "index.html").read_text(encoding="utf-8")
    check_js(web_js(index))
    shutil.copytree(WEB, out_dir, dirs_exist_ok=True)
    (out_dir / "data").mkdir(parents=True, exist_ok=True)
    (out_dir / "data" / "taxi-data.js").write_text(data_js(payload), encoding="utf-8")
    size = sum(f.stat().st_size for f in out_dir.rglob("*") if f.is_file())
    print(f"เขียนโฟลเดอร์ {out_dir} · {size / 1e6:.1f} MB · เปิด {out_dir / 'index.html'}")


def write_bundle(out_file, payload):
    """รวมต้นฉบับเว็บกลับเป็น HTML ไฟล์เดียว (ไว้ส่งต่อทางอีเมล/แชท)

    CSS → <style> · JS → <script> แบบ inline ตามลำดับเดิม · โลโก้ → data URI
    ผลลัพธ์ทำงานเหมือนเปิดจากโฟลเดอร์ทุกอย่าง เพราะมาจากต้นฉบับเดียวกัน
    """
    html = (WEB / "index.html").read_text(encoding="utf-8")
    html = LINK_CSS.sub(lambda m: "<style>\n" + (WEB / m.group(1)).read_text(encoding="utf-8") + "</style>", html)

    def js(m):
        src = m.group(1)
        body = data_js(payload) if src == "data/taxi-data.js" else (WEB / src).read_text(encoding="utf-8")
        return "<script>\n" + body + "</script>"
    html = LOCAL_JS.sub(js, html)
    html = html.replace("assets/images/ev7logo.png", logo_uri())
    left = LINK_CSS.findall(html) + LOCAL_JS.findall(html)
    if left:
        raise SystemExit(f"❌ ยังมีไฟล์ที่ไม่ได้รวม: {left}")
    check_js(web_js((WEB / "index.html").read_text(encoding="utf-8")))
    out_file.write_text(html, encoding="utf-8")
    print(f"เขียนไฟล์เดียว {out_file} · {out_file.stat().st_size / 1e6:.1f} MB")


def main():
    print("โหลด ...", flush=True)
    d = load_points()
    print("ทำความสะอาด ...", flush=True)
    d, last_known, log = clean(d)
    for k, v in log.items():
        print(f"  {k:<18} {v:>10,}")
    print("ระบุพื้นที่ ...", flush=True)
    d, dists, provs = assign_area(d)
    cols, meta, vehicles, areas = encode(d, dists, provs, last_known, log)
    print(f"  รถ {len(vehicles['vin']):,} คัน · จุด {meta['n']:,} · "
          f"ช่วง {meta['t0']} + {meta['tmax'] / 3600:.1f} ชม.")
    d.to_parquet(OUT_DIR / "points_clean.parquet", index=False)
    places = None
    if V2:
        print("หาลานจอดและดึงที่อยู่ ...", flush=True)
        deps = find_depots(d)
        print(f"  ลานจอด {len(deps)} แห่ง · {sum(x[2] for x in deps):,} คัน")
        places = geocode([(la, lo) for la, lo, _ in deps])
    ev = None
    if V2:
        print("สถานีชาร์จ EV (OpenStreetMap) ...", flush=True)
        ev = ev_chargers()
        print(f"  {len(ev):,} จุด")
    payload = make_payload(cols, meta, vehicles, areas, places, ev)
    if WEB_DIR:
        write_web(WEB_DIR, payload)
    if BUNDLE:
        write_bundle(BUNDLE, payload)
    if not (WEB_DIR or BUNDLE):
        render(payload)


if __name__ == "__main__":
    main()
