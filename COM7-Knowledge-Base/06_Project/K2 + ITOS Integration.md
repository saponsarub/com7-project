# K2 + ITOS Integration

**สถานะ:** Data Preparation
**ที่มา:** ClickUp `K2 & ITOS Integrated Loan System.txt` + `UFF/` ใน `C:\Projects\Data-Team-Code\` + **ประชุม 2026-08-27**

> **อัปเดต 2026-08-28** — SQL union ที่ใช้อยู่จริง (58 คอลัมน์) → [[Collection Union (K2 + ITOS)]]
> ความต่างเชิงธุรกิจที่ต้องแก้ก่อนรวม: เลขสัญญา `TFF` vs ตัวเลข · วันครบกำหนด 1/16 vs หลากหลาย

> **มติเรื่องทิศทางระบบและ Customer 360** → [[UFUND in Customer 360]]

> ข้อมูลของตัวระบบเอง (schema, ตาราง, field) อยู่ที่ [[ITOS Overview]]

---

## Goal

> "บริษัทมีเเผนที่จะรวม Data K2 ITOS มาเป็นระบบเดียว เพื่อง่ายต่อการวิเคราะห์ Data เป็นการสร้าง Full loan system ตั้งเเต่ APP In → Scoring → Approve → Collection → Close Case"

ปัจจุบันวงจรสินเชื่อถูกแยกอยู่คนละระบบที่สร้างคนละยุค จึงไม่มีมุมมองสัญญาแบบครบวงจร `[อนุมาน]`

---

## Progress

**Task Done**
- Business Understanding
- Data Understanding — ขอ data dic และทำความเข้าใจจากทั้ง K2 (พี่เนตร) และ ITOS (พี่ต้น)

**Task In Progress**
- Data Preparation — กำลัง clean ข้อมูล และออกแบบ table ที่รองรับทั้ง 2 ระบบ
- เตรียมรวม data เข้ามาในถังของพี่คอง

---

## Direction agreed in the 2026-08-27 meeting

**ITOS คือปลายทาง · K2 คือระบบที่กำลังถูกเลิกใช้** — ไม่ใช่สองระบบคู่ขนานอย่างที่เคยเข้าใจ

| | |
|---|---|
| ยุคแรก | UFUND ใช้ **K2** เป็นระบบหลัก |
| บริษัทโตขึ้น | เปลี่ยนมาใช้ **iLoan บน ITOS** เป็นระบบหลัก |
| ปัจจุบัน | migration **ยังไม่เสร็จ** ข้อมูลอยู่ทั้งสองที่ |
| **เป้าหมาย** | **migrate ครบ 100% ภายในสิ้นปี 2026** |
| ข้อยกเว้น | **UFUND Student** อาจอยู่บน K2 ต่อ |

**หลักฐานจากฐานที่สนับสนุน** — สัญญาใหม่ใน K2 ปี 2024 = 81,476 · ปี 2025 = 102,809 · **ปี 2026 ถึง ส.ค. = 16,567** ตกลงเหลือ ~16% ของปีก่อน

> ⚠️ **มีผลต่อแผน lake** — ถ้า K2 ปิดสิ้นปี 2026 pipeline จาก K2 ควรคิดเป็น **historical load ครั้งเดียว** ไม่ใช่ pipeline ที่ต้องดูแลระยะยาว `[อนุมาน]`

---

## Three-phase migration plan

```
ช่วงที่ 1:  K2 ──┐
                 ├──► Unified
            ITOS ─┘

ช่วงที่ 2:  K2 ──────► Unified
            ITOS ────► Unified
                         │
                         ▼
                  ตรวจสอบข้อมูล
                         │
                         ▼
                K2 ค่อย ๆ ลดการใช้งาน

ช่วงสุดท้าย: K2 ──X
            ITOS ─────────► Unified
```

---

## Two build plans

ทั้งคู่เริ่มเหมือนกัน:

> "Schema Mapping (ในexcel) เช็ค column /datatype ให้ตรงกัน (ปรับ Column / Data Type ใหม่)"

| | UnionPlan1 | UnionPlan2 |
|---|---|---|
| หลังจาก mapping | "Direct Union From 2 database" → "Insert into (Create new table)" | **"create Schema เปล่าๆ มา กำหนด datatype ใหม่, pkใหม่ (ID) เพิ่ม column ระบุว่า migrate มาจากไหน"** → "Insert data จากทั้ง 2 table เข้า new table (Union) ทีละ table" |
| ต่อไป | Stored Procedure Incremental → กำหนด schedule Update/Insert | เหมือนกัน |

**UnionPlan2 ดีกว่าตรงที่** schema เป้าหมายถูกออกแบบตั้งใจ ไม่ใช่สืบทอดจาก source ที่รันก่อน · มีคอลัมน์ระบุที่มา · ทำทีละ table validate ง่ายกว่า `[อนุมาน]`

---

## Queries already written

`K2_U_ITOS_P1.sql` — union จริงที่รันได้

```sql
SELECT <คอลัมน์ที่ CAST/COLLATE แล้ว>, 'ITOS' as SOURCE_SYSTEM
FROM [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[dbo].[ITOS_COLLECTION_DETAIL] a
UNION ALL
SELECT <คอลัมน์ที่ map กัน>, 'K2' as SOURCE_SYSTEM
FROM HPCOM7.dbo.COLLECTION_OD_ASSIGNMENT b
```

คอลัมน์ `SOURCE_SYSTEM` implement แล้วจริง — ตรงกับหลักการที่ตกลงในงาน customer identity ด้วย ([[Decisions|D-07]])

**Domain ที่ record รวมครอบคลุม:** contract · financial · schedule · ค้างชำระ · assignment · **ข้อมูลลูกค้า** (วันเกิด โทร ชื่อ ที่อยู่ 3 แบบ อาชีพ) · product · **ผู้ค้ำประกัน**

---

## Problems this query exposed

สรุป — รายละเอียดเต็มอยู่ที่ [[Data Standardization & Quality]]

- สะกดต่างกัน: `TOTAL_PRINCIPAL` (ITOS) vs `TOTAL_PRINCIPLE` (K2)
- typo ใน production: `PRODUCT_ID` vs `PRODUDCT_ID`
- ชื่อต่างความหมายเดียวกัน: `PRODUCT_NAME` vs `MODEL_NAME`
- ต้อง `CAST` เกือบทุกคอลัมน์
- ต้อง `COLLATE DATABASE_DEFAULT` ทุกคอลัมน์ข้อความ
- K2 ไม่มี `PRODUCT_MODEL`, `PRODUCT_SERIAL_NO`, `CREATE_DATE`, `MODIFY_DATE`
- ที่อยู่คนละโครงสร้าง — K2 เก็บ 3 คอลัมน์ / ITOS แยกตาราง `S_CUSTADDR`

---

## Relationship to the AWS work

> **2026-11-10:** งาน lake ย้ายจาก AWS มาเป็นเครื่อง PC + MySQL ([[Decisions|D-21]]) — ความสัมพันธ์ด้านล่างยังเหมือนเดิม

โปรเจกต์นี้อยู่**เหนือน้ำ**ของงาน lake — รวมที่ต้นทางก่อน แปลว่า lake จะ ingest ระบบสินเชื่อที่สะอาดหนึ่งระบบ แทนสองระบบที่ขัดกัน `[อนุมาน]`

และเป็นการซ้อมที่ดี เพราะปัญหา standardization ที่เจอตรงนี้เป็นชนิดเดียวกับที่อีก 10 ระบบจะมี `[อนุมาน]`

---

## เชื่อมกับโน้ตอื่น

[[UFUND in Customer 360]] · [[ITOS Overview]] · [[Data Standardization & Quality]] · [[SQL & Source Schemas]]
