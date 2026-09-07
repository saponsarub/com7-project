# COM7 Data Knowledge Base

บันทึกงานข้อมูลของ **บริษัท คอมเซเว่น จำกัด (มหาชน)** — โครงการ Centralized Data Lake / SSOT

**โน้ตระบบต้นทางแยกโฟลเดอร์ตามธุรกิจ** · ชื่อไฟล์ขึ้นต้นด้วยชื่อระบบ เช่น `K2 - Data Dictionary`

---

## หาอะไร เปิดตรงไหน

### ระบบต้นทาง — `02_System`

| อยากรู้ | เปิด |
|---|---|
| ระบบไหนเก็บอะไร ใครดูแล | [[System Inventory]] |
| **ฟิลด์ใน K2 หมายถึงอะไร** | [[K2 - Data Dictionary]] |
| ตาราง K2 มีอะไรบ้าง ตัวไหนใช้จริง | [[K2 - Table Inventory]] · [[K2 Overview]] |
| **ขอที่อยู่ / ชื่อ / สัญญาของลูกค้า K2** | [[K2 - Query Cookbook]] |
| ลูกค้าและที่อยู่เก็บยังไง | [[K2 - Customer & Address]] |
| สัญญาและบัญชี | [[K2 - Contract & Account]] |
| ใบแจ้งหนี้และการรับชำระ | [[K2 - Payment & Invoice]] |
| งานติดตามหนี้ / OD | [[K2 - Collection & OD]] |
| รหัสสถานะ · จังหวัด · แบรนด์ | [[K2 - Master & Setup]] |
| **ฟิลด์ใน CRM / ระบบสมาชิก** | [[CRM - Data Dictionary]] · [[CRM Overview]] |
| **ฟิลด์ใน ITEC (ค้าปลีก)** | [[ITEC - Data Dictionary]] |
| **ดึงยอดขาย / หาสินค้า / หาสาขา ITEC** | [[ITEC - Query Cookbook]] |
| ระบบค้าปลีก ITEC | [[ITEC Overview]] |
| ระบบสินเชื่อ ITOS | [[ITOS Overview]] |
| ระบบฝั่ง EV | [[EV Systems]] |
| ระบบที่ยังรู้น้อย (D365 · SAP B1 · iCare · Tech Trade · Synapse) | [[Other Systems]] |

### ธุรกิจ — `01_Business`

| อยากรู้ | เปิด |
|---|---|
| กลุ่ม COM7 มีบริษัท / ธุรกิจ / แบรนด์อะไรบ้าง | [[Group Structure]] |
| ธุรกิจเช่าซื้อ UFUND | [[UFUND]] |
| ธุรกิจค้าปลีก | [[Retail]] |
| ธุรกิจ EV | [[EV Business]] |

### กฎและงานประจำ

| อยากรู้ | เปิด |
|---|---|
| กติกาธุรกิจของ K2 (OD · สถานะ · การนับงวด) | [[K2 - Business Rules]] |
| ค่าเบี้ยปรับ / ค่าติดตามคิดยังไง | [[K2 - Fee Policy]] |
| **คัดสัญญาเพื่อบอกเลิก** ยังไง | [[K2 - OD6 Selection Logic]] |
| ไฟล์ OD6 ที่ส่งทีมติดตามจริง | [[OD6 Collection Delivery]] |
| **ทำงานออกหนังสือบอกเลิกให้อัตโนมัติบน AWS** | [[K2 Termination Automation]] |
| กรอกหนังสือบอกเลิกสัญญา เอาข้อมูลจากไหน | [[K2 - Termination Letter Mapping]] |

### ข้อมูลและ Data Lake — `03_Data` · `04_DataLake` · `05_ETL`

| อยากรู้ | เปิด |
|---|---|
| ลูกค้าซ้ำ แก้ยังไง | [[Customer Identity]] |
| PDPA / consent | [[Consent & PDPA]] |
| ข้อมูลแต่ละระบบไม่เป็นมาตรฐานเดียวกัน | [[Data Standardization & Quality]] |
| ฟิลด์ลูกค้าที่ต้องการ มีใน K2 ไหม | [[K2 Customer Field Survey]] |
| ฟิลด์ค้าปลีกที่ต้องการ มีใน ITEC ไหม | [[ITEC Data Requirement Survey]] |
| UFUND เข้า Customer 360 ยังไง | [[UFUND in Customer 360]] |
| สถาปัตยกรรม AWS | [[Architecture]] · [[AWS Services]] |
| **เริ่มใช้ Redshift ยังไง · โหลดจาก S3 · ให้สิทธิ์ยังไง** | [[Redshift]] |
| **ตั้ง Glue Crawler ยังไงไม่ให้ตารางแตก · วางโครงสร้าง S3** | [[Glue Crawler]] |
| เชื่อมเครือข่าย on-prem ↔ AWS | [[Network & VPN]] |
| เขียน Glue job ยังไง | [[ETL & Spark]] |
| รวมข้อมูล collection K2 + ITOS | [[Collection Union (K2 + ITOS)]] |
| **แพ็ก Lambda ยังไง ทำไมต้อง build บน Linux** | [[Google Sheet to S3 (Lambda)]] |
| อ่านโค้ด Lambda ทีละฟังก์ชัน | `docs/googlesheet-to-s3.md` → [[Google Sheet to S3 - Code Walkthrough]] |
| **flow เต็ม + แผนล่วงหน้าของ pipeline ชีต** | [[Google Sheet Pipeline]] |

### สถานะ · ปัญหา · อ้างอิง

| อยากรู้ | เปิด |
|---|---|
| ตอนนี้โครงการถึงไหน | [[Current Status]] |
| ตกลงอะไรไปแล้ว | [[Decisions]] |
| **ติดอะไรอยู่ ใครต้องตอบ** | [[Issue Index]] |
| ความเสี่ยงระดับโครงการ | [[Open Questions & Risks]] |
| ศัพท์นี้แปลว่าอะไร | [[Glossary]] |
| ใครดูแลอะไร | [[People & Teams]] |
| ข้อมูลใน vault มาจากไหน | [[Source Inventory]] |
| **library ไหนใช้ทำอะไร · เลือกยังไง** | [[Python Libraries]] |
| **ใช้ git/GitHub ยังไง · SSH 2 บัญชี · แก้ตอน push ไม่ผ่าน** | [[Git & GitHub]] |
| บันทึกประชุม | [[Meeting Index]] |
| ของเก่าที่เลิกใช้ | [[Archive]] |

---

## โครงสร้างโฟลเดอร์

```
00_Home/        Home · Current Status · Glossary
01_Business/    Group Structure · UFUND · Retail · EV Business
02_System/      System Inventory
                ├── UFUND (K2 + ITOS)/    K2 Overview · K2 - *.md (12) · ITOS Overview
                ├── Retail (ITEC + CRM)/  ITEC Overview · ITEC - Data Dictionary · ITEC - Query Cookbook
                │                         CRM Overview · CRM - Data Dictionary
                ├── EV/                   EV Systems
                ├── TBD/                  Other Systems
                └── _raw/                 ไฟล์ดิบ · sample ที่ mask แล้ว
03_Data/        Customer Identity · Consent & PDPA · Data Standardization · Customer 360 · K2 Field Survey
04_DataLake/    Architecture · AWS Services · Network & VPN · Decisions · Redshift · Glue Crawler
05_ETL/         ETL & Spark · Collection Union (K2 + ITOS) · Google Sheet to S3 (Lambda)
                Google Sheet to S3 - Code Walkthrough
06_Project/     K2 + ITOS Integration · GI + EV7 → 7Club · OD6 Collection Delivery
                Data Framework Scope · SSOT Roadmap · K2 Termination Automation
                Google Sheet Pipeline
07_Meeting/     บันทึกประชุม (ภาษาไทย)
08_Reference/   Source Inventory · People & Teams · SQL & Source Schemas · Python Libraries · Git & GitHub
                Analytics & AI · Athena Benchmark · EV China Benchmark
09_Issues/      คำถามที่ยังไม่มีคำตอบ · งานค้าง · ความเสี่ยง
99_Archive/     ของเก่าที่เลิกใช้แล้ว
```

| ธุรกิจ | ระบบต้นทาง | โฟลเดอร์ |
|---|---|---|
| [[UFUND]] — เช่าซื้อ IT | K2 · ITOS | `02_System/UFUND (K2 + ITOS)/` |
| [[Retail]] — ค้าปลีก IT | ITEC · CRM | `02_System/Retail (ITEC + CRM)/` |
| [[EV Business]] — รถไฟฟ้า | Ev7core · Ev7 tracking · GI Core · 365 · **K2** | `02_System/EV/` |
| ยังไม่ระบุ | D365 · SAP B1 · iCare · Tech Trade · Synapse | `02_System/TBD/` |

> **K2 อยู่ 2 ธุรกิจ** — ไฟล์เก็บไว้ใต้ UFUND เพราะเป็นเจ้าของหลัก แต่ทำใบแจ้งหนี้/บิลค้าง/ค่าปรับจราจรให้ EV ด้วย → [[EV Systems]]

---

## กติกาการเขียนโน้ต

| กติกา | หมายความว่า |
|---|---|
| **โน้ตความรู้เก็บเฉพาะเนื้อหา** | คำถามที่ยังไม่มีคำตอบ · สถานะงาน · ใครรับผิดชอบ → ไปที่ `09_Issues` |
| **บอกที่มาได้เสมอ** | ข้อความปกติ = มาจากเอกสาร/ฐานข้อมูลจริง · `[อนุมาน]` = สรุปเอง |
| **ไม่มีหลักฐาน เขียนว่าไม่รู้** | ห้ามเดา |
| **ภาษา** | ชื่อไฟล์และหัวข้อเป็นอังกฤษ · คำอธิบายเป็นไทย · บันทึกประชุมเป็นไทยทั้งหมด |
| **ทุกโน้ตต้องมีลิงก์เข้าและออก** | จบด้วยหัวข้อ "เชื่อมกับโน้ตอื่น" |

> **บทเรียน:** vault เวอร์ชันแรกมีข้อมูลผิดเพราะไปอ้างไฟล์สรุปที่ AI เขียนเอง ทำให้ตัวเลขอย่าง "1,000 สาขา" หลุดเข้ามาทั้งที่ไม่มีในเอกสารจริง — **อ้างเฉพาะเอกสารต้นทาง**

---

## ตัวเลขที่ยืนยันแล้ว

| | ค่า | ที่มา |
|---|---|---|
| Region เป้าหมาย | ap-southeast-7 (Bangkok) | AWS Proposal |
| ขนาด lake | 30 TB | AWS Proposal |
| ข้อมูลเข้า / ออก | ~50 GB/วัน · ~1 TB/วัน | AWS Proposal |
| Pipeline | ~30 เส้น | AWS Proposal |
| Survey เสร็จ | 2 จาก 11 ระบบ (ITEC · K2) | Project Timeline |
| view ใน ITEC (ฐาน MIS) | 23 view · 297 คอลัมน์ · ไม่มี table | probe ฐานจริง 2026-08-28 |
| บรรทัดขายใน ITEC | 79,828,304 (2025-01 → 2026-08) | probe |
| สาขาใน ITEC | 3,205 · สินค้า 216,009 | probe |
| ตาราง K2 | 542 ตาราง · 165 view · FK 16 ตัว | probe ฐานจริง 2026-08-26 |
| สัญญาใน K2 | 288,205 | probe |
| เลขบัตรไม่ซ้ำใน K2 | 343,249 (จาก 404,627 แถว) | probe |
| สมาชิก CRM | ~8,000,000 · 7Club+ ~800,000 | เอกสารทีม CRM |
| ลูกค้าใน ITOS | 165,722 | schema wiki |
| ความพร้อมฟิลด์ลูกค้าใน K2 | 69 มี / 4 ทดแทนได้ / 25 ขาด (จาก 98) | [[K2 Customer Field Survey]] |
| ช่วงเวลาโครงการ | ส.ค. 2569 – ก.พ. 2570 | Project Timeline |

---

## ข้อมูลอ่อนไหว

- ห้าม commit ไฟล์ที่มี PII (ชื่อ · เลขบัตร · ที่อยู่ · เบอร์โทร) — `.gitignore` กัน `*.xlsx` `*.csv` ไว้แล้ว
- ห้ามเก็บรหัสผ่าน / Pre-Shared Key ในโน้ต — ใช้ env var หรือ AWS Secrets Manager
- ตัวอย่างข้อมูลใน `02_System/_raw/` ผ่านการ mask แล้ว
