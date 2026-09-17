# AWS Services

Service ที่อยู่ในสถาปัตยกรรม COM7 · Region หลัก **ap-southeast-7**

---

## Region

AWS Proposal ระบุว่า storage, ingestion, transformation, analytics อยู่ที่ ap-southeast-7 ส่วน AI และ visualization บางตัวคิดเงินจาก us-east-1

**ข้อเท็จจริงเรื่อง AZ** (จากบันทึกทีม):
- เลือก Region ได้ แต่ S3 Standard เลือก AZ เองไม่ได้
- S3 เก็บ redundant ข้ามอย่างน้อย 3 AZ ใน Region เดียวกัน
- S3 Standard durability 99.999999999% (11 nines), availability 99.99%
- AZ ล่มยังรอด **Region ล่มไม่รอด** ต้องใช้ Cross-Region Replication

---

## Cost figures stated in the documents

| รายการ                        | ตัวเลข                                             | ที่มา      |
| ----------------------------- | -------------------------------------------------- | ---------- |
| GuardDuty ถ้า scan ทุก object | ~3,500 USD/เดือน                                   | PoC review |
| QuickSight                    | ค่าใช้จ่ายส่วนใหญ่มาจาก Amazon Q (AI chat)         | PoC review |
| Redshift Spectrum             | บันทึกว่า "แพงมาก"                                 | PoC review |
| Athena                        | คิดตาม TB ที่ scan                                 | ทั่วไป     |
| Glue                          | คิดตาม compute resources และ runtime ไม่ใช่ต่อ job | PoC review |

Partition pruning ลดข้อมูลที่ scan ได้ 94% จากการวัดจริง → [[Athena Benchmark]]

---

# S3

ที่เก็บ data lake · เป็น object storage ไม่ใช่ filesystem

Key มีหน้าตาเหมือน path แต่จริงๆ เป็น string เดียว:
```
s3://bucket/sales/year=2026/month=03/part-0001.parquet
```
Console แสดงเป็นโฟลเดอร์ให้อ่านง่าย แต่ Athena และ Glue ใช้ **prefix** ทำ partition pruning

**Storage class:** Standard · Intelligent-Tiering · Standard-IA · Glacier

บันทึกทีมเตือนว่า:
> "ไม่ควรเลือก Glacier เพียงเพราะเป็นข้อมูลเก่า เพราะ Glacier มี Retrieval Cost และระยะเวลาขั้นต่ำในการจัดเก็บในบาง Storage Class"

**Security ที่ proposal ระบุ:** Block Public Access · Bucket Policies · Versioning · KMS encryption

**Cross-Region Replication** — asynchronous เลือก replicate ทั้ง bucket หรือเฉพาะบาง prefix/tag ได้
ข้อเสียที่บันทึกไว้: storage cost คูณ 2 · ค่า transfer ระหว่าง region · ต้องคิด RPO · ต้องออกแบบ failover/failback · ต้องจัดการ IAM สองฝั่ง
จุดยืนเบื้องต้น: *"ข้อมูลของ COM7 อาจไม่ต้อง CRR ก็ได้"*

---

# Glue

3 ส่วน:

| ส่วน | ทำอะไร |
|---|---|
| Glue ETL (Spark) | แปลงข้อมูลระหว่าง medallion zone |
| Glue Data Catalog | metadata กลาง |
| Glue Crawler | เดา schema และ partition จาก object ใน S3 |

AWS Proposal ระบุว่า:
> "Both Amazon Athena and Amazon Redshift READ table definitions from the Catalog, providing a consistent schema across query and warehouse engines."

## Cost model

> "AWS Glue ETL Jobs มีค่าใช้จ่ายตาม Compute Resources และ Runtime ที่ใช้ โดยคิดค่าบริการเป็นรายเวลา ไม่ได้คิดง่ายๆ ตามจำนวน Glue Job ที่สร้างขึ้น ดังนั้นการแยก Job ไม่ได้แปลว่าจะประหยัดเงินเสมอไป"

> "ลดปริมาณข้อมูลที่ต้องอ่านและประมวลผลในแต่ละขั้นตอน และเลือก Compute ให้เหมาะกับ Workload"

แต่การแยก job น่าจะช่วยเรื่อง failure recovery และความชัดเจนว่าใครรับผิดชอบอะไร `[อนุมาน]`

## Glue vs plain PySpark

Glue คือ Spark บวก AWS integration — `GlueContext`, `DynamicFrame`, การอ่านผ่าน Data Catalog, `EvaluateDataQuality()` + DQDL, และไม่ต้องดูแล cluster

logic การ clean ที่เขียนเป็น DataFrame operation ธรรมดาน่าจะย้ายมาได้โดยไม่ต้องแก้ ต่างแค่ตอนอ่านและเขียน `[อนุมาน]`

## Crawler caveats

ถ้าไฟล์ใต้ prefix เดียวกันมี schema ไม่เหมือนกัน crawler อาจเดาผิด → ควรรัน crawler บนข้อมูลที่ผ่าน pipeline ที่บังคับ schema แล้ว `[อนุมาน]`

---

# Athena

Serverless SQL บน S3 · **คิดเงินตาม TB ที่ scan**

ทุกอย่างที่ลด bytes ที่ scan ลด cost ในสัดส่วนเดียวกัน

## Measured results (45 query runs)

| สถานการณ์ | Runtime | Data Scanned |
|---|---|---|
| Full scan 6.15M แถว | 14.3–15.6 วินาที | 433 MB |
| กรอง 1 partition | 1.7–2.4 วินาที | 26.35 MB |
| กรอง + cross-region | 4.39 วินาที | 26.35 MB |

3 ข้อสรุป:
1. Partition pruning เร็วขึ้น 8–9 เท่า scan น้อยลง 94%
2. Cross-region ช้ากว่า 2.6 เท่าบน bytes เท่ากัน
3. Iceberg vs Hive-partition ต่างกันไม่ถึง 9% บน full scan

รายละเอียด: [[Athena Benchmark]]

## BI

Athena → Power BI ทดสอบแล้วเชื่อมได้ผ่าน **Athena ODBC** ด้วย Access Key และ Secret Key ที่ admin สร้างให้

AWS Proposal ระบุว่า Athena รันใน VPC

> **หมายเหตุ (2026-09-16):** Athena เป็น serverless — compute อยู่นอก VPC เสมอ · ที่ทำได้คือใช้ VPC Interface Endpoint ให้ traffic ไป Athena API ไม่ออกเน็ต ไม่ใช่ engine รันใน VPC

---

# Redshift

Data warehouse ที่มี compute ของตัวเอง · **เลื่อนไปก่อน รอวัดผล**

PoC review เปรียบเทียบไว้:

**Athena + S3 เหมาะกับ:** Ad-hoc Query · query เป็นครั้งคราว · Data Lake · query บน Parquet/Iceberg · workload ที่ไม่มี query ต่อเนื่องจำนวนมาก

**Redshift เหมาะกับ:** Data Warehouse · query ซับซ้อน · join หลาย table · aggregation จำนวนมาก · concurrent query สูง · dashboard ที่ query ซ้ำๆ · BI workload ที่ผู้บริหารต้องดูบ่อย

## The decision

> "เนื่องด้วยหากต้องการควบคุม cost และ Redshift เหมือนเป็นตัวเสริม ที่ทำให้ query เร็วขึ้น แต่จริงๆ สามารถใช้แค่ Athena ก็ได้ และอยู่ในช่วง POC และยังไม่ได้ทดสอบกับข้อมูลจริง"

เริ่มจาก `S3 (Silver, Gold) → Iceberg + Parquet (Glue) → Athena → BI` แล้วทำ performance test

**จะพิจารณา Redshift เมื่อ:** query ใช้เวลานานเกิน requirement · มี query จำนวนมาก · query มี join/aggregation ซับซ้อน · dashboard ต้องการ response time ต่ำ · Athena cost จาก query volume สูง

**Metric ที่ต้องเก็บมาเทียบ:** Query Runtime · Data Scanned · Query Cost · Concurrent Users · Dashboard Response

**ติดที่:** รอ AWS setup Redshift demo

**Redshift Spectrum** query S3 ตรงโดยไม่ต้องโหลด แต่บันทึกระบุว่า "แพงมาก"

---

# QuickSight

**ไม่ใช้ใน Phase 1**

PoC review ข้อ 6 (Complete):

> "Amazon QuickSight ยังไม่มี Region ในประเทศไทย ทำให้การใช้งานร่วมกับ S3 / Athena ใน Thailand Region ต้องมีการเชื่อมต่อข้าม Region ซึ่งอาจส่งผลต่อ Performance และ Latency เเละยังมีต้นทุนที่สูงสาเหตุหลักมากจาก Amason Q-S (ตัว chat ใน Quick ที่ user เขียน Prompt ได้)"

> "จากผลทดสอบพบว่า Cross-Region ส่งผลให้ Runtime / Latency รวมถึงค่าใช้จ่าย (ค่าใช้จ่ายที่มีสัดส่วนมากที่สุดคือ AI agent chat) เพิ่มขึ้นอย่างมีนัยสำคัญ"

2 ทางเลือกที่บันทึกไว้:
1. ใช้ Power BI แทนใน Phase 1 หรือจนกว่า QuickSight จะรองรับ Thailand Region
2. Replicate ข้อมูลจาก S3 Thailand ไป Region ที่รองรับ โดยต้องพิจารณา PDPA เพิ่ม

---

# GuardDuty

AWS Proposal ระบุว่าใช้ **Malware Protection for S3** สแกน object ก่อนเลื่อนขึ้น Bronze
Findings → EventBridge Rule → Step Functions → SNS
ข้อมูลสะอาดขึ้น Bronze ข้อมูลติดเชื้อค้างใน quarantine

## Cost problem

PoC review ข้อ 2:

> "หาก Scan ข้อมูลทุก Object อาจทำให้เกิด Cost เยอะ (แค่ Amazon Guard Duty) ก็ 3500 us ต่อเดือนแล้ว แต่ข้อมูลส่วนใหญ่มี Source เป็น Database โดยตรง (จากทั้ง cloud และ on premise)"

> "VPN ไม่ได้ทำหน้าที่ Scan Malware โดยตรง เบื้องต้นอาจยังไม่จำเป็นต้อง Scan ข้อมูลทั้งหมด และพิจารณาเป็นราย Source/ประเภทข้อมูลตามระดับความเสี่ยง"

**สิ่งที่ต้องทำก่อน** ตามบันทึก — Data Classification / Threat Model:
> "Data มาจากไหน / เป็น File หรือ Database / มี Sensitive Data หรือไม่ / ข้อมูลมีความสำคัญระดับใด / มีโอกาสถูกนำ Malware เข้ามาหรือไม่"

หมายเหตุ: *"Pipeline Draft แรกๆ ยังไม่มีส่วน Amazon Guard Duty"*

---

# Macie

**ยังไม่เปิดใน ap-southeast-7**

AWS Proposal:

> "Amazon Macie is currently 'Awaited Available on Thailand' — it is not yet available in the ap-southeast-7 region. Macie is therefore included as a roadmap item. Until regional availability, enabling Macie would require either replicating the relevant S3 data to the Asia Pacific (Singapore) region for classification, or waiting for the service to become generally available in Thailand."

ทั้งสองทางมีปัญหา — replicate ไป Singapore ติดเรื่องส่งข้อมูลข้ามพรมแดน หรือรอก็ไม่มีการตรวจหา PII อัตโนมัติ

---

# Connectivity from on-premise

**⚠️ แนวทางเปลี่ยนที่ประชุม 24 ส.ค. 2026 — จะต่อผ่าน VPN Client โดย Vanguard แทน Site-to-Site VPN**

## New approach (current)

**VPN Client โดย Wireguard**`

## Original approach per the AWS proposal

> "AWS Site-to-Site VPN using 30 encrypted tunnels terminated on Virtual Private Gateways"

ยังไม่มีข้อมูลว่าแผนนี้ถูกยกเลิกหรือเลื่อน

## How the two differ `[อนุมาน]`

- **Site-to-Site VPN** เชื่อมเครือข่ายถึงเครือข่าย เปิดค้างไว้ ทำให้ service ใน VPC (เช่น DMS) เข้าถึง database ฝั่ง on-premise ได้ต่อเนื่อง
- **Client VPN** โดยทั่วไปออกแบบให้ client แต่ละตัวต่อเข้าเครือข่าย

ความต่างนี้อาจสำคัญกับ pipeline ที่ต้องเชื่อมต่อเนื่อง — **ต้องถามว่ารองรับ DMS CDC ยังไง**

## Context still valid from the PoC review

> "ปัจจุบัน POC ยังเป็นการทดลองโดยนำ File Upload เข้า AWS แล้วทำ ETL จึงยังไม่ได้ทดสอบที่เชื่อมต่อกับ Database จริงโดยตรง ทำให้ยังไม่ทราบปัญหาที่อาจเกิดขึ้นจริง เช่น Network Latency, Throughput, Connection Stability, Firewall, Database Permission"

**ยังไม่ได้ทดสอบต่อ database จริงเหมือนเดิม** เปลี่ยนแค่วิธีเชื่อม

คำถามเดิมที่บันทึกไว้: *"อนาคตจะมีแพลน ต่อสาย Direct connect (เป็น private) ไหม"* — ยังไม่รู้ว่ายังใช้ได้กับแนวทางใหม่ไหม

---

# DMS

Ingestion Path C ตาม AWS Proposal:

> "Relational database sources are replicated using AWS Database Migration Service (DMS) with Change Data Capture (CDC). Data is encrypted in transit, enabling near-real-time, low-impact replication of database changes into the lake."

**CDC สำคัญกับ COM7 เป็นพิเศษ** เพราะ K2 ไม่มี `CREATE_DATE`/`MODIFY_DATE` จึงดึง incremental ด้วย timestamp ไม่ได้ `[อนุมาน]`

ควรตรวจต่อ source ว่า: CDC เปิดที่ต้นทางไหม · log retention พอไหม · replication user มีสิทธิ์พอไหม · โหลดที่เพิ่มให้ production เท่าไหร่ `[อนุมาน]`

---

# Kinesis Data Firehose

Ingestion Path A ตาม AWS Proposal:

> "COM7 sends data to an API Endpoint (/POST) that is protected by AWS WAF. The endpoint streams all incoming data into Amazon Kinesis Data Firehose, which continuously delivers the records into the data lake landing zone."

> "A complementary AWS Lambda function ('Call REST API') is triggered on a schedule by an Amazon EventBridge rule to pull data from the source REST API (/GET) for scheduled batch retrieval."

Gap Review `ARC-03` ระบุว่า streaming ingestion ยังขาด และ:
> "hyper-personalization ต้องมี streaming หรือ CDC สำหรับ trigger ที่ไวต่อเวลา เช่น cart abandonment ต้องยิงภายใน 30 นาที ไม่ใช่ T+1"

---

# Transfer Family

Ingestion Path B ตาม AWS Proposal:

> "Inbound SFTP traffic reaches AWS Transfer Family through an Elastic Network Interface and a VPC Endpoint secured within a dedicated Security Group. Transfer Family then lands the received files directly into the data lake."

Auth 2 แบบ: Customer Managed User Route (username/credentials) และ Service Managed User Route (username/SSH key) เก็บ credential ใน Secrets Manager

เป็นเส้นทางที่รับไฟล์จากภายนอก จึงน่าจะเป็นเส้นทางที่ควรคง malware scan ไว้ที่สุดถ้าเลือก scan บางส่วน `[อนุมาน]`

---

# Lake Formation

**ไม่มีใน AWS Proposal**

เป็น service ที่ทำ access control ระดับ database, table, column, row พร้อม tag-based access control

เกี่ยวกับ Gap Review `ARC-10` ที่ระบุว่า:
> "พนักงาน BU หนึ่งเข้าถึงข้อมูลลูกค้าของอีก BU ได้โดยไม่มีฐานทางกฎหมายรองรับ"

IAM ที่ proposal มีอยู่คุมได้ระดับ bucket เขียนกฎระดับ column ไม่ได้ `[อนุมาน]`

**ยังไม่มีการตัดสินใจว่าจะใช้ไหม**

---

# Other services in the proposal

**Security:** KMS (encryption at rest) · IAM + MFA · CloudTrail (API audit) · CloudWatch · WAF · Secrets Manager · VPC PrivateLink · Resource Access Manager · Step Functions + SNS

**Ingestion ทางเลือก (ยังไม่ประเมิน):** Glue Crawler · MWAA · AppFlow · DataSync · Amazon MSK · Airbyte

## Region และ PDPA (ยืนยัน 2026-08-27)

**Minimum requirement service อยู่ที่ไทยทั้งหมด** → ตัดประเด็น PDPA เรื่องข้อมูลออกนอกประเทศไปได้

**ยกเว้นตัวที่ยังไม่อยู่ที่ไทย:**

| Service | ใช้ทำอะไร | ต้องทำอะไร |
|---|---|---|
| **Macie** | detect ข้อมูล sensitive / personal | ประเมินผลกระทบ PDPA แยก |
| **SES** | ส่งอีเมล | **ประเมินผลกระทบ PDPA** — ถ้าแนบไฟล์ที่มี PII จะออกนอกประเทศ → [[K2 Termination Automation]] |

### ตรวจความพร้อมของ region ใหม่ 2026-09-03

ตรวจจากเอกสาร endpoint ทางการของ AWS — **แก้ข้อมูลเดิมที่บันทึกว่า SNS ยังไม่อยู่ที่ไทย**

| Service | ap-southeast-7 | ที่มา |
|---|---|---|
| **SNS** | **มี** — `sns.ap-southeast-7.amazonaws.com` | [SNS endpoints](https://docs.aws.amazon.com/general/latest/gr/sns.html) |
| **SES** | **ไม่มี** | [SES endpoints](https://docs.aws.amazon.com/general/latest/gr/ses.html) |
| Redshift + Redshift Serverless | มี | [Redshift endpoints](https://docs.aws.amazon.com/general/latest/gr/redshift-service.html) · [[Redshift]] |

บันทึกเดิมจาก PoC review ระบุว่า SNS ยังไม่อยู่ที่ไทย — น่าจะเป็นข้อมูล ณ ตอนทำ PoC แล้ว service เพิ่งเข้ามาทีหลัง `[อนุมาน]`

**ประเด็นที่ต้องประเมินใหม่คือ SES ไม่ใช่ SNS** — งานไหนที่ต้องส่งอีเมลพร้อมไฟล์ที่มี PII จะติดเรื่องข้อมูลข้ามพรมแดน

**QuickSight ยังไม่มีแผนเปิดที่ไทย** → ต้องหาทางเลือก BI อื่น

### คำถามที่ค้างกับทีม AWS

- มี service ไหนทดแทน **SQL Server Management Studio (SSMS)** ได้
- **Query Editor** ของ AWS เชื่อมกับ database ต้นทางโดยตรงได้ไหม
- ขอสรุป **Minimum Tools** ว่ามีอะไรบ้าง แต่ละตัวทำอะไร ถ้าไม่มีจะทำ process ไหนไม่ได้

---

## เชื่อมกับโน้ตอื่น

[[Architecture]] · [[ETL & Spark]] · [[Athena Benchmark]] · [[Redshift]]
