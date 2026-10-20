/* js/map/map.js — สร้างแผนที่ (MapLibre + deck.gl overlay) · มุมมอง 3D · ปุ่มกลางเมาส์
   ใช้: config.js · interaction.js
   ให้: initMap() · syncViewSeg() · initMiddleTilt()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

function initMap() {
  map = new maplibregl.Map({
    container: 'map', style: CFG.BASEMAP, center: [100.62, 13.78], zoom: 9.6,
    attributionControl: { compact: true }, maxPitch: 70,     // คลิกขวาค้าง/Ctrl+ลาก = หมุนและเอียง
  });
  map.on('error', e => {
    if (!initMap._fell && e && e.error && String(e.error.message || '').match(/style|fetch|Failed/i) && !map.isStyleLoaded()) {
      initMap._fell = true; map.setStyle(FALLBACK_STYLE);
    }
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), 'bottom-right');  // เข็มทิศ: กด = กลับทิศเหนือ/มุมตรง
  deckOverlay = new deck.MapboxOverlay({
    interleaved: false, layers: [],
    getTooltip: tooltip,
    onClick: onMapClick,
    onError: e => { showErr('deck', e); if (!S.noCar && /icon/i.test(String(e && (e.message || e)))) { S.noCar = true; render(); } },  // รูปรถพัง → กลับเป็นจุด
  });
  map.addControl(deckOverlay);
}
function syncViewSeg() {
  $('#viewSeg').querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', (b.dataset.v === '3d') === (map.getPitch() > 5)));
}
/* ปุ่มกลางเมาส์ค้างแล้วลาก: ขึ้น/ลง = เอียง · ซ้าย/ขวา = หมุน  (MapLibre ไม่มีในตัว)
   ดักที่ container แบบ capture เพื่อไม่ให้ชั้น deck หรือการเลื่อนอัตโนมัติของเบราว์เซอร์แย่งไป */
function initMiddleTilt() {
  const el = map.getContainer();
  let st = null;
  el.addEventListener('mousedown', e => {
    if (e.button !== 1) return;
    e.preventDefault(); e.stopPropagation();
    st = { x: e.clientX, y: e.clientY, b: map.getBearing(), p: map.getPitch() };
    el.style.cursor = 'move';
  }, true);
  window.addEventListener('mousemove', e => {
    if (!st) return;
    const dx = e.clientX - st.x, dy = e.clientY - st.y;
    map.jumpTo({ bearing: st.b + dx * 0.4, pitch: Math.max(0, Math.min(70, st.p - dy * 0.3)) });
  });
  window.addEventListener('mouseup', e => {
    if (!st || e.button !== 1) return;
    st = null; el.style.cursor = ''; syncViewSeg();
  });
  el.addEventListener('auxclick', e => { if (e.button === 1) e.preventDefault(); }, true);   // กันเปิดลิงก์/เลื่อนอัตโนมัติ
}
