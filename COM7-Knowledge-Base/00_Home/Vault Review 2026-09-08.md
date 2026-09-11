# Vault Review — 2026-09-08

> รายงานตรวจทาน Obsidian vault ทั้งหมด (78 ไฟล์) โดยแบ่งอ่านเป็น 8 กลุ่มขนาน · READ-ONLY
> เป้าหมาย: ทำให้อ่านง่ายทั้งคนและ AI · กระชับ · ไม่มีความเห็นเกิน · รักษาข้อมูลจริง (data dictionary, ตาราง, SQL, ตัวเลข) ไว้ครบ

---

## สรุปผู้บริหาร (Executive Summary)

vault มี**คุณภาพดีโดยรวม** — เขียนจากการ query จริง มีตัวเลข/ตาราง/SQL ที่ตรวจสอบแล้ว จุดแข็งคือ Query Cookbook, Decisions, Glossary, Fee Policy จุดที่ต้องปรับปรุงคือ **ความซ้ำซ้อนข้ามไฟล์** และ **ไฟล์ที่ยาวเกินจนกลายเป็นบันทึกการทำงาน**

**ธีมปัญหาหลัก 6 ข้อที่พบทั่วทั้ง vault:**

| # | ธีม | ความรุนแรง | พบที่ |
|---|---|:---:|---|
| 1 | **Field table ซ้ำกันข้ามไฟล์** — Data Dictionary ควรเป็น single source แต่ Contract/Customer/Payment ต่างมี field table ซ้อน | 🔴 High | K2 group, Retail group |
| 2 | **ไฟล์ยาวเกิน = บันทึกการทำงาน** — เก็บ v1-v3 ที่เลิกใช้ปนกับของจริง | 🔴 High | OD6 Logic (70KB), Redshift, AWS Services |
| 3 | **`[อนุมาน]` tag กระจาย inline** — AI แยกไม่ออกว่าอันไหน fact อันไหนเดา | 🟡 Medium | เกือบทุกกลุ่ม |
| 4 | **Heading ผิดระดับ** — ใช้ `#` (H1) เป็น section separator ชนกับ title | 🟡 Medium | AWS Services, Other Systems, ITEC DD, Open Questions |
| 5 | **Format ไม่สม่ำเสมอ** — ไทย/อังกฤษปน, emoji priority ใช้ไม่มีระบบ, ตาราง 2 vs 3 คอลัมน์ | 🟢 Low | ทั่วไป |
| 6 | **wikilink อาจตาย + metadata/changelog ฝังกลางเนื้อหา** | 🟡 Medium | ทั่วไป |

---

## ไฟล์ที่ควรเรียบเรียงก่อน (จัดลำดับความสำคัญ)

### 🔴 High — ควรทำก่อน (8 ไฟล์)

| ไฟล์ | ปัญหาหลัก | แนวทาง |
|---|---|---|
| `K2 - OD6 Selection Logic` (70KB) | รวม v1-v4 ในไฟล์เดียว 997 บรรทัด | แยก v1-v3 ไป `(Archive)` เหลือแต่ v4 ที่ใช้จริง |
| `Current Status` | โครงสร้างแบน timestamp ล้าสมัย | ใส่ frontmatter `last_updated` + จัดลำดับ TL;DR→blocking→updates→PoC→roadmap |
| `Redshift` (31KB) | ทำ 4 หน้าที่ในไฟล์เดียว | แยกเป็น Setup + Permissions/Troubleshoot หรือใส่ TOC |
| `AWS Services` | ใช้ H1 ทุก section + ซ้ำกับ Architecture/Decisions/Glue | แก้เป็น H2 + ตัดส่วนซ้ำ → link |
| `SSOT Roadmap` | "Why these objectives" ซ้ำ 3 ไฟล์คำต่อคำ | ลบทั้ง section → link |
| `K2 - Contract & Account` | field table ซ้ำ Data Dictionary | ตัด field table → cross-ref DD |
| `K2 - Customer & Address` | identity keys + address block ซ้ำ DD | ตัดซ้ำ เก็บเฉพาะ trap + stats |
| `Collection Team Questions` | ตารางสัญญาซ้ำ 3 ครั้ง + emoji ล้น | รวมตาราง ลด emoji แยก 3 section |
| `K2 Issues` | 3 ทางเลือกซ้ำ Collection Team Q + field ซ้ำ DD | ตัดซ้ำ → link |
| `Open Questions & Risks` | H1 ผิดระดับ + risk เป็น paragraph | แปลง H2 + risk เป็นตาราง |
| `Other Systems` | H1 ผิดระดับทุก section | แก้เป็น H2 |
| `Analytics & AI` | BHV เป็น paragraph + quote ซ้ำครั้งที่ 4 | แปลง BHV เป็นตาราง ตัด quote |
| `UFUND in Customer 360` | ตาราง volume ซ้ำ 2 ครั้งในไฟล์เดียว | ลบซ้ำ |

### 🟠 Medium (ประมาณ 12 ไฟล์)
`Home` · `EV Business` · `CRM Overview` · `System Inventory` · `EV Systems` · `Architecture` · `ITEC - Data Dictionary` · `K2 - Data Dictionary` · `K2 - Payment & Invoice` · `K2 - Business Rules` · `K2 - Collection & OD` · `DMS Full Load Validation` · `Data Standardization & Quality` · `ITEC Data Requirement Survey` · `Customer Data Issues` · meeting `2026-08-27 AWS Data Lake` (มี factual error) · `2026-08-27 UFUND`

### 🟢 Low — ดีอยู่แล้ว แก้เล็กน้อย (ที่เหลือ)
`Glossary` · `Group Structure` · `Decisions` · `Network & VPN` · `Athena Benchmark` · `K2 - Query Cookbook` · `ITEC - Query Cookbook` · `K2 - Fee Policy` · `K2 - Master & Setup` · `K2 - Table Inventory` · `CRM - Data Dictionary` · `K2 Customer Field Survey` · `Customer Identity` · ฯลฯ

---

## ⚠️ ข้อผิดพลาดเชิงข้อเท็จจริงที่ต้องแก้ (ตรวจพบระหว่างรีวิว)

1. **`2026-08-27 AWS Data Lake.md`** — ระบุ "Macie **และ SNS** ไม่มีที่ไทย" แต่ `K2 Termination Automation` ยืนยันว่า **SNS มีที่ ap-southeast-7 แล้ว** → แก้ให้เหลือแค่ "Macie"
2. **`K2 - Table Inventory`** — section 1 หัวว่า "20 tables" แต่แสดง 18 แถว → ตรวจให้ตรง
3. **`UFUND in Customer 360`** — "200k-300k active" (ประชุม) ≠ "288,205 สัญญา" (probe) → ใส่ footnote อธิบายว่าคนละความหมาย
4. **`2026-08-27 UFUND`** — note "ต้องยืนยันวันที่จริง" ยังค้างตั้งแต่บันทึก

---

## ข้อเสนอปรับมาตรฐานทั้ง vault (ทำครั้งเดียว ใช้ได้ทุกไฟล์)

1. **`[อนุมาน]` → ระบบ icon 3 ระดับ**: ✅ ยืนยันจากฐานจริง / ⚠️ ต้องตรวจเพิ่ม / ❓ ยังไม่ทราบ — นิยามไว้ที่ [[Home]] หรือ [[Glossary]] แล้วใช้เหมือนกันทุกไฟล์ (ช่วย AI แยก fact/assumption)
2. **Heading**: title ไฟล์ = H1 (`#`) เดียว · section = H2 (`##`) · ห้ามใช้ H1 เป็น separator
3. **Field table = อยู่ที่ Data Dictionary ที่เดียว** — ไฟล์อื่นอ้าง `→ [[X - Data Dictionary]] § table` แทนการ copy
4. **Changelog/metadata**: ย้ายไป frontmatter (`last_updated:`) หรือ section ท้ายไฟล์ ไม่ฝังกลางเนื้อหา
5. **emoji**: ใช้เฉพาะที่มีความหมายเชิงระบบ (status icon) ไม่ใช้เป็นการตกแต่ง — เลิกใช้ 🔴🟠🟡 แบบสุ่ม
6. **แยก "runbook/debug log" ออกจาก "reference doc"** — เช่น Glue debug ควรเป็นไฟล์ log แยก ไม่ฝังใน Pipeline Issues

---

## รายละเอียดต่อกลุ่ม

> รายงานเต็มต่อไฟล์ของแต่ละกลุ่ม (คะแนน 1-5, ปัญหาเจาะจง, ข้อเสนอ) ถูกเก็บไว้ครบ — ด้านล่างเป็นสรุปหัวข้อของแต่ละกลุ่ม

### กลุ่ม 1 · Home + Business (7 ไฟล์)
- Glossary (4.5/5), Group Structure (4.5/5) — สะอาดสุด
- Current Status (3/5) 🔴 — entry point แต่โครงสร้างแบน, timestamp ล้าสมัย
- Home (4/5) 🟠 — index table ซ้ำหลายชุด, folder tree ซ้ำ
- EV Business (3.5/5) 🟠 — blockquote business rules ขัดกันเองยังไม่ resolve
- Retail (4/5) — ตัวเลข/แบรนด์ ซ้ำ Group Structure

### กลุ่ม 2 · K2 core (7 ไฟล์)
- Query Cookbook (4.5/5), Table Inventory (4.5/5) — ดีมาก
- Data Dictionary (4/5) — เป็น source of truth แต่ format ตารางไม่สม่ำเสมอ
- Contract & Account, Customer & Address (High 🔴) — field table ซ้ำ DD หนัก
- Payment & Invoice (4.5/5) — insight ดีมาก แต่ field ซ้ำ DD

### กลุ่ม 3 · K2 rules + ITOS (8 ไฟล์)
- Fee Policy (4.5/5) — ดีสุดในกลุ่ม
- OD6 Selection Logic (2.5/5) 🔴 — ไฟล์ปัญหาสุด รวม v1-v4 ควรแยก archive
- Business Rules, Collection & OD, Termination How-To — ซ้ำกันเรื่อง OD6 refresh/collector

### กลุ่ม 4 · Retail + EV + System (8 ไฟล์)
- ITEC Query Cookbook (4.5/5), CRM Data Dictionary (4.5/5) — ดีมาก
- Other Systems (High 🔴) — H1 ผิดระดับทุก section
- System Inventory / EV Systems (Medium) — K2 cross-BU note ซ้ำกัน
- ITEC Data Dictionary (4/5) — ใหญ่สุด 756 บรรทัด, H1 ผิด, PCI note ซ้ำทุก view

### กลุ่ม 5 · Data (6 ไฟล์)
- K2 Customer Field Survey (4/5), Customer Identity (4/5) — ดี
- UFUND in Customer 360 (3/5) 🔴 — ตาราง volume ซ้ำ 2 ครั้ง
- Data Standardization, ITEC Survey (3/5) — โครงสร้างปน evidence/method, PCI ซ้ำ Consent

### กลุ่ม 6 · Data Lake + ETL (13 ไฟล์)
- Decisions (4.5/5), Network & VPN (4.5/5), Collection Union (4.5/5) — ดีมาก
- Redshift (3.5/5) 🔴, AWS Services (3/5) 🔴 — ยาว/ซ้ำ/H1 ผิด
- Architecture (4/5) — ซ้ำ AWS Services เรื่อง Region/AZ

### กลุ่ม 7 · Project + Meeting + Reference (19 ไฟล์)
- K2+ITOS Integration (5/5), OD6 Collection Delivery (5/5), meeting notes, Athena Benchmark (5/5) — ดีมาก
- SSOT Roadmap (4/5) 🔴 — "Why" ซ้ำ 3 ไฟล์
- Analytics & AI (3/5) 🔴 — BHV เป็น paragraph, quote ซ้ำครั้งที่ 4
- ⚠️ 2026-08-27 AWS Data Lake — factual error เรื่อง SNS

### กลุ่ม 8 · Issues (10 ไฟล์)
- ITEC Issues (4/5), Issue Index (4/5) — ดี
- K2 Issues (3/5) 🔴, Collection Team Questions (3/5) 🔴, Open Questions & Risks (3/5) 🔴 — ซ้ำ/emoji ล้น/H1 ผิด
- Pipeline Issues (3/5) — debug log ควรแยกไฟล์

---

## เชื่อมกับโน้ตอื่น

[[Home]] · [[Current Status]] · [[Issue Index]]
