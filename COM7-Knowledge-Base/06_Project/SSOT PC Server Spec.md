# SSOT PC Server Spec

เครื่องเก็บข้อมูล SSOT แทน AWS ([[Decisions|D-21]]) · ฐานข้อมูล **MySQL** · สั่งซื้อ 2026-11 (ราคาอ้างอิงตลาดกลาง) → [[Current Status]]

---

## สเปกที่สั่ง

| ส่วน | รุ่น | ราคา (บาท) |
|---|---|---|
| CPU | Intel Core Ultra 5 245K · 14 คอร์ / 14 เธรด · LGA-1851 | 6,900 |
| Cooler | DeepCool LE720 360 mm (น้ำ) | 1,990 |
| Mainboard | ASUS TUF Gaming Z890-Plus WiFi · DDR5 | 10,900 |
| RAM | Corsair Vengeance DDR5 **128 GB** (2×64) 6000 MHz | 98,890 |
| SSD (OS) | Samsung 990 Pro **1 TB** NVMe | 9,690 |
| SSD (ข้อมูล) | Samsung 990 Pro **4 TB** NVMe | 33,100 |
| PSU | Cooler Master MWE Gold 750 W V3 | 2,290 |
| Case | Montech Air 903 Base (E-ATX) | 1,990 |
| LAN | TP-Link TX201 2.5 GbE PCIe | 590 |
| OS | Windows Server 2025 (สิทธิ์ 16 คอร์) | 39,990 |
| **รวม** | | **206,330** |

---

## เทียบกับขนาดข้อมูลที่วัดไว้

| ข้อมูล | ขนาดที่วัด | ที่มา |
|---|---|---|
| K2 + ITOS | ~89 GB (ตาราง ไม่รวม index) | [[K2 + ITOS - Storage Sizing]] |
| D365 F&O | ~234 GB (SQL ไม่รวม index · ส่วนสรุป `vtb_*` 130 GB สร้างใหม่ได้) | [[D365 F&O - Storage Sizing]] |
| ITEC ยอดขาย `fact_sales_itec` | 81M แถว · ~10 GB parquet | [[AWS Data Lake - Pipeline & Data Layers]] |
| CRM members | ~8–22M แถว | [[CRM Customer Field Survey]] |

ประมาณการรวม bronze + silver + gold + index ใน MySQL ≈ **1–1.5 TB** `[อนุมาน — InnoDB ใหญ่กว่า parquet หลายเท่า และเก็บหลายชั้น]` → **SSD 4 TB พอสำหรับเริ่ม** · RAM 128 GB พอให้ `innodb_buffer_pool_size` ~80–96 GB

---

## ข้อสังเกต / ความเสี่ยง

| เรื่อง | ทำไม | ทางแก้ |
|---|---|---|
| **ข้อมูลอยู่บน SSD ลูกเดียว ไม่มี RAID / สำเนา** | SSD เสีย = ข้อมูลหาย | เพิ่ม SSD 4 TB อีกลูกทำ mirror (Storage Spaces) **หรือ** มีที่ backup แยก (NAS / HDD ภายนอก) + ทดสอบกู้คืน |
| **ไม่มี UPS** | ไฟดับระหว่างเขียน = ตาราง InnoDB เสียหายได้ | UPS ~1,000–1,500 VA + ตั้งให้ shutdown อัตโนมัติ |
| **ไม่มีแผน backup** | เดิมพึ่ง S3 versioning | `mysqldump` / MySQL Shell dump ทุกคืน → ที่เก็บนอกเครื่อง · เก็บหลายรุ่น |
| เมนบอร์ด/การ์ดแลนเป็นของ consumer บน **Windows Server** | driver แลน/WiFi ของบอร์ด desktop มักไม่รองรับ Windows Server อย่างเป็นทางการ | ตรวจ driver ของ LAN บนบอร์ดและ TX201 กับ Windows Server 2025 ก่อนลงเครื่อง `[ควรเช็ก]` |
| License Windows Server | นอกจาก core license อาจต้องมี **CAL** ตามจำนวนผู้ใช้/เครื่องที่เข้าถึง | ถามฝ่ายจัดซื้อ/IT `[ควรเช็ก]` · ทางเลือก: Ubuntu Server (ฟรี ใช้กับ MySQL บ่อยกว่า) |
| RAM ไม่ใช่ ECC | ข้อมูลผิดเงียบ ๆ ได้ (โอกาสต่ำ) | รับได้สำหรับระยะแรก · ตรวจผลด้วยการ reconcile นับแถว/ยอดรวมกับต้นทาง |
| ไม่มี GPU | ไม่จำเป็นกับ MySQL | งานโมเดล (เช่น ITEC category) ใช้ Kaggle/Colab ต่อ |

---

## ยังไม่รู้

- เครื่องวางที่ไหน (ห้อง server / ห้องทำงาน) · ใครเข้าถึงทางกายภาพได้
- MySQL เวอร์ชัน (8.0 / 8.4 LTS) · แยก database ตามชั้น bronze / silver / gold
- เครื่องอยู่ในวงแลนเดียวกับ SQL Server ต้นทาง (ITEC 250 · K2) ไหม
- ใครดูแลเครื่อง (patch · backup · เฝ้าดูดิสก์)

[[Current Status]] · [[Open Questions & Risks]] · [[Medallion Layer Definition]] · [[Consent & PDPA]]
