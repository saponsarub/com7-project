# Reconcile Pipeline - Orchestration & Alerts

> Step Functions `<project>-pipeline` (`templates/state_machine.json.tftpl`, 357 บรรทัด) + Scheduler + SNS + CloudWatch alarm
> ค่าที่ไหลเข้า/ออก state machine → [[Reconcile Pipeline - Arguments & Variables]] ข้อ 5

---

## ผัง

```
ValidateInput (Choice: มีครบ 6 field?)
   ├─ ไม่ครบ ─► AlertBadInput ─► FailPipeline
   └─ ครบ ─► SetDefaults (+executionName)
              ─► ReconcileEachTable  [Map · MaxConcurrency = 1 · ทีละตาราง]
                   ReconcileTable  glue:startJobRun.sync  (TimeoutSeconds 14400)
                     ├─ สำเร็จ ─► TableReconciled
                     └─ Catch ALL ─► ReadFailureClass  s3:getObject _control/<t>/last_failure.json (retry 3)
                                       ├─ อ่านไม่ได้ ─► AlertUnclassifiedFailure ─┐
                                       └─► ParseFailureClass (StringToJson)       │
                                            ─► IsRetryable (Choice)               │
                                                retryable && attempt < maxLinkRetries
                                                    ─► WaitForLink (linkRetryWaitSeconds)
                                                    ─► NextAttempt (attempt+1) ─► ReconcileTable
                                                COUNT_MISMATCH ─► AlertDataMismatch ──┤
                                                VALUE_DRIFT    ─► AlertValueDrift ────┤
                                                SIGNATURE_RENDERING_MISMATCH ─► AlertSignatureDefect ┤
                                                (อื่น ๆ)        ─► AlertHardFailure ──┤
                                                                       FailTable ◄────┘ (Error ReconcileFailed)
              Map Catch: ReconcileFailed ─► FailPipeline (alert ส่งไปแล้ว)
                         อื่น ๆ          ─► AlertPipelineFailure ─► FailPipeline
              ─► IcebergMaintenance  glue:startJobRun.sync (retry 2 · 120s · backoff 2)
                     └─ ล้ม ─► AlertMaintenanceFailed ─► PipelineComplete (ยังนับสำเร็จ)
              ─► PipelineComplete
```

---

## state ทีละตัว

| state | ทำอะไร | ทำไม |
|---|---|---|
| `ValidateInput` | ตรวจ `IsPresent` ของ `tables, mode, maxLinkRetries, linkRetryWaitSeconds, deepVerify, deepRepair` | อ้าง field ที่ไม่มีใน `Parameters` = `States.Runtime` ซึ่ง **catch ไม่ได้** → execution ตายเงียบ · เคยเกิดจริงตอนเพิ่ม `deepVerify/deepRepair` แล้ว schedule เก่าไม่ได้ส่ง |
| `SetDefaults` | คัด 6 field + `executionName = $$.Execution.Name` | ไม่มี default ซ่อน — caller ต้องบอกเองว่าทำตารางไหน |
| `ReconcileEachTable` | Map ทีละตาราง · ส่ง `table`, `attempt = 1` + field อื่นต่อ | link ไป on-prem มีจำกัด ไม่ให้ตารางแย่งกัน · ส่ง deep flag ต่อทุก state กัน retry แล้วกลายเป็นรอบปกติ |
| `ReconcileTable` | `startJobRun.sync` (รอจบ) · Arguments: `--TABLE`, `--MODE`, `--RUN_ID = <exec>-<table>-<attempt>`, `--DEEP_VERIFY`, `--DEEP_REPAIR` | |
| `ReadFailureClass` | อ่าน `last_failure.json` | SFN แยกได้แค่ชื่อ error · Glue ส่งทุก exception เป็นชื่อเดียว |
| `IsRetryable` | `failure.retryable == true` และ `attempt < maxLinkRetries` → รอ · ไม่งั้นแยกตาม `failure_class` | **retry เฉพาะเน็ต** — ข้อมูลไม่ตรง retry กี่รอบก็เท่าเดิม |
| `WaitForLink` | `SecondsPath = linkRetryWaitSeconds` (900) | อาการจริง: IP สาธารณะของ peer on-prem เปลี่ยน หายเองในไม่กี่นาที · เป็น input เพื่อให้เทสต์ใส่ค่าสั้นได้ |
| `IcebergMaintenance` | รันหลังทุกตาราง · `--RUN_ID = <exec>-maint` | ตอนนั้น delete file/ไฟล์เล็กเพิ่งเกิด · ไม่ต้องใช้ต้นทาง → link ล่มก็รันได้ |
| `AlertMaintenanceFailed` → `PipelineComplete` | ไม่ fail pipeline | ข้อมูลถูกแล้ว แค่อ่านช้าลง |

`maxLinkRetries = 4` + รอ 900 วินาที → link ล่มได้ราว 45 นาทีก่อนแจ้งคน (attempt 1–4 · รอ 3 ช่วง) `[อนุมาน จากเงื่อนไข attempt < max]`

---

## Alert (SNS) — หัวเรื่องและความหมาย

| state | Subject | ความหมาย / ต้องทำ |
|---|---|---|
| `AlertDataMismatch` | `Reconcile COUNT MISMATCH on <t>` | จำนวนแถวไม่ตรง · watermark ไม่เลื่อน · ข้อความบอกวิธีแก้ตามทิศ (ขาด → deep repair / เพิ่ม lookback · เกิน → `FULL_KEYSET=true`) |
| `AlertValueDrift` | `Reconcile VALUE DRIFT on <t>` | count ตรงแต่ค่าผิด (deep verify เจอ) · DEEP_REPAIR ปิด → รันซ้ำด้วย `DEEP_VERIFY=true` + `DEEP_REPAIR=true` |
| `AlertSignatureDefect` | `Reconcile signature defect on <t> (not a data problem)` | ทุกแถวเหมือนกัน แต่ signature สองฝั่งไม่ตรง → **แก้ตัวตรวจ ไม่ใช่ข้อมูล** |
| `AlertHardFailure` | `Reconcile FAILED on <t> (<class>)` | class อื่น เช่น `SOURCE_QUERY_ERROR`, `PK_NOT_UNIQUE_IN_SOURCE`, `DRIFT_TOO_WIDE` · "No target state was changed" |
| `AlertUnclassifiedFailure` | `Reconcile failed on <t> with no classification` | job ตายก่อนเขียนไฟล์ → ดู log ของ Glue run |
| `AlertBadInput` | `Reconcile pipeline was started with an unusable input` | caller (schedule) ส่ง input ไม่ครบ → แก้ caller ไม่ใช่ state machine |
| `AlertPipelineFailure` | `Reconcile pipeline failed outside the per-table checks` | loop พังเอง (รวม SNS publish พังใน alert) → เช็คว่าตารางไหนมี `_SUMMARY.json` ใหม่ |
| `AlertMaintenanceFailed` | `Iceberg maintenance failed after a successful reconcile` | ข้อมูลถูก · query จะช้าลงจนแก้ |

---

## Scheduler

| schedule | cron | input |
|---|---|---|
| `<project>-nightly` | `cron(30 23 ? * MON-SAT *)` Asia/Bangkok | `deepVerify=false, deepRepair=false` |
| `<project>-weekly-deep` | `cron(30 23 ? * SUN *)` | `deepVerify=true, deepRepair=true` |
- `state` = `ENABLED` ก็ต่อเมื่อ `schedules.enabled = true` (default false)
- `flexible_time_window = OFF` · retry ส่ง event 1 ครั้ง · event อายุเกิน 900 วินาทีทิ้ง
- `depends_on = bootstrap` → ตารางยังไม่มี = schedule ไม่ถูกสร้าง

## CloudWatch alarm (→ SNS เดียวกัน · ทั้ง ALARM และ OK)

| alarm | metric | เงื่อนไข | missing data |
|---|---|---|---|
| `<project>-execution-failed` | `AWS/States ExecutionsFailed` | ≥ 1 ใน 5 นาที | `notBreaching` |
| `<project>-no-success-26h` | `AWS/States ExecutionsSucceeded` | < 1 ต่อชั่วโมง × 26 ชั่วโมงติด | **`breaching`** — ไม่มี metric = ไม่ได้รัน = เตือน |

ระวัง: ตอน schedule ยัง DISABLED (ช่วง smoke) alarm `no-success` จะเตือนเมื่อครบ 26 ชม. ไม่มี run สำเร็จ — เป็นพฤติกรรมที่ตั้งใจ `[อนุมาน]`

## SNS email
subscription เริ่มเป็น `PendingConfirmation` · **ต้องคลิกลิงก์ในอีเมล** ไม่งั้นไม่ส่งอะไรเลย · Terraform รายงานว่าสร้างแล้วไม่ว่าจะยืนยันหรือไม่ → ตรวจด้วย
```bash
aws sns list-subscriptions-by-topic --topic-arn <alerts_topic_arn>
```

---

## สั่งรันมือ

```bash
# รอบปกติ
aws stepfunctions start-execution --state-machine-arn <arn> --name smoke-<yyyyMMddHHmmss> \
  --input '{"tables":["fact_orders"],"mode":"reconcile","maxLinkRetries":4,"linkRetryWaitSeconds":900,"deepVerify":false,"deepRepair":false}'
# รอบ deep: เปลี่ยน deepVerify/deepRepair เป็น true
# dry run ทั้ง pipeline: "mode":"verify"
aws stepfunctions describe-execution --execution-arn <executionArn>
```
คำสั่ง smoke พร้อม input จริงอยู่ใน `terraform output -raw next_steps`

---

## เชื่อมกับโน้ตอื่น

[[Reconcile Pipeline - Overview]] · [[Reconcile Pipeline - Glue Jobs]] · [[Reconcile Pipeline - Runbook]]
