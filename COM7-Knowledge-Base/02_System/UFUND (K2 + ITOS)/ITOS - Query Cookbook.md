# ITOS — Query Cookbook

อยากได้ข้อมูลอะไรจาก ITOS → ใช้ตารางไหน · query อะไร · ตารางไหนเป็นข้อมูลเดียวกัน

ทุก query ในหน้านี้ **รันจริงแล้ว 2026-10-09** ผ่าน profile `k2` · มีเวลาที่ใช้กำกับ
ภาพรวมระบบ → [[ITOS Overview]] · ที่อยู่/ภูมิศาสตร์ → [[ITOS - Address & Geography]] · ฝั่ง K2 → [[K2 - Query Cookbook]]

> ⚠️ หลาย query ดึง **ข้อมูลส่วนบุคคลจริง** (ชื่อ เลขบัตร เบอร์ ที่อยู่ รายได้) ดึงเท่าที่ใช้
> ห้าม export ลงไฟล์ที่ commit เข้า git · ดู [[Consent & PDPA]]

---

## การเข้าถึง

ITOS ไม่มีฐานให้ต่อตรง ต้องเข้าผ่าน **linked server บนเครื่อง K2**

| | |
|---|---|
| เครื่อง | `43.254.133.123` (ฐาน `HPCOM7`) · profile **`k2`** ใน `scripts/db.py` |
| login | env `K2_USER` / `K2_PWD` |
| ชื่อตาราง | `ILOAN_DATASOURCE.ILOAN_DATASOURCE.<schema>.<ตาราง>` |

```python
import db
B = "ILOAN_DATASOURCE.ILOAN_DATASOURCE"
df = db.query("k2", f"SELECT TOP 10 * FROM {B}.ext_collection.S_CONTRACT", timeout=1800)
```

ใน `ILOAN_DATASOURCE` มี 4 กลุ่มที่ใช้ได้

| schema / prefix | คืออะไร | ความสด |
|---|---|---|
| `ext_collection.*` | external table ชี้ไปฐานจริง `ILOAN_COLLECTION` (ตารางที่ [[ITOS Overview]] สำรวจไว้) | **สด** — เห็นการจ่ายเงินของวันนี้ |
| `ext_cash_receive.*` | external table ของระบบรับชำระ · **ประวัติรายเดือน** | ปิดเดือนละครั้ง (ล่าสุด 2026-09) |
| `dbo.ITOS_STAGE_*` · `dbo.ITOS_COLLECTION_*` | ตารางที่ ETL สร้างทุกคืนสำหรับงานติดตามหนี้ | โหลดคืนละครั้ง ~23:00–23:10 |
| `dbo.COLLECTION_*` | สำเนาตารางจาก `ILOAN_COLLECTION` (ที่อยู่ · บันทึกติดตาม · ค่าทวงถาม · master) | อัปเดตระหว่างวัน |

**กติกา 4 ข้อ**
1. **ห้าม `WITH (NOLOCK)`** → error 46915 (external table)
2. **อ้างฐาน `ILOAN_COLLECTION.` ตรงไม่ได้** → error "Reference to database and/or server name ... is not supported"
3. **อย่า join หลายตารางใหญ่ในทีเดียว** — linked server ทำ remote nested loop ทีละแถว · ดึงแยกแล้ว join ใน pandas
4. บางตาราง filter ไม่ถูกส่งไปทำที่ต้นทาง ทำให้ช้าแม้ดึงสัญญาเดียว — `S_PMTSCHDLE` **107 วินาที** · `COLLECTION_S_ADDRESS` **43 วินาที** · ถ้าต้องดึงหลายสัญญา ให้ดึงทีเดียวแล้วกรองใน pandas

---

## อยากได้อะไร → ใช้ตารางไหน

| อยากได้ | ตารางที่แนะนำ | ตัวสำรอง (ข้อมูลเดียวกัน) | query |
|---|---|---|---|
| สถานะสัญญาตอนนี้ (Active / ปิด / ยกเลิก) | `ext_collection.S_CONTRACT` (`CONTRACT_STATUS` + `CONTRACT_SUBSTATUS`) | `dbo.ITOS_STAGE_CONTRACT_BASE.CONTRACT_STATUS_RAW` (เมื่อคืน) | [[#1 · ภาพรวมพอร์ตตามสถานะ]] |
| ลิสต์ลูกหนี้ค้างชำระ OD1–OD6 / WO | `dbo.ITOS_COLLECTION_DETAIL` | — (สถานะ OD มีแค่ที่นี่) | [[#2 · ลิสต์ลูกหนี้ค้างชำระ]] |
| ยอดค้าง งวดค้าง วันครบกำหนด **ล่าสุด** | `ext_collection.S_OUTSTANDING` | DETAIL / `ITOS_STAGE_CONTRACT_BASE` (เมื่อคืน) | [[#3 · ดูสัญญาเดียวแบบสด]] |
| ตารางงวดผ่อน | `ext_collection.S_PMTSCHDLE` | — | [[#4 · ตารางงวดผ่อน]] |
| ข้อมูลลูกค้า (ชื่อ อายุ อาชีพ รายได้) | `ext_collection.S_CUSTOMER` | `ITOS_COLLECTION_PORTFOLIO` (เพศ อายุ รายได้ เฉพาะลูกหนี้ค้าง) | [[#5 · ข้อมูลลูกค้าของสัญญา]] |
| คนเดียวกันมีกี่สัญญา | `S_CUSTOMER.CUST_CARDNO` | — | [[#6 · หาทุกสัญญาของคนเดียวกัน]] |
| เบอร์โทร | `ext_collection.S_CUSTTEL` | `DETAIL.CUSTOMER_PHONE_NUM` | [[#7 · เบอร์โทร]] |
| ที่อยู่ (แยกช่อง + รหัสพื้นที่) | `dbo.COLLECTION_S_ADDRESS` | `dbo.ITOS_STAGE_ADDRESS` (เป็นข้อความยาวบรรทัดเดียว) | [[#8 · ที่อยู่]] |
| สินค้า รุ่น serial | `ext_collection.S_ASSET` | `dbo.ITOS_STAGE_PRODUCT_ASSET` · DETAIL | [[#3 · ดูสัญญาเดียวแบบสด]] |
| ประวัติการโทรติดตาม / นัดชำระ | `dbo.COLLECTION_ORCL_T_NOTE` | — | [[#9 · ประวัติการติดตาม]] |
| ใครถือเคส · bucket | `ext_collection.T_JOBTRANS` + `M_COLLECTOR` | `dbo.ITOS_STAGE_ASSIGNMENT` · DETAIL | [[#10 · เคสนี้ใครถือ และ bucket]] |
| ค่าทวงถาม | `dbo.COLLECTION_S_COLELCTION_FEE` | `dbo.COLLECTION_ORCL_S_COLELCTIONFEE` (เหมือนกันทุกแถว) | [[#11 · ค่าทวงถาม]] |
| เบี้ยปรับ | `dbo.ITOS_STAGE_CASH_SUMMARY.PENALTY_OWED_CALC` | `DETAIL.PENALTY_AMT` (ค่าเดียวกัน 100%) | [[#14 · เบี้ยปรับ และยอดคงเหลือ]] |
| ยอดคงค้างสิ้นเดือน · DPD · NPL ย้อนหลัง | `ext_cash_receive.T_SnapShort_Report_OutStanding_Hp` | — | [[#12 · ยอดคงค้างและ DPD รายเดือน]] |
| สถานะสัญญาย้อนหลังรายเดือน | `ext_cash_receive.H_Contract` | — | [[#13 · ประวัติสถานะสัญญารายเดือน]] |
| เพศ อายุ รายได้ credit score ของลูกหนี้ค้าง | `dbo.ITOS_COLLECTION_PORTFOLIO` | `dbo.ITOS_STAGE_CONTRACT_BASE` (ทุกสัญญา) | [[#15 · โปรไฟล์ลูกหนี้ค้าง]] |
| ความหมายของรหัส | `ext_collection.M_MASTERINFO` | `dbo.COLLECTION_ORCL_M_MASTERINFO` (เหมือนกันทุกแถว) | [[#รหัสที่ต้องรู้]] |

---

## ตารางไหนเป็นข้อมูลเดียวกัน

ตรวจเทียบรายสัญญา 2026-10-09 · DETAIL รอบ 2026-10-08 23:10 มี 11,413 สัญญา

### `ITOS_COLLECTION_DETAIL` ประกอบจาก `ITOS_STAGE_*` 5 ตาราง

```
ITOS_STAGE_CONTRACT_BASE   (343,322 · ทุกสัญญา)  ─┐
ITOS_STAGE_CASH_SUMMARY    (329,161)              ├─ กรองเฉพาะ NUMBER_OF_OD_INSTALLMENT > 0
ITOS_STAGE_ASSIGNMENT      (10,155)               │   + แปลงสถานะเป็น OD1–OD6 / WO
ITOS_STAGE_PRODUCT_ASSET   (343,322)              │
ITOS_STAGE_ADDRESS         (343,322)             ─┘──► ITOS_COLLECTION_DETAIL (11,413)
                                                       ITOS_COLLECTION_PORTFOLIO (11,413)
```
`[อนุมาน]` จากค่าที่ตรงกัน (ไม่ได้เห็นโค้ด ETL)

| คอลัมน์ใน DETAIL | มาจาก | ตรง |
|---|---|---:|
| `NUMBER_OF_OD_INSTALLMENT` · `OD_AMOUNT` · `NUMBER_OF_PERIOD` · `PAID_NUMBER_OF_PERIOD` | `ITOS_STAGE_CONTRACT_BASE` | 100% |
| `PENALTY_AMT` | `ITOS_STAGE_CASH_SUMMARY.PENALTY_OWED_CALC` | 100% |
| `REMAINING_OUTSTANDING` | `ITOS_STAGE_CASH_SUMMARY.REMAINING_OUTSTANDING` | 98.3% |
| `CUSTOMER_ADDRESS_*` | `ITOS_STAGE_ADDRESS` | 100% |
| `PRODUCT_SERIAL_NO` | `ITOS_STAGE_PRODUCT_ASSET` | 100% |
| `ASSIGN_TO_TEAM` · `EMP_CODE` | `ITOS_STAGE_ASSIGNMENT` | 89% (ตาราง assignment อัปเดตแล้ววันนี้) |

**ชื่อเหมือนแต่ค่าไม่เหมือน:** `ITOS_STAGE_CONTRACT_BASE.PENALTY_AMT` ≠ `DETAIL.PENALTY_AMT` (ตรง 0%) → เบี้ยปรับให้ใช้ `PENALTY_OWED_CALC` · `CASH_SUMMARY.REMAINING_PRINCIPAL` ตรง DETAIL แค่ 20%

### DETAIL (เมื่อคืน) vs `ext_collection` (สด)

สัญญาชุดเดียวกัน (DETAIL เจอใน `S_CONTRACT` ครบ 100%) · **join ด้วยเลขสัญญาเท่านั้น** — `CONTRACT_ID` คนละชุดเลข (เช่น 1308 vs 5286006)

| DETAIL | ext_collection | ตรง |
|---|---|---:|
| `PAID_NUMBER_OF_PERIOD` | `S_OUTSTANDING.OUTS_PAIDTERM` | 99.74% |
| `NUMBER_OF_OD_INSTALLMENT` | `OUTS_OVDTERM` | 99.74% |
| `OD_AMOUNT` | `OUTS_OVDAMTTOTAL` | 99.61% |
| `PERIOD_DUE_DATE` | `OUTS_DUEDATE` | 99.74% |
| `LAST_REPAY_DATE` | `OUTS_LASTPAYMENTDATE` | 99.52% |
| `REMAINING_OUTSTANDING` | `OUTS_AMTTOTAL` | 96.77% |
| `PRODUCT_MODEL` | `S_ASSET.ASSET_MODEL` | 100% |
| `PRODUCT_SERIAL_NO` | `S_ASSET.ASSET_SERIALNO` | 97.14% |

ส่วนที่ไม่ตรง 30 สัญญา = ลูกค้า**จ่ายเงินวันนี้** (ext เห็นแล้ว DETAIL ยังไม่เห็น) → เป็นเรื่องเวลาดึงต่างกัน

**ใช้แทนกันไม่ได้**

| คอลัมน์ | ปัญหา |
|---|---|
| `OUTS_TERM` | ไม่ใช่จำนวนงวดทั้งหมด (ตรง `NUMBER_OF_PERIOD` แค่ 0.6%) `[อนุมาน: งวดปัจจุบัน]` |
| `OUTS_PENALTY` | null ทุกแถว |
| `OUTS_PRINCIPLE` / `OUTS_PRINCIPLETOTAL` | ไม่ใช่เงินต้นคงเหลือ · ต่างกัน ~1.07 เท่า `[อนุมาน: ยอดตั้งต้น รวม / ไม่รวม VAT]` |
| `OUTS_ASOFDATE` | null ทุกแถว |
| `ASSET_IMEI` | ตรง serial ใน DETAIL แค่ 4% → ใช้ `ASSET_SERIALNO` |
| `S_CONTRACT.CONTRACT_STATUSCODE` | `A` เกือบทุกแถว (343,321) ใช้ไม่ได้ → ใช้ `CONTRACT_STATUS` (`ACT` / `CLS` / `TEM`) |

### คู่ที่เป็นสำเนากันทุกแถว

| ตาราง A | ตาราง B | ตรวจ |
|---|---|---|
| `dbo.COLLECTION_S_COLELCTION_FEE` | `dbo.COLLECTION_ORCL_S_COLELCTIONFEE` | 80,623 แถว · `EXCEPT` ได้ 0 |
| `ext_collection.M_MASTERINFO` | `dbo.COLLECTION_ORCL_M_MASTERINFO` | 400 แถว · `EXCEPT` ได้ 0 |
| `ext_collection.M_COLLECTOR` | `dbo.COLLECTION_ORCL_M_COLLECTOR` | 77 แถว (dbo มีคอลัมน์ `COLLECTOR_EXPEDITE_DEBT` เพิ่ม) · ยังไม่ได้เทียบค่า |

### snapshot รายเดือน vs ข้อมูลสด

`T_SnapShort_Report_OutStanding_Hp` เดือน 2026-09 มี 324,470 สัญญา (ขึ้นต้น `TFF` ทั้งหมด) · เจอใน `S_OUTSTANDING` ครบ 100% → ชุดสัญญาเดียวกัน แต่เป็น**ค่า ณ สิ้นเดือน** ไม่ใช่วันนี้

---

## 1 · ภาพรวมพอร์ตตามสถานะ

```sql
-- สด
SELECT  CONTRACT_STATUS, CONTRACT_SUBSTATUS, COUNT(*) AS contracts
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_CONTRACT
GROUP BY CONTRACT_STATUS, CONTRACT_SUBSTATUS
ORDER BY contracts DESC;

-- พร้อมยอดคงค้าง (ข้อมูลเมื่อคืน)
SELECT  CONTRACT_STATUS_RAW,
        COUNT(*)                AS contracts,
        SUM(TOTAL_OUTSTANDING)  AS total_outstanding,
        SUM(CASE WHEN NUMBER_OF_OD_INSTALLMENT > 0 THEN 1 ELSE 0 END) AS overdue
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.ITOS_STAGE_CONTRACT_BASE
GROUP BY CONTRACT_STATUS_RAW;
```
1 วินาที · ผล 2026-10-09: `ACT` ปกติ 330,748 · `CLS` ปิดปกติ 9,764 · `CLS` ปิดก่อนกำหนด 1,488 · `ACT` ปิดหนี้สูญ 1,226 · `TEM` ยกเลิกสัญญา 79

## 2 · ลิสต์ลูกหนี้ค้างชำระ

```sql
SELECT  CONTRACT_NUMBER, CONTRACT_STATUS_ID, NUMBER_OF_OD_INSTALLMENT,
        OD_AMOUNT, PENALTY_AMT, PERIOD_DUE_DATE, LAST_REPAY_DATE,
        ASSIGN_TO_TEAM_DESC, EMP_NAME
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.ITOS_COLLECTION_DETAIL
WHERE   CONTRACT_STATUS_ID IN ('OD3', 'OD4', 'OD5', 'OD6');   -- ค้าง 3 งวดขึ้นไป
```
1.2 วินาที · 2,064 แถว
- DETAIL เก็บ**เฉพาะสัญญาที่ค้าง** (`NUMBER_OF_OD_INSTALLMENT > 0`) และ**ไม่มีประวัติ** — โหลดทับทุกคืน
- `CONTRACT_STATUS_ID`: `OD1`–`OD6` = ค้าง 1–6 งวด · `WO` = Write Off (1,184 สัญญา)
- กรองคนที่ต้องตามจริง: `CONTRACT_STATUS_DESC <> 'Write Off' AND CONTRACT_STATUS_ID <> 'CLS'` (ดู [[ITOS Flood Waiver 2026-09]])

## 3 · ดูสัญญาเดียวแบบสด

```sql
SELECT  c.CONTRACT_NO, c.CONTRACT_DATE, c.CONTRACT_FIRST_PAYMENTDATE,
        c.CONTRACT_STATUS, c.CONTRACT_SUBSTATUS, c.CONTRACT_BRANCHCODE, c.CONTRACT_DEALERNAME,
        o.OUTS_PAIDTERM, o.OUTS_OVDTERM, o.OUTS_OVDDAY, o.OUTS_OVDAMTTOTAL,
        o.OUTS_AMTTOTAL, o.OUTS_DUEDATE, o.OUTS_LASTPAYMENTDATE,
        a.ASSET_BRAND, a.ASSET_MODEL, a.ASSET_SERIALNO
FROM        ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_CONTRACT    c
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_OUTSTANDING o ON o.OUTS_CONTRACTNO  = c.CONTRACT_NO
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_ASSET       a ON a.ASSET_CONTRACTNO = c.CONTRACT_NO
WHERE   c.CONTRACT_NO = 'TFF2510-005889';      -- ← เลขสัญญา
```
2.1 วินาที · 1 แถว · join 3 ตารางได้เพราะกรองสัญญาเดียว — **ถ้าเอาทั้งพอร์ตให้ดึงแยกแล้ว join ใน pandas**

## 4 · ตารางงวดผ่อน

```sql
SELECT  SCHEDULE_TERMNO, SCHEDULE_DUEDATE, SCHEDULE_TOTALINSTAMT,
        SCHEDULE_PRINCIPALAMT, SCHEDULE_INTERESTAMT, SCHEDULE_VATAMT, SCHEDULE_PRINCIPALBAL
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_PMTSCHDLE
WHERE   SCHEDULE_CONTRACTNO = 'TFF2510-005889'
ORDER BY SCHEDULE_TERMNO;
```
⏱ **107 วินาที** สำหรับสัญญาเดียว (ตาราง 6 ล้านแถว · filter ไม่ถูกส่งไปต้นทาง) · ถ้าต้องหลายสัญญาให้ดึงทั้งตารางครั้งเดียว · ตารางนี้ไม่มีสถานะว่างวดไหนจ่ายแล้ว → เทียบกับ `S_OUTSTANDING.OUTS_PAIDTERM`

## 5 · ข้อมูลลูกค้าของสัญญา

```sql
SELECT  c.CONTRACT_NO, s.CUST_CODE, s.CUST_TITLETH, s.CUST_NAMETH, s.CUST_LASTNAMETH,
        s.CUST_BIRTHDATE, s.CUST_GENDER, s.CUST_OCCUPATION, s.CUST_SALARY
FROM        ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_CONTRACT c
JOIN        ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_CUSTOMER s ON s.CUST_CODE = c.CONTRACT_CUSTCODE
WHERE   c.CONTRACT_NO = 'TFF2510-005889';
```
1.2 วินาที · 🔴 PII + รายได้ · ตัวอย่างเพิ่มเติมของตารางนี้ → [[#S_CUSTOMER — ตัวอย่าง query]]

## 6 · หาทุกสัญญาของคนเดียวกัน

`CUST_CODE` ไม่ใช่รหัสคน — มี 343,312 รหัส เกือบเท่าจำนวนสัญญา (343,322) · เลขบัตรไม่ซ้ำ 342,486 → **คนที่มีหลายสัญญาได้ `CUST_CODE` ใหม่ทุกสัญญา** ต้องรวมด้วย `CUST_CARDNO`

```sql
-- คนที่มีมากกว่า 1 สัญญา
SELECT  TOP 20 CUST_CARDNO, COUNT(*) AS contracts
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_CUSTOMER
WHERE   CUST_CARDNO IS NOT NULL
GROUP BY CUST_CARDNO HAVING COUNT(*) > 1
ORDER BY contracts DESC;

-- ทุกสัญญาของเลขบัตรหนึ่ง
SELECT  s.CUST_CARDNO, c.CONTRACT_NO, c.CONTRACT_DATE, c.CONTRACT_STATUS
FROM        ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_CUSTOMER s
JOIN        ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_CONTRACT c ON c.CONTRACT_CUSTCODE = s.CUST_CODE
WHERE   s.CUST_CARDNO = '<เลขบัตร 13 หลัก>';
```
6.4 / 3.0 วินาที · 🔴 เลขบัตร — ห้ามเก็บลงไฟล์

## 7 · เบอร์โทร

```sql
SELECT  t.TEL_PHONE, t.TEL_TYPE, t.TEL_ACTIVE, t.TEL_UPDATEDATE
FROM        ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_CONTRACT c
JOIN        ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.S_CUSTTEL  t ON t.TEL_CUSTCODE = c.CONTRACT_CUSTCODE
WHERE   c.CONTRACT_NO = 'TFF2510-005889';
```
1.4 วินาที · `TEL_TYPE` มีแค่ `P02` (เบอร์บ้านตาม master `PHOT` แต่ค่าจริงน่าจะเป็นมือถือ `[อนุมาน]`) · `TEL_ACTIVE = 0` มี 1,722 แถว

## 8 · ที่อยู่

```sql
SELECT  ADDR_TYPE, ADDR_NO, ADDR_MOO, ADDR_VILLAGE, ADDR_SOI, ADDR_ROAD,
        ADDR_DISTRICT,   -- ⚠️ = ตำบล
        ADDR_AMPHUR,     -- ⚠️ = อำเภอ
        ADDR_PROVINCE, ADDR_ZIPCODE, ADDR_ADDRESS
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.COLLECTION_S_ADDRESS
WHERE   ADDR_CONTRACTNO = 'TFF2510-005889';
```
⏱ 43 วินาที · 4 แถว (ทุกสัญญามีครบ 4 ประเภท `AD01`–`AD04`) · บางสัญญามี 2 แถวต่อประเภท → เอา `ADDR_ID` ล่าสุด
แปลงรหัสเป็นชื่อ → ดึง `dbo.HP_COMMON_PROVINCE` / `_DISTRICT` / `_SUBDISTRICT` แยกแล้ว merge · รายละเอียด [[ITOS - Address & Geography]]

## 9 · ประวัติการติดตาม

```sql
SELECT  n.NOTE_CREATEDATE, n.NOTE_RESULTCODE, r.RESULT_NAME,
        n.NOTE_APPOINTMENTSDATE, n.NOTE_MSG1, n.NOTE_CREATEBY
FROM        ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.COLLECTION_ORCL_T_NOTE   n
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.COLLECTION_ORCL_M_RESULT r ON r.RESULT_CODE = n.NOTE_RESULTCODE
WHERE   n.NOTE_CONTRACTNO = 'TFF2510-005889'
ORDER BY n.NOTE_CREATEDATE DESC;
```
3.4 วินาที · ตารางมี 767,250 บันทึก ตั้งแต่ 2025-09-28 · ผลที่พบบ่อย: `NA` ไม่รับสาย 167,600 · `PP` นัดชำระ 125,591 · `TN` ติดต่อไม่ได้ 11,369 · `PTP` ชำระแล้ว 7,546
**`TJA` (358,910) · `MPP` (81,668) · `CC` (12,591) ไม่มีใน `M_RESULT`** → ยังไม่รู้ความหมาย

## 10 · เคสนี้ใครถือ และ bucket

```sql
SELECT  j.JOB_CONTRACT_NO, j.JOB_BUCKET_CODE, j.JOB_OVD_DAY, j.JOB_OVD_AMT,
        j.JOB_PAID_STATUS, j.JOB_COLLECTOR_CODE, m.COLLECTOR_NAMETH, j.JOB_ASSIGN_DATE
FROM        ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.T_JOBTRANS  j
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.M_COLLECTOR m ON m.COLLECTOR_CODE = j.JOB_COLLECTOR_CODE
WHERE   j.JOB_CONTRACT_NO = 'TFF2510-005889';

-- สรุปตาม bucket
SELECT  JOB_BUCKET_CODE, COUNT(*) AS jobs, SUM(JOB_OVD_AMT) AS ovd_amt
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection.T_JOBTRANS
GROUP BY JOB_BUCKET_CODE;
```
1–2 วินาที · 2026-10-09: BK001 18,655 งาน · BK002 1,820 · BK003 1,002 · BK004 712 · BK005 587 · BK006 465

## 11 · ค่าทวงถาม

```sql
SELECT  FEE_DATE, FEE_CODE, FEE_DESCRIPTION, FEE_RECEVIEAMT, FEE_STATUS
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.COLLECTION_S_COLELCTION_FEE
WHERE   FEE_CONTRACTNO = 'TFF2510-005889'
ORDER BY FEE_DATE;
```
0.8 วินาที · `FEE_CODE 4003` = ค่าทวงถาม 50 บาท · `FEE_RECEVIEAMT` เป็น null ในรหัสที่พบบ่อย · ⚠️ `FEE_CREATEDATE` สูงสุดเป็น **2026-12-14** (อนาคต) — ข้อมูลผิดปกติ

## 12 · ยอดคงค้างและ DPD รายเดือน

**ตารางเดียวที่ย้อนเวลาได้** — snapshot สิ้นเดือน 2025-08 → 2026-09 (14 เดือน) · มี DPD · ค่าเผื่อหนี้สงสัยจะสูญ · TFRS9

```sql
-- ทั้งพอร์ตรายเดือน
SELECT  AsOfYear, AsOfMonth, COUNT(*) AS contracts,
        SUM(TOTAL_BALANCE) AS total_balance,
        SUM(CASE WHEN DPD > 90 THEN TOTAL_BALANCE ELSE 0 END) AS npl_balance
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_cash_receive.T_SnapShort_Report_OutStanding_Hp
GROUP BY AsOfYear, AsOfMonth
ORDER BY AsOfYear, AsOfMonth;

-- สัญญาเดียวย้อนหลัง
SELECT  AsOfYear, AsOfMonth, DPD, UNFINISH_PERIOD, OUTSTANDING_PRINCIPAL, TOTAL_BALANCE
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_cash_receive.T_SnapShort_Report_OutStanding_Hp
WHERE   CONT_CODE = 'TFF2510-005889'
ORDER BY AsOfYear, AsOfMonth;
```
3.1 / 1.7 วินาที · 2026-09: 324,470 สัญญา · ยอดรวม ฿9,616 ล้าน · DPD > 90 ฿79.3 ล้าน
🔴 มี `ID_CARD` · ชื่อ — อย่า `SELECT *`

## 13 · ประวัติสถานะสัญญารายเดือน

```sql
SELECT  AsOfYear, AsOfMonth, Contract_Status, Contract_SubStatus,
        Contract_WriteOff_Flag, Contract_CloseDate
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_cash_receive.H_Contract
WHERE   Contract_Code = 'TFF2510-005889'
ORDER BY AsOfYear, AsOfMonth;
```
6.9 วินาที · 1 แถวต่อสัญญาต่อเดือน (2025-08 → 2026-09) · 87 คอลัมน์ รวมดอกเบี้ย EIR · write off · ปรับโครงสร้างหนี้ · เคลมประกัน
`Contract_Status`: `ACT` / `CLS` / `TEM` · `Contract_SubStatus` เป็นรหัส (`100` 320,026 · `103` 8,658 · `102` 1,401 · `208` 1,157 · `201` 79) → **ยังไม่รู้ความหมายของรหัส**

## 14 · เบี้ยปรับ และยอดคงเหลือ

```sql
SELECT  CONTRACT_NUMBER, PENALTY_OWED_CALC, PENALTY_PAID,
        REMAINING_OUTSTANDING, LAST_REPAY_DATE
FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.ITOS_STAGE_CASH_SUMMARY
WHERE   CONTRACT_NUMBER = 'TFF2510-005889';
```
1.2 วินาที · `PENALTY_OWED_CALC` = `DETAIL.PENALTY_AMT` ทุกสัญญา · มีทุกสัญญา (329,161) ไม่ใช่เฉพาะที่ค้าง

## 15 · โปรไฟล์ลูกหนี้ค้าง

```sql
SELECT  p.GENDER, COUNT(*) AS contracts, AVG(p.AGE) AS avg_age, AVG(p.INCOME) AS avg_income
FROM        ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.ITOS_COLLECTION_DETAIL    d
JOIN        ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.ITOS_COLLECTION_PORTFOLIO p
       ON   p.EXTRACT_DATE = d.EXTRACT_DATE AND p.CONTRACT_ID = d.CONTRACT_ID
GROUP BY p.GENDER;
```
3 วินาที · join ต้องใช้ **ทั้ง `EXTRACT_DATE` และ `CONTRACT_ID`** · ถ้าต้องทั้งพอร์ตใช้ `ITOS_STAGE_CONTRACT_BASE` (มี `GENDER` `AGE` `INCOME` `CREDIT_SCORING` ทุกสัญญา)

---

## S_CUSTOMER — ตัวอย่าง query

`[ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]` · 343,317 แถว · 67 คอลัมน์ · **ข้อมูลสด** (มีลูกค้าใหม่ของวันนี้)
รายชื่อคอลัมน์ทั้งหมด → [[ITOS Overview#`S_CUSTOMER` — ทะเบียนลูกค้า 67 คอลัมน์]]

> 🔴 ตารางนี้มีชื่อ · เลขบัตร · วันเกิด · รายได้ — query ที่ดึงรายคนใช้ดูบนจอเท่านั้น ห้ามเซฟลงไฟล์ใน repo
> ใส่ `N` หน้าข้อความภาษาไทยเสมอ (`N'สมชาย'`)

### สิ่งที่ต้องรู้ก่อน query (ตรวจ 2026-10-09)

| เรื่อง | ของจริง |
|---|---|
| `CUST_CODE` | **1 รหัสต่อ 1 สัญญา** ไม่ใช่ต่อคน (343,312 รหัส) → รวมคนด้วย `CUST_CARDNO` |
| `CUST_CARDNO` | มีครบทุกแถว · 13 หลักทุกแถว · **checksum ถูก 100%** · ไม่ซ้ำ 342,486 คน |
| คนที่มีหลายสัญญา | 2 สัญญา 808 คน · 3 สัญญา 9 คน · 6 สัญญา 1 คน |
| `CUST_GENDER` | **ว่างเกือบทุกแถว** (343,316) → ใช้คำนำหน้า `CUST_TITLETH` แทน (นางสาว 182,839 · นาย 140,548 · นาง 18,772 · อื่นๆ 1,158) |
| `CUST_OCCUPATION` | **null ทุกแถว** — อาชีพใช้ `ITOS_STAGE_CONTRACT_BASE.OCCUPATION_DESC` แทน |
| คู่สมรส `CUST_SP_*` · รหัส ธปท. `CUST_BOT*` | **ว่างทุกแถว** — คอลัมน์มี แต่ไม่ได้กรอก (ต่างจากที่ wiki บอก) |
| `CUST_CARDTYPE` · `CUST_TYPECODE` · `CUST_NATIONALITY` | ค่าเดียวทั้งตาราง: บัตรประชาชน · `CT1` · ไทย |
| `CUST_SALARY` | มีเกือบครบ (ว่าง/0 แค่ 21 แถว) |
| `CUST_ASOFDATE` | **เก็บเป็นข้อความ** (`Sep 30 2026 12:00AM`) → `MAX()` / `ORDER BY` ตรง ๆ เรียงผิด ต้อง `TRY_CONVERT(date, CUST_ASOFDATE)` · ค่าคือวันที่เพิ่มลูกค้า (2025-01-15 → วันนี้ · ~1,000–2,400 คน/วัน) |
| เชื่อมสัญญา | `S_CONTRACT.CONTRACT_CUSTCODE = S_CUSTOMER.CUST_CODE` · ลูกค้าทุกแถวมีสัญญา (orphan 0) |

### ดูข้อมูล / ค้นหารายคน

```sql
-- ดูตัวอย่าง 10 แถว
SELECT TOP 10 CUST_CODE, CUST_TITLETH, CUST_NAMETH, CUST_LASTNAMETH, CUST_BIRTHDATE, CUST_SALARY
FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER];

-- ค้นด้วยรหัสลูกค้า (ทุกคอลัมน์)
SELECT *
FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]
WHERE  CUST_CODE = '<CUST_CODE>';

-- ค้นด้วยเลขบัตร
SELECT CUST_CODE, CUST_TITLETH, CUST_NAMETH, CUST_LASTNAMETH, CUST_BIRTHDATE
FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]
WHERE  CUST_CARDNO = '<เลขบัตร 13 หลัก>';

-- ค้นด้วยชื่อ (ขึ้นต้นด้วย)
SELECT TOP 50 CUST_CODE, CUST_TITLETH, CUST_NAMETH, CUST_LASTNAMETH, CUST_BIRTHDATE
FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]
WHERE  CUST_NAMETH LIKE N'สมชาย%'
  AND  CUST_LASTNAMETH LIKE N'ใจ%';
```
ทั้งหมด < 1.5 วินาที

### ลูกค้าพร้อมสัญญา

```sql
SELECT s.CUST_CODE, s.CUST_NAMETH, s.CUST_LASTNAMETH,
       c.CONTRACT_NO, c.CONTRACT_DATE, c.CONTRACT_STATUS, c.CONTRACT_SUBSTATUS
FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER] s
JOIN   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CONTRACT] c
       ON c.CONTRACT_CUSTCODE = s.CUST_CODE
WHERE  s.CUST_CARDNO = '<เลขบัตร 13 หลัก>';      -- คืนทุกสัญญาของคนนี้
```
3.2 วินาที

### ลูกค้าใหม่รายวัน

```sql
SELECT TRY_CONVERT(date, CUST_ASOFDATE) AS added_date, COUNT(*) AS customers
FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]
GROUP BY TRY_CONVERT(date, CUST_ASOFDATE)
ORDER BY added_date DESC;
```
3 วินาที

### โปรไฟล์ลูกค้า (ไม่มี PII ในผลลัพธ์)

```sql
-- ตามคำนำหน้า (แทนเพศ)
SELECT CUST_TITLETH, COUNT(*) AS customers
FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]
GROUP BY CUST_TITLETH
ORDER BY customers DESC;

-- ช่วงอายุ
SELECT age_band, COUNT(*) AS customers
FROM (
    SELECT CASE
             WHEN age < 20 THEN '<20'   WHEN age < 30 THEN '20-29'
             WHEN age < 40 THEN '30-39' WHEN age < 50 THEN '40-49'
             WHEN age < 60 THEN '50-59' WHEN age >= 60 THEN '60+'
             ELSE 'ไม่มีวันเกิด' END AS age_band
    FROM (
        SELECT DATEDIFF(year, CUST_BIRTHDATE, GETDATE())
             - CASE WHEN DATEADD(year, DATEDIFF(year, CUST_BIRTHDATE, GETDATE()), CUST_BIRTHDATE) > GETDATE()
                    THEN 1 ELSE 0 END AS age
        FROM [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]
    ) a
) b
GROUP BY age_band
ORDER BY age_band;

-- ช่วงเงินเดือน
SELECT salary_band, COUNT(*) AS customers
FROM (
    SELECT CASE
             WHEN CUST_SALARY IS NULL OR CUST_SALARY = 0 THEN N'ไม่ระบุ'
             WHEN CUST_SALARY < 15000 THEN '<15k'
             WHEN CUST_SALARY < 30000 THEN '15-30k'
             WHEN CUST_SALARY < 50000 THEN '30-50k'
             ELSE '50k+' END AS salary_band
    FROM [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]
) x
GROUP BY salary_band;
```
1.6–4.6 วินาที · ผล 2026-10-09
- อายุ: 20–29 ปี 159,545 · 30–39 ปี 94,303 · 40–49 ปี 61,358 · 50–59 ปี 27,655 · 60+ 456
- เงินเดือน: <15k 59,366 · 15–30k 198,729 · 30–50k 58,727 · 50k+ 26,474

### ตรวจคุณภาพข้อมูล

```sql
-- ภาพรวมความครบ
SELECT COUNT(*) AS total,
       SUM(CASE WHEN CUST_CARDNO IS NULL OR LTRIM(CUST_CARDNO) = '' THEN 1 ELSE 0 END)            AS no_card,
       SUM(CASE WHEN LEN(CUST_CARDNO) = 13 AND CUST_CARDNO NOT LIKE '%[^0-9]%' THEN 1 ELSE 0 END)   AS card_13_digits,
       SUM(CASE WHEN CUST_BIRTHDATE IS NULL THEN 1 ELSE 0 END)                                     AS no_birthdate,
       SUM(CASE WHEN CUST_SP_NAMETH IS NOT NULL AND LTRIM(CUST_SP_NAMETH) <> '' THEN 1 ELSE 0 END) AS has_spouse,
       COUNT(DISTINCT CUST_CODE)   AS distinct_code,
       COUNT(DISTINCT CUST_CARDNO) AS distinct_card
FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER];

-- checksum เลขบัตรประชาชน (หลักที่ 13 = (11 - Σ d[i]×(14-i) mod 11) mod 10)
SELECT SUM(CASE WHEN (11 - (
           CAST(SUBSTRING(CUST_CARDNO, 1,1) AS int)*13 + CAST(SUBSTRING(CUST_CARDNO, 2,1) AS int)*12 +
           CAST(SUBSTRING(CUST_CARDNO, 3,1) AS int)*11 + CAST(SUBSTRING(CUST_CARDNO, 4,1) AS int)*10 +
           CAST(SUBSTRING(CUST_CARDNO, 5,1) AS int)*9  + CAST(SUBSTRING(CUST_CARDNO, 6,1) AS int)*8  +
           CAST(SUBSTRING(CUST_CARDNO, 7,1) AS int)*7  + CAST(SUBSTRING(CUST_CARDNO, 8,1) AS int)*6  +
           CAST(SUBSTRING(CUST_CARDNO, 9,1) AS int)*5  + CAST(SUBSTRING(CUST_CARDNO,10,1) AS int)*4  +
           CAST(SUBSTRING(CUST_CARDNO,11,1) AS int)*3  + CAST(SUBSTRING(CUST_CARDNO,12,1) AS int)*2
       ) % 11) % 10 = CAST(SUBSTRING(CUST_CARDNO,13,1) AS int) THEN 1 ELSE 0 END) AS valid,
       COUNT(*) AS checked
FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]
WHERE  LEN(CUST_CARDNO) = 13 AND CUST_CARDNO NOT LIKE '%[^0-9]%';

-- 1 คนมีกี่สัญญา
SELECT contracts_per_person, COUNT(*) AS people
FROM (
    SELECT CUST_CARDNO, COUNT(*) AS contracts_per_person
    FROM   [ILOAN_DATASOURCE].[ILOAN_DATASOURCE].[ext_collection].[S_CUSTOMER]
    WHERE  CUST_CARDNO IS NOT NULL AND LTRIM(CUST_CARDNO) <> ''
    GROUP BY CUST_CARDNO
) x
GROUP BY contracts_per_person
ORDER BY contracts_per_person;
```
⏱ ภาพรวมความครบ 56 วินาที · checksum 19 วินาที · กี่สัญญาต่อคน 9 วินาที (สแกนทั้งตาราง)

---

## รหัสที่ต้องรู้

ดูทั้งหมด: `SELECT * FROM ...ext_collection.M_MASTERINFO WHERE MASTERINFO_TYPE = '<type>'` (400 รหัส · 23 type)

| type | รหัส |
|---|---|
| `ADDT` ประเภทที่อยู่ | `AD01` ปัจจุบัน · `AD02` ทะเบียนบ้าน · `AD03` ที่ทำงาน · `AD04` จัดส่งเอกสาร |
| `PHOT` ประเภทเบอร์ | `PT01` มือถือ · `PT02` บ้าน · `PT03` ที่ทำงาน (แต่ `S_CUSTTEL.TEL_TYPE` ใช้ `P02` — คนละชุดรหัส) |
| `BUCK` | `BK000`–`BK007` = Bucket 0–7 |
| `CUST` | `CT1` ผู้เช่าซื้อ/ผู้กู้ · `CT2` ผู้ค้ำประกัน · `CT3` อื่น ๆ |
| `PayStatus` | `FULL` Current · `NONE` Not Pay · `PART` Partial · `SUCC` Success |
| `STAC` | รหัสสถานะแบบเช่าซื้อรถ (10 ปกติ · 21 บอกเลิก · 91 ปิดปกติ · 99 Closing Write Off ฯลฯ) `[อนุมาน: มาจาก template ระบบ อาจไม่ได้ใช้กับมือถือ]` |

**สถานะสัญญา** (`S_CONTRACT.CONTRACT_STATUS` · `ITOS_STAGE_CONTRACT_BASE.CONTRACT_STATUS_RAW` · `H_Contract.Contract_Status`): `ACT` ใช้งาน · `CLS` ปิด · `TEM` ยกเลิก (terminate)
**สถานะติดตามหนี้** (`ITOS_COLLECTION_DETAIL.CONTRACT_STATUS_ID`): `OD1`–`OD6` · `WO`

---

## ตารางอื่นใน `ILOAN_DATASOURCE` ที่ยังไม่ได้สำรวจ

`dbo.M_CUST_*` (ทะเบียนลูกค้า เบอร์ ที่อยู่ blacklist credit line) · `R_CONTRACT` · `V_Contract_DPD_List` · `V_EGG_CONTRACT` · `V_EGG_CUSTOMER_CARD` · `CASH_RECEIVE_S_CONTRACT` · `T_Snap_Cust_Installment` · `T_CONTRACT_LEGAL*` → ยังไม่รู้ว่าเป็นของระบบไหน (ITOS หรือระบบอื่นที่ใช้ฐานเดียวกัน)

## คำถามที่ยังไม่มีคำตอบ

- ผลติดตาม `TJA` · `MPP` · `CC` คืออะไร (ไม่มีใน `M_RESULT`)
- `H_Contract.Contract_SubStatus` รหัส 100 / 102 / 103 / 201 / 208 คืออะไร
- `REMAINING_OUTSTANDING` vs `OUTS_AMTTOTAL` ต่างกัน 369 สัญญา — เพราะอะไร
- `FEE_CREATEDATE` ที่เป็นวันในอนาคต (2026-12-14)
- ข้อมูล NCB อยู่ตารางไหน (ดู [[ITOS Overview#ข้อมูล NCB (เครดิตบูโร)]])

## เชื่อมกับโน้ตอื่น

[[ITOS Overview]] · [[ITOS - Address & Geography]] · [[K2 - Query Cookbook]] · [[Collection Union (K2 + ITOS)]] · [[ITOS Flood Waiver 2026-09]] · [[Consent & PDPA]]
