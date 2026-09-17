# Environment Setup

> **หมายเหตุที่มา:** รายการทั้งหมดมาจากการ**สแกน import จริง**ในโปรเจกต์ `my-first-project` และอ่านเวอร์ชันที่ติดตั้งอยู่บนเครื่อง `Sapon.S` เมื่อ **2026-09-17** ไม่ได้เขียนจากความจำ
> library ที่ไม่มีใครเรียกใช้จริง (`matplotlib` · `SQLAlchemy`) **ไม่ได้ใส่ไว้** แม้จะติดตั้งอยู่บนเครื่องเดิม
>
> ไฟล์จริง: `requirements.txt` · `requirements-ml.txt` ที่ราก repo

---

## ติดตั้งแบบสั้นที่สุด

```powershell
git clone git@github.com:saponsarub/com7-project.git
cd com7-project

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

แค่นี้ใช้ได้เลย — ต่อฐานข้อมูล · จัดหมวดสินค้า ITEC ด้วยกฎ · สร้างพื้นหลัง Power BI

จะรันส่วน ML ค่อยเติมทีหลัง (หนักอีก ~2.5 GB)

```powershell
pip install -r requirements-ml.txt
```

---

## 3 อย่างที่ `pip` ลงให้ไม่ได้

### 1 · ODBC Driver 18 for SQL Server

`pyodbc` เป็นแค่สะพาน **ตัว driver ต้องลงแยก** ไม่มีแล้วต่อฐานไม่ได้เลย

ดาวน์โหลดจาก Microsoft → `msodbcsql18.msi`

ตรวจว่าลงแล้วหรือยัง

```powershell
python -c "import pyodbc; print(pyodbc.drivers())"
```

ต้องเห็น `ODBC Driver 18 for SQL Server` ในรายการ

> เครื่อง `Sapon.S` มี `SQL Server` (ตัวเก่า) อยู่ด้วย **อย่าใช้ตัวนั้น** — `db.py` ระบุ Driver 18 ไว้ตายตัว

### 2 · ฟอนต์ไทยสำหรับวาดพื้นหลัง Power BI

`Powerbi/_design/make_bg.py` เรียกฟอนต์จาก `C:\Windows\Fonts\` ตรง ๆ

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `leelauib.ttf` | Leelawadee UI **Bold** — หัวเรื่อง |
| `LeelawUI.ttf` | Leelawadee UI Regular — คำอธิบาย |

Windows มีมาให้อยู่แล้ว · **แต่บน Linux/Mac ต้องแก้ path ในสคริปต์**

### 3 · Power BI Desktop

ต้องเป็น **Windows** เท่านั้น · เวอร์ชันที่ทดสอบแล้ว `2.156.951.0 (July 2026)`

เปิด preview 2 ตัวนี้ก่อน ไม่งั้นเปิด `.pbip` ไม่ได้ — `File ▸ Options ▸ Preview features`

```
PBI_tmdlInDataset
PBI_enhancedReportFormat
```

รายละเอียดการแก้ `.pbip` → [[Power BI PBIP Cookbook]]

---

## ตัวแปรสภาพแวดล้อม

**มี 2 ฐานข้อมูล คนละรหัสผ่าน** — `scripts/db.py` อ่านจาก env เท่านั้น

> [!danger] ห้ามเขียนรหัสผ่านลงไฟล์ใด ๆ ในโปรเจกต์
> `.env` ถูกใส่ `.gitignore` ไว้แล้ว แต่วิธีที่ใช้จริงคือตั้งเป็น **User environment variable** ของ Windows ไม่ใช่ไฟล์

| ตัวแปร | ต้องตั้งไหม | ค่าถ้าไม่ตั้ง |
|---|---|---|
| `MIS_USER` `MIS_PWD` | **ต้องตั้ง** | — ต่อไม่ได้ |
| `K2_USER` `K2_PWD` | **ต้องตั้ง** | — ต่อไม่ได้ |
| `MIS_SERVER` `MIS_DB` | ไม่ต้อง | มี default ใน `db.py` |
| `K2_SERVER` `K2_DB` | ไม่ต้อง | มี default ใน `db.py` |

ตั้งแบบถาวร (ติดค้างข้ามการ reboot)

```powershell
[Environment]::SetEnvironmentVariable("MIS_USER", "ชื่อผู้ใช้", "User")
[Environment]::SetEnvironmentVariable("MIS_PWD",  "รหัสผ่าน",  "User")
[Environment]::SetEnvironmentVariable("K2_USER",  "ชื่อผู้ใช้", "User")
[Environment]::SetEnvironmentVariable("K2_PWD",   "รหัสผ่าน",  "User")
```

ค่าไปอยู่ใน registry `HKCU:\Environment` · **ต้องปิดเปิด terminal ใหม่** ถึงจะเห็น

ตรวจว่าต่อได้จริง — คำสั่งนี้พิมพ์แค่ชื่อผู้ใช้ ไม่พิมพ์รหัสผ่าน

```powershell
python scripts\db.py
```

---

## เวอร์ชันที่ยืนยันแล้วว่าใช้ได้

```
python                  3.14.6
pandas                  3.0.3
numpy                   2.4.6
pyarrow                 23.0.1
PyYAML                  6.0.3
pyodbc                  5.3.0
openpyxl                3.1.5
pillow                  12.3.0
jupyterlab              4.5.9
ipykernel               7.3.0
boto3                   1.43.86
google-api-python-client 2.200.0
google-auth             2.57.0

── เฉพาะส่วน ML ──
scikit-learn            1.9.0
sentence-transformers   6.0.1
transformers            5.16.1
torch                   2.14.0
joblib                  1.5.3
datasets                ยังไม่ได้ลง — notebook จะ pip ให้เองตอนรัน Cell 8.3
accelerate              ยังไม่ได้ลง — เหมือนกัน
```

> [!warning] **pandas 3 ไม่เหมือน pandas 2**
> pandas 3 ใช้ Arrow/RE2 เป็น regex engine · `\w` กับ `\s` เป็น **ASCII ล้วน**
> ผลคือภาษาไทยกับ `\xa0` (NBSP) ไม่โดนจับ ทั้งที่ Python `re` ปกติจับได้
>
> ในโค้ดจึงต้องเขียน `ก-๛` เป็นอักษรไทยจริง **ห้ามใช้ `\u0E00` เพราะ RE2 ไม่รองรับ**
> เคยพลาดมาแล้ว — ภาษาไทยหายทั้งคอลัมน์โดยไม่มี error สักตัว
>
> ถ้าไปรันบนเครื่องที่เป็น pandas 2 ผลจะไม่เหมือนกัน → [[ITEC Category Toolkit]]

---

## GPU — ต้องลง torch คนละแบบ

`requirements-ml.txt` ให้ **torch ตัว CPU**

เครื่องมี NVIDIA GPU อย่าลงจากไฟล์นั้น ให้ลงตามคำสั่งของ pytorch.org แทน

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

เช็คว่า torch เห็น GPU ไหม

```python
import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
```

**ไม่มี GPU ก็รันได้** — notebook สลับ backbone ให้เอง

| | มี GPU | ไม่มี GPU |
|---|---|---|
| backbone | `BAAI/bge-m3` (~2.3 GB) | `paraphrase-multilingual-MiniLM-L12-v2` (~470 MB) |
| encode 216k แถว | ไม่กี่นาที | **~4 ชั่วโมง** |
| fine-tune (Cell 8.3) | ได้ | มี `assert` กันไว้ ไม่ให้รัน |

CPU แล้วอยากลองเร็ว ๆ ให้ลดขนาดก่อน — `work = work.sample(20000)`

---

## รันบน Colab / Kaggle แทน

`itec_dimension.ipynb` ตรวจสภาพแวดล้อมเองใน Cell 2 **ไม่ต้องแก้โค้ด**

```python
IN_COLAB  = "google.colab" in sys.modules
IN_KAGGLE = Path("/kaggle/input").exists()
ENV = "colab" if IN_COLAB else "kaggle" if IN_KAGGLE else "local"
```

มันจะ `pip install` เฉพาะตัวที่ขาด และแตกไฟล์ `.zip` / `.csv.gz` ให้เอง

ต้องอัปขึ้นไป 2 อย่าง

```
dimension.py            สร้าง zip ด้วย  python scripts/itec/dimension/make_zip.py
dim_item_itec.csv.gz    6 MB  อยู่ใน _data/ (ไม่ขึ้น git)
```

> `rules.yaml` **ไม่ต้องอัป** — Cell 3 เขียนขึ้นมาใหม่เองทุกครั้ง

Kaggle T4 ฟรี 30 ชม./สัปดาห์ · เหมาะกับ fine-tune ที่สุด

---

## ไฟล์ที่ไม่ได้อยู่ใน git ต้องหามาเอง

`.gitignore` บล็อก `*.csv` `*.xlsx` `_data/` `_out/` ไว้ เพราะอาจมี PII

| ไฟล์ | เอามาจากไหน |
|---|---|
| `scripts/itec/dimension/_data/dim_item_itec.csv` | export จาก `rpt.dim_item_itec` · 216,009 แถว · 37 MB |
| `scripts/itec/dimension/_out/*` | สร้างใหม่ได้จากโน้ตบุ๊ก ไม่ต้องหา |
| `Powerbi/**/.pbi/cache.abf` | กด Refresh ใน Power BI สร้างใหม่ |

---

## เช็กว่าพร้อมจริงไหม

```powershell
# 1 · library ครบ
python -c "import pandas, numpy, yaml, pyodbc, PIL; print('ok', pandas.__version__)"

# 2 · ODBC driver
python -c "import pyodbc; print('ODBC Driver 18 for SQL Server' in pyodbc.drivers())"

# 3 · ต่อฐานได้ทั้ง 2 ตัว
python scripts\db.py

# 4 · กฎ ITEC ทำงาน
python -c "import sys; sys.path.insert(0,'scripts/itec/dimension'); import dimension as D; print(len(D.load_rules(D.RULES_FILE)), 'ตารางกฎ')"

# 5 · วาดพื้นหลัง Power BI ได้
cd Powerbi\_design; python make_bg.py
```

ผ่านครบ 5 ข้อ = พร้อมทำงาน

---

## ดูเพิ่ม

- [[Power BI PBIP Cookbook]] — แก้ `.pbip` ด้วยโค้ด · กับดัก TMDL/DAX
- [[Python Libraries]] — library ไหนใช้ทำอะไร เลือกยังไง
- [[Git & GitHub]] — SSH 2 บัญชี · ตอน push ไม่ผ่าน
- [[ITEC Category Toolkit]] — กับดัก pandas 3 แบบเต็ม
- [[ITEC Model - Run on EC2 Guide]] — ถ้าจะไปรันบน EC2 แทน
