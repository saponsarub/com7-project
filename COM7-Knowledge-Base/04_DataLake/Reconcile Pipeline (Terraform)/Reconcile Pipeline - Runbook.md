# Reconcile Pipeline - Runbook

> ขั้นตอน deploy → ทดสอบ → ลบ ทีละคำสั่ง (ย่อจาก `CROSS_ACCOUNT_DEPLOY.md`) + **ปัญหาที่เจอจริงในรอบ workshop 2026-10-05**
> ค่าแต่ละตัวมาจากไหน → [[Reconcile Pipeline - Arguments & Variables]]

---

## 0. ต้องมีในเครื่อง

- Terraform `1.14.3` (มี 1.16.5 ใน `D:\aws-workshop\terraform_1.16.5_windows_amd64\` — ใช้ได้)
- AWS CLI v2 · **Python 3 ที่เรียกด้วยชื่อ `python3` ได้** (bootstrap ใช้)
- credential ที่สร้าง IAM, EC2/VPC, S3, Glue, Step Functions, Scheduler, SNS, CloudWatch, Athena, อ่าน Secrets Manager ได้
- platform: Windows x64 / Linux / macOS (ไม่มี Windows ARM64)

---

## 1. เลือกบัญชี — STOP GATE

```powershell
$env:AWS_PROFILE = "<profile>"; $env:AWS_PAGER = ""
aws sts get-caller-identity          # ต้องเป็นบัญชีที่ตั้งใจ · ห้ามใช้ admin กับ production ที่ใช้ร่วมกัน
```

## 2. สร้างต้นทาง (workshop)

```bash
aws cloudformation deploy --template-file source-simulator.yaml --stack-name <stack> \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides VpcId=<vpc> SubnetId=<subnet> AllowedClientCidr=<cidr ของ subnet Glue>
aws cloudformation describe-stacks --stack-name <stack> --query "Stacks[0].Outputs"
aws ssm get-parameter --name /<project>/source-ready      # ต้องเป็น READY
```
`[อนุมาน: คำสั่ง deploy ตัวอย่าง — รอบจริงสร้างด้วยวิธีไหนไม่มีบันทึก]` · ต้องมี `CAPABILITY_NAMED_IAM` เพราะตั้ง `RoleName` เอง
รอ `CREATE_COMPLETE` + `READY` + `SeededRows=6` · **ใช้ Outputs ของบัญชีนี้เท่านั้น** ห้ามคัดลอก ID จากบัญชีอื่น

## 3. tfvars

```powershell
Copy-Item examples\cross-account-sandbox.tfvars.example my-pipeline.tfvars
# แก้ทุก REPLACE_* · ใส่ค่าจาก CFN Outputs · schedules.enabled = false
if (Select-String -Path my-pipeline.tfvars -Pattern "REPLACE_") { throw "ยังมี placeholder" }
```
`my-*.tfvars` อยู่ใน `.gitignore` · **ห้ามใส่รหัสผ่าน**

## 4. state

- sandbox คนเดียว: local state (`terraform init`)
- ใช้ร่วม / production: S3 backend เข้ารหัส + versioning → `backend.tf` + `backend.s3.hcl` → `terraform init -backend-config=backend.s3.hcl` (`use_lockfile = true`)
- **ห้ามเอา tfstate จากบัญชีอื่นมาใช้**

## 5. ตรวจก่อน plan

```powershell
Get-FileHash assets\jars\mssql-jdbc-12.8.1.jre11.jar -Algorithm SHA256
#   ต้องได้ e6933c0711e598a224060e52ed31392f720a4a7664e85d8ae37c52a85b67ebb0
terraform fmt -check -recursive
terraform validate
```

## 6. plan — STOP GATE

```powershell
terraform plan -input=false -var-file="my-pipeline.tfvars" -out="my-pipeline.tfplan"
terraform show my-pipeline.tfplan
```
รอบแรกต้องมีแต่ **add** · หยุดถ้าเห็น: destroy · replace ที่ไม่คาด · ID บัญชีอื่น · สร้าง secret ทั้งที่ `manage_secret=false` · ชื่อ bucket ซ้ำ · CIDR ชน · schedule `ENABLED`

## 7. apply

```powershell
terraform apply my-pipeline.tfplan
```
ระหว่าง apply จะเห็น:
```
STARTED fact_orders JobRunId=jr_...
STATE fact_orders RUNNING
SUCCEEDED fact_orders JobRunId=jr_...
BOOTSTRAP_COMPLETE tables=1
Apply complete!
```
bootstrap ล้ม → apply ล้ม (resource อื่นสร้างแล้วและ**คิดเงินต่อ** เช่น NAT) → ดู Glue run → แก้ → apply ใหม่ (ตารางที่มีแล้วข้าม)

## 8. ตรวจหลัง apply

```powershell
terraform output
terraform plan -input=false -detailed-exitcode -var-file="my-pipeline.tfvars"   # ต้อง No changes · exit 0
```
- subnet Glue ไม่ได้ public IP · default route → NAT · S3 → endpoint
- SG ต้นทางรับ 1433 จาก Glue SG → **ลบ rule CIDR ชั่วคราวของ stack ต้นทาง**
- artifacts bucket มี 4 ไฟล์ (2 script · jar · registry)
- bootstrap summary: source = target · key unique · drift 0
- reconcile job อยู่ใน VPC + default `--MODE verify` · maintenance ไม่อยู่ใน VPC
- schedule ทั้งสอง `DISABLED`

## 9. smoke + Athena + email

```bash
aws stepfunctions start-execution ...     # คำสั่งเต็มใน terraform output -raw next_steps
```
ต้องได้: SFN `SUCCEEDED` · `source_rows = target_rows_after` · `distinct_keys = target_rows_after` · `drift = 0` · maintenance ไม่มี error
คลิกลิงก์ยืนยันอีเมล SNS → subscription ไม่เป็น `PendingConfirmation`

Athena (workgroup `<project>-readonly`, database = glue db):
```sql
SELECT order_id, line_no, branch_id, item_id, qty, amount, source_updated_at, note
FROM fact_orders ORDER BY order_id, line_no;
SELECT operation, primary_key_json, run_id, delete_path, deleted_at, recorded_at, row_before_json
FROM reconcile_delete_audit ORDER BY recorded_at DESC LIMIT 10;   -- production: กรอง deleted_at เสมอ
```

## 10. เปิด schedule (apply แยก)

แก้แค่ `schedules.enabled = true` → plan ต้องเห็น **2 in-place update** ไม่มี add/destroy → apply

---

## 11. ทดสอบ INSERT / UPDATE / DELETE (สิ่งที่ทำในรอบ workshop)

สคริปต์ `D:\aws-workshop\.agents\tasks\run_iud_test.py` (ผล → `iud_test.log`, `iud_results.json`, รายงาน `pipeline-iud-test-report.md/.pdf`)

| ขั้น | ต้นทาง (SSM `reconcile-source-lab`) | SFN input | คาดหวัง |
|---|---|---|---|
| 0 | `status` | ปกติ | 6 แถวตรง |
| 1 | `insert` | ปกติ | +2001/1 · 7 แถว |
| 2 | `update` | ปกติ | 1001/1 = 110 |
| 3 | `delete` | ปกติ | −1002/1 · audit `scoped_orphan_delete` |
| 4a | `stale` | ปกติ | **ไม่เปลี่ยน** (จุดบอด) |
| 4b | — | deep | 1003/1 ถูกซ่อม |
| 5 | `reset` | deep | กลับ baseline · 2001/1 ลบผ่าน `deep_repair_delete` |

ผล: **ผ่านทั้ง 7** · ปกติ ~4.5–6 นาที · deep ~7 นาที (Glue reconcile 100–180 วินาที + maintenance 80–135 วินาที + overhead)

---

## 12. ลบ (teardown)

**ลำดับที่ถูก**
```
1. terraform destroy -var-file=my-pipeline.tfvars        ← pipeline ก่อน
   (bucket ไม่ว่าง → ต้องเทของออกก่อน หรือ force_destroy=true — ขอ approve ก่อนทำ)
2. ลบ stack ต้นทาง (CloudFormation)                         ← ทีหลัง
3. ตรวจไม่เหลือ: NAT · EIP · EC2 · Glue job · bucket · Athena workgroup
```
เหตุผล: pipeline เป็นเจ้าของ ingress rule บน SG ต้นทาง และอ่าน secret ของ stack ต้นทางเป็น data source

ตรวจว่าไม่เหลืออะไรคิดเงิน (read-only):
```bash
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE DELETE_FAILED
aws ec2 describe-instances --filters Name=instance-state-name,Values=running,stopped
aws ec2 describe-nat-gateways --filter Name=state,Values=available,pending
aws ec2 describe-addresses
aws glue get-jobs --query "Jobs[].Name"
```

---

## 13. ปัญหาที่เจอจริง (workshop 2026-10-05)

| # | อาการ | สาเหตุ | แก้ |
|---|---|---|---|
| 1 | apply ล้ม `Python was not found; run without arguments to install from the Microsoft Store` exit 9009 | Windows: `python3` เป็น alias ของ Microsoft Store | ปิด App execution alias / ให้ `python3` ชี้ Python จริง |
| 2 | apply ล้ม `can't open file '...\"\scripts\bootstrap_glue.py"'` | `local-exec` แบบ default บน Windows ใช้ `cmd /C` → เครื่องหมาย `"` ติดเข้าไปใน path | เปลี่ยนเป็น `interpreter = ["python3"]` + `command = "${path.module}/scripts/bootstrap_glue.py"` (ไม่ผ่าน shell) |
| 3 | apply รอบ 3 ผ่าน `BOOTSTRAP_COMPLETE tables=1` | — | — |
| 4 | destroy ล้ม `reading Secrets Manager Secret (.../mssql-source): couldn't find resource` | **ลบ stack ต้นทางก่อน** → data source หา secret ไม่เจอ | เทของใน bucket + ลบ Athena workgroup ด้วยมือ (`cleanup_pipeline_destroy.py`) แล้ว destroy ส่วนที่เหลือ (3 resource) |

⚠️ ผลของข้อ 2: `bootstrap.tf` ในเครื่องต่างจาก bundle → `SHA256SUMS` / `MANIFEST.json` ไม่ตรงแล้ว · ถ้าจะปล่อย bundle ใหม่ต้องรัน `build_portable_bundle.py` ใหม่

ไฟล์ทดลองที่ค้างใน `D:\aws-workshop\`: `cd`, `tmp_probe*.txt`, `probe3.txt`, `pyprobe.txt`, `.tmp_env.txt`, `remaining-*.json`, log apply/destroy — ไม่ต้องเข้า git

---

## 14. ก่อนใช้ production

- [ ] TLS ถึงต้นทาง — แก้ JDBC URL ใน script (`encrypt=false` hardcode) ไม่ใช่แค่ `enforce_ssl`
- [ ] deployment role / CI-OIDC แทน admin
- [ ] remote state เข้ารหัส + lock
- [ ] ตั้ง retention ของ CloudWatch log group (module ไม่ได้ตั้ง)
- [ ] ปรับขนาด Glue ตามข้อมูลจริง (G.2X × 10 เกินไปมากสำหรับตารางเล็ก)
- [ ] เจ้าของ / runbook / ใครรับ alert
- [ ] ทดสอบใน `ap-southeast-7` (ตัวอย่างใน module ใช้ region นี้ · workshop ทดสอบ us-east-1)
- [ ] import ของ COM7 ที่สร้างด้วยมือ ถ้าจะให้ Terraform ดูแล

---

## เชื่อมกับโน้ตอื่น

[[Reconcile Pipeline - Overview]] · [[Reconcile Pipeline - Source Simulator]] · [[Reconcile Pipeline - Terraform Modules]] · [[Reconcile Pipeline - Orchestration & Alerts]]
