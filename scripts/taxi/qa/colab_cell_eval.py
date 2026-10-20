# ── 14 · ประเมินผลด้วยชุดคำถามจริง (eval_questions.csv) ──
# อัปโหลด eval_questions.csv เข้า dataset เดียวกับข้อมูล (หรือวางใน /kaggle/working) แล้วรัน
# ผล → /kaggle/working/eval_results_<แบบ>.csv · เปิดใน Excel แล้วกรอกช่อง "ผล" (ถูก / พอใช้ / ผิด)
import time
import pandas as pd

EVAL_MODES = ["agent", "chat"]          # แบบที่จะประเมิน (ชื่อฟังก์ชัน): agent = cell 13 · chat = cell 10 · chat_claude = cell 11

src = sorted(INPUT.rglob("eval_questions.csv")) + sorted(DRIVE.glob("eval_questions.csv"))
assert src, "ไม่พบ eval_questions.csv — อัปโหลดเข้า dataset หรือ /kaggle/working ก่อน"
EVAL = pd.read_csv(src[0], encoding="utf-8-sig", dtype=str).fillna("")
print("ชุดคำถาม:", src[0], len(EVAL), "ข้อ")


def ประเมิน(mode, rows=None):
    f = globals().get(mode)
    if f is None:
        print(f"⏭ ข้าม {mode} — ยังไม่ได้รัน cell ของแบบนี้")
        return None
    out = []
    for r in (EVAL if rows is None else EVAL.iloc[rows]).to_dict("records"):   # ใช้ r["ชื่อ"] — r.ชื่อไทย พังกับสระ "ำ"
        if r["หมวด"] != "ต่อเนื่อง":                      # คำถามต่อเนื่อง ให้จำบทสนทนาจากข้อก่อนหน้า · ข้ออื่นเริ่มใหม่
            for h in ("history", "agent_history"):
                if h in globals():
                    globals()[h].clear()
            if "memory" in globals():
                memory.update(plate=None, place=None)
        t0 = time.time()
        try:
            a = f(r["คำถาม"])
        except Exception as e:
            a = f"ERROR {type(e).__name__}: {e}"
        sec = round(time.time() - t0, 1)
        out.append({"id": r["id"], "หมวด": r["หมวด"], "คำถาม": r["คำถาม"], "คำตอบ": a, "วินาที": sec,
                    "คำตอบที่อยากได้": r["คำตอบที่อยากได้"], "ควรมีในคำตอบ": r["ควรมีในคำตอบ"], "ผล": ""})
        print(f"[{r['id']}] {r['คำถาม']}\n     → {a[:200]}  ({sec} วิ)", flush=True)   # quote เดี่ยว — Python < 3.12 ห้ามซ้อน "
    res = pd.DataFrame(out)
    path = DRIVE / f"eval_results_{mode}.csv"
    res.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"\nบันทึก {path} · เวลาเฉลี่ย {res['วินาที'].mean():.1f} วิ/ข้อ")
    return res


for m in EVAL_MODES:
    ประเมิน(m)
