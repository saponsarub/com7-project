# ITEC Model — Fine-tune Design

> ออกแบบการ fine-tune backbone + วิธีพิสูจน์ว่าคุ้มหรือไม่ — 2026-09-15
> **โปรเจกต์แยก** `scripts/itec/finetune/` · ต่อจาก [[ITEC Model - Notebook Explained]]

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
| 4 | ถ้าไม่ช่วย **กลับไปทำ label สะอาดก่อน** → Cell 12 ใน [[ITEC Model - Notebook Explained]] | — |

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

[[ITEC Model - Notebook Explained]] · [[ITEC Category Toolkit]] · [[ITEC Category Model (ML)]] · [[ITEC Model - Run on EC2 Guide]]
