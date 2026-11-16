/* js/ui/filters.js — filter bar at the top of the side panel: center · status · area (Bangkok / Bangkok + vicinity) · area chips
   provides: initFilters() · renderFilterChips() · areaPreset() · activeFilters() · clearAllFilters() · syncClearAll() */

function initFilters() {
  const centers = [...new Set(D.vehicles.center)].sort();
  const count = c => D.vehicles.center.filter(x => x === c).length;
  $('#fCenter').innerHTML = `<option value="">Centers</option>` + centers.map(c => `<option value="${esc(c)}">${esc(centerName(c))} (${fmt(count(c))})</option>`).join('');
  $('#fStatus').innerHTML = `<option value="">Status</option>` + ['hired', 'vacant', 'park'].map(k => `<option value="${k}">${STATUS_LABEL[k]}</option>`).join('');
  $('#fPreset').onchange = e => {
    const p = CFG.AREA_PRESETS[e.target.value];
    S.areas = new Set(p ? p.prov.map(pc => 'p:' + PROV.findIndex(x => x.pc === pc)).filter(k => k !== 'p:-1') : []);
    refresh('filter');
    if (p) {                                                   // zoom to the chosen area
      const bb = [...S.areas].map(areaBBox).filter(Boolean);
      if (bb.length) fitPoints([[Math.min(...bb.map(b => b[0][0])), Math.min(...bb.map(b => b[0][1]))], [Math.max(...bb.map(b => b[1][0])), Math.max(...bb.map(b => b[1][1]))]], 12);
    }
  };
  $('#fCenter').onchange = e => { S.centers = new Set(e.target.value ? [e.target.value] : []); refresh('filter'); };
  $('#fStatus').onchange = e => { S.status = new Set(e.target.value ? [e.target.value] : ['hired', 'vacant', 'park']); refresh('filter'); };
}
/* the area filter equals one of the presets → show it in the dropdown instead of one chip per province */
function areaPreset() {
  for (const [k, p] of Object.entries(CFG.AREA_PRESETS)) {
    const keys = p.prov.map(pc => 'p:' + PROV.findIndex(x => x.pc === pc));
    if (keys.length === S.areas.size && keys.every(x => S.areas.has(x))) return k;
  }
  return S.areas.size ? 'custom' : '';
}
function renderFilterChips() {
  const el = $('#fArea'), pre = areaPreset();
  $('#fPreset').innerHTML = `<option value="">Areas</option>` + Object.entries(CFG.AREA_PRESETS).map(([k, p]) => `<option value="${k}" title="${p.label}">${p.short || p.label}</option>`).join('')
    + (pre === 'custom' ? `<option value="custom" disabled>${S.areas.size} selected</option>` : '');
  $('#fPreset').value = pre;
  $('#fPreset').title = pre && CFG.AREA_PRESETS[pre] ? CFG.AREA_PRESETS[pre].label : 'Area';
  $('#fPreset').classList.toggle('active', !!pre);
  el.hidden = pre !== 'custom';
  el.innerHTML = (pre === 'custom' ? [...S.areas] : []).map(k => `<span class="chip on">${esc(areaName(k))}<button type="button" data-k="${k}" aria-label="Remove ${esc(areaName(k))}">${ICON.x}</button></span>`).join('');
  el.querySelectorAll('button[data-k]').forEach(b => b.onclick = () => toggleArea(b.dataset.k));
  $('#fCenter').classList.toggle('active', S.centers.size > 0);
  $('#fStatus').classList.toggle('active', S.status.size < 3);
  syncClearAll();
}

/* everything that narrows or holds what is shown — one button puts the page back to its start: the filter bar · the panels'
   own filters (zone level · parking place and list · plate search) · the selected car (and its route window) · a period
   or History time · what the assistant highlighted · the assistant conversation. Settings stay as they are (allowed zone,
   trip length, base map, 2D/3D). */
function activeFilters() {
  return [S.centers.size, S.status.size < 3, S.areas.size, S.sev, S.sSev, S.pPlace, S.vehQ, S.highlight || EV_FOCUS.length,
    S.sel >= 0, !isLive() || S.a > 0 || S.b < D.meta.tmax, Chat.hasTalk()].filter(Boolean).length;
}
function clearAllFilters() {
  S.centers.clear(); S.status = new Set(['hired', 'vacant', 'park']); S.areas.clear();
  S.sev = ''; S.sSev = ''; S.pPlace = ''; S.vehQ = '';
  S.highlight = null; EV_FOCUS = [];
  S.others = 'dim'; S.trk = 'all'; selectVehicle(-1);
  Chat.reset();                                         // the conversation too — a fresh start everywhere
  $('#fCenter').value = ''; $('#fStatus').value = '';
  S.a = 0; S.b = D.meta.tmax;
  refresh('filter');                                    // redraws the chips, the open panel, the legend and the map
  if (!isLive() && !SIM.on) goLive();
  toast('Cleared — filters, selected car, time and chat');
}
/* the button sits in the header next to Ask and shows how many things are on — called after every map redraw (cheap) */
function syncClearAll() {
  const b = $('#clrAll'), n = activeFilters();
  if (b._n === n) return;
  b._n = n; b.hidden = !n;
  b.innerHTML = `${ICON.reset}<span>Clear all</span><b>${n}</b>`;
  b.title = 'Back to the start: clears filters, the selected car, the period / history time, map highlights and the assistant chat';
  b.setAttribute('aria-label', `Clear all (${n})`);
  b.onclick = clearAllFilters;
}
