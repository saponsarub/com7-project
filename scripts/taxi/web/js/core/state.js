/* js/core/state.js — สถานะของหน้าเว็บ (S) + คอลัมน์ข้อมูลจุดที่ใช้ร่วมกันทุกโมดูล
   ใช้: –
   ให้: S · D · N · NV · PROV · DIST · POS · TT · SPD · FLG · DI · VV · DUR · MASK · EXC · map · deckOverlay
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ══════════════════════════════════════════════════════════════════════
   สถานะ
   ══════════════════════════════════════════════════════════════════════ */
const S = {
  T: 0, a: 0, b: 0, playing: false, speed: 600,
  pt: 'now', trail: 30, choro: false, level: 'prov', metric: 'veh',
  centers: new Set(), status: new Set(['hired', 'vacant', 'park']),
  areas: new Set(),            // คีย์ 'p:<idx>' หรือ 'd:<idx>'
  sel: -1, zone: 'bkk', minDur: 10, sev: '', sortK: 'hrs', sortDir: -1, vehSort: 'km',
  exDepot: false, tab: 'ov', sSev: '', mly: false, noCar: false,
  ev: false,                   // ชั้นสถานีชาร์จ EV (OpenStreetMap)
  trk: 'all',                  // รถที่เลือก: 'all' = เส้นทางทั้งช่วง · 'live' = ถึงเวลาปัจจุบันของ timeline
};
let D, N, NV, PROV, DIST, distProv, t0ms;
let POS, TT, SPD, FLG, DI, VV, DUR;           // คอลัมน์จุด
let MASK, maskVer = 0;                        // ผ่านตัวกรองไหม (ไม่รวมเวลา)
let EXC = [], EXC_BY_V = new Map(), VSTAT = null;
let deckOverlay, map;
