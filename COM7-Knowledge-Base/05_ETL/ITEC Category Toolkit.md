# ITEC Category Toolkit

> **จุดเริ่มต้นของงานจัดหมวดสินค้า ITEC ทั้งหมด** — ทุกไฟล์อยู่ที่ `scripts/itec/category/`
> อัปเดต 2026-09-14 · ต่อจาก [[ITEC Item Category Mapping (SQL to Python)]] · [[ITEC Category Model (ML)]] · [[ITEC Flag & Category Review Guide]]

---

## โฟลเดอร์เดียว จบทุกอย่าง

```
scripts/itec/
│
├── category/                               ◄── งานหลัก จัดหมวด
│   ├── itec_recategorization.ipynb         ◄── เริ่มที่นี่ · แก้กฎที่ Cell 4
│   ├── type_platform.py   type_platform.yaml    ระบบ B "หมวดใหม่"
│   ├── itec_mapper.py     item_keywords.yaml    ระบบ A "สะท้อน SQL"
│   ├── rules.py
│   ├── predict_all.py     explore_flags.py      สคริปต์ทำงาน
│   ├── benchmark_models.py  reconcile.py
│   ├── export_items.py    extract_keywords.py   เตรียมของ
│   ├── make_zip.py        itec_category_scripts.zip
│   ├── _data/  dim_item_itec.csv (36 MB) · .csv.gz (5.8 MB)
│   └── _out/   ผลลัพธ์ทุกไฟล์
│
└── finetune/                               ◄── แยกขาด · ปรับ backbone
    ├── finetune_notebook.ipynb
    ├── finetune.py
    ├── sync_rules.py                       ดึงกฎจาก ../category + build zip
    ├── type_platform.py  .yaml             **สำเนา ห้ามแก้**
    ├── itec_finetune_scripts.zip
    └── _data/  _out/
```

**`finetune/` แยกออกมาเพราะเป็นคนละงาน** — ที่นั่นปรับ backbone ที่นี่จัดหมวด
กฎยังมีที่เดียวคือ `category/` · `sync_rules.py` คัดลอกมาตอน build → [[ITEC Model - Fine-tune Design]]

**โน้ตบุ๊กรันได้ 3 ที่ด้วยไฟล์เดียว** — Cell 1 ตรวจเองว่า local / Colab / Kaggle

**`_data/` และ `_out/` ไม่ขึ้น git** — `.gitignore` กัน `*.csv` ไว้อยู่แล้ว

---

## มี 2 ระบบ ทำคนละเรื่อง — ต้องแยกให้ออกก่อน

```
                      ┌─ ระบบ A "สะท้อน SQL" ────────► 5 คอลัมน์เดิม
ItemName ─────────────┤
                      └─ ระบบ B "หมวดใหม่" ──────────► Case iPhone
```

| | **A · สะท้อน SQL** | **B · หมวดใหม่** |
|---|---|---|
| กฎอยู่ที่ | `item_keywords.yaml` + `rules.py` | **notebook Cell 4** (เขียนลง `type_platform.yaml`) |
| ได้อะไร | `Sale_Type` · `Product_Dimension` · `Product_Purpose` · `Main_Product_Dimension` · `Sub_Product_Dimension` | `Item_Type` · `Item_Platform` · `Type_Platform` |
| ไว้ทำอะไร | **เทียบกับ production ว่าตรงไหม** | **ของที่จะใช้จริงต่อไป** |
| ต้องแก้ไหม | ❌ ไม่ต้อง เว้นแต่ SQL เปลี่ยน | ✅ **นี่คือที่ต้องแก้** |

**A บอกว่า "ของเดิมเป็นยังไง" · B บอกว่า "อยากให้เป็นยังไง"** — ต้องมีทั้งคู่ถึงจะพิสูจน์ได้ว่าเปลี่ยนแล้วดีขึ้น

---

## ระบบ A · สะท้อน SQL — 3 ชั้น

```
ItemName + CategoryName + SubCategoryName
   │  ต่อเป็น search_text คั่นด้วย " | "
   ▼
item_keywords.yaml   67 flag · 76 keyword       ◄── ดึงจาก SQL อัตโนมัติ
   │  IS_iPhone=1 · IS_Case=1 · ...
   ▼
rules.py             main_rules() เรียงลำดับ    ◄── ตัวแรกที่ตรงชนะ
   │                 sub_rules()
   ▼
5 คอลัมน์
```

### ทำไมต้องต่อ 3 คอลัมน์เป็นข้อความเดียว

SQL เดิมทำ `LIKE` บน 3 คอลัมน์แบบ `OR` เหมือนกันทุก flag → **ยุบเหลือค้นครั้งเดียว 201 → 67 ครั้งต่อแถว**

**คั่นด้วย `|` ไม่ใช่ช่องว่าง** — กันคำจากคนละคอลัมน์ต่อกันเป็นคำใหม่ เช่น `power` + `bank`

### ลำดับใน `main_rules()` คือหัวใจ

```python
("Smart Phone", IS_Smartphone | IS_Mobile | IS_Galaxy | IS_iPhone),
("Tablet",      IS_iPad | IS_Tablet),
...
```

`np.select` = `CASE WHEN` ของ pandas **เงื่อนไขแรกที่จริงชนะ** เหมือน SQL เป๊ะ

### `strict=True` เป็นค่าเริ่มต้น

| | `strict=True` | `strict=False` |
|---|---|---|
| `whole_word` | ❌ ปิด | ✅ เปิด |
| บั๊ก PC/Notebook | คงไว้ | แก้ |
| ใช้ตอน | **พิสูจน์ว่าทำเหมือนเดิมได้** | ดูว่าแก้แล้วต่างกี่แถว |

**ต้องได้ 0% ต่างตอน strict ก่อน ถึงจะมีสิทธิ์บอกว่าที่ต่างทีหลังคือของที่ดีขึ้น**

---

## ระบบ B · หมวดใหม่ — 2 ชั้น

```
ItemName
   │
   ├─ TYPES        20 ประเภท   ► Item_Type      Case · PC Case · Charger · Device
   ├─ PLATFORMS    22 แบรนด์   ► Item_Platform  iPhone · Galaxy · Asus · Generic
   │
   ├─ DISAMBIGUATE            ► แก้ความกำกวม
   ▼
Type_Platform = "Case iPhone"
```

### ต่างจากระบบ A ตรงลำดับความสำคัญ

```
ระบบ A   iPhone 15 Case  ►  Main "Smart Phone" / Sub "Smart Phone Case"
ระบบ B   iPhone 15 Case  ►  "Case iPhone"
```

**ระบบ A ให้ระบบนิเวศชนะ · ระบบ B ให้ประเภทชนะ** — ตอบคนละคำถาม

| อยากรู้ | ใช้ |
|---|---|
| iPhone สร้างรายได้เท่าไหร่รวมของเสริม | **ระบบ A** |
| ขายเคสไปกี่ชิ้น เคสของอะไรบ้าง | **ระบบ B** |

### ลำดับใน `TYPES` สำคัญมาก

```python
TYPES = [
    {"label": "Service",     ...},   # อะไหล่ต้องชนะเคส
    {"label": "PowerSupply", ...},   # ชิ้นส่วนคอมต้องชนะเคส
    {"label": "Case",        ...},   # ตกมาอยู่ล่าง
    ...
]
```

**`(Part) BACK HOUSING COVER IPHONE` จะกลายเป็นเคส ถ้า Service ไม่อยู่บนสุด**

### `DISAMBIGUATE` — ชั้นที่สอง

```python
{"from": "Case", "words": ["atx", "tower", "chassis"], "to": "PC Case"}
```

**ได้ `Case` แล้วค่อยถามว่าอยู่ในบริบทคอมไหม** — แยกเคสคอม (2,567) ออกจากเคสมือถือ (28,608)

### ชื่อสินค้าชนะหมวดเดิมเสมอ

```python
t = _first(ItemName, TYPES, "Device")
if context and t == "Device":          # ชื่อบอกไม่ได้ค่อยถามหมวดเดิม
    t = _first(context, TYPES, "Device")
```

**หมวดเดิมของ ITEC key ผิดเยอะ** ใช้เป็นตัวสำรองเท่านั้น พิสูจน์ได้จาก

```
Tengu Gaming Mouse Pad        SubCategory = "MOUSE & KEYBOARD & MOUSE PAD"
  → Mouse ✅  ไม่ใช่ Keyboard   (ชื่อชนะ)
```

---

## ✏️ ที่ต้องแก้เอง — มีที่เดียว

### `itec_recategorization_colab.ipynb` **Cell 4**

```python
TYPES = [
    {"label": "Case", "words": ["case", "เคส", "cover"], "whole_word": True},
    ...
]
PLATFORMS = [...]
DISAMBIGUATE = [...]
```

**รัน cell นี้แล้ว `type_platform.yaml` ถูกเขียนใหม่อัตโนมัติ** → สคริปต์ทุกตัวได้กฎชุดเดียวกันทันที

| อยากทำ | แก้ตรงไหน |
|---|---|
| เพิ่มคำ | เติมใน `"words"` |
| เพิ่มประเภทใหม่ | เพิ่มบรรทัด |
| **เปลี่ยนลำดับความสำคัญ** | **ย้ายบรรทัดขึ้นลง** |
| เปลี่ยนชื่อหมวดเป็นไทย | แก้ `"label"` |
| กันคำสั้นจับมั่ว | `"whole_word": True` |
| ลดจำนวน label | ลบแบรนด์ออกจาก `PLATFORMS` |

**Cell 5 ทดสอบให้เห็นผลใน 1 วินาที** — แก้กฎแล้วรัน Cell 5 ไม่ต้องรอ embed 30 นาที

### พารามิเตอร์อื่นในโน้ตบุ๊ก

| Cell | ตัวแปร | ค่า | ทำอะไร |
|---|---|---|---|
| 6 | `LABEL_COL` | `"Type_Platform"` | เลือก label ที่เทรน · `"Item_Type"` = หมวดน้อยกว่า |
| 7 | `data.sample(5000)` | comment ไว้ | **ปลด comment = เทสต์เร็ว** |
| 9 | `USE_SVC` | `True` | `False` = LogisticRegression |
| 12 | `Q` | `0.60` | เกณฑ์ตัด suspect |

---

## สคริปต์ทั้ง 8 ตัว

| ไฟล์ | ทำอะไร | ออกอะไร |
|---|---|---|
| `type_platform.py` | ระบบ B · `classify(name, context)` | 3 คอลัมน์ |
| `itec_mapper.py` | ระบบ A · `run(df, strict)` | flags + 5 คอลัมน์ |
| `rules.py` | กฎ Main/Sub ของระบบ A | — |
| **`predict_all.py`** | **ทำนาย flag ด้วย ML → เข้ากฎเดิม → 5 คอลัมน์ + 3 คอลัมน์** | `--out` ไฟล์ผล |
| **`explore_flags.py`** | **สำรวจว่าควรเพิ่ม/ลด flag ตัวไหน** | 4 ไฟล์ใน `_out/` |
| `benchmark_models.py` | เทียบ backbone / classifier / label | `_out/benchmark_result.csv` |
| `reconcile.py` | เทียบกับ SQL จริงทีละ `ItemId` | `category_diff.csv` |
| `export_items.py` | ดึงจาก SQL Server → CSV → S3 | `_data/` |
| `extract_keywords.py` | SQL → `item_keywords.yaml` | ⚠️ **เขียนทับของที่แก้เอง** |
| `make_zip.py` | รวมไฟล์เป็น zip ไว้อัป Colab/Kaggle | `itec_category_scripts.zip` ในโฟลเดอร์เดียวกัน |

รันได้เลยไม่ต้องใส่ path — default ชี้ `_data/dim_item_itec.csv` แล้ว

```bash
cd scripts/itec/category
python explore_flags.py
python predict_all.py -n 216009 --out _out/itec_categorized.csv
python benchmark_models.py --label Type_Platform -n 30000 --skip-embed
```

---

## `predict_all.py` — สถาปัตยกรรมที่สำคัญที่สุด

```
ItemName → TF-IDF → 50 binary classifier → flags → rules.py → 5 คอลัมน์
                                                    ↑ ไม่แตะเลย
```

**ML แทนที่แค่ขั้น keyword matching** — กฎที่เหลือเหมือนเดิม

### ทำไมไม่ทำนาย 5 คอลัมน์ตรง ๆ

| | ทำนายแยก 5 ตัว | **ทำนาย flag แล้วคำนวณต่อ** |
|---|---|---|
| ผลขัดกันเองได้ไหม | **ได้** — Main=`Tablet` แต่ Sub=`Smart Phone Case` | **ไม่มีทาง** |
| เพิ่มหมวดใหม่ | เทรนใหม่หมด | แก้ `rules.py` |

**พิสูจน์ได้จากผลรัน** — `แถวที่ Sub ขัดกับ Main: 0` เป็นศูนย์โดยโครงสร้าง ไม่ใช่โดยบังเอิญ

### `out-of-fold` ไม่ใช่เทรนแล้วทำนายตัวเอง

ทุกแถวถูกทำนายโดยโมเดลที่ไม่เคยเห็นแถวนั้น — **ถ้าเทรนทั้งก้อนแล้วทำนายทั้งก้อน ตัวเลขจะสวยเกินจริง**

### คอลัมน์ `differs` คือของที่มีค่าที่สุด

**ไม่ใช่ error แต่คือจุดที่ ML กับกฎเห็นไม่ตรงกัน** ซึ่งฝ่ายใดฝ่ายหนึ่งผิด — เอาไปให้คนตรวจ

---

## ตัวเลขที่วัดได้จริง

### ผลจัดหมวด 216,006 แถว

| | ค่า |
|---|---|
| ประเภท (`Item_Type`) | 20 |
| แบรนด์ (`Item_Platform`) | 23 |
| รวม (`Type_Platform`) | **294** |
| `Device` ไม่รู้ประเภท | 137,845 (63.8%) |
| `Case iPhone` | **10,252** |
| `PC Case` แยกออกจาก `Case` แล้ว | 2,567 |

### เทียบ classifier — 200,000 แถว label `Main_Product_Dimension`

| | accuracy | **f1_macro** | เวลา | `predict_proba` |
|---|---|---|---|---|
| **LinearSVC** | 0.9629 | **0.9519** | 115s | ❌ |
| LogisticRegression | 0.9522 | 0.9336 | 384s | ✅ |
| ComplementNB | 0.8705 | 0.8193 | 57s | ✅ |
| SGD log_loss | 0.8993 | 0.7757 | 89s | ✅ |

**LinearSVC ชนะ 1.8 จุด และเร็วกว่า 3.3 เท่า** · `sd=0.0005` ผลนิ่งมาก

### จำนวนข้อมูลสำคัญกว่าที่คิด

| | 5,000 แถว | 200,000 แถว |
|---|---|---|
| accuracy | 0.8730 | 0.9522 |
| **f1_macro** | 0.6922 | **0.9336** |

**f1 ขยับ +24 จุด ส่วน accuracy ขยับแค่ +8** — ปัญหาที่ 5,000 แถวคือ**ข้อมูลไม่พอ ไม่ใช่โมเดลไม่พอ**

### `predict_all` 5 คอลัมน์ (8,000 แถว)

| ตัวแปร | ตรงกับกฎเดิม | f1_macro |
|---|---|---|
| Sale_Type | 99.44% | 0.9790 |
| Product_Purpose | 99.31% | 0.9569 |
| Main_Product_Dimension | 93.00% | 0.9093 |
| Sub_Product_Dimension | 91.31% | 0.7974 |
| **Product_Dimension** | 91.19% | **0.6257** ⚠️ |

**`Product_Dimension` (Demo/Normal) ทำนายจากชื่อไม่ได้** — `demo` เป็นสถานะการขาย ไม่ใช่ลักษณะสินค้า · "iPhone 15 Demo" กับ "iPhone 15" ชื่อแทบเหมือนกัน
→ **3 flag นี้ (`IS_Promotion` `IS_Demo_Product` `IS_Gaming`) ควรใช้ keyword ต่อไป อย่าให้ ML ทำ**

---

## ⚠️ ข้อจำกัดที่ต้องรู้ก่อนตีความตัวเลข

**label มาจาก rule-based ที่เป็น keyword matching · TF-IDF ก็ทำงานด้วย character n-gram**

**0.93 แปลว่า "ถอดกฎ keyword เดิมกลับได้ 93%" ไม่ใช่ "จัดหมวดถูก 93%"**

ซึ่งขัดกับเป้าหมายอยู่กลาย ๆ — เป้าหมายคือแก้หมวดเดิมที่ผิด **แต่ถ้าโมเดลถอดกฎเดิมได้เป๊ะ ก็สืบทอดข้อผิดพลาดเดิมมาด้วย**

**จะวัดว่าดีขึ้นจริงต้องมี label ที่คนตรวจแล้ว** ไม่ใช่ label ที่กฎสร้าง

ตัวเลขพวกนี้ยังใช้**เทียบโมเดลกันเอง**ได้ เพราะทุกตัววัดกับ target เดียวกัน

---

## กับดักที่เจอจริง

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| `ModuleNotFoundError` / import ผิดตัว | **anaconda มี package ชื่อ `mapper`** | เปลี่ยนเป็น `itec_mapper.py` + `sys.path.insert` |
| `KeyError: 'ItemName'` | CSV ใช้ `item_name` ไม่ใช่ชื่อจาก view | `normalize_columns()` map ให้อัตโนมัติ |
| `AttributeError: no attribute 'Main_Product_Dimension'` | **pandas 3 ตัดคอลัมน์ที่ group ออกจาก `groupby.apply`** | ใช้ลูปธรรมดา |
| `TypeError: only integer scalar arrays...` | **pandas 3 คืน `ArrowExtensionArray`** | `.to_numpy(dtype=object)` |
| `Stand Huawei` จาก "Medal of **Honor** **Standard**" | คำสั้นจับมั่ว | `whole_word` + ตัด `honor` |
| `band` ชน `brand` | คำสั้นจับมั่ว | `whole_word` |
| `Keyboard Nintendo` จาก "Red **Switch**" | คำกำกวม | ใช้ `nintendo` ไม่ใช่ `switch` |

**สามข้อกลางเป็นเรื่อง pandas 3 ทั้งหมด** — จะเจอซ้ำถ้าเขียนโค้ดใหม่แบบเดิม

---

## ขั้นตอนใช้งาน

### บนเครื่องตัวเอง

```bash
cd scripts/itec/category
jupyter notebook itec_recategorization_colab.ipynb
```

Cell 1 ตรวจเองว่าไม่ได้อยู่ Colab → ใช้ `_data/` ตรง ๆ ไม่ต้องอัปอะไร

### บน Colab

```bash
python make_zip.py          # ต้องรันทุกครั้งที่แก้โค้ด
```

อัป 3 ไฟล์ — notebook · `_data/dim_item_itec.csv.gz` · `itec_category_scripts.zip`

**Runtime → Change runtime type → T4 GPU** ก่อนรัน

> **zip เป็นสำเนา ไม่ใช่ตัวจริง** — ไม่ build ใหม่ Colab จะใช้กฎเก่า · ปัญหาเดียวกับ "ซอร์ส 3 ที่" ใน [[Google Sheet to S3 (Lambda)]]

---

## สิ่งที่ยังไม่ได้ทำ

| # | เรื่อง | ทำไมสำคัญ |
|---|---|---|
| 1 | **ยังไม่รู้ว่า `bge-m3` ชนะ TF-IDF ไหม** | ต้องรัน Colab · ตอบคำถามว่าต้องใช้ GPU จริงไหม |
| 2 | ยังไม่ได้รัน `reconcile.py` เทียบ SQL จริง | ต้องผ่าน strict 0% ก่อน |
| 3 | **ยังไม่ได้ตัดสินใจเรื่อง flag** | → [[ITEC Flag & Category Review Guide]] |
| 4 | **คำถาม Telecom 8,592 แถว ควรอยู่ใน `dim_item` ไหม** | ต้องตอบก่อนข้ออื่น |
| 5 | GPU quota ยัง `CASE_OPENED` | → [[ITEC Model - Run on EC2 Guide]] |

---

## เชื่อมกับโน้ตอื่น

[[ITEC Item Category Mapping (SQL to Python)]] · [[ITEC Category Model (ML)]] · [[ITEC Flag & Category Review Guide]] · [[ITEC Model - Run on EC2 Guide]] · [[ITEC - Data Dictionary]] · [[ITEC Overview]] · [[Python Libraries]] · [[ITEC Model - Notebook Explained]]
