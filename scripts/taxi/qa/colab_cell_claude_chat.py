# ── 11 · Chatbot แบบ Claude — เข้าใจทุกรูปประโยค · ตอบสั้นตรงประเด็น · จำบทสนทนา ──
# ต้องรันส่วน 1–7 (และ 7.1 ถ้ามี) ก่อน · ไม่ต้องใช้ GPU
# ⚠️ ผลค้นข้อมูล (รหัสรถสมมติ EV-xxxx · ชื่อพื้นที่ · พิกัด) จะถูกส่งไป Anthropic — ใช้กับชุดข้อมูลทดลองนี้ได้ · ข้อมูลจริงต้องให้ DPO อนุมัติก่อน
#
# ตั้ง API key ครั้งเดียว: แถบซ้ายของ Colab → 🔑 Secrets → Add new secret
#   Name = ANTHROPIC_API_KEY · Value = key จาก console.anthropic.com · เปิดสวิตช์ Notebook access
import os, sys, json, subprocess
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "anthropic"], check=True)
import anthropic

if "google.colab" in sys.modules and not os.environ.get("ANTHROPIC_API_KEY"):
    from google.colab import userdata
    os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic()

MODEL = "claude-opus-5-5"     # ฉลาดที่สุด · อยากเร็ว/ถูกลงลอง "claude-haiku-5-5"

# ── tools: ห่อ executor ส่วน 6 ให้ Claude เรียก · คืน JSON สั้น ๆ ─────────────
def _j(x):
    return json.dumps(x, ensure_ascii=False, default=str)

def _when(text):
    return find_time(text or "")[0]                  # "ล่าสุด" · "วันนี้" · "เมื่อวาน" · "14:30" · "9 โมง"

def _place(name):
    return find_place(name) if name else None        # เกณฑ์ 0.85 — หลวมกว่านี้ "ดาวอังคาร" จะกลายเป็น "นาวัง"

def _plate(car):
    p = find_plate(car or "")[0]
    return p or (car or "").upper().replace("-", "").replace(" ", "")

def run_tool(name, a):
    try:
        if name == "find_place":
            pl = _place(a["text"])
            return _j(pl or {"error": "ไม่พบสถานที่นี้"})
        if name == "cars_in_area":
            pl = _place(a["place"])
            if not pl:
                return _j({"error": f"ไม่รู้จักสถานที่ '{a['place']}'"})
            return _j(x_cars_in_area(pl, _when(a.get("time"))))
        if name == "car_status":
            return _j(x_car_status(_plate(a["car"]), _when(a.get("time"))))
        if name == "car_track":
            return _j(x_car_track(_plate(a["car"]), _when(a.get("time") or "วันนี้")))
        if name == "rank_areas":
            pl = _place(a.get("place"))
            return _j(x_rank_area(pl, _when(a.get("time")), top=a.get("top", 5)))
        if name == "out_of_zone":
            r = x_out_of_zone(_when(a.get("time") or "วันนี้"))
            r["cars"] = r["cars"][:15]
            return _j(r)
        if name == "fleet_stats":
            return _j(x_fleet_stats(_when(a.get("time"))))
        if name == "nearest_chargers":
            return _j(x_nearest_charger(_plate(a["car"]) if a.get("car") else None, _place(a.get("place")),
                                        _when(None), k=a.get("k", 3)))
        return _j({"error": f"ไม่มี tool ชื่อ {name}"})
    except Exception as e:                            # ส่งข้อผิดพลาดกลับให้ Claude อธิบาย/ถามใหม่ ไม่ให้ระบบล้ม
        return _j({"error": f"{type(e).__name__}: {e}"})

TIME = {"type": "string", "description": "ช่วงเวลาเป็นคำไทย เช่น 'ล่าสุด' (ค่าเริ่มต้น) · 'วันนี้' · 'เมื่อวาน' · '14:30' · '9 โมง'"}
CAR = {"type": "string", "description": "รหัสรถ เช่น EV-0042"}
PLACE = {"type": "string", "description": "ชื่อจังหวัด/อำเภอ/เขต ตามที่ผู้ใช้พิมพ์ (สะกดผิดได้)"}
def _tool(name, desc, props, required):
    return {"name": name, "description": desc,
            "input_schema": {"type": "object", "properties": props, "required": required}}

TOOLS = [
    _tool("cars_in_area", "จำนวนและรายชื่อรถที่ออนไลน์ในจังหวัด/อำเภอ/เขต ณ เวลาหนึ่ง พร้อมแยกสถานะ (จอด · ว่าง·วิ่ง · มีผู้โดยสาร)",
          {"place": PLACE, "time": TIME}, ["place"]),
    _tool("car_status", "ตำแหน่ง สถานะ ความเร็ว ทิศ ของรถ 1 คัน ณ เวลาหนึ่ง", {"car": CAR, "time": TIME}, ["car"]),
    _tool("car_track", "สรุปการเดินทางของรถ 1 คันในช่วงเวลา: ระยะทาง จุดเริ่ม-จุดสุดท้าย จังหวัดที่ผ่าน ความเร็วสูงสุด",
          {"car": CAR, "time": TIME}, ["car"]),
    _tool("rank_areas", "จัดอันดับพื้นที่ที่มีรถมากที่สุด: ใส่จังหวัด = อันดับเขต/อำเภอในจังหวัดนั้น · ไม่ใส่ = อันดับจังหวัดทั่วประเทศ",
          {"place": PLACE, "time": TIME, "top": {"type": "integer", "description": "จำนวนอันดับ (ค่าเริ่มต้น 5)"}}, []),
    _tool("out_of_zone", "รถที่ออกนอกเขตกรุงเทพฯ และปริมณฑลในช่วงเวลา พร้อมจังหวัดที่ไป", {"time": TIME}, []),
    _tool("fleet_stats", "ภาพรวมทั้งฝูงรถ: จำนวนรถออนไลน์ แยกสถานะ และ 5 จังหวัดที่รถเยอะสุด", {"time": TIME}, []),
    _tool("nearest_chargers", "สถานีชาร์จ EV ใกล้รถคันหนึ่ง หรือใกล้กลางจังหวัด (ข้อมูล OpenStreetMap มีแค่บางส่วน)",
          {"car": CAR, "place": PLACE, "k": {"type": "integer", "description": "จำนวนสถานี (ค่าเริ่มต้น 3)"}}, []),
]

SYSTEM_CLAUDE = f"""คุณคือผู้ช่วยของทีม EV7 ที่ดูแลรถแท็กซี่ไฟฟ้า คุยกับพนักงานเป็นภาษาไทย

วิธีตอบ
- ตอบเหมือนเพื่อนร่วมงานคุยกัน สั้น ตรงประเด็น ส่วนใหญ่ 1–2 ประโยค ตอบเฉพาะสิ่งที่ถาม ไม่ทวนคำถาม ไม่เกริ่น
- ถ้าเป็นรายการ แสดงไม่เกิน 5 รายการ เว้นแต่ผู้ใช้ขอเพิ่ม
- ตัวเลข ชื่อพื้นที่ และรหัสรถ ต้องมาจากผลของ tool เท่านั้น ห้ามเดา · ถ้า tool ตอบ error ให้บอกสั้น ๆ และแนะนำว่าถามยังไงแทน
- ถ้าคำถามกำกวม (เช่น ไม่ระบุว่ารถคันไหน และไม่มีในบทสนทนาก่อนหน้า) ให้ถามกลับสั้น ๆ
- ใช้บริบทจากบทสนทนาก่อนหน้า เช่น "คันนี้" "ที่นั่น"
- บอกเวลาของข้อมูลเมื่อเกี่ยวข้อง

ข้อมูลที่มี
- ตำแหน่ง GPS รถแท็กซี่ EV ช่วง 30 ก.ย. – 1 ต.ค. 2026 · "ตอนนี้" = เวลาล่าสุดของข้อมูล {LATEST:%d/%m/%Y %H:%M} (ไม่ใช่เวลาจริง)
- รหัสรถเป็นรหัสสมมติ EV-xxxx · รถออนไลน์ = มีสัญญาณภายใน 15 นาที
- "นอกเขต" = นอกกรุงเทพฯ และปริมณฑล (นนทบุรี ปทุมธานี สมุทรปราการ สมุทรสาคร นครปฐม)

ข้อห้าม
- ระบบนี้ตอบคำถามเท่านั้น สั่งการรถไม่ได้ (ตัดสัญญาณ ล็อก ดับเครื่อง) ถ้าถูกขอให้บอกว่าทำไม่ได้
- คำถามที่ไม่เกี่ยวกับรถ EV7 ให้ตอบสั้น ๆ ว่าช่วยได้เฉพาะเรื่องรถ"""

history = []          # จำบทสนทนา · history.clear() = เริ่มใหม่ · ชื่อแยกจาก cell 10 (Qwen) รันคู่กันได้

def chat_claude(q, show_tools=False):
    history.append({"role": "user", "content": q})
    for _ in range(8):                                     # กันวนไม่จบ
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=2000,
            system=SYSTEM_CLAUDE, tools=TOOLS, messages=history,
            output_config={"effort": "low"},               # ตอบเร็ว · คำถามแบบนี้ไม่ต้องคิดลึก
            cache_control={"type": "ephemeral"},           # cache คำสั่ง + tools ลดค่าใช้จ่ายรอบถัดไป
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": "claude-opus-4-8"}],      # ถ้าโมเดลหลักปฏิเสธ ให้รุ่นสำรองตอบแทน
        )
        history.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "refusal":
            return "ขออภัย ตอบคำถามนี้ไม่ได้"
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text").strip()
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = run_tool(b.name, b.input)
                if show_tools:
                    print(f"  🔧 {b.name}({json.dumps(b.input, ensure_ascii=False)}) → {out[:160]}")
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
        history.append({"role": "user", "content": results})
    return "ขออภัย ใช้เวลานานเกินไป ลองถามใหม่อีกครั้ง"

def แชต_claude():
    # คุยต่อเนื่อง · Enter ว่าง = จบ · พิมพ์ "ล้าง" = เริ่มบทสนทนาใหม่
    while True:
        q = input("คุณ: ").strip()
        if not q:
            break
        if q == "ล้าง":
            history.clear(); print("บอท: เริ่มใหม่แล้วครับ"); continue
        print("บอท:", chat_claude(q))

for q in ["หวัดดี", "ตอนนี้ภูเก็ตมีรถกี่คัน", "เขตไหนในกรุงเทพมีรถเยอะสุด", "EV-2038 อยู่ไหน", "แล้ววันนี้มันไปไหนมาบ้าง", "ช่วยดับเครื่องคันนี้หน่อย"]:
    print("คุณ:", q); print("บอท:", chat_claude(q, show_tools=True)); print()
