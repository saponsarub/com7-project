/* js/ui/away.js — "Outside BKK" panel: vehicles that are outside Bangkok + vicinity right now and have been for longer than X hours,
   counted back from the timeline cursor (S.T). Same rule as the daily LINE alert (scripts/taxi/outzone.py, which uses 120 h):
     · the clock starts at the first point outside the zone after the vehicle was last inside
     · it only counts as back inside after AWAY.RETURN_N points in a row inside the zone (one GPS jump does not reset it)
     · gaps in the data (engine off · GPS removed) do not reset the clock — the vehicle still counts as outside
     · points without a GPS fix are ignored
   Uses all history up to the cursor (not only the selected period).
   provides: computeAway() · renderAway() · AWAY · setAwayBadge() */

const AWAY = { RETURN_N: 2, HOURS: [[1, '1 h'], [5, '5 h'], [24, '24 h'], [120, '5 days']] };
let AWAY_ROWS = [], _awayKey = '', _metroOk = null;

function metroAllowed() {           // district idx → 1 if inside Bangkok + vicinity (fixed — not the Zone panel's setting)
  if (_metroOk) return _metroOk;
  const p = new Set(CFG.ZONES.metro.prov.map(pc => PROV.findIndex(x => x.pc === pc)));
  _metroOk = new Uint8Array(DIST.length);
  for (let j = 0; j < DIST.length; j++) _metroOk[j] = p.has(distProv[j]) ? 1 : 0;
  return _metroOk;
}
function computeAway() {
  const key = `${S.T}|${S.awayH}|${[...S.centers].join(',')}`;
  if (key === _awayKey) return AWAY_ROWS;
  const ok = metroAllowed(), T = S.T, lim = S.awayH * 3600, stale = CFG.STALE_MIN * 60;
  const rows = [];
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const s = D.vehicles.start[v], e = lastIdxAt(v, T);     // lastIdxAt: analysis/fleet.js
    if (e < 0) continue;
    let since = -1, run = 0, seenIn = false, firstOut = false, last = -1;
    for (let i = s; i <= e; i++) {
      if (FLG[i] & 2 || DI[i] === 65535) continue;
      last = i;
      if (ok[DI[i]]) { seenIn = true; if (++run >= AWAY.RETURN_N) since = -1; }
      else { run = 0; if (since < 0) { since = TT[i]; firstOut = !seenIn; } }
    }
    if (since < 0 || last < 0 || T - since <= lim) continue;
    rows.push({ v, since, sec: T - since, last, lastT: TT[last], d: DI[last], firstOut, offline: T - TT[last] > stale });
  }
  rows.sort((a, b) => b.sec - a.sec);
  _awayKey = key; AWAY_ROWS = rows;
  return rows;
}
function fAway(sec) {
  const h = Math.floor(sec / 3600), d = Math.floor(h / 24);
  return d ? `${d} d ${h % 24} h` : fDur(sec);
}
function setAwayBadge() {
  const b = $('#awayBadge'); if (!b) return;
  const n = computeAway().length;
  b.textContent = !n ? '' : n < 1000 ? String(n) : (n / 1000).toFixed(1) + 'k';
  b.title = `${fmt(n)} vehicles outside Bangkok + vicinity for more than ${S.awayH} h`;
}
function renderAway() {
  const el = $('#p-away');
  const rows = computeAway();
  const off = rows.filter(r => r.offline).length;
  const cnt = new Map();
  rows.forEach(r => { const p = r.d === 65535 ? -1 : distProv[r.d]; cnt.set(p, (cnt.get(p) || 0) + 1); });
  el.innerHTML = `
    <section class="sec">
      <p class="hint">Vehicles outside <b>Bangkok + vicinity</b> (Bangkok · Nonthaburi · Pathum Thani · Samut Prakan · Samut Sakhon · Nakhon Pathom)
        for longer than the limit, counted back from <b>${fDT(S.T)}</b>. Gaps in the data do not reset the clock;
        ${AWAY.RETURN_N} GPS points in a row inside the zone do.</p>
      <div class="field"><span class="lbl">Outside for more than</span>
        ${segHtml('awaySeg', AWAY.HOURS, S.awayH, 'Outside for more than')}</div>
    </section>
    <section class="sec">
      <div class="stats">
        ${stat('Vehicles', fmt(rows.length), `outside for more than ${AWAY.HOURS.find(h => h[0] === S.awayH)[1]}`, 'alert')}
        ${stat('No signal now', fmt(off), `last GPS point older than ${CFG.STALE_MIN} min`)}
      </div>
    </section>
    <section class="sec">
      <div class="sec-h"><h3>Longest outside first</h3>
        <button type="button" class="btn sm" id="awayCsv" title="One row per vehicle">${ICON.download} CSV</button></div>
      <div class="xlist" id="awayList">${rows.slice(0, 300).map(r => `<button type="button" class="xrow${r.v === S.sel ? ' on' : ''}" data-v="${r.v}">
          <span class="sev far" title="Outside since ${fDT(r.since)}">${fAway(r.sec)}</span>
          <span><span class="plate">${esc(plateOf(r.v))}</span>${r.offline ? ' <span class="sev all" title="No GPS point since ' + fDT(r.lastT) + '">No signal</span>' : ''}
            <small class="muted">${esc(whereOf(r.d))} · since ${r.firstOut ? 'at least ' : ''}${fDT(r.since)}</small></span>
          <span class="num muted" title="Last GPS point">${fDay(r.lastT) === fDay(S.T) ? fHM(r.lastT) : fDT(r.lastT)}</span></button>`).join('')
        || empty(`No vehicle has been outside Bangkok + vicinity for more than ${AWAY.HOURS.find(h => h[0] === S.awayH)[1]} at ${fDT(S.T)}.`)}</div>
      ${rows.length > 300 ? `<p class="hint">Showing 300 of ${fmt(rows.length)} — download the CSV for all.</p>` : ''}
      <p class="hint">"at least" = never seen inside the zone in the data, so the real time outside may be longer.</p>
    </section>
    <section class="sec">
      <div class="sec-h"><h3>Where they are</h3><span class="muted">vehicles · last known province</span></div>
      <div class="bars" id="awayProv"></div>
    </section>`;
  barsInto($('#awayProv'), [...cnt.entries()].filter(e => e[0] >= 0).sort((a, b) => b[1] - a[1]).slice(0, 8)
    .map(([p, n]) => ({ key: 'p:' + p, name: provName(p), val: n, txt: fmt(n) })), { red: true, empty: 'No vehicle.' });
  seg($('#awaySeg'), v => { S.awayH = +v; renderAway(); setAwayBadge(); });
  $('#awayCsv').onclick = () => awayCSV(rows);
  $$('#awayList .xrow').forEach(b => b.onclick = () => selectVehicle(+b.dataset.v, true, 'hide'));
}
function awayCSV(rows) {
  const q = s => '"' + String(s).replace(/"/g, '""') + '"';
  const lines = [['plate', 'vin', 'center', 'outside_since', 'hours_outside', 'since_is_first_seen', 'last_gps', 'no_signal', 'last_area'].join(',')];
  rows.forEach(r => lines.push([q(plateOf(r.v)), D.vehicles.vin[r.v], D.vehicles.center[r.v], fISO(r.since), (r.sec / 3600).toFixed(1),
    r.firstOut ? 1 : 0, fISO(r.lastT), r.offline ? 1 : 0, q(whereOf(r.d))].join(',')));
  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = `ev7_outside_bkk_${S.awayH}h_${fISO(S.T).replace(/[\s:]/g, '')}.csv`; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
