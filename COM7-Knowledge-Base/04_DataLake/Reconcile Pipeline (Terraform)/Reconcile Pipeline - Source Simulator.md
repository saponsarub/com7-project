# Reconcile Pipeline - Source Simulator

> CloudFormation `source-simulator.yaml` (512 บรรทัด) — สร้าง **SQL Server ต้นทางจำลอง** ทิ้งได้ สำหรับฝึก/ทดสอบ pipeline
> ไม่สร้างอะไรของ pipeline · ไม่เปิด SSH · ทุกอย่างสั่งผ่าน SSM

ภาพรวม → [[Reconcile Pipeline - Overview]] · ค่าที่ส่งต่อให้ Terraform → [[Reconcile Pipeline - Arguments & Variables]] ข้อ 9

---

## 1. Parameters (กรอกตอนสร้าง stack)

| Parameter | default | ข้อจำกัด / ความหมาย |
|---|---|---|
| `ProjectName` | `reconcile-source-sim-2` | `^[a-z][a-z0-9-]{2,40}$` · prefix ชื่อทุก resource |
| `DatabaseName` | `ReconcileWorkshop` | SQL identifier |
| `VpcId` | — | ต้องใส่ |
| `SubnetId` | — | ต้องออกเน็ตได้ (ดึง image จาก MCR + เรียก AWS API) · public subnet + public IP ง่ายสุด |
| `ClientSecurityGroupId` | `''` | SG ของ Glue ที่ให้ต่อ 1433 (แนะนำ) |
| `AllowedClientCidr` | `10.0.0.0/16` | ใช้เมื่อไม่ใส่ SG · **ห้าม 0.0.0.0/0** |
| `AssociatePublicIpAddress` | `true` | ไว้ออกเน็ตขาออกเท่านั้น |
| `SQLPort` | `1433` | 1024–65535 |
| `InstanceType` | `t3.medium` | `t3.medium` / `t3.large` (SQL ต้อง RAM ≥ 2 GB) |
| `LatestAmiId` | SSM `/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64` | Amazon Linux 2023 ล่าสุด |
| `SqlServerImage` | `mcr.microsoft.com/mssql/server:2022-CU27-ubuntu-22.04` | regex บังคับว่าต้องมาจาก `mcr.microsoft.com/mssql/server:2022-*` |

**Conditions**
```yaml
HasClientSecurityGroup: !Not [!Equals [!Ref ClientSecurityGroupId, '']]   # → ingress จาก SG
UseClientCidr:          !Equals [!Ref ClientSecurityGroupId, '']          # → ingress จาก CIDR
UsePublicIp:            !Equals [!Ref AssociatePublicIpAddress, 'true']
```
⚠️ ตอนสร้าง stack ครั้งแรก Glue SG ยังไม่มี (Terraform สร้างทีหลัง) → มักต้องใช้ CIDR → Terraform เพิ่ม rule จาก Glue SG ทีหลัง → **ควรลบ rule CIDR ออก** (runbook ข้อ 8) · รอบ workshop ใช้ CIDR อะไร — **ไม่รู้** (ไม่มีใน log)

---

## 2. Resources

| Logical ID | ชนิด | สาระ |
|---|---|---|
| `AdminSecret` | SecretsManager | `<project>/mssql-admin` · `{"username":"sa"}` + password สุ่ม 24 ตัว · **ไว้ผู้ดูแล ห้ามผูกกับ Glue** |
| `PipelineSecret` | SecretsManager | `<project>/mssql-source` · `{"username":"pipeline_reader"}` + password สุ่ม · pipeline ใช้ตัวนี้ |
| `ReadyParameter` | SSM Parameter | `/<project>/source-ready` เริ่ม `PROVISIONING` → `READY` / `FAILED: ...` |
| `InstanceRole` | IAM Role | ดูข้อ 3 |
| `InstanceProfile` | IAM | ผูก role กับ EC2 |
| `SourceSecurityGroup` | EC2 SG | egress ทั้งหมด · **ไม่มี ingress 22** |
| `SqlIngressFromSecurityGroup` / `SqlIngressFromCidr` | SG Ingress | 1433 อย่างใดอย่างหนึ่งตาม Condition |
| `SourceInstance` | EC2 | ดูข้อ 4–5 |

password ทั้งสองสร้างด้วย `GenerateSecretString` + `ExcludeCharacters: "'"` (เพราะจะถูกฝังในสตริง T-SQL `N'...'`) + `RequireEachIncludedType: true`

---

## 3. InstanceRole — สิทธิ์ของ EC2

```yaml
AssumeRolePolicyDocument: Principal ec2.amazonaws.com + Condition aws:SourceAccount = บัญชีตัวเอง
ManagedPolicyArns: AmazonSSMManagedInstanceCore          # สั่งงานผ่าน SSM แทน SSH
Policies:
  - secretsmanager:GetSecretValue, PutSecretValue  → เฉพาะ AdminSecret + PipelineSecret
  - ssm:PutParameter                               → เฉพาะ /<project>/source-ready
  - cloudformation:SignalResource                  → เฉพาะ stack ตัวเอง
```

---

## 4. SourceInstance — คุณสมบัติ

```yaml
DependsOn: [InstanceProfile, ReadyParameter, AdminSecret, PipelineSecret]
CreationPolicy: ResourceSignal: { Timeout: PT20M, Count: 1 }
```
- stack **ไม่ CREATE_COMPLETE จนกว่า EC2 ส่ง signal** ว่า SQL พร้อม · เกิน 20 นาที = rollback
- `MetadataOptions.HttpTokens: required` = IMDSv2 เท่านั้น · hop limit 2 (ให้ container เรียกได้)
- EBS gp3 30 GB **encrypted** · ลบพร้อม instance
- tag `Name = <project>-sql-source`

---

## 5. UserData — สคริปต์บูต (bash)

ค่าทุกตัวในสคริปต์มาจาก `!Sub` ของ CFN: `${AWS::Region}` `${AWS::StackName}` `${AdminSecret}` (= ARN) `${PipelineSecret}` `${ReadyParameter}` (= ชื่อ) `${DatabaseName}` `${SQLPort}` `${SqlServerImage}`

| ขั้น | code | หมายเหตุ |
|---|---|---|
| log | `exec > >(tee /var/log/source-simulator-bootstrap.log \| logger -t source-simulator -s 2>/dev/console) 2>&1` | log ไป 3 ที่: ไฟล์ · syslog · console |
| strict | `set -Eeuo pipefail` | คำสั่งไหนพัง = หยุด |
| signal | `signal(status, reason)`: ขอ IMDSv2 token → instance-id → `cfn signal-resource` · SUCCESS → SSM `READY` · FAILURE → `FAILED: <reason>` | `|| true` กันไม่ให้ signal พังซ้อน |
| trap | `trap 'on_error $LINENO' ERR` | พังบรรทัดไหน → `FAILED: bootstrap line N` |
| ติดตั้ง | `dnf install -y docker jq` · `systemctl enable --now docker` | |
| อ่าน secret | `aws secretsmanager get-secret-value` × 2 → `jq -r .password` → `test -n` + `!= null` | ตรวจว่าได้ค่าจริง |
| รัน SQL | `docker run -d --name sqlserver --restart unless-stopped -e ACCEPT_EULA=Y -e MSSQL_PID=Developer -e MSSQL_SA_PASSWORD=... -e MSSQL_TCP_PORT=... -p port:port -v reconcile-sql-data:/var/opt/mssql <image>` | ข้อมูลอยู่ใน docker volume |
| รอพร้อม | วน 90 × 10 วินาที `sqlcmd -C -Q 'SELECT 1'` | สูงสุด 15 นาที · `-C` = trust cert |
| init.sql | heredoc → `chmod 600` → `sqlcmd -b < init.sql` → **`shred -u`** | ไฟล์มีรหัส reader → ลบแบบเขียนทับ |
| อัปเดต secret | IMDS → `local-ipv4` → `jq -n` สร้าง `{host,port,database,username,password}` → `put-secret-value` ทั้ง 2 ตัว | **นี่คือรูปแบบที่ Glue job อ่าน** |
| lab script | เขียน `/usr/local/bin/reconcile-source-lab` `chmod 750` | ข้อ 7 |
| จบ | `reconcile-source-lab status` → `signal SUCCESS 'ready'` → `trap - ERR` | |

---

## 6. init.sql — สิ่งที่สร้างใน SQL Server

```sql
IF DB_ID(N'ReconcileWorkshop') IS NULL CREATE DATABASE [ReconcileWorkshop];
CREATE SCHEMA workshop AUTHORIZATION dbo;
CREATE TABLE workshop.orders_reconcile_lab (
    OrderId int NOT NULL, [LineNo] int NOT NULL, BranchId int NOT NULL,
    ItemId nvarchar(50) NOT NULL, Qty int NOT NULL, Amount decimal(19,4) NOT NULL,
    OrderDatetime datetime2(3) NOT NULL, UpdatedAt datetime2(3) NOT NULL, Note nvarchar(100) NULL,
    CONSTRAINT PK_orders_reconcile_lab PRIMARY KEY (OrderId, [LineNo]));
CREATE LOGIN [pipeline_reader] WITH PASSWORD=N'<สุ่ม>', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;
CREATE USER [pipeline_reader] FOR LOGIN [pipeline_reader];
GRANT SELECT ON OBJECT::workshop.orders_reconcile_lab TO [pipeline_reader];   -- อ่านได้ตารางเดียว
```
ทุกคำสั่งมี `IF ... IS NULL` / `IF NOT EXISTS` → รันซ้ำได้

### ข้อมูลตั้งต้น 6 แถว — แต่ละแถวมีหน้าที่
| แถว | Branch | วันที่ (ย้อนจากตอนสร้าง) | Note | ใช้ทดสอบ |
|---|---|---|---|---|
| 1001/1 | 10 | −90 วัน | `baseline-a` | update ปกติ |
| 1001/2 | 10 | −90 วัน | `baseline-b` | แถวคงที่ |
| 1002/1 | 20 | −60 วัน | `delete-me-later` | delete |
| 1003/1 | 20 | −30 วัน | `stale-change-later` | **จุดบอด watermark** |
| 1004/1 | 30 | −7 วัน | NULL | ค่า NULL ใน signature |
| 1005/1 | 30 | ตอนนี้ | `watermark-anchor` | ตั้ง max UpdatedAt |

วันที่กระจายหลายเดือน → partition `months(order_datetime)` มีหลายกลุ่ม · Branch 3 ค่า → `drift_group_column` มีหลายกลุ่ม

---

## 7. `reconcile-source-lab` — เครื่องมือแก้ข้อมูลระหว่างฝึก

อ่านรหัส **sa** จาก `AdminSecret` ทุกครั้งที่รัน · เรียกผ่าน SSM:
```bash
aws ssm send-command --instance-ids <id> --document-name AWS-RunShellScript \
  --parameters '{"commands":["sudo /usr/local/bin/reconcile-source-lab <action>"]}'
aws ssm get-command-invocation --command-id <cid> --instance-id <id>
```

| action | SQL | ผลที่ pipeline ควรเห็น |
|---|---|---|
| `status` | count, distinct key, min OrderDatetime, max UpdatedAt + ทุกแถว | — |
| `seed` | INSERT เฉพาะแถวตั้งต้นที่หาย (ไม่ทับของเดิม) | — |
| `insert` | `2001/1` Branch 40 `ITEM-NEW` 345.67 `insert-test` | INSERT |
| `update` | `1001/1` Amount 110, Note `normal-update-test`, **UpdatedAt = now** | UPDATE ผ่าน slice ปกติ |
| `delete` | ลบ `1002/1` | DELETE + audit |
| `stale` | Note `1003/1` = `changed-without-watermark` **ไม่แตะ UpdatedAt** | รอบปกติไม่เห็น · รอบ deep เห็น |
| `reset` | ลบ 2001 → seed → คืนค่า 1001 (UpdatedAt = now) และ 1003 (UpdatedAt = −30 วัน) | กลับ baseline (timestamp ไม่ตรงเดิมเป๊ะ) |

---

## 8. Outputs

| Output | ค่า | ใช้ที่ |
|---|---|---|
| `InstanceId` | EC2 ID | SSM send-command |
| `PrivateIp` | IP ภายใน | `source_database.host` |
| `SQLPort` / `DatabaseName` | | tfvars |
| `SeededRows` | `'6'` (ค่าคงที่) | ตรวจว่า bootstrap ครบ |
| `SourceTable` | `workshop.orders_reconcile_lab` | `tables[]` |
| `PipelineSecretName` | `<project>/mssql-source` | `secret_name` / `--SECRET_ID` |
| `AdminSecretName` | `<project>/mssql-admin` | **ห้ามผูกกับ Glue** |
| `ReadinessParameter` | `/<project>/source-ready` | รอ `READY` |
| `SourceSecurityGroupId` | SG | `source_security_group_id` |
| `JdbcUrl` | `jdbc:sqlserver://<ip>:<port>;databaseName=<db>` | อ้างอิง |
| `SsmLabCommand` | `sudo /usr/local/bin/reconcile-source-lab status` | |

---

## 9. ความปลอดภัยที่ออกแบบไว้

- ไม่มี SSH key · ไม่เปิด 22 · ใช้ SSM
- password สุ่มโดย Secrets Manager — คนไม่เห็น ไม่ได้พิมพ์
- ไฟล์ที่มีรหัส `shred -u` ทันที · `chmod 600`
- reader มีแค่ `SELECT` ตารางเดียว
- IAM จำกัดเฉพาะ resource ของ stack + `aws:SourceAccount`
- IMDSv2 บังคับ · EBS เข้ารหัส
- image pin tag + regex บังคับ registry

ข้อสังเกต: `sa` password ถูกส่งเป็น env ของ container (`MSSQL_SA_PASSWORD`) และ argument ของ `sqlcmd -P` — คนที่มีสิทธิ์ root บน EC2 เห็นได้ (`docker inspect` / process list) · ยอมรับได้สำหรับ sandbox `[อนุมาน]`

---

## เชื่อมกับโน้ตอื่น

[[Reconcile Pipeline - Overview]] · [[Reconcile Pipeline - Arguments & Variables]] · [[Reconcile Pipeline - Runbook]]
