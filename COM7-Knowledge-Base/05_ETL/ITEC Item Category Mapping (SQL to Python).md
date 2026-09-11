# ITEC Item Category Mapping (SQL → Python)

> แผนย้าย logic จำแนกประเภทสินค้าออกจาก SQL ไปทำใน **pandas / Spark**
> ต้นฉบับ `ci_item_category.sql` (244 บรรทัด · 29.5 KB) → ตารางปลายทาง [[ITEC - Data Dictionary|ci.clean_item_category_itec]] · 216,009 แถว
> แนวทาง ML (ทำนายด้วย LLM embedding แทน rule-based) → [[ITEC Category Model (ML)]]

**หลักการ** — SQL ทำหน้าที่**ดึงข้อมูล**อย่างเดียว · **ตรรกะทั้งหมดย้ายไป Python** ที่เทสได้ แก้ได้ และเก็บ keyword เป็นข้อมูลไม่ใช่โค้ด

---

## ของเดิมทำอะไร — 3 ชั้นซ้อนกัน

```
rpt.dim_item_itec  (a)
        │
        ├─ ชั้น 1 (aa)   สร้าง IS_* 67 ตัว จาก LIKE บน 3 คอลัมน์
        │                ItemName · CategoryName · SubCategoryName
        │
        ├─ ชั้น 2 (aaa)  Sale_Type · Product_Dimension · Product_Purpose
        │                Main_Product_Dimension     ← CASE เรียงลำดับ
        │
        └─ ชั้นนอก        Sub_Product_Dimension      ← CASE เรียงลำดับ
```

| ตัวเลขจริงที่นับจากไฟล์ | |
|---|---|
| IS_* flag | **67 ตัว** |
| keyword ที่ใช้ค้น | **76 คำ** |
| การเทียบ LIKE ทั้งหมด | **67 × 3 = 201 ครั้งต่อแถว** |
| flag ที่มีมากกว่า 1 keyword | 4 ตัว — `IS_Applewatch` `IS_HeadPhone` `IS_PowerBank` `IS_Harddisk` |
| ผลลัพธ์ที่ต้องได้เหมือนเดิม | `Main_Product_Dimension` · `Sub_Product_Dimension` + 4 คอลัมน์รอง |

**ทุก flag ค้นครบทั้ง 3 คอลัมน์แบบ OR เหมือนกันหมด** — ตรวจแล้วไม่มีข้อยกเว้น จึงยุบเหลือ **ค้นครั้งเดียวบนข้อความที่ต่อกัน** ได้ทันที · 201 → 67

---

## โค้ดอยู่ที่ไหน

`scripts/itec/category/`

| ไฟล์ | ทำอะไร |
|---|---|
| `extract_keywords.py` | อ่าน SQL เดิม → เขียน `item_keywords.yaml` · ตั้ง `whole_word` ให้คำเสี่ยงอัตโนมัติ |
| `item_keywords.yaml` | **สร้างแล้ว** — 67 flag · 76 keyword · `whole_word` เปิดไว้ 14 ตัว |
| `rules.py` | กฎ Main / Sub แปลงตรงจาก `CASE WHEN` · เรียงลำดับเหมือนเดิมห้ามสลับ |
| `mapper.py` | pipeline หลัก · `run(df, strict=True)` · มีตัวอย่างรันได้ทันที |
| `reconcile.py` | เทียบกับ SQL เดิมทีละ `ItemId` · strict ไม่ตรง = `sys.exit` |

```
python scripts/itec/category/extract_keywords.py <path>.sql   # ครั้งเดียว
python scripts/itec/category/mapper.py                        # ดูตัวอย่าง
python scripts/itec/category/reconcile.py <path>.sql           # ต้องผ่านก่อนไปต่อ
```

**`strict=True` คือค่าเริ่มต้น** — ทำเหมือนของเดิมทุกประการ ไม่ใช้ `whole_word` ไม่แก้บั๊ก
`strict=False` จึงเปิดทั้งสองอย่างพร้อมกัน เพื่อให้ `reconcile.py` เทียบสองแบบในรอบเดียว

### ผลจากตัวอย่างที่รันแล้ว

```
                  ItemName Main_Product_Dimension Sub_Product_Dimension  IS_Pin
   iPhone 15 Pro Max 256GB            Smart Phone Smart Phone Main&Other      0
      Case iPhone 15 Clear            Smart Phone      Smart Phone Case       0
         MacBook Air M3 13               Notebook     Ordinary-Notebook       0
Logitech Gaming Mouse G502         Mouse&Keyboard                 Mouse       0
              Shipping Fee   Accessory and Others  Accessory and Others      1  ← false positive
       AppleCare+ for iPad                 Tablet      Tablet Insurance       0
       Samsung SSD 980 1TB  PC&Notebook Component PC&Notebook Component       0
```

**`Shipping Fee` ติด `IS_Pin`** เพราะ `LIKE '%pin%'` เจอใน "shi**ppin**g" — เปิด `whole_word` แล้วหาย
นี่คือตัวอย่างจริงว่าทำไมขั้น 5 ถึงจำเป็น

---

## ขั้นตอน

### ขั้น 1 · SQL เหลือแค่ดึงข้อมูล

```sql
SELECT ItemId, ItemName, CategoryName, SubCategoryName, [Model/Series], Brand
FROM   rpt.dim_item_itec;
```

**6 คอลัมน์ แทนที่จะเป็น 76** — ไม่มี CASE ไม่มี LIKE ไม่มี subquery ซ้อน

| ได้อะไร | |
|---|---|
| โหลดฐานเบาลง | คิดครั้งเดียวที่ Python ไม่ใช่ให้ SQL Server คิด 201 ครั้ง × 216,009 แถว |
| แก้ keyword ไม่ต้องแก้ SQL | เจ้าของฐานไม่อนุมัติให้แก้ view อยู่แล้ว → [[Decisions]] D-20 |
| เทสได้ | ใส่ข้อความสมมติเข้าฟังก์ชัน ตรวจผลได้โดยไม่ต้องต่อฐาน |

### ขั้น 2 · รวมข้อความเป็นคอลัมน์เดียวแล้ว normalize

```python
import pandas as pd, re

def normalize(s: pd.Series) -> pd.Series:
    return (s.fillna("")
             .str.lower()
             .str.replace(r"[^\w\s/&+.-]", " ", regex=True)   # เก็บ / & + . - ไว้ เพราะ h/d ใช้
             .str.replace(r"\s+", " ", regex=True)
             .str.strip())

df["search_text"] = (normalize(df.ItemName) + " | "
                     + normalize(df.CategoryName) + " | "
                     + normalize(df.SubCategoryName))
```

**คั่นด้วย `|` ไม่ใช่ช่องว่าง** — กันคำจากคอลัมน์คนละตัวมาต่อกันแล้วเกิดคำใหม่ที่ไม่มีจริง เช่น `ItemName` จบด้วย "power" และ `CategoryName` เริ่มด้วย "bank" จะกลายเป็น "power bank"

### ขั้น 3 · เก็บ keyword เป็นข้อมูล ไม่ใช่โค้ด

```yaml
# item_keywords.yaml
IS_iPhone:      ["iphone"]
IS_Galaxy:      ["galaxy"]
IS_PowerBank:   ["power bank", "powerbank"]
IS_Harddisk:    ["hdd", "ssd", "h/d", "external", "portable",
                 "internal harddrive", "solid state drive"]
IS_Applewatch:  ["apple watch", "applewatch"]
IS_HeadPhone:   ["headphone", "head phone"]
# ... ครบ 67 ตัว
```

**นี่คือหัวใจของการย้าย** — คนที่รู้เรื่องสินค้าแก้ไฟล์นี้ได้เอง โดยไม่ต้องแตะโค้ดและไม่ต้องขอสิทธิ์แก้ view

ดึง keyword ชุดตั้งต้นจาก SQL เดิมได้ด้วย regex เดียว ไม่ต้องพิมพ์เอง

```python
import re, yaml
sql  = open("ci_item_category.sql", encoding="utf-8").read()
flat = re.sub(r"\s+", " ", sql)
rules = {name: sorted({w.lower() for w in re.findall(r"LIKE '%([^']*)%'", cond)})
         for cond, name in
         re.findall(r"CASE WHEN (.*?) THEN 1 ELSE 0 END AS (IS_[A-Za-z_]+)", flat, re.I)}
yaml.safe_dump(rules, open("item_keywords.yaml", "w", encoding="utf-8"),
               allow_unicode=True, sort_keys=False)
```

### ขั้น 4 · สร้าง flag แบบ vectorized

```python
def build_flags(df, rules):
    for flag, words in rules.items():
        pattern = "|".join(re.escape(w) for w in words)
        df[flag] = df.search_text.str.contains(pattern, regex=True).astype("int8")
    return df
```

**`int8` ไม่ใช่ `int64`** — 67 คอลัมน์ × 216,009 แถว ต่างกัน 8 เท่า (116 MB → 14 MB)

**Spark เขียนแบบเดียวกัน**

```python
from pyspark.sql import functions as F
for flag, words in rules.items():
    df = df.withColumn(flag, F.col("search_text").rlike("|".join(map(re.escape, words))).cast("tinyint"))
```

### ขั้น 5 · แก้ false positive ด้วยขอบเขตคำ

**นี่คือสิ่งที่ SQL ทำไม่ได้ แต่ Python ทำได้** — `LIKE '%pin%'` จับ "shi**ppin**g" · "**pin**k" · "s**pin**ner"

keyword ที่สั้นกว่า 5 ตัวอักษรและเสี่ยงสูง **18 คำ**

| flag | keyword | จับผิดเป็นอะไรได้ |
|---|---|---|
| `IS_Pin` | `pin` | shipping · pink · spinner |
| `IS_SD` | `sd` | ไม่จำกัด — 2 ตัวอักษร |
| `IS_Card` | `card` | cardboard · graphic**card** |
| `IS_Case` | `case` | show**case** · brief**case** |
| `IS_PC` | `pc` | ทุกคำที่มี pc ติดกัน |
| `IS_RAM` | `ram` | prog**ram** · **Ram**adan |
| `IS_Sim` | `sim` | **sim**ple · **Sim**s |
| `IS_film` | `film` | ค่อนข้างปลอดภัย |
| `IS_Care` | `care` | **care**ful |

วิธีแก้ — ประกาศไว้ใน YAML ว่าคำไหนต้องบังคับขอบเขตคำ

```yaml
IS_Pin:
  words: ["pin"]
  whole_word: true      # → \bpin\b
IS_Harddisk:
  words: ["hdd", "ssd", "h/d"]
  whole_word: true
```

```python
def to_pattern(words, whole_word=False):
    esc = [re.escape(w) for w in words]
    return r"\b(?:" + "|".join(esc) + r")\b" if whole_word else "|".join(esc)
```

**ห้ามเปิด `whole_word` ทุกตัวรวด** — `IS_iPhone` ต้องจับ "iPhone15" ที่ติดกันได้ · ต้องเลือกทีละตัวแล้ววัดผล

### ขั้น 6 · Main_Product_Dimension — กฎเรียงลำดับ

**ลำดับสำคัญมาก ตัวแรกที่ตรงชนะ** เหมือน `CASE WHEN` ของเดิมเป๊ะ

```python
import numpy as np

MAIN_RULES = [
    ("Smart Phone",               lambda d: d.IS_Smartphone | d.IS_Mobile | d.IS_Galaxy | d.IS_iPhone),
    ("Tablet",                    lambda d: d.IS_iPad | d.IS_Tablet),
    ("Smart Watch",               lambda d: d.IS_Watch),
    ("HeadSet&Earpiece",          lambda d: d.IS_AirPod | d.IS_HeadSet | d.IS_HeadPhone),
    ("Mouse&Keyboard",            lambda d: d.IS_Mouse | d.IS_Keyboard),
    ("Software",                  lambda d: d.IS_Software),
    ("Insurance",                 lambda d: d.IS_AppleCare | d.IS_Insurance | d.IS_Care),
    ("Console Gaming",            lambda d: d.IS_Nintendo_SwitchG | d.IS_NintendoSwitch | d.IS_Playstation),
    ("PC",                        lambda d: (d.IS_iMac | d.IS_PC | d.IS_Desktop | d.IS_Computer)
                                            & ~(d.IS_Notebook | d.IS_Macbook)),          # ← แก้บั๊ก ดูด้านล่าง
    ("Notebook",                  lambda d: d.IS_Notebook | d.IS_Macbook),
    ("PC&Notebook Component",     lambda d: d.IS_GraphicCard | d.IS_PowerSupply | d.IS_Mainboard
                                            | d.IS_RAM | d.IS_CPU | d.IS_Cooling | d.IS_Harddisk),
    ("Camera",                    lambda d: d.IS_Camera),
    ("Adapter/Charger/Powerbank", lambda d: d.IS_Adapter | d.IS_Charger | d.IS_PowerBank),
]

df["Main_Product_Dimension"] = np.select(
    [f(df).astype(bool) for _, f in MAIN_RULES],
    [label for label, _ in MAIN_RULES],
    default="Accessory and Others",
)
```

**`np.select` คือ `CASE WHEN` ของ pandas** — เงื่อนไขแรกที่เป็นจริงชนะ เหมือนกันทุกประการ

### ขั้น 7 · Sub_Product_Dimension — กฎชั้นสอง

รูปแบบซ้ำกันชัดเจน ไม่ต้องเขียน 40 บรรทัด **ให้สร้างจาก template**

```python
ACCESSORY_OF = [                       # (คำต่อท้าย, เงื่อนไข)
    ("Adapter/Charger", lambda d: d.IS_Adapter | d.IS_Charger),
    ("Case",            lambda d: d.IS_Case | d.IS_Casing | d.IS_Protect | d.IS_Bumper),
    ("Film",            lambda d: d.IS_film),
    ("Cable",           lambda d: d.IS_Cable),
    ("Insurance",       lambda d: d.IS_AppleCare | d.IS_Insurance | d.IS_Care),
    ("Other Accessory", lambda d: d.IS_Pin | d.IS_Strap | d.IS_Stand | d.IS_Dock | d.IS_Accessory),
]

SUB_RULES = []
for parent in ("Smart Phone", "Tablet", "Smart Watch", "HeadSet&Earpiece"):
    for suffix, cond in ACCESSORY_OF:
        SUB_RULES.append((f"{parent} {suffix}",
                          lambda d, p=parent, c=cond: (d.Main_Product_Dimension == p) & c(d)))
    SUB_RULES.append((f"{parent} Main&Other",
                      lambda d, p=parent: d.Main_Product_Dimension == p))
```

> ⚠️ **ของเดิมไม่ได้สมมาตรทุกช่อง** — `Smart Watch` ไม่มีกฎ Cable · `HeadSet&Earpiece` มีแค่ Adapter/Charger กับ Case
> **ต้องคัดออกให้ตรงของเดิม** ไม่งั้นผลจะต่าง → ใช้ขั้น 9 จับ

### ขั้น 8 · fuzzy สำหรับตัวที่ยังจับไม่ได้

**ใช้เป็นตาข่ายรับท้าย ไม่ใช่ตัวหลัก** — รันเฉพาะแถวที่ตกลงมาเป็น `Accessory and Others`

```python
from rapidfuzz import process, fuzz

VOCAB = {"iphone": "Smart Phone", "ipad": "Tablet", "macbook": "Notebook",
         "airpods": "HeadSet&Earpiece", "galaxy tab": "Tablet", ...}

leftover = df.Main_Product_Dimension == "Accessory and Others"

def guess(text):
    hit = process.extractOne(text, VOCAB.keys(),
                             scorer=fuzz.token_set_ratio, score_cutoff=88)
    return (VOCAB[hit[0]], hit[0], hit[1]) if hit else (None, None, None)

res = df.loc[leftover, "search_text"].map(guess)
df.loc[leftover, ["fuzzy_guess", "fuzzy_term", "fuzzy_score"]] = list(res)
```

**กฎเหล็ก 4 ข้อของ fuzzy**

| กฎ | เหตุผล |
|---|---|
| **เก็บคะแนนและคำที่ตรงลงคอลัมน์เสมอ** | ต้องตรวจย้อนได้ว่าทำไมถึงเดาแบบนั้น |
| **ห้ามเขียนทับผลจาก keyword** | keyword คือกฎที่คนตั้งใจ · fuzzy คือการเดา |
| **ห้ามใช้ตัดสินรุ่น/ความจุ** | "iPhone 15" กับ "iPhone 5" คะแนนสูงมาก **แต่คนละสินค้า** |
| **ตัวที่ fuzzy เดา ต้องมีคนตรวจก่อนเข้า Gold** | ออกเป็นไฟล์ให้ทีมสินค้าดู แล้วค่อยเลื่อนคำที่ยืนยันแล้วขึ้นไปเป็น keyword |

**`rapidfuzz` ไม่ใช่ `fuzzywuzzy`** — เร็วกว่ามาก · ใบอนุญาต MIT · เป็น pure-Python + C ที่มี manylinux wheel พร้อม → [[Python Libraries]]

**`token_set_ratio` ไม่ใช่ `ratio`** — ทนต่อการสลับลำดับคำและคำเกิน ซึ่งชื่อสินค้าจริงมีเยอะ

### ขั้น 9 · กระทบยอดกับของเดิม — ห้ามข้าม

```python
old = pd.read_sql(open("ci_item_category.sql").read(), conn)   # ผลจาก SQL เดิม
new = pipeline(pd.read_sql("SELECT ItemId, ItemName, ... FROM rpt.dim_item_itec", conn))

cmp = old[["ItemId", "Main_Product_Dimension", "Sub_Product_Dimension"]].merge(
        new[["ItemId", "Main_Product_Dimension", "Sub_Product_Dimension"]],
        on="ItemId", suffixes=("_old", "_new"))

diff = cmp[cmp.Main_Product_Dimension_old != cmp.Main_Product_Dimension_new]
print(f"ต่างกัน {len(diff):,} / {len(cmp):,} = {len(diff)/len(cmp):.2%}")
diff.to_csv("category_diff.csv", index=False, encoding="utf-8-sig")
```

**เป้าหมายไม่ใช่ 0%** — เพราะตั้งใจแก้บั๊กและ false positive ไว้ **เป้าหมายคืออธิบายทุกความต่างได้**

| ความต่าง | ต้องทำอะไร |
|---|---|
| เกิดจากบั๊ก PC/Notebook | ตั้งใจ · บันทึกไว้ |
| เกิดจาก `whole_word` | ตั้งใจ · ตรวจตัวอย่างว่าดีขึ้นจริง |
| อธิบายไม่ได้ | **ยังไม่พร้อมใช้** กลับไปแก้ |

`utf-8-sig` เพราะชื่อสินค้ามีภาษาไทย ถ้าไม่มี BOM Excel จะแสดงเป็นขยะ → [[Google Sheet to S3 (Lambda)]]

---

## บั๊กที่เจอในของเดิม

### PC / Notebook — ตัวกรองแทบไม่ทำงาน

```sql
WHEN (IS_iMac=1 OR IS_PC=1 OR IS_Desktop=1 OR is_computer=1)
 AND (IS_Notebook=0 OR IS_macbook=0) THEN 'PC'
```

`(A=0 OR B=0)` **เป็นเท็จก็ต่อเมื่อ A=1 และ B=1 พร้อมกัน** — ของที่เป็น MacBook แต่ไม่มีคำว่า "notebook" ในชื่อ จะได้ `IS_Notebook=0` `IS_Macbook=1` → เงื่อนไขเป็นจริง → **ถ้าดันติด `IS_PC` ด้วยจะถูกจัดเป็น PC**

สาขา `Notebook` ก็เขียนแบบเดียวกัน `(IS_iMac=0 OR IS_PC=0 OR ...)` ซึ่งเกือบจะจริงเสมอ

**ที่ควรเป็นคือ `AND`** — โค้ด Python ในขั้น 6 ใช้ `& ~(...)` ซึ่งคือ AND แล้ว

> **ผลกระทบจริงกี่แถวยังไม่ได้วัด** — ขั้น 9 จะบอกเอง `[ต้องยืนยันกับเจ้าของ logic ก่อนถือว่าเป็นบั๊ก อาจตั้งใจ]`

### flag 17 ตัวไม่ได้ใช้ตัดสินอะไร

`IS_Applewatch` `IS_EarPhone` `IS_Earcap` `IS_Monitor` `IS_Printer` `IS_Toner` `IS_Cartridge` `IS_USB` `IS_Speaker` `IS_Gadget` `IS_Sim` `IS_Flashdrive` `IS_SD` `IS_Card` `IS_Microphone` `IS_Buletooth` `IS_Battery`

**ยังเป็นคอลัมน์ผลลัพธ์อยู่ ไม่ใช่ของตาย** แต่ไม่มีผลต่อ `Main_` หรือ `Sub_Product_Dimension` เลย

น่าสนใจว่า **`IS_Monitor` `IS_Printer` `IS_Speaker` ไม่มีหมวดของตัวเอง** — จอและเครื่องพิมพ์ตกไปอยู่ `Accessory and Others` ทั้งหมด · ควรถามว่าตั้งใจไหม

### `IS_Harddisk` อยู่ในกลุ่ม Component แต่ไม่มีหมวดย่อย

`Sub_Product_Dimension` มีหมวดย่อยให้ 6 ตัว — GraphicCard · PowerSupply · Mainboard · RAM · CPU · Cooling System

**ไม่มี Harddisk** ทั้งที่ `IS_Harddisk` เป็นหนึ่งในเงื่อนไขที่พาเข้ากลุ่ม `PC&Notebook Component`

ผลคือ SSD / HDD ตกไปที่ `ELSE` แล้วได้ `Sub_Product_Dimension = 'PC&Notebook Component'` เท่ากับ Main — เห็นได้จากแถว `Samsung SSD 980 1TB` ในตัวอย่างข้างบน

> **น่าจะตกหล่น ไม่ใช่ตั้งใจ** แต่ `[ต้องยืนยันกับเจ้าของ logic]` · ถ้าเติมก็แค่เพิ่มบรรทัดเดียวใน `_COMPONENT_OF`

### `IS_Buletooth` สะกดผิด

บันทึกไว้แล้วใน [[ITEC - Data Dictionary]] · **ตอนย้ายคือจังหวะที่แก้ได้** โดยคง alias เดิมไว้ให้ของเก่าไม่พัง

```yaml
IS_Bluetooth:
  words: ["bluetooth"]
  alias: IS_Buletooth       # เขียนออกทั้งสองชื่อไปก่อน
```

---

## pandas หรือ Spark

**216,009 แถว × 6 คอลัมน์ ใช้ pandas** — ประมาณ 50–100 MB ใน RAM `[อนุมาน จากขนาดคอลัมน์ข้อความ]`

| | pandas | Spark |
|---|---|---|
| เหมาะเมื่อ | **ตาราง dimension แบบนี้** | ตาราง fact 79.8M แถว |
| เวลาที่คาด | ไม่กี่วินาที | เสียเวลา start cluster มากกว่าเวลาประมวลผล |
| fuzzy | `rapidfuzz` ตรง ๆ | ต้องทำเป็น UDF ซึ่งช้า |

**เขียนให้ logic แยกจาก engine** — เก็บกฎไว้ใน YAML และเขียนฟังก์ชันสร้าง pattern ครั้งเดียว แล้วมีตัวรัน 2 ตัว (pandas / Spark) ที่ใช้ pattern ชุดเดียวกัน **ห้ามมี keyword สองชุด** ไม่งั้นจะเพี้ยนจากกันแน่นอน → บทเรียน "ซอร์ส 3 ที่" ใน [[Google Sheet to S3 (Lambda)]]

---

## ลำดับที่ควรทำ

| ลำดับ | ทำ | เสร็จแล้วรู้อะไร |
|---|---|---|
| 1 | ดึง keyword จาก SQL เป็น YAML (สคริปต์ขั้น 3) | มีชุดกฎตั้งต้นที่ตรงกับของเดิม 100% |
| 2 | สร้าง flag + Main + Sub **โดยยังไม่แก้อะไรเลย** | reproduce ของเดิมได้ไหม |
| 3 | รันขั้น 9 เทียบ | ควรได้ **0% ต่าง** ถ้าไม่ใช่ แปลว่าแปลงกฎผิด |
| 4 | แก้บั๊ก PC/Notebook | ต่างกี่แถว อธิบายได้ไหม |
| 5 | เปิด `whole_word` ทีละคำ | แต่ละคำทำให้ดีขึ้นหรือแย่ลง |
| 6 | เพิ่ม fuzzy สำหรับ `Accessory and Others` | เหลือจัดไม่ได้กี่ % |
| 7 | ส่งไฟล์ให้ทีมสินค้าตรวจ | คำไหนควรเลื่อนขึ้นเป็น keyword ถาวร |

**ขั้น 3 คือด่านที่ห้ามข้าม** — ต้องพิสูจน์ว่าทำเหมือนเดิมได้ก่อน ถึงจะมีสิทธิ์บอกว่าที่ต่างคือของที่ดีขึ้น

---

## เชื่อมกับโน้ตอื่น

[[ITEC - Data Dictionary]] · [[ITEC Overview]] · [[Data Standardization & Quality]] · [[Python Libraries]] · [[ETL & Spark]] · [[SQL & Source Schemas]] · [[Snapshot Change Detection (ITEC DMS)]]
