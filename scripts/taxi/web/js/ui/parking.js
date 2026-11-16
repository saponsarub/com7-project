/* js/ui/parking.js — Overnight panel: where vehicles sleep (00:00–05:00) · depots · vehicles parked overnight outside the zone
   Stops are only computed when this panel is opened; depots are found in the background after start-up.
   provides: renderParking() · whenDepots() · startDepots() */

const _depWait = [];
function whenDepots(fn) { depotsReady() ? fn() : _depWait.push(fn); }
function startDepots() {
  idle(async () => {
    const t = performance.now();
    await computeDepotsAsync();
    console.info(`depots: ${DEPOTS.length} in ${Math.round(performance.now() - t)} ms`);
    DIRTY.add('parking'); DIRTY.add('zone'); DIRTY.add('vehicles');
    if (S.panel === 'parking' || S.panel === 'zone' || S.panel === 'vehicles') renderPanel(S.panel);
    if (S.panel === 'parking') render();
    _depWait.splice(0).forEach(f => f());
  });
}
const NSEV = { far: 'Upcountry', near: 'Vicinity' };
function renderParking() {
  const el = $('#p-parking');
  if (!depotsReady()) {
    el.innerHTML = `<div class="sec"><div class="loading-row"><span class="spinner"></span> Finding overnight spots and depots…</div></div>`;
    return;
  }
  computeStays();
  let on = 0, out = 0, far = 0, near = 0, dep = 0;
  const rows = [];
  for (const [v, x] of NIGHT) {
    if (S.areas.size && !areaMatchDist(x.d)) continue;
    on++;
    const sev = nightSev(x);
    if (sev === 'in') continue;
    out++; if (sev === 'far') far++; else near++;
    const dp = depotOf(x.lat, x.lon); if (dp) dep++;
    rows.push({ v, x, sev, dp });
  }
  let list = rows;
  if (S.sSev === 'far' || S.sSev === 'near') list = rows.filter(r => r.sev === S.sSev);
  if (S.sSev === 'nodep') list = rows.filter(r => !r.dp);
  list.sort((a, b) => (b.sev === 'far') - (a.sev === 'far') || b.x.night - a.x.night);
  const pk = parkedNow(), byPlace = { charger: 0, depot: 0, home: 0, street: 0 };
  let safe = 0; pk.forEach(r => { byPlace[r.place]++; if (r.cut.safe) safe++; });
  const pkList = (S.pPlace ? pk.filter(r => r.place === S.pPlace) : pk).sort((a, b) => b.stillMin - a.stillMin);
  el.innerHTML = `
    <section class="sec">
      <div class="sec-h"><h3>Parked at ${fHM(S.T)}</h3><span class="muted">${fmt(pk.length)} vehicles · ${fmt(safe)} pass the power-cut check</span></div>
      <div class="field" style="margin-bottom:10px"><span class="lbl">Power-cut rule</span>
        ${segHtml('cutSeg', [['basic', 'Basic · parked / engine off ≥ 10 min'], ['offroad', 'Off-road · also not on a road']], S.cutRule, 'Power-cut rule')}
        <span class="hint">${fmt(pk.filter(r => r.road.cls === 'on').length)} on the road · ${fmt(pk.filter(r => r.road.cls === 'edge').length)} at the road edge (unsure) · ${fmt(pk.filter(r => r.road.cls === 'off').length)} off the road</span></div>
      <div class="pgrid">${Object.entries(PARK_PLACE).map(([k, t]) => `<button type="button" class="pcell ${k}${S.pPlace === k ? ' on' : ''}" data-p="${k}">
        <span class="v num">${fmt(byPlace[k])}</span><span class="k">${t}</span></button>`).join('')}</div>
      <div class="xlist" id="pkList">${pkList.slice(0, 60).map(r => `<button type="button" class="xrow" data-v="${r.v}">
          <span class="ps-dot ${r.cut.safe ? 'ok' : 'no'}" title="${r.cut.safe ? 'Safe to cut power' : 'Do not cut power'}"></span>
          <span><span class="plate">${esc(plateOf(r.v))}</span> <small class="muted">${PARK_PLACE[r.place]} · ${esc(whereOf(r.d))}</small></span>
          <span class="num muted">${fDur(r.stillMin * 60)}</span></button>`).join('') || empty('No parked vehicle in this group.')}</div>
      ${pkList.length > 60 ? `<p class="hint">Longest-parked 60 of ${fmt(pkList.length)}.</p>` : ''}
      <p class="hint">Charger = within ${PARK.CHARGER_KM * 1000} m of an OpenStreetMap charger (not every charger is mapped) · Home = a spot this car slept at · rule-based, not a trained model.</p>
    </section>
    <section class="sec">
      <div class="sec-h"><h3>Overnight</h3></div>
      <p class="hint">A vehicle "sleeps" where it stays put ≥ ${CFG2.NIGHT_MIN_H} h between ${p2(CFG2.NIGHT_H[0])}:00 and ${p2(CFG2.NIGHT_H[1])}:00.
        A depot = ${CFG2.DEPOT_MIN}+ vehicles sleeping within ${CFG2.DEPOT_R_KM * 1000} m. <span class="dot" style="background:var(--green)"></span> inside / <span class="dot" style="background:var(--red)"></span> outside the zone on the map.</p>
      <div class="stats">
        ${stat('Parked overnight', fmt(on), `of ${fmt(AREA.active)} active vehicles`)}
        ${stat('Outside the zone', fmt(out), `upcountry ${fmt(far)} · vicinity ${fmt(near)} · at a depot ${fmt(dep)}`, 'alert')}
      </div>
    </section>
    <section class="sec">
      <div class="sec-h"><h3>Depots</h3><span class="muted">${DEPOTS.length} · ${fmt(DEPOTS.reduce((s, d) => s + d.n, 0))} vehicles</span></div>
      <div class="xlist" id="depList">${DEPOTS.map(dp => {
        const g = Geo.peek(dp.lat, dp.lon), outZ = !inZone(dp.d);
        return `<button type="button" class="xrow two" data-k="${dp.k}" title="${dp.n} vehicles sleep here"><span class="ic depot num">${dp.n}</span>
          <span>${esc(whereOf(dp.d))} ${outZ ? '<span class="sev near">Outside zone</span>' : ''}<small class="muted">${g ? esc(g.short) : 'Click for address'}</small></span></button>`;
      }).join('') || empty('No depot found.')}</div>
    </section>
    <section class="sec">
      <div class="sec-h"><h3>Slept outside the zone</h3><span class="muted">${fmt(list.length)}</span></div>
      ${segHtml('sSeg', [['', 'All'], ['far', 'Upcountry'], ['near', 'Vicinity'], ['nodep', 'Not at a depot']], S.sSev, 'Show')}
      <div class="xlist" id="sList">${list.slice(0, 250).map(r => {
        const g = Geo.peek(r.x.lat, r.x.lon);
        return `<button type="button" class="xrow${r.v === S.sel ? ' on' : ''}" data-v="${r.v}"><span class="sev ${r.sev}">${NSEV[r.sev]}</span>
          <span><span class="plate">${esc(plateOf(r.v))}</span> ${r.dp ? '<span class="sev all">Depot</span>' : ''}
            <small class="muted">${esc(g ? g.short : whereOf(r.x.d))}</small></span>
          <span class="num muted">${fDur(r.x.dur)}</span></button>`;
      }).join('') || empty('No vehicle slept outside the zone with these filters.')}</div>
    </section>`;
  seg($('#sSeg'), v => { S.sSev = v; renderParking(); });
  seg($('#cutSeg'), v => { S.cutRule = v; renderParking(); });
  $$('.pgrid .pcell').forEach(b => b.onclick = () => { S.pPlace = S.pPlace === b.dataset.p ? '' : b.dataset.p; renderParking(); });
  $$('#pkList .xrow').forEach(b => b.onclick = () => selectVehicle(+b.dataset.v, true, 'dim'));
  $$('#depList .xrow').forEach(b => b.onclick = () => {
    const dp = DEPOTS[+b.dataset.k];
    map.flyTo({ center: [dp.lon, dp.lat], zoom: 16, duration: 800 });
    showPlace(dp.lat, dp.lon, `Depot · ${dp.n} vehicles overnight`, whereOf(dp.d));
  });
  $$('#sList .xrow').forEach(b => b.onclick = () => {
    const v = +b.dataset.v, x = NIGHT.get(v);
    map.flyTo({ center: [x.lon, x.lat], zoom: 16, duration: 800 });
    showPlace(x.lat, x.lon, plateOf(v), `Overnight ${fDT(x.s)} – ${fDT(x.e)}`);
  });
}
