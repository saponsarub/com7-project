# ── 15 · สร้างชุดข้อมูลสอน text-to-SQL (AI ตัวใหญ่เขียนโจทย์ → ตรวจกับข้อมูลจริง → ใช้สอน Qwen) ──
# ต้องรันส่วน 0–7 และ cell 13 (ตาราง SQL + db) ก่อน · ไม่ต้องใช้ GPU · ~1–3 นาที
#
# แต่ละตัวอย่าง = บทสนทนาเต็ม 1 รอบ:  ผู้ใช้ถาม → โมเดลเรียก run_sql (SQL เฉลย) → ผล SQL จริง → คำตอบภาษาไทย
# - คำถาม/SQL/รูปแบบคำตอบ เขียนโดย Claude (ครอบคลุม ~35 แบบคำถาม × หลายสำนวน) · เติมจังหวัด/เขต/ทะเบียน/เวลา จากข้อมูลจริง
# - SQL ทุกข้อถูกรันจริง · error หรือผลแปลก = ทิ้ง → เฉลยถูกเสมอ
# - แบ่ง train / test ตาม "สำนวน" (สำนวนใน test ไม่เคยเห็นตอนเทรน) → วัดว่าเข้าใจจริง ไม่ใช่จำประโยค
import json, random, re
import pandas as pd

random.seed(42)
TODAY = LATEST.normalize()
YDAY = TODAY - pd.Timedelta(days=1)
D_TODAY, D_YDAY = f"{TODAY:%Y-%m-%d}", f"{YDAY:%Y-%m-%d}"
ZONE_TH = ["กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "สมุทรสาคร", "นครปฐม"]
ZONE_SQL = ", ".join(f"'{z}'" for z in ZONE_TH)

# ── prompt สั้นของโมเดลที่เทรน (ใช้ทั้งตอนเทรนและตอนใช้งาน · สั้นกว่า SYSTEM_A → ตอบเร็วขึ้น) ──
SYSTEM_FT = f"""คุณคือผู้ช่วยวิเคราะห์ข้อมูลรถแท็กซี่ไฟฟ้า EV7 ตอบภาษาไทยสั้น ๆ ตัวเลขต้องมาจากผล run_sql เท่านั้น
ตาราง: points(car_id, plate, plate_key, ts, lat, lon, speed, direction, meter, signal, status, dist_th, prov_th) ทุกจุด GPS
 now(คอลัมน์เดียวกัน) ตำแหน่งล่าสุดของรถออนไลน์ · pickups(car_id, plate, ts, lat, lon, dist_th, prov_th) ทุกครั้งที่รับผู้โดยสาร
 chargers(name, operator, lat, lon, dist_th, prov_th) สถานีชาร์จ OSM บางส่วน · ฟังก์ชัน dist_km(lat1, lon1, lat2, lon2)
status: 'จอด' 'วิ่งว่าง' 'มีผู้โดยสาร' 'ไม่มีสัญญาณ' · plate_key = ทะเบียนไม่มีขีด/เว้นวรรค · นับรถใช้ COUNT(DISTINCT car_id)
ตอนนี้ = {LATEST:%Y-%m-%d %H:%M} · วันนี้ = {D_TODAY} · เมื่อวาน = {D_YDAY} · นอกเขต = prov_th NOT IN ({ZONE_SQL})
ข้อมูลไม่มี: ชื่อถนน รายได้ แบตเตอรี่ ข้อมูลคนขับ · สั่งการรถไม่ได้"""
TOOLS_FT = [t for t in TOOLS_A if t["function"]["name"] == "run_sql"]

# ── ค่าที่สุ่มเติมในคำถาม (จากข้อมูลจริง) ─────────────────────────────────
_cnt = T_NOW.groupby("prov_th").car_id.nunique()
PROVS = _cnt[_cnt >= 3].index.tolist()
BKK_D = T_NOW[T_NOW.prov_th == "กรุงเทพมหานคร"].dist_th.value_counts().index[:40].tolist()
PROV_D = T_NOW[T_NOW.prov_th != "กรุงเทพมหานคร"].groupby(["prov_th", "dist_th"]).size().index.tolist()
PLATES = T_POINTS.groupby("plate").size().pipe(lambda s: s[s > 50]).index.tolist()
CHG_P = T_CHARGERS.prov_th.dropna().value_counts().index.tolist()
DAYS = [("วันนี้", D_TODAY), ("เมื่อวาน", D_YDAY), (f"วันที่ {TODAY.day} ", D_TODAY), (f"วันที่ {YDAY.day} ", D_YDAY)]   # เว้นวรรคท้าย "วันที่ 30 " ไม่ติดคำถัดไป
HOUR_TH = {6: "6 โมงเช้า", 7: "7 โมงเช้า", 8: "8 โมงเช้า", 9: "9 โมง", 10: "10 โมง", 12: "เที่ยง", 13: "บ่ายโมง", 14: "บ่าย 2",
           15: "บ่าย 3", 16: "4 โมงเย็น", 17: "5 โมงเย็น", 18: "6 โมงเย็น", 19: "1 ทุ่ม", 20: "2 ทุ่ม", 21: "3 ทุ่ม", 22: "4 ทุ่ม"}


def ptypo(name):
    # สะกดผิด/ย่อ แบบที่คนพิมพ์จริง → SQL ยังต้องใช้ชื่อที่ถูก
    alias = {"กรุงเทพมหานคร": ["กทม", "กรุงเทพ", "กรุงเทพฯ"], "นครราชสีมา": ["โคราช"], "พระนครศรีอยุธยา": ["อยุธยา"]}
    r = random.random()
    if name in alias and r < 0.5:
        return random.choice(alias[name])
    return typo(name, 0.25) if r < 0.8 else name


def plate_text(p):
    # ผู้ใช้พิมพ์ทะเบียนได้หลายแบบ: EV-0152 · EV 0152 · ev0152
    k = re.sub(r"[\s-]", "", p)
    return random.choice([p, p, p.replace("-", " "), k.lower() if k.isascii() else k])


def pkey(p):
    return re.sub(r"[\s-]", "", p).upper()


def th_h(h):
    return HOUR_TH.get(h, f"{h}:00")


def n(x):
    return f"{int(x):,}"


def rows_txt(df, unit="คัน", k=5):
    return " · ".join(f"{i}. {r[0]} {n(r[1])} {unit}" for i, r in enumerate(df.head(k).itertuples(index=False), 1))


# ── แบบคำถาม: (ชื่อ, [สำนวน], สร้างพารามิเตอร์, SQL, สร้างคำตอบจากผล) ─────────────
F = []
def fam(name, qs, gen, sql, ans):
    F.append(dict(name=name, qs=qs, gen=gen, sql=sql, ans=ans))

fam("cars_now_prov",
    ["ตอนนี้{p}มีรถกี่คัน", "{p}มีแท็กซี่ออนไลน์กี่คัน", "รถเราอยู่{p}ตอนนี้กี่คัน", "ขอจำนวนรถใน{p}หน่อย", "{p} มีรถอยู่เท่าไหร่", "แถว{p}มีรถไหม"],
    lambda: {"P": random.choice(PROVS)},
    "SELECT COUNT(DISTINCT car_id) AS cars FROM now WHERE prov_th = '{P}'",
    lambda d, a: f"ตอนนี้{a['P']}มีรถออนไลน์ {n(d.iloc[0, 0])} คันครับ")
fam("status_now_prov",
    ["{p}ตอนนี้มีรถว่างกี่คัน มีผู้โดยสารกี่คัน", "แยกสถานะรถใน{p}ให้หน่อย", "รถใน{p}จอดกี่คัน วิ่งกี่คัน", "{p}มีรถกี่คัน ว่างกี่คัน มีคนนั่งกี่คัน", "สถานะรถ{p}ตอนนี้"],
    lambda: {"P": random.choice(PROVS)},
    "SELECT status, COUNT(DISTINCT car_id) AS cars FROM now WHERE prov_th = '{P}' GROUP BY status ORDER BY cars DESC",
    lambda d, a: f"{a['P']}มีรถ {n(d.cars.sum())} คัน: " + " · ".join(f"{s} {n(c)}" for s, c in zip(d.status, d.cars)) + " ครับ")
fam("cars_now_bkk_dist",
    ["เขต{d}มีรถกี่คัน", "ตอนนี้แถว{d}มีแท็กซี่กี่คัน", "{d}มีรถว่างไหม", "รถในเขต{d}ตอนนี้"],
    lambda: {"D": random.choice(BKK_D)},
    "SELECT status, COUNT(DISTINCT car_id) AS cars FROM now WHERE prov_th = 'กรุงเทพมหานคร' AND dist_th = '{D}' GROUP BY status ORDER BY cars DESC",
    lambda d, a: f"เขต{a['D']}มีรถ {n(d.cars.sum())} คัน (" + " · ".join(f"{s} {n(c)}" for s, c in zip(d.status, d.cars)) + ")")
fam("moving_now_prov",
    ["แถว{p}มีแท็กซี่วิ่งอยู่ไหมตอนนี้", "ตอนนี้{p}มีรถวิ่งอยู่กี่คัน", "{p}มีรถกำลังวิ่งไหม", "รถที่วิ่งอยู่ใน{p}ตอนนี้"],
    lambda: {"P": random.choice(PROVS)},
    "SELECT COUNT(DISTINCT car_id) FILTER (WHERE status IN ('วิ่งว่าง', 'มีผู้โดยสาร')) AS moving, COUNT(DISTINCT car_id) AS online FROM now WHERE prov_th = '{P}'",
    lambda d, a: f"{a['P']}ตอนนี้มีรถกำลังวิ่ง {n(d.moving[0])} คัน จากรถออนไลน์ {n(d.online[0])} คันครับ")
fam("out_of_zone_day_where",
    ["{day}รถออกนอกเขตกี่คัน ไปไหนบ้าง", "รถออกนอกเขต{day}ไปจังหวัดไหนบ้าง กี่คัน", "{day}มีรถหลุดโซนกี่คัน อยู่จังหวัดไหน"],
    lambda: dict(zip(("DAYW", "DAY"), random.choice(DAYS))),
    "SELECT prov_th, COUNT(DISTINCT car_id) AS cars, (SELECT COUNT(DISTINCT car_id) FROM points WHERE CAST(ts AS DATE) = '{DAY}' AND signal <> 'V' AND prov_th NOT IN (" + ZONE_SQL + ")) AS total FROM points WHERE CAST(ts AS DATE) = '{DAY}' AND signal <> 'V' AND prov_th NOT IN (" + ZONE_SQL + ") GROUP BY prov_th ORDER BY cars DESC LIMIT 5",
    lambda d, a: f"{a['DAYW']}มีรถออกนอกกรุงเทพฯ และปริมณฑล {n(d.total[0])} คัน ไปมากสุดที่ " + rows_txt(d[["prov_th", "cars"]], k=3))
fam("hired_now_prov",
    ["{p}มีรถรับผู้โดยสารอยู่กี่คัน", "ตอนนี้{p}มีรถที่มีผู้โดยสารกี่คัน", "รถไม่ว่างใน{p}กี่คัน"],
    lambda: {"P": random.choice(PROVS)},
    "SELECT COUNT(DISTINCT car_id) AS cars FROM now WHERE prov_th = '{P}' AND status = 'มีผู้โดยสาร'",
    lambda d, a: f"{a['P']}มีรถที่มีผู้โดยสาร {n(d.iloc[0, 0])} คันครับ")
fam("idle_now_prov",
    ["รถว่างใน{p}มีกี่คัน", "{p}มีรถว่างพร้อมรับงานกี่คัน", "ตอนนี้{p}รถว่างเท่าไหร่"],
    lambda: {"P": random.choice(PROVS)},
    "SELECT COUNT(DISTINCT car_id) AS cars FROM now WHERE prov_th = '{P}' AND status IN ('จอด', 'วิ่งว่าง')",
    lambda d, a: f"{a['P']}มีรถว่าง (จอดหรือวิ่งว่าง) {n(d.iloc[0, 0])} คันครับ")
fam("fleet_now",
    ["ตอนนี้รถออนไลน์ทั้งหมดกี่คัน", "ภาพรวมรถตอนนี้", "ทั้งระบบมีรถกี่คัน แยกสถานะ", "สรุปสถานะรถทั้งหมด", "รถทั้งฝูงตอนนี้เป็นยังไง"],
    lambda: {},
    "SELECT status, COUNT(DISTINCT car_id) AS cars FROM now GROUP BY status ORDER BY cars DESC",
    lambda d, a: f"ตอนนี้รถออนไลน์ {n(d.cars.sum())} คัน: " + " · ".join(f"{s} {n(c)}" for s, c in zip(d.status, d.cars)))
fam("top_prov_now",
    ["จังหวัดไหนมีรถมากที่สุด", "5 จังหวัดที่รถเยอะสุด", "จัดอันดับจังหวัดตามจำนวนรถ", "รถกระจุกอยู่จังหวัดไหน"],
    lambda: {},
    "SELECT prov_th, COUNT(DISTINCT car_id) AS cars FROM now GROUP BY prov_th ORDER BY cars DESC LIMIT 5",
    lambda d, a: "จังหวัดที่มีรถมากที่สุด: " + rows_txt(d))
fam("top_dist_in_prov",
    ["เขตไหนใน{p}มีรถมากที่สุด", "อำเภอไหนใน{p}รถเยอะสุด", "จัดอันดับพื้นที่ใน{p}ตามจำนวนรถ", "ใน{p} รถอยู่แถวไหนเยอะ"],
    lambda: {"P": random.choice(["กรุงเทพมหานคร"] * 3 + PROVS[:15])},
    "SELECT dist_th, COUNT(DISTINCT car_id) AS cars FROM now WHERE prov_th = '{P}' GROUP BY dist_th ORDER BY cars DESC LIMIT 5",
    lambda d, a: f"พื้นที่ใน{a['P']}ที่มีรถมากที่สุด: " + rows_txt(d))
fam("car_where",
    ["{pl} อยู่ไหน", "รถ {pl} ตอนนี้อยู่ที่ไหน", "ตำแหน่งล่าสุดของ {pl}", "{pl} วิ่งอยู่หรือจอด", "เช็คสถานะ {pl} หน่อย"],
    lambda: {"PL": random.choice(PLATES)},
    "SELECT plate, ts, status, speed, dist_th, prov_th FROM points WHERE plate_key = '{K}' ORDER BY ts DESC LIMIT 1",
    lambda d, a: f"{d.plate[0]} อยู่ที่{d.dist_th[0]} {d.prov_th[0]} สถานะ{d.status[0]} (จุดล่าสุด {pd.Timestamp(d.ts[0]):%d/%m %H:%M})")
fam("car_km_day",
    ["{pl} {day}วิ่งไปกี่กิโล", "{day} {pl} วิ่งไปกี่กิโลเมตร", "ระยะทางของ {pl} {day}", "{pl} วิ่งได้กี่โล{day}"],
    lambda: dict(zip(("DAYW", "DAY"), random.choice(DAYS)), PL=random.choice(PLATES)),
    """SELECT ROUND(SUM(dist_km(lat0, lon0, lat, lon)), 1) AS km FROM (SELECT lat, lon, lag(lat) OVER w AS lat0, lag(lon) OVER w AS lon0,
 ts - lag(ts) OVER w AS gap FROM points WHERE plate_key = '{K}' AND CAST(ts AS DATE) = '{DAY}' AND signal <> 'V' WINDOW w AS (ORDER BY ts))
 WHERE gap <= INTERVAL 15 MINUTE""",
    lambda d, a: f"{a['PL']} {a['DAYW']}วิ่งประมาณ {d.km[0]} กม. ครับ (คิดจากระยะเส้นตรงระหว่างจุด GPS)")
fam("car_provinces",
    ["{pl} ไปจังหวัดไหนมาบ้าง", "{pl} ผ่านจังหวัดอะไรบ้าง", "{pl} ออกต่างจังหวัดไหม"],
    lambda: {"PL": random.choice(PLATES)},
    "SELECT prov_th, COUNT(*) AS points, MIN(ts) AS first_seen FROM points WHERE plate_key = '{K}' AND signal <> 'V' GROUP BY prov_th ORDER BY first_seen",
    lambda d, a: f"{a['PL']} อยู่ใน " + ", ".join(d.prov_th) + ("" if len(d) > 1 else " จังหวัดเดียว ไม่ได้ออกต่างจังหวัด"))
fam("car_pickups",
    ["{pl} รับผู้โดยสารกี่ครั้ง", "{pl} ได้งานกี่เที่ยว", "{pl} รับลูกค้าไปกี่รอบ"],
    lambda: {"PL": random.choice(PLATES)},
    "SELECT COUNT(*) AS pickups FROM pickups WHERE plate = '{PL}'",
    lambda d, a: f"{a['PL']} รับผู้โดยสาร {n(d.pickups[0])} ครั้งตลอดช่วงข้อมูลครับ")
fam("peak_hour_pickups",
    ["ชั่วโมงไหนรับผู้โดยสารมากที่สุด", "ช่วงไหนคนเรียกรถเยอะสุด", "เวลาไหนมีงานเยอะ", "peak hour ของการรับผู้โดยสาร"],
    lambda: {},
    "SELECT hour(ts) AS h, COUNT(*) AS pickups FROM pickups GROUP BY h ORDER BY pickups DESC LIMIT 3",
    lambda d, a: f"รับผู้โดยสารมากสุดช่วง {th_h(int(d.h[0]))} ({n(d.pickups[0])} ครั้ง) รองลงมา {th_h(int(d.h[1]))} และ {th_h(int(d.h[2]))}")
fam("peak_hour_hired",
    ["เวลากี่โมงมีผู้โดยสารมากที่สุด", "ช่วงไหนรถมีผู้โดยสารเยอะสุด", "ชั่วโมงไหนรถไม่ว่างมากสุด"],
    lambda: {},
    "SELECT hour(ts) AS h, COUNT(DISTINCT car_id) AS cars FROM points WHERE status = 'มีผู้โดยสาร' GROUP BY h ORDER BY cars DESC LIMIT 3",
    lambda d, a: f"ช่วง {th_h(int(d.h[0]))} มีรถที่มีผู้โดยสารมากที่สุด {n(d.cars[0])} คัน")
fam("pickups_prov_day",
    ["{day}{p}รับผู้โดยสารไปกี่ครั้ง", "{p}{day}มีงานกี่เที่ยว", "จำนวนการรับผู้โดยสารใน{p}{day}"],
    lambda: dict(zip(("DAYW", "DAY"), random.choice(DAYS)), P=random.choice(PROVS[:12])),
    "SELECT COUNT(*) AS pickups FROM pickups WHERE prov_th = '{P}' AND CAST(ts AS DATE) = '{DAY}'",
    lambda d, a: f"{a['DAYW']}{a['P']}มีการรับผู้โดยสาร {n(d.pickups[0])} ครั้ง")
fam("top_pickup_dist",
    ["เขตไหนใน{p}คนเรียกรถมากสุด", "จุดรับผู้โดยสารยอดนิยมใน{p}อยู่เขตไหน", "พื้นที่ไหนใน{p}ได้งานเยอะ"],
    lambda: {"P": random.choice(["กรุงเทพมหานคร"] * 3 + PROVS[:8])},
    "SELECT dist_th, COUNT(*) AS pickups FROM pickups WHERE prov_th = '{P}' GROUP BY dist_th ORDER BY pickups DESC LIMIT 5",
    lambda d, a: f"พื้นที่ใน{a['P']}ที่รับผู้โดยสารมากสุด: " + rows_txt(d, "ครั้ง"))
fam("top_cars_pickups",
    ["รถคันไหนรับผู้โดยสารบ่อยสุด", "คันไหนได้งานเยอะที่สุด", "5 อันดับรถที่รับลูกค้ามากสุด", "คนขับคันไหนขยันสุด"],
    lambda: {},
    "SELECT plate, COUNT(*) AS pickups FROM pickups GROUP BY plate ORDER BY pickups DESC LIMIT 5",
    lambda d, a: "รถที่รับผู้โดยสารบ่อยสุด: " + rows_txt(d, "ครั้ง"))
fam("data_range",
    ["มีข้อมูลของวันไหนบ้าง", "ข้อมูลเริ่มวันไหนถึงวันไหน", "ข้อมูลล่าสุดถึงเมื่อไหร่", "ข้อมูลมีกี่วัน"],
    lambda: {},
    "SELECT MIN(ts) AS first_ts, MAX(ts) AS last_ts, COUNT(DISTINCT car_id) AS cars FROM points",
    lambda d, a: f"มีข้อมูลตั้งแต่ {pd.Timestamp(d.first_ts[0]):%d/%m/%Y %H:%M} ถึง {pd.Timestamp(d.last_ts[0]):%d/%m/%Y %H:%M} รวม {n(d.cars[0])} คัน")
fam("online_at_hour",
    ["ตอน{h} {day}มีรถออนไลน์กี่คัน", "{day}ช่วง{h}มีรถวิ่งกี่คัน", "{day} {h} มีรถในระบบเท่าไหร่"],
    lambda: dict(zip(("DAYW", "DAY"), random.choice(DAYS)), H=random.choice(list(HOUR_TH))),
    "SELECT COUNT(DISTINCT car_id) AS cars FROM points WHERE CAST(ts AS DATE) = '{DAY}' AND hour(ts) = {H} AND signal <> 'V'",
    lambda d, a: f"{a['DAYW']}ช่วง{th_h(a['H'])} มีรถส่งสัญญาณ {n(d.cars[0])} คัน")
fam("compare_days_prov",
    ["เทียบ{p}เมื่อวานกับวันนี้ช่วง{h}ถึง{h2} รถเยอะขึ้นไหม", "{p} ช่วง{h}-{h2} เมื่อวานกับวันนี้ต่างกันยังไง", "เปรียบเทียบจำนวนรถใน{p} 2 วัน ช่วง{h}ถึง{h2}"],
    lambda: (lambda h: {"P": random.choice(PROVS[:12]), "H": h, "H2": h + random.choice([2, 3])})(random.choice([7, 8, 12, 13, 17, 18])),
    "SELECT CAST(ts AS DATE) AS d, COUNT(DISTINCT car_id) AS cars FROM points WHERE prov_th = '{P}' AND hour(ts) BETWEEN {H} AND {H2m} AND signal <> 'V' GROUP BY d ORDER BY d",
    lambda d, a: f"{a['P']} ช่วง{th_h(a['H'])}–{th_h(a['H2'])}: " + " · ".join(f"{pd.Timestamp(x):%d/%m} {n(c)} คัน" for x, c in zip(d.d, d.cars)))
fam("chargers_prov",
    ["{p}มีสถานีชาร์จกี่แห่ง", "ที่ชาร์จ EV ใน{p}มีกี่ที่", "จำนวนปั๊มอีวีใน{p}", "{p}มีจุดชาร์จรถไฟฟ้าไหม"],
    lambda: {"P": random.choice(CHG_P[:25] + PROVS[:10])},
    "SELECT COUNT(*) AS chargers FROM chargers WHERE prov_th = '{P}'",
    lambda d, a: f"{a['P']}มีสถานีชาร์จ {n(d.chargers[0])} แห่ง (ข้อมูล OpenStreetMap มีแค่บางส่วน)")
fam("chargers_operator",
    ["ผู้ให้บริการสถานีชาร์จเจ้าไหนมีมากสุด", "แบรนด์ที่ชาร์จไหนเยอะที่สุด", "สถานีชาร์จแยกตามผู้ให้บริการ"],
    lambda: {},
    "SELECT operator, COUNT(*) AS chargers FROM chargers WHERE operator <> '' GROUP BY operator ORDER BY chargers DESC LIMIT 5",
    lambda d, a: "ผู้ให้บริการที่มีสถานีมากสุด: " + rows_txt(d, "แห่ง"))
fam("nearest_charger_car",
    ["{pl} ใกล้สถานีชาร์จไหนที่สุด", "ที่ชาร์จใกล้ {pl} อยู่ไหน", "{pl} ควรไปชาร์จที่ไหน"],
    lambda: {"PL": random.choice(PLATES)},
    """SELECT c.name, c.operator, c.dist_th, ROUND(dist_km(p.lat, p.lon, c.lat, c.lon), 1) AS km
 FROM (SELECT lat, lon FROM points WHERE plate_key = '{K}' AND signal <> 'V' ORDER BY ts DESC LIMIT 1) p, chargers c ORDER BY km LIMIT 3""",
    lambda d, a: f"สถานีชาร์จใกล้ {a['PL']} ที่สุด: {d.name[0]} ({d.dist_th[0]}) {d.km[0]} กม.")
fam("cars_near_chargers",
    ["มีรถจอดอยู่ที่สถานีชาร์จกี่คัน", "รถจอดใกล้ที่ชาร์จกี่คัน", "ตอนนี้รถอยู่ที่จุดชาร์จกี่คัน"],
    lambda: {},
    """SELECT COUNT(DISTINCT n.car_id) AS cars FROM now n JOIN chargers c ON dist_km(n.lat, n.lon, c.lat, c.lon) <= 0.3 WHERE n.status = 'จอด'""",
    lambda d, a: f"มีรถจอดห่างสถานีชาร์จไม่เกิน 300 ม. ประมาณ {n(d.cars[0])} คัน (ประมาณจากระยะ ไม่รู้ว่ากำลังชาร์จจริงไหม)")
fam("out_of_zone_day",
    ["{day}มีรถออกนอกเขตกี่คัน", "{day}รถวิ่งออกต่างจังหวัดกี่คัน", "นับรถที่ออกนอกกรุงเทพและปริมณฑล{day}"],
    lambda: dict(zip(("DAYW", "DAY"), random.choice(DAYS))),
    "SELECT COUNT(DISTINCT car_id) AS cars FROM points WHERE CAST(ts AS DATE) = '{DAY}' AND signal <> 'V' AND prov_th NOT IN (" + ZONE_SQL + ")",
    lambda d, a: f"{a['DAYW']}มีรถอยู่นอกกรุงเทพฯ และปริมณฑล {n(d.cars[0])} คัน")
fam("out_of_zone_where",
    ["รถที่ออกนอกเขตไปจังหวัดไหนบ้าง", "รถนอกเขตอยู่จังหวัดไหนมากสุด", "จังหวัดนอกเขตที่มีรถเราไป"],
    lambda: {},
    "SELECT prov_th, COUNT(DISTINCT car_id) AS cars FROM points WHERE signal <> 'V' AND prov_th NOT IN (" + ZONE_SQL + ") GROUP BY prov_th ORDER BY cars DESC LIMIT 5",
    lambda d, a: "จังหวัดนอกเขตที่มีรถไปมากสุด: " + rows_txt(d))
fam("no_signal_now",
    ["ตอนนี้รถไม่มีสัญญาณกี่คัน", "รถที่สัญญาณหายอยู่แถวไหน", "มีรถขาดการติดต่อไหม"],
    lambda: {},
    "SELECT prov_th, COUNT(DISTINCT car_id) AS cars FROM now WHERE status = 'ไม่มีสัญญาณ' GROUP BY prov_th ORDER BY cars DESC LIMIT 5",
    lambda d, a: f"รถไม่มีสัญญาณ {n(d.cars.sum())} คัน มากสุดที่ " + rows_txt(d, k=3))
fam("avg_speed_prov",
    ["รถใน{p}วิ่งเร็วเฉลี่ยเท่าไหร่", "ความเร็วเฉลี่ยตอนวิ่งใน{p}", "{p}รถวิ่งกี่กิโลต่อชั่วโมงโดยเฉลี่ย"],
    lambda: {"P": random.choice(PROVS[:15])},
    "SELECT ROUND(AVG(speed), 1) AS avg_kmh FROM points WHERE prov_th = '{P}' AND speed >= 5 AND signal <> 'V'",
    lambda d, a: f"ตอนวิ่ง รถใน{a['P']}เร็วเฉลี่ย {d.avg_kmh[0]} กม./ชม.")
fam("status_ratio",
    ["เทียบสัดส่วนรถที่วิ่งกับรถที่จอด", "รถจอดกี่เปอร์เซ็นต์", "สัดส่วนรถมีผู้โดยสารต่อรถว่าง", "อัตราส่วนรถวิ่งต่อรถจอด"],
    lambda: {},
    """SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status IN ('วิ่งว่าง', 'มีผู้โดยสาร')) / COUNT(*)) AS moving_pct,
 ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'จอด') / COUNT(*)) AS parked_pct,
 ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'มีผู้โดยสาร') / COUNT(*)) AS hired_pct FROM now""",
    lambda d, a: f"ตอนนี้รถวิ่ง {int(d.moving_pct[0])}% จอด {int(d.parked_pct[0])}% (มีผู้โดยสาร {int(d.hired_pct[0])}%)")
fam("prov_no_charger",
    ["จังหวัดไหนมีรถแต่ไม่มีสถานีชาร์จ", "จังหวัดที่ไม่มีที่ชาร์จเลยแต่มีรถวิ่ง", "ที่ไหนขาดสถานีชาร์จ"],
    lambda: {},
    """SELECT n.prov_th, COUNT(DISTINCT n.car_id) AS cars FROM now n WHERE n.prov_th NOT IN (SELECT DISTINCT prov_th FROM chargers WHERE prov_th IS NOT NULL)
 GROUP BY n.prov_th ORDER BY cars DESC LIMIT 5""",
    lambda d, a: "จังหวัดที่มีรถแต่ไม่พบสถานีชาร์จ (OSM): " + rows_txt(d))
fam("site_recommend",
    ["ถ้าอยากเปิดปั๊ม EV ใน{p} ควรเปิดเขตไหน", "ควรตั้งสถานีชาร์จที่ไหนดีใน{p}", "ทำเลไหนใน{p}เหมาะเปิดจุดชาร์จ"],
    lambda: {"P": random.choice(["กรุงเทพมหานคร"] * 3 + PROVS[:6])},
    """SELECT a.dist_th, a.cars_per_hour, COALESCE(c.chargers, 0) AS chargers, ROUND(a.cars_per_hour / (COALESCE(c.chargers, 0) + 1), 1) AS score
 FROM (SELECT dist_th, ROUND(COUNT(DISTINCT car_id || CAST(date_trunc('hour', ts) AS VARCHAR)) / COUNT(DISTINCT date_trunc('hour', ts)), 1) AS cars_per_hour
       FROM points WHERE prov_th = '{P}' AND signal <> 'V' GROUP BY dist_th) a
 LEFT JOIN (SELECT dist_th, COUNT(*) AS chargers FROM chargers WHERE prov_th = '{P}' GROUP BY dist_th) c USING (dist_th)
 ORDER BY score DESC LIMIT 3""",
    lambda d, a: f"แนะนำ{d.dist_th[0]} (รถเฉลี่ย {d.cars_per_hour[0]} คัน/ชม. มีสถานี {int(d.chargers[0])} แห่ง) รองลงมา{d.dist_th[1]} — ประเมินเบื้องต้นจากจำนวนรถกับสถานี OSM")
fam("longest_km_day",
    ["รถคันไหนวิ่งไกลสุด{day}", "{day}คันไหนวิ่งเยอะที่สุด", "5 อันดับรถที่วิ่งไกลสุด{day}"],
    lambda: dict(zip(("DAYW", "DAY"), random.choice(DAYS))),
    """SELECT plate, ROUND(SUM(dist_km(lat0, lon0, lat, lon)), 1) AS km FROM (SELECT plate, lat, lon, lag(lat) OVER w AS lat0, lag(lon) OVER w AS lon0,
 ts - lag(ts) OVER w AS gap FROM points WHERE CAST(ts AS DATE) = '{DAY}' AND signal <> 'V' WINDOW w AS (PARTITION BY car_id ORDER BY ts))
 WHERE gap <= INTERVAL 15 MINUTE GROUP BY plate ORDER BY km DESC LIMIT 5""",
    lambda d, a: f"{a['DAYW']}รถที่วิ่งไกลสุด: " + rows_txt(d, "กม."))

# ── เพิ่มจากคลังคำถามธุรกิจ (EV7 Taxi - Business Questions · สถานะ 🟡) ──
fam("offline_long",
    ["รถคันไหนไม่ส่งสัญญาณเกิน {hr} ชั่วโมง", "มีรถหายจากระบบนานกว่า {hr} ชม. กี่คัน", "รถที่ขาดการติดต่อเกิน {hr} ชั่วโมง"],
    lambda: {"HR": random.choice([1, 2, 3, 6, 12])},
    f"""SELECT COUNT(*) AS cars, MIN(last_ts) AS oldest FROM (SELECT car_id, MAX(ts) AS last_ts FROM points WHERE signal <> 'V' GROUP BY car_id)
 WHERE last_ts < TIMESTAMP '{LATEST:%Y-%m-%d %H:%M:%S}' - INTERVAL {{HR}} HOUR""",
    lambda d, a: f"มีรถไม่ส่งสัญญาณเกิน {a['HR']} ชั่วโมง {n(d.cars[0])} คัน")
fam("speeding",
    ["รถคันไหนวิ่งเร็วเกิน {spd} กม./ชม.", "มีรถขับเร็วเกิน {spd} กี่คัน", "{day}รถคันไหนขับเร็วสุด"],
    lambda: dict(zip(("DAYW", "DAY"), random.choice(DAYS)), SPD=random.choice([100, 110, 120])),
    "SELECT plate, MAX(speed) AS max_kmh FROM points WHERE CAST(ts AS DATE) = '{DAY}' AND signal <> 'V' AND speed > {SPD} GROUP BY plate ORDER BY max_kmh DESC LIMIT 5",
    lambda d, a: f"{a['DAYW']}มีรถวิ่งเร็วเกิน {a['SPD']} กม./ชม. — เร็วสุด: " + rows_txt(d, "กม./ชม."))
fam("car_out_of_zone",
    ["{pl} ออกนอกเขตไหม", "{pl} ไปนอกกรุงเทพและปริมณฑลหรือเปล่า", "{pl} เคยออกต่างจังหวัดนอกโซนไหม"],
    lambda: {"PL": random.choice(PLATES)},
    "SELECT COUNT(*) AS points_outside, COUNT(DISTINCT prov_th) AS provinces, string_agg(DISTINCT prov_th, ', ') AS where_ FROM points WHERE plate_key = '{K}' AND signal <> 'V' AND prov_th NOT IN (" + ZONE_SQL + ")",
    lambda d, a: (f"{a['PL']} ออกนอกเขต ไปที่ {d.where_[0]}" if d.points_outside[0] else f"{a['PL']} ไม่เคยออกนอกกรุงเทพฯ และปริมณฑลในช่วงข้อมูล"))
fam("fleet_km_day",
    ["{day}รถทั้งหมดวิ่งรวมกี่กิโล", "ระยะทางรวมทั้งฝูง{day}", "{day}เฉลี่ยรถวิ่งคันละกี่กิโล"],
    lambda: dict(zip(("DAYW", "DAY"), random.choice(DAYS))),
    """SELECT ROUND(SUM(km)) AS total_km, ROUND(AVG(km), 1) AS avg_km_per_car, COUNT(*) AS cars FROM (
 SELECT car_id, SUM(dist_km(lat0, lon0, lat, lon)) AS km FROM (SELECT car_id, lat, lon, lag(lat) OVER w AS lat0, lag(lon) OVER w AS lon0,
 ts - lag(ts) OVER w AS gap FROM points WHERE CAST(ts AS DATE) = '{DAY}' AND signal <> 'V' WINDOW w AS (PARTITION BY car_id ORDER BY ts))
 WHERE gap <= INTERVAL 15 MINUTE GROUP BY car_id)""",
    lambda d, a: f"{a['DAYW']}รถ {n(d.cars[0])} คันวิ่งรวม {n(d.total_km[0])} กม. เฉลี่ยคันละ {d.avg_km_per_car[0]} กม.")
fam("utilization_prov",
    ["อัตราการใช้งานรถใน{p}เท่าไหร่", "รถใน{p}มีผู้โดยสารกี่เปอร์เซ็นต์ของเวลา", "{p}รถทำงานคุ้มไหม มีผู้โดยสารบ่อยแค่ไหน"],
    lambda: {"P": random.choice(PROVS[:15])},
    "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'มีผู้โดยสาร') / COUNT(*), 1) AS hired_pct, COUNT(DISTINCT car_id) AS cars FROM points WHERE prov_th = '{P}' AND signal <> 'V'",
    lambda d, a: f"รถใน{a['P']}มีผู้โดยสาร {d.hired_pct[0]}% ของจุดข้อมูลทั้งหมด (รถ {n(d.cars[0])} คัน)")
fam("gps_gap_moving",
    ["รถคันไหนสัญญาณหายระหว่างวิ่ง", "สงสัยถอด GPS คันไหนบ้าง", "รถที่สัญญาณขาดตอนกำลังวิ่งเร็ว"],
    lambda: {},
    """SELECT plate, COUNT(*) AS gaps, MAX(gap_min) AS max_gap_min FROM (SELECT plate, speed,
 date_diff('minute', ts, lead(ts) OVER (PARTITION BY car_id ORDER BY ts)) AS gap_min FROM points WHERE signal <> 'V')
 WHERE speed >= 40 AND gap_min >= 30 GROUP BY plate ORDER BY gaps DESC, max_gap_min DESC LIMIT 5""",
    lambda d, a: "รถที่สัญญาณหายเกิน 30 นาทีขณะวิ่ง ≥ 40 กม./ชม. (อาจอับสัญญาณหรือถอด GPS — ต้องตรวจต่อ): " + rows_txt(d, "ครั้ง"))

# คำถามที่ไม่ต้องเรียก SQL (ปฏิเสธ / ข้อมูลไม่มี / นอกเรื่อง)
NO_SQL = [
    (["ช่วยดับเครื่อง {pl} หน่อย", "ตัดสัญญาณรถ {pl}", "ล็อครถ {pl} เลย", "สั่งหยุดรถ {pl}"],
     "ระบบนี้ตอบคำถามจากข้อมูลได้อย่างเดียว สั่งการรถ (ดับเครื่อง ตัดสัญญาณ ล็อก) ไม่ได้ครับ"),
    (["คนขับคันไหนได้เงินเยอะสุด", "รายได้ต่อคันเท่าไหร่", "วันนี้รถทำเงินได้เท่าไหร่"],
     "ข้อมูลที่มีเป็นแค่ตำแหน่ง GPS กับสถานะมิเตอร์ ไม่มีข้อมูลรายได้ครับ · ถ้าต้องการ ดูจำนวนครั้งที่รับผู้โดยสารแทนได้"),
    (["รถคันไหนแบตใกล้หมด", "แบตเหลือกี่เปอร์เซ็นต์", "คันไหนต้องชาร์จด่วน"],
     "ข้อมูลไม่มีระดับแบตเตอรี่ครับ (ต้องขอจากระบบ SMART)"),
    (["ถนนสุขุมวิทตอนนี้มีรถกี่คัน", "รถบนถนนพระราม 9 มีกี่คัน", "ถนนไหนรถติด"],
     "ข้อมูลไม่มีชื่อถนนครับ ถามเป็นเขตหรืออำเภอแทนได้ เช่น 'เขตวัฒนามีรถกี่คัน'"),
    (["พรุ่งนี้ฝนตกไหม", "ราคาหุ้นวันนี้", "ช่วยเขียนอีเมลให้หน่อย", "กินอะไรดี"],
     "ช่วยได้เฉพาะเรื่องข้อมูลรถแท็กซี่ EV7 ครับ"),
    (["สวัสดี", "หวัดดีครับ", "ทำอะไรได้บ้าง"],
     "สวัสดีครับ ถามเรื่องรถแท็กซี่ EV7 ได้เลย เช่น จำนวนรถในพื้นที่ ตำแหน่งรถ ระยะทาง ช่วงเวลาที่ผู้โดยสารเยอะ สถานีชาร์จ"),
]


# ── สร้าง + ตรวจกับข้อมูลจริง ───────────────────────────────────────────────
def fill_q(q, a):
    return q.format(p=ptypo(a["P"]) if "P" in a else "", d=typo(a["D"], 0.2) if "D" in a else "",
                    pl=plate_text(a["PL"]) if "PL" in a else "", day=a.get("DAYW", ""),
                    h=th_h(a["H"]) if "H" in a else "", h2=th_h(a["H2"]) if "H2" in a else "",
                    hr=a.get("HR", ""), spd=a.get("SPD", ""))


def call(sql):
    return "<tool_call>\n" + json.dumps({"name": "run_sql", "arguments": {"sql": sql}}, ensure_ascii=False) + "\n</tool_call>"


examples, dropped = [], 0
PER_Q = 12                                           # ตัวอย่างต่อสำนวน
for f in F:
    for qi, q in enumerate(f["qs"]):
        for _ in range(PER_Q):
            a = f["gen"]()
            if "PL" in a:
                a["K"] = pkey(a["PL"])
            if "H2" in a:
                a["H2m"] = a["H2"] - 1
            sql = f["sql"].format(**a)
            try:
                d = db.execute(sql).df()
                if d.empty or d.iloc[0].isna().all():
                    dropped += 1
                    continue
                ans = f["ans"](d, a)
            except Exception:
                dropped += 1
                continue
            uq = re.sub(r"\s+", " ", random.choice(PRE) + fill_q(q, a) + random.choice(POST)).strip()
            msgs = [{"role": "user", "content": uq},
                    {"role": "assistant", "content": call(re.sub(r"\s+", " ", sql))},
                    {"role": "tool", "content": _fmt(d)},
                    {"role": "assistant", "content": ans}]
            examples.append({"family": f["name"], "style": f"{f['name']}#{qi}", "messages": msgs})
for qi, (qs, ans) in enumerate(NO_SQL):
    for k, q in enumerate(qs):
        for _ in range(6):
            uq = re.sub(r"\s+", " ", random.choice(PRE) + q.format(pl=plate_text(random.choice(PLATES))) + random.choice(POST)).strip()
            examples.append({"family": f"nosql{qi}", "style": f"nosql{qi}#{k}",
                             "messages": [{"role": "user", "content": uq}, {"role": "assistant", "content": ans}]})

TRAIN_DF = pd.DataFrame(examples)
TRAIN_DF["q"] = TRAIN_DF.messages.map(lambda m: m[0]["content"])
TRAIN_DF = TRAIN_DF.drop_duplicates("q").reset_index(drop=True)

# แบ่ง test = 1 สำนวนต่อแบบคำถาม (ตัวสุดท้าย) → โมเดลไม่เคยเห็นสำนวนนี้ตอนเทรน
last_style = TRAIN_DF.groupby("family")["style"].agg(lambda s: sorted(s.unique())[-1])
TRAIN_DF["split"] = ["test" if s == last_style[f] else "train" for f, s in zip(TRAIN_DF.family, TRAIN_DF["style"])]

out_path = DRIVE / "taxi_sql_train.jsonl"
with open(out_path, "w", encoding="utf-8") as fh:
    for r in TRAIN_DF.itertuples():
        fh.write(json.dumps({"split": r.split, "family": r.family, "messages": r.messages}, ensure_ascii=False) + "\n")
print(f"ตัวอย่าง {len(TRAIN_DF):,} ข้อ ({len(F)} แบบที่ใช้ SQL + {len(NO_SQL)} แบบไม่ใช้ SQL) · ทิ้ง {dropped} ข้อที่ SQL ไม่ผ่าน")
print(TRAIN_DF.split.value_counts().to_dict(), "→", out_path)
for r in TRAIN_DF.sample(3, random_state=1).itertuples():
    print("\nQ:", r.messages[0]["content"])
    for m in r.messages[1:]:
        print(f"  [{m['role']}]", m["content"][:220].replace("\n", " "))
