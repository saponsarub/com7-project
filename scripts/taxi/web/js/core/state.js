/* js/core/state.js — page state (S) + the point columns every module shares
   provides: S · D · N · NV · PROV · DIST · distProv · t0ms · POS · TT · SPD · FLG · DI · VV · DUR · MASK · maskVer · map · deckOverlay */

const S = {
  T: 0, a: 0, b: 0, playing: false, speed: 600,       // timeline: cursor, selected range, playback (sec of data per sec)
  panel: 'overview',                                  // left panel shown
  centers: new Set(), status: new Set(['hired', 'vacant', 'park']),
  areas: new Set(),                                   // area filter keys 'p:<idx>' / 'd:<idx>'
  sel: -1, trk: 'all',                                // selected vehicle · its route: 'all' | 'live' | last N seconds
  zone: 'metro', minDur: 10, exDepot: false, sev: '', sortK: 'hrs', sortDir: -1,
  vehSort: 'km', sSev: '',
  pt: 'now', trail: 0, choro: false, level: 'prov', metric: 'veh', ev: false,
  basemap: 'light',
  highlight: null,                                    // Set of vehicle idx highlighted by the assistant
  others: 'dim',                                      // other vehicles while one is selected: 'dim' (faded) | 'hide'
  offline: true,                                      // live mode: show offline vehicles at their last known position
  cutRule: 'offroad',                                 // power-cut rule: 'basic' (parked/engine off ≥ 10 min) · 'offroad' (+ not on a road)
  awayH: 5,                                           // Outside panel: outside Bangkok + vicinity longer than this (h) before the cursor
  pPlace: '',                                       // Parking panel: show one place type ('charger' · 'depot' · 'home' · 'street')
  vehQ: '',                                           // plate search in the Vehicles panel
  follow: true,                                       // playback: the map keeps the selected car in view (off after you drag the map)
  trkFrom: null,                                      // replay start: the route is drawn from here to the cursor
  live: true,                                         // the cursor follows the live clock (ui/liveclock.js) · false = History
};
/* live = the cursor runs with the live clock, just behind the newest data (moving the cursor yourself = History) */
const isLive = () => !!D && S.live;
let D, N, NV, PROV, DIST, distProv, t0ms;
let POS, TT, SPD, FLG, DI, VV, DUR;                   // point columns
let MASK, maskVer = 0;                                // passes the non-time filters
let EXC = [], EXC_BY_V = new Map(), VSTAT = null;
let deckOverlay, map;
