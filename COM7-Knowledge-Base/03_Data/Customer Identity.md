# Customer Identity

ปัญหาที่ยากที่สุด — เป้าหมายเรื่อง Customer 360, CDP, segmentation, cross-selling ทั้งหมดขึ้นกับข้อนี้

> **อัปเดต 2026-08-28** — จุดเชื่อมข้ามระบบที่ยืนยันแล้ว: `members.itec_cuscode` (CRM → ITEC)
> และ `citizen_no` ↔ `PERSON.TAX_ID` (CRM → K2, **ยังไม่ทดสอบ join จริง**)
> ⚠️ `customer_master.citizen_no` มีตามเอกสาร แต่**บัญชีเรามองไม่เห็น** (ถูกซ่อนสิทธิ์ระดับคอลัมน์ — ต้องขอจากทีม Inno) · ที่เห็นได้คือ `member_auth.identity_no` (154,889 แถว)
> [[CRM - Data Dictionary]] · [[K2 Customer Field Survey]] · ผลทดสอบคีย์ CRM ↔ ITEC-Rep และ promotion (2026-11-10) → [[Customer Dimension - Feasibility]]

---

## The problem

ลูกค้าคนเดียวอาจอยู่ในหลายระบบด้วย ID คนละตัว

Gap Review `ARC-02` **Identity Resolution Engine** — สถานะ **ขาด**, P1

> "มี Main Customer ID และ Source Customer ID [แต่] ยังไม่ระบุกลไกที่ทำให้สอง ID เชื่อมกัน ต้องกำหนดกฎ deterministic (citizen id, เบอร์โทร) และ probabilistic, survivorship rule, golden record, merge log"

> ผลกระทบ: "ลูกค้าคนเดียวถูกนับเป็นหลาย record ทำให้ personalization ผิดคนและวัดผลเพี้ยน"

---

## Readiness

Customer Data Gap Review (4 ส.ค. 2026) ตรวจ 88 รายการ

| หมวด | รวม | มี | ไม่พอ | ขาด |
|---|---:|---:|---:|---:|
| Data Fields | 63 | 8 | 11 | 44 |
| Architecture | 12 | 0 | 3 | 9 |
| Activation & KPI | 13 | 1 | 3 | 9 |
| **รวม** | **88** | **9** | **17** | **62** |

ข้อสรุปหลักของรายงาน:

> "หน้า 8 แข็งแรงเรื่อง Identity และ Demographic (main/source customer id, citizen id, ที่อยู่ 3 ประเภท, LINE ID, Facebook ID) ซึ่งเป็นฐานที่ดี"

> "แต่สิ่งที่หน้า 8 ให้ยังเป็น 'ทะเบียนลูกค้า (customer master)' ไม่ใช่ 'customer intelligence' ซึ่งเป็นสิ่งที่ hyper-personalization ต้องใช้"

> "ช่องว่างหลัก 3 จุด: (1) ความลึกของ transaction (2) สัญญาณพฤติกรรมแบบ real-time (3) derived attributes / scoring ที่ยังไม่ปรากฏเลยแม้แต่รายการเดียว"

> "หน้า 8 ระบุว่า 'Can identify customer segment' แต่ไม่ได้ระบุว่า segment คำนวณจาก field ใด ด้วย model อะไร และเก็บไว้ที่ไหน"

---

## Identity fields — 12 of them

| ID | Field | สถานะ | P | ความอ่อนไหว PDPA |
|---|---|---|---|---|
| IDN-01 | Main Customer ID (golden record key) | ขาด | P1 | ปานกลาง |
| **IDN-02** | **Source Customer ID** | **มีแล้ว** | P1 | ปานกลาง |
| IDN-03 | Customer Type | ขาด | P1 | ปานกลาง |
| IDN-04 | Identification type | ขาด | P1 | ปานกลาง |
| IDN-05 | Citizen ID | มีแต่ไม่ละเอียดพอ | P1 | **สูงมาก — ต้อง tokenize/encrypt** |
| IDN-06 | Passport ID | ขาด | P1 | ปานกลาง |
| IDN-07 | Juristic ID | ขาด | P1 | ปานกลาง |
| IDN-08 | Device / Cookie / Advertising ID | ขาด | P1 | สูง |
| IDN-09 | Hashed Email / Hashed Phone | ขาด | P2 | สูง |
| IDN-10 | App User ID / LINE UID | มีแต่ไม่ละเอียดพอ | P1 | สูง |
| IDN-11 | Household / Family Linkage ID | มีแต่ไม่ละเอียดพอ | P3 | สูง |
| IDN-12 | Merge / Unmerge History | ขาด | P2 | ปานกลาง |

**มีครบแค่ 1 จาก 12**

ความเห็นที่บันทึกในรายงาน:
- `IDN-05`: *"เก็บในระบบด้วย hash จะได้ไม่เสี่ยง pdpa"*
- `IDN-09`: *"ควรเก้บเป้น data จริงเพราจะใช้ส่ง แต่เวลาส่งออกนอกระบบควร hash"*
- `IDN-10`, `IDN-11`: Source System ระบุว่า K2, ITOS · Owner ระบุว่า Thunder · หมายเหตุ *"ระบบอื่นไม่น่ามีเพราะ UFUND เก็บละเอียด"*

---

## The approach agreed in the meeting

จากบันทึกประชุม GI+EV7 (21 ส.ค. 2026):

> "นำข้อมูลลูกค้า 2 เเหล่งมารวมกัน → remove duplicate ด้วยบัตรประชาชน → gen customer_id ตัวใหม่เเต่ยังเก็บ source ไว้ หลังจากนั้นค่อยนำมา map กับข้อมูลการซื้อขายสินค้าอื่นๆ"

> "ต้องกำหนดหลักในการ Deduplicate เช่น ใช้เลขบัตรประชาชน(ถ้ามี)/email/เบอร์โทร สร้าง customer_id, CRM_id กลางใหม่"

**หลักการเก็บ source ไว้** ปรากฏ 2 ที่โดยอิสระ — ในแนวทางนี้ และในคอลัมน์ `SOURCE_SYSTEM` ของคิวรี่ union K2/ITOS

---

## Known obstacles

### The national ID may be missing

GI Core `IdentityCard` เป็น `VarChar(13)` และ **nullable** → กลยุทธ์ "dedupe ด้วยบัตรประชาชน" ใช้ไม่ได้กับทุกเรคอร์ด

**ไม่รู้ว่ามีกี่เปอร์เซ็นต์** — ต้องนับจากข้อมูลจริง

### Thai addresses

Gap Review `DQY-03`:
> "ที่อยู่ภาษาไทยเขียนได้หลายรูปแบบ ทำให้ match พลาดสูงมากหากไม่ normalize"

GI Core เก็บ `address` เป็น LongText ไม่มีโครงสร้าง

### Addresses and phones are one-to-many

ITOS: `S_CUSTOMER` 165,722 แถว แต่ `S_CUSTADDR` 746,916 แถว และ `S_CUSTTEL` 371,323 แถว
→ matching ต้องรองรับหลายค่าต่อคน `[อนุมาน]`

### There is no system of record yet

Gap Review `DQY-02` **System of Record ต่อ field** — สถานะ **ขาด**, P1
> "ระบุว่าฟิลด์ใดยึดข้อมูลจากระบบไหนเป็นหลัก ป้องกันข้อมูลขัดแย้งกันระหว่าง BU"

**ถ้าไม่มีข้อนี้ เขียน survivorship rule ไม่ได้ และสร้าง golden record ไม่ได้** `[อนุมาน]`

### The two error types are not equal

`[อนุมาน]` — ไม่ได้เขียนในรายงาน แต่สำคัญต่อการตั้ง threshold:

- **ไม่รวมทั้งที่ควรรวม** → ลูกค้ายังแยกกัน personalization ไม่ครบ · แก้ทีหลังได้
- **รวมทั้งที่ไม่ควร** → คนหนึ่งเห็นข้อมูลอีกคน · เป็นเรื่องความเป็นส่วนตัว และแก้ยากถ้าไม่ได้บันทึก merge history ไว้ (ซึ่ง `IDN-12` ระบุว่าขาด)

---

## Architecture gaps

Architecture ได้คะแนนต่ำสุด — **0 จาก 12 รายการที่มีครบ**

| ID | หัวข้อ | สถานะ | P |
|---|---|---|---|
| ARC-01 | CDP / Customer 360 Layer | ขาด | P1 |
| ARC-02 | Identity Resolution Engine | ขาด | P1 |
| ARC-03 | Real-time / Streaming Ingestion | ขาด | P1 |
| ARC-04 | Data Freshness SLA per Domain | ขาด | P2 |
| ARC-05 | Event Taxonomy / Naming Standard ข้าม BU | ขาด | P1 |
| ARC-06 | Feature Store + Model Registry | ขาด | P2 |
| ARC-07 | Reverse ETL / Activation API | มีแต่ไม่ละเอียดพอ | P2 |
| ARC-08 | Real-time Decisioning Engine | ขาด | P2 |
| ARC-09 | Tokenization / Encryption ของ Citizen ID | ขาด | P1 |
| ARC-10 | Data Access Control ระดับข้อมูลลูกค้า | มีแต่ไม่ละเอียดพอ | P1 |
| ARC-11 | Data Lineage + Audit Trail | ขาด | P2 |
| ARC-12 | Ownership Model: Central vs Federated | มีแต่ไม่ละเอียดพอ | P2 |

**`ARC-01` เป็นข้อที่รายงานจัดเป็นอันดับ 3 ของทั้งโปรแกรม:**

> "ระบุตำแหน่ง CDP / Customer 360 layer ให้ชัดเจน — Braze เป็น engagement platform ไม่ใช่ CDP หากไม่มี layer รวมข้อมูลอยู่ข้างหน้า แต่ละ BU จะยิงข้อมูลเข้า Braze แยกกัน"

> ผลกระทบ: "ได้ segment หยาบ ไม่เกิด single customer view จริง ลงทุนซ้ำซ้อนหลาย BU"

**`ARC-12` — ยังไม่ตอบว่าใครเป็นเจ้าของข้อมูลลูกค้า:**

> "ควรระบุให้ชัดว่าใครเป็นเจ้าของข้อมูลลูกค้าในทางปฏิบัติ ระหว่างส่วนกลางกับแต่ละ BU และใครมีสิทธิ์สร้าง segment"
> ผลกระทบ: "เกิดข้อขัดแย้งเรื่องความเป็นเจ้าของข้อมูลระหว่าง BU ทำให้โครงการล่าช้า"

---

## Device ownership — the number one gap

Gap Review จัดเป็นอันดับ 1 จาก 5 ของทั้งโปรแกรม

> "เป็น field ที่ให้ ROI เร็วที่สุดสำหรับธุรกิจค้าปลีกไอที เพราะทำ replacement-cycle prediction, warranty renewal และ accessory cross-sell ได้ทันที"

| ID | Field | Source System ที่ระบุ | สถานะ |
|---|---|---|---|
| DEV-01 | Device Registry: brand/model/serial/IMEI | NA — ต้องสร้างใหม่ | ขาด |
| DEV-02 | Purchase Date + Device Age | ITEC | ขาด |
| DEV-03 | Warranty Expiry Date | Icare | ขาด |
| DEV-04 | Trade-in History + Eligibility | Tectrade | ขาด |
| DEV-05 | Service / Repair / Claim History | Icare | ขาด |
| DEV-06 | Accessory Attach History | ITEC | **มีแล้ว** |

รู้เจ้าของข้อมูล 3 ระบบแล้ว ช่องว่างหลักคือ device registry ที่ยังไม่มีใครถือ `[อนุมาน]`

---

## Derived / score — all 10 missing

| ID | Attribute | P |
|---|---|---|
| DRV-01 | RFM Score | P1 |
| DRV-02 | CLV — Historical และ Predicted | P1 |
| DRV-03 | Churn Probability | P1 |
| DRV-04 | Propensity to Buy (รายหมวด) | P1 |
| DRV-05 | Brand / OS Affinity | P1 |
| DRV-06 | Price Sensitivity / Discount Affinity | P2 |
| DRV-07 | Preferred Channel + Contact Time | P1 |
| DRV-08 | Lifecycle Stage | P1 |
| DRV-09 | Segment / Persona Label + model version | P1 |
| DRV-10 | Next Best Offer / Next Best Action | P2 |

รายงานระบุ `DRV-01` ว่า *"เป็น segmentation ขั้นต่ำที่สุดที่ต้องมี"*

RFM ต้องการแค่ประวัติการซื้อ ซึ่ง ITEC มีอยู่แล้ว จึงน่าจะคำนวณได้โดยไม่ต้องรอ identity resolution ข้าม BU `[อนุมาน]`

---

## Order of work

`[อนุมาน]` — ไม่ได้เขียนเป็นลำดับในรายงาน แต่เป็นการเรียงตามการพึ่งพา

```
consent (รอ legal) → identity resolution → customer master รวมแล้ว
→ เชื่อม device + transaction → derived scores → recommendation → activation
```

ทุก derived attribute คำนวณต่อลูกค้า 1 คน ถ้าคนหนึ่งยังเป็นหลาย record จะได้ score ที่ผิด

## เส้นทางเชื่อมลูกค้าข้ามระบบ (ยืนยัน 2026-08-28)

```
ITEC   rpt.dim_mem_itec.crmid          ── M + 12 ตัว ──►  CRM  members.member_id
CRM    members.itec_cuscode            ──────────────►  ITEC (ทิศทางกลับ)
CRM    members.customer_master_id      ──────────────►  CRM  customer_master.id
CRM    customer_master.citizen_no 🔒 / member_auth.identity_no ── เลขบัตร ───►  K2   PERSON.TAX_ID
K2     PERSON.PERSON_ID                ──────────────►  K2   CONTRACT
```

### ระบุตัวตนลูกค้าได้กี่ % — วัดจริงจากฝั่ง ITEC

| | จำนวน | สัดส่วน |
|---|---:|---:|
| บิลขายที่จับคู่ลูกค้าได้ (ทดสอบ 200,000 บิล) | 178,454 | **89.2%** |
| แถวใน `dim_mem_itec` ที่มี `crmid` ใช้งานได้ | 12,590,750 | 57% |
| `crmid` เป็น NULL | 9,409,040 | 43% |
| `crmid` เป็น `-` (placeholder ต้องถือเป็น NULL) | 42,613 | 0.2% |

### ⚠️ ปัญหาที่เจอตอนสำรวจ

| ปัญหา | รายละเอียด |
|---|---|
| **`memcode` ใช้เป็นคีย์ไม่ได้** | มี 20 ความยาว ปนกันตั้งแต่ 1–20 ตัวอักษร · 1.35 ล้านแถวเป็นเบอร์โทร (10 หลัก) |
| **`dim_mem_itec` grain ไม่นิ่ง** | 1 บิลมีได้ถึงหลายร้อยแถว — ต้อง `DISTINCT` ก่อน join ไม่งั้นยอดถูกคูณ |
| **มีบัญชีที่ไม่ใช่บุคคล** | `crmid` เดียวมี 10,861 บิลใน 8 เดือน (~45 บิล/วัน) — น่าจะเป็นองค์กร/ตัวแทน/รหัสสำรอง<br>**ต้องกรองออกก่อนทำ analytics รายบุคคล** |
| **`crmid` มีหลาย prefix** | พบ `M06` `M04` `M01` `M02` — ยังไม่ทราบความหมาย |

ที่มา → [[ITEC Overview]] · [[ITEC-MIS - Query Cookbook]]

---

## เชื่อมกับโน้ตอื่น

[[Consent & PDPA]] · [[Data Standardization & Quality]] · [[CRM Overview|CRM, 7Club, Braze]] · [[Analytics & AI]]
