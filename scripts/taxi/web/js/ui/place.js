/* js/ui/place.js — การ์ดสถานที่ (ที่อยู่ OSM · ภาพถนน · ลิงก์ Street View)
   ใช้: geocode.js · mapillary.js
   ให้: PLACE · showPlace()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ── การ์ดสถานที่ ─────────────────────────────────────────────────── */
let PLACE = null;
function showPlace(lat, lon, title, sub) {
  PLACE = { lat, lon };
  const el = $('#place'); el.classList.add('on');
  const sv = `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lon}`;
  const mly = `https://www.mapillary.com/app/?lat=${lat}&lng=${lon}&z=17`;
  const osm = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=18/${lat}/${lon}`;
  const gm = `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;
  el.innerHTML = `<div class="ph"><div><b>${title}</b><small>${sub ? sub + ' · ' : ''}${lat.toFixed(5)}, ${lon.toFixed(5)}</small></div>
      <button class="btn" id="plX" aria-label="ปิด">✕</button></div>
    <div class="addr" id="plAddr">กำลังหาที่อยู่จาก OpenStreetMap…</div>
    <div class="img" id="plImg">${MLY.tok ? '<div class="none">กำลังหาภาพถนน…</div>' : '<div class="none">ใส่ Mapillary token ที่ปุ่ม ⚙ เพื่อแสดงภาพถนนตรงนี้</div>'}</div>
    <div class="links"><a class="sv" href="${sv}" target="_blank" rel="noopener">Street View</a>
      <a href="${mly}" target="_blank" rel="noopener">Mapillary</a>
      <a href="${osm}" target="_blank" rel="noopener">OpenStreetMap</a>
      <a href="${gm}" target="_blank" rel="noopener">Google Maps</a></div>`;
  $('#plX').onclick = () => { el.classList.remove('on'); PLACE = null; render(); };
  const same = () => PLACE && PLACE.lat === lat && PLACE.lon === lon;
  Geo.get(lat, lon).then(r => {
    if (!same()) return;
    $('#plAddr').innerHTML = r.err ? `<span class="muted">${r.line}</span>` : `${r.name ? `<b>${r.name}</b><br>` : ''}${r.full}`;
  });
  if (MLY.tok) MLY.near(lat, lon).then(im => {
    if (!same()) return;
    const box = $('#plImg');
    if (!im || im.none) { box.innerHTML = '<div class="none">ไม่มีภาพถนน Mapillary ในรัศมี ~600 ม. — ลองกด Street View</div>'; return; }
    const d = new Date(im.captured_at);
    box.innerHTML = `<a href="https://www.mapillary.com/app/?pKey=${im.id}" target="_blank" rel="noopener"><img src="${im.thumb_1024_url}" alt="ภาพถนนใกล้จุดนี้"></a>
      <span class="cap">Mapillary · ถ่าย ${TH_MON[d.getMonth()]} ${d.getFullYear() + 543} · ห่าง ${Math.round(im.dist * 1000)} ม.${im.dist > 0.1 ? ' · ภาพถนนใกล้เคียง ไม่ใช่จุดนี้พอดี' : ''}</span>`;
  }).catch(e => { if (same()) $('#plImg').innerHTML = `<div class="none" style="color:var(--red)">Mapillary: ${e.message}</div>`; });
  render();
}
