/* js/data/model.js — prepare the data after loading + interpret point status
   uses: state.js
   provides: prepare() · status() · areaName() · provName() · distName() · plateOf() · centerName() · whereOf() */

function status(i) {
  if (FLG[i] & 2) return 'nosig';
  if (FLG[i] & 1) return 'hired';
  return SPD[i] >= CFG.MOVING_KMH ? 'vacant' : 'park';
}
const provName = p => PROV[p].en || PROV[p].th;
const distName = d => DIST[d].en || DIST[d].th;
function areaName(key) {
  const [k, i] = key.split(':'); const j = +i;
  return k === 'p' ? provName(j) : distName(j) + ', ' + provName(distProv[j]);
}
function whereOf(dI) { return dI === 65535 ? 'Unknown area' : `${distName(dI)}, ${provName(distProv[dI])}`; }
const plateOf = v => D.vehicles.plate[v];
const centerName = c => CFG.CENTER_NAMES[c] || 'Center ' + c;

function prepare(data) {
  D = data;
  const c = D.cols;
  POS = c.pos; TT = c.t; SPD = c.spd; FLG = c.flg; DI = c.dist; VV = c.v;
  N = TT.length; NV = D.vehicles.vin.length;
  PROV = D.areas.prov; DIST = D.areas.dist;
  distProv = new Uint8Array(DIST.length);
  DIST.forEach((d, i) => distProv[i] = d.p);
  t0ms = new Date(D.meta.t0).getTime();
  // time each point "stands for" = until the next point of the same vehicle (max 10 min)
  DUR = new Float32Array(N);
  const st = D.vehicles.start, ct = D.vehicles.count;
  for (let v = 0; v < NV; v++) {
    const s = st[v], n = ct[v];
    for (let k = 0; k < n; k++) { const i = s + k; DUR[i] = k + 1 < n ? Math.min(TT[i + 1] - TT[i], 600) : 300; }
  }
  S.a = 0; S.b = D.meta.tmax; S.T = Math.min(S.b, 3600 * 3);
}
