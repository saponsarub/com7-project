# ITEC Product Dimension

> จัดหมวดสินค้า ITEC ใหม่จากชื่อสินค้า แทน `ci_item_category.sql` เดิม
> **216,009 รายการ · 29 Main · 98 Sub** · ประมวลผล 12 วินาที
> โปรเจกต์ `scripts/itec/dimension/` · อัปเดต 2026-09-21
>
> แทนที่ → [[ITEC Category Model (ML)]] (รุ่นเก่า เก็บไว้ดูประวัติเท่านั้น)
> ต้นทาง rule-based → [[ITEC Item Category Mapping (SQL to Python)]] · [[ITEC - Data Dictionary]]

---

## โจทย์

`CategoryName` / `SubCategoryName` ที่ key มากับ ITEC **ผิดมากเกินกว่าจะเชื่อ** — จัดหมวดใหม่จากสิ่งที่เชื่อได้มากกว่าคือ **ชื่อสินค้า** แล้วออกมาเป็นคอลัมน์เดิมที่ report ปลายทางใช้อยู่

| เข้า | ออก |
|---|---|
| `ItemName` `CategoryName` `SubCategoryName` `Brand` | `Main_Product_Dimension` `Sub_Product_Dimension` `Sale_Type` `Product_Dimension` `Product_Purpose` + `IS_Promotion` `IS_Product` `Promotion_Source` |

---

## สถาปัตยกรรม

```
ItemName ─┬─► Item_Type      ของชิ้นนี้คืออะไร    Case · Notebook · Ink
          ├─► Item_Host      ใช้กับเครื่องอะไร     Smart Phone · Tablet
          └─► Item_Platform  แบรนด์/รุ่น          iPhone · iPad · MacBook
                    │
                    ▼
            TAXONOMY {Item_Type: (Main, Sub)}      ตารางเดียว อ่านแล้วรู้เลย
                    │
                    ▼
       Main_Product_Dimension · Sub_Product_Dimension
```

**จับ 3 ชั้น บนสุดเชื่อได้มากสุด**

| ชั้น | ดูอะไร | สัดส่วน |
|---|---|---|
| 1 | ชื่อสินค้า ตรงกับ `TYPES` | ~78% |
| 2 | ชื่อบอกไม่ได้ → `CategoryName` + `SubCategoryName` | ~11% |
| 3 | ยังไม่ได้ → `CATEGORY_MAP` เดาจากหมวดเดิม | **9.8%** ← ติดธง `by_category` ไว้ตรวจ |

---

## กติกา 6 ข้อที่ตัดสินกันไว้

### 1 · host ไม่กำหนด Main

เคสมือถือคือ **เคส** ไม่ใช่มือถือ — host ใช้บอกแค่ว่า "อุปกรณ์เสริมชิ้นนี้ของอะไร" แล้วเอาไปต่อหน้า Sub

```
เคส iPhone  →  Main "Case"  ·  Sub "iPhone Case"
```

> เดิมเอา host เป็น Main ทำให้ **Smart Phone เฟ้อจาก 12,506 เป็น 40,696**

### 2 · DEMO แยกเป็น Main

เครื่องโชว์ **69% (13,296/19,253) มีฝาแฝดชื่อเดียวกันที่ขายจริง** อยู่ในฐาน

```
[Demo Product  ] Tengu Gaming Chair Kusanagi White
[Normal Product] Tengu Gaming Chair Kusanagi White   ← นับ SKU ซ้ำ
```

ถ้าไม่แยก `Phone` จะเฟ้อ 29% · Sub เก็บหมวดเดิมไว้ (`Demo Phone`) จึงยังรู้ว่าเครื่องโชว์คืออะไร

### 3 · Promotion เป็นคอลัมน์ ไม่ใช่ Main

ตรงข้ามกับ DEMO — **โปรขายจริง นับยอดได้** สินค้าที่ติดโปรยังเป็นสินค้าตัวเดิม

```
Apple Watch Sport Band ใน sub "ACC WATCH PROMOTION"
   IS_Promotion = True  ·  Main = Accessory&Bag ▸ Apple Watch Strap
```

แหล่งที่บอกว่าเป็นโปร**ไม่สม่ำเสมอ** จึงเก็บที่มาไว้ด้วยใน `Promotion_Source`

| ที่มา | สัดส่วน |
|---|---:|
| `CategoryName` | 68% |
| `ItemName` | 23% |
| `SubCategoryName` | 7% |
| ชนิด Telecom | 1% |

> **32% ไม่ได้มาจาก CategoryName** — เชื่อ cat อย่างเดียวจะพลาด 5,969 แถว

### 4 · โปรที่ระบุรุ่นเครื่อง = ขายเครื่องรุ่นนั้น

```
"TRUE-iPhone 11 128GB.New-1099จ่าย4494ลด6700"  →  Phone   (ไม่ใช่ Telecom Package)
"โปรโมชั่นผ่อน 0% 10เดือน"                      →  Telecom Package
```

`IS_Promotion` ยังเป็น `True` จึงไม่เสียข้อมูล · Telecom Package จาก 16,906 เหลือ 3,921

### 5 · แยก Apple ทุกตระกูลในระดับ Sub

Apple เป็นสินค้าหลักของบริษัท ต้องดูยอดแยกได้โดยไม่ต้องไปกรอง `Item_Platform` เอง

```
Phone ▸ iPhone   ·   Tablet ▸ iPad   ·   Smart Watch ▸ Apple Watch
Case  ▸ iPhone Case / iPad Case / Apple Watch Case / AirPods Case
```

ใช้ `Item_Platform` ที่จับไว้แล้ว ไม่ต้องเขียนกฎ keyword ใหม่

### 6 · Sub ที่เล็กกว่า 300 แถว ยุบเป็น `Other <Main>`

ตัวอย่างน้อยเกินไปทั้งสำหรับเทรน ML และสำหรับอ่านกราฟ — ยุบเป็น `Other <Main>` ไม่ใช่โยนไป `Others` ระดับ Main จะได้ไม่เสียข้อมูลว่าอยู่หมวดไหน

---

## ผลลัพธ์

| Main | แถว | Sub |
|---|---:|---|
| **Case** | 23,992 | iPhone Case 10,193 · Smart Phone Case 8,017 · iPad Case 2,484 · Other Case 2,207 · AirPods Case 423 · Tablet Case 338 · Mac Case 330 |
| **PC Component** | 22,916 | CPU/GPU/RAM/Mainboard 9,746 · PC Case & Cooling 8,594 · Printer & Scanner 1,738 · Ink & Toner 1,120 · Power Supply 965 · UPS 488 |
| **Phone** | 19,359 | Smart Phone 15,494 · iPhone 3,865 |
| **DEMO** | 19,245 | Demo Phone 3,694 · Demo Home Appliance 2,006 · Demo HeadSet 1,616 · Demo Case 1,305 · (อีก 13 Sub) |
| **Accessory&Bag** | 16,054 | Other Accessory 5,672 · Bag 1,851 · Notebook Bag 1,536 · iPhone Accessory 1,342 · Smart Watch Strap 1,247 · Stand 905 · Mouse Pad 634 · Mac Accessory 603 · Apple Watch Strap 428 |
| **Adapter&Cable&Film** | 13,246 | Charger 2,386 · Smart Phone Cable 2,355 · Smart Phone Film 1,997 · iPhone A&C&F 1,603 · Adapter 1,121 · Tablet Film 1,034 |
| **Notebook** | 12,478 | Notebook |
| **Spare Part** | 11,101 | Apple Service Part 7,069 · Other Part 4,032 |
| **HeadSet&Earpiece** | 7,646 | Headphone & Earphone |
| **Storage** | 6,893 | HDD & SSD 5,952 · Memory Card 849 |
| **Tablet** | 6,289 | iPad 4,293 · Tablet 1,996 |
| **Mouse&Keyboard** | 6,278 | Mouse 3,809 · Keyboard 2,469 |
| **Mac** | 5,386 | Mac Notebook 3,385 · Mac Desktop 2,001 |
| **Home Appliance** | 5,269 | Other Appliance 2,558 · Smart Living 2,539 |
| **PC** | 4,800 | Desktop |
| **Camera** | 4,033 | Digital Camera |
| **Telecom Package** | 3,921 | Operator Subsidy 3,466 · SIM & Plan 455 |
| **Lifestyle & Hobby** | 3,745 | Music Player 1,436 · Merchandise 896 · Furniture 837 · Drone & Action Cam 430 |
| **Speaker** | 3,404 | Other Speaker 2,045 · Portable Speaker 1,359 |
| **Monitor** | 3,190 | Monitor |
| **Network** | 2,934 | Other Network |
| **Smart Watch** | 2,817 | Smart Watch 1,819 · Apple Watch 998 |
| **Service & Insurance** | 2,663 | Other Service 1,263 · Smart Phone Insurance 598 · Insurance 501 |
| **Power Bank** | 1,775 | Power Bank 1,547 |
| **Health & Sport** | 1,501 | Health Product 1,018 · Sport Gadget 483 |
| **TV** | 1,478 | TV |
| **Others** | 1,247 | Stationery 708 · Other 539 |
| **Software** | 1,176 | Software |
| **Console Gaming** | 1,173 | Console & Game |

**สุขภาพของกฎ**

```
Item_Type = Unknown        1.2%   เป้า < 10%   ✓
Main = Others              0.6%   เป้า < 10%   ✓
เชื่อ CategoryName เดิม     9.8%   ยิ่งน้อยยิ่งดี
Sub ที่ชี้ไปหลาย Main       ไม่มี              ✓
```

---

## ⭐ accuracy — วัดจาก gold set ที่คนตรวจ

| | accuracy |
|---|---:|
| ตอนที่เจ้าของงานตรวจ 300 แถว | **72.3%** |
| หลังแก้กฎรอบแรก | 77.0% |
| หลังแก้ตามที่ gold set ชี้ | **85.7%** |

> [!warning] 85.7% สูงเกินจริง
> ใช้ gold set ชุดเดียวกัน **ทั้งแก้กฎและวัดผล** — เหมือนดูเฉลยก่อนสอบ
> ตัวเลขที่เชื่อได้ต้องสุ่มชุดใหม่ที่ยังไม่เคยเห็น (`python run.py --gold 300`)

**ตัวเลขนี้เท่านั้นที่บอกว่า "ถูกจริงกี่ %"** — ค่าอื่นที่โน้ตบุ๊กพิมพ์ออกมาบอกแค่ "กฎทำงานตามที่เขียน"

---

## วิธีรัน

### เครื่องที่มี Jupyter

เปิด `itec_dimension.ipynb` — **แก้กฎที่ Cell 3 ที่เดียว** แล้วรันทั้งไฟล์

### เครื่องอื่น ไม่ต้องมี Jupyter

```bash
cd scripts/itec/dimension
python run.py                     # ประมวลผลทั้งชุด -> _out/
python run.py --source db         # ดึงข้อมูลสดจากฐาน ไม่ต้องมี csv
python run.py --gold 300          # สุ่ม gold set ให้คนตรวจ
python run.py --score             # วัดผลกับ gold_set_checked.csv
python run.py --sample 5000       # ลองบางส่วนก่อน
```

ตั้งเครื่องใหม่ → [[Environment Setup]]

### ไฟล์แต่ละตัวทำอะไร

| ไฟล์ | หน้าที่ | ขึ้น git |
|---|---|:--:|
| `itec_dimension.ipynb` | **ที่เดียวที่เก็บกฎ** — Cell 3 เขียน `rules.yaml` | ✅ |
| `run.py` | **ที่เดียวที่เก็บขั้นตอนทำงาน** — report · make_gold · score · save | ✅ |
| `dimension.py` | เครื่องยนต์ ไม่มีกฎฝังอยู่ | ✅ |
| `rules.yaml` | ผลผลิตจาก Cell 3 · **ห้ามแก้ด้วยมือ** | ✅ |
| `_data/` `_out/` | ข้อมูลเข้า/ผลลัพธ์ | ❌ ติด `.gitignore` |

โน้ตบุ๊กเรียกฟังก์ชันจาก `run.py` — ผลจาก 2 ทางเหมือนกันเป๊ะ ไม่มีโค้ดซ้ำ

---

## ⚠️ กับดักที่เจอจริง

### คำสั้นใน keyword ต้องมีขอบเขตคำ

```
rog   ไปจับ  program · hydrogel · ifrogz      1,825 แถว
omen  ไปจับ  women · momentum                     53
tuf   ไปจับ  stuff · tuffwrap                     35
band  ไปจับ  "Dual-Band Wi-Fi 7 Router"           60
demo  ไปจับ  demon · demos
```

แยกเป็น `loose` (คำยาว) กับ `tight` (ต้องเป็นคำเต็ม) ใน `FLAG_WORDS`
`Product_Purpose = Gaming` เคยเฟ้อจาก 10,803 เป็น 12,713 เพราะเรื่องนี้

### รวม 3 ช่องแล้วจับด้วยกฎ = พังหนัก

ทดสอบแล้ว **เปลี่ยนผล 22,232 แถว (10.3%) และเกือบทั้งหมดผิด**

```
"Case ATX RJA 826-2"     cat=PC Case & Cooling  →  Cooling    ❌ 6,329 แถว
"Elephant Mouse Wired"   cat=Mouse & Keyboard   →  Keyboard   ❌ 3,002 แถว
```

เพราะ `CategoryName` มักมีชื่อสินค้า **2 ชนิดในช่องเดียว** แล้วกฎตัดสินแบบ first-match-wins

> **แต่การรวมช่องถูกสำหรับ ML** — `D.build_text()` ทำแบบนั้นอยู่ เพราะ ML เรียนน้ำหนักเองว่าคำใน `ItemName` เชื่อได้มากกว่า

### gold set ต้องมี `ItemId`

`ItemName` ไม่ unique — `(Part) LCD` มี **60 แถว** ในฐาน
เคยวัด accuracy ได้ 73.7% ทั้งที่ของจริง 77.0% เพราะ join ไปเจอฝาแฝดตัว Demo

### ลำดับใน `TYPES` คือลำดับความสำคัญ

```
Speaker ต้องมาก่อน Audio   ไม่งั้นลำโพง 4,445 แถวถูกดูดไปรวมกับหูฟัง
Ink     ต้องมาก่อน Printer ไม่งั้นหมึกถูกนับเป็นเครื่องพิมพ์
ipad    ต้องมาก่อน tab     · macbook ต้องมาก่อน mac
```

### แบรนด์บางตัวเชื่อได้มากกว่าชื่อสินค้า

`Case Club` ตั้งชื่อสินค้าเป็น**ชื่อลายอาร์ตเวิร์ก** — `Join The Club French Bull Dog` · `Bicolor Cat Life`

เคยเข้าใจผิดว่าเป็นฟิกเกอร์ Hot Toys แล้วส่ง 876 แถวไปกอง Art Toy → ใช้ `BRAND_FORCE` แทน

### pandas 3

`\w` `\s` เป็น ASCII ล้วน — ต้องเขียน `ก-๛` เป็นอักษรไทยจริง ห้าม `฀`
รายละเอียด → [[ITEC Category Toolkit]]

---

## งานที่เหลือ

| # | งาน | สถานะ |
|:--:|---|---|
| 1 | ตรวจ gold set ชุดใหม่ 300 แถว | ⬜ ต้องได้ตัวเลขที่ไม่ปนเปื้อน |
| 2 | รัน ML (`RUN_ML = True`) | ⬜ ต้องมี GPU → Colab / Kaggle |
| 3 | ตัดสินว่าใช้กฎล้วน / ML ล้วน / ผสม | ⬜ |
| 4 | เทียบกับ `ci_item_category.sql` เดิมก่อนเปลี่ยนจริง | ⬜ |

**14% ที่กฎแก้ไม่ได้คืองานของ ML** — พวก `ตราปั๊ม` `สายยาง` `เส้นพลาสติก 3D` ที่ชื่อกับ category ไม่มีคำใบ้เลย เขียน keyword ต่อไม่คุ้ม

ML ออกแบบไว้แล้วในโน้ตบุ๊ก ส่วน 8.0–8.3 — feature รวม 4 ช่อง + สุ่มปิด field กัน train-serving skew และกัน target leakage ที่แถว `by_category`

---

## เชื่อมกับโน้ตอื่น

- [[ITEC Category Model (ML)]] — รุ่นเก่า มีกล่องเตือนว่าอย่าใช้เป็นคู่มือ
- [[ITEC Item Category Mapping (SQL to Python)]] — SQL ต้นทางที่กำลังจะถูกแทน
- [[ITEC Category Toolkit]] — กับดัก pandas 3 แบบเต็ม
- [[ITEC - Data Dictionary]] — `dim_item_itec` และ view อื่นของ ITEC
- [[Environment Setup]] — ตั้งเครื่องใหม่ · pip · ODBC · GPU
- [[ITEC Model - Run on EC2 Guide]] — ถ้าจะไปรันบน EC2
