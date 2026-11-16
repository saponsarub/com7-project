/* js/analysis/stays.js — stops · overnight stops · depots (same logic as build_dashboard.find_depots)
   uses: filters.js · utils.js
   provides: staysOf() · isNight() · computeStays() · computeDepots() · computeDepotsAsync() · depotsReady() · depotOf() · nightSev()
             STAYS_BY_V · NIGHT · DEPOTS · NEARDEP */

let NIGHT_WIN = null;
function nightWindows() {
  if (NIGHT_WIN) return NIGHT_WIN;
  const ws = [], m = tDate(0); m.setHours(0, 0, 0, 0);
  for (let ms = m.getTime(); ms <= t0ms + D.meta.tmax * 1000; ms += 86400000) {
    const s = (ms - t0ms) / 1000;
    ws.push([s + CFG2.NIGHT_H[0] * 3600, s + CFG2.NIGHT_H[1] * 3600]);
  }
  return (NIGHT_WIN = ws);
}
/* stops of vehicle v inside [a,b] — anchor = first point of the stop (matches the Python reference) */
function staysOf(v, a = S.a, b = S.b) {
  const NW = nightWindows();
  const R = CFG2.STAY_R_KM, GAP = CFG.GAP_MIN * 60, MIN = CFG2.STAY_MIN * 60;
  const s0 = D.vehicles.start[v], e0 = s0 + D.vehicles.count[v], out = [];
  const ok = k => TT[k] >= a && TT[k] <= b && !(FLG[k] & 2) && DI[k] !== 65535;
  let i = s0;
  while (i < e0) {
    if (!ok(i)) { i++; continue; }
    let j = i, k = i + 1;
    while (k < e0) {
      if (!ok(k)) { k++; continue; }
      if (TT[k] - TT[j] > GAP) break;
      if (hav(POS[2 * i], POS[2 * i + 1], POS[2 * k], POS[2 * k + 1]) > R) break;
      j = k; k++;
    }
    const dur = TT[j] - TT[i];
    if (dur >= MIN) {
      let ov = 0;
      for (const [x, y] of NW) ov = Math.max(ov, Math.max(0, Math.min(TT[j], y) - Math.max(TT[i], x)));
      out.push({ v, i0: i, i1: j, s: TT[i], e: TT[j], dur, night: ov, lon: POS[2 * i], lat: POS[2 * i + 1], d: DI[i] });
    }
    i = j + 1;
  }
  return out;
}
const isNight = x => x.night >= CFG2.NIGHT_MIN_H * 3600;

/* longest overnight stop per vehicle in the selected range — only computed when the Parking panel needs it */
let STAYS_BY_V = new Map(), NIGHT = new Map(), staysKey = '';
function computeStays() {
  const key = [S.a, S.b, [...S.centers].join(), maskVer].join('|');
  if (key === staysKey) return;
  staysKey = key;
  STAYS_BY_V = new Map(); NIGHT = new Map();
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const st = staysOf(v);
    if (!st.length) continue;
    STAYS_BY_V.set(v, st);
    let best = null;
    for (const x of st) if (isNight(x) && (!best || x.night > best.night)) best = x;
    if (best) NIGHT.set(v, best);
  }
}

/* depots: computed once from the whole data range, independent of filters (a real place, not a view)
   computeDepots() = all at once (selftest) · computeDepotsAsync() = in small slices after first paint,
   so the page stays responsive while it runs */
let DEPOTS = [], NEARDEP = null;
const depotsReady = () => !!NEARDEP;
function computeDepots() {
  if (NEARDEP) return;
  for (const _ of depotSteps()) { /* run to the end */ }
}
async function computeDepotsAsync() {
  if (NEARDEP) return;
  let t = performance.now();
  for (const _ of depotSteps()) {
    if (performance.now() - t > 12) { await new Promise(ok => setTimeout(ok, 0)); t = performance.now(); }
  }
}
function* depotSteps() {
  const pts = [];
  for (let v = 0; v < NV; v++) {
    let best = null;
    for (const x of staysOf(v, 0, D.meta.tmax)) if (isNight(x) && (!best || x.night > best.night)) best = x;
    if (best) pts.push(best);
    if (v % 64 === 63) yield;
  }
  const n = pts.length, R = CFG2.DEPOT_R_KM;
  const near = (a, b) => Math.abs(a.lat - b.lat) < 0.003 && hav(a.lon, a.lat, b.lon, b.lat) <= R;
  const dens = new Uint16Array(n);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (near(pts[i], pts[j])) dens[i]++;
  const order = [...Array(n).keys()].sort((x, y) => dens[y] - dens[x] || x - y);
  const lab = new Int32Array(n).fill(-1);
  DEPOTS = [];
  for (const i of order) {
    if (lab[i] >= 0) continue;
    const mem = [];
    for (let j = 0; j < n; j++) if (lab[j] < 0 && near(pts[i], pts[j])) mem.push(j);
    if (mem.length < CFG2.DEPOT_MIN) continue;
    const k = DEPOTS.length; let la = 0, lo = 0; const dc = new Map();
    for (const j of mem) { lab[j] = k; la += pts[j].lat; lo += pts[j].lon; dc.set(pts[j].d, (dc.get(pts[j].d) || 0) + 1); }
    const d = [...dc.entries()].sort((x, y) => y[1] - x[1])[0][0];
    DEPOTS.push({ k, lat: la / mem.length, lon: lo / mem.length, n: mem.length, d, vs: mem.map(j => pts[j].v) });
  }
  // which points are inside a depot
  yield;
  const nd = new Uint8Array(N);
  const NR = CFG2.DEPOT_NEAR_KM, dl = NR / 111 * 1.2;
  for (let i = 0; i < N; i++) {
    const x = POS[2 * i], y = POS[2 * i + 1];
    for (const dp of DEPOTS) {
      if (Math.abs(y - dp.lat) > dl || Math.abs(x - dp.lon) > dl * 1.1) continue;
      if (hav(x, y, dp.lon, dp.lat) <= NR) { nd[i] = 1; break; }
    }
    if ((i & 65535) === 65535) yield;
  }
  NEARDEP = nd;
}
function depotOf(lat, lon) {
  for (const dp of DEPOTS) if (hav(lon, lat, dp.lon, dp.lat) <= CFG2.DEPOT_NEAR_KM) return dp;
  return null;
}
function nightSev(x) {
  if (inZone(x.d)) return 'in';
  const pc = PROV[distProv[x.d]].pc;
  return CFG.METRO.includes(pc) || CFG.ZONES[S.zone].prov.includes(pc) ? 'near' : 'far';
}
