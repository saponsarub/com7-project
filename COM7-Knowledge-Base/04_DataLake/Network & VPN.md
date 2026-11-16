# Network & VPN

> 🗄️ **2026-11-10 — เลิกใช้ AWS แล้ว** (ไม่ผ่าน POC และงบประมาณ) · แพลตฟอร์มใหม่ = เครื่อง PC on-prem + **MySQL** (concept SSOT เดิม) · ระบบใน AWS ปิดและลบแล้ว → [[AWS Data Lake - Backup & Shutdown 2026-10]] · การเชื่อม on-prem ↔ AWS (Client VPN / Site-to-Site / WireGuard EC2) ไม่ต้องใช้แล้ว เครื่อง PC อยู่ในเครือข่ายบริษัท · ฐาน CRM (Aurora) เข้าผ่าน Outline VPN ของทีม Inno → [[CRM Customer Field Survey]]

การเชื่อมต่อเครือข่ายระหว่าง **on-premise ของ COM7** กับ **AWS VPC** สำหรับดึงข้อมูลเข้า Data Lake

**ที่มา:** `Template AWS VPN Site-to-Site.xlsx` (แบบฟอร์มจาก True IDC ให้ COM7 กรอก) · รับเข้า vault 2026-08-28
สถาปัตยกรรมรวม → [[Architecture]] · บริการที่ใช้ → [[AWS Services]]

---

## 🔴 แจ้งเตือนความปลอดภัย

**ไฟล์ต้นทางมี Pre-Shared Key ของทั้ง 2 tunnel เป็นข้อความธรรมดา**

- โน้ตนี้ **ไม่ได้คัดลอกค่า PSK มา** โดยเจตนา — vault นี้อยู่ใน git repo
- ไฟล์ `Template AWS VPN Site-to-Site.xlsx` **ห้าม commit เข้า repo** และห้ามส่งต่อทางอีเมล/แชท
- ถ้าไฟล์ถูกส่งผ่านช่องทางที่ไม่ปลอดภัยแล้ว → **ควรสร้าง PSK ใหม่ก่อนเปิดใช้งานจริง** (AWS สร้าง PSK ใหม่ได้จากหน้า VPN connection)
- ที่เก็บที่ถูกต้อง: AWS Secrets Manager หรือ password vault ขององค์กร

---

## ทำไมต้องมี VPN

ฐานข้อมูลต้นทางทั้งหมด (K2 / ITOS / ITEC / EV7 / CRM) อยู่ **on-premise** ไม่ได้เปิดสู่อินเทอร์เน็ต
AWS Glue ที่รันใน VPC ต้องเข้าถึงฐานเหล่านี้ได้ → ต้องมีอุโมงค์เชื่อม 2 ฝั่ง

```
On-premise (COM7)                         AWS
┌──────────────────┐                ┌──────────────────┐
│ K2 / ITOS / ITEC │                │  VPC             │
│ CRM / EV7        │◄── IPsec ─────►│  Glue · S3       │
│                  │   Tunnel 1     │  Athena          │
│ Firewall         │   Tunnel 2     │  VGW / TGW       │
│ (Fortigate /     │   (redundant)  │                  │
│  Sophos / Palo)  │                │                  │
└──────────────────┘                └──────────────────┘
```

> อาการ "ต่อฐาน K2 แล้วหลุดกลางคัน" (`Communication link failure`) ที่เจอตอนสำรวจข้อมูล
> เกิดจากลิงก์เครือข่ายเส้นปัจจุบัน — **การมี 2 tunnel คือสิ่งที่แก้ปัญหานี้**

---

## ข้อมูลที่ COM7 ต้องกรอก

| หัวข้อ | ค่าที่ต้องให้ | สถานะ |
|---|---|---|
| Customer Public IP | IP สาธารณะของ firewall ฝั่ง COM7 | ⬜ รอกรอก |
| Customer Firewall | ยี่ห้อ/รุ่น (Fortigate / Sophos / Palo Alto) | ⬜ รอกรอก |
| On-prem CIDR | ช่วง IP ของเครือข่ายภายใน | ⬜ รอกรอก |
| AWS VPC CIDR | ช่วง IP ของ VPC ปลายทาง | ⬜ รอกรอก |
| Routing Type | Static หรือ BGP | ⬜ รอตัดสินใจ |

---

## พารามิเตอร์ IPsec (ตั้งไว้แล้ว ทั้ง 2 ฝั่งต้องตรงกัน)

### Phase 1 — IKE

| พารามิเตอร์ | ค่า |
|---|---|
| IKE Version | **IKEv2** |
| Encryption | AES256 |
| Integrity / Hash | SHA2-256 |
| Diffie-Hellman Group | Group 14 |
| Lifetime | 28,800 วินาที (8 ชม.) |
| Authentication | Pre-Shared Key |

### Phase 2 — IPsec

| พารามิเตอร์ | ค่า |
|---|---|
| Encryption | AES256 |
| Integrity / Hash | SHA2-256 |
| PFS Group | Group 14 |
| Perfect Forward Secrecy | Enabled |
| Encapsulation | ESP |
| Lifetime | 3,600 วินาที (1 ชม.) |
| Mode | Tunnel |

**ประเมิน:** ชุดนี้เป็น **มาตรฐานที่ยอมรับได้ในปี 2026** — AES256 + SHA2-256 + DH14 + PFS
ถ้าอุปกรณ์ฝั่ง COM7 รองรับ อาจพิจารณา DH Group 19/20 (ECDH) เพื่อความแข็งแรงและเร็วขึ้น แต่ไม่ใช่ข้อบังคับ

---

## Tunnel 2 — สำรอง

ใช้ค่าเดียวกับ Tunnel 1 ทั้งหมด **ยกเว้น 4 ค่า**:

| ค่า | รูปแบบ |
|---|---|
| AWS Tunnel Outside IP | `x.x.x.x` (AWS กำหนดให้) |
| **Pre-shared Key** | ต่างจาก tunnel 1 (🔒 ไม่บันทึกในโน้ตนี้) |
| AWS Inside Tunnel IP | `169.254.x.x/30` |
| Customer Inside Tunnel IP | `169.254.x.x/30` |

> AWS Site-to-Site VPN ให้ **2 tunnel เสมอ** เพื่อ high availability — ต้อง config ทั้งคู่
> ถ้า config แค่ tunnel เดียว จะขาดการเชื่อมต่อทุกครั้งที่ AWS ทำ maintenance ฝั่งนั้น

---

## Static vs BGP — ต้องเลือก

| | Static Routing | BGP |
|---|---|---|
| ตั้งค่า | ง่าย ระบุ CIDR ตรงๆ | ซับซ้อนกว่า |
| Failover ระหว่าง tunnel | **ไม่อัตโนมัติ** | **อัตโนมัติ** |
| เพิ่ม subnet ใหม่ | ต้องแก้ config 2 ฝั่ง | ประกาศเส้นทางเองได้ |
| เหมาะกับ | เครือข่ายเล็ก คงที่ | หลาย subnet · ต้องการ HA จริง |

**ข้อเสนอ:** ถ้าต้องการให้ tunnel สำรองทำงานได้จริง ควรใช้ **BGP**
เพราะ static routing ทำให้ tunnel 2 เป็นแค่ของประดับ — ต้องแก้เส้นทางด้วยมือเมื่อ tunnel 1 ล่ม

---

## สิ่งที่ต้องพิจารณาเพิ่ม (ไม่มีในแบบฟอร์ม)

| เรื่อง | ทำไมสำคัญ |
|---|---|
| **Bandwidth** | AWS S2S VPN จำกัดที่ **~1.25 Gbps ต่อ tunnel** และ **ไม่รวมแบนด์วิดท์ข้าม tunnel** — ถ้า full load ครั้งแรกใหญ่มาก อาจไม่พอ |
| **Direct Connect** | ถ้าปริมาณข้อมูลสูงต่อเนื่อง DX เสถียรและถูกกว่าในระยะยาว — ควรประเมินคู่กัน |
| **Security Group / NACL** | ต้องเปิดพอร์ตฐานข้อมูล (MSSQL 1433) เฉพาะ subnet ของ Glue เท่านั้น |
| **DNS resolution** | Glue ต้อง resolve ชื่อ host ฝั่ง on-prem ได้ → Route 53 Resolver inbound/outbound endpoint |
| **ใครดูแล** | ยังไม่ระบุว่าทีมไหนถือ credential และดูแล tunnel |
| **Monitoring** | CloudWatch alarm บน `TunnelState` เพื่อรู้ทันทีเมื่อ tunnel ล่ม |

## สถานะล่าสุด (ประชุม 2026-08-27)

**Client VPN พร้อมเชื่อมต่อได้แล้ว** — ทีม AWS จะดำเนินการขั้นตอนต่อไป
งานถัดไปคือเชื่อมกับ **เครื่อง 250 แบบ full load** โดยประสานกับพี่คอง
→ [[2026-08-27 AWS Data Lake]]

---

## เชื่อมกับโน้ตอื่น

[[Architecture]] · [[AWS Services]] · [[Decisions]] · [[Open Questions & Risks]] · [[Current Status]]
