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



---

# ภาคผนวก: Flag & Category Review (ผลวิเคราะห์ข้อมูลจริง 216k แถว)

> ยุบจากไฟล์ `ITEC Flag & Category Review Guide` (2026-09-16)

> สำรวจข้อมูลจริง **216,006 แถว** เพื่อชี้ว่าควรเพิ่ม/ลด flag ตัวไหน — **2026-09-14**
> สคริปต์ `scripts/itec/category/explore_flags.py` · ต่อจาก [[ITEC Item Category Mapping (SQL to Python)]]
> โมเดล → [[ITEC Category Model (ML)]] · รันบน GPU → [[ITEC Model - Run on EC2 Guide]]

**คู่มือนี้ไม่ได้ตัดสินใจแทน** — ให้ตัวเลขและหลักฐานไว้แยกหมวดเอง

---

# ✅ ลงมือแก้แล้ว 2026-09-15 — ผลจริง

ทำตามข้อ 2–5 ของ "ลำดับที่แนะนำ" ข้างล่าง

```
Accessory and Others   68,200 (31.6%)  →  41,425 (19.2%)
ดึงออกได้ 26,775 แถว · หมวดเพิ่มจาก 14 → 23
```

| หมวดที่เพิ่ม | จำนวน |
|---|---|
| Storage | 6,257 |
| Spare Part | 5,374 |
| **Telecom / Package** | **5,285** |
| Audio | 3,392 |
| Monitor | 3,006 |
| Printer / Ink | 2,882 |
| Network | 1,439 |
| Furniture | 1,025 |
| Merchandise | 126 |

## แก้อะไรไปบ้าง

| ไฟล์ | เปลี่ยน |
|---|---|
| `item_keywords.yaml` | **67 → 75 flag** · เติมคำไทยให้ 12 flag · เปิด `whole_word` 7 ตัว |
| `rules.py` | **+9 หมวด** · เพิ่ม `IS_PowerBank` เข้ากฎ Sub |
| `itec_mapper.py` | **แก้ regex ที่ลบภาษาไทยทิ้ง** |

ของเดิมสำรองไว้ที่ `_out/item_keywords.before.yaml` · `_out/rules.before.py`

## 🛑 บั๊กใหญ่ที่เจอระหว่างทาง — regex ลบภาษาไทยทิ้งหมด

```
'บัตรเติมเงิน จ่ายล่วงหน้า 300 บาท'  →  '                          300    '
```

`normalize()` ใช้ `[^\w\s/&+.-]` ซึ่งพังสองชั้นซ้อนกัน

| ชั้น | ปัญหา |
|---|---|
| 1 | **`re` ธรรมดาก็พัง** — สระ/วรรณยุกต์ไทยเป็น Unicode `Mn` ไม่นับเป็น `\w` |
| 2 | **pandas 3 ใช้ Arrow + RE2** → `\w` เป็น ASCII ล้วน → ไทยหายทั้งตัว |

แก้เป็น `[^\w\s/&+.\-ก-๛]` — **ต้องใส่อักษรไทยจริง ไม่ใช่ `\u0E00`** เพราะ RE2 ไม่รองรับ `\u`

> **keyword ภาษาไทยทุกตัวในระบบไม่เคยทำงานเลยจนกว่าจะแก้บรรทัดนี้**
> `Telecom` ขยับจาก **279 → 5,285 แถว** ทันทีหลังแก้

## ที่ยังต้องระวัง

| | |
|---|---|
| **`Telecom / Package` 5,285 แถว** | อาจไม่ควรอยู่ใน `dim_item` ตั้งแต่แรก — **ยังต้องถามเจ้าของระบบ** |
| `Merchandise` ได้แค่ 126 | keyword ยังแคบไป ดู `_out/accessory_words.csv` เพิ่ม |
| **`reconcile.py` จะไม่ได้ 0% อีกแล้ว** | ตั้งใจ เพราะเพิ่ม 9 หมวด — ไม่ใช่การ port ผิด |


---

## ปัญหาใหญ่ที่สุด — กองขยะ 31.6%

```
Accessory and Others    68,200 แถว    31.6% ของทั้งหมด
```

**หนึ่งในสามของสินค้าทั้งบริษัทตกอยู่ในหมวดเดียวที่แปลว่า "อย่างอื่น"** — ทำให้วิเคราะห์อะไรไม่ได้เลย

ทดสอบแล้วว่า **41.2% ของกองนี้แยกออกได้ทันที** ด้วยหมวดใหม่ 8 หมวด

| หมวดที่เสนอ | ดึงออกได้ | % ของกอง |
|---|---:|---:|
| **Telecom / Package** | 8,592 | **12.6%** |
| **Spare Part / Repair** | 6,426 | **9.4%** |
| **Printer / Ink** | 4,521 | 6.6% |
| **Monitor / Display** | 3,350 | 4.9% |
| Audio / Speaker | 2,709 | 4.0% |
| Network | 1,197 | 1.8% |
| Smart Home / IoT | 768 | 1.1% |
| Storage | 540 | 0.8% |
| **รวม** | **28,103** | **41.2%** |

**กองจะลดจาก 31.6% เหลือ 18.6% ของทั้งหมด**

---

## 1 · Telecom / Package — ไม่ใช่สินค้าด้วยซ้ำ

คำที่โผล่บ่อยที่สุดในกองขยะ

```
บาท              9,816   14.4% ของกอง
true             7,717   11.3%
จ่ายล่วงหน้า      3,074    4.5%
จ่าย             2,707    4.0%
ราคาเครื่อง       2,130    3.1%
ลดค่าเครื่อง      1,544    2.3%
plan             1,414    2.1%
```

**นี่คือรายการแพ็กเกจมือถือและส่วนลดค่าเครื่อง ไม่ใช่ตัวสินค้า**

> ⚠️ **คำถามที่ใหญ่กว่าการเพิ่ม flag** — ของพวกนี้ควรอยู่ใน `dim_item` หรือเปล่า
> มันเป็นเงื่อนไขการขาย ไม่ใช่สิ่งของ · ถ้านับรวมเป็น "สินค้า" ตัวเลข 216,009 จะไม่ใช่จำนวนสินค้าจริง
> **ควรถามเจ้าของระบบก่อนตัดสินใจ** → [[ITEC Overview]]

เกี่ยวกับ **TRUE by COM7** ซึ่งเป็นธุรกิจโทรคมนาคมในเครือ → [[Retail]]

## 2 · Spare Part / Repair — 9.4%

```
part    3,164     lcd    1,832
```

อะไหล่ซ่อม — เชื่อมกับธุรกิจศูนย์บริการ → [[ICS (iCare Service)]]

**แยกออกมาแล้วจะตอบได้ว่าอะไหล่ตัวไหนขายดี ซึ่งตอนนี้ตอบไม่ได้เลย**

---

## flag ที่มีอยู่แล้วแต่กฎไม่ได้ใช้ — 17 ตัว

**คำนวณทุกแถวแต่ไม่มีผลต่อ `Main_Product_Dimension` เลย** — เสียแรงเปล่า และของที่ควรแยกก็ตกกอง

| flag | ติดทั้งหมด | ติดในกองขยะ | ควรทำอะไร |
|---|---:|---:|---|
| `IS_USB` | 9,882 (4.6%) | 4,111 (6.0%) | **รวมเข้า Accessory ย่อย หรือ Storage** |
| `IS_Monitor` | 3,915 (1.8%) | 3,609 (5.3%) | **ตั้งหมวด Monitor** |
| `IS_Speaker` | 5,049 (2.3%) | 3,164 (4.6%) | **ตั้งหมวด Audio** |
| `IS_Printer` | 2,703 (1.3%) | 2,584 (3.8%) | **ตั้งหมวด Printer** |
| `IS_Card` | 3,293 (1.5%) | 2,402 (3.5%) | คลุมเครือ — `%card%` จับทั้ง SD card, graphic card, การ์ดอวยพร |
| `IS_Buletooth` | 3,960 (1.8%) | 1,817 (2.7%) | **สะกดผิด** ควรแก้เป็น `IS_Bluetooth` |
| `IS_Gadget` | 2,500 (1.2%) | 1,766 (2.6%) | กว้างเกินไป ไม่สื่ออะไร |
| `IS_Sim` | 2,640 (1.2%) | 1,294 (1.9%) | **เข้ากลุ่ม Telecom** |
| `IS_SD` | 6,118 (2.8%) | — | **`%sd%` 2 ตัวอักษร จับมั่วสูง** ต้องเปิด `whole_word` |
| `IS_Applewatch` | 2,296 (1.1%) | — | ซ้ำกับ `IS_Watch` ที่ใช้อยู่แล้ว |
| `IS_Battery` | 1,722 (0.8%) | — | เข้ากลุ่ม Spare Part |
| `IS_EarPhone` · `IS_Earcap` · `IS_Toner` · `IS_Cartridge` · `IS_Flashdrive` · `IS_Microphone` | น้อย | — | รวมเข้ากลุ่มใหญ่ |

**ข้อสรุป** — ไม่ต้องเพิ่ม flag ใหม่มาก **ของที่มีอยู่แล้วยังไม่ได้ถูกใช้เลย 17 ตัว**

---

## flag ที่ควรพิจารณาเพิ่ม

จากคำที่ยังไม่มี flag ไหนจับ

| กลุ่ม | keyword ที่เจอในข้อมูลจริง |
|---|---|
| **Telecom** | `จ่ายล่วงหน้า` `ราคาเครื่อง` `ลดค่าเครื่อง` `plan` `prepaid` `postpaid` `เติมเงิน` `รายเดือน` |
| **Spare Part** | `part` `lcd` `อะไหล่` `screen` `flex` `board` |
| **Network** | `router` `wifi` `modem` `access point` `เราเตอร์` |
| **Furniture** | `chair` `desk` — เจอ Gaming Chair/Desk เยอะในกองที่เหลือ |
| **Merchandise** | `t-shirt` `shirt` — เสื้อ AMD, ของพรีเมียม |

> **`chair` กับ `shirt` เป็นตัวอย่างที่ดีว่าทำไมต้องสำรวจข้อมูลจริง** — ไม่มีใครคิดว่าร้านขาย IT จะมีเก้าอี้กับเสื้อยืดในระบบ แต่มีจริงและตกอยู่ในกองขยะ

---

## flag ที่ควรระวัง ไม่ใช่ลบ

| flag | ปัญหา | ทำยังไง |
|---|---|---|
| `IS_SD` | `%sd%` **2 ตัวอักษร** จับคำอื่นมั่ว | เปิด `whole_word` |
| `IS_Pin` | `%pin%` จับ shi**ppin**g · **1,362 แถวในกองขยะ** | เปิด `whole_word` |
| `IS_Card` | จับทั้ง SD card / graphic card / การ์ดอวยพร | แยกเป็น flag ย่อย |
| `IS_Case` | `%case%` จับ show**case** · 4,711 ในกอง | เปิด `whole_word` |
| `IS_Demo_Product` | **ML ทำนายไม่ได้ (f1 0.42)** เพราะเป็นสถานะการขาย | **ใช้ keyword ต่อไป อย่าให้ ML ทำ** |

---

## flag ที่ซ้อนทับกัน — มีคู่เดียว

```
IS_Mouse ∩ IS_Keyboard    jaccard 0.65
  ติดทั้งคู่ 6,052 · เฉพาะ Mouse 1,939 · เฉพาะ Keyboard 1,289
```

**ไม่ใช่ปัญหา** — SQL เดิมจัดการไว้แล้วด้วยกฎ

```
Mouse=1 Keyboard=0  →  Mouse
Mouse=0 Keyboard=1  →  Keyboard
Mouse=1 Keyboard=1  →  Bundle Mouse&Keyboard
```

เป็นตัวอย่างที่ดีของการใช้ flag ซ้อนกันอย่างตั้งใจ

---

## ของที่เหลือในกองหลังแยกแล้ว

ตัวอย่างจริงที่ยังจัดไม่ได้

```
^^ Monster AI 800 MINI-3 (Mini jack to Mini jack 3.5 mm)
โปรโมชั่นผ่อน 0% 10เดือน Samsung ช่วยออก 2 เดือน ลดราคาหน้าบิล
AMD T-shirt RYZEN xPUCK
Tengu Gaming Chair Kusanagi Red        ← เจอหลายสิบรุ่น
Tengu Gaming Desk Sasaki All White
Network Card TB-21E
```

**เห็นกลุ่มชัดอีก 3 กลุ่ม** — เฟอร์นิเจอร์เกมมิ่ง · ของพรีเมียม/เสื้อ · สายแปลงสัญญาณ

---

## ไฟล์ที่สคริปต์ออกให้ — เอาไปแยกมือต่อ

```bash
cd C:\Users\Sapon.S\Downloads
python C:\Projects\my-first-project\scripts\itec\category\explore_flags.py --csv dim_item_itec.csv
```

| ไฟล์ | มีอะไร | ใช้ทำอะไร |
|---|---|---|
| `flag_usage.csv` | 67 flag · ติดกี่แถว · กฎใช้ไหม · keyword | **ตัดสินว่าจะลบ/เก็บ flag ไหน** |
| `accessory_words.csv` | 120 คำเด่นในกองขยะที่ยังไม่มี flag จับ | **หา flag ที่ควรเพิ่ม** |
| `unmatched_words.csv` | 120 คำเด่นทั้งชุดที่ยังไม่มี flag จับ | ดูภาพรวม |
| `flag_overlap.csv` | คู่ flag ที่ซ้อนกันเกิน 50% | หาตัวซ้ำซ้อน |

---

## ลำดับที่แนะนำให้ทำ

| # | ทำอะไร | ได้อะไร |
|---|---|---|
| 1 | **ถามเจ้าของระบบว่า Telecom/Package ควรอยู่ใน `dim_item` ไหม** | อาจตัดออก 8,592 แถวเลย · กระทบทุกตัวเลขที่นับ "จำนวนสินค้า" |
| 2 | เอา 17 flag ที่มีอยู่แล้วมาใช้ — ตั้งหมวด Monitor · Printer · Audio | ดึงออกจากกอง ~13.7% โดยไม่ต้องเขียน keyword ใหม่ |
| 3 | เพิ่ม flag กลุ่ม Telecom กับ Spare Part | ดึงอีก ~22% |
| 4 | เปิด `whole_word` ให้ `IS_SD` `IS_Pin` `IS_Case` | ลด false positive |
| 5 | แก้ `IS_Buletooth` → `IS_Bluetooth` | คงชื่อเดิมเป็น alias ไว้ให้ของเก่าไม่พัง |
| 6 | รัน `reconcile.py` เทียบกับของเดิม | ดูว่าเปลี่ยนไปกี่แถว อธิบายได้ทุกแถวไหม |

**ข้อ 1 ต้องตอบก่อนข้ออื่น** — ถ้าตัด Telecom ออกจาก item dimension ตัวเลขทั้งหมดข้างบนจะเปลี่ยน

---

## เชื่อมกับโน้ตอื่น

[[ITEC - Data Dictionary]] · [[ITEC Overview]] · [[Data Standardization & Quality]] · [[Python Libraries]] · [[ETL & Spark]] · [[SQL & Source Schemas]] · [[Snapshot Change Detection (ITEC DMS)]] · [[ITEC Item Category Mapping (SQL to Python)]] · [[ITEC Category Toolkit]]
