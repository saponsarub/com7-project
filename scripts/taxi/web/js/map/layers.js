/* js/map/layers.js — deck.gl layers: points · area colours · selected track · stops / depots · chargers · assistant highlights
   uses: analysis/*
   provides: render() · rangeData() · choroColor() · updateChoroScale() · buildZoneGeo() · EV · EV_FOCUS · pcToProv · pcToDist */

const RAMP_RGB = RAMP.map(hexRgb);

let RANGE_DATA = null, RANGE_VER = -1, COLORS = null;
function rangeData() {
  if (RANGE_VER === maskVer && RANGE_DATA) return RANGE_DATA;
  if (!COLORS) {
    COLORS = new Uint8Array(N * 4);
    for (let i = 0; i < N; i++) {
      const c = COL[status(i)];
      COLORS[4 * i] = c[0]; COLORS[4 * i + 1] = c[1]; COLORS[4 * i + 2] = c[2]; COLORS[4 * i + 3] = 255;
    }
  }
  const f = new Float32Array(N * 2);
  for (let i = 0; i < N; i++) { f[2 * i] = TT[i]; f[2 * i + 1] = MASK[i]; }
  RANGE_DATA = { length: N, attributes: {
    getPosition: { value: POS, size: 2 },
    getFillColor: { value: COLORS, size: 4, normalized: true },
    getFilterValue: { value: f, size: 2 },
  } };
  RANGE_VER = maskVer;
  return RANGE_DATA;
}

let choroScale = { max: 1 };
function choroColor(level, idx) {
  const val = areaVal(level, idx);
  if (!val) return [0, 0, 0, 0];
  const r = Math.min(1, Math.log1p(val) / Math.log1p(choroScale.max));
  const k = Math.min(RAMP_RGB.length - 1, Math.floor(r * RAMP_RGB.length));
  return rgba(RAMP_RGB[k], 120);
}
function updateChoroScale() {
  const n = S.level === 'prov' ? PROV.length : DIST.length;
  let mx = 1; for (let i = 0; i < n; i++) mx = Math.max(mx, areaVal(S.level, i));
  choroScale.max = mx;
}
let pcToProv, pcToDist;           // geo features are matched to areas by code (pc), not by order
let layerVer = 0;

/* ── size follows the zoom: tiny dots when zoomed out (thousands of cars overlap), full size from street level ──
   ZS = 0.25 (zoom ≤ 7) … ~0.6 (Bangkok view) … 1 from zoom 12 (no further growth) · redraw only when the rounded step changes
   pointers (direction) appear from about zoom 10.5 — below that every car is a plain dot */
let ZS = 1, ZB = -1;
function zoomScale() { const z = map ? map.getZoom() : 10; return Math.max(0.25, Math.min(1, 0.25 + (z - 7) * 0.15)); }
let Z3 = -1, Z2 = -1;
function onZoomScale() {
  const s = zoomScale(), b = Math.round(s * 20), z3 = use3DCars() ? Math.round(map.getZoom() * 4) : -1;
  const z2 = S.sel >= 0 ? Math.round(map.getZoom() * 2) : -1;          // route dashes keep their on-screen size
  if (b !== ZB || z3 !== Z3 || z2 !== Z2) { ZB = b; ZS = s; Z3 = z3; Z2 = z2; render(); }
}

/* ── one vehicle selected: the others are faded ('dim') or not drawn ('hide') ── */
const hideOthers = () => S.sel >= 0 && S.others === 'hide';
const alphaOf = (v, a) => S.sel >= 0 && v !== S.sel ? Math.round(a * 0.16) : a;
const nowData = () => hideOthers() ? NOW.filter(d => d.v === S.sel) : NOW;

function render() {
  if (!deckOverlay || !D) return;
  syncClearAll();                                                   // ui/filters.js — any filter or highlight shows on the map, so check here
  if (ZB < 0) { ZS = zoomScale(); ZB = Math.round(ZS * 20); }
  const layers = [], focus = [S.sel, S.others, ZB];
  if (S.choro) {
    const geo = S.level === 'prov' ? D.geo.prov : D.geo.dist;
    const idxOf = S.level === 'prov' ? pcToProv : pcToDist;
    const pre = S.level === 'prov' ? 'p:' : 'd:';
    layers.push(new deck.GeoJsonLayer({
      id: 'areas', data: geo, pickable: true, stroked: true, filled: true,
      getFillColor: f => choroColor(S.level, idxOf.get(f.properties.pc)),
      getLineColor: f => S.areas.has(pre + idxOf.get(f.properties.pc)) ? [16, 35, 26, 255] : [255, 255, 255, 170],
      getLineWidth: f => S.areas.has(pre + idxOf.get(f.properties.pc)) ? 2.5 : 0.6,
      lineWidthUnits: 'pixels',
      autoHighlight: true, highlightColor: [16, 35, 26, 40],
      updateTriggers: { getFillColor: [layerVer, S.metric, S.level], getLineColor: [layerVer], getLineWidth: [layerVer] },
    }));
  }
  // allowed zone outline
  layers.push(new deck.GeoJsonLayer({
    id: 'zone', data: ZONE_GEO, stroked: true, filled: false, pickable: false,
    getLineColor: [13, 147, 214, 230], getLineWidth: 2.2, lineWidthUnits: 'pixels',
    updateTriggers: { getLineColor: [S.zone] },
  }));
  if ((S.pt === 'range' || (S.pt === 'now' && S.trail > 0)) && !hideOthers()) {
    const lo = S.pt === 'range' ? S.a : Math.max(S.a, S.T - S.trail * 60);
    const hi = S.pt === 'range' ? S.b : S.T;
    const op = (S.pt === 'range' ? 0.55 : 0.35) * (S.sel >= 0 ? 0.25 : 1);
    layers.push(new deck.ScatterplotLayer({
      id: 'range', data: rangeData(), radiusUnits: 'pixels', getRadius: S.pt === 'range' ? 1.4 : 1.6,
      radiusMinPixels: 1, opacity: op, stroked: false,
      extensions: [new deck.DataFilterExtension({ filterSize: 2 })],
      filterRange: [[lo, hi], [0.5, 1.5]],
      updateTriggers: { getFilterValue: RANGE_VER },
    }));
  }
  if (S.pt === 'now' && isLive() && S.offline && !hideOthers() && OFFLINE.length) {
    // live: vehicles without a recent point, at their last known position (hollow grey)
    layers.push(new deck.ScatterplotLayer({
      id: 'offline', data: OFFLINE, pickable: true, radiusUnits: 'pixels', billboard: true, getRadius: Math.max(1, 2 * ZS),
      stroked: true, lineWidthUnits: 'pixels', getLineWidth: Math.max(0.5, 1.2 * ZS),
      getPosition: d => [POS[2 * d.i], POS[2 * d.i + 1]],
      getFillColor: d => [255, 255, 255, alphaOf(d.v, 200)], getLineColor: d => [120, 134, 126, alphaOf(d.v, 230)],
      updateTriggers: { getPosition: S.T, getFillColor: focus, getLineColor: focus },
    }));
  }
  if (S.sel >= 0) layers.push(...trackLayers(S.sel));
  if (S.pt === 'now') {
    // no car pictures — moving car = direction arrow (status colour, dark rim) · parked / no signal = dot
    // zoomed far out the arrows would be specks → dots for all · the selected car is drawn last (= on top)
    // ⚠️ deck.gl matches layers by id — layers of different types must never share an id
    const data = nowData().slice().sort((a, b) => (a.v === S.sel) - (b.v === S.sel));
    if (S.sel >= 0) {                                                // selected car glides along the roads
      const d = data[data.length - 1];
      if (d && d.v === S.sel) { const p = snappedAt(S.sel, S.T); if (p) { d.x = p[0]; d.y = p[1]; if (isMoving(d.i) || p[2] != null) d.h = p[2]; } }
    }
    const puck = !!D.cols.head && ZS >= 0.8;
    // arrow = moving car (when zoomed in enough) · the selected car always gets one, so a tracked car shows its heading even parked
    const asArrow = d => !!D.cols.head && (d.v === S.sel || (puck && isMoving(d.i)));
    const sel = S.sel >= 0 ? data.find(d => d.v === S.sel) : null;
    if (use3DCars()) {                                              // tilted + zoomed in: 3D taxis facing their way
      layers.push(...car3dLayers(data));
      if (S.highlight && S.highlight.size) layers.push(new deck.ScatterplotLayer({
        id: 'hl', data: nowData().filter(d => S.highlight.has(d.v)), radiusUnits: 'pixels', getRadius: 18, stroked: true, filled: false,
        getLineColor: [214, 51, 108, 255], lineWidthUnits: 'pixels', getLineWidth: 2.5, getPosition: d => [d.x, d.y],
        updateTriggers: { getPosition: S.T, data: S.highlight } }));
      overlayLayers(layers);
      deckOverlay.setProps({ layers });
      return;
    }
    if (sel) layers.push(new deck.ScatterplotLayer({                // halo under the selected car
      id: 'sel-halo', data: [sel], radiusUnits: 'pixels', billboard: true, getRadius: 13, stroked: true, lineWidthUnits: 'pixels', getLineWidth: 2,
      getPosition: d => [d.x, d.y], getFillColor: d => rgba(COL[d.st], 50), getLineColor: d => rgba(COL[d.st], 210),
      updateTriggers: { getPosition: S.T, getFillColor: S.T, getLineColor: S.T },
    }));
    layers.push(new deck.ScatterplotLayer({
      id: 'now', data: data.filter(d => !asArrow(d)), pickable: true, radiusUnits: 'pixels', billboard: true,
      getPosition: d => [d.x, d.y],
      getRadius: d => d.v === S.sel ? 5 : Math.max(1, 2 * ZS),
      getFillColor: d => rgba(COL[d.st], alphaOf(d.v, d.v === S.sel ? 255 : 235)),
      stroked: true, lineWidthUnits: 'pixels',
      getLineColor: d => d.out ? [217, 58, 64, alphaOf(d.v, 255)] : [16, 35, 26, alphaOf(d.v, 220)],
      getLineWidth: d => d.v === S.sel ? (d.out ? 2.2 : 1.3) : (d.out ? 1.4 : 0.8) * Math.max(0.35, ZS),
      updateTriggers: { getPosition: S.T, getFillColor: [S.T, focus], getRadius: focus, getLineColor: [S.T, focus], getLineWidth: [S.T, focus] },
    }));
    if (D.cols.head) layers.push(...puckLayers(data.filter(asArrow)));
    if (S.highlight && S.highlight.size) {                          // vehicles picked by the assistant
      layers.push(new deck.ScatterplotLayer({
        id: 'hl', data: nowData().filter(d => S.highlight.has(d.v)), radiusUnits: 'pixels', getRadius: 15,
        stroked: true, filled: true, getFillColor: [214, 51, 108, 35], getLineColor: [214, 51, 108, 255], lineWidthUnits: 'pixels', getLineWidth: 2.5,
        getPosition: d => [d.x, d.y], updateTriggers: { getPosition: S.T, data: S.highlight },
      }));
    }
  }
  overlayLayers(layers);
  deckOverlay.setProps({ layers });
}

/* ── direction icons ────────────────────────────────────────────────
   lie flat on the ground (billboard: false) so they stay correct when the map rotates / tilts
   GPS heading 0° = north, clockwise · deck.gl rotates counter-clockwise → negative angle · mask: colour from getColor
   puck  = a moving car: navigation arrow (one marker per car, colour = status)
   arrow = small chevron along the selected car's route                                                   */
const ICONS = {
  url: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="64" viewBox="0 0 128 64">'
    + '<path d="M32 4 L56 58 L32 46 L8 58 Z" fill="#fff"/>'
    + '<path d="M96 8 L114 52 L96 41 L78 52 Z" fill="#fff"/></svg>'),
  map: { puck: { x: 0, y: 0, width: 64, height: 64, anchorY: 34, mask: true },
         arrow: { x: 64, y: 0, width: 64, height: 64, anchorY: 32, mask: true } },
};
const PUCK_PX = 12;                                                  // puck height at zoom ≥ 12
const puckPx = () => PUCK_PX * ZS * ZS;                              // shrinks faster than dots when zooming out
function headDeg(i) { const H = D.cols.head; return H ? H[i] * 360 / 256 : 0; }
const isMoving = i => !(FLG[i] & 2) && SPD[i] >= CFG.MOVING_KMH && !!D.cols.head;
/* 2D: icons lie flat on the ground and turn with the map
   3D (tilted): flat icons get squashed to slivers → stand them up facing the camera (billboard) and
   turn them by heading − map bearing so they still point the right way on screen */
const atIdx = i => [POS[2 * i], POS[2 * i + 1]];
function iconLayer(id, icon, data, getPos, getHead, size, getColor, trig, pickable = false) {
  const up = is3D(), brg = up ? map.getBearing() : 0;
  return new deck.IconLayer({
    id, data, pickable, iconAtlas: ICONS.url, iconMapping: ICONS.map, getIcon: () => icon,
    billboard: up, sizeUnits: 'pixels', getSize: size, getColor,
    getPosition: getPos,
    getAngle: d => -(getHead(d) - brg),
    updateTriggers: { getPosition: trig, getAngle: [trig, up, Math.round(brg)], getColor: trig, getSize: trig },
  });
}
function puckLayers(mov) {
  const sz = d => d.v === S.sel ? 22 : puckPx();
  const trig = [S.T, S.sel, S.others, ZB];
  return [
    // dark rim (red = outside the zone) under the coloured puck
    iconLayer('now-puck-o', 'puck', mov, d => [d.x, d.y], d => d.h, d => sz(d) + (d.v === S.sel ? 5 : 3.5),
      d => d.out ? [217, 58, 64, alphaOf(d.v, 255)] : [16, 35, 26, alphaOf(d.v, 230)], trig),
    iconLayer('now-puck', 'puck', mov, d => [d.x, d.y], d => d.h, sz, d => rgba(COL[d.st], alphaOf(d.v, 255)), trig, true),
  ];
}

/* ── selected vehicle's route ───────────────────────────────────────
   S.trk = 'all'   the whole selected period (S.a → S.b)
   S.trk = 'live'  up to the cursor (from S.trkFrom when replaying, else S.a) — press play and the line grows
   S.trk = <sec>   the last N seconds before the cursor (last 1 h … 7 days)
   the line breaks where points are more than STALE_MIN apart (no line across signal gaps)
   line style (v4):
     History  solid  = driven up to the cursor · dotted = still ahead of the cursor (when the window reaches past it)
     Live     dotted = the last LIVE_TRACK_SEC driven (S.trk is ignored while live)
   colour: magenta TRK_RGB (the old navy read as black on the map)                          */
const LIVE_TRACK_SEC = 3600;
const TRK_RGB = [230, 0, 126];                    // route colour of the selected car
function trackWindow() {
  if (isLive()) return [Math.max(0, S.T - LIVE_TRACK_SEC), S.T];
  if (typeof S.trk === 'number') return [Math.max(0, S.T - S.trk), S.T];
  if (S.trk === 'live') return [S.trkFrom != null ? S.trkFrom : S.a, S.T];
  return [S.a, S.b];
}
function trackLayers(v) {
  const s = D.vehicles.start[v], n = D.vehicles.count[v];
  const [lo, hi] = trackWindow();
  const idx = [];
  for (let i = s; i < s + n; i++) if (TT[i] >= lo && TT[i] <= hi && !(FLG[i] & 2)) idx.push(i);
  if (!idx.length) return tripLayers(v);
  const gap = CFG.STALE_MIN * 60;
  const snap = roadLegsFor(v) || Router.trackPeek(v);
  if (!snap && !ROADS && !Router.tracks.has(v)) Router.track(v).then(() => { if (S.sel === v) { render(); if (S.panel === 'vehicles') updateVehLive(); } });
  const live = isLive(), T = S.T;
  // straight lines between GPS points (no road match yet) · broken at signal gaps
  const straight = list => {
    const out = []; let cur = [];
    for (let k = 0; k < list.length; k++) {
      if (k && TT[list[k]] - TT[list[k - 1]] > gap) { if (cur.length > 1) out.push(cur); cur = []; }
      cur.push([POS[2 * list[k]], POS[2 * list[k] + 1]]);
    }
    if (cur.length > 1) out.push(cur);
    return out;
  };
  const nPast = idx.findIndex(i => TT[i] > T), cutK = nPast < 0 ? idx.length : nPast;   // idx[0 … cutK-1] = at or before the cursor
  const past = snap ? snappedPaths(snap, lo, Math.min(hi, T)) : straight(idx.slice(0, cutK));
  // ahead: from the car's spot at the cursor to the end of the window (History only)
  const ahead = live || hi <= T ? [] : snap ? snappedPaths(snap, T, hi) : straight(idx.slice(Math.max(0, cutK - 1)));
  let total = 0;
  for (let k = 1; k < idx.length; k++) if (TT[idx[k]] - TT[idx[k - 1]] <= gap) total += hav(POS[2 * idx[k - 1]], POS[2 * idx[k - 1] + 1], POS[2 * idx[k]], POS[2 * idx[k] + 1]);
  const span = Math.max(1, hi - lo);
  const col = i => {
    if (TT[i] > T) return [242, 178, 214, 170];                      // not reached yet: pale
    const r = (TT[i] - lo) / span; return [Math.round(246 - 16 * r), Math.round(196 - 196 * r), Math.round(226 - 100 * r), 235];   // light pink → magenta
  };
  // ~12 small chevrons spread evenly by distance along the route, never on top of the car itself
  const ci = lastIdxAt(v, S.T), cx = ci >= 0 ? POS[2 * ci] : null, cy = ci >= 0 ? POS[2 * ci + 1] : null;
  const step = Math.max(total / 12, 0.25), arrows = [];
  let acc = step / 2;
  for (let k = 1; k < idx.length; k++) {
    const i = idx[k], j = idx[k - 1];
    acc += hav(POS[2 * j], POS[2 * j + 1], POS[2 * i], POS[2 * i + 1]);
    if (acc < step || !isMoving(i)) continue;
    if (cx != null && hav(cx, cy, POS[2 * i], POS[2 * i + 1]) < 0.5) continue;      // keep clear of the car
    arrows.push(i); acc = 0;
  }
  const last = idx[idx.length - 1], trig = [lo, hi, S.trk, v, T, live];
  const ends = [{ i: idx[0], k: 's' }];
  if (last !== ci) ends.push({ i: last, k: 'e' });                  // end of the route ≠ where the car is now
  const dotted = live ? past : ahead;
  const solid = live ? [] : past;
  return [
    // History: driven part = solid
    new deck.PathLayer({
      id: 'track-line', data: solid, getPath: p => p, widthUnits: 'pixels', getWidth: 3.5,
      getColor: [...TRK_RGB, snap ? 220 : 190], capRounded: true, jointRounded: true, updateTriggers: { getPath: [trig, !!snap] },
    }),
    // History: part still ahead of the cursor · Live: the last hour driven = small round dots (fixed on-screen spacing)
    new deck.PathLayer({
      id: 'track-dash', data: dotted.flatMap(p => dashes(p, 0.5, 7)), getPath: p => p, widthUnits: 'pixels', getWidth: 4,
      getColor: live ? [...TRK_RGB, 235] : [...TRK_RGB, 140], capRounded: true, jointRounded: true,
      updateTriggers: { getPath: [trig, !!snap, Z2], getColor: live, getWidth: live },
    }),
    new deck.ScatterplotLayer({
      id: 'track', data: idx, radiusUnits: 'pixels', getRadius: 2.4, stroked: true, lineWidthUnits: 'pixels', getLineWidth: 0.5,
      getPosition: i => [POS[2 * i], POS[2 * i + 1]], getFillColor: col,
      getLineColor: [255, 255, 255, 180], pickable: true,
      updateTriggers: { getFillColor: trig, getPosition: trig },
    }),
    iconLayer('track-dir-o', 'arrow', arrows, atIdx, headDeg, 16, [...TRK_RGB, 235], trig),
    iconLayer('track-dir', 'arrow', arrows, atIdx, headDeg, 10, [255, 255, 255, 255], trig),
    // ○ start of the route · ■ end of the route (only when the car is somewhere else now)
    new deck.ScatterplotLayer({
      id: 'track-ends', data: ends, radiusUnits: 'pixels',
      getRadius: d => d.k === 'e' ? 6 : 7, stroked: true, filled: true, lineWidthUnits: 'pixels', getLineWidth: 2.5,
      getPosition: d => [POS[2 * d.i], POS[2 * d.i + 1]],
      getFillColor: d => d.k === 'e' ? [...TRK_RGB, 235] : [255, 255, 255, 220],
      getLineColor: d => d.k === 'e' ? [255, 255, 255, 255] : [...TRK_RGB, 255],
      updateTriggers: { getPosition: trig },
    }),
    // the real route ahead is already drawn dashed → drop the estimated route line (keep the A / B / ? markers)
    ...tripLayers(v).filter(l => !(ahead.length && l.id === 'trip-line')),
  ];
}
/* the driven route along roads between lo and hi: consecutive kept points → their road leg
   (the leg the cursor is in is cut where the car is now) · no line across a signal gap, like the straight version */
function snappedPaths(snap, lo, hi) {
  const out = [], K = snap.kept;
  let cur = [];
  const flush = () => { if (cur.length > 1) out.push(cur); cur = []; };
  for (let n = 0; n + 1 < K.length; n++) {
    const a = K[n], b = K[n + 1];
    if (TT[b] < lo) continue;
    if (TT[a] >= hi) break;
    const leg = snap.legs.get(a);
    let piece;
    if (b - a >= 1 && TT[b] - TT[b - 1] > CFG.STALE_MIN * 60 && hav(POS[2 * a], POS[2 * a + 1], POS[2 * b], POS[2 * b + 1]) > 1) { flush(); continue; }
    if (!leg) piece = [[POS[2 * a], POS[2 * a + 1]], [POS[2 * b], POS[2 * b + 1]]];
    else piece = leg.path;
    if (TT[b] > hi) piece = cutAt(piece, leg ? leg.cum : null, (hi - TT[a]) / (TT[b] - TT[a]));
    if (TT[a] < lo) piece = cutFrom(piece, leg ? leg.cum : null, (lo - TT[a]) / (TT[b] - TT[a]));
    cur.push(...(cur.length ? piece.slice(1) : piece));
  }
  flush();
  return out;
}
function cumOf(p) { const c = [0]; for (let k = 1; k < p.length; k++) c.push(c[k - 1] + hav(p[k - 1][0], p[k - 1][1], p[k][0], p[k][1])); return c; }
/* point at fraction f (0–1) of a path's length → [index of the segment end, point] */
function alongPath(p, cum, f) {
  cum = cum || cumOf(p);
  const d = Math.max(0, Math.min(1, f)) * cum[cum.length - 1];
  let k = 1; while (k < cum.length - 1 && cum[k] < d) k++;
  const g = (d - cum[k - 1]) / ((cum[k] - cum[k - 1]) || 1);
  return [k, [p[k - 1][0] + (p[k][0] - p[k - 1][0]) * g, p[k - 1][1] + (p[k][1] - p[k - 1][1]) * g]];
}
function cutAt(p, cum, f) { const [k, q] = alongPath(p, cum, f); return [...p.slice(0, k), q]; }
function cutFrom(p, cum, f) { const [k, q] = alongPath(p, cum, f); return [q, ...p.slice(k)]; }
/* where the selected car is on its road leg at time T (for smooth replay along roads) → [lon, lat, heading] or null */
function snappedAt(v, T) {
  if (ROADS) return null;                                            // the road file already places every car (fleet.js)
  const snap = Router.trackPeek(v); if (!snap) return null;
  const K = snap.kept;
  let lo = 0, hi = K.length - 1;
  if (!K.length || T < TT[K[0]] || T >= TT[K[hi]]) return null;
  while (lo < hi - 1) { const m = (lo + hi) >> 1; if (TT[K[m]] <= T) lo = m; else hi = m; }
  const a = K[lo], b = K[lo + 1], leg = snap.legs.get(a);
  if (!leg || TT[b] - TT[a] > CFG.STALE_MIN * 60 * 4) return null;
  // the car stood at a for part of the time (jitter points in between) — move only during the last moving stretch
  let start = TT[a];
  for (let i = b - 1; i > a; i--) if (hav(POS[2 * i], POS[2 * i + 1], POS[2 * a], POS[2 * a + 1]) < 0.06) { start = TT[i]; break; }
  const f = T <= start ? 0 : (T - start) / (TT[b] - start);
  const [k, q] = alongPath(leg.path, leg.cum, f);
  const p0 = leg.path[k - 1], p1 = leg.path[k];
  return [q[0], q[1], bearing(p0[0], p0[1], p1[0], p1[1])];
}
/* trip of the selected car: A = where it left from · B = next stop (from data) or the estimated destination */
function tripLayers(v) {
  const r = updateTrip();
  if (!r || r.stopped) return [];
  const pts = [];
  if (r.origin) pts.push({ k: 'A', lon: r.origin.lon, lat: r.origin.lat });
  if (r.next) pts.push({ k: r.next.kind === 'data' ? 'B' : '?', lon: r.next.lon, lat: r.next.lat });
  if (!pts.length) return [];
  const trig = [v, S.T];
  const out = [];
  if (r.next) {
    const rt = routeFor(r);
    const path = rt ? rt.path : [[r.here.lon, r.here.lat], [r.next.lon, r.next.lat]];
    out.push(new deck.PathLayer({
      id: 'trip-line', data: dashes(path), getPath: p => p,
      widthUnits: 'pixels', getWidth: rt ? 3 : 2, getColor: r.next.kind === 'data' ? [124, 58, 237, 220] : [194, 122, 0, 230],
      updateTriggers: { getPath: [trig, !!rt, Z2], getColor: trig, getWidth: !!rt },
    }));
  }
  out.push(new deck.ScatterplotLayer({
    id: 'trip-pts', data: pts, radiusUnits: 'pixels', getRadius: 11, stroked: true, lineWidthUnits: 'pixels', getLineWidth: 2,
    getPosition: p => [p.lon, p.lat], getFillColor: p => p.k === 'A' ? [0, 96, 28, 235] : p.k === 'B' ? [124, 58, 237, 235] : [194, 122, 0, 235],
    getLineColor: [255, 255, 255, 255], updateTriggers: { getPosition: trig, getFillColor: trig },
  }));
  out.push(new deck.TextLayer({
    id: 'trip-k', data: pts, getPosition: p => [p.lon, p.lat], getText: p => p.k, getSize: 12, fontWeight: 700,
    getColor: [255, 255, 255, 255], characterSet: 'AB?', fontFamily: 'IBM Plex Mono, monospace', updateTriggers: { getPosition: trig, getText: trig },
  }));
  return out;
}
/* cut a polyline into dashes of a fixed on-screen size (deck's dash extension restarts the pattern at every vertex,
   so a road route made of hundreds of tiny pieces came out solid) · redrawn when the zoom changes */
function dashes(path, dashPx = 8, gapPx = 6) {
  const L = [0];
  for (let k = 1; k < path.length; k++) L.push(L[k - 1] + hav(path[k - 1][0], path[k - 1][1], path[k][0], path[k][1]));
  const total = L[L.length - 1];
  if (!total) return [path];
  const kmPx = metersPerPx() / 1000, step = (dashPx + gapPx) * kmPx, on = dashPx * kmPx, out = [];
  if (total / step > 20000) return [path];                           // zoomed far out: solid is fine (dashes would be sub-pixel)
  // d only ever grows → the segment pointer only moves forward (one pass over the path, not one per dash)
  let k = 1;
  const at = d => { while (k < L.length - 1 && L[k] < d) k++; const f = (d - L[k - 1]) / ((L[k] - L[k - 1]) || 1);
    return [k, [path[k - 1][0] + (path[k][0] - path[k - 1][0]) * f, path[k - 1][1] + (path[k][1] - path[k - 1][1]) * f]]; };
  for (let d0 = 0; d0 < total; d0 += step) {
    const d1 = Math.min(total, d0 + on), [k0, p0] = at(d0), [k1, p1] = at(d1);
    out.push([p0, ...path.slice(k0, k1), p1]);
  }
  return out;
}
/* road route for the trip's next leg — cached; asks the router once and redraws when it answers */
function routeFor(r) {
  const a = { lon: r.here.lon, lat: r.here.lat }, b = { lon: r.next.lon, lat: r.next.lat };
  const hit = Router.peek(a, b);
  if (hit !== null || Router.cache.has(Router.key(a, b))) return hit;
  if (S.playing) return null;                                       // no requests during playback — asked again once paused
  Router.get(a, b).then(rt => { if (rt) { render(); if (S.panel === 'vehicles' && S.sel >= 0) updateVehLive(); } });
  return null;
}
/* cached trip of the selected vehicle at the cursor (recomputed when the car or the cursor changes) */
let TRIP = null;
function updateTrip() {
  if (S.sel < 0) { TRIP = null; return null; }
  if (!TRIP || TRIP.v !== S.sel || TRIP.T !== S.T) TRIP = { v: S.sel, T: S.T, info: tripInfo(S.sel, S.T) };
  return TRIP.info;
}

let ZONE_GEO = { type: 'FeatureCollection', features: [] };
function buildZoneGeo() {
  const z = CFG.ZONES[S.zone];
  ZONE_GEO = { type: 'FeatureCollection', features: [
    ...D.geo.prov.features.filter(f => z.prov.includes(f.properties.pc)),
    ...D.geo.dist.features.filter(f => z.dist.includes(f.properties.pc)),
  ] };
}

/* ── overlays: chargers · overnight stops / depots · stops of the selected car · place pin ── */
// EV chargers from OpenStreetMap: [lat, lon, name, operator, sockets, capacity] — only part of the real network
const EV = (EMBEDDED && EMBEDDED.ev) || [];
let EV_FOCUS = [];                                                 // chargers the assistant is pointing at (numbered)
function overlayLayers(layers) {
  if (S.ev && EV.length) {
    layers.push(new deck.ScatterplotLayer({
      id: 'ev', data: EV, pickable: true, radiusUnits: 'pixels', getRadius: 5.5,
      stroked: true, lineWidthUnits: 'pixels', getLineWidth: 1.5,
      getPosition: d => [d[1], d[0]], getFillColor: rgba(COL.charger, 220), getLineColor: [255, 255, 255, 240],
    }));
  }
  if (EV_FOCUS.length) {
    layers.push(new deck.ScatterplotLayer({
      id: 'ev-focus', data: EV_FOCUS, pickable: true, radiusUnits: 'pixels', getRadius: 11,
      stroked: true, lineWidthUnits: 'pixels', getLineWidth: 2.5,
      getPosition: d => [d[1], d[0]], getFillColor: rgba(COL.charger, 235), getLineColor: [255, 255, 255, 255],
    }));
    layers.push(new deck.TextLayer({
      id: 'ev-focus-n', data: EV_FOCUS, getPosition: d => [d[1], d[0]], getText: (d, { index }) => String(index + 1),
      getSize: 12, getColor: [255, 255, 255, 255], fontWeight: 700, characterSet: '0123456789',
      fontFamily: 'IBM Plex Mono, monospace',
    }));
  }
  if (S.panel === 'parking' && depotsReady()) {
    const data = [...NIGHT.values()].filter(x => !S.areas.size || areaMatchDist(x.d));
    layers.push(new deck.ScatterplotLayer({
      id: 'night', data, pickable: true, radiusUnits: 'pixels', getRadius: 4.5, stroked: true, lineWidthUnits: 'pixels', getLineWidth: 1,
      getPosition: x => [x.lon, x.lat],
      getFillColor: x => inZone(x.d) ? [0, 163, 50, 210] : [217, 58, 64, 230],
      getLineColor: [255, 255, 255, 230],
      updateTriggers: { getFillColor: [S.zone, layerVer] },
    }));
    layers.push(new deck.ScatterplotLayer({
      id: 'depot', data: DEPOTS, pickable: true, radiusUnits: 'pixels',
      getRadius: d => 9 + Math.sqrt(d.n) * 2.2, stroked: true, filled: true, lineWidthUnits: 'pixels', getLineWidth: 2.5,
      getPosition: d => [d.lon, d.lat], getFillColor: [28, 43, 74, 60], getLineColor: [28, 43, 74, 255],
    }));
    layers.push(new deck.TextLayer({
      id: 'depot-n', data: DEPOTS, getPosition: d => [d.lon, d.lat], getText: d => String(d.n),
      getSize: 12, getColor: [28, 43, 74, 255], fontWeight: 700, characterSet: '0123456789',
      fontFamily: 'IBM Plex Mono, monospace', getPixelOffset: d => [0, -(14 + Math.sqrt(d.n) * 2.2)],
      outlineWidth: 3, outlineColor: [255, 255, 255, 255], fontSettings: { sdf: true },
    }));
  }
  const vst = S.sel >= 0 && S.panel === 'vehicles' ? selStays() : null;
  if (vst && vst.length) {
    layers.push(new deck.ScatterplotLayer({
      id: 'vstays', data: vst, pickable: true, radiusUnits: 'pixels',
      getRadius: x => 7 + Math.min(16, Math.sqrt(x.dur / 600) * 3), stroked: true, filled: true, lineWidthUnits: 'pixels', getLineWidth: 2,
      getPosition: x => [x.lon, x.lat],
      getFillColor: x => isNight(x) ? [28, 43, 74, 90] : [120, 134, 126, 45],
      getLineColor: x => isNight(x) ? [28, 43, 74, 255] : [90, 104, 96, 255],
    }));
  }
  if (PLACE) {
    layers.push(new deck.ScatterplotLayer({
      id: 'place', data: [PLACE], radiusUnits: 'pixels', getRadius: 11, stroked: true, filled: true, lineWidthUnits: 'pixels', getLineWidth: 3,
      getPosition: p => [p.lon, p.lat], getFillColor: [255, 255, 255, 60], getLineColor: [16, 35, 26, 255],
    }));
  }
}
/* stops of the selected vehicle in the selected range — cached, recomputed only when the car or range changes */
let _selStays = { key: '', list: [] };
function selStays() {
  const key = S.sel + '|' + S.a + '|' + S.b;
  if (_selStays.key !== key) _selStays = { key, list: S.sel >= 0 ? staysOf(S.sel) : [] };
  return _selStays.list;
}
