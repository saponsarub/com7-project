# Pipeline Issues

คำถามและงานค้างของ pipeline · เครือข่าย · โปรเจกต์ที่กำลังเดิน

---

## Network & VPN — งานที่ต้องทำต่อ

เนื้อหา → [[Network & VPN]]

- [ ] กรอกช่องที่ยังว่าง (Public IP · firewall · CIDR ทั้ง 2 ฝั่ง)
- [ ] ตัดสินใจ Static vs **BGP**
- [ ] **สร้าง PSK ใหม่** ถ้าไฟล์เดิมผ่านช่องทางที่ไม่ปลอดภัย และย้ายไปเก็บใน Secrets Manager
- [ ] ตรวจว่า on-prem CIDR ไม่ทับกับ VPC CIDR (ถ้าทับ ต้องทำ NAT)
- [ ] ประเมินแบนด์วิดท์ที่ต้องใช้ตอน full load ครั้งแรก — เทียบกับเพดาน 1.25 Gbps
- [ ] ตั้ง CloudWatch alarm บนสถานะ tunnel
- [ ] ระบุเจ้าของ/ผู้ดูแลการเชื่อมต่อ

---

## K2 Termination Automation — เรื่องที่ต้องตัดสินใจก่อนลงมือ

เนื้อหา → [[K2 Termination Automation]] · ยังเป็นข้อเสนอ ยังไม่ได้ลงมือ

- [ ] **"📧 USER" ผู้รับอีเมลคือใคร** — ทีมติดตามหนี้ภายใน หรือตัวลูกค้าเอง · ถ้าเป็นลูกค้า **ขั้นให้คนอนุมัติก่อนส่งจำเป็น ไม่ใช่ทางเลือก** → **หัวหน้าทีมติดตามหนี้**
- [ ] **SES ไม่มีที่ ap-southeast-7** — เลือกทางไหน: presigned URL (แนะนำ) · SMTP ของบริษัท · หรือ SES สิงคโปร์ (ต้องให้ legal เคลียร์เรื่อง PII ข้ามพรมแดน) → **legal / DPO**
- [ ] เลือก compute: **ECS Fargate** (เสนอ) หรือ Lambda container image
- [ ] เลือกวิธีทำ PDF: LibreOffice headless หรือ reportlab · และหาฟอนต์ไทยที่มีสิทธิ์ใช้เชิงพาณิชย์
- [ ] ตกลงว่าจะเก็บ audit trail ว่าใครได้รับหนังสือเมื่อไหร่ไว้ที่ไหน (เสนอ DynamoDB)
- [ ] **connection string ยังเป็น public IP** — ต้องเปลี่ยนเป็น private IP ตอนย้ายไปวิ่งผ่าน VPN → [[Network & VPN]]

---

## Redshift — เรื่องที่ต้องหาคำตอบก่อนตัดสินใจ

เนื้อหา → [[Redshift]] · **ยังไม่ได้ตัดสินใจว่าจะใช้หรือไม่**

*(ปิดแล้ว 2026-09-02: ap-southeast-7 มีทั้ง Redshift Serverless และ Provisioned · Serverless GA ที่ไทยตั้งแต่ มี.ค. 2025 — ไม่ติดข้อกำหนด PDPA ดู [[Redshift]])*

- [ ] PoC review บันทึกว่า Spectrum "แพงมาก" — **ประเมินบนฐาน Provisioned ($5/TB แยก) หรือ Serverless (รวมใน RPU) ?** ขอตัวเลขจริงด้วยว่า scan เท่าไหร่ query แบบไหน → **คนที่ทำ PoC** · ดู [[Redshift]]
- [ ] มี dashboard ที่ต้องใช้ทุกวันจริงไหม — ถ้าไม่มี [[Athena Benchmark|Athena]] ยังพอ ยังไม่ต้องเปิด Redshift
- [ ] ถ้าเปิดใช้ ต้องตกลง VARCHAR ของฟิลด์ข้อความไทยให้เผื่อ 3–4 เท่า (byte ไม่ใช่ตัวอักษร) → [[Data Standardization & Quality]]
- [ ] QuickSight ไม่มีที่ไทย — ถ้าเลือก BI ตัวอื่น ตัวนั้นต่อ Redshift หรือ Athena ได้ไหม → [[Analytics & AI]]

---

## Google Sheet Pipeline — งานที่ต้องทำต่อ

แผนเต็ม → [[Google Sheet Pipeline]] · ข้อตัดสินใจ → [[Google Sheet to S3 (Lambda)]]
โค้ด `scripts/lambda/googlesheet-to-s3/` · เอกสารทีละฟังก์ชัน `docs/googlesheet-to-s3.md`

**สถานะ 2026-09-07 · v2.1.0** — 4 ชีต 14 tabs · รันสำเร็จ 14/14 ใน 32.8 วินาที · SES ส่งได้ · **log ใช้ schema กลางของแผนก 32 คอลัมน์** · **Lambda ตัวที่ 2 นับแถวจาก S3**

**Phase 1 · Bronze**

- [x] อัปโหลด zip แล้ว Test — **ผ่าน 2026-09-03 · 7/7 tab · 42,372 แถว · 16.3 วินาที**
- [x] ตั้ง Memory 2048 MB · Timeout 5 นาที — ใช้จริง 432 MB
- [x] ตั้ง SNS + อีเมลรายงาน — **ส่งได้แล้ว** (topic `googlesheet-ev1`)
- [ ] เปิด **S3 Versioning** บน `google-sheet-extract` — ได้ประวัติย้อนหลังโดยไม่ต้องแก้โค้ด
- [ ] ลบตารางเก่าใน Glue (ที่ `location` ลงท้าย `.csv`) แล้ว run crawler ใหม่
- [ ] ตรวจว่าทุกตารางมี `skip.header.line.count = 1`
- [ ] ลบโฟลเดอร์เก่าใน S3 (`leads-ev7-*`) หลังยืนยันข้อมูลใหม่ครบ
- [ ] ตั้ง EventBridge Scheduler `cron(0 23 * * ? *)` timezone Asia/Bangkok + **DLQ**
- [ ] CloudWatch Alarm บน error/timeout → SNS
- [ ] **เพิ่ม path `google-sheet-gi/` ให้ Crawler** — ข้อมูล GI ยังไม่มีใครสแกน → [[Glue Crawler]]
- [ ] ตกลงชื่อโฟลเดอร์ตัวพิมพ์ใหญ่ (`Grab_Clean` · `GI_Booking`) หรือเปลี่ยนเป็นตัวเล็กให้เข้าชุดกับ `ev7_*` — Glue แปลงชื่อตารางเป็นตัวเล็กอยู่แล้ว

**Phase 2 · สำรวจข้อมูล**

- [ ] query ทั้ง 14 tab ด้วย Athena ดูว่าคอลัมน์อะไรบ้าง อันไหนใช้จริง
- [ ] ตรวจว่า `Clean` กับ `ชีต1` ของ Grab/Lineman ต่างกันยังไง — ถ้า `Clean` เป็นเวอร์ชันที่ผ่านการล้างแล้ว อาจไม่ต้องเก็บดิบทั้งคู่
- [ ] **ยืนยันว่ามี PII ไหม** — ถ้ามีต้องเข้ากติกา [[Consent & PDPA]] → **legal / DPO**
- [ ] ตัดสินใจว่า tab ไหนควรเข้า lake จริง (`Check` `Filter` `Event` `Compare by puii` อาจเป็นช่องช่วยคำนวณ)

**Phase 3-4 · Silver และการต่อขั้น**

- [ ] ออกแบบ Silver หลังเห็นข้อมูลจริงแล้วเท่านั้น
- [ ] ตัดสินใจ Iceberg vs Parquet (เอียงไป Iceberg เพราะสร้างทับทุกวัน)
- [ ] ย้ายมา Step Functions ตอนมี 3 ขั้นที่พึ่งกัน

**ทำให้พร้อมใช้จริง**

- [x] สร้างถัง log + ตั้ง `LOG_BUCKET` — **เขียน log CSV 25 คอลัมน์ได้แล้ว** (ถัง `com7-ingest-logs-603238661233`)
- [x] ตั้ง SES ให้ส่งได้จริง — **ส่งออกแล้วผ่าน ap-southeast-1**
- [ ] `NEXT_RUN` ในรายงานยัง hard-code เป็น `"Tomorrow 23:30 (UTC+7)"`

**ปรับปรุง log — ทำแล้วใน v2.0.0** → [[Google Sheet to S3 (Lambda)]]

- [x] **`rows_match` เป็น `true` เสมอ** — แก้แล้ว · เทียบ `ContentLength` หลังอัปโหลด + Lambda 2 นับแถวจากไฟล์จริง
- [x] `Header_Hash` · `Etag` — เพิ่มแล้ว
- [x] **เวลาเริ่ม-จบ-ระยะเวลาราย tab** — เพิ่มแล้วใน v2.1.0 รวม tab ที่พัง
- [x] เรียง column ตาม schema กลางของแผนก

**ที่ยังค้าง**

- [ ] **`Threat_scan_Malware` ยังว่าง** — ต้องตัดสินใจว่าจะใช้ GuardDuty Malware Protection for S3 (PoC บันทึกว่า scan ทุก object **~3,500 USD/เดือน** → [[AWS Services]]) หรือรอ Macie เปิดที่ ap-southeast-7 → **ทีม AWS / เจ้าของงบ**
- [ ] `Step_Function_Name` `Server_Name` `Port` `DB_Name` ปล่อยว่าง — **ยืนยันกับพี่ที่ออกแบบ schema** ว่าให้ว่างหรือใส่ `N/A`
- [ ] `Table_row count` มีช่องว่างในชื่อ — query ใน Athena ต้องครอบ `"..."` ทุกครั้ง · **ขอเปลี่ยนเป็น `_` ได้ไหม**
- [ ] `Job_No` เป็น UUID ไม่ใช่เลขลำดับ — ถ้า schema กลางต้องการเลขรัน ต้องมีตัวนับกลาง
- [ ] `Write_Mode` · `Column_count` ไม่มีใน schema กลางทั้งที่ **D-15 บังคับ** — ยกไปคุยในทีม
- [ ] CloudWatch metric filter จับ `MISMATCH` · `ROWCOUNT INVOKE FAILED` · `SES SEND FAILED`
- [ ] `values:batchGet` — รวม tab ของชีตเดียวกันเป็นคำขอเดียว (14 → 4) **แก้ต้นเหตุที่ tab ท้าย ๆ timeout**
- [ ] อีเมลออกก่อน `S3_row_count` มีค่า — ถ้าอยากให้รายงานมีผลนับ ต้องเปลี่ยนลำดับหรือส่งเมลจาก Lambda 2
- [ ] error ถาวร (400/403/404) ยังถูกยกไป pass 2-3 ทั้งที่แก้ไม่ได้
- [ ] `rows_delta` เทียบรอบก่อน · null rate · duplicate count

- [x] ย้าย library ไป **Lambda Layer** — zip โค้ดเหลือ 38.9 KB · แก้ใน Console ได้แล้ว
- [ ] เปลี่ยนชื่อฟังก์ชัน/role จาก `test-*` ถ้าจะใช้จริง
- [ ] ตรวจ bucket policy / encryption ของ `google-sheet-extract`

---

## Collection Union (K2 + ITOS) — งานที่ต้องทำต่อ

เนื้อหา → [[Collection Union (K2 + ITOS)]]

- [ ] แก้ `nvarchar` ให้ระบุความยาว (ข้อบกพร่อง #1) แล้วเทียบว่าที่อยู่ยาวขึ้นจริง
- [ ] เติม `WHERE EXTRACT_DATE` เพื่อจำกัดปริมาณ
- [ ] ตัดสินใจว่าจะ union ที่ **ต้นทาง (SQL)** หรือที่ **Bronze/Silver (Glue)** — ดู [[ETL & Spark]] · [[Decisions]]
- [ ] ตรวจว่ามี `CONTRACT_ID` ชนกันระหว่าง 2 ระบบไหม (ถ้าชน ต้องทำ composite key `SOURCE_SYSTEM + CONTRACT_ID`)
- [ ] หา entity resolution ระหว่างลูกค้า K2 กับ ITOS — คนเดียวกันอาจมีทั้ง 2 ระบบ → [[Customer Identity]]

---

## K2 + ITOS Integration — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[K2 + ITOS Integration]]

*(ปิดแล้วจากประชุม 2026-08-27: K2 table ไหนยัง update · lake จะ ingest อะไร → **ITOS primary · K2 historical** ดู [[UFUND in Customer 360]])*

- K2 กับ ITOS มีข้อมูลสัญญาเดียวกันซ้ำกันไหม
- "ถังของพี่คอง" คืออะไรในเชิง AWS — S3 bucket หรือ staging DB
- **ข้อมูลผู้ค้ำประกัน** จะใช้หรือไม่ใช้ (ความเห็นล่าสุด: น่าจะไม่ใช้ เพราะไม่ใช่ลูกค้าจริง)

---

## OD6 Collection Delivery — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[OD6 Collection Delivery]]

1. เกณฑ์แบ่ง `GROUP_ASSIGN` 1–5 คืออะไร ใครกำหนด
2. ทำไมไฟล์นี้ไม่มีสัญญา ITOS (`TFF`) — ทีม ITOS ส่งไฟล์แยก หรือยังไม่ได้รวม
3. `ASSIGN_TO_TEAM` มีค่าอะไรอีกบ้างนอกจาก `OA_OD6` (OD1–OD5 ส่งให้ทีมไหน)
4. ไฟล์นี้ส่งด้วยมือหรืออัตโนมัติ ความถี่เท่าไหร่
5. หลังส่งแล้ว ผลการติดตามถูกบันทึกกลับเข้าระบบไหม ที่ตารางไหน

---

## EV China Benchmark (Ontime) — งานที่ต้องทำต่อ

เนื้อหา → [[EV China Benchmark]]

- [ ] **ยืนยันกับฐานข้อมูลจริงว่า K2 มีข้อมูล EV ปนอยู่จริงหรือไม่ และแยกด้วยคอลัมน์ไหน** ← สำคัญที่สุด
- [ ] ตรวจว่า `365` (Dynamics) ควรเป็นแหล่งข้อมูลใน Data Lake หรือไม่ — ปัจจุบันยังไม่อยู่ใน [[System Inventory]]
- [ ] ระบุว่า `Gtrack Smarth` (GPS) เก็บข้อมูลอะไร ความถี่เท่าไหร่ — เป็น time-series ขนาดใหญ่
- [ ] ประเมินว่าจะสร้าง risk layer บน Data Lake หรือซื้อระบบ risk engine

---

## เชื่อมกับโน้ตอื่น

[[Issue Index]] · [[Open Questions & Risks]] · [[Current Status]] · [[Home]]
