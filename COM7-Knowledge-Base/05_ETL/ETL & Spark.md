# ETL & Spark

> **หมายเหตุที่มา:** เนื้อหาส่วนใหญ่ในหน้านี้มาจากการทดลองเขียน ETL บนเครื่องตัวเอง (`D:\aws\Test_Spark`, `D:\aws\etl-lab`) ไม่ใช่ production code ของ COM7 — เก็บไว้เพราะปัญหาที่เจอจะเจอซ้ำตอนเขียน Glue job จริง

> **อัปเดต 2026-08-28** — ตัวอย่าง ETL จริงที่ใช้อยู่ + ข้อบกพร่องที่ต้องแก้ → [[Collection Union (K2 + ITOS)]]

---

## Spark ANSI mode — a problem hit for real

**Spark 4.x เปิด ANSI SQL mode เป็นค่าเริ่มต้น** ทำให้ function แปลง type **throw exception** เมื่อแปลงไม่ได้ แทนที่จะคืน `NULL`

```python
# Dies the moment it meets a badly formatted date
F.to_date(F.col("sale_date"), "yyyy-MM-dd")
# SparkDateTimeException [CANNOT_PARSE_TIMESTAMP]
```

**พฤติกรรมต่างกันตาม engine:**

| Engine | เจอวันที่ที่ parse ไม่ได้ |
|---|---|
| pandas `to_datetime(errors="coerce")` | คืน `NaT` |
| Spark 3.x `to_date()` | คืน `NULL` |
| **Spark 4.x `to_date()`** | **throw exception** |

### The fix

```python
F.coalesce(
    F.try_to_date(F.col("sale_date"), "yyyy-MM-dd"),
    F.try_to_date(F.col("sale_date"), "dd/MM/yyyy"),
    F.try_to_date(F.col("sale_date"), "yyyy/MM/dd"),
)
```

**กับดักซ้อน:** `format` ต้องเป็น string ธรรมดา ไม่ใช่ Column

```python
F.try_to_date(F.col("sale_date"), F.lit("yyyy-MM-dd"))  # PySparkTypeError: Column is not iterable
F.try_to_date(F.col("sale_date"), "yyyy-MM-dd")         # ถูก
```

### Why this matters for COM7

นิยาม Bronze→Silver ที่ทีมร่างไว้รวม *"แปลง Data Type ให้ถูกต้อง เช่น string "2024-01-01" → date"* และ *"Standardize format ... วันที่ เป็น (YYYY-MM-DD)"*

ข้อมูลต้นทางของ COM7 มีวันที่หลาย format จริง (คิวรี่ union K2/ITOS ต้อง `CAST(... as date)`)

**และภายใต้ ANSI mode หนึ่งแถวที่พังจะฆ่าทั้ง job** ซึ่งขัดกับ quarantine pattern ที่ทีมออกแบบไว้ `[อนุมาน]`

**กฎ:** ใช้ `try_*` (`try_to_date`, `try_cast`, `try_to_timestamp`) กับ input ที่ไม่เชื่อถือ ซึ่งใน Bronze→Silver คือเสมอ

---

## Job structure

แยก extract / transform / load เป็น method ทำให้ `transform()` เป็นฟังก์ชันบริสุทธิ์ที่ test ได้โดยไม่ต้องมี AWS

```python
class BronzeToSilverJob:
    def extract(self, spark):
        return spark.read.parquet(self.config.bronze_path)

    def transform(self, df):
        cleaned = self.cleaner.clean_pipeline(df)
        passed, rejected = self.validator.validate(cleaned)
        passed = self.cleaner.add_date_partitions(passed)
        return passed, rejected

    def load(self, passed, rejected):
        self.silver_writer.write(passed)
        self.quarantine_writer.write(rejected)
```

## Inject source/writer instead of constructing them

```python
job = BronzeToSilverJob(
    config,
    cleaner=DataCleaner,
    validator=DataQualityValidator(),
    silver_writer=PartitionedParquetWriter(path, ["year","month","day"]),
    quarantine_writer=PartitionedParquetWriter(qpath, []),
)
```

เปลี่ยนจาก local path เป็น `s3://...` แก้แค่ config — job เดียวกันรันบนเครื่องตอน dev และบน Glue ตอน production

## Config comes from the environment

```python
class Config:
    def __init__(self, base_dir):
        load_dotenv(base_dir / ".env")   # ระบุ path ชัดเจน
        self.bronze_path = os.environ.get("BRONZE_PATH", "data/bronze")
```

2 บทเรียนจากการทดลอง:
- ห้าม hard-code credential — ใช้ env var ตอน local, Secrets Manager บน AWS
- `load_dotenv()` ต้องระบุ path เพราะการเรียกเปล่าๆ ไปดู call stack เพื่อหา `.env` ซึ่งพังใน context ที่ไม่ปกติ

## Quarantine with a reason

```python
def validate(self, df):
    checked = self._build_reject_reason(df)
    passed   = checked.filter(F.col("reject_reason").isNull()).drop("reject_reason")
    rejected = checked.filter(F.col("reject_reason").isNotNull())
    return passed, rejected
```

ใช้ `concat_ws` สะสมทุกเหตุผลที่แถวนั้นผิด ไม่ใช่แค่ข้อแรก:

```python
F.concat_ws("; ",
    F.when(F.col("store_name").isNull(), "store_name is empty"),
    F.when(F.col("quantity") <= 0, "quantity must be > 0"),
    F.when(F.col("unit_price") <= 0, "unit_price must be > 0"),
)
```

## Partition

จากที่ทดลอง:

| Zone | Partition | เหตุผล |
|---|---|---|
| Bronze | `ingest_date` | วันที่ข้อมูลเข้ามา |
| Silver | `year` / `month` / `day` | วันที่ทางธุรกิจ ตรงกับที่ analyst กรอง |
| Quarantine | ไม่ partition | ปริมาณน้อย |

---

## Parquet vs Iceberg

**คนละชั้นกัน ไม่ใช่ทางเลือกแทนกัน:**
- **Parquet** = file format (columnar, compression)
- **Iceberg** = table format (ACID, schema evolution, time travel) ที่ประกอบด้วยไฟล์ Parquet

### Partitioning

ตัวอย่างที่ทีมบันทึก:
```
sales/
  year=2026/
    month=03/
```

**ผลวัดจริง:** กรอง 1 partition เทียบ full scan → เร็วขึ้น 8–9 เท่า scan น้อยลง 94%

กฎที่ทีมบันทึก:
- Partition บน column ที่ใช้ใน `WHERE` จริง — สำรวจ query pattern ก่อน
- ไม่ควร partition ทุก table
- ไม่ควรละเอียดเกิน — *"ควรแบ่งแค่ต่ำสุด month ก็พอ"* เพราะ partition มากเกินสร้าง small file และ metadata overhead

### What Iceberg adds

- ACID transaction
- **Row-level UPDATE / DELETE** — เกี่ยวกับสิทธิขอลบข้อมูลตาม PDPA เพราะ Parquet ธรรมดาลบแถวเดียวไม่ได้โดยไม่เขียนไฟล์ใหม่ทั้งก้อน `[อนุมาน]`
- Schema evolution
- Time travel

### The cost of Iceberg (measured)

| Query | Hive-style partition | Iceberg |
|---|---|---|
| Full scan 433 MB | 14.34 วินาที | 15.58 วินาที |
| กรอง 26 MB | 1.71 วินาที (sd 0.08) | 2.44 วินาที (sd 0.63) |

Iceberg ช้ากว่า 43% บน query เล็ก และแปรปรวนกว่ามาก
สาเหตุน่าจะมาจากการต้องอ่าน snapshot/manifest metadata ก่อน prune ไฟล์ `[อนุมาน]`

**ข้อสรุป:** เลือก Iceberg เพราะความสามารถ ไม่ใช่เพราะเร็วกว่า

---

## PySpark basics

| แนวคิด | ความหมาย |
|---|---|
| Transformation | `withColumn`, `filter`, `select` — สร้างแผน ยังไม่รัน |
| Action | `count`, `show`, `write` — สั่งรันจริง |
| Lazy evaluation | Spark สะสม transformation แล้วรันตอนเจอ action |

Lazy evaluation ทำให้ error โผล่ไกลจากบรรทัดที่เขียนผิด — `withColumn` 10 บรรทัดจะรันตอน `.count()` `[อนุมาน]`

### Functions used often when cleaning

```python
F.trim(col)
F.when(cond, val).otherwise(other)
F.coalesce(a, b, c)
F.initcap(col)
F.try_to_date(col, "yyyy-MM-dd")
F.col(c).cast(DoubleType())
F.concat_ws("; ", *cols)
F.year(col), F.month(col), F.dayofmonth(col)
df.dropDuplicates([cols])
```

### Caveats

- `dropDuplicates(subset)` เลือกตัวที่รอดแบบไม่กำหนด — ถ้าต้องการตัวล่าสุดหรือสมบูรณ์ที่สุด ต้องใช้ window function + `row_number()`
- ระวัง small file ตอนเขียน — DataFrame ที่มี 200 partition เขียน 200 ไฟล์
- built-in function เร็วกว่า Python UDF มาก
- `.cache()` ช่วยเมื่อ DataFrame ถูกใช้หลายครั้ง นอกนั้นเปลือง memory

### Running locally

ต้องมี **Java** เพราะ Spark รันบน JVM
บน **Windows** ต้องมี `winutils.exe` + `hadoop.dll` และตั้ง `HADOOP_HOME` แม้จะเขียนลงดิสก์ในเครื่อง เพราะ Spark ผ่าน Hadoop filesystem layer เสมอ

---

## Glue and PySpark

Glue เพิ่ม `GlueContext`, `DynamicFrame`, การอ่านผ่าน Data Catalog และ `EvaluateDataQuality()` + DQDL

```python
dyf = glueContext.create_dynamic_frame.from_catalog(
    database="com7_datalake", table_name="bronze_sales")
df = dyf.toDF()   # เป็น DataFrame ธรรมดา ใช้ logic เดิมได้
```

---

## Checklist before writing a pipeline

`[อนุมาน]`

- Idempotent ไหม (รันซ้ำแล้วผลเหมือนเดิม)
- Incremental หรือ full reload และคอลัมน์ที่ต้องใช้มีไหม
- แถวเสียไปไหน บันทึกเหตุผลไหม
- เก็บ provenance ไหม (`source_system`, `ingested_at`)
- Partition ตรงกับ query pattern จริงไหม
- Latency ที่ต้องการเท่าไหร่
- รันซ้ำหลังพังกลางทางปลอดภัยไหม

## ข้อกำหนด log ของทุก ETL job (ตกลง 2026-08-27)

ทุก job ที่ ETL ขึ้น AWS **ต้องเก็บ log** ที่ตอบได้ว่า

| ต้องบันทึก | รายละเอียด |
|---|---|
| **ปริมาณต้นทาง** | จำนวน column · จำนวน row · ขนาด |
| **ปริมาณปลายทาง** | ได้ผลเท่ากับต้นทางไหม |
| **เวลา** | เวลาเริ่ม · เวลาเสร็จ |
| **โหมดเขียน** | `append` (เติมเฉพาะที่ยังไม่มี) หรือ `rewrite` (เขียนทับทั้งหมด) |
| **ชื่อตาราง** | ต้นทาง → ปลายทาง |

**Schedule เบื้องต้น: 23:30 น. ทุกวัน**
MIS จะส่งอีเมลระบุผู้รับ log ให้ทีม AWS

### แบ่ง pipeline เป็น 2 scenario

| Scenario | ลักษณะข้อมูล | ผลต่อ pipeline |
|---|---|---|
| A | ต้อง **clean ก่อน** | มีขั้นตอน transform/validate เพิ่ม |
| B | **พร้อมใช้งานเลย** | โหลดตรงได้ |

→ [[2026-08-27 AWS Data Lake]]

---

## เชื่อมกับโน้ตอื่น

[[AWS Services]] · [[SQL & Source Schemas]] · [[Architecture]] · [[Athena Benchmark]] · [[Google Sheet to S3 (Lambda)]] · [[DMS Full Load Validation (Lambda)]] · [[ITEC Item Category Mapping (SQL to Python)]]
