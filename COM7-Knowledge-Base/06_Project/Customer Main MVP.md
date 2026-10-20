# Customer Main MVP

ผลงานรูปธรรมแรกของโครงการ SSOT ที่ CBO ขอ: **map ลูกค้าแต่ละ BU** และ **ตาราง customer main** · เป้าส่ง **ธันวาคม 2026**
ร่างเมื่อ 2026-10-06 · ข้อเสนอของทีมข้อมูล ยังไม่ได้รับการอนุมัติ · ส่วนที่เป็นความเห็นติดป้าย `[อนุมาน]`

ฐานข้อมูลที่ใช้ → [[Customer Identity]] · [[SSOT Roadmap]] · [[Current Status]] · [[Medallion Layer Definition]] · [[Consent & PDPA]]

---

## สรุปข้อเสนอ

แบ่งงานส่งมอบเป็น **2 ชิ้น** เพราะความเสี่ยง PDPA ของสองชิ้นนี้ต่างกันมาก

| ชิ้นงาน | คืออะไร | ความเสี่ยง PDPA | ส่งได้ธันวาไหม |
|---|---|---|---|
| **① Customer Map** | dashboard ตัวเลขรวม: แต่ละ BU มีลูกค้ากี่คน ซ้อนกับ BU อื่นกี่คน คีย์ไหนจับคู่ได้กี่ % | ต่ำ (ตัวเลขรวม ไม่มีรายชื่อ) | **ได้** |
| **② Customer Main** | golden record หนึ่งแถวต่อหนึ่งคน + ตารางผูก ID ของทุกระบบ | สูง | **สร้างได้ แต่เปิดใช้จริงเมื่อ legal ตอบเรื่อง consent ข้ามบริษัท** |

เหตุผล: [[Consent & PDPA]] ยังค้างคำถามว่า "การรวม record ลูกค้าข้ามบริษัทถือเป็นการเปิดเผยข้อมูลไหม" และยังไม่มีเจ้าของงาน consent
ถ้าเอา ② เป็นงานหลักแล้ว legal ไม่ตอบ ธันวาจะไม่มีอะไรโชว์ แต่ ① แสดงคุณค่า SSOT ได้ทันที เช่น "ลูกค้า UFUND X% เคยซื้อของที่ร้าน ITEC" ซึ่งตรงกับภาพ cross-sell ที่ CBO ต้องการ `[อนุมาน]`

---

## ขอบเขต Wave 1

เลือกระบบที่ survey แล้วและมีคีย์เชื่อมกันจริง

| BU / ระบบ | ข้อมูลลูกค้า | คีย์จับคู่ | สถานะ |
|---|---|---|---|
| **UFUND: K2** | `PERSON` 404,749 แถว | `TAX_ID` (เลขบัตรไม่ซ้ำ 343,249) | survey ✅ · ต่อฐานได้ |
| **UFUND: ITOS** | `S_CUSTOMER` 165,722 แถว | `CUST_CARDNO` | มี schema · ยังไม่ได้ต่อฐานเอง |
| **CRM / 7Club** | สมาชิก ~22M | `citizen_no` · `phone` · `itec_cuscode` | survey ✅ · ❌ **ยังไม่มี connection** |
| **ITEC (ค้าปลีก)** | ผ่าน `crmid` | `crmid` → CRM (จับคู่บิลได้ 89.2%) | survey ✅ |
| GI Core / EV7 | `IdentityCard` (nullable) | เลขบัตร (ถ้ามี) · เบอร์ | ยังไม่ได้ต่อฐาน · **เป้าเสริม** |
| **D365 F&O** | ไม่ใช่แหล่งตัวตนลูกค้า (D-18) · **ใช้เป็นแกน BU** ของ map | `CompanyCode` | สำรวจฐานจริงแล้ว 2026-09-23 → ดูหัวข้อถัดไป |
| iCare · Tech Trade · SAP B1 | — | — | Wave 2 (2027) |

เส้นทางเชื่อมที่ยืนยันแล้ว
```
ITEC crmid ──► CRM member ──► customer_master.citizen_no ══ เลขบัตร ══► K2 TAX_ID / ITOS CUST_CARDNO
```
⚠️ **ยังไม่เคยทดสอบ join จริงระหว่าง CRM กับ K2** ต้องทดสอบเป็นอย่างแรกเมื่อได้ connection CRM

---

## D365 F&O: ผลสำรวจที่กระทบแผนนี้

ที่มา → [[D365 F&O Overview]] (สำรวจฐานจริง 2026-09-23) · [[D365 F&O - Query Cookbook]]

### ① BU มี 21 บริษัท ไม่ใช่ 3 — ต้องตกลงว่า map แสดง BU ไหน

`Transaction_FO.CompanyCode` มี 21 ค่า · `tm_FinDimValueSet` มีบริษัทเพิ่มอีก (`PRIME` `TFF` `ITEC` `C7H` `NOVUS` `SKH` `GIH` `ICI`) ที่ไม่มีใน `Transaction_FO`

| CompanyCode | ชื่อ | สัดส่วนรายการสต็อก | สถานะข้อมูล |
|---|---|--:|---|
| `com7` | COMSEVEN | 91.1% | สดรายวัน |
| `dou7` | Double7 | 4.8% | สดรายวัน |
| `bnn` | Adept | 1.9% | สดรายวัน |
| `drph` | ไม่รู้ | 1.3% | **หยุดตั้งแต่ ก.ค. 2026** |
| `lor` | ไม่รู้ | 0.6% | สดรายวัน |
| `drl` | ไม่รู้ | 0.1% | **หยุดตั้งแต่ ม.ค. 2024** |
| `gi` + `gi01`–`gi12` | GI (12 บริษัท) | 0.1% | สดรายวัน |
| `pss` · `nov` | ไม่รู้ | ~0% | — |

**ใช้ทำอะไร:** ตาราง master บริษัท/BU สำหรับแกนของ map (`dim_bu`) และติดป้าย BU ให้ลูกค้าตามบริษัทที่ซื้อ
**ขาด:** ชื่อเต็มของ `drph` `lor` `drl` `pss` `nov` `skh` `gih` `gi01`–`gi12` — ต้องถาม MIS-ERP

### ② ลูกค้าของ BU ค้าปลีกอื่น (Double7 · Adept · lor) อยู่ระบบไหน — รู้แล้ว 1 จาก 3

**อัปเดต 2026-10-08:** **Double7 ใช้ Dynamics 365 Business Central (LS Retail)** — ข้อมูลไหลเข้า Azure Synapse เป็น `raws.BC_D7_*` (เช่น `raws.BC_D7_Trans_Sales_Entry`) → [[Other Systems]] · [[ADLS Gen2 to S3]]
LS Retail มักมีตารางลูกค้า/สมาชิกของตัวเอง `[อนุมาน — ยังไม่ได้ดูตาราง BC จริง]` → ลูกค้า Double7 อาจดึงได้จาก BC ผ่าน Synapse หรือจากฐาน BC ตรง · Adept · lor ยังไม่รู้

ITEC ไม่แบ่งบริษัท (`dim_item_itec` ไม่มี BU) และ CRM/7Club ยังไม่รู้ว่าครอบคลุมบริษัทไหนบ้าง
**ถ้าลูกค้า Double7 / Adept ไม่ได้อยู่ใน ITEC/CRM** map ธันวาจะไม่มี BU เหล่านี้ ทั้งที่เป็น BU ค้าปลีกที่ใหญ่รองจาก com7
ที่ประชุม GI+EV7 จับคู่ **GI กับ Banana** ไว้ → [[GI + EV7 to 7Club]] — ถ้า Banana ไม่มีข้อมูลลูกค้าเข้า pipeline คู่นี้ทำ cross-sell ไม่ได้ `[อนุมาน]`

### ③ D-18 ยังไม่ได้พิสูจน์จากฐานจริงครบ

สิ่งที่สำรวจแล้วคือฝั่งสต็อก/จัดซื้อ (`Transaction_FO` · `purchtable` · `vendtable` · `dirpartytable`) **ไม่เจอข้อมูลลูกค้า** — PII ชื่อลูกค้าเจอแค่ 4 แถวจาก 104.8M ที่เป็นข้อมูลเพี้ยน
แต่มีตารางฝั่งขายที่**ยังไม่ได้แตะ**: `custinvoicetrans` 118M แถว (บรรทัดใบกำกับลูกค้า) · `salesline` 106M แถว
ใน D365 มาตรฐาน ตารางเหล่านี้มีบัญชีลูกค้า (`CustAccount` / `InvoiceAccount`) — อาจเป็นลูกค้าองค์กร/ขายส่ง หรือบัญชีเงินสดรวม (walk-in) `[อนุมาน]`
`dirpartytable` (114,573 แถว) ที่ใช้หาชื่อผู้ขาย เป็นตาราง party กลางของ D365 ซึ่งเก็บทั้งผู้ขายและลูกค้าได้ `[อนุมาน]`
**ต้องตรวจ 1 ครั้ง** ก่อนปิดประเด็นว่า D365 ไม่ใช่แหล่งลูกค้าของ BU ไหนเลย

---

## Pipeline

```
 ต้นทาง (on-prem)            AWS (ap-southeast-7)
 ───────────────            ────────────────────────────────────────────────────────────────
 K2  PERSON/ADDRESS ─┐
 ITOS S_CUSTOMER/TEL ┤ DMS full load   RAW            BRONZE (Iceberg)      SILVER (ยังแยก BU)
 CRM members/master ─┼── + Client VPN ─► ไฟล์ดิบ ─────► ตามต้นทาง ───────────► customer_k2
 ITEC dim_mem/sales ─┤   (ทุกคืน 23:30)  ตาม BU          snapshot รายวัน         customer_itos
 GI Core customer ───┘                                  (snapshot diff D-20)    customer_crm
                                                                                customer_itec
                                                                                customer_gi
                                                                                 + quarantine
                                                                                     │
                                         ┌───────────────────────────────────────────┘
                                         ▼
                              IDENTITY (ชั้นแยก สิทธิ์จำกัด)
                              1. รวม candidate จากทุก source
                              2. จับคู่ตามกฎ T1→T3
                              3. จัดกลุ่ม (connected components)
                              4. ออก / คง customer_main_id
                              5. merge log
                                         │
                       ┌─────────────────┼──────────────────────────┐
                       ▼                 ▼                          ▼
                GOLD customer_main   GOLD customer_xref        GOLD customer_bu_summary
                1 แถว / 1 คน         main_id ↔ source_id       ตัวเลขรายคน × BU
                (สิทธิ์จำกัด)          (สิทธิ์จำกัด)
                       │
                       ▼
                GOLD customer_map_agg ── ไม่มี PII ──► Athena ──► Power BI   ◄── ① ส่ง CBO
```

ใช้สิ่งที่ได้จาก POC
- ดึงข้อมูลแบบ **DMS → S3 → Glue** เพราะ Glue ต่อ on-prem ผ่าน Client VPN ไม่ได้ → [[Glue Connectivity]]
- Iceberg ทุกชั้นตาม [[Medallion Layer Definition]] · infra เป็น Terraform แบบเดียวกับ [[Reconcile Pipeline - Overview|reconcile pipeline]]
- ตาราง customer ไม่ใหญ่ (หลักแสนถึง 22M แถว) **full snapshot ทุกคืนแล้วหา diff ได้** ไม่ต้องรอ CDC → [[Decisions]] D-20
- ทุก job มี reconciliation log → [[Decisions]] D-15

---

## Silver: ทำความสะอาดรายระบบ

| ฟิลด์ | ทำอะไร |
|---|---|
| **เลขบัตร** | ตัดขีด/ช่องว่าง → ตรวจ **checksum 13 หลัก** (ทิ้งเลขปลอม เช่น `1111111111111`) → **HMAC-SHA256 ด้วย key ใน Secrets Manager** |
| เบอร์มือถือ | เลขไทย → ตัวเลขล้วน → `66` เปลี่ยนเป็น `0` → ต้องตรง `0[689]\d{8}` → เก็บ hash + แบบ masked (`08x-xxx-5678`) |
| อีเมล | trim + lower + ตรวจรูปแบบ |
| ชื่อ | ตัดคำนำหน้า (เรียง `นางสาว` ก่อน `นาง`) · ยุบช่องว่าง · NFC (**ห้าม NFKC** สระอำแตก) |
| จังหวัด | map เป็นรหัสมาตรฐานจากตาราง master (ITOS `HP_COMMON_*`) → [[ITOS - Address & Geography]] |
| ค่าแทน null | `-` · `NULL` · `0000000000` · เบอร์ร้าน → null |
| แถวที่ไม่ใช่บุคคล | ตัดออก เช่น `crmid` ที่มี 10,861 บิลใน 8 เดือน · เบอร์ที่ผูกกับคนเกิน N คน |

checksum เลขบัตรประชาชน: `sum(d[i] × (13 − i)) สำหรับ i = 0..11` แล้ว `(11 − sum mod 11) mod 10` ต้องเท่ากับหลักที่ 13

⚠️ **ห้ามใช้ hash ธรรมดา (SHA-256 เปล่า) กับเลขบัตร** เลขบัตรมีแค่ 13 หลัก ไล่ hash ครบทุกเลขแล้วย้อนกลับได้ในไม่กี่ชั่วโมง ต้องใช้ **HMAC ที่มี secret key** ซึ่งต่างจากความเห็นใน Gap Review (`IDN-05`) ที่เขียนว่า "เก็บด้วย hash" `[อนุมาน — ให้ทีม security ยืนยัน]`

ตัวอย่างโค้ด clean ทุกข้อด้านบน (pandas และ PySpark) → บทเรียน `pandas-pyspark-etl-lab.html` บท "ข้อความ" และ "Mini project"

---

## Identity: กฎจับคู่ v1

deterministic อย่างเดียว ยังไม่ทำ probabilistic

| ระดับ | กฎ | การใช้ |
|---|---|---|
| **T1** | เลขบัตร (HMAC) ตรงกัน | รวมอัตโนมัติ |
| **T2** | เบอร์มือถือตรง **และ** ชื่อจริงตรง | รวมอัตโนมัติ + สุ่มตรวจ |
| **T3** | อีเมลตรง **และ** ชื่อจริงตรง | รวมอัตโนมัติ + สุ่มตรวจ |
| เชื่อมตรง | ITEC `crmid` → CRM `member_id` | ตามระบบ |
| ห้าม | เบอร์อย่างเดียว · ชื่ออย่างเดียว | — |

- **รวมผิดคนร้ายแรงกว่าไม่รวม** (คนหนึ่งเห็นข้อมูลอีกคน) เริ่มจากกฎเข้มก่อน ค่อยผ่อนทีหลัง → [[Customer Identity]] § The two error types
- **`customer_main_id` ต้องคงที่ข้ามรอบ** กลุ่มที่มี ID เดิมใช้ ID เดิม · บันทึกทุก merge/split ลง `merge_log` (ตรงกับ `IDN-12`)
- **วัดผล:** สุ่มคู่ที่ระบบจับมา 200 คู่ต่อกฎ ให้คนตรวจ แล้วรายงาน precision

---

## Gold: Customer Main

ฟิลด์ที่มีประโยชน์และหาได้จริงใน Wave 1

| กลุ่ม | ฟิลด์ | system of record ที่เสนอ |
|---|---|---|
| ตัวตน | `customer_main_id` · `id_hash` · `customer_type` · `match_tier` · `n_source_records` | Identity |
| ข้อมูลพื้นฐาน | ชื่อ · ช่วงอายุ · เพศ · จังหวัด/ภาค | **K2/ITOS ก่อน** (ผ่าน KYC) → GI → CRM |
| ติดต่อ | เบอร์ (masked + hash) · อีเมล · LINE ID | **ข้อมูลล่าสุด** ข้ามระบบ |
| ความยินยอม | consent flags · วันที่ | **CRM** (K2 ไม่มีฟิลด์ PDPA ตรงๆ) |
| ความสัมพันธ์กับ BU | `is_ufund` · `is_itec` · `is_7club` · `is_ev` · `n_bu` · `first_seen` · `last_seen` | xref |
| ค้าปลีก | ยอดซื้อสะสม · จำนวนบิล · ซื้อล่าสุด · หมวด/แบรนด์ที่ซื้อบ่อย | ITEC |
| สินเชื่อ | จำนวนสัญญา · มีสัญญา active ไหม | K2/ITOS (**ไม่เอา NCB** ตาม D-14 · ระดับ OD ถาม legal ก่อน) |
| คุณภาพข้อมูล | `completeness_score` · `data_as_of` | Pipeline |

คอลัมน์ system of record คือ**ร่างแรกของ `DQY-02`** ที่ Gap Review ระบุว่ายังขาด — ต้องให้เจ้าของแต่ละ BU ยืนยัน

ตาราง Gold ทั้งชุด

| ตาราง | grain | สิทธิ์ |
|---|---|---|
| `customer_main` | 1 แถวต่อคน | จำกัด |
| `customer_xref` | 1 แถวต่อ source record | จำกัด |
| `customer_bu_summary` | คน × BU | จำกัด |
| `customer_merge_log` | 1 แถวต่อการ merge/split | จำกัด |
| `customer_map_agg` | ตัวเลขรวม ไม่มี PII | ทีมธุรกิจ / CBO |

---

## Customer Map: สิ่งที่ CBO จะเห็น

- **ลูกค้าไม่ซ้ำทั้งกลุ่ม** เทียบกับผลรวม record ทุกระบบ (เห็นขนาดของลูกค้าซ้ำ)
- **Overlap matrix:** UFUND ∩ ITEC · UFUND ∩ 7Club · ITEC ∩ EV … เป็นจำนวนคน
- **ลูกค้าหลาย BU:** คนที่อยู่ 1 / 2 / 3+ BU
- **คุณภาพคีย์รายระบบ:** % มีเลขบัตร · % เบอร์ถูกรูปแบบ · % จับคู่ได้แต่ละ tier
- **โอกาส cross-sell ตัวอย่าง:** ลูกค้า UFUND ที่ยังไม่เคยซื้อ accessory · ลูกค้า ITEC ที่ใช้เครื่องเกิน 2 ปี (ตัวเลขรวม ไม่มีรายชื่อ)

แสดงตัวเลข overlap คู่กับ % ที่จับคู่ได้เสมอ ไม่งั้นตัวเลข overlap ต่ำจะถูกอ่านว่าลูกค้าไม่ซ้อนกัน ทั้งที่จริงคือคีย์จับคู่ไม่ได้

---

## Timeline ต.ค. – ธ.ค. 2026

| ช่วง | งาน | ผลลัพธ์ |
|---|---|---|
| **6–17 ต.ค.** | ปิด POC · ล็อก scope Wave 1 · **profile คีย์จริง** (null % · checksum ผ่านกี่ % · รูปแบบเบอร์) · ส่งคำถาม legal · ขอ connection CRM | scope + ตัวเลขคุณภาพคีย์ |
| **20–31 ต.ค.** | DMS ดึงตาราง customer ของ K2, ITOS, CRM, ITEC ลง Raw → Bronze · Terraform infra | Bronze ครบ 4 ระบบ |
| **3–14 พ.ย.** | Silver รายระบบ + quarantine + HMAC · **ทดสอบ join CRM ↔ K2 ด้วยเลขบัตรครั้งแรก** | Silver + รายงานกระทบยอด |
| **17–28 พ.ย.** | Identity v1 + xref + merge log · สุ่มตรวจ 200 คู่ต่อกฎ | precision แต่ละ tier |
| **1–12 ธ.ค.** | Gold `customer_main` · `bu_summary` · `map_agg` · dashboard Power BI | ① พร้อม demo |
| **15–19 ธ.ค.** | **Demo CBO** · buffer | — |
| ถ้าทำทัน | GI Core / EV7 เข้า Wave 1 | — |

---

## ทำอะไรต่อ

เรียงจากสิ่งที่บล็อกงานอื่นมากที่สุด

- [ ] **ขอ connection ฐาน CRM** — CRM คือสะพานเดียวระหว่าง ITEC กับ UFUND ถ้าช้า map จะเหลือแค่ UFUND
- [ ] **ส่งคำถาม consent ข้ามบริษัทให้ legal/DPO พร้อมทางออกที่เสนอ** (map เป็นตัวเลขรวม + customer main จำกัดสิทธิ์จนกว่าจะได้คำตอบ) · **หาเจ้าของงาน consent**
- [ ] **นับคุณภาพคีย์จริง** ของ K2 / ITOS / CRM / ITEC ก่อนสัญญาตัวเลขกับ CBO
- [ ] **ยืนยันกับ CBO ว่าผลงานธันวาคือ ①** และ ② พร้อมใช้เมื่อ legal อนุมัติ
- [ ] **ร่าง system of record รายฟิลด์** ส่งเจ้าของ BU ยืนยัน
- [ ] **ปิดเรื่องที่ค้างใน POC** — นิยาม Bronze/Silver/Gold · โครงถัง S3 · Iceberg vs Parquet → [[Medallion Layer Definition]]
- [ ] **ตกลงนิยาม "ลูกค้า Active"** — UFUND ในที่ประชุม 200–300k เทียบที่นับจาก K2 ~103k → [[UFUND in Customer 360]]
- [ ] **ตั้งเจ้าของ survey EV7** — ยังว่างอยู่
- [ ] **ตรวจตารางลูกค้าใน BC LS Retail ของ Double7** (`raws.BC_D7_*`) · ถามว่าลูกค้าของ Adept · lor เก็บอยู่ระบบไหน (ITEC / CRM / POS แยก) — ตัดสินว่า map ธันวามี BU เหล่านี้ไหม
- [ ] **ตรวจ `custinvoicetrans` / `salesline` / `dirpartytable` ของ D365** ว่ามีบัญชีลูกค้าจริงหรือแค่บัญชีเงินสดรวม — ปิด D-18 ด้วยหลักฐาน
- [ ] **ขอชื่อเต็มของ CompanyCode** ทั้ง 21 + บริษัทใน `tm_FinDimValueSet` จาก MIS-ERP → ทำ `dim_bu`

---

## ความเสี่ยง

| ความเสี่ยง | ผลกระทบ | ทางลด |
|---|---|---|
| ไม่ได้ connection CRM ภายใน ต.ค. | map ไม่มีฝั่งค้าปลีก | ขอ export ไฟล์ชั่วคราว |
| legal ไม่ตอบก่อน ธ.ค. | ② ใช้จริงไม่ได้ | ① ไม่ต้องรอ legal |
| K2 → ITOS migration ยังไม่จบ (เป้าสิ้นปี) | ลูกค้า UFUND ซ้ำกันเองระหว่างสองระบบ | dedupe ด้วยเลขบัตรตั้งแต่ Silver |
| คีย์คุณภาพต่ำกว่าที่คิด | overlap ต่ำเกินจริง | รายงาน % จับคู่ได้คู่กับ overlap เสมอ |
| GI Core `IdentityCard` nullable | ลูกค้า EV จับคู่ได้น้อย | ใช้ T2/T3 · ยอมรับว่า EV เป็นเป้าเสริม |
| ลูกค้า Double7 / Adept ไม่อยู่ใน ITEC/CRM | map ขาด BU ค้าปลีกรองลงมา | ถามให้ได้คำตอบใน ต.ค. · ถ้ามี POS แยกให้เป็น Wave 2 และบอก CBO ล่วงหน้า |

---

## เชื่อมกับโน้ตอื่น

[[SSOT Roadmap]] · [[Customer Identity]] · [[Consent & PDPA]] · [[Medallion Layer Definition]] · [[D365 F&O Overview]] · [[K2 Customer Field Survey]] · [[CRM Customer Field Survey]] · [[ITEC Data Requirement Survey]] · [[UFUND in Customer 360]] · [[GI + EV7 to 7Club]] · [[Current Status]]
