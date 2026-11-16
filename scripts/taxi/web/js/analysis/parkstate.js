/* js/analysis/parkstate.js — is a vehicle really parked, and where: EV charger · depot · home (its usual overnight spot) · street
   + is it safe to cut its power (immobilise) right now — decision support only, the page never sends a command
   Rules, not a trained model: there are no labelled examples yet (confirmed homes, charging sessions, cut-power outcomes).
   Once those exist, the same features (dwell time, engine flag, distance to chargers/depots/overnight spots, time of day,
   how often the car sleeps there) can train a classifier — see the README.
   uses: fleet.js · stays.js · trip.js (allStays) · layers.js (EV)
   Two power-cut rules (S.cutRule):
     'basic'   parked or engine off ≥ PARKED_MIN, no passenger, GPS fresh
     'offroad' basic + not on a public road. Coordinates are quantised (often only 4 decimals ≈ ±5.5 m) and GPS
               wanders 5–15 m, so the road test is normalised: the MEDIAN distance-to-road-edge over every GPS point
               while the car stood still (build: roads.py), then a margin that shrinks with more samples — and
               "too close to tell" is never treated as off the road.
   provides: parkState() · engineOf() · PARK_PLACE · ROAD_LABEL · parkedNow() */

const PARK = {
  STILL_R_KM: 0.15,        // moving less than this = standing still
  PARKED_MIN: 10,          // still at least this long = parked (shorter = stopped: traffic, pick-up)
  CHARGER_KM: 0.08,        // within 80 m of an EV charger = at the charger
  HOME_KM: 0.2,            // within 200 m of a place the car slept before = home
  SAFE_MIN: 15,            // parked at least this long before a power cut is suggested
  FRESH_MIN: 15,           // last GPS point must be this recent — otherwise the position is not known well enough
  ROAD_TOL_M: [12, 10, 8], // GPS + rounding margin (m) with 1 · 2–4 · ≥5 still points
  ROAD_CLEAR_M: 12,        // must be at least this much beyond the margin to count as off the road
};
const ROAD_LABEL = { off: 'Off the road', edge: 'At the road edge (unsure)', on: 'On the road', unknown: 'No road data' };
const PARK_PLACE = { charger: 'EV charger', depot: 'Depot', home: 'Home (usual overnight spot)', street: 'Street / other' };
const ENGINE = ['on', 'off', 'unknown', 'unknown'];
const engineOf = i => ENGINE[(FLG[i] >> 2) & 3];          // from the API's cm_engine: 0 running · 1 off · 2 unknown

/* where the car usually sleeps: its overnight stops (whole data), clustered ~200 m */
const _homes = new Map();
function homesOf(v) {
  if (_homes.has(v)) return _homes.get(v);
  const cl = [];
  for (const s of allStays(v)) {
    if (!isNight(s)) continue;
    let c = cl.find(c => hav(c.lon, c.lat, s.lon, s.lat) < PARK.HOME_KM);
    if (!c) cl.push(c = { lon: s.lon, lat: s.lat, nights: 0 });
    c.nights++;
  }
  _homes.set(v, cl);
  return cl;
}
function nearestCharger(lon, lat) {
  let best = null, bk = 1e9;
  for (const e of EV) {
    if (Math.abs(e[0] - lat) > 0.01 || Math.abs(e[1] - lon) > 0.01) continue;
    const k = hav(lon, lat, e[1], e[0]); if (k < bk) { bk = k; best = e; }
  }
  return best ? { e: best, km: bk } : null;
}

/* state of vehicle v at time T */
function parkState(v, T = S.T) {
  const i = lastIdxAt(v, T);
  if (i < 0) return { v, state: 'nodata' };
  const age = (T - TT[i]) / 60, x = POS[2 * i], y = POS[2 * i + 1];
  const eng = engineOf(i), hired = !!(FLG[i] & 1), nosig = !!(FLG[i] & 2);
  // how long it has been standing within ~150 m of where it is now
  let k = i; const s0 = D.vehicles.start[v];
  while (k > s0 && !(FLG[k - 1] & 2) && SPD[k - 1] < CFG.MOVING_KMH && hav(x, y, POS[2 * k - 2], POS[2 * k - 1]) < PARK.STILL_R_KM && TT[k] - TT[k - 1] <= CFG.GAP_MIN * 60) k--;
  // … and how long the engine has been reported off
  let e = i; while (e > s0 && engineOf(e - 1) === 'off' && TT[e] - TT[e - 1] <= CFG.GAP_MIN * 60) e--;
  const moving = SPD[i] >= CFG.MOVING_KMH;
  const stillMin = moving ? 0 : (T - TT[k]) / 60;
  const offMin = eng === 'off' && !moving ? (T - TT[e]) / 60 : 0;
  const parkedMin = Math.max(stillMin, offMin);
  const state = age > CFG.STALE_MIN ? 'offline' : moving ? 'moving' : parkedMin >= PARK.PARKED_MIN ? 'parked' : 'stopped';
  // normalise the position: median of all still points (rounding + GPS noise average out)
  const sx = [], sy = [], rd = [], rn = [];
  const R = D.cols.road, RN = D.cols.rname;
  for (let j = Math.max(k, i - 200); j <= i; j++) {
    if (FLG[j] & 2) continue;
    sx.push(POS[2 * j]); sy.push(POS[2 * j + 1]);
    if (R && R[j] !== 255) { rd.push(R[j]); if (RN[j] !== 65535) rn.push(RN[j]); }
  }
  const nx = sx.length ? median(sx) : x, ny = sx.length ? median(sy) : y;
  const road = roadCheck(rd, rn);
  // where
  let place = 'street', detail = null;
  const ch = nearestCharger(nx, ny);
  const dp = depotsReady() ? depotOf(ny, nx) : null;
  const home = homesOf(v).filter(c => hav(nx, ny, c.lon, c.lat) < PARK.HOME_KM).sort((a, b) => b.nights - a.nights)[0];
  if (ch && ch.km <= PARK.CHARGER_KM) { place = 'charger'; detail = { name: ch.e[2] || 'EV charger', op: ch.e[3] || '', m: Math.round(ch.km * 1000) }; }
  else if (dp) { place = 'depot'; detail = { n: dp.n, k: dp.k }; }
  else if (home) { place = 'home'; detail = { nights: home.nights }; }
  // power cut: every reason it is NOT safe, or the cautions when it is
  const no = [], caution = [];
  if (state === 'offline') no.push(`no GPS for ${fDur(age * 60)} — position not current`);
  if (nosig) no.push('no GPS fix on the last point');
  if (state === 'moving') no.push(`moving at ${SPD[i]} km/h`);
  if (state === 'stopped') no.push(`stopped only ${Math.round(parkedMin)} min — may be in traffic or picking up`);
  if (hired) no.push('meter shows a passenger on board');
  if (eng === 'on' && state !== 'moving') no.push('engine reported running');
  if (!no.length && parkedMin < PARK.SAFE_MIN) no.push(`parked only ${Math.round(parkedMin)} min (wait ${PARK.SAFE_MIN})`);
  if (place === 'charger') caution.push('at an EV charger — the car will keep blocking the charging bay');
  if (eng !== 'off') caution.push('engine state not reported as off');
  const roadTxt = road.m != null ? ` (≈${road.m} m from the road edge${road.name ? ' · ' + road.name : ''}, ${road.n} GPS points)` : '';
  const basic = { safe: !no.length, no: no.slice(), caution: caution.slice() };
  if (road.cls === 'on' || road.cls === 'edge') basic.caution.push(`${ROAD_LABEL[road.cls].toLowerCase()}${roadTxt}`);
  // off-road rule: the road test must say "off the road"
  const off = { no: no.slice(), caution: caution.slice() };
  if (road.cls === 'on') off.no.push(`parked on the road${roadTxt}`);
  else if (road.cls === 'edge') off.no.push(`at the road edge${roadTxt} — within GPS error (±${road.tol} m), cannot tell`);
  else if (road.cls === 'unknown') off.no.push('no road data for this spot');
  off.safe = !off.no.length;
  for (const c of [basic, off]) c.conf = c.safe ? (eng === 'off' && parkedMin >= 30 && (road.cls === 'off' || place !== 'street') ? 'high' : 'medium') : null;
  const cut = S.cutRule === 'offroad' ? off : basic;
  return { v, i, state, age, stillMin, offMin, parkedMin, since: moving ? null : Math.min(TT[k], TT[e]), eng, hired, place, detail,
    lat: ny, lon: nx, d: DI[i], road, cut, cutBasic: basic, cutOffroad: off };
}
function median(a) { const s = a.slice().sort((p, q) => p - q), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
/* distance to road edge (m, per still point, from the build) → on / edge / off / unknown with a margin for GPS error */
function roadCheck(rd, rn) {
  if (!D.cols.road) return { cls: 'unknown', m: null, n: 0 };
  if (!rd.length) return { cls: 'unknown', m: null, n: 0 };
  const m = Math.round(median(rd)), n = rd.length;
  const tol = PARK.ROAD_TOL_M[n >= 5 ? 2 : n >= 2 ? 1 : 0];
  const cls = m >= 251 ? 'off' : m <= tol ? 'on' : m >= tol + PARK.ROAD_CLEAR_M ? 'off' : 'edge';
  let name = null;
  if (rn.length && D.meta.road_names) {                      // most frequent nearby road name
    const c = new Map(); let best = -1, bc = 0;
    for (const r of rn) { const x = (c.get(r) || 0) + 1; c.set(r, x); if (x > bc) { bc = x; best = r; } }
    name = D.meta.road_names[best] || null;
  }
  return { cls, m: m >= 251 ? '>250' : m, n, tol, name };
}
/* parked vehicles at the cursor, with their place type (for the Parking panel) */
let _parkedNow = { key: '', list: [] };
function parkedNow() {
  const key = S.T + '|' + maskVer + '|' + depotsReady() + '|' + S.cutRule;
  if (_parkedNow.key === key) return _parkedNow.list;
  const list = [];
  for (const d of NOW) if (d.st === 'park') { const r = parkState(d.v); if (r.state === 'parked') list.push(r); }
  _parkedNow = { key, list };
  return list;
}
