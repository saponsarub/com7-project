# Google Sheet to S3 - Code Walkthrough

> **ย้ายแล้ว 2026-09-07** — คำอธิบายโค้ดทีละฟังก์ชันย้ายไปอยู่ในรีโปแทน เพื่อให้เอกสารอยู่ติดกับโค้ดและอัปเดตพร้อมกัน
>
> **`docs/googlesheet-to-s3.md`**

vault เก็บเฉพาะ**ความรู้ที่ใช้ซ้ำได้** ส่วนรายละเอียดที่ผูกกับโค้ดเวอร์ชันหนึ่ง ๆ อยู่ในรีโป — ไม่งั้นแก้โค้ดแล้วโน้ตจะเก่าโดยไม่มีใครรู้

---

## ไฟล์อยู่ที่ไหน

|                      |                                                       |
| -------------------- | ----------------------------------------------------- |
| โค้ด                 | `scripts/lambda/googlesheet-to-s3/lambda_function.py` |
| เอกสารทีละฟังก์ชัน   | `docs/googlesheet-to-s3.md`                           |
| สคริปต์ดูหน้าตาอีเมล | `scripts/lambda/googlesheet-to-s3/make_preview.py`    |
| build script         | `build-lambda.ps1` (เครื่อง)                          |
| zip ที่ build แล้ว   | `dist/com7-ingest-googlesheet-ev7-v*.zip` (เครื่อง)   |

## ความรู้ที่ยังอยู่ใน vault

| อยากรู้                                   | เปิด                            |
| ----------------------------------------- | ------------------------------- |
| pipeline นี้ทำอะไร · ข้อตัดสินใจ · กับดัก | [[Google Sheet to S3 (Lambda)]] |
| ทำไมต้อง build บน Linux · packaging       | [[Google Sheet to S3 (Lambda)]] |
| ทำไมหนึ่ง tab = หนึ่งโฟลเดอร์             | [[Glue Crawler]]                |
| ภาพรวมโปรเจกต์ · roadmap · ค่าใช้จ่าย     | [[Google Sheet Pipeline]]       |
| ข้อกำหนด log ที่ทีมตกลง (D-15)            | [[ETL & Spark]] · [[Decisions]] |
| งานที่ยังค้าง                             | [[Pipeline Issues]]             |

---

## เชื่อมกับโน้ตอื่น

[[Google Sheet to S3 (Lambda)]] · [[Google Sheet Pipeline]] · [[Glue Crawler]] · [[ETL & Spark]] · [[Pipeline Issues]]
