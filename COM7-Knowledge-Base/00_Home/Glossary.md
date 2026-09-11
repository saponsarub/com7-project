# Glossary

---

## Systems and names in COM7 documents

| คำ                        | ความหมาย                                               | ที่มา                    |
| ------------------------- | ------------------------------------------------------ | ------------------------ |
| **ITEC**                  | ระบบหลักธุรกิจค้าปลีก IT · ระบบเดียวที่ป้อน CRM ตอนนี้ | Data Framework, Timeline |
| **K2**                    | ระบบสินเชื่อเดิมของ UFUND · ฐาน `HPCOM7` · **ทีม dev ของบริษัทเขียนเอง · on-premise** | ClickUp, union SQL, แจ้งด้วยวาจา 2026-09-02 |
| **ITOS**                  | ระบบ collection ของ UFUND · ฐาน `ILOAN_COLLECTION`     | schema wiki              |
| **TFF**                   | บริษัท ธันเดอร์ ฟิน ฟิน จำกัด                          | `M_COMPANY` ใน ITOS      |
| **UFund / UFUND**         | ธุรกิจสินเชื่อ อยู่ใต้ TFF ตาม Timeline                | Timeline                 |
| **GI / GI CORE**          | ระบบหลักปัจจุบันฝั่ง EV/AION                           | ClickUp, schema.prisma   |
| **AION**                  | แบรนด์รถ EV                                            | ClickUp                  |
| **AION DMS**              | ระบบ vendor — บันทึกเขียนว่า "ของจีน"                  | ClickUp                  |
| **EV7 / EV7CORE**         | ธุรกิจและระบบฝั่ง EV7                                  | Timeline, ClickUp        |
| **EVTRACKING**            | ระบบที่ยังมีบางรายการของ GI ค้างอยู่                   | ClickUp                  |
| **EVSEVEN**               | ชื่อ BU ใน brief เดิม                                  | brief                    |
| **D365**                  | Dynamics 365 · ข้อมูลผ่าน `D365FO_DATALAKE`            | Timeline, SQL            |
| **SAP B1**                | SAP Business One                                       | Timeline                 |
| **iCare**                 | ศูนย์ซ่อม **Apple** 61 สาขา · **ไม่ใช่บริษัทประกัน** | Timeline, [[Smart Care Service]] |
| **Smart Care**            | ศูนย์ซ่อม **ยี่ห้ออื่น (non-Apple)** — แยกจาก iCare ตามยี่ห้อสินค้า | [[Smart Care Service]] |
| **iCare Insurance (ICI)** | บริษัทประกันวินาศภัย 8 ผลิตภัณฑ์ · รถ · ทรัพย์สิน · อุบัติเหตุ | [[iCare Insurance (ICI)]] |
| **7Club / 7Club+**        | โปรแกรมสมาชิก                                          | Data Framework, Timeline |
| **Tech Trade / Tectrade** | ธุรกิจเทิร์นเครื่อง                                    | Timeline, Gap Review     |
| **Braze**                 | platform ส่งข้อความและแคมเปญที่ทีม CRM ใช้             | Data Framework           |
| **BaNANA / BNN**          | แบรนด์ค้าปลีก                                          | `M_COMPANY`, Gap Review  |
| **Studio7**               | แบรนด์ค้าปลีก                                          | `M_COMPANY`, ClickUp     |
| **Alphametrics**          | vendor ที่เขียนคู่มือ Azure Synapse                    | PDF ใน `D:\Azure\`       |

---

## Databases and servers seen in SQL

| ชื่อ | เกี่ยวกับ |
|---|---|
| `ILOAN_COLLECTION` | ITOS |
| `ILOAN_DATASOURCE` | extract ของ ITOS |
| `HPCOM7` | K2 |
| `D365FO_DATALAKE` | D365 Finance & Operations |
| `syndpdev001` | Azure Synapse |
| `PROJECT_1` | view ของ ITEC |
| `TAN_MIS` | MIS |

---

## Codes in the Customer Data Gap Review

| Prefix | หมวด | จำนวน |
|---|---|---|
| `IDN-` | Identity | 12 |
| `DEM-` | Demographic | 7 |
| `TXN-` | Transaction | 5 |
| `DEV-` | Device Ownership | 6 |
| `BHV-` | Behavior | 8 |
| `LOY-` | Loyalty | 4 |
| `DRV-` | Derived / Score | 10 |
| `CNS-` | Consent / PDPA | 6 |
| `DQY-` | Data Quality | 5 |
| `ARC-` | Architecture | 12 |
| `ACT-` | Activation | 6 |
| `MSR-` | Measurement | 7 |

**สถานะที่ใช้:** มีแล้ว · มีแต่ไม่ละเอียดพอ · ขาด
**Priority:** P1 จำเป็นต่อ hyper-personalization · P2 เพิ่มความแม่นยำ · P3 ส่วนเสริม

---

## Technical terms

| คำ | ความหมาย |
|---|---|
| **Medallion** | การแบ่ง data lake เป็นชั้น Bronze / Silver / Gold |
| **Quarantine** | ที่เก็บข้อมูลที่ไม่ผ่านการตรวจ |
| **CDC** | Change Data Capture — อ่านการเปลี่ยนแปลงจาก transaction log |
| **Partition pruning** | การข้าม partition ที่ไม่ตรงกับเงื่อนไข query |
| **Iceberg** | table format รองรับ ACID, schema evolution, time travel |
| **Parquet** | file format แบบ columnar |
| **DQDL** | Data Quality Definition Language ของ AWS Glue |
| **DynamicFrame** | DataFrame แบบยืดหยุ่นของ Glue |
| **CRR** | Cross-Region Replication ของ S3 |
| **RPO / RTO** | Recovery Point / Time Objective |
| **SSOT** | Single Source of Truth |
| **CDP** | Customer Data Platform |
| **RFM** | Recency, Frequency, Monetary |
| **CLV** | Customer Lifetime Value |
| **NBO / NBA** | Next Best Offer / Next Best Action |
| **Golden record** | ข้อมูลลูกค้าฉบับที่ถือเป็นทางการ |
| **Survivorship** | กฎว่าเมื่อข้อมูลขัดกัน ค่าไหนชนะ |
| **ROPA** | Records of Processing Activity ตาม PDPA ม.39 |
| **DPO** | Data Protection Officer |
| **4OD** | นโยบายของ EV7 — ค้างชำระได้ 4 วันแล้วตัดการชาร์จ |
| **BOT** | ธนาคารแห่งประเทศไทย |
| **UTM** | พารามิเตอร์ติดตามแคมเปญ |

---

## Thai terms that appear often

| คำ | ความหมาย |
|---|---|
| ถัง | bucket (S3) |
| ขาด | ไม่มี |
| มีแล้ว | มีอยู่แล้ว |
| มีแต่ไม่ละเอียดพอ | มีบางส่วนแต่ไม่พอใช้ |
| ซ้ำซ้อน | redundant |
| บัตรประชาชน | national ID |
| ความยินยอม | consent |
| ข้อมูลอ่อนไหว | sensitive data |

---

## เชื่อมกับโน้ตอื่น

[[System Inventory]] · [[Source Inventory]] · [[Consent & PDPA]]
