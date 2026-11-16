/* js/analysis/trip.js — the current trip of one vehicle at time T: where it came from · where it is · where it goes next
   Next stop: in history mode the data already contains it (fact). At the end of the data it is unknown, so it is
   estimated from this vehicle's own past stops that lie in its direction of travel (an estimate, never shown as fact).
   uses: stays.js · fleet.js · tools.js (inArea)
   provides: tripInfo() · allStays() · bearing() · compass() */

const _allStays = new Map();
function allStays(v) {                      // stops over the whole data range — cached per vehicle
  if (!_allStays.has(v)) _allStays.set(v, staysOf(v, 0, D.meta.tmax));
  return _allStays.get(v);
}
function bearing(lon1, lat1, lon2, lat2) {
  const r = Math.PI / 180, y = Math.sin((lon2 - lon1) * r) * Math.cos(lat2 * r);
  const x = Math.cos(lat1 * r) * Math.sin(lat2 * r) - Math.sin(lat1 * r) * Math.cos(lat2 * r) * Math.cos((lon2 - lon1) * r);
  return (Math.atan2(y, x) / r + 360) % 360;
}
const compass = deg => ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'][Math.round(deg / 45) % 8];
function districtAt(lon, lat) {
  for (let j = 0; j < DIST.length; j++) if (inArea('d:' + j, lon, lat)) return j;
  return 65535;
}

function tripInfo(v, T) {
  const i = lastIdxAt(v, T);
  if (i < 0) return null;
  const t = TT[i], st = allStays(v), here = { lon: POS[2 * i], lat: POS[2 * i + 1], d: DI[i], t };
  const online = T - t <= CFG.STALE_MIN * 60;
  const cur = st.find(x => x.s <= t && x.e >= t);
  if (cur) return { i, online, stopped: true, stop: cur, here };
  let origin = null, next = null;
  for (const x of st) { if (x.e < t) origin = x; else if (x.s > t) { next = x; break; } }
  // distance since leaving the last stop
  let km = 0, px = null, py = null;
  for (let k = origin ? origin.i1 : D.vehicles.start[v]; k <= i; k++) {
    if (FLG[k] & 2) continue;
    const x = POS[2 * k], y = POS[2 * k + 1];
    if (px != null) { const d = hav(px, py, x, y); if (d < 5) km += d; }
    px = x; py = y;
  }
  const res = { i, online, stopped: false, origin, here, km, hired: !!(FLG[i] & 1), head: D.cols.head ? headDeg(i) : null };
  if (next && next.s - t < 6 * 3600) res.next = { kind: 'data', lat: next.lat, lon: next.lon, d: next.d, at: next.s, dur: next.e - next.s };
  else res.next = predictNext(v, res);
  return res;
}

/* ── estimate where a moving vehicle is going (end of the data only) ──
   candidates = places this vehicle stopped before (clustered ~300 m), ahead of it (within ±40° of its heading),
   0.8–60 km away · score favours places visited often / long / overnight and nearer ones
   with a passenger the destination is the passenger's choice → direction only                          */
function predictNext(v, r) {
  const i = r.i;
  if (r.head == null || SPD[i] < CFG.MOVING_KMH) return null;
  const { lon: x, lat: y } = r.here, h = r.head;
  const ahead = (lon, lat) => Math.abs(((bearing(x, y, lon, lat) - h + 540) % 360) - 180);
  if (!r.hired) {
    const cl = [];
    for (const s of allStays(v)) {
      let c = cl.find(c => hav(c.lon, c.lat, s.lon, s.lat) < 0.3);
      if (!c) cl.push(c = { lon: s.lon, lat: s.lat, d: s.d, n: 0, hrs: 0, night: 0 });
      c.n++; c.hrs += s.dur / 3600; if (isNight(s)) c.night++;
    }
    let best = null, bs = 0;
    for (const c of cl) {
      const km = hav(x, y, c.lon, c.lat), diff = ahead(c.lon, c.lat);
      if (km < 0.8 || km > 60 || diff > 40) continue;
      const score = (c.n + c.hrs * 0.3 + c.night * 2) * Math.cos(diff * Math.PI / 180) / (1 + km / 15);
      if (score > bs) { bs = score; best = Object.assign({ km }, c); }
    }
    if (best) return { kind: 'estimate', lat: best.lat, lon: best.lon, d: best.d, km: best.km, visits: best.n, overnight: best.night > 0,
      confidence: best.n >= 3 || best.night ? 'medium' : 'low' };
  }
  // direction only: the district about 3 km ahead
  const r3 = 3 / 6371, b = h * Math.PI / 180, la = y * Math.PI / 180, lo = x * Math.PI / 180;
  const la2 = Math.asin(Math.sin(la) * Math.cos(r3) + Math.cos(la) * Math.sin(r3) * Math.cos(b));
  const lo2 = lo + Math.atan2(Math.sin(b) * Math.sin(r3) * Math.cos(la), Math.cos(r3) - Math.sin(la) * Math.sin(la2));
  const lon = lo2 * 180 / Math.PI, lat = la2 * 180 / Math.PI;
  return { kind: 'direction', lat, lon, d: districtAt(lon, lat), compass: compass(h) };
}
