/* js/map/map.js — the map (MapLibre + deck.gl overlay) · base map switch · 2D / 3D
   uses: config.js · interaction.js
   provides: initMap() · setBasemap() · set3D() · is3D() · flyHome() · fitThailand() · fitPoints() */

function initMap() {
  map = new maplibregl.Map({
    container: 'map', style: BASEMAPS[S.basemap].style, center: CFG.HOME_VIEW.center, zoom: CFG.HOME_VIEW.zoom,
    attributionControl: { compact: true }, maxPitch: 70,        // right-drag or Ctrl+drag = rotate / tilt
    fadeDuration: 0,
  });
  map.on('error', e => {
    // vector style could not be fetched (offline, blocked) → simple raster map so the page still works
    if (!initMap._fell && e && e.error && /style|fetch|Failed/i.test(String(e.error.message || '')) && !map.isStyleLoaded()) {
      initMap._fell = true; map.setStyle(FALLBACK_STYLE);
    }
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), 'top-right');
  deckOverlay = new deck.MapboxOverlay({
    interleaved: false, layers: [],
    getTooltip: tooltip,
    onClick: onMapClick,
    onError: e => showErr('map', e),
  });
  map.addControl(deckOverlay);
  map.on('dragstart', e => { if (e.originalEvent && S.follow && S.sel >= 0 && (S.playing || isLive())) setFollow(false); });
  map.on('zoom', rafThrottle(onZoomScale));                       // dots / arrows follow the zoom
  let was3D = false;
  map.on('rotate', rafThrottle(() => { if (is3D()) render(); }));   // 3D arrows are aimed against the bearing
  map.on('pitch', rafThrottle(() => { if (is3D() !== was3D) { was3D = is3D(); render(); } }));
  map.on('pitchend', () => window.syncMapTools && syncMapTools());
}
function setBasemap(k) {
  if (!BASEMAPS[k] || k === S.basemap) return;
  S.basemap = k; initMap._fell = false;
  map.setStyle(BASEMAPS[k].style);
  store.set('ev7.basemap', k);
}
const is3D = () => !!map && map.getPitch() > 5;
// 3D buildings exist only on the Streets map at zoom ≥ 14, so switch to it
function set3D(on) {
  if (on) {
    if (S.basemap === 'light') setBasemap('streets');
    map.easeTo({ pitch: 60, bearing: map.getBearing() || -20, zoom: Math.max(map.getZoom(), 15.5), duration: 700 });
  } else map.easeTo({ pitch: 0, bearing: 0, duration: 500 });
}
function flyHome() { map.flyTo({ center: CFG.HOME_VIEW.center, zoom: CFG.HOME_VIEW.zoom, pitch: 0, bearing: 0, duration: 800 }); }
function fitThailand() { map.fitBounds(CFG.TH_BOUNDS, { padding: 30, duration: 800 }); }
/* fit the map to [[lon,lat], …] — keeps room for the panels that cover the map */
function fitPoints(pts, maxZoom = 14) {
  if (!pts.length) return;
  if (pts.length === 1) { map.flyTo({ center: pts[0], zoom: Math.max(map.getZoom(), Math.min(maxZoom, 14)), duration: 800 }); return; }
  let x0 = 999, y0 = 999, x1 = -999, y1 = -999;
  for (const [x, y] of pts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  const chat = document.body.classList.contains('chat-open') ? 380 : 0;
  map.fitBounds([[x0, y0], [x1, y1]], { padding: { top: 70, bottom: 60, left: 60, right: 60 + chat }, maxZoom, duration: 800 });
}
