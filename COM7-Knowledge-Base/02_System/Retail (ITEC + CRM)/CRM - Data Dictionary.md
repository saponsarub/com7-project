# CRM - Data Dictionary

ระบบสมาชิก/ลูกค้าของ COM7 — เอกสารทีม CRM: 3 ตาราง 61 ฟิลด์ · ฐานจริง: 15 ตาราง

> **ตรวจฐานจริง 2026-11-10** (Aurora MySQL 8.0.42 · database `crm_pool_prod` · read-only ผ่าน Outline VPN · profile `crm` ใน `scripts/db.py` · env `CRM_USER` / `CRM_PWD`)
> คำอธิบายฟิลด์มาจากเอกสารทีม CRM (ส.ค.) · ตารางฟิลด์ด้านล่างเรียงตามลำดับคอลัมน์จริง — **บัญชีเรามองเห็นไม่ครบ**: `members` 30 จาก 63 คอลัมน์ · `customer_master` 34 จาก 42 · `member_auth` 6 จาก 8 (ถูกซ่อนสิทธิ์ระดับคอลัมน์) · ฟิลด์ในเอกสารที่มองไม่เห็นติด 🔒 · โครงสร้างที่เห็นทั้งหมด `02_System/_raw/crm-columns.csv`

## ฐานจริง — 15 ตาราง (นับ 2026-11-10)

| ตาราง | แถว | เก็บอะไร |
|---|--:|---|
| `customer_master` | 21,013,427 | ลูกค้าทั้งหมด · มีเบอร์ 20.5M · อีเมล 11.1M · วันเกิด 4.2M · `is_member=1` 8.87M |
| `members` | 8,964,616 | สมาชิก · `itec_cuscode` ครบทุกแถว · `pdpa_consents` 8.96M · `subdistrict` 7.97M |
| `member_auth` | 1,992,680 | 7Club+ (login) · **`identity_no` มีค่า 154,889 แถว (เป็นเลข 13 หลัก 150,241)** |
| `customers_order_ingestion` | 12,160,952 | หัวออเดอร์ ม.ค. 2023 → ปัจจุบัน · ช่องทาง OFFLINE 11.7M · ONLINE 291k · MKP 152k · มีสาขา ยอด ส่วนลด ผ่อน UTM · `inv_ref`/`doc_ref` (เชื่อมบิล ITEC `[อนุมาน]`) |
| `customers_order_items_ingestion` | 40,811,406 | รายการสินค้าในออเดอร์ · sku · ราคา · หมวด · แบรนด์ · รุ่น |
| `order_payment_info` | 12,830,571 | การจ่ายเงินของบิล (`sell_branch_id`, `sell_id` = บิล ITEC `[อนุมาน]`) |
| `customers_voucher` | 7,350,121 | คูปอง/voucher ที่สมาชิกได้รับ ใช้แล้วหรือยัง |
| `data_migration_crm_data` / `data_migration_customers` | 3.5M / 3.6M | ข้อมูลที่ย้ายมาจากระบบเก่า |
| `member_line_accounts` | 431,439 | LINE UID ของสมาชิก |
| `member_backup_register` | 192,640 | สำรองการสมัคร |
| `customers_non_sales` | 12,360 | event ที่ไม่ใช่การขาย |
| `customers_order_mkp` / `…_items_mkp` | 590 / 635 | ออเดอร์ marketplace |
| `view_customers_ingestion` (view) | — | สรุปลูกค้า: consent · 7Club BU/ช่องทาง/วันสมัคร · จังหวัด · มีอีเมล/เบอร์ไหม |

**`pdpa_consents`** = JSON array ของ `{"id", "consent"}` ทุกแถว (ตอบคำถามเดิมว่าโครงสร้างเป็นอย่างไร)
**เชื่อม ITEC ตัวใหม่:** `members.itec_cuscode` = [[ITEC-Rep Overview|Customer2.CusCode]] — สุ่ม 20,000 เจอ 100%

---

| ตาราง | เก็บใคร | จำนวน |
|---|---|---|
| `customer_master` | ลูกค้าทั้งหมด (เป็นสมาชิกและไม่เป็นสมาชิก) | 21,013,427 |
| `members` | สมาชิก | 8,964,616 (นับจริง 2026-11-10) |
| `member_auth` | สมาชิก 7Club+ | 1,992,680 |

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
-- ต้องมีสิทธิ์คอลัมน์ cm.citizen_no (บัญชีทีมเรายังมองไม่เห็น) — ถ้าไม่มี ใช้ ma.identity_no
SELECT cm.citizen_no, m.member_id, m.first_name, m.last_name,
       m.phone, m.province, ma.email AS login_email
FROM customer_master cm
JOIN members     m  ON m.customer_master_id = cm.id
LEFT JOIN member_auth ma ON ma.member_id = m.id
WHERE cm.citizen_no = ?;
```

---

## 1. `members` — สมาชิก 8,964,616 คน · 30 ฟิลด์

| # | ฟิลด์ | ชนิด | คำอธิบาย |
|--:|---|---|---|
| 1 | `id` 🔑 | bigint unsigned | Primary Key — เชื่อมกับ `member_auth.member_id` |
| 3 | `customer_master_id` 🔑 | bigint unsigned | เชื่อมไป `customer_master.id` |
| 4 | `type` | varchar(20) | ประเภทสมาชิก |
| 6 | `title` | varchar(50) | คำนำหน้าชื่อ |
| 7 | `first_name` | varchar(100) | ชื่อจริง |
| 8 | `last_name` | varchar(100) | นามสกุล |
| 10 | `gender` | varchar(20) | เพศ |
| 11 | `birth_date` | date | วันเกิด |
| 13 | `district` | varchar(100) | อำเภอ |
| 14 | `subdistrict` | varchar(100) | ตำบล |
| 15 | `province` | varchar(100) | จังหวัด |
| 26 | `phone` | varchar(50) | เบอร์โทรศัพท์สมาชิก |
| 27 | `email` | varchar(50) | อีเมลสมาชิก |
| 30 | `store_id` 🔑 | varchar(50) | รหัสร้าน |
| 31 | `itec_cuscode` 🔗 | varchar(50) | **รหัสลูกค้าฝั่ง ITEC** |
| 32 | `itec_sended_at` | timestamp | วันเวลาที่ส่งข้อมูลไป ITEC |
| 33 | `update_itec` | datetime | เวลาที่อัปเดตข้อมูล ITEC |
| 34 | `verified_type` | varchar(10) | ประเภทการยืนยันตัวตน |
| 35 | `verified_at` | timestamp | เวลายืนยันตัวตนล่าสุด |
| 36 | `pdpa_consents` | json | ข้อมูลยืนยัน PDPA — JSON array ของ `{"id", "consent"}` |
| 38 | `created_at` | timestamp | วันที่เก็บข้อมูลสมาชิก |
| 39 | `updated_at` | timestamp | วันที่อัปเดตข้อมูลล่าสุด |
| 42 | `career_group` | varchar(40) | กลุ่มอาชีพ |
| 45 | `career_name` | varchar(99) | ชื่ออาชีพ |
| 47 | `client` | varchar(50) | ช่องทาง/แอปที่สมัคร |
| 55 | `member_id` | varchar(255) | รหัสสมาชิก เช่น `M06xxxxxxx` |
| 58 | `is_student` | tinyint(1) | สถานะนักศึกษา (0/1) |
| 59 | `utm_source` | varchar(255) | UTM Source |
| 60 | `utm_medium` | varchar(255) | UTM Medium |
| 63 | `utm_campaign` | varchar(255) | UTM Campaign |
| 🔒 | `tax_id` | — | เลขประจำตัวผู้เสียภาษี · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |
| 🔒 | `branch_id` | — | รหัสสาขา (Tax Branch ID) · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |
| 🔒 | `branch_name` | — | ชื่อสาขา · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |
| 🔒 | `age` | — | อายุ · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |
| 🔒 | `address` | — | ที่อยู่ปัจจุบัน (บ้านเลขที่ · หมู่ · ซอย · ถนน) · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |
| 🔒 | `postcode` | — | รหัสไปรษณีย์ · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |
| 🔒 | `phone_etax` | — | เบอร์โทรศัพท์สำหรับ e-Tax · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |
| 🔒 | `email_etax` | — | อีเมลสำหรับ e-Tax · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |
| 🔒 | `utm_consent` | — | UTM Consent · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |
| 🔒 | `utm_term` | — | UTM Term · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |

### จุดที่ใช้งานได้ทันที

**ที่อยู่แยกฟิลด์** — ตามเอกสาร `address` + `subdistrict` + `district` + `province` + `postcode` · บัญชีเรามองเห็นแค่ `subdistrict` `district` `province` (`address` `postcode` 🔒)
ต่างจาก K2 ที่เก็บ 5 บล็อกในแถวเดียวและมีคำนำหน้าปนในข้อความ ([[K2 - Customer & Address]])
→ ใช้ CRM เป็นต้นแบบมาตรฐานที่อยู่ได้

**`itec_cuscode` คือคีย์เชื่อม CRM ↔ ITEC** พร้อมคู่ timestamp (`itec_sended_at`, `update_itec`) ที่บอกได้ว่า sync ล่าสุดเมื่อไหร่

**`is_student`** ตรงกับกลุ่มเป้าหมายหลักของ [[UFUND]] — ใช้ทำ segment ข้ามธุรกิจได้

**UTM** — มองเห็น 3 ตัว (`utm_source` `utm_medium` `utm_campaign`) → ตอบได้ว่าสมาชิกคนนี้มาจากแคมเปญไหน

**`created_at` / `updated_at`** → ทำ incremental extraction ได้

**e-Tax แยกช่องทาง** (🔒 มองไม่เห็น) — `phone_etax` / `email_etax` ต่างจาก `phone` / `email` ทั่วไป
เวลาส่งใบกำกับภาษีต้องใช้คู่ `_etax` ไม่ใช่ช่องทางปกติ

---

## 2. `customer_master` — ลูกค้าทั้งหมด 21,013,427 คน · 34 ฟิลด์

| # | ฟิลด์ | ชนิด | คำอธิบาย |
|--:|---|---|---|
| 1 | `id` 🔑 | bigint unsigned | Primary Key — ปลายทางของ `members.customer_master_id` |
| 2 | `uuid` | char(36) | UUID ของลูกค้า |
| 3 | `first_name` | varchar(100) | ชื่อ |
| 4 | `last_name` | varchar(100) | นามสกุล |
| 5 | `email` | varchar(100) | อีเมล |
| 6 | `phone` | varchar(50) | เบอร์โทรศัพท์ |
| 8 | `birth_date` | datetime | วันเกิด |
| 9 | `age` | int | อายุ |
| 10 | `consent_personal` | int | การยินยอมข้อมูลส่วนบุคคล |
| 11 | `consent_product` | int | การยินยอมข้อมูลสินค้า |
| 12 | `consent_promotion` | int | การยินยอมข้อมูลโปรโมชัน |
| 14 | `created_at` | timestamp | วันที่สร้างเรคอร์ด |
| 15 | `updated_at` | timestamp | วันที่แก้ไขล่าสุด |
| 20 | `amount_yearly` | decimal(12,2) | ยอดซื้อ 1 ปี |
| 21 | `period_yearly_at` | timestamp | วันตัดรอบยอด 1 ปี |
| 22 | `amount_6months` | decimal(12,2) | ยอดซื้อ 6 เดือน |
| 23 | `period_6months_at` | timestamp | วันตัดรอบยอด 6 เดือน |
| 24 | `amount_3months` | decimal(12,2) | ยอดซื้อ 3 เดือน |
| 25 | `period_3months_at` | timestamp | วันตัดรอบยอด 3 เดือน |
| 26 | `amount_monthly` | decimal(12,2) | ยอดซื้อเดือนนี้ |
| 27 | `period_monthly_at` | timestamp | วันตัดรอบยอดรายเดือน |
| 28 | `gender` | varchar(10) | เพศ |
| 29 | `is_member` | tinyint(1) | เป็นสมาชิกหรือไม่ (0/1) |
| 30 | `bnn` | tinyint(1) | เป็นลูกค้า/สมาชิก BaNANA `[อนุมาน จากชื่อ]` |
| 31 | `studio7` | tinyint(1) | เป็นลูกค้า/สมาชิก Studio7 `[อนุมาน จากชื่อ]` |
| 32 | `education` | tinyint(1) | การศึกษา |
| 33 | `caseclub` | tinyint(1) | เป็นลูกค้า Case Club `[อนุมาน จากชื่อ]` |
| 34 | `tire` | varchar(255) | ระดับ (tier) `[อนุมาน จากชื่อ]` |
| 35 | `type_online` | tinyint(1) | เคยซื้อออนไลน์ |
| 36 | `type_offline` | tinyint(1) | เคยซื้อหน้าร้าน |
| 37 | `is_active` | tinyint(1) | บัญชียังใช้งานอยู่ |
| 38 | `is_email_verify` | tinyint(1) | ยืนยันอีเมลแล้ว |
| 40 | `first_register_at` | timestamp | วันที่ลงทะเบียนครั้งแรก |
| 42 | `is_staff` | tinyint(1) | เป็นพนักงาน |
| 🔒 | `citizen_no` | — | **เลขบัตรประชาชน** · *มีในเอกสาร แต่บัญชีเรามองไม่เห็น* |

### จุดที่ใช้งานได้ทันที

**`citizen_no` คือคีย์ข้ามระบบที่แข็งแรงที่สุด** — ตรงชนิดเดียวกับ `PERSON.TAX_ID` ของ K2

> ⚠️ `customer_master.citizen_no` มีตามเอกสาร แต่**บัญชีเรามองไม่เห็น** (ถูกซ่อนสิทธิ์ระดับคอลัมน์ — ต้องขอจากทีม Inno) · ที่เห็นได้คือ `member_auth.identity_no` (154,889 แถว)
เป็นเส้นทางเดียวที่จะรู้ว่าลูกค้าที่ซื้อเครื่องสดที่ร้าน กับลูกค้าที่ผ่อนกับ UFUND เป็นคนเดียวกัน
→ [[Customer Identity]]

**consent แยก 3 ระดับ** — personal / product / promotion
ละเอียดกว่าทุกระบบต้นทางที่สำรวจมา และเป็นเหตุผลที่เสนอให้ CRM เป็นเจ้าของ consent → [[Consent & PDPA]]

**`is_staff` ต้องกรองออกทุกครั้งที่นับลูกค้า** — ไม่งั้นยอดสมาชิกและยอดขายจะรวมพนักงานเข้าไปด้วย

**`is_member = 0` คือลูกค้าที่ซื้อแต่ไม่สมัครสมาชิก** — ตารางนี้จึงกว้างกว่า `members`

---

## 3. `member_auth` — 7Club+ 1,992,680 คน · 6 ฟิลด์

| # | ฟิลด์ | ชนิด | คำอธิบาย |
|--:|---|---|---|
| 1 | `id` 🔑 | bigint unsigned | Primary Key |
| 2 | `identity_no` 🔗 | varchar(255) | เลขประจำตัวอ้างอิง |
| 3 | `email` | varchar(255) | อีเมลที่ใช้ Login |
| 4 | `phone` | varchar(255) | เบอร์โทรศัพท์ที่ใช้ Login |
| 5 | `member_id` | int | เชื่อมไป `members.id` |
| 8 | `created_at` | timestamp | วันที่สมัคร 7Club+ |

ตารางนี้เป็น**ชั้น authentication** ไม่ใช่โปรไฟล์ — โปรไฟล์อยู่ที่ `members`
สัดส่วน 1.99M / 8.96M ≈ **22% ของสมาชิกสมัคร 7Club+** (นับ 2026-11-10)

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
| `citizen_no` 🔒 · `identity_no` | `customer_master` · `member_auth` | **สูงสุด** — ระบุตัวตนได้โดยตรง ต้อง tokenize |
| `tax_id` | `members` | สูง |
| `identity_no` | `member_auth` | สูง |
| `phone` · `email` · `phone_etax` · `email_etax` | ทุกตาราง | กลาง — mask |
| `address` · `subdistrict` · `district` | `members` | กลาง — เก็บถึงระดับจังหวัดพอสำหรับ analytics |
| `birth_date` | ทั้งสอง | กลาง — เก็บเป็นช่วงอายุแทนได้ |

---

## เชื่อมกับโน้ตอื่น

[[CRM Overview]] · [[CRM Issues]] · [[Customer Identity]] · [[Consent & PDPA]] · [[System Inventory]] · [[K2 - Data Dictionary]] · [[Retail]]
