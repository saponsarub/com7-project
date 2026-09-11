# COM7 Group Structure

โครงสร้างนิติบุคคล · ธุรกิจ · แบรนด์ ของกลุ่มคอมเซเว่น

**ที่มา:** `COM7_Group_AI_Reference.md` (ทบทวนล่าสุด 2026-08-28)

> **กฎที่ต้องยึด:** แยก **นิติบุคคล (Legal Entity)** · **ธุรกิจ (Business)** · **แบรนด์ (Brand)** ออกจากกัน
> **แบรนด์หรือร้าน ไม่ได้แปลว่าเป็นนิติบุคคลแยก**

---

## Legal entities

| บริษัท                                | บทบาท                          | ธุรกิจหลัก                                                             |
| ------------------------------------- | ------------------------------ | ---------------------------------------------------------------------- |
| **Com7 PCL (COM7)**                   | บริษัทแม่ · จดทะเบียนในตลาด    | ค้าปลีก IT · สมาร์ทโฟน · คอมพิวเตอร์ · B2B/องค์กร/การศึกษา             |
| **Adept Co., Ltd.**                   | ค้าส่ง / กระจายสินค้า          | IT · สมาร์ทโฟน · IoT · อุปกรณ์เสริม · เครือข่ายตัวแทนจำหน่าย           |
| **Novus Integration**                 | Holding / ลงทุน                | ลงทุนในธุรกิจกลุ่ม · เกี่ยวข้องกับ Prime Solution                      |
| **See Know How (SKH)**                | เรียนรู้ / ฝึกอบรม             | พัฒนาบุคลากรและองค์ความรู้ภายใน                                        |
| **Double7 Co., Ltd.**                 | ค้าปลีก / บริการ               | บริหารร้าน **TRUE by COM7** · ธุรกิจโทรคมนาคม                          |
| **Prime Solution & Services (PRIME)** | เทคโนโลยี / System Integration | SI · พัฒนาซอฟต์แวร์ · IT solution · ดูแลระบบ                           |
| **Thunder FinFin (TFF)**              | บริการทางการเงิน               | **เช่าซื้อ/ผ่อนชำระ** สินค้า IT · เน้นกลุ่มนักศึกษา — แบรนด์ **UFUND** |
| **COM7 Holding**                      | Holding / ลงทุน                | ถือหุ้นบริษัทย่อย · เกี่ยวข้องกับ iCare Insurance, Gold Integrated     |
| **iCare Insurance PCL (ICI)**         | ประกันภัย                      | ประกันวินาศภัย — รถ · ทรัพย์สิน · อุบัติเหตุ · ขนส่ง → [[iCare Insurance (ICI)]] |

---

## Business domains

```
COM7 GROUP
│
├── CORE IT / RETAIL          BaNANA · Studio7 · U.Store · BaNANA Mobile
│                             BKK · KingKong Phone · Brand Shops
├── B2B / ENTERPRISE / EDU    องค์กร · SME · โรงเรียน · มหาวิทยาลัย · ราชการ
├── DISTRIBUTION              Adept
├── SERVICE / TELECOM         iCare (ซ่อม Apple) · Smart Care (ซ่อมยี่ห้ออื่น) · TRUE by COM7 (Double7)
├── FINANCE                   Thunder FinFin → UFUND
├── INSURANCE                 iCare Insurance
├── EV                        EV7
├── SOLAR / ENERGY            Solar9
├── TECHNOLOGY                PRIME
├── LEARNING / SUPPORT        SKH
└── HOLDING / INVESTMENT      Novus Integration · COM7 Holding
```

---

## Brands

| กลุ่ม | แบรนด์ |
|---|---|
| ค้าปลีก IT | BaNANA · Studio7 · U.Store · BaNANA Mobile · BKK · KingKong Phone · BaNANA Equip · BaNANA Outlet · Bb · B-Play · Bb-Move |
| บริการ / โทรคมนาคม | iCare · Smart Care · TRUE by COM7 |
| การเงิน | **UFUND** |
| EV | **EV7** |
| Solar | Solar9 |
| เทคโนโลยี | PRIME |
| ประกัน | iCare Insurance |

**ช่องทางออนไลน์:** BNN.IN.TH · Studio7.com

---

## ⚠️ คำที่สับสนบ่อย

| คำ | หมายถึง |
|---|---|
| **iCare** | ศูนย์ซ่อม/หลังการขาย **เฉพาะ Apple** |
| **Smart Care** | ศูนย์ซ่อม/หลังการขาย **ยี่ห้ออื่น** — ธุรกิจเดียวกับ iCare แบ่งตามยี่ห้อ |
| **iCare Insurance** | **บริษัทประกันภัย** — คนละธุรกิจกัน |
| **UFUND** | **แบรนด์** ธุรกิจเช่าซื้อ |
| **TFF / Thunder FinFin** | **นิติบุคคล**ที่ดำเนินธุรกิจ UFUND |
| **Studio7** | ค้าปลีก **Apple** เป็นหลัก |
| **BaNANA** | ค้าปลีก IT ทั่วไป รายใหญ่ที่สุด |

---

## ธุรกิจที่ตัดออกจาก reference ปัจจุบัน

**Dr.Pharma · 4Paws · PetPaw** — ห้ามนำมารวมในโครงสร้างธุรกิจปัจจุบัน เว้นแต่ถามถึงบริบทย้อนหลังโดยตรง

---

## Source system mapping

| ธุรกิจ | ระบบต้นทาง | สถานะ |
|---|---|---|
| ค้าปลีก · Apple / Studio7 | **ITEC** | สำคัญ · ใช้งานปัจจุบัน |
| UFUND / Thunder FinFin | **K2** · **ITOS** | สำคัญ · legacy |
| EV / EV7 | **GIcore** · **EV Core** | สำคัญ · ใช้งานปัจจุบัน |
| ประกัน · บริการ · B2B · ออนไลน์ · Adept · Solar9 · PRIME · SKH · 7Club · CRM · ERP | **TBD** | รอข้อมูล |

> **ห้ามเดาชื่อฐานข้อมูลให้ธุรกิจที่เป็น TBD** — รอจนกว่าจะมีการยืนยันจากเจ้าของระบบ

รายละเอียดแต่ละระบบ → [[System Inventory]]

---

## Master data hierarchy ที่แนะนำ

```
COM7 GROUP
├── Legal Entity ── Operating Company / Holding Company
├── Business Domain
├── Business Unit
├── Brand
├── Store / Channel
├── Product
└── Customer
```

**อย่าใช้ Brand = Company เป็นกฎทั่วไป**

---

## Data domains สำหรับ Data Lake / SSOT

Customer · Product · Sales · Store · Order · Payment · Finance · Contract · Insurance ·
Service · Vehicle · Rental · Energy · Employee · Supplier · Dealer · Campaign ·
Membership · Customer Interaction

---

## เชื่อมกับโน้ตอื่น

[[Home]] · [[System Inventory]] · [[UFUND]] · [[Retail]] · [[EV Business]] · [[Customer Identity]] · [[iCare Insurance (ICI)]]
