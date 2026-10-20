"""สร้าง taxi_qa_kaggle.ipynb จาก taxi_qa_colab.ipynb + cell เสริม (7.1 · 8.9b · 10 · 11 · 12)

    python scripts/taxi/qa/make_kaggle_nb.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
nb = json.loads((HERE / "taxi_qa_colab.ipynb").read_text(encoding="utf-8"))
cells = nb["cells"]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n").splitlines(True)}


def src(c):
    return "".join(c["source"])


def find(prefix):
    return next(i for i, c in enumerate(cells) if src(c).lstrip().startswith(prefix))


def cell_file(name, **repl):
    s = (HERE / name).read_text(encoding="utf-8")
    for a, b in repl.items():
        s = s.replace(a, b)
    return code(s)


# ── หัว notebook + ส่วน 0 แบบ Kaggle ─────────────────────────────────────
HEAD = md("""
# EV7 Taxi — ถามตอบภาษาไทย (Kaggle)

รุ่น Kaggle ของ `taxi_qa_colab.ipynb` · เนื้อหาเหมือนกัน ต่างแค่ที่เก็บไฟล์ + มี chatbot 3 แบบให้เทียบท้าย notebook

**ตั้งค่าครั้งแรก**
1. kaggle.com → **Create → New Dataset** → ชื่อ `taxi-qa-data` → ลาก `taxi_qa_data.zip` ใส่ (Kaggle แตก zip ให้เอง)
   และลากโฟลเดอร์ `lora_taxi` (ดาวน์โหลดจาก Google Drive) ใส่ dataset เดียวกัน → ตั้ง **Private** → Create
2. **Create → New Notebook** → **File → Import Notebook** → เลือกไฟล์นี้
3. แผงขวา **Input → Add Input** → ค้น `taxi-qa-data` (แท็บ Your Datasets) → ➕
4. แผงขวา **Settings**
   - **Accelerator → GPU T4 x2** (ส่วน 8 · 8.9b · 10 ต้องใช้ · ฟรี 30 ชม./สัปดาห์)
   - **Internet → On** (ต้องยืนยันเบอร์โทรในบัญชี Kaggle ก่อน · ใช้ดาวน์โหลดโมเดลและ pip)
5. รันจากบนลงล่าง (`Shift + Enter`)

> 🔒 ห้ามอัปโหลด `plate_map_LOCAL.csv` · dataset ต้องเป็น **Private** · พิกัดรถเป็นข้อมูลอ่อนไหว — ขออนุมัติก่อนใช้ cloud ภายนอก

| chatbot | cell | ค่าใช้จ่าย | ต้องมี |
|---|---|---|---|
| ① LoRA ที่เทรนไว้ | 8.1–8.3 → 8.9b → 8.8 → 8.10 | ฟรี | GPU · โฟลเดอร์ `lora_taxi` ใน dataset |
| ② Qwen chat | 10 | ฟรี | GPU |
| ③ Claude | 11 | จ่ายตามใช้ | Secret `ANTHROPIC_API_KEY` |
| เทียบ 3 แบบ | 12 | — | รันแบบไหนก่อนก็ได้ |
""")

SEC0_MD = md("""
## 0 · ตั้งค่า Kaggle — หาไฟล์ข้อมูลจาก dataset

Kaggle วางไฟล์ dataset ไว้ที่ `/kaggle/input/<ชื่อ dataset>/` (อ่านอย่างเดียว) · ไฟล์ที่เราบันทึกเองอยู่ `/kaggle/working/` (ดาวน์โหลดได้จากแท็บ Output หลังรัน)

ผลที่ถูก: `['dim_province.csv', 'dist_pip.geojson', 'ev_chargers_osm.json', 'points.parquet']` และบอกที่อยู่ `lora_taxi`

| ถ้าเจอ | แก้ |
|---|---|
| `ไม่พบ points.parquet` | ยังไม่ได้ Add Input dataset (ข้อ 3 ด้านบน) |
| `lora_taxi: ไม่พบ` | ใช้แบบ ② ③ ได้ตามปกติ · แบบ ① ต้องอัปโหลดโฟลเดอร์ `lora_taxi` เข้า dataset |
""")

SEC0 = code(r'''
import sys, zipfile, shutil
from pathlib import Path

IN_COLAB = False
CLOUD = True                                                 # บันทึกผลลง DRIVE (= /kaggle/working)
INPUT = Path("/kaggle/input")
DRIVE = Path("/kaggle/working")                              # ที่บันทึก qa_intent.joblib / lora_taxi ใหม่
DATA = DRIVE / "taxi_qa"
DATA.mkdir(exist_ok=True)

found = sorted(INPUT.rglob("points.parquet"))
if found:                                                    # Kaggle แตก zip ให้แล้ว
    for f in found[0].parent.iterdir():
        if f.is_file():
            shutil.copy(f, DATA / f.name)
else:                                                        # ยังเป็น zip
    z = sorted(INPUT.rglob("taxi_qa_data.zip"))
    assert z, "ไม่พบ points.parquet / taxi_qa_data.zip ใน /kaggle/input — Add Input dataset ก่อน"
    zipfile.ZipFile(z[0]).extractall(DATA)

cfg = sorted(INPUT.rglob("adapter_config.json"))
LORA_IN = cfg[0].parent if cfg else None                     # โฟลเดอร์ lora_taxi ที่อัปโหลดมา
print("ข้อมูลอยู่ที่", DATA, "·", sorted(p.name for p in DATA.iterdir() if p.is_file()))
print("lora_taxi:", LORA_IN or "ไม่พบ")
''')

cells[0] = HEAD
cells[1] = SEC0_MD
cells[2] = SEC0

# ── แทนคำ Colab ในส่วนที่เหลือ ───────────────────────────────────────────
for c in cells[3:]:
    s = src(c)
    s = s.replace("IN_COLAB", "CLOUD").replace("/content/lora_taxi", "/kaggle/working/lora_ckpt")
    s = s.replace("Runtime → Change runtime type → T4 GPU", "Settings → Accelerator → GPU T4 x2")
    s = s.replace("# Colab: เก็บลง Drive (เครื่อง Colab ถูกล้างเมื่อปิด)", "# Kaggle: /kaggle/working (ดาวน์โหลดจากแท็บ Output)")
    c["source"] = s.splitlines(True)

# ส่วน 6/7: รถนอกเขต → บอกจังหวัดปลายทางเรียงตามจำนวนคัน (เดิมเรียงตามคันที่มีจุดมากสุด จังหวัดเลยดูสุ่ม)
OOZ_X = 'return {"from": a, "to": when[1], "n": len(g), "cars": g.head(20).to_dict("records")}'
OOZ_X2 = ('top = r.groupby("prov_th").car_id.nunique().sort_values(ascending=False).head(5)\n'
          '    return {"from": a, "to": when[1], "n": len(g), "cars": g.head(20).to_dict("records"), "top_prov": top.to_dict()}')
OOZ_A = "มีรถออกนอกกรุงเทพฯ และปริมณฑล {r['n']} คัน\" + (f\" — {lst}\" if lst else \"\")"
OOZ_A2 = ("มีรถออกนอกกรุงเทพฯ และปริมณฑล {r['n']} คัน\" + "
          "(\" · ไปมากสุด (คัน): \" + \", \".join(f\"{k} {v}\" for k, v in r[\"top_prov\"].items()) if r.get(\"top_prov\") else \"\")")
_hit = 0
for c in cells:
    s = src(c)
    if OOZ_X in s or OOZ_A in s:
        _hit += 1
        c["source"] = s.replace(OOZ_X, OOZ_X2).replace(OOZ_A, OOZ_A2).splitlines(True)
assert _hit == 2, f"แก้ out_of_zone ไม่ครบ ({_hit})"

i81 = find("### 8.1")
cells[i81] = md("""
### 8.1 · เปิด GPU และเปิดส่วนนี้

1. แผงขวา **Settings → Accelerator → GPU T4 x2** (ถ้าเปลี่ยนตอนนี้ เครื่องจะเริ่มใหม่ → รันส่วน 0–7 ใหม่)
2. แก้ `RUN_LLM = False` เป็น `RUN_LLM = True` ใน cell ข้างล่าง แล้วรัน
3. ผลที่ถูก: `GPU: Tesla T4 ...` · ถ้าขึ้นไม่มี GPU → ตรวจ Accelerator หรือโควตา GPU สัปดาห์นี้หมด (ดูที่ kaggle.com → Settings)

**เลือกโมเดล (`LLM_ID`)** — ค่าเริ่มต้น `Qwen/Qwen2.5-1.5B-Instruct` · ต้องเป็นรุ่นเดียวกับที่เทรน `lora_taxi` ไว้
""")

i89 = find("### 8.9")
cells[i89] = md("""
### 8.9 · บันทึก LoRA (และวิธีโหลดกลับมาใช้)

ถ้าเทรนใหม่ใน Kaggle: cell ข้างล่างบันทึกลง `/kaggle/working/lora_taxi/` → หลังรันเสร็จ ดาวน์โหลดจากแท็บ **Output** แล้วอัปโหลดเข้า dataset เพื่อใช้ครั้งหน้า

**ใช้ตัวที่เทรนไว้แล้ว (ไม่ต้องเทรนใหม่):** รัน 8.1 → 8.2 → 8.3 → **8.9b** (ข้าม 8.4–8.7) → 8.8 → 8.10
""")

LORA_LOAD = code('''
# ── 8.9b · โหลดโมเดล LoRA ที่เทรนไว้แล้วจาก dataset (ไม่ต้องเทรนใหม่) ──
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

assert RUN_LLM, "แก้ RUN_LLM = True ใน cell 8.1 แล้วรัน 8.1 ใหม่ก่อน"
assert LORA_IN, "ไม่พบโฟลเดอร์ lora_taxi ใน /kaggle/input — อัปโหลดเข้า dataset แล้ว Add Input"

tok = AutoTokenizer.from_pretrained(LLM_ID)
base = AutoModelForCausalLM.from_pretrained(
    LLM_ID, device_map="auto",
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16))
model = PeftModel.from_pretrained(base, str(LORA_IN))
model.eval()
print("โหลดโมเดล LoRA แล้ว:", LORA_IN)
''')
cells.insert(i89 + 2, LORA_LOAD)

# 7.1 ต่อท้ายส่วน 7 (ก่อนหัวข้อส่วน 8)
i8 = next(i for i, c in enumerate(cells) if c["cell_type"] == "markdown" and re.match(r"\s*## 8", src(c)))
cells[i8:i8] = [md("### 7.1 · จัดอันดับพื้นที่ — \"เขตไหนมีรถมากที่สุด\""), cell_file("colab_cell_rank.py"),
                md("""
### 7.2 · คำถามเชิงวิเคราะห์

ช่วงเวลาที่ผู้โดยสารเยอะ · ช่วงวันที่ของข้อมูล · จำนวนสถานีชาร์จในพื้นที่ · รถจอดใกล้สถานีชาร์จ · แนะนำทำเลเปิดสถานีชาร์จ ·
เดาปลายทางรถที่สัญญาณหาย · รถที่รับผู้โดยสารบ่อยสุด · สัดส่วนรถวิ่ง/จอด

**เลือกประเภทคำถามยังไง (semantic router):** แปลงคำถามเป็นเวกเตอร์ด้วย MiniLM ตัวเดิม แล้วเทียบกับตัวอย่างใน `EXAMPLES`
ถ้าใกล้ตัวอย่างประเภทใหม่มากกว่าคำถามแบบเดิม (ส่วน 4) → ใช้ตัวคำนวณใหม่ · ไม่ต้องเทรน · **ระบบเข้าใจผิด = เพิ่มตัวอย่างคำถามนั้นใน `EXAMPLES` แล้วรันใหม่**

ทุกตัวเลขคำนวณจากข้อมูลจริง · ส่วนที่เป็นการประมาณ (รถใกล้สถานีชาร์จ · ทำเล · ปลายทาง) จะบอกในคำตอบ
"""), cell_file("colab_cell_analytics.py")]

# ── ท้าย notebook: chatbot 3 แบบ + เทียบ ─────────────────────────────────
CLAUDE_KEY_OLD = '''if "google.colab" in sys.modules and not os.environ.get("ANTHROPIC_API_KEY"):
    from google.colab import userdata
    os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")'''
CLAUDE_KEY_NEW = '''if not os.environ.get("ANTHROPIC_API_KEY"):
    from kaggle_secrets import UserSecretsClient
    os.environ["ANTHROPIC_API_KEY"] = UserSecretsClient().get_secret("ANTHROPIC_API_KEY")'''
claude = cell_file("colab_cell_claude_chat.py", **{CLAUDE_KEY_OLD: CLAUDE_KEY_NEW})
claude_src = src(claude).replace(
    "# ตั้ง API key ครั้งเดียว: แถบซ้ายของ Colab → 🔑 Secrets → Add new secret\n"
    "#   Name = ANTHROPIC_API_KEY · Value = key จาก console.anthropic.com · เปิดสวิตช์ Notebook access",
    "# ตั้ง API key ครั้งเดียว: เมนู Add-ons → Secrets → Add Secret\n"
    "#   Label = ANTHROPIC_API_KEY · Value = key จาก console.anthropic.com · ติ๊ก Attached ให้ notebook นี้")
assert "kaggle_secrets" in claude_src and "Add-ons" in claude_src, "แทนส่วน API key ของ cell Claude ไม่สำเร็จ"
claude["source"] = claude_src.splitlines(True)

cells += [
    md("""
## 10 · Chatbot ② Qwen — ฟรี · ตอบเป็นภาษาพูด

ต้องรันส่วน 0–7 (+ 7.1) ก่อน · ใช้ GPU · ครั้งแรกดาวน์โหลดโมเดล 3B (~6 GB) 2–3 นาที
ตัวเลขทุกตัวยังมาจาก executor ส่วน 6 — LLM แค่เรียบเรียงภาษา · ถ้า LLM ใส่ตัวเลขที่ไม่มีในข้อมูล จะใช้คำตอบจากระบบแทน

ลองถาม: `chat("เขตไหนในกรุงเทพมีรถเยอะสุด", show_facts=True)` · คุยต่อเนื่อง: `แชต()`
"""),
    cell_file("colab_cell_qwen_chat.py"),
    md("""
## 11 · Chatbot ③ Claude — ใกล้ ChatGPT/Claude ที่สุด · เสียเงินตามใช้

1. สร้าง key ที่ console.anthropic.com → เติมเครดิต → **ตั้ง spend limit**
2. เมนู **Add-ons → Secrets → Add Secret** · Label `ANTHROPIC_API_KEY` · ติ๊ก **Attached** ให้ notebook นี้
3. อยากประหยัด: แก้ `MODEL = "claude-haiku-5-5"` ก่อนรัน

⚠️ ผลค้นข้อมูล (รหัสสมมติ EV-xxxx · ชื่อพื้นที่ · พิกัด) จะถูกส่งไป Anthropic · คุยต่อเนื่อง: `แชต_claude()`
"""),
    claude,
    md("""
## 12 · เทียบ 3 แบบ

ถามคำถามชุดเดียวกันกับทุกแบบ พร้อมเวลาตอบ · แบบที่ยังไม่ได้รันขึ้น "ยังไม่ได้โหลด" · ถามเพิ่ม: `เทียบ("คำถาม 1", "คำถาม 2")`
"""),
    cell_file("colab_cell_compare.py"),
    md("""
## 13 · Agent ฟรี — Qwen เขียน SQL เอง (ใกล้แชตบอตจริงที่สุดแบบไม่เสียเงิน)

ต่างจาก cell 10: ไม่ต้องตกลงในช่องที่เขียนไว้ · Qwen อ่านคำอธิบายข้อมูล → เขียน SQL (DuckDB) → ดูผล → เขียนใหม่ได้หลายรอบ → สรุปเป็นภาษาคน
ถามได้ทุกเรื่องที่ข้อมูลมี เช่น "เทียบชลบุรีเมื่อวานกับวันนี้ช่วง 6 โมงเย็นถึง 3 ทุ่ม"

- ต้องรันส่วน 0–7 ก่อน · GPU T4 x2 · ครั้งแรกดาวน์โหลด Qwen 14B ~30 GB แล้วบีบ 4-bit (10–15 นาที) · ตอบข้อละ ~30–90 วินาที
- ถ้ารัน cell 10 ไว้ด้วย หน่วยความจำอาจไม่พอ → `del cmodel; torch.cuda.empty_cache()` ก่อน
- เร็วขึ้นแต่พลาดบ่อยขึ้น: `AGENT_LLM = "Qwen/Qwen2.5-7B-Instruct"`
- ดู SQL ที่ใช้: `agent("คำถาม", show_steps=True)` · คุยต่อเนื่อง: `แชต_agent()` (พิมพ์ `sql` เพื่อเปิด/ปิดการแสดง SQL)
- ตารางอ่านอย่างเดียว · รับเฉพาะ SELECT · ตัวเลขที่ไม่ได้มาจากผล query จะมี ⚠️ เตือน
"""),
    cell_file("colab_cell_agent.py"),
    md("""
## 14 · ประเมินผลด้วยชุดคำถามจริง

1. อัปโหลด `eval_questions.csv` (จาก `scripts/taxi/qa/`) เข้า dataset `taxi-qa-data` (New Version) หรือลากใส่ `/kaggle/working`
2. แก้ `EVAL_MODES` ให้เป็นแบบที่รันไว้ (`agent` · `chat` · `chat_claude`) แล้วรัน
3. ดาวน์โหลด `eval_results_<แบบ>.csv` จากแท็บ Output → เปิดใน Excel → กรอกช่อง **ผล** (ถูก / พอใช้ / ผิด)
4. รันบางข้อ: `ประเมิน("agent", rows=[0, 9, 29])`
"""),
    cell_file("colab_cell_eval.py"),
    md("""
## 15 · สร้างชุดข้อมูลสอน text-to-SQL

Claude (AI ตัวใหญ่) เขียนแบบคำถามภาษาไทย ~38 แบบ × หลายสำนวน + SQL เฉลย + รูปแบบคำตอบ → cell นี้เติมจังหวัด/เขต/ทะเบียน/เวลาจากข้อมูลจริง
แล้ว**รัน SQL ทุกข้อตรวจกับข้อมูลจริง** (ไม่ผ่าน = ทิ้ง) → ได้ ~1,300 บทสนทนา · บันทึก `taxi_sql_train.jsonl`

- แบ่ง test = 1 สำนวนต่อแบบคำถาม ที่โมเดลไม่เคยเห็นตอนเทรน → วัดว่าเข้าใจจริง ไม่ใช่จำประโยค
- ก่อนรัน: รัน cell 13 โดยตั้ง `LOAD_AGENT_MODEL = False` (ต้องการแค่ตาราง SQL ไม่ต้องโหลด 14B) · ใช้เวลา ~5 นาที
- เพิ่มแบบคำถามได้ที่ `fam(...)` · คำถามที่ไม่ต้องใช้ SQL ที่ `NO_SQL`
"""),
    cell_file("colab_cell_sql_trainset.py"),
    md("""
## 16 · เทรน Qwen (LoRA) → วัดผลก่อน/หลัง → ใช้ใน agent

- โมเดลตั้งต้น `Qwen2.5-7B-Instruct` (4-bit) · LoRA r=16 · 2 รอบ · สอนเฉพาะคำพูดของ assistant (SQL + คำตอบ)
- วัดผล: ให้โมเดลเขียน SQL ข้อสอบ 120 ข้อ → รันจริง → ถือว่าถูกเมื่อผลตรงเฉลยทุกตัว · แสดงก่อน/หลังเทรน + แบบคำถามที่ยังอ่อน
- เวลาเทรนบน T4 ~1–2 ชม. (ประมาณ — ดู log) · Kaggle ตัด session ที่ 12 ชม. · อย่าปิดแท็บระหว่างเทรน
- เสร็จแล้ว `agent()` ใช้โมเดลที่เทรนอัตโนมัติ (prompt สั้นกว่า → ตอบเร็วขึ้น) · adapter อยู่ที่ `/kaggle/working/lora_sql` → ดาวน์โหลดจาก Output
"""),
    cell_file("colab_cell_sql_finetune.py"),
    md("""
### 16b · ใช้ adapter ที่เทรนไว้แล้ว (ครั้งถัดไป ไม่ต้องเทรนใหม่)

อัปโหลดโฟลเดอร์ `lora_sql` เข้า dataset → รัน 0–7 → 13 (`LOAD_AGENT_MODEL = False`) → 15 → cell นี้ → `agent(...)`
"""),
    cell_file("colab_cell_sql_load.py"),
]

for c in cells:
    c.pop("id", None)
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                  "language_info": {"name": "python"}}
out = HERE / "taxi_qa_kaggle.ipynb"
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(out, len(cells), "cells")
