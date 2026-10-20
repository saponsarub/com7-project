# Reconcile Pipeline - Terraform Modules

> แต่ละไฟล์ใน `reconcile-pipeline-terraform-portable-v1.0.0/` สร้างอะไร · code สำคัญ · เหตุผลที่ออกแบบแบบนี้
> ค่าแต่ละตัวมาจากไหน → [[Reconcile Pipeline - Arguments & Variables]]

---

## โครงสร้างไฟล์

```
reconcile-pipeline-terraform-portable-v1.0.0/
├── versions.tf            Terraform/provider version + default_tags
├── variables.tf           ตัวแปรทั้งหมด + validation (479 บรรทัด)
├── locals.tf              ชื่อ · path · JDBC URL · input ของ schedule
├── network.tf             private subnet · route · NAT · S3 endpoint
├── secrets.tf             secret แบบเป็นเจ้าของ / แบบยืมอ่าน
├── s3.tf                  bucket data/artifacts + upload script/jar
├── registry.tf            สร้าง reconcile_tables.json (หัวใจของ config)
├── iam.tf                 role 3 ตัว
├── glue.tf                catalog DB · SG · connection · 2 job
├── bootstrap.tf           รัน Glue สร้างตารางตอน apply
├── orchestration.tf       Step Functions + 2 schedule
├── monitoring.tf          SNS + 2 alarm
├── athena.tf              workgroup readonly (optional)
├── outputs.tf             next_steps + ชื่อ/ARN ต่าง ๆ
├── templates/state_machine.json.tftpl   definition ของ SFN
├── scripts/bootstrap_glue.py            runner ของ bootstrap
├── assets/glue_reconcile_generic.py     Glue job หลัก (2,192 บรรทัด)
├── assets/glue_iceberg_maintenance.py   Glue job ดูแล Iceberg (325 บรรทัด)
├── assets/jars/mssql-jdbc-12.8.1.jre11.jar (+ .sha256)
├── examples/minimal.tfvars · cross-account-sandbox.tfvars.example
├── source-simulator/                    CFN + validator
├── backend.tf.example · backend.s3.hcl.example
├── MANIFEST.json · SHA256SUMS · build_portable_bundle.py
└── README.md · CROSS_ACCOUNT_DEPLOY.md · THIRD_PARTY_NOTICES.md
```

ลำดับที่ resource ถูกสร้าง (ตาม dependency):
```
data sources ─► s3 (bucket → script/jar/registry) ─► iam ─► network ─► glue (SG → connection → jobs)
            ─► sns ─► state machine ─► bootstrap (รัน Glue จริง) ─► schedules ─► alarms
```

---

## versions.tf

```hcl
terraform { required_version = ">= 1.5.0"
  required_providers { aws = { source = "hashicorp/aws", version = "6.67.0" } } }
provider "aws" { region = var.aws_region
  default_tags { tags = var.tags } }
```
- provider **pin เป๊ะ** `6.67.0` + `.terraform.lock.hcl` (lock 5 platform · ไม่มี windows_arm64)
- `.terraform-version` = `1.14.3` · เครื่องเรามี binary 1.16.5 (`D:\aws-workshop\terraform_1.16.5_windows_amd64`) — ผ่านเพราะบังคับแค่ `>= 1.5`

---

## locals.tf

```hcl
account_id       = data.aws_caller_identity.current.account_id
data_bucket      = coalesce(var.buckets.data_bucket_name, "${var.project}-data-${local.account_id}")
artifacts_bucket = coalesce(var.buckets.artifacts_bucket_name, "${var.project}-artifacts-${local.account_id}")
glue_db          = coalesce(var.glue_database_name, replace(var.project, "-", "_"))

manage_source_secret = coalesce(var.source_database.manage_secret, true)
source_secret_name   = manage ? aws_secretsmanager_secret.source[0].name : data....source_existing[0].name

registry_key = "reconcile/reconcile_tables.json"     # ทุกอย่างที่ job อ่านอยู่ใต้ reconcile/
reconcile_script_path = abspath("${path.module}/assets/glue_reconcile_generic.py")
jdbc_driver_uri = local_path != null ? "s3://<artifacts>/reconcile/jars/<file>" : var.glue.jdbc_driver_jar.s3_uri

reconcile_job_name   = "${var.project}-generic"
maintenance_job_name = "${var.project}-iceberg-maintenance"
connection_name      = "${var.project}-source-jdbc"
state_machine_name   = "${var.project}-pipeline"
topic_name           = "${var.project}-alerts"

glue_subnet_id     = coalesce(try(aws_subnet.glue[0].id, null), var.network.subnet_id)
security_group_ids = coalesce(var.network.security_group_ids, [try(aws_security_group.glue[0].id, null)])
enabled_table_names = [for t in var.tables : t.name if coalesce(t.enabled, true)]
pipeline_input_nightly / pipeline_input_deep = jsonencode({...})   # ดู Arguments ข้อ 5
```
- `coalesce(x, default)` คือรูปแบบหลักของ module — ใส่ = ใช้ · ไม่ใส่ = คำนวณ
- `try(resource[0].id, null)` = resource ที่มี `count = 0` ได้

---

## variables.tf — validation ที่ควรรู้

| validation | ป้องกันอะไร |
|---|---|
| `project` regex | ชื่อ resource ผิดกฎ AWS |
| managed mode ต้องมี cidr + AZ + NAT + endpoint และห้ามมี `subnet_id` | ได้ subnet ที่ออกเน็ตไม่ได้ → job ค้างจน timeout |
| NAT ต้องมี `nat_public_subnet_id` (+ route table ใน existing mode) | NAT ไม่มีที่วาง |
| `manage_secret=false` ต้องมี `secret_name` | |
| `source_security_group_id` ต้องขึ้นต้น `sg-` | |
| ตารางชื่อไม่ซ้ำ · มี PK · `column_map` ไม่ว่าง · ≥1 enabled | |
| PK / watermark / drift_group ต้องอยู่ใน `column_map.source` | job ตายตอน map ชื่อ |
| `merge_guard` ∈ {gt, gte} | |
| jar: `local_path` xor `s3_uri` | |
| `orphan_age_days ≥ 3` เมื่อเปิด cleanup | ลบไฟล์ของ job ที่ยังไม่ commit |
| `bootstrap.poll_seconds ≥ 5` · `timeout_minutes` 5–2880 | |
| Athena ต้องมี `output_location` | |

ผิด = **`terraform plan` ล้ม** ไม่ใช่ job ล้มตอนตี 3

---

## network.tf

```hcl
aws_subnet.glue           count = create_private_subnet ? 1 : 0   map_public_ip_on_launch = false
aws_route_table.glue      + aws_route_table_association.glue
aws_eip.nat               count = create_nat_gateway ? 1 : 0     domain = "vpc"
aws_nat_gateway.this      subnet_id = var.network.nat_public_subnet_id
aws_route.nat_managed     (managed)  0.0.0.0/0 → NAT
aws_route.nat_existing    (existing) for_each nat_route_table_ids
aws_vpc_endpoint.s3       Gateway · route_table_ids = local.s3_endpoint_route_table_ids
```
- **Glue ENI ไม่ได้ public IP** → วางใน public subnet ที่มี IGW ก็ออกไม่ได้ → ต้อง NAT
- **S3 gateway endpoint ฟรี** · NAT คิดตาม GB → ข้อมูล Iceberg วิ่งผ่าน endpoint
- อาการถ้าไม่มี egress: job **ไม่ล้มเร็ว แต่ค้างจน timeout**
- NAT + EIP คิดเงินรายชั่วโมงตลอดที่มีอยู่ → output `nat_gateway_public_ip` ไว้ allow-list firewall on-prem

---

## secrets.tf

```hcl
data "aws_secretsmanager_secret" "source_existing" { count = manage ? 0 : 1, name = requested_secret_name }

resource "aws_secretsmanager_secret" "source" { count = manage ? 1 : 0 ... }
resource "aws_secretsmanager_secret_version" "source_placeholder" {
  secret_string = jsonencode({ host, port, database, username = "SET_ME", password = "SET_ME" })
  lifecycle { ignore_changes = [secret_string] }   # คนใส่ค่าจริงแล้ว apply รอบหน้าจะไม่ทับกลับ
}
```
- `manage_secret=false` (workshop): **ไม่สร้าง ไม่ import ไม่แก้ ไม่ลบ** — stack ต้นทางเป็นเจ้าของ · ไม่มี IaC สองตัวแย่ง resource เดียว
- `manage_secret=true`: apply 2 รอบ — รอบแรก `bootstrap.enabled=false` → ใส่ค่าจริงนอก Terraform → รอบสองเปิด bootstrap
- ⚠️ ถ้า secret (ของ stack ต้นทาง) ถูกลบก่อน → `terraform destroy` พัง ตอนอ่าน data source

---

## s3.tf

| | `data` | `artifacts` |
|---|---|---|
| เก็บ | `iceberg/` ตาราง · `_control/` สถานะ pipeline | `reconcile/` script · jar · registry · `spark-logs/` · `tmp/` · `athena-results/` |
| versioning | **เปิด** — `_control/` คือความจำของ pipeline | ปิด (สร้างใหม่ได้) |
| encryption | SSE-S3 AES256 + bucket key | เหมือนกัน |
| public access | block ทั้ง 4 | เหมือนกัน |
| lifecycle | multipart ค้าง 7 วัน · version เก่าของ `_control/` 90 วัน | multipart 7 · spark-logs 30 · tmp 7 |
| `force_destroy` | `false` | `false` |

```hcl
resource "aws_s3_object" "reconcile_script" { source = local.reconcile_script_path
                                              etag   = filemd5(local.reconcile_script_path) }
```
`etag = filemd5(...)` → แก้ script ในเครื่องแล้ว `apply` = upload ใหม่อัตโนมัติ

---

## registry.tf — สร้าง `reconcile_tables.json`

ไฟล์ config ที่ **Glue ทั้ง 2 job อ่านตอนเริ่ม** · render จากตัวแปรชุดเดียวกับที่สร้าง infra

รูปร่างผลลัพธ์:
```json
{
  "contract_version": "com7.reconcile.registry.v1",
  "_generated_by": "terraform",
  "defaults": { "target_bucket": "...", "glue_db": "...", "jdbc_fetch_size": 20000,
                "read_partitions": 4, "merge_guard": "gte", "watermark_lookback_days": 2 },
  "tables": [ { "name": "fact_orders", "enabled": true, "source_schema": "workshop",
                "source_table": "orders_reconcile_lab", "primary_key": ["OrderId","LineNo"],
                "watermark_column": "UpdatedAt", "watermark_type": "datetime",
                "partition_column": "OrderId", "target_partition_spec": "months(order_datetime)",
                "drift_group_column": "BranchId", "signature_group": {...}, "read_partitions": 4,
                "column_map": { "OrderId": "order_id", "LineNo": "line_no", ... },
                "notes": [] } ],
  "maintenance_only_tables": [ { "name": "reconcile_delete_audit", "enabled": true,
                "retain_snapshots": 20, "snapshot_age_days": 30, "notes": [...] } ]
}
```

**ทำไมต่อสตริงเอง ไม่ `jsonencode` ทั้งก้อน**
```hcl
"      \"column_map\": {\n        ",
join(",\n        ", [for c in t.column_map : "${jsonencode(c.source)}: ${jsonencode(c.target)}"]),
```
`jsonencode(object)` เรียง key ตามตัวอักษร → job เอาลำดับ key ใน `column_map` เป็นลำดับคอลัมน์ตาราง → ตารางปลายทางจะได้คอลัมน์เรียง A-Z · ต่อสตริงเองรักษาลำดับที่เขียนใน tfvars

**null vs ไม่มี key**
- job ทำ `{**defaults, **entry}` → key ที่มีค่า null **ทับ** default
- 4 ฟิลด์ (`read_partitions`, `jdbc_fetch_size`, `merge_guard`, `watermark_lookback_days`) ถูกอ่านด้วย `int(CFG[...])` → null = พัง → **เขียนเฉพาะตอนตั้งค่า**
- ฟิลด์อื่น (`watermark_column`, …) เขียน null ไว้ได้ — `"watermark_column": null` บอกเจตนาว่าตั้งใจ full compare

**ตาราง audit แยกไว้ใน `maintenance_only_tables`** — job reconcile ค้นเฉพาะ `tables` → จะไม่เผลอไป reconcile ตาราง audit (ไม่มี source, PK, column map)

**ตรวจตอน plan**
```hcl
resource "terraform_data" "registry_is_valid_json" {
  lifecycle {
    precondition { condition = can(jsondecode(local.registry_json)) }                       # JSON ถูก
    precondition { condition = length(jsondecode(...).tables) == length(var.tables) }       # ตารางครบ
    precondition { condition = alltrue([... column_map keys == distinct sources ...]) }   # column ไม่หาย/ซ้ำ
  }
}
resource "aws_s3_object" "registry" { content = local.registry_json, etag = md5(...) }
```

---

## iam.tf — 3 role

| role | trust | inline policy |
|---|---|---|
| `<project>-glue-role` | `glue.amazonaws.com` + `aws:SourceAccount` | + managed `AWSGlueServiceRole` · S3 Get/Put/Delete/AbortMultipart บน 2 bucket · ListBucket · **`GetSecretValue` เฉพาะ ARN secret ตัวเดียว** · Glue catalog เฉพาะ DB ตัวเอง (`catalog`, `database/<db>`, `table/<db>/*`) · `GetConnection` เฉพาะ connection ตัวเอง · logs `/aws-glue/*` |
| `<project>-sfn-role` | `states.amazonaws.com` + `aws:SourceAccount` | `glue:StartJobRun/GetJobRun/GetJobRuns/BatchStopJobRun` เฉพาะ 2 job · `s3:GetObject` เฉพาะ `data/_control/*` (อ่าน `last_failure.json`) · `sns:Publish` เฉพาะ topic |
| `<project>-scheduler-role` | `scheduler.amazonaws.com` + `aws:SourceAccount` | `states:StartExecution` เฉพาะ state machine |

`aws:SourceAccount` กัน **confused deputy** — role ที่ trust service principal เฉย ๆ บัญชีอื่นสั่ง service ให้ assume ได้

---

## glue.tf

```hcl
aws_glue_catalog_database.this  { name = local.glue_db }

aws_security_group.glue  count = security_group_ids == null ? 1 : 0
  + ingress self-reference ip_protocol "-1"    # Glue บังคับ: SG ต้องรับทุกอย่างจากตัวเอง
  + egress 0.0.0.0/0

aws_vpc_security_group_ingress_rule.source_from_glue   # วางบน SG **ของต้นทาง** (stack อื่น)
  for_each = source_security_group_id == null ? {} : { index => glue_sg }
  from/to_port = source_database.port  ip_protocol = "tcp"

aws_glue_connection.source {
  connection_type = "JDBC"
  connection_properties = { JDBC_CONNECTION_URL = local.jdbc_url,
                            JDBC_ENFORCE_SSL = tostring(enforce_ssl), SECRET_ID = local.source_secret_name }
  physical_connection_requirements { subnet_id, security_group_id_list, availability_zone }
}

aws_glue_job.reconcile {
  glue_version, worker_type, number_of_workers, timeout, max_retries = 0
  connections = [aws_glue_connection.source.name]   # ← ทำให้ job อยู่ใน VPC
  command { name = "glueetl", python_version = "3", script_location = "s3://<artifacts>/reconcile/glue_reconcile_generic.py" }
  default_arguments = merge(common_job_arguments, { --extra-jars, --MODE=verify, --SECRET_ID,
                                                    --TABLE=<ตารางแรก>, --ENABLE_DELETES=true, --STRICT_COUNT_CHECK=true })
}
aws_glue_job.maintenance { ไม่มี connections · default_arguments = common + --RETAIN_SNAPSHOTS ... --ORPHAN_AGE_DAYS }
```
- `max_retries = 0` — retry อยู่ที่ Step Functions (แยกประเภทได้) ไม่ใช่ Glue (retry มั่ว)
- connection ต้องผูกแม้ job สร้าง JDBC URL เอง — **การผูก connection คือสิ่งที่ทำให้ job ได้ ENI ใน subnet**
- rule `source_from_glue` อยู่ใน state ของ pipeline แต่ SG เป็นของ stack ต้นทาง → **destroy pipeline ก่อนลบ stack ต้นทาง**
- `common_job_arguments`: `--datalake-formats=iceberg` (ไม่มี = Iceberg SQL parse ไม่ผ่าน) · `--enable-glue-datacatalog` · `--TempDir` · `--spark-event-logs-path` · `--REGISTRY_URI`

---

## bootstrap.tf + scripts/bootstrap_glue.py

```hcl
resource "terraform_data" "bootstrap" {
  count = bootstrap.enabled ? 1 : 0
  triggers_replace = { enabled_tables_json, registry_sha256, reconcile_script_md5, glue_job_name }
  provisioner "local-exec" {
    interpreter = ["python3"]                                # แก้แล้ว — ดู Runbook
    command     = "${path.module}/scripts/bootstrap_glue.py"
    environment = { AWS_REGION, AWS_PAGER="", GLUE_DATABASE, GLUE_JOB_NAME, TABLES_JSON, POLL_SECONDS, TIMEOUT_SECONDS }
  }
  depends_on = [glue job, NAT routes, S3 endpoint, source ingress]
}
```
script (Python stdlib + AWS CLI · ไม่ใช้ boto3):
```
for table in TABLES_JSON:
    glue get-table → มีแล้ว: SKIPPED_TABLE_EXISTS · EntityNotFound: ไปต่อ · error อื่น: raise
    glue start-job-run --arguments {"--TABLE","--MODE":"bootstrap","--RUN_ID":"terraform-bootstrap-<t>-<epoch>"}
    poll get-job-run ทุก POLL_SECONDS:
        SUCCEEDED → ต่อ · FAILED/STOPPED/TIMEOUT/ERROR/EXPIRED → raise (apply ล้ม)
    หมดเวลา → batch-stop-job-run แล้ว raise
print BOOTSTRAP_COMPLETE tables=N
```
- ทีละตาราง (ไม่ขนานกัน) · ตารางที่มีแล้วข้าม → **apply ซ้ำได้ปลอดภัย**, เพิ่มตารางใหม่ = bootstrap แค่ตัวใหม่
- schedule `depends_on = [terraform_data.bootstrap]` → bootstrap ไม่ผ่าน = schedule ไม่เกิด

---

## orchestration.tf

```hcl
aws_sfn_state_machine.pipeline { type = "STANDARD"
  definition = templatefile("templates/state_machine.json.tftpl",
               { sns_topic_arn, reconcile_job_name, maintenance_job_name, data_bucket }) }

aws_scheduler_schedule.nightly { state = enabled ? "ENABLED" : "DISABLED"
  schedule_expression = var.schedules.nightly_cron   schedule_expression_timezone = var.schedules.timezone
  flexible_time_window { mode = "OFF" }
  target { arn = SFN, role_arn = scheduler role, input = local.pipeline_input_nightly
           retry_policy { maximum_event_age_in_seconds = 900, maximum_retry_attempts = 1 } } }
aws_scheduler_schedule.deep    { ... deep_cron, input = local.pipeline_input_deep }
```
- definition **คัดจาก production** แทนค่า 4 ตัว — ไม่พิมพ์ใหม่ เพราะพลาดแล้วจะเห็นตอนพังจริงเท่านั้น
- `flexible_time_window OFF` — อ่าน on-prem ผ่าน link จำกัด อยากให้เวลาเริ่มคาดเดาได้
- รายละเอียด state machine → [[Reconcile Pipeline - Orchestration & Alerts]]

---

## monitoring.tf · athena.tf

```hcl
aws_sns_topic.alerts + aws_sns_topic_subscription.email (for_each alert_emails)   # ต้องคลิกยืนยันในอีเมล
aws_cloudwatch_metric_alarm.execution_failed  AWS/States ExecutionsFailed ≥1 / 300s   treat_missing_data = notBreaching
aws_cloudwatch_metric_alarm.no_success        ExecutionsSucceeded <1 ทุกชั่วโมง × 26 รอบ  treat_missing_data = **breaching**
aws_athena_workgroup.readonly { enforce_workgroup_configuration = true
                                bytes_scanned_cutoff_per_query = 10 GiB  result → output_location }
```
- alarm ตัวที่สอง **จับ "ไม่ได้รันเลย"** (schedule ปิด/พัง) ซึ่งตัวแรกมองไม่เห็นเพราะไม่มีอะไร fail
- cutoff ของ workgroup บังคับฝั่ง server → กันได้ทุก tool ที่ต่อเข้ามา

---

## outputs.tf

`next_steps` (ข้อความ): วิธีใส่ secret (ถ้า manage) · ยืนยันอีเมล · สถานะ bootstrap · คำสั่ง smoke `start-execution` พร้อม input · สถานะ schedule
อื่น ๆ: `data_bucket` · `artifacts_bucket` · `registry_uri` · `glue_database` · `reconcile_job_name` · `maintenance_job_name` · `bootstrap_gate_enabled` · `schedules_state` · `state_machine_arn` · `alerts_topic_arn` · `secret_name` · `tables` · `delete_audit_table` · `security_group_ids` · `source_ingress_rule_ids` · `glue_subnet_id` · `glue_route_table_id` · `s3_vpc_endpoint_id` · `nat_gateway_public_ip` · `athena_workgroup`

---

## State / backend / git

- module **ไม่มี backend** → default = local `terraform.tfstate` (workshop ใช้แบบนี้)
- production: `cp backend.tf.example backend.tf` + `backend.s3.hcl` (`bucket`, `key = reconcile-pipelines/<project>/terraform.tfstate`, `encrypt = true`, `use_lockfile = true`) → `terraform init -backend-config=backend.s3.hcl`
- `.gitignore` ตัด: `.terraform/` · tfstate ทุกแบบ · `*.tfplan` (plan มีค่าที่ resolve แล้ว) · `backend.tf`/`backend.s3.hcl` · `/dist/` · `*.auto.tfvars` · `/my-*.tfvars`
- commit: code + `.terraform.lock.hcl` · **ห้าม** state / plan / tfvars จริง / credential
- `MANIFEST.json` + `SHA256SUMS` = checksum ทุกไฟล์ของ bundle · `build_portable_bundle.py` สร้าง bundle จาก allowlist

---

## เชื่อมกับโน้ตอื่น

[[Reconcile Pipeline - Overview]] · [[Reconcile Pipeline - Arguments & Variables]] · [[Reconcile Pipeline - Glue Jobs]] · [[Reconcile Pipeline - Orchestration & Alerts]] · [[Reconcile Pipeline - Runbook]]
