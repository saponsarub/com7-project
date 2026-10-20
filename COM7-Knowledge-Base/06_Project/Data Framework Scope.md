# Data Framework Scope

**COM7 Group Standard Data Framework** — มาตรฐานที่ MIS ออกให้ทั้งเครือ
ที่มา: `D:\Consent_PDPA\COM7 Group Data Framework.pptx` (16 สไลด์)

> นี่คือ**มาตรฐาน** ไม่ใช่โปรเจกต์ · โปรเจกต์ที่นำมาตรฐานนี้ไปทำจริงอยู่ที่ [[Current Status|AWS Data Lake]]

---

## Purpose

> "Due to business expansion of COM7 group, increasing complexity of data and regulatory compliance, MIS department need to set standard framework for data management to ensure consistency and integration for every business entity in COM7 group."

---

## Six scopes

1. **Finance & Accounting**
2. **Operation**
3. **Customers**
4. **Clean & Unified Data**
5. **Audit & Risk Management**
6. **Regulation & Compliance**

---

## 1 · Finance & Accounting

ขอบเขตที่เขียนละเอียดที่สุดในเดค ครอบคลุม:

**Corporate** — งบการเงินรวมและงบเดี่ยว (P&L, B/S, Cash-Flow)

**General Ledger และ Cost Center** — พร้อมคำอธิบาย และ **ต้อง map เข้ากับ company functions**

**Revenue** — ยอดขายแยกตาม product / customer / channel / geography / promotion / date-time · AR และ aging · เงื่อนไขสัญญาที่กระทบรายได้

**Cost** — headcount รายแผนก · production/service ระดับ transaction (unit/hours) · จำนวน IT license หรือ user

**Overhead & Shared Services** — ค่าใช้จ่ายรายแผนก (finance, HR, R&D) · service-level metric (ticket, payroll, invoice)

**Fixed Assets & Leases** — ทะเบียนสินทรัพย์พร้อมราคาทุน มูลค่าตามบัญชี อายุคงเหลือ · capex และ forecast · ตารางสัญญาเช่าและสิทธิ์ต่ออายุ

**Treasury** — cost recharge, ยอดเงินกู้, statement ธนาคาร

**Tax** — แบบยื่นภาษี, effective tax rate, transfer pricing, ข้อตกลงราคาระหว่างบริษัท, NOL, tax credit

**Employee Financials** — payroll รายพนักงานและ cost center · pension และ post-employment benefit

**Contract & Commitments** — สัญญาลูกค้าหลัก ซัพพลายเออร์ license · สัญญาเงินกู้

**Audit & Compliance** — รายงานตรวจสอบ, เอกสาร internal control, เอกสารสำหรับผู้สอบบัญชีภายนอก

เดคยังให้ **template งบการเงินมาตรฐาน** (สไลด์ 5) ครอบคลุมทั้ง P&L, Balance Sheet, Cash Flow ทั้งแบบ Accrual และ Cash basis

---

## 2 · Operation — by business type

> "Every business has some data in common. However, each business type has specific data of its own."

| ประเภท               | โฟกัส                                                                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Retail**           | Inventory Management · Product Shelf Life · Transportation Schedule · Sale Channel Planning · Promotion · Product Dimension · Product Variety     |
| **Service Provider** | Scope of Services · Progress Planning · License Management · Software Maintenance · Labor Efficiency                                              |
| **Manufacturing**    | Inventory (raw mat, WIP, finished good) · Production Capacity · Production Planning · Logistic System · Machine Maintenance · Supplier Management |
| **Finance**          | Portfolio Management · Customer Credit Score · Approval Process · Collection · Loss Prevention · Loss Reserve · **BOT Compliance**                |

ทุกประเภทมีร่วมกัน: **User Role & Permission** · **Activity Log** · feed เข้า **Consolidated Customer Environment & Leads**

> แถว Finance ตรงกับธุรกิจสินเชื่อของ [[ITOS Overview|TFF/UFUND]] และ **BOT Compliance เป็นกฎเกณฑ์อีกชุดนอกเหนือจาก PDPA** — ยืนยันได้จาก field `CUST_BOTCUSTCODE`, `CUST_BOTCODE`, `CUST_BOTINSTCODE` ใน ITOS

---

## 3 · Customers

### Consent principles (slide 6)

> "According to PDPA a Consent should be:
> **Every Business entity (company) should have consent of its own.**
> Purpose must be separate and specific.
> Easy to understand and not misleading.
> Consent must be given on data owner's free will.
> Data owners can access their personal data.
> Easy to give and easy to revoke."

⚠️ ข้อนี้ขัดกับสไลด์ 8 ที่เสนอให้ CRM ครอบคลุมทั้งเครือ → [[Consent & PDPA]]

### What CRM must have (slide 7)

- **Character** — age, income, occupation
- **Demographic** — address, country, region
- **Historical transaction** — buy, sale, **trade-in**, trn-amt, trn-frequency, first-last trn
- **Timing** — member aging, buy-sell when
- **Product Preference**

ผลลัพธ์ที่คาดหวัง: Improved strategic decision · Cost & Time reduction · Hyper personalization · Increased income

โครงสร้างที่เดควาง: **Consent System → Transaction → Customer Profile → Personalization**

> "trade-in" ถูกระบุระดับ framework แต่ระบบที่ถือข้อมูลนี้ ([[Other Systems|Tech Trade]]) ไม่อยู่ใน project brief เดิม

### CRM Data — current vs proposed (slide 8)

**Current:**
> "CRM Data: Covers ITEC only. Data is sent to CRM team to conduct promotion/loyalty program through Braze."

**Propose:**
> "CRM Data: Covers every system in COM7 group. ... Can identify customer segment."

**Available Data (ทั้งสองฝั่ง):** Main Customer id (เชื่อม 7Club ได้) · Citizen id · demographic · career type · address · contract channel · create/updated date · activity and engagement (UTM) · PDPA Consent · employee flag · student flag

รายละเอียด: [[CRM Overview|CRM, 7Club, Braze]]

### Customer Tracking (slides 9–11)

วงจรที่เดควางไว้:

```
Interest (Website/Physical/Event) → Decision
  ├─ Buy → Existing Customer → Loyalty Program
  └─ Not Buy → Leads/Prospects → Promotion
       ↓
  Campaign Evaluation → Store Result
       ↓
  Consolidated Customer Environment & Leads → กลับไปที่ Interest
```

เกณฑ์วัดแคมเปญที่เดคระบุ: Pros/Cons · Target customers · Cost generated · Sale generated · Time period · **Conversion rate** · Feedback

เดคเขียน **PDPA Law** คร่อมทั้ง flow นี้ไว้

> ⚠️ Gap Review `MSR-02`/`MSR-03` ระบุว่าวัด conversion rate แต่ไม่มีกลุ่มควบคุม จึงพิสูจน์ incremental lift ไม่ได้
> ⚠️ `ACT-06` ระบุว่าเส้นทาง "Not Buy → Leads" ยังไม่มีกลไกเก็บข้อมูลคนที่ยังไม่ซื้ออย่างถูกกฎหมาย

---

## 4–6 · Scopes named in the deck but not detailed

- **Clean & Unified Data** → งานจริงอยู่ที่ [[Data Standardization & Quality]]
- **Audit & Risk Management** → Gap Review `ARC-11` ระบุว่ายังไม่ลงรายละเอียดถึงระดับ lineage
- **Regulation & Compliance** → [[Consent & PDPA]]

---

## เชื่อมกับโน้ตอื่น

[[SSOT Roadmap]] · [[Current Status|AWS Data Lake]] · [[Consent & PDPA]]
