# GI + EV7 → 7Club

**สถานะ:** รอ requirement จากพี่โจ้ (คาดว่าหลังขาย iPhone 18 / Q4)
**ที่มา:** ClickUp `Integrate GI + EV7 → 7Club CRM.txt` — บันทึกประชุม 21 ส.ค. 2026

> ข้อมูลของตัวระบบเอง อยู่ที่ [[EV Business]] และ [[CRM Overview|CRM, 7Club, Braze]]

---

## Goal

> "รวม Customer Data จาก GI (AION) และ EV7 เข้า 7Club เพื่อวิเคราะห์ Customer Behavior และทำ Promotion / Cross-selling ร่วมกับบริษัทในเครือ เช่น Studio7 / Banana IT /Thunder fin fin"

---

## Business rationale

> "ในมุมมองด้านธุรกิจพี่โจ้มองว่าลูกค้าที่ซื้อ/เช่ารถไฟฟ้าที่เป็นสินค้าที่มีมูลค่าสูง ซึ่งลูกค้ากลุ่มนี้ เป็นกลุ่มที่มีโอกาสสร้างมูลค่าเพิ่มได้ หากได้รับ benefit เพิ่มเติมจาก 7club เช่นลูกค้าที่ซื้อหรือเช่าซื้อรถไฟฟ้า Aion สามารถนำไป cross sale กับ product ของ banana/studio7/ufund ได้"

> "การเพิ่ม benefit ของ 7club ให้กับลูกค้า EV7&GI ยังสอดคล้องกับเเนวทางของ คุณปอน CBO ในการสร้าง data integration ภายในเครือ COM7 ซึ่งจะนำไปสู่ customer ecosystem (ติด tag ลูกค้า เเละเเนวทางการว่งเสริมการขายอื่นๆ)"

คู่ที่บันทึกไว้: **GI จับกับ banana** · **EV7 จับกับ thunder finfin**

---

## Meeting decisions

> "อย่างไรก็ตาม data ของ EV7&GI ยังไม่สะอาดเท่าที่ควร บวกกับยังไม่ได้ทำการ standardize ให้เข้ากับ 7club ทางที่ประชุมจึงเห็นว่าควรเริ่มจากการ migrate เเละ clean data ก่อน"

**Clean และ migrate ก่อน แล้วค่อย integrate** → [[Decisions|D-09]]

---

## What comes next

> "1. พี่โจ้เเจ้งว่าจะเขียน requirement บวกทำ data prep ให้เบื้องต้น คาดว่าจะนำส่งได้หลังขาย iphone18 (Quarter 4) พร้อมจัดประชุมอีกครั้งกับทีม Oper standard เพื่อเตรียม migrate data ต่อไป"

> "2. หลังจากที่ MIS ได้รับ data EV7&GI เเล้ว จะต้องนำมารวมกับ data 7club เพื่อทำการ clean ต่อ เเนวทางการ clean เบื้องต้นคือนำข้อมูลลูกค้า 2 เเหล่งมารวมกัน → remove duplicate ด้วยบัตรประชาชน → gen customer_id ตัวใหม่เเต่ยังเก็บ source ไว้ หลังจากนั้นค่อยนำมา map กับข้อมูลการซื้อขายสินค้าอื่นๆ เพื่อทำเเนวทางการส่งเสริมการขายต่อไป โดย end user คือทีม CRM (คาดว่าจะต้องเก็บ data ในเครื่อง 250)"

---

## Four issues on record

### 1 · What benefits do EV customers get from 7Club+

> "ยังไม่มี Benefit ที่ตอบโจทย์ลูกค้า EV7/GI อย่างชัดเจน ต้องกำหนด Value Proposition ก่อนว่าจะนำ 7Club มาใช้เพื่อสร้าง Cross-selling / Promotion"

**เป็นปัญหาเชิงธุรกิจที่ทีมข้อมูลแก้เองไม่ได้ และมันกำหนดว่างานทั้งหมดจะมีค่าหรือไม่** `[อนุมาน]`

### 2 · EV7/GI data quality and structure are not ready

> "Data ต้นทางยังไม่ Clean และยังไม่ได้ Standardize ให้ตรงกับโครงสร้างของ 7Club"
> "ยังไม่ได้ Standardize ให้ตรงกับโครงสร้างของ CRM"

### 3 · Redundant databases

> "มีฐานข้อมูลซ้ำซ้อนจากการพัฒนาระบบหลายช่วงเวลาและ Data Source กระจายหลายระบบ ex. D365 (GI เก่า) / GI CORE (ปัจจุบัน) / AION DMS (ของจีน) / EV7CORE / EVTRACKING บางรายการ GI ยังอยู่ในนี้ เพราะโอนไปเป็น EV7"

> "ปัจจุบัน GI CORE เป็นระบบหลัก และมี RPA เชื่อมข้อมูลไปยังระบบอื่น ทำให้ต้องทำความเข้าใจ Data Flow ให้ชัดเจนก่อน"

### 4 · Customer Matching / Unique Customer

> "ต้องรวม Customer Data จาก EV7/GI และ 7Club
> ต้องกำหนดหลักในการ Deduplicate เช่น ใช้เลขบัตรประชาชน(ถ้ามี)/email/เบอร์โทร
> สร้าง customer_id, CRM_id กลางใหม่
> จากนั้นจึงค่อย Map กับ Transaction/Product จาก BU เช่น Thunder finfin, Bananait เพื่อทำ Customer 360 และ Promotion ต่างๆ"

⚠️ GI Core `IdentityCard` เป็น **nullable** — กลยุทธ์นี้จึงต้องมี fallback → [[Customer Identity]]

---

## Five-step action plan

> "1.) Data Discovery สำรวจ Source, Structure, Data Type และ Data Quality / เปรียบเทียบข้อมูล GI vs EV7 / Identify Key สำหรับ Customer Matching
> 2.) Cleaning & Standardization Remove Duplicate / Missing Data / Standardize Format, Data Type และ Cleaning Data / Normalize Customer Data
> 3.) Matching Match Customer ระหว่าง GI และ EV7 / กำหนด Customer ID ใหม่
> 4.) Data Integration รวม GI + EV7 → 7Club CRM / พิจารณาใช้ CRM Fields เดิม หรือ Create New Table/Entity ใหม่
> 5.) Validation ตรวจสอบ Data Quality และ Reconciliation / Analytic ส่งให้ทีมการตลาด นำไปวิเคราะห์ Customer Behavior, Segmentation และทำ Personalized Promotion / Cross-selling"

---

## Business notes from the meeting

> "EVSEVEN มี collection ของตัวเอง /ไม่เกี่ยวกับ TFF"
> "EV 7 มีแค่ 4OD (4วัน) และจะทำการตัด ไม่ให้ชาจไฟ"
> "EV7 ลูกค้าบางโอน อาจโอนเคส Collection ไปยัง TFF ได้"
> "GI อาจทำการ Coss-selling /ส่งเสริมการขาย กับ BU อื่นได้ เช่น Bananait"

---

## Dataset

| Dataset | ที่บันทึกไว้ | สถานะจริง |
|---|---|---|
| GI & EV7 | `ev,gi / schema.prisma` | **มี** ที่ `D:\EV_GI_database\` |
| CRM | `crm_fied_description.html` | **ได้แล้ว** → [[CRM - Data Dictionary]] |

หมายเหตุจากที่ประชุม: การสร้าง ER จาก Prisma *"ซับซ้อนอยู๋"* · มี `ERD.svg` อยู่ข้าง schema แล้ว

---

## เชื่อมกับโน้ตอื่น

[[EV Business]] · [[CRM Overview|CRM, 7Club, Braze]] · [[Customer Identity]]
