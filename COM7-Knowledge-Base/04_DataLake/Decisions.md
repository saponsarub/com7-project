# Decisions

สิ่งที่ตัดสินใจไปแล้ว พร้อมเหตุผล
ถ้ายังถกกันอยู่ ให้อยู่ใน [[Open Questions & Risks]] ไม่ใช่ที่นี่

---

## D-01 · Primary region is ap-southeast-7

**ที่มา:** AWS Proposal (4 ส.ค. 2026)

Storage, ingestion, transformation, analytics deploy ที่ AWS Asia Pacific (Thailand)

**หลักฐานเสริมจากการวัด:** query ข้าม region ช้ากว่า 2.6 เท่าบนข้อมูลเดียวกัน → [[Athena Benchmark]]

---

## D-02 · Use Medallion architecture on S3

**ที่มา:** AWS Proposal + บันทึกออกแบบของทีม

Raw → Bronze → Silver → Gold พร้อม Quarantine zone
*(เส้นแบ่งแต่ละ layer ยังไม่ตกลง → [[Architecture]])*

---

## D-03 · Use Parquet + Iceberg

**ที่มา:** PoC review

Columnar format สำหรับงาน analytics ช่วยลดข้อมูลที่ต้อง scan และลด cost ของ Athena

**ข้อควรรู้จากการวัด:** Iceberg ช้ากว่า Hive-style partition บน query เล็กที่กรองแล้ว (2.44 vs 1.71 วินาที) แต่ใกล้เคียงกันบน full scan → เลือก Iceberg เพราะความสามารถ (ACID update/delete, schema evolution, time travel) ไม่ใช่เพราะเร็วกว่า `[อนุมาน]`

---

## D-04 · Use Power BI in Phase 1, not QuickSight

**ที่มา:** PoC review ข้อ 6 และ 7 (ทั้งคู่สถานะ Complete)

QuickSight ไม่มี region ในไทย ผลทดสอบพบว่า cross-region ทำให้ runtime, latency และค่าใช้จ่ายเพิ่มอย่างมีนัยสำคัญ โดยค่าใช้จ่ายส่วนใหญ่มาจาก Amazon Q

Athena → Power BI ทดสอบแล้วเชื่อมได้ผ่าน Athena ODBC ด้วย Access Key และ Secret Key ที่ admin สร้างให้

**ทบทวนเมื่อ:** QuickSight เปิดให้บริการใน Thailand Region

---

## D-05 · Do not malware-scan every object

**สถานะ: เสนอไว้ ยังไม่เห็นการอนุมัติเป็นทางการในเอกสาร**
**ที่มา:** PoC review ข้อ 2

Scan ทุก object ทำให้ GuardDuty อย่างเดียวประมาณ 3,500 USD/เดือน และข้อมูลส่วนใหญ่มาจาก internal database ผ่าน VPN

**แนวทาง:** ทำ Data Classification / Threat Model ก่อน แล้ว scan ตามความเสี่ยงราย source

**ข้อแม้ที่บันทึกไว้เอง:** *"VPN ไม่ได้ทำหน้าที่ Scan Malware โดยตรง"* — เป็นการยอมรับความเสี่ยง ไม่ใช่การรับประกันความปลอดภัย

---

## D-06 · Start with Athena, defer Redshift

**สถานะ: เสนอไว้ กำลังทดสอบ**
**ที่มา:** PoC review ข้อ 4

เริ่มจาก `S3 (Silver, Gold) → Iceberg + Parquet → Athena → BI` แล้วทำ performance test

**จะพิจารณา Redshift เมื่อพบว่า:** query ใช้เวลานานเกิน requirement · มี query จำนวนมาก · query มี join/aggregation ซับซ้อน · dashboard ต้องการ response time ต่ำ (โดยเฉพาะรายงานผู้บริหาร) · Athena cost จาก query volume สูง

---

## D-07 · Mint a new customer_id but keep the source key

**ที่มา:** บันทึกประชุม GI+EV7 (21 ส.ค. 2026)

> "gen customer_id ตัวใหม่แต่ยังเก็บ source ไว้"

หลักการเดียวกันปรากฏในงาน K2/ITOS ด้วย โดยใส่คอลัมน์ `SOURCE_SYSTEM` ในคิวรี่ union

---

## D-08 · Dedupe customers primarily by national ID

**ที่มา:** บันทึกประชุม GI+EV7

> "ต้องกำหนดหลักในการ Deduplicate เช่น ใช้เลขบัตรประชาชน(ถ้ามี)/email/เบอร์โทร"

ลำดับ: เลขบัตร → email → เบอร์โทร

**ยังไม่ตอบ:** ถ้าไม่มีเลขบัตรจะทำยังไง (GI Core `IdentityCard` เป็น nullable)

---

## D-09 · Clean and migrate GI/EV7 data first, then integrate into 7Club

**ที่มา:** บันทึกประชุม GI+EV7

> "data ของ EV7&GI ยังไม่สะอาดเท่าที่ควร บวกกับยังไม่ได้ทำการ standardize ให้เข้ากับ 7club ทางที่ประชุมจึงเห็นว่าควรเริ่มจากการ migrate เเละ clean data ก่อน"

---

## D-10 · Merge K2 and ITOS into one system

**สถานะ: กำลังทำ (Data Preparation)**
**ที่มา:** ClickUp `K2 & ITOS Integrated Loan System.txt`

สร้าง full loan system ครอบคลุม `APP In → Scoring → Approve → Collection → Close Case`

**แผน migrate 3 ช่วง:** ทั้งคู่ป้อน Unified → ตรวจสอบข้อมูล → K2 ค่อยๆ ลดการใช้งาน → เลิกใช้ K2 เหลือ ITOS

มี 2 แผนการสร้างที่บันทึกไว้ (UnionPlan1 กับ UnionPlan2) โดย **UnionPlan2 สร้าง schema เปล่าก่อนแล้วค่อย insert ทีละ table** พร้อมเพิ่มคอลัมน์ระบุว่า migrate มาจากไหน

---

## D-20 · ใช้ snapshot diff แทน DMS CDC เพราะ IT ไม่อนุมัติให้เปิด CDC

**สถานะ:** ตกลงแล้ว · **ที่มา:** ทีม Data Engineering (AWS) แจ้ง 2026-09-08

**บริบท:** Data Lake ต้องรู้ว่าแถวไหนเพิ่ม / แก้ / ลบ ซึ่งวิธีมาตรฐานคือ **DMS CDC**
แต่ CDC ต้องเปิดความสามารถที่ระดับฐานข้อมูลต้นทาง (SQL Server ของ ITEC) — **เจ้าของระบบฝั่ง IT ไม่อนุมัติ**

**ที่เลือก:** DMS รันเป็น **Full Load** ส่ง snapshot เต็มทุกรอบ แล้ว**หา change เอาเองจากการเทียบ snapshot รอบนี้กับรอบก่อนหน้า**
→ [[Snapshot Change Detection (ITEC DMS)]]

**ที่ไม่เลือก และทำไม:**

| ทางเลือก | ทำไมไม่ได้ |
|---|---|
| DMS CDC | **IT ไม่อนุมัติ** — ต้องเปิดที่ตัวฐานข้อมูลต้นทาง |
| trigger / audit table ฝั่งต้นทาง | ต้องแก้ระบบของเจ้าของ ซึ่งเป็นข้อจำกัดเดียวกัน |
| ใช้คอลัมน์เวลาอัปเดตแทน | **จับ DELETE ไม่ได้** และ ITEC เปิดให้เห็นแค่ 23 view ไม่มี table → [[ITEC Overview]] |

**ราคาที่ต้องจ่ายกับข้อจำกัดนี้**

| ผล | รายละเอียด |
|---|---|
| โหลดหนักกว่า | ย้ายข้อมูลทั้งชุดทุกรอบ ไม่ใช่เฉพาะที่เปลี่ยน |
| ต้องเก็บ snapshot ไว้เทียบ | Bronze ต้องเปิด versioning · ต้องมี snapshot ผูกกับ run |
| **รู้แค่ผลลัพธ์ ไม่รู้ลำดับ** | แถวที่ถูกแก้ 3 ครั้งระหว่างสองรอบ เห็นเป็นการแก้ครั้งเดียว |
| ความละเอียดเท่ากับความถี่ที่รัน | รันวันละครั้ง = รู้การเปลี่ยนแปลงระดับวัน ไม่ใช่ near-real-time |

**ทบทวนเมื่อ:** IT เปลี่ยนท่าที · ย้ายจาก P&O ไป IDS (K2) on-premise แล้วเจ้าของระบบเป็นทีม dev ภายใน ซึ่งอาจอนุมัติได้ง่ายกว่า

---

## D-12 · Connect to the database over VPN Client by Vanguard instead of Site-to-Site VPN

**ที่มา:** ประชุม 24 ส.ค. 2026

เดิม AWS Proposal ระบุ Site-to-Site VPN 30 encrypted tunnels บน Virtual Private Gateway
ที่ประชุมสรุปว่าจะต่อผ่าน **VPN Client โดย Vanguard** แทน

**ยังไม่รู้:** Vanguard คืออะไร · เหตุผลที่เปลี่ยน · เป็นแนวทางถาวรหรือเฉพาะ PoC · แผน Site-to-Site เดิมยกเลิกหรือเลื่อน

**สิ่งที่ต้องตามต่อ:** VPN Client รองรับการเชื่อมต่อแบบต่อเนื่องของ pipeline (เช่น DMS CDC) ได้ไหม เพราะโดยทั่วไป Client VPN ออกแบบให้ client ต่อเข้าเครือข่าย ต่างจาก Site-to-Site ที่เชื่อมเครือข่ายถึงเครือข่ายแบบเปิดค้าง `[อนุมาน]`

> **คำถามนี้ไม่บล็อกอีกต่อไปแล้ว** — CDC ไม่ได้รับอนุมัติตั้งแต่ต้น ตัวปิดคือเจ้าของฐาน ไม่ใช่เครือข่าย → **D-20**

---

## D-11 · PDPA consent is a separate task

**ที่มา:** `datacleanplan.txt` + Project Timeline

> "Consent PDPA จะอยู่ในช่วง Standardize ข้อมูล → สร้างTable ใหม่รวมข้อมูล Customer > แยกไปอีก Task"

Timeline ระบุ "Customer Consent for Com7 Group" เป็น Related Project แยก

---

## D-13 · ITOS is the primary source, K2 is legacy/historical

**ที่มา:** ประชุม 27 ส.ค. 2026 → [[2026-08-27 UFUND K2 และ ITOS]]

migration K2 → ITOS ยังไม่เสร็จ · เป้าครบ 100% สิ้นปี 2026 · **อาจต้องใช้คู่ขนานถึงราว Q1/2027**

**ยังต้อง ingest K2 เข้า S3 อยู่ดี** — ทั้งเพื่อข้อมูลย้อนหลัง และเพราะ **UFUND Student** อาจต้องอยู่บน K2 ต่อไป
(กลุ่มนักศึกษายังไม่มี Credit History / Risk Assessment · และถ้าบริษัท IPO ต้องมีประวัติย้อนหลังให้ ธปท. ตรวจสอบ)

---

## D-14 · Store only an NCB summary/indicator, never the full record

**ที่มา:** ประชุม 27 ส.ค. 2026

ข้อมูล NCB เป็น sensitive — **ห้ามนำรายละเอียดเข้า Data Lake (S3)**
เก็บได้เฉพาะสรุปที่จำเป็นต่อการวิเคราะห์ เช่น ระดับภาระหนี้ **สูง / กลาง / ต่ำ** หรือทำเป็น flag

ปัจจุบัน NCB อยู่ที่ **ITOS เท่านั้น** — K2 หยุดเก็บตั้งแต่ 08/2025

**ยังไม่รู้:** ข้อมูล NCB อยู่ตารางไหนใน `ILOAN_COLLECTION`

---

## D-15 · Every ETL job must produce a reconciliation log

**ที่มา:** ประชุม 27 ส.ค. 2026 → [[2026-08-27 AWS Data Lake]]

ทุก job ต้องบันทึก: จำนวน column/row/ขนาดของ**ต้นทาง** เทียบกับ**ปลายทาง** · เวลาเริ่มและเวลาเสร็จ ·
เป็น `append` หรือ `rewrite` · ชื่อตารางต้นทางและปลายทาง

MIS จะส่งอีเมลระบุผู้รับ log ให้ทีม AWS

---

## D-16 · ETL runs at 23:30 daily

**ที่มา:** ประชุม 27 ส.ค. 2026 · **สถานะ: เบื้องต้น**

---

## D-17 · Split pipelines into "needs cleaning" and "ready to use"

**ที่มา:** ประชุม 27 ส.ค. 2026

ข้อมูลสองแบบนี้เขียน ETL pipeline คนละแบบ ต้องแยก scenario ตั้งแต่ออกแบบ → [[ETL & Spark]]

---

## D-18 · D365 is not a source of customer data

**ที่มา:** ประชุม 26 ส.ค. 2026 → [[2026-08-26 ERP]]

COM7 ใช้ **D365 F&O** (module: Finance · Accounting · Inventory · Sale)
D365 **ไม่มีข้อมูลลูกค้าและไม่มีข้อมูล promotion** และเป็นระบบที่ **replicate มาจาก database หลักของแต่ละ BU อีกที**

→ ตัด D365 ออกจากแหล่งข้อมูลของ Customer 360 · ถ้าจะ ingest ควรดึงจากฐานต้นทางของแต่ละ BU โดยตรง

---

## D-19 · PDPA on region is closed except Macie and SNS

**ที่มา:** ประชุม 27 ส.ค. 2026

AWS ยืนยันว่า **minimum requirement service อยู่ที่ไทยทั้งหมด** → ตัดประเด็นข้อมูลออกนอกประเทศ
**ยกเว้น Macie และ SNS** ที่ยังไม่อยู่ที่ไทย — ต้องประเมินผลกระทบแยก

**QuickSight ยังไม่มีแผนเปิดที่ไทย** — สนับสนุน [[Decisions|D-04]] ที่เลือก Power BI ใน Phase 1

---

## Template for the next entry

```markdown
## D-XX · <what was decided>
**สถานะ:** เสนอ / ตกลงแล้ว / ถูกแทนที่
**วันที่:** · **ใครตัดสิน:** · **ที่มา:**

**บริบท:** ปัญหาอะไรที่ทำให้ต้องตัดสินใจ
**ที่เลือก:**
**ที่ไม่เลือก และทำไม:**
**ทบทวนเมื่อ:**
```

---

## เชื่อมกับโน้ตอื่น

[[Open Questions & Risks]] · [[Current Status]] · [[Architecture]]
