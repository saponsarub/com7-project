# Current Status

อัปเดต **2026-08-28** · ที่มา: `Project Timeline _ Data Team.xlsx` + `สรุปประเด็นจากการ POC AWS Data Lake.md` + ชุดข้อมูลที่รับเข้า 2026-08-28

---

## 🆕 อัปเดต 2026-09-08 — Glue ต่อ MSSQL: เจอต้นตอ Client VPN

**ข้อค้นพบสำคัญ:** ไล่ debug Glue job ต่อ MSSQL ทั้งวัน สรุปว่า **Client VPN ใช้กับ Glue ต่อ on-prem ไม่ได้** — Client VPN เชื่อม "เครื่องคน" ไม่ได้เชื่อม "subnet" ที่ Glue รัน (ต่างจาก DMS ที่ต่อได้เพราะสั่งจากเครื่องคน) → รายละเอียด [[Glue Connectivity]]

| เรื่อง | สถานะ |
|---|---|
| เส้นทาง network ฝั่ง S3 (endpoint/route/SG/DNS/NACL) | ✅ verify ครบแล้ว |
| STS Interface Endpoint (assume role) | ⬜ ยังต้องสร้าง |
| ต่อ on-prem ผ่าน Glue | ❌ Client VPN ไม่รองรับ → ต้อง **Site-to-Site VPN** หรือ **DMS→S3→Glue** ⭐ |

**แนวทางแนะนำ:** `on-prem ──DMS+Client VPN──► S3 ──Glue──► Bronze/Silver/Gold` (ใช้ของที่มีอยู่ เลี่ยงปัญหา network)

---

## The bottleneck

**Survey เสร็จ 2 จาก 11 ระบบ** (ITEC · K2) — ทุกอย่างปลายน้ำรอตรงนี้

### สถานะจริงของแต่ละระบบ ณ 2026-08-28

| ระบบ              | มีอะไรแล้ว                                                                 | ขาดอะไร                                                                                |     |
| ----------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | --- |
| **ITEC**          | survey เสร็จ                                                               | —                                                                                      |     |
| **K2**            | สำรวจฐานจริงครบ 542 ตาราง · data dictionary · query cookbook · กติกาธุรกิจ | เอกสารยืนยันจาก MIS-Fintech · null rate จริงรายคอลัมน์                                 |     |
| **ITOS**          | schema wiki 55 ตาราง                                                       | ยังไม่ได้ต่อฐานเอง · ไม่รู้ว่ายัง update อยู่ไหม                                       |     |
| **CRM**           | พจนานุกรมข้อมูล 3 ตารางจากทีม CRM                                          | **ยังไม่มี connection** · ไม่รู้ DBMS · `pdpa_consent` เป็น JSON ที่ยังไม่รู้โครงสร้าง |     |
| **GI Core / EV7** | `schema.prisma` 166 models · เอกสารเทียบ 88 โมดูล                          | ยังไม่ได้ต่อฐาน · ไม่รู้ว่า Ev7core กับ GI Core สัมพันธ์กันยังไง                       |     |
| อีก 6 ระบบ        | —                                                                          | ยังไม่เริ่ม                                                                            |     |

---

## จากประชุม 26–27 ส.ค. 2026

| เรื่อง | สถานะ | ไปดูต่อ |
|---|---|---|
| **Client VPN** | พร้อมเชื่อมต่อแล้ว · ถัดไปคือ full load เครื่อง 250 | [[2026-08-27 AWS Data Lake]] |
| **PDPA กับ AWS** | service ขั้นต่ำอยู่ที่ไทยทั้งหมด — ปิดประเด็นแล้ว ยกเว้น Macie/SNS | [[AWS Services]] |
| **QuickSight** | ยังไม่มีแผนเปิดที่ไทย — ต้องหาทางเลือก BI | [[Analytics & AI]] |
| **Schedule ETL** | 23:30 น. ทุกวัน | [[ETL & Spark]] |
| **K2 → ITOS** | ยังไม่เสร็จ · เป้าครบ 100% สิ้นปี 2026 · คู่ขนานถึง Q1/2027 | [[2026-08-27 UFUND K2 และ ITOS]] |
| **UFUND Student** | ยังต้องอยู่บน K2 ต่อ | [[K2 Overview]] |
| **NCB** | ห้ามเข้า S3 แบบละเอียด · เก็บได้เฉพาะ Indicator | [[Consent & PDPA]] |
| **D365 F&O** | **ไม่มีข้อมูลลูกค้า** — ตัดออกจาก Customer 360 | [[2026-08-26 ERP]] |

---

## เพิ่งรู้เมื่อ 2026-08-28 — มีผลต่อแผน

| เรื่อง                                                       | ผลกระทบ                                                                                              | ไปดูต่อที่                       |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- | -------------------------------- |
| **K2 อาจให้บริการธุรกิจ EV ด้วย** ไม่ใช่แค่ UFUND            | ถ้าจริง ตาราง `CONTRACT`/`INVOICE`/`REPAYMENT` มี 2 ธุรกิจปน — ต้องหาคอลัมน์แยก BU ก่อนออกแบบ Silver | [[EV China Benchmark]]           |
| **วันครบกำหนด 1/16 เป็นกติกาของ K2 เท่านั้น**                | สูตรที่ทำไว้ใช้กับ ITOS ไม่ได้                                                                       | [[ITOS Overview]]                |
| **เกณฑ์ OD6 ที่ production ใช้ หลวมกว่าที่เราออกแบบ**        | 608 ราย vs 208 ราย — ต้องตกลงว่าใช้เกณฑ์ไหนตอนออกหนังสือบอกเลิก                                      | [[OD6 Collection Delivery]]      |
| **CRM ผูกกับ ITEC ด้วย `itec_cuscode`**                      | ปิดคำถามเปิดเรื่องเส้นทาง identity                                                                   | [[CRM - Data Dictionary]]        |
| **K2 ไม่มีฟิลด์ PDPA ตรงๆ สักตัว**                           | ต้องให้ CRM เป็น system of record ของ consent                                                        | [[K2 Customer Field Survey]]     |
| **SQL union K2+ITOS ที่ใช้อยู่ ตัดที่อยู่เหลือ 30 ตัวอักษร** | ข้อมูลหายเงียบๆ ต้องแก้ก่อนเข้า pipeline                                                             | [[Collection Union (K2 + ITOS)]] |
| **ได้แบบฟอร์ม VPN แล้ว**                                     | เดินเรื่องเชื่อม on-prem ↔ AWS ได้ · 🔒 มี PSK ในไฟล์                                                | [[Network & VPN]]                |

---

## เพิ่งรู้เมื่อ 2026-09-02 (แจ้งด้วยวาจา ยังไม่มีเอกสารยืนยัน)

| เรื่อง | ผลกระทบ | ไปดูต่อที่ |
|---|---|---|
| **ฐานข้อมูล ICI (iCare Insurance) อยู่บน P&O และจะย้ายไป IDS (K2) on-premise** เพราะ P&O ต้องจ่าย subscription | เป็นคำตอบแรกของคำถาม "iCare รันบนระบบอะไร" · **อย่าเพิ่ง ingest จาก P&O** เพราะจะต้องทำใหม่หลังย้าย · survey 1.1.6.1 ต้องนัดกับแผนย้าย | [[Other Systems]] · [[Source System Issues]] |

---

## Phase

ช่วงเวลาใน Timeline: **ส.ค. 2569 – ก.พ. 2570** (W1–W29)

| Phase           | มีอะไร                                                                                                  | สถานะ   |
| --------------- | ------------------------------------------------------------------------------------------------------- | ------- |
| 1. Survey       | Main System (1.1) + Other Legacy (1.2)                                                                  | **2/11** |
| 2. Summary      | สรุปผล survey                                                                                           | Todo    |
| AWS PoC         | Overview (Done) · Setup User · Demo/Workshop · Connect Database · Draft Plan · Weekly Meeting · Summary | กำลังทำ |
| AWS Pilot       | Synapse→AWS · ITEC replication · other sources · full data flow diagram · summary                       | Todo    |
| AWS Production  | Design & Planning · Implementation · Testing · Deploy · Maintain                                        | Todo    |
| Related Project | Customer Consent for Com7 Group                                                                         | Todo    |

Survey กับ PoC เดินคู่กัน

---

## Outstanding surveys

| ระบบ                 | ผู้รับผิดชอบ         |
| -------------------- | -------------------- |
| K2 (UFund)           | MIS-Fintech          |
| ITOS (UFund)         | K.Ton                |
| GI Core              | Punt, Nut            |
| D365                 | MIS-ERP              |
| **EV7**              | **ไม่มีชื่อในตาราง** |
| iCare Insurance      | P.Pui                |
| iCare / Smart Care   | P.Pui                |
| SAP B1               | K.Benz               |
| 7Club+/CRM           | P.Por                |
| Tech Trade           | K.Koj, K.Poj         |

EV7 เป็นระบบเดียวที่ตารางไม่ระบุผู้รับผิดชอบ

### What a survey must produce

จาก `datacleanplan.txt`:

> "นัดคุยเจ้าของข้อมูล แต่ละ BU สอบถาม/ทำความเข้าใจ/เก็บ Requirement
> วิเคราะห์ความแตกต่างของข้อมูลแต่ละ BU, แต่ละ BU ข้อมูลถูกเก็บไว้ที่ Source ใด
> เลือก Field ที่เกี่ยวข้อง, ที่ต้องการ
> วางแผน Data Ingestion / วิธีดึงข้อมูลจาก On-premises / Cloud / 365"

รายการที่ควรถามเพิ่ม `[อนุมาน]` — จากปัญหาที่เจอจริงในงาน K2/ITOS และ GI Core:

- มี `created_at` / `updated_at` ไหม → ถ้าไม่มี ดึง incremental ด้วย timestamp ไม่ได้ (K2 เจอปัญหานี้)
- match key ของลูกค้าเป็น nullable ไหม → GI Core `IdentityCard` เป็น nullable
- collation ของฐานข้อมูลคืออะไร → K2 กับ ITOS ใช้คนละแบบ ทำให้ union พัง
- มี RPA หรือ automation อะไรเชื่อมออกไปบ้าง → GI Core มี แต่ไม่มีเอกสาร
- มีข้อมูล consent ไหม

---

## PoC — eight issues

รีวิวโดย P'Max (AWS)

| #   | เรื่อง                                | สถานะ        |
| --- | ------------------------------------- | ------------ |
| 1   | เชื่อม Database ผ่าน Site-to-Site VPN | In Progress  |
| 2   | Malware scanning (GuardDuty)          | In Progress  |
| 3   | นิยาม Bronze/Silver/Gold + Glue Job   | In Progress  |
| 4   | Redshift จำเป็นใน Phase 1 ไหม         | Testing      |
| 5   | ออกแบบ S3 Bucket, Region, Schema      | In Progress  |
| 6   | QuickSight                            | **Complete** |
| 7   | Athena – Power BI                     | **Complete** |
| 8   | Migration จาก Azure Synapse → AWS     | In Progress  |

### 1 · Database connectivity

**⚠️ เปลี่ยนแนวทาง — ประชุม 24 ส.ค. 2026**

> **จะต่อผ่าน VPN Client โดย Vanguard แทน** (เดิมแผนคือ Site-to-Site VPN)

แนวทางเดิมตาม AWS Proposal คือ Site-to-Site VPN 30 encrypted tunnels บน Virtual Private Gateway

**บริบทก่อนหน้าที่ยังใช้ได้:**
> "ปัจจุบัน POC ยังเป็นการทดลองโดยนำ File Upload เข้า AWS แล้วทำ ETL จึงยังไม่ได้ทดสอบที่เชื่อมต่อกับ Database จริงโดยตรง ทำให้ยังไม่ทราบปัญหาที่อาจเกิดขึ้นจริง เช่น Network Latency, Throughput, Connection Stability, Firewall, Database Permission"

ยังไม่ได้ทดสอบต่อ database จริงเหมือนเดิม เปลี่ยนแค่วิธีเชื่อม

**สิ่งที่ยังไม่รู้เกี่ยวกับแนวทางใหม่:**

- Vanguard คือใคร/อะไร — vendor, product, หรือทีม
- เปลี่ยนเพราะอะไร
- เป็นการเปลี่ยนถาวร หรือใช้เฉพาะช่วง PoC
- Site-to-Site VPN 30 tunnels ใน proposal ยกเลิกหรือเลื่อน
- **VPN Client รองรับ pipeline ที่ต้องเชื่อมต่อเนื่อง (เช่น DMS CDC) ยังไงบ้าง** — Client VPN โดยทั่วไปออกแบบมาให้ client ต่อเข้าเครือข่าย ต่างจาก Site-to-Site ที่เชื่อมเครือข่ายถึงเครือข่ายแบบเปิดค้างไว้ `[อนุมาน]`
- ยังต้องพิจารณา Direct Connect ในอนาคตไหม

→ [[Open Questions & Risks]] · [[Decisions]] D-12

### 2 · GuardDuty

> "หาก Scan ข้อมูลทุก Object อาจทำให้เกิด Cost เยอะ (แค่ Amazon Guard Duty) ก็ 3500 us ต่อเดือนแล้ว"

ข้อมูลส่วนใหญ่มาจาก internal database ผ่าน VPN ที่คุม network อยู่แล้ว แต่บันทึกเองก็ระบุว่า:

> "VPN ไม่ได้ทำหน้าที่ Scan Malware โดยตรง"

**แนวทาง:** ทำ Data Classification / Threat Model ก่อน แล้วประเมินเป็นราย source ว่าต้อง scan ทุก object ไหม

### 3 · Bronze/Silver/Gold

ยังไม่นิยามชัด ทำให้ออกแบบ Glue job ไม่ได้ → [[Architecture]]

### 4 · Redshift

> "เนื่องด้วยหากต้องการควบคุม cost และ Redshift เหมือนเป็นตัวเสริม ที่ทำให้ query เร็วขึ้น แต่จริงๆ สามารถใช้แค่ Athena ก็ได้ และอยู่ในช่วง POC และยังไม่ได้ทดสอบกับข้อมูลจริง"

เริ่มจาก `S3 → Iceberg + Parquet → Athena → BI` แล้วเก็บผล Query Runtime, Data Scanned, Query Cost, Concurrent Users, Dashboard Response มาเทียบ

**ติดที่:** รอ AWS setup Redshift demo

### 5 · S3 Bucket / Region / Schema

ยังไม่กำหนด structure → [[Architecture]]

### 6 · QuickSight — Complete

QuickSight ไม่มี region ในไทย ผลทดสอบพบว่า cross-region ทำให้ runtime, latency และค่าใช้จ่ายเพิ่มอย่างมีนัยสำคัญ โดยค่าใช้จ่ายส่วนใหญ่มาจาก **Amazon Q (AI chat ที่ user เขียน prompt ได้)**

**2 ทางเลือกที่บันทึกไว้:**
1. ใช้ Power BI ใน Phase 1 หรือจนกว่า QuickSight จะรองรับ Thailand Region
2. Replicate ข้อมูลไป region ที่รองรับ — ต้องพิจารณา PDPA เพิ่ม

ผลทดสอบ: [[Athena Benchmark]]

### 7 · Athena – Power BI — Complete

> "สามารถเชื่อมต่อได้แล้วผ่าน Athena ODBC โดยใช้ Access Key และ Secret Key ที่ admin สร้างให้"

### 8 · Azure Synapse → AWS

> "ปัจจุบันข้อมูลจาก SharePoint 365 / Azure Data Lake Storage ใช้ Azure Synapse ต้องทดสอบย้ายระบบมาใช้งาน AWS"
> "สำรวจการใช้งานระบบเดิมก่อนว่าใช้ Service และ Function ใดบ้าง จากนั้นนำมาเปรียบเทียบกับ AWS Services ที่เหมาะสม เช่น S3, Glue, Athena และ Redshift และออกแบบ Flow ใหม่"

---

## Pilot

ลำดับที่ Timeline ระบุ:

1. MS Synapse จาก D365 to AWS directly — tag `RPA/GLUE/AI AGENT`
2. ITEC Replicated Data to AWS directly — tag `INGEST`
3. Other Source Replicated Data to AWS directly (ตาม framework plan)
4. Design Full Data Flow Diagram (High-Level → Low-Level)
5. Summary Result

---

## Five-step plan from datacleanplan

> "1. สำรวจข้อมูลแต่ละ BU
> 2. Ingest และ Replicate ข้อมูลเข้าสู่ S3 — กำหนดโครงสร้าง Raw/Bronze/Silver/Gold, วางแผน Data Cleaning แต่ละ BU, สร้าง Glue
> 3. Standardize & Normalize Customer Data — mapping field ของแต่ละ BU, กำหนด Customer Matching/Deduplication
> 4. สร้าง Unified Customer Table — สร้าง Customer ID กลางใหม่, เก็บใน S3 (Gold)
> 5. Hyper-Personalization — ทำ Analytic/ML, สร้าง Dashboard"

หมายเหตุในแผน: **Consent PDPA อยู่ระหว่างขั้น 3 กับ 4 และแยกเป็นอีก task**

---

## Merging K2 and ITOS

ที่มา: ClickUp `K2 & ITOS Integrated Loan System.txt`

> "บริษัทมีเเผนที่จะรวม Data K2 ITOS มาเป็นระบบเดียว เพื่อง่ายต่อการวิเคราะห์ Data เป็นการสร้าง Full loan system ตั้งเเต่ APP In → Scoring → Approve → Collection → Close Case"

**เสร็จแล้ว:** Business Understanding · Data Understanding (ได้ data dic จาก K2 โดยพี่เนตร และ ITOS โดยพี่ต้น)
**กำลังทำ:** Data Preparation — clean ข้อมูลและออกแบบ table ที่รองรับทั้ง 2 ระบบ
**ถัดไป:** เตรียมรวม data เข้ามาในถังของพี่คอง

รายละเอียด: [[ITOS Overview]]

---

## GI + EV7 → 7Club

ที่มา: บันทึกประชุม 21 ส.ค. 2026

**ที่ประชุมสรุปว่า** ควร migrate และ clean data ก่อน แล้วค่อย integrate เพราะ data ยังไม่สะอาดและยังไม่ standardize เข้ากับ 7club

**รอ:** พี่โจ้เขียน requirement + ทำ data prep เบื้องต้น คาดว่าส่งได้หลังขาย iPhone 18 (Quarter 4)

รายละเอียด: [[EV Business]]

---

## What to do next

`[อนุมาน]` — เรียงจากสิ่งที่บล็อกคนอื่นมากที่สุด

1. **ปิด survey ให้ครบ** — เหลือ 10 ระบบ เป็นคอขวดของทุกอย่าง
2. **ทดสอบต่อ database จริงผ่าน VPN** — AWS เริ่ม 24 ส.ค. และยังไม่เคยทดสอบเลย
3. **ปิดนิยาม Raw/Bronze/Silver/Gold** — Glue job ออกแบบไม่ได้ถ้าไม่ปิด
4. **ส่งคำถาม cross-BU consent ให้ legal** — Gap Review จัดเป็นอันดับ 2 และยังไม่มีเจ้าของงาน
5. **หาเจ้าของ survey ของ EV7**

---

## Gap Review — top five

จากชีต Summary ของ Customer Data Gap Review:

| อันดับ | สิ่งที่ต้องเติม | ช่วงเวลาที่แนะนำ |
|---|---|---|
| 1 | Device Ownership Registry + SKU-level transaction | Phase 1 (0-3 เดือน) |
| 2 | Consent granularity + แผน cross-entity consent | Phase 1 (0-3 เดือน) |
| 3 | ระบุตำแหน่ง CDP / Customer 360 layer ให้ชัด | Phase 1 (0-3 เดือน) |
| 4 | Event taxonomy มาตรฐาน + Derived attributes | Phase 1-2 (0-6 เดือน) |
| 5 | Control group / holdout ใน measurement framework | Phase 2 (3-6 เดือน) |

---

## เชื่อมกับโน้ตอื่น

[[SSOT Roadmap]] · [[Architecture]] · [[Decisions]] · [[Open Questions & Risks]] · [[System Inventory]] · [[Glue Connectivity]]
