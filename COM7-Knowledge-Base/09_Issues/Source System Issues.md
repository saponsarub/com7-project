# Source System Issues

คำถามและงานค้างของระบบต้นทางอื่น — ITEC · ITOS · D365 · SAP B1 · iCare · Tech Trade · Synapse · EV · ค้าปลีก

---

## ITEC

ย้ายไปที่ [[ITEC Issues]] แล้ว — มี 16 คำถามหลังสำรวจฐานจริง 2026-08-28

---

## ITOS Overview — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[ITOS Overview]]

1. K2 กับ ITOS มีข้อมูลสัญญาเดียวกันซ้ำกันไหม (ลูกค้าคนเดียวมี 2 สัญญา 2 ระบบ)
2. ITOS ยัง update อยู่ไหม — usage stats น้อยผิดปกติ
3. `ILOAN_COLLECTION` กับ `ILOAN_DATASOURCE` refresh บ่อยแค่ไหน ใครเป็นคนรัน
4. พอรวมระบบเสร็จ lake จะ ingest ระบบรวมระบบเดียว หรือยัง ingest 2 source
5. `CUST_CODE` เป็น nvarchar(500) — รูปแบบจริงคืออะไร ใช้ join ข้ามระบบได้ไหม
6. ผู้ค้ำประกัน — เก็บหรือไม่เก็บใน lake (**รอ legal**)

---

## D365 — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[Other Systems]]

ใช้ทำอะไรโดยรวม · BU ไหนใช้บ้าง · ยัง active หรือ legacy แล้ว (เรียกว่า "GI เก่า" แต่ `D365FO_DATALAKE` ยังถูก query อยู่) · ข้อมูลอยู่ที่ไหนจริง · เชื่อมกับ Azure/ADLS ไหม · **มีข้อมูลลูกค้าไหม** (query ที่พบเป็น inventory/vendor/purchasing ล้วน)

---

## SAP B1 — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[Other Systems]]

**เกือบทั้งหมด** — BU ไหนใช้ · มีข้อมูลลูกค้าไหม · product/sales/financial data · อยู่ on-prem หรือ cloud · integration กับระบบอื่น · **ความสัมพันธ์กับ D365**

COM7 ดูเหมือนมี ERP สองระบบ (D365 F&O และ SAP B1) ซึ่งกระทบขอบเขต Finance & Accounting ของ Data Framework ที่ต้องการงบการเงินรวม — 2 ERP อาจแปลว่าต้อง reconcile chart of accounts สองชุด `[อนุมาน]`

---

## iCare — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[Other Systems]]

*(ตอบบางส่วนแล้ว 2026-09-02: **ICI อยู่บน P&O ตอนนี้ · จะย้ายไป IDS (K2) on-premise เพราะ P&O ต้อง subscription** — แจ้งด้วยวาจา ยังไม่มีเอกสารยืนยัน ดู [[Other Systems]])*

- [ ] **P&O คืออะไร** — ผู้ให้บริการ SaaS · แพลตฟอร์ม · หรือชื่อฐานข้อมูล → **P.Pui / คนที่แจ้ง**
- [ ] **`IDS` ในคำว่า "IDS (K2)" คืออะไร** — ยืนยันแล้วว่า K2 คือฐาน on-prem ที่ทีม dev เขียนเอง `[อนุมาน: IDS น่าจะเป็นชื่อโปรแกรมที่ใช้ฐาน K2]` · ถ้าใช่ ICI จะไปอยู่ฐานเดียวกับ UFUND (`HPCOM7`) และ K2 จะถือ 3 ธุรกิจ → **ทีม dev / MIS-Fintech**
- [ ] **แผนย้ายมีกำหนดเมื่อไหร่** — กระทบว่าจะ survey และ ingest ตอนไหน อย่าดึงจาก P&O แล้วต้องทำใหม่
- [ ] ย้ายทั้ง Insurance (1.1.6.1) และ Mobile Service (1.1.6.2) หรือแค่ Insurance
- [ ] Insurance กับ Mobile Service เป็นคนละระบบหรือระบบเดียว · เป็นนิติบุคคลแยกไหม · ใช้ customer identifier อะไร · เก็บ serial/IMEI ของเครื่องไหม

---

## Tech Trade — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[Other Systems]]

รันบนระบบอะไร · เป็น BU หรือระบบ หรือทั้งคู่ · เป็นนิติบุคคลแยกไหม · ถือ customer identifier อะไร · เก็บ serial/IMEI ไหม · สัมพันธ์กับ `buyback_iphone` ยังไง · ทำไมถูกจัดเป็น Other Legacy System

---

## Azure Synapse + ADLS — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[Other Systems]] · วิธีย้าย → [[ADLS Gen2 to S3]]

**ปิดแล้ว 2026-10-08 (จากคู่มือ Alphametrics):** ADLS เป็น **Gen2** · ใช้ **Synapse pipeline** (ไม่ใช่ ADF แยก) · `syndpdev001` คือ **dedicated SQL pool** ใน workspace `synw-com7dw-dev` · ข้อมูลที่ผ่าน Synapse มาจาก D365 F&O (Synapse Link) · BC LS Retail (Double7) · ITEC · Excel บน SharePoint

**ยังค้าง:** ชื่อ storage account / container จริง (`stcom7dw001` ใช่ไหม) · Synapse Link เขียนเป็น **Delta หรือ CSV** · ไฟล์จาก pipeline BCLS/ITEC เป็น CSV หรือ Parquet และเป็น snapshot หรือส่วนต่าง · ขนาดข้อมูลรวม · storage ปิด public network ไหม · Azure region · มี workspace production แยกไหม (ชื่อมี `dev`) · RPA ทำอะไร · Alphametrics ยังดูแลอยู่ไหม

### 🔴 รหัสผ่านในเอกสาร training

`D:\Azure\COM7-02 Training material - Azure Synapse.pdf` หน้า "ตั้งค่า Row-Level security" มีคำสั่ง `create login ... with password = '...'` **พร้อมรหัสจริงของ login ทุก BU** (`sqluser_all` และรายบริษัท) เป็นข้อความธรรมดา
- แจ้งเจ้าของ Synapse ให้ **เปลี่ยนรหัสทุก login** และตรวจว่าใครได้ไฟล์นี้ไปบ้าง
- จำกัดการเข้าถึงไฟล์ · ไม่ส่งต่อ · ไม่คัดลอกรหัสลงที่ใด (vault นี้ไม่ได้เก็บรหัส)
- ระยะยาวใช้ Entra ID แทน SQL login

---

## EV Business — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[EV Business]]

- RPA ย้ายอะไร ทิศทางไหน ตารางเวลาอะไร
- 166 models ใช้จริงกี่ตัว
- จำนวน customer record เท่าไหร่
- `customers` ใน GI Core ซ้ำกับ record ใน EV7CORE และ AION DMS ไหม
- `customer_identify` ใช้ทำอะไร
- EV7CORE คืออะไร ขนาดเท่าไหร่ schema เป็นยังไง
- อะไรค้างอยู่ใน EVTRACKING และตอนนี้ใครเป็นเจ้าของ
- ความสัมพันธ์เชิงองค์กรระหว่าง EVSEVEN, GI, EV7 คืออะไร

---

## Retail — คำถามที่ยังไม่มีคำตอบ

เนื้อหา → [[Retail]]

1. ITEC ครอบคลุมทุกแบรนด์ร้านหรือแยกระบบตามแบรนด์
2. ธุรกิจค้าส่ง (Adept) ใช้ระบบอะไร
3. ช่องทางออนไลน์ (BNN.IN.TH · Studio7.com) เก็บข้อมูลที่ไหน เชื่อมกับ ITEC ไหม
4. B2B / การศึกษา แยกระบบหรืออยู่ใน ITEC
5. iCare (ศูนย์ซ่อม) ใช้ระบบอะไร — ยังอยู่ในกลุ่ม TBD → [[Other Systems]]

---

## เชื่อมกับโน้ตอื่น

[[Issue Index]] · [[Open Questions & Risks]] · [[Current Status]] · [[Home]] · [[iCare Insurance (ICI)]]
