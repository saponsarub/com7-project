/* js/analysis/excursions.js — out-of-zone trips (continuous periods a vehicle spends outside the allowed zone)
   uses: filters.js · stays.js (NEARDEP when "ignore depots" is on)
   provides: computeExcursions() · violRows() · SEV_LABEL */

const SEV_LABEL = { far: 'Upcountry', near: 'Vicinity', all: 'Always outside' };

function computeExcursions() {
  const { pIdx, dIdx } = zoneSets();
  const metro = new Set(CFG.METRO.map(pc => PROV.findIndex(p => p.pc === pc)));
  const allowed = new Uint8Array(DIST.length);
  for (let j = 0; j < DIST.length; j++) allowed[j] = pIdx.has(distProv[j]) || dIdx.has(j) ? 1 : 0;
  const GAP = CFG.GAP_MIN * 60, MIN = S.minDur * 60;
  const [bx, by] = CFG.BKK_CENTER;
  const useDep = S.exDepot && NEARDEP;
  const out = [];
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const s = D.vehicles.start[v], e = s + D.vehicles.count[v];
    let cur = null, lastT = -1e9, nIn = 0, nAll = 0;
    const mine = [];
    const close = () => {
      if (!cur) return;
      cur.dur = cur.e - cur.s;
      if (cur.dur >= MIN && (MIN > 0 || cur.n >= 1)) mine.push(cur);
      cur = null;
    };
    for (let i = s; i < e; i++) {
      const t = TT[i];
      if (t < S.a || t > S.b) continue;
      if (FLG[i] & 2 || DI[i] === 65535) continue;              // no GPS signal: not counted
      nAll++;
      const isOut = !allowed[DI[i]] && !(useDep && NEARDEP[i]);
      if (!isOut) { nIn++; close(); lastT = t; continue; }
      if (!cur || t - lastT > GAP) { close(); cur = { v, s: t, e: t, n: 1, provs: new Map(), km: 0, i0: i }; }
      else { cur.e = t; cur.n++; }
      const p = distProv[DI[i]];
      cur.provs.set(p, (cur.provs.get(p) || 0) + Math.min(DUR[i], GAP));
      const km = hav(POS[2 * i], POS[2 * i + 1], bx, by);
      if (km > cur.km) { cur.km = km; cur.far = p; }
      lastT = t;
    }
    close();
    if (nAll && !nIn) for (const x of mine) x.allOut = true;    // never inside the zone in this range
    for (const x of mine) out.push(x);
  }
  for (const x of out) {
    let far = false;
    for (const p of x.provs.keys()) if (!pIdx.has(p) && !metro.has(p)) { far = true; break; }
    x.sev = far ? 'far' : 'near';
  }
  EXC = out;
  EXC_BY_V = new Map();
  for (const x of out) { if (!EXC_BY_V.has(x.v)) EXC_BY_V.set(x.v, []); EXC_BY_V.get(x.v).push(x); }
}
function violRows() {
  const rows = [];
  for (const [v, xs] of EXC_BY_V) {
    const provs = new Map(); let hrs = 0, km = 0, far = false, allOut = false;
    for (const x of xs) {
      hrs += x.dur / 3600; km = Math.max(km, x.km); far = far || x.sev === 'far'; allOut = allOut || !!x.allOut;
      for (const [p, s] of x.provs) provs.set(p, (provs.get(p) || 0) + s);
    }
    const top = [...provs.entries()].sort((a, b) => b[1] - a[1]).map(e => provName(e[0]));
    const sev = allOut ? 'all' : far ? 'far' : 'near';
    rows.push({ v, plate: plateOf(v), n: xs.length, hrs, km, provs: top, sev, sevRank: sev === 'far' ? 3 : sev === 'all' ? 2 : 1 });
  }
  return rows;
}
