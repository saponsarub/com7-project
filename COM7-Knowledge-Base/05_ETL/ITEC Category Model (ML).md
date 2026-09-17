# ITEC Category Model (ML)

> [!warning] โน้ตนี้เป็น**รุ่นเก่า** — เก็บไว้เป็นบันทึกสิ่งที่เคยลอง อย่าใช้เป็นคู่มือ
> เขียนไว้ 2026-09-14 · ตรวจสอบใหม่ 2026-09-17 แล้วพบว่าไม่ตรงกับงานจริงอีกต่อไป
>
> **งานปัจจุบันอยู่ที่** `scripts/itec/dimension/` -> [[ITEC Product Dimension]]
>
> | | โน้ตนี้ (เก่า) | งานจริงตอนนี้ |
> |---|---|---|
> | โฟลเดอร์ | `scripts/itec/category/` | `scripts/itec/dimension/` |
> | notebook | `itec_recategorization_full.ipynb` | `itec_dimension.ipynb` (33 cell) |
> | กฎอยู่ไหน | ฝังใน notebook | `rules.yaml` + `dimension.py` |
> | จำนวนหมวด | 14 | **20** |
> | ชื่อหมวดที่เลิกใช้แล้ว | `Accessory and Others` · `Service and Others` · `Adapter/Charger/Powerbank` | `Others` · `IT Accessories` · `Powerbank` · `Smart Home` · `Personal Care & Health` · `Lifestyle & Hobby` |
> | คอลัมน์กลาง | ไม่มี | `Item_Type` · `Item_Host` · `Item_Platform` |
> | สถานะ ML | เขียนไว้ว่าเทรนแล้ว | **ยังไม่เคยรัน** — `RUN_ML = False` ทุกเซลล์ |
>
> **⚠️ ขั้น 3 + ขั้น 4 ในโน้ตนี้มี target leakage อย่าลอกไปใช้**
> label (`Category_std`) สร้างจาก `CategoryName` แล้วเอา `CategoryName` ใส่กลับเป็น feature
> -> accuracy จะเข้าใกล้ 1.0 แต่โมเดลไม่ได้เรียนอะไร มันแค่อ่านค่าเดิมคืนมา
>
> ตัวโน้ตยังขัดแย้งกันเองด้วย — หัวโน้ตเขียน `Feature: ItemName (ตอน predict มีแค่นี้)` แต่ขั้น 4 ใช้ 2 factor

---

## เป้าหมาย

จาก `rpt.dim_item_itec` (216,009 แถว) จัดหมวดสินค้าใหม่ แก้ปัญหา category เดิมที่ **key ผิด** และ **ซ้ำซ้อน** (ชื่อต่างแต่หมวดเดียวกัน)

- **Feature:** `ItemName` (ตอน predict มีแค่นี้)
- **Target:** หมวดที่ตั้งเอง (จาก IS_ flags → จัดกลุ่ม) หรือ `Main_Product_Dimension` (14 หมวด)
- **Backbone:** LLM embedding — **ไม่ fine-tune** (LLM แช่แข็ง เรียนแค่ classifier)

### ข้อค้นพบสำคัญ
```
SubCategory ที่ชี้ไปหลาย Category: 129 / 1,708 (8%)
```
→ 92% เป็น lookup ตรงได้ · 8% กำกวมต้องใช้ ML · แต่ predict มีแค่ ItemName → ต้อง ML จาก ItemName ล้วน

---

## 🗺️ ภาพรวม 8 ขั้น

```
ItemName → ① Normalize → ② Flags → ③ จัดหมวด(label) → ④ Embedding
                                                          ↓
        ⑧ Fine-tune ← ⑦ label สะอาด ← ⑥ ประเมิน ← ⑤ เทรน Classifier
```

| ขั้น | ทำอะไร | เรียนไหม | notebook |
|---|---|---|---|
| ① Normalize | ทำความสะอาดข้อความ | — | Cell 3 |
| ② Flags | คำ → IS_ flags (keyword) | ❌ กฎ | Cell 4 ✏️ |
| ③ Label | รวม flags → หมวดใหญ่ | ❌ กฎ | Cell 6 ✏️ |
| ④ Embedding | LLM → เวกเตอร์ (แช่แข็ง) | ❌ | Cell 8 |
| ⑤ Classifier | เวกเตอร์ → หมวด | ✅ **เรียนตรงนี้** | Cell 9-10 |
| ⑥ ประเมิน | Accuracy + Macro-F1 | — | Cell 11 |
| ⑦ label สะอาด | จับ key ผิด → แก้ → retrain | — | Cell 12 |
| ⑧ Fine-tune | ปรับ weights LLM (option) | ✅ | Cell 13 |

> **หัวใจ:** สิ่งที่เรียนจริงมีแค่ขั้น ⑤ · ② ③ เป็นกฎที่ตั้งเอง · ④ ใช้ LLM สำเร็จรูป — **นี่ไม่ใช่ fine-tune**

---

## 🎚️ 3 ระดับที่ตั้งเองได้

| ระดับ | คือ | ตัวอย่าง | notebook |
|---|---|---|---|
| 1. **Flag** (ชื่ออังกฤษ) | มี flag อะไรบ้าง | `IS_iPhone`, `IS_Case` | Cell 4 |
| 2. **คำใน flag** (ไทย/eng) | keyword ที่ติด flag | `IS_Charger`: `["charger","ที่ชาร์จ"]` | Cell 4 |
| 3. **จัดหมวด** (label) | flag ไหนรวมเป็นหมวด | `IS_Case` → "อุปกรณ์เสริม" | Cell 6 |

---

## Backbone ที่แนะนำ

| Model | ขนาด | 216k บน CPU | คุณภาพ |
|---|---|---|---|
| bge-m3 | 2GB | ~14 ชม. ❌ | สูงสุด (ใช้กับ GPU) |
| multilingual-e5-base | 1GB | ~3-4 ชม. | ดี |
| MiniLM-L12-v2 | 470MB | ~1-2 ชม. | พอใช้ (CPU) |
| TF-IDF | - | วินาที | พอใช้ (+override) |

สถาปัตยกรรม: `ItemName → [LLM embedding] → เวกเตอร์ 1024 มิติ → [LogisticRegression] → หมวด`

---

## ⚠️ ปัญหาที่เจอ: "iPhone Case → มั่วเป็น phone"

**สาเหตุ:** accessory มีชื่อสินค้าหลักปน ("iPhone Case") → คำ brand เด่นกว่าคำประเภท → โมเดลลากไป phone

**วิธีแก้ — keyword override (ทับ ML):**
- คำบอกประเภทชัด (case/charger/shipping/applecare) → rule ทับผล ML ทันที
- ใช้ `whole_word` กันคำสั้นเจอในคำอื่น (`pin` ใน "shi**ppin**g")

| Override group | keyword | → หมวด |
|---|---|---|
| Accessory | case, cover, เคส, charger, สายชาร์จ, power bank, stand | Accessory and Others |
| Service | shipping, ค่าส่ง, ค่าบริการ, repair | Service and Others |
| Warranty | applecare, care+, ประกัน, insurance | Warranty and Insurance |

**Flag เสริม (multi-label):** `IS_Promotion` · `IS_Demo` · `IS_Gaming` · `IS_Refurbished`

---

## 🔬 2 โมเดลที่เทรนเทียบ

| แบบ | เทรนด้วย | predict ใส่ | เมื่อไหร่ใช้ |
|---|---|---|---|
| **M1 · Random-drop** | ItemName + สุ่มปิด extra 50% | **แค่ ItemName** | ใช้จริง |
| **M2 · Full** | ItemName + Category + Sub + Brand | **ครบทุกตัว** | ถ้ามี Category ตอน predict |

> ⚠️ **train-serving skew:** อย่าเทรน 4 ตัวแล้ว predict ตัวเดียวตรง ๆ (เพี้ยน) — M1 ใช้ random-drop ให้โมเดลชินกับการมีแค่ ItemName · Model ที่ใช้ = **LogisticRegression** (เบา เร็ว อธิบายได้ · ทางเลือก LinearSVC/LightGBM)

---

## ⑤ Classifier vs ⑧ Fine-tune

| | ⑤ Embedding + Classifier (ที่ทำ) | ⑧ Fine-tune |
|---|---|---|
| ตัว LLM | ❄️ แช่แข็ง | 🔥 ปรับ weights |
| ทรัพยากร | เบา (CPU ได้) | ต้อง GPU |
| นี่คือ fine-tune ไหม | **ไม่ใช่** | ใช่ |

**ลำดับความคุ้ม:**
```
1. embedding + classifier (baseline)   ← ทำก่อนเสมอ
2. label สะอาด + เพิ่มข้อมูล + override  ← คุ้มสุด
3. fine-tune                           ← ท้ายสุด
```

> 🔑 fine-tune ดีขึ้น **ต่อเมื่อ label สะอาดก่อน** — ถ้า label ยัง noisy (จาก rule ที่ผิด) จะเรียนของผิดแม่นขึ้น = **แย่ลง** · สำหรับงานนี้ การทำ label สะอาดมักช่วยมากกว่า fine-tune

---

### ขั้น 0 · ตั้ง env + โหลด backbone (แก้ปัญหา Windows)

```python
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DISABLE_XET"] = "1"       # กันค้างตอน "reconstructing" บน Windows

import pandas as pd, numpy as np, joblib, torch
from sentence_transformers import SentenceTransformer

token = os.getenv("HF_TOKEN", "") or None
device = "cuda" if torch.cuda.is_available() else "cpu"

# CPU → ใช้ตัวเบา (bge-m3 ช้า ~14 ชม.สำหรับ 216k) · GPU → bge-m3 ได้
backbone = "BAAI/bge-m3" if device == "cuda" else "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embedder = SentenceTransformer(backbone, device=device, token=token)
print(f"backbone={backbone} · device={device}")

def clean(s):   # หรือใช้ normalize_text_series ที่มีอยู่แล้ว
    return (s.fillna("").astype(str).str.lower()
             .str.replace(r"[^\w\s/&+.-]", " ", regex=True)
             .str.replace(r"\s+", " ", regex=True).str.strip())
```

### ขั้น 1 · Taxonomy มาตรฐาน จาก IS_ flags ใน SQL

```python
import re
sql = open(r"D:\ci_item_category.sql", encoding="utf-8").read()   # ← path ไฟล์จริง
flat = re.sub(r"\s+", " ", sql)

# ดึงชื่อ flag IS_ ทั้งหมด (รองรับ alias มี/ไม่มี [ ])
standard_taxonomy = sorted(set(
    re.findall(r"END\s+AS\s+\[?(IS_[A-Za-z_]+)\]?", flat, re.I)
))
print(f"taxonomy มาตรฐาน: {len(standard_taxonomy)} หมวด")
print(standard_taxonomy[:10])
# ถ้าอยากใช้ Main/Sub Dimension แทน ก็ดึงจากคอลัมน์นั้นของ df แทน
```

### ขั้น 2 · หา Category ซ้ำซ้อน (embedding + union-find)

```python
cats = df.CategoryName.dropna().unique().tolist()
cat_emb = embedder.encode(cats, normalize_embeddings=True)
sim = cat_emb @ cat_emb.T          # cosine (normalize แล้ว = dot product)

THRESHOLD = 0.90                   # ⚠️ ตั้งสูง! 0.85 หลวมเกิน เกิด false merge
pairs = [(i, j, float(sim[i, j]))
         for i in range(len(cats)) for j in range(i+1, len(cats))
         if sim[i, j] >= THRESHOLD]

# union-find จัดกลุ่มชื่อที่ควร merge
parent = list(range(len(cats)))
def find(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
for i, j, _ in pairs: parent[find(i)] = find(j)

groups = {}
for idx in range(len(cats)): groups.setdefault(find(idx), []).append(cats[idx])

# canonical = ชื่อที่เจอบ่อยสุดในข้อมูลจริง (ดีกว่าเลือกสั้นสุด)
freq = df.CategoryName.value_counts()
merge_mapping = {}
for members in groups.values():
    canonical = max(members, key=lambda c: freq.get(c, 0))
    for m in members: merge_mapping[m] = canonical

# ตรวจตาด้วยตาก่อนใช้จริง!
for members in groups.values():
    if len(members) > 1:
        print(f"MERGE → {max(members, key=lambda c: freq.get(c,0))!r}: {members}")
```

> ⚠️ **ต้องตรวจด้วยตา (human review) ก่อน apply** — union-find อาจ merge ผิดถ้า threshold ต่ำ (ทดสอบพบว่า 0.85 ทำให้หมวดไม่เกี่ยวกันหลุดเข้ากลุ่มเดียว) เริ่มที่ 0.90-0.92 แล้วปรับ

### ขั้น 3 · สร้าง Training Label สะอาด

```python
df["Category_std"] = df.CategoryName.map(merge_mapping).fillna(df.CategoryName)

# ใช้เฉพาะหมวดที่มีตัวอย่างพอ (>=5) เป็นตัวสอน
vc = df.Category_std.value_counts()
train = df[df.Category_std.isin(vc[vc >= 5].index)].copy()
print(f"training: {len(train):,} แถว · {train.Category_std.nunique()} หมวด")
```

### ขั้น 4 · เทรน (embedding ItemName + Category เดิม → มาตรฐาน)

```python
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# feature = 2 factor: ItemName + Category(เดิม)
text = (clean(train.ItemName) + " | หมวดเดิม: " + clean(train.CategoryName)).tolist()
X = embedder.encode(text, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
y = train.Category_std.values

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
clf = LogisticRegression(max_iter=2000, C=10, class_weight="balanced", n_jobs=-1)
clf.fit(X_tr, y_tr)

print(f"Accuracy: {accuracy_score(y_te, clf.predict(X_te)):.4f}")
print(classification_report(y_te, clf.predict(X_te), zero_division=0))
joblib.dump({"backbone": backbone, "clf": clf, "merge_mapping": merge_mapping}, "regroup_model.joblib")
```

### ขั้น 5 · ตรวจจับ Item ที่ Key ผิด

```python
# embed ทั้งชุด (ระวัง: 216k บน CPU ช้า — ทำ batch/subset)
text_all = (clean(df.ItemName) + " | หมวดเดิม: " + clean(df.CategoryName)).tolist()
X_all = embedder.encode(text_all, batch_size=64, show_progress_bar=True, normalize_embeddings=True)

proba = clf.predict_proba(X_all)
df["Category_pred"] = clf.classes_[proba.argmax(axis=1)]
df["confidence"]    = proba.max(axis=1)

# โมเดลทายต่างจากเดิม + มั่นใจสูง = น่าจะ key ผิดจริง
suspect = df[(df.Category_pred != df.Category_std) & (df.confidence >= 0.80)]
suspect = suspect.sort_values("confidence", ascending=False)
print(f"item น่าสงสัยว่า key ผิด: {len(suspect):,} รายการ")
suspect[["ItemName","CategoryName","Category_pred","confidence"]].to_csv(
    "suspect_miscategorized.csv", index=False, encoding="utf-8-sig")
```

### ขั้น 6 · ทำนายของใหม่ (มี override กันเคส accessory)

```python
# ใช้ฟังก์ชันสำเร็จ apply_keyword_category_override คู่กับ clf
kw = {"Accessory and Others": ["case","cover","charger","cable","เคส","ฟิล์ม","สายชาร์จ"],
      "Service and Others":    ["shipping","ค่าส่ง","ค่าบริการ","repair"]}

def ml_predict(name):
    emb = embedder.encode([name.lower()], normalize_embeddings=True)
    return clf.predict(emb)[0]

def predict(item_name, old_category=""):
    # rule override ก่อน (แก้ "iPhone Case → phone")
    return apply_keyword_category_override(item_name, kw, fallback_fn=ml_predict)

print(predict("iPhone 15 Case Clear"))   # → Accessory (rule)
print(predict("Samsung SSD 980 1TB"))    # → ML
```

---

---

## ขั้นตอนเทรนจริง + ค่าที่ตั้ง

> วัดจริง 2026-09-14 · โค้ด `scripts/itec/category/benchmark_models.py`

### เส้นทางทั้งหมด 5 ขั้น

```
1. โหลด CSV            dim_item_itec.csv  (216,009 แถว)
2. สร้าง label         itec_mapper.run(df, strict=True)  → Main_Product_Dimension
3. ทำความสะอาด        ตัดแถว ItemName ว่าง · normalize ชื่อคอลัมน์
4. แปลงข้อความเป็นเลข   TF-IDF หรือ embedding
5. เทรน + วัด          LogisticRegression + 5-fold cross-validation
```

**ขั้น 2 คือจุดที่คนมองข้าม** — label ไม่ได้มาจากไหน ต้องสร้างเอง งานนี้ใช้ rule-based เดิมที่แปลงจาก SQL ไว้แล้ว → [[ITEC Item Category Mapping (SQL to Python)]]

### ค่าที่ตั้งได้ทั้งหมด

| ค่า | ตั้งเท่าไหร่ | ทำไม |
|---|---|---|
| **จำนวนแถว** `-n` | **200,000** | ผลต่างจาก 5,000 มหาศาล ดูหัวข้อถัดไป |
| **วิธีสุ่ม** | คงสัดส่วนหมวด (stratified) | สุ่มตรง ๆ หมวดเล็กหายหมด แล้ววัดได้ตัวเลขหลอกตัวเอง |
| `random_state` | `42` | ให้รันซ้ำได้ผลเดิม · เทียบโมเดลต้องใช้ชุดเดียวกัน |
| **analyzer** | `char_wb` | **ชื่อสินค้าไทยไม่มีเว้นวรรค** ตัดคำแบบ `word` ใช้ไม่ได้ |
| **ngram_range** | `(2, 4)` | จับ 2–4 ตัวอักษร · สั้นกว่านี้ไม่มีความหมาย ยาวกว่านี้ feature บานและช้า |
| **min_df** | `2` | ตัดคำที่โผล่ครั้งเดียว ลด noise และขนาด |
| **max_features** | `50,000` | เพดาน RAM · 200k × 50k sparse ใช้ ~3.3 GB ตอน 5-fold |
| **classifier** | `LogisticRegression` | เบา เร็ว อธิบายได้ว่าคำไหนดันไปหมวดไหน |
| **max_iter** | `2000` | default 100 ไม่พอ จะเตือน `ConvergenceWarning` แล้วผลต่ำกว่าจริง |
| **cv** | `5` fold | ได้ค่า sd มาดูว่าผลนิ่งไหม |
| **scoring** | `accuracy` + **`f1_macro`** | **ต้องดู f1_macro เป็นหลัก** |

### ผลจริง — จำนวนข้อมูลสำคัญกว่าที่คิดมาก

| | 5,000 แถว | 200,000 แถว | ขยับ |
|---|---|---|---|
| accuracy | 0.8730 | **0.9522** | +7.9 จุด |
| **f1_macro** | 0.6922 | **0.9336** | **+24.1 จุด** |
| sd | 0.0078 | **0.0006** | นิ่งขึ้นมาก |
| เวลา fit | 6.8 วิ | 160.2 วิ | |

**f1_macro ขยับมากกว่า accuracy 3 เท่า** เพราะปัญหาที่ 5,000 แถวคือหมวดเล็กไม่มีตัวอย่างพอ

```
Insurance        15 →   600 แถว
Console Gaming   20 →   826
Software         24 →   976
```

> **บทเรียน** — ตอนเห็น f1 = 0.69 ที่ 5,000 แถว ถ้าสรุปว่า "โมเดลไม่ดี ต้องใช้โมเดลใหญ่กว่า" จะผิด **ปัญหาคือข้อมูลไม่พอ ไม่ใช่โมเดลไม่พอ** · เพิ่มข้อมูลอย่างเดียวได้ 0.93

### ทำไมต้องดู f1_macro ไม่ใช่ accuracy

หมวดกระจายไม่เท่ากันมาก — `Accessory and Others` กับ `Smart Phone` รวมกันเกินครึ่ง

| | นับยังไง | ผล |
|---|---|---|
| **accuracy** | ถูกกี่แถวจากทั้งหมด | **ทายหมวดใหญ่ถูกก็ได้คะแนนสูง** |
| **f1_macro** | เฉลี่ย F1 ของทุกหมวดเท่า ๆ กัน | **หมวดเล็กพังจะเห็นทันที** |

ที่ 5,000 แถว accuracy 0.87 ดูดี แต่ f1 0.69 บอกว่าหมวดเล็กแทบใช้ไม่ได้

### ⚠️ ข้อจำกัดของตัวเลขพวกนี้

**label มาจาก rule-based ที่เป็น keyword matching และ TF-IDF ก็ทำงานด้วย character n-gram**

**0.93 จึงแปลว่า "ถอดกฎ keyword เดิมกลับมาได้ 93%" ไม่ใช่ "จัดหมวดถูก 93%"**

ซึ่งขัดกับเป้าหมายของงานอยู่กลาย ๆ — เป้าหมายคือ**แก้หมวดเดิมที่ key ผิดและซ้ำซ้อน** แต่ถ้าโมเดลถอดกฎเดิมได้เป๊ะ **ก็สืบทอดข้อผิดพลาดเดิมมาด้วย**

**จะวัดว่าดีขึ้นจริงต้องมี label ที่คนตรวจแล้ว** ไม่ใช่ label ที่กฎสร้าง → ตรงกับที่โน้ตนี้บอกไว้ว่า "label สะอาดก่อน ค่อย fine-tune"

ตัวเลขพวกนี้ยังมีประโยชน์สำหรับ**เทียบโมเดลกันเอง** เพราะทุกตัววัดกับ target เดียวกัน

### วิธีรัน

```bash
cd C:\Users\Sapon.S\Downloads
python C:\Projects\my-first-project\scripts\itec\category\benchmark_models.py -n 5000
python ...\benchmark_models.py --skip-embed -n 200000      # TF-IDF อย่างเดียว
```

สคริปต์เรียงผลตาม `f1_macro` และเซฟลง `benchmark_result.csv`

### กับดักจาก pandas 3 ที่เจอจริง

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| `AttributeError: no attribute 'Main_Product_Dimension'` | **pandas 3 ตัดคอลัมน์ที่ใช้ group ออกจากผล `groupby.apply`** | ใช้ลูปธรรมดาแทน apply |
| `TypeError: only integer scalar arrays...` | **pandas 3 คืน `ArrowExtensionArray`** ซึ่ง sklearn index ด้วย array ไม่ได้ | `.to_numpy(dtype=object)` |
| `KeyError: 'ItemName'` | CSV ที่ export มาใช้ `item_name` ไม่ใช่ชื่อจาก view | `itec_mapper.normalize_columns()` map ให้อัตโนมัติ |
| `import mapper` ไปโดน package อื่น | **anaconda มี package ชื่อ `mapper`** | เปลี่ยนชื่อเป็น `itec_mapper.py` + `sys.path.insert` |

---

## สิ่งที่ต้องทำต่อ

- [ ] ตัดสิน taxonomy: 67 IS_ flags / Main_Product_Dimension (14) / ออกแบบเอง
- [ ] เติม FLAG_RULES ให้ครบ + จัด MY_TAXONOMY (Cell 4, 6)
- [ ] เทสต์ subset 5,000 ดู Accuracy + Macro-F1 ก่อนรันเต็ม
- [ ] รันเต็มบน GPU (EC2/Colab) → เซฟ embedding .npy → [[ITEC Model - Run on EC2 Guide]]
- [ ] ทำ label สะอาด (suspect list) ก่อนพิจารณา fine-tune
- [ ] ถ้า "อื่นๆ"/default บวม → เพิ่ม flag/keyword

---



---

# ภาคผนวก: Fine-tune Design (รายละเอียด)

> ยุบจากไฟล์ `ITEC Model - Fine-tune Design` (2026-09-16)

> ออกแบบการ fine-tune backbone + วิธีพิสูจน์ว่าคุ้มหรือไม่ — 2026-09-15
> **โปรเจกต์แยก** `scripts/itec/finetune/` · ต่อจาก [[ITEC Category Toolkit]]

```
scripts/itec/finetune/
├── finetune_notebook.ipynb      ตั้งค่าที่ Cell 2 ที่เดียว
├── finetune.py
├── sync_rules.py                ดึงกฎจาก ../category + build zip
├── type_platform.py  .yaml      **สำเนา ห้ามแก้ที่นี่**
└── _data/  _out/
```

**แยกจาก `category/` เพราะเป็นคนละงาน** แต่ยังใช้กฎชุดเดียวกันเพื่อสร้าง label
`sync_rules.py` คัดลอกกฎมาตอน build — **กฎมีที่เดียวคือ `../category/`**

---

## ต่างจากของเดิมตรงไหน

```
เดิม   ItemName ─► [ backbone ] ─► เวกเตอร์ ─► [ LinearSVC ] ─► หมวด
                    ❄️ แช่แข็ง                   🔥 เรียนตรงนี้

ใหม่   ItemName ─► [ backbone ] ─► เวกเตอร์ ─► [ LinearSVC ] ─► หมวด
                    🔥 ปรับด้วย                  🔥 เรียนใหม่
```

**เปลี่ยนแค่ชั้นแรก** — classifier ยังเป็น `LinearSVC` ตัวเดิม พารามิเตอร์เดิม

**ทำแบบนี้เพื่อให้พิสูจน์ได้ว่าอะไรทำให้ดีขึ้น** — ถ้าเปลี่ยนสองชั้นพร้อมกันจะแยกไม่ออกว่ามาจากไหน

---

## เลือก loss อะไร ทำไม

| loss | ต้องเตรียมข้อมูลยังไง | เหมาะกับงานนี้ |
|---|---|---|
| `CosineSimilarityLoss` | คู่ `(a, b, คะแนน 0-1)` | ❌ ต้องกำหนดคะแนนความเหมือนเอง ซึ่งไม่มีข้อมูล |
| `MultipleNegativesRankingLoss` | คู่ `(anchor, positive)` | ⚠️ ต้องสร้างคู่เอง · negative มาจากใน batch |
| **`BatchAllTripletLoss`** | **`(ประโยค, label)` เฉย ๆ** | ✅ **มี label อยู่แล้ว ไม่ต้องสร้างคู่** |
| `SoftmaxLoss` | `(ประโยค, label)` | ⚠️ ต่อหัว classifier เข้าไปในโมเดล — ขัดกับที่อยากเปลี่ยนชั้นเดียว |

**เลือก `BatchAllTripletLoss`** เพราะรับ label ตรง ๆ

### มันเรียนอะไร

```
ในแต่ละ batch หยิบ 3 ตัว
    anchor     "iPhone 15 Case Clear"      หมวด Case iPhone
    positive   "เคส iPhone 14 ใส"          หมวดเดียวกัน
    negative   "iPhone 15 Pro Max 256GB"   คนละหมวด
            ↓
    ดันให้ anchor-positive ใกล้กัน · anchor-negative ห่างกัน
```

**"All" = ใช้ทุกคู่ที่เป็นไปได้ใน batch** ไม่ใช่สุ่มมาแค่บางคู่ — เรียนได้มากกว่าต่อหนึ่ง batch

### ⚠️ ต้องมีหลายตัวอย่างต่อหมวดใน batch เดียวกัน

**ถ้า batch มีหมวดละ 1 ตัว จะสร้าง positive ไม่ได้เลย → loss เป็น 0 → ไม่เรียนอะไร**

แก้ด้วย

```python
batch_sampler = BatchSamplers.GROUP_BY_LABEL
```

**บังคับให้แต่ละ batch มีหลายตัวอย่างจากหมวดเดียวกัน** — ขาดข้อนี้ fine-tune จะรันผ่านแต่ไม่มีผลอะไรเลย

และตัดหมวดที่มีน้อยกว่า 4 แถวออกก่อน (`--min-per-class 4`)

---

## กันข้อมูลรั่ว — สำคัญที่สุด

```python
tr, te = train_test_split(..., random_state=42, stratify=y)

ds = Dataset.from_dict({"sentence": [texts[i] for i in tr], ...})   # ← train เท่านั้น
```

**fine-tune เห็นแต่ train** — ถ้าให้เห็น test ด้วย คะแนนจะสวยแบบหลอกตัวเอง เพราะโมเดลจำคำตอบไว้แล้ว

**test ชุดเดิม · seed เดิม · classifier เดิม** → ต่างกันแค่ backbone จึงชี้สาเหตุได้

---

## พารามิเตอร์ที่ตั้งและเหตุผล

| | ค่า | ทำไม |
|---|---|---|
| `max_seq_length` | **64** | **ชื่อสินค้าสั้น ~20 token** · ค่า default 512 เปลืองทั้งเวลาและ VRAM โดยไม่ได้อะไร |
| `epochs` | **1** | 294 หมวด หลายหมวดตัวอย่างน้อย · เกิน 1 เสี่ยงจำข้อมูลแทนที่จะเรียน pattern |
| `learning_rate` | **2e-5** | ค่ามาตรฐานของการ fine-tune transformer · สูงกว่านี้ทำลายของที่โมเดลรู้มาแต่เดิม |
| `warmup_ratio` | **0.1** | ค่อย ๆ เพิ่ม lr ช่วง 10% แรก กันโมเดลพังตั้งแต่ก้าวแรก |
| `batch_size` | **32** | ต้องใหญ่พอให้มีหลายหมวดต่อ batch · เล็กไปสร้าง triplet ไม่ได้ |
| `fp16` | **เปิดเมื่อมี GPU** | เร็วขึ้นเท่าตัว ประหยัด VRAM ครึ่งหนึ่ง |

### เลือกโมเดลไหนก่อน

| | พารามิเตอร์ | fine-tune บน T4 |
|---|---|---|
| **`mini`** MiniLM-L12 | 118M | **ไหวสบาย ~10 นาที** ← เริ่มตัวนี้ |
| `e5` multilingual-e5-base | 278M | ไหว |
| `bge` bge-m3 | 568M | **หนัก อาจ OOM ถ้า batch ใหญ่** |

**เริ่มที่ `mini` เสมอ** — พิสูจน์ว่ากระบวนการทำงานก่อน ค่อยขยับไปตัวใหญ่

```bash
python sync_rules.py                                   # ดึงกฎมาก่อนเสมอ
python finetune.py --label Item_Type -n 20000 --model mini
python finetune.py --label Item_Type -n 20000 --model bge --batch 16
```

### ⭐ เริ่มด้วย `--label Item_Type` ไม่ใช่ `Type_Platform`

วัดจริงที่ 20,000 แถว

| label | หมวด | **ตัวอย่างต่อหมวด** |
|---|---|---|
| **`Item_Type`** | **20** | **1,000** |
| `Type_Platform` | 245 | 83 |

**ต่างกัน 12 เท่า** และเรื่องนี้สำคัญกับ triplet loss เป็นพิเศษ

```
batch 32 · 20 หมวด    →  เฉลี่ยหมวดละ 1.6 ตัว    ยังหา positive ได้
batch 32 · 245 หมวด   →  เกือบทุกตัวคนละหมวด     หา positive แทบไม่ได้
```

`GROUP_BY_LABEL` ช่วยจัด batch ให้ **แต่ถ้าหมวดเยอะเกินก็ยังได้ triplet น้อย loss แกว่ง**

---

## เกณฑ์ตัดสินว่าคุ้มไหม

สคริปต์พิมพ์ออกมาให้เลย

```
                        accuracy    f1_macro
frozen                    0.xxxx      0.xxxx
fine-tuned                0.xxxx      0.xxxx
ต่าง                     +0.xxxx     +0.xxxx
```

| `f1_macro` ต่าง | ตัดสิน |
|---|---|
| **> +0.01** | คุ้ม · ใช้ backbone ที่ปรับแล้ว |
| **−0.01 ถึง +0.01** | ไม่คุ้ม · เสียเวลาและได้ของที่ต้องดูแลเพิ่ม |
| **< −0.01** | **แย่ลง** · แปลว่า label ยัง noisy เกินไป |

**ดู `f1_macro` ไม่ใช่ `accuracy`** — หมวดเบ้มาก accuracy บอกอะไรไม่ได้

---

## ⚠️ ทำไมอาจไม่ช่วย และควรรู้ก่อนลงแรง

**label มาจากกฎ keyword ที่เราเขียนเอง**

```
fine-tune = สอนให้ embedding แยกหมวดตาม label ที่ให้ไป
label ผิด = สอนให้แยกผิดแม่นขึ้น
```

**นี่คือเหตุผลที่โน้ตเดิมบอกว่าให้ทำ label สะอาดก่อน**

```
1. embedding + classifier (baseline)   ← ทำแล้ว
2. label สะอาด + เพิ่มข้อมูล            ← ยังไม่ได้ทำ
3. fine-tune                           ← กำลังทำ
```

**ทำข้าม 2 มา 3 ได้ แต่ต้องยอมรับว่าผลอาจออกมาว่า "ไม่ช่วย"** ซึ่งก็เป็นคำตอบที่มีค่า เพราะพิสูจน์ได้ว่าคอขวดไม่ได้อยู่ที่ embedding

### กรณีที่ fine-tune น่าจะช่วยจริง

| สถานการณ์ | ช่วยไหม |
|---|---|
| ชื่อสินค้ามีศัพท์เฉพาะที่โมเดลทั่วไปไม่รู้จัก (`TUF`, `VOOC`, `xPUCK`) | ✅ |
| หมวดที่แยกกันด้วยรายละเอียดเล็ก ๆ (`Galaxy-S` vs `Flip-Fold`) | ✅ |
| label ผิดเยอะ | ❌ **แย่ลง** |
| ข้อมูลน้อย | ❌ overfit |

---

## ลำดับที่ควรทำ

| # | ทำอะไร | เวลา |
|---|---|---|
| 1 | `--label Item_Type --model mini -n 20000` บน GPU | ~15 นาที |
| 2 | ดู `f1_macro` ต่างกี่จุด | — |
| 3 | ถ้า > +0.01 ลอง `--model bge --batch 16` | ~40 นาที |
| 4 | ถ้าไม่ช่วย **กลับไปทำ label สะอาดก่อน** → Cell 12 ใน [[ITEC Category Toolkit]] | — |

**อย่ารันเต็ม 216k ตั้งแต่รอบแรก** — 20,000 แถวพอบอกทิศทางแล้ว

---

## ผลที่ได้จะออกเป็น

```
_out/mini-Item_Type-finetuned/  backbone ที่ปรับแล้ว เอาไปใช้แทนตัวเดิมได้
_out/finetune_result.csv        ตัวเลขก่อน-หลัง ไว้เทียบย้อนหลัง
```

ใช้ backbone ใหม่ในโน้ตบุ๊กโดยแก้ Cell 8

```python
backbone = "../finetune/_out/mini-Item_Type-finetuned"
```

---

## เชื่อมกับโน้ตอื่น

[[ITEC Item Category Mapping (SQL to Python)]] · [[ITEC Model - Run on EC2 Guide]] · [[ITEC - Data Dictionary]] · [[Data Standardization & Quality]] · [[Analytics & AI]] · [[ITEC Item Category Mapping (SQL to Python)]] · [[ITEC Category Toolkit]] · [[ITEC Category Model (ML)]]
