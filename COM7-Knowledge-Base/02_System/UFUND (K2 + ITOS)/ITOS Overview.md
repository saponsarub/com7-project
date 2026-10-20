# ITOS Overview

ระบบสินเชื่อ/ติดตามหนี้ของ **UFUND (Thunder FinFin)** — ระบบที่ K2 กำลังย้ายไปหา

|              |                                                                                                    |     |
| ------------ | -------------------------------------------------------------------------------------------------- | --- |
| Survey       | **Done** · schema wiki สร้าง 2026-05-04                                                            |     |
| เจ้าของงาน   | K.Ton                                                                                              |     |
| Physical     | MSSQL ฐาน **`ILOAN_COLLECTION`**                                                                   |     |
| ชั้น extract | `ILOAN_DATASOURCE.dbo.ITOS_COLLECTION_DETAIL` · `ITOS_COLLECTION_PORTFOLIO`                        |     |
| ขนาด         | **55 ตารางที่ใช้จริง** (ตัดออก 167 ตารางที่ว่างเปล่าหรือชื่อเป็น `BK_*`, `*_BK`, ลงท้ายด้วยตัวเลข) |     |
|              |                                                                                                    |     |

ธุรกิจที่ระบบนี้รองรับ → [[UFUND]] · ระบบคู่แฝด → [[K2 Overview]]

> **K2 กำลังถูกเลิกใช้** — ประชุม 2026-08-27 ระบุว่าจะ migrate มา ITOS ครบ 100% ภายในสิ้นปี 2026
> **ยกเว้น UFUND Student** ที่ยังอยู่บน K2 → [[UFUND in Customer 360]]

---

## วิธีดูออกว่าสัญญาไหนมาจากระบบไหน

| | K2 | ITOS |
|---|---|---|
| รูปแบบเลขสัญญา | ตัวเลขล้วน — `2495733`, `25221018` | ขึ้นต้น **`TFF`** — `TFF2510-005889` |
| วันครบกำหนดชำระ | **วันที่ 1 และ 16 เท่านั้น** | หลากหลาย — พบ 14, 20, 21, 22, 23, 26, 27 |
| รูปแบบปีในเลขสัญญา | — | `TFF` + ปีพ.ศ. 2 หลัก + เดือน + ลำดับ (`TFF` `25` `10` `-005889`) |

**ผลกระทบ:** สูตรที่สร้างไว้สำหรับ K2 ที่สมมติว่าวันครบกำหนดคือ 1/16 **ใช้กับ ITOS ไม่ได้**
ต้องอ่านวันครบกำหนดจากข้อมูลจริงเสมอ ไม่ใช่คำนวณจากปฏิทิน

---

## ตารางหลัก

| ตาราง             |         แถว | คอลัมน์ | เก็บอะไร                                        |
| ----------------- | ----------: | ------: | ----------------------------------------------- |
| `S_PMTSCHDLE`     |   3,768,675 |      16 | ตารางงวดชำระ (เทียบเท่า `CUSTOMER_CARD` ของ K2) |
| `S_CUSTADDR`      |     746,916 |      19 | ที่อยู่ลูกค้า — **หลายแถวต่อคน**                |
| `S_ADDRESS`       |     663,728 |      27 | ทะเบียนที่อยู่                                  |
| `S_CUSTTEL`       |     371,323 |      13 | เบอร์โทร — หลายแถวต่อคน                         |
| `S_CUSTEMAIL`     |     370,828 |       6 | อีเมล — หลายแถวต่อคน                            |
| `T_NOTE`          |     277,694 |     109 | บันทึกการติดตาม                                 |
| `S_COLLECTRESP`   |     166,189 |      10 | ผลการติดต่อ                                     |
| `S_CONTRACT`      |     165,723 |      71 | สัญญา                                           |
| **`S_CUSTOMER`**  | **165,722** |  **67** | **ทะเบียนลูกค้า**                               |
| `S_ASSET`         |     165,723 |      44 | สินค้า/ทรัพย์สินตามสัญญา                        |
| `S_CONTRACTCUST`  |     165,723 |      11 | เชื่อมสัญญากับลูกค้า                            |
| `S_INSURANCE`     |     165,723 |      10 | ประกัน                                          |
| `S_FINANCE`       |     165,547 |      78 | เงื่อนไขทางการเงิน                              |
| `S_OUTSTANDING`   |     165,094 |      48 | ยอดคงค้าง                                       |
| `R_SNAP`          |      83,075 |      48 | snapshot                                        |
| `S_COLLECTIONFEE` |      37,750 |      18 | ค่าติดตาม                                       |
| `T_JOBTRANS`      |      15,684 |      61 | ธุรกรรมงาน                                      |

**ตาราง master:** `M_AREA` (7,488) · `M_DISTRICT` (7,460) · `M_COMPANYBRANCH` (1,741) · `M_BUCKETAREA` (1,737) · `M_AMPHUR` (929) · `M_ROAD` (745) · `M_HOLIDAY` (730) · `M_PROVINCE` (80) · `M_COMPANY` (18) · `M_PRODUCT` (16) · `M_CHANNEL` (7)

### วิธี query ตารางหลัก (ตรวจจริง 2026-10-09)

**ตัวอย่าง query ครบทุกเรื่อง + ตารางที่ข้อมูลเหมือนกัน → [[ITOS - Query Cookbook]]**

เข้า `ILOAN_COLLECTION` ตรงไม่ได้ แต่ฐาน `ILOAN_DATASOURCE` (linked server ของ k2 · profile `k2`) มี **external table ใน schema `ext_collection`** ที่ชี้ไปตารางชุดนี้ (จำนวนคอลัมน์ตรงกัน)

```
ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.<ตาราง>
```

| ตาราง                                         |    แถว 2026-10-09 | คีย์ join                                               |
| --------------------------------------------- | ----------------: | ------------------------------------------------------- |
| `S_CONTRACT`                                  |           343,322 | `CONTRACT_NO` · ลูกค้า `CONTRACT_CUSTCODE`              |
| `S_CUSTOMER`                                  |           343,317 | `CUST_CODE`                                             |
| `S_ASSET`                                     |           343,322 | `ASSET_CONTRACTNO` (มี `ASSET_IMEI` · `ASSET_SERIALNO`) |
| `S_OUTSTANDING`                               |           337,333 | `OUTS_CONTRACTNO`                                       |
| `S_PMTSCHDLE`                                 |         6,074,043 | `SCHEDULE_CONTRACTNO` + `SCHEDULE_TERMNO`               |
| `S_CUSTTEL`                                   |           951,893 | `TEL_CUSTCODE`                                          |
| `T_JOBTRANS` · `M_COLLECTOR` · `M_MASTERINFO` | 23,241 · 77 · 400 |                                                         |
|                                               |                   |                                                         |

**ไม่มีใน `ext_collection`:** `S_CUSTADDR` · `S_ADDRESS` (ใช้ `dbo.COLLECTION_S_ADDRESS` แทน) · `S_CUSTEMAIL` · `S_CONTRACTCUST` · `S_FINANCE` · `S_INSURANCE` · `T_NOTE` (มี `dbo.COLLECTION_ORCL_T_NOTE`) · `S_COLLECTRESP` · `R_SNAP` · ตาราง `M_*` ส่วนใหญ่

**เทียบกับ `dbo.ITOS_COLLECTION_DETAIL` (2026-10-09 · 11,413 สัญญา):** สัญญาชุดเดียวกัน (เจอครบ 100% ด้วยเลขสัญญา) แต่ **`ext_collection` เป็นข้อมูลสด** ส่วน DETAIL เป็น snapshot ที่โหลดตอน 23:10 ของคืนก่อน
- ตรงกัน ≥99.5%: งวดที่จ่ายแล้ว (`OUTS_PAIDTERM`) · งวดค้าง (`OUTS_OVDTERM`) · ยอดค้าง (`OUTS_OVDAMTTOTAL`) · วันครบกำหนด · วันจ่ายล่าสุด · model 100% · serial (`ASSET_SERIALNO`) 97%
- 30 สัญญาที่ไม่ตรงคือลูกค้าที่**จ่ายเงินวันที่ 10-09** ฝั่ง ext จึงเห็นแล้ว (งวดค้าง 1 → 0) แต่ DETAIL ยังไม่เห็น
- **ใช้แทนกันไม่ได้:**
  - `CONTRACT_ID` เป็นคนละชุดเลข → ต้อง join ด้วยเลขสัญญา
  - `OUTS_TERM` ไม่ใช่จำนวนงวดทั้งหมด `[อนุมาน: เป็นงวดปัจจุบัน]`
  - `OUTS_PENALTY` เป็น null ทุกแถว (DETAIL มี `PENALTY_AMT`)
  - `OUTS_PRINCIPLE` / `OUTS_PRINCIPLETOTAL` ไม่ใช่เงินต้นคงเหลือ `[อนุมาน: เป็นยอดตั้งต้น รวม VAT / ไม่รวม VAT]`
  - `OUTS_ASOFDATE` เป็น null ทุกแถว
  - `REMAINING_OUTSTANDING` เท่ากับ `OUTS_AMTTOTAL` 96.8% · อีก 369 สัญญายังไม่รู้ว่าต่างเพราะอะไร

แถวเพิ่มจาก ~165k (ตอนทำ wiki 2026-05) เป็น ~343k · ห้ามใส่ `WITH (NOLOCK)` · ทุกตารางมี `*_ASOFDATE` / `*_BATCHROUND`

> **การตั้งชื่อ:** `S_` = ข้อมูลสัญญา/ลูกค้า · `M_` = master · `T_` = transaction · `R_` = report/snapshot
> สะอาดกว่า K2 มาก · ⚠️ แก้ 2026-10-09: wiki บอกว่า 1 แถวต่อ 1 ลูกค้า แต่ของจริง `CUST_CODE` มี 343,312 รหัส ≈ จำนวนสัญญา (343,322) · เลขบัตรไม่ซ้ำ 342,486 → **ได้ `CUST_CODE` ใหม่ทุกสัญญา** ต้องรวมคนด้วย `CUST_CARDNO`

---

## `S_CUSTOMER` — ทะเบียนลูกค้า 67 คอลัมน์

| กลุ่ม | ฟิลด์ |
|---|---|
| คีย์ | `CUST_ID` (int, NOT NULL) · `CUST_CODE` (nvarchar 500, NOT NULL) |
| ชื่อไทย | `CUST_TITLETH` · `CUST_NAMETH` · `CUST_LASTNAMETH` |
| ชื่ออังกฤษ | `CUST_TITLEEN` · `CUST_NAMEEN` · `CUST_LASTNAMEEN` |
| ข้อมูลส่วนตัว | `CUST_BIRTHDATE` · `CUST_GENDER` · `CUST_RACE` · `CUST_NATIONALITY` · `CUST_MARITALSTATUS` |
| **บัตรประชาชน** | **`CUST_CARDTYPE`** · **`CUST_CARDNO`** · `CUST_CARDISSUEDATE` · `CUST_CARDEXPIREDATE` · `CUST_CARDISSUEPLACE` |
| ภาษี | `CUST_TAXNO` |
| อาชีพ | `CUST_OCCUPATION` · `CUST_COMPANY` · `CUST_DEPT` · `CUST_POSITION` · `CUST_NOOFYEAR` · `CUST_NOOFMONTH` |
| **รายได้** | `CUST_SALARY` · `CUST_OTHERINCOME` · `CUST_INCOMEYEAR` (numeric 18,2) |
| **คู่สมรส** | `CUST_SP_*` (ไทย + อังกฤษ) |
| **รหัส ธปท.** | `CUST_BOTCUSTCODE` · `CUST_BOTCODE` · `CUST_BOTINSTCODE` |

### เทียบกับ K2

| | ITOS | K2 |
|---|---|---|
| เลขบัตรประชาชน | `S_CUSTOMER.CUST_CARDNO` | `PERSON.TAX_ID` |
| แถวต่อคน | **1 แถวต่อลูกค้า** | 1 แถวต่อ**ใบคำขอ** → ซ้ำได้ |
| ที่อยู่ | ตารางแยก หลายแถวต่อคน (`S_CUSTADDR`) | ตารางเดียว 5 บล็อกในแถวเดียว (`ADDRESS`) |
| รหัส ธปท. | **มี 3 คอลัมน์** | **ไม่พบ** |
| ชื่อไทย/อังกฤษ | มีคู่กัน | มีคู่กัน |

> **รหัส ธปท. ยืนยันว่ามีภาระรายงานต่อธนาคารแห่งประเทศไทย** นอกเหนือจาก PDPA
> → มีผลต่อการเก็บรักษาและการเข้าถึงข้อมูลใน lake ดู [[Consent & PDPA]]
>
> ⚠️ **ตรวจค่าจริง 2026-10-09:** คอลัมน์ `CUST_BOT*` · `CUST_SP_*` (คู่สมรส) · `CUST_OCCUPATION` **ว่างทุกแถว** · `CUST_GENDER` ว่างเกือบทุกแถว → มีคอลัมน์แต่ไม่ได้กรอก ข้อสรุปเรื่องภาระรายงาน ธปท. ข้างบนจึงยังไม่มีหลักฐานจากข้อมูล · ตัวอย่าง query → [[ITOS - Query Cookbook#S_CUSTOMER — ตัวอย่าง query]]

---

## ข้อสังเกตที่มีผลต่อการออกแบบ pipeline

| ข้อสังเกต | ผลกระทบ |
|---|---|
| **ที่อยู่/เบอร์/อีเมล เป็น one-to-many** | 746,916 ที่อยู่ ต่อ 165,722 ลูกค้า → การ match ต้องรองรับหลายค่าต่อคน ไม่ใช่ค่าเดียว `[อนุมาน]` |
| **มีข้อมูลบุคคลที่สาม** | คู่สมรส (`CUST_SP_*`) และผู้ค้ำประกัน — คนเหล่านี้ไม่ได้ทำสัญญากับ COM7 โดยตรง<br>*มีความเห็นว่าไม่ควรใช้ข้อมูลผู้ค้ำเพราะไม่ใช่ลูกค้าจริง — **รอ legal ยืนยัน*** |
| **มีข้อมูลรายได้** | salary · other income · annual income → ข้อมูลอ่อนไหวทางการเงิน |
| **ชื่อไทยกับอังกฤษคู่กัน** | ต้องตัดสินว่าอันไหนเป็นตัวหลักตอน standardize |
| **ไม่มีคำอธิบายในฐานเลย** | `MS_Description: not defined` ทุกตารางทุกคอลัมน์ → ต้องอาศัยคนที่รู้ |
| **คอลัมน์ข้อความเป็น `nvarchar(500)`/`(800)` เกือบทั้งหมด** | ความยาวไม่มีความหมายเชิงธุรกิจ ใช้ validate ไม่ได้ |

---

## Usage stats

จาก `sys.dm_db_index_usage_stats`:
`M_RESULT` (8 ops) · `M_MASTERINFO` (7) · `M_NOTERESULT` (5) · `M_NOTE` (2) · `S_CONTRACT` · `S_CUSTOMER` · `S_OUTSTANDING` · `T_JOBTRANS` (1 แต่ละตัว)

`S_CUSTOMER` — สร้าง 2025-07-10 · อัปเดตล่าสุด 2025-10-29

> wiki เตือนว่า *"ตัวเลขจะรีเซ็ตเมื่อ restart server หรือทำ index maintenance"* — อย่าใช้สรุปว่าตารางไหนตายแล้ว

---

## การรวมกับ K2

| งาน | โน้ต |
|---|---|
| SQL union ที่ใช้อยู่จริง (58 คอลัมน์) | [[Collection Union (K2 + ITOS)]] |
| โครงการรวมระบบ | [[K2 + ITOS Integration]] |
| ข้อมูลติดตามหนี้ฝั่ง K2 | [[K2 - Collection & OD]] |

**ข้อได้เปรียบของ ITOS ในชุด union:** มี `PRODUCT_MODEL` · `PRODUCT_SERIAL_NO` · `CREATE_DATE` · `MODIFY_DATE`
ซึ่งฝั่ง K2 เป็น `NULL` ทั้งหมด → **ทำ incremental จากฝั่ง ITOS ได้ แต่ฝั่ง K2 ไม่ได้**

## ข้อมูล NCB (เครดิตบูโร)

**ITOS เป็นที่เดียวที่มีข้อมูล NCB** — K2 หยุดเก็บตั้งแต่ **08/2025** (ประชุม 2026-08-27)

| กติกา | รายละเอียด |
|---|---|
| **ห้ามเก็บรายละเอียด NCB ใน S3** | เป็นข้อมูล sensitive |
| **เก็บได้เฉพาะสรุป / Indicator** | เช่น ระดับภาระหนี้ สูง / กลาง / ต่ำ · หรือทำเป็น flag |

ยังไม่ทราบว่าข้อมูล NCB อยู่ตารางไหนใน `ILOAN_COLLECTION` → [[Source System Issues]]

---

## เชื่อมกับโน้ตอื่น

[[UFUND]] · [[K2 Overview]] · [[ITOS - Query Cookbook]] · [[Collection Union (K2 + ITOS)]] · [[K2 + ITOS Integration]] · [[System Inventory]] · [[Customer Identity]] · [[Data Standardization & Quality]] · [[K2 + ITOS - Storage Sizing]]
