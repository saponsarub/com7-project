---
tags: [ai, llm, fine-tune, lora, text-to-sql, taxi]
date: 2026-10-16
---

# Text-to-SQL Fine-tune (EV7 Taxi)

เทรน Qwen2.5-7B ให้เขียน SQL บนข้อมูลรถแท็กซี่ EV7 จากคำถามไทย · cell 15–16 ของ [[EV7 Taxi - Q&A Notebook (Kaggle)]] · แนวคิดใน [[Train vs Prompting (LoRA · Distillation)]]

## ทำไมต้องเทรน

agent แบบไม่เทรน (cell 13 · Qwen 14B + prompt ยาว) จากการเทียบ 6 คำถาม 2026-10-16: ถูก 3/6 · ตอบ 12–55 วินาที · แต่งตัวเลข (จตุจักร "45 คัน" จริง 130) · นับรถนอกเขตผิด ("15" จริง 441) → รายละเอียดใน [[EV7 Taxi - Business Questions]]

## ขั้นตอน

```
cell 13  LOAD_AGENT_MODEL = False → สร้างแค่ตาราง SQL (DuckDB) + ฟังก์ชัน
cell 15  สร้างชุดสอน → taxi_sql_train.jsonl
cell 16  วัดก่อนเทรน → เทรน LoRA → วัดหลังเทรน → ต่อเข้า agent()
cell 16b ครั้งถัดไป: โหลด adapter lora_sql ไม่ต้องเทรนใหม่
```

### cell 15 · ชุดสอน (distillation)

- Claude เขียน **แบบคำถาม (family)** — ปัจจุบัน 40 แบบใช้ SQL + 6 แบบไม่ใช้ SQL (ปฏิเสธ · ไม่มีข้อมูล · นอกเรื่อง · ทักทาย)
- แต่ละแบบ = หลายสำนวน + SQL เฉลย + ฟังก์ชันสร้างคำตอบไทยจากผล SQL
- เติมจังหวัด/เขต/ทะเบียน/วัน/ชั่วโมง สุ่มจากข้อมูลจริง · ชื่อจังหวัดสะกดผิด/ชื่อเล่น (กทม · โคราช) · ทะเบียนหลายรูปแบบ · คำขึ้นต้น/ลงท้าย
- **รัน SQL ทุกข้อกับข้อมูลจริง** · error/ผลว่าง = ทิ้ง
- 1 ตัวอย่าง = บทสนทนา: ผู้ใช้ → `<tool_call>run_sql(SQL)</tool_call>` → ผล SQL จริง → คำตอบไทย
- แบ่ง test = สำนวนสุดท้ายของแต่ละแบบ (ไม่เคยเห็นตอนเทรน)
- prompt สั้น `SYSTEM_FT` (ใช้ทั้งเทรนและใช้งาน) · ใช้ชื่อจังหวัด/เขตตรง ๆ (`prov_th = 'ภูเก็ต'`) ไม่ต้องเรียก find_place

| รอบ | ตัวอย่าง | train / test | ทิ้ง |
|---|---:|---|---:|
| 1 (32+6 แบบ) | 1,313 | 946 / 367 | 1 |
| 2 (+ moving_now_prov · out_of_zone_day_where) | 1,452 | 1,038 / 414 | 0 |
| 3 (+ offline_long · speeding · car_out_of_zone · fleet_km_day · utilization_prov · gps_gap_moving) | 1,661 | 1,175 / 486 | 0 |

### cell 16 · เทรน

| ค่า | |
|---|---|
| base | `Qwen/Qwen2.5-7B-Instruct` 4-bit NF4 |
| LoRA | r 16 · alpha 32 · dropout 0.05 · q/k/v/o/gate/up/down · trainable 40.4M / 7.66B = 0.53% |
| เทรน | 2 epoch · lr 1e-4 cosine · batch 1 × grad accum 8 · fp16 · paged_adamw_8bit · gradient checkpointing |
| ความยาว | เฉลี่ย 802 token · สูงสุด 1,046 · MAX_LEN 1536 |
| label mask | เรียนเฉพาะ tool call + คำตอบ (ตรวจด้วย tokenizer แล้ว) |
| วัดผล | 120 ข้อ test · โมเดลเขียน SQL → รันจริง → ถูกเมื่อผลตรงเฉลยทุกตัว · ข้อไม่ใช้ SQL ถูกเมื่อไม่เรียก tool |

### ผล

| | ถูก | เวลา |
|---|---|---|
| ก่อนเทรน (prompt สั้น ไม่มีตัวอย่าง) | **7/120 = 6%** | 11.4 วิ/ข้อ |
| หลังเทรน | _รอผลรันบน Kaggle_ | |

## Error ที่เจอและวิธีแก้

| error | สาเหตุ | แก้ |
|---|---|---|
| `TrainingArguments ... unexpected keyword 'warmup_ratio'` | transformers 5 บน Kaggle เลิกใช้ | `warmup_steps=max(1, int(0.05 * steps))` |
| `CUDA out of memory` ตอน `prepare_model_for_kbit_training` | โมเดลรอบที่ error ยังค้าง (`fbase`) + ฟังก์ชันนี้แปลง embedding/lm_head เป็น fp32 (+2 GB/ชั้น) | ลบ `fbase` ด้วย · ไม่ใช้ฟังก์ชันนี้ → `gradient_checkpointing_enable` + `enable_input_require_grads` เอง |
| GPU ไม่คืนหลัง `del` (ว่าง 5–7 GB) | traceback ของ error เก่ายังถือโมเดล | `sys.last_traceback = None` + `%reset -f out` · ชัวร์สุด = Restart แล้วรัน 0–7 → 13 → 15 |
| `CUDA out of memory` ตอนเทียบ (cell 12) | โหลด LoRA + Qwen 3B + 14B พร้อมกัน | cell 13 ปล่อยโมเดลอื่นก่อนโหลด · เว้น ~3 GB/การ์ด (`max_memory`) |
| `'Pandas' object has no attribute 'คําถาม'` (cell 14) | `itertuples` แปลงชื่อคอลัมน์ไทยที่มี "ำ" (NFKC) | อ่านด้วย `to_dict("records")` + `r["คำถาม"]` |

**กติกา:** cell 16 error กลางทาง → Restart ก่อนรันใหม่ทุกครั้ง

## ข้อจำกัด / ต่อไป

- วันที่ในชุดสอนตายตัว (วันนี้ = 1 ต.ค. · เมื่อวาน = 30 ก.ย.) → ข้อมูลช่วงใหม่ต้องรัน 15–16 ใหม่
- ตอบดีเฉพาะแบบที่สอน → เพิ่ม `fam(...)` จากคำถามที่ผิด (cell 14 + [[EV7 Taxi - Business Questions]])
- ถ้าใช้ชุดทะเบียนจริง `taxi_sql_train.jsonl` / `lora_sql` มีทะเบียน → เก็บบน Kaggle หรือ `D:\Taxi` เท่านั้น ห้ามเข้า repo
- ความเร็วข้อมูล GPS มีค่าผิดปกติ (สูงสุด 250 กม./ชม.) → กรอง > 180 ก่อนถามเรื่องขับเร็ว

ต่อ: [[AI-ML Index]]
