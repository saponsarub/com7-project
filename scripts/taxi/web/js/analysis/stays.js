/* js/analysis/stays.js — จุดจอด · ค้างคืน · ลานจอด (ตรรกะเดียวกับ build_dashboard.find_depots)
   ใช้: filters.js · utils.js
   ให้: staysOf() · computeStays() · computeDepots() · depotOf() · inZone() · nightSev()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ── จุดจอด ─────────────────────────────────────────────────────────── */
function nightWindows() {
  const ws = [], m = tDate(0); m.setHours(0, 0, 0, 0);
  for (let ms = m.getTime(); ms <= t0ms + D.meta.tmax * 1000; ms += 86400000) {
    const s = (ms - t0ms) / 1000;
    ws.push([s + CFG2.NIGHT_H[0] * 3600, s + CFG2.NIGHT_H[1] * 3600]);
  }
  return ws;
}
/* จุดจอดของรถ v ในช่วง [a,b] — anchor = จุดแรกของช่วง (ตรงกับสคริปต์อ้างอิง Python) */
function staysOf(v, a, b, NW) {
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
let STAYS_BY_V = new Map(), NIGHT = new Map(), DEPOTS = [], NEARDEP = null;
function computeStays() {
  const NW = nightWindows();
  STAYS_BY_V = new Map(); NIGHT = new Map();
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const st = staysOf(v, S.a, S.b, NW);
    if (!st.length) continue;
    STAYS_BY_V.set(v, st);
    let best = null;
    for (const x of st) if (x.night >= CFG2.NIGHT_MIN_H * 3600 && (!best || x.night > best.night)) best = x;
    if (best) NIGHT.set(v, best);
  }
}
/* ลานจอด: คำนวณครั้งเดียวจากข้อมูลทั้งช่วง ไม่ขึ้นกับตัวกรอง (เป็นสถานที่จริง ไม่ใช่มุมมอง) */
function computeDepots() {
  const NW = nightWindows(), pts = [];
  for (let v = 0; v < NV; v++) {
    let best = null;
    for (const x of staysOf(v, 0, D.meta.tmax, NW)) if (x.night >= CFG2.NIGHT_MIN_H * 3600 && (!best || x.night > best.night)) best = x;
    if (best) pts.push(best);
  }
  const n = pts.length, R = CFG2.DEPOT_R_KM;
  const dens = new Uint16Array(n);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++)
    if (Math.abs(pts[i].lat - pts[j].lat) < 0.003 && hav(pts[i].lon, pts[i].lat, pts[j].lon, pts[j].lat) <= R) dens[i]++;
  const order = [...Array(n).keys()].sort((x, y) => dens[y] - dens[x] || x - y);
  const lab = new Int32Array(n).fill(-1);
  DEPOTS = [];
  for (const i of order) {
    if (lab[i] >= 0) continue;
    const mem = [];
    for (let j = 0; j < n; j++) if (lab[j] < 0 && Math.abs(pts[i].lat - pts[j].lat) < 0.003 && hav(pts[i].lon, pts[i].lat, pts[j].lon, pts[j].lat) <= R) mem.push(j);
    if (mem.length < CFG2.DEPOT_MIN) continue;
    const k = DEPOTS.length; let la = 0, lo = 0; const dc = new Map();
    for (const j of mem) { lab[j] = k; la += pts[j].lat; lo += pts[j].lon; dc.set(pts[j].d, (dc.get(pts[j].d) || 0) + 1); }
    const d = [...dc.entries()].sort((x, y) => y[1] - x[1])[0][0];
    DEPOTS.push({ k, lat: la / mem.length, lon: lo / mem.length, n: mem.length, d, vs: mem.map(j => pts[j].v) });
  }
  // จุดไหนอยู่ในลานจอด
  NEARDEP = new Uint8Array(N);
  const NR = CFG2.DEPOT_NEAR_KM, dl = NR / 111 * 1.2;
  for (let i = 0; i < N; i++) {
    const x = POS[2 * i], y = POS[2 * i + 1];
    for (const dp of DEPOTS) {
      if (Math.abs(y - dp.lat) > dl || Math.abs(x - dp.lon) > dl * 1.1) continue;
      if (hav(x, y, dp.lon, dp.lat) <= NR) { NEARDEP[i] = 1; break; }
    }
  }
}
function depotOf(lat, lon) {
  for (const dp of DEPOTS) if (hav(lon, lat, dp.lon, dp.lat) <= CFG2.DEPOT_NEAR_KM) return dp;
  return null;
}
function inZone(dI) {
  if (dI === 65535) return true;
  const { pIdx, dIdx } = zoneSets();
  return pIdx.has(distProv[dI]) || dIdx.has(dI);
}
function nightSev(x) {
  if (inZone(x.d)) return 'in';
  const p = distProv[x.d];
  return CFG.METRO.includes(PROV[p].pc) || CFG.ZONES[S.zone].prov.includes(PROV[p].pc) ? 'near' : 'far';
}
