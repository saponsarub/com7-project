# Thai Administrative Dimension

ตาราง dimension ที่อยู่ไทย — **จังหวัด 77 · อำเภอ/เขต 928 · ตำบล/แขวง 7,426** · รหัส 2/4/6 หลัก + ชื่อไทย + ชื่ออังกฤษ + ภาค
ใช้ทำมาตรฐานที่อยู่ข้ามระบบ (K2 · ITOS · CRM `district`/`subdistrict` · ITEC `Branch.Province/District`) → [[Data Standardization & Quality]]

> โน้ตนี้สรุปจาก docstring ของสคริปต์ (2026-11-10) — รายละเอียดกับดักการแปลง PDF อยู่ในโค้ด

| | |
|---|---|
| สร้างด้วย | `python scripts/geo/thai_admin_from_pdf.py` แล้ว `python scripts/geo/thai_admin_dim.py` |
| ตัวตั้ง | `ชื่อจังหวัดอำเภอตำบล.pdf` (ราชบัณฑิตยสภา) — ชื่อไทย + อังกฤษครบทุกแถว |
| ตัวเสริม | `provincecode.pdf` — เอาเฉพาะรหัส · จับคู่ไม่ได้ปล่อย NULL ไม่เดา (ไฟล์รหัสเก่ากว่า ขาดบึงกาฬ มีรายการที่ยุบแล้ว) |
| ผลลัพธ์ | `scripts/geo/_out/` — `dim_province.csv` · `dim_district.csv` · `dim_subdistrict.csv` · `dim_admin_flat.csv` · `thai_admin_dim.xlsx` · `thai_admin_dim.sql` (CREATE TABLE + FK) · `no_code.csv` (จับคู่รหัสไม่ได้) |
| ใช้กับ MySQL | `thai_admin_dim.sql` เขียนแบบ SQL Server (`nvarchar`) — ต้องแปลงชนิดเป็น `VARCHAR … utf8mb4` ก่อนลงเครื่อง SSOT `[อนุมาน]` |

กับดักที่แก้ไว้แล้วในโค้ด: ฟอนต์เก็บวรรณยุกต์ใน Private Use Area · ไม่มีช่องว่างทั้งเล่ม (แยกคอลัมน์ด้วยชนิดอักขระ) · สระอำแยกส่วน · รหัส `00`/`99` เป็น placeholder / ตำบลที่ยุบ (เก็บไว้พร้อมธง)

[[ITOS - Address & Geography]] · [[ITOS Flood Waiver 2026-09]] · [[Customer Identity]]
