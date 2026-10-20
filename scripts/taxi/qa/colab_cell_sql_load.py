# ── 16b · ใช้ adapter ที่เทรนไว้แล้ว (ไม่ต้องเทรนใหม่) ──
# ลำดับ: 0–7 → 13 (ตั้ง AGENT_LLM เป็นรุ่นเดียวกับ FT_BASE หรือข้ามการโหลดก็ได้) → 15 → cell นี้
# ต้องอัปโหลดโฟลเดอร์ lora_sql (จากแท็บ Output ของรอบที่เทรน) เข้า dataset ก่อน
import gc
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

FT_BASE = "Qwen/Qwen2.5-7B-Instruct"     # ต้องตรงกับตอนเทรน
_cfg = [p for p in INPUT.rglob("adapter_config.json") if "lora_sql" in str(p)] + list(DRIVE.glob("lora_sql/adapter_config.json"))
assert _cfg, "ไม่พบ lora_sql — อัปโหลดเข้า dataset แล้ว Add Input"
for v in ("amodel", "cmodel", "model", "base"):
    if v in globals():
        del globals()[v]
gc.collect(); torch.cuda.empty_cache()

atok = AutoTokenizer.from_pretrained(FT_BASE)
_b = AutoModelForCausalLM.from_pretrained(
    FT_BASE, device_map="auto", dtype=torch.float16,
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16))
amodel = PeftModel.from_pretrained(_b, str(_cfg[0].parent)).eval()
SYSTEM_A, TOOLS_A = SYSTEM_FT, TOOLS_FT
agent_history.clear()
print("ใช้โมเดลที่เทรนแล้ว:", _cfg[0].parent)
