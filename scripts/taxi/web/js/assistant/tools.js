/* js/assistant/tools.js — what the assistant can look up and do on the page
   The same functions serve the offline assistant and the AI agent (server → tool_use → run here in the browser),
   so the data never leaves the browser. Results name vehicles only as "car:<id>" — never the plate —
   and the chat turns [[car:<id>]] back into the plate on screen.
   uses: analysis/* · map/* · ui/actions.js · nlu.js
   provides: TOOLS · runTool() · carArg() · timeArg() · areaFeature() · areaBBox() · areaCenter() · inArea() */

/* ── areas: GeoJSON feature · bounding box · centre · point-in-area ── */
const _areaCache = new Map();
function areaFeature(key) {
  const [k, i] = key.split(':'), pc = (k === 'p' ? PROV : DIST)[+i].pc;
  return (k === 'p' ? D.geo.prov : D.geo.dist).features.find(f => f.properties.pc === pc) || null;
}
function areaBBox(key) {
  if (_areaCache.has(key)) return _areaCache.get(key);
  const f = areaFeature(key); let bb = null;
  if (f) {
    let x0 = 999, y0 = 999, x1 = -999, y1 = -999;
    const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const poly of polys) for (const [x, y] of poly[0]) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    bb = [[x0, y0], [x1, y1]];
  }
  _areaCache.set(key, bb);
  return bb;
}
function areaCenter(key) { const b = areaBBox(key); return b ? [(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2] : null; }
function inArea(key, lon, lat) {
  const bb = areaBBox(key);
  if (!bb || lon < bb[0][0] || lon > bb[1][0] || lat < bb[0][1] || lat > bb[1][1]) return false;
  const g = areaFeature(key).geometry, polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  const inRing = r => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, yi] = r[i], [xj, yj] = r[j];
    if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) c = !c; } return c; };
  return polys.some(p => inRing(p[0]) && !p.slice(1).some(inRing));
}

/* ── arguments ───────────────────────────────────────────────────── */
function carArg(x) {
  if (x == null || x === '') return -1;
  if (typeof x === 'number') return x >= 0 && x < NV ? x : -1;
  const m = /car:(\d+)/.exec(String(x));
  if (m) return +m[1] < NV ? +m[1] : -1;
  const p = NLU.plate(String(x)); if (p && p.v >= 0) return p.v;
  const v = NLU.plateIndex().get(String(x).replace(/[\s-]/g, '').toUpperCase());
  return v === undefined ? -1 : v;
}
/* 'now' · 'today' · 'yesterday' · '14:30' · 'ตี 3' · '2026-10-01 14:30' → { at, a, b, label } (seconds from data start) */
function timeArg(x) {
  const s = String(x || '');
  const m = /(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2}))?/.exec(s);
  if (m) {
    const t = (new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0)).getTime() - t0ms) / 1000;
    const clamp = u => Math.max(0, Math.min(D.meta.tmax, u));
    return m[4] != null ? { at: clamp(t), a: 0, b: clamp(t), label: fISO(clamp(t)), outside: t < 0 || t > D.meta.tmax }
      : { at: clamp(t + 86399), a: clamp(t), b: clamp(t + 86399), label: fDay(clamp(t)), outside: t + 86399 < 0 || t > D.meta.tmax };
  }
  return NLU.time(s);
}
function placeArg(x) {
  if (!x) return null;
  if (typeof x === 'object') return x;
  return NLU.place(String(x), 0.8);
}
const ST_OUT = { hired: 'on_trip', vacant: 'available', park: 'parked', nosig: 'no_signal' };
const STATUS_IN = { on_trip: 'hired', available: 'vacant', parked: 'park', hired: 'hired', vacant: 'vacant', park: 'park' };
const tok = v => 'car:' + v;
const kmR = x => Math.round(x * 10) / 10;

/* vehicles online at T (whole fleet — the sidebar filters do not apply to the assistant) */
function fleetAt(T, test) {
  const out = [];
  for (let v = 0; v < NV; v++) {
    const i = lastIdxAt(v, T);
    if (i < 0 || T - TT[i] > CFG.STALE_MIN * 60) continue;
    if (test && !test(i)) continue;
    out.push({ v, i, st: status(i) });
  }
  return out;
}
function placeTest(p) {
  if (p.kind === 'prov') return i => DI[i] !== 65535 && distProv[DI[i]] === p.idx;
  if (p.kind === 'dist') return i => DI[i] === p.idx;
  return i => !(FLG[i] & 2) && hav(POS[2 * i], POS[2 * i + 1], p.lon, p.lat) <= p.r;
}

const TOOLS = {
  cars_in_area({ place, time, status: st }) {
    const p = placeArg(place);
    if (!p) return { error: `Unknown place "${place}". Use a Thai province, district or a well-known landmark.` };
    const tm = timeArg(time), T = tm.at, want = STATUS_IN[st] || null;
    const all = fleetAt(T, placeTest(p));
    const by = { on_trip: 0, available: 0, parked: 0, no_signal: 0 };
    all.forEach(d => by[ST_OUT[d.st]]++);
    const list = want ? all.filter(d => d.st === want) : all;
    list.sort((x, y) => (x.st === 'hired') - (y.st === 'hired') || SPD[y.i] - SPD[x.i]);
    UI_ACT.showCars(list.map(d => d.v), T, p);
    return { as_of: fISO(T), place: p.name, place_kind: p.kind, radius_km: p.r, status_filter: st || null,
      count: list.length, online_in_place: all.length, by_status: by,
      vehicles: list.slice(0, 15).map(d => ({ car: tok(d.v), status: ST_OUT[d.st], speed_kmh: SPD[d.i], where: whereOf(DI[d.i]) })),
      more: Math.max(0, list.length - 15), time_outside_data: tm.outside || undefined };
  },

  vehicle_status({ car, time }) {
    const v = carArg(car);
    if (v < 0) return { error: `No vehicle found for "${car}".` };
    const tm = timeArg(time), i = lastIdxAt(v, tm.at);
    UI_ACT.focusCar(v, tm.at, i);
    if (i < 0) return { car: tok(v), error: `No GPS data for this vehicle before ${fISO(tm.at)}.` };
    const age = Math.round((tm.at - TT[i]) / 60), st = status(i);
    return { car: tok(v), center: centerName(D.vehicles.center[v]), as_of: fISO(tm.at),
      status: ST_OUT[st], online: age <= CFG.STALE_MIN, speed_kmh: SPD[i], heading_deg: D.cols.head ? Math.round(headDeg(i)) : null,
      where: whereOf(DI[i]), lat: +POS[2 * i + 1].toFixed(5), lon: +POS[2 * i].toFixed(5),
      gps_time: fISO(TT[i]), minutes_since_gps: age, outside_allowed_zone: DI[i] !== 65535 && !inZone(DI[i]) && !(FLG[i] & 2) };
  },

  vehicle_track({ car, time }) {
    const v = carArg(car);
    if (v < 0) return { error: `No vehicle found for "${car}".` };
    const tm = timeArg(time), a = tm.a, b = tm.b;
    const s = D.vehicles.start[v], e = s + D.vehicles.count[v];
    let km = 0, mx = 0, px = 0, py = 0, pt = -1, first = -1, last = -1, hired = 0, onl = 0;
    const provs = new Map();
    for (let i = s; i < e; i++) {
      const t = TT[i]; if (t < a || t > b) continue;
      onl += DUR[i]; if (FLG[i] & 1) hired += DUR[i];
      if (FLG[i] & 2) continue;
      if (first < 0) first = i; last = i;
      mx = Math.max(mx, SPD[i]);
      const x = POS[2 * i], y = POS[2 * i + 1];
      if (pt >= 0 && t - pt <= 900) { const k = hav(px, py, x, y); if (k / ((t - pt) / 3600 || 1) < 160) km += k; }
      px = x; py = y; pt = t;
      if (DI[i] !== 65535) { const p = distProv[DI[i]]; provs.set(p, (provs.get(p) || 0) + DUR[i]); }
    }
    UI_ACT.showTrack(v, a, b);
    if (first < 0) return { car: tok(v), from: fISO(a), to: fISO(b), error: 'No GPS points for this vehicle in that period.' };
    const { pIdx } = zoneSets();
    return { car: tok(v), from: fISO(a), to: fISO(b), km: Math.round(km), max_speed_kmh: mx,
      online: fDur(onl), on_trip: fDur(hired),
      start: { time: fISO(TT[first]), where: whereOf(DI[first]) }, end: { time: fISO(TT[last]), where: whereOf(DI[last]) },
      provinces: [...provs.entries()].sort((x, y) => y[1] - x[1]).map(([p, sec]) => ({ name: provName(p), time: fDur(sec), outside_zone: !pIdx.has(p) })) };
  },

  out_of_zone({ time, zone }) {
    const tm = timeArg(time || 'all');
    UI_ACT.showOutOfZone(tm.a, tm.b, zone && CFG.ZONES[zone] ? zone : null);
    const rows = violRows().sort((x, y) => y.sevRank - x.sevRank || y.hrs - x.hrs);
    const dest = new Map();
    for (const xs of EXC_BY_V.values()) { const ps = new Set(); xs.forEach(x => x.provs.forEach((_, p) => ps.add(p))); ps.forEach(p => dest.set(p, (dest.get(p) || 0) + 1)); }
    const lvl = { far: 'upcountry', near: 'vicinity', all: 'always_outside' };
    return { from: fISO(S.a), to: fISO(S.b), zone: CFG.ZONES[S.zone].label, min_trip_minutes: S.minDur,
      filters: S.centers.size ? 'center ' + [...S.centers].join(', ') : 'none',
      vehicles: rows.length, trips: EXC.length, hours: Math.round(EXC.reduce((s, x) => s + x.dur, 0) / 3600),
      by_level: { upcountry: rows.filter(r => r.sev === 'far').length, always_outside: rows.filter(r => r.sev === 'all').length, vicinity: rows.filter(r => r.sev === 'near').length },
      top: rows.slice(0, 10).map(r => ({ car: tok(r.v), level: lvl[r.sev], trips: r.n, hours: kmR(r.hrs), max_km_from_bangkok: Math.round(r.km), provinces: r.provs.slice(0, 3) })),
      top_destinations: [...dest.entries()].sort((x, y) => y[1] - x[1]).slice(0, 6).map(([p, n]) => ({ province: provName(p), vehicles: n })) };
  },

  fleet_stats({ time, place, level }) {
    const tm = timeArg(time), T = tm.at, p = placeArg(place);
    const all = fleetAt(T, p ? placeTest(p) : null);
    const by = { on_trip: 0, available: 0, parked: 0, no_signal: 0 };
    let out = 0; const cnt = new Map();
    // inside one province → rank its districts, otherwise rank provinces (or districts if asked)
    const lv = level === 'district' || (p && p.kind === 'prov') ? 'dist' : 'prov';
    for (const d of all) {
      by[ST_OUT[d.st]]++;
      const dI = DI[d.i]; if (dI === 65535) continue;
      if (!inZone(dI) && !(FLG[d.i] & 2)) out++;
      const k = lv === 'prov' ? distProv[dI] : dI; cnt.set(k, (cnt.get(k) || 0) + 1);
    }
    const moving = by.on_trip + by.available;
    UI_ACT.release(); UI_ACT.setTime(T);
    if (p && p.key) UI_ACT.fitArea(p.key);
    return { as_of: fISO(T), scope: p ? p.name : 'whole fleet', fleet_size: NV, online: all.length, by_status: by,
      share_on_trip: moving + by.parked ? kmR(by.on_trip / (moving + by.parked) * 100) + '%' : null,
      outside_zone: out, zone: CFG.ZONES[S.zone].label,
      top_areas: [...cnt.entries()].sort((x, y) => y[1] - x[1]).slice(0, 8)
        .map(([k, n]) => ({ name: lv === 'prov' ? provName(k) : distName(k) + ', ' + provName(distProv[k]), vehicles_online: n })) };
  },

  nearest_chargers({ car, place, time, n }) {
    if (!EV.length) return { error: 'No EV charger data in this build.' };
    let ref = null, key = null;
    const v = carArg(car);
    if (v >= 0) {
      const i = lastIdxAt(v, timeArg(time).at);
      if (i >= 0) ref = { name: tok(v), lat: POS[2 * i + 1], lon: POS[2 * i], car: v };
    }
    if (!ref && place) {
      const p = placeArg(place);
      if (!p) return { error: `Unknown place "${place}".` };
      if (p.lat != null) ref = { name: p.name, lat: p.lat, lon: p.lon }; key = p.key || null;
    }
    if (!ref) { const c = map.getCenter(); ref = { name: 'the map centre', lat: c.lat, lon: c.lng }; }
    const k = Math.max(1, Math.min(10, +n || 5));
    let pool = EV;
    let inside = null;
    if (key) { pool = EV.filter(d => inArea(key, d[1], d[0])); inside = pool.length; if (!pool.length) pool = EV; }
    const items = pool.map(d => ({ d, km: hav(ref.lon, ref.lat, d[1], d[0]) })).sort((x, y) => x.km - y.km).slice(0, k);
    UI_ACT.showChargers(items.map(x => x.d), ref);
    return { from: ref.name, chargers_in_area: inside, total_chargers_in_data: EV.length,
      items: items.map((x, j) => ({ n: j + 1, name: x.d[2] || 'EV charger', operator: x.d[3] || null, sockets: x.d[4] || null, bays: x.d[5] || null, km: kmR(x.km), lat: x.d[0], lon: x.d[1] })),
      note: 'Charger list comes from OpenStreetMap and covers only part of the real network.' };
  },

  parking_status({ car, time }) {
    const v = carArg(car);
    if (v < 0) return { error: `No vehicle found for "${car}".` };
    const T = timeArg(time).at, r = parkState(v, T);
    UI_ACT.focusCar(v, T, r.i != null ? r.i : -1);
    if (r.state === 'nodata') return { car: tok(v), error: `No GPS data for this vehicle before ${fISO(T)}.` };
    return { car: tok(v), as_of: fISO(T), state: r.state, parked_minutes: Math.round(r.stillMin), engine: r.eng, passenger: r.hired,
      place: PARK_PLACE[r.place], place_detail: r.detail, where: whereOf(r.d),
      road: { status: ROAD_LABEL[r.road.cls], meters_from_edge: r.road.m, gps_points: r.road.n, margin_m: r.road.tol, nearest_road: r.road.name },
      rule_in_use: S.cutRule,
      power_cut: { safe: r.cut.safe, confidence: r.cut.conf, reasons_not_safe: r.cut.no, cautions: r.cut.caution },
      power_cut_basic: { safe: r.cutBasic.safe, reasons_not_safe: r.cutBasic.no },
      power_cut_offroad: { safe: r.cutOffroad.safe, reasons_not_safe: r.cutOffroad.no },
      note: 'Rule-based check. This dashboard cannot send commands — power cuts go through the telematics system by an authorised person.' };
  },

  peak_time() {
    const nb = Math.ceil((D.meta.tmax + 1) / BIN), on = new Uint16Array(nb), hi = new Uint16Array(nb);
    for (let v = 0; v < NV; v++) {
      const s = D.vehicles.start[v], e = s + D.vehicles.count[v]; let lb = -1, lbh = -1;
      for (let i = s; i < e && TT[i] <= D.meta.tmax; i++) { const b = Math.floor(TT[i] / BIN); if (b !== lb) { on[b]++; lb = b; } if (FLG[i] & 1 && b !== lbh) { hi[b]++; lbh = b; } }
    }
    let bo = 0, bh = 0, lo = -1;
    for (let b = 0; b < nb; b++) { if (on[b] > on[bo]) bo = b; if (hi[b] > hi[bh]) bh = b; }
    for (let b = 6; b < nb - 6; b++) if (on[b] && (lo < 0 || on[b] < on[lo])) lo = b;
    UI_ACT.release(); UI_ACT.setTime(bh * BIN);
    return { most_on_trip: { time: fISO(bh * BIN), vehicles: hi[bh] }, most_online: { time: fISO(bo * BIN), vehicles: on[bo] },
      fewest_online: lo >= 0 ? { time: fISO(lo * BIN), vehicles: on[lo] } : null, bin_minutes: BIN / 60 };
  },

  data_info() {
    return { from: fISO(0), to: fISO(D.meta.tmax), vehicles: NV, gps_points: N, source: D.meta.source || null,
      note: 'The data is a batch pull, so "now" means the latest point in the data.' };
  },

  control_map({ action, panel, basemap, view, layer, on, place }) {
    switch (action) {
      case 'open_panel': if (!PANELS[panel]) return { error: 'panel must be one of ' + Object.keys(PANELS).join(', ') }; openPanel(panel); break;
      case 'set_basemap': if (!BASEMAPS[basemap]) return { error: 'basemap must be light, streets or satellite' }; setBasemap(basemap); syncMapTools(); break;
      case 'set_view': set3D(view === '3d'); break;
      case 'zoom_bangkok': UI_ACT.release(); flyHome(); break;
      case 'zoom_thailand': UI_ACT.release(); fitThailand(); break;
      case 'zoom_place': { UI_ACT.release(); const p = placeArg(place); if (!p) return { error: `Unknown place "${place}"` }; if (p.key) UI_ACT.fitArea(p.key); else map.flyTo({ center: [p.lon, p.lat], zoom: 14 }); break; }
      case 'toggle_layer':
        if (layer === 'ev_chargers') S.ev = on !== false;
        else if (layer === 'area_colors') S.choro = on !== false;
        else return { error: 'layer must be ev_chargers or area_colors' };
        syncMapTools(); renderLegend(); render(); break;
      case 'clear': UI_ACT.clear(); break;
      default: return { error: 'unknown action' };
    }
    return { ok: true };
  },
};
function runTool(name, input) {
  const f = TOOLS[name];
  if (!f) return { error: `Unknown tool ${name}` };
  try { return f(input || {}); } catch (e) { showErr('assistant', e); return { error: String(e.message || e) }; }
}

/* ── what the tools do on the page ─────────────────────────────────── */
const UI_ACT = {
  clear() { S.highlight = null; EV_FOCUS = []; this.release(); render(); },
  /* a new answer about the fleet / an area lets go of the car an earlier answer picked (it would stay alone on the map) */
  release() { if (S.sel >= 0) { S.others = 'dim'; selectVehicle(-1); } },
  setTime(T) { if (T < S.a || T > S.b) { S.a = 0; S.b = D.meta.tmax; refresh('range'); } setT(T); },
  fitArea(key) { const b = areaBBox(key); if (b) fitPoints(b, 12); },
  showCars(vs, T, p) {
    this.release();
    EV_FOCUS = []; S.highlight = new Set(vs); S.pt = 'now';
    this.setTime(T);
    const pts = vs.map(v => { const i = lastIdxAt(v, T); return [POS[2 * i], POS[2 * i + 1]]; }).filter(x => x[0]);
    if (pts.length) fitPoints(pts, 14);
    else if (p.key) this.fitArea(p.key);
    else map.flyTo({ center: [p.lon, p.lat], zoom: 13, duration: 800 });
    syncMapTools();
  },
  focusCar(v, T, i) {
    S.highlight = null; EV_FOCUS = [];
    this.setTime(T);
    selectVehicle(v, false, 'dim');
    if (i >= 0) map.flyTo({ center: [POS[2 * i], POS[2 * i + 1]], zoom: Math.max(map.getZoom(), 14), duration: 800 });
  },
  showTrack(v, a, b) {
    S.highlight = null; EV_FOCUS = [];
    S.a = a; S.b = b; S.T = Math.max(a, Math.min(b, S.T));
    S.trk = 'all'; S.trkFrom = null;
    refresh('range');
    selectVehicle(v, true, 'hide');
  },
  showOutOfZone(a, b, zone) {
    this.release();
    S.highlight = null; EV_FOCUS = [];
    S.a = a; S.b = b; S.T = Math.max(a, Math.min(b, S.T));
    if (zone) { S.zone = zone; buildZoneGeo(); }
    refresh('range');
    openPanel('zone');
  },
  showChargers(list, ref) {
    if (ref.car == null) this.release();
    S.highlight = ref.car != null ? new Set([ref.car]) : null;
    EV_FOCUS = list; S.ev = true;
    fitPoints([...list.map(d => [d[1], d[0]]), [ref.lon, ref.lat]], 15);
    syncMapTools(); renderLegend(); render();
  },
};
