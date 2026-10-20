---
tags: [ai, ml, llm, data-science, learning, overview]
date: 2026-10-16
---

# AI & Data Science 2026 - What Changed

สรุปสิ่งที่เปลี่ยนไปช่วงปี 2023 → 2026 สำหรับคนที่ห่างงาน data science / AI ไป 2–3 ปี · เรียงจากเรื่องที่กระทบงานทีมเรามากที่สุด
ชื่อรุ่นโมเดลและเครื่องมือเปลี่ยนเร็วมาก — ใช้เป็นแผนที่ ไม่ใช่รายการที่ต้องจำ · ก่อนเลือกใช้จริงให้ตรวจเวอร์ชัน/ราคา/region ล่าสุดเสมอ

## ภาพรวมใน 1 ย่อหน้า

ปี 2023 คนเพิ่งเริ่มใช้ ChatGPT คุยถามตอบ · ปี 2026 LLM กลายเป็น "ชิ้นส่วนมาตรฐาน" ในระบบงาน: เรียก tool ได้ · อ่านรูป/เสียง/เอกสารยาวได้ · คิดหลายขั้นก่อนตอบ · ทำงานเป็น agent (เขียนโค้ด ค้นข้อมูล ทำงานต่อเนื่องหลายขั้น) · โมเดลเปิดที่รันเองได้เก่งขึ้นมาก · งานส่วนใหญ่**ไม่เทรน LLM** แต่ประกอบระบบรอบ LLM (prompt + tool + RAG + eval) · ส่วนงาน ML กับข้อมูลตารางยังเทรนเหมือนเดิม แต่เครื่องมือเร็วขึ้นและ AI ช่วยเขียนโค้ดเกือบทุกขั้น

## 1. LLM ทำอะไรได้มากขึ้น

| เรื่อง | 2023 | 2026 |
|---|---|---|
| ความยาวข้อความที่อ่านได้ (context) | ~4k–32k token | 100k–1M token · ใส่เอกสารทั้งเล่มได้ |
| ข้อมูลเข้า | ข้อความ | ข้อความ + รูป + PDF + เสียง (multimodal) |
| การคิด | ตอบทันที | **reasoning / extended thinking** — คิดหลายขั้นก่อนตอบ เก่งขึ้นมากในงานคำนวณ/โค้ด/วางแผน |
| เรียก tool | เริ่มมี (function calling) | มาตรฐานทุกเจ้า · **structured output** บังคับให้ตอบตาม JSON schema |
| Agent | ทดลอง | ใช้จริง: coding agent (Claude Code · Cursor · Copilot) · agent ค้นข้อมูล · computer use |
| ต่อเครื่องมือ/ข้อมูล | เขียนเชื่อมเองทีละระบบ | **MCP (Model Context Protocol)** — มาตรฐานเปิดสำหรับต่อ LLM เข้ากับฐานข้อมูล/ไฟล์/ระบบต่าง ๆ ใช้กันแพร่หลาย |
| ราคา | แพง | ถูกลงหลายสิบเท่าต่อ token · มี prompt caching · batch API ลดราคา |

ค่ายหลักที่ควรรู้จัก: **Anthropic (Claude)** · **OpenAI (GPT)** · **Google (Gemini)** · โมเดลเปิด: **Qwen (Alibaba)** · **Llama (Meta)** · **DeepSeek** · **Mistral** · **Gemma (Google)**
ภาษาไทยโดยเฉพาะ: **Typhoon (SCB 10X)** · **OpenThaiGPT** · **Pathumma (NECTEC)** — ตรวจ license ก่อนใช้เชิงพาณิชย์

## 2. วิธีสร้างแอป AI ที่เป็นที่นิยม

ลำดับที่วงการใช้: **prompt → few-shot → tool / RAG → agent → fine-tune (ถ้าจำเป็น)** · รายละเอียดใน [[How AI Assistant Works (Tool + RAG)]] · [[Train vs Prompting (LoRA · Distillation)]]

| แนวทาง | ใช้เมื่อ | สิ่งที่เปลี่ยนไปจากปี 2023 |
|---|---|---|
| **RAG** | ถามจากเอกสาร | ค้นแบบผสม (คำตรง BM25 + ความหมาย vector) · **reranker** จัดลำดับซ้ำ · chunk ตามโครงสร้างเอกสาร · บางงานใส่เอกสารทั้งก้อนได้เพราะ context ยาวขึ้น |
| **Text-to-SQL / ถามข้อมูลด้วยภาษาคน** | ถามตัวเลขจาก warehouse | แพลตฟอร์ม data ใส่มาให้ในตัว (เช่น Databricks Genie · Snowflake Cortex Analyst · Amazon Q in QuickSight) · หัวใจคือ **semantic layer** (นิยาม metric/คอลัมน์ให้ชัด) |
| **Agent** | งานหลายขั้น | LLM วนเรียก tool เอง · ต้องคุมด้วยสิทธิ์ + จำกัดรอบ + log ทุกขั้น |
| **Fine-tune** | โมเดลเล็ก/ข้อมูลห้ามออก/คุมรูปแบบ | LoRA / QLoRA เป็นมาตรฐาน · **DPO** แทน RLHF สำหรับสอนความชอบ · **distillation + synthetic data** (ให้โมเดลใหญ่สร้างข้อมูลสอน) แพร่หลาย |

**Framework:** LangChain / LangGraph · LlamaIndex · DSPy · OpenAI Agents SDK · Claude Agent SDK — หลายทีมเรียก SDK ของผู้ให้บริการตรง ๆ แทน framework เพราะ API ทำได้เองมากขึ้น
**รันโมเดลเอง:** **vLLM** (server production) · **Ollama / llama.cpp** (เครื่องตัวเอง) · บีบ 4-bit (GGUF · AWQ · bitsandbytes)
**Cloud:** AWS **Bedrock** (Claude · Llama · ฯลฯ) · Azure AI Foundry / OpenAI · Google Vertex AI — ตรวจว่าโมเดลมีใน region ที่ใช้ (เช่น ap-southeast-7) และนโยบายเก็บข้อมูล

## 3. วัดผลและดูแลระบบ (LLMOps)

- **Eval set** เป็นเรื่องแรกที่ต้องมี ไม่ใช่เรื่องสุดท้าย · วัดทุกครั้งที่แก้ prompt/โมเดล
- **LLM-as-judge**: ให้ LLM อีกตัวให้คะแนนคำตอบตาม rubric (ต้องสุ่มตรวจด้วยคนด้วย)
- **Observability**: เก็บทุกคำถาม · tool call · token · ค่าใช้จ่าย · เวลา — เช่น Langfuse · LangSmith · Arize Phoenix
- **Guardrails**: ขอบเขตคำถาม · กันข้อมูลส่วนบุคคลหลุด · ตรวจตัวเลขกับผล tool · กัน prompt injection (ข้อความในเอกสาร/เว็บที่พยายามสั่ง LLM)
- **Prompt เป็นโค้ด**: เก็บใน git · มีเวอร์ชัน · ผ่าน eval ก่อนขึ้นจริง

## 4. Data Science / ML แบบดั้งเดิม — ยังเทรนกันปกติ

| เรื่อง | สถานะ 2026 |
|---|---|
| ข้อมูลตาราง (ทำนาย ค้างชำระ churn) | **gradient boosting (XGBoost · LightGBM · CatBoost)** ยังเป็นตัวหลัก · มี tabular foundation model (เช่น **TabPFN**) สำหรับข้อมูลเล็ก |
| พยากรณ์อนุกรมเวลา | ยังใช้ statistical + boosting · มี **time-series foundation model** (เช่น Chronos · TimesFM · TimeGPT) พยากรณ์ได้โดยไม่ต้องเทรน — เหมาะเป็น baseline |
| จัดหมวด / ข้อความ | embedding + classifier เล็ก (แบบโมเดล ITEC) ถูกและเร็วกว่าเรียก LLM ทุกแถว · หรือใช้ LLM ติดป้ายให้ แล้วเทรนโมเดลเล็กตาม (distillation) |
| Embedding หลายภาษา (รวมไทย) | bge-m3 · multilingual-e5 · ของผู้ให้บริการ API |
| อธิบายโมเดล | SHAP ยังเป็นมาตรฐาน |

## 5. เครื่องมือข้อมูลที่เปลี่ยน

| เรื่อง | ที่นิยมขึ้น |
|---|---|
| DataFrame | **Polars** (เร็วกว่า pandas มาก) · pandas ยังใช้ทั่วไป |
| Query ในเครื่อง | **DuckDB** — SQL บน Parquet/CSV/S3 โดยไม่ต้องมี server (ใช้แล้วใน agent Taxi) |
| Format / Lakehouse | Parquet + **Apache Iceberg** เป็นมาตรฐาน (AWS มี S3 Tables) · Delta Lake ฝั่ง Databricks |
| Transform | **dbt** · SQLMesh |
| Python | **uv** (ติดตั้ง package / env เร็วมาก) · **ruff** (lint/format) |
| เขียนโค้ด | AI coding assistant เป็นเรื่องปกติ — ตรวจโค้ดที่ AI เขียนทุกครั้ง |

## 6. กฎหมายและความปลอดภัย

- **PDPA (ไทย)** — ส่งข้อมูลส่วนบุคคลไปผู้ให้บริการ LLM = ส่งออกนอกองค์กร (บางเจ้าออกนอกประเทศ) → ต้องมีฐานทางกฎหมาย + DPO อนุมัติ · เลือก region / ตัวเลือกไม่เก็บข้อมูล (zero data retention) ถ้ามี · pseudonymize ก่อนส่ง
- **EU AI Act** มีผลแบบทยอยตั้งแต่ปี 2024 — กระทบถ้ามีลูกค้า/ธุรกิจในยุโรป · ไทยมีร่างกฎหมาย AI อยู่ระหว่างพิจารณา `[ต้องตรวจสถานะล่าสุด]`
- ความเสี่ยงใหม่: **prompt injection** · ข้อมูลลับหลุดผ่านคำตอบ · AI แต่งข้อมูล (hallucination) → ต้องมี guardrail + log

## 7. บทบาทและทักษะ

- เกิดตำแหน่ง **AI Engineer** — ประกอบระบบรอบ LLM (prompt · tool · RAG · eval · deploy) ทับซ้อนกับ data scientist / data engineer
- ทักษะที่ **ยังสำคัญเท่าเดิมหรือมากขึ้น**: SQL · ความเข้าใจข้อมูลและธุรกิจ · สถิติ/การวัดผล · คุณภาพข้อมูล · การเขียน spec ให้ชัด
- ทักษะที่ **ต้องเพิ่ม**: เขียน prompt/คำอธิบายข้อมูลให้ LLM · ออกแบบ tool · ทำ eval set · คุมต้นทุน token · ความปลอดภัย LLM

## 8. แผนเรียนกลับเข้ามา (ผูกกับงานจริงของทีม)

| ช่วง | เรียน | ทำกับงานจริง |
|---|---|---|
| สัปดาห์ 1–2 | ใช้ LLM ผ่าน API: messages · system prompt · tool calling · structured output · streaming | อ่าน cell 11 (Claude + tool) ใน [[EV7 Taxi - Q&A Notebook (Kaggle)]] · ลองรันกับ key ทดลอง |
| สัปดาห์ 3–4 | RAG: embedding · vector search · reranking · eval | ทำ bot ถามโน้ต Obsidian (เลือกเฉพาะโน้ตที่ไม่มีข้อมูลอ่อนไหว) |
| เดือน 2 | Text-to-SQL + semantic layer · eval แบบรันผลเทียบเฉลย | Taxi agent (cell 13–16) → ต่อยอดถามยอดขาย ITEC บน Athena |
| เดือน 2–3 | Fine-tune LoRA · synthetic data · DPO (อ่าน) | ปิดงาน [[Text-to-SQL Fine-tune (EV7 Taxi)]] |
| ต่อเนื่อง | LLMOps: logging · eval อัตโนมัติ · ต้นทุน · guardrail · PDPA | ออกแบบ deploy (แบบ C หรือ D) |
| ควบคู่ | ML ตาราง: LightGBM · SHAP · time-series foundation model | ทำนายค้างชำระ UFUND · พยากรณ์ยอดขาย ITEC |

ต่อ: [[AI-ML Index]] · หน้า HTML: https://claude.ai/artifact/DKbXfz4Bp4rpbz4ufSTJf8
