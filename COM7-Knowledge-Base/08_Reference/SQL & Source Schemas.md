# SQL & Source Schemas

---

## Databases seen in the team's SQL

| ฐาน / Server | Engine | ระบบ |
|---|---|---|
| `ILOAN_COLLECTION` | MSSQL | ITOS |
| `ILOAN_DATASOURCE` | MSSQL | extract ของ ITOS |
| `HPCOM7` | MSSQL | K2 — **545 tables · 165 views · สำรวจครบแล้ว** |
| `D365FO_DATALAKE` | ไม่ระบุ | D365 |
| `syndpdev001` | Azure Synapse | Synapse |
| `PROJECT_1` | MSSQL | view ของ ITEC |
| `TAN_MIS` | MSSQL | MIS |
| (GI Core) | **MySQL** | GI Core |

---

## Collations must match in a UNION

```sql
CAST(a.CONTRACT_NUMBER AS nvarchar) COLLATE DATABASE_DEFAULT AS CONTRACT_NUMBER
```

จำเป็นกับทุกคอลัมน์ข้อความตอนรวม K2 กับ ITOS เพราะสองฐานใช้ collation คนละแบบ

Error จาก collation จะชี้ไปที่ `UNION` ไม่ใช่ที่ต้นเหตุ ทำให้วินิจฉัยผิดได้ง่าย — ควรเช็ค collation ตั้งแต่ต้นเมื่อทำงานข้ามฐาน `[อนุมาน]`

---

## Filling in missing columns

```sql
CAST(NULL AS nvarchar) COLLATE DATABASE_DEFAULT AS PRODUCT_MODEL
```

ยังต้อง cast เพราะ `NULL` เปล่าๆ ไม่มี type และ `UNION` ต้องการ type ที่ตรงกัน

---

## Adding a source column

```sql
SELECT ..., 'ITOS' AS SOURCE_SYSTEM FROM ...
UNION ALL
SELECT ..., 'K2'   AS SOURCE_SYSTEM FROM ...
```

---

## Thai column names

ตัวอย่างจริงจาก `PROJECT_1.dbo.view_itec_payment`:

```sql
SELECT ISNULL(vip.ประเภท, 'Total') AS Type,
       FORMAT(SUM(vip.[จำนวนเงินที่ได้รับ]), 'N0') AS ยอดเงินรวม
FROM [PROJECT_1].[dbo].[view_itec_payment] vip
```

ต้อง bracket-quote และระวัง encoding ตลอดเส้นทาง

---

## Typos already in production

| ที่ควรเป็น | ที่มีจริง | ระบบ |
|---|---|---|
| `PRODUCT_ID` | `PRODUDCT_ID` | K2 |
| `PRINCIPAL` | `PRINCIPLE` | K2 |
| `first_name` | `fisrt_name` | GI Core |
| `IMPORT` | `BANK_IMPRORT` (ชื่อตาราง) | K2 |
| `VOUCHER_NO` | `VOURCHER_NO` | K2 |
| `ACCOUNT_DESCRIPTION` | `ACCOUNT_DESCIPTION` | K2 |
| `CONTRACT_NUMBER` | `CONTARCT_NUMBER` | K2 |
| `MOO` (หมู่) | `A1_MOI` | K2 |
| `LIVING_TIME` | `A1_LIVEING_TIME` | K2 |
| `PRODUCT_BRAND` | `PRODUCT_BAND` | K2 |

แก้ที่ต้นทางไม่ได้แล้วโดยไม่กระทบผู้ใช้ ต้อง map ให้ถูกที่ Bronze `[อนุมาน]`

---

## Incremental extraction

| วิธี | ต้องมี | หมายเหตุ |
|---|---|---|
| Timestamp watermark | คอลัมน์ `updated_at` | **K2 มี** — `CREATE_DATE` + `UPDATE_DATE` บน `PERSON`, `CONTRACT`, `APPLICATION`, `QUOTATION`, `REPAYMENT` |
| CDC จาก transaction log | DB รองรับ CDC | วิธีของ DMS |
| ID watermark | key ที่เพิ่มเรื่อยๆ | ตาราง insert-only |
| Full reload | ไม่ต้องมีอะไร | ตารางเล็กเท่านั้น |

ควรเช็คว่ามี audit column ไหมตอน survey เพราะการไม่มีมันเปลี่ยนวิธี ingest `[อนุมาน]`

> **แก้ข้อสรุปเดิม:** เคยเขียนว่า K2 ไม่มี timestamp จึงทำ incremental ไม่ได้ — ข้อสรุปนั้นมาจากดู `COLLECTION_OD_ASSIGNMENT` ตารางเดียวซึ่งเป็น **extract** ไม่ใช่ตารางต้นทาง
> survey 2026-08-26 พบว่าตารางต้นทางมี `CREATE_DATE` + `UPDATE_DATE` ครบ
> **บทเรียน: อย่าสรุปคุณสมบัติของทั้งระบบจากตารางเดียว โดยเฉพาะถ้าตารางนั้นเป็น view หรือ extract** `[อนุมาน]`

---

## Reading an unfamiliar schema

วิธีที่ใช้กับ ITOS ได้ผล `[อนุมาน]`:

1. **นับแถวก่อน** — เห็นว่าตารางไหนสำคัญจริง (`S_PMTSCHDLE` 3.77M vs `M_PRODUCT` 16)
2. **ดู index usage stats** — `sys.dm_db_index_usage_stats` บอกว่า application อ่านอะไรจริง (แต่ reset เมื่อ restart)
3. **ดู naming convention** — ITOS ใช้ `M_` master · `S_` core · `T_` transaction · `R_` report
4. **ข้าม backup table** — ITOS มีถูกตัด 167 tables เพราะ zero-row หรือชื่อ `BK_*`, `*_BK`, ลงท้ายตัวเลข
5. **ดู sample rows** — schema wiki ของ ITOS มี Top 10 rows ต่อ table ซึ่งเผยข้อมูลจริง เช่น `M_COMPANY` มีชื่อบริษัท และ `M_CHANNEL` มีช่องทางชำระเงิน

### Added after working on K2 (542 tables)

วิธี 5 ข้อข้างบนยังใช้ได้ แต่กับฐานที่ใหญ่กว่าและไม่มี FK ต้องเพิ่มอีก 4 ข้อ `[อนุมาน]`

6. **นับ foreign key ก่อนเป็นอันดับแรก** — K2 มี **16 FK ทั้งฐาน** ถ้าตัวเลขนี้ต่ำ แปลว่าเครื่องมือสร้าง ER อัตโนมัติจะไร้ประโยชน์ และต้องวางแผนพิสูจน์ relation ด้วยการ join จริงตั้งแต่ต้น
```sql
SELECT COUNT(*) FROM sys.foreign_keys;
```

7. **เช็คว่า cardinality ตรงกับชื่อไหม ก่อนเชื่อชื่อตาราง** — `CUSTOMER_CARD` มี 5.8M แถวต่อสัญญา 288k ตัว **ไม่มีทางเป็นทะเบียนลูกค้า** พอเปิดดูจริงคือตารางผ่อนรายงวด
> ถ้าจำนวนแถวไม่สมเหตุสมผลกับชื่อ ให้เชื่อจำนวนแถว

8. **ตรวจว่าคอลัมน์ที่ดูเหมือนคีย์ ถูกใช้จริงหรือเปล่า** — `CIF_PERSON_ID` มีอยู่ในทุกตารางหลักของ K2 แต่ว่าง 99.97% และ `CONTRACT.STATUS_HP` เป็น NULL 288,201 จาก 288,205 แถว
```sql
SELECT COUNT(*) total,
       SUM(CASE WHEN COL IS NULL OR COL = 0 THEN 1 ELSE 0 END) empty
FROM T;
```
**คอลัมน์ที่มีชื่อถูกต้องแต่ไม่มีข้อมูล อันตรายกว่าคอลัมน์ที่ไม่มีอยู่** เพราะทำให้วางแผนผิด

9. **ดู type จริง ไม่ใช่ชื่อ** — `ADDRESS.A1_PROVINCE` ชื่อบอกว่าจังหวัดแต่เป็น `nvarchar` ที่เก็บรหัสตัวเลข ต้อง `TRY_CAST` ก่อน join
เช่นเดียวกัน `NUMBER_OF_OD_INSTALLMENT` และ `INSTALL_OD_SUM` เป็น `nvarchar` ทั้งที่เป็นตัวเลข

### Check permissions before planning a survey

กับ ITOS อ่าน `sys.dm_db_index_usage_stats` ได้ กับ K2 ไม่ได้ — **ต้องรู้ก่อนว่าจะได้อะไรบ้าง**

| ต้องการ | ต้องมีสิทธิ์ | ถ้าไม่มี |
|---|---|---|
| จำนวนแถว, คอลัมน์, index | อ่าน `sys.*` ปกติ | — |
| ตารางไหนถูกอ่านจริง | `VIEW SERVER STATE` | เดาจาก row count + modify_date แทน |
| SQL ของ view / stored proc | `VIEW DEFINITION` | เห็นแค่ชื่อกับคอลัมน์ |

การอ่าน view definition ได้มีค่ามากในฐานที่ไม่มี FK เพราะ view คือที่ที่ทีมเจ้าของระบบเขียน join ที่ถูกต้องไว้แล้ว — **ควรขอสิทธิ์นี้ตั้งแต่ต้นเวลาขอ access** `[อนุมาน]`

### Mask when sampling

ตอนดึง sample rows จากฐานที่มี PII ให้ mask **ก่อน**เขียนลงไฟล์เสมอ ไม่ใช่หลัง
เก็บค่าจริงไว้เฉพาะ **เงิน · วันที่ · รหัสสถานะ · surrogate key** เพราะจำเป็นต่อการเข้าใจ business
ตัวอย่างที่ใช้จริง: `scripts\k2\k2_samples.py` ใน `C:\Projects\my-first-project\`

---

## Prisma

GI Core ใช้ Prisma — `schema.prisma` เป็น data dictionary ที่อ่านได้ทั้งไฟล์

### How to read it

```prisma
model customers {
  id_customer   Int       @id @default(autoincrement())
  fisrt_name    String    @db.VarChar(255)     // บังคับ
  last_name     String?   @db.VarChar(255)     // ? = nullable
  email         String    @db.VarChar(255)     // บังคับ
  IdentityCard  String?   @db.VarChar(13)      // nullable
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  districts     districts? @relation(fields: [id_district_2], references: [id_district])
  @@index([id_district_2], map: "customers_id_district_2_fkey")
}
```

| Syntax | ความหมาย |
|---|---|
| `Type?` | nullable |
| `Type[]` | one-to-many |
| `@id` | primary key |
| `@unique` | unique constraint |
| `@default(...)` | ค่า default |
| `@updatedAt` | timestamp อัปเดตอัตโนมัติ |
| `@db.VarChar(n)` | type จริงในฐาน |
| `@relation(...)` | foreign key |
| `enum` | ชุดค่าที่จำกัด |

### What GI Core's schema.prisma yields

- 166 models
- `provider = "mysql"`
- `IdentityCard` **nullable** — match key อาจไม่มี
- `email` และ `tel` **NOT NULL**
- `address` เป็น `LongText`
- `enum OrgCode { Com7, Aion, DPI1, CFW }`
- model ที่บอกใบ้ integration: `taxi_follow_ufund`, `buyback_iphone`, `taxi_lineman`, `taxi_grab`

**Nullability คือสิ่งที่มีค่าที่สุดที่ดึงออกมาได้** — บอกทันทีว่ากลยุทธ์ dedupe ด้วยเลขบัตรต้องมี fallback `[อนุมาน]`

### Use before a survey meeting

ถ้าระบบมี Prisma schema ดึงข้อมูลพวกนี้ก่อนได้ `[อนุมาน]`:

- จำนวนและชื่อ model
- model ไหนถือข้อมูลลูกค้า
- nullability ของ match key ทุกตัว
- มี `createdAt` / `updatedAt` ไหม
- enum ที่ต้อง standardize
- relation ที่บอกใบ้ integration

บันทึกประชุมระบุว่าการสร้าง ER จาก Prisma *"ซับซ้อนอยู๋"* · มีไฟล์ `ERD.svg` อยู่ข้าง schema แล้ว

---

## เชื่อมกับโน้ตอื่น

[[ETL & Spark]] · [[AWS Services]] · [[K2 Overview]] · [[System Inventory]] · [[Data Standardization & Quality]]
