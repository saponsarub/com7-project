# ── 10 · ตอบแบบ chatbot — ภาษาพูด + จำบทสนทนา ─────────────────────────────
# ต้องรันส่วน 0–7 ก่อน · ฟรี · ใช้ GPU T4 (ไม่มี GPU ได้แต่ช้ามาก) · ตัวเลขทุกตัวยังมาจาก executor ส่วน 6 — LLM แค่เรียบเรียงภาษา
import re, random, torch
from transformers import AutoTokenizer, AutoModelForCausalLM

CHAT_LLM = "Qwen/Qwen2.5-3B-Instruct"   # เก่งกว่า: "Qwen/Qwen2.5-7B-Instruct" (โหลดแบบ 4-bit อัตโนมัติ · ~5 GB · ช้าลง ~2 เท่า)
USE_LLM = True                          # False = ไม่ใช้ LLM (ตอบจากแม่แบบที่เป็นกันเองขึ้น)
# เปลี่ยนรุ่นแล้วต้องลบตัวเก่าก่อน:  del cmodel; torch.cuda.empty_cache()  แล้วรัน cell นี้ใหม่

if USE_LLM and "cmodel" not in globals():
    ctok = AutoTokenizer.from_pretrained(CHAT_LLM)
    kw = {}
    if "7B" in CHAT_LLM or "14B" in CHAT_LLM:                # รุ่นใหญ่ บีบเป็น 4-bit ให้พอ GPU T4
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "bitsandbytes", "accelerate"], check=True)
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
    cmodel = AutoModelForCausalLM.from_pretrained(
        CHAT_LLM, dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None, **kw)
    cmodel.eval()

SYSTEM = ("คุณคือผู้ช่วยของทีม EV7 ตอบคำถามเรื่องรถแท็กซี่ไฟฟ้าเป็นภาษาไทย เหมือนเพื่อนร่วมงานคุยกัน\n"
          "- ตอบเฉพาะสิ่งที่ถาม สั้น 1–2 ประโยค ขึ้นต้นด้วยคำตอบเลย ไม่ทวนคำถาม\n"
          "- ใช้เฉพาะข้อมูลจากระบบ ห้ามเพิ่มตัวเลข ชื่อ หรือทะเบียนที่ไม่มีในข้อมูล\n"
          "- ถ้าข้อมูลมีคำพูดแบบคนไทย (เช่น บ่าย 3) ให้ใช้คำนั้น · ถ้าข้อมูลบอกว่าเป็นการประมาณ/คาดเดา ให้บอกด้วย\n"
          "- ข้อมูลส่วนที่ผู้ใช้ไม่ได้ถาม ไม่ต้องพูดถึง")

# ตัวอย่างคำตอบที่อยากได้ (few-shot) — Qwen จะเลียนแบบความยาวและน้ำเสียง · ตัวเลขในนี้ถูกกันไม่ให้หลุดไปในคำตอบจริงโดย safe()
FEWSHOT = [
    ("ช่วงที่มีผู้โดยสารมากที่สุดคือ 7 โมงเช้า (07:00–07:59) เฉลี่ย 512 คันที่มีผู้โดยสาร · น้อยสุดคือ ตี 4 (98 คัน)",
     "ผู้โดยสารเยอะช่วงไหน", "ช่วง 7 โมงเช้าครับ มีรถรับผู้โดยสารเฉลี่ย 512 คัน"),
    ("ณ 02/10 09:00 รถออนไลน์ทั้งหมด 2,000 คัน · มีผู้โดยสาร 20% · วิ่งว่าง 30% · จอด 50% → รถวิ่ง : รถจอด ≈ 50:50 · รถมีผู้โดยสาร : รถจอด ≈ 29:71",
     "รถมีผู้โดยสารเทียบกับรถจอดเป็นยังไง", "รถมีผู้โดยสาร : รถจอด ประมาณ 29:71 ครับ (ข้อมูล 09:00)"),
    ("เขตที่น่าเปิดสถานีชาร์จในนนทบุรี: 1. อำเภอปากเกร็ด (รถเฉลี่ย 88 คัน/ชม. · สถานีชาร์จ 1 แห่ง) · 2. อำเภอบางใหญ่ (รถเฉลี่ย 61 คัน/ชม. · สถานีชาร์จ 0 แห่ง) — เป็นคำแนะนำเบื้องต้น",
     "นนทบุรีควรเปิดที่ชาร์จตรงไหน", "แนะนำอำเภอปากเกร็ดครับ รถวิ่งเฉลี่ย 88 คันต่อชั่วโมงแต่มีสถานีชาร์จแค่ 1 แห่ง รองลงมาคืออำเภอบางใหญ่ (เป็นการประเมินเบื้องต้น)"),
]

memory = {"plate": None, "place": None}
REF_CAR = re.compile(r"คันนี้|คันเดิม|คันนั้น|คันเมื่อกี้|รถคันนี้|มัน")
REF_PLACE = re.compile(r"ที่นั่น|จังหวัดนี้|แถวนั้น|ที่เดิม|ที่นี่")

def understand(q):
    """ดึง slot + ทาย intent · ถ้าอ้าง 'คันนี้' / 'ที่นั่น' ใช้ค่าจากคำถามก่อนหน้า"""
    e = extract(q)
    extra = ""
    if not e["plate"] and memory["plate"] and REF_CAR.search(q):
        e["plate"] = memory["plate"]; extra += " ทะเบียนรถ"
    if not e["place"] and memory["place"] and REF_PLACE.search(q):
        e["place"] = memory["place"]; extra += " สถานที่"
    p = clf.predict_proba(enc.encode([mask(q) + extra], normalize_embeddings=True))[0]
    return e, clf.classes_[p.argmax()], float(p.max())

def facts_for(q):
    """คืน (intent, ข้อเท็จจริงเป็นข้อความ) — ข้อเท็จจริงมาจาก executor ส่วน 6 / 7.2 เท่านั้น"""
    if "route_analytic" in globals():                      # cell 7.2 — คำถามวิเคราะห์
        r = route_analytic(q)
        if r:
            return r
    if "is_rank" in globals() and is_rank(q):             # cell 7.1 — "เขตไหน…มากที่สุด"
        return "area_ranking", rank_facts(q)
    e, intent, conf = understand(q)
    if conf < MIN_CONF:
        return "unclear", "ระบบไม่แน่ใจว่าผู้ใช้ถามเรื่องอะไร ให้ชวนถามใหม่ เช่น ตำแหน่งรถ รถในจังหวัด เส้นทาง รถนอกเขต จุดชาร์จ"
    if intent == "action_request":
        return intent, "ระบบนี้ตอบคำถามได้อย่างเดียว ไม่สามารถสั่งการรถ (ตัดสัญญาณ ล็อก ดับเครื่อง) ได้"
    if intent == "other":
        return intent, "คำถามนี้ไม่เกี่ยวกับรถแท็กซี่ EV7 ระบบตอบได้เฉพาะ ตำแหน่งรถ รถในพื้นที่ เส้นทาง รถนอกเขต สถานีชาร์จ"
    run = {"cars_in_area": lambda: x_cars_in_area(e["place"], e["when"]),
           "car_status": lambda: x_car_status(e["plate"], e["when"]),
           "car_track": lambda: x_car_track(e["plate"], e["when"]),
           "out_of_zone": lambda: x_out_of_zone(e["when"]),
           "fleet_stats": lambda: x_fleet_stats(e["when"]),
           "nearest_charger": lambda: x_nearest_charger(e["plate"], e["place"], e["when"])}[intent]
    r = run()
    if "error" not in r:                                   # จำไว้ใช้กับคำถามต่อไป
        memory["plate"] = e["plate"] or memory["plate"]
        memory["place"] = e["place"] or memory["place"]
    return intent, answer(intent, r)

DIGITS = re.compile(r"\d+")
def safe(text, facts):
    """กัน LLM แต่งตัวเลข: ทุกกลุ่มตัวเลขในคำตอบต้องมีอยู่ในข้อเท็จจริง"""
    ok = set(DIGITS.findall(facts))
    return all(d in ok for d in DIGITS.findall(text))

OPEN = ["", "ได้เลยครับ ", "เช็คให้แล้วครับ ", "ครับ "]
def friendly(facts):
    return random.choice(OPEN) + facts

def chat(q, show_facts=False):
    intent, facts = facts_for(q)
    if show_facts:
        print("  [ข้อเท็จจริง]", facts)
    if not USE_LLM:
        return friendly(facts)
    msgs = [{"role": "system", "content": SYSTEM}]
    for f_, q_, a_ in FEWSHOT:
        msgs += [{"role": "user", "content": f"ข้อมูลจากระบบ:\n{f_}\n\nคำถามของผู้ใช้: {q_}"},
                 {"role": "assistant", "content": a_}]
    msgs.append({"role": "user", "content": f"ข้อมูลจากระบบ:\n{facts}\n\nคำถามของผู้ใช้: {q}"})
    prompt = ctok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    x = ctok(prompt, return_tensors="pt").to(cmodel.device)
    with torch.no_grad():
        out = cmodel.generate(**x, max_new_tokens=200, do_sample=False, pad_token_id=ctok.eos_token_id)
    text = ctok.decode(out[0][x["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    if not text or not safe(text, facts):
        if show_facts:
            print("  [ตรวจ] LLM ใส่ตัวเลขที่ไม่มีในข้อมูล → ใช้คำตอบจากระบบแทน:", text[:120])
        return friendly(facts)
    return text

def แชต():
    # พิมพ์คุยต่อเนื่อง · Enter ว่าง = จบ · พิมพ์ "ล้าง" = เริ่มบทสนทนาใหม่
    while True:
        q = input("คุณ: ").strip()
        if not q:
            break
        if q == "ล้าง":
            memory.update(plate=None, place=None); print("บอท: เริ่มใหม่แล้วครับ"); continue
        print("บอท:", chat(q))
