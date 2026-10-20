# ── 13 · Agent ฟรี — Qwen เขียน SQL เอง (DuckDB) · ถามอะไรก็ได้ที่ข้อมูลตอบได้ · คิดหลายขั้น ──
# ต้องรันส่วน 0–7 ก่อน (7.1 / 7.2 / 10 ไม่จำเป็น) · ใช้ GPU T4 x2 · ไม่มีค่าใช้จ่าย
#
# ต่างจาก cell 10 ยังไง
#   cell 10: คำถาม → เลือก 1 ช่องจากที่เขียนไว้ → Qwen แค่เรียบเรียง   (rule-based)
#   cell 13: คำถาม → Qwen อ่านคำอธิบายข้อมูล → เขียน SQL → ดูผล → เขียนใหม่ได้ → สรุป  (agent)
# ตัวเลขทุกตัวยังมาจากผล SQL บนข้อมูลจริง · show_steps=True แสดง SQL ที่ใช้ให้ตรวจ
import json, re, sys, time, threading, subprocess
import numpy as np
import pandas as pd
import torch

try:
    import duckdb
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "duckdb"], check=True)
    import duckdb

AGENT_LLM = "Qwen/Qwen2.5-14B-Instruct"   # ฟรี · 4-bit ~9 GB · เร็วกว่าแต่พลาดบ่อยกว่า: "Qwen/Qwen2.5-7B-Instruct"
MAX_STEPS = 6                             # เรียก tool ได้สูงสุดกี่รอบต่อคำถาม
MAX_ROWS = 30                             # ผล SQL ที่ส่งให้ LLM อ่าน (กันข้อความยาวเกิน)
SQL_TIMEOUT = 20                          # วินาที

# ── 1) ตารางให้ LLM query (DuckDB อ่านจาก DataFrame ในหน่วยความจำ · ไม่แก้ข้อมูลต้นทาง) ──
if "dist_code" not in chg.columns:                                   # ระบุเขตของสถานีชาร์จ (ถ้ายังไม่ได้รัน 7.2)
    from shapely.geometry import shape, Point
    from shapely import STRtree
    _polys = [shape(f["geometry"]) for f in json.load(open(OUT / "dist_pip.geojson", encoding="utf-8"))["features"]]
    _tree = STRtree(_polys)
    _idx = [(_tree.query(Point(b, a), predicate="within").tolist() or [-1])[0] for a, b in zip(chg.lat, chg.lon)]
    chg["dist_code"] = [dist.pc.iloc[i][2:] if i >= 0 else None for i in _idx]
    chg["prov_code"] = [dist.ppc.iloc[i][2:] if i >= 0 else None for i in _idx]
    chg["dist_th"] = [dist.th.iloc[i] if i >= 0 else None for i in _idx]

T_POINTS = pos[["car_id", "plate", "plate_key", "gps_time", "lat", "lon", "speed", "direction", "meter", "signal", "status",
                "dist_code", "dist_th", "prov_code", "prov_th"]].rename(columns={"gps_time": "ts"})
T_NOW = latest_at(LATEST)[["car_id", "plate", "plate_key", "gps_time", "lat", "lon", "speed", "status", "dist_code", "dist_th",
                           "prov_code", "prov_th"]].rename(columns={"gps_time": "ts"})
_s = pos.sort_values(["car_id", "gps_time"])
_f = _s.meter.eq("F")
T_PICKUPS = _s[_f & ~_f.groupby(_s.car_id).shift(fill_value=False)][["car_id", "plate", "gps_time", "lat", "lon", "dist_th", "prov_th"]] \
              .rename(columns={"gps_time": "ts"})
T_CHARGERS = chg.assign(prov_th=chg.prov_code.map(name_of))[["name", "op", "lat", "lon", "dist_code", "dist_th", "prov_code", "prov_th"]] \
               .rename(columns={"op": "operator"})
T_DISTRICTS = dist.assign(dist_code=dist.pc.str[2:], prov_code=dist.ppc.str[2:])[["dist_code", "th", "en", "prov_code", "pth"]] \
                .rename(columns={"th": "dist_th", "en": "dist_en", "pth": "prov_th"})

STATUS_SQL = {"ว่าง·วิ่ง": "วิ่งว่าง"}                     # "·" พิมพ์ยาก LLM มักเขียนผิด → ใช้ชื่อเรียบ ๆ ในตาราง SQL
for _t in (T_POINTS, T_NOW):
    _t["status"] = _t["status"].replace(STATUS_SQL)

db = duckdb.connect()
for name, df in {"points": T_POINTS, "now": T_NOW, "pickups": T_PICKUPS, "chargers": T_CHARGERS, "districts": T_DISTRICTS}.items():
    db.register(name, df)
db.execute("""CREATE MACRO dist_km(lat1, lon1, lat2, lon2) AS
              12742 * asin(sqrt(pow(sin(radians(lat2 - lat1) / 2), 2)
                     + cos(radians(lat1)) * cos(radians(lat2)) * pow(sin(radians(lon2 - lon1) / 2), 2)))""")

SCHEMA = f"""
ตาราง (DuckDB SQL)
- points  ทุกจุด GPS {len(T_POINTS):,} แถว · {pos.gps_time.min():%Y-%m-%d %H:%M} ถึง {LATEST:%Y-%m-%d %H:%M} · ~5 นาที/จุด/คัน
    car_id (รหัสประจำคัน), plate (ทะเบียน เช่น ทอ-1234), plate_key (ทะเบียนไม่มีขีด/เว้นวรรค เช่น ทอ1234), ts (timestamp), lat, lon, speed (กม./ชม.), direction (องศา 0=เหนือ 90=ตะวันออก),
    meter ('F'=มีผู้โดยสาร 'E'=ว่าง), signal ('V'=ไม่มีสัญญาณ), status = หนึ่งใน 'จอด' 'วิ่งว่าง' 'มีผู้โดยสาร' 'ไม่มีสัญญาณ' (สะกดตามนี้เท่านั้น),
    dist_code, dist_th (เขต/อำเภอ), prov_code, prov_th (จังหวัด)
- now     ตำแหน่งล่าสุดของรถที่ออนไลน์ ณ "ตอนนี้" = {LATEST:%Y-%m-%d %H:%M} ({len(T_NOW):,} คัน) · คอลัมน์เหมือน points (บางส่วน)
- pickups ทุกครั้งที่รถรับผู้โดยสาร (มิเตอร์เปลี่ยน E→F) · car_id, plate, ts, lat, lon, dist_th, prov_th
- chargers สถานีชาร์จ EV จาก OpenStreetMap {len(T_CHARGERS)} แห่ง (มีแค่บางส่วน ของจริงมากกว่านี้) · name, operator, lat, lon, dist_code, dist_th, prov_code, prov_th
- districts รายชื่อเขต/อำเภอทั้งประเทศ · dist_code, dist_th, dist_en, prov_code, prov_th
- ฟังก์ชัน dist_km(lat1, lon1, lat2, lon2) = ระยะทางเป็นกิโลเมตร

ความหมาย
- รถออนไลน์ = มีสัญญาณภายใน 15 นาที · "ตอนนี้" = {LATEST:%H:%M} ของ {LATEST:%Y-%m-%d} (ไม่ใช่เวลาจริง)
- รถว่าง = status IN ('จอด','วิ่งว่าง') (ไม่มีผู้โดยสาร) · รถวิ่ง = status IN ('วิ่งว่าง','มีผู้โดยสาร') · นอกเขต = prov_th ไม่อยู่ใน กรุงเทพมหานคร นนทบุรี ปทุมธานี สมุทรปราการ สมุทรสาคร นครปฐม
- นับจำนวนรถ ใช้ COUNT(DISTINCT car_id) เสมอ (1 คันมีหลายจุด) · ชั่วโมง: hour(ts) · วัน: CAST(ts AS DATE)
- ค้นรถตามทะเบียน: WHERE plate_key = 'ทอ1234' (ตัดขีด/เว้นวรรคจากที่ผู้ใช้พิมพ์ก่อน)
- ชื่อสถานที่ที่ผู้ใช้พิมพ์อาจสะกดผิด → เรียก find_place ก่อนเพื่อได้ชื่อ/รหัสที่ถูก แล้วกรองด้วย prov_code / dist_code
- ข้อมูลไม่มีชื่อถนน · ไม่มีข้อมูลคนขับ/รายได้/แบตเตอรี่
"""

TOOLS_A = [
    {"type": "function", "function": {
        "name": "run_sql", "description": "รัน DuckDB SQL (SELECT เท่านั้น) บนตาราง points / now / pickups / chargers / districts · คืนสูงสุด 30 แถว",
        "parameters": {"type": "object", "properties": {"sql": {"type": "string", "description": "คำสั่ง SELECT"}}, "required": ["sql"]}}},
    {"type": "function", "function": {
        "name": "find_place", "description": "แปลงชื่อจังหวัด/อำเภอ/เขตที่ผู้ใช้พิมพ์ (สะกดผิดได้) เป็นชื่อและรหัสที่ถูกต้อง",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
]

SYSTEM_A = f"""คุณคือผู้ช่วยวิเคราะห์ข้อมูลรถแท็กซี่ไฟฟ้า EV7 คุยกับพนักงานเป็นภาษาไทย
หาคำตอบด้วยการเรียก tool (เขียน SQL ได้หลายครั้ง ถ้าผลแปลกหรือว่างให้ตรวจ SQL แล้วลองใหม่) แล้วตอบเหมือนคนคุยกัน
- ตอบสั้น ตรงประเด็น 1–3 ประโยค ขึ้นต้นด้วยคำตอบ · พูดเวลาแบบไทยได้ (15:00 = บ่าย 3)
- ตัวเลข ชื่อ รหัสรถ ต้องมาจากผล tool เท่านั้น ห้ามเดา · ถ้าข้อมูลตอบไม่ได้ ให้บอกตรง ๆ ว่าขาดข้อมูลอะไร
- คำถามเชิงความเห็น (เช่น ควรเปิดสถานีที่ไหน) ให้หาข้อมูลประกอบก่อน แล้วบอกเหตุผลและบอกว่าเป็นการประเมินเบื้องต้น
- คำถามกำกวม ถามกลับสั้น ๆ · คำสั่งควบคุมรถ (ตัดสัญญาณ ล็อก ดับเครื่อง) ตอบประโยคเดียวว่าระบบตอบคำถามได้อย่างเดียว · เรื่องที่ไม่เกี่ยวกับรถ ตอบประโยคเดียวว่าช่วยได้เฉพาะเรื่องรถ ไม่ต้องแนะนำที่อื่น
- "วันนี้" ใช้ตาราง points กรองวัน · "ตอนนี้" ใช้ตาราง now · นับรถออกนอกเขตต่อวัน = คันที่มีจุดนอกเขตอย่างน้อย 1 จุดในวันนั้น
{SCHEMA}
ตัวอย่างการใช้ tool
ถาม: ตอนนี้เชียงใหม่มีรถกี่คัน แยกสถานะ
  1) find_place(text="เชียงใหม่") → filter: prov_code = '50'
  2) run_sql: SELECT status, COUNT(DISTINCT car_id) AS cars FROM now WHERE prov_code = '50' GROUP BY status ORDER BY cars DESC
ถาม: ชั่วโมงไหนรับผู้โดยสารมากสุด
  run_sql: SELECT hour(ts) AS h, COUNT(*) AS pickups FROM pickups GROUP BY h ORDER BY pickups DESC LIMIT 3
ถาม: ทอ-4141 วิ่งไปกี่กิโลวันที่ 1 ต.ค.
  run_sql: SELECT SUM(dist_km(lat0, lon0, lat, lon)) AS km FROM (SELECT lat, lon, lag(lat) OVER w AS lat0, lag(lon) OVER w AS lon0,
           ts - lag(ts) OVER w AS gap FROM points WHERE plate_key = 'ทอ4141' AND CAST(ts AS DATE) = '2026-10-01' AND signal <> 'V'
           WINDOW w AS (ORDER BY ts)) WHERE gap <= INTERVAL 15 MINUTE
ถาม: เทียบจำนวนรถมีผู้โดยสาร 2 วัน ช่วง 18–21 น. ในกรุงเทพ
  run_sql: SELECT CAST(ts AS DATE) AS d, COUNT(DISTINCT car_id) AS cars FROM points WHERE prov_code = '10' AND status = 'มีผู้โดยสาร'
           AND hour(ts) BETWEEN 18 AND 20 GROUP BY d ORDER BY d
แล้วตอบจากผลที่ได้ เช่น "ตอนนี้เชียงใหม่มีรถออนไลน์ 25 คัน จอด 15 วิ่งว่าง 6 มีผู้โดยสาร 4 ครับ" (ตัวเลขในตัวอย่างนี้สมมติ ห้ามใช้)"""


# ── 2) tools ─────────────────────────────────────────────────────────────
def _fmt(df):
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].round(3)
        elif pd.api.types.is_datetime64_any_dtype(df[c]):
            only_date = (df[c].dt.normalize() == df[c]).all()
            df[c] = df[c].dt.strftime("%Y-%m-%d" if only_date else "%Y-%m-%d %H:%M")
    more = f"\n(แสดง {MAX_ROWS} จาก {len(df):,} แถว)" if len(df) > MAX_ROWS else ""
    return df.head(MAX_ROWS).to_csv(index=False) + more if len(df) else "(ไม่มีแถว)"


def tool_run_sql(sql):
    s = sql.strip().rstrip(";")
    if not re.match(r"(?is)^\s*(with|select)\b", s) or re.search(r"(?i)\b(insert|update|delete|drop|create|alter|attach|copy|pragma|install|load|export)\b", s):
        return "ERROR: ใช้ได้เฉพาะ SELECT"
    timer = threading.Timer(SQL_TIMEOUT, db.interrupt)
    timer.start()
    try:
        out = _fmt(db.execute(s).df())
        if out == "(ไม่มีแถว)":
            out += (" — ตรวจค่าที่กรอง: status ต้องเป็น 'จอด' 'วิ่งว่าง' 'มีผู้โดยสาร' 'ไม่มีสัญญาณ' · "
                    "สถานที่ให้ใช้ prov_code/dist_code จาก find_place · ทะเบียนใช้ plate_key ไม่มีขีด")
        return out
    except Exception as e:
        return f"ERROR: {str(e).splitlines()[0][:300]}"
    finally:
        timer.cancel()


def tool_find_place(text):
    p = find_place(text or "")
    if not p:
        return "ไม่พบสถานที่นี้"
    col = "prov_code" if p["level"] == "prov" else "dist_code"
    return json.dumps({"label": p["label"], "level": "จังหวัด" if p["level"] == "prov" else "เขต/อำเภอ",
                       "filter": f"{col} = '{p['code']}'"}, ensure_ascii=False)


def run_tool_a(name, args):
    if name == "run_sql":
        return tool_run_sql(args.get("sql", ""))
    if name == "find_place":
        return tool_find_place(args.get("text", ""))
    return f"ERROR: ไม่มี tool ชื่อ {name}"


# ── 3) โหลดโมเดล ─────────────────────────────────────────────────────────
LOAD_AGENT_MODEL = True                    # False = สร้างแค่ตาราง SQL + ฟังก์ชัน ไม่โหลดโมเดล (ใช้ก่อน cell 15–16 ที่เทรน/โหลดโมเดลเอง)
FREE_OTHERS = True                         # ปล่อยโมเดลของ cell 8 / 10 ออกจาก GPU ก่อน (กัน CUDA out of memory)
if FREE_OTHERS and LOAD_AGENT_MODEL:
    import gc
    for v in ("cmodel", "model", "base", "trainer"):
        if v in globals():
            del globals()[v]
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

if LOAD_AGENT_MODEL and "amodel" not in globals():
    from transformers import AutoTokenizer, AutoModelForCausalLM
    atok = AutoTokenizer.from_pretrained(AGENT_LLM)
    kw = {}
    if torch.cuda.is_available():                        # เว้นที่ ~3 GB ต่อการ์ดไว้ใช้ตอนสร้างคำตอบ
        kw["max_memory"] = {i: f"{int(torch.cuda.get_device_properties(i).total_memory / 2**30) - 3}GiB"
                            for i in range(torch.cuda.device_count())}
    if torch.cuda.is_available() and re.search(r"(7|14|32)B", AGENT_LLM):
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "bitsandbytes", "accelerate"], check=True)
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
    amodel = AutoModelForCausalLM.from_pretrained(
        AGENT_LLM, dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None, **kw)
    amodel.eval()


def _generate(msgs, max_new=400):
    prompt = atok.apply_chat_template(msgs, tools=TOOLS_A, add_generation_prompt=True, tokenize=False)
    x = atok(prompt, return_tensors="pt").to(amodel.device)
    with torch.no_grad():
        out = amodel.generate(**x, max_new_tokens=max_new, do_sample=False, pad_token_id=atok.eos_token_id)
    return atok.decode(out[0][x["input_ids"].shape[1]:], skip_special_tokens=True).strip()


TOOL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
agent_history = []                                         # จำบทสนทนา · agent_history.clear() = เริ่มใหม่


def agent(q, show_steps=False):
    t0 = time.time()
    agent_history.append({"role": "user", "content": q})
    msgs = [{"role": "system", "content": SYSTEM_A}] + agent_history[-12:]
    seen = []                                              # ผล tool ทั้งหมด ไว้ตรวจตัวเลข
    for step in range(MAX_STEPS):
        text = _generate(msgs)
        calls = TOOL_RE.findall(text)
        if not calls:
            break
        msgs.append({"role": "assistant", "content": text})
        for c in calls:
            try:
                j = json.loads(c)
                name, args = j.get("name"), j.get("arguments") or {}
                if isinstance(args, str):
                    args = json.loads(args)
            except Exception:
                name, args, res = "?", {}, "ERROR: tool call ไม่ใช่ JSON ที่ถูกต้อง"
            else:
                res = run_tool_a(name, args)
            seen.append(res)
            if show_steps:
                arg = args.get("sql") or args.get("text") or ""
                print(f"  🔧 {name}: {arg.strip()[:300]}\n     → {res.strip()[:300].replace(chr(10), ' | ')}")
            msgs.append({"role": "tool", "content": res})
    else:
        text = _generate(msgs + [{"role": "user", "content": "สรุปคำตอบจากข้อมูลที่มีตอนนี้ ไม่ต้องเรียก tool เพิ่ม"}])
    answer_ = re.sub(r"</?tool_(call|response)>", "", TOOL_RE.sub("", text)).strip() or "ขออภัย หาคำตอบไม่ได้ ลองถามใหม่อีกแบบ"
    # ตรวจตัวเลข: ตัวเลขในคำตอบที่ไม่พบในผล tool เลย → เตือน (LLM อาจคำนวณเอง เช่น % · หรือแต่งขึ้น)
    found = " ".join(seen) + " " + q
    nums = re.findall(r"(?<![A-Za-z\d.,\-])\d[\d,]*(?:\.\d+)?(?![A-Za-z])", answer_)
    odd = [n for n in nums if n.replace(",", "") not in found.replace(",", "")]
    if odd and seen:
        answer_ += f"\n   ⚠️ ตัวเลข {', '.join(odd[:5])} ไม่ได้มาจากผล query โดยตรง (คำนวณเองหรืออาจผิด) — ดู show_steps=True"
    agent_history.append({"role": "assistant", "content": answer_})
    if show_steps:
        print(f"  ⏱ {time.time() - t0:.0f} วิ")
    return answer_


def แชต_agent():
    # คุยต่อเนื่อง · Enter ว่าง = จบ · "ล้าง" = เริ่มใหม่ · "sql" = เปิด/ปิดการแสดง SQL
    show = False
    while True:
        q = input("คุณ: ").strip()
        if not q:
            break
        if q == "ล้าง":
            agent_history.clear(); print("บอท: เริ่มใหม่แล้วครับ"); continue
        if q.lower() == "sql":
            show = not show; print("บอท: แสดง SQL", "เปิด" if show else "ปิด"); continue
        print("บอท:", agent(q, show_steps=show))


for q in ([] if not LOAD_AGENT_MODEL else ["เวลาประมาณกี่โมงมีผู้โดยสารมากที่สุด", "มีข้อมูลของวันไหนบ้าง", "มีสถานีชาร์จกี่แห่งในกรุงเทพ",
          "เทียบชลบุรีเมื่อวานกับวันนี้ช่วง 6 โมงเย็นถึง 3 ทุ่ม รถเยอะขึ้นไหม", "ถ้าอยากเปิดปั๊ม ev ควรเปิดเขตไหน"]):
    agent_history.clear()
    print("คุณ:", q); print("บอท:", agent(q, show_steps=True)); print()
