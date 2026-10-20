/* js/ui/controls.js — ผูกปุ่ม/ตัวกรองทั้งหมด · ค้นหา · ดาวน์โหลด CSV · ตั้งค่า · ลิงก์ตรง (#hash)
   ใช้: ทุกโมดูล
   ให้: refreshPanels() · selectVehicle() · switchTab() · initUI() · initV2() · applyHash()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ══════════════════════════════════════════════════════════════════════
   เหตุการณ์
   ══════════════════════════════════════════════════════════════════════ */
function refreshPanels() {
  computeAreas(); updateChoroScale(); computeExcursions(); computeStays();
  renderOverview(); renderViolations(); renderStays(); renderAreas(); renderVehCard(); renderVehList(); renderLegend(); renderAreaChips(); renderRangeText();
  layerVer++; computeNow(); render(); drawTimeline();
}
function onFilterChange() { rebuildMask(); buildTimelineBins(); refreshPanels(); }
function onRangeChange() { refreshPanels(); }
function toggleArea(key) { S.areas.has(key) ? S.areas.delete(key) : S.areas.add(key); onFilterChange(); }
function selectVehicle(v, fly) {
  S.sel = v;
  if (v >= 0) {
    switchTab('veh');
    if (fly) {
      const s = D.vehicles.start[v], n = D.vehicles.count[v];
      let x0 = 999, y0 = 999, x1 = -999, y1 = -999;
      for (let i = s; i < s + n; i++) {
        if (TT[i] < S.a || TT[i] > S.b || FLG[i] & 2) continue;
        x0 = Math.min(x0, POS[2 * i]); x1 = Math.max(x1, POS[2 * i]); y0 = Math.min(y0, POS[2 * i + 1]); y1 = Math.max(y1, POS[2 * i + 1]);
      }
      if (x0 < 999) map.fitBounds([[x0, y0], [x1, y1]], { padding: 80, maxZoom: 14, duration: 700 });
      else if (D.vehicles.llon[v] != null) map.flyTo({ center: [D.vehicles.llon[v], D.vehicles.llat[v]], zoom: 13 });
    }
  }
  renderVehCard(); renderVehList(); renderViolations(); render();
}
function switchTab(id) {
  document.querySelectorAll('.tabs button').forEach(b => b.setAttribute('aria-selected', b.dataset.tab === id));
  document.querySelectorAll('.pane').forEach(p => p.classList.toggle('on', p.id === 'p-' + id));
  if (id === 'veh' && S.sel >= 0) drawSpark(S.sel);
  S.tab = id;
  render();
  if (id === 'area' && !S.choro) {
    S.choro = true;
    $('#chSeg').querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', b.dataset.v === 'on'));
    renderLegend(); render();
  }
}
function initUI() {
  // ศูนย์
  const centers = [...new Set(D.vehicles.center)].sort();
  $('#fCenter').innerHTML = centers.map(c => `<button class="chip" aria-pressed="false" data-c="${c}">${CFG.CENTER_NAMES[c] || c} <span class="num muted">${fmt(D.vehicles.center.filter(x => x === c).length)}</span></button>`).join('');
  $('#fCenter').querySelectorAll('button').forEach(b => b.onclick = () => {
    const c = b.dataset.c; S.centers.has(c) ? S.centers.delete(c) : S.centers.add(c);
    b.setAttribute('aria-pressed', S.centers.has(c)); onFilterChange();
  });
  // สถานะ
  const STS = [['hired', 'มีผู้โดยสาร', 'var(--blue)'], ['vacant', 'ว่าง·วิ่ง', 'var(--green)'], ['park', 'จอด', 'var(--slate)']];
  $('#fStatus').innerHTML = STS.map(([k, n, c]) => `<button class="chip" aria-pressed="false" data-s="${k}"><i class="dot" style="background:${c}"></i>${n}</button>`).join('');
  const syncSt = () => $('#fStatus').querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', S.status.size < 3 && S.status.has(b.dataset.s)));
  $('#fStatus').querySelectorAll('button').forEach(b => b.onclick = () => {
    const k = b.dataset.s;
    if (S.status.size === 3) S.status = new Set([k]);          // กดครั้งแรก = ดูเฉพาะสถานะนี้
    else if (S.status.has(k)) { S.status.delete(k); if (!S.status.size) S.status = new Set(['hired', 'vacant', 'park']); }
    else S.status.add(k);
    syncSt(); onFilterChange();
  });
  // แท็บ
  document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => switchTab(b.dataset.tab));
  // นอกเขต
  $('#zone').onchange = e => { S.zone = e.target.value; buildZoneGeo(); refreshPanels(); };
  $('#minDur').onchange = e => { S.minDur = +e.target.value; refreshPanels(); };
  seg($('#sevSeg'), v => { S.sev = v; renderViolations(); });
  document.querySelectorAll('#vTable th').forEach(th => th.onclick = () => {
    const k = th.dataset.k; if (S.sortK === k) S.sortDir *= -1; else { S.sortK = k; S.sortDir = k === 'plate' ? 1 : -1; }
    renderViolations();
  });
  $('#csv').onclick = downloadCSV;
  // พื้นที่
  seg($('#lvSeg'), v => { S.level = v; updateChoroScale(); layerVer++; renderAreas(); renderLegend(); render(); });
  seg($('#mtSeg'), v => { S.metric = v; updateChoroScale(); layerVer++; renderAreas(); renderLegend(); render(); });
  // รถ
  $('#vehSort').onchange = e => { S.vehSort = e.target.value; renderVehList(); };
  // แผนที่
  seg($('#ptSeg'), v => { S.pt = v; $('#trailWrap').style.display = $('#iconWrap').style.display = v === 'now' ? '' : 'none'; render(); });
  $('#trail').onchange = e => { S.trail = +e.target.value; render(); };
  seg($('#chSeg'), v => { S.choro = v === 'on'; renderLegend(); render(); });
  seg($('#evSeg'), v => { S.ev = v === 'on'; render(); });
  if (!EV.length) $('#evBox').style.display = 'none';         // ไม่มีข้อมูล (ดึงไม่ได้ตอน build) → ซ่อนปุ่ม
  document.querySelectorAll('.zoomto [data-z]').forEach(b => b.onclick = () => {
    b.parentElement.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
    if (b.dataset.z === 'th') map.fitBounds([[97.3, 5.6], [105.7, 20.5]], { padding: 30, duration: 800 });
    else map.flyTo({ center: [100.62, 13.78], zoom: 9.6, duration: 800 });
  });
  seg($('#bmSeg'), v => map.setStyle(v === 'sat' ? SAT_STYLE : v === 'osm' ? OSM_STYLE : CFG.BASEMAP));
  // ไทม์ไลน์
  $('#play').onclick = () => setPlaying(!S.playing);
  seg($('#spdSeg'), v => { S.speed = +v; });
  const days = []; for (let t = 0; t <= D.meta.tmax; t += 3600) { const k = fDay(t); if (!days.includes(k)) days.push(k); }
  const presets = [['ทั้งหมด', 0, D.meta.tmax]];
  days.forEach(k => {
    let a = Infinity, b = -Infinity;
    for (let t = 0; t <= D.meta.tmax; t += 300) if (fDay(t) === k) { a = Math.min(a, t); b = Math.max(b, t); }
    const d = tDate(a); presets.push([`${d.getDate()} ${TH_MON[d.getMonth()]}`, a, Math.min(b, D.meta.tmax)]);
  });
  $('#rngSeg').innerHTML = presets.map((p, i) => `<button aria-pressed="${i === 0}" data-v="${i}">${p[0]}</button>`).join('');
  seg($('#rngSeg'), v => { const p = presets[+v]; S.a = p[1]; S.b = p[2]; S.T = Math.max(S.a, Math.min(S.b, S.T)); onRangeChange(); setT(S.T); });
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.code === 'Space') { e.preventDefault(); setPlaying(!S.playing); }
    if (e.code === 'ArrowRight') setT(Math.min(S.b, S.T + 300));
    if (e.code === 'ArrowLeft') setT(Math.max(S.a, S.T - 300));
    if (e.code === 'Escape') selectVehicle(-1);
  });
  initSearch();
}
function initSearch() {
  const q = $('#q'), dd = $('#qdd');
  const V = D.vehicles;
  const idxPlate = V.plate.map((p, v) => [p.replace(/[\s-]/g, '').toLowerCase(), V.vin[v].toLowerCase(), v]);
  let items = [], hi = 0;
  const draw = () => {
    dd.innerHTML = items.map((x, i) => `<div class="${i === hi ? 'on' : ''}" data-i="${i}" role="option"><span>${x.label}</span><small>${x.sub}</small></div>`).join('');
    dd.classList.toggle('open', items.length > 0);
    dd.querySelectorAll('div').forEach(d => d.onmousedown = e => { e.preventDefault(); pick(items[+d.dataset.i]); });
  };
  const pick = x => {
    if (!x) return; dd.classList.remove('open'); q.value = '';
    if (x.kind === 'veh') selectVehicle(x.v, true);
    else { if (!S.areas.has(x.key)) toggleArea(x.key); switchTab('area'); }
  };
  q.oninput = () => {
    const s = q.value.trim().toLowerCase(), sk = s.replace(/[\s-]/g, '');
    items = []; hi = 0;
    if (!s) return draw();
    for (const [p, vin, v] of idxPlate) { if (p.includes(sk) || vin.includes(sk)) { items.push({ kind: 'veh', v, label: V.plate[v], sub: 'รถ · ' + V.center[v] }); if (items.length >= 8) break; } }
    PROV.forEach((p, i) => { if (p.th.includes(s) || p.en.toLowerCase().includes(s)) items.push({ kind: 'area', key: 'p:' + i, label: p.th, sub: 'จังหวัด' }); });
    let k = 0; DIST.forEach((d, i) => { if (k < 10 && (d.th.includes(s) || d.en.toLowerCase().includes(s))) { k++; items.push({ kind: 'area', key: 'd:' + i, label: d.th, sub: 'อำเภอ/เขต · ' + PROV[d.p].th }); } });
    items = items.slice(0, 16); draw();
  };
  q.onkeydown = e => {
    if (e.key === 'ArrowDown') { hi = Math.min(items.length - 1, hi + 1); draw(); e.preventDefault(); }
    if (e.key === 'ArrowUp') { hi = Math.max(0, hi - 1); draw(); e.preventDefault(); }
    if (e.key === 'Enter') pick(items[hi]);
    if (e.key === 'Escape') { dd.classList.remove('open'); }
  };
  q.onblur = () => setTimeout(() => dd.classList.remove('open'), 120);
}
function downloadCSV() {
  const lbl = { far: 'ต่างจังหวัด', near: 'ปริมณฑล', all: 'อยู่นอกตลอด' };
  const lines = [['ทะเบียน', 'VIN', 'ศูนย์', 'ระดับ', 'ครั้งที่', 'เริ่ม', 'สิ้นสุด', 'นาที', 'จังหวัด', 'ไกลสุด_กม'].join(',')];
  for (const r of VROWS) {
    const xs = EXC_BY_V.get(r.v).slice().sort((a, b) => a.s - b.s);
    xs.forEach((x, k) => {
      const d0 = tDate(x.s), d1 = tDate(x.e);
      const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
      lines.push([r.plate, D.vehicles.vin[r.v], D.vehicles.center[r.v], lbl[r.sev], k + 1, iso(d0), iso(d1), Math.round(x.dur / 60),
        '"' + [...x.provs.keys()].map(p => PROV[p].th).join(' / ') + '"', Math.round(x.km)].join(','));
    });
  }
  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = `taxi_out_of_zone_${S.zone}_${fDay(S.a).replace(/\s/g, '')}.csv`; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
function initV2() {
  Geo.init(); MLY.init(); updGeoQ();
  $('#gear').onclick = e => { e.stopPropagation(); $('#pop').classList.toggle('on'); $('#mlyTok').value = MLY.tok; updGeoQ(); };
  document.addEventListener('click', e => { if (!$('#pop').contains(e.target) && e.target !== $('#gear')) $('#pop').classList.remove('on'); });
  $('#mlySave').onclick = async () => {
    const t = $('#mlyTok').value.trim(); MLY.set(t);
    const m = $('#mlyMsg'); m.className = ''; m.textContent = 'กำลังทดสอบ…';
    try { await MLY.near(13.7465, 100.5348); m.className = 'ok'; m.textContent = '✓ ใช้ได้ — เปิดเส้นภาพถนนบนแผนที่แล้ว'; setMly(true); }
    catch (e) { m.className = 'bad'; m.textContent = '✗ ' + e.message; }
  };
  $('#mlyClear').onclick = () => { MLY.set(''); setMly(false); $('#mlyTok').value = ''; $('#mlyMsg').className = 'muted'; $('#mlyMsg').textContent = 'ลบแล้ว'; };
  $('#geoClear').onclick = () => { Geo.cache = {}; Geo.save(); updGeoQ(); };
  $('#exDepot').onchange = e => { S.exDepot = e.target.checked; refreshPanels(); };
  seg($('#sSeg'), v => { S.sSev = v; renderStays(); });
  seg($('#mlySeg'), v => setMly(v === 'on'));
  map.on('pitch', onViewCars);                       // เอียง/ตั้งตรง → สลับรูปรถ/จุด
  // มุมมอง 3 มิติ — ตึก 3 มิติมีเฉพาะแผนที่ OSM (Liberty) ที่ซูม ≥ 14 จึงสลับให้เอง
  seg($('#viewSeg'), v => {
    if (v === '3d') {
      const b = $('#bmSeg').querySelector('[data-v="osm"]');
      if (b.getAttribute('aria-pressed') !== 'true') b.click();
      // jumpTo ไม่ใช่ easeTo — แอนิเมชันถูกขัดจังหวะได้ง่าย (เช่นตอนสลับสไตล์แผนที่) แล้วมุมแทบไม่ขยับ
      map.jumpTo({ pitch: 60, bearing: map.getBearing() || -20, zoom: Math.max(map.getZoom(), 15.5) });
    } else map.jumpTo({ pitch: 0, bearing: 0 });
    syncViewSeg();
  });
  map.on('pitchend', syncViewSeg);
  initMiddleTilt();
  map.on('style.load', syncMly);                     // เปลี่ยนแผนที่พื้นหลัง → ใส่เส้นกลับ
  map.once('idle', syncMly);                         // กันพลาดตอนเปิดไฟล์ครั้งแรก
  map.on('click', 'mly-seq', e => showPlace(e.lngLat.lat, e.lngLat.lng, 'ภาพถนน ณ จุดที่คลิก', ''));
  map.on('mouseenter', 'mly-seq', () => map.getCanvas().style.cursor = 'pointer');
  map.on('mouseleave', 'mly-seq', () => map.getCanvas().style.cursor = '');
  setMly(!!MLY.tok);
}
/* ลิงก์ตรง เช่น  Taxi_dashboard.html#tab=viol&zone=metro&plate=ทอ-9094 */
function applyHash() {
  const h = new URLSearchParams(decodeURIComponent(location.hash.slice(1)));
  if (h.get('zone') && CFG.ZONES[h.get('zone')]) { S.zone = h.get('zone'); $('#zone').value = S.zone; buildZoneGeo(); refreshPanels(); }
  if (h.get('plate')) {
    const k = h.get('plate').replace(/[\s-]/g, '');
    const v = D.vehicles.plate.findIndex(p => p.replace(/[\s-]/g, '').includes(k));
    if (v >= 0) { selectVehicle(v, true); S.pt = 'now'; }
  }
  if (h.get('bm')) { const b = h.get('bm'); map.setStyle(b === 'sat' ? SAT_STYLE : b === 'osm' ? OSM_STYLE : CFG.BASEMAP);
    $('#bmSeg').querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x.dataset.v === b)); }
  if (h.get('tab')) switchTab(h.get('tab'));
  if (h.get('depot') && DEPOTS[+h.get('depot')]) {          // #tab=stay&depot=0
    const dp = DEPOTS[+h.get('depot')];
    map.jumpTo({ center: [dp.lon, dp.lat], zoom: 15 });
    showPlace(dp.lat, dp.lon, `ลานจอด · ${dp.n} คันค้างคืน`, `${DIST[dp.d].th}, ${PROV[distProv[dp.d]].th}`);
  }
  if (h.get('view') === '3d') $('#viewSeg').querySelector('[data-v="3d"]').click();   // #view=3d
  if (h.get('test') === 'car') testCar();
  if (h.get('test') === 'wheel') testWheel();
  if (h.get('test') === 'tilt') testTilt().catch(e => { const pre = document.createElement('pre'); pre.id = 'tilt'; pre.textContent = 'ERROR ' + e.message + '\n' + e.stack; document.body.appendChild(pre); });
}
