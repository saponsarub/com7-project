/* js/map/cars.js — รูปรถ (EV7 หรือรูปมุมบนที่วาดเอง) — แสดงเฉพาะตอนเอียงแผนที่ 3D
   ใช้: layers.js
   ให้: useCarIcons() · carLayers() · onViewCars()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ── รูปรถ ─────────────────────────────────────────────────────────────
   วาดรูปรถมุมบนลง canvas ครั้งเดียว 4 สี (ตามสถานะ) แล้วใช้เป็น icon atlas
   billboard:false = รูปรถนอนราบบนพื้นและหมุนตามทิศจริง (เอียง 3D แล้วยังถูก)  */
let CAR_ATLAS = null;
const CAR_MAP = {};
function buildCarAtlas() {
  const W = 64, keys = ['hired', 'vacant', 'park', 'nosig'];
  const cv = document.createElement('canvas'); cv.width = W * keys.length; cv.height = W;
  const c = cv.getContext('2d');
  const rr = (x, y, w, h, r) => { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); };
  const quad = (pts) => { c.beginPath(); c.moveTo(pts[0], pts[1]); for (let k = 2; k < pts.length; k += 2) c.lineTo(pts[k], pts[k + 1]); c.closePath(); c.fill(); };
  keys.forEach((k, n) => {
    const col = COL[k];
    c.save(); c.translate(n * W + W / 2, W / 2);                 // หน้ารถชี้ขึ้น (ทิศเหนือ)
    c.shadowColor = 'rgba(16,35,26,.35)'; c.shadowBlur = 4; c.shadowOffsetY = 1;
    c.fillStyle = '#ffffff'; rr(-14, -28, 28, 56, 10); c.fill();  // ขอบขาว
    c.shadowColor = 'transparent';
    c.fillStyle = `rgb(${col})`; rr(-12, -26, 24, 52, 8); c.fill();
    c.fillStyle = 'rgba(16,35,26,.78)';
    quad([-9, -13, 9, -13, 7, -5, -7, -5]);                       // กระจกหน้า
    quad([-7, 13, 7, 13, 8.5, 19, -8.5, 19]);                     // กระจกหลัง
    c.fillStyle = 'rgba(16,35,26,.35)'; quad([-11, -4, -9, -3, -9, 11, -11, 12]); quad([11, -4, 9, -3, 9, 11, 11, 12]);
    c.fillStyle = '#ffffff'; rr(-4, 0, 8, 5, 1.5); c.fill();      // ไฟหลังคา TAXI
    c.fillStyle = '#fff6c8'; rr(-10, -26, 5, 3, 1); c.fill(); rr(5, -26, 5, 3, 1); c.fill();   // ไฟหน้า
    c.restore();
    CAR_MAP[k] = { x: n * W, y: 0, width: W, height: W, anchorX: W / 2, anchorY: W / 2 };
  });
  CAR_ATLAS = cv.toDataURL('image/png');
}
// กติกา (ตามที่ขอ 2026-10-02): รูปรถเฉพาะตอนเอียงแผนที่ (3D) · มุมตรงเป็นจุดเสมอ
function useCarIcons() {
  return !S.noCar && !!map && map.getPitch() > 5;
}
function carLayers() {
  const img = EMBEDDED && EMBEDDED.car;
  if (img) return ev7Layers(img);
  if (!CAR_ATLAS) buildCarAtlas();
  const H = D.cols.head;                                          // ทิศหน้ารถ 0–255 = 0–360°
  return [
    new deck.ScatterplotLayer({                                   // วงแดง = อยู่นอกเขต
      id: 'now-ring', data: NOW.filter(d => d.out), radiusUnits: 'pixels', getRadius: 12,
      stroked: true, filled: true, getFillColor: [217, 58, 64, 40], getLineColor: [217, 58, 64, 255], lineWidthUnits: 'pixels', getLineWidth: 2.5,
      getPosition: d => [POS[2 * d.i], POS[2 * d.i + 1]], updateTriggers: { getPosition: S.T },
    }),
    new deck.IconLayer({
      id: 'now-car', data: NOW, pickable: true, iconAtlas: CAR_ATLAS, iconMapping: CAR_MAP,   // ⚠️ id ต้องไม่ซ้ำกับชั้นจุด 'now'
      getIcon: d => d.st, sizeUnits: 'pixels', getSize: d => d.v === S.sel ? 32 : 20, billboard: false,
      getPosition: d => [POS[2 * d.i], POS[2 * d.i + 1]],
      getAngle: d => H ? -(H[d.i] * 360 / 256) : 0,                // deck หมุนทวนเข็ม · ทิศรถตามเข็ม
      updateTriggers: { getPosition: S.T, getIcon: S.T, getAngle: S.T, getSize: S.sel },
    }),
  ];
}
/* รูปรถ EV7 (D:\Taxi\ev7.png ฝังตอนสร้างไฟล์)
   รูปเป็นมุมเฉียงด้านหน้า หันซ้าย — หมุนตามทิศไม่ได้ จึงตั้งตรงเสมอ (billboard)
   แล้วใช้ภาพกลับด้านเมื่อรถวิ่งไปทางตะวันออก (ทิศ 0–180°) ให้หน้ารถชี้ไปทางที่วิ่ง
   สถานะดูจากวงสีใต้ล้อ (รูปรถเป็นสีขาวเหมือนกันทุกคัน)                         */
function ev7Layers(img) {
  const H = D.cols.head;
  const map_ = {
    L: { x: 0, y: 0, width: img.w, height: img.h, anchorX: img.w / 2, anchorY: img.h * 0.92 },
    R: { x: img.w, y: 0, width: img.w, height: img.h, anchorX: img.w / 2, anchorY: img.h * 0.92 },
  };
  const east = d => { const deg = H ? H[d.i] * 360 / 256 : 270; return deg > 0 && deg < 180; };
  return [
    new deck.ScatterplotLayer({
      id: 'now-ring', data: NOW, radiusUnits: 'pixels',
      getRadius: d => d.v === S.sel ? 10 : 6.5, stroked: true, filled: true, lineWidthUnits: 'pixels',
      getFillColor: d => rgba(COL[d.st], 210),
      getLineColor: d => d.out ? [217, 58, 64, 255] : [255, 255, 255, 230],
      getLineWidth: d => d.out ? 2.2 : 1.2,
      getPosition: d => [POS[2 * d.i], POS[2 * d.i + 1]],
      updateTriggers: { getPosition: S.T, getFillColor: S.T, getLineColor: S.T, getLineWidth: S.T, getRadius: S.sel },
    }),
    new deck.IconLayer({
      id: 'now-car', data: NOW, pickable: true, iconAtlas: img.url, iconMapping: map_,
      getIcon: d => east(d) ? 'R' : 'L', billboard: true, sizeUnits: 'pixels',
      getSize: d => d.v === S.sel ? 34 : 20,                     // ความสูงของรูป (กว้างตามสัดส่วน)
      getPosition: d => [POS[2 * d.i], POS[2 * d.i + 1]],
      updateTriggers: { getPosition: S.T, getIcon: S.T, getSize: S.sel },
    }),
  ];
}
let lastCar = null;
function onViewCars() {                                           // วาดใหม่เฉพาะตอนข้ามเส้น เอียง↔ตรง
  const u = useCarIcons();
  if (u !== lastCar) { lastCar = u; render(); }
}
