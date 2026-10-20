# CRM - Data Dictionary

ระบบสมาชิก/ลูกค้าของ COM7 — 3 ตาราง 61 ฟิลด์

| ตาราง | เก็บใคร | จำนวน |
|---|---|---|
| `customer_master` | ลูกค้าทั้งหมด (เป็นสมาชิกและไม่เป็นสมาชิก) | — |
| `members` | สมาชิก | ~8,000,000 |
| `member_auth` | สมาชิก 7Club+ | ~800,000 |

---

## ความสัมพันธ์

```
customer_master
      │ id
      ▲
      │ customer_master_id
   members
      │ id
      ▲
      │ member_id
 member_auth
```

| การเชื่อม | ตอบคำถามว่า |
|---|---|
| `members.customer_master_id` → `customer_master.id` | สมาชิกคนนี้คือลูกค้าคนไหนในระบบใหญ่ |
| `member_auth.member_id` → `members.id` | สมาชิก 7Club+ คนนี้ มีโปรไฟล์อะไรบ้าง |

```sql
SELECT cm.citizen_no, m.member_id, m.first_name, m.last_name,
       m.phone, m.province, ma.email AS login_email
FROM customer_master cm
JOIN members     m  ON m.customer_master_id = cm.id
LEFT JOIN member_auth ma ON ma.member_id = m.id
WHERE cm.citizen_no = ?;
```

---

## 1. `members` — สมาชิก (~8 ล้านคน) · 39 ฟิลด์

|   # | ฟิลด์                   | ชนิด            | คำอธิบาย                                        |
| --: | ----------------------- | --------------- | ----------------------------------------------- |
|   1 | `id` 🔑                 | bigint unsigned | Primary Key — เชื่อมกับ `member_auth.member_id` |
|   2 | `customer_master_id` 🔑 | bigint unsigned | เชื่อมไป `customer_master.id`                   |
|   3 | `member_id`             | varchar(100)    | รหัสสมาชิก เช่น `M06xxxxxxx`                    |
|   4 | `type`                  | varchar(20)     | ประเภทสมาชิก                                    |
|   5 | `tax_id`                | varchar(20)     | เลขประจำตัวผู้เสียภาษี                          |
|   6 | `branch_id`             | varchar(20)     | รหัสสาขา (Tax Branch ID)                        |
|   7 | `branch_name`           | varchar(200)    | ชื่อสาขา                                        |
|   8 | `title`                 | varchar(50)     | คำนำหน้าชื่อ                                    |
|   9 | `first_name`            | varchar(100)    | ชื่อจริง                                        |
|  10 | `last_name`             | varchar(100)    | นามสกุล                                         |
|  11 | `gender`                | varchar(20)     | เพศ                                             |
|  12 | `birth_date`            | date            | วันเกิด                                         |
|  13 | `age`                   | int             | อายุ                                            |
|  14 | `address`               | varchar(255)    | ที่อยู่ปัจจุบัน (บ้านเลขที่ · หมู่ · ซอย · ถนน) |
|  15 | `subdistrict`           | varchar(100)    | ตำบล                                            |
|  16 | `district`              | varchar(100)    | อำเภอ                                           |
|  17 | `province`              | varchar(100)    | จังหวัด                                         |
|  18 | `postcode`              | varchar(5)      | รหัสไปรษณีย์                                    |
|  19 | `phone`                 | varchar(50)     | เบอร์โทรศัพท์สมาชิก                             |
|  20 | `email`                 | varchar(50)     | อีเมลสมาชิก                                     |
|  21 | `phone_etax`            | varchar(255)    | เบอร์โทรศัพท์สำหรับ e-Tax                       |
|  22 | `email_etax`            | varchar(255)    | อีเมลสำหรับ e-Tax                               |
|  23 | `store_id`              | varchar(20)     | รหัสร้าน                                        |
|  24 | `itec_cuscode` 🔗       | varchar(50)     | **รหัสลูกค้าฝั่ง ITEC**                         |
|  25 | `itec_sended_at`        | timestamp       | วันเวลาที่ส่งข้อมูลไป ITEC                      |
|  26 | `update_itec`           | datetime        | เวลาที่อัปเดตข้อมูล ITEC                        |
|  27 | `verified_type`         | varchar(10)     | ประเภทการยืนยันตัวตน                            |
|  28 | `verified_at`           | timestamp       | เวลายืนยันตัวตนล่าสุด                           |
|  29 | `pdpa_consent`          | **json**        | ข้อมูลยืนยัน PDPA                               |
|  30 | `career_group`          | varchar(40)     | กลุ่มอาชีพ                                      |
|  31 | `career_name`           | varchar(99)     | ชื่ออาชีพ                                       |
|  32 | `is_student`            | tinyint(1)      | สถานะนักศึกษา (0/1)                             |
|  33 | `utm_source`            | varchar(255)    | UTM Source                                      |
|  34 | `utm_medium`            | varchar(255)    | UTM Medium                                      |
|  35 | `utm_campaign`          | varchar(255)    | UTM Campaign                                    |
|  36 | `utm_consent`           | varchar(255)    | UTM Consent                                     |
|  37 | `utm_term`              | varchar(255)    | UTM Term                                        |
|  38 | `created_at`            | timestamp       | วันที่เก็บข้อมูลสมาชิก                          |
|  39 | `updated_at`            | timestamp       | วันที่อัปเดตข้อมูลล่าสุด                        |

### จุดที่ใช้งานได้ทันที

**ที่อยู่แยกฟิลด์เรียบร้อยแล้ว** — `address` + `subdistrict` + `district` + `province` + `postcode`
ต่างจาก K2 ที่เก็บ 5 บล็อกในแถวเดียวและมีคำนำหน้าปนในข้อความ ([[K2 - Customer & Address]])
→ ใช้ CRM เป็นต้นแบบมาตรฐานที่อยู่ได้

**`itec_cuscode` คือคีย์เชื่อม CRM ↔ ITEC** พร้อมคู่ timestamp (`itec_sended_at`, `update_itec`) ที่บอกได้ว่า sync ล่าสุดเมื่อไหร่

**`is_student`** ตรงกับกลุ่มเป้าหมายหลักของ [[UFUND]] — ใช้ทำ segment ข้ามธุรกิจได้

**UTM ครบชุด 5 ตัว** → ตอบได้ว่าสมาชิกคนนี้มาจากแคมเปญไหน ทำ attribution ได้

**`created_at` / `updated_at`** → ทำ incremental extraction ได้

**e-Tax แยกช่องทาง** — `phone_etax` / `email_etax` ต่างจาก `phone` / `email` ทั่วไป
เวลาส่งใบกำกับภาษีต้องใช้คู่ `_etax` ไม่ใช่ช่องทางปกติ

---

## 2. `customer_master` — ลูกค้าทั้งหมด · 16 ฟิลด์

|   # | ฟิลด์               | ชนิด            | คำอธิบาย                                              |
| --: | ------------------- | --------------- | ----------------------------------------------------- |
|   1 | `id` 🔑             | bigint unsigned | Primary Key — ปลายทางของ `members.customer_master_id` |
|   2 | `first_name`        | varchar(100)    | ชื่อ                                                  |
|   3 | `last_name`         | varchar(100)    | นามสกุล                                               |
|   4 | `email`             | varchar(100)    | อีเมล                                                 |
|   5 | `phone`             | varchar(50)     | เบอร์โทรศัพท์                                         |
|   6 | `citizen_no` 🔗     | varchar(255)    | **เลขบัตรประชาชน**                                    |
|   7 | `birth_date`        | datetime        | วันเกิด                                               |
|   8 | `age`               | int             | อายุ                                                  |
|   9 | `consent_personal`  | int             | การยินยอมข้อมูลส่วนบุคคล                              |
|  10 | `consent_product`   | int             | การยินยอมข้อมูลสินค้า                                 |
|  11 | `consent_promotion` | int             | การยินยอมข้อมูลโปรโมชัน                               |
|  12 | `is_member`         | int             | เป็นสมาชิกหรือไม่ (0/1)                               |
|  13 | `is_active`         | int             | บัญชียังใช้งานอยู่                                    |
|  14 | `is_staff`          | int             | เป็นพนักงาน                                           |
|  15 | `created_at`        | timestamp       | วันที่สร้างเรคอร์ด                                    |
|  16 | `updated_at`        | timestamp       | วันที่แก้ไขล่าสุด                                     |
|     |                     |                 |                                                       |

### จุดที่ใช้งานได้ทันที

**`citizen_no` คือคีย์ข้ามระบบที่แข็งแรงที่สุด** — ตรงชนิดเดียวกับ `PERSON.TAX_ID` ของ K2
เป็นเส้นทางเดียวที่จะรู้ว่าลูกค้าที่ซื้อเครื่องสดที่ร้าน กับลูกค้าที่ผ่อนกับ UFUND เป็นคนเดียวกัน
→ [[Customer Identity]]

**consent แยก 3 ระดับ** — personal / product / promotion
ละเอียดกว่าทุกระบบต้นทางที่สำรวจมา และเป็นเหตุผลที่เสนอให้ CRM เป็นเจ้าของ consent → [[Consent & PDPA]]

**`is_staff` ต้องกรองออกทุกครั้งที่นับลูกค้า** — ไม่งั้นยอดสมาชิกและยอดขายจะรวมพนักงานเข้าไปด้วย

**`is_member = 0` คือลูกค้าที่ซื้อแต่ไม่สมัครสมาชิก** — ตารางนี้จึงกว้างกว่า `members`

---

## 3. `member_auth` — 7Club+ (~8 แสนคน) · 6 ฟิลด์

| # | ฟิลด์ | ชนิด | คำอธิบาย |
|--:|---|---|---|
| 1 | `id` | bigint unsigned | Primary Key |
| 2 | `member_id` 🔑 | int | เชื่อมไป `members.id` |
| 3 | `identity_no` | varchar(255) | เลขประจำตัวอ้างอิง |
| 4 | `email` | varchar(255) | อีเมลที่ใช้ Login |
| 5 | `phone` | varchar(255) | เบอร์โทรศัพท์ที่ใช้ Login |
| 6 | `created_at` | timestamp | วันที่สมัคร 7Club+ |

ตารางนี้เป็น**ชั้น authentication** ไม่ใช่โปรไฟล์ — โปรไฟล์อยู่ที่ `members`
สัดส่วน 800k / 8M = **ราว 10% ของสมาชิกสมัคร 7Club+**

`email` / `phone` ในตารางนี้คือ**ช่องทางที่ใช้ล็อกอิน** อาจไม่เหมือนกับ `members.email` / `members.phone` ที่เป็นช่องทางติดต่อ

---

## ฟิลด์ที่ซ้ำกันระหว่างตาราง

| ฟิลด์ | `members` | `customer_master` | `member_auth` |
|---|:--:|:--:|:--:|
| `first_name` · `last_name` | ✅ | ✅ | — |
| `email` | ✅ | ✅ | ✅ (login) |
| `phone` | ✅ | ✅ | ✅ (login) |
| `birth_date` · `age` | ✅ | ✅ | — |
| `created_at` · `updated_at` | ✅ | ✅ | ✅ (created เท่านั้น) |

เวลาค่าไม่ตรงกัน ยังไม่มีกติกาว่ายึดตารางไหน → [[CRM Issues]]

---

## ฟิลด์ที่ต้องปกปิดก่อนเข้า Data Lake

| ฟิลด์ | ตาราง | ระดับ |
|---|---|---|
| `citizen_no` | `customer_master` | **สูงสุด** — ระบุตัวตนได้โดยตรง ต้อง tokenize |
| `tax_id` | `members` | สูง |
| `identity_no` | `member_auth` | สูง |
| `phone` · `email` · `phone_etax` · `email_etax` | ทุกตาราง | กลาง — mask |
| `address` · `subdistrict` · `district` | `members` | กลาง — เก็บถึงระดับจังหวัดพอสำหรับ analytics |
| `birth_date` | ทั้งสอง | กลาง — เก็บเป็นช่วงอายุแทนได้ |

---

## เชื่อมกับโน้ตอื่น

[[CRM Overview]] · [[CRM Issues]] · [[Customer Identity]] · [[Consent & PDPA]] · [[System Inventory]] · [[K2 - Data Dictionary]] · [[Retail]]
