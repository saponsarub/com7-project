# System Inventory

อัปเดต 2026-08-24 · ที่มา: `D:\Project Timeline _ Data Team.xlsx` + เอกสารประกอบ

**ห้ามเดาใส่ช่องว่าง** ไม่รู้ให้เขียนว่าไม่รู้

---

## Survey status

จาก Project Timeline — แบ่งเป็น Main System (1.1) กับ Other Legacy System (1.2)

| Ref | ระบบ | สถานะ | ผู้รับผิดชอบ |
|---|---|---|---|
| 1.1.1 | [[ITEC Overview]] | **Done** | Data Team |
| 1.1.2.1 | [[K2 Overview\|K2]] (UFund) | **Done** (survey ฐานจริง 2026-08-26) | MIS-Fintech |
| 1.1.2.2 | [[ITOS Overview\|ITOS]] (UFund) | **ตอบแบบสำรวจฟิลด์ลูกค้าแล้ว 2026-09-04** (53 มี · 31 ทดแทน · 14 ไม่มี) | K.Ton |
| 1.1.3 | [[EV Business\|GI Core]] | Todo | Punt, Nut |
| 1.1.4 | [[Other Systems\|D365]] | Todo | MIS-ERP |
| 1.1.5 | [[EV Business\|EV7]] | Todo | **ไม่มีชื่อในตาราง** |
| 1.1.6.1 | [[iCare Insurance (ICI)\|iCare]] — Insurance | Todo | P.Pui |
| 1.1.6.2 | [[Smart Care Service\|iCare / Smart Care]] — Mobile Service | Todo | P.Pui |
| 1.1.7 | [[Other Systems\|SAP B1]] | Todo | K.Benz |
| 1.2.1 | [[CRM Overview\|7Club+/CRM]] | **มี data dictionary แล้ว 2026-08-28** (3 ตาราง 61 ฟิลด์) · เหลือ coverage | P.Por |
| 1.2.2 | [[Other Systems\|Tech Trade]] | Todo | K.Koj, K.Poj |

**เสร็จ 2 จาก 11** — งานนี้เป็นคอขวดของทุกอย่าง

> K2 เลื่อนจาก In-Progress เป็น Done เพราะสำรวจฐาน `HPCOM7` โดยตรงครบ 542 tables เมื่อ 2026-08-26 ผลอยู่ที่ [[K2 Overview]] — **ยังไม่มีเอกสารจาก MIS-Fintech ยืนยัน** สถานะนี้อ้างจากการสำรวจของทีมเราเอง

---

## System table

| ระบบ | ธุรกิจ | ทำอะไร | สถานะ | ที่มา |
|---|---|---|---|---|
| [[ITEC Overview]] | ค้าปลีก IT | ฐาน MIS บน **SQL Server 2025** · เปิดให้เห็นเฉพาะ **23 view · 297 คอลัมน์ ไม่มี table** · star schema พร้อมชั้น clean · บรรทัดขาย 79.8M · สาขา 3,205 · สินค้า 216,009 | **Confirmed** | survey ฐานจริง 2026-08-28 · ความพร้อมฟิลด์ **39/77 มี · 4 ทดแทน · 21 ไม่มี · 13 ไม่ตอบ** |
| [[K2 Overview\|K2]] | สินเชื่อเช่าซื้อ IT **(legacy — ปิดสิ้นปี 2026)** | ฐาน `HPCOM7` · **542 tables · 288,205 สัญญา · 343,249 เลขบัตรไม่ซ้ำ** · กลุ่มหลักคือนักศึกษา | **Confirmed** | survey ฐานจริง 2026-08-26 |
| [[ITOS Overview\|ITOS]] | สินเชื่อ (collection) | `ILOAN_COLLECTION` 55 tables · ลูกค้า 165,722 ราย | Confirmed | schema wiki |
| [[EV Business\|GI Core]] | EV / AION | ระบบหลักปัจจุบันฝั่ง GI · MySQL 166 Prisma models | Confirmed | schema.prisma · ClickUp |
| [[Other Systems\|D365]] | ERP / GI เก่า | ข้อมูลผ่าน `D365FO_DATALAKE` | To Verify | Timeline · SQL |
| AION DMS | GI | ระบบ vendor — บันทึกประชุมเขียนว่า "ของจีน" | To Verify | ClickUp |
| EV7CORE | EV7 | ระบุเป็นระบบแยกในปัญหาข้อมูลซ้ำ | To Verify | ClickUp |
| EVTRACKING | EV7 / GI | ยังมีบางรายการของ GI ค้างอยู่หลังโอนไป EV7 | To Verify | ClickUp |
| [[iCare Insurance (ICI)]] | ประกันวินาศภัย | บริษัทประกัน · 8 ผลิตภัณฑ์ · คนละธุรกิจกับศูนย์ซ่อม | Confirmed | เว็บทางการ 2026-09-09 |
| [[Smart Care Service]] | บริการหลังการขาย | **iCare = Apple · Smart Care = ยี่ห้ออื่น** | To Verify | แจ้งวาจา 2026-09-11 |
| [[Other Systems\|SAP B1]] | ERP | ไม่รู้ว่า BU ไหนใช้ | To Verify | Timeline |
| [[CRM Overview\|7Club]] | membership | โปรแกรมสมาชิก · survey รวมกับ CRM | To Verify | Timeline · Data Framework |
| [[CRM Overview\|CRM]] | ลูกค้า / แคมเปญ | ครอบคลุมแค่ ITEC · ส่งต่อให้ทีม CRM ใช้ Braze | Partially Confirmed | Data Framework |
| [[Other Systems\|Tech Trade]] | เทิร์นเครื่อง | ถือประวัติและสิทธิ์เทิร์น · **ไม่อยู่ใน brief เดิม** | To Verify | Timeline · Gap Review |
| [[Other Systems\|Azure Synapse]] | analytics เดิม | `syndpdev001` · รับจาก SharePoint 365 + ADLS · กำลังย้ายมา AWS | Confirmed (เป็น source ของ migration) | PDF ของ Alphametrics · PoC |
| [[CRM Overview\|Braze]] | ส่งข้อความ/แคมเปญ | ทีม CRM ใช้ทำ promotion และ loyalty | Confirmed | Data Framework |

---

## ระบบที่เพิ่งพบจากเอกสารเทียบระบบ EV (2026-08-28)

เอกสาร `สรุป Ev model china.xlsx` เปิดเผยระบบที่ยังไม่เคยอยู่ใน inventory นี้

| ระบบ | ทำอะไร | สถานะ |
|---|---|---|
| **Ev7core** | สัญญา · ลูกค้า · ลีด · คำสั่งซื้อ · สิทธิ์ผู้ใช้ · โครงสร้างพื้นฐาน — **API จากทุกโปรแกรมมารวมที่นี่** | To Verify |
| **Ev7 tracking** | ใบสั่งงาน · ตรวจสภาพรถ · ซ่อมบำรุง · background check | To Verify |
| **365** (Dynamics) | บัญชี · ต้นทุน · คลังรถ · แบรนด์/รุ่นรถ · BI | To Verify — น่าจะเป็นตัวเดียวกับ D365 `[อนุมาน]` |
| **Gtrack Smarth** | GPS tracking รถ | To Verify — เป็น time-series ขนาดใหญ่ ต้องประเมินก่อน ingest |
| **3CX** | ระบบโทรศัพท์ / เบอร์เสมือน | To Verify |
| **7chat** | แชทภายในองค์กร | To Verify |
| **ici** | ระบบประกันภัย (iCare Insurance) | To Verify — ตรงกับ 1.1.6.1 · **ฐานอยู่บน P&O จะย้ายไป IDS (K2) on-prem** (แจ้งด้วยวาจา 2026-09-02) → [[Other Systems]] |

### ⚠️ K2 อาจไม่ได้ให้บริการแค่ UFUND

เอกสารเดียวกันระบุว่า **K2 ทำหน้าที่ระบบใบแจ้งหนี้/ลูกหนี้ให้ธุรกิจ EV ด้วย**:
Billing & Repayment · Overdue Bills · Refund Orders · E-invoicing · Consolidated Invoicing ·
Invoice Reversal · Traffic Violation · Cash Flow & Profit Analysis (ร่วมกับ 365)

**ยังไม่ได้ยืนยันจากฐานข้อมูลจริง** — ถ้าจริง แปลว่าตาราง `CONTRACT` / `INVOICE` / `REPAYMENT`
ใน `HPCOM7` มีข้อมูล 2 ธุรกิจปนกัน และเกณฑ์ OD/ค่าปรับที่ทำไว้ให้ UFUND อาจใช้กับ EV ไม่ได้

→ ต้อง probe หาคอลัมน์ที่แยก BU · รายละเอียด [[EV China Benchmark]]

**และอาจกลายเป็น 3 ธุรกิจ** — มีการแจ้งด้วยวาจา 2026-09-02 ว่าฐานข้อมูล **ICI (iCare Insurance) จะย้ายจาก P&O มาอยู่ IDS (K2) on-premise** ถ้า IDS คือฐานเดียวกับ `HPCOM7` จริง คำถามเรื่องคอลัมน์แยก BU จะยิ่งสำคัญ `[อนุมาน]` → [[Other Systems]] · [[Source System Issues]]

---

## จุดเชื่อมข้ามระบบที่ยืนยันแล้ว

| จาก | ถึง | คีย์ | ที่มา |
|---|---|---|---|
| CRM `members` | **ITEC** | `itec_cuscode` | `crm_fied_description.html` |
| CRM `members` | CRM `customer_master` | `customer_master_id → id` | เอกสาร CRM |
| CRM `member_auth` (7Club+) | CRM `members` | `member_id → id` | เอกสาร CRM |
| CRM `customer_master` | **K2** `PERSON` | เลขบัตรประชาชน (`citizen_no` ↔ `TAX_ID`) | `[อนุมาน]` — ยังไม่ได้ทดสอบ join จริง |
| K2 `COLLECTION_OD_ASSIGNMENT` | ITOS `ITOS_COLLECTION_DETAIL` | union ด้วย `SOURCE_SYSTEM` ไม่ใช่ join | [[Collection Union (K2 + ITOS)]] |

> **คำถามเดิมที่ว่า "CRM ผูกกับ ITEC ด้วยอะไร" — ปิดแล้ว** คำตอบคือ `members.itec_cuscode`

---

## Databases seen in SQL whose role is unknown

| ชื่อ | ใช้กับ | สถานะ |
|---|---|---|
| `PROJECT_1` | view ของ ITEC (`view_itec_payment`) | ไม่รู้ว่าเป็น source หรือชั้น reporting |
| `TAN_MIS` | query ของ MIS | ไม่รู้ |
| `ILOAN_DATASOURCE` | extract ของ ITOS | น่าจะเป็นชั้น extract เหนือ ITOS `[อนุมาน]` |
| `HPCOM7` | K2 ทั้งระบบ | **ยืนยันแล้ว** — เป็นฐานจริงของ K2 สำรวจครบ 2026-08-26 |
| `D365FO_DATALAKE` | inventory/purchasing ของ D365 | เป็น data lake export ของ D365 F&O `[อนุมาน]` |
| `syndpdev001` | item master, sales/purchase invoice | น่าจะเป็น Synapse dev endpoint `[อนุมาน]` |

---

## Company list from ITOS

ตาราง `M_COMPANY` มี 18 แถว ตัวอย่าง 10 แถวแรกจาก schema wiki:

| Code | ชื่อ |
|---|---|
| **TFF** | **บริษัท ธันเดอร์ ฟิน ฟิน จํากัด (THUNDER FINFIN Co.,LTD.)** |
| BaNANA | BaNANA |
| BKK | BKK |
| UFicon | UFicon |
| Samsung | Samsung |
| Studio7 | Studio 7 |
| U-Store | U-Store |
| Kingkong | Kingkong |
| SPVI | SPVI |
| BN | BN-POP, BN-Stand Alone |

**ข้อสังเกตสำคัญ:** นี่คือ *บริษัท/ร้านที่เกี่ยวข้องกับสัญญาสินเชื่อในระบบ ITOS* ไม่ใช่ "รายชื่อ BU ของ COM7" — Samsung และ SPVI เป็นคนละบริษัท การใช้ตารางนี้เป็นรายชื่อ BU จะผิด `[อนุมาน]`

**สิ่งที่ตารางนี้ยืนยันได้:** **TFF เป็นนิติบุคคลจริง** ชื่อ "บริษัท ธันเดอร์ ฟิน ฟิน จำกัด" — สำคัญต่อเรื่อง consent เพราะ Data Framework กำหนดว่า consent เป็นของแต่ละบริษัท

---

## Payment channels from ITOS

ตาราง `M_CHANNEL` มี 7 แถว:

| Type | ช่องทาง |
|---|---|
| B (ธนาคาร) | ธนชาติ · กรุงศรี · กรุงไทย |
| O (อื่น) | Counter Service · True Money · Tesco Lotus · Dtac |

**ข้อสังเกต:** **Dtac ในนี้คือจุดรับชำระเงิน ไม่ใช่ร้านในเครือ COM7** — brief เดิมระบุ "Dtac Shop" เป็น BU แต่ในข้อมูลจริงที่เจอ Dtac ปรากฏเป็น payment channel เท่านั้น ยังไม่มีหลักฐานว่า Dtac Shop เป็น BU

---

## BUs with no evidence yet

Brief เดิมระบุ **Double7**, **Co-Ture Shop**, **Dtac Shop** เป็น business unit

**ไม่พบชื่อเหล่านี้ในเอกสารต้นฉบับไฟล์ไหนเลย** (ค้นใน ClickUp, Data Framework, Gap Review, Timeline, ITOS wiki, AWS Proposal)

อาจเป็นได้ว่า: ใช้ระบบที่มีในรายการอยู่แล้วภายใต้ชื่ออื่น · ยังไม่ถูกนำเข้า scope · หรือชื่อในเอกสารต่างจากชื่อที่ใช้พูด — **ต้องถามคน ไม่ใช่เดา**

---

## Grouped by problem

**ระบบทับซ้อนกันฝั่ง EV:** D365 · GI Core · AION DMS · EV7CORE · EVTRACKING

**กำลังรวมเป็นระบบเดียว:** K2 + ITOS

**ถือข้อมูลลูกค้าและต้อง reconcile:** ITEC · K2 · ITOS · GI Core · iCare · 7Club · CRM · Tech Trade

**ข้อมูลวงจรชีวิตอุปกรณ์** (Gap Review จัดเป็นช่องว่างอันดับ 1): ITEC (การซื้อ, อุปกรณ์เสริม) · iCare (ประกัน, ซ่อม) · Tech Trade (เทิร์น) · ทะเบียนอุปกรณ์ (ยังไม่มี)

---

## เชื่อมกับโน้ตอื่น

[[SSOT Roadmap]] · [[Current Status]] · [[People & Teams]] · [[Source Inventory]] · [[EV Systems]] · [[Issue Index]]
