# ITEC Overview

ระบบค้าปลีกของ COM7 (BaNANA · Studio7 · KingKong · BKK · iCare · TRUE by COM7 ฯลฯ) → [[Retail]]
**ข้อมูล ITEC มี 2 ฐาน — คนละเครื่อง คนละโครงสร้าง อย่าปนกัน**

| | **ITEC-Rep** ⭐ ตัวหลัก | **ITEC-MIS** |
|---|---|---|
| คืออะไร | replica ของระบบ ITEC ทั้งระบบ — **ตารางดิบ** | ฐาน MIS ที่ทีมสร้าง **view สรุป/ทำความสะอาด** ไว้แล้ว |
| Server · ฐาน | `10.100.101.50` · `SSSynced50` | `192.168.43.250,18963` · `_db1_3f9c2a7e-8b41-4d6f-9c25-1a7e5c0d2b8f` |
| DBMS | SQL Server 2017 | SQL Server 2025 |
| เห็นอะไร | 472 ตาราง + 8 view ใน `dbo` (`Sell` · `SellItem` · `Product` · `Branch` · `Customer2` …) | 23 view ใน `rpt` (14) · `ci` (13) — ไม่มี table |
| ความสด | เกือบ real-time (ห่างไม่กี่นาที) | ตามรอบ refresh ของ view `[ไม่รู้รอบที่แน่นอน]` |
| ช่วงข้อมูล | บิลตั้งแต่ 2007-03 | ยอดขายตั้งแต่ 2023 (`rpt.fact_sales_itec`) |
| ลูกค้า | `Customer2` — ตัดข้อมูลส่วนบุคคลเหลือ `CusCode` · `Name` · `CRMID` | `rpt.dim_mem_itec` |
| profile ใน `scripts/db.py` | **`itec`** · env `ITEC_USER` / `ITEC_PWD` | **`itec_mis`** · env `MIS_USER` / `MIS_PWD` |
| โน้ต | [[ITEC-Rep Overview]] | [[ITEC-MIS Overview]] · [[ITEC-MIS - Data Dictionary]] · [[ITEC-MIS - Query Cookbook]] |

## ใช้ตัวไหนเมื่อไร

- **งานใหม่ / pipeline เข้า SSOT (MySQL)** → **ITEC-Rep** — ข้อมูลครบและสด แต่ต้องสร้างนิยามยอดขาย สินค้า สาขาเองจากตารางดิบ
- **ต้องการตัวเลขตามนิยามที่ทีมใช้อยู่แล้ว** (ยอดขาย · หมวดสินค้า `ci.clean_item_category_itec` · สาขา `ci.clean_branch`) → **ITEC-MIS**
- งานเดิมที่เขียนบน view `rpt.*` / `ci.*` (booking · category · warehouse) ใช้ **ITEC-MIS** — สคริปต์ใน `scripts/itec/`, `scripts/fo/` เรียก profile `itec_mis`
- ตารางเทียบ view ของ ITEC-MIS ↔ ตารางดิบของ ITEC-Rep → [[ITEC-Rep Overview#เทียบกับ ITEC-MIS]]

## เชื่อมกับระบบอื่น

- CRM: `members.itec_cuscode` = **ITEC-Rep** `Customer2.CusCode` (สุ่ม 20,000 ตรง 100%) → [[CRM - Data Dictionary]]
- เรื่องจัดหมวดสินค้า → [[ITEC Product Dimension]] · [[ITEC Item Category Mapping (SQL to Python)]]
- ปัญหาข้อมูล → [[ITEC Issues]]

[[System Inventory]] · [[Current Status]] · [[CRM Overview]]
