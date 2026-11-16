/* js/data/roads.js — every car's trace along real roads (built by roadsnap.py with our own GraphHopper)
   data/taxi-roads.js is loaded after the first paint, so it never slows the start-up; until it arrives (or when
   the build had no GraphHopper) cars hop from fix to fix and the selected car falls back to OSRM.
   leg k: from point a[k] to point a[k] + n[k] · inner vertices verts[off[k] … off[k+1]) as int16 steps of 1e-5°
   uses: source.js (decodeEmbedded helpers) · state.js
   provides: ROADS · loadRoads() · roadPosAt() · roadLegsFor() */

let ROADS = null;
async function loadRoads() {
  if (!window.TAXI_ROADS) {
    if (!document.querySelector('script[src^="data/taxi-data.js"]')) return null;     // single file without roads
    await new Promise(ok => {
      const s = document.createElement('script');
      s.src = 'data/taxi-roads.js?t=' + (D.meta.pulled_to || '');
      s.onload = ok; s.onerror = ok;
      document.head.appendChild(s);
    });
  }
  const R = window.TAXI_ROADS;
  if (!R) return null;
  const [a, n, off, verts] = await Promise.all([R.a, R.n, R.off, R.verts].map(b64gunzip));
  ROADS = { a: new Uint32Array(a), n: new Uint16Array(n), off: new Uint32Array(off), verts: new Int16Array(verts), stats: R.stats };
  _roadLegs.clear();
  return ROADS;
}
/* leg whose start point is the last one ≤ i */
function legAt(i) {
  const A = ROADS.a;
  let lo = 0, hi = A.length - 1;
  if (hi < 0 || A[0] > i) return -1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (A[m] <= i) lo = m; else hi = m - 1; }
  return lo;
}
function legPath(k) {
  const a = ROADS.a[k], b = a + ROADS.n[k];
  let x = Math.round(POS[2 * a] * 1e5), y = Math.round(POS[2 * a + 1] * 1e5);
  const p = [[POS[2 * a], POS[2 * a + 1]]];
  for (let o = ROADS.off[k]; o < ROADS.off[k + 1]; o++) { x += ROADS.verts[2 * o]; y += ROADS.verts[2 * o + 1]; p.push([x / 1e5, y / 1e5]); }
  p.push([POS[2 * b], POS[2 * b + 1]]);
  return p;
}
/* position of vehicle v at time T on its road leg → [lon, lat, heading] or null (no leg / outside it)
   i = its last point at or before T · the car waits at a while it was parked there (jitter points), then drives */
function roadPosAt(v, i, T) {
  if (!ROADS) return null;
  const k = legAt(i); if (k < 0) return null;
  const a = ROADS.a[k], b = a + ROADS.n[k];
  if (b <= i || TT[b] <= T || TT[b] > D.meta.tmax || b >= D.vehicles.start[v] + D.vehicles.count[v]) return null;   // b not arrived yet (live test)
  let start = TT[a];
  for (let j = b - 1; j > a; j--) if (hav(POS[2 * j], POS[2 * j + 1], POS[2 * a], POS[2 * a + 1]) < 0.06) { start = TT[j]; break; }
  const p = legPath(k), cum = cumOf(p);
  const f = T <= start ? 0 : (T - start) / (TT[b] - start);
  const [m, q] = alongPath(p, cum, f);
  return [q[0], q[1], bearing(p[m - 1][0], p[m - 1][1], p[m][0], p[m][1])];
}
/* the same legs in the shape the track layer uses: { kept, legs: Map(a → { b, path, cum, km }) } */
const _roadLegs = new Map();
function roadLegsFor(v) {
  if (!ROADS) return null;
  if (_roadLegs.has(v)) return _roadLegs.get(v);
  const s = D.vehicles.start[v], e = s + D.vehicles.count[v], legs = new Map(), kept = new Set();
  for (let k = Math.max(0, legAt(s)); k < ROADS.a.length && ROADS.a[k] < e; k++) {
    const a = ROADS.a[k]; if (a < s) continue;
    const path = legPath(k), cum = cumOf(path);
    legs.set(a, { b: a + ROADS.n[k], path, cum, km: cum[cum.length - 1] });
    kept.add(a); kept.add(a + ROADS.n[k]);
  }
  const r = { kept: [...kept].sort((x, y) => x - y), legs, done: true };
  _roadLegs.set(v, r);
  return r;
}
