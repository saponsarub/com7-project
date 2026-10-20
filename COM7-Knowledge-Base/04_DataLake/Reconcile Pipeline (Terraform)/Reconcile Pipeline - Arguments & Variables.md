# Reconcile Pipeline - Arguments & Variables

> ทุกค่าที่ pipeline ใช้ **มาจากไหน · ผ่านอะไร · ไปจบที่ไหน · ถูกเก็บไว้ที่ไหน**
> อ่านคู่กับ [[Reconcile Pipeline - Overview]] · code อ้างอิงจาก bundle v1.0.0

---

## 1. ภาพเดียวจบ — ค่าไหลผ่าน 6 ชั้น

```
 [ชั้น 0] CloudFormation outputs ──(คนคัดลอกเอง)──┐
                                                  ▼
 [ชั้น 1] my-pipeline.tfvars            ← คนเขียน (ไฟล์เดียวที่ต้องแก้)
                │  terraform plan/apply -var-file=my-pipeline.tfvars
                ▼
 [ชั้น 2] variables.tf                  ← ใส่ default + validation (ผิด = plan ล้ม)
                ▼
 [ชั้น 3] locals.tf / registry.tf       ← คำนวณชื่อ, path, JSON, input ของ schedule
          + data sources                ← account_id (จาก credential), AZ ของ subnet, ARN ของ secret
                ▼
 [ชั้น 4] resource ใน AWS (+ สำเนาใน terraform.tfstate)
          ├─ Glue job DefaultArguments  ──────────┐
          ├─ S3 artifacts/reconcile/reconcile_tables.json (registry)
          ├─ Scheduler target input (JSON)        │
          ├─ Step Functions definition (templatefile)
          └─ Secrets Manager (ชื่อเท่านั้น ค่าอยู่ข้างใน)
                ▼                                  │
 [ชั้น 5] ตอนรัน                                    │
          Scheduler ─input─► Step Functions ─Arguments─► Glue job run ◄┘ (default + run args)
          terraform apply ─env─► bootstrap_glue.py ─Arguments─► Glue job run
                ▼
 [ชั้น 6] ใน Glue script
          sys.argv ─get_arg()─► ตัวแปร global (MODE, TABLE, ...)
          REGISTRY_URI ─► S3 ─► CFG (ค่าต่อตาราง)
          SECRET_ID ─► Secrets Manager ─► host/port/db/user/password
          _control/<table>/watermark.json ─► จุดเริ่มอ่านรอบนี้
```

**กฎสั้น ๆ**
- arg ที่ต่างกัน**ทุกรอบ** (`TABLE`, `MODE`, `RUN_ID`, `DEEP_*`) → มาจาก **Step Functions / bootstrap** ตอนรัน
- arg ที่**คงที่ทั้ง job** (`REGISTRY_URI`, `SECRET_ID`, ค่า maintenance) → มาจาก **Glue job DefaultArguments** ที่ Terraform ตั้ง
- ค่าที่**ต่างกันต่อตาราง** (PK, watermark, column map, partition) → **ไม่ผ่าน argv** อยู่ใน **registry JSON บน S3**
- **ความลับ** → **ไม่ผ่าน argv / tfvars / registry** อยู่ใน **Secrets Manager** อย่างเดียว
- **สถานะที่จำข้ามรอบ** (watermark, failure, pending delete) → **S3 `_control/`**

---

## 2. ชั้น 1–2: Terraform variables มาจากไหน

### ลำดับความสำคัญ (Terraform มาตรฐาน — ตัวหลังชนะ)
1. `default` ใน `variables.tf`
2. env `TF_VAR_<name>`
3. `terraform.tfvars` / `*.auto.tfvars` (โหลดอัตโนมัติ)
4. `-var-file=...` / `-var ...` บน command line (ตามลำดับที่พิมพ์)

workshop ใช้ `-var-file=my-pipeline.tfvars` อย่างเดียว · ค่าที่ไม่ได้ใส่ → ใช้ default ใน `variables.tf` (ส่วนใหญ่เป็น `optional(type, default)` ใน object)

### ตาราง: ตัวแปรทุกตัว — ใส่ที่ไหน · default · workshop ใช้อะไร · ไปจบที่ไหน

| ตัวแปร (tfvars)                                                                 | default                                                                | workshop                                                    | ไปจบที่                                                       |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------- |
| `project`                                                                       | **ต้องใส่** · regex `^[a-z][a-z0-9-]{2,40}$`                           | `reconcile-workshop`                                        | prefix ชื่อทุกอย่าง: bucket, role, job, SFN, SNS, schedule    |
| `aws_region`                                                                    | **ต้องใส่**                                                            | `us-east-1`                                                 | provider · ARN · `AWS_REGION` ของ bootstrap                   |
| `tags`                                                                          | `{}`                                                                   | Project/Environment/ManagedBy/Owner                         | `default_tags` ทุก resource                                   |
| `network.vpc_id`                                                                | **ต้องใส่**                                                            | default VPC                                                 | subnet, SG, endpoint                                          |
| `network.create_private_subnet`                                                 | `false`                                                                | `true`                                                      | สร้าง subnet + route table                                    |
| `network.private_subnet_cidr` / `availability_zone`                             | —                                                                      | `/24` ว่าง · AZ เดียวกับต้นทาง                              | `aws_subnet.glue`                                             |
| `network.subnet_id`                                                             | —                                                                      | (ไม่ใช้ — ใช้คู่กับ managed ไม่ได้)                         | existing mode                                                 |
| `network.create_nat_gateway` + `nat_public_subnet_id`                           | `false`                                                                | `true` + public subnet                                      | EIP + NAT + route `0.0.0.0/0`                                 |
| `network.create_s3_vpc_endpoint`                                                | `false`                                                                | `true`                                                      | gateway endpoint                                              |
| `network.security_group_ids`                                                    | null → สร้าง SG ใหม่                                                   | (ไม่ใส่)                                                    | Glue connection                                               |
| `source_database.host` / `port` / `database`                                    | port `1433`                                                            | **จาก CFN output** `PrivateIp` / `SQLPort` / `DatabaseName` | Glue connection URL · placeholder secret                      |
| `source_database.secret_name`                                                   | `<project>/mssql-source`                                               | **จาก CFN output** `PipelineSecretName`                     | `--SECRET_ID` ของ job · IAM policy                            |
| `source_database.manage_secret`                                                 | `true`                                                                 | `false`                                                     | true = สร้าง placeholder · false = data source อ่านอย่างเดียว |
| `source_database.source_security_group_id`                                      | null                                                                   | **จาก CFN output** `SourceSecurityGroupId`                  | ingress rule 1433 จาก Glue SG                                 |
| `source_database.enforce_ssl`                                                   | `false`                                                                | `false`                                                     | Glue Connection `JDBC_ENFORCE_SSL` เท่านั้น (ดูข้อ 8)         |
| `buckets.data_bucket_name` / `artifacts_bucket_name`                            | `<project>-data-<account>` / `-artifacts-`                             | ใส่ชื่อเอง                                                  | S3 · registry `defaults.target_bucket`                        |
| `buckets.force_destroy`                                                         | `false`                                                                | `false`                                                     | destroy bucket ที่มีของไม่ได้                                 |
| `glue_database_name`                                                            | project แทน `-` ด้วย `_`                                               | `reconcile_workshop`                                        | Glue DB · registry `defaults.glue_db`                         |
| `glue.version` / `worker_type` / `number_of_workers`                            | `5.0` / `G.2X` / `10`                                                  | เท่า default                                                | ทั้ง 2 job                                                    |
| `glue.timeout_minutes` / `maintenance_timeout_minutes`                          | `180` / `240`                                                          | เท่า default                                                | job timeout                                                   |
| `glue.jdbc_driver_jar.local_path` **xor** `s3_uri`                              | ต้องเลือก 1                                                            | `assets/jars/mssql-jdbc-12.8.1.jre11.jar`                   | upload → `--extra-jars`                                       |
| `registry_defaults.read_partitions`                                             | `64`                                                                   | `4`                                                         | registry `defaults`                                           |
| `registry_defaults.jdbc_fetch_size`                                             | `20000`                                                                | `20000`                                                     | registry `defaults`                                           |
| `registry_defaults.merge_guard`                                                 | `gte`                                                                  | `gte`                                                       | registry `defaults`                                           |
| `registry_defaults.watermark_lookback_days`                                     | `2`                                                                    | `2`                                                         | registry `defaults`                                           |
| `maintenance.*`                                                                 | ดูข้อ 4                                                                | เท่า default                                                | maintenance job DefaultArguments / registry ledger            |
| `bootstrap.enabled` / `poll_seconds` / `timeout_minutes`                        | `true` / `15` / `180`                                                  | `true` / `15` / `30`                                        | `terraform_data.bootstrap` env                                |
| `schedules.enabled`                                                             | `false`                                                                | `false`                                                     | schedule `state` ENABLED/DISABLED                             |
| `schedules.timezone` / `nightly_cron` / `deep_cron`                             | `Asia/Bangkok` / `cron(30 23 ? * MON-SAT *)` / `cron(30 23 ? * SUN *)` | เท่า default                                                | Scheduler                                                     |
| `schedules.max_link_retries` / `link_retry_wait_seconds`                        | `4` / `900`                                                            | เท่า default                                                | **input ของ SFN** (ข้อ 5)                                     |
| `alert_emails`                                                                  | `[]`                                                                   | อีเมลทีม                                                    | SNS subscription                                              |
| `no_success_alarm_hours`                                                        | `26`                                                                   | `26`                                                        | alarm `no-success-26h`                                        |
| `athena.create` / `workgroup_name` / `output_location` / `bytes_scanned_cutoff` | `false` / `<project>-readonly` / — / 10 GiB                            | `true` + ตั้งเอง                                            | Athena workgroup                                              |
| `tables[]`                                                                      | **ต้องใส่ ≥ 1**                                                        | 1 ตาราง `fact_orders`                                       | registry `tables` · input ของ schedule · `--TABLE` default    |

### ค่าที่**ไม่ได้มาจาก tfvars** (Terraform หาเอง)
| ค่า | มาจาก | ใช้ทำ |
|---|---|---|
| `local.account_id` | `data.aws_caller_identity` ← credential ที่รัน (`AWS_PROFILE`) | ชื่อ bucket default · ARN ใน IAM |
| `availability_zone` ของ Glue connection | `data.aws_subnet.glue` | Glue connection |
| `local.source_secret_arn` | data source หรือ resource secret | IAM `GetSecretValue` เฉพาะ ARN นี้ |
| `local.jdbc_url` | `format("jdbc:sqlserver://%s:%d;databaseName=%s", host, port, database)` | Glue connection เท่านั้น |
| path ของ script / jar | `abspath("${path.module}/...")` | รันจาก directory ไหนก็หาเจอ |

---

## 3. Glue reconcile job — sys.argv ทุกตัว

ไฟล์ `assets/glue_reconcile_generic.py` บรรทัด 55–98, 295

### Glue สร้าง sys.argv ยังไง
- Glue รวม **DefaultArguments ของ job** (ตั้งใน `glue.tf`) กับ **Arguments ของ run นั้น** (จาก `start-job-run`) — **key เดียวกัน ค่าของ run ชนะ**
- ส่งเข้า script เป็นคู่ `--KEY value` ใน `sys.argv` พร้อม arg ระบบที่ Glue ใส่เอง เช่น `--JOB_NAME`, `--JOB_RUN_ID`, `--TempDir` `[อนุมาน: ตามพฤติกรรมมาตรฐานของ Glue — ไม่ได้ print sys.argv ดูจริง]`
- ค่าทุกตัวเป็น **string** → script แปลงเอง (`.lower() == "true"`, `int(...)`)

### script อ่านยังไง
```python
args = getResolvedOptions(sys.argv, ["JOB_NAME"])   # บังคับแค่ JOB_NAME (ไม่มี = error)

def get_arg(name, default=""):                       # อ่านเองแบบ optional
    flag = "--" + name
    if flag in sys.argv:                             # เอาตัวแรกที่เจอ
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default                                   # ไม่มี = ใช้ default ใน code
```
เหตุที่ไม่ใช้ `getResolvedOptions` กับทุกตัว — มันบังคับว่าต้องมี ถ้าไม่ส่งจะ error · `get_arg` ทำให้ arg ส่วนใหญ่ **ไม่ส่งก็ได้**

### ตาราง arg

| arg | default ใน code | ใครส่ง · ค่าอะไร | ต้นทางของค่า | ใช้ทำอะไร |
|---|---|---|---|---|
| `--JOB_NAME` | (บังคับ) | Glue ใส่เอง | ชื่อ job `<project>-generic` | `job.init()` |
| `--REGISTRY_URI` | `""` → **error** `REGISTRY_URI_REQUIRED` | DefaultArguments | `local.registry_uri` = `s3://<artifacts>/reconcile/reconcile_tables.json` | โหลด CFG |
| `--TABLE` | `""` → **error** `TABLE_REQUIRED` | DefaultArguments = ตารางแรกที่ enabled · **SFN ส่งทับทุกรอบ** `$.table` · bootstrap ส่งทับ | `var.tables[*].name` | เลือก entry ใน registry |
| `--MODE` | `verify` | DefaultArguments = **`verify`** · SFN = `$.mode` (`reconcile`) · bootstrap = `bootstrap` | schedule input `mode = "reconcile"` (hardcode ใน locals) | `bootstrap` / `reconcile` / `verify` (dry run) |
| `--SECRET_ID` | `""` | DefaultArguments | `local.source_secret_name` ← `source_database.secret_name` | ชื่อ secret · **registry `secret_id` ต่อตารางชนะ arg นี้** |
| `--RUN_ID` | เวลา UTC `YYYYMMDDTHHMMSSZ` | SFN: `<executionName>-<table>-<attempt>` · bootstrap: `terraform-bootstrap-<table>-<epoch>` | — | ชื่อโฟลเดอร์ `_SUMMARY.json` · ฟิลด์ audit · metadata `target_operation_run_id` |
| `--DEEP_VERIFY` | `false` | SFN `$.deepVerify` | schedule input (nightly false · deep true) | เปิดการเทียบ signature |
| `--DEEP_REPAIR` | `false` | SFN `$.deepRepair` | schedule input | ให้ซ่อมจริงหลังเจอ drift |
| `--ENABLE_DELETES` | `true` | DefaultArguments `"true"` | hardcode ใน `glue.tf` | เปิดการหาแถวถูกลบ |
| `--STRICT_COUNT_CHECK` | `true` | DefaultArguments `"true"` | hardcode ใน `glue.tf` | count ไม่ตรง = job ล้ม (ไม่ใช่แค่ status) |
| `--FULL_KEYSET` | `false` | **ไม่มีใครส่ง** — สั่งมือเท่านั้น | — | บังคับหาแถวถูกลบแม้ count ตรง |
| `--MAX_REPAIR_GROUPS` | `10` | **ไม่มีใครส่ง** | — | drift เกินกี่กลุ่ม = `DRIFT_TOO_WIDE` |
| `--DRIVER_QUERY_ATTEMPTS` | `6` | **ไม่มีใครส่ง** · registry `driver_query_attempts` ชนะ | `tables[].driver_query_attempts` | retry JDBC ฝั่ง driver |
| `--extra-jars` | — | DefaultArguments | `local.jdbc_driver_uri` | โหลด JDBC driver (Glue ใช้ ไม่ใช่ script) |
| `--datalake-formats=iceberg` · `--enable-glue-datacatalog` · `--TempDir` · `--spark-event-logs-path` · `--enable-metrics/spark-ui/continuous-cloudwatch-log` | — | DefaultArguments (`common_job_arguments`) | hardcode + bucket | ตั้งค่า Glue runtime (script ไม่อ่าน) |

**สั่งรันมือพร้อม override** (ตัวอย่าง — verify แบบ deep ไม่เขียนข้อมูล):
```bash
aws glue start-job-run --job-name <project>-generic \
  --arguments '{"--TABLE":"fact_orders","--MODE":"verify","--DEEP_VERIFY":"true"}'
```

---

## 4. Glue maintenance job — sys.argv

ไฟล์ `assets/glue_iceberg_maintenance.py` บรรทัด 45–72

| arg | default ใน code | ใครส่ง | ต้นทาง (tfvars) |
|---|---|---|---|
| `--REGISTRY_URI` | **error** ถ้าไม่มี | DefaultArguments | `local.registry_uri` |
| `--TABLE` | `""` = ทุกตาราง | ไม่มีใครส่ง (สั่งมือได้) | — |
| `--RETAIN_SNAPSHOTS` | `5` | DefaultArguments | `maintenance.retain_snapshots` |
| `--SNAPSHOT_AGE_DAYS` | `3` | DefaultArguments | `maintenance.snapshot_age_days` |
| `--TARGET_FILE_MB` | `256` | DefaultArguments | `maintenance.target_file_mb` |
| `--MIN_INPUT_FILES` | `2` | DefaultArguments | `maintenance.min_input_files` |
| `--REWRITE_ALL_DELETES` | `true` | DefaultArguments | `maintenance.rewrite_all_deletes` |
| `--ORPHAN_CLEANUP` | `false` | DefaultArguments | `maintenance.orphan_cleanup` |
| `--ORPHAN_AGE_DAYS` | `7` (ต่ำกว่า 3 = error) | DefaultArguments | `maintenance.orphan_age_days` |
| `--DRY_RUN` | `false` | ไม่มีใครส่ง | — |
| `--RUN_ID` | เวลา UTC | SFN `<executionName>-maint` | — |

**ค่าต่อตารางชนะ arg** — `retain_snapshots = cfg.get("retain_snapshots", RETAIN_SNAPSHOTS)` → ตาราง `reconcile_delete_audit` ใช้ `audit_ledger_retain_snapshots` (20) / `audit_ledger_snapshot_age_days` (30) จาก registry แทนค่า arg

job นี้วนทุกตารางใน `registry.tables` + `registry.maintenance_only_tables` ที่ `enabled`

---

## 5. Step Functions input — มาจาก Scheduler

ใน `locals.tf`:
```hcl
pipeline_input_nightly = jsonencode({
  tables               = local.enabled_table_names           # ← tables[] ที่ enabled
  mode                 = "reconcile"                         # ← hardcode
  maxLinkRetries       = var.schedules.max_link_retries      # ← 4
  linkRetryWaitSeconds = var.schedules.link_retry_wait_seconds  # ← 900
  deepVerify = false, deepRepair = false })                  # deep: true / true
```
- Scheduler เก็บ JSON นี้เป็น `target.input` → ส่งให้ SFN ทุกครั้งที่ถึงเวลา
- SFN `ValidateInput` ตรวจว่ามีครบ **6 field** — ขาด = `AlertBadInput` (ส่ง email) ไม่รันอะไรเลย
- `SetDefaults` เพิ่ม `executionName = $$.Execution.Name`
- `Map` แตกเป็นทีละตาราง เพิ่ม `table`, `attempt = 1`
- `ReconcileTable` แปลงเป็น Glue Arguments:

| SFN field | → Glue arg |
|---|---|
| `$.table` | `--TABLE` |
| `$.mode` | `--MODE` |
| `States.Format('{}-{}-{}', executionName, table, attempt)` | `--RUN_ID` |
| `States.Format('{}', $.deepVerify)` | `--DEEP_VERIFY` (เป็น string `"true"`/`"false"`) |
| `States.Format('{}', $.deepRepair)` | `--DEEP_REPAIR` |
| `maxLinkRetries` / `linkRetryWaitSeconds` | **ไม่ส่งเข้า Glue** — SFN ใช้เองใน loop retry |

ค่าที่ Terraform ฝังลง definition ตอน `templatefile`: `${sns_topic_arn}` · `${reconcile_job_name}` · `${maintenance_job_name}` · `${data_bucket}`

---

## 6. bootstrap — ส่งค่าทาง environment

`bootstrap.tf` → `local-exec` → `scripts/bootstrap_glue.py`

| env | มาจาก |
|---|---|
| `AWS_REGION` | `local.region` |
| `AWS_PAGER` | `""` (ปิด pager ของ CLI) |
| `GLUE_DATABASE` | `aws_glue_catalog_database.this.name` |
| `GLUE_JOB_NAME` | `aws_glue_job.reconcile.name` |
| `TABLES_JSON` | `jsonencode(local.enabled_table_names)` |
| `POLL_SECONDS` | `bootstrap.poll_seconds` |
| `TIMEOUT_SECONDS` | `bootstrap.timeout_minutes * 60` |

credential **ไม่ได้ส่ง** — script ใช้ AWS CLI ซึ่ง inherit identity เดียวกับที่รัน Terraform · script **ไม่อ่านรหัสผ่าน DB**
script ส่งต่อให้ Glue: `{"--TABLE": t, "--MODE": "bootstrap", "--RUN_ID": "terraform-bootstrap-<t>-<epoch>"}`

bootstrap รันใหม่เมื่อ `triggers_replace` เปลี่ยน: รายชื่อตาราง · sha256 ของ registry · md5 ของ script reconcile · ชื่อ job (ตารางที่มีอยู่แล้วจะถูก skip)

---

## 7. ค่าที่ไม่ได้มาจาก argv

### 7.1 registry → `CFG` (ต่อตาราง)
`load_registry()`: อ่าน JSON จาก `--REGISTRY_URI` → หา entry `name == TABLE` → `CFG = {**defaults, **entry}` (**ค่าตาราง ทับ defaults**) · `enabled=false` = error `TABLE_DISABLED` · ไม่เจอ = `TABLE_NOT_IN_REGISTRY`

| CFG key | ต้นทาง (tfvars) | อ่านแบบ | ถ้าไม่ใส่ |
|---|---|---|---|
| `target_bucket` | `buckets.data_bucket_name` (defaults) | `CFG[...]` | — |
| `glue_db` | `glue_database_name` (defaults) | `CFG[...]` | — |
| `source_schema` / `source_table` | `tables[].source_schema/source_table` | `CFG[...]` | ต้องใส่ |
| `primary_key` | `tables[].primary_key` (ชื่อฝั่งต้นทาง) | `CFG[...]` | ต้องใส่ |
| `column_map` | `tables[].column_map` (list → JSON object **ลำดับเดิม**) | `CFG[...]` | ต้องใส่ |
| `drift_group_column` | `tables[].drift_group_column` | `CFG[...]` | ต้องใส่ |
| `read_partitions` · `jdbc_fetch_size` · `merge_guard` · `watermark_lookback_days` | `tables[]` ถ้าใส่ ไม่งั้น `registry_defaults` | `CFG[...]` → `int()` | **ห้าม null** → registry.tf ไม่เขียน key ถ้าไม่ใส่ จึงตกไปใช้ defaults |
| `watermark_column` / `watermark_type` | `tables[]` | `.get()` | null = full compare ทุกรอบ |
| `partition_column` | `tables[]` | `.get()` | null = แบ่ง slice ด้วย hash ของ PK ตัวแรก |
| `target_partition_spec` | `tables[]` | `.get()` | null = ไม่ partition |
| `signature_group` | `tables[]` (`{source, target}`) | `.get()` | null = ใช้ `drift_group_column` |
| `secret_id` | `tables[]` | `.get()` | null = ใช้ `--SECRET_ID` |
| `driver_query_attempts` | `tables[]` | `.get()` | null = `--DRIVER_QUERY_ATTEMPTS` หรือ 6 |

### 7.2 Secrets Manager → JDBC
```python
EFFECTIVE_SECRET_ID = CFG.get("secret_id") or SECRET_ID
secret = json.loads(secrets.get_secret_value(SecretId=EFFECTIVE_SECRET_ID)["SecretString"])
# ใช้ secret["host"], ["port"], ["database"], ["username"], ["password"]
```
- รูปแบบ JSON ต้องมี 5 key นี้ — **simulator เขียนให้ตอน bootstrap EC2** · กรณี `manage_secret=true` คนต้อง `put-secret-value` เอง (คำสั่งอยู่ใน output `next_steps`)
- **host ใน JDBC ของ job มาจาก secret ไม่ใช่จาก tfvars** — `source_database.host` ใน tfvars ไปแค่ Glue Connection + placeholder
- อ่าน secret ตั้งแต่ตอน import script (top-level) — แม้ `MODE=verify` ก็ต้องอ่านได้

### 7.3 S3 `_control/` (สถานะข้ามรอบ — อยู่ใน bucket `data`)
| key | เขียนโดย | อ่านโดย |
|---|---|---|
| `_control/<t>/watermark.json` | bootstrap · reconcile ที่ผ่านทุกด่าน | reconcile รอบถัดไป (จุดเริ่ม slice) |
| `_control/<t>/runs/run_id=<RUN_ID>/_SUMMARY.json` | ทุก run (ผ่าน/ไม่ผ่าน gate) | คน / ตรวจผล |
| `_control/<t>/last_failure.json` | `record_failure()` · ลบเมื่อ run สำเร็จ | **Step Functions** `ReadFailureClass` |
| `_control/<t>/pending_deletes/<token>.json` | ก่อน DELETE | reconcile รอบถัดไป (กู้ audit) |
| `_control/<t>/delete_staging/<token>/` | แถวเต็มก่อนลบ (parquet) | complete / recover |

---

## 8. "sys.argv เก็บไว้ที่ไหน"

`sys.argv` เองอยู่**แค่ในหน่วยความจำของ Glue driver ระหว่าง run** — script คัดลอกไปเป็นตัวแปร global แล้วไม่ได้เขียน argv ทั้งก้อนลงที่ไหน แต่**ค่าเดียวกันหาย้อนหลังได้จากที่เหล่านี้**:

| ที่ | เก็บอะไร | ดูยังไง | อยู่นานแค่ไหน |
|---|---|---|---|
| **Glue job definition** | DefaultArguments (ค่าคงที่ทุกตัวในข้อ 3–4) | `aws glue get-job --job-name <job> --query Job.DefaultArguments` · Console → Job → Job details → Advanced → Job parameters | จนกว่าจะแก้/ลบ job |
| **Glue job run** | Arguments ที่ส่งมากับ run นั้น (TABLE, MODE, RUN_ID, DEEP_*) | `aws glue get-job-run --job-name <job> --run-id <jr_...> --query JobRun.Arguments` · Console → Runs → Run details | ตาม retention ประวัติ run ของ Glue `[อนุมาน: เอกสาร AWS ระบุ 90 วัน — ยังไม่ได้ตรวจ]` |
| **Step Functions execution history** | input ของ execution + Parameters ที่ส่งให้ `startJobRun` | `aws stepfunctions get-execution-history --execution-arn ...` · Console → Execution → Graph/Events | Standard workflow `[อนุมาน: 90 วันหลังจบ]` |
| **Scheduler target** | JSON input ของ nightly / deep | `aws scheduler get-schedule --name <project>-nightly` | จนกว่าจะแก้ |
| **CloudWatch Logs** (`/aws-glue/jobs/output`) | บรรทัด `[CONFIG] table / mode run_id / primary key` ที่ script print | Console → Glue run → Output logs | ตาม retention ของ log group (module ไม่ได้ตั้ง) |
| **`_SUMMARY.json`** | `mode, run_id, deep_verify, deep_repair, deletes_enabled, merge_guard, read_partitions, watermark_column, slice_predicate, primary_key` + ผลนับ | S3 `_control/<t>/runs/run_id=<RUN_ID>/` · ข้อ 7.3 | ถาวร (versioning เปิด · version เก่าหมด 90 วัน) |
| **`last_failure.json`** | `mode, run_id, failure_class, message` | S3 | ถูกลบเมื่อ run ถัดไปสำเร็จ |
| **ตาราง Iceberg** | `target_operation_run_id` ทุกแถว · `reconcile_delete_audit.run_id` | Athena | ถาวร |
| **terraform.tfstate** | สำเนา DefaultArguments, schedule input, registry ที่ render แล้ว | `terraform state show aws_glue_job.reconcile` | ตาม state (workshop เป็น local file — หลัง destroy ว่างแล้ว) |

**สิ่งที่ไม่อยู่ใน argv และไม่ควรอยู่:** รหัสผ่าน · username · host ของ DB — มีแค่**ชื่อ secret** (`--SECRET_ID`)

---

## 9. ค่าจาก CloudFormation → tfvars (คนคัดลอก)

| CFN Output (simulator) | → tfvars | หมายเหตุ |
|---|---|---|
| `PrivateIp` | `source_database.host` | Glue ต่อผ่าน private IP |
| `SQLPort` | `source_database.port` | |
| `DatabaseName` | `source_database.database` | |
| `PipelineSecretName` | `source_database.secret_name` + `manage_secret=false` | **ห้ามใช้** `AdminSecretName` |
| `SourceSecurityGroupId` | `source_database.source_security_group_id` | Terraform เพิ่ม rule 1433 จาก Glue SG |
| `SourceTable` = `workshop.orders_reconcile_lab` | `tables[].source_schema` + `source_table` | |
| `ReadinessParameter` | — | รอให้เป็น `READY` ก่อน apply |
| VPC / subnet ที่ใช้ตอนสร้าง stack | `network.vpc_id` · AZ เดียวกัน | |

ค่าใน simulator เองมาจาก CFN Parameters (`ProjectName`, `DatabaseName`, `SQLPort`, …) ผ่าน `!Sub` เข้า UserData → [[Reconcile Pipeline - Source Simulator]]

---

## 10. กับดัก

- **`enforce_ssl` ไม่ถึง job** — job สร้าง URL เองแบบ `encrypt=false;trustServerCertificate=true` ไม่สนค่านี้ `[อนุมาน จาก code]` · ถ้าจะบังคับ TLS ต้องแก้ script
- **`--MODE` default = `verify`** — ถ้าสั่ง run มือแล้วลืมส่ง `--MODE reconcile` จะไม่มีอะไรถูกเขียน (ตั้งใจ)
- **`--TABLE` default = ตารางแรก** — run มือโดยไม่ส่ง TABLE จะทำตารางแรกเสมอ
- **registry ชนะ arg** สำหรับ `secret_id`, `driver_query_attempts`, และค่า retention ต่อตารางของ maintenance
- **ใส่ null ใน 4 ฟิลด์ตัวเลขไม่ได้** — ปล่อยว่างใน tfvars (registry.tf จะไม่เขียน key) อย่าแก้ JSON บน S3 ให้เป็น `null` เอง
- **ค่า arg เป็น string เสมอ** — `"True"` ใช้ได้ (มี `.lower()`) แต่ `"1"` = false
- `get_arg` เอาค่า**ตัวแรก**ที่เจอใน argv

---

## เชื่อมกับโน้ตอื่น

[[Reconcile Pipeline - Overview]] · [[Reconcile Pipeline - Terraform Modules]] · [[Reconcile Pipeline - Glue Jobs]] · [[Reconcile Pipeline - Orchestration & Alerts]] · [[Reconcile Pipeline - Runbook]]
