/* js/main.js — start-up (must load last)
   1. the map starts drawing at once, while the data decodes (progress bar)
   2. only what the first screen needs is computed, then the loading screen goes away
   3. depots (slow, whole data range) are found in the background afterwards */

(async function main() {
  const bar = $('#loadBar'), msg = $('#loadMsg');
  const step = (f, m) => { bar.style.width = Math.round(f * 100) + '%'; if (m) msg.textContent = m; };
  try {
    S.basemap = BASEMAPS[store.get('ev7.basemap')] ? store.get('ev7.basemap') : S.basemap;
    initMap();
    const data = await DataSource.load(f => step(f * 0.8, 'Decoding GPS data…'));
    step(0.85, 'Preparing…'); await nextFrame();
    prepare(data);
    pcToProv = new Map(PROV.map((p, i) => [p.pc, i]));
    pcToDist = new Map(DIST.map((d, i) => [d.pc, i]));
    liveAnchor(D.meta.tmax - CFG.LIVE_LAG_SEC); S.T = LC.T0;   // open in Live: the clock starts one batch behind the newest data
    $('#subtitle').textContent = `${fmt(NV)} vehicles · ${fDT(0)} – ${fDT(D.meta.tmax)}`;
    rebuildMask(); buildTimelineBins(); buildZoneGeo();
    step(0.95, 'Analysing…'); await nextFrame();
    Geo.init();
    initShell(); initFilters(); initSearch(); initMapTools(); initTimeline(); initKeys(); Chat.init();
    computeAreas(); updateChoroScale(); computeExcursions();
    setZoneBadge();
    openPanel('overview', true);
    renderFilterChips(); renderLegend(); syncPresets();
    setT(S.T, true);
    startLiveClock();
    $('#loading').classList.add('done');
    document.body.dataset.readyMs = Math.round(performance.now());     // start-up time (read by tests)
    setTimeout(() => $('#loading').remove(), 400);
    applyHash(); _hashOn = true;
    DataSource.watch(applyNewData);
    // road paths for every car — after the first paint, never blocks start-up
    idle(() => loadRoads().then(r => { if (r) { computeNow(); render(); if (S.sel >= 0 && S.panel === 'vehicles') updateVehLive(); } })
      .catch(e => showErr('roads', e)));
    if (location.search.includes('refreshtest')) DataSource.reload().then(applyNewData).then(refreshtestDone);
    if (location.search.includes('selftest')) selftest();
    else startDepots();
    if (location.search.includes('asktest')) whenDepots(asktest);
    if (location.search.includes('triptest')) triptest();
    if (location.search.includes('layertest')) layertest();
    if (location.search.includes('roadtest')) roadtest();
    if (location.search.includes('followtest')) followtest();
    if (location.search.includes('clocktest')) clocktest();
    if (location.search.includes('cleartest')) cleartest();
    if (location.search.includes('layoutdump')) setTimeout(layoutdump, 3000);
    const lt = new URLSearchParams(location.search).get('livetest');
    if (lt != null) startLiveTest(+lt || 1);
    const ask = new URLSearchParams(location.search).get('ask');    // link that opens the assistant with a question
    if (ask) Agent.detect().then(m => { Chat.badge(m); Chat.open(ask); });
  } catch (e) {
    console.error(e);
    $('#loading').classList.add('failed');
    msg.innerHTML = `<b>Could not load the data.</b><br>${esc(e.message)}<br><span class="muted">Use a recent Chrome or Edge with an internet connection (for the map).</span>`;
  }
})();

/* new data arrived (live): rebuild everything, keep what the user is looking at
   live → the live clock runs on into the new data · history → stay at the same clock time · selected car kept by VIN */
async function applyNewData(data) {
  const wasLive = isLive(), oldT0 = t0ms, abs = t => oldT0 + t * 1000;
  const keep = { T: abs(S.T), a: abs(S.a), b: abs(S.b), full: S.a === 0 && S.b === D.meta.tmax,
    vin: S.sel >= 0 ? D.vehicles.vin[S.sel] : null, playing: S.playing };
  setPlaying(false);
  prepare(data);
  // everything derived from the old columns
  COLORS = null; RANGE_DATA = null; RANGE_VER = -1; NLU._plates = null; NLU._gaz = null;
  _allStays.clear(); _homes.clear(); _parkedNow = { key: '', list: [] }; _selStays = { key: '', list: [] }; TRIP = null;
  ROADS = null; _roadLegs.clear(); delete window.TAXI_ROADS; idle(() => loadRoads().then(() => { computeNow(); render(); }));
  staysKey = ''; NIGHT_WIN = null; NEARDEP = null; DEPOTS = []; _zoneCache = { zone: null }; _areaCache.clear();
  pcToProv = new Map(PROV.map((p, i) => [p.pc, i]));
  pcToDist = new Map(DIST.map((d, i) => [d.pc, i]));
  const rel = ms => Math.max(0, Math.min(D.meta.tmax, (ms - t0ms) / 1000));
  if (!keep.full) { S.a = rel(keep.a); S.b = rel(keep.b); }
  S.sel = keep.vin ? D.vehicles.vin.indexOf(keep.vin) : -1;
  rebuildMask(); buildTimelineBins(); buildZoneGeo(); buildPresets();
  $('#subtitle').textContent = `${fmt(NV)} vehicles · ${fDT(0)} – ${fDT(D.meta.tmax)}`;
  // live: the clock carries on from the same moment (no jump) unless it fell more than two batches behind
  if (wasLive) { liveAnchor(Math.max(rel(keep.T), D.meta.tmax - 2 * CFG.LIVE_LAG_SEC)); S.T = LC.T0; }
  else S.T = Math.max(S.a, Math.min(S.b, rel(keep.T)));                    // before refresh: it computes 'now' at S.T
  refresh('filter');
  setT(S.T, wasLive);
  if (keep.playing) setPlaying(true);
  startDepots();
  toast(`Data updated · latest ${fDT(D.meta.tmax)}`);
}
function toast(msg) {
  const t = $('#toast'); t.textContent = msg; t.hidden = false;
  clearTimeout(toast._h); toast._h = setTimeout(() => t.hidden = true, 4000);
}
