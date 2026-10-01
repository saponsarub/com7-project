# ITOS — Address & Geography

วิธีหา **จังหวัด / อำเภอ / ตำบล ของลูกหนี้ ITOS** ให้ถูกและครบ
สำรวจ 2026-09-30 ตอนทำงาน [[ITOS Flood Waiver 2026-09]]

ระบบแม่ → [[ITOS Overview]] · ระบบคู่ → [[K2 - Customer & Address]]

> **สรุปสั้น:** ใช้ `COLLECTION_S_ADDRESS` แล้ว join ด้วย**รหัส** ไปที่ `HP_COMMON_*`
> **อย่า**ใช้ `CUSTOMER_ADDRESS_REGISTER` / `_CURRENT` ใน `ITOS_COLLECTION_DETAIL`
> เป็นแหล่งหลัก — เป็นข้อความก้อนเดียว และ**ว่าง 15.3%**

---

## ที่อยู่ลูกหนี้ ITOS มี 3 ทาง — เลือกทางที่ 1

| # | ทาง | คีย์ | ครอบคลุม | โครงสร้าง | ใช้ไหม |
|---|---|---|---|---|---|
| **1** | **`COLLECTION_S_ADDRESS`** | `ADDR_CONTRACTNO` | **329,078 / 329,078 = 100%** | **รหัส** จังหวัด/อำเภอ/ตำบล | ✅ **ใช้ตัวนี้** |
| 2 | `M_CUST_ADDRESS` | `CUSTOMER_ID` | 278,726 (84.7%) | รหัส | ⚠️ ต้องผ่าน stage ก่อน |
| 3 | `ITOS_COLLECTION_DETAIL.CUSTOMER_ADDRESS_*` | `CONTRACT_ID` | 278,726 (84.7%) | **ข้อความก้อนเดียว** | ❌ ใช้สอบทานเท่านั้น |

**ทำไมทาง 2 กับ 3 ได้เท่ากันเป๊ะ** — ทั้งคู่มีต้นทางเดียวกันคือ
`ITOS_STAGE_ADDRESS` (278,802 แถว) ซึ่งมีไม่ครบทุกสัญญา
สัญญาที่ตกไป 50,352 รายไม่มีที่อยู่ในสองทางนี้เลย แต่**มีใน `COLLECTION_S_ADDRESS`**

```
ITOS_COLLECTION_DETAIL ──┬─→ ITOS_STAGE_ADDRESS ─→ M_CUST_ADDRESS   84.7%
   (CONTRACT_NUMBER)      │      (CUSTOMER_ID)
                          └─→ COLLECTION_S_ADDRESS                  100%   ⭐
                                 (ADDR_CONTRACTNO)
```

---

## ⚠️ กับดัก 1 — ชื่อคอลัมน์ `COLLECTION_S_ADDRESS` หลอก

| คอลัมน์ | ชื่อบอกว่า | **เก็บจริง** | ยาว |
|---|---|---|---|
| `ADDR_PROVINCE` | จังหวัด | **รหัสจังหวัด** | 2 หลัก |
| `ADDR_AMPHUR` | อำเภอ | **รหัสอำเภอ** | 4 หลัก |
| `ADDR_DISTRICT` | อำเภอ (district) | **รหัสตำบล** ← ไม่ตรงชื่อ | 6 หลัก |
| `ADDR_ZIPCODE` | ไปรษณีย์ | รหัสไปรษณีย์ | 5 หลัก |

**สองชั้นซ้อนกัน:** (ก) เก็บเป็น *รหัส* ไม่ใช่ *ชื่อ* (ข) `ADDR_DISTRICT` เก็บ**ตำบล**

> ผลของการไม่รู้: `JOIN HP_COMMON_PROVINCE ON NAME_THA = ADDR_PROVINCE`
> ได้ NULL **ทั้ง 658,768 แถว** โดยไม่มี error — query รันผ่าน ผลว่างเปล่า

## ⚠️ กับดัก 2 — `ADDR_TYPE` ไม่มีตาราง master

ไม่มีตารางไหนในฐานถอดรหัส `AD01`–`AD04` ให้ ถอดได้จากการเทียบข้อมูลจริง
กับ `CUSTOMER_ADDRESS_CURRENT` / `_REGISTER` ของสัญญาเดียวกัน

| รหัส | คือ | หลักฐาน |
|---|---|---|
| **`AD01`** | **ที่อยู่ปัจจุบัน** | `TFF2609-035420` AD01 = ระยอง/ปลวกแดง ตรงกับ `_CURRENT` |
| **`AD02`** | **ตามทะเบียนบ้าน** | สัญญาเดียวกัน AD02 = นครราชสีมา/พิมาย ตรงกับ `_REGISTER` |
| `AD03` | ที่ทำงาน | ต่างจากทั้งสองฝั่ง · ชี้ไปนิคมอุตสาหกรรม (เชียงรากน้อย บางปะอิน) |
| `AD04` | ที่อยู่จัดส่ง | เท่ากับ AD02 ในตัวอย่างที่ตรวจ |

มีครบ 4 ประเภทต่อสัญญาเสมอ (329,384 แถวต่อประเภท)

## ⚠️ กับดัก 3 — `(สัญญา, ADDR_TYPE)` ซ้ำได้

1,315,864 คู่มี 1 แถว · **836 คู่มี 2 แถว** → ต้องเลือกแถวเดียวก่อน join
ไม่งั้นแถวงอก ใช้ `ROW_NUMBER() OVER (PARTITION BY ADDR_CONTRACTNO, ADDR_TYPE ORDER BY ADDR_ID DESC)`

---

## ตาราง master ภูมิศาสตร์ — ตรงกับทะเบียนราชการเป๊ะ

| ตาราง | แถว | คีย์ | ทะเบียนราชการ | ตรงไหม |
|---|---|---|---|---|
| `HP_COMMON_PROVINCE` | 77 | `PROVINCE_CODE` 2 หลัก | 77 จังหวัด | ✅ |
| `HP_COMMON_DISTRICT` | 928 | `DISTRICT_CODE` 4 หลัก | 928 อำเภอ | ✅ |
| `HP_COMMON_SUBDISTRICT` | 7,437 | `SUBDISTRICT_CODE` 6 หลัก | 7,425 ตำบล | ต่าง 12 `[อนุมาน]` |

มี `NAME_THA` **และ** `NAME_ENG` ทั้งสามระดับ · `GEOGRAPHY_CODE` = ภาค · `AREA` = IN/OUT
`HP_COMMON_SUBDISTRICT` มี `ZIPCODE_CODE` ด้วย → **ใช้เป็นตาราง zip → ตำบล ได้**

> เทียบกับที่เราสร้างจาก PDF ราชบัณฑิตยสภาไว้ที่ `scripts/geo/_out/dim_admin_flat.csv`
> (77 / 928 / 7,425) — **จำนวนจังหวัดและอำเภอตรงกันเป๊ะ**
> ตำบลต่าง 12 แถว ยังไม่ได้ไล่ว่าเพราะอะไร → [[Thai Administrative Dimension]]
> **ถ้างานอยู่ในฐานนี้อยู่แล้ว ใช้ `HP_COMMON_*` ดีกว่า** เพราะ join ด้วยรหัสได้เลย

---

## Query ที่ใช้ได้เลย

```sql
-- ที่อยู่ทะเบียนบ้าน (AD02) + ปัจจุบัน (AD01) ของทุกสัญญา ITOS
-- ⚠️ ADDR_AMPHUR = รหัสอำเภอ · ADDR_DISTRICT = รหัสตำบล (ชื่อคอลัมน์หลอก)
WITH addr AS (
    SELECT  ADDR_CONTRACTNO, ADDR_TYPE, ADDR_PROVINCE, ADDR_AMPHUR,
            ADDR_DISTRICT, ADDR_ZIPCODE,
            rn = ROW_NUMBER() OVER (PARTITION BY ADDR_CONTRACTNO, ADDR_TYPE
                                    ORDER BY ADDR_ID DESC)   -- 836 คู่ซ้ำ
    FROM    ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.COLLECTION_S_ADDRESS WITH (NOLOCK)
    WHERE   ADDR_TYPE IN ('AD01','AD02')
)
SELECT      d.CONTRACT_NUMBER,
            rp.NAME_THA AS reg_จังหวัด, rd.NAME_THA AS reg_อำเภอ,
            rs.NAME_THA AS reg_ตำบล,    r.ADDR_ZIPCODE AS reg_ไปรษณีย์,
            cp.NAME_THA AS cur_จังหวัด, cd.NAME_THA AS cur_อำเภอ,
            cs.NAME_THA AS cur_ตำบล,    c.ADDR_ZIPCODE AS cur_ไปรษณีย์
FROM        ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.ITOS_COLLECTION_DETAIL d WITH (NOLOCK)
LEFT JOIN   addr r ON r.ADDR_CONTRACTNO = d.CONTRACT_NUMBER
                  AND r.ADDR_TYPE = 'AD02' AND r.rn = 1
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.HP_COMMON_PROVINCE    rp ON rp.PROVINCE_CODE    = r.ADDR_PROVINCE
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.HP_COMMON_DISTRICT    rd ON rd.DISTRICT_CODE    = r.ADDR_AMPHUR
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.HP_COMMON_SUBDISTRICT rs ON rs.SUBDISTRICT_CODE = r.ADDR_DISTRICT
LEFT JOIN   addr c ON c.ADDR_CONTRACTNO = d.CONTRACT_NUMBER
                  AND c.ADDR_TYPE = 'AD01' AND c.rn = 1
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.HP_COMMON_PROVINCE    cp ON cp.PROVINCE_CODE    = c.ADDR_PROVINCE
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.HP_COMMON_DISTRICT    cd ON cd.DISTRICT_CODE    = c.ADDR_AMPHUR
LEFT JOIN   ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.HP_COMMON_SUBDISTRICT cs ON cs.SUBDISTRICT_CODE = c.ADDR_DISTRICT
```

---

## การเข้าถึง

ทุกตารางข้างบนอยู่ในฐาน **`ILOAN_DATASOURCE`** เข้าถึงผ่าน **linked server ของ k2**
(`43.254.133.123` · profile `k2` ใน `scripts/db.py`)

```
ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo.<ตาราง>
  ^linked server   ^ฐาน           ^schema
```

⚠️ **linked server ตัวนี้ข้ามฐานไม่ได้** — อ้าง `ILOAN_COLLECTION.` หรือ `master.sys.`
จะได้ error *"Reference to database and/or server name ... is not supported"*
ตาราง `S_CUSTADDR` / `S_ADDRESS` / `M_PROVINCE` ที่ [[ITOS Overview]] พูดถึงอยู่ในฐาน
`ILOAN_COLLECTION` จึง**เอื้อมไม่ถึงทางนี้** — ของที่ใช้ได้คือสำเนาในฐานนี้
ชื่อขึ้นต้น `COLLECTION_*` (เช่น `COLLECTION_S_ADDRESS`)

⚠️ **ห้ามใส่ `WITH (NOLOCK)`** — ตารางที่มาทาง linked server เป็น *external table*
จะได้ error **46915** *"Table hints are not supported on queries that reference
external tables"* · เขียน `FROM ... d` เปล่า ๆ

schema ในฐานนี้: `dbo` 296 ตาราง · `ext_collection` 9 · `ext_cash_receive` 2

---

## ที่อยู่ข้อความ — ถ้าจำเป็นต้องแกะ

`ITOS_COLLECTION_DETAIL.CUSTOMER_ADDRESS_REGISTER` / `_CURRENT` / `_DELIVERY`
เป็น `nvarchar(2000)` ก้อนเดียว รูปแบบท้ายสตริงคงที่

```
148 เธก.หมู่ที่ 8 ยี่ล้น วิเศษชัยชาญ อ่างทอง 14110
                  ^ตำบล  ^อำเภอ      ^จังหวัด ^ไปรษณีย์
```

| เรื่อง | รายละเอียด |
|---|---|
| **mojibake** | `เธก.` คือ `ม.` ที่ decode เป็น CP874 แทน UTF-8 · `เธเธฑเนเธ` คือ `ชั้น` |
| ลงท้ายด้วย zip 5 หลัก | 278,726 / 278,726 ของแถวที่มีที่อยู่ |
| zip ผิดความยาว | มี `120120` · `4000` · `12` → ต้องตัด token เลขท้ายทุกกรณี ไม่ใช่แค่ 5 หลัก |
| แกะจังหวัด+อำเภอได้ | **100% ของแถวที่มีที่อยู่** (278,726) |
| แกะตำบลได้ | 98.8% — ที่พลาดคือที่อยู่ กทม. ที่มีชื่อซอยคั่น และคำสะกดต่าง (`จรเข้มาก` vs `จระเข้มาก`) |

โค้ดอยู่ที่ `scripts/itos/_addr_text.py` — ใช้เป็น**ตัวสอบทาน**ผลจากการ join รหัส

> **บทเรียนโค้ด:** dict ค้นหาต้องใช้คีย์ tuple ทุกระดับ
> ถ้าระดับจังหวัดเป็น `str` แต่ค้นด้วย `prefix + (k,)` จะได้ **0%** โดยไม่ error
> — ดูเหมือนข้อมูลพัง แต่จริง ๆ คือคีย์ผิดชนิด

---

## เชื่อมกับโน้ตอื่น

[[ITOS Overview]] · [[K2 - Customer & Address]] · [[ITOS Flood Waiver 2026-09]] ·
[[Thai Administrative Dimension]] · [[Data Standardization & Quality]] · [[Customer Identity]]
