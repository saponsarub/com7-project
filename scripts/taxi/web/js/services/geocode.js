/* js/services/geocode.js — แปลงพิกัดเป็นที่อยู่ — OpenStreetMap Nominatim (1 ครั้ง/วินาที · จำผลในเครื่อง)
   ใช้: utils.js (store)
   ให้: PLACES · Geo · fmtAddr() · updGeoQ()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ── ที่อยู่จาก OpenStreetMap (Nominatim) ──────────────────────────────
   กติกาของ Nominatim: ไม่เกิน 1 ครั้ง/วินาที · ห้ามยิงเป็นชุดใหญ่
   จึงดึงเฉพาะจุดที่ผู้ใช้กดดู + ลานจอดไม่กี่สิบแห่ง แล้วจำผลไว้ในเครื่อง        */
// ที่อยู่ลานจอดดึงไว้ตอนสร้างไฟล์ (build_dashboard.py) — เปิดไฟล์แล้วไม่ต้องเรียก OSM
const PLACES = (EMBEDDED && EMBEDDED.places) || [];
const GEO_BLOCK = 'OpenStreetMap จำกัดการใช้งานชั่วคราว (เกิน 1 ครั้ง/วินาที จาก IP นี้) — ลองใหม่ในอีกสักครู่ หรือกดลิงก์ Google Maps แทน';
const Geo = {
  cache: {}, q: [], busy: false, wait: {}, done: 0, blockedUntil: 0,
  init() { try { this.cache = JSON.parse(store.get('ev7.geo', '{}')) || {}; } catch (e) { this.cache = {}; } },
  save() { store.set('ev7.geo', JSON.stringify(this.cache)); },
  key(lat, lon) { return lat.toFixed(4) + ',' + lon.toFixed(4); },
  peek(lat, lon) {
    const c = this.cache[this.key(lat, lon)]; if (c) return c;
    for (const p of PLACES) if (hav(lon, lat, p.lon, p.lat) <= 0.05) return p;
    return null;
  },
  get(lat, lon) {
    const k = this.key(lat, lon), have = this.peek(lat, lon);
    if (have) return Promise.resolve(have);
    if (Date.now() < this.blockedUntil) return Promise.resolve({ err: true, line: GEO_BLOCK });
    if (!this.wait[k]) { this.wait[k] = []; this.q.push({ k, lat, lon }); this.pump(); }
    return new Promise(res => this.wait[k].push(res));
  },
  async pump() {
    if (this.busy) return; this.busy = true;
    while (this.q.length) {
      const { k, lat, lon } = this.q.shift(); updGeoQ();
      let r;
      try {
        const u = `${CFG2.NOMINATIM}?format=jsonv2&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1&accept-language=th`;
        const res = await fetch(u);
        if (res.status === 429 || res.status === 403) {
          this.blockedUntil = Date.now() + 10 * 60 * 1000;
          r = { err: true, line: GEO_BLOCK };
          for (const x of this.q) { (this.wait[x.k] || []).forEach(f => f(r)); delete this.wait[x.k]; }
          this.q = [];
        } else {
          const j = await res.json();
          r = j && !j.error ? fmtAddr(j) : { err: true, line: 'ไม่พบที่อยู่' };
        }
      } catch (e) { r = { err: true, line: 'ดึงที่อยู่ไม่ได้ — ไม่มีอินเทอร์เน็ตหรือถูกบล็อก' }; }
      if (!r.err) { this.cache[k] = r; this.save(); }
      (this.wait[k] || []).forEach(f => f(r)); delete this.wait[k]; this.done++;
      await new Promise(ok => setTimeout(ok, 1100));
    }
    this.busy = false; updGeoQ();
  },
};
function fmtAddr(j) {
  const a = j.address || {};
  const name = j.name || a.amenity || a.shop || a.building || a.tourism || '';
  const road = a.road || a.pedestrian || a.residential || '';
  const tambon = a.city || a.town || a.village || a.suburb || a.quarter || '';
  const short = [name, road, tambon].filter(Boolean).filter((x, i, arr) => arr.indexOf(x) === i).join(' · ');
  return { name, short: short || (j.display_name || '').split(',').slice(0, 2).join(','), full: j.display_name || '' };
}
function updGeoQ() {
  const el = $('#geoQ'); if (!el) return;
  el.textContent = Geo.q.length || Geo.busy ? `กำลังดึงที่อยู่จาก OpenStreetMap… เหลือ ${Geo.q.length + (Geo.busy ? 1 : 0)} จุด` : '';
  const c = $('#geoCache'); if (c) c.textContent = Object.keys(Geo.cache).length.toLocaleString();
}
