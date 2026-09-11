# Glue Connectivity

> **สรุปสาระสำคัญ 2026-09-08** — ไล่ debug การตั้ง AWS Glue job (`testjob`) ให้ต่อ MSSQL ทั้งวัน ได้ข้อสรุปเรื่องสถาปัตยกรรมเน็ตเวิร์กที่สำคัญมาก
> เกี่ยวข้อง → [[Network & VPN]] · [[ETL & Spark]] · [[Glue Crawler]] · [[DMS Full Load Validation (Lambda)]] · [[Pipeline Issues]]
> Region **ap-southeast-7 (Bangkok)** · VPC `vpc-0724ede854478d5a3` · Subnet `subnet-01fb5215a38d90391` · RouteTable `rtb-08ed1761f17749e9e` · SG `sg-0027ef551e6e063d2` · Account `603238661233`

---

## 🎯 ข้อสรุปสำคัญที่สุด: Client VPN ใช้กับ Glue ต่อ on-prem ไม่ได้

**คำถามหลัก:** ทำไม DMS ต่อ on-prem MSSQL (K2/ITOS) ได้ แต่ Glue ต่อไม่ได้ ทั้งที่อยู่ AWS เหมือนกัน?

| | Client VPN (ที่ COM7 ใช้อยู่) | Site-to-Site VPN |
|---|---|---|
| เชื่อมอะไร | **เครื่องของคน** (โน้ตบุ๊ก) ↔ AWS VPC | **network ↔ network** (VPC ↔ on-prem) |
| รูปแบบ | client-to-site (คนล็อกอินเข้า) | ถาวร ระดับ subnet |
| DMS ใช้ได้ไหม | ✅ ได้ (สั่งจากเครื่องคนที่ล็อกอิน) | ✅ |
| **Glue ใช้ได้ไหม** | ❌ **ไม่ได้** | ✅ ได้ |

**เหตุผล:** Glue รัน Spark cluster บน **subnet ของ AWS โดยตรง** (ผูก ENI) ไม่มี "คน" ล็อกอิน Client VPN ให้ subnet → subnet จึงไม่มี route กลับไป on-prem (ยืนยันแล้ว: `describe-route-tables` ไม่เจอ on-prem CIDR → vgw/tgw)

> **จำไว้:** DMS/เครื่องคน ต่อ on-prem ผ่านตัวคนที่ล็อกอิน Client VPN · แต่ Glue เป็น service ที่รันเองใน subnet — ต้องมีการเชื่อมระดับ network-to-network เท่านั้น

---

## ✅ ทางเลือกในการต่อ on-prem MSSQL

| ทางเลือก | ข้อดี | ข้อเสีย |
|---|---|---|
| ⭐ **DMS → S3 → Glue** | ใช้ของที่มีอยู่ (DMS + Client VPN) · เลี่ยงปัญหา network ทั้งหมด · เร็วสุด | มี latency (ไม่ real-time) |
| **Site-to-Site VPN** | Glue ต่อ on-prem ตรงได้ · ตรงกับ template ที่เตรียมไว้ | ต้องคุยทีม network COM7 / True IDC · ตั้งค่าเยอะ |
| Direct Connect | bandwidth สูง เสถียร | แพง |

**แนวทางที่แนะนำ:**
```
on-prem MSSQL (K2/ITOS) ──DMS + Client VPN──► S3 ──Glue อ่าน──► Bronze / Silver / Gold
```

---

## 🟢 เส้นทาง network ฝั่ง AWS (S3) — verify แล้วว่าครบสมบูรณ์

ระหว่าง debug ได้ไล่เช็กและแก้จนผ่านทั้งหมด (log ยืนยัน `GlueLibsDownloader` + `Get job script: testjob.py` โหลดสำเร็จ):

- [x] **S3 Gateway Endpoint** `vpce-00e4b9e719776257a` ผูกกับ `rtb-08ed1761f17749e9e`
- [x] **Route S3** `pl-14bc597d → vpce-00e4b9...` = **active**
- [x] **Endpoint policy** เปิดหมด (`Allow / Principal * / Action * / Resource *`)
- [x] **Security Group** `sg-0027ef551e6e063d2`: inbound self-reference (all traffic) + outbound `0.0.0.0/0`
- [x] **VPC DNS**: `enableDnsSupport` + `enableDnsHostnames` = true
- [x] **NACL**: allow all ทั้งขาเข้า/ออก

> S3 Gateway Endpoint แนะนำมากกว่า NAT: ฟรี · อยู่บน AWS backbone (ไม่ออกเน็ต) · ดีต่อ PDPA

---

## 🔧 Error ที่เจอระหว่างทาง + วิธีแก้ (เรียงตามที่เจอ)

### 1. AZ ไม่ตรง subnet
```
InvalidInputException — Availability Zone ap-southeast-7a does not correspond to subnet
```
→ `AvailabilityZone` ใน Glue Connection ต้อง = AZ จริงของ subnet (subnet หนึ่งอยู่ได้ AZ เดียว)

### 2. ไม่มี S3 endpoint / NAT
```
Could not find S3 endpoint or NAT gateway for subnetId ...
```
→ สร้าง **S3 Gateway Endpoint** ผูก route table ของ subnet (ต้อง `modify-vpc-endpoint --add-route-table-ids` ให้ตรงกับ route table ที่ subnet ใช้จริง)

### 3. ชื่อ connection มีเว้นวรรค
```
LAUNCH ERROR — Invalid connection name: Sqlserver connectiontest
```
→ ชื่อ Glue connection **ห้ามมีเว้นวรรค** · rename ในที่ไม่ได้ → สร้างใหม่ (`sqlserver_connection`)
→ 🧹 ปัจจุบันมี connection รก **15 ตัว** จากลองผิดลองถูก — ควรลบตัวที่ไม่ใช้

### 4. ⭐ ตัวหลอก — "Invalid connection name" ทั้งที่ชื่อมีจริง
```
Invalid connection name: Sqlserver-connection2
(แต่ get-connection เจอ connection นี้จริง)
```
→ สาเหตุจริงอยู่ที่ `Status: FAILED · StatusReason: Failed to assume the customers role. Verify that your VPC has access to STS`
→ ต้องสร้าง **STS Interface Endpoint** (ไม่ใช่ Gateway):
```bash
aws ec2 create-vpc-endpoint --vpc-id vpc-0724ede854478d5a3 \
  --service-name com.amazonaws.ap-southeast-7.sts --vpc-endpoint-type Interface \
  --subnet-ids subnet-01fb5215a38d90391 --security-group-ids sg-0027ef551e6e063d2 \
  --private-dns-enabled --region ap-southeast-7
```
> **บทเรียน:** error "Invalid connection name" ไม่ได้แปลว่าชื่อผิดเสมอ — เช็ก `Status`/`StatusReason` ของ connection ด้วย `get-connection` เสมอ
> ถ้ายังติด assume role → เพิ่ม **Glue Interface Endpoint** (`com.amazonaws.ap-southeast-7.glue`) แบบเดียวกัน

### 5. PORT ผิด
connection type `SQLSERVER` แต่ `PORT: 3306` (พอร์ต MySQL) → SQL Server ต้อง **1433**
→ Console SchemaVersion 2 อาจไม่มีช่อง Port เมื่อ host เป็น RDS → แก้ผ่าน CLI `update-connection` (ต้องส่ง ConnectionInput ครบทุก field เพราะเขียนทับทั้งก้อน)

### 6. RDS instance
สร้าง `mssql-datalake-1` (`sqlserver-ex`) — RDS ตั้ง port 1433 ให้เองตาม engine
→ **RDS ไม่จำเป็นถ้าเป้าหมายคือดึง on-prem** (มีค่าใช้จ่าย)
→ รหัส master ห้ามใช้ `/` `@` `"` และเว้นวรรค

---

## 📌 Reference: Endpoint ที่ Glue-in-VPC ต้องมี

| Endpoint | ชนิด | ทำไมต้องมี |
|---|---|---|
| S3 | **Gateway** | script, temp/shuffle, libs, data lake |
| STS | **Interface** | assume role (`Failed to assume role` ถ้าขาด) |
| Glue | **Interface** | บาง setup ต้องมีเพื่อ assume role / API |
| CloudWatch Logs | Interface | เขียน log (ถ้าต้องการ) |

> Gateway (S3/DynamoDB) = เพิ่ม route ใน route table · Interface (ที่เหลือ) = สร้าง ENI + private DNS

---

## ⬜ สิ่งที่ต้องทำต่อ

- [ ] **ตัดสินใจสถาปัตยกรรม**: DMS→S3→Glue (⭐ แนะนำ) หรือ Site-to-Site VPN
- [ ] ถ้าใช้ Site-to-Site: on-prem firewall เปิด **1433** ให้ VPC CIDR + เพิ่ม route on-prem CIDR → VGW/TGW
- [ ] ถ้าเก็บ RDS SQL Server ไว้: ตั้ง Glue connection port **1433** + สร้าง STS endpoint · ถ้าไม่ใช้: ลบ RDS + connection รก 15 ตัว
- [ ] กด **Test connection** ใน Console ให้ผ่านก่อนใช้ใน job เสมอ

---

## เชื่อมกับโน้ตอื่น

[[Network & VPN]] · [[ETL & Spark]] · [[Glue Crawler]] · [[DMS Full Load Validation (Lambda)]] · [[Collection Union (K2 + ITOS)]] · [[Pipeline Issues]] · [[Home]] · [[Current Status]]
