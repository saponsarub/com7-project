/* js/config.js — every tunable setting in one place
   provides: CFG · CFG2 · COL · RAMP · BASEMAPS · AI
   ⚠️ All files share one global scope (classic scripts, not ES modules) so the page also opens
      from file://. Load order lives in index.html — a file must load after the files it uses.
   Deploy: a server can override any value by defining window.EV7_CONFIG before this file loads,
      e.g. an inline script in index.html: window.EV7_CONFIG = { ai: { endpoint: '/api/agent' } }   */

const CFG = {
  STALE_MIN: 15,          // last GPS point older than this = vehicle not online at that moment
  GAP_MIN: 30,            // gap between points longer than this = separate segments
  MOVING_KMH: 5,          // faster than this = moving
  GLIDE_KM: 0.4,          // playback: glide between two GPS fixes only if they are this close (else hop fix to fix — no flying across blocks)
  BKK_CENTER: [100.5018, 13.7563],
  HOME_VIEW: { center: [100.62, 13.78], zoom: 9.6 },
  TH_BOUNDS: [[97.3, 5.6], [105.7, 20.5]],
  CENTER_NAMES: { '0a': 'Center 0a', 'yF': 'Center yF', 'ux': 'Center ux' },   // real names not known yet
  ZONES: {               // allowed zone · default = metro: Bangkok + vicinity vs everywhere else
    metro:   { label: 'Bangkok + vicinity', prov: ['TH10', 'TH11', 'TH12', 'TH13', 'TH73', 'TH74'], dist: [] },
    bkk:     { label: 'Bangkok only', prov: ['TH10'], dist: [] },
    bkk_air: { label: 'Bangkok + Suvarnabhumi', prov: ['TH10'], dist: ['TH1103'] },   // TH1103 = Bang Phli (airport)
  },
  METRO: ['TH11', 'TH12', 'TH13', 'TH73', 'TH74'],    // Bangkok vicinity provinces
  AREA_PRESETS: {         // quick area filter in the filter bar
    bkk: { label: 'Bangkok', prov: ['TH10'] },
    metro: { label: 'Bangkok + vicinity', short: 'BKK + vicinity', prov: ['TH10', 'TH11', 'TH12', 'TH13', 'TH73', 'TH74'] },   // + Samut Prakan · Nonthaburi · Pathum Thani · Nakhon Pathom · Samut Sakhon
  },
  REFRESH_SEC: 60,        // live: check for new data this often (only when served over http — a file:// copy is a fixed snapshot)
  LIVE_LAG_SEC: 300,      // live: the clock runs this far behind the newest data (= one 5-min GPS batch) so cars always drive between fixes they have
};

/* stops · overnight · depots — same logic as build_dashboard.find_depots() */
const CFG2 = {
  STAY_R_KM: 0.2,         // within this radius = same spot
  STAY_MIN: 30,           // parked at least this long (min) = a stop
  NIGHT_H: [0, 5],        // overnight window 00:00–05:00
  NIGHT_MIN_H: 1,         // must overlap the overnight window at least this long (h)
  DEPOT_R_KM: 0.2,        // overnight spots closer than this = same place
  DEPOT_MIN: 5,           // at least this many vehicles overnight together = depot
  DEPOT_NEAR_KM: 0.3,     // a point this close to a depot = inside the depot
  NOMINATIM: 'https://nominatim.openstreetmap.org/reverse',
  ROUTER: 'https://router.project-osrm.org/route/v1/driving/',   // OSRM demo (light use) — self-host for production
};

const COL = {
  hired: [240, 140, 0], vacant: [0, 163, 50], park: [138, 151, 166], nosig: [194, 201, 209],
  red: [217, 58, 64], blue: [13, 147, 214], charger: [124, 58, 237],
};
const STATUS_LABEL = { hired: 'On trip', vacant: 'Available · moving', park: 'Parked', nosig: 'No GPS signal' };
const RAMP = ['#e3f4e8', '#b9e3c5', '#86cf9b', '#4fb56f', '#1f9148', '#0b6e30', '#00491c'];

/* ── base maps ─────────────────────────────────────────────────────────
   ⚠️ never use tile.openstreetmap.org directly — pages opened from file:// send no Referer
      and OSM answers with a "403 Access blocked" image (osm.wiki/Blocked)               */
const BASEMAPS = {
  light: { label: 'Light', style: 'https://tiles.openfreemap.org/styles/positron' },
  streets: { label: 'Streets · 3D', style: 'https://tiles.openfreemap.org/styles/liberty' },   // has 3D buildings at zoom ≥ 14
  satellite: { label: 'Satellite', style: {
    version: 8,
    sources: { sat: { type: 'raster', tileSize: 256, attribution: 'Esri World Imagery',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'] } },
    layers: [{ id: 'sat', type: 'raster', source: 'sat' }],
  } },
};
const FALLBACK_STYLE = {      // used when the vector style cannot be fetched
  version: 8,
  sources: { esri: { type: 'raster', tileSize: 256, attribution: 'Esri, HERE, Garmin, © OpenStreetMap contributors',
    tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}'] } },
  layers: [{ id: 'esri', type: 'raster', source: 'esri', paint: { 'raster-saturation': -0.6 } }],
};

/* ── AI assistant ──────────────────────────────────────────────────────
   endpoint = URL of the agent API (scripts/taxi/server/app.py → POST /api/agent)
   null     = auto: use '/api/agent' when the page is served over http(s) and /api/health answers,
              otherwise the built-in offline assistant (rule-based, no data leaves the browser) */
const AI = Object.assign({ endpoint: null, health: '/api/health', timeoutMs: 45000 },
  (window.EV7_CONFIG && window.EV7_CONFIG.ai) || {});
