# ── 8.9b · โหลดโมเดล LoRA ที่เทรนไว้แล้วจาก Drive (ไม่ต้องเทรนใหม่) ──
# ลำดับ: ส่วน 0–7 → 8.1 (RUN_LLM = True) → 8.2 → 8.3 → cell นี้ → 8.8 → 8.10
# ข้าม 8.4–8.7 ได้ทั้งหมด · ต้องใช้ GPU T4
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

assert RUN_LLM, "แก้ RUN_LLM = True ใน cell 8.1 แล้วรัน 8.1 ใหม่ก่อน"
ADAPTER = DRIVE / "lora_taxi"
assert ADAPTER.exists(), f"ไม่พบ {ADAPTER} — ตรวจว่า mount Drive แล้ว (ส่วน 0) และมีโฟลเดอร์ lora_taxi"

tok = AutoTokenizer.from_pretrained(LLM_ID)
base = AutoModelForCausalLM.from_pretrained(
    LLM_ID, device_map="auto",
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16))
model = PeftModel.from_pretrained(base, str(ADAPTER))
model.eval()
print("โหลดโมเดล LoRA แล้ว:", ADAPTER)
