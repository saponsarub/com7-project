# EV Business

ธุรกิจรถยนต์ไฟฟ้าของกลุ่ม COM7 — ให้เช่า/ขายรถ EV ภายใต้แบรนด์ **EV7** และ **AION**
ระบบต้นทาง: **GI Core** · **EV7 Core** · **EV7 Tracking**

> **อัปเดต 2026-08-28** — มีเอกสารเทียบระบบกับ Ontime (จีน) แล้ว: มี 67 จาก 88 โมดูล (76%)
> และพบว่า **K2 อาจให้บริการงานใบแจ้งหนี้/บิลค้างของธุรกิจ EV ด้วย** → [[EV System Landscape]] · [[EV China Benchmark]]

---

## Naming

| คำ | ปรากฏยังไง |
|---|---|
| EVSEVEN | ชื่อ BU ใน brief เดิม |
| GI | ใช้ทั่วไป — "GI Core", "GI CORE เป็นระบบหลัก", ชื่อไฟล์ `FO_GICARS.sql` |
| EV7 | เป็น survey item แยก (1.1.5) จาก GI Core (1.1.3) |
| AION | แบรนด์รถ EV |

Timeline แยก survey GI Core กับ EV7 เป็นคนละรายการ และบันทึกประชุมพูดถึงทั้งคู่ว่าเป็นสองสิ่งที่จะเอามารวมกัน — **ความสัมพันธ์เชิงองค์กรที่แน่นอนยังไม่รู้**

---

## GI Core

**Physical:** MySQL กำหนดด้วย Prisma — `schema.prisma` มี **166 models**
**Org codes:** `enum OrgCode { Com7, Aion, DPI1, CFW }`

บันทึกประชุม: *"ปัจจุบัน GI CORE เป็นระบบหลัก และมี RPA เชื่อมข้อมูลไปยังระบบอื่น"*

### Domains covered

จาก 166 models:

- **User และองค์กร** — `user`, `user_permission`, `user_zone`, `company`, `locations`, `location_account`
- **ภูมิศาสตร์** — `geographies`, `provinces`, `amphures`, `districts`
- **ลูกค้า** — `customers`, `customer_identify`
- **รถ** — `cars_models`, `cars_series`, `cars_colors`, `cars_colors_stock`, `car_company`
- **Lead** — `interesting`, `lead`, `follow_lead`, `admin_lead`, `admin_follow_lead`
- **ทดลองขับ** — `testdrive`, `testdrive_before`, `testdrive_after` + ตารางรูป
- **Booking** (กลุ่มใหญ่) — `booking`, `booking_document`, `booking_cancel`, `booking_slip`, `booking_delivery`, `booking_contract`, `booking_gift`, `booking_match_car`, `booking_summary_*`
- **สต็อก** — `stock`, `stock_serial`, `stock_lot`, `import_car`, `task_checkstock`
- **CRM** — `crm`, `crm_file`, `crm_comment`, `crm_case_log`
- **แท็กซี่/fleet** — `taxi`, `taxi_log`, `taxi_follow`, `taxi_follow_fleet`, `taxi_follow_ufund`, `taxi_preset`, `taxi_link`, `taxi_auto_assign`, `taxi_lineman`, `taxi_grab`
- **แชท** — `chat_folder`, `chat_room`, `chat_room_message`, `chat_room_tag`
- **อื่นๆ** — `gift`, `gift_list`, `red_tag`, `red_label_match_car`, `buyback_iphone`, `news_content`, `account`

**3 model ที่น่าสนใจ:**
- `taxi_follow_ufund` — มีความเชื่อมโยงกับ UFUND อยู่ในโครงสร้างแล้ว
- `buyback_iphone` — การรับซื้อคืน iPhone อยู่ในระบบ EV
- `taxi_lineman`, `taxi_grab` — เชื่อมกับ Lineman และ Grab

### The `customers` table

```prisma
model customers {
  id_customer   Int       @id @default(autoincrement())
  prefix        String?   @db.VarChar(255)
  fisrt_name    String    @db.VarChar(255)   // สะกดผิดใน production
  last_name     String?   @db.VarChar(255)
  address       String?   @db.LongText
  email         String    @db.VarChar(255)   // NOT NULL
  tel           String    @db.VarChar(255)   // NOT NULL
  line_id       String?   @db.VarChar(255)
  IdentityCard  String?   @db.VarChar(13)    // nullable
  id_district_2 Int?
  channel       String?
  passport      String?   @db.VarChar(255)
  company_name  String?   @db.VarChar(255)
  birthday      DateTime?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @default(now()) @updatedAt
}
```

**สิ่งที่ schema บอกได้ทันที:**

- `IdentityCard` เป็น **nullable** — match key หลักที่ที่ประชุมตกลงกันไว้ อาจไม่มีในบางเรคอร์ด
- `email` และ `tel` เป็น **NOT NULL** — มีเสมอ ใช้เป็น fallback ได้ `[อนุมาน]`
- `address` เป็น **LongText** ไม่มีโครงสร้างแยกจังหวัด/อำเภอ
- `line_id` เป็นช่องทางติดต่อ ไม่ใช่ LINE UID ระดับระบบ
- `fisrt_name` สะกดผิด แก้ที่ต้นทางไม่ได้แล้วโดยไม่กระทบผู้ใช้

`customer_identify` เป็นตารางเล็ก (address, district, customer link, createdAt) — **ไม่รู้ว่าใช้ทำอะไร**

---

## EV7

**ระบบ: EV7CORE** — ไม่พบเอกสาร schema

### Business rules from meeting notes

> "EVSEVEN มี collection ของตัวเอง /ไม่เกี่ยวกับ TFF"
> "EV 7 มีแค่ 4OD (4วัน) และจะทำการตัด ไม่ให้ชาจไฟ"
> "EV7 ลูกค้าบางโอน อาจโอนเคส Collection ไปยัง TFF ได้"

สองข้อแรกกับข้อสามดูขัดกันเล็กน้อย ควรถามให้ชัดว่าเมื่อไหร่เคสถึงโอนไป TFF `[อนุมาน]`

**นโยบาย 4OD** เป็นกลไกที่ไม่ธรรมดา — ตัดการชาร์จไฟจากระยะไกลเมื่อค้างชำระ 4 วัน แปลว่า EV7 น่าจะมีข้อมูล operational แบบเกือบ real-time ที่ผู้ให้สินเชื่อทั่วไปไม่มี `[อนุมาน]`

---

## Five overlapping systems

บันทึกประชุม:

> "มีฐานข้อมูลซ้ำซ้อนจากการพัฒนาระบบหลายช่วงเวลาและ Data Source กระจายหลายระบบ ex.
> D365 (GI เก่า) / GI CORE (ปัจจุบัน) / AION DMS (ของจีน) / EV7CORE / EVTRACKING บางรายการ GI ยังอยู่ในนี้ เพราะโอนไปเป็น EV7"

> "ปัจจุบัน GI CORE เป็นระบบหลัก และมี RPA เชื่อมข้อมูลไปยังระบบอื่น ทำให้ต้องทำความเข้าใจ Data Flow ให้ชัดเจนก่อน"

**RPA เป็นความเสี่ยงตอน migrate** — บันทึกเองเตือนไว้ว่าต้องเข้าใจ data flow ก่อน

---

## Project GI + EV7 → 7Club

มีโปรเจกต์แยกที่จะรวมข้อมูลลูกค้าเข้า 7Club → **[[GI + EV7 to 7Club|GI + EV7 → 7Club]]**

---

## เชื่อมกับโน้ตอื่น

[[System Inventory]] · [[ITOS Overview]] · [[CRM Overview]] · [[Customer Identity]]
