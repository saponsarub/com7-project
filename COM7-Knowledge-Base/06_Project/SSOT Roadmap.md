# SSOT Roadmap

เป้าหมายปลายทางของงานข้อมูลทั้งหมด และลำดับที่ต้องทำ

---

## The chain

```
Data Framework → Data Migration → Centralized Platform → SSOT
→ Customer 360 / CDP → Analytics / AI → Business Activation
```

**ตอนนี้อยู่ 2 ขั้นแรก** — framework เขียนแล้ว ([[Data Framework Scope]]) ส่วน migration กำลัง survey ระบบและทำ PoC ควบคู่กัน ([[Current Status|AWS Data Lake]])

---

## 13 objectives and their prerequisites

| # | เป้าหมาย | ขึ้นกับข้อ | อยู่ที่ไหนใน vault |
|---|---|---|---|
| 1 | รวมข้อมูลจากทุก BU | — | [[System Inventory]] |
| 1b | **แบบสำรวจฟิลด์รายแผนก** — input ของข้อ 3 และ 6 | 1 | [[ITEC Data Requirement Survey]] · [[iCare Insurance (ICI)]] · [[K2 Customer Field Survey]] |
| 2 | สร้างสถาปัตยกรรมกลาง | 1 | [[Architecture]] |
| 3 | สร้าง **SSOT** | 2 | [[Customer Identity]] |
| 4 | **Standardize** ข้ามทุก BU | 1 | [[Data Standardization & Quality\|Data Standardization]] |
| 5 | ยกระดับ Data Quality | 4 | เหมือนข้อ 4 |
| 6 | แก้ปัญหา **ลูกค้าซ้ำ** | 4, 5 | [[Customer Identity]] |
| 7 | **Customer 360** | 3, 6 | เหมือนข้อ 6 |
| 8 | รองรับ **CDP** | 7 | เหมือนข้อ 6 |
| 9 | Segmentation | 7 | [[Analytics & AI]] |
| 10 | **Hyper-personalization** | 7, 8 | เหมือนข้อ 9 |
| 11 | **Cross-selling** | 7 | เหมือนข้อ 9 |
| 12 | Personalized promotion | 8, 10 | เหมือนข้อ 9 |
| 13 | ค้นหาโอกาสธุรกิจใหม่ | ทั้งหมด | — |

**ข้อ 9–13 อยู่ปลายน้ำของข้อ 6 และ 7 ทั้งหมด** — ถ้าข้ามการแก้ identity ไปทำ segmentation เลย จะได้ segment ที่สร้างบนลูกค้าซ้ำ `[อนุมาน]`

---

## Why these objectives

**AWS Proposal:**
> "data is currently fragmented across disparate systems, on-premises data centers, and third-party cloud providers. This fragmentation limits the group's ability to perform consolidated analytics, enterprise reporting, and AI-driven decision-making."

**บันทึกประชุม GI+EV7 (21 ส.ค. 2026)** — เหตุผลเชิงพาณิชย์ที่ชัดที่สุด:
> "ลูกค้าที่ซื้อ/เช่ารถไฟฟ้าที่เป็นสินค้าที่มีมูลค่าสูง ซึ่งลูกค้ากลุ่มนี้ เป็นกลุ่มที่มีโอกาสสร้างมูลค่าเพิ่มได้ หากได้รับ benefit เพิ่มเติมจาก 7club เช่นลูกค้าที่ซื้อหรือเช่าซื้อรถไฟฟ้า Aion สามารถนำไป cross sale กับ product ของ banana/studio7/ufund ได้"

> "การเพิ่ม benefit ของ 7club ให้กับลูกค้า EV7&GI ยังสอดคล้องกับเเนวทางของ คุณปอน CBO ในการสร้าง data integration ภายในเครือ COM7 ซึ่งจะนำไปสู่ customer ecosystem"

คู่ที่บันทึกไว้: **GI จับกับ Banana** · **EV7 จับกับ Thunder FinFin**

---

## Five steps to SSOT

จาก `datacleanplan.txt`:

> "1. สำรวจข้อมูลแต่ละ BU
> 2. Ingest และ Replicate ข้อมูลเข้าสู่ S3 — กำหนดโครงสร้าง Raw/Bronze/Silver/Gold, วางแผน Data Cleaning แต่ละ BU, สร้าง Glue
> 3. Standardize & Normalize Customer Data — mapping field ของแต่ละ BU, กำหนด Customer Matching/Deduplication
> 4. สร้าง Unified Customer Table — สร้าง Customer ID กลางใหม่, เก็บใน S3 (Gold)
> 5. Hyper-Personalization — ทำ Analytic/ML, สร้าง Dashboard"

**หมายเหตุสำคัญในแผน:** Consent PDPA อยู่ระหว่างขั้น 3 กับ 4 และ **แยกเป็นอีก task**

```
Ingest → Clean แต่ละ BU → Standardize → [CONSENT] → Unified Customer Table → Hyper-Personalization
```

Gate อยู่**ก่อน**สร้าง unified customer table

---

## Current state

### Data is scattered

ฐานข้อมูลที่พบจาก SQL ที่ทีมใช้งานจริง:
`HPCOM7` · `ILOAN_COLLECTION` · `ILOAN_DATASOURCE` · `D365FO_DATALAKE` · `syndpdev001` · `PROJECT_1` · `TAN_MIS`
บวก MySQL ของ GI Core, Azure Data Lake Storage, SharePoint 365

### Overlapping systems on the EV side

> "มีฐานข้อมูลซ้ำซ้อนจากการพัฒนาระบบหลายช่วงเวลาและ Data Source กระจายหลายระบบ"

5 ระบบทับกัน: D365 (GI เก่า) · GI CORE (ปัจจุบัน) · AION DMS · EV7CORE · EVTRACKING

### Data is not standardized

พิสูจน์แล้วจากคิวรี่ union K2/ITOS → [[Data Standardization & Quality]]

### CRM covers ITEC only

→ [[Data Framework Scope]] § Customers

---

## Distance from the goal

| เป้าหมาย | ปัจจุบัน |
|---|---|
| SSOT ทั้งกลุ่ม | กระจาย 11+ ระบบ · survey เสร็จ 1 |
| Customer 360 | มีแค่ทะเบียนลูกค้า (Gap Review: 9 มี / 17 ไม่พอ / 62 ขาด จาก 88) |
| CRM ทั้งกลุ่ม | ITEC อย่างเดียว |
| Hyper-personalization | batch campaign ผ่าน Braze |
| AI/ML | ยังไม่เริ่ม และไม่มี phase ไหนใน Timeline ครอบคลุม |

---

## เชื่อมกับโน้ตอื่น

[[Data Framework Scope]] · [[Current Status|AWS Data Lake Status]] · [[Customer Identity]] · [[System Inventory]]
