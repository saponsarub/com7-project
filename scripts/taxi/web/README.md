# Smart Taxi Monitor (EV7) — web app

หน้าเว็บติดตามแท็กซี่ EV7 (UI ภาษาอังกฤษ · ผู้ช่วยตอบได้ทั้งไทย/อังกฤษ)
แผนที่ + timeline · Out of zone · Overnight parking / depots · Areas · Vehicles · **Fleet assistant (chat)**
โฟลเดอร์นี้คือ **source** — ไม่มีข้อมูลรถ ต้อง build ก่อนเปิด

## Build / เปิดใช้

```bash
# โฟลเดอร์ (dev / deploy) → ดับเบิลคลิก index.html ได้เลย หรือเสิร์ฟด้วย server/app.py
python scripts/taxi/build_dashboard.py --web D:\Taxi\dashboard_v3

# ไฟล์เดียว (ส่งต่อทางอีเมล/แชท) — รวม css/js/data/logo ลง HTML ไฟล์เดียว
python scripts/taxi/build_dashboard.py --bundle D:\Taxi\Taxi_dashboard_v3.html
```

- ต้องมี `scripts/taxi/_out/smarttaxi.parquet` (จาก `load_rpt.py`) และ geojson ใน `_out/`
- build ตรวจ syntax JS ทุกไฟล์ + ชื่อ `const/let` ซ้ำข้ามไฟล์ ด้วย node ก่อนเขียน — พังจะไม่เขียน
- `--web` ใส่ `?v=<hash>` ท้าย css/js ทุกไฟล์ (cache-busting) → deploy ใหม่แล้ว browser ไม่ใช้ไฟล์เก่าปน

## ทดสอบ

| URL | ผล |
|---|---|
| `index.html?selftest` | ตัวเลขวิเคราะห์ทั้งหมดลง `<pre id="st">` — ต้องตรงกับรุ่นก่อน (ต.ค. 2026: ตรงทุกค่า) |
| `index.html?asktest` | รันผู้ช่วยแบบ offline กับคำถามชุดเทรน ลง `<pre id="ask">` |
| `index.html?triptest` | สรุป trip ของรถ 40 คัน + ทดลอง replay ลง `<pre id="trip">` |
| `index.html?ask=EV chargers near Siam` | เปิดแชทพร้อมคำถาม (ลิงก์แชร์ได้) |
| `#panel=zone&zone=metro` · `#car=<id>` · `#plate=ทอ-9094` · `#bm=satellite` · `#view=3d` · `#zoom=th` · `#depot=0` | ลิงก์ตรงไปยังมุมมอง |

```bash
msedge --headless=new --virtual-time-budget=120000 --dump-dom "file:///D:/Taxi/dashboard_v3/index.html?selftest"
```

## โครงสร้าง

```
web/
├── index.html              layout + ลำดับโหลด script (classic scripts ใช้ scope ร่วมกัน — ลำดับสำคัญ)
├── css/  tokens · layout (grid: header · rail · side panel · map · timeline · chat) · components · map · chat
├── js/
│   ├── config.js           ค่าตั้งทั้งหมด (zone · เกณฑ์ · base map · AI endpoint) — override ได้ด้วย window.EV7_CONFIG
│   ├── core/               errors · utils · state (S + คอลัมน์ข้อมูลที่ใช้ร่วมกัน)
│   ├── data/               source (decode ข้อมูลแบบ parallel · จุดต่อ API) · model
│   ├── analysis/           filters · excursions (นอกเขต) · fleet (สถานะ ณ เวลา) · stays (จุดจอด · depot แบบ time-sliced)
│   ├── services/geocode.js Nominatim (1 req/s · cache ในเครื่อง · escape ทุกครั้ง)
│   ├── map/                map (MapLibre + deck.gl · 2D/3D) · layers (จุด · ลูกศรทิศทาง · เส้นทาง — ไม่มีรูปรถ) · interaction (tooltip/click)
│   ├── ui/                 shell (rail + panel) · actions (refresh/selection/keys/hash/CSV) · overview · vehicles · zone
│   │                       parking · areas · filters · search · mapcontrols · timeline · place · widgets · icons
│   ├── assistant/          nlu (intent + slot ไทย/อังกฤษ) · tools (ค้นข้อมูล + สั่งแผนที่) · agent (offline / AI) · chat (UI)
│   ├── dev/selftest.js     ?selftest · ?asktest
│   └── main.js             start-up — ต้องโหลดเป็นไฟล์สุดท้าย
├── assets/images/ev7logo.png
└── data/taxi-data.js       ⚠️ สร้างโดย build · มีทะเบียน/VIN/ตำแหน่ง · อยู่ใน .gitignore
```

## Start-up (ทำไมเร็วขึ้น)

1. แผนที่เริ่มวาดทันที ระหว่าง decode ข้อมูล (มี progress bar · decode ทุกคอลัมน์ parallel)
2. คำนวณเฉพาะที่หน้าแรกใช้ แล้วปิด loading — เปิดที่เวลาล่าสุดของข้อมูล ("now")
3. หา depot (ช้า — ทั้งช่วงข้อมูล) ทีหลังแบบแบ่งชิ้น ≤12 ms ไม่ทำให้หน้าค้าง · จุดจอดคำนวณเมื่อเปิดแผง Overnight เท่านั้น
4. วาดเฉพาะแผงที่เปิดอยู่ (แผงอื่น mark dirty) · ลาก timeline / play อัปเดตไม่เกิน 1 ครั้งต่อ frame

## Live / History · รถรายคัน

- **Live (ค่าเริ่มต้น)** — cursor อยู่ที่จุดล่าสุดของข้อมูล (ป้าย LIVE สีแดงที่ header/timeline) · รถที่ไม่มีสัญญาณล่าสุดแสดงเป็นวงกลวงสีเทา ณ ตำแหน่งสุดท้ายที่รู้ (ปิดได้ในปุ่ม Map)
- **History** — ลาก/คลิก timeline หรือกด ▶ = ดูย้อนหลัง · ปุ่ม "Go live" กลับมาที่ล่าสุด
- ป้าย LIVE / HISTORY / REPLAY มุมซ้ายบนของแผนที่ (มีปุ่ม Go live ตอนดูย้อนหลัง)
- ไม่มีรูปรถ: รถที่กำลังวิ่ง = ลูกศรบอกทิศ (สีตามสถานะ: ส้ม = มีผู้โดยสาร · เขียว = ว่าง · ขอบดำ / แดง = นอกเขต) · จอด = จุด · ขนาดตาม zoom — ต่ำกว่า ~zoom 10.5 เหลือจุดเล็ก · มุม 3D + ซูม ≥ 13 = รถแท็กซี่ 3D (low-poly สร้างในโค้ด `js/map/car3d.js` ไม่มีไฟล์โมเดล) หันหน้าไปทางที่วิ่ง
- ตอนเล่น/replay รถเคลื่อนลื่น: ตำแหน่งเติมเป็นเส้นตรงระหว่างจุด GPS 2 จุด (ห่าง ~4–5 นาที) — ยังไม่ snap ตามถนนจริง (ต้องทำ map matching)
- เส้นทางรถที่เลือก: ลูกศรเล็ก ~12 ตัวกระจายตามระยะทาง ไม่ทับตัวรถ · เลือกช่วงได้: ทั้งช่วงที่เลือก · ถึง cursor · ย้อนหลัง 1/3/6/12 ชม. · 1/2/3/7 วัน (เกินช่วงข้อมูลจะกดไม่ได้)
- คลิกรถบนแผนที่ → รถคันอื่นจางลง · เลือกจากรายการ/ค้นหาทะเบียน → แสดงเฉพาะคันนั้น (สลับได้ในการ์ด "Only this car / Others faded")
- การ์ดรถ: Trip = From (จุดจอดล่าสุด) → Now → Next stop
  - History: จุดจอดถัดไป**จากข้อมูลจริง** (B สีม่วง)
  - ปลายข้อมูล: **ประมาณ**จากจุดที่รถคันนี้เคยจอด ที่อยู่ในทิศที่กำลังวิ่ง (±40°, 0.8–60 กม.) แสดง "?" สีส้ม + ความมั่นใจ low/medium · มีผู้โดยสาร = บอกแค่ทิศ (ปลายทางเป็นของผู้โดยสาร)
  - เส้นทางไปจุดถัดไป/จุดหมายที่คาด = **เส้นประตามถนนจริง** จาก OSRM (`CFG2.ROUTER` · ค่าเริ่มต้น = OSRM demo server ใช้เบา ๆ ได้ — ใช้จริงควร self-host)
    ส่งแค่พิกัด 2 จุด ไม่มีทะเบียน/รหัสรถ · ถามเฉพาะรถที่เลือก ตอนไม่ได้เล่น · cache ต่อ ~100 ม. · แสดงระยะทางตามถนน + เวลาโดยประมาณ (ไม่รวมรถติด)
    ถ้าเรียกไม่ได้ = เส้นประตรง · รถที่เลือกมีลูกศรบอกทิศเสมอ (แม้จอด/ซูมออก)
  - เส้นทางที่วิ่งมาแล้วของรถที่เลือก **ตามถนนจริง**: route ผ่านจุด GPS ที่เคลื่อนที่ (ตัดจุดจอดที่ขยับ < 60 ม.) ทีละ 100 จุด/request
    (map matching ของ OSRM demo จำกัด 10 จุด/request — route ผ่าน waypoint ให้ผลเท่ากันสำหรับจุดห่าง 4–5 นาที)
    leg ที่ยาวเกิน 3 เท่าของระยะตรง + 1 กม. (snap ผิดถนน) ใช้เส้นตรงแทน · ช่วงสัญญาณขาดไม่ลากเส้น · ตอน replay รถคันที่เลือกเลื่อนไปตามถนน
  - รถคันอื่นตอนเล่น: เลื่อนลื่นเฉพาะเมื่อจุด GPS ถัดไปห่าง ≤ 400 ม. (`CFG.GLIDE_KM`) นอกนั้นอยู่ที่จุดล่าสุด (อยู่บนถนน) แล้วกระโดดไปจุดใหม่
    — ข้อมูลจริง: ระหว่าง 2 จุด (ห่าง ~5 นาที) รถวิ่งเฉลี่ย 1.3 กม. · เส้นตรงจึงตัดผ่านตึก ("รถบิน")
  - **ทุกคันวิ่งตามถนน** (เมื่อ build ตอนที่ GraphHopper รันอยู่): `roadsnap.py` route รถทุกคันผ่านจุด GPS ที่เคลื่อนที่
    บน GraphHopper ของเราเอง (localhost · ไม่มีข้อมูลออกนอกเครื่อง) → `data/taxi-roads.js` (~11 MB · โหลดเบื้องหลังหลังแผนที่ขึ้น)
    ต.ค. 2026: ตามถนน 370k / 397k ช่วง (93%) ใน ~90 วิ · ระหว่างเล่น 73–80% ของรถบนจอวางบนเส้นทางตามถนน · ทดสอบ `?roadtest`
    ไม่มีไฟล์นี้ (GraphHopper ไม่ได้รันตอน build) = รถกระโดดจุดต่อจุดแบบเดิม · รถที่เลือกใช้ OSRM สาธารณะแทน

### GraphHopper (ตัวคำนวณเส้นทาง — ไม่ต้องใช้ Docker / admin)

```bash
# ครั้งแรก: ดาวน์โหลด jar + แผนที่ถนนไทย (OpenStreetMap ~330 MB) ไว้ที่ D:\Taxi\graphhopper\ (นอก repo)
#   https://repo1.maven.org/maven2/com/graphhopper/graphhopper-web/11.1/graphhopper-web-11.1.jar
#   https://download.geofabrik.de/asia/thailand-latest.osm.pbf
cd D:\Taxi\graphhopper
java -Xmx4500m -jar graphhopper-web-11.1.jar server C:\Projects\my-first-project\scripts\taxi\graphhopper\config.yml
# ครั้งแรก import ~3.5 นาที (graph-cache\ ~0.5 GB) · ครั้งต่อไปเปิดได้ทันที · ฟังเฉพาะ 127.0.0.1:8989
# แล้วค่อยรัน build_dashboard.py ตามปกติ — เจอ GraphHopper เองอัตโนมัติ
```
ต้องการ Java 17+ · RAM ~3–4 GB ตอนรัน · อัปเดตแผนที่ = โหลด .pbf ใหม่ ลบ graph-cache\ แล้วเปิดใหม่
  - ตอนเล่น แผนที่**ตามรถที่เลือก** (เลื่อนเข้าหารถทีละนิดทุกเฟรมเมื่อรถออกจากกลางจอ) · ลากแผนที่เอง = หยุดตาม · ปุ่ม "Follow car" บนป้ายมุมซ้ายบน = กลับมาตาม · ทดสอบ `?followtest`
  - "Replay this trip" ย้อนไปตอนออกจากจุดจอดแล้วเล่น เส้นทางงอกตามรถ แผนที่เลื่อนตามเมื่อรถออกนอกจอ
- ทดสอบ: `index.html?triptest`

## Live update · timeline

- เปิดมาเป็น **Live** — ไม่มีแถบ timeline (แผนที่เต็มจอ) · ปุ่ม **History** บนป้าย LIVE เปิด timeline เพื่อดูย้อนหลัง/เล่นซ้ำ · ✕ หรือ Go live = กลับ Live และซ่อน timeline
- เมื่อเสิร์ฟผ่าน http (server/app.py): หน้าเว็บเช็ก `data/taxi-data.js` ทุก `CFG.REFRESH_SEC` (60 วิ) ถ้า ETag/Last-Modified เปลี่ยน → โหลดใหม่เอง
  คงมุมมองไว้ (รถที่เลือกจับด้วย VIN · Live กระโดดไปเวลาล่าสุด · History อยู่เวลาเดิม) · ให้ฝั่ง server รัน build ตามรอบ (เช่นทุก 5 นาที) เขียนไฟล์นี้ใหม่
- เปิดจาก file:// หรือไฟล์เดียว = snapshot คงที่ (ข้อมูลทดสอบจะนิ่ง) · ทดสอบเส้นทางโหลดใหม่: `index.html?refreshtest`

## Live test — จำลอง live จากชั่วโมงสุดท้าย (livetest.js)

- ปุ่ม Map → Live test (หรือ `?livetest` · `?livetest=60` = เร็ว ×60): ซ่อน 1 ชม. สุดท้าย แล้วปล่อยเข้ามาตามนาฬิกาจริง (×1 · ×10 · ×60)
- ขอบข้อมูล = `D.meta.tmax` → ทุกฟังก์ชันเห็นแค่ข้อมูลที่ "มาถึงแล้ว" (รถไม่เลื่อนไปหาจุดที่ยังไม่มา · จุดจอด/ทำนาย cache ล้างทุกครั้ง)
- ทุก 15 นาทีของข้อมูล บันทึกคำทำนายของรถที่กำลังวิ่ง → เทียบของจริงเมื่อข้อมูลมาถึง: ตำแหน่งอีก 15 นาที (3 วิธี) · ทิศ ±45° · ถึงจุดหมาย ≤ 500 ม. → การ์ดใน Overview + CSV
- ข้อยกเว้น: ลานจอด (depot) คำนวณจากข้อมูลทั้งชุดก่อนเริ่ม (เป็นสถานที่คงที่)
- ข้อมูลต้นทางเก็บตำแหน่ง**ทุกคันพร้อมกันทุก 5 นาที** (เวลา :x4:30 / :x9:30 · ~3,500 คันต่อรอบ · นาทีอื่นแทบไม่มี) → ใน live ทั้งฝูงได้ตำแหน่งใหม่พร้อมกัน
  `js/ui/liveclock.js`: **Live เดินตามนาฬิกาจริง** ช้ากว่าข้อมูลล่าสุด `CFG.LIVE_LAG_SEC` (5 นาที = 1 รอบข้อมูล) — รถทุกคันอยู่ระหว่าง 2 จุดที่มาถึงแล้วเสมอ จึงวิ่งตามถนนต่อเนื่อง ไม่หยุดรอรอบ ไม่เดาล่วงหน้า · ตามทันข้อมูลแล้ว = นาฬิกาหยุดรอ ป้ายบอก "Waiting for new data" (server) / "Snapshot · no newer data" + ปุ่ม Replay last hour (file://) · ทดสอบ `?clocktest`
- **Clear all** (หัวเว็บ ข้างปุ่ม Ask · มีตัวเลขบอกจำนวน · มือถือเป็นไอคอน): กลับไปเหมือนเพิ่งเปิดหน้า — ตัวกรองทุกที่ (center/status/area · ระดับใน Zone · ที่จอดใน Parking · ช่องค้นทะเบียน) · รถที่เลือก · ช่วงเวลา/History → Live · ไฮไลต์จากผู้ช่วย · **แชทผู้ช่วย (รวมประวัติที่ส่ง AI)** — ค่าตั้ง (เขตที่อนุญาต · ความยาวทริป · แผนที่ฐาน · 2D/3D) คงเดิม · ผู้ช่วยตอบเรื่องภาพรวม/พื้นที่ = ปล่อยรถที่เลือกจากคำถามก่อนเอง · Live: Follow car เริ่มปิด (ลากแผนที่ = หยุดตาม) · ทดสอบ `?cleartest`

## จอดจริงไหม · จอดที่ไหน · ตัดไฟได้ไหม (parkstate.js)

ตอนนี้เป็น **rule-based** (ยังไม่มีข้อมูลที่มีเฉลยไว้เทรน ML):
- **จอดจริง** = อยู่ในรัศมี 150 ม. ความเร็ว < 5 ติดกัน ≥ 10 นาที (สั้นกว่า = หยุดชั่วคราว รถติด/รับส่ง) + ธง engine จาก API (0 ทำงาน · 1 ดับ · 2 ไม่ทราบ)
- **ที่ไหน**: สถานีชาร์จ EV (≤ 80 ม. จากจุด OSM — OSM มีไม่ครบ) · ลานจอด (depot) · **บ้าน** = จุดที่รถคันนี้เคยจอดค้างคืน (≤ 200 ม.) · ริมถนน/อื่น ๆ
- **บนถนน / นอกถนน** (build: `roads.py`): ระยะจากจุดที่รถนิ่งถึง "ขอบถนน" (ระยะถึงเส้นกลาง − ครึ่งความกว้างตามประเภทถนน) จาก vector tiles ของ OpenFreeMap (OSM) ซูม 14 · cache ที่ `_out/roads_z14/`
  - normalize: พิกัดหลายจุดมีแค่ทศนิยม 4 ตำแหน่ง (±5.5 ม.) + GPS คลาด 5–15 ม. → ใช้ **มัธยฐาน** ของทุกจุดช่วงที่นิ่ง และเผื่อ ±12 / 10 / 8 ม. (1 · 2–4 · ≥5 จุด)
  - ≤ ระยะเผื่อ = บนถนน · ≥ ระยะเผื่อ + 12 ม. = นอกถนน · ระหว่างนั้น = ขอบถนน (ไม่แน่ใจ — ไม่นับเป็นนอกถนน)
  - ไม่นับ service road (ทางในลานจอด/ทางเข้าบ้าน) และสะพาน/อุโมงค์ (ใต้ทางด่วนมักเป็นลานจอด)
- **2 แบบ** (สลับได้ในการ์ดรถและแผง Parking): **Basic** = จอดหรือเครื่องดับ ≥ 10 นาที · **Off-road** (ค่าเริ่มต้น) = Basic + ต้องอยู่นอกถนน
- **ตัดไฟปลอดภัยไหม** (decision support — หน้าเว็บไม่ส่งคำสั่ง): ไม่ปลอดภัยถ้า วิ่งอยู่ · หยุด < 15 นาที · มีผู้โดยสาร · เครื่องยังทำงาน · GPS เก่า > 15 นาที/ไม่มี fix
  ข้อควรระวัง: จอดที่ชาร์จ (บังช่องชาร์จ) · เครื่องไม่รายงานว่าดับ · จอดริมถนน
- แสดงในการ์ดรถ · แผง Parking (นับตามประเภทที่จอด + จำนวนที่ตัดไฟได้) · ผู้ช่วย (ขอให้ตัดไฟ → ปฏิเสธ แต่บอกผลตรวจของคันนั้น)
- ต่อยอดเป็น ML: เก็บเฉลย (ที่อยู่บ้านที่ยืนยันแล้ว · log การชาร์จจากผู้ให้บริการ · ผลการตัดไฟจริง) แล้วเทรน classifier (เช่น gradient boosting)
  ด้วย feature เดิม: ระยะเวลาจอด · ช่วงเวลา · ธง engine · ระยะถึงที่ชาร์จ/depot/จุดค้างคืน · จำนวนคืนที่เคยจอด · ต้องมีข้อมูลหลายสัปดาห์

## Fleet assistant

- **Offline (ค่าเริ่มต้น)** — rule-based ในเบราว์เซอร์ ไม่มีข้อมูลออกนอกหน้า · intent เดียวกับโมเดลที่เทรนใน `scripts/taxi/qa/taxi_qa_local.ipynb`
  (cars_in_area · car_status · car_track · out_of_zone · fleet_stats · nearest_charger · action_request (ปฏิเสธ) · other + peak_time · data_info)
  ทดสอบกับ template ชุดเทรน 2,675 คำถาม: intent ถูก 99.6% · HAND set 32/32
- **AI agent** — เมื่อเปิดผ่าน `server/app.py` ที่ตั้ง `ANTHROPIC_API_KEY` หน้าเว็บเจอ `/api/health` แล้วสลับเป็น AI เอง (badge "AI agent")
  - server เป็น proxy stateless ถือแค่ key · Claude ขอ tool → **tool รันในเบราว์เซอร์** บนข้อมูลในหน้า → ส่งผลกลับ
  - ทะเบียนในคำถามถูกแทนด้วย `[[car:<id>]]` ก่อนส่ง · ผล tool อ้างรถเป็น `car:<id>` เท่านั้น → ทะเบียน/ตำแหน่งดิบไม่ออกจากเครื่อง
  - คำตอบที่มี `[[car:<id>]]` แสดงเป็นปุ่มทะเบียน คลิกแล้วเลือกรถบนแผนที่
  - server ล่ม/ตอบช้า → ตอบแบบ offline แทนพร้อมหมายเหตุ
- ผู้ช่วย **สั่งหน้าเว็บได้**: highlight รถ · วาดเส้นทาง · เลื่อน timeline · เปิดแผง · แสดงสถานีชาร์จ (ถาม "ที่ชาร์จใกล้…" แล้วขึ้นบนแผนที่พร้อมเลข)
- สั่งการรถ (ตัดไฟ/ล็อก/ดับเครื่อง/ส่งข้อความ) **ไม่ได้** — ตอบปฏิเสธเสมอ

## Deploy

ดู `scripts/taxi/server/` — FastAPI เสิร์ฟโฟลเดอร์ที่ build + `/api/health` + `/api/agent`

```bash
pip install -r scripts/taxi/server/requirements.txt
set WEB_DIR=D:\Taxi\dashboard_v3
set EV7_USER=ops & set EV7_PASS=<รหัส>          # basic auth ทั้งเว็บ — ควรเปิดเสมอ (ข้อมูลมี PII)
set ANTHROPIC_API_KEY=<key>                       # ไม่ใส่ = ผู้ช่วยแบบ offline
uvicorn app:app --app-dir scripts/taxi/server --port 8080
```

Docker: `scripts/taxi/server/Dockerfile` — ไม่ bake ข้อมูลลง image · mount โฟลเดอร์ build ตอน run (`-v …:/web:ro`)
ตัวเลือก env: `EV7_MODEL` (default `claude-opus-5-5`) · `EV7_EFFORT` (default `low`) · `EV7_MAX_TOKENS`

⚠️ ข้อมูลมีทะเบียน/VIN/ตำแหน่ง → วางหลัง VPN/SSO หรืออย่างน้อย basic auth + HTTPS · อย่าเปิด public

## ความปลอดภัย

- **ห้ามใส่ credential ฐานข้อมูล / API key ในไฟล์หน้าเว็บ** — key อยู่ใน env ของ server เท่านั้น
- ข้อความจากภายนอก (ที่อยู่ OSM · ชื่อสถานีชาร์จ · คำตอบ AI) ผ่าน `esc()` ทุกครั้งก่อนลง HTML
- Nominatim: ไม่เกิน 1 ครั้ง/วินาที ดึงเฉพาะจุดที่คลิก (ที่อยู่ depot ฝังมาตอน build) · โดน 429/403 พัก 10 นาที
- ไฟล์ที่ build ออกมามีข้อมูลรถ — ส่งเฉพาะคนที่ควรเห็น · ห้าม commit
- ห้ามใช้ `tile.openstreetmap.org` ตรง ๆ (บล็อก file://) — ใช้ OpenFreeMap / Esri

## ต่อฐานข้อมูล / API (ยังไม่ทำ)

จุดต่อที่ `js/data/source.js` (`DataSource`) — ตอนนี้อ่าน `window.TAXI_DATA`
ทำ API ฝั่ง server ส่งข้อมูลรูปแบบเดียวกับ `build_dashboard.make_payload()` แล้วให้ `DataSource` เรียกแทน
