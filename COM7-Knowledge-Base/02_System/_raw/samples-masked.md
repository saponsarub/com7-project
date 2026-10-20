# ตัวอย่างข้อมูล K2 (HPCOM7) — mask แล้ว

สร้างโดย `scripts\k2\k2_samples.py` · ทุกค่าที่เป็น PII ถูกปิดบังก่อนเขียนไฟล์
ชื่อ → `ก***` · เลขบัตร → `1-XXXX-XXXXX-XX-X` · เบอร์ → `XXX-XXX-1234` 
ที่อยู่บรรทัด (บ้านเลขที่/หมู่/ซอย/ถนน) → `***` · ไฟล์แนบ/พิกัด → ตัดออก
**เงิน · วันที่ · รหัสสถานะ · id → เก็บค่าจริง** เพราะจำเป็นต่อการเข้าใจ business

---

## PERSON

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 190

| PERSON_ID | APP_ID | PRODUCT_ID | CIF_PERSON_ID | JURISTIC_ID | FLAG_GUARANTOR | PREFIX | PREFIX_OTHER | FIRST_NAME | LAST_NAME | CARD_CODE | TAX_ID | STUDENT_ID | BIRTHDAY | AGE | CUSTOMER_TYPE | SEX | IDCARD_REGIS_DATE | IDCARD_EXPIRE_DATE | IDCARD_REGIS_BY | NATIONALITY_CODE | CITIZEN_CODE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 100000 | 1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 2 | 100001 | 2 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 3 | 100002 | 3 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 4 | 100003 | 4 | 1 | NULL | NULL | 1 | NULL | ช*** | ช*** | 1 | 1-XXXX-XXXXX-XX-X | 6001781 | 1998-07-31 | 22 | 1 | 1 | NULL | NULL | NULL | 1 | NULL |
| 5 | 100004 | 5 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |

## ADDRESS

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 101

| ADDRESS_ID | PERSON_ID | CIF_PERSON_ID | JURISTIC_ID | QUOTATION_ID | A1_MASTER | A1_COPY | A1_NO | A1_MOI | A1_VILLAGE | A1_BUILDING | A1_FLOOR | A1_ROOM_NO | A1_SOI | A1_ROAD | A1_PROVINCE | A1_DISTRICT | A1_SUBDISTRICT | A1_POSTALCODE | A1_OWNER_TYPE | A1_LIVEING_TIME | A1_PHONE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 2 | 2 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 3 | 3 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 4 | 4 | 1 | NULL | NULL | 1 | 1 | *** | *** | *** | *** | - | *** | *** | *** | 57 | 5716 | 570206 | 57210 | 3 | 18 | XXXX |
| 5 | 5 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |

## PROSPECT_CUSTOMER

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 132

| PST_CUST_ID | QUOTATION_ID | PREFIX | PREFIX_OTHER | FIRST_NAME | LAST_NAME | TAX_ID | STUDENT_ID | BIRTHDAY | AGE | SEX | MARITAL_STATUS | PHONE | FACEBOOK | LINEID | EMAIL | OCCUPATION_CODE | MAIN_INCOME | UNIVERSITY_NAME | UNIVERSITY_OTHER | CAMPUS_NAME | FACULTY_NAME |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 1 | NULL |
| 2 | 2 | 3 | NULL | อ*** | พ*** | NULL | NULL | 1999-01-22 | 21 | 2 | NULL | XXX-XXX-7924 | j*** | b*** | b***@hotmail.com | NULL | NULL | 4 | NULL | 1 | 93 |
| 3 | 3 | 3 | NULL | อ*** | พ*** | NULL | NULL | 1999-01-22 | 21 | 2 | NULL | XXX-XXX-7924 | A*** | b*** | b***@hotmail.com | NULL | NULL | 4 | NULL | 1 | 93 |
| 4 | 4 | 3 | NULL | จ*** | ห*** | NULL | NULL | 1996-09-01 | 24 | 2 | NULL | XXX-XXX-5858 | J*** | S*** | N***@gmail.com | NULL | NULL | 4 | NULL | 1 | 95 |
| 5 | 5 | 3 | NULL | ป*** | เ*** | NULL | NULL | 1998-09-15 | 22 | 2 | NULL | XXX-XXX-0774 | P*** | 0*** | p***@gmail.com | NULL | NULL | 4 | NULL | 1 | 87 |

## ADDRESS_PROSPECT_CUSTOMER

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 80

| ADD_CUST_ID | QUOTATION_ID | PST_CUST_ID | A1_MASTER | A1_COPY | A1_NO | A1_MOI | A1_VILLAGE | A1_BUILDING | A1_FLOOR | A1_ROOM_NO | A1_SOI | A1_ROAD | A1_PROVINCE | A1_DISTRICT | A1_SUBDISTRICT | A1_POSTALCODE | A1_OWNER_TYPE | A1_LIVEING_TIME | A1_PHONE | A1_LATITUDE | A1_LONGITUDE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 99 | 99 | 1 | 1 | *** | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 18 | 1807 | 180701 | 17120 | 9 | 50 | NULL | NULL | NULL |
| 2 | 100 | 100 | 1 | 1 | *** | *** | NULL | NULL | NULL | NULL | *** | *** | 39 | 3901 | 390110 | 39000 | 3 | 18 | NULL | NULL | NULL |
| 3 | 101 | 101 | 1 | 1 | *** | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 40 | 4001 | 400101 | 40000 | 3 | NULL | NULL | NULL | NULL |
| 4 | 103 | 103 | 1 | 1 | *** | *** | NULL | NULL | NULL | NULL | NULL | *** | 37 | 3701 | 370101 | 37000 | 3 | NULL | NULL | NULL | NULL |
| 5 | 102 | 102 | 1 | 1 | *** | *** | *** | NULL | NULL | NULL | NULL | NULL | 63 | 6308 | 630806 | 63170 | 3 | NULL | NULL | NULL | NULL |

## QUOTATION

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 107

| QUOTATION_ID | QT_DATE | DATE_END | STATUS_ID | APPROVE_CODE | BRANCH_TYPE | BRANCH_ID | BRANCH_AD | TAX_ID | CUSTOMER_NAME | OCCUPATION_ID | UNIVERSITY_ID | CAMPUS_ID | FACULTY_ID | FLAG_GUARANTOR | PRODUCT_TYPE | PRODUCT_CATEGORY | PRODUCT_BAND | PRODUCT_SERIES | PRODUCT_SUB_SERIES | PRODUCT_COLOR | REMARK |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 2020-07-03 | 2020-08-25 | 28 | NULL | NULL | NULL | NULL | NULL | น*** อ*** | NULL | 4 | 1 | 93 | NULL | 2 | 2 | 1 | 10 | NULL | NULL | NULL |
| 3 | 2020-07-03 | 2021-07-29 | 28 | NULL | 3 | 509 | COMSEVEN2019\10633 | 1-XXXX-XXXXX-XX-X | ภ*** ป*** | 2 | 0 | 1 | 0 | NULL | 2 | 3 | 9 | 54 | 78 | 112 | NULL |
| 4 | 2020-07-03 | 2020-08-25 | 28 | NULL | NULL | NULL | NULL | NULL | น*** จ*** | NULL | 4 | 1 | 95 | NULL | 2 | 2 | 1 | 12 | 12 | 20 | NULL |
| 5 | 2020-07-04 | 2020-08-25 | 28 | NULL | NULL | NULL | NULL | NULL | น*** ป*** | NULL | 4 | 1 | 87 | NULL | 2 | 2 | 1 | 10 | 7 | 10 | NULL |
| 6 | 2020-07-06 | 2020-08-25 | 28 | NULL | NULL | NULL | NULL | NULL | น*** ธ*** | NULL | 8 | 1 | 193 | NULL | 2 | 2 | 1 | 10 | 7 | 13 | NULL |

## APPLICATION

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 27

| APP_ID | STATUS_ID | APPLICATION_NUMBER | APP_DATE | CUSTOMER_NAME | CIF_PERSON_ID | PERSON_ID | JURISTIC_ID | PARTNER_ID | P_BRANCH_TYPE | P_BRANCH_ID | PRODUCT_ID | CHECKER_ID | CHECKER_RESULT | APPROVE_ID | SCORING | EMP_ID | EMP_ID_Global | EMP_ComCode | QUOTATION_ID | CREATE_DATE | UPDATE_DATE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100000 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 2020-07-03 10:52:42 | NULL |
| 100001 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 2020-07-03 11:49:07 | NULL |
| 100002 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 2020-07-03 13:35:28 | NULL |
| 100003 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 2020-07-03 14:35:37 | NULL |
| 100004 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | 2020-07-03 14:58:06 | NULL |

## PRODUCT

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 95

| PRODUCT_ID | APP_ID | QUOTATION_ID | PRODUCT_CODE | PRODUCT_TYPE | PRODUCT_CATEGORY | PRODUCT_BAND | PRODUCT_SERIES | PRODUCT_SUB_SERIES | PRODUCT_COLOR | PROD_PRICE | PROD_VAT | PROD_SUM_PRICE | DOWN_PERCENT | DOWN_AMT | DOWN_VAT | DOWN_SUM_AMT | HP_AMT | HP_INVEST_AMT | INTEREST_FLAT | INTEREST_EFFECTIVE | INSTALL_NUM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 100000 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 2 | 100001 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 3 | 100002 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 4 | 100003 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 5 | 100004 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |

## CONTRACT

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 30

| CONTRACT_ID | STATUS_ID | STATUS_HP | APP_ID | PERSON_ID | PARTNER_ID | P_BRANCH_ID | EMP_ID | CIF_PERSON_ID | PRODUDCT_ID | REPAY_ID | APPLICATION_NUMBER | CONTRACT_NUMBER | CUSTOMER_NAME | MAKE_DATE | CONTRACT_START | CONTRACT_END | PERIOD_DATE | INSTALL_NUM_FINAL | OVERDUE | ASSIGN_DATE | COLLECTION_NAME |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 40 | NULL | 100059 | 60 | NULL | 19 | 10041 | 22 | 60 | NULL | 7062020100060 | 2000001 | น*** ท*** | 2020-07-15 | 2020-07-15 | 2021-07-10 | 2020-07-22 | 12 | 0 | NULL | NULL |
| 2 | 40 | NULL | 100095 | 96 | NULL | 15 | 0 | 46 | 96 | NULL | 2602020100096 | 2000002 | น*** อ*** | 2020-07-17 | 2020-07-17 | 2022-01-08 | 2020-07-24 | 18 | 0 | NULL | NULL |
| 3 | 53 | NULL | 100091 | 92 | NULL | 15 | 0 | 42 | 92 | NULL | 2602020100092 | 2000003 | น*** ก*** | 2020-07-17 | 2020-07-17 | 2022-01-08 | 2020-07-24 | 18 | 0 | NULL | NULL |
| 4 | 40 | NULL | 100037 | 38 | NULL | 15 | 0 | 12 | 38 | NULL | 2602020100038 | 2000004 | น*** ธ*** | 2020-07-17 | 2020-07-17 | 2021-07-12 | 2020-07-24 | 12 | 0 | NULL | NULL |
| 5 | 40 | NULL | 100014 | 15 | NULL | 22 | 0 | 7 | 15 | NULL | 7092020100015 | 2000005 | น*** ป*** | 2020-07-18 | 2020-07-18 | 2021-07-13 | 2020-07-25 | 12 | 0 | NULL | NULL |

## CHECKER

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 44

| CHECKER_ID | APP_ID | CHECKER_TYPE | CHECKER_RESULT | CHARACTER_HOME | SIZE_AREA | DESCRIPTION | IMAGE_HOME1 | IMAGE_HOME2 | IMAGE_HOME3 | REMARK01 | CHECK01 | REMARK02 | CHECK02 | REMARK03 | CHECK03 | REMARK04 | CHECK04 | REMARK05 | CHECK05 | REMARK06 | CHECK06 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 100000 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 2 | 100008 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 3 | 100008 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 4 | 100009 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NOT PASS | NULL | NOT PASS | NULL | NOT PASS | NULL | NOT PASS | NULL | NOT PASS | NULL | NOT PASS |
| 5 | 100008 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |

## CHECKER_GUARANTOR

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 58

| CHECKER_ID | APP_ID | GUAR_ID | CHECKER_TYPE | CHECKER_RESULT | CHARACTER_HOME | SIZE_AREA | DESCRIPTION | IMAGE_HOME1 | IMAGE_HOME2 | IMAGE_HOME3 | CHECK01 | REMARK01 | CHECK02 | REMARK02 | CHECK03 | REMARK03 | CHECK04 | REMARK04 | CHECK05 | REMARK05 | CHECK06 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 141103 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 2 | 141145 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 3 | 141140 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 4 | 141092 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 5 | 141141 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |

## CUSTOMER_CARD

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 26

| ID | CONTRACT_ID | CONTRACT_NUMBER | APPLICATION_NUMBER | INSTALL_NUM | DUEDATE | INSTALL_AMT | PAY_PRINCIPLE | PAY_INTEREST | PAY_INSTALL_VAT | OUTSTD_SUM_PRINCIPLE | OUTSTD_SUM_INTEREST | DISCOUNT_AMT | INVOICE_NUMBER | RECEIPT_NUMBER | SUM_OUTSTAND | INSTALL_OD_01 | INSTALL_OD_02 | INSTALL_OD_SUM | SUM_OD_AMT | PENALTY_AMT | COLLECT_AMT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 2000001 | 100059 | 1 | 2020-08-01 | 1090.144 | 677.38 | 341.44 | 71.31783177570094 | 9191.78 | 2015.24 | 1007.62 | 20100001 | 20100016 | NULL | 1 | 2 | 2 | 0.0 | NULL | NULL |
| 3 | 1 | 2000001 | 100059 | 2 | 2020-09-01 | 1090.144 | 700.82 | 318.0 | 71.31783177570094 | 8490.96 | 1697.24 | 848.62 | 20100026 | 20100100 | NULL | 1 | 2 | 2 | 0.0 | NULL | NULL |
| 4 | 1 | 2000001 | 100059 | 3 | 2020-10-01 | 1090.144 | 725.06 | 293.76 | 71.31783177570094 | 7765.9 | 1403.48 | 701.74 | 20100197 | 201000298 | 9169.38 | 1 | 2 | 2 | 0.0 | NULL | NULL |
| 5 | 1 | 2000001 | 100059 | 4 | 2020-11-01 | 1090.144 | 750.15 | 268.67 | 71.31783177570094 | 7015.75 | 1134.81 | 567.4 | 20100583 | 201000936 | NULL | 1 | 2 | 2 | 0.0 | NULL | NULL |
| 6 | 1 | 2000001 | 100059 | 5 | 2020-12-01 | 1090.144 | 776.1 | 242.72 | 71.31783177570094 | 6239.65 | 892.09 | 446.04 | 20101278 | 201001997 | 8150.56 | 1 | 2 | 2 | 0.0 | 100.0 | NULL |

## INVOICE

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 24

| INVOICE_ID | STATUS_ID | INVOICE_NUMBER | INVOICEE_TYPE | CONTRACT_ID | CUSTOMER_CARD_ID | INVOICE_DATE | DUE_DATE | AMT_OLD | INSTALL_NUM_OLD | INSTALL_OUTSTAND | SUM_OUTSTAND | INSTALL_CURRENT | AMOUNT | WHT_AMT | VAT_AMT | INSTALL_OD_01 | INSTALL_OD_02 | INSTALL_OD_SUM | SUM_OD_AMT | PENALTY_AMT | COLLECT_AMT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100000 | NULL | 20100001 | 1 | 1 | 2 | 2020-07-22 | 2020-08-01 | NULL | NULL | NULL | NULL | 1 | 1018.8261682243 | NULL | 71.3178317757009 | NULL | NULL | NULL | NULL | NULL | NULL |
| 100001 | NULL | 20100002 | 1 | 2 | 14 | 2020-08-05 | 2020-08-16 | NULL | NULL | NULL | NULL | 1 | 744.682866043614 | NULL | 52.127800623053 | NULL | NULL | NULL | NULL | NULL | NULL |
| 100002 | NULL | 20100003 | 1 | 3 | 32 | 2020-08-05 | 2020-08-16 | NULL | NULL | NULL | NULL | 1 | 744.682866043614 | NULL | 52.127800623053 | NULL | NULL | NULL | NULL | NULL | NULL |
| 100003 | NULL | 20100004 | 1 | 4 | 50 | 2020-08-05 | 2020-08-16 | NULL | NULL | NULL | NULL | 1 | 960.938317757009 | NULL | 67.2656822429906 | NULL | NULL | NULL | NULL | NULL | NULL |
| 100004 | NULL | 20100005 | 1 | 5 | 62 | 2020-08-05 | 2020-08-16 | NULL | NULL | NULL | NULL | 1 | 1201.17289719626 | NULL | 84.0821028037383 | NULL | NULL | NULL | NULL | NULL | NULL |

## REPAYMENT

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 47

| REPAY_ID | CONTRACT_ID | CUSTOMER_CARD_ID | APP_ID | INVOICE_ID | STATUS_ID | APPLICATION_NUMBER | CONTRACT_NUMBER | CUSTOMER_NAME | REPAY_TYPE | RECEIPT_NUMBER | TAX_NUMBER | PHY_NUMBER | CREDIT_NOTE_NUMBER | PAY_TYPE | MAKE_DATE | REPAY_DATE | REPAY_NAME | REPAY_PENALTY | REPAY_COLLECT | REPAY_AMOUNT | REPAY_WHT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100000 | NULL | NULL | 100046 | NULL | NULL | 2602020100047 | NULL | น*** ก*** | 1 | 22100001 | 22847998 | 722-481 | NULL | 1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 100001 | NULL | NULL | 100048 | NULL | NULL | 2602020100049 | NULL | น*** น*** | 1 | 22100002 | 22848019 | 46563-260 | NULL | 1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 100002 | NULL | NULL | 100037 | NULL | NULL | 2602020100038 | NULL | น*** ธ*** | 1 | 22100003 | 22848025 | 46572-260 | NULL | 1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 100003 | NULL | NULL | 100059 | NULL | NULL | 7062020100060 | NULL | น*** ท*** | 1 | 22100004 | 22848030 | 10106-706 | NULL | 1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 100004 | NULL | NULL | 100091 | NULL | NULL | 2602020100092 | NULL | น*** ก*** | 1 | 22100005 | 22848044 | 46754-260 | NULL | 1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL |

## PAYMENT

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 24

| PAYMENT_ID | STATUS_ID | APP_ID | PV_ID | INV_PN_NUMBER | PO_NUMBER | PV_NUMBER | MAKE_DATE | PAY_DATE | SUBSIDY_PAY | REBATE | DEDUCT_DOWN_AMT | DEDUCT_FEE_HP | DEDUCT_SUBSIDY_RECEIPT | AMOUNT | WHT_AMOUNT | VAT_AMOUNT | SUM_AMOUNT | RECEIPT_NAME | PAY_TYPE | BANK | BANK_BRANCH |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 38 | 100046 | NULL | 01NS6307-11577 | 20100001 | NULL | NULL | NULL | 0.0 | 0.0 | NULL | 0.0 | 0.0 | 12336.45 | 660.0 | 863.55 | 13200.0 | บ*** ค*** | 3.0 | กสิกรไทย | ราชดำริ |
| 2 | 38 | 100048 | NULL | 6307-BR317-00312 | 20100002 | NULL | NULL | NULL | 0.0 | 0.0 | 2040.0 | 0.0 | 0.0 | 8160.0 | 408.0 | 571.2 | 8731.2 | บ*** ค*** | 2.0 | กสิกรไทย | ราชดำริ |
| 3 | 38 | 100037 | NULL | 6307-BR317-00317 | 20100003 | NULL | NULL | NULL | 0.0 | 0.0 | 14940.0 | 0.0 | 0.0 | 9960.0 | 498.0 | 697.2 | 10657.2 | บ*** ค*** | 2.0 | กสิกรไทย | ราชดำริ |
| 4 | 38 | 100059 | NULL | 6307-BR490-00072 | 20100004 | NULL | NULL | NULL | 0.0 | 0.0 | 2640.0 | 0.0 | 0.0 | 10560.0 | 528.0 | 739.2 | 11299.2 | บ*** ค*** | 2.0 | กสิกรไทย | ราชดำริ |
| 5 | 38 | 100091 | NULL | 6307-BR317-00481 | 20100005 | NULL | NULL | NULL | 0.0 | 0.0 | 2640.0 | 0.0 | 0.0 | 10560.0 | 528.0 | 739.2 | 11299.2 | บ*** ค*** | 2.0 | กสิกรไทย | ราชดำริ |

## TAX_INVOICE

5 แถวตัวอย่าง · 11 คอลัมน์

| TAX_INVOICE_ID | REPAY_ID | CONTRACT_ID | CUSTOMER_CARD_ID | STATUS_ID | TAX_NUMBER | TAX_SUM_AMT | DES_SUM_AMT | CREATE_DATE | UPDATE_DATE | NAME_MAKE |
|---|---|---|---|---|---|---|---|---|---|---|
| 100000 | NULL | NULL | NULL | NULL | 20100001 | NULL | NULL | NULL | NULL | NULL |
| 100001 | NULL | NULL | NULL | NULL | 20100002 | NULL | NULL | NULL | NULL | NULL |
| 100002 | NULL | NULL | NULL | NULL | 20100003 | NULL | NULL | NULL | NULL | NULL |
| 100003 | NULL | NULL | NULL | NULL | 20100004 | NULL | NULL | NULL | NULL | NULL |
| 100004 | NULL | NULL | NULL | NULL | 20100005 | NULL | NULL | NULL | NULL | NULL |

## ACCOUNT

5 แถวตัวอย่าง · 16 คอลัมน์

| ACCOUNT_ID | CONTRACT_ID | CONTRACT_NUMBER | APP_ID | APP_NUMBER | REPAY_ID | PAY_ID | VOURCHER_NO | DATE | DATE_POST | APAR_CODE | ACCOUNT_CODE | ACCOUNT_CATEGORY | ACCOUNT_DESCIPTION | RECORD_TYPE | AMOUNT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | NULL | NULL | 100046 | 2602020100047 | 100000 | NULL | *** | 2020-07-08 | 2020-07-08 | NULL | 1112001 | 1 | <ข้อความอิสระ ตัดออก 13 ตัวอักษร> | Dr. | 2640.0 |
| 2 | NULL | NULL | 100046 | 2602020100047 | 100000 | NULL | *** | 2020-07-08 | 2020-07-08 | NULL | 2111105 | 2 | <ข้อความอิสระ ตัดออก 35 ตัวอักษร> | Cr. | 2467.29 |
| 3 | NULL | NULL | 100046 | 2602020100047 | 100000 | NULL | *** | 2020-07-08 | 2020-07-08 | NULL | 2191001 | 2 | <ข้อความอิสระ ตัดออก 17 ตัวอักษร> | Cr. | 172.71 |
| 4 | NULL | NULL | 100048 | 2602020100049 | 100001 | NULL | *** | 2020-07-09 | 2020-07-09 | NULL | 1112001 | 1 | <ข้อความอิสระ ตัดออก 13 ตัวอักษร> | Dr. | 2040.0 |
| 5 | NULL | NULL | 100048 | 2602020100049 | 100001 | NULL | *** | 2020-07-09 | 2020-07-09 | NULL | 2111105 | 2 | <ข้อความอิสระ ตัดออก 35 ตัวอักษร> | Cr. | 1906.54 |

## ACCOUNT_RECEIVABLE

5 แถวตัวอย่าง · 11 คอลัมน์

| RECEIVABLE_ID | REPAY_ID | R_VOURCHER_NO | R_DATE | R_DATE_POST | R_APAR_CODE | R_ACCOUNT_CODE | R_ACCOUNT_CATEGORY | R_ACCOUNT_DESCIPTION | R_RECORD_TYPE | R_AMOUNT |
|---|---|---|---|---|---|---|---|---|---|---|
| 1000000 | 100000 | *** | 2020-07-08 | 2020-07-08 | NULL | NULL | NULL | NULL | NULL | NULL |
| 1000001 | 100001 | *** | 2020-07-09 | 2020-07-09 | NULL | NULL | NULL | NULL | NULL | NULL |
| 1000002 | 100002 | *** | 2020-07-10 | 2020-07-10 | NULL | NULL | NULL | NULL | NULL | NULL |
| 1000003 | 100003 | *** | 2020-07-13 | 2020-07-13 | NULL | NULL | NULL | NULL | NULL | NULL |
| 1000004 | NULL | *** | 2020-07-15 | 2020-07-15 | NULL | NULL | NULL | NULL | NULL | NULL |

## TRANSACTION_REPAY

5 แถวตัวอย่าง · 7 คอลัมน์

| TRANSACTION_ID | REPAY_ID | INSTALL_NUM | DESCRIPTION | AMOUNT | LOG_DATE | NAME_MAKE |
|---|---|---|---|---|---|---|
| 1 | 100000 | NULL | <ข้อความอิสระ ตัดออก 9 ตัวอักษร> | 2467.28971962617 | NULL | NULL |
| 2 | 100000 | NULL | <ข้อความอิสระ ตัดออก 13 ตัวอักษร> | 172.710280373832 | NULL | NULL |
| 3 | 100001 | NULL | <ข้อความอิสระ ตัดออก 9 ตัวอักษร> | 1906.54205607477 | NULL | NULL |
| 4 | 100001 | NULL | <ข้อความอิสระ ตัดออก 13 ตัวอักษร> | 133.457943925234 | NULL | NULL |
| 5 | 100002 | NULL | <ข้อความอิสระ ตัดออก 9 ตัวอักษร> | 13962.6168224299 | NULL | NULL |

## COLLECTION_OD

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 33

| EXTRACT_DATE | CONTRACT_ID | CONTRACT_NUMBER | CONTRACT_STATUS | CONTRACT_STATUS_DESC | PRODUDCT_ID | UPDATE_DATE | PRODUCT_TYPE | TOTAL_OUTSTANDING | TOTAL_PRINCIPLE | TOTAL_INTEREST | TOTAL_VAT | NUMBER_OF_PERIOD | INSTALLMENT_PER_PERIOD | PAID_TOTAL_OUTSTANDING | PAID_TOTAL_PRINCIPLE | PAID_TOTAL_INTEREST | PAID_TOTAL_VAT | PAID_NUMBER_OF_PERIOD | PERIOD_DUE_DATE | LAST_REPAY_DATE | REMAINING_OUTSTANDING |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-04-19 | 138557 | 24138557 | 43 | Overdue 1 | 192320 | 2025-09-17 23:30:02.203000 | Personal | 42573.35999999999 | 32149.53 | 7638.730000000001 | 2785.2000000000007 | 24 | 1773.89 | 31930.019999999993 | 22794.039999999997 | 7047.080000000001 | 2088.8999999999996 | 18 | 2026-04-16 | 2026-03-23 | 10643.34 |
| 2026-04-19 | 138973 | 24138973 | 43 | Overdue 1 | 192774 | 2025-09-24 23:30:01.993000 | Student | 51769.92000000003 | 29146.35 | 19236.59 | 3386.8799999999983 | 24 | 2157.08 | 38827.44000000002 | 18757.13 | 17530.149999999998 | 2540.159999999999 | 18 | 2026-04-16 | 2026-03-25 | 12942.48000000001 |
| 2026-04-19 | 139259 | 24139259 | 43 | Overdue 1 | 193097 | 2025-12-17 23:30:03.323000 | Student | 39070.8 | 21996.829999999998 | 14517.909999999998 | 2556.0 | 24 | 1627.95 | 29303.10000000001 | 14156.089999999998 | 13230.009999999998 | 1917.0 | 18 | 2026-04-16 | 2026-04-12 | 9767.699999999993 |
| 2026-04-19 | 139291 | 24139291 | 43 | Overdue 1 | 193145 | 2025-09-18 23:30:01.717000 | Personal | 42573.35999999999 | 32149.53 | 7638.730000000001 | 2785.2000000000007 | 24 | 1773.89 | 31930.019999999993 | 22794.039999999997 | 7047.080000000001 | 2088.8999999999996 | 18 | 2026-04-16 | 2026-03-03 | 10643.34 |
| 2026-04-19 | 139411 | 24139411 | 43 | Overdue 1 | 193256 | 2025-09-23 23:30:02.367000 | Personal | 34529.039999999986 | 26074.77 | 6195.370000000002 | 2258.8799999999987 | 24 | 1438.71 | 25896.77999999999 | 18487.120000000003 | 5715.500000000002 | 1694.1599999999994 | 18 | 2026-04-16 | 2026-03-26 | 8632.259999999995 |

## COLLECTION_OD_ASSIGNMENT

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 56

| EXTRACT_DATE | CONTRACT_ID | CONTRACT_NUMBER | CONTRACT_STATUS | CONTRACT_STATUS_DESC | PRODUDCT_ID | UPDATE_DATE | PRODUCT_TYPE | TOTAL_OUTSTANDING | TOTAL_PRINCIPLE | TOTAL_INTEREST | TOTAL_VAT | NUMBER_OF_PERIOD | INSTALLMENT_PER_PERIOD | PAID_TOTAL_OUTSTANDING | PAID_TOTAL_PRINCIPLE | PAID_TOTAL_INTEREST | PAID_TOTAL_VAT | PAID_NUMBER_OF_PERIOD | PERIOD_DUE_DATE | LAST_REPAY_DATE | REMAINING_OUTSTANDING |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-06-05 | 284181 | 26284181 | 43 | Overdue 1 | 391877 | 2026-05-12 14:16:19 | Student | 31415.670000000006 | 23535.420000000002 | 5825.0199999999995 | 2055.2400000000007 | 9 | 3490.63 | NULL | NULL | NULL | NULL | NULL | 2026-06-01 | NULL | NULL |
| 2026-06-05 | 283616 | 26283616 | 43 | Overdue 1 | 391129 | 2026-05-02 15:09:22 | Student | 65870.64 | 37085.13999999999 | 24476.18999999999 | 4309.200000000002 | 24 | 2744.61 | NULL | NULL | NULL | NULL | NULL | 2026-06-01 | NULL | NULL |
| 2026-06-05 | 283730 | 26283730 | 43 | Overdue 1 | 391221 | 2026-05-04 16:39:57 | Student | 44334.359999999986 | 27715.09 | 13718.97 | 2900.340000000001 | 18 | 2463.02 | NULL | NULL | NULL | NULL | NULL | 2026-06-01 | NULL | NULL |
| 2026-06-05 | 283582 | 26283582 | 43 | Overdue 1 | 391057 | 2026-05-01 20:57:07 | Student | 39442.68000000002 | 24657.140000000007 | 12205.28 | 2580.2999999999993 | 18 | 2191.26 | NULL | NULL | NULL | NULL | NULL | 2026-06-01 | NULL | NULL |
| 2026-06-05 | 284302 | 26284302 | 43 | Overdue 1 | 392293 | 2026-05-14 19:51:18 | Student | 38695.31999999998 | 24189.859999999997 | 11973.980000000001 | 2531.5199999999986 | 18 | 2149.74 | NULL | NULL | NULL | NULL | NULL | 2026-06-01 | NULL | NULL |

## CONTACT_DEBT_COLLECTION

5 แถวตัวอย่าง · 14 คอลัมน์

| ID | CONTRACT_ID | APP_ID | CONTARCT_NUMBER | CONTACT_NUMBER | RESULT_COLLECTION | REMARK_1 | REMARK_2 | DUE_DATE | PAYMENT_AMT | CreateBy | CreateByName | CreateByEmail | CreateDate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 9242 | 111049 | 2109242 | 1 | <ข้อความอิสระ ตัดออก 9 ตัวอักษร> | <ข้อความอิสระ ตัดออก 83 ตัวอักษร> | NULL | 2022-03-23 00:00:00 | NULL | COMSEVEN2019\supatra.r | supatra.r | s***@comseven.com | 2022-03-21 09:10:03 |
| 2 | 31459 | 136250 | 2131459 | 1 | <ข้อความอิสระ ตัดออก 9 ตัวอักษร> | <ข้อความอิสระ ตัดออก 22 ตัวอักษร> | NULL | NULL | NULL | COMSEVEN2019\atiphat.t | atiphat.t | a***@comseven.com | 2022-03-21 10:06:52 |
| 3 | 1649 | 101891 | 2001649 | 1 | <ข้อความอิสระ ตัดออก 12 ตัวอักษร> | <ข้อความอิสระ ตัดออก 59 ตัวอักษร> | NULL | 2022-03-21 00:00:00 | NULL | COMSEVEN2019\Nitchaon.S | Nitchaon.S | N***@comseven.com | 2022-03-21 10:13:47 |
| 4 | 7975 | 110001 | 2107975 | 1 | <ข้อความอิสระ ตัดออก 12 ตัวอักษร> | <ข้อความอิสระ ตัดออก 21 ตัวอักษร> | NULL | NULL | NULL | COMSEVEN2019\Nitchaon.S | Nitchaon.S | N***@comseven.com | 2022-03-21 10:19:08 |
| 5 | 14676 | 116458 | 2114676 | 1 | <ข้อความอิสระ ตัดออก 12 ตัวอักษร> | <ข้อความอิสระ ตัดออก 61 ตัวอักษร> | NULL | NULL | NULL | COMSEVEN2019\Warayu.s | Warayu.s | W***@comseven.com | 2022-03-21 10:23:00 |

## MT_STATUS

5 แถวตัวอย่าง · 2 คอลัมน์

| HP_STA_ID | STA_NAME |
|---|---|
| 1 | Save draft |
| 2 | Wait Checker |
| 3 | Wait Approve |
| 4 | Approve |
| 5 | Rework |

## MT_ADDRESS_TYPE

5 แถวตัวอย่าง · 2 คอลัมน์

| ADRTYPE_ID | ADRTYPE_NAME |
|---|---|
| 1 | ที่อยู่ตามทะเบียน |
| 2 | ที่อยู่ปัจจุบัน |
| 3 | ที่อยู่ติดต่อได้ |
| 4 | ที่อยู่จัดส่งเอกสาร |
| 5 | อื่น ๆ |

## MT_PROVINCE

5 แถวตัวอย่าง · 3 คอลัมน์

| PROVINCE_ID | PROVINCE_NAME | ZONE_ID |
|---|---|---|
| 10 | กรุงเทพมหานคร | 7 |
| 11 | สมุทรปราการ | 7 |
| 12 | นนทบุรี | 7 |
| 13 | ปทุมธานี | 7 |
| 14 | พระนครศรีอยุธยา | 3 |

## MT_DISTRICT

5 แถวตัวอย่าง · 3 คอลัมน์

| DISTRICT_ID | DISTRICT_NAME | PROVINCE_ID |
|---|---|---|
| 1001 | พระนคร | 10 |
| 1002 | ดุสิต | 10 |
| 1003 | หนองจอก | 10 |
| 1004 | บางรัก | 10 |
| 1005 | บางเขน | 10 |

## MT_SUB_DISTRICT

5 แถวตัวอย่าง · 3 คอลัมน์

| SUB_DISTRICT_ID | SUB_DISTRICT_NAME | DISTRICT_ID |
|---|---|---|
| 100101 | พระบรมมหาราชวัง | 1001 |
| 100102 | วังบูรพาภิรมย์ | 1001 |
| 100103 | วัดราชบพิธ | 1001 |
| 100104 | สำราญราษฎร์ | 1001 |
| 100105 | ศาลเจ้าพ่อเสือ | 1001 |

## MT_BRAND

5 แถวตัวอย่าง · 8 คอลัมน์

| BRAND_ID | BRAND_CODE | BRAND_NAME | PRODUCT_CATEGORY_ID | PRODUCT_CATEGORY_NAME | ACTIVE_STATUS | ACTIVE_STATUS_PFUND | UPhone_Active |
|---|---|---|---|---|---|---|---|
| 1 | 01 | Apple | 2 | Smart Phone | True | True | NULL |
| 9 | 09 | Apple | 3 | Tablet | True | True | NULL |
| 15 | 15 | Apple | 4 | Laptop | True | True | NULL |
| 16 | 16 | Samsung | 5 | Smart Phone | False | False | NULL |
| 17 | 17 | Samsung | 6 | Tablet | False | False | NULL |

## MT_CATEGORY

5 แถวตัวอย่าง · 6 คอลัมน์

| CATEGORY_ID | CATEGORY_CODE | CATEGORY_NAME | GROUP_CATE_ID | BUNDLE_WARRANTY_STATUS | ACTIVE_STATUS |
| ----------- | ------------- | ------------- | ------------- | ---------------------- | ------------- |
| 2           | 01            | Smart Phone   | 1             | F                      | T             |
| 3           | 02            | Tablet        | 1             | F                      | T             |
| 4           | 03            | Laptop        | 1             | F                      | T             |
| 5           | 05            | Smart Phone   | 2             | F                      | F             |
| 6           | 06            | Tablet        | 2             | F                      | F             |

## MT_SERIES

5 แถวตัวอย่าง · 8 คอลัมน์

| SERIES_ID | SERIES_CODE | SERIES_NAME | BRAND_ID | BRAND_NAME | ACTIVE_STATUS | ACTIVE_STATUS_PFUND | UPhone_Active |
|---|---|---|---|---|---|---|---|
| 8 | 8 | iPhone 11 Pro | 1 | Apple | F | F | NULL |
| 9 | 9 | iPhone 11 Pro Max | 1 | Apple | F | F | NULL |
| 10 | 10 | iPhone 11 (New Box) 64GB | 1 | Apple | F | F | NULL |
| 11 | 11 | iPhone 7 Plus | 1 | Apple | F | F | NULL |
| 12 | 12 | iPhone SE | 1 | Apple | F | F | NULL |

## MT_OCCUPATION

5 แถวตัวอย่าง · 10 คอลัมน์

| Ocpt_ID | Ocpt_name | Flag_Ocpt | GROUP_INCOME | GROUP_TYPE | GROUP_RISK | Ocpt_Active | Ascend_Name_En | Create_Datetime | Update_Datetime |
|---|---|---|---|---|---|---|---|---|---|
| 0 | อื่นๆ | NULL | 1 | 1 | 3 | F          | Others | NULL | NULL |
| 1 | นักเรียน/นักศึกษา | NULL | 1 | 3 | 3 | T          | Student | NULL | NULL |
| 2 | ข้าราชการ | NULL | 1 | 1 | 1 | T          | Government Officer | NULL | NULL |
| 3 | พนักงานรัฐวิสาหกิจ | NULL | 1 | 1 | 1 | T          | State Enterprise Employee | NULL | NULL |
| 4 | ข้าราชการเกษียณอายุ | NULL | 1 | 1 | 2 | T          | Retired Government Officer | NULL | NULL |

## MT_BANK

5 แถวตัวอย่าง · 3 คอลัมน์

| MT_BANK_ID | BANK_NAME | ABBV |
|---|---|---|
| 1 | ธนาคารกรุงเทพ | BBL |
| 2 | ธนาคารกสิกรไทย | KBANK |
| 3 | ธนาคารกรุงไทย | KTB |
| 4 | ธนาคารไทยพาณิชย์ | SCB |
| 5 | ธนาคารกรุงศรีอยุธยา | BAY |

## MT_REPAY_TYPE

5 แถวตัวอย่าง · 2 คอลัมน์

| MT_REPAY_TYPE | REPAY_TYPE_NAME |
|---|---|
| 1 | เงินดาวน์ |
| 2 | ค่างวดเช่าซื้อ |
| 3 | ค่าเบี้ยปรับ |
| 4 | ค่าติดตามทวงถาม |
| 5 | ค่าเช่าซื้อ |

## MT_TYPE_PAYMENT

5 แถวตัวอย่าง · 2 คอลัมน์

| TYPE_PAY_ID | TYPE_PAYMENT |
|---|---|
| 1 | ค่ารถยนต์ |
| 2 | ค่า Commission |
| 3 | ค่า Commission Extra 1 |
| 4 | ค่า Commission Extra 2 |
| 5 | ค่า Commission Extra 3 |

## MT_MARITAL_STATUS

5 แถวตัวอย่าง · 2 คอลัมน์

| Mst_ID | MaritalStatus |
|---|---|
| 1 | โสด |
| 2 | สมรส |
| 3 | สมรสไม่จดทะเบียน |
| 4 | หม้าย |
| 5 | หย่า |

## MT_INSTALLMENT

5 แถวตัวอย่าง · 4 คอลัมน์

| INSTALL_ID | INSTALL | ACTIVE_UFUND | ACTIVE_PFUND |     |
| ---------- | ------- | ------------ | ------------ | --- |
| 1          | 3       | False        | False        |     |
| 2          | 6       | False        | False        |     |
| 3          | 9       | True         | True         |     |
| 4          | 12      | True         | True         |     |
| 5          | 18      | True         | True         |     |

## MT_COLLECTION

5 แถวตัวอย่าง · 2 คอลัมน์

| RESULT_DEBT_ID | RESULT_DEBT_NAME |
|---|---|
| 1 | ติดต่อลูกค้าสำเร็จ |
| 2 | ติดต่อลูกหนี้ไม่ได้ |
| 3 | ยินยอมพร้อมนัดหมายชำระหนี้ |
| 4 | ไม่ชำระหนี้ขอคืนเครื่องพร้อมนัดหมาย |
| 5 | ลูกหนี้ขอเจรจาปรับปรุงโครงสร้างหนี้ |

## MT_DebtContactStatus

5 แถวตัวอย่าง · 8 คอลัมน์

| ID | Debt_Contact_Status_Name | StatusGroup | ActiveStatus | Create_Date | Create_By | Update_Date | Update_By |
|---|---|---|---|---|---|---|---|
| 1 | นัดชำระ | 1 | True | 2023-06-29 17:48:15 | COMSEVEN2019\K2admin | 2023-07-03 16:16:47 | COMSEVEN2019\K2admin |
| 2 | ติดต่อไม่ได้ | 2 | True | 2023-06-29 17:52:21 | COMSEVEN2019\K2admin | NULL | NULL |
| 3 | ติดต่อได้แต่ยังไม่นัดชำระ (Not Promise to pay) | 2 | True | 2023-06-29 17:53:10 | COMSEVEN2019\K2admin | NULL | NULL |
| 4 | ผิดนัดชำระ (Broken Promise  to pay) | 2 | True | 2023-06-29 17:53:23 | COMSEVEN2019\K2admin | 2023-07-26 11:07:15 | COMSEVEN2019\Supreeya.T |
| 5 | ไม่รับสาย (No Answer) | 2 | True | 2023-06-29 17:53:33 | COMSEVEN2019\K2admin | NULL | NULL |

## MT_SALARY_RANGE

5 แถวตัวอย่าง · 4 คอลัมน์

| SALARY_RANGE_ID | SALARY_RANGE_MAX | SALARY_RANGE_MIN | SALARY_RANGE_CODE |
|---|---|---|---|
| 1 | 7999.99 | 1 | 01 |
| 2 | 9999.99 | 8000 | 02 |
| 3 | 11999.99 | 10000 | 03 |
| 4 | 14999.99 | 12000 | 04 |
| 5 | 19999.99 | 15000 | 05 |

## MT_RESIDENCE_STATUS

5 แถวตัวอย่าง · 3 คอลัมน์

| RESIDENCE_ID | RESIDENCE_NAME | PROJECT_NAME |
|---|---|---|
| 1 | เจ้าของบ้าน | STUDENDT |
| 2 | เจ้าบ้าน | STUDENDT |
| 3 | บ้านพ่อ,แม่ | STUDENDT |
| 4 | บ้านพี่,น้อง | STUDENDT |
| 5 | บ้านคู่สมรส | STUDENDT |

## SETUP_PARTNER

5 แถวตัวอย่าง · แสดง 22 คอลัมน์แรกจาก 53

| PARTNER_ID | ADDRESS_NON_ID | PARTNER_CODE | PARTNER_TYPE | PARTNER_NAME | PHONE | FAX | EMAIL | LINEID | FACEBOOK | WEBSITE | REGIST_NO | REGISTER_DATE | CAPITAL | CAPITAL_PAY | BUSINESS_YEAR | PRODUCT_BRAND1 | PRODUCT_BRAND2 | PRODUCT_BRAND3 | PRODUCT_BRAND4 | INCOME | PRINCIPLE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1024 | 43 | D20201025 | 1 | บริษัท คอมเซเว่น จำกัด (มหาชน) | XXX-XXX-7770 | 020177770 | c***@comseven.com | c*** | c*** | www.comseven.com | 0-XXXX-XXXXX-XX-X | 2004-02-27 | 300000000.0 | 300000000.0 | 16 | NULL | NULL | NULL | NULL | 1500000.0 | 1500000.0 |
| 1026 | 68 | D20201027 | 1 | บริษัท ไพร์ม โซลูชั่น แอนด์ เซอร์วิส จำกัด | XXX-XXX-7777 | 029997777 | t***@COMSEVEN.COM | p*** | p*** | www.prime.com | 0-XXXX-XXXXX-XX-X | 2005-04-27 | 39200000.0 | 39200000.0 | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 1027 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 1028 | 1 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |
| 1029 | 63 | NULL | 1 | บริษัท ยูฟิคอน จำกัด | NULL | NULL | NULL | NULL | NULL | NULL | 0-XXXX-XXXXX-XX-X | 1987-06-10 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |

## SETUP_PARTNER_BRANCH

5 แถวตัวอย่าง · 10 คอลัมน์

| P_BRANCH_ID | PARTNER_ID | P_BRANCH_CODE | BRANCH_TYPE | BRANCH_NAME | BRANCH_ADDRESS | SALLLER_PHONE | CALLCENTER_PHONE | FAX_PHONE | EMAIL |
|---|---|---|---|---|---|---|---|---|---|
| 1062 | 1024 | 260 | 1 | ID260 : Studio 7(Ustore)-KKU-Khonkaen | *** | XXX-XXX-6152 | XXX-XXX-6152 | NULL | NULL |
| 1063 | 1024 | 417 | 1 | ID417 : Studio 7(Ustore)-CMU-Chiangmai | *** | XXX-XXX-6151 | XXX-XXX-6151 | NULL | NULL |
| 1065 | 1024 | 705 | 1 | ID705 : Studio7(Ustore)-KMITL-Ladkrabang | *** | XXX-XXX-4098 | XXX-XXX-4098 | NULL | NULL |
| 1066 | 1024 | 706 | 1 | ID706 : Studio7(Ustore)-KMUTT-Bangmod | *** | XXX-XXX-8160 | XXX-XXX-8160 | NULL | NULL |
| 1067 | 1024 | 707 | 1 | ID707 : Studio7(Ustore)-RSU-Rangsit | *** | XXX-XXX-8164 | XXX-XXX-8164 | NULL | NULL |
