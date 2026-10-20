/* js/analysis/fleet.js — สถานะรถ ณ เวลา T + สรุปตามพื้นที่/รายคันในช่วงเวลา
   ใช้: filters.js
   ให้: lastIdxAt() · computeNow() · NOW · computeAreas() · AREA · areaVal()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ══════════════════════════════════════════════════════════════════════
   ตำแหน่ง ณ เวลา T
   ══════════════════════════════════════════════════════════════════════ */
function lastIdxAt(v, T) {
  const s = D.vehicles.start[v], n = D.vehicles.count[v];
  if (!n || TT[s] > T) return -1;
  let lo = s, hi = s + n - 1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (TT[m] <= T) lo = m; else hi = m - 1; }
  return lo;
}
let NOW = [];
function computeNow() {
  const { pIdx, dIdx } = zoneSets();
  const stale = CFG.STALE_MIN * 60;
  const res = []; let on = 0, hired = 0, mov = 0, park = 0, outz = 0;
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const i = lastIdxAt(v, S.T);
    if (i < 0 || S.T - TT[i] > stale) continue;
    if (!areaMatchDist(DI[i])) continue;
    const st = status(i);
    if (st !== 'nosig' && !S.status.has(st)) continue;
    const dI = DI[i];
    const isOut = dI !== 65535 && !(pIdx.has(distProv[dI]) || dIdx.has(dI)) && !(FLG[i] & 2) && !(S.exDepot && NEARDEP && NEARDEP[i]);
    on++; if (st === 'hired') hired++; else if (st === 'vacant') mov++; else if (st === 'park') park++;
    if (isOut) outz++;
    res.push({ v, i, st, out: isOut });
  }
  NOW = res;
  $('#kOnline').textContent = fmt(on);
  $('#kHired').textContent = fmt(hired);
  $('#kMove').textContent = fmt(mov);
  $('#kPark').textContent = fmt(park);
  $('#kUtil').textContent = on ? pct(hired / on) : '–';
  $('#kOut').textContent = fmt(outz);
}

/* ══════════════════════════════════════════════════════════════════════
   สรุปตามพื้นที่ / รายคัน ในช่วง [a,b]
   ══════════════════════════════════════════════════════════════════════ */
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
function areaVal(level, idx) {
  const A = AREA;
  if (level === 'prov') return S.metric === 'veh' ? A.vehP[idx] : S.metric === 'hrs' ? A.hrsP[idx] : A.hirP[idx];
  return S.metric === 'veh' ? A.vehD[idx] : S.metric === 'hrs' ? A.hrsD[idx] : A.hirD[idx];
}
