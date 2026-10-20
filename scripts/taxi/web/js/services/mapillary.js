/* js/services/mapillary.js — ภาพถนน Mapillary — ภาพใกล้จุด + เส้นถนนที่มีภาพบนแผนที่
   ใช้: utils.js · map.js
   ให้: MLY · setMly() · syncMly()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ── ภาพถนน Mapillary (ต้องมี token ของผู้ใช้เอง) ──────────────────── */
const MLY = {
  tok: '',
  init() { this.tok = store.get('ev7.mly', ''); },
  set(t) { this.tok = t || ''; store.set('ev7.mly', t || null); },
  // ภาพในไทยมีไม่หนาแน่น (ทดสอบ 2026-10-02: ลานจอดทั้ง 4 แห่งไม่มีภาพในรัศมี 80 ม.
  // แต่มีที่ 106–405 ม.) จึงค้นเป็นขั้น แล้วบอกระยะห่างให้ผู้ใช้รู้ว่าไม่ใช่จุดนั้นพอดี
  async near(lat, lon) {
    if (!this.tok) return null;
    for (const d of [0.0008, 0.0015, 0.0028, 0.0055]) {   // ~80 · ~160 · ~300 · ~600 ม. — กรอบเล็กก่อน เพราะจุดที่ภาพหนาแน่น API ส่งมาไม่ครบ
      const u = `https://graph.mapillary.com/images?access_token=${encodeURIComponent(this.tok)}&fields=id,thumb_1024_url,captured_at,computed_geometry,altitude&bbox=${lon - d},${lat - d},${lon + d},${lat + d}&limit=500`;   // API ไม่เรียงตามระยะ ต้องขอมากพอ
      const j = await (await fetch(u)).json();
      if (j.error) throw new Error(j.error.message || 'token ใช้ไม่ได้');
      const c = [];
      for (const im of j.data || []) {
        const g = (im.computed_geometry || {}).coordinates; if (!g) continue;
        // ⚠️ ข้ามภาพถ่ายจากเครื่องบิน — ความสูงจากกล้อง (altitude) หลายร้อยเมตร
        //    เจอจริงที่สุวรรณภูมิ: altitude 697 ม. แต่ computed_altitude ถูกกดเหลือ 3.6 ม.
        if ((im.altitude || 0) > 300) continue;
        c.push(Object.assign({}, im, { dist: hav(g[0], g[1], lon, lat) }));
      }
      if (c.length) {
        // ระยะใกล้เคียงกัน (ห่างกันไม่เกิน 50 ม.) เลือกภาพใหม่สุด
        const dmin = Math.min(...c.map(x => x.dist));
        return c.filter(x => x.dist <= dmin + 0.05).sort((x, y) => y.captured_at - x.captured_at)[0];
      }
    }
    return { none: true };
  },
};
/* ── เส้นถนนที่มีภาพ Mapillary (vector tiles) ──────────────────────────
   ใช้ระดับ z10–12 เท่านั้น — tile z14 ใจกลางกรุงเทพฯ ใหญ่ ~5 MB ต่อแผ่น
   ซูมลึกกว่า 12 ระบบจะขยายแผ่น z12 แทน เส้นยังคมพอ                       */
function setMly(on) {
  if (on && !MLY.tok) { on = false; $('#mlyHint').textContent = 'ใส่ token ที่ปุ่ม ⚙ ก่อน'; }
  else $('#mlyHint').textContent = on ? 'ซูมเข้าระดับเขต/ถนนเพื่อเห็นเส้น' : '';
  S.mly = on;
  $('#mlySeg').querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', (b.dataset.v === 'on') === on));
  syncMly(); renderLegend();
}
// ⚠️ ห้ามเช็ค map.isStyleLoaded() ก่อน — มันคืน false ตลอดช่วงที่แผ่นแผนที่ยังโหลด
//    และ 'style.load' มักเกิดไปแล้วก่อนข้อมูลรถถอดเสร็จ → เส้นจะไม่ถูกใส่เลย
//    ให้ลองใส่ตรง ๆ ถ้าสไตล์ยังไม่พร้อมจริง จะ throw แล้ว 'style.load' รอบหน้าเรียกซ้ำเอง
function syncMly() {
  if (!map) return;
  try {
    const has = !!map.getSource('mly');
    if (!S.mly) {
      if (map.getLayer('mly-seq')) map.removeLayer('mly-seq');
      if (has) map.removeSource('mly');
      return;
    }
    if (!has) map.addSource('mly', { type: 'vector', minzoom: 10, maxzoom: 12, attribution: '© Mapillary',
      tiles: [`https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token=${encodeURIComponent(MLY.tok)}`] });
    if (!map.getLayer('mly-seq')) map.addLayer({ id: 'mly-seq', type: 'line', source: 'mly', 'source-layer': 'sequence', minzoom: 10,
      layout: { 'line-cap': 'round' },
      paint: { 'line-color': '#05cb63', 'line-opacity': 0.85, 'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.4, 15, 4] } });
  } catch (e) { /* สไตล์ยังไม่พร้อม — รอ 'style.load' */ }
}
