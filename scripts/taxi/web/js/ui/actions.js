/* js/ui/actions.js — what happens when something changes: filters · time range · time cursor · selected vehicle
   + header numbers · keyboard shortcuts · links (#hash) · CSV export
   uses: analysis/* · map/* · ui/*
   provides: refresh() · setT() · selectVehicle() · toggleArea() · renderKpis() · applyHash() · writeHash() · initKeys() · downloadCSV() */

/* kind: 'filter' (center · status · area) → 'range' (selected period · zone) → 'time' (cursor only) */
function refresh(kind = 'range') {
  if (kind === 'filter') { rebuildMask(); buildTimelineBins(); }
  if (kind !== 'time') {
    computeAreas(); updateChoroScale(); computeExcursions(); layerVer++;
    markDirty(); renderPanel(S.panel);
    renderFilterChips(); renderLegend(); syncPresets();
    setZoneBadge(); setAwayBadge();
  }
  computeNow(); renderKpis(); render(); drawTimeline();
}
function setZoneBadge() {
  const n = EXC_BY_V.size, b = $('#zoneBadge');
  b.textContent = !n ? '' : n < 1000 ? String(n) : (n / 1000).toFixed(n < 10000 ? 1 : 0) + 'k';
  b.title = `${fmt(n)} vehicles left the zone`;
}
/* moving the cursor happens many times a second (drag, playback) → at most once per frame */
const _timeFrame = rafThrottle(() => {
  computeNow(); renderKpis(); render(); drawTimeline();
  if (S.panel === 'vehicles' && S.sel >= 0) updateVehLive();
  // the parking list is heavy to redraw: while the live clock runs, at most every 5 s
  if (S.panel === 'parking' && !S.playing && (!isLive() || performance.now() - _parkAt > 5000)) { _parkAt = performance.now(); renderPanel('parking'); }
  else DIRTY.add('parking');
  // Outside panel counts back from the cursor: redraw (and the rail badge) at most every 1 s while playing / live
  if ((!S.playing && !isLive()) || performance.now() - _awayAt > 1000) {
    _awayAt = performance.now(); setAwayBadge();
    if (S.panel === 'away') renderPanel('away'); else DIRTY.add('away');
  }
  if ((S.playing || isLive()) && S.sel >= 0) followSel();
});
let _parkAt = 0, _awayAt = 0;
/* live = true only for the live clock; any other move of the cursor is History, unless it lands on the newest data */
function setT(t, live = false) {
  S.T = Math.max(0, Math.min(D.meta.tmax, t));
  if (live) S.live = true;
  else { S.live = S.T >= D.meta.tmax - 1; if (S.live) liveAnchor(S.T); }
  $('#clkD').textContent = fDay(S.T);
  $('#clkH').textContent = fHM(S.T);
  syncLive();
  _timeFrame();
}
/* Live = the clock runs CFG.LIVE_LAG_SEC behind the newest data · any move of the cursor = History (replay) · "Live" returns */
function goLive() {
  setPlaying(false);
  if (S.b < D.meta.tmax) { S.b = D.meta.tmax; refresh('range'); }
  S.trkFrom = null;
  liveAnchor(D.meta.tmax - CFG.LIVE_LAG_SEC);
  setT(LC.T0, true);
  openTimeline(false);
}
function openTimeline(on) {
  if (document.body.classList.contains('tl-open') === on) return;
  document.body.classList.toggle('tl-open', on);
  requestAnimationFrame(() => { drawTimeline(); syncLive(); });
}
function syncLive() {
  const live = isLive(), b = $('#liveBtn');
  b.classList.toggle('on', live);
  b.innerHTML = live ? '<i></i>LIVE' : '<i></i>Go live';
  b.title = live ? `Showing the latest data (${fDT(D.meta.tmax)})` : 'Jump back to the latest data';
  $('#kat').classList.toggle('live', live);
  const mm = $('#mapMode');
  mm.className = 'mapmode ' + (live ? 'live' : 'hist');
  if (!live) openTimeline(true);                             // any look into the past brings the timeline up
  const tlOpen = document.body.classList.contains('tl-open');
  const follow = S.sel >= 0;
  // caught up with the newest data: say why the clock stopped (feed late · fixed snapshot) — a snapshot can replay its last hour
  const wait = live && !SIM.on && liveWaiting(), snap = !DataSource.canWatch();
  const key = [live, tlOpen, S.playing, follow, S.follow, SIM.on, SIM.done, wait].join();
  if (mm._key !== key) {                                       // rebuild buttons only when the mode changes
    mm._key = key;
    mm.innerHTML = (live ? `<i></i><b>${SIM.on ? 'LIVE TEST' : 'LIVE'}</b><span id="mmT"></span>${SIM.on ? `<span class="mm-sim" id="mmSim"></span><button type="button" id="mmStop" title="Stop the test and show all data">Stop test</button>` : ''}`
        + (wait ? `<span class="mm-wait">${snap ? 'Snapshot · no newer data' : 'Waiting for new data'}</span>` : '')
        + (wait && snap ? '<button type="button" id="mmReplay" title="Play the last hour of the data as if it were arriving live">Replay last hour</button>' : '')
        + (tlOpen ? '' : '<button type="button" id="mmHist" title="Open the timeline to look back or replay">History</button>')
      : `<b>${S.playing ? 'REPLAY' : 'HISTORY'}</b><span id="mmT"></span><button type="button" id="mmLive">Go live</button>`)
      + (follow ? `<button type="button" id="mmFollow" class="${S.follow ? 'on' : ''}" title="Keep the selected car in view while it moves">${S.follow ? 'Following car' : 'Follow car'}</button>` : '');
    mm.title = live ? `Live runs ${CFG.LIVE_LAG_SEC / 60} min behind the newest data, so cars drive between positions that have arrived · `
      + (snap ? 'fixed snapshot (test data) — serve the page with the server to get new data' : `checks for new data every ${CFG.REFRESH_SEC} s`) : '';
    const g = $('#mmLive'); if (g) g.onclick = goLive;
    const hb = $('#mmHist'); if (hb) hb.onclick = () => openTimeline(true);
    const fb = $('#mmFollow'); if (fb) fb.onclick = () => setFollow(!S.follow);
    const sb = $('#mmStop'); if (sb) sb.onclick = () => stopLiveTest();
    const rb = $('#mmReplay'); if (rb) rb.onclick = () => startLiveTest(1);
  }
  $('#mmT').textContent = live ? `${fDayShort(S.T)} ${fHMS(S.T)}` : fDT(S.T);   // seconds while live: the clock is visibly running
  const ms = $('#mmSim');
  if (ms) { const m = Math.max(0, (D.meta.tmax - SIM.h0) / 60); ms.textContent = `+${Math.floor(m)}:${p2(Math.floor((m % 1) * 60))} / 60:00 · ${SIM.speed === 1 ? 'real time' : '×' + SIM.speed}`; }
  $('#kMode').textContent = live ? 'LIVE' : 'at';
  if (live !== syncLive.was) { syncLive.was = live; if ($('#legend').childElementCount) renderLegend(); }
}
/* while playing, the camera chases the selected car: every frame it moves a little toward the car once the car leaves
   the middle of the map. (It used to start a 0.4 s panTo every frame — each restart threw away the previous one before it
   got past its slow start, so the map looked frozen.) Dragging the map yourself stops following → "Follow car" resumes. */
function followSel() {
  if (!S.follow || map.isMoving()) return;
  const d = NOW.find(x => x.v === S.sel);
  let ll = d ? [d.x, d.y] : null;
  if (!ll) { const i = lastIdxAt(S.sel, S.T); if (i < 0) return; ll = [POS[2 * i], POS[2 * i + 1]]; }
  const p = map.project(ll), c = map.getContainer(), w = c.clientWidth, h = c.clientHeight;
  const dx = p.x - w / 2, dy = p.y - h / 2;
  if (Math.abs(dx) > w || Math.abs(dy) > h) { map.jumpTo({ center: ll }); return; }      // far away: jump straight to it
  if (Math.abs(dx) < w * 0.15 && Math.abs(dy) < h * 0.15) return;                       // in the middle: leave the map alone
  map.jumpTo({ center: map.unproject([w / 2 + dx * 0.12, h / 2 + dy * 0.12]) });
}
function setFollow(on) {
  S.follow = on;
  syncLive();
  if (on && S.sel >= 0) { const d = NOW.find(x => x.v === S.sel); if (d) map.easeTo({ center: [d.x, d.y], duration: 500 }); }
}
function renderKpis() {
  const s = NOWSTAT;
  $('#kOnline').textContent = fmt(s.on);
  $('#kHired').textContent = fmt(s.hired);
  $('#kMove').textContent = fmt(s.mov);
  $('#kPark').textContent = fmt(s.park);
  $('#kOut').textContent = fmt(s.out);
  $('#kAt').textContent = `${fDayShort(S.T)} · ${fHM(S.T)}`;
}
/* others: 'hide' (picked from a list / search → only this car on the map) · 'dim' (clicked on the map) */
function selectVehicle(v, fly = true, others) {
  if (others) S.others = others;
  if (v !== S.sel) { S.trkFrom = null; S.follow = !isLive(); }     // Live: off until "Follow car" — else the map keeps snapping back to it
  S.sel = v;
  if (v >= 0) {
    if (S.panel !== 'vehicles') openPanel('vehicles'); else renderPanel('vehicles');
    if (fly) {
      const s = D.vehicles.start[v], n = D.vehicles.count[v], pts = [];
      for (let i = s; i < s + n; i += 1) if (TT[i] >= S.a && TT[i] <= S.b && !(FLG[i] & 2)) pts.push([POS[2 * i], POS[2 * i + 1]]);
      if (pts.length) fitPoints(pts.length > 400 ? pts.filter((_, k) => k % Math.ceil(pts.length / 400) === 0).concat([pts[pts.length - 1]]) : pts, 14);
      else if (D.vehicles.llon && D.vehicles.llon[v] != null) map.flyTo({ center: [D.vehicles.llon[v], D.vehicles.llat[v]], zoom: 13 });
    }
  } else if (S.panel === 'vehicles') renderPanel('vehicles');
  DIRTY.add('zone'); DIRTY.add('parking');            // their rows mark the selected car
  renderLegend(); render(); writeHash();
}
function toggleArea(key) { S.areas.has(key) ? S.areas.delete(key) : S.areas.add(key); refresh('filter'); }

/* ── keyboard: Space play/pause · ←/→ 5 min · Esc close / deselect ── */
function initKeys() {
  document.addEventListener('keydown', e => {
    const t = e.target, tag = t.tagName;
    const typing = tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || t.isContentEditable;
    if (e.code === 'Escape') {
      if (!$('#layersPop').hidden) { closeLayers(); return; }
      if (document.body.classList.contains('chat-open') && t.closest && t.closest('#chat')) { Chat.close(); return; }
      if (!$('#place').hidden) { hidePlace(); return; }
      if (S.sel >= 0 && !typing) selectVehicle(-1);
      return;
    }
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.code === 'Space' && tag !== 'BUTTON' && tag !== 'A') { e.preventDefault(); setPlaying(!S.playing); }
    else if (e.code === 'ArrowRight' && tag !== 'BUTTON') setT(Math.min(S.b, S.T + 300));
    else if (e.code === 'ArrowLeft' && tag !== 'BUTTON') setT(Math.max(S.a, S.T - 300));
  });
}

/* ── links: index.html#panel=zone&zone=metro&plate=ทอ-9094&bm=satellite&view=3d&depot=0 ── */
const OLD_TABS = { ov: 'overview', viol: 'zone', stay: 'parking', area: 'areas', veh: 'vehicles' };
function applyHash() {
  const h = new URLSearchParams(decodeURIComponent(location.hash.slice(1)));
  if (h.get('zone') && CFG.ZONES[h.get('zone')]) { S.zone = h.get('zone'); buildZoneGeo(); $('#zoneSel') && ($('#zoneSel').value = S.zone); refresh('range'); }
  const bm = { sat: 'satellite', osm: 'streets' }[h.get('bm')] || h.get('bm');
  if (bm && BASEMAPS[bm]) { setBasemap(bm); syncMapTools(); }
  const p = h.get('panel') || OLD_TABS[h.get('tab')] || h.get('tab');
  if (p && PANELS[p]) openPanel(p);
  if (h.get('plate') || h.get('car')) {                     // plate=ทอ-9094 · car=<id> (same id the assistant uses)
    const v = h.get('car') != null ? carArg('car:' + h.get('car')) : carArg(h.get('plate'));
    if (v >= 0) selectVehicle(v, true, 'hide');
  }
  if (h.get('depot') != null) whenDepots(() => {
    const dp = DEPOTS[+h.get('depot')]; if (!dp) return;
    openPanel('parking');
    map.jumpTo({ center: [dp.lon, dp.lat], zoom: 15 });
    showPlace(dp.lat, dp.lon, `Depot · ${dp.n} vehicles overnight`, whereOf(dp.d));
  });
  if (h.get('view') === '3d') set3D(true);
  if (h.get('zoom') === 'th') fitThailand();
  if (CFG.AREA_PRESETS[h.get('area')]) { $('#fPreset').value = h.get('area'); $('#fPreset').onchange({ target: $('#fPreset') }); }   // #area=metro                     // #zoom=th — whole country
}
let _hashOn = false;
function writeHash() {
  if (!_hashOn) return;
  const h = new URLSearchParams();
  if (S.panel !== 'overview') h.set('panel', S.panel);
  if (S.zone !== 'metro') h.set('zone', S.zone);   // default zone = Bangkok + vicinity
  if (S.sel >= 0) h.set('plate', plateOf(S.sel).split(' · ')[0]);
  if (S.basemap !== 'light') h.set('bm', S.basemap);
  const s = h.toString();
  history.replaceState(null, '', s ? '#' + s : location.pathname + location.search);
}

/* ── CSV of out-of-zone trips (one row per trip) ──────────────────── */
function downloadCSV() {
  const lvl = { far: 'Upcountry', near: 'Vicinity', all: 'Always outside' };
  const q = s => '"' + String(s).replace(/"/g, '""') + '"';
  const lines = [['plate', 'vin', 'center', 'level', 'trip_no', 'start', 'end', 'minutes', 'provinces', 'max_km_from_bangkok'].join(',')];
  for (const r of VROWS) {
    const xs = EXC_BY_V.get(r.v).slice().sort((a, b) => a.s - b.s);
    xs.forEach((x, k) => lines.push([q(r.plate), D.vehicles.vin[r.v], D.vehicles.center[r.v], lvl[r.sev], k + 1, fISO(x.s), fISO(x.e),
      Math.round(x.dur / 60), q([...x.provs.keys()].map(provName).join(' / ')), Math.round(x.km)].join(',')));
  }
  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = `ev7_out_of_zone_${S.zone}_${fDay(S.a).replace(/\s/g, '')}.csv`; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
