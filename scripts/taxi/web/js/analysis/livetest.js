/* js/analysis/livetest.js — LIVE TEST: replay the last hour of the data as if it were arriving live, and score predictions
   ─ the feed ─────────────────────────────────────────────────────────────────────────────────────────────────
   The last hour is held back. "Now" starts 1 h before the end of the data and moves with the wall clock (×1 = real
   time · ×10 · ×60 to see results sooner). The data horizon IS D.meta.tmax, so every function — positions, stops,
   routes, the assistant, the predictions — only sees points that have "arrived". Nothing reads past it:
     interpAt / roadPosAt (fleet.js · roads.js) never move a car toward a fix that has not arrived yet.
   ─ the scoring ──────────────────────────────────────────────────────────────────────────────────────────────
   Every 15 data-minutes: for each moving car, record what the app predicts (trip.js tripInfo → next stop estimate
   or direction only) using only data up to then. When the real data arrives, check it:
     • 15 min later — where was the car really? error of 3 simple forecasts of its position:
         stay put · keep going straight at its speed · head toward the estimated destination (estimates only)
     • direction — did it really go that way (±45°, if it moved > 300 m)?
     • destination estimate — did it come within 500 m of the estimated place before the end? closest approach
   uses: fleet.js · trip.js · ui/actions.js (refresh · setT)
   provides: SIM · startLiveTest() · stopLiveTest() · LT · ltSummary() · ltRowsFor() · downloadLiveTestCSV() */

const SIM = { on: false, done: false, speed: 1, realTmax: 0, h0: 0, wall0: 0, timer: 0, lastFull: 0 };
const LT = { rounds: [], every: 15 * 60, look: 15 * 60, reachKm: 0.5, dirDeg: 45, minMoveKm: 0.3 };

function startLiveTest(speed = 1) {
  if (SIM.on) stopLiveTest(false);
  if (!SIM.realTmax) SIM.realTmax = D.meta.tmax;
  Object.assign(SIM, { on: true, done: false, speed, h0: SIM.realTmax - 3600, wall0: Date.now(), lastFull: 0 });
  LT.rounds = [];
  setHorizon(SIM.h0, true);
  ltSnapshot(SIM.h0);
  clearInterval(SIM.timer);
  SIM.timer = setInterval(simTick, 1000);
  toast(`Live test: the last hour (${fHM(SIM.h0)}–${fHM(SIM.realTmax)}) now arrives in ${speed === 1 ? 'real time' : '×' + speed}`);
}
function stopLiveTest(restore = true) {
  clearInterval(SIM.timer);
  SIM.on = false;
  if (restore && SIM.realTmax) { setHorizon(SIM.realTmax, true); SIM.realTmax = 0; }
  syncLive();
}
function simTick() {
  const h = Math.min(SIM.realTmax, SIM.h0 + (Date.now() - SIM.wall0) / 1000 * SIM.speed);
  // a full re-analysis (areas · out of zone · panels) is heavier → every 20 s; positions every second
  const full = Date.now() - SIM.lastFull > 20000 || h >= SIM.realTmax;
  setHorizon(h, false, full);
  const next = SIM.h0 + LT.rounds.length * LT.every;
  if (h >= next && h < SIM.realTmax) ltSnapshot(next);
  ltEvaluate(h);
  if (S.panel === 'overview') renderLiveTestCard();
  if (h >= SIM.realTmax) { clearInterval(SIM.timer); SIM.done = true; SIM.on = false; ltEvaluate(h, true); syncLive(); renderPanel(S.panel); toast('Live test finished — results in Overview'); }
}
/* move the data horizon; a viewer who was "live" stays live */
function setHorizon(h, first, full = true) {
  const wasLive = first || isLive(), oldH = D.meta.tmax;
  D.meta.tmax = h;
  _allStays.clear(); _homes.clear(); _parkedNow = { key: '', list: [] }; NIGHT_WIN = null; staysKey = '';
  _selStays = { key: '', list: [] }; TRIP = null;
  if (S.b >= oldH - 1 || S.b > h) S.b = h;
  if (S.a > S.b) S.a = 0;
  if (full || first) {
    SIM.lastFull = Date.now();
    buildTimelineBins(); buildPresets();
    refresh('range');
  }
  if (!wasLive) return setT(Math.min(S.T, h));
  if (first) liveAnchor(h - CFG.LIVE_LAG_SEC);                     // the clock runs one batch behind the arriving data
  setT(liveTarget(), true);
}

/* ── predictions ─────────────────────────────────────────────────────────────────────────────── */
function ltSnapshot(t0) {
  const rows = [];
  for (let v = 0; v < NV; v++) {
    const i = lastIdxAt(v, t0);
    if (i < 0 || t0 - TT[i] > CFG.STALE_MIN * 60 || FLG[i] & 2 || SPD[i] < CFG.MOVING_KMH) continue;
    const r = tripInfo(v, t0);
    if (!r || r.stopped || !r.next || r.next.kind === 'data') continue;     // 'data' would mean a leak — never expected
    const [x, y] = interpAt(v, i, t0);
    rows.push({ v, t0, x, y, head: r.head != null ? r.head : 0, kmh: SPD[i], hired: r.hired, kind: r.next.kind,
      dlon: r.next.lon, dlat: r.next.lat, conf: r.next.confidence || '', closest: Infinity, reachedAt: null });
  }
  LT.rounds.push({ t0, rows });
}
function ltEvaluate(H, final = false) {
  for (const R of LT.rounds) for (const p of R.rows) {
    if (p.err == null && H >= p.t0 + LT.look) {
      const T = p.t0 + LT.look, i = lastIdxAt(p.v, T);
      if (i >= 0 && TT[i] > p.t0 && !(FLG[i] & 2)) {
        const ax = POS[2 * i], ay = POS[2 * i + 1], moved = hav(p.x, p.y, ax, ay);
        const go = p.kmh * (TT[i] - p.t0) / 3600;                            // km it would cover at its speed
        const ahead = destPoint(p.x, p.y, p.head, go);
        p.err = { stay: moved, straight: hav(ahead[0], ahead[1], ax, ay) };
        if (p.kind === 'estimate') {
          const dd = hav(p.x, p.y, p.dlon, p.dlat), f = dd ? Math.min(1, go / dd) : 0;
          p.err.toward = hav(p.x + (p.dlon - p.x) * f, p.y + (p.dlat - p.y) * f, ax, ay);
        }
        if (moved >= LT.minMoveKm) {
          const b = bearing(p.x, p.y, ax, ay);
          p.dirOk = Math.abs(((b - p.head + 540) % 360) - 180) <= LT.dirDeg;
        }
      } else if (H >= p.t0 + 2 * LT.look) p.err = { none: true };          // no fix in time to judge
    }
    if (p.kind === 'estimate' && p.reachedAt == null) {
      const s = D.vehicles.start[p.v], e = s + D.vehicles.count[p.v];
      for (let k = lastIdxAt(p.v, p.t0) + 1; k < e && TT[k] <= H; k++) {
        if (FLG[k] & 2) continue;
        const d = hav(POS[2 * k], POS[2 * k + 1], p.dlon, p.dlat);
        if (d < p.closest) p.closest = d;
        if (d <= LT.reachKm) { p.reachedAt = TT[k]; break; }
      }
    }
  }
}
function destPoint(lon, lat, deg, km) {
  const r = km / 6371, b = deg * Math.PI / 180, la = lat * Math.PI / 180, lo = lon * Math.PI / 180;
  const la2 = Math.asin(Math.sin(la) * Math.cos(r) + Math.cos(la) * Math.sin(r) * Math.cos(b));
  const lo2 = lo + Math.atan2(Math.sin(b) * Math.sin(r) * Math.cos(la), Math.cos(r) - Math.sin(la) * Math.sin(la2));
  return [lo2 * 180 / Math.PI, la2 * 180 / Math.PI];
}
/* median() comes from parkstate.js */
function ltSummary() {
  const rows = LT.rounds.flatMap(R => R.rows);
  const judged = rows.filter(p => p.err && !p.err.none);
  const est = rows.filter(p => p.kind === 'estimate'), dir = rows.filter(p => p.dirOk != null);
  const estJ = est.filter(p => p.reachedAt != null || SIM.done || D.meta.tmax >= p.t0 + 3600);
  return {
    rounds: LT.rounds.length, predictions: rows.length, judged: judged.length,
    stay: median(judged.map(p => p.err.stay)), straight: median(judged.map(p => p.err.straight)),
    toward: median(judged.filter(p => p.err.toward != null).map(p => p.err.toward)),
    towardStay: median(judged.filter(p => p.err.toward != null).map(p => p.err.stay)),
    dirN: dir.length, dirOk: dir.filter(p => p.dirOk).length,
    estN: est.length, estReached: est.filter(p => p.reachedAt != null).length, estFinal: estJ.length,
    estClosest: median(est.filter(p => isFinite(p.closest)).map(p => p.closest)),
    byKind: { estimate: est.length, direction: rows.filter(p => p.kind === 'direction').length },
  };
}
const ltRowsFor = v => LT.rounds.flatMap(R => R.rows.filter(p => p.v === v));
function downloadLiveTestCSV() {
  const q = s => '"' + String(s).replace(/"/g, '""') + '"';
  const f = x => x == null || !isFinite(x) ? '' : x.toFixed(2);
  const lines = [['plate', 'predicted_at', 'kind', 'confidence', 'with_passenger', 'speed_kmh', 'heading', 'dest_lat', 'dest_lon',
    'err15_stay_km', 'err15_straight_km', 'err15_toward_km', 'went_that_way', 'reached_500m_at', 'closest_km'].join(',')];
  for (const p of LT.rounds.flatMap(R => R.rows)) lines.push([q(plateOf(p.v)), fISO(p.t0), p.kind, p.conf, p.hired ? 1 : 0, p.kmh, Math.round(p.head),
    p.kind === 'estimate' ? p.dlat.toFixed(5) : '', p.kind === 'estimate' ? p.dlon.toFixed(5) : '',
    f(p.err && p.err.stay), f(p.err && p.err.straight), f(p.err && p.err.toward), p.dirOk == null ? '' : p.dirOk ? 1 : 0,
    p.reachedAt != null ? fISO(p.reachedAt) : '', f(p.closest)].join(','));
  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'ev7_live_test_predictions.csv'; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
