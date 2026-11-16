# Analytics & AI

เนื้อหาเกือบทั้งหมดมาจาก Customer Data Gap Review (4 ส.ค. 2026)

---

## Hyper-Personalization

Data Framework slide 7 ระบุ Expected Result ของงานลูกค้าไว้ว่า:
> "Improved strategic decision · Cost & Time reduction · Hyper personalization · Increased income"

Gap Review ประเมินความพร้อมได้ 9 มี / 17 ไม่พอ / 62 ขาด จาก 88 รายการ

### The report's main conclusion

> "สิ่งที่หน้า 8 ให้ยังเป็น 'ทะเบียนลูกค้า (customer master)' ไม่ใช่ 'customer intelligence' ซึ่งเป็นสิ่งที่ hyper-personalization ต้องใช้"

> "ช่องว่างหลัก 3 จุด: (1) ความลึกของ transaction (2) สัญญาณพฤติกรรมแบบ real-time (3) derived attributes / scoring ที่ยังไม่ปรากฏเลยแม้แต่รายการเดียว"

### The time ceiling

`ARC-03` Real-time / Streaming Ingestion — ขาด, P1

> "hyper-personalization ต้องมี streaming หรือ CDC สำหรับ trigger ที่ไวต่อเวลา เช่น cart abandonment ต้องยิงภายใน 30 นาที ไม่ใช่ T+1 ควรกำหนด latency SLA แยกตามประเภท use case"

> ผลกระทบ: "แคมเปญที่ต้องอาศัยจังหวะจะทำไม่ได้เลย เหลือแต่ batch campaign แบบเดิม"

Batch pipeline รายวันทำ segmentation ได้ แต่ทำ trigger ตามจังหวะไม่ได้ — เป็นข้อจำกัดเชิงสถาปัตยกรรม ไม่ใช่เรื่อง tuning `[อนุมาน]`

### Activation destination

`ACT-01` Personalization ที่จุดสัมผัส — ขาด, P1

> "ยังไม่ระบุว่าจะแสดงเนื้อหาเฉพาะบุคคลที่จุดใดบ้าง โดยเฉพาะการส่ง context ลูกค้าให้พนักงานหน้าร้านผ่าน POS ซึ่งให้ผลตอบแทนสูงในธุรกิจค้าปลีก"

`ARC-07` Reverse ETL / Activation API — มีแต่ไม่ละเอียดพอ, P2

> "ระบุเฉพาะการส่งไป Braze ควรครอบคลุมปลายทางอื่นด้วย: ad platform, website / mobile app, LINE OA และที่สำคัญคือ POS หน้าร้าน"

---

## Derived attributes — all 10 missing

| ID | Attribute | P | เหตุผลในรายงาน |
|---|---|---|---|
| DRV-01 | RFM Score | P1 | "เป็น segmentation ขั้นต่ำที่สุดที่ต้องมี" |
| DRV-02 | CLV — Historical และ Predicted | P1 | "ใช้จัดสรรงบการตลาดตามมูลค่าลูกค้า" |
| DRV-03 | Churn Probability | P1 | "ใช้ trigger แคมเปญรักษาลูกค้าล่วงหน้า" |
| DRV-04 | Propensity to Buy (รายหมวด) | P1 | "เป็นหัวใจของการเลือกสินค้าที่จะเสนอรายบุคคล" |
| DRV-05 | Brand / OS Affinity | P1 | "ป้องกันการเสนอสินค้าข้ามค่ายที่ลูกค้าไม่สนใจ" |
| DRV-06 | Price Sensitivity / Discount Affinity | P2 | "ใช้ตัดสินใจว่าควรให้ส่วนลดหรือไม่ ช่วยรักษา margin" |
| DRV-07 | Preferred Channel + Contact Time | P1 | "เพิ่ม open rate และลดการรบกวน" |
| DRV-08 | Lifecycle Stage | P1 | "เป็นตัวกำหนดว่าจะสื่อสารด้วยข้อความแบบใด" |
| DRV-09 | Segment / Persona Label + model version | P1 | "หน้า 8 เคลมว่า can identify customer segment แต่ยังไม่ระบุที่มา วิธีคำนวณ และที่จัดเก็บ" |
| DRV-10 | Next Best Offer / Next Best Action | P2 | "เป็นผลลัพธ์ปลายทางของ hyper-personalization" |

### What can be done first `[อนุมาน]`

**RFM** ต้องการแค่ประวัติการซื้อ ซึ่ง ITEC มี `TXN-01` (SKU level detail) อยู่แล้วในสถานะ "มีแล้ว" → น่าจะคำนวณได้ภายใน BU เดียวโดยไม่ต้องรอ identity resolution ข้าม BU

**Brand / OS Affinity** ก็น่าจะได้จากประวัติการซื้อของ ITEC เช่นกัน

**Preferred Channel** ต้องการ `BHV-05` (message engagement) ซึ่ง Braze สร้างอยู่แล้วแต่ไม่ไหลกลับ

### Where it must be stored

`ARC-06` Feature Store + Model Registry — ขาด, P2

> "จำเป็นสำหรับเก็บ derived attribute ให้ทั้ง batch และ real-time ใช้ค่าเดียวกัน พร้อม version ของ model"
> ผลกระทบ: "score ที่ใช้ในแต่ละช่องทางไม่ตรงกัน และตรวจสอบย้อนหลังไม่ได้"

**เงื่อนไขก่อน:** derived attribute คำนวณต่อลูกค้า 1 คน ถ้าคนหนึ่งยังเป็นหลาย record จะได้ score ที่ผิด `[อนุมาน]`

---

## Customer behaviour — all 8 missing

| ID | สัญญาณ | P | เหตุผลในรายงาน |
|---|---|---|---|
| BHV-01 | Product View / Category Browse | P1 | "เป็นสัญญาณความสนใจที่แรงที่สุดก่อนการซื้อ" |
| BHV-02 | Add-to-Cart / Cart Abandonment | P1 | "เป็น trigger ที่ให้ conversion สูงที่สุด ต้องยิงภายใน 30 นาที" |
| BHV-03 | Wishlist / Price-drop Watch | P2 | "ใช้ trigger เมื่อราคาลดหรือของกลับมาสต็อก" |
| BHV-04 | Search Keyword + Session Clickstream | P1 | "ใช้เข้าใจ intent และลำดับการตัดสินใจ" |
| BHV-05 | Message Engagement | P1 | "ใช้เลือกช่องทางและความถี่ที่เหมาะกับลูกค้าแต่ละราย" |
| BHV-06 | In-store Behavior | P3 | "เชื่อม online-offline journey ให้สมบูรณ์" |
| BHV-07 | Call Center / Chat Log / Complaint | P2 | "ใช้ระบุ pain point และป้องกัน churn" |
| BHV-08 | NPS / CSAT / Product Review-Rating | P2 | "ใช้แยกลูกค้า promoter กับ detractor" |

### Two that may already be obtainable

**`BHV-01`** — หมายเหตุในรายงาน:
> "คิดว่ายังไม่มีใครดู Data ส่วนนี้แต่คิดว่าสามารถหาได้ น่าจะเป็นทีม Dev หรือ Data Admin ที่ดู Log ของ website: BNN, Studio7, Bkk, Case Club และ BNN App ถ้าเป็นส่วนของ website ต้องดูว่า cookie เก็บอะไรไว้บ้าง ถ้ามี IP ก็ดี"

**เว็บและแอปที่ระบุ:** BNN · Studio7 · Bkk · Case Club · BNN App

**`BHV-05`** — สถานะใน slide 8 ที่รายงานบันทึก:
> "ไม่ปรากฏ (แม้จะส่งผ่าน Braze อยู่แล้ว)"

Braze สร้างข้อมูล open/click/unsubscribe/bounce อยู่แล้ว แต่ไม่ไหลกลับ `[อนุมาน]`

### Sensitivity

รายงานจัด `BHV-06` (in-store tracking) และ `BHV-07` (call/chat log) ว่าความอ่อนไหว PDPA **สูง**
`IDN-08` (Device / Cookie / Advertising ID) ก็จัดว่า **สูง** และสถานะขาด

---

## Segmentation

Data Framework slide 8 ฝั่ง Propose เคลมว่า **"Can identify customer segment"**

Gap Review ตอบว่า:
> "หน้า 8 ระบุว่า 'Can identify customer segment' แต่ไม่ได้ระบุว่า segment คำนวณจาก field ใด ด้วย model อะไร และเก็บไว้ที่ไหน"

`DRV-09` (Segment / Persona Label) สถานะ **ขาด**, P1

### What is feasible now `[อนุมาน]`

จากสถานะ field ที่ Gap Review ระบุ:
- **Demographic segmentation** — `DEM-01` (ชื่อ อายุ วันเกิด เพศ) และ `DEM-02` (career type) อยู่ในสถานะ "มีแล้ว"
- **RFM** — ต้องการ transaction history ซึ่ง ITEC มี

ทั้งสองแบบคำนวณได้ภายใน BU เดียว ไม่ต้องรอ identity resolution

### Measurement

`MSR-02` Control Group / Holdout — ขาด, P1
> "หน้า 11 วัด conversion rate แต่ไม่มีกลุ่มควบคุมเทียบ จึงพิสูจน์ incremental lift ไม่ได้"

`MSR-05` KPI ระดับโครงการ — ขาด, P1
> "ไม่มีเกณฑ์ตัดสินว่าโครงการสำเร็จหรือไม่"

---

## Cross-Selling

### Rationale from the GI+EV7 meeting notes

> "ลูกค้าที่ซื้อ/เช่ารถไฟฟ้าที่เป็นสินค้าที่มีมูลค่าสูง ซึ่งลูกค้ากลุ่มนี้ เป็นกลุ่มที่มีโอกาสสร้างมูลค่าเพิ่มได้ หากได้รับ benefit เพิ่มเติมจาก 7club เช่นลูกค้าที่ซื้อหรือเช่าซื้อรถไฟฟ้า Aion สามารถนำไป cross sale กับ product ของ banana/studio7/ufund ได้"

**คู่ที่บันทึกไว้:**
> "ถ้าจะให้จับคู่ BU GI Match banana และ EV7 - Match - thunder finfin"

> "GI อาจทำการ Coss-selling /ส่งเสริมการขาย กับ BU อื่นได้ เช่น Bananait"

### Blockers that are not about data

> "ลูกค้า EV ได้ Benefit อะไรบ้างจาก 7Club+ — ยังไม่มี Benefit ที่ตอบโจทย์ลูกค้า EV7/GI อย่างชัดเจน ต้องกำหนด Value Proposition ก่อนว่าจะนำ 7Club มาใช้เพื่อสร้าง Cross-selling / Promotion"

เป็นปัญหาเชิงธุรกิจที่ทีมข้อมูลแก้เองไม่ได้ `[อนุมาน]`

### Risk specific to the group structure

`ACT-04` Frequency Capping + Channel Arbitration ข้าม BU — ขาด, P1
> "ลูกค้าหนึ่งรายอาจได้รับข้อความจากหลาย BU ในวันเดียวกัน ต้องมี suppression และ priority rule ส่วนกลาง"
> ผลกระทบ: "ลูกค้ารำคาญและ opt-out ซึ่งเป็นความเสียหายที่กู้คืนได้ยากที่สุด"

---

## Machine Learning

### Status

> **2026-11-10:** AWS ยกเลิกแล้ว ([[Decisions|D-21]]) — งานโมเดลต้องรันบนเครื่อง PC / Kaggle / Colab

**Timeline ไม่มี phase ไหนครอบคลุมการสร้าง model** — จบที่ AWS Production (Design → Implement → Test → Deploy → Maintain)

**AWS Proposal ไม่มี SageMaker หรือ ML platform ใดๆ ในสถาปัตยกรรม**

### What the data supports

Gap Review `ARC-06` (Feature Store + Model Registry) และ `MSR-07` (Model Performance Monitoring / Drift) ระบุว่าขาดทั้งคู่

`MSR-07`: *"score ต่างๆ จะเสื่อมความแม่นยำตามเวลา ต้องมีการติดตาม"*

### Models likely feasible first `[อนุมาน]`

**Credit scoring** — ITOS มีข้อมูลที่ครบที่สุดสำหรับงานนี้: ลูกค้า 165,722 ราย พร้อม `CUST_SALARY`, `CUST_OCCUPATION`, `S_PMTSCHDLE` 3.77M แถว, ข้อมูลค้างชำระ และผลลัพธ์จริง — และไม่ต้องรอ identity resolution ข้าม BU

แต่ credit scoring อยู่ภายใต้การกำกับ — ITOS มี field รหัส ธปท. 3 ตัว ยืนยันว่ามีภาระรายงานต่อ ธปท.

---

## เชื่อมกับโน้ตอื่น

[[Customer Identity]] · [[Consent & PDPA]] · [[CRM Overview|CRM, 7Club, Braze]]
