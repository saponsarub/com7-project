# CRM Overview

ระบบฐานสมาชิกและลูกค้าของกลุ่ม COM7 — สมาชิก ~8 ล้านคน · 7Club+ ~8 แสนคน
พจนานุกรมข้อมูลระดับฟิลด์ → [[CRM - Data Dictionary]]

> **อัปเดต 2026-08-28** — ได้พจนานุกรมข้อมูลระดับฟิลด์แล้ว 3 ตาราง → [[CRM - Data Dictionary]]
> คีย์ที่เชื่อม CRM กับ ITEC คือ **`members.itec_cuscode`**

---

## CRM

**ไม่รู้ว่าเป็น platform อะไร** — ไม่มีเอกสารไหนระบุชื่อผลิตภัณฑ์

### What Data Framework slide 8 says

**Current:**
> "CRM Data: Covers ITEC only. Data is sent to CRM team to conduct promotion/loyalty program through Braze."

**Propose:**
> "CRM Data: Covers every system in COM7 group. Data is sent to CRM team to conduct promotion/loyalty program through Braze. Can identify customer segment."

**Available Data (ทั้งสองฝั่ง):** มีทั้งสมาชิก 7Club และไม่ใช่สมาชิก

Main Customer id (เชื่อม 7Club ได้) · Citizen id · demographic (name, age, birth day, gender) · career type · address (province, district, post code) · contract channel (phone, e-mail) · create/updated date · activity and engagement · PDPA Consent · employee flag · student flag

### Fields the Gap Review places in CRM

Owner ที่ระบุคือ **Innovation**

| ID       | Field                                | สถานะ                                                                             |
| -------- | ------------------------------------ | --------------------------------------------------------------------------------- |
| `IDN-05` | Citizen ID                           | มีแต่ไม่ละเอียดพอ · ความเห็นในรายงาน: *"เก็บในระบบด้วย hash จะได้ไม่เสี่ยง pdpa"* |
| `LOY-01` | 7Club Tier / Membership Level        | มีแต่ไม่ละเอียดพอ · *"อ้างถึง 7Club แต่ไม่ระบุ field tier"*                       |
| `LOY-02` | Point Balance / Earn / Burn / Expiry | มีแต่ไม่ละเอียดพอ                                                                 |
| `LOY-04` | Member Aging / Tenure                | มีแต่ไม่ละเอียดพอ · อยู่ในหน้า 7 แต่ไม่อยู่ในหน้า 8                               |

Gap Review มีหมายเหตุปรากฏ 2 ครั้ง: *"สอบถาม Innovation และดูใน DataDic CRM แล้วไม่มี ต้องสร้างใหม่"*

→ **ได้ไฟล์แล้ว** `crm_fied_description.html` ถูกส่งให้ทีมข้อมูลและแตกเป็น [[CRM - Data Dictionary]] เรียบร้อย (3 ตาราง 61 ฟิลด์) — **ปิดคำถามนี้ 2026-09-11**

### Opinions recorded in the report

- `DEM-04`: *"ระบบ CRM ใหม่ควรจะให้เลือกช่องทางติดต่อที่สะดวกด้วย"*
- `DEM-07`: *"ระบบ CRM ใหม่ควรจะให้เลือกได้"*

คำว่า "ระบบ CRM ใหม่" ปรากฏซ้ำ — อาจกำลังพิจารณาเปลี่ยน CRM `[อนุมาน]` ยังไม่ยืนยัน

---

## 7Club

**ที่รู้:**
- CRM มีทั้งสมาชิกและไม่ใช่สมาชิก 7Club
- Main Customer id ของ CRM เชื่อมกับ 7Club ได้
- ทีม CRM รันโปรแกรม loyalty ผ่าน Braze
- Timeline เรียกว่า "7Club+" และ survey รวมกับ CRM

**ที่ไม่รู้:** 7Club เป็น source, target, หรือทั้งคู่ · เป็นระบบเดียวกับ CRM หรือคนละระบบที่เชื่อมกัน · membership ID scheme เป็นยังไง · BU ไหนเข้าร่วมบ้าง · เก็บ consent ของตัวเองไหม

**ไม่มีเอกสารไหนบอกว่า 7Club เป็น master customer system** — ที่เอกสารบอกคือ Main Customer id ของ CRM *เชื่อมได้* กับ 7Club ซึ่งเป็นคนละเรื่องกับการเป็น master

Gap Review `LOY-03` (Voucher / Coupon Issued & Redeemed) ระบุว่า **ขาด**

`DEV-06` มีหมายเหตุ *"น่าจะจับได้ถ้ามี 7 club"* — แปลว่าสมาชิก 7Club น่าจะเป็นสิ่งที่เชื่อมการซื้อเข้ากับตัวบุคคล `[อนุมาน]`

### Role in GI/EV7

7Club เป็นเป้าหมายของการรวมข้อมูล GI+EV7 แต่ที่ประชุมระบุว่า

> "ยังไม่มี Benefit ที่ตอบโจทย์ลูกค้า EV7/GI อย่างชัดเจน ต้องกำหนด Value Proposition ก่อน"

---

## Braze

Data Framework slide 8 (ทั้ง Current และ Propose) ระบุว่าข้อมูลถูกส่งให้ทีม CRM เพื่อทำ promotion/loyalty ผ่าน Braze

### Problems the Gap Review identifies

`ARC-01` — สถานะ **ขาด**, Priority **P1**, และเป็น**อันดับ 3 จาก 5** ของทั้งโปรแกรม

> "Braze เป็น engagement / orchestration platform ไม่ใช่ CDP หากไม่มี layer รวมข้อมูลอยู่ข้างหน้า แต่ละ BU จะยิงข้อมูลเข้า Braze แยกกัน"

> ผลกระทบหากไม่แก้ไข: "แต่ละ BU จะยิงข้อมูลเข้า Braze แยกกัน เกิด segment หยาบ ลงทุนซ้ำซ้อน และไม่เกิด single customer view"

ข้อเสนอในรายงาน: ควรระบุ layer รวมข้อมูล (CDP หรือ Customer 360 บน lakehouse) ให้ชัดว่าอยู่ระหว่าง source system กับ Braze

### `ARC-07` — narrow activation

สถานะ มีแต่ไม่ละเอียดพอ, P2

> "ระบุเฉพาะการส่งไป Braze ควรครอบคลุมปลายทางอื่นด้วย: ad platform, website / mobile app, LINE OA และที่สำคัญคือ POS หน้าร้าน"

> ผลกระทบ: "personalization เกิดเฉพาะช่องทางส่งข้อความ ไม่เกิดที่จุดขายจริงซึ่งเป็นจุดแข็งของธุรกิจค้าปลีก"

### `BHV-05` — engagement data does not flow back

สถานะ **ขาด**, P1

> "การตอบสนองต่อข้อความจาก Braze, LINE OA, e-mail"
> สถานะใน slide 8: "ไม่ปรากฏ (แม้จะส่งผ่าน Braze อยู่แล้ว)"

Braze สร้างข้อมูลนี้อยู่แล้ว แต่ไม่ไหลกลับเข้าข้อมูลลูกค้าของกลุ่ม — น่าจะเป็นช่องว่างที่ปิดได้ง่ายที่สุดเพราะข้อมูลมีอยู่แล้ว `[อนุมาน]`

### `ACT-04` — risk specific to the group structure

สถานะ **ขาด**, P1

> "เป็นความเสี่ยงเฉพาะของโครงสร้างแบบกลุ่มบริษัท ลูกค้าหนึ่งรายอาจได้รับข้อความจากหลาย BU ในวันเดียวกัน ต้องมี suppression และ priority rule ส่วนกลาง"

> ผลกระทบ: "ลูกค้ารำคาญและ opt-out ซึ่งเป็นความเสียหายที่กู้คืนได้ยากที่สุด"

### Governance

Braze เป็น data processor ภายนอกที่ประมวลผลข้อมูลส่วนบุคคล PDPA ม.37 กำหนดให้ผู้ควบคุมข้อมูลป้องกันไม่ให้ผู้รับข้อมูลใช้ผิดวัตถุประสงค์

**ยังไม่รู้:** Braze ประมวลผลและเก็บข้อมูลที่ประเทศไหน (เกี่ยวกับเรื่องส่งข้อมูลข้ามพรมแดน) · มีสัญญากับ processor แล้วหรือยัง

---

## เชื่อมกับโน้ตอื่น

[[System Inventory]] · [[ITEC Overview]] · [[EV Business]] · [[Customer Identity]] · [[Consent & PDPA]]
