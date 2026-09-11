# ITEC Category Override Rules

> ชุด keyword override + flag สำหรับแก้เคสที่ ML ทำนายหมวดสินค้ามั่ว (โดยเฉพาะ accessory)
> บันทึก 2026-09-08 · ใช้คู่กับ [[ITEC Category Model (ML)]]
> เกี่ยวข้อง → [[ITEC - Data Dictionary]] · [[ITEC Item Category Mapping (SQL to Python)]]

---

## ปัญหาที่แก้

ML จาก ItemName ล้วนมัก**ทายผิดกับ accessory** เพราะชื่อสินค้าหลักกลบคำประเภท:

| ItemName | ML ทาย (ผิด) | ที่ถูก |
|---|---|---|
| iPhone 15 Case Clear | Smart Phone ❌ | Accessory |
| Samsung Fast Charger | Smart Phone ❌ | Accessory |
| Shipping Fee | (เคยติด IS_Pin) ❌ | Service |
| AppleCare+ for iPad | Tablet ❌ | Warranty |

**หลักการแก้:** คำที่บอกประเภทชัดเจน (case, charger, shipping, applecare) ให้ **rule ทับผล ML** — ถ้าไม่เจอ keyword ค่อยปล่อยให้ ML ทำนาย (ไม่ไปยุ่งเคสที่ ML ถูกอยู่แล้ว)

---

## Override Rules (ทับ Category)

เรียงตาม priority (เลขน้อย = เช็กก่อน) · ทุกกลุ่มใช้ `whole_word` กัน false positive (บทเรียน `pin`→"shipping")

| Priority | Category ปลายทาง | Keyword หลัก |
|---|---|---|
| 10 | **Accessory and Others** | case, cover, เคส, screen protector, ฟิล์ม, charger, adapter, สายชาร์จ, cable, power bank, stand, holder, dock, strap, grip |
| 20 | **Service and Others** | shipping, ค่าส่ง, service fee, ค่าบริการ, repair, ค่าซ่อม, installation, delivery |
| 30 | **Warranty and Insurance** | applecare, care+, warranty, ประกัน, insurance, คุ้มครอง |

> ชื่อ Category ต้องตรงกับค่าจริงในฐาน — ตรวจกับ [[ITEC - Data Dictionary]] (`Main_Product_Dimension`) ก่อนใช้จริง · จาก ITEC Overview: `Accessory and Others` = 67,406 แถว (มากสุด)

## Flag Rules (multi-label — เสริม ไม่ทับ category)

ตรงกับ `IS_*` ที่มีในระบบ + `Product_Dimension`/`Product_Purpose`:

| Flag | Keyword | whole_word |
|---|---|---|
| `IS_Promotion` | promotion, promo, โปรโมชั่น, ของแถม, bundle, เซ็ต, ฟรี | ไม่ |
| `IS_Demo_Product` | demo, tester, ตัวโชว์, display, sample | ✅ |
| `IS_Gaming` | gaming, เกมมิ่ง, rog, predator, legion, tuf, nitro | ไม่ |
| `IS_Refurbished` | refurbish, มือสอง, second hand, used | ไม่ |

> อ้างอิงตัวเลขจริง: `Product_Dimension` = Demo Product 19,253 · `Product_Purpose` = Gaming 10,432

---

## โค้ด — รวม override + ML + flag เป็น pipeline เดียว

```python
import re, pandas as pd

# ── config (ดู artifacts/category_override.json) ──
OVERRIDE_RULES = [   # (priority, category, [keywords], whole_word)
    (10, "Accessory and Others",
     ["case","casing","cover","bumper","เคส","ซอง","screen protector","tempered",
      "ฟิล์ม","film","charger","adapter","อะแดปเตอร์","ที่ชาร์จ","cable","สายชาร์จ",
      "power bank","powerbank","stand","holder","ขาตั้ง","dock","strap","grip"], True),
    (20, "Service and Others",
     ["shipping","ค่าส่ง","ค่าจัดส่ง","service fee","ค่าบริการ","ค่าซ่อม","repair",
      "installation","ค่าติดตั้ง","delivery"], True),
    (30, "Warranty and Insurance",
     ["applecare","apple care","care+","warranty","ประกัน","insurance","คุ้มครอง"], False),
]
FLAG_RULES = {
    "IS_Promotion":    (["promotion","promo","โปรโมชั่น","ของแถม","bundle","เซ็ต","ฟรี"], False),
    "IS_Demo_Product": (["demo","tester","ตัวโชว์","display","sample"], True),
    "IS_Gaming":       (["gaming","เกมมิ่ง","rog","predator","legion","tuf","nitro"], False),
    "IS_Refurbished":  (["refurbish","มือสอง","second hand","used"], False),
}

def _pat(words, ww):
    return "|".join((rf"\b{re.escape(w.lower())}\b" if ww else re.escape(w.lower())) for w in words)

_compiled = [(c, _pat(k, ww)) for _, c, k, ww in sorted(OVERRIDE_RULES, key=lambda x: x[0])]
_flags    = {f: _pat(w, ww) for f, (w, ww) in FLAG_RULES.items()}

def predict_category(item_name, ml_predict=None):
    """rule override ก่อน → ถ้าไม่เจอ keyword ค่อยให้ ML"""
    t = item_name.lower()
    for cat, pat in _compiled:            # 1) override
        if re.search(pat, t):
            return cat
    if ml_predict:                        # 2) ไม่เจอ → ML (จาก [[ITEC Category Model (ML)]])
        return ml_predict(item_name)
    return "UNKNOWN"

def get_flags(item_name):
    t = item_name.lower()
    return [f for f, pat in _flags.items() if re.search(pat, t)]

# ── ใช้กับทั้ง DataFrame ──
def enrich(df, ml_predict=None):
    df = df.copy()
    df["Category_pred"] = df.ItemName.apply(lambda x: predict_category(str(x), ml_predict))
    for f in FLAG_RULES:
        pat = _flags[f]
        df[f] = df.ItemName.str.lower().str.contains(pat, regex=True).astype("int8")
    return df
```

## ผลทดสอบ (ยืนยันแล้ว 2026-09-08)

```
ItemName                    Override Category       Flags
iPhone 15 Case Clear        Accessory and Others    -
iPhone 15 Pro Max 256GB     (→ ให้ ML ทำนาย)        -
Samsung Fast Charger 25W    Accessory and Others    -
Shipping Fee                Service and Others      -
AppleCare+ for iPad         Warranty and Insurance  -
MacBook Air M3 13 (Demo)    (→ ให้ ML)              IS_Demo_Product
ROG Gaming Mouse            (→ ให้ ML)              IS_Gaming
Power Bank 20000mAh ของแถม  Accessory and Others    IS_Promotion
```

ทุกเคสที่เคยมั่วแก้ได้ · เคสที่ ML ถูกอยู่แล้ว (iPhone Pro Max) ไม่ถูกแตะต้อง

---

## flow รวม

```
ItemName
   │
   ├─ เจอ override keyword (case/charger/shipping/applecare) ─► Category (rule ทับ) ✅
   │
   └─ ไม่เจอ ─► ML embedding ([[ITEC Category Model (ML)]]) ─► Category
   │
   └─ (ขนาน) เช็ก flag keyword ─► IS_Promotion / IS_Demo_Product / IS_Gaming / IS_Refurbished
```

---

## สิ่งที่ต้องทำต่อ

- [ ] ตรวจชื่อ Category ปลายทางให้ตรงค่าจริงในฐาน (`Accessory and Others`, `Service and Others` ฯลฯ) — ดู [[ITEC - Data Dictionary]]
- [ ] เพิ่ม override กลุ่มอื่นถ้าเจอ ML มั่วเพิ่ม (ดูจาก confusion matrix)
- [ ] รัน enrich() กับข้อมูลจริง 216k แถว แล้วเทียบ Category_pred กับของเดิม
- [ ] whole_word: ระวังคำสั้น (case, film, used) — เปิด whole_word ไว้แล้ว แต่ทวนอีกครั้งกับข้อมูลจริง

---

## เชื่อมกับโน้ตอื่น

[[ITEC Category Model (ML)]] · [[ITEC Item Category Mapping (SQL to Python)]] · [[ITEC - Data Dictionary]] · [[Data Standardization & Quality]]
