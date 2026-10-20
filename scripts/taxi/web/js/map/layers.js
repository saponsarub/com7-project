/* js/map/layers.js — ชั้นข้อมูลบนแผนที่ (deck.gl) — จุด · สีพื้นที่ · เส้นทางรถ · จุดจอด/ลานจอด
   ใช้: analysis/* · cars.js
   ให้: render() · rangeData() · choroColor() · buildZoneGeo() · addV2Layers()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

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
let pcToProv, pcToDist;
let layerVer = 0;
function render() {
  if (!deckOverlay) return;
  const layers = [];
  const geo = S.level === 'prov' ? D.geo.prov : D.geo.dist;
  const idxOf = S.level === 'prov' ? pcToProv : pcToDist;
  const pre = S.level === 'prov' ? 'p:' : 'd:';
  if (S.choro) {
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
  // เส้นขอบเขตที่อนุญาต
  layers.push(new deck.GeoJsonLayer({
    id: 'zone', data: ZONE_GEO, stroked: true, filled: false, pickable: false,
    getLineColor: [13, 147, 214, 230], getLineWidth: 2.2, lineWidthUnits: 'pixels',
    updateTriggers: { getLineColor: [S.zone] },
  }));
  if (S.pt === 'range' || (S.pt === 'now' && S.trail > 0)) {
    const lo = S.pt === 'range' ? S.a : Math.max(S.a, S.T - S.trail * 60);
    const hi = S.pt === 'range' ? S.b : S.T;
    layers.push(new deck.ScatterplotLayer({
      id: 'range', data: rangeData(), radiusUnits: 'pixels', getRadius: S.pt === 'range' ? 1.4 : 1.6,
      radiusMinPixels: 1, opacity: S.pt === 'range' ? 0.55 : 0.35, stroked: false,
      extensions: [new deck.DataFilterExtension({ filterSize: 2 })],
      filterRange: [[lo, hi], [0.5, 1.5]],
      updateTriggers: { getFilterValue: RANGE_VER },
    }));
  }
  if (S.sel >= 0) layers.push(...trackLayers(S.sel));
  // สร้างทั้งชั้นรูปรถและชั้นจุดไว้ตลอด แล้วสลับ visible — รูปรถโหลดรอไว้ก่อน สลับแล้วขึ้นทันที
  const carOn = S.pt === 'now' && useCarIcons();
  if (S.pt === 'now') layers.push(...carLayers().map(l => l.clone({ visible: carOn })));
  if (S.pt === 'now') {
    // ⚠️ deck.gl จับคู่ชั้นด้วย id — ชั้นต่างชนิดห้ามใช้ id ซ้ำ ไม่งั้นตอนสลับจุด↔รูปรถ
    //    deck เอา state ของ ScatterplotLayer ไปให้ IconLayer แล้วพังทั้งชั้น (จุดหาย รูปไม่ขึ้น)
    layers.push(new deck.ScatterplotLayer({
      id: 'now', data: NOW, pickable: true, radiusUnits: 'pixels', visible: !carOn,
      getPosition: d => [POS[2 * d.i], POS[2 * d.i + 1]],
      getRadius: d => d.v === S.sel ? 8 : 4.2,
      getFillColor: d => rgba(COL[d.st], d.v === S.sel ? 255 : 235),
      stroked: true, lineWidthUnits: 'pixels',
      getLineColor: d => d.out ? [217, 58, 64, 255] : [255, 255, 255, 230],
      getLineWidth: d => d.out ? 2.2 : 1,
      updateTriggers: { getPosition: S.T, getFillColor: [S.T, S.sel], getRadius: S.sel, getLineColor: S.T, getLineWidth: S.T },
    }));
  }
  if (S.pt === 'now' && !carOn) layers.push(...dirLayers());
  addV2Layers(layers);
  deckOverlay.setProps({ layers });
}
/* ── ทิศทางรถ ───────────────────────────────────────────────────────
   ลูกศรวางราบกับพื้น (billboard: false) จึงชี้ถูกแม้หมุน/เอียงแผนที่ · ทิศมาจาก GPS (0° = เหนือ ตามเข็ม)
   deck.gl หมุนทวนเข็ม → ใส่มุมติดลบ · mask: true = ระบายสีตาม getColor                          */
const ARROW = {
  url: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path d="M32 3 L56 58 L32 45 L8 58 Z" fill="#fff"/></svg>'),
  map: { a: { x: 0, y: 0, width: 64, height: 64, anchorY: 32, mask: true } },
};
function headDeg(i) { const H = D.cols.head; return H ? H[i] * 360 / 256 : 0; }
const isMoving = i => !(FLG[i] & 2) && SPD[i] >= CFG.MOVING_KMH && !!D.cols.head;
function arrowLayer(id, data, idxOf, size, getColor, trig) {
  return new deck.IconLayer({
    id, data, iconAtlas: ARROW.url, iconMapping: ARROW.map, getIcon: () => 'a',
    billboard: false, sizeUnits: 'pixels', getSize: size, getColor,
    getPosition: d => { const i = idxOf(d); return [POS[2 * i], POS[2 * i + 1]]; },
    getAngle: d => -headDeg(idxOf(d)),
    updateTriggers: { getPosition: trig, getAngle: trig, getColor: trig, getSize: trig },
  });
}
// รถที่กำลังวิ่ง ณ เวลาที่เลือก: ลูกศรขาว (ขอบ) + ลูกศรสีตามสถานะ ซ้อนบนจุด
function dirLayers() {
  const mov = NOW.filter(d => isMoving(d.i));
  const sz = d => d.v === S.sel ? 22 : 15;
  return [
    arrowLayer('now-dir-o', mov, d => d.i, d => sz(d) + 5, [255, 255, 255, 235], [S.T, S.sel]),
    arrowLayer('now-dir', mov, d => d.i, sz, d => rgba(COL[d.st].map(c => Math.round(c * 0.75)), 255), [S.T, S.sel]),
  ];
}
/* ── เส้นทางรถที่เลือก ───────────────────────────────────────────────
   S.trk = 'all'  ทั้งช่วงที่เลือกบน timeline (S.a → S.b)
   S.trk = 'live' ถึงเวลาปัจจุบันของ timeline (S.a → S.T) — กด ▶ แล้วเส้นจะงอกตามรถ
   เส้นขาดเมื่อช่วงห่างของจุดเกิน CFG.STALE_MIN (ไม่ลากเส้นข้ามช่วงที่ไม่มีสัญญาณ)              */
function trackLayers(v) {
  const s = D.vehicles.start[v], n = D.vehicles.count[v];
  const hi = S.trk === 'live' ? S.T : S.b;
  const idx = [];
  for (let i = s; i < s + n; i++) if (TT[i] >= S.a && TT[i] <= hi && !(FLG[i] & 2)) idx.push(i);
  if (!idx.length) return [];
  const gap = CFG.STALE_MIN * 60, paths = [];
  let cur = [];
  for (let k = 0; k < idx.length; k++) {
    const i = idx[k];
    if (k && TT[i] - TT[idx[k - 1]] > gap) { if (cur.length > 1) paths.push(cur); cur = []; }
    cur.push([POS[2 * i], POS[2 * i + 1]]);
  }
  if (cur.length > 1) paths.push(cur);
  const span = Math.max(1, hi - S.a);
  const col = i => { const r = (TT[i] - S.a) / span; return [Math.round(200 - 190 * r), Math.round(225 - 120 * r), Math.round(240 - 30 * r), 235]; };
  // ลูกศรตามเส้นทาง: เฉพาะจุดที่กำลังวิ่ง เว้นระยะให้เหลือไม่เกิน ~40 ตัว
  const mov = idx.filter(isMoving), step = Math.max(1, Math.ceil(mov.length / 40));
  const arrows = mov.filter((_, k) => k % step === 0);
  const last = idx[idx.length - 1], trig = [S.a, hi, S.trk, v];
  const out = [
    new deck.PathLayer({
      id: 'track-line', data: paths, getPath: p => p, widthUnits: 'pixels', getWidth: 2.5,
      getColor: [28, 43, 74, 150], capRounded: true, jointRounded: true, updateTriggers: { getPath: trig },
    }),
    new deck.ScatterplotLayer({
      id: 'track', data: idx, radiusUnits: 'pixels', getRadius: 3.2, stroked: true, lineWidthUnits: 'pixels', getLineWidth: 0.6,
      getPosition: i => [POS[2 * i], POS[2 * i + 1]], getFillColor: col,
      getLineColor: [255, 255, 255, 200], pickable: true,
      updateTriggers: { getFillColor: trig, getPosition: trig },
    }),
    arrowLayer('track-dir', arrows, i => i, 13, i => col(i).map((c, k) => k < 3 ? Math.round(c * 0.55) : 255), trig),
  ];
  // ต้น-ปลาย: วงโปร่ง = จุดเริ่ม · วงแดง (+ ลูกศรถ้ากำลังวิ่ง) = ตำแหน่งล่าสุด (โหมด live = ณ เวลา timeline)
  out.push(new deck.ScatterplotLayer({
    id: 'track-ends', data: [{ i: idx[0], k: 's' }, { i: last, k: 'e' }], radiusUnits: 'pixels',
    getRadius: d => d.k === 'e' ? 9 : 7, stroked: true, filled: true, lineWidthUnits: 'pixels', getLineWidth: 2.5,
    getPosition: d => [POS[2 * d.i], POS[2 * d.i + 1]],
    getFillColor: d => d.k === 'e' ? [217, 58, 64, 230] : [255, 255, 255, 200],
    getLineColor: d => d.k === 'e' ? [255, 255, 255, 255] : [28, 43, 74, 255],
    updateTriggers: { getPosition: trig },
  }));
  if (isMoving(last)) out.push(arrowLayer('track-head', [last], i => i, 24, [217, 58, 64, 255], trig));
  return out;
}
let ZONE_GEO = { type: 'FeatureCollection', features: [] };
function buildZoneGeo() {
  const z = CFG.ZONES[S.zone];
  ZONE_GEO = { type: 'FeatureCollection', features: [
    ...D.geo.prov.features.filter(f => z.prov.includes(f.properties.pc)),
    ...D.geo.dist.features.filter(f => z.dist.includes(f.properties.pc)),
  ] };
}
/* ── ชั้นแผนที่ ────────────────────────────────────────────────────── */
// สถานีชาร์จ EV จาก OpenStreetMap: [lat, lon, ชื่อ, ผู้ให้บริการ, หัวชาร์จ, จำนวนช่อง] · มีแค่บางส่วนของของจริง
const EV = (EMBEDDED && EMBEDDED.ev) || [];
function addV2Layers(layers) {
  if (S.ev && EV.length) {
    layers.push(new deck.ScatterplotLayer({
      id: 'ev', data: EV, pickable: true, radiusUnits: 'pixels', getRadius: 5.5,
      stroked: true, lineWidthUnits: 'pixels', getLineWidth: 1.5,
      getPosition: d => [d[1], d[0]], getFillColor: [124, 58, 237, 220], getLineColor: [255, 255, 255, 240],
    }));
  }
  if (S.tab === 'stay') {
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
  if (S.sel >= 0 && STAYS_BY_V.has(S.sel)) {
    layers.push(new deck.ScatterplotLayer({
      id: 'vstays', data: STAYS_BY_V.get(S.sel), pickable: true, radiusUnits: 'pixels',
      getRadius: x => 7 + Math.min(16, Math.sqrt(x.dur / 600) * 3), stroked: true, filled: true, lineWidthUnits: 'pixels', getLineWidth: 2,
      getPosition: x => [x.lon, x.lat],
      getFillColor: x => x.night >= CFG2.NIGHT_MIN_H * 3600 ? [28, 43, 74, 90] : [13, 147, 214, 40],
      getLineColor: x => x.night >= CFG2.NIGHT_MIN_H * 3600 ? [28, 43, 74, 255] : [13, 147, 214, 255],
    }));
  }
  if (PLACE) {
    layers.push(new deck.ScatterplotLayer({
      id: 'place', data: [PLACE], radiusUnits: 'pixels', getRadius: 11, stroked: true, filled: true, lineWidthUnits: 'pixels', getLineWidth: 3,
      getPosition: p => [p.lon, p.lat], getFillColor: [255, 255, 255, 60], getLineColor: [16, 35, 26, 255],
    }));
  }
}
