# ── 16 · เทรน Qwen ด้วยชุดข้อมูลจาก cell 15 (LoRA) → วัดผล → เอาไปใช้แทนโมเดลใน agent ──
# ต้องรัน 0–7 · 13 · 15 ก่อน · GPU T4 x2 · เวลาเทรนขึ้นกับจำนวนตัวอย่าง (ดูตัวเลข ETA ตอนรัน)
#
# สอนอะไร: อ่านคำถามไทย → เขียน SQL ที่ถูก (ตามตารางของเรา) → อ่านผล → ตอบสั้น ๆ
# ทำไมใช้ LoRA: ไม่แตะน้ำหนักเดิม 7 พันล้านตัว · เทรนแค่ชั้นเล็กที่แปะเพิ่ม → พอ GPU ฟรี · ไฟล์ผลลัพธ์หลักสิบ MB
import gc, json, math, re, subprocess, sys, time
import pandas as pd
import torch

FT_BASE = "Qwen/Qwen2.5-7B-Instruct"     # โมเดลตั้งต้น · เร็วกว่า: "Qwen/Qwen2.5-3B-Instruct"
EPOCHS = 2
LR = 1e-4
LORA_R = 16
MAX_LEN = 1536                           # ตัดตัวอย่างที่ยาวเกิน (token) · ปกติ ~800
EVAL_N = 120                             # จำนวนข้อสอบ (test) ที่ใช้วัดผล · ทั้งหมด = None (นาน)
EVAL_BASE = True                         # วัดโมเดลก่อนเทรนด้วย (ไว้เทียบ) · รันซ้ำแล้วรู้ผลแล้ว ตั้ง False ประหยัด ~20 นาที
OUT_DIR = DRIVE / "lora_sql"

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "peft", "bitsandbytes", "accelerate"], check=True)
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, PeftModel

# ── 0) เคลียร์ GPU (โมเดลจาก cell อื่น) ──────────────────────────────────
for v in ("amodel", "cmodel", "model", "base", "trainer", "ftmodel", "fbase"):   # รวมของรอบก่อนที่ค้าง
    if v in globals():
        del globals()[v]
gc.collect(); torch.cuda.empty_cache()

# ── 1) ข้อมูล ──────────────────────────────────────────────────────────
rows = [json.loads(l) for l in open(DRIVE / "taxi_sql_train.jsonl", encoding="utf-8")]
train_rows = [r for r in rows if r["split"] == "train"]
test_rows = [r for r in rows if r["split"] == "test"]
print(f"train {len(train_rows):,} · test {len(test_rows):,}")

ftok = AutoTokenizer.from_pretrained(FT_BASE)
ftok.pad_token = ftok.pad_token or ftok.eos_token


def render(msgs, gen=False):
    return ftok.apply_chat_template([{"role": "system", "content": SYSTEM_FT}] + msgs, tools=TOOLS_FT,
                                    tokenize=False, add_generation_prompt=gen)


def encode(msgs):
    """token ทั้งบทสนทนา · labels = -100 ทุกส่วนยกเว้นคำตอบของ assistant (สอนเฉพาะสิ่งที่โมเดลต้องพูด)"""
    ids = ftok(render(msgs), add_special_tokens=False)["input_ids"]
    labels = [-100] * len(ids)
    for j, m in enumerate(msgs):
        if m["role"] != "assistant":
            continue
        a = len(ftok(render(msgs[:j], gen=True), add_special_tokens=False)["input_ids"])
        b = len(ftok(render(msgs[:j + 1]), add_special_tokens=False)["input_ids"])
        labels[a:b] = ids[a:b]
    return {"input_ids": ids[:MAX_LEN], "labels": labels[:MAX_LEN]}


enc_train = [encode(r["messages"]) for r in train_rows]
lens = pd.Series([len(e["input_ids"]) for e in enc_train])
print(f"ความยาว token: เฉลี่ย {lens.mean():.0f} · สูงสุด {lens.max()} · ถูกตัด {int((lens >= MAX_LEN).sum())} ข้อ")


class DS(torch.utils.data.Dataset):
    def __init__(self, x): self.x = x
    def __len__(self): return len(self.x)
    def __getitem__(self, i): return self.x[i]


def collate(batch):
    m = max(len(b["input_ids"]) for b in batch)
    pad = lambda s, v: s + [v] * (m - len(s))
    return {"input_ids": torch.tensor([pad(b["input_ids"], ftok.pad_token_id) for b in batch]),
            "labels": torch.tensor([pad(b["labels"], -100) for b in batch]),
            "attention_mask": torch.tensor([pad([1] * len(b["input_ids"]), 0) for b in batch])}


# ── 2) โหลดโมเดลตั้งต้น 4-bit + ติด LoRA ───────────────────────────────────
mem = {i: f"{int(torch.cuda.get_device_properties(i).total_memory / 2**30) - 2}GiB" for i in range(torch.cuda.device_count())}
fbase = AutoModelForCausalLM.from_pretrained(
    FT_BASE, device_map="auto", max_memory=mem, dtype=torch.float16,
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16))
# ไม่ใช้ prepare_model_for_kbit_training — มันแปลง embedding/lm_head เป็น fp32 (+2 GB ต่อชั้น) จน T4 เต็ม
fbase.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
fbase.enable_input_require_grads()
fbase.config.use_cache = False
ftmodel = get_peft_model(fbase, LoraConfig(
    r=LORA_R, lora_alpha=LORA_R * 2, lora_dropout=0.05, task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
ftmodel.print_trainable_parameters()


# ── 3) วัดผล: ให้โมเดลเขียน SQL ข้อสอบ → รันจริง → เทียบผลกับเฉลย ───────────────
TOOL_RE_FT = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def first_turn(msgs_user):
    x = ftok(render(msgs_user, gen=True), return_tensors="pt").to(ftmodel.device)
    with torch.no_grad():
        out = ftmodel.generate(**x, max_new_tokens=300, do_sample=False, pad_token_id=ftok.pad_token_id, use_cache=True)
    return ftok.decode(out[0][x["input_ids"].shape[1]:], skip_special_tokens=True)


def judge(r, text):
    gold = r["messages"]
    m = TOOL_RE_FT.search(text)
    if len(gold) == 2:                                  # ข้อที่ไม่ควรเรียก SQL
        return m is None
    if not m:
        return False
    try:
        sql = json.loads(m.group(1))["arguments"]["sql"]
    except Exception:
        return False
    return tool_run_sql(sql).strip() == gold[2]["content"].strip()   # ผลตรงเฉลยทุกตัว


def evaluate(label):
    import random as _r
    _r.seed(0)
    sample = test_rows if EVAL_N is None else _r.sample(test_rows, min(EVAL_N, len(test_rows)))
    ok, t0, per = 0, time.time(), {}
    ftmodel.eval()
    for r in sample:
        good = judge(r, first_turn(r["messages"][:1]))
        ok += good
        per.setdefault(r["family"], []).append(good)
    acc = ok / len(sample)
    print(f"[{label}] ถูก {ok}/{len(sample)} = {acc:.0%} · {(time.time() - t0) / len(sample):.1f} วิ/ข้อ")
    return acc, pd.Series({k: sum(v) / len(v) for k, v in per.items()}).sort_values()


if EVAL_BASE:
    with ftmodel.disable_adapter():
        base_acc, base_per = evaluate("ก่อนเทรน")

# ── 4) เทรน ────────────────────────────────────────────────────────────
steps = math.ceil(len(enc_train) / 8) * EPOCHS
print(f"เริ่มเทรน {EPOCHS} รอบ · {steps} steps · ดู loss ลดลงเรื่อย ๆ = กำลังเรียน")
trainer = Trainer(
    model=ftmodel, train_dataset=DS(enc_train), data_collator=collate,
    args=TrainingArguments(output_dir="/kaggle/working/ft_ckpt", per_device_train_batch_size=1, gradient_accumulation_steps=8,
                           num_train_epochs=EPOCHS, learning_rate=LR, lr_scheduler_type="cosine", warmup_steps=max(1, int(0.05 * steps)),   # transformers 5 เลิกใช้ warmup_ratio
                           fp16=True, logging_steps=10, save_strategy="no", report_to=[], optim="paged_adamw_8bit",
                           gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
                           remove_unused_columns=False))
t0 = time.time()
res = trainer.train()
print(f"เทรนเสร็จ {(time.time() - t0) / 60:.0f} นาที · loss เฉลี่ย {res.metrics['train_loss']:.3f}")
ftmodel.save_pretrained(str(OUT_DIR)); ftok.save_pretrained(str(OUT_DIR))
print("บันทึก adapter →", OUT_DIR, "(ดาวน์โหลดจากแท็บ Output แล้วอัปเข้า dataset เพื่อใช้ครั้งหน้า)")

# ── 5) วัดผลหลังเทรน ─────────────────────────────────────────────────────
ft_acc, ft_per = evaluate("หลังเทรน")
if EVAL_BASE:
    cmp = pd.DataFrame({"ก่อน": base_per, "หลัง": ft_per}).fillna(0).sort_values("หลัง")
    print(f"\nก่อนเทรน {base_acc:.0%} → หลังเทรน {ft_acc:.0%}\nแบบคำถามที่ยังอ่อน (หลังเทรน):")
    print((cmp.head(8) * 100).round().astype(int).astype(str) + "%")

# ── 6) ใช้กับ agent (cell 13): สลับโมเดล + prompt สั้น ─────────────────────────
ftmodel.eval()
fbase.config.use_cache = True                       # ปิดไว้ตอนเทรน · เปิดคืนให้ตอบเร็ว
amodel, atok = ftmodel, ftok
SYSTEM_A, TOOLS_A = SYSTEM_FT, TOOLS_FT
agent_history.clear()
print('\nพร้อมใช้: agent("คำถาม", show_steps=True) ตอนนี้ใช้โมเดลที่เทรนแล้ว')
for q in ["ตอนนี้ภูเก็ตมีรถกี่คัน ว่างกี่คัน มีผู้โดยสารกี่คัน", "เขตไหนในกทมคนเรียกรถเยอะสุด", "ถนนสีลมมีรถกี่คัน"]:
    agent_history.clear()
    print("คุณ:", q); print("บอท:", agent(q, show_steps=True)); print()
