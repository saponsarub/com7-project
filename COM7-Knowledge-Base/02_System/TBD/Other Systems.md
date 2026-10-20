# Other Systems

ระบบที่ยังรู้น้อย — D365 · SAP B1 · iCare · Tech Trade · Azure Synapse

---

# D365

## What we know

**บทบาทฝั่ง GI:** บันทึกประชุมเรียกว่า **"D365 (GI เก่า)"** และ GI Core ยิงข้อมูลไป D365 ผ่าน RPA

**ที่พบใน SQL:** `D365FO_DATALAKE.dbo.*` — ตารางที่เห็น `inventsum`, `inventtrans`, `inventdim`, `purchline`, `vendtable`

ไฟล์ที่อ้างถึง: `GI/FO_All GI Onhand.sql`, `GI/FullSalesReportFinal.sql`, `GI/GI_PhysicalCost.sql`, `GI/SalesReportTuning.sql`, `PODetial.sql`, `PODetial_Com7.sql`, `VendorCom7Final.sql`, `DRPH/LSStatement.sql`

prefix `FO_` ในชื่อไฟล์ และชื่อฐาน `D365FO_DATALAKE` บ่งชี้ว่าเป็น **Dynamics 365 Finance & Operations** `[อนุมาน]`

query ที่พบเน้น inventory, purchasing, vendor, stock costing

## Relationship with Synapse

Server `syndpdev001` ปรากฏใน query ข้างเคียง และหลาย query join ข้ามทั้ง `syndpdev001` กับ `D365FO_DATALAKE`

Timeline Pilot item 1: **"MS Synapse จาก D365 to AWS directly"** ยืนยันว่ามีเส้นทาง D365 → Synapse
# SAP B1

## What we know

Timeline ระบุเป็น **main system 1.1.7** — แค่นั้น

การถูกจัดเป็น Main System (1.1) แทนที่จะเป็น Other Legacy (1.2) บ่งชี้ว่าน่าจะยังใช้งานอยู่ `[อนุมาน]`
# iCare

| Ref | Track |
|---|---|
| 1.1.6.1 | Insurance |
| 1.1.6.2 | Mobile Service |

> **ตัวธุรกิจ ICI — ขายผลิตภัณฑ์อะไร · เก็บ entity อะไร · ผลต่อ Data Lake** → [[iCare Insurance (ICI)]]
โน้ตนี้เก็บเฉพาะ**ระบบที่มันรันอยู่**

## ICI รันบนระบบอะไร — มีคำตอบแล้วบางส่วน

> **ที่มา:** แจ้งด้วยวาจาจากทีมภายใน **2026-09-02** — **ยังไม่มีเอกสารยืนยัน**

| | ระบบ |
|---|---|
| **ตอนนี้** | ฐานข้อมูล ICI อยู่บน **P&O** |
| **จะย้ายไป** | ระบบ **IDS (K2)** — **on-premise ของบริษัท** |
| **เหตุผล** | P&O ต้องจ่ายค่า **subscription** |

นี่เป็นคำตอบแรกของคำถาม *"iCare รันบนระบบอะไร"* ที่ค้างมาตั้งแต่เริ่ม vault → [[Source System Issues]]

### ผลต่อ Data Lake `[อนุมาน]`

| ผล | รายละเอียด |
|---|---|
| **น่าจะไม่ต้องเปิดการเชื่อมต่อใหม่** | ถ้า ICI ไปอยู่บน K2 on-prem จริง จะ ingest ผ่านเส้นทางเดียวกับ K2 ได้ ไม่ต้องต่อ P&O แยก → [[Network & VPN]] |
| **อย่าเพิ่ง ingest จาก P&O** | ถ้าดึงจาก P&O ตอนนี้แล้วเขาย้ายทีหลัง งานที่ทำจะทิ้งทั้งหมด — ควรรอให้ย้ายเสร็จก่อน |
| **survey 1.1.6.1 ต้องนัดกับแผนย้าย** | ไม่งั้น survey โครงสร้างของระบบที่กำลังจะเลิกใช้ → [[System Inventory]] · ผู้รับผิดชอบ P.Pui |
| **K2 จะถือ 3 ธุรกิจ** | UFUND + EV (ถ้ายืนยัน) + ประกัน — ทำให้คำถามเรื่อง "แยก BU ด้วยคอลัมน์ไหน" สำคัญขึ้นอีก → [[K2 - Data Dictionary]] |

### ยังไม่รู้

- **P&O คืออะไร** — ผู้ให้บริการ SaaS · แพลตฟอร์ม · หรือชื่อฐานข้อมูล ยังไม่มีข้อมูล
- **`IDS` คืออะไร** — ยืนยันแล้ว (2026-09-02) ว่า **K2 คือฐานข้อมูล on-premise ที่ทีม dev ของบริษัทเขียนขึ้นเอง** จึงเหลือคำถามว่า IDS เป็นชื่อโปรแกรมที่ใช้ฐาน K2 ใช่ไหม `[อนุมาน]` · ถ้าใช่ ICI จะเข้าไปอยู่ฐานเดียวกับ UFUND (`HPCOM7`) → [[K2 Overview]]
- **ย้ายเมื่อไหร่** — ยังไม่มีกำหนด
- **ย้ายทั้ง Insurance และ Mobile Service หรือแค่ Insurance**
- ย้ายทั้งฐานหรือแค่บางส่วน

## Health data — not applicable

เคยมีข้อกังวลว่า iCare Insurance อาจมีข้อมูลสุขภาพซึ่งเป็นข้อมูลอ่อนไหวตาม PDPA ม.26

**ได้รับการชี้แจงแล้วว่าเป็นประกันอุปกรณ์ ไม่ใช่ประกันคน** → ข้อกังวลเรื่อง ม.26 ไม่เกี่ยวข้อง

## Why iCare matters

Gap Review ระบุว่า iCare เป็นเจ้าของ 2 field ในหมวด Device Ownership ซึ่งเป็นหมวดที่รายงานจัดเป็น**ช่องว่างอันดับ 1 ของทั้งโปรแกรม**

| ID | Field | สถานะ | เหตุผลในรายงาน |
|---|---|---|---|
| `DEV-03` | Warranty Expiry Date | ขาด | "ใช้ trigger ขายประกันขยายและบริการหลังการขาย" |
| `DEV-05` | Service / Repair / Claim History | ขาด | "สะท้อนความพึงพอใจและความเสี่ยง churn โดยตรง" |
# Tech Trade

**ไม่อยู่ใน project brief เดิม** — เจอจากการตรวจเอกสาร

## Where it was found

1. Timeline item `1.2.2` — "Tech Trade" ใต้ Other Legacy System
2. Gap Review `DEV-04` — Source System และ Owner ระบุว่า "Tectrade"

## What it owns

`DEV-04` **Trade-in History + Eligibility** — สถานะ **ขาด**, P2
เหตุผลในรายงาน: *"ใช้คำนวณข้อเสนอเทิร์นรายบุคคล"*

## Why it matters

Data Framework slide 7 ระบุ historical transaction ที่ CRM ต้องการว่า *"buy, sale, **trade-in**, trn-amt, trn-frequency, first-last trn"*

เทิร์นเครื่องถูกระบุระดับ framework แต่ระบบที่ถือข้อมูลนี้ไม่อยู่ใน brief เดิม `[อนุมาน]`

GI Core มี model `buyback_iphone` ด้วย — กิจกรรมรับซื้อคืนเกิดอย่างน้อย 2 ที่
# Azure Synapse + ADLS

กำลังย้ายมา AWS · PoC issue ข้อ 8

## What we know

**เอกสาร:** PDF 2 ไฟล์ใน `D:\Azure\` เขียนโดย vendor **Alphametrics**
- COM7-02 Enterprise Analytics Platform — Synapse Analytics user manual (31 หน้า)
- COM7-02 Training material — Azure Synapse

**Server:** `syndpdev001` · ตารางที่เห็นใน SQL: `tm_Item`, `tb_SalesInvoice`, `tb_PurchInvoice`, `tm_FinDimValueSet`

prefix `tm_` / `tb_` น่าจะเป็น convention master / transaction `[อนุมาน]`

**Source ที่ป้อนเข้ามา** ตาม PoC review:
> "ปัจจุบันข้อมูลจาก SharePoint 365 / Azure Data Lake Storage ใช้ Azure Synapse"

## จากคู่มือ Alphametrics (อ่านละเอียด 2026-10-08)

| ส่วน | รายละเอียด |
|---|---|
| Workspace | `synw-com7dw-dev` |
| Serverless SQL | `synw-com7dw-dev-ondemand.sql.azuresynapse.net` · lake database `dataverse_com7_…` = ตาราง D365 F&O จาก **Azure Synapse Link** |
| Dedicated SQL pool | **`syndpdev001` คือชื่อ dedicated SQL pool** (Azure SQL Data Warehouse) บน `synw-com7dw-dev.sql.azuresynapse.net` · ตั้งเวลาเปิด **จ.–ศ. 09:00–18:00 · ส.–อา. ปิด** |
| ADLS | **Gen2** · เปิดดูผ่าน Data > Linked > Azure Data Lake Storage Gen2 · Synapse Link profile ชื่อ `stcom7dw001` (น่าจะเป็นชื่อ storage account `[อนุมาน]`) |
| Schema `raws` | `FO_` D365 F&O · `BC_` **Dynamics 365 Business Central (LS Retail)** · `ITEC_` · `MT_` ไฟล์ master จาก SharePoint |
| Pipeline | Synapse pipeline (ไม่ใช่ ADF แยก) · ขับด้วย control table `cfg._bcls_control_table` · `cfg._itec_control_table` · `cfg._master_control_table` · ดึงแบบ watermark (`timestamp` / row version) |
| SharePoint | `/sites/COM7_Team/Shared Documents/Data Lake Source file/…` |
| สิทธิ์ | Entra ID (Synapse Administrator / Synapse SQL Administrator) + SQL login แยกราย BU (`sqluser_com7` `sqluser_dou7` `sqluser_ppw` `sqluser_lor` `sqluser_drph` `sqluser_bnn` `sqluser_gi` `sqluser_nov` `sqluser_pss` `sqluser_skh` `sqluser_c7h`) + **Row-Level Security ตาม Company** |
| Source control | Azure DevOps (POWERBI) |

**คำตอบใหม่ที่ได้**
- **Double7 ใช้ Business Central LS Retail** — ตัวอย่างตาราง `raws.BC_D7_Trans_Sales_Entry` · ต้นทาง `D7$Item` → [[Customer Main MVP]]
- ADLS เป็น **Gen2** · ใช้ **Synapse pipeline** · `syndpdev001` คือ dedicated pool ในชื่อ workspace `-dev`
- ⚠️ เอกสาร training มี **รหัสผ่าน SQL login ทุก BU เป็นข้อความธรรมดา** → [[Source System Issues]]

## Migration approach

> "สำรวจการใช้งานระบบเดิมก่อนว่าใช้ Service และ Function ใดบ้าง จากนั้นนำมาเปรียบเทียบกับ AWS Services ที่เหมาะสม เช่น S3, Glue, Athena และ Redshift และออกแบบ Flow ใหม่"

**วิธีย้าย ADLS Gen2 → S3 ทุกวิธี (DataSync · Glue · data flow · rclone · Python · Synapse SQL · ต้นทางตรง)** → [[ADLS Gen2 to S3]]

## Priority

Timeline Pilot item 1 — เป็นงานแรกของ Pilot นำหน้าแม้แต่ ITEC replication
tag ที่ระบุ: `RPA/GLUE/ AI AGENT`

tag `RPA` บ่งชี้ว่ามี RPA อยู่ในเส้นทาง D365→Synapse ปัจจุบัน `[อนุมาน]`

## D365 F&O — ขอบเขตที่ยืนยันแล้ว (ประชุม 2026-08-26)

**COM7 ใช้ Dynamics 365 Finance & Operations**

| Module ที่ใช้ | Finance · Accounting · Inventory · Sale |
|---|---|
| **นิติบุคคลใน D365** | COM7 · Dou7 (Double7) · GI · GI 1–13 · GI Holding · GI 6 · ICI · BNN → Adept |

| ประเด็น | รายละเอียด |
|---|---|
| **บทบาท** | เก็บข้อมูลทั้งหมดขององค์กรทุก BU — **replicate มาจาก database หลักของแต่ละ BU อีกที** |
| **ไม่มีข้อมูล promotion** | โปรโมชันไม่ได้อยู่ที่นี่ |
| **ไม่มีข้อมูลลูกค้า** | D365 **ไม่ใช่**แหล่งข้อมูลลูกค้า — ตัดออกจากแหล่งของ Customer 360 ได้ |

**D365 เป็นระบบปลายทาง ไม่ใช่ระบบต้นทาง** — ถ้า ingest จาก D365 จะได้ข้อมูลที่ผ่านการแปลงมาแล้วชั้นหนึ่ง
ควร ingest จากฐานต้นทางของแต่ละ BU โดยตรง → [[2026-08-26 ERP]]

**ERP อื่นที่มีในตลาด** (อ้างอิงจากที่ประชุม): SAP · SAP B1 · D365 F&O · D365 BC · Oracle ERP · Odoo

---

## เชื่อมกับโน้ตอื่น

[[System Inventory]] · [[ITEC Overview]] · [[EV Business]] · [[Current Status]]
