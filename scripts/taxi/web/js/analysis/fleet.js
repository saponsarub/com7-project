/* js/analysis/fleet.js — vehicle status at time T + totals per area / per vehicle in the selected range
   uses: filters.js
   provides: lastIdxAt() · computeNow() · NOW · NOWSTAT · computeAreas() · AREA · areaVal() */

function lastIdxAt(v, T) {
  const s = D.vehicles.start[v], n = D.vehicles.count[v];
  if (!n || TT[s] > T) return -1;
  let lo = s, hi = s + n - 1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (TT[m] <= T) lo = m; else hi = m - 1; }
  return lo;
}

/* vehicles online at S.T (last point ≤ STALE_MIN old) that pass the filters
   + in live mode, OFFLINE = the others at their last known position */
let NOW = [], NOWSTAT = { on: 0, hired: 0, mov: 0, park: 0, out: 0 }, OFFLINE = [];
function computeNow() {
  const { pIdx, dIdx } = zoneSets();
  const stale = CFG.STALE_MIN * 60, useDep = S.exDepot && NEARDEP, live = isLive();
  const res = [], off = []; const st = { on: 0, hired: 0, mov: 0, park: 0, out: 0 };
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const i = lastIdxAt(v, S.T);
    if (i < 0) continue;
    if (S.T - TT[i] > stale) { if (live && !(FLG[i] & 2) && areaMatchDist(DI[i])) off.push({ v, i }); continue; }
    if (!areaMatchDist(DI[i])) continue;
    const sx = status(i);
    if (sx !== 'nosig' && !S.status.has(sx)) continue;
    const dI = DI[i];
    const isOut = dI !== 65535 && !(pIdx.has(distProv[dI]) || dIdx.has(dI)) && !(FLG[i] & 2) && !(useDep && NEARDEP[i]);
    st.on++; if (sx === 'hired') st.hired++; else if (sx === 'vacant') st.mov++; else if (sx === 'park') st.park++;
    if (isOut) st.out++;
    const [x, y, h] = interpAt(v, i, S.T);
    res.push({ v, i, st: sx, out: isOut, x, y, h });
  }
  NOW = res; NOWSTAT = st; OFFLINE = off;
}
/* where the car is at time T
   GPS arrives every ~4–5 min, often 1–3 km apart — a straight line between two fixes cuts across blocks
   ("flying cars"), so the car only glides when the next fix is close (≤ CFG.GLIDE_KM, almost surely the same
   road); otherwise it stays on its last fix (which is on a road) until the next one arrives.
   With data/taxi-roads.js loaded every car drives along its road leg instead (roads.js roadPosAt). */
function interpAt(v, i, T) {
  const r = roadPosAt(v, i, T);                                   // road-snapped legs (data/taxi-roads.js)
  if (r) return r;
  let x = POS[2 * i], y = POS[2 * i + 1], h = D.cols.head ? D.cols.head[i] * 360 / 256 : 0;
  const j = i + 1, e = D.vehicles.start[v] + D.vehicles.count[v];
  if (j < e && TT[j] > T && TT[j] <= D.meta.tmax && TT[j] - TT[i] <= CFG.STALE_MIN * 60 && !(FLG[i] & 2) && !(FLG[j] & 2)) {
    const x2 = POS[2 * j], y2 = POS[2 * j + 1], km = hav(x, y, x2, y2);
    if (km > 0.03 && km <= CFG.GLIDE_KM) {
      const f = (T - TT[i]) / (TT[j] - TT[i]);
      h = bearing(x, y, x2, y2); x += (x2 - x) * f; y += (y2 - y) * f;
    }
  }
  return [x, y, h];
}
/* time of the last GPS point at or before index i where the vehicle was moving (-1 = never in the data) */
function lastMovedAt(v, i) {
  const s = D.vehicles.start[v];
  for (let k = i; k >= s; k--) if (!(FLG[k] & 2) && SPD[k] >= CFG.MOVING_KMH) return TT[k];
  return -1;
}

/* totals per area and per vehicle inside [S.a, S.b] */
let AREA = null;
function computeAreas() {
  const nP = PROV.length, nD = DIST.length;
  const vehP = new Uint32Array(nP), vehD = new Uint32Array(nD);
  const lastP = new Int32Array(nP).fill(-1), lastD = new Int32Array(nD).fill(-1);
  const hrsP = new Float64Array(nP), hrsD = new Float64Array(nD);
  const hirP = new Float64Array(nP), hirD = new Float64Array(nD);
  let active = 0, totOn = 0, totHire = 0;
  const vs = new Float64Array(NV * 4);     // km, hired_s, idle_s, online_s
  for (let v = 0; v < NV; v++) {
    const s = D.vehicles.start[v], e = s + D.vehicles.count[v];
    let any = false, px = 0, py = 0, pt = -1;
    for (let i = s; i < e; i++) {
      const t = TT[i];
      if (t < S.a || t > S.b || !MASK[i]) continue;
      any = true;
      const dI = DI[i], du = DUR[i] / 3600, hired = FLG[i] & 1;
      totOn += du; if (hired) totHire += du;
      vs[v * 4 + 3] += DUR[i];
      if (hired) vs[v * 4 + 1] += DUR[i];
      if (SPD[i] < CFG.MOVING_KMH && !hired) vs[v * 4 + 2] += DUR[i];
      if (!(FLG[i] & 2)) {
        const x = POS[2 * i], y = POS[2 * i + 1];
        if (pt >= 0 && t - pt <= 900) { const k = hav(px, py, x, y); if (k / ((t - pt) / 3600 || 1) < 160) vs[v * 4] += k; }
        px = x; py = y; pt = t;
      }
      if (dI === 65535) continue;
      const p = distProv[dI];
      if (lastP[p] !== v) { lastP[p] = v; vehP[p]++; }
      if (lastD[dI] !== v) { lastD[dI] = v; vehD[dI]++; }
      hrsP[p] += du; hrsD[dI] += du;
      if (hired) { hirP[p] += du; hirD[dI] += du; }
    }
    if (any) active++;
  }
  AREA = { vehP, vehD, hrsP, hrsD, hirP, hirD, active, util: totOn ? totHire / totOn : NaN };
  VSTAT = vs;
}
function areaVal(level, idx, metric = S.metric) {
  const A = AREA;
  if (level === 'prov') return metric === 'veh' ? A.vehP[idx] : metric === 'hrs' ? A.hrsP[idx] : A.hirP[idx];
  return metric === 'veh' ? A.vehD[idx] : metric === 'hrs' ? A.hrsD[idx] : A.hirD[idx];
}
