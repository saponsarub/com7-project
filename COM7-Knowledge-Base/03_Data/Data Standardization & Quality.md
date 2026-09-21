# Data Standardization & Quality

ความจำเป็นพิสูจน์แล้วจากงานจริง · มาตรฐานเองยังไม่มี

---

## Evidence: the K2 / ITOS union query

ไฟล์ `C:\Projects\Data-Team-Code\Adhoc Project\UFF\K2_U_ITOS_P1.sql`

รวมสองระบบที่อยู่ในโดเมนธุรกิจเดียวกัน (collection ของ UFUND) และต้องแก้ทุกอย่างต่อไปนี้ในคิวรี่เดียว

### Different spellings for the same thing

| ITOS | K2 |
|---|---|
| `TOTAL_PRINCIPAL` | `TOTAL_PRINCIPLE` |
| `PAID_TOTAL_PRINCIPAL` | `PAID_TOTAL_PRINCIPLE` |
| `REMAINING_PRINCIPAL` | `REMAINING_PRINCIPLE` |
| `PAID_TOTAL_PRINCIPAL_TO_DUE` | `PAID_TOTAL_PRINCIPLE_TO_DUE` |

### Typos baked into production column names

| ITOS | K2 |
|---|---|
| `PRODUCT_ID` | `PRODUDCT_ID` |

### Different names, same meaning

| ITOS | K2 |
|---|---|
| `CONTRACT_STATUS_ID` | `CONTRACT_STATUS` |
| `PRODUCT_NAME` | `MODEL_NAME` |

**ภายใน ITEC เองก็มี** — รหัสสินค้าตัวเดียวกันเรียก 2 ชื่อตาม schema

| schema `rpt` | schema `ci` (aggregate) |
|---|---|
| `ItemId` | `PRODUCT_ID` · `PRODUCT_ID_MAIN` · `_SALE` · `_STOCK` |

join ตรงได้ ไม่ต้องแปลง · ทดสอบแล้ว 99.2% ของรหัสไม่ซ้ำ → [[ITEC - Data Dictionary]]

⚠️ `PRODUCT_ID` ของ ITEC (รหัสสินค้า varchar) **ไม่ใช่** `PRODUCT_ID` ของ K2 (รหัสผลิตภัณฑ์สินเชื่อ int)
ชื่อชนกันข้ามระบบ — ต้องระบุ schema ทุกครั้งที่พูดถึง

### Data types do not match

ต้อง `CAST` เกือบทุกคอลัมน์:
```sql
CAST(a.CONTRACT_ID AS int)
CAST(a.CONTRACT_NUMBER AS nvarchar)
CAST(a.REMAINING_PRINCIPAL as float)
CAST(a.IS_FIRST_DUE as int)
CAST(a.CREATE_DATE as date)
```

### Collations do not match

ทุกคอลัมน์ข้อความต้องใส่ `COLLATE DATABASE_DEFAULT`:
```sql
CAST(a.CONTRACT_NUMBER AS nvarchar) COLLATE DATABASE_DEFAULT as CONTRACT_NUMBER
```

ถ้าไม่ใส่ `UNION ALL` จะพัง เพราะ SQL Server ไม่ยอมรวมคอลัมน์ที่ collation ขัดกัน `[อนุมาน]`

### Fields present on one side only

K2 ไม่มี `PRODUCT_MODEL`, `PRODUCT_SERIAL_NO`, `CREATE_DATE`, `MODIFY_DATE`:
```sql
CAST(NULL as nvarchar) COLLATE DATABASE_DEFAULT as PRODUCT_MODEL,
CAST(NULL as date) as CREATE_DATE
```

### Customer data is structured differently

- **K2** เก็บที่อยู่เป็น 3 คอลัมน์: `CUSTOMER_ADDRESS_REGISTER`, `_CURRENT`, `_DELIVERY`
- **ITOS** เก็บที่อยู่แยกตาราง `S_CUSTADDR` (746,916 แถว)

### Consequences

**K2 ไม่มี `CREATE_DATE` / `MODIFY_DATE`** แปลว่าดึงข้อมูลแบบ incremental ด้วย timestamp ไม่ได้ ต้องใช้ CDC หรือ full reload — กระทบดีไซน์ ingestion โดยตรง `[อนุมาน]`

---

## Other evidence

### GI Core (`schema.prisma`)

- `fisrt_name` — สะกดผิดในตาราง `customers`
- `IdentityCard` เป็น `VarChar(13)` และ **nullable**
- `address` เป็น `LongText` ไม่มีโครงสร้าง
- `OrgCode` enum = `Com7`, `Aion`, `DPI1`, `CFW` — taxonomy ระดับระบบที่ต้อง map เข้ากับ taxonomy ของกลุ่ม

บันทึกประชุม: *"data ของ EV7&GI ยังไม่สะอาดเท่าที่ควร บวกกับยังไม่ได้ทำการ standardize ให้เข้ากับ 7club"*

### ITOS

- คอลัมน์ข้อความเกือบทั้งหมดเป็น `nvarchar(500)` หรือ `(800)`
- มีชื่อไทยและอังกฤษคู่ขนาน (`CUST_NAMETH` / `CUST_NAMEEN`)
- `MS_Description: not defined` ทุก table ทุก column
- 167 tables ถูกตัดจาก wiki เพราะ zero-row หรือชื่อเป็น backup

### ITEC

`PROJECT_1.dbo.view_itec_payment` ใช้ชื่อคอลัมน์ภาษาไทย (`ประเภท`, `จำนวนเงินที่ได้รับ`)

### Group-wide

Gap Review `DQY-03`: *"ที่อยู่ภาษาไทยเขียนได้หลายรูปแบบ ทำให้ match พลาดสูงมากหากไม่ normalize"*

---

## Foundations the Gap Review says are missing

| ID | รายการ | สถานะ | P |
|---|---|---|---|
| DQY-01 | Data Dictionary + Field Definition | ขาด | P1 |
| DQY-02 | System of Record ต่อ field | ขาด | P1 |
| DQY-03 | Deduplication Rule + Address / Phone Normalization | ขาด | P1 |
| DQY-04 | Data Quality KPI: completeness / contactability / consent coverage | ขาด | P2 |
| DQY-05 | Create Date / Updated Date / Last Activity Date | ขาด | P2 |
| ARC-05 | Event Taxonomy / Naming Standard ข้าม BU | ขาด | P1 |
| MSR-06 | Data Quality KPI และรายงานคุณภาพ | ขาด | P2 |

**`DQY-05` เป็นการถดถอย** — รายงานระบุว่า *"หน้า Current มี Create/Updated Date แต่หายไปจากฝั่ง Propose"*

**หมายเหตุผู้รีวิวบน `DQY-01`:** *"ไม่เอา"*
แต่ `DQY-02` นิยามไม่ได้ถ้าไม่มี data dictionary และ survivorship rule ก็เขียนไม่ได้ถ้าไม่มี `DQY-02` `[อนุมาน]`

---

## What standardization must cover

จากที่ทีมร่างไว้ในนิยาม Silver layer:

- **Data type** — `"2024-01-01"` → date · `"1,234.56"` → decimal
- **Format** — เบอร์โทร → `+66XXXXXXXXX` · วันที่ → `YYYY-MM-DD`
- **Categorical** — `"M"` / `"Male"` / `"ชาย"` → `"M"`
- **Whitespace** — `" ABC  "` → `"ABC"`
- **Encoding** → UTF-8 (บันทึกระบุว่า *"กรณีข้อความภาษาไทยอ่านไม่ออก"*)
- **Null / Missing** — เติมค่า default ที่ตกลงไว้ หรือ drop record ที่ field สำคัญเป็น null
- **Business rule** — อายุห้ามติดลบ ราคาห้ามน้อยกว่า 0 ผิดให้ flag หรือแยกไป quarantine

บวกจาก Gap Review:
- **Address normalization** (`DQY-03`)
- **Event taxonomy ข้าม BU** (`ARC-05`)

**Naming** ทำที่ Bronze — บันทึกทีมระบุว่า *"ตั้งชื่อ table/column ใหม่ให้เป็นมาตรฐานขององค์กร"*

---

## Timing

Gap Review `ARC-05`:

> "ต้อง lock มาตรฐานการตั้งชื่อ event และ schema ก่อน BU อื่นเริ่ม onboard การแก้ภายหลังมีต้นทุนสูงมาก"
> ผลกระทบ: "ข้อมูลจากแต่ละ BU รวมกันแล้วเทียบกันไม่ได้ ต้องทำ mapping ย้อนหลังทั้งหมด"

ตอนนี้ survey เสร็จ 1 จาก 11 ระบบ — เป็นจังหวะที่ต้นทุนการตั้งมาตรฐานต่ำที่สุด `[อนุมาน]`

`PRODUDCT_ID` อยู่ใน production แล้วและแก้ที่ต้นทางไม่ได้โดยไม่กระทบผู้ใช้ปลายทาง

---

## Always keep provenance

เมื่อรวมข้อมูลจากหลาย source ให้บันทึกว่าแต่ละแถวมาจากไหน

COM7 ทำแล้ว 2 ที่โดยอิสระ:
- `SOURCE_SYSTEM` ในคิวรี่ union K2/ITOS
- `IDN-02 Source Customer ID` ในแนวทาง identity ที่ Gap Review ระบุว่า "มีแล้ว"
- UnionPlan2 ก็ระบุ *"เพิ่ม column ระบุว่า migrate มาจากไหน"*

สามแหล่งพูดตรงกัน น่าจะกำหนดเป็นมาตรฐานกลุ่มได้ `[อนุมาน]`

---

## Quarantine

จากนิยาม layer ที่ทีมร่าง: ข้อมูลที่ผิด business rule ให้ *"flag หรือแยกไปเก็บใน quarantine"*

ควรบันทึกเหตุผลที่ reject ไว้ด้วย ไม่งั้นไม่มีใครรู้ว่า reject ถูกไหม และต้นทางจะไม่ถูกแก้ `[อนุมาน]`

### Critical vs non-critical field

จากนิยาม Silver ที่ทีมร่าง: *"เติมค่า default ที่ตกลงกันไว้ หรือ drop record ที่ field สำคัญ (primary key) เป็น null"*

การจัดว่า field ไหนสำคัญต้องระบุชัด ซึ่งต้องมี `DQY-01` `[อนุมาน]`

---

## The method the team recorded

จาก UnionPlan2:

1. **Schema Mapping ในเอ็กเซล** — เช็ค column และ datatype ให้ตรงกัน
2. **สร้าง Schema เปล่าๆ** — กำหนด datatype ใหม่ pk ใหม่ เพิ่ม column ระบุว่ามาจากไหน
3. **Insert ทีละ table**
4. **Stored Procedure Incremental**
5. **กำหนด schedule**

ขั้นที่ 1 บังคับให้เห็นความไม่ตรงกันทั้งหมดก่อนเขียนโค้ด `[อนุมาน]`

---

## Cleaning rules are per BU

`datacleanplan.txt`:

> "วางแผน Data Cleaning แต่ละ BU กำหนด Cleaning Rules ตามลักษณะข้อมูลของแต่ละ BU"

จัดการความแปลกของแต่ละ BU ในที่ที่เข้าใจมัน แล้วค่อยรวมเข้ามาตรฐานกลาง `[อนุมาน]`

---

## Lessons that apply to all 11 systems

`[อนุมาน]` — จากปัญหาที่เจอจริง ใช้เป็น checklist ตอน survey ได้:

- Schema ของระบบพี่น้องต่างกันเป็นเรื่องปกติ ไม่ใช่ข้อยกเว้น
- เช็ค **collation** ตั้งแต่ต้นเมื่อทำงานข้ามฐาน — error ชี้ไปที่ `UNION` ไม่ใช่ที่ต้นเหตุ
- เช็คว่ามี **audit column** (`created_at` / `updated_at`) ไหม — ไม่มีแล้วเปลี่ยนวิธี ingest
- เช็คว่า **match key เป็น nullable** ไหม
- Typo ในชื่อคอลัมน์แก้ไม่ได้แล้ว ต้อง map ที่ Bronze
- Union view ใช้วิเคราะห์ได้ แต่ไม่ใช่สถาปัตยกรรมระยะยาว

## ตัวอย่างจริงจากฐาน ITEC (2026-08-28)

| ปัญหา | หลักฐาน |
|---|---|
| **ชื่อแบรนด์ไม่เป็นมาตรฐาน** | ต้องมีตาราง `ci.clean_brand_itec` **2,685 แถว** เพื่อแม็ปชื่อดิบ → ชื่อมาตรฐาน |
| **หมวดหมู่ไม่เป็นมาตรฐาน** | `ci.clean_category_ITEC` **1,966 แถว** · หมวดดิบปนทั้งอังกฤษและไทย ("Smartphone" กับ "รายการส่งเสริมการขาย") |
| **`Brand` ว่าง 5.4%** | 11,745 จาก 216,009 รายการไม่มีแบรนด์ |
| **จังหวัดผิด** | สาขา "Studio 7-Mega-Bangna" ระบุจังหวัดเป็น **Trat** ทั้งที่เมกาบางนาอยู่สมุทรปราการ |
| **ช่องกรอกอิสระถูกใช้เป็นคีย์** | `dim_mem_itec.memcode` มี 20 ความยาวปนกัน · 1.35 ล้านแถวเป็นเบอร์โทรศัพท์ |
| **placeholder แทน NULL** | `crmid = '-'` 42,613 แถว |
| **ชื่อคอลัมน์สะกดผิด** | `IS_Buletooth` (ควรเป็น Bluetooth) |
| **ชนิดข้อมูลผิด** | `dim_officer_itec.OfficerName` เป็น `int` ทั้งที่เป็นชื่อคน |
| **ชื่อคอลัมน์มีอักขระพิเศษ** | `[GP %]` · `[Model/Series]` · `[TRANS DATE]` · `[CC NO_]` — ต้องครอบ `[ ]` ทุกครั้ง |

### ของดีที่ ITEC มีอยู่แล้ว

- **`ci.thailand_map`** 77 จังหวัด ไทย/อังกฤษ + ภูมิภาค → **ใช้เป็น master ภูมิศาสตร์กลางของทั้งกลุ่มได้**
- **ชั้น `ci`** ทำ standardization ไว้แล้ว — ต่างจาก K2 ที่ต้องทำเองทั้งหมด

---

## เชื่อมกับโน้ตอื่น

[[Customer Identity]] · [[ITOS Overview]] · [[EV Business]] · [[Architecture]] · [[SQL & Source Schemas]]
