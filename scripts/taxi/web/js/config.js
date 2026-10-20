/* js/config.js — ค่าตั้งทั้งหมดของหน้าเว็บ — ปรับพฤติกรรมที่นี่ที่เดียว
   ใช้: –
   ให้: CFG · COL · RAMP · SAT_STYLE · FALLBACK_STYLE · CFG2 · OSM_STYLE
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ══════════════════════════════════════════════════════════════════════
   ค่าตั้ง
   ══════════════════════════════════════════════════════════════════════ */
const CFG = {
  STALE_MIN: 15,          // จุดล่าสุดเก่ากว่านี้ = ไม่ออนไลน์ ณ เวลานั้น
  GAP_MIN: 30,            // ช่องว่างระหว่างจุดเกินนี้ = ตัดเป็นคนละช่วง
  MOVING_KMH: 5,          // เร็วกว่านี้ = กำลังวิ่ง
  BKK_CENTER: [100.5018, 13.7563],
  CENTER_NAMES: { '0a': 'ศูนย์ 0a', 'yF': 'ศูนย์ yF', 'ux': 'ศูนย์ ux' },  // ⚠️ ยังไม่ทราบชื่อจริง
  ZONES: {
    bkk:     { prov: ['TH10'], dist: [] },
    bkk_air: { prov: ['TH10'], dist: ['TH1103'] },           // TH1103 อ.บางพลี = สุวรรณภูมิ (TH1102 คือบางบ่อ)
    metro:   { prov: ['TH10', 'TH11', 'TH12', 'TH13', 'TH73', 'TH74'], dist: [] },
  },
  METRO: ['TH11', 'TH12', 'TH13', 'TH73', 'TH74'],           // ปริมณฑล
  BASEMAP: 'https://tiles.openfreemap.org/styles/positron',
};
const COL = {
  hired: [13, 147, 214], vacant: [0, 163, 50], park: [138, 151, 166], nosig: [194, 201, 209],
  red: [217, 58, 64], blue: [13, 147, 214],
};
const RAMP = ['#e3f4e8', '#b9e3c5', '#86cf9b', '#4fb56f', '#1f9148', '#0b6e30', '#00491c'];
/* ══════════════════════════════════════════════════════════════════════
   แผนที่
   ══════════════════════════════════════════════════════════════════════ */
const SAT_STYLE = {
  version: 8,
  sources: { sat: { type: 'raster', tileSize: 256, attribution: 'Esri World Imagery',
    tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'] } },
  layers: [{ id: 'sat', type: 'raster', source: 'sat' }],
};
// ⚠️ ห้ามใช้ tile.openstreetmap.org ตรง ๆ — ไฟล์ที่เปิดจากเครื่อง (file://) ไม่มี Referer
//    เซิร์ฟเวอร์ OSM จะส่งภาพ "403 Access blocked" มาแทนแผนที่ (นโยบาย osm.wiki/Blocked)
const FALLBACK_STYLE = {
  version: 8,
  sources: { esri: { type: 'raster', tileSize: 256, attribution: 'Esri, HERE, Garmin, © OpenStreetMap contributors',
    tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}'] } },
  layers: [{ id: 'esri', type: 'raster', source: 'esri', paint: { 'raster-saturation': -0.6 } }],
};
/* ── จุดจอด · ลานจอด · บริการแผนที่ภายนอก ─────────────────────────── */
const CFG2 = {
  STAY_R_KM: 0.2,       // อยู่ในรัศมีนี้ = จอดที่เดิม
  STAY_MIN: 30,         // จอดนานกว่านี้ (นาที) = จุดจอด
  NIGHT_H: [0, 5],      // ช่วงค้างคืน 00:00–05:00
  NIGHT_MIN_H: 1,       // ทับช่วงค้างคืนอย่างน้อย (ชม.)
  DEPOT_R_KM: 0.2,      // จุดค้างคืนห่างกันไม่เกินนี้ = ที่เดียวกัน
  DEPOT_MIN: 5,         // ค้างคืนรวมกันกี่คันขึ้นไป = ลานจอด
  DEPOT_NEAR_KM: 0.3,   // จุดที่อยู่ใกล้ลานจอดเท่านี้ = อยู่ในลานจอด
  NOMINATIM: 'https://nominatim.openstreetmap.org/reverse',
};
// ปุ่ม "OSM" = ข้อมูล OpenStreetMap สไตล์ Liberty จาก OpenFreeMap (ฟรี · ไม่ต้องมี key/Referer)
// ไม่ใช้ tile.openstreetmap.org เพราะบล็อกไฟล์ที่เปิดจากเครื่อง — ดูคอมเมนต์ที่ FALLBACK_STYLE
const OSM_STYLE = 'https://tiles.openfreemap.org/styles/liberty';
