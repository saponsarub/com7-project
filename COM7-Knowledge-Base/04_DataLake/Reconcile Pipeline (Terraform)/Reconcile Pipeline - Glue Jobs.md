# Reconcile Pipeline - Glue Jobs

> อ่าน code ของ 2 Glue job: `assets/glue_reconcile_generic.py` (2,192 บรรทัด) และ `assets/glue_iceberg_maintenance.py` (325 บรรทัด)
> arg / CFG แต่ละตัวมาจากไหน → [[Reconcile Pipeline - Arguments & Variables]]

---

## A. glue_reconcile_generic.py

### แนวคิด (จาก docstring)
- ต้นทางไม่มี CDC / transaction log → **เทียบสถานะสองฝั่งแล้ว MERGE ส่วนต่าง** · ฝั่งต้นทางแค่ `SELECT`
- **อ่านเป็น slice ขนานหลายก้อน** เพราะ WireGuard peer on-prem อยู่หลัง NAT ที่เปลี่ยน UDP port เป็นระยะ → TCP ที่ค้างอยู่ตาย · เคยมี key extract 30 นาทีค้างไม่มีวันจบ · query สั้นหลายก้อนจบทันในช่วงที่ link นิ่ง และ Spark retry เฉพาะก้อนที่พัง
- ขั้นตามสัญญาที่ตกลงกัน: **1.1** นับปลายทาง · **1.2** นับต้นทาง · **1.3** ใส่ส่วนต่าง (INSERT / UPDATE / DELETE) · **1.4** ยืนยัน count ตรง ไม่ตรง = run ล้ม
- หาแถวถูกลบแบบ **scoped** — นับรายกลุ่มก่อน แล้วดึง key เฉพาะกลุ่มที่ไม่ตรง (ใน production: แทนที่จะดึง key 78M แถว เหลือ query เล็กไม่กี่ตัว)

### แผนที่ไฟล์

| บรรทัด | ส่วน | สาระ |
|---|---|---|
| 1–35 | docstring | แนวคิดข้างบน |
| 55–98 | **อ่าน arg** | `getResolvedOptions(["JOB_NAME"])` + `get_arg()` · ตรวจ `REGISTRY_URI` / `TABLE` / `MODE` |
| 100–160 | **registry → CFG** | `load_registry()` · `{**defaults, **entry}` · คำนวณ `PK`, `WM`, `COLUMN_MAP`, `BUSINESS_COLS` |
| 160–185 | ชื่อ/path | `FQ_TABLE = glue_catalog.<db>.<table>` · `WAREHOUSE = s3://<data>/iceberg/` · key ใน `_control/` |
| 187–235 | failure | `record_failure()` / `clear_failure()` |
| 237–260 | **secret → JDBC** | อ่าน Secrets Manager · สร้าง URL + props |
| 270–290 | Spark | Iceberg extension · `glue_catalog` = GlueCatalog + S3FileIO · `job.init` |
| 295–365 | retry | `TRANSIENT_SIGNATURES` · `with_retry()` · `jdbc_query()` |
| 386–470 | อ่านต้นทาง | `jdbc_parallel()` · `rename_to_target()` |
| 473–590 | bootstrap | `create_table_from_source_schema()` · `run_bootstrap()` |
| 592–740 | helpers | watermark · `write_json` · metadata · เงื่อนไข MERGE · ตรวจ schema |
| 741–1185 | **delete audit** | stage → manifest → delete → audit · recover |
| 1185–1265 | utils | `pk_on` · `dedupe_by_pk` · `sql_literal` |
| 1262–1525 | **signature** (deep verify) | canonical string + hash ทั้งสองฝั่ง · `classify_group_drift` |
| 1525–1722 | **repair** | `repair_groups()` |
| 1724–2175 | **`run()`** | ขั้น 1.1–1.4 |
| ท้ายไฟล์ | main | `bootstrap` → `run_bootstrap()` · `reconcile`/`verify` → `run()` · print summary · `clear_failure()` · `job.commit()` |

---

### A1. ตั้งค่าตอน import (ก่อนทำงานจริง)

```python
REGISTRY_URI = get_arg("REGISTRY_URI")            # ต้องเป็น s3://bucket/key ไม่งั้น REGISTRY_URI_REQUIRED
TABLE        = get_arg("TABLE")                   # ว่าง = TABLE_REQUIRED
MODE         = get_arg("MODE", "verify").lower()  # bootstrap | reconcile | verify
CFG, DEFAULTS = load_registry()                   # TABLE_NOT_IN_REGISTRY / TABLE_DISABLED

PK = [COLUMN_MAP[c] for c in PK_SRC]              # ชื่อฝั่งปลายทาง
WM = COLUMN_MAP[WM_SRC] if WM_SRC else None       # ไม่มี watermark = full compare
BUSINESS_COLS        = ทุก target ใน column_map (ลำดับเดิม)
NON_PK_BUSINESS_COLS = BUSINESS_COLS − PK         # ใช้ทั้งนับ update และเงื่อนไข MERGE → ตัวเลขที่รายงานตรงกับที่เขียนจริง
TARGET_METADATA_COLS = [reconciled_at, target_inserted_at, target_updated_at,
                        target_last_operation, target_operation_run_id]   # ของปลายทาง ไม่อยู่ใน column_map
```

secret → JDBC:
```python
EFFECTIVE_SECRET_ID = CFG.get("secret_id") or SECRET_ID      # ตารางระบุ secret เองได้ → onboard ต้นทางที่ 2 ได้โดยไม่ copy job
secret = json.loads(secrets.get_secret_value(SecretId=EFFECTIVE_SECRET_ID)["SecretString"])
JDBC_URL = (f"jdbc:sqlserver://{secret['host']}:{secret['port']};databaseName={secret['database']};"
            "encrypt=false;trustServerCertificate=true;loginTimeout=30;socketTimeout=180000")
JDBC_PROPS = {"user": ..., "password": ..., "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
              "fetchsize": str(FETCH_SIZE)}
```
- `socketTimeout=180000` (3 นาที) **จำเป็น** — ไม่มีแล้ว NAT rebind ทำ driver ค้างรอ socket ตายตลอดไป (เคยเกิดกับ DMS)
- ⚠️ `encrypt=false` hardcode → ค่า `enforce_ssl` ใน tfvars **ไม่มีผลกับ job** `[อนุมาน จาก code]`

`_static_semantic_assertions()` รันตอน import: ตรวจว่า SQL ที่ generate ใช้ `<=>` (null-safe) และ UPDATE ไม่แตะ `target_inserted_at` / PK

---

### A2. จัดการ error — `record_failure` + `with_retry`

```python
def record_failure(failure_class, message) -> RuntimeError:
    # ตัด Java stack frame ("at ...") · ยาวเกิน 1200 ตัวอักษรตัดท้าย (ข้อความไปลง SNS)
    payload = {"failure_class", "retryable": failure_class in ("SOURCE_UNREACHABLE",),
               "table", "run_id", "mode", "message", "failed_at"}
    s3.put_object(Key=f"_control/{TABLE}/last_failure.json", ...)
    return RuntimeError(f"{failure_class}: {message}")       # ผู้เรียก raise ต่อ
```
Step Functions แยกได้แค่ชื่อ error แต่ Glue ส่ง Python exception ทุกตัวเป็น error ชื่อเดียว → **job เขียนประเภทลงไฟล์ให้ SFN อ่าน**

```python
TRANSIENT_SIGNATURES = ("connection to the host", "connect timed out", "connection reset",
    "connection refused", "socket closed", "broken pipe", "the connection is closed",
    "network-related or instance-specific error", "read timed out", "no route to host", ...)

def with_retry(fn, label):
    for attempt in 1..DRIVER_QUERY_ATTEMPTS (6):
        try: return fn()
        except e:
            if not is_transient(e): raise record_failure("SOURCE_QUERY_ERROR", ...)   # SQL ผิด/ไม่มีสิทธิ์ → ไม่ retry
            sleep(min(15 * attempt, 60))
    raise record_failure("SOURCE_UNREACHABLE", ...)   # retryable = true → SFN รอ 15 นาทีแล้วลองใหม่
```
retry ของ Spark ป้องกันแค่งานบน executor · JDBC ที่รันบน driver (นับแถว, หา schema) ไม่มีใครป้อง → ต้องห่อเอง

`jdbc_query(sql)` — query เล็ก (aggregate) · `collect()` **อยู่ใน retry** → หลุดกลาง fetch ก็ retry

---

### A3. `jdbc_parallel` — อ่านต้นทางแบบแบ่ง slice

```python
subquery = f"(SELECT [c1],[c2],... FROM [schema].[table] WHERE {where}) AS s"
if PART_COL_SRC:   # มีคอลัมน์ตัวเลขให้แบ่ง
    bounds = jdbc_query("SELECT COUNT_BIG(*), MIN(col), MAX(col) ... WHERE {where}")
    row_count == 0        → คืน frame ว่างที่มี schema (ใช้ anti-join ต่อได้)
    lo/hi เป็น NULL หมด  → อ่านก้อนเดียว (กันแถวหาย)
    ปกติ → spark.read.jdbc(partitionColumn, lowerBound=lo, upperBound=hi, numPartitions=READ_PARTITIONS)
else:              # ไม่มี → hash ของ PK ตัวแรก
    predicates = [f"ABS(CHECKSUM([pk0])) % N = {i}" for i in range(N)]   # ทุกแถวอยู่ slice เดียวพอดี
```

---

### A4. `MODE=bootstrap`

```python
create_table_from_source_schema():
    probe = SELECT * FROM src WHERE 1 = 0          # เอา type จาก JDBC driver (ไม่เดา decimal/timestamp)
    CREATE TABLE IF NOT EXISTS glue_catalog.<db>.<t> (<คอลัมน์ธุรกิจ>, <metadata 5 ตัว>)
    USING iceberg PARTITIONED BY (<target_partition_spec>)
    TBLPROPERTIES ('format-version'='2', 'write.delete/update/merge.mode'='merge-on-read',
                   'write.parquet.compression-codec'='zstd')
run_bootstrap():
    ตาราง มีข้อมูลแล้ว           → BOOTSTRAP_REFUSED
    ต้นทาง 0 แถว                 → BOOTSTRAP_EMPTY_SOURCE
    อ่านทั้งตาราง → append (+ metadata INSERT)
    distinct PK ≠ loaded         → PK_NOT_UNIQUE_AFTER_BOOTSTRAP
    loaded ≠ source_count        → BOOTSTRAP_ROW_MISMATCH (มีคนเขียนระหว่างโหลด)
    เขียน watermark = max(UpdatedAt) ของต้นทาง · _SUMMARY.json status BOOTSTRAP_COMPLETE
```
**merge-on-read** = MERGE เขียนเร็ว (ไฟล์ใหม่ + delete file เล็ก) แต่ภาระไปตกฝั่งอ่าน → ต้องมี maintenance

---

### A5. `run()` — reconcile / verify ทีละขั้น

```
0    ตารางต้องมี (ไม่มี = TABLE_MISSING) · validate_target_metadata_schema()
     recover_pending_delete_audits()   ← เคลียร์ delete ที่ค้างจากรอบก่อน ก่อนตัดสินใจอะไรใหม่
     dry_run = (MODE == "verify") · watermark = read _control/<t>/watermark.json
1.1  target_before = COUNT(*) ปลายทาง
1.2  SELECT COUNT_BIG(*), MAX(UpdatedAt) FROM ต้นทาง
1.3  slice:
       ไม่มี watermark column → WHERE 1 = 1 (ทั้งตาราง)
       มี watermark แล้ว       → WHERE UpdatedAt >= '<watermark.date() − lookback วัน>'
       ยังไม่มี (ครั้งแรก)      → WHERE UpdatedAt >= '<max ต้นทาง>'
     อ่าน slice → rename → dedupe ตาม PK
       แถว ≠ distinct PK → PK_NOT_UNIQUE_IN_SOURCE (หยุดก่อนแตะปลายทาง)
     จำแนกก่อน MERGE (MERGE ไม่คืนตัวเลข):
       inserted = key ไม่มีในปลายทาง
       updated  = key มี AND WM ใหม่กว่า (gte: >=, gt: >) AND ค่าธุรกิจต่างจริง (null-safe)
     ถ้าไม่ verify และมีอะไรต้องทำ:
       MERGE INTO t USING incoming_batch s ON <pk>
         WHEN MATCHED AND s.WM >= t.WM AND NOT (s.c1 <=> t.c1 AND ...) THEN UPDATE SET ...
         WHEN NOT MATCHED THEN INSERT (...)
1.3.3 หาแถวถูกลบ (ข้ามถ้า DEEP_VERIFY+DEEP_REPAIR เพราะ 1.3.4 ทำครอบแล้ว):
       count หลัง upsert = source → ไม่ต้องหา (เว้น FULL_KEYSET)
       ไม่ตรง → COUNT ต่อ drift_group_column ทั้งสองฝั่ง → full outer join → กลุ่มที่ไม่ตรง
              → ดึงเฉพาะ PK ของกลุ่มนั้นจากต้นทาง → left_anti กับปลายทางในกลุ่มนั้น = orphans
              → (ไม่ verify) stage → MERGE ... WHEN MATCHED THEN DELETE → audit
1.3.4 ถ้า DEEP_VERIFY → signature รายกลุ่ม (A6) → กลุ่มเกิน MAX_REPAIR_GROUPS = DRIFT_TOO_WIDE
       DEEP_REPAIR → repair_groups() · ไม่งั้นรายงาน REPAIR_DISABLED
1.4  gate: drift = COUNT ปลายทาง − source_count
       ≠ 0                      → status COUNT_MISMATCH (+ วิธีแก้ตามทิศ: ขาด → deep repair · เกิน → FULL_KEYSET)
       กลุ่มยัง count ไม่ตรง    → GROUP_COUNT_MISMATCH (ขาดกลุ่มหนึ่งเกินอีกกลุ่ม รวมแล้วเท่ากัน)
       ค่ายังเพี้ยน             → VALUE_DRIFT
       ผ่านหมด                  → RECONCILED + เลื่อน watermark = max ต้นทาง (ไม่ verify เท่านั้น)
     เขียน _SUMMARY.json ทุกกรณี
```

**จุดสำคัญ**
- **watermark เลื่อนเฉพาะเมื่อผ่านทุกด่าน** — ล้ม = รอบหน้าอ่าน slice เดิม ไม่มีข้อมูลหลุด
- lookback ปัดเป็น**ระดับวัน** + `>=` เพราะ watermark column ละเอียดแค่วันในข้อมูลจริง และกันแถว backdate
- **NULL ในคอลัมน์กลุ่ม**: ใช้ sentinel `"\u0000NULL"` เทียบ เพราะ `NULL = NULL` เป็นเท็จ · ฝั่ง SQL แยก `IS NULL` · ฝั่ง Spark แยก `isNull()` (`isin([None])` กรองทิ้งหมด)
- ค่า group อาจเป็น string → `sql_literal()` ใส่ `N'...'` + escape
- `verify` ทำทุกขั้นเหมือนจริงแต่ไม่เขียน · ถ้ามี pending delete ค้าง verify จะล้ม (`PENDING_DELETE_AUDIT_EXISTS`) เพราะไม่ยอมแก้ข้อมูล

**metadata ที่ปลายทาง**
| คอลัมน์ | INSERT | UPDATE |
|---|---|---|
| `reconciled_at` | เวลาทำ | เวลาทำ |
| `target_inserted_at` | เวลาทำ | **ไม่แตะ** |
| `target_updated_at` | NULL | เวลาทำ |
| `target_last_operation` | `INSERT` | `UPDATE` |
| `target_operation_run_id` | RUN_ID | RUN_ID |
ตาราง schema ไม่ตรงนี้ → `TARGET_SCHEMA_MIGRATION_REQUIRED` (job ไม่แก้ schema ให้เอง) · ยอมรับทั้ง `timestamp` และ `timestamp_ntz` (ตารางที่สร้างจาก Athena)

---

### A6. Deep verify — signature รายกลุ่ม

เป้าหมาย: หาแถวที่ค่าเปลี่ยนแต่ watermark ไม่ขยับ **โดยไม่ดึงทุกแถวข้ามเน็ต** → ให้ SQL Server กับ Spark คำนวณ hash แบบเดียวกันเป๊ะแล้วเทียบแค่ผลรวมรายกลุ่ม

`signature_spec()` — เลือกคอลัมน์จาก schema ปลายทาง:
| type | kind | ใช้ใน hash | ใช้ SUM |
|---|---|---|---|
| int, bigint, smallint, ... | `int` | ✓ | ✓ |
| decimal | `dec` | ✓ | ✓ |
| string | `str` | ✓ | |
| date / timestamp / boolean | `date` / `ts` / `bool` | ✓ | |
| float, double, binary, อื่น ๆ | — | **ตัดทิ้ง** (render ข้าม engine ไม่ตรง) | |

ฝั่ง SQL Server (query เดียว — ตารางต้นทางเป็น heap ไม่มี index แบ่ง slice = scan ซ้ำ):
```sql
SELECT grp, COUNT_BIG(*) AS row_count, SUM(CAST([Qty] AS bigint)) AS sum_qty, SUM([Amount]) AS sum_amount,
       SUM((CAST(h4 AS bigint) & CAST(4294967295 AS bigint))) AS hash_sum
FROM (SELECT CONVERT(char(7), OrderDatetime, 126) AS grp, [Qty], [Amount],
             CAST(SUBSTRING(HASHBYTES('MD5', ISNULL(CAST([OrderId] AS nvarchar(20)),N'~') + N'|' + ...), 1, 4) AS int) AS h4
      FROM [workshop].[orders_reconcile_lab] WHERE 1 = 1) x
GROUP BY grp
```
ฝั่ง Spark:
```python
digest = F.md5(F.encode(F.concat_ws("|", *parts), "UTF-16LE"))
h4     = F.conv(F.substring(digest, 1, 8), 16, 10).cast("long")    # 32 bit unsigned ใน long
groupBy(F.expr("date_format(order_datetime,'yyyy-MM')")).agg(count, sum(...), sum(h4))
```
**กับดัก 4 ข้อที่ code บันทึกไว้**
1. `CONVERT(..., 126)` **ตัดเศษวินาทีทิ้งถ้าเป็น 0** → ประกอบ `.mmm` เอง ฝั่ง Spark `yyyy-MM-dd'T'HH:mm:ss.SSS`
2. `HASHBYTES` ของ nvarchar hash **UTF-16LE** → Spark ต้อง encode UTF-16LE (ไม่งั้นแถวที่มีภาษาไทยไม่ตรงทุกแถว)
3. ตัวเลขเดียวกันมาเป็น Python type ต่างกัน (Decimal precision ต่างกัน) → `sig_norm()` แปลงเป็นข้อความก่อนเทียบ
4. `4294967295` ใน SQL Server ถูกอ่านเป็น numeric → `&` กับ bigint ไม่ได้ → ต้อง `CAST(... AS bigint)`

NULL ทุกชนิด render เป็น `~` · boolean บังคับเป็น 0/1 ทั้งสองฝั่ง · sum ไม่ล้น (78M × 2³² ≈ 3.35e17 < 9.22e18)

`classify_group_drift()` แยกผล:
| verdict | ความหมาย | แก้ด้วย |
|---|---|---|
| `MISSING_ON_ONE_SIDE` / `COUNT_DIFF` → `count_drift_groups` | แถวขาด/เกิน | ดึงทั้งแถวมาซ่อม |
| `VALUE_DIFF` → `value_drift_groups` | count ตรง แต่ sum/hash ไม่ตรง | เขียนแถวที่ต่างทับ |

`signature_group` (registry) ใช้ expression เป็นกลุ่มได้ — fact table ใช้เดือน (ตรงกับ partition `months(...)`) → ได้ไม่กี่สิบกลุ่ม · dimension ใช้คอลัมน์ตรง ๆ

---

### A7. `repair_groups()` — ซ่อมรายกลุ่ม

```
รวมกลุ่ม value + count (ไม่ซ้ำ) → ดึง "ทั้งแถว" ของกลุ่มเหล่านั้นจากต้นทาง (jdbc_parallel)
src_canon = แถวต้นทาง + canonical string
to_write  = แถวที่ไม่มีในปลายทาง หรือ canonical ต่าง                      → INSERT / UPDATE
orphans   = แถวปลายทางในกลุ่มนั้นที่ไม่มีในต้นทาง                         → DELETE
ไม่มีอะไรต้องทำ:
    มีแต่ value drift  → SIGNATURE_RENDERING_MISMATCH (ตัวตรวจผิด ไม่ใช่ข้อมูล)
    มี count drift ด้วย → NOTHING_TO_REPAIR_SOURCE_MOVED (ต้นทางเปลี่ยนระหว่างทาง ให้ gate ตัดสิน)
ไม่ verify:
    stage orphans (ก่อนแตะตาราง) → MERGE repair_batch (UPDATE ทุกคอลัมน์ / INSERT) → MERGE ... DELETE → audit
ตรวจซ้ำ: เทียบแถวที่เพิ่งดึงกับปลายทางหลังเขียน → residual ต้องเป็น 0
```
- MERGE ตรงนี้ **ไม่มี watermark guard** — drift เกิดเพราะ watermark ไม่ขยับ ถ้าใส่ guard จะข้ามแถวที่ต้องแก้พอดี
- เขียน**เฉพาะแถวที่ต่าง** ไม่ re-merge ทั้งเดือน (กัน delete file บาน)
- 1.3.3 ดึงแค่ key → **ลบได้แต่สร้างแถวที่หายคืนไม่ได้** · repair ดึงทั้งแถว → แก้ได้ทั้ง 3 แบบ → เหตุผลที่รอบ deep สำคัญ

---

### A8. Delete audit — ลบแบบมีหลักฐาน และกู้ได้ถ้าตายกลางทาง

ตาราง `glue_catalog.<db>.reconcile_delete_audit` (สร้างเมื่อจะลบครั้งแรก):
`event_id · target_table · source_table · operation · deleted_at · run_id · delete_path · primary_key_json · row_before_json · recorded_at` · `PARTITIONED BY (days(deleted_at))` → **query ต้องกรอง `deleted_at`**

ลำดับ (ทั้ง `scoped_orphan_delete` และ `deep_repair_delete`):
```
token = sha256(run_id + "\x1f" + delete_path)
1. stage_delete_rows          แถวเต็ม → parquet _control/<t>/delete_staging/<token>/ · อ่านกลับนับต้องเท่า
2. persist_pending_delete_manifest   _control/<t>/pending_deletes/<token>.json  state=STAGED_BEFORE_DELETE
3. MERGE INTO t USING keys ON pk WHEN MATCHED THEN DELETE
4. complete_committed_delete_audit   append audit (row_before_json) → ลบ manifest + staging
```
ตายระหว่าง 2–4 → รอบหน้า `recover_pending_delete_audits()` (ก่อนอ่านต้นทาง) ดูว่าแถวใน staging ยังอยู่ในตารางไหม → เขียน audit ให้ครบ · พังขั้นไหนก่อนลบ = ยังไม่ลบ (`DELETE_SNAPSHOT_STAGING_FAILED`, `PENDING_DELETE_MANIFEST_FAILED`, `DELETE_AUDIT_SETUP_FAILED`)

---

### A9. failure_class ทั้งหมด

| class | retryable | เกิดเมื่อ |
|---|---|---|
| `SOURCE_UNREACHABLE` | **✓** | JDBC transport พัง 6 ครั้ง |
| `SOURCE_QUERY_ERROR` | | SQL ถูกปฏิเสธ (ไม่ใช่ปัญหาเน็ต) |
| `TABLE_MISSING` | | ยังไม่ bootstrap |
| `TARGET_SCHEMA_MIGRATION_REQUIRED` | | metadata column ไม่ครบ/type ผิด |
| `PK_NOT_UNIQUE_IN_SOURCE` | | PK ใน registry ไม่ unique จริง |
| `COUNT_MISMATCH` | | gate 1.4 |
| `GROUP_COUNT_MISMATCH` | | รวมเท่ากันแต่บางกลุ่มไม่ตรง |
| `VALUE_DRIFT` | | ค่าไม่ตรง (deep) |
| `SIGNATURE_RENDERING_MISMATCH` | | ตัวตรวจเอง render ไม่ตรง |
| `DRIFT_TOO_WIDE` | | กลุ่มเพี้ยน > `MAX_REPAIR_GROUPS` |
| `PENDING_DELETE_AUDIT_EXISTS` / `..._RECOVERY_FAILED` | | delete ค้างจากรอบก่อน |
| `DELETE_*_FAILED` / `PENDING_DELETE_MANIFEST_FAILED` | | ขั้นเตรียมลบพัง (ยังไม่ได้ลบ) |

ไม่ได้ผ่าน `record_failure` (ไม่มีไฟล์ → SFN แจ้ง "no classification"): `REGISTRY_URI_REQUIRED` · `TABLE_REQUIRED` · `INVALID_MODE` · `TABLE_NOT_IN_REGISTRY` · `TABLE_DISABLED` · `SECRET_ID_REQUIRED` · error ของ bootstrap · อะไรก็ตามที่ตายก่อนสร้าง s3 client

---

## B. glue_iceberg_maintenance.py

ทำไมต้องมี: ตาราง merge-on-read · ทุก MERGE ทิ้ง delete file + ไฟล์เล็ก · แถวที่ถูกลบยังอยู่จริงในไฟล์แค่ถูก "บัง" → ปล่อยไว้ query ช้าลงเรื่อย ๆ ทั้งที่จำนวนแถวเท่าเดิม

```python
TABLES = [{**DEFAULTS, **t} for t in registry["tables"] + registry["maintenance_only_tables"]
          if t.enabled and (not ONLY_TABLE or t.name == ONLY_TABLE)]
for cfg in TABLES:
    before = profile(fq)
    CALL glue_catalog.system.rewrite_data_files(table, options => map(
        'min-input-files', MIN_INPUT_FILES, 'delete-file-threshold', '1',   # ไฟล์ที่มี delete ใด ๆ = ต้อง rewrite
        'target-file-size-bytes', TARGET_FILE_MB*1MB, 'max-concurrent-file-group-rewrites', '8',
        'partial-progress.enabled', 'true', 'partial-progress.max-commits', '10'))
    CALL glue_catalog.system.rewrite_position_delete_files(table, options => map('rewrite-all', REWRITE_ALL_DELETES))
        # rewrite-all=true ทิ้ง delete file ที่ถูก apply ไปแล้วแต่ยังค้างใน manifest (dangling)
    CALL glue_catalog.system.rewrite_manifests(table)
    CALL glue_catalog.system.expire_snapshots(table, older_than = now − snapshot_age_days, retain_last)
    if ORPHAN_CLEANUP: CALL glue_catalog.system.remove_orphan_files(older_than = now − ORPHAN_AGE_DAYS)
    after = profile(fq)
    live_rows เปลี่ยน → MAINTENANCE_CHANGED_ROW_COUNT (maintenance ห้ามเปลี่ยนข้อมูล)
```
- **ลำดับมีผล**: expire หลัง rewrite (ปล่อยไฟล์ที่ rewrite ทิ้ง) · orphan สุดท้าย (ขั้นเดียวที่ลบไฟล์จริง)
- `call()` จับ error ทีละขั้น — procedure ไหนไม่มีใน build นี้ ไม่ทำให้ขั้นอื่นหยุด · `DRY_RUN` = print SQL ไม่รัน
- `profile()`: `data_files`, `physical_records`, `live_rows`, `shadowed_rows` (มีจริงแต่มองไม่เห็น), `delete_files`, `dangling_delete_records`, `snapshots` · กรอง `content = 0` เพราะ `.files` รวม delete file ด้วย
- `rewritten_data_files_count = 0` **มักถูกต้อง** — partition รายเดือนที่มีไฟล์เดียวไม่ถึง `min-input-files=2` · อย่าลดเป็น 1 เพื่อให้ "มีงาน" (จะ rewrite ทุก partition ทุกคืน)
- `remove_orphan_files` ปิดไว้ — ไฟล์ของ job ที่กำลัง commit ดูเหมือน orphan · เปิดต้อง ≥ 3 วัน
- ตาราง audit เก็บ snapshot นานกว่า (20 ตัว / 30 วัน) — snapshot คือทางย้อนกลับเดียวถ้ามีอะไรเขียนทับ ledger ผิด

---

## เชื่อมกับโน้ตอื่น

[[Reconcile Pipeline - Overview]] · [[Reconcile Pipeline - Arguments & Variables]] · [[Reconcile Pipeline - Orchestration & Alerts]] · [[ETL & Spark]] · [[Glue Connectivity]]
