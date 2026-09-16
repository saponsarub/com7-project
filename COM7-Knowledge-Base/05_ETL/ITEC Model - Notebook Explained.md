# ITEC Model — Notebook Explained

> **อธิบายโน้ตบุ๊กทีละ cell ทุกฟังก์ชัน เพื่อให้ทำเองได้ในอนาคต** — 2026-09-14
> ไฟล์ `scripts/itec/category/itec_recategorization.ipynb` · **รันได้ทั้ง local · Colab · Kaggle**
> ภาพรวมเครื่องมือทั้งชุด → [[ITEC Category Toolkit]]

---

# ส่วนที่ 1 · YAML คืออะไร

## รูปแบบเก็บ "ข้อมูลที่คนอ่านออก"

**YAML = ไฟล์ข้อความธรรมดาที่เก็บโครงสร้างข้อมูล** ใช้ย่อหน้าบอกว่าอะไรอยู่ใต้อะไร

```yaml
types:
  - label: Case
    words: ["case", "เคส", "cover"]
    whole_word: true
  - label: Film
    words: ["film", "ฟิล์ม"]
    whole_word: true
```

อ่านเป็น Python ได้ตรง ๆ

```python
{"types": [
    {"label": "Case", "words": ["case", "เคส", "cover"], "whole_word": True},
    {"label": "Film", "words": ["film", "ฟิล์ม"], "whole_word": True},
]}
```

| สัญลักษณ์              | ความหมาย                       |
| ---------------------- | ------------------------------ |
| `key: value`           | คู่ชื่อ-ค่า                    |
| `- ` นำหน้า            | สมาชิกของลิสต์                 |
| **ย่อหน้า (เว้นวรรค)** | **บอกลำดับชั้น — ห้ามใช้ Tab** |
| `#`                    | คอมเมนต์                       |
| `["a", "b"]`           | ลิสต์แบบสั้น เขียนบรรทัดเดียว  |

## ทำไมใช้ YAML ไม่ใช้ JSON

|                  | YAML    | JSON            |
| ---------------- | ------- | --------------- |
| คอมเมนต์         | ✅       | ❌ **ใส่ไม่ได้** |
| ต้องมี `{ } " ,` | ไม่ต้อง | ต้องครบทุกตัว   |
| คนแก้เองไหว      | ✅       | พลาดง่าย        |

**ข้อที่ชี้ขาดคือคอมเมนต์** — กฎที่คนต้องกลับมาแก้ ต้องอธิบายได้ว่าทำไมถึงตั้งแบบนั้น

## กับดักของ YAML

| อาการ | สาเหตุ |
|---|---|
| `ScannerError` | **ใช้ Tab แทนเว้นวรรค** |
| ค่ากลายเป็น `True`/`False` | เขียน `yes` / `no` / `on` / `off` โดยไม่ใส่ `"` |
| `whole_word: true` ไม่ทำงาน | เขียน `True` ตัวใหญ่ — YAML ต้องเป็น `true` ตัวเล็ก |
| ตัวเลขกลายเป็นสตริง | ใส่ `"` ครอบโดยไม่ตั้งใจ |

## ในโปรเจกต์นี้มี YAML 2 ไฟล์

| ไฟล์                 | เก็บอะไร            | ใครเขียน                         |
| -------------------- | ------------------- | -------------------------------- |
| `item_keywords.yaml` | **75 flag ตาม SQL** | `extract_keywords.py` ดึงจาก SQL |
| `type_platform.yaml` | **ประเภท + แบรนด์** | **Cell 4 ในโน้ตบุ๊กเขียนให้**    |

> ⚠️ **`type_platform.yaml` ห้ามแก้มือ** — Cell 4 เขียนทับทุกครั้งที่รัน
> แก้ที่ Cell 4 เท่านั้น · YAML มีไว้ให้สคริปต์อ่าน ไม่ใช่ให้คนแก้

---

# ส่วนที่ 2 · โน้ตบุ๊กทีละ cell

## ภาพรวม 13 ขั้น

```
ItemName ดิบ
   │
① Setup            ติดตั้ง · ตรวจ GPU · หาไฟล์             Cell 1
② โหลดข้อมูล        อ่าน CSV · แปลงชื่อคอลัมน์               Cell 2
③ Normalize        ทำความสะอาดข้อความ                     Cell 3
④ กฎ               TYPES / PLATFORMS / DISAMBIGUATE  ✏️   Cell 4
⑤ ทดสอบกฎ          ดูผลกับ 7 ตัวอย่าง                      Cell 5
⑥ สร้าง label       ใช้กฎแปะป้ายให้ทุกแถว                   Cell 6
⑦ เตรียม X, y       ตัดหมวดที่ตัวอย่างน้อยเกินไป              Cell 7
⑧ Embedding        ข้อความ → เวกเตอร์ 1024 มิติ            Cell 8
⑨ เทรน M1          เวกเตอร์ → หมวด (ItemName ล้วน)          Cell 9
⑩ เทรน M2          เวกเตอร์ → หมวด (ครบทุกคอลัมน์)          Cell 10
⑪ เทียบ + เซฟ       Accuracy · Macro-F1 · joblib            Cell 11
⑫ หา label ผิด      โมเดลมั่นใจแต่ไม่ตรงกับกฎ = น่าสงสัย      Cell 12
⑬ Fine-tune        ปรับ weights ของ LLM (ทำท้ายสุด)        Cell 13
```

**ส่วนที่ "เรียน" จริงมีแค่ขั้น ⑨⑩** — ขั้น ⑧ เป็นการแปลงข้อความเฉย ๆ ไม่ได้เรียนอะไร

---

## Cell 1 · Setup

```python
IN_COLAB  = "google.colab" in sys.modules
IN_KAGGLE = Path("/kaggle/input").exists()
ENV = "colab" if IN_COLAB else "kaggle" if IN_KAGGLE else "local"
```

**ตรวจเองว่าอยู่ที่ไหน รันได้ 3 ที่ด้วยไฟล์เดียว**

| | หาไฟล์ยังไง |
|---|---|
| `local` | ใช้ `_data/` ที่อยู่ข้าง ๆ |
| `colab` | ขึ้นปุ่มให้อัป `.csv.gz` แล้ว `.zip` |
| `kaggle` | **คัดลอกจาก `/kaggle/input/` ออกมา** เพราะที่นั่นเขียนไม่ได้ |

```python
src = [p for p in Path("/kaggle/input").rglob("*") if p.is_file()]
```

**ต้อง `rglob` + `is_file()`** — dataset ของ Kaggle ซ้อนโฟลเดอร์หลายชั้น
เคยใช้ `glob("/kaggle/input/*/*")` แล้วไปโดนโฟลเดอร์ → `IsADirectoryError`

```python
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass
```

**`sys.stdout` ของ Jupyter/Colab เป็น `ipykernel.OutStream` ซึ่งไม่มีเมธอดนี้** — มีแต่ตอนรันเป็นสคริปต์

```python
try:
    import sentence_transformers
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "sentence-transformers"])
```

**`try/except ImportError` ดีกว่า `pip install` ตรง ๆ** — ลงแล้วไม่ลงซ้ำ รัน cell ซ้ำได้ไม่เสียเวลา

**ใช้ `subprocess` ไม่ใช่ `!pip`** เพราะ `!` เป็น magic ของ IPython ซึ่งพังเมื่ออยู่ในบล็อก `if`

```python
sys.path.insert(0, str(SCRIPTS))
```

**บอก Python ว่าหาโมดูลที่โฟลเดอร์นี้ก่อน** — ทำให้ `import type_platform` เจอไฟล์ของเรา ไม่ใช่ package ชื่อซ้ำใน anaconda

> เคยเจอจริง — anaconda มี package ชื่อ `mapper` ทำให้ต้องเปลี่ยนชื่อไฟล์เป็น `itec_mapper.py`

---

## Cell 2 · โหลดข้อมูล

```python
df = pd.read_csv(DATA, encoding="utf-8-sig", dtype=str).fillna("")
```

| ส่วน | ทำไม |
|---|---|
| `encoding="utf-8-sig"` | **ตัด BOM ทิ้ง** — ไฟล์จาก Excel มี 3 ไบต์นำหน้า ถ้าไม่ตัด ชื่อคอลัมน์แรกจะมีขยะติด |
| `dtype=str` | **กันรหัสสินค้าที่ขึ้นต้นด้วย 0 หายไป** และกัน pandas เดาชนิดผิด |
| `.fillna("")` | ค่าว่างเป็น `""` ไม่ใช่ `NaN` — `str.contains` กับ `NaN` จะได้ `NaN` ไม่ใช่ `False` |

```python
RENAME = {"item_name": "ItemName", "category": "CategoryName", ...}
df = df.rename(columns={k: v for k, v in RENAME.items() if k in df.columns})
```

**CSV ที่ export มาใช้ snake_case แต่โน้ตบุ๊กใช้ PascalCase** — map ก่อน ไม่งั้น `KeyError`

**`if k in df.columns` สำคัญ** — ถ้า rename คอลัมน์ที่ไม่มี pandas จะไม่ error แต่จะเงียบ ทำให้หาบั๊กยาก

```python
assert "ItemName" in df.columns, f"ไม่พบคอลัมน์ ItemName · ที่มีคือ {list(df.columns)}"
```

**`assert` พร้อมข้อความที่บอกว่ามีอะไรให้เลือก** — พังทันทีตรงจุด ดีกว่าไปพังอีก 5 cell ข้างหน้าโดยไม่รู้สาเหตุ

---

## Cell 3 · Normalize

```python
def normalize(s: pd.Series) -> pd.Series:
    return (s.fillna("").astype(str).str.lower()
             .str.replace(r"[^\w\s/&+.\-ก-๛]", " ", regex=True)
             .str.replace(r"\s+", " ", regex=True).str.strip())
```

ทำ 4 อย่างเรียงกัน

| ขั้น | ทำอะไร | ทำไม |
|---|---|---|
| `.str.lower()` | พิมพ์เล็กหมด | `iPhone` = `IPHONE` = `iphone` |
| `[^\w\s/&+.\-ก-๛]` → ช่องว่าง | ตัดอักขระพิเศษ | `CS@ MUSE` → `cs muse` · **เก็บ `/ & + . -` ไว้เพราะ `h/d`, `type-c`, `care+` ใช้** |
| `\s+` → ช่องว่างเดียว | ยุบช่องว่างซ้ำ | `iPhone    15` → `iphone 15` |
| `.strip()` | ตัดหัวท้าย | |

### ⚠️ `ก-๛` คือส่วนที่แก้บั๊กใหญ่

**ก่อนหน้านี้เป็น `[^\w\s/&+.-]` ซึ่งลบภาษาไทยทิ้งทั้งหมด**

```
'บัตรเติมเงิน จ่ายล่วงหน้า 300 บาท'  →  '                          300    '
```

สาเหตุซ้อนกัน 2 ชั้น

| ชั้น | ปัญหา |
|---|---|
| 1 | **`re` ธรรมดาก็พัง** — สระ/วรรณยุกต์ไทยเป็น Unicode category `Mn` ไม่นับเป็น `\w` → `จ่ายล่วงหน้า` เหลือ `จ ายล วงหน า` |
| 2 | **pandas 3 ใช้ Arrow + RE2** → `\w` เป็น ASCII ล้วน → **ไทยหายทั้งตัว** |

**ต้องใช้ `ก-๛` ตัวอักษรจริง ไม่ใช่ `฀`** เพราะ RE2 ไม่รองรับ `\u` escape — จะขึ้น `ArrowInvalid: invalid escape sequence`

> **keyword ภาษาไทยทุกตัวไม่เคยทำงานเลยจนกว่าจะแก้บรรทัดนี้** — `Telecom` ขยับจาก 279 → 5,285 แถวหลังแก้

### ⚠️ Cell 3 นิยามฟังก์ชันเท่านั้น — ยังไม่สร้าง `NORM`

**`NORM` ถูกสร้างที่ Cell 7 หลังกรองหมวดแล้ว** ไม่ใช่ที่นี่ — เหตุผลอยู่ในหัวข้อ Cell 7

---

## Cell 4 ✏️ · กฎ — ที่เดียวที่ต้องแก้

```python
TYPES = [
    {"label": "Service",     "words": [...], "whole_word": True},
    {"label": "PowerSupply", "words": [...], "whole_word": False},
    {"label": "Case",        "words": [...], "whole_word": True},
]
```

### กฎ 3 ชุด

| ชุด | ตอบคำถาม | ตัวอย่างผล |
|---|---|---|
| **`TYPES`** | **เป็นของประเภทไหน** | `Case` · `Charger` · `Device` |
| **`PLATFORMS`** | **ของยี่ห้อ/รุ่นอะไร** | `iPhone` · `Galaxy` · `Generic` |
| **`DISAMBIGUATE`** | **ได้ประเภทแล้ว บริบทบอกว่าควรเปลี่ยนไหม** | `Case` + `atx` → `PC Case` |

รวมกันเป็น `Type_Platform` เช่น **`Case iPhone`**

### ลำดับคือความสำคัญ — ตัวแรกที่ตรงชนะ

```python
("Service", ["part", "อะไหล่"]),   # ← ต้องอยู่ก่อน
("Case",    ["case", "เคส"]),
```

`(Part) BACK HOUSING COVER IPHONE 6` มีทั้ง `part` และ `cover`
**ถ้า `Case` อยู่ก่อน จะกลายเป็นเคส ทั้งที่เป็นอะไหล่**

### `whole_word` กันคำสั้นจับมั่ว

```python
{"label": "Stand", "words": ["stand"], "whole_word": True},
```

| | `whole_word: False` | `whole_word: True` |
|---|---|---|
| `stand` | จับ **Stand**ard ❌ | ไม่จับ ✅ |
| `band` | จับ **brand** ❌ | ไม่จับ ✅ |
| `pin` | จับ shi**ppin**g ❌ | ไม่จับ ✅ |

**แต่ห้ามเปิดทุกตัว** — `iPhone` ต้องจับ `iPhone15` ที่ติดกันได้

> `whole_word` **ไม่มีผลกับคำไทย** เพราะ lookaround เช็ค `[a-z0-9]` ซึ่งอักษรไทยไม่เข้าข่าย

### ⚠️ ลำดับใน `PLATFORMS` — กับดักที่เจอจริง

```python
{"label": "Galaxy-S", "words": ["galaxy", ...]},     # ← กลืนทุกอย่าง
{"label": "Flip-Fold", "words": ["z fold", ...]},
```

`Samsung Galaxy Z Fold 5` มีคำว่า `galaxy` → ตกที่ `Galaxy-S` ก่อนถึง `Flip-Fold`

**ต้องเรียงจากเจาะจงไปกว้าง**

```python
{"label": "Flip-Fold",   "words": ["z fold", "z flip"]},
{"label": "Galaxy-Note", "words": ["galaxy note"]},
{"label": "Galaxy-S",    "words": ["galaxy s"]},
{"label": "Samsung",     "words": ["galaxy", "samsung"]},   # ตาข่ายรับท้าย
```

### ท้าย cell เขียน YAML ให้สคริปต์

```python
with open(SCRIPTS / "type_platform.yaml", "w", encoding="utf-8") as f:
    yaml.safe_dump(_rules, f, allow_unicode=True, sort_keys=False, width=120)
importlib.reload(TP)
```

| ส่วน | ทำไม |
|---|---|
| `allow_unicode=True` | **ไม่งั้นภาษาไทยกลายเป็น `เค...`** อ่านไม่ออก |
| `sort_keys=False` | **รักษาลำดับ** — ลำดับคือความสำคัญ ถ้าเรียงใหม่กฎเปลี่ยนความหมาย |
| `importlib.reload(TP)` | บังคับให้โมดูลอ่านกฎใหม่ · **ไม่ reload จะยังใช้ของเก่าที่ค้างในหน่วยความจำ** |

**โน้ตบุ๊กเป็นตัวจริง YAML เป็นของที่ถูกสร้าง** — สคริปต์ `predict_all.py` / `explore_flags.py` อ่าน YAML จึงได้กฎชุดเดียวกันเสมอ

---

## Cell 5 · ทดสอบกฎ

```python
for s in chk:
    print(f"{str(TP.classify(s)):28} | {s}")
```

**แก้กฎที่ Cell 4 → รัน Cell 5 → เห็นผลใน 1 วินาที**

ไม่ต้องรอ embed 30 นาทีเพื่อจะรู้ว่าตั้งกฎผิด — **นี่คือ cell ที่ประหยัดเวลาที่สุดในโน้ตบุ๊ก**

---

## Cell 6 · สร้าง label

```python
df = TP.add_columns(df)
LABEL_COL = "Type_Platform"
```

### `classify()` ทำงานยังไง

```python
def classify(name, context=""):
    t = _first(name, TYPES, "Device")        # ประเภทจากชื่อสินค้า
    p = _first(name, PLATFORMS, "Generic")   # แบรนด์จากชื่อสินค้า

    if context:                              # ชื่อบอกไม่ได้ค่อยถามหมวดเดิม
        if t == "Device":   t = _first(context, TYPES, "Device")
        if p == "Generic":  p = _first(context, PLATFORMS, "Generic")

    for old, kw, new, ww in DISAMBIGUATE:    # แก้ความกำกวมเป็นขั้นสุดท้าย
        if t == old and re.search(...): t = new; break
    return t, p
```

**ชื่อสินค้าชนะหมวดเดิมเสมอ** — หมวดเดิมของ ITEC key ผิดเยอะ ใช้เป็นตัวสำรองเท่านั้น

พิสูจน์ได้จาก `Tengu Gaming Mouse Pad` ที่ `SubCategoryName` เขียนว่า `MOUSE & KEYBOARD & MOUSE PAD`
→ ได้ `Mouse` ✅ ไม่ใช่ `Keyboard` เพราะชื่อสินค้าตัดสินก่อน

### เลือก label

| `LABEL_COL` | หมวด | เหมาะกับ |
|---|---|---|
| `"Type_Platform"` | ~294 | ละเอียด · `Case iPhone` แยกจาก `Case Galaxy` |
| `"Item_Type"` | ~20 | หยาบ · เทรนง่ายกว่า ตัวอย่างต่อหมวดเยอะกว่า |

---

## Cell 7 · เตรียม X, y

```python
vc = df[LABEL_COL].value_counts()
data = df[df[LABEL_COL].isin(vc[vc >= 5].index)].reset_index(drop=True)
```

**ตัดหมวดที่มีน้อยกว่า 5 แถวออก**

**ทำไมต้องตัด** — `train_test_split(stratify=y)` ต้องมีอย่างน้อย 2 ตัวอย่างต่อหมวด และ `cross_val` 5 fold ต้องมี 5 · หมวดที่มีแถวเดียวจะทำให้ทั้งขั้นตอนพัง

```python
y = data[LABEL_COL].to_numpy(dtype=object)
NORM = {c: normalize(data[c]) for c in TEXT_COLS if c in data.columns}
assert len(NORM["ItemName"]) == len(y)
```

**ไม่ใช้ `.values`** — pandas 3 คืน `ArrowExtensionArray` ซึ่ง sklearn index ด้วย array ไม่ได้
จะขึ้น `TypeError: only integer scalar arrays can be converted to a scalar index`

### 🛑 บั๊กที่เจอจริง — `NORM` ต้องสร้างจาก `data` ไม่ใช่ `df`

```python
NORM = {c: normalize(df[c]) ...}                              # ❌ ผิด
data = df[...].reset_index(drop=True)
build_text(np.arange(len(data)))   # NORM.iloc[ตำแหน่งของ data] = แถวของ df
```

`data` ถูก `reset_index(drop=True)` **ตำแหน่งจึงไม่ตรงกับ `df` อีกต่อไป**
ข้อความมาจาก `df` แต่ label มาจาก `data` → **จับคู่ผิดทั้งชุด**

**ผลที่วัดได้จริง `acc 0.0997 · f1_macro 0.0539`** ทั้งที่ TF-IDF ธรรมดายังได้ 0.95

> **โมเดลไม่พัง โค้ดพัง** — ตัวเลขต่ำผิดปกติขนาดนี้ให้สงสัยการจับคู่ข้อมูลก่อนเสมอ
> `assert len(NORM["ItemName"]) == len(y)` ถูกใส่ไว้กันพลาดซ้ำ

---

## Cell 8 · Backbone

```python
device = "cuda" if torch.cuda.is_available() else "cpu"
backbone = "BAAI/bge-m3" if device == "cuda" else "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embedder = SentenceTransformer(backbone, device=device)
```

**เลือกโมเดลตามเครื่องอัตโนมัติ** — GPU ใช้ตัวใหญ่ CPU ใช้ตัวเล็ก ไม่ต้องแก้โค้ด

| โมเดล | พารามิเตอร์ | 216k บน CPU | คุณภาพ |
|---|---|---|---|
| `bge-m3` | 568M | ~14 ชม. ❌ | สูงสุด |
| `multilingual-e5-base` | 278M | ~3-4 ชม. | ดี |
| `MiniLM-L12-v2` | 118M | ~1-2 ชม. | พอใช้ |

### `build_text()` — ประกอบข้อความก่อนส่งเข้าโมเดล

```python
def build_text(idx, drop_extra=None):
    out = NORM["ItemName"].iloc[idx].reset_index(drop=True)
    for col, tag in (("CategoryName","หมวด: "), ("SubCategoryName","ซับ: "), ("Brand","brand: ")):
        v = NORM[col].iloc[idx].reset_index(drop=True)
        add = (v.str.strip() != "") & ~drop_extra      # ว่างหรือถูกสั่งตัด = ไม่ต่อ
        out = out.where(~add, out + " | " + tag + v)
    return out.tolist()
```

**ใส่ป้ายชื่อฟิลด์นำหน้า** (`หมวด:` `ซับ:` `brand:`) เพราะ LLM เข้าใจข้อความมีบริบท
`"iphone 15 | หมวด: smartphone | brand: apple"` สื่อความหมายมากกว่าเอามาต่อ ๆ กันเฉย ๆ

**`drop_extra` เป็น array รายแถว** — ใช้ทำ random-drop ใน Cell 9

### ⚠️ ทำไมต้องทำทั้งคอลัมน์ ไม่ใช่ทีละแถว

ของเดิมเขียนแบบนี้

```python
p = [normalize(pd.Series([item]))[0]]      # สร้าง Series ใหม่ทีละค่า
```

**4 ครั้งต่อแถว × 216,006 แถว = สร้าง pandas Series 800,000 ครั้ง**

| | 3,000 แถว | ประมาณการ 216k |
|---|---|---|
| ทีละแถว | 6.56 s | **7.9 นาที** |
| ทั้งคอลัมน์ | 0.01 s | **0.8 วินาที** |

**เร็วขึ้น 563 เท่า** — pandas ออกแบบมาให้ทำทั้งคอลัมน์ เรียกทีละค่าเสีย overhead ทุกครั้ง

---

## Cell 9 · โมเดล 1 — หัวใจของทั้งโน้ตบุ๊ก

```python
rng = np.random.default_rng(42)
t1 = [make_text(r.ItemName, r.CategoryName, r.SubCategoryName, r.Brand,
                drop_extra=(rng.random() < 0.5)) for r in data.itertuples()]
```

### ⭐ Random-drop — แก้ปัญหา train-serving skew

**ตอนเทรนมีข้อมูลครบ 4 คอลัมน์ แต่ตอนใช้จริงมีแค่ `ItemName`**

```
เทรน:     ItemName + CategoryName + SubCategoryName + Brand
ใช้จริง:   ItemName เท่านั้น                    ← สินค้าใหม่ยังไม่มีใคร key หมวด
```

**ถ้าเทรนด้วย 4 ตัวแล้วทำนายด้วยตัวเดียว โมเดลจะเพี้ยน** เพราะไม่เคยเจอข้อมูลหน้าตาแบบนั้นมาก่อน

**วิธีแก้** — สุ่มปิดคอลัมน์เสริม 50% ตอนเทรน ให้โมเดลชินกับทั้งสองแบบ

> ปัญหานี้เรียกว่า **train-serving skew** เป็นสาเหตุอันดับต้น ๆ ที่โมเดลแม่นตอนทดสอบแต่พังตอนใช้จริง

```python
X1 = embedder.encode(t1, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
```

| พารามิเตอร์ | ทำไม |
|---|---|
| `batch_size=64` | ส่งเข้า GPU ทีละ 64 · มากไป VRAM ไม่พอ น้อยไปช้า |
| **`normalize_embeddings=True`** | **ปรับเวกเตอร์ให้ยาว 1 หน่วย** — ทำให้เทียบด้วย cosine similarity ได้ และ linear model ทำงานได้ดีขึ้นมาก |

```python
Xtr, Xte, ytr, yte, itr, ite = train_test_split(X1, y, np.arange(len(y)),
                                                test_size=0.2, random_state=42, stratify=y)
```

| ส่วน | ทำไม |
|---|---|
| `test_size=0.2` | เก็บ 20% ไว้วัด **ห้ามให้โมเดลเห็น** |
| `random_state=42` | รันซ้ำได้ผลเดิม |
| **`stratify=y`** | **คงสัดส่วนหมวดในทั้งสองชุด** — ไม่งั้นหมวดเล็กอาจไม่มีในชุดทดสอบเลย |
| `np.arange(len(y))` | **ลาก index ติดไปด้วย** เพื่อย้อนกลับไปหาแถวต้นฉบับได้ (ใช้ต่อใน Cell 10) |

```python
clf1 = make_clf().fit(Xtr, ytr)
tt = [make_text(data.iloc[i].ItemName, drop_extra=True) for i in ite]
p1 = clf1.predict(embedder.encode(tt, normalize_embeddings=True))
```

**ตอนวัดผลใช้ `drop_extra=True` คือ ItemName ล้วน** — วัดในสภาพเดียวกับตอนใช้งานจริง ไม่ใช่สภาพที่สวยกว่าความจริง

### `make_clf()` — สลับ classifier ได้ที่เดียว

```python
USE_SVC = True
def make_clf():
    return (LinearSVC(C=1.0, class_weight="balanced") if USE_SVC
            else LogisticRegression(max_iter=2000, C=10, class_weight="balanced", n_jobs=-1))
```

| พารามิเตอร์ | ความหมาย |
|---|---|
| `C=1.0` | **ความเข้มของ regularization** — ต่ำ = โมเดลเรียบง่าย กันโอเวอร์ฟิต · สูง = ตามข้อมูลมากขึ้น |
| **`class_weight="balanced"`** | **ถ่วงน้ำหนักหมวดเล็กให้สำคัญเท่าหมวดใหญ่** — ไม่งั้นโมเดลจะทายหมวดใหญ่ตลอดเพราะได้คะแนนดีอยู่แล้ว |
| `max_iter=2000` | default 100 ไม่พอ จะได้ `ConvergenceWarning` แล้วผลต่ำกว่าจริง |

### `confidence()` — แก้ปัญหา SVC ไม่มี `predict_proba`

```python
def confidence(clf, X):
    if hasattr(clf, "predict_proba"):
        p = clf.predict_proba(X)
    else:
        d = clf.decision_function(X)
        e = np.exp(d - d.max(axis=1, keepdims=True))   # softmax บน margin
        p = e / e.sum(axis=1, keepdims=True)
    return clf.classes_[p.argmax(1)], p.max(1)
```

**`LinearSVC` คืน margin (ระยะห่างจากเส้นแบ่ง) ไม่ใช่ความน่าจะเป็น** — ฟังก์ชันนี้แปลงด้วย softmax ให้เทียบกันได้

**`d - d.max()` ก่อน `exp` เป็นเทคนิคกัน overflow** — ถ้า `d` ใหญ่ `exp(d)` จะล้น `inf` แต่ลบค่าสูงสุดออกก่อนทำให้ผลลัพธ์เท่าเดิมและไม่ล้น

> ⚠️ **ค่าที่ได้ใช้เรียงลำดับได้ แต่ไม่ใช่ความน่าจะเป็นจริง** — `0.80` ของ SVC กับของ LogisticRegression คนละความหมาย

---

## Cell 10 · โมเดล 2 — Full

```python
t2 = [make_text(r.ItemName, r.CategoryName, r.SubCategoryName, r.Brand) for r in data.itertuples()]
clf2 = make_clf().fit(X2[itr], ytr)
```

**เทรนและทำนายด้วยครบทุกคอลัมน์** — ใช้ `itr`/`ite` ชุดเดิมจาก Cell 9 เพื่อให้เทียบกันได้ตรง ๆ

| | M1 | M2 |
|---|---|---|
| ตอนเทรน | สุ่มปิดคอลัมน์เสริม 50% | ครบเสมอ |
| ตอนทำนาย | **`ItemName` ล้วน** | ครบเสมอ |
| ใช้เมื่อ | **สินค้าใหม่ที่ยังไม่มีหมวด** | ของเดิมที่มีหมวดอยู่แล้ว |

**M2 จะแม่นกว่าเสมอ แต่ใช้กับสินค้าใหม่ไม่ได้** — เป็นเพดานบนไว้ดูว่าถ้ามีข้อมูลครบจะดีได้แค่ไหน

---

## Cell 11 · เทียบ + เซฟ

```python
meta = {"backbone": backbone, "label_col": LABEL_COL,
        "types": TYPES, "platforms": PLATFORMS, "disambiguate": DISAMBIGUATE,
        "classes": sorted(set(y))}
joblib.dump({**meta, "clf": clf1}, "model1_itemname.joblib")
```

**เก็บกฎไปกับโมเดลด้วย** — ไม่งั้นวันหน้าเปิดไฟล์มาแล้วไม่รู้ว่าโมเดลนี้เทรนด้วยกฎชุดไหน ทำนายออกมาเป็นหมวดอะไรได้บ้าง

**`joblib` ไม่ใช่ `pickle`** — เร็วกว่ามากกับ numpy array ขนาดใหญ่

---

## Cell 12 ⭐ · หา label ที่ key ผิด

**นี่คือขั้นที่มีมูลค่าทางธุรกิจสูงสุด**

```python
pred, conf = confidence(clf1, X1)
CUT = float(np.quantile(conf, 0.60))
suspect = data[(data.Cat_pred != data[LABEL_COL]) & (data.conf >= CUT)]
```

### ตรรกะ

```
โมเดลทาย A · กฎบอก B · โมเดลมั่นใจสูง
                ↓
   แปลว่าอย่างใดอย่างหนึ่งผิด และน่าจะเป็นกฎ
```

**ถ้าโมเดลเรียนจากตัวอย่างส่วนใหญ่แล้วมั่นใจว่าแถวนี้ควรเป็น A** ทั้งที่กฎบอก B
→ มักแปลว่า **แถวนี้คือข้อยกเว้นที่กฎครอบไม่ถึง**

### ทำไมใช้ quantile ไม่ใช่เลขตายตัว

```python
Q = 0.60
CUT = float(np.quantile(conf, Q))     # เอา 40% ที่มั่นใจสุด
```

**`0.80` ตายตัวใช้ไม่ได้** เพราะค่า confidence ของ SVC มาจาก softmax บน margin ซึ่งสเกลต่างจาก LogisticRegression
**quantile ปรับตามการกระจายจริงของข้อมูล** จึงใช้ได้กับทั้งสอง classifier

### ใช้ผลยังไง

ออกเป็น `suspect.csv` → **ให้คนตรวจ** → แก้กฎที่ Cell 4 → รันใหม่

**นี่คือวงจรที่ทำให้ label สะอาดขึ้นเรื่อย ๆ** ซึ่งคุ้มกว่าการไปทำ fine-tune

---

## Cell 13 · Fine-tune (ยังไม่ทำ)

**ต่างจาก Cell 9 ตรงที่ปรับ weights ของ LLM เอง ไม่ใช่แค่เรียน classifier**

| | Cell 9 (ที่ทำอยู่) | Cell 13 Fine-tune |
|---|---|---|
| LLM | ❄️ แช่แข็ง | 🔥 ปรับ weights |
| ทรัพยากร | CPU ได้ | **ต้อง GPU** |
| เวลา | นาที | ชั่วโมง |

> 🔑 **fine-tune ดีขึ้นต่อเมื่อ label สะอาดก่อน** — ถ้า label ยัง noisy จะเรียนของผิดแม่นขึ้น = **แย่ลง**

**ลำดับความคุ้ม**

```
1. embedding + classifier (baseline)   ← ทำก่อนเสมอ
2. label สะอาด + เพิ่มข้อมูล            ← คุ้มสุด
3. fine-tune                           ← ท้ายสุด
```

---

# ส่วนที่ 3 · ใช้โมเดลอะไร ทำไมเลือกแบบนี้

## สถาปัตยกรรม 2 ชั้น

```
ItemName  →  [ LLM Embedding ]  →  เวกเตอร์ 1024 มิติ  →  [ LinearSVC ]  →  หมวด
                ❄️ แช่แข็ง                                   🔥 เรียนตรงนี้
```

**ชั้นแรกไม่เรียนอะไรเลย · ชั้นสองเป็นโมเดลเชิงเส้นธรรมดา**

## ชั้นที่ 1 · ทำไมใช้ LLM Embedding

**ปัญหาคือชื่อสินค้าเขียนไม่เหมือนกันแต่หมายถึงของเดียวกัน**

```
"iPhone 15 Pro Max"  ·  "ไอโฟน 15 โปรแม็กซ์"  ·  "IP15PM"
```

| วิธี | จับได้ไหม | ทำไม |
|---|---|---|
| keyword | ❌ | ต้องเขียนทุกตัวสะกด |
| TF-IDF | บางส่วน | เทียบตัวอักษร ไม่เข้าใจความหมาย |
| **LLM embedding** | ✅ | **เข้าใจว่าคำต่างกันแต่ความหมายใกล้กัน** |

**`bge-m3` รองรับหลายภาษารวมไทย** จึงเทียบ `iPhone` กับ `ไอโฟน` ได้

### ทำไมไม่ fine-tune

| | แช่แข็ง | Fine-tune |
|---|---|---|
| ต้องมี label สะอาด | ไม่ต้อง | **ต้อง** |
| ทรัพยากร | CPU ได้ | ต้อง GPU |
| เสี่ยงเรียนของผิด | ต่ำ | **สูง ถ้า label ยัง noisy** |

**ตอนนี้ label มาจากกฎที่เรารู้ว่ายังมีบั๊ก** — fine-tune ตอนนี้คือสอนให้โมเดลจำข้อผิดพลาดได้แม่นขึ้น

## ชั้นที่ 2 · ทำไมใช้ LinearSVC

**วัดจริงบน 200,000 แถว**

| classifier | accuracy | **f1_macro** | เวลา | `predict_proba` |
|---|---|---|---|---|
| **LinearSVC** | 0.9629 | **0.9519** | 115s | ❌ |
| LogisticRegression | 0.9522 | 0.9336 | 384s | ✅ |
| ComplementNB | 0.8705 | 0.8193 | 57s | ✅ |
| SGD log_loss | 0.8993 | 0.7757 | 89s | ✅ |

**LinearSVC ชนะ 1.8 จุด และเร็วกว่า 3.3 เท่า** · `sd = 0.0005` ผลนิ่งมาก

### แต่ละตัวเป็นโมเดลประเภทไหน

| | ตระกูล | เส้นแบ่ง | จุดขาย |
|---|---|---|---|
| **LinearSVC** | linear · discriminative · **margin-based** | ตรง | เลือกเส้นที่ห่างจากจุดใกล้สุดมากที่สุด · ทน outlier |
| LogisticRegression | linear · discriminative · probabilistic | ตรง | ได้ความน่าจะเป็นจริง · อธิบายได้ |
| SGDClassifier | **วิธีเทรน ไม่ใช่โมเดล** | ตรง | `loss="log_loss"` = LR · scale ถึงล้านแถว |
| ComplementNB | **generative** · Naive Bayes | โค้งตาม distribution | ออกแบบมาแก้หมวดเบ้ |

### ทำไมไม่ใช้ tree / gradient boosting

**เวกเตอร์ 1024 มิติ (หรือ TF-IDF 50,000 มิติ) เป็นสนามของ linear model**

Gradient boosting แบ่งทีละ feature ซึ่งไม่เหมาะกับข้อมูลมิติสูงที่ความหมายกระจายอยู่ในทุก dimension พร้อมกัน

### ทำไมไม่ใช้ neural network

**ข้อมูล 216k แถว · 294 หมวด · feature เป็นเวกเตอร์ที่ normalize แล้ว** — linear model พอ และ

- เทรนใน 2 นาที ไม่ใช่ 2 ชั่วโมง
- ไม่ต้องจูน architecture / learning rate / epochs
- **อธิบายได้ว่าทำไมตัดสินแบบนั้น**

**ถ้า linear ได้ 0.95 แล้ว การไปเพิ่มความซับซ้อนเพื่อได้อีก 1 จุดไม่คุ้ม** — เวลาเดียวกันเอาไปทำ label ให้สะอาดได้ผลมากกว่า

## ทำไมวัดด้วย Macro-F1 ไม่ใช่ Accuracy

```
                  accuracy   f1_macro
5,000 แถว          0.8730     0.6922
200,000 แถว        0.9522     0.9336
```

**f1 ขยับ +24 จุด ส่วน accuracy ขยับแค่ +8**

| | นับยังไง | ปัญหา |
|---|---|---|
| **accuracy** | ถูกกี่แถวจากทั้งหมด | **ทายหมวดใหญ่ถูกก็ได้คะแนนสูง** |
| **f1_macro** | เฉลี่ย F1 ของทุกหมวดเท่า ๆ กัน | หมวดเล็กพังจะเห็นทันที |

หมวดกระจายไม่เท่ากันมาก — `Accessory and Others` กับ `Smart Phone` รวมกันเกินครึ่ง
**accuracy 0.87 ดูดี แต่ f1 0.69 บอกว่าหมวดเล็กแทบใช้ไม่ได้**

> **บทเรียน** — ตอนเห็น f1 0.69 ที่ 5,000 แถว ถ้าสรุปว่า "โมเดลไม่ดี ต้องใช้ตัวใหญ่กว่า" จะผิด
> **ปัญหาคือข้อมูลไม่พอ ไม่ใช่โมเดลไม่พอ** — เพิ่มข้อมูลอย่างเดียวได้ 0.93

## ⚠️ ข้อจำกัดที่ต้องรู้ก่อนตีความตัวเลข

**label มาจากกฎ keyword · TF-IDF ก็ทำงานด้วย character n-gram**

**0.95 แปลว่า "ถอดกฎเดิมกลับมาได้ 95%" ไม่ใช่ "จัดหมวดถูก 95%"**

ซึ่งขัดกับเป้าหมายอยู่กลาย ๆ — เป้าหมายคือแก้หมวดที่ผิด **แต่ถ้าโมเดลถอดกฎได้เป๊ะ ก็สืบทอดข้อผิดพลาดมาด้วย**

**จะวัดว่าดีขึ้นจริงต้องมี label ที่คนตรวจแล้ว** — ซึ่งเป็นเหตุผลที่ Cell 12 สำคัญที่สุด

---

## สรุปสั้น ๆ ว่าแต่ละขั้นเพื่ออะไร

| ขั้น | เพื่ออะไร | ถ้าข้ามจะเป็นยังไง |
|---|---|---|
| Normalize | ให้ข้อความเทียบกันได้ | keyword ไม่ตรงเพราะตัวพิมพ์/อักขระพิเศษ |
| กฎ | **สร้าง label — ML ไม่มี label เรียนไม่ได้** | ไม่มีอะไรให้เทรน |
| ตัดหมวด < 5 | ให้ split/cross-val ทำงานได้ | พังตอน `stratify` |
| Embedding | ให้เข้าใจคำที่เขียนต่างกันแต่ความหมายเดียวกัน | จับได้แค่ตัวสะกดที่ตรงเป๊ะ |
| **Random-drop** | **ให้ชินกับการมีแค่ ItemName** | **แม่นตอนทดสอบ พังตอนใช้จริง** |
| `stratify` | คงสัดส่วนหมวด | หมวดเล็กหายจากชุดทดสอบ |
| `class_weight` | หมวดเล็กไม่ถูกกลบ | โมเดลทายหมวดใหญ่ตลอด |
| Macro-F1 | เห็นว่าหมวดเล็กพัง | หลงคิดว่าโมเดลดีแล้ว |
| **Cell 12** | **หา label ที่ผิด → แก้กฎ → วนซ้ำ** | **ติดอยู่ที่คุณภาพของกฎตั้งต้นตลอดไป** |

---

## เชื่อมกับโน้ตอื่น

[[ITEC Category Toolkit]] · [[ITEC Category Model (ML)]] · [[ITEC Item Category Mapping (SQL to Python)]] · [[ITEC Flag & Category Review Guide]] · [[ITEC Model - Run on EC2 Guide]] · [[Python Libraries]] · [[ITEC - Data Dictionary]] · [[ITEC Model - Fine-tune Design]]
