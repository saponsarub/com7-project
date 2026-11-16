# CRM Issues

คำถามและงานค้างของระบบ CRM / สมาชิก · เนื้อหา → [[CRM Overview]] · [[CRM - Data Dictionary]]

---

## คำถามที่ยังไม่มีคำตอบ

| # | คำถาม | ใครตอบได้ | ทำไมสำคัญ |
|--:|---|---|---|
| 1 | `pdpa_consent` (json) ใน `members` มีโครงสร้างอะไร มี timestamp กับ channel ไหม | ทีม CRM | ถ้าไม่มี = ทั้งกลุ่มพิสูจน์ไม่ได้ว่าลูกค้ายินยอมเมื่อไหร่ ผ่านช่องทางไหน |
| 2 | `pdpa_consent` สัมพันธ์ยังไงกับ `consent_personal` / `consent_product` / `consent_promotion` ใน `customer_master` — อันไหนคือของจริง | ทีม CRM + legal | ตัดสินว่าจะอ่าน consent จากฟิลด์ไหน |
| 3 | ฐาน CRM คือ DBMS อะไร host ที่ไหน | ทีม CRM | ยังต่อฐานไม่ได้ ทำให้ verify ตัวเลขไม่ได้ (ชนิดข้อมูลเป็นสไตล์ MySQL `[อนุมาน]`) |
| 4 | `members` กับ `customer_master` เก็บ email/phone/birth_date ซ้ำกัน — เมื่อค่าไม่ตรง ยึดอันไหน | ทีม CRM | กระทบการทำ golden record |
| 5 | `identity_no` ใน `member_auth` คือเลขอะไร (บัตรประชาชน? รหัสภายใน?) | ทีม CRM | ถ้าเป็นเลขบัตร ต้อง mask เพิ่มอีกจุด |
| 6 | มีตารางอื่นอีกไหมนอกจาก 3 ตารางนี้ — แต้มสะสม · คูปอง · ธุรกรรม | ทีม CRM | เอกสารที่ได้ครอบคลุมแค่ 3 ตาราง |
| 7 | `itec_cuscode` เติมครบทุกแถวไหม หรือมีเฉพาะคนที่เคยซื้อ | ทีม CRM | กระทบว่าจะเชื่อม CRM ↔ ITEC ได้กี่ % |
| 8 | 7Club เป็น source, target หรือทั้งคู่ · เป็นระบบเดียวกับ CRM ไหม | P.Por | กระทบว่าจะ ingest กี่ระบบ |
| 9 | ITEC → CRM feed ทำงานยังไง ความถี่เท่าไหร่ | P.Por | ปัจจุบันรู้แค่ว่ามีคอลัมน์ `itec_sended_at` / `update_itec` |
| 10 | Braze ประมวลผลและเก็บข้อมูลที่ประเทศไหน · มีสัญญา processor แล้วหรือยัง | legal / DPO | PDPA ม.37 — การส่งข้อมูลข้ามพรมแดน |

---

## งานที่ต้องทำต่อ

- [ ] ขอ connection แบบ read-only เข้าฐาน CRM เพื่อ verify row count · null rate · รูปแบบข้อมูลจริง
- [ ] ขอตัวอย่าง `pdpa_consent` มา 5–10 แถวเพื่อดูโครงสร้าง JSON
- [ ] ทดสอบ join `member_auth.identity_no` (และ `customer_master.citizen_no` เมื่อได้สิทธิ์) กับ `PERSON.TAX_ID` ของ K2 ว่าตรงกันกี่ราย
- [ ] ขอสิทธิ์คอลัมน์ที่ถูกซ่อนจากทีม Inno — `customer_master` 8 คอลัมน์ (รวม `citizen_no`) · `members` 33 คอลัมน์ (รวม `address` `postcode` `tax_id`)
- [ ] ตัดสินใจกับ legal ว่า **CRM เป็น system of record ของ consent** หรือไม่ → [[Consent & PDPA]]

---

## ที่ปิดไปแล้ว

| คำถามเดิม | คำตอบ | เมื่อ |
|---|---|---|
| CRM data dictionary อยู่ที่ไหน | ได้จากทีม CRM แล้ว → [[CRM - Data Dictionary]] | 2026-08-28 |
| CRM ผูกกับ ITEC ด้วยคีย์อะไร | `members.itec_cuscode` | 2026-08-28 |
| 7Club+ มีสมาชิกเท่าไหร่ | **1,992,680** (นับ `member_auth`) | 2026-11-10 |

---

## เชื่อมกับโน้ตอื่น

[[Issue Index]] · [[CRM Overview]] · [[CRM - Data Dictionary]] · [[Consent & PDPA]] · [[Customer Identity]]
