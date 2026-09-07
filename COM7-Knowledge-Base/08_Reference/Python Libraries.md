# Python Libraries

> **รายละเอียดอยู่ในรีโป: `docs/libraries.md`** — ทุก library ที่ pipeline ใช้ พร้อมลิงก์เอกสาร ฟังก์ชันสำคัญ (ทั้งที่ใช้และยังไม่ได้ใช้) และกับดักของแต่ละตัว

โน้ตนี้เก็บเฉพาะ**หลักที่ใช้ตัดสินใจ** ซึ่งใช้ซ้ำกับ pipeline อื่นได้

---

## หลักเลือก library

| หลัก | เหตุผล |
|---|---|
| **stdlib ทำได้ อย่าเพิ่มของ** | `urllib` แทน `requests` ทำให้ zip เล็กลงและไม่มี dependency ให้ดูแล |
| **boto3 ไม่ต้องแพ็ก** | Lambda/Glue มีให้อยู่แล้ว · แพ็กเองเมื่อต้องการเวอร์ชันเจาะจงเท่านั้น |
| **เช็ค native code ก่อนเพิ่ม** | ชื่อ wheel ลงท้าย `-any.whl` = ย้ายข้ามเครื่องได้ · มีชื่อ OS = ต้อง build ให้ตรง → [[Google Sheet to S3 (Lambda)]] |
| **ใส่ `timeout=` ทุกการเรียกเครือข่าย** | ไม่ใส่แล้วจะตายเพราะหมดเวลาแทนที่จะได้ error ที่อ่านรู้เรื่อง |

## library ที่ pipeline ปัจจุบันใช้

| ชั้น | library |
|---|---|
| stdlib | `json` `csv` `io` `os` `time` `datetime` `urllib` `email` |
| AWS | `boto3` (ไม่ต้องแพ็ก) |
| Google | `google-auth` |
| ติดมาด้วย | `cryptography` `cffi` `pycparser` `pyasn1` `pyasn1_modules` `requests` `urllib3` `certifi` `idna` `charset_normalizer` |

**`cryptography` เป็นตัวที่บังคับให้ต้อง build บน Linux** — มีโค้ด Rust/C คอมไพล์แล้ว ผูกกับ OS และเวอร์ชัน Python · `google-auth` เรียกใช้ตอนเซ็น JWT จึงตัดออกไม่ได้

## ตัวเลือกสำหรับงานถัดไป

| ต้องการ | library | ข้อควรรู้ |
|---|---|---|
| ต่อ SQL Server จาก Lambda | **`pymssql`** | มี manylinux wheel พร้อม FreeTDS ในตัว · `pyodbc` ต้องมี ODBC Driver 18 ระดับ OS ด้วย zip ธรรมดาไม่พอ ต้องใช้ container → [[K2 Termination Automation]] |
| เขียน Parquet | `pyarrow` | ไม่ต้องลาก pandas มาด้วย |
| อ่าน/เขียน xlsx | `openpyxl` | `k2_termination.py` ใช้อยู่ |
| คุยกับ Google Sheets แบบสั้น | `gspread` | **ไม่ได้ทำให้ zip เล็กลง** ลาก `google-auth` → `cryptography` มาเหมือนกัน |

---

## เชื่อมกับโน้ตอื่น

[[Google Sheet to S3 (Lambda)]] · [[Google Sheet Pipeline]] · [[ETL & Spark]] · [[K2 Termination Automation]] · [[Glue Crawler]]
