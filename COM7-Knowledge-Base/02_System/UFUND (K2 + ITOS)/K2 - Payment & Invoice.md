# K2 — Payment & Invoice

ค่างวด · ใบแจ้งหนี้ · การรับชำระ · เอกสารภาษี · survey 2026-08-26

---

## The collection flow

```
CONTRACT ──► CUSTOMER_CARD ──► INVOICE ──► REPAYMENT ──► ACCOUNT
             5,816,540         4,396,632   5,205,081     25,977,656
             ตารางผ่อนรายงวด      ใบแจ้งหนี้     รับชำระจริง     ลงบัญชี

ช่องทางรับเงิน:  LOG_SCB_BILLPAYMENT (8.0M) · LOG_SCB_BILLPAYMENT_AUTO (7.1M)
                 BANK_IMPRORT (4.4M) · TTP_QR_DOWN (237k) · LOG_SCB_DOWNPAYMENT (116k)
เอกสารภาษี:      TAX_INVOICE (5.2M) · TTP_VAT_RPT (4.8M) · TTP_INV_BARCODE (4.5M)
```

---

## `CUSTOMER_CARD` — 5,816,540 rows · 26 columns

### ⚠️ Misleading name — **this is not a customer table**

เป็น **"การ์ดลูกหนี้" 1 แถวต่อ 1 งวดผ่อน** ของ 288,198 สัญญา · `INSTALL_NUM` ตั้งแต่ 1 ถึง **84**

ใครที่เห็นชื่อ `CUSTOMER_CARD` แล้วคิดว่าเป็นทะเบียนลูกค้าจะได้ผลผิดทันที — ข้อมูลลูกค้าอยู่ที่ `PERSON` ดู [[K2 - Customer & Address]]

| กลุ่ม | คอลัมน์ |
|---|---|
| คีย์ | `ID`, `CONTRACT_ID`, `CONTRACT_NUMBER`, `APPLICATION_NUMBER`, `INSTALL_NUM` |
| งวด | `DUEDATE`, `INSTALL_AMT`, `PAY_PRINCIPLE`*, `PAY_INTEREST`, `PAY_INSTALL_VAT` |
| ยอดคงเหลือ | `OUTSTD_SUM_PRINCIPLE`, `OUTSTD_SUM_INTEREST`, `SUM_OUTSTAND` |
| ค้างชำระ | `INSTALL_OD_01`, `INSTALL_OD_02`, `INSTALL_OD_SUM`, `SUM_OD_AMT`, `PENALTY_AMT`, `COLLECT_AMT` |
| เอกสาร | `INVOICE_NUMBER`, `RECEIPT_NUMBER` |
| ประกัน/ค่าธรรมเนียม | `REVENUE_INS_MARGIN`, `REVENUE_INS_MARGIN_OUTSTD`, `FEE_INSTALL`, `FEE_SUM` |
| ส่วนลด | `DISCOUNT_AMT` |

\* `PRINCIPLE` ควรเป็น `PRINCIPAL` — typo ที่ vault บันทึกไว้แล้ว

**5.8M ÷ 288k = เฉลี่ย 20 งวดต่อสัญญา** สอดคล้องกับ `MT_INSTALLMENT` ที่เปิดใช้ 9/12/18/24/36 งวด

**`DUEDATE` มีแค่ 2 ค่าทั้งตาราง — วันที่ 1 (3,000,934 งวด) และ 16 (2,815,636 งวด)**
**`RECEIPT_NUMBER IS NOT NULL` = งวดนั้นชำระแล้ว** (4,335,203 ชำระ · 1,481,373 ยังไม่ชำระ)
สองกฎนี้มาจากเอกสารความรู้ของทีม ตรวจกับฐานแล้ว → [[K2 - Business Rules]] ข้อ 1–2

**คอลัมน์ยอดค้างเก็บเป็น `nvarchar`** — `INSTALL_OD_01`, `INSTALL_OD_02`, `INSTALL_OD_SUM` เป็นข้อความไม่ใช่ตัวเลข ต้อง cast ก่อนคำนวณ (ปัญหาเดียวกันปรากฏใน `COLLECTION_OD.NUMBER_OF_OD_INSTALLMENT`)

ตัวอย่างจริง (สัญญา 24 งวด ค่างวด 2,062.95): งวด 1 = เงินต้น 666.37 + ดอกเบี้ย 1,261.62 → งวด 4 = เงินต้น 761.01 + ดอกเบี้ย 1,166.98 — **ดอกเบี้ยลดลงตามเงินต้นแบบ effective**

---

## `INVOICE` — 4,396,632 rows · 24 columns

`INVOICE_ID` · `INVOICE_NUMBER` · `CONTRACT_ID` · **`CUSTOMER_CARD_ID`** · `INVOICE_DATE` · `DUE_DATE` · `STATUS_ID` · `INVOICEE_TYPE`

ยอด: `AMOUNT`, `VAT_AMT`, `WHT_AMT`, `SUM_AMT`, `DES_SUM_AMT` (จำนวนเงินเป็นตัวอักษร)
ค้าง: `AMT_OLD`, `INSTALL_NUM_OLD`, `INSTALL_OUTSTAND`, `SUM_OUTSTAND`, `INSTALL_CURRENT`, `INSTALL_OD_01/02/SUM`, `SUM_OD_AMT`, `PENALTY_AMT`, `COLLECT_AMT`

**`CUSTOMER_CARD_ID` คือกาวที่เชื่อมใบแจ้งหนี้กับงวดผ่อน** — ใบแจ้งหนี้ 1 ใบผูกกับ 1 งวด

4.4M ใบแจ้งหนี้ ต่อ 5.8M งวด → **ไม่ใช่ทุกงวดที่ออกใบแจ้งหนี้** (งวดในอนาคตยังไม่ออก) `[อนุมาน]`

---

## `REPAYMENT` — 5,205,081 rows · 47 columns

การรับชำระจริง ครอบคลุม 287,553 สัญญา

> ⚠️ **แก้ 2026-09-01 — เดิมโน้ตนี้เขียนสลับกัน** ตรวจกับข้อมูลจริงแล้วเป็นตรงข้าม

## ⭐ ตารางนี้บอก "จ่ายงวดไหน เมื่อไหร่" — สิ่งที่ `CUSTOMER_CARD` บอกไม่ได้

`CUSTOMER_CARD` บอกได้แค่ *จ่ายแล้ว/ยังไม่จ่าย* (`RECEIPT_NUMBER` ว่างหรือไม่ว่าง)
**`REPAYMENT` บอกวันที่เงินเข้าจริงรายงวด** — จำเป็นทุกครั้งที่ต้องตอบว่า *"คนนี้จ่ายมาหลังเราส่งรายชื่อไปหรือเปล่า"*

```sql
-- ประวัติการจ่ายรายงวดของสัญญาหนึ่ง
SELECT c.INSTALL_NUM, c.DUEDATE, r.REPAY_DATE AS วันที่เงินเข้าจริง,
       r.STATUS_ID, r.RECEIPT_NUMBER, r.REPAY_SUM_AMOUNT
FROM REPAYMENT r
JOIN CUSTOMER_CARD c ON c.ID = r.CUSTOMER_CARD_ID
WHERE r.REPAY_TYPE = 2 AND r.CONTRACT_ID = 129135
ORDER BY c.INSTALL_NUM;
```

**ตัวอย่างจริง `24129135`** (`CONTRACT_ID` 129135) — เคสที่เคยสงสัยว่าทำไมอยู่ในรายชื่อบอกเลิกทั้งที่ค้างแค่ 3 งวด

| งวด | ครบกำหนด | วันที่เงินเข้าจริง | สถานะ |
|---:|---|---|---|
| 18 | 2026-02-01 | 2026-02-18 | 33 จ่ายแล้ว |
| 19 | 2026-03-01 | **2026-08-30** | 33 จ่ายแล้ว |
| 20 | 2026-04-01 | **2026-08-30** | 33 จ่ายแล้ว |
| 21 | 2026-05-01 | **2026-08-30** | 33 จ่ายแล้ว |
| 22 | 2026-06-01 | – | 32 ยังค้าง |
| 23 | 2026-07-01 | – | 32 ยังค้าง |
| 24 | 2026-08-01 | – | 32 ยังค้าง |

**จ่าย 3 งวดรวดเมื่อ 30 ส.ค.** หลังรายชื่อถูกคัดไปตั้งแต่ 3 ส.ค. — snapshot บอก 5 งวด การ์ดวันนี้บอก 3 งวด
`REPAYMENT` เป็นตัวเดียวที่อธิบายช่องว่างนี้ได้

### `CUSTOMER_CARD_ID` — join ที่เชื่อถือได้

```sql
JOIN CUSTOMER_CARD c ON c.ID = r.CUSTOMER_CARD_ID
```

ทดสอบ 2026-09-01 กับ 1,033,171 แถวปี 2026 — **join ติด 1,033,169 (99.9998%)** และ `r.INSTALL = c.INSTALL_NUM` ตรงกันทุกแถวที่ join ติด
**เป็น join ที่แน่นที่สุดเส้นหนึ่งในฐานนี้** ต่างจาก join อื่นที่ต้องเดาจากชื่อคอลัมน์

### ⚠️ `PAY_*` = ที่ต้องชำระ · `REPAY_*` = ที่ชำระจริง — **ตรงข้ามกับที่ชื่อชวนคิด**

| ชั้น | คอลัมน์ | ความหมาย |
|---|---|---|
| **`PAY_*`** | `PAY_DATE`, `PAY_AMT`, `PAY_PENALTY`, `PAY_COLLECT`, `PAY_VAT`, `PAY_DISCOUNT`, `PAY_SUM_AMT`, `PAY_NAME` | **ยอดที่ต้องชำระ** — มีค่าตั้งแต่ตอนสร้างแถว |
| **`REPAY_*`** | `REPAY_DATE`, `REPAY_AMOUNT`, `REPAY_PENALTY`, `REPAY_COLLECT`, `REPAY_VAT`, `REPAY_WHT`, `REPAY_DISCOUNT`, `REPAY_SUM_AMOUNT`, `REPAY_NAME` | **ยอดที่ชำระจริง** — ว่างจนกว่าจะจ่าย |

**หลักฐาน** — แถวที่ยังไม่จ่าย (`STATUS_ID = 32`) 84,264 แถว

| | ว่างกี่แถว |
|---|---:|
| `REPAY_DATE` | **84,263** |
| `REPAY_SUM_AMOUNT` | **84,263** |
| `PAY_SUM_AMT` | **0** |
| `PAY_DATE` | 115 |

ระบบสร้างแถวรอไว้ล่วงหน้าพร้อมยอดที่ต้องจ่าย (`PAY_*`) แล้วเติม `REPAY_*` ตอนเงินเข้าจริง

> **ถ้าจะรู้ว่าเงินเข้าเมื่อไหร่ ใช้ `REPAY_DATE` · ถ้าจะรู้ว่าต้องจ่ายเท่าไหร่ ใช้ `PAY_SUM_AMT`**
> ใช้สลับกันจะได้ผลว่าทุกคนจ่ายครบตรงเวลา

### สูตรยอดเงิน — ตรวจแล้ว 1,056,588 แถวปี 2026

| สูตร | ตรง |
|---|---:|
| `PAY_AMT + PAY_VAT = CUSTOMER_CARD.INSTALL_AMT` | 99.46% |
| `PAY_SUM_AMT = PAY_AMT + PAY_VAT + PAY_PENALTY + PAY_COLLECT` | 99.44% |
| `REPAY_AMOUNT ≈ PAY_AMT` (จ่ายตรงยอด) | 99.84% |

**`PAY_AMT` ไม่ใช่ค่างวด** — เป็นยอดก่อน VAT ค่างวดเต็มคือ `PAY_AMT + PAY_VAT`
ตัวอย่าง `24129135`: 1,681.46 + 117.70 = **1,799.16** = `INSTALL_AMT` · บวกค่าปรับ 100 + ค่าติดตาม 50 = `PAY_SUM_AMT` 1,949.16

### `STATUS_ID` — ใช้ 2 ค่าหลัก

| รหัส | `MT_STATUS` | แถว (`REPAY_TYPE=2`) | ความหมายจริง |
|---:|---|---:|---|
| **33** | Repay Complete | 4,255,575 | **จ่ายแล้ว** |
| **32** | Wait Repay by Transaction | 141,110 | **ยังไม่จ่าย** — แถวที่สร้างรอไว้ |
| 30 | In active | 610 | ซากข้อมูล |

**ตรงกับการ์ด 99.7%** — ตรวจกับ `CUSTOMER_CARD.RECEIPT_NUMBER` งวดปี 2026

| | การ์ดมีใบเสร็จ | การ์ดยังค้าง |
|---|---:|---:|
| `STATUS_ID = 33` | **1,053,090** | 3,466 |
| `STATUS_ID = 32` | 79 | **57,503** |

### `PAY_DATE` ตรงกับ `DUEDATE` แค่ 54% — ยังไม่รู้สาเหตุ

จาก 1,056,577 แถวปี 2026 `PAY_DATE = DUEDATE` แค่ 566,237 แถว
เคสตัวอย่างที่ดูตรงทุกงวด แต่ทั้งพอร์ตไม่ตรง — **อย่าใช้ `PAY_DATE` แทนวันครบกำหนด ให้ join เอา `DUEDATE` จากการ์ด** `[อนุมาน]`

ส่วน `REPAY_DATE` เทียบ `DUEDATE`: จ่ายก่อนกำหนด 490,411 · ตรงวัน 314,468 · จ่ายสาย 251,698

### Incoming payments are allocated horizontally

```
ค่าปรับ  →  ค่าติดตามทวงถาม  →  ดอกเบี้ย  →  เงินต้น        (ทีละงวดจนครบ แล้วข้ามไปงวดถัดไป)
```

**ลูกค้าที่จ่ายไม่เต็มจะไม่ได้ลดเงินต้นเลย** เพราะเงินถูกกินโดยค่าปรับกับค่าติดตามก่อน `[อนุมาน]`
เป็นเหตุผลที่ `REPAY_TYPE` ต้องแยกประเภท — เงินก้อนเดียวถูกแตกไปหลายรายการ
→ **ทำรายงาน "จ่ายค่างวดไปเท่าไหร่" ต้องกรอง `REPAY_TYPE` ไม่ใช่รวมทั้งก้อน** · ที่มา [[K2 - Fee Policy]]

**`PAY_NAME` มี index (`INNO_PAY_NAME`)** — ชื่อผู้ชำระอาจไม่ใช่ผู้ทำสัญญา ระบบตั้งใจให้ค้นได้

### `REPAY_TYPE` — from `MT_REPAY_TYPE`

ตรวจใหม่ 2026-10-12 (แยกตาม `STATUS_ID` → `MT_STATUS.HP_STA_ID`)

| `REPAY_TYPE` | ความหมาย | `STATUS_ID` | แถว | เงินอยู่คอลัมน์ไหน |
|---|---|---|---:|---|
| 2 | ค่างวดเช่าซื้อ | **33** Repay Complete | 4,393,921 | `PAY_AMT` + `PAY_VAT` + **`PAY_PENALTY`** + **`PAY_COLLECT`** − `PAY_DISCOUNT` = `PAY_SUM_AMT` |
| 2 | | 32 Wait Repay (ยังไม่จ่าย) | 148,498 | — |
| 2 | | 30 In active | 612 | |
| 4 | ค่าติดตามทวงถาม | 33 | 529,308 | **`REPAY_SUM_AMOUNT`** (50 บาท 459,367 · 100 บาท 68,458) · `PAY_*` ว่างเกือบทั้งหมด |
| 1 | เงินดาวน์ | **29** Active (ไม่ใช่ 33) | 291,599 | `PAY_AMT` + `PAY_VAT` · ผูก `APP_ID` |
| NULL | | 29 / 30 / NULL | 1,809 | |
| 3 · 5 | ค่าเบี้ยปรับ · ค่าเช่าซื้อ | | **0** | มีใน `MT_REPAY_TYPE` แต่ไม่เคยใช้ |

**เบี้ยปรับไม่มีแถวของตัวเอง** — อยู่ในคอลัมน์ `PAY_PENALTY` ของแถว type 2 (รวม ฿116.2 ล้าน) · ค่าติดตามที่จ่ายจริงอยู่ใน `PAY_COLLECT` ของแถว type 2 (฿32.5 ล้าน)
`[อนุมาน]` แถว type 4 คือ**การตั้งหนี้**ค่าติดตาม 50 บาท/ครั้ง (ยอดอยู่ฝั่ง `REPAY_*` = ที่ต้องจ่าย) ส่วนเงินที่รับจริงไปลงใน `PAY_COLLECT` ของแถวค่างวด — ยอดใกล้กัน (฿29.9 ล้าน vs ฿32.5 ล้าน) แต่ยังไม่ได้ยืนยันรายสัญญา

**สรุปการกรอง**
- เงินที่รับจริงทั้งหมด (ค่างวด + VAT + เบี้ยปรับ + ค่าติดตาม) → `REPAY_TYPE = 2 AND STATUS_ID = 33` แล้วใช้ `PAY_SUM_AMT` · ไม่ต้องบวก type 4 (จะนับค่าติดตามซ้ำ)
- เฉพาะค่างวด → `PAY_AMT` (+ `PAY_VAT`) ของแถวเดียวกัน
- เงินดาวน์ → `REPAY_TYPE = 1` ใช้ `STATUS_ID = 29` · กรอง 33 จะได้ 0 แถว

**ค่าติดตามทวงถาม 515,382 รายการ** ≈ 10% ของรายการรับชำระทั้งหมด — เป็นรายได้ของธุรกิจอีกทาง `[อนุมาน]`

### Unusually many indexes

`REPAYMENT` มี **21 index** ส่วนใหญ่เป็น covering index ชื่อยาวแบบ `INDEX_NCL_REPAYMENT_CONTRACT_ID_REPAY_TYPE_STATUS_ID_...`
→ ตารางนี้ถูก query หนักมากในการทำรายงาน และมีคนมานั่ง tune แล้ว `[อนุมาน]` **การเพิ่ม load จาก ETL ต้องระวัง**

### Bad data found

`MIN(REPAY_DATE) = 1067-07-09` — **ปีพุทธศักราชถูกกรอกผิดเป็น ค.ศ.** อย่างน้อย 1 แถว
→ ต้องมี date range filter ตอน ingest ไม่งั้น partition จะแตกไปปี 1067

---

## `PAYMENT` — 286,196 rows · 24 columns

**เงินขาออก ไม่ใช่เงินเข้า** — จ่ายให้พาร์ทเนอร์ที่ขายเครื่อง

`PAYMENT_ID` · `APP_ID` · `PV_ID` · `PV_NUMBER` · `PO_NUMBER` · `INV_PN_NUMBER`
`SUBSIDY_PAY` · `REBATE` · `DEDUCT_DOWN_AMT` · `DEDUCT_FEE_HP` · `DEDUCT_SUBSIDY_RECEIPT`
`AMOUNT` · `WHT_AMOUNT` · `VAT_AMOUNT` · `SUM_AMOUNT` · `PAY_TYPE` · `BANK` · `BANK_BRANCH` · `CHEQUE_NUMBER` · `ACCOUNT_NUMBER`

`MT_TYPE_PAYMENT` มีค่าอย่าง "ค่า Commission", "ค่า Commission Extra 1–3" → **จ่ายค่าคอมให้คนขาย**
คู่กับ `PURCHASE_ORDER` (290,213) และ `RECORD_RECEIPT_PAYMENT` (286,258) — ทั้งสามใกล้เคียง 288k สัญญา = **1 ชุดต่อ 1 สัญญา** `[อนุมาน]`

`MT_TYPE_PAYMENT` ยังมี "ค่ารถยนต์" ซึ่งไม่เข้ากับธุรกิจเครื่อง IT — น่าจะเป็น master ที่ copy มาจากระบบเช่าซื้อรถ `[อนุมาน]`

---

## Payment channels

| ตาราง | แถว | คืออะไร |
|---|---:|---|
| `LOG_SCB_BILLPAYMENT` | 8,046,041 | bill payment ผ่าน SCB |
| `LOG_SCB_BILLPAYMENT_AUTO` | 7,091,407 | หักบัญชีอัตโนมัติ SCB |
| `BANK_IMPRORT`* | 4,411,373 | ไฟล์ import จากธนาคาร |
| `TRANSACTION_REPAY` | 9,726,871 | 7 คอลัมน์ · แก้ล่าสุด 2022-03-17 |
| `TTP_QR_DOWN` | 237,610 | จ่ายดาวน์ด้วย QR |
| `LOG_SCB_DOWNPAYMENT` | 116,117 | จ่ายดาวน์ผ่าน SCB |
| `RESERVER_REPAYMENT` | 619,320 | เงินสำรองรอตัดชำระ |

\* สะกดผิด (`IMPRORT`)

**SCB เป็นธนาคารหลักของช่องทางรับชำระ** — 15.1 ล้านแถวรวมสองตาราง ไม่มีตาราง log ของธนาคารอื่น
`MT_BANK` มี 10 ธนาคาร (BBL, KBANK, KTB, SCB, BAY, GSB, TTB, UOB, BAAC, OTH) แต่ใช้สำหรับบันทึกบัญชีลูกค้า ไม่ใช่ช่องทางรับเงิน `[อนุมาน]`

`TRANSACTION_REPAY` มี 9.7M แถวแต่ **หยุดอัปเดตตั้งแต่ 2022-03-17** — เป็นตารางเก่าที่เลิกใช้แล้วหรือเปล่า ต้องยืนยัน

---

## Tax documents

| ตาราง | แถว |
|---|---:|
| `TAX_INVOICE` | 5,242,720 |
| `TTP_VAT_RPT` | 4,809,559 |
| `TTP_INV_BARCODE` | 4,477,750 |
| `TTP_CONTRACT_DUTY_RPT` | 576,386 |
| `CONTRACT_DUTY` | 288,609 |
| `LOG_ReGenTAX` | 722,708 |
| `PDF_FORM` | 2,553,530 |

`CONTRACT_DUTY` 288,609 ≈ จำนวนสัญญาพอดี = **อากรแสตมป์ 1 ชุดต่อ 1 สัญญา** `[อนุมาน]`

**`TTP_*` เป็นชั้น reporting/interface ทั้งหมด 42 ตาราง** — `_RPT` ลงท้าย = รายงาน · `TTP_VOUCHER_DETAIL` (14.5M) ใหญ่เป็นอันดับ 4 ของฐาน
ยังไม่รู้ว่า `TTP` ย่อมาจากอะไร

`PDF_FORM` 2.5M แถว — ถ้าเก็บ PDF เป็น binary ในฐาน นี่คือน้ำหนักที่ไม่ควรลาก mai ไป lake `[อนุมาน]`

---

## เชื่อมกับโน้ตอื่น

[[K2 Overview]] · [[K2 - Data Dictionary]] · [[K2 - Query Cookbook]] · [[K2 - Business Rules]] · [[K2 - Fee Policy]] · [[K2 - Contract & Account]] · [[K2 - Collection & OD]] · [[K2 - Master & Setup]]
