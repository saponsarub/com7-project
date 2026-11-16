# ITEC-Rep Overview

**ฐาน ITEC ตัวหลักที่จะใช้จริง** ตั้งแต่ 2026-11 — replica ของระบบค้าปลีก ITEC ทั้งระบบ (ตารางดิบ ไม่ใช่ view สรุปแบบITEC-MIS)
คู่กับ [[ITEC-MIS Overview|ITEC-MIS]] (view สรุปบนเครื่อง 250 — ยังใช้ได้) · เปรียบเทียบ 2 ฐาน → [[ITEC Overview]] · สำรวจ 2026-11-10 ด้วยสิทธิ์อ่าน

| | |
|---|---|
| Server | `10.100.101.50` (พอร์ต 1433) |
| DBMS | Microsoft SQL Server 2017 (14.0) |
| ฐานหลัก | **`SSSynced50`** — schema `dbo` อย่างเดียว · **472 ตาราง + 8 view** · 8,480 คอลัมน์ |
| ฐานอื่นที่เข้าได้ | `SSSynced50report` (29 ตาราง) · `SSSynced50pic` (ว่าง) · `ITECUpdate` (ไม่มีสิทธิ์) |
| ความสด | **เกือบ real-time** — บิลล่าสุดใน `Sell` / `FullTaxInv` / `Receipt` ห่างเวลาจริงไม่กี่นาที (ตรวจ 10:51 วันที่ 10 พ.ย.) |
| ประวัติ | `Sell.DocDate` ตั้งแต่ **2007-03-15** ถึงปัจจุบัน · 2,834 สาขาที่เคยขาย |
| ต่อจากโค้ด | `python scripts/db.py itec` · profile `itec` · credential จาก env **`ITEC_USER` / `ITEC_PWD`** (ห้ามจดรหัสในโน้ต) |
| ไฟล์โครงสร้างเต็ม | `02_System/_raw/itec-rep-tables.csv` (ตาราง · แถว · คอลัมน์) · `itec-rep-columns.csv` · `itec-rep-pk.csv` |

---

## ตารางแบ่งตามเรื่อง (จัดกลุ่มจากชื่อ `[อนุมาน]`)

105 ตารางว่าง · 78 ตารางเกิน 1 ล้านแถว

| เรื่อง | ตาราง | แถวรวม | ตารางใหญ่สุด |
|---|---|---|---|
| สินค้า / ราคา / โปรโมชัน | 26 | 6,659M | `PMTPToPP` (5,910M) · `ProductBSP` · `PMTProduct` · `SeeNewProduct` · `Product` (220,725) |
| ขาย / ใบกำกับ | 47 | 703M | `SellItem` (143M) · `FullTaxInvItem` (116M) · `SOItem` · `Receipt` (59M) · `Sell` (53M) |
| สต็อก / โอน / ต้นทุน | 57 | 671M | `SetCheckStockProduct` (321M) · `MAForCalRRCenter` · `Cost` (66M) · `BISN` · `MinAutoSet` |
| ชำระเงิน / ธนาคาร | 33 | 88M | `CreditCardRev` (38M) · `BankCDCReportItem` · `CDCDeposit` · `BranchCashDeposit` · `Pay` |
| log | 6 | 41M | `LogSave` · `NotifyLog` |
| ลูกค้า | 10 | 32M | `Customer2` (24.8M) · `Cus2Address` (6.9M) · `Customer` (44k) |
| สาขา / พนักงาน | 15 | 3.4M | `Branch` (3,390) · `Officer` · `OfficerTime` |
| อื่น ๆ | 278 | 100M | `BI` · `ULSO` · `SalesOrderItem` · `AgingRotate` · `Buy` |

View: `ProductView` (94 คอลัมน์) · `BranchView` (74) · `BuyView` · `SOView` · `SupplierView` · `StockForWeb` · `LimitedViewCustomer` / `LimitedViewCustomer2` (คอลัมน์เดียว)

---

## ตารางแกน

| ตาราง | แถว | Primary key | เก็บอะไร |
|---|---|---|---|
| `Sell` | 53.3M | `ID, Branch` | หัวบิลขาย — `DocNo` · `DocDate` · `CusCode` · ยอด (`SumPrice` `TotalPrice` `VAT`) · `OfficerID` · `Chanel` · `Status` |
| `SellItem` | 142.7M | `ID, Branch, Product, Serial, …` (14 คอลัมน์) | รายการในบิล — `Product` · `Serial` · `Number` (จำนวน) · `Price` · ส่วนลด · ประกัน (`WTDays`) |
| `Product` | 220,725 | `Product` | สินค้า — `Name` · `CategoryID` · `Brand` · `Model` · `Series` · `CurCost` · `EOL` · `Status` |
| `Branch` | 3,390 | `ID` | สาขา — `Name` · `BU` · `Channel` · `Region` · `Province` · `District` · `Latitude/Longitude` · `OpenDate/CloseDate` · `BranchStatus` · `Franchise` |
| `Customer2` | 24.8M | `CusCode` | ลูกค้า — **ดูหัวข้อถัดไป** |
| `Cus2Sell` | 42.3M | `CusCode, SellID, SellBranch` | ลูกค้า ↔ บิล (+ `InvNo`) |
| `FullTaxInv` / `…Item` | 28.1M / 115.8M | `InvNo` | ใบกำกับภาษีเต็มรูป |
| `Receipt` | 59.5M | `PID, PBranch` | ใบเสร็จ / รับเงิน |
| `Cost` | 66.2M | `ID, Branch, TType, TID, Product, Serial` | ต้นทุนรายชิ้น |
| `CreditCardRev` | 37.9M | `ID, Branch` | รับชำระบัตรเครดิต |

ทุกตารางมีคอลัมน์ระบบ `CrOff` `CrTime` `UOff` `UTime` `RepTime` `Counter` (ผู้สร้าง/แก้ · เวลา · replicate)

---

## ข้อมูลลูกค้า `Customer2` (unmask แล้ว 2026-11-13)

`Customer2` 24,848,793 แถว · 44 คอลัมน์ · นับวันที่ 2026-11-13

| คอลัมน์ | มีค่า | หมายเหตุ |
|---|---:|---|
| `Name` · `Surname` | 100% | |
| `Tel` | 24.27M (97.7%) | เป็นมือถือ 10 หลัก 21.0M · หลัง normalize ใช้ได้ ~96% |
| `Email` | 11.31M (45.5%) | |
| `CitizenNo` | 8.52M (34.3%) | เลข 13 หลัก 7.96M |
| `TaxNo` | 20.17M (81.2%) | ใช้ได้ (ผ่าน checksum) ~61% · **เท่ากับ `CitizenNo` 100% เมื่อมีทั้งคู่** · มีเลขบัตรใน `TaxNo` แต่ไม่มีใน `CitizenNo` อีก ~12% |
| `HBD` | 4.62M (18.6%) | |
| `Gender` | 20.32M | |
| `CRMID` | 9.04M (36.4%) | รูปแบบ `M` + 12 หลัก = CRM `members.member_id` |
| `CusCompany` | 593k | |
| `ConsentPersonal` > 0 | 9.22M | |

- เลขบัตร = `CitizenNo` ถ้าผ่าน checksum ไม่งั้นใช้ `TaxNo` → ครอบคลุม ~60% ของลูกค้า ITEC `[วัดจาก sample 200k]`
  - `TaxNo` ของนิติบุคคลเป็นเลขผู้เสียภาษี 13 หลักเหมือนกัน (ขึ้นต้น `0`) — ต้องแยกก่อนใช้เป็นเลขบัตรบุคคล
- ⚠️ เป็นข้อมูลส่วนบุคคลเต็มรูปแบบ — ใช้ตาม [[Consent & PDPA]] · เลขบัตรต้อง hash (HMAC) ก่อนเก็บ · `Cus2Address` มีที่อยู่จริง

**เชื่อม CRM** (sample 20,000 แถวที่มี `CRMID` · 2026-11-13)
- `Customer2.CRMID` = CRM `members.member_id` → เจอ **98.7%**
- `Customer2.CusCode` = CRM `members.itec_cuscode` ตรงกัน 100% ในคู่ที่เจอ (join ด้วย `member_id` — `IN` บน `itec_cuscode` ตรงๆ แทบไม่เจอ)
- ค่าตรงกันระหว่าง 2 ระบบ: เบอร์ **100%** · ชื่อ+นามสกุล 97.5% · เลขบัตร vs `member_auth.identity_no` 96.3% (n=460)
- ⇒ ITEC เป็นแหล่ง**เลขบัตรของสมาชิก CRM** ได้ (CRM `customer_master.citizen_no` ยังถูกซ่อน)

```
CRM members.itec_cuscode ══ Customer2.CusCode ── Cus2Sell ── Sell (ID, Branch) ── SellItem ── Product
                                                                  └── Branch
```

---

## เทียบกับ ITEC-MIS

ชื่อ view ของ ITEC-MIS ทุกตัว (`rpt.fact_sales_itec` · `rpt.dim_item_itec` · `rpt.dim_mem_itec` · `ci.clean_item_category_itec` · `ci.clean_branch` · …) **ไม่มีใน ITEC-Rep** — ต้องสร้างเองจากตารางดิบ หรือใช้ view บน ITEC-MIS
| view ของ ITEC-MIS | ตารางต้นทางในฐานนี้ `[อนุมาน — ยังไม่ได้เทียบตัวเลข]` |
|---|---|
| `rpt.fact_sales_itec` | `Sell` ⨝ `SellItem` (+ `Cost` สำหรับต้นทุน) |
| `rpt.dim_item_itec` | `Product` / `ProductView` |
| `rpt.dim_branch_itec` | `Branch` / `BranchView` |
| `rpt.dim_mem_itec` | `Customer2` + `Cus2Sell` |
| `rpt.fact_bank_itec` | `CreditCardRev` · `BankCDCReportItem` · `Receipt` |
| `rpt.onhandendmonth_itec` | ตารางสต็อก (`SetCheckStockProduct` · `BISN`?) |
| `ci.*` (ทำความสะอาดหมวด/แบรนด์) | ไม่มี — ใช้ logic ใน [[ITEC Item Category Mapping (SQL to Python)]] |

งานถัดไป: เทียบยอดขายรายเดือนจาก `Sell/SellItem` กับ `rpt.fact_sales_itec` ของ ITEC-MIS เพื่อยืนยันนิยามยอดขาย/ต้นทุน/คืนสินค้า

[[ITEC Overview]] · [[CRM - Data Dictionary]] · [[Current Status]] · [[System Inventory]]
