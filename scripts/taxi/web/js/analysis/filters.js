/* js/analysis/filters.js — filters that do not depend on time (center · status · area) → MASK per point
   uses: state.js · model.js
   provides: areaMatchDist() · vehPass() · rebuildMask() · zoneSets() · inZone() */

function areaMatchDist(dIdx) {
  if (!S.areas.size) return true;
  if (dIdx === 65535) return false;
  return S.areas.has('d:' + dIdx) || S.areas.has('p:' + distProv[dIdx]);
}
function vehPass(v) {
  return !S.centers.size || S.centers.has(D.vehicles.center[v]);
}
function rebuildMask() {
  MASK = new Uint8Array(N);
  const st = S.status, allSt = st.size === 3, noArea = !S.areas.size;
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const s = D.vehicles.start[v], e = s + D.vehicles.count[v];
    for (let i = s; i < e; i++) {
      if (!allSt) { const sx = status(i); if (sx !== 'nosig' && !st.has(sx)) continue; }
      if (!noArea && !areaMatchDist(DI[i])) continue;
      MASK[i] = 1;
    }
  }
  maskVer++;
}

/* allowed zone (selected preset) → sets of province / district indexes — cached per zone */
let _zoneCache = { zone: null };
function zoneSets() {
  if (_zoneCache.zone === S.zone) return _zoneCache;
  const z = CFG.ZONES[S.zone];
  const pIdx = new Set(z.prov.map(pc => PROV.findIndex(p => p.pc === pc)));
  const dIdx = new Set(z.dist.map(pc => DIST.findIndex(d => d.pc === pc)));
  _zoneCache = { zone: S.zone, pIdx, dIdx };
  return _zoneCache;
}
function inZone(dI) {
  if (dI === 65535) return true;
  const { pIdx, dIdx } = zoneSets();
  return pIdx.has(distProv[dI]) || dIdx.has(dI);
}
