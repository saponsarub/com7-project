# Snapshot Change Detection (ITEC DMS)

> ผังจากทีม **Data Engineering (AWS)** — `Screenshot 2026-09-08 at 15.34.33.png`
> **TARGET ARCHITECTURE · Observer ยังไม่เปิดใช้จริง (not yet production-enabled)**

**หลักการทั้งใบสรุปได้ประโยคเดียว** — DMS ส่ง **full snapshot** มาทุกครั้ง ไม่ใช่ CDC ดังนั้นต้อง**หา change เอาจากการเทียบ snapshot ปัจจุบันกับ snapshot ก่อนหน้า**

คือวิธี "คล้าย CDC โดยไม่มี CDC" ที่เคยคุยกันไว้ แต่ทำในระดับ production พร้อม gate และ rollback

---

## ทำไมต้องมีของชิ้นนี้

### รากของเรื่อง — CDC ไม่ได้รับอนุมัติ

**ต่อ DMS แบบ CDC ตรง ๆ ไม่ได้ เพราะเจ้าของฐานข้อมูลฝั่ง IT ไม่อนุมัติ** ต้องเปิดความสามารถที่ระดับ SQL Server ต้นทาง ซึ่งอยู่นอกอำนาจของทีมข้อมูล → [[Decisions]] D-20

**สถาปัตยกรรมทั้งใบนี้จึงเป็นผลของข้อจำกัดนั้น ไม่ใช่ทางที่เลือกเพราะดีกว่า** — ถ้าเปิด CDC ได้ ของครึ่งหนึ่งในผังนี้ไม่ต้องมี

| ถ้ามี CDC | ที่ต้องทำแทนเพราะไม่มี |
|---|---|
| DMS บอก INSERT/UPDATE/DELETE มาให้เลย | ต้องเทียบ snapshot สองรอบเอง (6A / 6B) |
| ส่งเฉพาะที่เปลี่ยน | ย้ายข้อมูลทั้งชุดทุกรอบ |
| ไม่ต้องเก็บของรอบก่อน | ต้องเปิด versioning + เก็บ snapshot ผูกกับ run (3 / 4) |
| ได้ลำดับการเปลี่ยนแปลง | **แถวที่ถูกแก้ 3 ครั้งระหว่างสองรอบ เห็นเป็นแก้ครั้งเดียว** |
| near-real-time | ละเอียดเท่าความถี่ที่รัน |

**ข้อที่ต้องบอกคนใช้ข้อมูลให้ชัด** — วิธีนี้ให้ **ผลลัพธ์สุดท้ายที่ถูกต้อง แต่ไม่ให้ประวัติระหว่างทาง** ใครที่ต้องการ audit trail ระดับ transaction จะไม่ได้จากเส้นนี้

### ช่องว่างที่ pipeline เดิมทิ้งไว้

| ปัญหาของ pipeline ปัจจุบัน | ผล |
|---|---|
| DMS เป็น **Full Load** ไม่ใช่ CDC | ไม่รู้ว่าแถวไหนเพิ่ม / แก้ / ลบ |
| Glue ทำ **Destructive Silver / Gold refresh** | เขียนทับทั้งชุด **ประวัติหายทุกรอบ** |
| Bronze เป็น **Mutable** | รอบใหม่ทับของเก่า ย้อนดูไม่ได้ |

**Observer จึงเกิดมาเพื่อสร้างสองอย่างที่ pipeline เดิมไม่มี — snapshot ที่ไม่ถูกทับ และ view ที่บอกว่าอะไรเปลี่ยน**

---

## ต้นทาง (ใช้ร่วมกันทั้งสองเส้น)

```
SQL Server ──► AWS DMS ──► Mutable Bronze S3 ──► EventBridge
Source tables  Full Load    Parquet landing      DMS completion event
Full snapshots At-least-once Versioning required  Two isolated targets
```

**สามคำที่ต้องอ่านให้ขาด**

| คำ | ความหมายจริง |
|---|---|
| **At-least-once** | event เดียวกันมาซ้ำได้ → ทุกอย่างปลายทางต้อง idempotent |
| **Versioning required** | Bronze ถูกทับได้ **observer จึงต้องล็อก VersionId ไว้** ถึงจะอ่านชุดเดิมได้ตลอดรอบ |
| **Two isolated targets** | event เดียวยิงเข้า **สองเส้นแยกกัน** — นี่คือกลไกที่ทำให้ observer พังแล้วไม่ลาก pipeline เดิมล่ม |

---

## เส้นเดิม — ไม่แตะ

> **Observer failures never block this path**

| ขั้น | ทำอะไร |
|---|---|
| DMS Step Functions | Wait for settlement · Route by dataset |
| **Existing Validator** | **DMS/table status · Parquet row reconciliation** |
| Existing Glue Jobs | Dimension ก่อน แล้วค่อย Fact · Destructive Silver/Gold refresh |
| Existing Outputs | Silver / Gold tables · behavior เดิม |
| Outcome | EventBridge / SNS · success หรือ failure |

**`Existing Validator` คือโค้ดตัวที่จดไว้แล้ว** → [[DMS Full Load Validation (Lambda)]]

"Wait for settlement" ของ Step Functions ตรงกับเหตุผลที่ validator ต้อง poll — **DMS รายงานสถานะช้ากว่า event** (วัดจริง 28 และ 44 วินาที)

---

## เส้นใหม่ — Isolated Observer

> **Immutable · Idempotent · Validation-gated · Committed-only visibility**

| # | ขั้น | สาระ |
|---|---|---|
| 1 | **Observer Coordinator** | Allowlist + settlement · **reuse existing validator** · **ไม่มีสิทธิ์สั่ง DMS** |
| 2 | **Claim Run** | run/bundle ID แบบ deterministic · DynamoDB conditional write · **event ซ้ำ → เข้า run เดิม** |
| 3 | **Version-pinned Copy** | จับ Bronze VersionIds · Distributed Map + Copy Worker · server-side copy SSE-KMS |
| 4 | **Immutable Snapshot** | S3 object ผูกกับ run · manifest + digest marker · **ข้อมูลที่ยังไม่ครบมองไม่เห็น** |
| 5 | **Validate / Profile** | object + footer + Spark rows · schema + exact key gates · **technical failure → quarantine** |
| 6A | **DIMENSION: Item / Branch** | พิสูจน์ candidate key · full outer keyed diff → INSERT/UPDATE/DELETE · SCD Type 1 current + append-only changes · **ห้าม dedupe หรือถอยไปใช้ multiset** |
| 6B | **FACT SALES: Exact Multiset** | encode 12 คอลัมน์แบบ typed canonical · SHA-256 + retained columns + `occurrence_count` · delta = current − previous → **INSERT/DELETE เท่านั้น** · เก็บ duplicate ไว้ · **ห้าม UPDATE** |
| 7 | **All Outputs PREPARED** | Iceberg/Parquet ผูกกับ run · **รอบแรกไม่มี change** |
| 8 | **Atomic Promotion** | DynamoDB expected-version transaction · bundle เป็น **all-old หรือ all-new เท่านั้น** |
| 9 | **Commit Registry** | `committed_runs` แบบ idempotent · เป็นสวิตช์การมองเห็น |
| 10 | **Committed Views** | Glue Catalog + Athena · **แถวที่ PREPARED ยังถูกซ่อน** |
| → | Analytics | อ่านได้เฉพาะที่ commit แล้ว |

### ทำไม Dimension กับ Fact ใช้คนละวิธี

**นี่คือจุดที่ออกแบบมาดีที่สุดในผังนี้**

| | Dimension (Item / Branch) | Fact (Sales) |
|---|---|---|
| มี key ไหม | **มี** พิสูจน์ candidate key ได้ | **ไม่มี** แถวเหมือนกันเป๊ะเกิดซ้ำได้จริง |
| วิธีเทียบ | full outer join บน key | **multiset** — SHA-256 ทั้งแถว + นับจำนวนครั้ง |
| ผลลัพธ์ | INSERT / UPDATE / DELETE | **INSERT / DELETE เท่านั้น** |

**ขายของชิ้นเดียวกัน สาขาเดียวกัน วินาทีเดียวกัน สองรายการ = ข้อมูลถูก ไม่ใช่ duplicate** จึงห้าม dedupe และห้าม UPDATE — ถ้า UPDATE ได้แปลว่าต้องระบุได้ว่าแถวไหน ซึ่งระบุไม่ได้ตั้งแต่ต้น

`occurrence_count` คือตัวที่ทำให้ "ขาย 3 ครั้งเหมือนกัน" ต่างจาก "ขาย 2 ครั้งเหมือนกัน" ได้

---

## สองประเภทความล้มเหลว ตั้งใจให้ต่างกัน

```
                    ┌─ technical failure ─► FAILED / QUARANTINED
Correctness &       │                       ไม่ promote · ห้ามอนุมัติข้าม
anomaly gates ──────┤
                    └─ anomaly only ──────► HOLD_FOR_APPROVAL
                                            อนุมัติ = เดินต่อจาก artifact เดิม
                                            ปฏิเสธ = คง baseline
```

| | technical failure | anomaly |
|---|---|---|
| หมายถึง | **ของพัง** — schema เพี้ยน · key ไม่ unique · นับไม่ตรง | **ของแปลก** — ยอดเปลี่ยนเยอะผิดปกติ แต่ไม่ผิดกติกา |
| คนอนุมัติข้ามได้ไหม | **ไม่ได้** fail closed | **ได้** แต่ถูกบันทึกไว้ |

**แยกสองอย่างนี้ออกจากกันคือหัวใจ** — ถ้ารวมเป็นถังเดียว สุดท้ายคนจะกดอนุมัติทุกอย่างจนกลไกไม่มีความหมาย

---

## กลไกที่ทำให้ปลอดภัย

| กลไก | กันอะไร |
|---|---|
| **Two isolated targets** | observer พัง ไม่กระทบ Silver/Gold ที่ธุรกิจใช้อยู่ |
| **No DMS control permission** | observer อ่านสถานะได้ **แต่สั่ง start/stop task ไม่ได้** |
| **Deterministic run ID + DynamoDB conditional write** | event ซ้ำจาก at-least-once ไม่สร้าง run ซ้ำ |
| **Version-pinned copy** | Bronze ถูกทับกลางรอบก็ยังอ่านชุดเดิมได้ |
| **PREPARED แยกจาก COMMITTED** | ข้อมูลครึ่ง ๆ กลาง ๆ ไม่มีทางถูกเห็น |
| **Atomic promotion แบบ bundle** | all-old หรือ all-new **ไม่มีสภาพผสม** |
| **รอบแรกไม่ emit change** | baseline run — **เห็น 0 change รอบแรกคือถูกแล้ว ไม่ต้องตกใจ** |

Replay / rollback รองรับ · สังเกตการณ์ผ่าน CloudWatch · SNS · EventBridge outcomes

---

## คำถามที่ควรถามทีม Data Engineering

| # | คำถาม | ทำไมถึงถาม |
|---|---|---|
| 1 | Observer เรียก validator ตัวเดิมด้วย argument ชุดไหน | ตอนนี้ validator มี 2 โหมด · **ถ้าเรียกแบบ gate จะเงียบไม่ส่งอีเมล** แต่ถ้าเรียกแบบ EventBridge จะได้อีเมลซ้ำสองใบต่อหนึ่ง load ซึ่งเป็นสิ่งที่ตั้งใจเลี่ยงไว้ |
| 2 | `is_pending` ของ validator ทำให้ observer ไม่เริ่มรอบไหม | DMS อัปเดตสถานะช้า = observer อาจข้ามรอบไปเงียบ ๆ · validator คืน `dataChecksPassed` มาให้ใช้แยกได้ |
| 3 | Bronze เปิด versioning แล้ว **มี lifecycle policy หรือยัง** | version เก่าคิดเงินเต็มราคาเหมือน object ปกติ ไม่มี policy = โตไปเรื่อย ๆ `[อนุมาน — ผังไม่ได้ระบุ]` |
| 4 | snapshot ที่ผูกกับ run เก็บไว้กี่รอบ | copy เต็มทุกรอบ · 30 TB lake จะโตเร็วมาก `[อนุมาน]` |
| 5 | schema เปลี่ยน (12 → 13 คอลัมน์) แล้วเทียบกับรอบก่อนยังไง | SHA-256 คำนวณจาก 12 คอลัมน์ **เพิ่มคอลัมน์ = hash เปลี่ยนทั้งตาราง** จะกลายเป็น delete ทั้งชุด insert ทั้งชุด · น่าจะถูกดักที่ schema gate แต่ควรยืนยันว่าดักจริงและ recover ยังไง |
| 6 | Item / Branch **พิสูจน์ candidate key จากอะไร** | ITEC เปิดให้เห็นแค่ 23 view ไม่มี table → ไม่มี PK ประกาศไว้ให้ใช้ → [[ITEC Overview]] |
| 7 | Fact 12 คอลัมน์ คือคอลัมน์ไหน | ITEC มีบรรทัดขาย **79.8M** · ต้องรู้ว่า 12 คอลัมน์นี้พอระบุความเป็นแถวได้จริงไหม |

---

## เชื่อมกับโน้ตอื่น

[[DMS Full Load Validation (Lambda)]] · [[Architecture]] · [[AWS Services]] · [[ITEC Overview]] · [[ETL & Spark]] · [[Decisions]] · [[Network & VPN]]
