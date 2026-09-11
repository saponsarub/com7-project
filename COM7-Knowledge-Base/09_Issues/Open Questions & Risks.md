# Open Questions & Risks

คำถามที่ได้คำตอบแล้ว → ย้ายไป [[Decisions]] พร้อมวันที่และคนตัดสิน

---

# Questions for legal

**ห้ามตอบเองด้วยดุลพินิจทีมข้อมูล**

| คำถาม | บล็อกอะไร |
|---|---|
| รวมข้อมูลลูกค้าข้ามบริษัทในเครือได้ตามกฎหมายไหม ภายใต้ consent ที่มีอยู่ | ทุกอย่างหลัง identity resolution |
| ถ้าไม่ได้ ต้องขอ consent ใหม่ระดับกลุ่ม หรือใช้ฐานทางกฎหมายอื่น | Customer 360 |
| การรวม record ลูกค้าข้ามบริษัท ถือเป็นการเปิดเผยข้อมูลที่ต้องขอ consent เองไหม | Identity resolution |
| Replicate ข้อมูลไป Singapore เพื่อใช้ Macie ได้ไหม | การตรวจหา PII |
| QuickSight / Amazon Q ประมวลผลใน us-east-1 ถือเป็นการส่งข้อมูลข้ามพรมแดนไหม | การใช้ QuickSight |
| Braze ประมวลผลและเก็บข้อมูลที่ประเทศไหน | สัญญากับ processor |
| VPN Client โดย Vanguard — ข้อมูลวิ่งผ่าน third party ไหม มีนัยด้าน PDPA ไหม | แนวทางเชื่อมต่อใหม่ |

**ปิดไปแล้ว:**
- iCare เป็นประกันอุปกรณ์ ไม่ใช่ประกันคน → ข้อกังวลเรื่องข้อมูลสุขภาพตาม ม.26 ไม่เกี่ยว
- COM7 มี DPO อยู่แล้ว
- ข้อมูลผู้ค้ำประกันน่าจะไม่ใช้ เพราะไม่ใช่ลูกค้าจริง (รอ legal ยืนยัน)

---

# Architecture questions

**Bronze จบตรงไหน Silver เริ่มตรงไหน**
Proposal บอก Bronze = raw ที่ scan แล้ว · ทีมร่างรวม schema normalization กับ rename ด้วย ต่างกันจริงและบล็อกการออกแบบ Glue job

**Quarantine คืออะไร**
ที่พักระหว่าง scan (proposal) หรือปลายทางของข้อมูลที่ถูก reject (ทีมร่าง)

**Dataset ไหนต้องผ่านทุก layer ไหนข้ามได้**

**Glue job เดียวใหญ่ หรือแยกตาม layer** — ยังไม่ทดลอง

**CDP / Customer 360 layer อยู่ตรงไหน** — Gap Review `ARC-01` ระบุว่าขาด และจัดเป็นอันดับ 3 ของโปรแกรม

**COM7 ต้องใช้ Lake Formation ไหม** — ไม่มีใน proposal เดิม

**Streaming หรือ batch อย่างเดียว** — Gap Review `ARC-03` ระบุว่า cart abandonment ต้องยิงใน 30 นาที ไม่ใช่ T+1

---

# S3 questions

- Dataset ไหนต้องทำ Multi-Region (CRR)
- Storage class ที่เหมาะกับแต่ละ dataset
- RPO/RTO ของข้อมูลแต่ละประเภท
- Retention period ต่อ dataset (เป็นข้อกำหนด PDPA ด้วย)
- Partition key ของแต่ละ dataset

---

# Customer data questions

**ถ้าไม่มีเลขบัตรประชาชนจะทำยังไง** — ที่ประชุมเขียนว่า "ถ้ามี" แต่ GI Core `IdentityCard` เป็น nullable และไม่รู้ว่ามีกี่เปอร์เซ็นต์

**Probabilistic matching รับความผิดพลาดได้แค่ไหน**
รวมคนผิดกันแย่กว่าไม่รวม เพราะทำให้คนหนึ่งเห็นข้อมูลอีกคน `[อนุมาน]`

**Survivorship rule** — เมื่อข้อมูลขัดกัน field ไหนเชื่อระบบไหน (Gap Review `DQY-02` ระบุว่ายังไม่มี)

**ใครเป็นเจ้าของ golden record** — MIS กลาง หรือแต่ละ BU (Gap Review `ARC-12`)

**7Club เป็น source, target, หรือทั้งคู่** — ไม่มีเอกสารไหนบอก อย่าเดาว่าเป็น master customer system

---

# Source system questions

| คำถาม | ถามใคร |
|---|---|
| BU ไหนใช้ SAP B1 บ้าง | K.Benz |
| D365 ยังเขียนอยู่ หรือ read-only แล้ว | MIS-ERP |
| K2 table ไหนยัง update อยู่ | MIS-Fintech |
| **Vanguard คือใคร/อะไร** — vendor, product, หรือทีม | Data Team / AWS Team |
| **VPN Client รองรับ DMS CDC ที่ต้องเชื่อมต่อเนื่องยังไง** | AWS Team |
| **แผน Site-to-Site VPN 30 tunnels เดิม ยกเลิกหรือเลื่อน** | AWS Team |
| K2 กับ ITOS มีข้อมูลสัญญาซ้ำกันไหม | K.Ton |
| `PROJECT_1` / `TAN_MIS` อยู่ใน scope ingest ไหม | Data Team |
| ADLS Gen1 หรือ Gen2 · มี Azure Data Factory ไหม | Data Team |
| AION DMS / EV7CORE / EVTRACKING คืออะไร · RPA ย้ายอะไร | Punt, Nut |
| **Double7 / Co-Ture Shop / Dtac Shop ใช้ระบบอะไร** — ไม่พบชื่อเหล่านี้ในเอกสารต้นฉบับไฟล์ไหนเลย | — |
| ITEC schema documentation อยู่ไหน — survey Done แล้วแต่ไม่พบเอกสาร | Data Team |
| ~~CRM data dictionary (`crm_fied_description.html`) อยู่ไหน~~ **ปิดแล้ว 2026-09-11** — ได้ไฟล์และแตกเป็น [[CRM - Data Dictionary]] | P.Por |
| CRM เป็น platform อะไร | P.Por |

---

# Measurement questions

- อะไรคือเกณฑ์ว่าโปรแกรมนี้สำเร็จ (Gap Review `MSR-05` ระบุว่ายังไม่มี)
- จะมี control group ไหม (`MSR-02`, `MSR-03`)
- Data quality KPI — completeness, contactability, consent coverage (`DQY-04`)

---

# Documentation questions

**ไฟล์ timeline ไหนเป็นตัวจริง**
`D:\aws\README.md` อ้างถึง `COM7-DataLake-Project-Timeline.xlsx` ที่มี 9 phase 50 subtask แต่ **ไม่พบไฟล์นี้บนดิสก์** ตัวที่ใช้จริงคือ `D:\Project Timeline _ Data Team.xlsx` ซึ่งโครงสร้างต่างกัน

หมายเหตุ: `D:\aws\README.md` เป็นไฟล์ที่ AI เขียน ไม่ใช่เอกสารบริษัท ข้อมูลในนั้นต้องตรวจกับต้นทางก่อนใช้

**มี phase สำหรับ AI/ML หลัง go-live ไหม**
Timeline หยุดที่ Production (Design → Implement → Test → Deploy → Maintain) ไม่มีงานสร้าง model

---

# Risks

## High

**รวมข้อมูลข้ามบริษัทอาจผิดกฎหมาย**
Data Framework slide 6 ระบุว่า consent เป็นของแต่ละบริษัท แต่ slide 8 เสนอครอบคลุมทั้งเครือ Gap Review ระบุว่าถ้าไม่มี consent orchestration สองข้อนี้ขัดกัน
ถ้าสร้าง unified customer table ไปก่อนแล้วค่อยรู้ อาจต้องทำลาย dataset ทิ้ง `[อนุมาน]`

**Identity resolution รวมผิดคน**
ยังไม่มี rule, survivorship, หรือ merge history (`IDN-12` ระบุว่าขาด) และ Gap Review `DQY-03` ระบุว่าที่อยู่ภาษาไทยเขียนได้หลายรูปแบบ ทำให้ match พลาดสูง
รวมผิดคนหมายถึงคนหนึ่งเห็นข้อมูลอีกคน ซึ่งกู้คืนยากกว่าการไม่รวม `[อนุมาน]`

**IAM ระดับ bucket คุมข้าม BU ไม่พอ**
Gap Review `ARC-10`: *"พนักงาน BU หนึ่งเข้าถึงข้อมูลลูกค้าของอีก BU ได้โดยไม่มีฐานทางกฎหมายรองรับ"*
ไม่มี Lake Formation ใน proposal

**ไม่เคยทดสอบต่อ database จริง**
PoC ทั้งหมดใช้ file upload ยังไม่รู้ latency, throughput, firewall, permission
ประชุม 24 ส.ค. เปลี่ยนเป็นต่อผ่าน VPN Client โดย Vanguard แต่**ยังไม่ได้ทดสอบเหมือนเดิม** — เปลี่ยนแค่วิธีเชื่อม
ถ้าความเร็วไม่พอสำหรับ 50 GB/วัน ทางแก้อาจเป็น Direct Connect ซึ่งใช้เวลาจัดหานาน `[อนุมาน]`

**แนวทางเชื่อมต่อใหม่ยังไม่มีเอกสาร**
เปลี่ยนจาก Site-to-Site VPN เป็น VPN Client โดย Vanguard แต่ยังไม่รู้ว่า Vanguard คืออะไร เปลี่ยนเพราะอะไร และรองรับการเชื่อมต่อแบบต่อเนื่องของ DMS CDC ยังไง
AWS Proposal ทั้งฉบับเขียนบนสมมติฐาน Site-to-Site VPN — **ยังไม่รู้ว่าส่วนอื่นของ proposal กระทบด้วยไหม** `[อนุมาน]`

**ไม่มีเครื่องมือตรวจหา PII ในภูมิภาค**
Macie ยังไม่เปิดใน ap-southeast-7 · ทางเลือกคือ replicate ไป Singapore (ติดเรื่องข้ามพรมแดน) หรือรอ
รวมกับ `ARC-09` ที่ระบุว่ายังไม่ได้ tokenize เลขบัตร → field ที่เสี่ยงที่สุดไม่ถูกค้นหาและไม่ถูกป้องกันอัตโนมัติ

## Medium

**RPA ที่ไม่มีเอกสารพังตอน migrate**
บันทึกประชุมระบุว่า GI Core มี RPA เชื่อมไประบบอื่น และเตือนเองว่า *"ต้องทำความเข้าใจ Data Flow ให้ชัดเจนก่อน"*

**ตัดสินใจเรื่องมาตรฐานช้าจะแพง**
Gap Review `ARC-05`: *"ต้อง lock naming convention ก่อน BU อื่นเริ่ม onboard การแก้ภายหลังมีต้นทุนสูงมาก"*
ตอนนี้ onboard ไปแค่ 1 ระบบ

**ลูกค้าได้ข้อความจากหลาย BU พร้อมกัน**
Gap Review `ACT-04`: *"ลูกค้ารำคาญและ opt-out ซึ่งเป็นความเสียหายที่กู้คืนได้ยากที่สุด"*

**พิสูจน์คุณค่าของโปรแกรมไม่ได้**
ไม่มี KPI (`MSR-05`) และไม่มี control group (`MSR-02`, `MSR-03`)

**ตัดสินใจเรื่อง Redshift โดยไม่มีข้อมูลจริง**
ยังรอ AWS setup demo

**Malware หลุดเข้า lake**
การ scan แบบเลือกสมเหตุสมผล แต่บันทึกเองระบุว่า VPN ไม่ scan malware — เป็นความเสี่ยงที่ยอมรับไว้ ควรทบทวนเมื่อ onboard source แบบไฟล์ใหม่ `[อนุมาน]`

**Cost บาน**
จุดที่มีตัวเลข: GuardDuty ~3,500 USD/เดือนถ้า scan ทุก object · Amazon Q เป็นก้อนใหญ่ที่สุดของ QuickSight · Redshift Spectrum บันทึกว่า "แพงมาก"

**Survey ค้าง**
เสร็จ 1/11 และเจ้าของกระจายหลายทีม ไม่มีใครคนเดียวปลดล็อกได้ `[อนุมาน]`

---

## เชื่อมกับโน้ตอื่น

[[SSOT Roadmap]] · [[Current Status]] · [[Decisions]] · [[Consent & PDPA]]
