# Source Inventory

ที่มาของข้อมูลทุกอย่างใน vault นี้ · สำรวจ 2026-08-24
**ไฟล์ต้นทางถูกอ่านอย่างเดียว ไม่มีการแก้ไข**

---

## ⚠️ The rule that matters

**อ้างเฉพาะเอกสารต้นทาง ห้ามอ้างไฟล์สรุปที่ AI เขียน**

`D:\aws\README.md` เป็นไฟล์ที่ AI เขียน (ท้ายไฟล์ระบุว่า *"สร้างและปรับปรุงร่วมกับ Claude"*) ไม่ใช่เอกสารบริษัท

vault เวอร์ชันแรกอ้างไฟล์นี้เป็นแหล่งข้อมูล ทำให้ข้อความต่อไปนี้หลุดเข้ามาทั้งที่**ไม่มีในเอกสารจริง**: "1,000 สาขา" · "สมาร์ทโฟน 60%+ ของรายได้" · "Lifestyle Technology Ecosystem" · "New S-Curve" · "iCare COVER+ ร่วมกับ Apple" · "EV7 เช่ารถ EV สำหรับผู้ประกอบการขนส่ง"

ข้อความเหล่านี้ถูกลบออกแล้ว

---

## Source documents used

| # | ที่ | เนื้อหา | ใช้ทำอะไร |
|---|---|---|---|
| 1 | `D:\Clickuptask\` (9 ไฟล์) | ClickUp task export — PoC issue log, datacleanplan, K2&ITOS, GI+EV7, VPN, GuardDuty, Redshift, Bronze/Silver/Gold, S3 design | บันทึกสถานะและปัญหาปัจจุบันที่ละเอียดที่สุด |
| 2 | `D:\Consent_PDPA\COM7 Group Data Framework.pptx` | 16 สไลด์ — framework ทางการของ MIS | ขอบเขต 6 เรื่อง, หลัก consent, CRM current vs propose, customer tracking |
| 3 | `D:\Consent_PDPA\พระราชบัญญัติPDPA.PDF` | ตัวบท PDPA ฉบับเต็ม | มาตราที่กระทบการออกแบบ |
| 4 | `D:\ITOS\` (61 ไฟล์) | Schema wiki ของ `ILOAN_COLLECTION` 55 tables พร้อม sample rows | จำนวนแถว, column, `M_COMPANY`, `M_CHANNEL` |
| 5 | `D:\EV_GI_database\schema.prisma` | 166 models, MySQL | โครงสร้าง GI Core, nullability ของ match key |
| 6 | `D:\aws\Proposal - COM7 Internal Data Lake.pdf` | 12 หน้า · AWS Solution Architect | สถาปัตยกรรมเป้าหมาย, sizing, ingestion paths, security |
| 7 | `D:\aws\COM7 Customer Data Gap Review updated.xlsx` | 5 ชีต · 88 รายการตรวจ | ความพร้อมข้อมูลลูกค้า, ช่องว่างสถาปัตยกรรม, priority |
| 8 | `D:\aws\etl-lab\athena performance.xlsx` + `.pptx` | 45 query runs | ผลวัด performance จริง |
| 9 | `D:\Project Timeline _ Data Team.xlsx` | Timeplan · 11 ระบบ + phase | สถานะ survey, เจ้าของ, ลำดับ phase |
| 10 | `D:\Azure\` (2 PDF โดย Alphametrics) | คู่มือและ training Azure Synapse | เอกสาร platform เดิม |
| 16 | **ประชุม K2 & ITOS 2026-08-27** | ทิศทาง migration · UFUND Student · NCB · Payment/Collection ใน Customer 360 | ปิดคำถามว่า lake จะ ingest อะไร และ K2 จะอยู่ต่อไหม → [[UFUND in Customer 360]] |
| 15 | **`ค่าปรับ ค่าติดตาม.pdf`** — นโยบาย UFUND | POLICIES UPDATED · อัตราค่าปรับ/ค่าติดตามตามขั้น OD · ลำดับการตัดรับชำระ | ตรวจกับ `COLLECTION_OD` แล้วตรงเกือบทุกช่อง → [[K2 - Fee Policy]] · สำเนาที่ `_raw/UFUND-policy-ค่าปรับ-ค่าติดตาม.pdf` |
| 14 | **`ตัวอย่างข้อมูลที่ใช้ในหนังสือบอกเลิกสัญญา.xlsx`** | 33 คอลัมน์ · 3 ตัวอย่างที่ทีมกรอกไว้ | ถอดสูตรได้ว่าหนังสือบอกเลิกสัญญาดึงข้อมูลจากตารางไหนบ้าง → [[K2 - Termination Letter Mapping]] |
| 13 | **`# K2 Database.md` — ชุดความรู้ของทีม** | กฎธุรกิจที่คนใช้งานรู้: วันชำระ 1 และ 16, `RECEIPT_NUMBER` = ชำระแล้ว, ความหมาย `GUARANTOR` / `MT_COLLECTION_COLLECTOR`, เส้นทาง join | สิ่งที่ schema บอกไม่ได้ · ตรวจกับฐานจริงทุกข้อแล้ว → [[K2 - Business Rules]] · สำเนาที่ `_raw/team-knowledge-K2-Database.md` |
| 12 | **ฐาน `HPCOM7` (K2) โดยตรง** | สำรวจ metadata + sample แบบ mask เมื่อ 2026-08-26 ด้วย `scripts\k2\k2_survey.py` / `scripts\k2\k2_samples.py` (read-only) | โครงสร้าง 542 tables, จำนวนแถว, index, join path ที่ทดสอบแล้ว → [[K2 Overview]] |
| 11 | `C:\Projects\Data-Team-Code\` | SQL ที่ทีมใช้จริง + บันทึกออกแบบ AWS (Medalion Archetecture, POC_reveiw) | ชื่อฐานข้อมูลจริง, นิยาม layer, คิวรี่ union K2/ITOS |

---

## ชุดข้อมูลที่รับเข้า 2026-08-28

| # | ไฟล์ | เนื้อหา | ใช้ทำอะไร |
|---|---|---|---|
| 17 | **`COM7_Group_AI_Reference.md`** | นิติบุคคล 9 บริษัท · 13 กลุ่มธุรกิจ · แบรนด์ · การแมประบบต้นทาง · ธุรกิจที่ตัดออก | โครงสร้างกลุ่มฉบับทางการ → [[Group Structure]] |
| 18 | **`crm_fied_description.html`** | พจนานุกรม 3 ตารางของ CRM (`members` · `customer_master` · `member_auth`) — จำนวนแถวจริงอยู่ที่ [[CRM - Data Dictionary]] | ปิดคำถามว่า CRM ผูกกับ ITEC ด้วยอะไร (`members.itec_cuscode`) |
| 19 | **`collection_Union.txt`** | SQL union K2 + ITOS · 58 คอลัมน์ · แท็ก `SOURCE_SYSTEM` | ตรรกะรวม 2 ระบบที่ใช้อยู่จริง + ข้อบกพร่องที่ต้องแก้ → [[Collection Union (K2 + ITOS)]] |
| 20 | **`OD6_UFUND_Collection.xlsx`** | ไฟล์ที่ส่งทีมติดตามจริง · 608 แถว · extract 2026-08-17 | *ground truth* ของเกณฑ์คัด OD6 ที่ production ใช้ → [[OD6 Collection Delivery]] |
| 21 | **`Template จดหมายบอกเลิก.xlsx`** | template หนังสือบอกเลิกรุ่นใหม่ · มีทั้งสัญญา K2 และ ITOS | เพิ่มคอลัมน์ "รวมจำนวนงวดที่ค้าง" · แตกที่อยู่ 4 ช่อง → [[K2 - Termination Letter Mapping]] |
| 22 | **`customer_k2servey.xlsx`** | ตรวจฟิลด์ลูกค้า 98 ตัวว่ามีใน K2 ไหม | 69 มี / 4 ทดแทนได้ / 25 ขาด · **PDPA ไม่มีตรงๆ สักตัว** → [[K2 Customer Field Survey]] |
| 23 | **`Template AWS VPN Site-to-Site.xlsx`** | แบบฟอร์มตั้งค่า IPsec 2 tunnel จาก True IDC | พารามิเตอร์เครือข่าย on-prem ↔ AWS → [[Network & VPN]] · 🔒 **มี PSK ในไฟล์ ห้าม commit** |
| 24 | **`สรุป Ev model china.xlsx`** | เทียบ 88 โมดูลของ Ontime (9680.HK) กับโปรแกรมของ COM7 | พบว่า **K2 อาจให้บริการธุรกิจ EV ด้วย** · พบระบบใหม่ 7 ตัว → [[EV China Benchmark]] |
| 25 | `EV7 model China.pdf` | เอกสารนำเสนอ Ontime ฉบับเต็ม 12 MB | **ยังไม่ได้อ่าน** — สรุปย่อใช้จากไฟล์ #24 ไปก่อน |

### สิ่งที่ชุดข้อมูลนี้เปลี่ยนไปจากที่เคยเข้าใจ

| เดิมเข้าใจว่า | ความจริง | หลักฐาน |
|---|---|---|
| วันครบกำหนดชำระคือวันที่ 1 และ 16 | **จริงเฉพาะ K2** — ITOS ใช้ 14, 20–23, 26, 27 | template หนังสือบอกเลิกรุ่นใหม่ |
| เกณฑ์คัด OD6 คือค้างจริง 6 งวด | production ใช้แค่ `STATUS_ID = 48` → ได้ 608 ราย แต่ค้างจริง 6 งวดแค่ 198 ราย (33%) | `OD6_UFUND_Collection.xlsx` |
| K2 คือระบบของ UFUND | **[ต้องยืนยัน]** เอกสาร EV ระบุว่า K2 ทำใบแจ้งหนี้/บิลค้างให้ธุรกิจ EV ด้วย | `สรุป Ev model china.xlsx` |
| ยังไม่รู้ว่า CRM ผูกกับ ITEC ยังไง | **`members.itec_cuscode`** | `crm_fied_description.html` |
| K2 ขาดข้อมูลลูกค้าเยอะ | ขาดจริงแค่ 25 จาก 98 และส่วนใหญ่เป็นข้อมูลของ BU อื่น ไม่ใช่ของ K2 | `customer_k2servey.xlsx` |

---

## บันทึกประชุมที่รับเข้า 2026-08-28

| # | ไฟล์ต้นฉบับ | ประชุม | โน้ต |
|---|---|---|---|
| 26 | `Meeting_ufund365_17_08_2026.txt` | UFUND — K2 และ ITOS (หัวเอกสารระบุ 27/08/2026 ชื่อไฟล์ระบุ 17) | [[2026-08-27 UFUND K2 และ ITOS]] |
| 27 | `Meeting_aws365_27_08_2026.txt` | AWS Data Lake 27/08/2026 16:00 | [[2026-08-27 AWS Data Lake]] |
| 28 | `Meeting_ERP365_26_08_2026.md` | ERP 26/08/2026 | [[2026-08-26 ERP]] |

## สำรวจฐาน ITEC 2026-08-28

| # | ที่มา | เนื้อหา | ใช้ทำอะไร |
|---|---|---|---|
| 29 | **ฐาน MIS (ITEC) โดยตรง** — `192.168.43.250,18963` | สำรวจ metadata + โปรไฟล์ + ทดสอบ join ด้วย `scripts/itec/*.py` (read-only) | 23 view · 297 คอลัมน์ · จำนวนแถว · เส้นทาง join ที่ทดสอบแล้ว → [[ITEC Overview]] |
| 30 | `ITEC product dimension.txt` | SQL ที่ทีมใช้สร้าง `ci.clean_item_category_itec` — flag 66 ตัวจาก LIKE | เข้าใจที่มาของฟิลด์ `IS_*` → [[ITEC-MIS - Data Dictionary]] |
| 31 | `scripts/legacy/TESTCONNECT.py` | สคริปต์เชื่อมต่อฐาน MIS ของทีม | จุดตั้งต้นของการสำรวจ · 🔴 รหัสผ่านเดิมอยู่ใน git history |

| 34 | `D:\Newdatabase.txt` (ไฟล์ของผู้ใช้ 2026-11) | ค่าเชื่อมต่อ ITEC-Rep `10.100.101.50` / `SSSynced50` + CRM — **มีรหัสผ่านเป็นข้อความธรรมดา** | ย้ายเข้า env `ITEC_*` / `CRM_*` แล้ว · ควรลบไฟล์ · ห้ามคัดลอกรหัสลง vault → [[ITEC-Rep Overview]] |
| 33 | อีเมล Tanapol.T (ทีม Inno) 4 พ.ย. 2026 *"ขอสิทธิ์การ connect CRM database"* | host ฐาน CRM (Aurora MySQL read-only) · user 3 คน · คู่มือ + key Outline VPN | เข้าฐาน CRM — **รหัสและ key ไม่จดลง vault** → [[CRM Customer Field Survey]] |
| 32 | `Copy of ITEC data requirement_reply1.xlsx` | แบบสำรวจ 77 ฟิลด์ที่ Data Lake ต้องการจากค้าปลีก + คำตอบจากเจ้าของระบบ | 39 มี / 4 ทดแทน / 21 ไม่มี / 13 ไม่ตอบ → [[ITEC Data Requirement Survey]] |

**ไฟล์ผลลัพธ์:** `02_System/_raw/itec-views.csv` · `02_System/_raw/itec-columns.csv`

---

## Found by following references in the documents

| เจอ | เจอจาก | ทำไมสำคัญ |
|---|---|---|
| `D:\Project Timeline _ Data Team.xlsx` | กวาดหาไฟล์ชื่อ Timeline | tracker ที่ใช้งานจริง — เป็นแกนของ System Inventory |
| **Tech Trade** | Timeline 1.2.2 + Gap Review DEV-04 | BU/ระบบที่ไม่อยู่ใน brief เดิม เป็นเจ้าของข้อมูลเทิร์นเครื่อง |
| **Braze** | Data Framework slide 8 + Gap Review ARC-01 | platform activation ปัจจุบัน และเป็นประเด็นว่าไม่ใช่ CDP |
| `M_COMPANY` มีรายชื่อบริษัท 18 รายการ | อ่าน table wiki ของ ITOS | **ยืนยันว่า TFF เป็นนิติบุคคล** — สำคัญต่อเรื่อง consent |
| `M_CHANNEL` เป็นช่องทางชำระเงิน | อ่าน table wiki ของ ITOS | **Dtac ในนี้คือจุดรับชำระ ไม่ใช่ร้านในเครือ** — แก้ความเข้าใจผิดจาก brief |
| `D365FO_DATALAKE`, `syndpdev001` | SQL ใน Data-Team-Code | ชื่อฐาน/server จริงเบื้องหลัง D365 และ Synapse |
| `ILOAN_DATASOURCE`, `HPCOM7` | คิวรี่ union K2/ITOS | ฐานจริงของ ITOS และ K2 |
| **`PERSON.TAX_ID` = เลขบัตรประชาชน** | query `HPCOM7` ตรง | ปิดคำถามเปิดว่า K2 เก็บเลขบัตรที่ไหน — มี 404,627 จาก 404,749 แถว |
| **`ZZ_PRODUCT_K2_ITOS_mapping`** | ไล่ดูตารางใน `HPCOM7` | มีคนทำ mapping สินค้า K2↔ITOS ไว้แล้ว 593 แถว เมื่อ ก.ย. 2025 |
| **`STATEMENT_FILE_PASSWORD`** | ไล่ดูตารางใน `HPCOM7` | รหัสผ่านไฟล์ statement ธนาคาร 79,067 แถวอยู่ในฐาน — ประเด็น security |
| AION DMS, EV7CORE, EVTRACKING | ClickUp GI+EV7 | ระบบฝั่ง EV ที่ทับซ้อนกัน |

---

## Checked and not used

| ที่ | เหตุผล |
|---|---|
| `D:\aws\README.md`, `readme.txt` | **ไฟล์ที่ AI เขียน ไม่ใช่เอกสารบริษัท** |
| `D:\EV_GI_database\node_modules\` | dependency ไม่มีข้อมูลธุรกิจ |
| `C:\Projects\Data-Team-Code\.vs\`, `.git\` | ไฟล์ภายในของ IDE/VCS |
| `D:\aws\Test_Spark\`, `D:\aws\etl-lab\` (โค้ด) | lab ฝึก ETL ส่วนตัว ไม่ใช่ production ของ COM7 — อ้างเฉพาะปัญหา Spark ANSI mode ที่เจอจริง และระบุที่มาไว้ชัด |
| `D:\UI Guideline.pptx` | ไม่เกี่ยวกับสถาปัตยกรรมข้อมูล |
| `C:\Projects\my-first-project\` | repo ฝึก Git — **แต่ `DatabaseK2.py` ในนั้นคือจุดตั้งต้นของ survey K2** และมี credential ฐาน production hardcode อยู่ |

---

## Documents referenced but not found

- `COM7-DataLake-Project-Timeline.xlsx` — `D:\aws\README.md` อ้างว่ามี 9 phase 50 subtask **ไม่มีบนดิสก์** และ README นั้นเป็นไฟล์ที่ AI เขียน จึงไม่ยืนยันว่าไฟล์นี้เคยมีจริง
- `crm_fied_description.html` — CRM data dictionary ที่บันทึกประชุม GI+EV7 ระบุ
- **ITEC schema / data dictionary** — survey เป็น Done แต่ไม่พบเอกสาร
- **K2 data dictionary** — ClickUp ระบุว่าได้จากพี่เนตรแล้ว แต่ไม่อยู่ในโฟลเดอร์ที่ตรวจ
- Architecture diagram (Figure 1) จาก AWS proposal — เป็นรูปภาพ

---

## Vault revision history

| วันที่ | ทำอะไร |
|---|---|
| 2026-08-24 | สร้างครั้งแรก 95 ไฟล์ 10 โฟลเดอร์ |
| 2026-08-24 | จัดใหม่เหลือ 23 ไฟล์ 5 โฟลเดอร์ (รวมโน้ตที่ทับซ้อน) |
| 2026-08-24 | **ตรวจสอบความถูกต้องทั้งหมด** — ลบข้อมูลที่มาจากไฟล์สรุปของ AI, แยก `[อนุมาน]` ออกจากข้อเท็จจริง, เพิ่มข้อมูลจาก `M_COMPANY` และ `M_CHANNEL` ที่ควรอ่านตั้งแต่แรก |

---

## เชื่อมกับโน้ตอื่น

[[System Inventory]] · [[SSOT Roadmap]] · [[People & Teams]] · [[Glossary]]
