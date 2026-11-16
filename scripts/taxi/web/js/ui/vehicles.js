/* js/ui/vehicles.js — Vehicles panel: list (sortable) · card of the selected vehicle (status · route · trips · stops)
   provides: renderVehicles() · updateVehLive() · drawSpark() */

/* route shown for the selected car — relative windows end at the timeline cursor */
const TRK_OPTS = [['all', 'Whole selected period'], ['live', 'Up to the cursor'], [3600, 'Last 1 hour'], [3 * 3600, 'Last 3 hours'],
  [6 * 3600, 'Last 6 hours'], [12 * 3600, 'Last 12 hours'], [86400, 'Last 1 day'], [2 * 86400, 'Last 2 days'], [3 * 86400, 'Last 3 days'], [7 * 86400, 'Last 7 days']];
const VEH_SORT = { km: 'Distance', hired: 'Time on trip', idle: 'Parked time', off: 'Offline time' };
function renderVehicles() { S.sel >= 0 ? renderVehCard() : renderVehList(); }

function renderVehList() {
  const el = $('#p-vehicles');
  el.innerHTML = `
    <div class="sec">
      <div class="vsearch"><span class="ic">${ICON.search}</span>
        <input id="vehQ" type="search" placeholder="Type a plate or VIN — e.g. ทอ 9027" value="${esc(S.vehQ)}" autocomplete="off" spellcheck="false" aria-label="Find a vehicle by plate or VIN"></div>
      <div class="sec-h"><h3 id="vehN"></h3>
        <label class="inline">Sort by <select id="vehSort">${Object.entries(VEH_SORT).map(([k, t]) => `<option value="${k}"${k === S.vehSort ? ' selected' : ''}>${t}</option>`).join('')}</select></label></div>
      <p class="hint">Dot = status at ${fHM(S.T)} · pick a vehicle to see only it on the map, its trip and a replay.</p>
      <div class="vlist" id="vehList" role="list"></div>
      <p class="hint" id="vehMore"></p>
    </div>`;
  const q = $('#vehQ');
  q.oninput = () => { S.vehQ = q.value; drawVehRows(); };
  q.onkeydown = e => { if (e.key === 'Enter') { const b = $('#vehList .vrow'); if (b) b.click(); } };
  $('#vehSort').onchange = e => { S.vehSort = e.target.value; drawVehRows(); };
  drawVehRows();
}
function drawVehRows() {
  const key = S.vehQ.replace(/[\s-]/g, '').toLowerCase(), V = D.vehicles;
  const rows = [];
  for (let v = 0; v < NV; v++) {
    if (key) { if (!V.plate[v].replace(/[\s-]/g, '').toLowerCase().includes(key) && !V.vin[v].toLowerCase().includes(key)) continue; }
    else if (!vehPass(v)) continue;
    const onl = VSTAT[v * 4 + 3];
    if (!key && S.areas.size && !onl) continue;
    rows.push({ v, km: VSTAT[v * 4], hired: VSTAT[v * 4 + 1], idle: VSTAT[v * 4 + 2], off: (S.b - S.a) - onl });
  }
  rows.sort((a, b) => b[S.vehSort] - a[S.vehSort]);
  const now = new Map(NOW.map(x => [x.v, x]));
  $('#vehN').textContent = `${fmt(rows.length)} vehicle${rows.length === 1 ? '' : 's'}${key ? ' found' : ''}`;
  $('#vehList').innerHTML = rows.slice(0, 200).map(r => {
    const nw = now.get(r.v), c = nw ? COL[nw.st] : [214, 220, 217];
    const val = S.vehSort === 'km' ? fmt1(r.km) + ' km' : fDur(r[S.vehSort]);
    return `<button type="button" class="vrow" data-v="${r.v}" role="listitem"><i class="dot" style="background:rgb(${c})"></i>
      <span><span class="plate">${esc(plateOf(r.v))}</span> <small class="muted">${esc(centerName(V.center[r.v]))}</small></span>
      <span class="num muted">${val}</span></button>`;
  }).join('') || empty(key ? 'No vehicle with that plate or VIN.' : 'No vehicles match the filters.');
  $('#vehMore').textContent = rows.length > 200 ? 'Showing the top 200 — type a plate to find any vehicle.' : '';
  $$('#vehList .vrow').forEach(x => x.onclick = () => selectVehicle(+x.dataset.v, true, 'hide'));
}

function renderVehCard() {
  const el = $('#p-vehicles');
  const v = S.sel, V = D.vehicles;
  const km = VSTAT[v * 4], hir = VSTAT[v * 4 + 1], idle = VSTAT[v * 4 + 2], onl = VSTAT[v * 4 + 3];
  const s = V.start[v], n = V.count[v];
  let mx = 0; const provs = new Map();
  for (let i = s; i < s + n; i++) {
    if (TT[i] < S.a || TT[i] > S.b) continue;
    mx = Math.max(mx, SPD[i]);
    if (DI[i] !== 65535) { const p = distProv[DI[i]]; provs.set(p, (provs.get(p) || 0) + DUR[i]); }
  }
  const pv = [...provs.entries()].sort((a, b) => b[1] - a[1]);
  const xs = (EXC_BY_V.get(v) || []).slice().sort((a, b) => a.s - b.s);
  const st = selStays().slice().sort((a, b) => a.s - b.s);
  el.innerHTML = `
    <button type="button" class="back" id="vehBack">${ICON.back} All vehicles</button>
    <div class="vcard">
      <div class="vhead"><div><div class="plate big">${esc(plateOf(v))}</div>
        <div class="muted small">${esc(centerName(V.center[v]))} · VIN <span class="num">${esc(V.vin[v])}</span></div></div></div>
      <div class="live" id="vehLive"></div>
      <div class="field"><span class="lbl">Other vehicles on the map</span>
        ${segHtml('othSeg', [['hide', 'Only this car'], ['dim', 'Others faded']], S.others, 'Other vehicles')}</div>
      <div class="pstate" id="vehPark"></div>
      <div class="trip" id="vehTrip"></div>
      <dl class="kv">
        <dt>Distance</dt><dd class="num">${fmt1(km)} km</dd>
        <dt>Online</dt><dd class="num">${fDur(onl)}</dd>
        <dt>On trip</dt><dd class="num">${fDur(hir)} <span class="muted">(${onl ? pct(hir / onl) : '–'})</span></dd>
        <dt>Parked</dt><dd class="num">${fDur(idle)}</dd>
        <dt>Top speed</dt><dd class="num">${mx} km/h</dd>
      </dl>
      <label class="field"><span class="lbl">Route on the map</span>
        <select id="trkSel">${TRK_OPTS.map(([v, t]) => {
          const tooLong = typeof v === 'number' && v > D.meta.tmax + 3600;
          return `<option value="${v}"${String(v) === String(S.trk) ? ' selected' : ''}${tooLong ? ' disabled' : ''}>${t}${tooLong ? ` (data covers ${fDur(D.meta.tmax)})` : ''}</option>`;
        }).join('')}</select>
        <span class="hint">${isLive() ? `Live: the last ${LIVE_TRACK_SEC / 3600} h driven, dotted (this setting applies in History).`
          : 'Solid = driven up to the cursor · dotted = still ahead. '}${isLive() ? '' : typeof S.trk === 'number' ? `From ${fDT(Math.max(0, S.T - S.trk))} to the cursor (${fDT(S.T)}) — moves with the timeline.`
          : S.trk === 'live' ? 'Up to the cursor — press play and the route grows with the car.' : '○ start · ■ end of the period · chevrons = direction'}</span></label>
      <p class="hint" id="snapHint"></p>
      <div class="field"><span class="lbl">Speed over time <span class="key-blue">■</span> on trip</span><canvas class="spark" id="spark" aria-label="Speed chart"></canvas></div>
      <p class="small"><span class="muted">Provinces</span> ${pv.map(([p, sec]) => `${esc(provName(p))} <span class="muted num">${fDur(sec)}</span>`).join(' · ') || '–'}</p>
      <button type="button" class="btn" id="vehAddr">${ICON.pin} Address at ${fHM(S.T)}</button>
    </div>
    <section class="sec">
      <div class="sec-h"><h3>Out-of-zone trips</h3><span class="muted">${xs.length} · click to jump</span></div>
      <div class="xlist">${xs.map((x, k) => `<button type="button" class="xrow" data-t="${x.s}"><span class="sev ${x.allOut ? 'all' : x.sev}">${k + 1}</span>
        <span>${fDT(x.s)} – ${fDay(x.s) === fDay(x.e) ? fHM(x.e) : fDT(x.e)}<small class="muted">${[...x.provs.keys()].map(p => esc(provName(p))).join(' · ')}</small></span>
        <span class="num">${fDur(x.dur)}</span></button>`).join('') || empty('Stayed inside the zone in this period.')}</div>
    </section>
    <section class="sec">
      <div class="sec-h"><h3>Stops ≥ ${CFG2.STAY_MIN} min</h3><span class="muted">${st.length} · ${ICON.moon} = overnight</span></div>
      <div class="xlist">${st.map((x, k) => {
        const g = Geo.peek(x.lat, x.lon), night = isNight(x), out = !inZone(x.d), dp = depotsReady() && depotOf(x.lat, x.lon);
        return `<button type="button" class="xrow" data-k="${k}"><span class="ic${night ? ' night' : ''}${out ? ' out' : ''}">${night ? ICON.moon : k + 1}</span>
          <span>${fDT(x.s)} – ${fDay(x.s) === fDay(x.e) ? fHM(x.e) : fDT(x.e)}<small class="muted">${dp ? 'Depot · ' : ''}${esc(g ? g.short : whereOf(x.d))}</small></span>
          <span class="num">${fDur(x.dur)}</span></button>`;
      }).join('') || empty('No long stops in this period.')}</div>
    </section>`;
  $('#vehBack').onclick = () => selectVehicle(-1);
  $('#trkSel').onchange = e => { const x = e.target.value; S.trk = /^\d+$/.test(x) ? +x : x; S.trkFrom = null; renderVehCard(); render(); };
  seg($('#othSeg'), val => { S.others = val; render(); });
  $('#vehTrip').addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.act === 'replay') replayTrip();
    else if (b.dataset.act === 'live') goLive();
    else if (b.dataset.lat) { map.flyTo({ center: [+b.dataset.lon, +b.dataset.lat], zoom: 15, duration: 800 }); showPlace(+b.dataset.lat, +b.dataset.lon, plateOf(v), b.dataset.t); }
  });
  $$('#p-vehicles .xrow[data-t]').forEach(x => x.onclick = () => setT(+x.dataset.t));
  $$('#p-vehicles .xrow[data-k]').forEach(b => b.onclick = () => {
    const x = st[+b.dataset.k];
    setT(x.s);
    map.flyTo({ center: [x.lon, x.lat], zoom: 16, duration: 800 });
    showPlace(x.lat, x.lon, plateOf(v), `Stopped ${fDur(x.dur)} · ${fDT(x.s)}`);
  });
  $('#vehAddr').onclick = () => {
    const i = lastIdxAt(v, S.T);
    if (i < 0 || FLG[i] & 2) return;
    const la = POS[2 * i + 1], lo = POS[2 * i];
    map.flyTo({ center: [lo, la], zoom: 16, duration: 800 });
    showPlace(la, lo, plateOf(v), `${fDT(TT[i])} · ${SPD[i]} km/h`);
  };
  updateVehLive();
}
/* the part of the card that follows the timeline cursor (also during playback) */
function updateVehLive() {
  const box = $('#vehLive'); if (!box) return;
  const v = S.sel, i = lastIdxAt(v, S.T);
  const on = i >= 0 && S.T - TT[i] <= CFG.STALE_MIN * 60;
  const lm = i >= 0 ? lastMovedAt(v, i) : -1;
  const moved = lm >= 0 ? `<br><span class="muted">Last moved ${fDT(lm)}${S.T - lm > 120 ? ` · ${fDur(S.T - lm)} ago` : ''}</span>` : '';
  const mode = isLive() ? '<span class="tag live">LIVE</span>' : '<span class="tag">History</span>';
  if (!on) box.innerHTML = `<i class="dot" style="background:rgb(${COL.nosig})"></i><span>${mode} <b>Offline</b> at ${fHM(S.T)}${i >= 0 ? `<br>Last seen ${fDT(TT[i])} · ${esc(whereOf(DI[i]))}` : ''}${moved}</span>`;
  else {
    const st = status(i), out = DI[i] !== 65535 && !inZone(DI[i]) && !(FLG[i] & 2);
    box.innerHTML = `<i class="dot" style="background:rgb(${COL[st]})"></i><span>${mode} <b>${STATUS_LABEL[st]}</b> · ${SPD[i]} km/h at ${fHM(S.T)}<br>${esc(whereOf(DI[i]))}${out ? ' <span class="sev far">Outside zone</span>' : ''}${st === 'park' ? moved : ''}</span>`;
  }
  const b = $('#vehAddr'); if (b) b.lastChild.textContent = ` Address at ${fHM(S.T)}`;
  renderTrip(v);
  renderParkState(v);
  const sh = $('#snapHint');
  if (sh) { const rl = roadLegsFor(v), st = Router.tracks.get(v), snap = rl || Router.trackPeek(v);
    sh.textContent = rl ? `Route along roads (own GraphHopper · OpenStreetMap): ${rl.legs.size} road legs.`
      : snap ? `Route drawn along roads (OSRM · OpenStreetMap): ${snap.legs.size} of ${Math.max(0, snap.kept.length - 1)} legs matched — the rest straight.`
      : st ? 'Fitting the route to roads…' : ''; }
  drawSpark(v);
}
/* parked where (charger · depot · home · street) + can the power be cut safely now — decision support only */
function renderParkState(v) {
  const el = $('#vehPark'); if (!el) return;
  const r = parkState(v);
  if (r.state === 'nodata') { el.innerHTML = ''; return; }
  const st = { parked: 'Parked', stopped: 'Stopped', moving: 'Moving', offline: 'Offline' }[r.state];
  const dl = r.detail;
  const where = r.place === 'charger' ? `${PARK_PLACE.charger} · ${esc(dl.name)}${dl.op ? ' (' + esc(dl.op) + ')' : ''} · ${dl.m} m`
    : r.place === 'depot' ? `${PARK_PLACE.depot} · ${dl.n} vehicles sleep here`
    : r.place === 'home' ? `${PARK_PLACE.home} · slept here ${dl.nights} night${dl.nights > 1 ? 's' : ''}`
    : PARK_PLACE.street;
  const c = r.cut;
  const html = `<span class="lbl">Parking &amp; power cut</span>
    ${r.state === 'moving' ? '' : `<div class="ps-row"><span class="ps-chip ${r.place}">${esc(where)}</span></div>`}
    <div class="ps-facts">${st}${r.since != null && r.state !== 'moving' ? ` ${fDur(r.parkedMin * 60)} (since ${fHM(r.since)})` : ''} · engine ${r.eng}${r.offMin >= 1 ? ` (off ${fDur(r.offMin * 60)})` : ''}${r.hired ? ' · passenger' : ''}</div>
    ${r.state === 'moving' ? '' : `<div class="ps-road ${r.road.cls}"><b>${ROAD_LABEL[r.road.cls]}</b>${r.road.m != null ? ` · ≈${r.road.m} m from the road edge${r.road.name ? ` (${esc(r.road.name)})` : ''}` : ''}<small>${r.road.n ? `median of ${r.road.n} GPS point${r.road.n > 1 ? 's' : ''} while standing · margin ±${r.road.tol} m for GPS / rounding` : ''}</small></div>`}
    <div class="field"><span class="lbl">Power-cut rule</span>${segHtml('cutSeg', [['basic', 'Basic'], ['offroad', 'Off-road only']], S.cutRule, 'Power-cut rule')}</div>
    <div class="ps-cut ${c.safe ? 'ok' : 'no'}"><b>${c.safe ? 'Safe to cut power' : 'Do not cut power'}</b>${c.safe ? ` <small>${c.conf} confidence</small>` : ''}
      <ul>${(c.safe ? c.caution : c.no).map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>
    <p class="hint">Rule-based check — the monitor never sends commands. Cut power only through the telematics system, by an authorised person.</p>`;
  if (el._h !== html) {
    el.innerHTML = html; el._h = html;
    seg($('#cutSeg'), val => { S.cutRule = val; DIRTY.add('parking'); renderParkState(v); });
  }
}
/* trip block: From (last stop) → Now → Next stop (from the data) or likely destination (estimate) */
function renderTrip(v) {
  const el = $('#vehTrip'); if (!el) return;
  const r = updateTrip();
  const place = (x, label) => `<button type="button" class="link" data-lat="${x.lat}" data-lon="${x.lon}" data-t="${esc(label)}">${esc(addrOr(x))}</button>`;
  const btns = `<div class="trip-act">${r && (r.origin || r.stopped) ? `<button type="button" class="btn sm" data-act="replay">${ICON.play} Replay this trip</button>` : ''}
    ${isLive() ? '' : `<button type="button" class="btn sm" data-act="live"><i class="live-dot"></i> Back to live</button>`}</div>`;
  if (!r) { el.innerHTML = `<span class="lbl">Trip</span><p class="hint">No GPS data before ${fDT(S.T)}.</p>`; return; }
  let h = '<span class="lbl">Trip</span><ol class="steps">';
  if (r.stopped) {
    const x = r.stop;
    h += `<li class="st-a"><b>Parked</b> at ${place(x, 'Parked since ' + fDT(x.s))}<small>since ${fDT(x.s)} · ${fDur(S.T - x.s)}${isNight(x) ? ' · overnight stop' : ''}</small></li>`;
  } else {
    h += r.origin
      ? `<li class="st-a"><b>From</b> ${place(r.origin, 'Left ' + fDT(r.origin.e))}<small>left ${fDT(r.origin.e)} · ${fDur(S.T - r.origin.e)} ago</small></li>`
      : `<li class="st-a"><b>From</b> <span class="muted">before the data starts</span></li>`;
    h += `<li class="st-now"><b>Now</b> ${esc(whereOf(r.here.d))}<small>${fmt1(r.km)} km since${r.head != null && SPD[r.i] >= CFG.MOVING_KMH ? ` · heading ${compass(r.head)}` : ''}${r.hired ? ' · with a passenger' : ''}</small></li>`;
    const n = r.next;
    const rt = n ? Router.peek({ lon: r.here.lon, lat: r.here.lat }, { lon: n.lon, lat: n.lat }) : null;
    const road = rt ? ` · <b>${fmt1(rt.km)} km by road</b>, ~${Math.max(1, Math.round(rt.min))} min without traffic` : '';
    if (!n) h += `<li class="st-b"><b>Next</b> <span class="muted">not moving — no direction to estimate</span></li>`;
    else if (n.kind === 'data') h += `<li class="st-b"><b>Next stop</b> ${place(n, 'Stopped ' + fDT(n.at))}<small>arrives ${fDT(n.at)} · stays ${fDur(n.dur)} · from the data${road}</small></li>`;
    else if (n.kind === 'estimate') h += `<li class="st-q"><b>Likely to</b> ${place(n, 'Estimated destination')}<small>~${fmt1(n.km)} km ahead · a place this car stopped ${n.visits}×${n.overnight ? ' (incl. overnight)' : ''} · estimate, ${n.confidence} confidence${road}</small></li>`;
    else h += `<li class="st-q"><b>Heading</b> ${n.compass} towards ${esc(whereOf(n.d))}<small>${r.hired ? 'with a passenger the destination is unknown' : 'no regular stop of this car ahead'} — direction only${road}</small></li>`;
  }
  const lt = typeof ltRowsFor === 'function' ? ltRowsFor(v) : [];
  if (lt.length) h += '</ol><span class="lbl">Live test · predictions for this car</span><ul class="lt-list">' + lt.map(p => {
    const what = p.kind === 'estimate' ? 'likely destination' : `heading ${compass(p.head)}`;
    const res = p.kind === 'estimate' ? (p.reachedAt != null ? `<b class="ok">reached ${fHM(p.reachedAt)}</b>` : isFinite(p.closest) ? `closest ${fmt1(p.closest)} km` : 'pending')
      : p.dirOk == null ? (p.err ? 'did not move far' : 'pending') : p.dirOk ? '<b class="ok">went that way</b>' : '<b class="no">went another way</b>';
    return `<li>${fHM(p.t0)} · ${what} → ${res}</li>`;
  }).join('') + '</ul><ol class="steps" hidden>';
  const html = h + '</ol>' + (r.next && !r.stopped ? '<p class="hint">Dashed line = route along roads (OSRM · OpenStreetMap); straight while loading or if routing is unavailable.</p>' : '') + btns;
  if (el._h !== html) { el.innerHTML = html; el._h = html; }          // playback calls this every frame
}
const addrOr = x => { const g = Geo.peek(x.lat, x.lon); return g ? g.short : whereOf(x.d); };
/* replay: jump to when the car left its last stop and play with the route growing behind it */
function replayTrip() {
  const r = updateTrip(); if (!r) return;
  let start = typeof S.trk === 'number' ? S.T - S.trk : r.stopped ? r.stop.s - 1800 : r.origin ? r.origin.e - 300 : TT[r.i] - 3600;
  start = Math.max(0, start);
  if (start < S.a) { S.a = 0; refresh('range'); }
  S.trk = 'live'; S.trkFrom = start; $('#trkSel').value = 'live';
  S.follow = true;
  S.speed = Math.min(S.speed, 600); $('#speed').value = String(S.speed);
  setT(start);
  setPlaying(true);
}
function drawSpark(v) {
  const cv = $('#spark'); if (!cv) return;
  const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  if (!w) return;
  if (cv.width !== w * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0);
  const s = D.vehicles.start[v], n = D.vehicles.count[v], span = Math.max(1, S.b - S.a);
  c.fillStyle = '#f4f7f5'; c.fillRect(0, 0, w, h);
  for (let i = s; i < s + n; i++) {
    if (TT[i] < S.a || TT[i] > S.b) continue;
    const x = (TT[i] - S.a) / span * w, y = h - Math.min(1, SPD[i] / 120) * (h - 4);
    c.fillStyle = FLG[i] & 1 ? '#f08c00' : '#9db3a8';
    c.fillRect(x, y, Math.max(1, w / 400), h - y);
  }
  const x = (S.T - S.a) / span * w; c.fillStyle = '#10231a'; c.fillRect(x - .5, 0, 1, h);
}
