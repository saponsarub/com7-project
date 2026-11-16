/* js/map/car3d.js — low-poly 3D taxis for the tilted (3D) map: body in the status colour, dark glass and wheels,
   nose pointing the way the car is going. Built from boxes in code — no model file, no licence to track.
   uses: layers.js (nowData · alphaOf) · fleet.js (d.x · d.y · d.h)
   provides: car3dLayers() · CAR3D_ZOOM */

const CAR3D_ZOOM = 13;                  // from this zoom the tilted map shows 3D cars instead of arrows / dots
const CAR3D_PX = 26;                    // on-screen length we aim for (a real 4.6 m car is only 2–3 px at zoom 15)

/* mesh in metres · x = right · y = forward (nose) · z = up · vertex colour multiplies the instance colour:
   1 = takes the status colour · dark values stay dark (glass, tyres) */
let CAR_MESH = null;
function carMesh() {
  if (CAR_MESH) return CAR_MESH;
  const P = [], Nn = [], C = [];
  const box = (x0, x1, y0, y1, z0, z1, c) => {
    const v = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]];
    const faces = [[0, 1, 2, 3, [0, 0, -1]], [4, 7, 6, 5, [0, 0, 1]], [0, 4, 5, 1, [0, -1, 0]], [3, 2, 6, 7, [0, 1, 0]], [0, 3, 7, 4, [-1, 0, 0]], [1, 5, 6, 2, [1, 0, 0]]];
    for (const [a, b, cc, d, n] of faces) for (const k of [a, b, cc, a, cc, d]) { P.push(...v[k]); Nn.push(...n); C.push(...c); }
  };
  const W = [1, 1, 1], GLASS = [0.16, 0.2, 0.24], TYRE = [0.07, 0.07, 0.08], LIGHT = [1.6, 1.6, 1.4];
  box(-0.9, 0.9, -2.3, 2.3, 0.28, 0.82, W);            // body
  box(-0.86, 0.86, 1.2, 2.3, 0.82, 0.95, W);           // bonnet (nose, +y)
  box(-0.8, 0.8, -1.5, 0.9, 0.82, 1.38, GLASS);        // cabin = glass all round …
  box(-0.76, 0.76, -1.4, 0.8, 1.38, 1.46, W);          // … with a roof
  box(-0.26, 0.26, -0.45, -0.05, 1.46, 1.68, W);       // TAXI sign
  box(-0.7, -0.35, 2.3, 2.34, 0.55, 0.72, LIGHT);      // headlights (show which end is the front)
  box(0.35, 0.7, 2.3, 2.34, 0.55, 0.72, LIGHT);
  for (const sx of [-1, 1]) for (const wy of [-1.5, 1.45]) box(sx > 0 ? 0.78 : -0.96, sx > 0 ? 0.96 : -0.78, wy - 0.33, wy + 0.33, 0, 0.62, TYRE);
  CAR_MESH = { positions: { size: 3, value: new Float32Array(P) }, normals: { size: 3, value: new Float32Array(Nn) }, colors: { size: 3, value: new Float32Array(C) } };
  return CAR_MESH;
}
const use3DCars = () => is3D() && map.getZoom() >= CAR3D_ZOOM;
/* metres per screen pixel at the map centre (MapLibre uses 512 px tiles) */
const metersPerPx = () => 78271.517 * Math.cos(map.getCenter().lat * Math.PI / 180) / 2 ** map.getZoom();

function car3dLayers(data) {
  const s = Math.max(1, CAR3D_PX * metersPerPx() / 4.6);
  const sel = S.sel;
  return [new deck.SimpleMeshLayer({
    id: 'car3d', data, mesh: carMesh(), pickable: true, sizeScale: s,
    getPosition: d => [d.x, d.y, 0],
    getOrientation: d => [0, -d.h, 0],                          // [pitch, yaw, roll] · heading is clockwise, yaw counter-clockwise
    getScale: d => d.v === sel ? [1.35, 1.35, 1.35] : [1, 1, 1],
    getColor: d => d.out ? rgba(COL[d.st].map(c => Math.round(c * 0.85)), alphaOf(d.v, 255)) : rgba(COL[d.st], alphaOf(d.v, 255)),
    material: { ambient: 0.55, diffuse: 0.55, shininess: 40, specularColor: [70, 74, 80] },
    updateTriggers: { getPosition: S.T, getOrientation: S.T, getColor: [S.T, S.sel, S.others], getScale: S.sel },
  })];
}
