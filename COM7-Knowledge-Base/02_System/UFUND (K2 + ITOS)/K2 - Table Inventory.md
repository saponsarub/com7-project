# K2 — Table Inventory

**364 ตารางที่ใช้จริง** จากทั้งหมด 542 (ตัดขยะ 178 ตาราง) · survey 2026-08-26

> **คำอธิบายระดับ field ของตารางแกน 10 ตัว** → [[K2 - Data Dictionary]]
> ชั้นความสำคัญ: ★★★ core 10 · ★★ สำคัญ 40 · ★ master 117 · ⛔ ระวัง 5 · ชั้นรอง 192
ไฟล์เต็มพร้อมทุกคอลัมน์: `_raw/tables.csv` · `_raw/columns.csv` · `_raw/indexes.csv`

**คอลัมน์ "แก้ล่าสุด"** มาจาก `sys.tables.modify_date` = วันที่ **โครงสร้าง** ถูกแก้ ไม่ใช่วันที่ข้อมูลเข้าล่าสุด
> อ่าน usage stats ไม่ได้เพราะ user ไม่มีสิทธิ์ `VIEW SERVER STATE` — จึง **บอกไม่ได้ว่าตารางไหน application อ่านจริง** ต่างจากที่ทำกับ ITOS ได้

---

## 1 · Customer — 20 tables

| ตาราง                        |         แถว | คอลัมน์ | แก้ล่าสุด  |
| ---------------------------- | ----------: | ------: | ---------- |
| `CONTACT_DEBT_COLLECTION`    |   3,458,409 |      14 | 2025-07-02 |
| `ADDRESS_PROSPECT_CUSTOMER`  |     987,518 |      80 | 2025-05-13 |
| `PROSPECT_CUSTOMER`          |     800,282 |     132 | 2025-07-02 |
| `CONTACT`                    |     490,498 |       9 | 2022-03-17 |
| **`PERSON`**                 | **404,745** | **190** | 2025-07-02 |
| **`ADDRESS`**                | **403,282** | **101** | 2025-07-02 |
| `CHECKER`                    |     402,965 |      44 | 2025-05-12 |
| `CHECKER_GUARANTOR`          |     361,169 |      58 | 2024-05-07 |
| `RESERVER_REPAYMENT_TempNCB` |     298,374 |      16 | 2025-01-06 |
| `NCB_testFormat`             |     230,556 |      33 | 2023-06-19 |
| `PROSPECT_GUARANTOR`         |      16,804 |      39 | 2025-05-12 |
| `ADDRESS_GUARANTOR`          |      12,623 |      79 | 2024-11-06 |
| `ADDRESS_PROSPECT_GUARANTOR` |       5,250 |      79 | 2025-05-13 |
| `PERSON_Dept`                |       3,273 |     109 | 2022-03-17 |
| `ADDRESS_Dept`               |       3,273 |      81 | 2022-03-17 |
| `PERSON_PHONE_DUP`           |       1,175 |       5 | 2022-03-17 |
| `NationalCreditBureau`       |         136 |      66 | 2025-07-02 |
| `CIF_PERSON`                 |         134 |      48 | 2022-03-17 |
|                              |             |         |            |
	
**ผู้ค้ำมีชุดตารางของตัวเองครบ** — `GUARANTOR` (12,629) · `ADDRESS_GUARANTOR` (12,623) · `PROSPECT_GUARANTOR` (16,804) · `CHECKER_GUARANTOR` (361,169) · `GUARANTOR_ATTACHMENT` (23,843)
`CHECKER_GUARANTOR` 361,169 แถวมากกว่า `GUARANTOR` 12,629 มาก — น่าจะเป็นผลตรวจสอบทุกใบคำขอ ไม่ใช่ผู้ค้ำจริง `[อนุมาน]`
**`GUARANTOR` คือผู้ค้ำตัวจริง 12,629 คน แต่มี `CONTRACT_ID` แค่ 1,121 สัญญา** ที่เหลือผูกกับ `APP_ID` → [[K2 - Business Rules]] ข้อ 6

**`PERSON_PHONE_DUP` (1,175)** — ตารางที่ทีมสร้างไว้ตามเบอร์ซ้ำ หลักฐานว่า **มีคนในทีมรู้เรื่องข้อมูลซ้ำอยู่แล้ว** ควรถามว่าใครทำและใช้ทำอะไร

**`*_Dept` 3,273 แถวเท่ากันทุกตาราง** (`PERSON_Dept`, `ADDRESS_Dept`, `PRODUCT_Dept`, `CONTRACT_Dept`, `CUSTOMER_CARD_Dept`) = ชุดข้อมูลแยกของสินเชื่อพนักงาน `[อนุมาน]` หยุดอัปเดตตั้งแต่ 2022-03

รายละเอียด → [[K2 - Customer & Address]]

---

## 2 · Quotation / application — 12 tables

| ตาราง                            |         แถว | คอลัมน์ | แก้ล่าสุด      |
| -------------------------------- | ----------: | ------: | -------------- |
| `APPLICATION_SCORING_DETAIL`     |   3,108,379 |       8 | 2025-05-12     |
| `APPROVAL_HISTORY`               |   2,111,963 |       9 | **2026-05-08** |
| **`QUOTATION`**                  | **801,188** | **107** | 2025-10-16     |
| `APPLICATION_SCORING`            |     621,676 |       7 | 2025-05-12     |
| `APPROVAL_HISTORY_STATUS_DESC`   |     506,322 |      13 | 2025-05-20     |
| **`APPLICATION`**                | **410,306** |  **27** | **2026-04-23** |
| `PRODUCT`                        |     403,758 |      95 | 2025-10-16     |
| `PURCHASE_ORDER`                 |     290,213 |      18 | 2025-05-20     |
| `Outsource_Credit_Scoring`       |     141,488 |      31 | 2025-09-24     |
| `PRODUCT_Dept`                   |       3,273 |      62 | 2022-03-17     |
| **`ZZ_PRODUCT_K2_ITOS_mapping`** |     **593** |      12 | **2025-09-14** |
| `PURCHASE_ORDER_REGEN`           |          32 |      16 | 2022-02-08     |

> **`ZZ_PRODUCT_K2_ITOS_mapping` คือของจริงจากโปรเจกต์รวม K2 กับ ITOS** — มีคนทำ mapping สินค้าระหว่างสองระบบไว้แล้ว 593 แถว เมื่อ ก.ย. 2025
> **ต้องไปดูตารางนี้ก่อนเริ่ม mapping ใหม่** เชื่อมกับ [[K2 + ITOS Integration]]

รายละเอียด → [[K2 - Contract & Account]]

---

## 3 · Contract — 16 tables

| ตาราง | แถว | คอลัมน์ | แก้ล่าสุด |
|---|---:|---:|---|
| `PDF_FORM` | 2,553,530 | 14 | 2025-07-02 |
| `IMAGE_FILE` | 582,798 | 44 | 2025-07-02 |
| `CONTRACT_DUTY` | 288,609 | 16 | 2022-03-17 |
| **`CONTRACT`** | **288,205** | **30** | 2025-07-02 |
| `CONTRACT_HISTORY_STATUS` | 248,326 | 11 | 2022-04-28 |
| `TRANSACTION_CONTRACT_WRITE_OFF` | 26,946 | 8 | 2025-07-02 |
| `HISTORY_CALCULATE_CLOSE_CONTRACT` | 20,680 | 22 | 2022-03-17 |
| `PDF_NOTICE` | 17,903 | 8 | 2024-05-07 |
| `CONTRACT_WRITE_OFF` | 17,298 | 16 | 2025-07-02 |
| `CONTRACT_Dept` | 3,273 | 23 | 2022-03-17 |
| `LEGAL_INACTIVECONTRACT_BAC` | 488 | 33 | 2025-02-18 |
| `LEGAL_INACTIVECONTRACT` | 453 | 33 | 2025-07-02 |
| `CONTRACT_ATTACHED` | 295 | 24 | 2022-03-17 |
| `HPAP_CUST_CONTRACT` | 54 | 14 | 2022-03-17 |

`PDF_FORM` (2.5M) + `IMAGE_FILE` (582k) = **เอกสารสัญญาที่อาจเก็บ binary ในฐาน** — ต้องเช็คก่อนประเมินขนาด ingestion
`LEGAL_INACTIVECONTRACT` (453) = สัญญาที่เข้าสู่กระบวนการกฎหมาย

---

## 4 · Instalments / payments / accounting — 31 tables

| ตาราง | แถว | คอลัมน์ | แก้ล่าสุด |
|---|---:|---:|---|
| **`ACCOUNT`** | **25,977,656** | 16 | **2026-08-03** |
| `ACCOUNT_CHECK_GL` | 14,120,139 | 19 | 2023-07-20 |
| `TRANSACTION_REPAY` | 9,726,871 | 7 | 2022-03-17 |
| **`CUSTOMER_CARD`** | **5,816,540** | 26 | 2025-07-02 |
| `ACCOUNT_RECEIVABLE` | 5,711,805 | 11 | 2025-05-13 |
| `TAX_INVOICE` | 5,242,720 | 11 | 2022-03-17 |
| **`REPAYMENT`** | **5,205,080** | **47** | **2026-04-27** |
| `BANK_IMPRORT` | 4,411,373 | 17 | 2025-07-02 |
| **`INVOICE`** | **4,396,632** | 24 | 2025-07-02 |
| `ACCOUNT_GENERAL` | 2,896,269 | 10 | 2022-03-17 |
| `HCTI` | 2,214,389 | 22 | 2025-05-12 |
| `NCAP_PAYMENT` | 2,028,719 | 6 | 2025-02-05 |
| `INSTALLMENT_PLAN` | 1,850,935 | 15 | 2024-12-20 |
| `RESERVER_REPAYMENT` | 619,320 | 16 | 2025-07-02 |
| `RECORD_RECEIPT_PAYMENT` | 286,258 | 18 | 2025-05-12 |
| `PAYMENT` | 286,196 | 24 | 2025-05-12 |
| `ACCOUNT_LOG` | 81,512 | 11 | 2023-08-09 |
| `CUSTOMER_CARD_Dept` | 52,860 | 24 | 2022-03-17 |

**กลุ่มนี้คือน้ำหนักหลักของฐาน** — 4 ตาราง `ACCOUNT*` รวมกัน ≈ 48.7 ล้านแถว
`HCTI` (2.2M · สร้าง 2025-01) ยังไม่รู้ว่าย่อมาจากอะไร

รายละเอียด → [[K2 - Payment & Invoice]]

---

## 5 · Collections — 2 tables

| ตาราง | แถว | คอลัมน์ | แก้ล่าสุด |
|---|---:|---:|---|
| **`COLLECTION_OD`** | **15,653,423** | 33 | 2026-04-08 |
| `COLLECTION_OD_ASSIGNMENT` | 98,477 | 56 | **2026-07-20** |

(`CONTACT_DEBT_COLLECTION` 3.4M จัดอยู่กลุ่มลูกค้าเพราะมีข้อมูลติดต่อ)

รายละเอียด → [[K2 - Collection & OD]]

---

## 6 · Log — 48 tables

| ตาราง | แถว | คอลัมน์ | แก้ล่าสุด |
|---|---:|---:|---|
| **`CreditScrolling_Logs_Contract`** | **239,757,512** | 15 | 2025-07-02 |
| `LOG_SCB_BILLPAYMENT` | 8,046,041 | 17 | **2026-08-17** |
| `LOG_SCB_BILLPAYMENT_AUTO` | 7,091,407 | 8 | 2025-05-12 |
| `LOGGED_EMAIL_LISTS` | 2,418,448 | 15 | 2024-02-23 |
| `LOGS_SEND_INET` | 1,193,966 | 13 | 2026-02-03 |
| `LOG_ReGenTAX` | 722,708 | 5 | 2023-07-19 |
| `LOG_SEND_SMS` | 601,475 | 20 | 2025-07-02 |
| `LOG_REPAIR_EFFECTIVE` | 359,395 | 4 | 2024-03-25 |
| `LOG_PENALTY_COLLECT` | 246,980 | 14 | 2022-03-17 |
| `LOG_SendAPI` | 122,831 | 7 | 2025-07-02 |
| `LOG_SCB_DOWNPAYMENT` | 116,117 | 23 | 2025-05-12 |
| `LOGS_EMAIL_OTP` | 54,434 | 10 | 2025-11-05 |
| `LOG_EditCustomerInfo` | 35,759 | 12 | 2022-03-23 |

**`CreditScrolling_Logs_Contract` = 66% ของแถวทั้งฐาน** — ตารางเดียวใหญ่กว่าตารางอื่นทั้งหมดรวมกัน
`LOG_EditCustomerInfo` (35,759) = **audit trail การแก้ข้อมูลลูกค้า** มีประโยชน์ต่องาน data quality

---

## 7 · Reporting / interface — 53 tables

| ตาราง                                    |        แถว | คอลัมน์ | แก้ล่าสุด  |
| ---------------------------------------- | ---------: | ------: | ---------- |
| `TTP_VOUCHER_DETAIL`                     | 14,487,412 |      22 | 2025-08-06 |
| `TTP_OS_HPCUST_RPT`                      |  9,884,306 |      27 | 2025-05-12 |
| `Temp_History_OD`                        |  5,067,003 |      30 | 2025-07-02 |
| `TTP_VAT_RPT`                            |  4,809,559 |      18 | 2022-03-17 |
| `TTP_APPL_TRANS`                         |  4,576,468 |      40 | 2024-11-01 |
| `TTP_INV_BARCODE`                        |  4,477,750 |      13 | 2025-07-02 |
| `Report_Balance_defered_interest`        |  4,219,562 |      17 | 2025-05-20 |
| `Report_outstanding_accounts_receivable` |  4,213,196 |      17 | 2025-05-12 |
| `Report_Aging`                           |  4,014,076 |      31 | 2025-07-02 |
| `TTP_ACTIVITIES_LOG`                     |  1,125,401 |       9 | 2022-03-17 |
| `TTP_CONTRACT_DUTY_RPT`                  |    576,386 |      26 | 2025-05-12 |

**`Report_*` เป็นรายงานที่ materialize ไว้ในฐาน** ไม่ใช่ข้อมูลต้นทาง — `Report_Aging` (4M) คือ aging ลูกหนี้ที่คำนวณไว้แล้ว
ถ้าจะย้าย reporting ไป lake ตารางกลุ่มนี้คือสิ่งที่ควรเลิกใช้ ไม่ใช่สิ่งที่ควร ingest `[อนุมาน]`

---

## 8 · Master / setup — 133 tables

ตารางใหญ่สุดในกลุ่ม: `MT_FACULTY` (39,475) · `MT_PACKAGE_SIM` (13,018) · `SETUP_CREDIT_LIMIT_DETAIL` (12,995) · `MT_POST_CODE` (7,537) · `MT_SUB_DISTRICT` (7,436)

ค่าจริงของ master ที่ใช้บ่อย → [[K2 - Master & Setup]]

---

## 9 · Other — 49 tables

| ตาราง | แถว | หมายเหตุ |
|---|---:|---|
| `UFUNDInterface` | 2,029,152 | คิว API ส่งออก (`Payload`, `URL`, `Status`) |
| `NCAP_STATUS` | 1,048,575 | |
| `NCAP_INFORMATION` | 132,630 | มี `FULL_NAME`, `TAX_ID`, `ADDRESS_*`, `INCOME` |
| `20241218_MIS_FD_CustCard` | 98,289 | **ตาราง ad-hoc ตั้งชื่อด้วยวันที่** |
| **`STATEMENT_FILE_PASSWORD`** | **79,067** | **รหัสผ่านไฟล์ statement ธนาคาร** |
| `MDM_HISTORY_APPLE` | 29,429 | อัปเดต **2026-07-22** |
| `GUARANTOR_ATTACHMENT` | 23,843 | |
| `BLACKLIST` | 18,383 | |
| `INSURANCE_DATA` | 16,828 | |
| `GUARANTOR` | 12,629 | |
| `ASSETS_INFORMATION` | 4,210 | ทะเบียนเครื่อง |
| `122020` | 1,960 | **ตารางชื่อเป็นตัวเลขล้วน** |

> **`STATEMENT_FILE_PASSWORD` 79,067 แถว** — รหัสผ่านของไฟล์ statement ธนาคารลูกค้าเก็บอยู่ในฐาน
> **ห้าม ingest ตารางนี้เข้า lake ในทุกกรณี** และควรแจ้ง security ว่ามีอยู่ `[อนุมาน]`

`MDM_HISTORY_APPLE` — MDM = Mobile Device Management ล็อกเครื่องระยะไกลเมื่อลูกค้าไม่จ่าย `[อนุมาน]` เป็นกลไกบังคับหลักประกันที่ไม่มีใน ITOS

**ตาราง ad-hoc ใน production** — `20241218_MIS_FD_CustCard`, `122020`, `MT_DownPercent_AKETEST`, `CUSTOMER_CARD_TEST`, `AR_CUSTOMERCARD_DEMO`
เป็นสัญญาณว่ามีการทำงานด้วยมือบนฐาน production `[อนุมาน]` — **กฎคัดตารางขยะจึงจำเป็น อย่าเลือกตารางจากชื่ออย่างเดียว**

---

## Views — 165 of them

| prefix | จำนวน |
|---|---:|
| `EGG_` | **65** |
| `View_` / `VIEW_` | 52 |
| `VW_` / `vw_` | 42 |
| อื่น | 6 |

**อ่าน SQL ของ view ไม่ได้** เพราะ user ไม่มีสิทธิ์ `VIEW_DEFINITION` — `sys.sql_modules.definition` คืน NULL
เห็นได้แค่ชื่อกับคอลัมน์ (อยู่ใน `_raw/views.csv`)

View ที่น่าสนใจ: `View_GetPersonDetails` · `View_ADDRESS` · `View_PERSON` · `View_outstanding_CUSTOMER` (มี 7 variant) · `VW_GUARANTOR_ADDR_READ` · `EGG_MDM` · `EGG_BANK_STATEMENT`

> **ขอสิทธิ์ `VIEW DEFINITION` เพิ่มจะได้ join logic ที่ทีม K2 ใช้จริง** — คุ้มกว่าการเดา relation เอง เพราะฐานนี้ไม่มี FK

---

## เชื่อมกับโน้ตอื่น

[[K2 Overview]] · [[K2 - Query Cookbook]] · [[K2 - Business Rules]] · [[K2 - Customer & Address]] · [[K2 - Contract & Account]] · [[K2 - Payment & Invoice]] · [[K2 - Collection & OD]] · [[K2 - Master & Setup]]
