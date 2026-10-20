# Smart Taxi Monitor (EV7) — หน้าเว็บ

หน้าเว็บติดตามตำแหน่งแท็กซี่ EV7 ที่ทำสัญญา (timeline · ออกนอกเขต · จุดจอด/ลานจอด · ที่อยู่ OSM · ภาพถนน)
โฟลเดอร์นี้คือ **ต้นฉบับ** — ข้อมูลรถไม่อยู่ในนี้ ต้อง build ก่อนเปิด

## Build / เปิดใช้

```bash
# โฟลเดอร์ (ไว้พัฒนา/เปิดในเครื่อง) → เปิด D:\Taxi\dashboard\index.html ได้เลย (ดับเบิลคลิก)
python scripts/taxi/build_dashboard.py --web D:\Taxi\dashboard

# ไฟล์เดียว (ไว้ส่งต่อทางอีเมล/แชท) — รวม css/js/ข้อมูล/โลโก้ลง HTML ไฟล์เดียว
python scripts/taxi/build_dashboard.py --bundle D:\Taxi\Taxi_dashboard_v2.html

# ทำทั้งสองอย่างพร้อมกันได้
python scripts/taxi/build_dashboard.py --web D:\Taxi\dashboard --bundle D:\Taxi\Taxi_dashboard_v2.html
```

ก่อน build ต้องมี `scripts/taxi/_out/smarttaxi.parquet` (จาก `load_rpt.py`) และ geojson ใน `_out/`
build จะตรวจ syntax JS ทุกไฟล์ด้วย node ก่อนเขียน — ถ้าพังจะไม่เขียนไฟล์

ทั้งสองแบบมาจากต้นฉบับชุดเดียวกัน ทำงานเหมือนกันทุกอย่าง (ทดสอบด้วย `?selftest` ได้ตัวเลขตรงกัน)

## โครงสร้าง

```
web/
├── index.html              โครงหน้า + ลำดับโหลดสคริปต์
├── css/
│   ├── tokens.css          สี · ฟอนต์ · ค่าพื้นฐาน (แก้ธีมที่นี่)
│   ├── layout.css          header · sidebar · แผนที่ · ไทม์ไลน์ · responsive
│   ├── components.css      ตัวกรอง · แท็บ · การ์ด · ตาราง · ตั้งค่า
│   └── map.css             สิ่งที่ลอยบนแผนที่ · tooltip · การ์ดสถานที่ · กล่อง error
├── js/
│   ├── config.js           ค่าตั้งทั้งหมด (เขต · เกณฑ์ · แผนที่ฐาน)
│   ├── core/               errors · utils · state (S และคอลัมน์ข้อมูลที่ใช้ร่วมกัน)
│   ├── data/               source (โหลด/ถอดข้อมูล · จุดต่อ API) · model
│   ├── analysis/           filters · excursions (นอกเขต) · fleet (สถานะ ณ เวลา) · stays (จุดจอด/ลานจอด)
│   ├── services/           geocode (Nominatim) · mapillary (ภาพถนน)
│   ├── map/                map (MapLibre + deck.gl · 3D) · layers · cars (รูปรถใน 3D) · interaction
│   ├── ui/                 timeline · panels · place · controls
│   ├── dev/selftest.js     ทดสอบอัตโนมัติ (?selftest · #test=car|tilt|wheel)
│   └── main.js             จุดเริ่ม — ต้องโหลดเป็นไฟล์สุดท้าย
├── assets/images/ev7logo.png
└── data/taxi-data.js       ⚠️ สร้างโดย build · มีทะเบียน/VIN/ตำแหน่ง · อยู่ใน .gitignore
```

แต่ละไฟล์ JS มีหัวไฟล์บอก หน้าที่ · ใช้อะไร · ให้อะไร

## ทำไมไม่ใช้ ES modules / fetch JSON

ต้องเปิด `index.html` จากเครื่อง (file://) ได้ตรง ๆ ซึ่งเบราว์เซอร์บล็อก:
- `<script type="module">` จาก file:// → ใช้ classic script ใช้ scope ร่วมกัน **ลำดับใน index.html สำคัญ**
- `fetch('data.json')` ในเครื่อง → ข้อมูลเป็น `data/taxi-data.js` ที่ตั้ง `window.TAXI_DATA`
- รูปในเครื่องเข้า WebGL ไม่ได้ (tainted canvas) → รูปรถ EV7 ฝังเป็น base64 ในข้อมูล

ถ้าวันหนึ่งเสิร์ฟผ่าน web server (http) ค่อยเปลี่ยนเป็น ES modules + Vite ได้

## ต่อฐานข้อมูล / API (ยังไม่ทำ)

จุดต่ออยู่ที่ `js/data/source.js` (`DataSource`) — ตอนนี้อ่าน `window.TAXI_DATA`
แนวทาง: ทำ API ฝั่ง server (ถือ credential เอง) ส่งข้อมูลรูปแบบเดียวกับ payload ของ `build_dashboard.make_payload()`
แล้วให้ `DataSource` เรียก API นั้นแทน — ส่วนอื่นของหน้าไม่ต้องแก้

## ความปลอดภัย

- **ห้ามใส่ credential ฐานข้อมูล / API key ในไฟล์หน้าเว็บ** — ทุกอย่างในหน้าเว็บผู้ใช้เปิดอ่านได้
- Mapillary token ใส่ผ่านปุ่ม ⚙ เท่านั้น เก็บใน localStorage ของเครื่องผู้ใช้ ไม่อยู่ในไฟล์
- Nominatim: จำกัด 1 ครั้ง/วินาที ไม่ดึงอัตโนมัติ (ที่อยู่ลานจอดฝังมาตอน build) · โดน 429/403 พัก 10 นาที
- ไฟล์ที่ build ออกมามีข้อมูลรถ (ทะเบียน · VIN · ตำแหน่ง) — ส่งเฉพาะคนที่ควรเห็น · ห้าม commit
- ห้ามใช้ `tile.openstreetmap.org` ตรง ๆ (บล็อก file://) — ใช้ OpenFreeMap / Esri
