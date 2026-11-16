# Consent & PDPA

การจัดการความยินยอมของลูกค้าตาม พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล และผลกระทบต่อการรวมข้อมูลข้ามบริษัทในเครือ

> **อัปเดต 2026-08-28** — สำรวจแล้วพบว่า **K2 ไม่มีฟิลด์ compliance ตรงๆ สักตัวจาก 4 ตัวที่ต้องการ**
> ส่วน CRM มี consent แยก 3 ระดับ → ข้อเสนอคือให้ **CRM เป็น system of record ของ consent**
> [[K2 Customer Field Survey]] · [[CRM - Data Dictionary]]

---

## The core conflict

**Data Framework slide 6** ระบุหลักการ consent:

> "According to PDPA a Consent should be:
> Every Business entity (company) should have consent of its own.
> Purpose must be separate and specific.
> Easy to understand and not misleading.
> Consent must be given on data owner's free will.
> Data owners can access their personal data.
> Easy to give and easy to revoke."

**Data Framework slide 8** ระบุเป้าหมาย:

> CRM Data: "Covers every system in COM7 group."

**Customer Data Gap Review เขียนถึงความขัดแย้งนี้ตรงๆ:**

> "ประเด็นเชิงโครงสร้าง: หน้า 6 ระบุว่า consent ต้องเป็นของแต่ละ business entity แต่หน้า 8 เสนอ 'covers every system in COM7 group' — สองข้อนี้ขัดกันหากไม่มี consent orchestration รองรับ"

รายงานจัดเป็น**อันดับ 2 จาก 5** ของทั้งโปรแกรม:

> เหตุผล: "หน้า 6 ระบุว่า consent เป็นของแต่ละ entity แต่หน้า 8 เสนอรวมทุก BU — ต้องแก้ก่อนจึงจะใช้ข้อมูลข้าม BU ได้ตามกฎหมาย"
> ผลกระทบหากไม่ทำ: "ความเสี่ยงทางกฎหมาย PDPA และไม่สามารถ activate ข้อมูลข้าม BU ได้จริง"
> ช่วงเวลาที่แนะนำ: Phase 1 (0-3 เดือน)

**ข้อมูลที่ช่วยได้:** ตาราง `M_COMPANY` ใน ITOS ยืนยันว่า TFF เป็นนิติบุคคลจริง (บริษัท ธันเดอร์ ฟิน ฟิน จำกัด) → หลักการ "consent ของแต่ละบริษัท" มีผลจริงกับกรณีนี้

---

## Questions for legal

- รวมข้อมูลลูกค้าข้ามบริษัทในเครือได้ตามกฎหมายไหม ภายใต้ consent ที่มีอยู่
- ถ้าไม่ได้ ต้องขอ consent ใหม่ระดับกลุ่ม หรือใช้ฐานทางกฎหมายอื่น
- การรวม record ลูกค้าข้ามบริษัท (identity resolution) ถือเป็นการเปิดเผยข้อมูลที่ต้องขอ consent เองไหม
- Replicate ข้อมูลไป Singapore เพื่อใช้ Macie ได้ไหม
- QuickSight / Amazon Q ประมวลผลใน us-east-1 ถือเป็นการส่งข้อมูลข้ามพรมแดนไหม
- Braze ประมวลผลและเก็บข้อมูลที่ประเทศไหน · มีสัญญากับ processor แล้วหรือยัง

### Closed

- **iCare เป็นประกันอุปกรณ์ ไม่ใช่ประกันคน** → ข้อกังวลเรื่องข้อมูลสุขภาพตาม ม.26 ไม่เกี่ยวข้อง
- **COM7 มี DPO อยู่แล้ว**
- **ข้อมูลผู้ค้ำประกัน** — ความเห็นล่าสุดคือน่าจะไม่ใช้ เพราะไม่ใช่ลูกค้าจริง (Gap Review `DEM-05` ระบุให้ปรึกษาคุณปองเรื่อง consent บุคคลที่สาม)

---

## Consent fields — all 6 missing or insufficient

ทุกรายการรายงานจัดความอ่อนไหว PDPA ว่า **"สูงมาก"**

| ID | Field | สถานะ | P |
|---|---|---|---|
| CNS-01 | Consent แยกตาม Purpose (จัดเก็บ / ประมวลผล / การตลาด / เปิดเผยข้าม entity) | มีแต่ไม่ละเอียดพอ — slide 8 ระบุแค่ "PDPA Consent" | P1 |
| CNS-02 | Consent Timestamp + Policy Version + Channel ที่ให้ consent | ขาด | P1 |
| CNS-03 | **Cross-entity Sharing Consent** | ขาด — *"ขัดแย้งกับหลักการในหน้า 6"* | P1 |
| CNS-04 | Withdrawal Date + Suppression List / DNC | ขาด | P1 |
| CNS-05 | Legal Basis per Field | ขาด | P2 |
| CNS-06 | Retention Period + Right to Erasure Workflow | ขาด | P1 |

รายงานระบุถึง `CNS-03` ว่า:
> "เป็นเงื่อนไขบังคับก่อนที่ข้อเสนอในหน้า 8 (covers every system in group) จะทำได้จริง"

`CNS-04` มีข้อสังเกต:
> "หน้า 6 ระบุว่าต้อง easy to revoke แต่ยังไม่มี field รองรับ"

`CNS-06`:
> "เป็นข้อกำหนดตาม PDPA ที่ยังไม่ปรากฏในเดคเลย"

---

## Where consent sits in the plan

`datacleanplan.txt` ระบุว่า:

> "Consent PDPA จะอยู่ในช่วง Standardize ข้อมูล → สร้างTable ใหม่รวมข้อมูล Customer > แยกไปอีก Task"

```
Ingest → Clean แต่ละ BU → Standardize → [CONSENT] → Unified Customer Table → Hyper-Personalization
```

Gate อยู่**ก่อน**สร้าง unified customer table

Project Timeline ระบุ **"Customer Consent for Com7 Group"** เป็น Related Project แยกต่างหาก

---

## PDPA — clauses that affect the design

พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562
*สรุปเพื่อใช้ทางวิศวกรรม ไม่ใช่คำแนะนำทางกฎหมาย*

**ความยินยอม (ม.19-20)** — ชัดแจ้ง แยกจากข้อความอื่น ห้าม pre-tick ถอนได้ง่ายเท่าที่ให้ ผู้เยาว์อายุ ≤10 ปีต้องขอจากผู้ปกครอง
→ ต้องมี field ของตัวเองพร้อม timestamp version channel ไม่ใช่ boolean เดียว

**ข้อมูลอ่อนไหว (ม.26)** — สุขภาพ ศาสนา เชื้อชาติ พฤติกรรมทางเพศ ประวัติอาชญากรรม ข้อมูลชีวภาพ ต้องขอ consent ชัดแจ้งแยกต่างหาก
→ ยืนยันแล้วว่า iCare ไม่เข้าข่าย

**สิทธิเจ้าของข้อมูล 8 ข้อ (ม.30-36)** — เข้าถึง/ขอสำเนา (ภายใน 30 วัน), แก้ไข, ลบ/ทำลาย, ระงับการใช้, **คัดค้าน (การตลาดตรงคัดค้านได้เสมอ)**, โอนย้ายข้อมูล, ถอนความยินยอม
→ **ระบบต้องทำได้จริง** ไม่ใช่แค่เขียนในนโยบาย
→ สิทธิขอลบมีนัยทางเทคนิค: ลบแถวเดียวใน Parquet ธรรมดาต้องเขียนไฟล์ใหม่ทั้งก้อน Iceberg ทำเป็น `DELETE` ได้ `[อนุมาน]`

**หน้าที่ผู้ควบคุมข้อมูล (ม.37)** — มาตรการความปลอดภัย, ป้องกันผู้รับข้อมูลใช้ผิดวัตถุประสงค์, ลบเมื่อหมดความจำเป็น, **แจ้งเหตุรั่วไหลภายใน 72 ชั่วโมง**

**ROPA (ม.39)** — บันทึกกิจกรรมการประมวลผล อย่างน้อย 8 รายการ

**DPO (ม.41-42)** — COM7 มีอยู่แล้ว

**ส่งข้อมูลข้ามพรมแดน (ม.28-29)** — ประเทศปลายทางต้องมีมาตรฐานคุ้มครองเพียงพอ หรือมี BCR/SCC ที่ สคส. รับรอง
→ เกี่ยวกับ QuickSight/Amazon Q ใน us-east-1, Macie ที่ต้อง replicate ไป Singapore, และ Braze

**บทลงโทษ** — ปรับทางปกครองสูงสุด 5 ล้านบาท (ข้อมูลอ่อนไหว) / 3 ล้านบาท (ทั่วไป) · โทษอาญาสูงสุด 1 ปี เฉพาะข้อมูลอ่อนไหว · ความรับผิดทางแพ่งไม่ต้องพิสูจน์เจตนา + ค่าเสียหายเชิงลงโทษสูงสุด 2 เท่า

**บริบทการบังคับใช้** — สคส. เริ่มปรับทางปกครองจริงจังตั้งแต่ ส.ค. 2568 (รวมกว่า 21.5 ล้านบาท) ปัญหาที่พบบ่อย: ไม่แต่งตั้ง DPO / มาตรการความปลอดภัยไม่พอ / **ไม่มีสัญญากับ Data Processor** / แจ้งเหตุรั่วไหลล่าช้า

---

## Access control — IAM is not enough

`ARC-10` Data Access Control ระดับข้อมูลลูกค้า — มีแต่ไม่ละเอียดพอ, P1

> "หน้า 13 ระบุ User Role & Permission ในบริบท Operation [แต่] ยังไม่ครอบคลุมการเข้าถึงข้อมูลลูกค้าข้าม BU ซึ่งเป็นประเด็น PDPA โดยตรง"
> ผลกระทบ: "พนักงาน BU หนึ่งเข้าถึงข้อมูลลูกค้าของอีก BU ได้โดยไม่มีฐานทางกฎหมายรองรับ"

AWS Proposal มีแค่ IAM ระดับ bucket ซึ่งเขียนกฎระดับ column ไม่ได้
**AWS Lake Formation ไม่อยู่ใน proposal** — เป็นบริการที่ทำ column/row-level access control ได้ `[อนุมาน]`

---

## PII Protection

> **2026-11-10 — ข้อมูลส่วนบุคคลในฐานใหม่:** ITEC-Rep `Customer2` ถูกตัดเหลือ `CusCode` · `Name` · `CRMID` (นามสกุล เบอร์ อีเมล เลขบัตร วันเกิด ว่างหมด) แต่ **`Cus2Address` ยังมีที่อยู่จริง 5.6M แถว** · CRM `customer_master` มีเบอร์ 20.5M · อีเมล 11.1M · `member_auth.identity_no` 155k · `members.pdpa_consents` = JSON array `{id, consent}` → [[ITEC-Rep Overview]] · [[CRM - Data Dictionary]]

`ARC-09` Tokenization / Encryption ของ Citizen ID — **ขาด**, P1

> "เป็นข้อมูลที่มีความเสี่ยงสูงสุดในรายการทั้งหมด ต้องระบุมาตรการ encryption at rest, tokenization และ role-based access ให้ชัด"

**Macie ยังไม่เปิดใน ap-southeast-7** ตาม AWS Proposal — ทางเลือกคือ replicate ไป Singapore (ติดเรื่องข้ามพรมแดน) หรือรอ

รวมกันแล้วแปลว่าตอนนี้ยังไม่มีเครื่องมือค้นหา PII อัตโนมัติ และ field ที่เสี่ยงที่สุดก็ยังไม่ถูกป้องกันเป็นพิเศษ → **การจัดประเภท PII ต้องทำด้วยมือตอน survey** `[อนุมาน]`

---

## Lineage & Audit

`ARC-11` Data Lineage + Audit Trail — **ขาด**, P2

> "หน้า 3 ระบุ Audit & Risk Management เป็นขอบเขต [แต่] ยังไม่ลงรายละเอียดถึงระดับ lineage ของข้อมูลลูกค้า ว่าข้อมูลมาจากไหน ผ่านการแปลงอะไรบ้าง"
> ผลกระทบ: "ตอบคำถามผู้ตรวจสอบและ DPO ไม่ได้ว่าข้อมูลชุดนี้มาจากที่ใด"

สิ่งที่ช่วยอยู่แล้ว: Medallion เก็บ Raw ไว้ไม่ลบไม่แก้ · CloudTrail ทำ API audit · คอลัมน์ `SOURCE_SYSTEM` และ `Source Customer ID`

ที่ขาดคือบันทึกว่า **transformation ไหนทำอะไรกับข้อมูล** `[อนุมาน]`

---

## Work to do

| งาน | อ้างอิง |
|---|---|
| ออกแบบ cross-entity consent + orchestration | Framework slide 6 vs 8 |
| จัดทำ ROPA | ม.39 |
| Runbook แจ้งเหตุรั่วไหล 72 ชม. | ม.37 |
| ทบทวน cross-border transfer (QuickSight, Macie, Braze) | ม.28-29 |
| กลไกรองรับสิทธิเจ้าของข้อมูล 8 ข้อ | ม.30-36 |
| นิยาม retention + erasure workflow | CNS-06 |
| ตรวจสอบสัญญากับ Data Processor | ม.37 |
| พิจารณา Lake Formation | ARC-10 |

**ยังไม่มีเจ้าของงานเรื่อง consent** ทั้งที่รายงานจัดเป็นอันดับ 2

## ข้อมูลที่ห้ามเก็บใน Data Lake

| ข้อมูล | เหตุผล | ทางออก | ที่มา |
|---|---|---|---|
| **รายละเอียด NCB** (เครดิตบูโร) | ข้อมูล sensitive | เก็บเฉพาะ Indicator สูง/กลาง/ต่ำ หรือ flag | ประชุม 2026-08-27 |
| **`STATEMENT_FILE_PASSWORD`** | รหัสผ่านไฟล์ statement ธนาคารลูกค้า 79,067 แถว | ไม่ ingest เลย | probe K2 |
| **Pre-Shared Key ของ VPN** | ความลับของระบบเครือข่าย | env var / password manager บนเครื่อง | [[Network & VPN]] |
| **รหัส CRM DB · Outline VPN key** | สิทธิ์เข้าฐานลูกค้า CRM | ห้ามจดในโน้ต / repo · ใช้ env var (`CRM_USER` / `CRM_PWD`) | [[CRM Customer Field Survey]] |

> **2026-11-10:** AWS ยกเลิกแล้ว ([[Decisions|D-21]]) — ประเด็น region / Macie / QuickSight ข้ามพรมแดนด้านล่าง **ไม่เกี่ยวแล้ว** · ประเด็นใหม่บนเครื่อง PC: ใครเข้าเครื่องได้ · เข้ารหัสดิสก์และ backup · สิทธิ์ระดับ column ใน MySQL (GRANT / view) · log การเข้าถึง `[อนุมาน]`

### Region ของ AWS Service (ยืนยัน 2026-08-27)

Minimum requirement service **อยู่ที่ไทยทั้งหมด** → ตัดประเด็นข้อมูลออกนอกประเทศไปได้
**ยกเว้น Macie และ SNS** ที่ยังไม่อยู่ที่ไทย — ต้องประเมินผลกระทบแยก

## 🔴 PCI-DSS — เลขบัตรเครดิต

**เป็นคนละกฎกับ PDPA และเข้มกว่า**

แบบสำรวจ ITEC (2026-08-28) มีคำขอ `credit card no` พร้อมหมายเหตุ *"จริงๆอยากได้ทุกตัว"*

| ข้อมูล | อยู่ที่ | ท่าที |
|---|---|---|
| **เลขบัตรเต็ม (PAN)** | `ci.creditcard_trn_bank.BANK_CC_NO` · `BANK_CREDIT_CARD_NO` · `BANK_CREDIT_CARD_NO2` · `rpt.raw_bank_trans.[CC NO_]` | **ห้าม ingest** |
| BIN 6 ตัวหน้า | `BANK_FIRST6` · `[FIRST 6-DIGIT]` | ใช้ได้ — บอกธนาคาร/ประเภทบัตร |
| 4 ตัวท้าย | `BANK_LAST4` · `ITEC_LAST4` | ใช้ได้ |
| `APPROVAL CODE` + `TERMINAL ID` + วันที่ | ทุก view บัตร | **ใช้จับคู่รายการได้โดยไม่ต้องมีเลขบัตร** |

**ข้อเสนอ:** ตอบกลับว่าให้ BIN + 4 ตัวท้าย ซึ่งตอบโจทย์ analytics ได้เกือบทั้งหมด
**ต้องได้ความเห็น legal / DPO ก่อนตัดสิน** ไม่ใช่ดุลพินิจทีมข้อมูล → [[ITEC Data Requirement Survey]]

---

## เชื่อมกับโน้ตอื่น

[[Customer Identity]] · [[Open Questions & Risks]] · [[CRM Overview|Braze]] · [[AWS Services]]
