# ITEC Category Model (ML)

> โมเดล Machine Learning สำหรับทำนายหมวดสินค้า ITEC จากชื่อสินค้า (ItemName)
> บันทึก 2026-09-08 · ต่อยอดจาก [[ITEC Item Category Mapping (SQL to Python)]] (แนว rule-based keyword)
> เกี่ยวข้อง → [[ITEC - Data Dictionary]] · [[Data Standardization & Quality]] · [[ETL & Spark]] · [[Analytics & AI]]

---

## เป้าหมาย

จาก `rpt.dim_item_itec` (216,009 แถว) ทำนาย **CategoryName** จาก **ItemName** โดยตอนใช้งานจริง**มีแค่ ItemName** (ไม่มี SubCategory ให้ใส่ตอน predict)

- **Feature (X):** `ItemName`
- **Target (y):** `CategoryName`
- ปัญหา: **text classification** (หมวดเป็น category → ไม่ใช่ regression)

> ต่างจาก [[ITEC Item Category Mapping (SQL to Python)]] ที่เป็น **rule-based** (keyword `IS_*` 67 flag จาก SQL) — โน้ตนี้เป็นแนว **ML** ที่เรียนจากข้อมูลเอง

---

## ข้อค้นพบสำคัญเรื่องข้อมูล

### SubCategory → Category ไม่ใช่ mapping ตายตัว

```
SubCategory ที่ชี้ไปหลาย Category: 129 / 1,708
```

| กลุ่ม | จำนวน | ความหมาย |
|---|---|---|
| ชัด (1 sub → 1 cat) | 1,579 (92%) | lookup ตรงได้ แม่น 100% |
| กำกวม (1 sub → หลาย cat) | 129 (8%) | ต้องดู ItemName ประกอบ → ใช้ ML |

**สรุป:** ML คุ้มที่จะใช้ เพราะมี 8% ที่ lookup อย่างเดียวแก้ไม่ได้ · แต่ตอน predict จริงมีแค่ ItemName → lookup ด้วย SubCategory ก็ใช้ไม่ได้ → **ต้อง ML จาก ItemName ล้วน**

---

## แนวทางที่เลือก: LLM Embedding + Classifier (รันเอง)

เลือก **embedding จาก backbone LLM รันเอง (local/HuggingFace)** เพราะ:
- ✅ ฟรี ไม่ส่งข้อมูลออกนอก (ดีต่อ PDPA)
- ✅ รองรับไทย/อังกฤษปนกัน (ต่างจาก TF-IDF ที่ตัดคำด้วยช่องว่าง ไทยพัง)
- ✅ เข้าใจความหมายรวม แก้ปัญหา "iPhone Case → มั่วเป็น phone" ได้

### Backbone ที่แนะนำ

| Model | ขนาด | จุดเด่น |
|---|---|---|
| **BAAI/bge-m3** ⭐ | ~2GB | รองรับไทยดีมาก เหมาะจัดหมวด |
| `intfloat/multilingual-e5-base` | ~1GB | เบา เร็ว ไทยโอเค |
| `intfloat/multilingual-e5-large` | ~2GB | แม่นสุด ช้ากว่า |

### สถาปัตยกรรม

```
ItemName → [backbone LLM: bge-m3] → embedding (เวกเตอร์ 1024 มิติ)
                                          │
                                          ▼
                          [Logistic Regression] → CategoryName
```

- **backbone LLM** = ตัวอ่าน/เข้าใจข้อความ → แปลงเป็นเวกเตอร์ (ไม่ต้องเทรน ใช้ pre-trained)
- **Logistic Regression** = classifier เบา ๆ เรียนจาก embedding → ทำนาย category

---

## โค้ดหลัก

```python
import pandas as pd, numpy as np, joblib, torch
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# 1. โหลด backbone LLM
device = "cuda" if torch.cuda.is_available() else "cpu"
embedder = SentenceTransformer("BAAI/bge-m3", device=device)

# 2. เตรียมข้อมูล (feature = ItemName เท่านั้น)
def clean(s):
    return (s.fillna("").astype(str).str.lower()
             .str.replace(r"[^\w\s/&+.-]", " ", regex=True)
             .str.replace(r"\s+", " ", regex=True).str.strip())

texts = clean(df.ItemName).tolist()
y = df.CategoryName.fillna("UNKNOWN").astype(str)
vc = y.value_counts(); keep = y.isin(vc[vc >= 2].index).values
texts = [t for t,k in zip(texts, keep) if k]
y = y[keep].reset_index(drop=True)

# 3. แปลงข้อความ → embedding (backbone อ่านตรงนี้)
X = embedder.encode(texts, batch_size=64, show_progress_bar=True,
                    normalize_embeddings=True)

# 4. เทรน classifier
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                          random_state=42, stratify=y)
clf = LogisticRegression(max_iter=2000, C=10, class_weight="balanced", n_jobs=-1)
clf.fit(X_tr, y_tr)
print(f"Accuracy: {accuracy_score(y_te, clf.predict(X_te)):.4f}")
print(classification_report(y_te, clf.predict(X_te), zero_division=0))

# 5. บันทึก
joblib.dump({"backbone": "BAAI/bge-m3", "clf": clf}, "category_llm.joblib")

# 6. ทำนาย
def predict(names):
    if isinstance(names, str): names = [names]
    emb = embedder.encode([s.lower() for s in names], normalize_embeddings=True)
    return clf.predict(emb)
```

**หมายเหตุ:** ต้อง `pip install sentence-transformers torch` · ครั้งแรกโหลด model ~2GB จาก HuggingFace · 216k แถวบน CPU ~10-30 นาที (GPU เร็วกว่ามาก)

---

## ⚠️ ปัญหาที่เจอ: "iPhone Case → มั่วเป็น phone"

### อาการ
```
predict("iPhone 15 Case Clear")  →  ทายเป็น phone category (ผิด — ควรเป็น Accessory)
```

### สาเหตุ
ItemName ของ accessory มักมีชื่อสินค้าหลักปนอยู่ (`iPhone Case`, `Samsung Charger`) → คำแบรนด์/รุ่นเด่นกว่าคำบอกประเภท → โมเดลโดน "iphone" ลากไป

### วิธีแก้ (เรียงจากตรงจุดสุด)

**1. Rule override — แนะนำสุดสำหรับเคสนี้**
คำที่บอกประเภทชัดเจน ให้ทับผล ML ทันที:
```python
import re
ACCESSORY_KW = ["case","cover","charger","cable","adapter","sleeve",
                "screen protector","tempered","film","stand","holder",
                "เคส","ฟิล์ม","สายชาร์จ","อะแดปเตอร์","ที่ชาร์จ"]
# whole_word กันคำสั้นเจอในคำอื่น (case → casement)
acc_pat = "|".join(rf"\b{re.escape(w)}\b" for w in ACCESSORY_KW)

def predict_smart(item_name):
    if re.search(acc_pat, item_name.lower()):
        return "Accessory and Others"   # rule ทับ
    return clf_predict(item_name)        # ไม่เจอ → ML
```

**2. char n-gram** — ช่วย embedding จับ substring "case" แม้ติดคำอื่น
```python
TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5))   # ถ้ายังใช้ TF-IDF
```

**3. Downweight คำแบรนด์** — ตัด iphone/samsung/รุ่น ออกก่อน แล้วย้ำคำประเภท

> บทเรียนเดียวกับ `whole_word` ใน [[ITEC Item Category Mapping (SQL to Python)]] — คำสั้นที่บอกประเภท (case, pin) ต้องกัน false positive และควรมี rule ทับเมื่อคำนั้นบอกประเภทชัด

---

## Model ที่ใช้ — ทำไม Logistic Regression

| เหตุผล | รายละเอียด |
|---|---|
| เหมาะ text | คู่กับ embedding/TF-IDF เป็น baseline มาตรฐาน |
| เร็ว | เทรน/ทำนายเร็วแม้หลายแสนแถว |
| อธิบายได้ | ดูน้ำหนักคำต่อ category ได้ |
| เบา | ไฟล์เล็ก ไม่ต้อง GPU (ส่วน classifier) |

**ทางเลือกอื่น** (สลับแค่บรรทัด classifier): `LinearSVC` (เร็ว แม่นกับ text sparse) · `LightGBM` (ข้อมูลเยอะ) · `WangchanBERTa` (ไทยล้วน ต้องการแม่นสุด แต่หนัก)

---

## สรุปวิวัฒนาการของแนวทาง (ที่คุยกันมา)

| เวอร์ชัน | Feature | วิธี | ปัญหา/ผล |
|---|---|---|---|
| v1 | Item + Category | ML → ทำนาย SubCategory | โจทย์เริ่มต้น |
| v2 | Item + SubCategory | ML → ทำนาย Category | เจอว่า 92% เป็น lookup |
| v3 | (hybrid) | lookup 92% + ML 8% | แม่นสูง แต่ต้องมี SubCategory ตอน predict |
| **v4 (ปัจจุบัน)** | **ItemName ล้วน** | **LLM embedding + LogReg** | ตรงกับ production (มีแค่ ItemName) + rule override แก้ accessory |

---

## สิ่งที่ต้องทำต่อ

- [ ] ตัดสิน backbone: bge-m3 (แม่น) หรือ multilingual-e5-base (เบา) — ลองเทียบ accuracy
- [ ] สร้าง ACCESSORY_KW ให้ครบทุกประเภทที่ ML มักมั่ว (ดูจาก confusion matrix)
- [ ] เทียบ TF-IDF (เดิม) vs embedding ว่าต่างกันแค่ไหน คุ้มกับต้นทุน embed ไหม
- [ ] ถ้า ItemName ไทยเยอะ ลอง pythainlp ตัดคำก่อน (กรณียังใช้ TF-IDF)
- [ ] ประเมินต่อ category (ไม่ใช่แค่ accuracy รวม) — class เล็กอาจแม่นต่ำ

---

## เชื่อมกับโน้ตอื่น

[[ITEC Item Category Mapping (SQL to Python)]] · [[ITEC - Data Dictionary]] · [[Data Standardization & Quality]] · [[Analytics & AI]] · [[ETL & Spark]]
