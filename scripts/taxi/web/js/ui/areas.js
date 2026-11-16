/* js/ui/areas.js — Areas panel: provinces / districts ranked by vehicles or hours · colour the map
   provides: renderAreas() */

const METRIC_LABEL = { veh: 'Vehicles', hrs: 'Hours online', hired: 'Hours on trip' };
function renderAreas() {
  const el = $('#p-areas');
  const isP = S.level === 'prov', n = isP ? PROV.length : DIST.length;
  const items = [];
  for (let i = 0; i < n; i++) {
    const val = areaVal(S.level, i); if (!val) continue;
    items.push({ key: (isP ? 'p:' : 'd:') + i, name: isP ? provName(i) : distName(i), sub: isP ? '' : provName(distProv[i]), val,
      txt: S.metric === 'veh' ? fmt(val) : fmt(val) + ' h' });
  }
  items.sort((a, b) => b.val - a.val);
  el.innerHTML = `
    <section class="sec">
      <label class="switch"><input type="checkbox" id="choroSw"${S.choro ? ' checked' : ''}><span></span> Colour the map by area</label>
      <div class="form row">
        <div class="field"><span class="lbl">Level</span>${segHtml('lvSeg', [['prov', 'Province'], ['dist', 'District']], S.level, 'Level')}</div>
        <div class="field"><span class="lbl">Measure</span>${segHtml('mtSeg', Object.entries(METRIC_LABEL), S.metric, 'Measure')}</div>
      </div>
    </section>
    <section class="sec">
      <div class="sec-h"><h3>${fmt(items.length)} ${isP ? 'provinces' : 'districts'}</h3><span class="muted">${METRIC_LABEL[S.metric].toLowerCase()} · click to filter</span></div>
      <div class="bars" id="areaList"></div>
      ${items.length > 60 ? '<p class="hint">Top 60 shown.</p>' : ''}
    </section>`;
  barsInto($('#areaList'), items.slice(0, 60));
  $('#choroSw').onchange = e => { S.choro = e.target.checked; syncMapTools(); renderLegend(); render(); };
  const re = () => { updateChoroScale(); layerVer++; renderAreas(); renderLegend(); render(); };
  seg($('#lvSeg'), v => { S.level = v; re(); });
  seg($('#mtSeg'), v => { S.metric = v; re(); });
}
