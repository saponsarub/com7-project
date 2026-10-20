# ── 7.2 · คำถามเชิงวิเคราะห์ — ช่วงเวลา · ช่วงข้อมูล · สถานีชาร์จ · แนะนำทำเล · เดาปลายทาง · รับผู้โดยสาร · สัดส่วน ──
# รันหลัง 7.1 · ทุกตัวเลขคำนวณจากข้อมูลจริง (pos / chg) — LLM แค่เรียบเรียง
#
# เลือกประเภทคำถามด้วย "ความหมายใกล้ตัวอย่าง" (semantic router): แปลงคำถามเป็นเวกเตอร์ด้วย MiniLM ตัวเดิม (enc)
# แล้วเทียบกับตัวอย่างของแต่ละประเภท ถ้าใกล้พอ (≥ ROUTE_MIN) ใช้ประเภทนั้น · ไม่ต้องเทรนใหม่ · อยากให้เข้าใจเพิ่ม = เพิ่มตัวอย่างใน EXAMPLES
import json
import numpy as np
import pandas as pd
from shapely.geometry import shape, Point
from shapely import STRtree

ROUTE_MIN = 0.72          # ต่ำกว่านี้ = ไม่ใช่คำถามวิเคราะห์ → ส่งต่อให้ระบบเดิม
NEAR_KM = 0.3             # "จอดใกล้สถานีชาร์จ" = ภายใน 300 ม.
TH_MONTH = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def th_hour(h):
    # 15 → "บ่าย 3" · คนไทยพูดเวลาแบบนี้
    if h == 0: return "เที่ยงคืน"
    if h < 6: return f"ตี {h}"
    if h < 12: return f"{h} โมงเช้า"
    if h == 12: return "เที่ยง"
    if h < 16: return f"บ่าย {h - 12}"
    if h < 19: return f"{h - 12} โมงเย็น"
    return f"{h - 18} ทุ่ม"


def th_date(t):
    t = pd.Timestamp(t)
    return f"{t.day} {TH_MONTH[t.month]} {t.year}"


# ── เตรียมข้อมูลครั้งเดียว ─────────────────────────────────────────────────
_ok = pos[pos.signal != "V"]
_feat = json.load(open(OUT / "dist_pip.geojson", encoding="utf-8"))["features"]
_polys = [shape(f["geometry"]) for f in _feat]
_tree = STRtree(_polys)


def _dist_idx(lat, lon):
    hit = _tree.query(Point(lon, lat), predicate="within")
    return int(hit[0]) if len(hit) else -1


chg["dist"] = [_dist_idx(a, b) for a, b in zip(chg.lat, chg.lon)]
chg["dist_code"] = [dist.pc.iloc[i][2:] if i >= 0 else None for i in chg["dist"]]
chg["prov_code"] = [dist.ppc.iloc[i][2:] if i >= 0 else None for i in chg["dist"]]
chg["dist_th"] = [dist.th.iloc[i] if i >= 0 else None for i in chg["dist"]]
_dist_cent = pd.DataFrame({"lat": [p.centroid.y for p in _polys], "lon": [p.centroid.x for p in _polys]})

# จำนวนรถเฉลี่ยต่อชั่วโมงในแต่ละเขต/อำเภอ (นับรถไม่ซ้ำต่อชั่วโมง แล้วเฉลี่ยทุกชั่วโมงที่มีข้อมูล)
_hr = _ok.assign(hour=_ok.gps_time.dt.floor("h"))
_n_hours = _hr.hour.nunique()
_dist_load = (_hr.groupby(["dist_code", "hour"]).car_id.nunique().groupby("dist_code").sum() / _n_hours).rename("cars_avg")


# ── ตัวคำนวณ ──────────────────────────────────────────────────────────────
def x_peak_hour(when=None):
    f = _hr[_hr.meter == "F"]
    per = f.groupby("hour").car_id.nunique()                      # รถมีผู้โดยสาร (ไม่ซ้ำ) ต่อชั่วโมง
    by_h = per.groupby(per.index.hour).mean().round().astype(int)
    h = int(by_h.idxmax())
    low = int(by_h.idxmin())
    return {"text": f"ช่วงที่มีผู้โดยสารมากที่สุดคือ {th_hour(h)} ({h:02d}:00–{h:02d}:59) เฉลี่ย {by_h[h]} คันที่มีผู้โดยสาร · "
                    f"น้อยสุดคือ {th_hour(low)} ({by_h[low]} คัน) · คิดจากข้อมูล {th_date(pos.gps_time.min())} – {th_date(LATEST)} "
                    f"(ข้อมูลแค่ประมาณ 1 วันครึ่ง ยังสรุปเป็นแนวโน้มประจำไม่ได้)"}


def x_data_range(when=None):
    a, b = pos.gps_time.min(), pos.gps_time.max()
    return {"text": f"มีข้อมูลตั้งแต่ {th_date(a)} {a:%H:%M} ถึง {th_date(b)} {b:%H:%M} "
                    f"รวม {pos.car_id.nunique():,} คัน · ระบบถือว่า \"ตอนนี้\" = {b:%H:%M} ของวันที่ {th_date(b)}"}


def x_chargers_in_area(place, when=None):
    if place:
        col = "prov_code" if place["level"] == "prov" else "dist_code"
        sub = chg[chg[col] == place["code"]]
        scope = place["label"]
    else:
        sub, scope = chg, "ทั้งประเทศ"
    by = sub.dist_th.value_counts().head(5)
    top = " · ".join(f"{k} {v} แห่ง" for k, v in by.items())
    return {"text": f"{scope} มีสถานีชาร์จ EV {len(sub)} แห่ง" + (f" (มากสุด: {top})" if len(sub) else "")
                    + " — ข้อมูลจาก OpenStreetMap มีแค่บางส่วน ของจริงน่าจะมากกว่านี้"}


def x_cars_near_chargers(place, when):
    now = latest_at(when[1])
    now = now[now.status == "จอด"]
    c = chg
    if place:
        col = "prov_code" if place["level"] == "prov" else "dist_code"
        c, now = chg[chg[col] == place["code"]], now[now[col] == place["code"]]
    if c.empty:
        return {"text": "ไม่พบสถานีชาร์จในพื้นที่นี้ในข้อมูล OpenStreetMap"}
    d = hav_km(now.lat.values[:, None], now.lon.values[:, None], c.lat.values[None, :], c.lon.values[None, :])
    near = d.min(axis=1) <= NEAR_KM
    nearest = d.argmin(axis=1)[near]
    top = pd.Series(nearest).map(lambda i: f"{c.name.iloc[i]} ({c.dist_th.iloc[i]})").value_counts().head(3)
    lst = " · ".join(f"{k} {v} คัน" for k, v in top.items())
    return {"text": f"ณ {fmt_t(when[1])} มีรถจอดอยู่ใกล้สถานีชาร์จ (ภายใน {int(NEAR_KM * 1000)} ม.) ประมาณ {int(near.sum())} คัน"
                    + (f" — มากสุดที่ {lst}" if lst else "")
                    + " · เป็นการประมาณจากระยะห่าง ไม่รู้ว่ากำลังชาร์จจริงหรือไม่"}


def x_site_recommend(place, when=None):
    code = place["code"][:2] if place else "10"                    # ไม่ระบุ = กรุงเทพฯ
    d = dist[dist.ppc.str[2:] == code].assign(dist_code=lambda x: x.pc.str[2:])
    d = d.merge(_dist_load, left_on="dist_code", right_index=True, how="left").fillna({"cars_avg": 0})
    d["chargers"] = d.dist_code.map(chg.dist_code.value_counts()).fillna(0).astype(int)
    d["score"] = d.cars_avg / (d.chargers + 1)                      # รถเยอะ + สถานีน้อย = น่าเปิด
    top = d.nlargest(3, "score")
    unit = "เขต" if code == "10" else "อำเภอ"
    lst = " · ".join(f"{i}. {unit}{r.th} (รถเฉลี่ย {r.cars_avg:.0f} คัน/ชม. · สถานีชาร์จ {r.chargers} แห่ง)"
                     for i, r in enumerate(top.itertuples(), 1))
    return {"text": f"{unit}ที่น่าเปิดสถานีชาร์จใน{name_of[code]} (รถเยอะแต่สถานีน้อย): {lst} "
                    f"— เป็นคำแนะนำเบื้องต้นจากจำนวนรถและสถานีใน OpenStreetMap เท่านั้น ยังไม่ได้ดูค่าเช่า/ไฟฟ้า/ที่จอด"}


def x_lost_signal(plate, place, when):
    # รถที่สัญญาณหาย: จุดสุดท้ายเก่ากว่า 15 นาที หรือ signal = V · เดาปลายทางจากทิศ + ความเร็วล่าสุด
    last = _ok[_ok.gps_time <= when[1]].groupby("car_id").tail(1)
    lost = last[(when[1] - last.gps_time > STALE) & (last.speed >= 20)]
    if plate:
        lost = lost[lost.plate_key.str.upper() == plate]
    elif place:
        col = "prov_code" if place["level"] == "prov" else "dist_code"
        lost = lost[lost[col] == place["code"]]
    if lost.empty:
        return {"text": "ไม่พบรถที่สัญญาณหายระหว่างวิ่งตามเงื่อนไขนี้"}
    out = []
    for r in lost.sort_values("gps_time", ascending=False).head(3).itertuples():
        hrs = (when[1] - r.gps_time).total_seconds() / 3600
        km = min(r.speed * hrs, 150)                                 # ไม่เดาไกลเกิน 150 กม.
        rad = np.radians(r.direction)
        lat2 = r.lat + km / 111 * np.cos(rad)
        lon2 = r.lon + km / (111 * np.cos(np.radians(r.lat))) * np.sin(rad)
        i = _dist_idx(lat2, lon2)
        if i < 0:
            i = int(hav_km(lat2, lon2, _dist_cent.lat, _dist_cent.lon).idxmin())
        out.append(f"{r.plate} สัญญาณหาย {fmt_t(r.gps_time)} ที่ {r.dist_th}, {r.prov_th} (วิ่ง {r.speed:.0f} กม./ชม. ทิศ {r.direction:.0f}°) "
                   f"→ ถ้าวิ่งต่อทางเดิม น่าจะไปทาง {dist.th.iloc[i]}, {dist.pth.iloc[i]}")
    return {"text": " · ".join(out) + f" (พบรถสัญญาณหายระหว่างวิ่ง {len(lost)} คัน · เป็นการคาดเดาจากทิศทาง ไม่ใช่ตำแหน่งจริง · ข้อมูลไม่มีชื่อถนน)"}


def x_top_trips(when=None):
    s = pos.sort_values(["car_id", "gps_time"])
    f = s.meter.eq("F")
    start = f & ~f.groupby(s.car_id).shift(fill_value=False)        # เปลี่ยนจากว่าง → มีผู้โดยสาร = รับ 1 ครั้ง
    dt = s.groupby("car_id").gps_time.diff().shift(-1)
    dur = dt.where(f & (dt <= STALE), pd.Timedelta(0))
    g = pd.DataFrame({"car_id": s.car_id, "plate": s.plate, "trip": start, "dur": dur}) \
          .groupby(["car_id", "plate"]).agg(trips=("trip", "sum"), dur=("dur", "sum")).reset_index()
    top = g.sort_values(["trips", "dur"], ascending=False).head(3)
    lst = " · ".join(f"{r.plate} รับ {int(r.trips)} ครั้ง รวม {r.dur.total_seconds() / 3600:.1f} ชั่วโมง" for r in top.itertuples())
    return {"text": f"รถที่รับผู้โดยสารบ่อยสุด ({th_date(pos.gps_time.min())} – {th_date(LATEST)}): {lst} "
                    f"· เฉลี่ยทั้งฝูง {g.trips.mean():.1f} ครั้งต่อคัน (นับจากมิเตอร์เปลี่ยนเป็นมีผู้โดยสาร)"}


def x_status_ratio(place, when):
    now = latest_at(when[1])
    scope = "ทั้งหมด"
    if place:
        col = "prov_code" if place["level"] == "prov" else "dist_code"
        now, scope = now[now[col] == place["code"]], place["label"]
    vc = now.status.value_counts()
    pct = (vc / vc.sum() * 100).round().astype(int)
    hired, park, run = pct.get("มีผู้โดยสาร", 0), pct.get("จอด", 0), pct.get("ว่าง·วิ่ง", 0)
    def ratio(a, b):                                                # ปรับให้รวมเป็น 100 เช่น 11:58 → 16:84
        x = round(a / (a + b) * 100) if a + b else 0
        return f"{x}:{100 - x}"
    return {"text": f"ณ {fmt_t(when[1])} รถออนไลน์{scope} {vc.sum():,} คัน · มีผู้โดยสาร {hired}% · วิ่งว่าง {run}% · จอด {park}% "
                    f"→ รถวิ่ง : รถจอด ≈ {ratio(hired + run, park)} · รถมีผู้โดยสาร : รถจอด ≈ {ratio(hired, park)}"}


# ── ตัวเลือกประเภทคำถาม ──────────────────────────────────────────────────
EXAMPLES = {
    "peak_hour": ["เวลากี่โมงมีผู้โดยสารมากที่สุด", "ช่วงไหนคนเรียกแท็กซี่เยอะสุด", "ชั่วโมงเร่งด่วนคือกี่โมง",
                  "ผู้โดยสารเยอะช่วงเวลาไหน", "ช่วงเวลาที่รถว่างน้อยที่สุด", "peak hour ตอนไหน"],
    "data_range": ["มีข้อมูลของวันไหนบ้าง", "ข้อมูลเริ่มวันไหนถึงวันไหน", "ข้อมูลล่าสุดถึงเมื่อไหร่",
                   "ช่วงวันที่ของข้อมูล", "ข้อมูลมีกี่วัน", "อัปเดตข้อมูลล่าสุดกี่โมง"],
    "chargers_in_area": ["มีสถานีชาร์จกี่แห่งในสถานที่", "สถานที่มีปั๊มอีวีกี่ที่", "จำนวนสถานีชาร์จรถไฟฟ้าในสถานที่",
                         "นับที่ชาร์จ EV ในสถานที่", "ทั้งประเทศมีสถานีชาร์จกี่แห่ง",
                         "มีสถานีชาจรถevกี่แห่งในสถานที่", "สถานที่มีที่ชาร์จ ev กี่จุด", "charger ในสถานที่มีกี่ที่"],
    "cars_near_chargers": ["มีรถจอดอยู่ที่สถานีชาร์จกี่คัน", "รถกำลังชาร์จอยู่กี่คัน", "รถจอดใกล้ปั๊ม EV กี่คัน",
                           "ตอนนี้มีรถอยู่ที่จุดชาร์จกี่คัน", "สถานีชาร์จไหนมีรถจอดเยอะสุด"],
    "site_recommend": ["ถ้าอยากเปิดปั๊ม EV ควรเปิดเขตไหน", "ควรตั้งสถานีชาร์จที่ไหนดี", "ทำเลไหนเหมาะเปิดจุดชาร์จ",
                       "พื้นที่ไหนขาดสถานีชาร์จ", "เปิดปั๊มอีวีที่อำเภอไหนดีในสถานที่", "เขตไหนสถานีชาร์จไม่พอ"],
    "lost_signal": ["รถสัญญาณหายคิดว่าวิ่งไปไหน", "รถที่โดนตัดสัญญาณน่าจะไปที่ไหน", "สัญญาณขาดล่าสุดที่ไหน รถจะไปไหนต่อ",
                    "รถที่ขาดการติดต่อไปทางไหน", "รถมีสัญญาณสุดท้ายที่ถนนสุขุมวิท คิดว่าวิ่งไปไหน", "เดาปลายทางรถที่สัญญาณหาย"],
    "top_trips": ["รถคันไหนรับผู้โดยสารบ่อยสุด", "คันไหนวิ่งงานเยอะที่สุด", "รถที่รับลูกค้ามากที่สุด",
                  "คนขับคันไหนขยันสุด", "อันดับรถที่มีเที่ยวผู้โดยสารมากสุด"],
    "status_ratio": ["เทียบสัดส่วนรถที่วิ่งกับรถที่จอด", "รถจอดกี่เปอร์เซ็นต์", "สัดส่วนรถมีผู้โดยสารต่อรถว่าง",
                     "อัตราส่วนรถวิ่งต่อรถจอด", "รถมีผู้โดยสารคิดเป็นกี่เปอร์เซ็นต์"],
    # คำถามที่หน้าตาคล้าย แต่ระบบเดิม (ส่วน 6) ตอบอยู่แล้ว → ส่งกลับ
    "_pass": ["แถวสถานที่มีปั๊มชาร์จไหม", "ที่ชาร์จใกล้สถานที่", "หาที่ชาร์จแถวสถานที่", "สถานีชาร์จใกล้รถ ทะเบียนรถ",
              "สถานที่มีรถกี่คัน", "รถออกนอกเขตกี่คัน", "ทะเบียนรถ อยู่ไหน",
              "แถวสถานที่มีแท็กซี่วิ่งอยู่ไหมตอนนี้", "ตอนนี้สถานที่มีรถวิ่งไหม", "สถานที่มีรถว่างไหม", "รถออกนอกเขตวันนี้ไปไหนบ้าง"],
}
_ex_q = [(k, q) for k, qs in EXAMPLES.items() for q in qs]
_ex_v = enc.encode([mask(q) for _, q in _ex_q], normalize_embeddings=True)
_base = train_df.groupby("intent").head(40)                          # ตัวอย่างคำถามแบบเดิม (ส่วน 4) ไว้เทียบ
_base_v = enc.encode(_base.masked.tolist(), normalize_embeddings=True)

ANALYTIC = {
    "peak_hour": lambda e: x_peak_hour(),
    "data_range": lambda e: x_data_range(),
    "chargers_in_area": lambda e: x_chargers_in_area(e["place"]),
    "cars_near_chargers": lambda e: x_cars_near_chargers(e["place"], e["when"]),
    "site_recommend": lambda e: x_site_recommend(e["place"]),
    "lost_signal": lambda e: x_lost_signal(e["plate"], e["place"], e["when"]),
    "top_trips": lambda e: x_top_trips(),
    "status_ratio": lambda e: x_status_ratio(e["place"], e["when"]),
}


def route_analytic(q, verbose=False):
    """คืน (intent, ข้อความข้อเท็จจริง) ถ้าเป็นคำถามวิเคราะห์ · ไม่ใช่ = None"""
    v = enc.encode([mask(q)], normalize_embeddings=True)[0]
    sim = _ex_v @ v
    i = int(sim.argmax())
    intent, score = _ex_q[i][0], float(sim[i])
    base = float((_base_v @ v).max())                                # ใกล้คำถามแบบเดิมมากกว่า → ให้ระบบเดิมตอบ
    if verbose:
        print(f"  analytic? {intent} ({score:.2f} · แบบเดิม {base:.2f}) ใกล้ตัวอย่าง: {_ex_q[i][1]}")
    if score < ROUTE_MIN or score < base or intent == "_pass":
        return None
    return intent, ANALYTIC[intent](extract(q))["text"]


# ห่อ ask() ส่วน 7 (รันซ้ำได้ ไม่ห่อซ้อน)
if "_ask_pre_analytic" not in globals():
    _ask_pre_analytic = ask
def ask(q, verbose=False):
    r = route_analytic(q, verbose)
    return r[1] if r else _ask_pre_analytic(q, verbose)


for q in ["เวลาประมาณกี่โมงมีผู้โดยสารมากที่สุด", "มีข้อมูลของวันไหนบ้าง", "มีสถานีชาจรถevกี่แห่งในกรุงเทพ",
          "มีรถจอดอยู่ที่สถานีจอดรถevกี่คัน", "ถ้าอยากเปิดปั้ม ev ควรเปิดเขตไหน",
          "รถมีสัญญาณที่ถนนสุขุมวิทสุดท้ายก่อนโดนตัด คิดว่าวิ่งไปไหน", "รถคันไหนที่รับผู้โดยสารบ่อยสุด",
          "เทียบสัดส่วนรถที่วิ่งกับรถที่จอด", "ตอนนี้ภูเก็ตมีรถกี่คัน"]:
    print("Q:", q); print("A:", ask(q, verbose=True)); print()
