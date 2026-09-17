# Power BI PBIP Cookbook

> **หมายเหตุที่มา:** ทุกอย่างในโน้ตนี้มาจากการทำ dashboard **NPI iPhone Launch** จริงบนเครื่อง `Sapon.S` ช่วง 2026-09-16 ถึง 2026-09-17 — Power BI Desktop **2.156.951.0 (July 2026)**
> ข้อที่ทำเองแล้วพัง + วิธีแก้ เขียนไว้ครบในหัวข้อ "กับดัก" ด้านล่าง · ข้อไหนยังไม่ได้พิสูจน์จะเขียน **[ยังไม่ยืนยัน]** กำกับ

ไฟล์จริงที่อ้างถึง: `Powerbi/booking_npi.pbip` ใน repo `my-first-project`

---

## ทำไมต้อง `.pbip` ไม่ใช่ `.pbix`

| | `.pbix` | `.pbip` |
|---|---|---|
| รูปแบบ | ไฟล์ zip binary | โฟลเดอร์ text ล้วน (TMDL + JSON) |
| ขึ้น git | ได้ แต่ diff ไม่ได้ | **diff ได้ทีละบรรทัด** |
| แก้ด้วยสคริปต์/AI | ไม่ได้ | **ได้** |
| merge conflict | แก้ไม่ได้ | แก้ได้ |

เปิด `.pbip` ใน Desktop ต้องเปิด preview **`PBI_tmdlInDataset`** + **`PBI_enhancedReportFormat`** ไว้ (File ▸ Options ▸ Preview features)

---

## โครงไฟล์

```
booking_npi.pbip                       ← ไฟล์ที่ดับเบิลคลิก
booking_npi.SemanticModel/
  definition.pbism
  definition/
    model.tmdl · database.tmdl · relationships.tmdl
    cultures/en-US.tmdl
    tables/
      ci npi_iphone (2).tmdl           ← ตารางหลัก column + measure อยู่ที่นี่
      LocalDateTable_*.tmdl            ← Desktop สร้างเอง อย่าแตะ
booking_npi.Report/
  definition.pbir
  definition/
    report.json                        ← theme + resourcePackages + settings
    version.json
    pages/
      pages.json                       ← ลำดับแท็บ + แท็บที่เปิดค้าง
      <pageId>/
        page.json                      ← ชื่อแท็บ + ขนาดหน้า
        visuals/<visualName>/visual.json
  StaticResources/RegisteredResources/
    com7_launch_theme.json             ← ธีม
    logocom7.png                       ← โลโก้
```

`<pageId>` และ `<visualName>` เป็นชื่อโฟลเดอร์ **ตั้งเองได้** ขอแค่ตรงกับ `"name"` ข้างในไฟล์

---

## TMDL — ไวยากรณ์ที่ต้องรู้

```tmdl
table 'ci npi_iphone (2)'
	lineageTag: 9371e051-8d3e-4b4e-9cce-4b4aa1380513

	measure Bookings = CALCULATE(COUNTROWS('ci npi_iphone (2)'), [Is Test Row] = 0)
		formatString: #,0
		lineageTag: a4220428-0594-4e51-8b61-a93163389a87

	column 'Launch Day' = DATEDIFF([Launch Open], [clean_bookdate], DAY)
		dataType: int64
		formatString: 0
		lineageTag: 292886f7-25ea-4dc7-a557-204c15562180
		summarizeBy: none

		annotation SummarizationSetBy = Automatic

	partition 'ci npi_iphone (2)' = m
		mode: import
		source =
				let
				    Source = Sql.Database("เซิร์ฟเวอร์", "ฐานข้อมูล"),
				    t = Source{[Schema="ci",Item="npi_iphone"]}[Data]
				in
				    t
```

กติกา

- **indent ด้วย tab เท่านั้น** — space ปนแม้ตัวเดียว parser ตาย
- ชื่อที่มีเว้นวรรคต้องครอบ `'...'` · ชื่อคำเดียวไม่ต้อง (Desktop จะถอด `'` ให้เองตอน save)
- `lineageTag` ต้องเป็น GUID **ไม่ซ้ำกันทั้งไฟล์** — สร้างใหม่ด้วย `uuid.uuid4()` ได้
- calculated column ต้องมี `dataType` · measure ไม่ต้อง
- property ที่ใช้ได้: `dataType` `formatString` `lineageTag` `summarizeBy` `mode` `sourceColumn` `isHidden` `displayFolder`

### กับดัก TMDL ที่เจอจริง

**① `///` ไม่ใช่คอมเมนต์**

```tmdl
	/// ══════ คอลัมน์คำนวณ ══════     ← ตั้งใจใช้เป็นเส้นคั่น
	                                   ← เว้นบรรทัด
	column 'Launch Open' = ...
```
```
Parsing error type - InvalidLineType
Detailed error - Unexpected line type: Empty!
```

`///` คือ **description ที่ต้องติดกับ object บรรทัดถัดไปทันที** ห้ามมีบรรทัดว่างคั่น
ถ้าอยากใส่คอมเมนต์ลอย ๆ — **ทำไม่ได้ อย่าใส่**

**② ไม่มี property ชื่อ `description:`**

```tmdl
	measure Bookings = ...
		formatString: #,0
		description: จำนวนใบจอง        ← พัง
```
```
Parsing error type - UnknownKeyword
Unsupported property - description is not a supported property in the current context!
```

คำอธิบายเขียนได้ทางเดียวคือ `/// ข้อความ` เหนือ object แบบติดกัน

**③ circular dependency จาก CALCULATE ใน calculated column**

calculated column ที่ใช้ `CALCULATE` / `ALLEXCEPT` จะถูกมองว่า **ขึ้นกับทุกคอลัมน์ในตาราง รวมถึง calculated column ตัวอื่น** ถ้าตัวอื่นย้อนกลับมาอ้างมันอีก = วน

```dax
-- พัง: Launch Cohort ใช้ CALCULATE แล้ว Launch Open อ้าง Launch Cohort
Launch Cohort = ... CALCULATE(MIN([clean_bookdate]), ALLEXCEPT(T, T[model])) ...
Launch Open   = SWITCH([Launch Cohort], ...)
```

ทางออก — เขียน calculated column ให้อยู่ใน row context ล้วน ๆ ไม่มี CALCULATE

---

## กับดัก DAX ที่ทำตัวเลขเพี้ยนแบบเงียบ ๆ

### `ALL(ตาราง)` ล้าง slicer ทุกอันทิ้ง

```dax
-- ผิด
Bookings Prev Model =
VAR n = SELECTEDVALUE(T[Model No])
RETURN CALCULATE([Bookings D0-2], ALL(T), T[Model No] = n - 1)
```

อาการ: **คอลัมน์ข้อมูลดิบถูก แต่คอลัมน์คำนวณเพี้ยน** — เลือก slicer ภาค `North`

```
ตัวตั้ง   3,332   ← North เท่านั้น   ถูก
ตัวหาร  23,242   ← ทั้งประเทศ       ผิด เพราะ ALL() ล้าง North ทิ้ง
YoY    -85.7%    ← ค่าจริงคือ +2.4%
```

```dax
-- ถูก: ล้างเฉพาะมิติที่ผูกกับ "ปีไหน" ที่เหลือปล่อยให้ slicer ทำงาน
Bookings Prev Model =
VAR n = SELECTEDVALUE(T[Model No])
RETURN CALCULATE([Bookings D0-2],
    REMOVEFILTERS(T[Launch Cohort], T[clean_iPhone_model], T[Launch Open],
                  T[Launch Sale], T[Launch Window Days],
                  T[clean_bookdate], T[booking_datetime]),
    T[Model No] = n - 1)
```

**กฎที่ควรจำ** — ใน measure เทียบช่วงเวลา ให้ `REMOVEFILTERS` เฉพาะคอลัมน์เวลา **ห้ามใช้ `ALL(ตาราง)`**

### boolean filter ใน CALCULATE ทับ slicer ของคอลัมน์นั้นให้เอง

```dax
Bookings Pro Only = CALCULATE([Bookings], T[submodel] IN {"Pro", "Pro Max"})
```

ไม่ต้อง `REMOVEFILTERS(T[submodel])` ก่อน — boolean predicate **แทนที่** filter เดิมบนคอลัมน์เดียวกันอยู่แล้ว

### ระวัง measure ฐานที่ไม่ได้ล็อกขอบเขต

`CALCULATE(COUNTROWS(T), [Is Test Row] = 0)` นับ **ทุกแถวในตาราง** รวมใบจองที่เกิดหลังช่วงงานเป็นปี
ต้องมี flag column ล็อกไว้ เช่น `In Launch Window = 1` ไม่งั้นรุ่นเก่าจะสะสมยอดจนเทียบ YoY ไม่ได้ (iPhone-15 มี 45,219 แถว แต่อยู่ในสัปดาห์เปิดตัวจริงแค่ 16,509)

---

## PBIR — `visual.json`

โครงขั้นต่ำที่ใช้ได้จริง

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.4.0/schema.json",
  "name": "colMix",
  "position": { "x": 16, "y": 162, "z": 10, "width": 762, "height": 284, "tabOrder": 10 },
  "visual": {
    "visualType": "columnChart",
    "query": {
      "queryState": {
        "Category": { "projections": [ { "field": { "Column":  { "Expression": { "SourceRef": { "Entity": "ci npi_iphone (2)" } }, "Property": "Launch Cohort" } }, "queryRef": "ci npi_iphone (2).Launch Cohort", "nativeQueryRef": "Launch Cohort" } ] },
        "Series":   { "projections": [ { "field": { "Column":  { "Expression": { "SourceRef": { "Entity": "ci npi_iphone (2)" } }, "Property": "clean_iPhone_submodel" } }, "queryRef": "ci npi_iphone (2).clean_iPhone_submodel", "nativeQueryRef": "clean_iPhone_submodel" } ] },
        "Y":        { "projections": [ { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "ci npi_iphone (2)" } }, "Property": "Bookings" } }, "queryRef": "ci npi_iphone (2).Bookings", "nativeQueryRef": "Bookings" } ] }
      }
    },
    "objects": { "labels": [ { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } } ] },
    "visualContainerObjects": {
      "title": [ { "properties": { "text": { "expr": { "Literal": { "Value": "'ใบจองแยกตามรุ่นย่อย'" } } } } } ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

จุดที่พลาดง่าย

- **column ใช้ `"Column"` · measure ใช้ `"Measure"`** สลับกันแล้วขึ้น error
- `queryRef` ต้องเป็น `<ชื่อตาราง>.<ชื่อฟิลด์ตรงตัว>`
- string literal ต้องมี **single quote ซ้อนอยู่ข้างใน**: `"Value": "'ข้อความ'"`
- boolean literal ไม่ต้องซ้อน: `"Value": "true"`
- `objects` = format ของตัวกราฟ · `visualContainerObjects` = กรอบ/หัวเรื่อง **คนละที่กัน**

### ชื่อ role ของแต่ละชนิด

| visualType | role ที่ต้องใส่ |
|---|---|
| `card` | `Values` |
| `columnChart` | `Category` · `Series` · `Y` |
| `barChart` | `Category` · `Series` · `X` |
| `lineChart` | `Category` · `Series` · `Y` |
| `tableEx` | `Values` (ใส่ได้หลายฟิลด์เรียงกัน) |
| `slicer` | `Values` |
| `image` | ไม่มี query |

### เวอร์ชัน schema

`report.json` เขียน `reportVersionAtImport: { visual: "2.11.0" }` — **นั่นคือเลขของ theme ที่ import มา ไม่ใช่เวอร์ชัน visual ที่ต้องใช้**
ชุดที่ Desktop July 2026 เขียนเองคือ report `3.3.0` / page `2.1.0` / pagesMetadata `1.1.0` / visualContainer `1.4.0`
`visualContainer/2.11.0` ก็โหลดผ่าน — **ปนกันในโปรเจกต์เดียวได้**

---

## ใส่โลโก้

**1 · วางไฟล์**

```
booking_npi.Report/StaticResources/RegisteredResources/logocom7.png
```

**2 · ลงทะเบียนใน `report.json`**

```json
{
  "name": "RegisteredResources",
  "type": "RegisteredResources",
  "items": [
    { "name": "com7_launch_theme", "path": "com7_launch_theme", "type": "CustomTheme" },
    { "name": "logocom7.png",      "path": "logocom7.png",      "type": "Image" }
  ]
}
```

**3 · สร้าง image visual**

```json
"visual": {
  "visualType": "image",
  "objects": { "general": [ { "properties": {
    "imageUrl": { "expr": { "ResourcePackageItem": {
      "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": "logocom7.png" } } },
    "imageScaling": { "expr": { "Literal": { "Value": "'Fit'" } } }
  } } ] },
  "visualContainerObjects": {
    "background": [ { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } } ],
    "border":     [ { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } } ]
  },
  "drillFilterOtherVisuals": true
}
```

`PackageType: 1` = RegisteredResources · ต้องปิด background กับ border ไม่งั้นโลโก้จะมีกรอบขาว
ขนาดที่ใช้: โลโก้จริง 738×261 ย่อเหลือ **104×37** มุมขวาบน `x:1160 y:12`

---

## ธีม

ไฟล์ `StaticResources/RegisteredResources/<ชื่อ>.json` แล้วอ้างใน `report.json`

```json
"themeCollection": { "customTheme": { "name": "com7_launch_theme", "type": "RegisteredResources" } }
```

### สี CI ของ COM7

ดึงจากไฟล์ `logocom7.png` ด้วย Pillow ไม่ได้เดา

```python
from PIL import Image; from collections import Counter
im = Image.open("logocom7.png").convert("RGB")
for (r,g,b), n in Counter(im.getdata()).most_common(6):
    print(f"#{r:02x}{g:02x}{b:02x}  {n:,}")
```

| บทบาท | hex | สัดส่วนในโลโก้ |
|---|---|---|
| **เขียว COM7** (เลข 7) | `#5cb047` | 11.5% |
| **เทา COM7** (ตัว com) | `#828285` | 16.3% |

### ชุดสีกราฟที่ผ่านการตรวจแล้ว

```
#5cb047  #2a6fb8  #e8833a  #7a5bbd  #c2456b  #eda100  #4a3aa7  #2f9e8f
 เขียวCI   น้ำเงิน    ส้ม      ม่วง     บานเย็น   เหลือง   ม่วงเข้ม  เขียวน้ำทะเล
```

ตรวจด้วย validator (skill `dataviz`) ไม่ได้เลือกด้วยตา

```
[PASS] ความสว่าง        ทั้ง 8 อยู่ในแถบ L 0.43-0.77
[PASS] ความอิ่มสี        ไม่มีสีไหนซีดจนดูเป็นเทา
[PASS] แยกออกเมื่อตาบอดสี  คู่แย่สุด dE 13.5  (เกณฑ์ 8)
[PASS] แยกออกด้วยตาปกติ    คู่แย่สุด dE 17.9  (เกณฑ์ 15)
```

หลักที่ใช้ — **น้ำเงิน+ส้มเป็นคู่หลัก · ห้ามคู่แดง-เขียว · 8 สีคือจุดพอดี**
ถ้าจะสลับลำดับสีเอง **ต้องรันตรวจใหม่** เพราะการตรวจดูคู่ที่ติดกันในลิสต์

### โครงธีมที่ใช้อยู่

```json
{
  "name": "COM7 NPI Launch",
  "dataColors": ["#5cb047", "..."],
  "good": "#5cb047", "neutral": "#eda100", "bad": "#c2456b",
  "maximum": "#22541a", "center": "#8ecb7c", "minimum": "#e6f2e1",
  "background": "#ffffff", "secondaryBackground": "#f4f5f6",
  "tableAccent": "#5cb047",
  "foreground": "#20232a", "foregroundNeutralSecondary": "#5c5f66",
  "textClasses": { "title": {...}, "callout": {...} },
  "visualStyles": {
    "*":        { "*": { "background": [...], "border": [...], "legend": [...] } },
    "card":     { "*": { "labels": [...] } },
    "tableEx":  { "*": { "grid": [...], "columnHeaders": [...] } },
    "image":    { "*": { "background": [{"show": false}], "border": [{"show": false}] } },
    "page":     { "*": { "background": [...], "outspace": [...] } }
  }
}
```

ระวัง — ใส่ `"show": true` ใน `visualStyles["*"]["*"]["labels"]` = **เปิด data label ทุกกราฟทั้งรายงาน** รก ให้เปิดเป็นราย visual แทน

---

## เพิ่มแท็บ

1. สร้าง `pages/<pageId ใหม่>/page.json`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
  "name": "b2f41a90c7e5486d1a03",
  "displayName": "พื้นที่ · สาขา",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```

2. เพิ่มลง `pages/pages.json`

```json
{ "pageOrder": ["หน้า1", "หน้า2", "หน้า3", "หน้า4"], "activePageName": "หน้า1" }
```

`displayName` ใส่ไทยได้ · `name` ควรเป็น hex ยาว ๆ ไม่ซ้ำ

---

## ขั้นตอนทำงาน

```
1. ปิด Power BI Desktop ให้สนิท        ← สำคัญสุด ไม่งั้น save ทับงานที่แก้
2. แก้ไฟล์ .tmdl / .json
3. ตรวจ: JSON parse ผ่านไหม · visual ล้นขอบหน้าไหม · lineageTag ซ้ำไหม
4. เปิด .pbip
5. ถ้า Desktop เปิดผ่าน แล้ว save -> มันจะ reformat ไฟล์เป็นสไตล์ตัวเอง (ปกติ)
```

สคริปต์ตรวจก่อนเปิด

```python
import json, io, os, re
# 1 · TMDL
s = io.open(TMDL, encoding="utf-8").read()
t = re.findall(r"lineageTag: (\S+)", s)
assert len(t) == len(set(t)),          "lineageTag ซ้ำ"
assert not re.search(r"^ +", s, re.M), "มี space indent ปน"
assert "description:" not in s,        "มี description: ที่ใช้ไม่ได้"
assert "///" not in s,                 "มี /// ลอย"
# 2 · visual
for d in os.listdir(VIS):
    j = json.load(io.open(f"{VIS}/{d}/visual.json", encoding="utf-8"))
    p = j["position"]
    assert p["x"] + p["width"] <= 1280 and p["y"] + p["height"] <= 720, d
```

**เครื่องนี้ต้องใส่ `PYTHONIOENCODING=utf-8`** ตอนรัน python ที่ print ภาษาไทย ไม่งั้น `UnicodeEncodeError: cp874`
และอย่าส่งสคริปต์ที่มีภาษาไทยผ่าน bash heredoc — เขียนลงไฟล์ก่อนแล้วค่อยรัน

---

## สิ่งที่ยังทำผ่านไฟล์ไม่ได้ (ต้องไปกดใน Desktop)

| อยากได้ | สถานะ |
|---|---|
| หัวเรื่อง textbox | **[ยังไม่ยืนยัน]** ยังไม่เคยลอง ลากใส่เองใน Desktop เร็วกว่า |
| sync slicer ข้ามแท็บ | **[ยังไม่ยืนยัน]** — ใช้ `View ▸ Sync slicers` แทน |
| กำหนดสีราย series เอง (ไล่เฉดตามปี) | **[ยังไม่ยืนยัน]** ต้องใช้ `dataPoint` + `scopeId` selector |
| Top N filter | ต้องเขียน `filterConfig` **[ยังไม่ยืนยัน]** — เลี่ยงโดยใช้ตารางแล้วคลิกหัวคอลัมน์เรียง |

---

## ขึ้น git

ใส่ `.gitignore`

```gitignore
Powerbi/**/.pbi/cache.abf
Powerbi/**/.pbi/localSettings.json
Powerbi/**/.pbi/editorSettings.json
*.pbix
```

`cache.abf` คือข้อมูลที่ import มาทั้งก้อน — หลุดขึ้น git แล้วทั้ง **PII และไฟล์เกิน 5 MB**
ถ้าเผลอ add ไปแล้ว `.gitignore` ไม่ช่วย ต้อง `git rm -r --cached <path>`

---

## เชื่อม Power BI Service

โมเดลนี้ต่อ SQL Server ที่เป็น **private IP** — Power BI Service มองไม่เห็น
ถ้าจะ publish ขึ้น workspace ต้องตั้ง **on-premises data gateway** ก่อน ยังไม่ได้ทำ

---

## ดูเพิ่ม

- [[Analytics & AI]] — เครื่องมือวิเคราะห์อื่นในทีม
- [[Git & GitHub]] — วิธี commit ไฟล์ในโปรเจกต์นี้
- [[ITEC - Query Cookbook]] — ดึงข้อมูล ITEC ที่เป็นต้นทางของโมเดลนี้
- [[Python Libraries]] — Pillow ที่ใช้ดึงสีจากโลโก้
