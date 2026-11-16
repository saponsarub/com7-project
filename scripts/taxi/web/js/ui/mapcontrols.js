/* js/ui/mapcontrols.js — map buttons (top-right) · "Map" popover (base map · vehicles · trail · chargers · area colours · 2D/3D) · legend
   provides: initMapTools() · syncMapTools() · closeLayers() · renderLegend() */

function initMapTools() {
  $('#btnLayers').innerHTML = `${ICON.layers}<span>Map</span>`;
  $('#btnHome').innerHTML = ICON.home;
  $('#btnTH').innerHTML = ICON.globe;
  $('#layersPop').innerHTML = `
    <div class="field"><span class="lbl">Base map</span>${segHtml('bmSeg', Object.entries(BASEMAPS).map(([k, b]) => [k, b.label]), S.basemap, 'Base map')}</div>
    <div class="field"><span class="lbl">Vehicles</span>${segHtml('ptSeg', [['now', 'At cursor time'], ['range', 'All points'], ['off', 'Hide']], S.pt, 'Vehicles')}</div>
    <label class="field inline" id="trailRow">Trail behind each car
      <select id="trail">${[[0, 'Off'], [10, '10 min'], [30, '30 min'], [60, '1 hour']].map(([v, t]) => `<option value="${v}"${v === S.trail ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
    <label class="switch"><input type="checkbox" id="offSw"><span></span> Offline vehicles <small class="muted">last known position · live only</small></label>
    <label class="switch" id="evRow"><input type="checkbox" id="evSw"><span></span> EV chargers <small class="muted">${fmt(EV.length)} from OpenStreetMap</small></label>
    <label class="switch"><input type="checkbox" id="choroSw2"><span></span> Colour areas</label>
    <div class="field"><span class="lbl">Live test</span>
      <div class="lt-row"><select id="ltSpeed" aria-label="Speed"><option value="1">Real time</option><option value="10">×10</option><option value="60">×60</option></select>
        <button type="button" class="btn sm" id="ltGo">Replay last hour as live</button></div>
      <span class="hint">Hides the last hour, then feeds it in as if live and scores the predictions (results in Overview).</span></div>
    <div class="field"><span class="lbl">View</span>${segHtml('viewSeg', [['2d', '2D'], ['3d', '3D']], '2d', 'View')}</div>
    <p class="hint">3D: right-drag or Ctrl+drag to tilt and turn. From zoom ${CAR3D_ZOOM} the cars are drawn in 3D, facing the way they drive.</p>`;
  if (!EV.length) $('#evRow').hidden = true;
  $('#btnLayers').onclick = e => { e.stopPropagation(); $('#layersPop').hidden ? openLayers() : closeLayers(); };
  document.addEventListener('pointerdown', e => { if (!$('#layersPop').hidden && !e.target.closest('#layersPop, #btnLayers')) closeLayers(); });
  $('#btnHome').onclick = flyHome;
  $('#btnTH').onclick = fitThailand;
  seg($('#bmSeg'), v => { setBasemap(v); writeHash(); });
  seg($('#ptSeg'), v => { S.pt = v; syncMapTools(); render(); });
  $('#trail').onchange = e => { S.trail = +e.target.value; render(); };
  $('#offSw').onchange = e => { S.offline = e.target.checked; renderLegend(); render(); };
  $('#evSw').onchange = e => { S.ev = e.target.checked; if (!S.ev) EV_FOCUS = []; renderLegend(); render(); };
  $('#choroSw2').onchange = e => { S.choro = e.target.checked; if (S.panel === 'areas') renderPanel('areas'); renderLegend(); render(); };
  seg($('#viewSeg'), v => set3D(v === '3d'));
  $('#ltGo').onclick = () => { closeLayers(); startLiveTest(+$('#ltSpeed').value); openPanel('overview'); };
  syncMapTools();
}
function openLayers() { syncMapTools(); $('#layersPop').hidden = false; $('#btnLayers').setAttribute('aria-expanded', 'true'); }
function closeLayers() { $('#layersPop').hidden = true; $('#btnLayers').setAttribute('aria-expanded', 'false'); }
function syncMapTools() {
  if (!$('#bmSeg')) return;
  setSeg($('#bmSeg'), S.basemap);
  setSeg($('#ptSeg'), S.pt);
  setSeg($('#viewSeg'), is3D() ? '3d' : '2d');
  $('#trailRow').hidden = S.pt !== 'now';
  $('#evSw').checked = S.ev;
  $('#offSw').checked = S.offline;
  $('#choroSw2').checked = S.choro;
  const c = $('#choroSw'); if (c) c.checked = S.choro;
}
function renderLegend() {
  const ch = S.choro ? `<div class="lg-ramp"><span class="lbl">${METRIC_LABEL[S.metric]} per ${S.level === 'prov' ? 'province' : 'district'}</span>
    <div class="ramp">${RAMP.map(c => `<i style="background:${c}"></i>`).join('')}</div>
    <div class="rampl num"><span>1</span><span>${fmt(choroScale.max)}</span></div></div>` : '';
  $('#legend').innerHTML = `
    <div class="row"><i class="dot" style="background:var(--hired)"></i>${STATUS_LABEL.hired}</div>
    <div class="row"><i class="dot" style="background:var(--green)"></i>${STATUS_LABEL.vacant}</div>
    <div class="row"><i class="dot" style="background:var(--slate)"></i>${STATUS_LABEL.park}</div>
    <div class="row"><i class="arrow"></i>Moving · arrow = direction</div>
    <div class="row"><i class="dot ring"></i>Outside the zone</div>
    ${isLive() && S.offline ? '<div class="row"><i class="dot off"></i>Offline · last known position</div>' : ''}
    ${S.sel >= 0 ? (isLive() ? `<div class="row"><i class="trk dashed"></i>Route · last ${LIVE_TRACK_SEC / 3600} h</div>`
      : '<div class="row"><i class="trk"></i>Route driven (to the cursor)</div><div class="row"><i class="trk dashed ahead"></i>Route still ahead</div>') : ''}
    ${S.sel >= 0 ? '<div class="row"><i class="dash"></i>Planned route (along roads)</div><div class="row"><i class="dot tA">A</i>Trip start</div><div class="row"><i class="dot tB">B</i>Next stop (data)</div><div class="row"><i class="dot tQ">?</i>Likely destination</div>' : ''}
    <div class="row"><i class="line"></i>Allowed zone</div>
    ${S.ev || EV_FOCUS.length ? '<div class="row"><i class="dot" style="background:var(--violet)"></i>EV charger</div>' : ''}
    ${S.highlight && S.highlight.size ? '<div class="row"><i class="dot hl"></i>Picked by the assistant</div>' : ''}`;
}
