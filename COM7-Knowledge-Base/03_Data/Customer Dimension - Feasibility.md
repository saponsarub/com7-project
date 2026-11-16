# Customer Dimension - Feasibility

บันทึกคร่าวๆ 2026-11-10 · ตรวจข้อเสนอ customer dimension ข้าม BU (แนวคิดแบบ The 1 ของ Central คือสมาชิกเลขเดียวใช้ได้ทุกธุรกิจในเครือ) เทียบกับข้อมูลที่มีจริง · **ยังไม่ได้สรุปแผนงาน**
ข้อมูลที่ใช้ตรวจ: CRM `crm_pool_prod` ↔ [[ITEC-Rep Overview|ITEC-Rep]] (`SSSynced50`) · สุ่มสมาชิก CRM 20,000 คน · บิลเดือน ต.ค. 2026
ที่เกี่ยวข้อง → [[Customer Main MVP]] · [[Customer Identity]] · [[CRM - Data Dictionary]] · [[Consent & PDPA]]

---

## คีย์เชื่อม CRM ↔ ITEC-Rep

| ทางเชื่อม | ผล | หมายเหตุ |
|---|---|---|
| **`members.itec_cuscode` = `Customer2.CusCode`** ⭐ | ตรง **99.97%** | `CusCode` เป็น PK จึงเร็ว · ควรใช้เป็นคีย์หลัก |
| `members.member_id` = `Customer2.CRMID` | ตรง 98.1% | อีก 1.9% `CRMID` ใน ITEC ว่าง · `CRMID` **ไม่มี index** จึงต้องสแกนทั้งตาราง 24.8 ล้านแถว |

**รูปแบบรหัส**
- `members.member_id` มีครบทุกแถว (8.97 ล้าน) เป็นรูปแบบ `M` + ตัวเลข 12 หลัก
- `members.itec_cuscode` มีครบทุกแถวเช่นกัน แต่มี 2 แบบ
  - **รหัสเก่า** 13 ตัว ตัวเลขปนตัวอักษรเล็ก ~7.0 ล้านคน
  - **รหัส `M…`** ซึ่งเท่ากับ `member_id` ~1.93 ล้านคน
- ฝั่ง ITEC-Rep `Customer2` มี 24.8 ล้านแถว แบ่งตาม `CRMID` ได้ดังนี้
  - `CRMID` ว่าง 15.8 ล้าน: น่าจะเป็นลูกค้าที่ไม่ได้เป็นสมาชิก `[อนุมาน]`
  - รหัสเก่าที่มี `CRMID` คู่กัน 7.0 ล้าน
  - `CusCode` = `CRMID` = รหัส `M…` 1.95 ล้าน
  - แบบอื่น 80k

**ชนิดข้อมูลต้องตั้งให้ตรงกันใน MySQL**
- ปัจจุบันไม่ตรงกัน
  - CRM: `itec_cuscode varchar(50)` · `member_id varchar(255)`
  - ITEC-Rep: `CusCode varchar(20)` · `CRMID varchar(50)`
- เสนอให้ตั้งคีย์ทั้งสองฝั่งเป็น `varchar(50)` และ collation เดียวกัน
- ระวังตัวพิมพ์เล็กใหญ่ เพราะรหัสเก่ามีตัวอักษรเล็กปน ถ้า join ใน pandas จะเทียบแบบแยกตัวพิมพ์

---

## ข้อเสนอ 5 ข้อ ทำได้แค่ไหน

### 1. ที่อยู่ลูกค้า เทียบกับสาขาที่ซื้อ: ทำได้
- **ที่อยู่**
  - ITEC-Rep `Cus2Address` มีที่อยู่จริง 5.57 ล้านรายการ
  - CRM `members` เห็นแค่ `district` / `subdistrict` / `province` เพราะที่อยู่เต็มและ `postcode` ถูกซ่อนจากบัญชีเรา
- **ที่ซื้อ:** `Sell.Branch` → สาขา / ภาค / จังหวัด
- **ที่ต้องทำต่อ:** ทำมาตรฐานชื่อพื้นที่ด้วย [[Thai Administrative Dimension]] ก่อนนำมาเทียบกัน

### 2. อายุสมาชิก และความถี่การซื้อ: ทำได้บางส่วน
- **ความถี่การซื้อ:** นับจาก `Sell` ตาม `CusCode` ได้เลย บิลมีตั้งแต่ 2007-03
- **อายุสมาชิก:** ยังมีปัญหา
  - `members.created_at` เก่าสุดคือ 2020-07-30 ทั้งที่มีสมาชิกรหัสเก่าก่อนหน้านั้น จึงน่าจะเป็นวันที่ย้ายเข้าระบบ CRM ปัจจุบัน ไม่ใช่วันสมัครจริง `[อนุมาน]`
  - **ต้องเช็ค** `customer_master.first_register_at` · ITEC-Rep `Customer.MemberSince` · วันซื้อครั้งแรกใน `Sell`

### 3. promotion กระตุ้นยอดแค่ไหน: ทำได้ แต่ดูที่รายการสินค้า ไม่ใช่เลขบิล
- `Sell.PMT` = 0 ทุกบิล และตาราง `SellPMT` ไม่มีข้อมูล (ต.ค. 2026 จำนวน 884k บิล)
- โปรโมชันอยู่ที่ **`SellItem.PMT` → `PMTProduct.ID`** ซึ่งเชื่อมได้ 100% · รายการที่ติดโปรมี 43% (1.19 ล้านจาก 2.79 ล้านรายการ)
- **ยังไม่ได้ดู:** ความหมายของ `PMTProduct.DiscountType` / `Discount` · คูปองเงินสด (`CashCoupon`, `CashCouponItem`) · ส่วนลดระดับบิล (`Sell.Discount`, `DiscountValue`)

### 4. active ล่าสุด และยอดซื้อ: ทำได้
- **คำนวณจาก ITEC-Rep:** `max(Sell.DocDate)` และ `sum(TotalPrice)` ต่อ `CusCode` ซึ่งเป็นพื้นฐานของ RFM
- **ใช้ค่าที่ CRM คำนวณไว้แล้ว:** `customer_master.amount_yearly` / `amount_6months` / `amount_3months` / `amount_monthly` · **ยังไม่ได้ตรวจ**ว่าตรงกับยอดที่คำนวณจาก ITEC-Rep หรือไม่

### 5. profile ข้าม BU: ทำได้เฉพาะฝั่งค้าปลีก
- **ค้าปลีก:** แยก BU ได้จาก `Sell.Branch` → สาขา → BU (BaNANA · Studio7 · KingKong ฯลฯ) ได้ทันที
- **รวม UFUND (K2):** ต้องเชื่อมด้วยเลขบัตรประชาชน แต่ติดอยู่หลายจุด
  - ฝั่ง CRM เราเห็นเลขบัตรแค่ใน `member_auth.identity_no` (~155k คน)
  - `customer_master.citizen_no` ถูกซ่อนจากบัญชีเรา ต้องขอสิทธิ์จากทีม Inno
  - การ join CRM ↔ K2 `PERSON.TAX_ID` **ยังไม่ได้ทดสอบ**
  - ต้องมีคำตอบเรื่อง consent ข้ามบริษัทก่อน → [[Consent & PDPA]]

---

## ค้างไว้ก่อนสรุปแผน
- เลือกแหล่งวันที่สมัครสมาชิกที่เชื่อถือได้ (ข้อ 2)
- ทำความเข้าใจตาราง promotion ให้ครบ (ข้อ 3)
- เทียบยอด `customer_master.amount_*` กับยอดที่คำนวณจาก ITEC-Rep (ข้อ 4)
- ขอสิทธิ์คอลัมน์ที่ถูกซ่อนใน CRM และทดสอบ join CRM ↔ K2 (ข้อ 5)
- ออกแบบ schema ใน MySQL ตาม [[SSOT Roadmap]]
