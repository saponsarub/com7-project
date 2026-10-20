# ── 12 · เทียบ 3 แบบ ด้วยคำถามชุดเดียวกัน ──
# รันได้แม้มีแค่บางแบบ — แบบที่ยังไม่ได้รัน cell จะขึ้น "ยังไม่ได้โหลด"
#   ① LoRA (ฟรี)       → ask_llm()     จาก 8.9b + 8.8 + 8.10
#   ② Qwen chat (ฟรี)  → chat()        จาก cell 10
#   ③ Claude (เสียเงิน) → chat_claude() จาก cell 11
#   ④ Agent (ฟรี)      → agent()       จาก cell 13
import time

MODES = [("② Qwen", "chat"), ("③ Claude", "chat_claude"), ("④ Agent", "agent")]   # ① LoRA ส่วน 8 เลิกใช้ (adapter เก่าตอบ JSON คนละรูปแบบ)


def เทียบ(*questions):
    for q in questions:
        print("━" * 70)
        print("คุณ:", q)
        for label, fn in MODES:
            f = globals().get(fn)
            if f is None:
                print(f"  {label:9s} — ยังไม่ได้โหลด")
                continue
            t0 = time.time()
            try:
                a = f(q)
            except Exception as e:
                a = f"ERROR {type(e).__name__}: {e}"
            print(f"  {label:9s} ({time.time() - t0:4.1f} วิ) {a}")


# ล้างความจำบทสนทนาก่อนเทียบ ให้ทุกแบบเริ่มเท่ากัน
if "memory" in globals():
    memory.update(plate=None, place=None)
if "history" in globals():
    history.clear()
if "agent_history" in globals():
    agent_history.clear()

เทียบ("ตอนนี้ภูเก็ตมีรถกี่คัน",
      "เขตไหนในกรุงเทพมีรถเยอะสุด",
      "แถวโคราชมีแท็กซี่วิ่งอยู่ไหมตอนนี้",
      "รถออกนอกเขตวันนี้กี่คัน ไปไหนบ้าง",
      "ช่วยดับเครื่องรถคันนี้หน่อย",
      "พรุ่งนี้ฝนตกไหม")
