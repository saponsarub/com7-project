/* js/ui/zone.js — Out of zone panel: settings · summary · vehicle table · CSV · top destinations
   provides: renderZone() · VROWS */

let VROWS = [];
const ZONE_COLS = [['plate', 'Vehicle'], ['sev', 'Level'], ['n', 'Trips'], ['hrs', 'Hrs'], ['km', 'Km']];
const SEV_SHORT = { far: 'Upcountry', near: 'Vicinity', all: 'Always out' };     // fits the narrow table (full words in the tooltip)
function renderZone() {
  const el = $('#p-zone');
  const rows = violRows();
  const trips = EXC.length, hrs = EXC.reduce((s, x) => s + x.dur, 0) / 3600;
  const far = rows.filter(r => r.sev === 'far').length, all = rows.filter(r => r.sev === 'all').length;
  let list = S.sev ? rows.filter(r => r.sev === S.sev) : rows;
  const k = S.sortK, dir = S.sortDir;
  list.sort((a, b) => {
    const x = k === 'sev' ? a.sevRank : a[k], y = k === 'sev' ? b.sevRank : b[k];
    return (x > y ? 1 : x < y ? -1 : 0) * dir || b.hrs - a.hrs;
  });
  VROWS = list;
  const cnt = new Map();
  for (const xs of EXC_BY_V.values()) { const ps = new Set(); xs.forEach(x => x.provs.forEach((_, p) => ps.add(p))); ps.forEach(p => cnt.set(p, (cnt.get(p) || 0) + 1)); }
  el.innerHTML = `
    <section class="sec">
      <div class="form">
        <label>Allowed zone <select id="zoneSel">${Object.entries(CFG.ZONES).map(([z, o]) => `<option value="${z}"${z === S.zone ? ' selected' : ''}>${o.label}</option>`).join('')}</select></label>
        <label>Count trips longer than <select id="minDur">${[[0, 'any length'], [10, '10 min'], [30, '30 min'], [60, '1 hour']].map(([v, t]) => `<option value="${v}"${v === S.minDur ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
        <label class="check"><input type="checkbox" id="exDepot"${S.exDepot ? ' checked' : ''}${depotsReady() ? '' : ' disabled'}>
          Ignore time at depots${depotsReady() ? '' : ' <span class="muted">(finding depots…)</span>'}</label>
      </div>
    </section>
    <section class="sec">
      <div class="stats">
        ${stat('Vehicles', fmt(rows.length), `upcountry ${fmt(far)} · always outside ${fmt(all)} · vicinity ${fmt(rows.length - far - all)}`, 'alert')}
        ${stat('Trips', fmt(trips), `${fmt(hrs)} h outside in total`)}
      </div>
    </section>
    <section class="sec">
      <div class="sec-h">${segHtml('sevSeg', [['', 'All'], ['far', SEV_LABEL.far], ['all', SEV_LABEL.all], ['near', SEV_LABEL.near]], S.sev, 'Level')}
        <button type="button" class="btn sm" id="csv" title="One row per trip">${ICON.download} CSV</button></div>
      <div class="tablewrap"><table class="tbl" id="vTable">
        <thead><tr>${ZONE_COLS.map(([c, t]) => `<th${c === 'plate' || c === 'sev' ? '' : ' class="r"'} aria-sort="${c === S.sortK ? (S.sortDir < 0 ? 'descending' : 'ascending') : 'none'}"><button type="button" data-k="${c}">${t}</button></th>`).join('')}</tr></thead>
        <tbody>${list.slice(0, 300).map(r => `<tr data-v="${r.v}" class="${r.v === S.sel ? 'on' : ''}" tabindex="0">
          <td><span class="plate">${esc(r.plate)}</span><small class="muted">${r.provs.slice(0, 2).map(esc).join(' · ')}${r.provs.length > 2 ? ` +${r.provs.length - 2}` : ''}</small></td>
          <td><span class="sev ${r.sev}" title="${SEV_LABEL[r.sev]}">${SEV_SHORT[r.sev]}</span></td>
          <td class="r num">${r.n}</td><td class="r num">${fmt1(r.hrs)}</td><td class="r num">${fmt(r.km)}</td></tr>`).join('')
          || `<tr><td colspan="5">${empty('No vehicle left the zone with these settings.')}</td></tr>`}</tbody>
      </table></div>
      <p class="hint">${list.length > 300 ? `Showing 300 of ${fmt(list.length)} — download the CSV for all. ` : ''}Hrs = hours outside · Km = farthest straight-line distance from central Bangkok.</p>
    </section>
    <section class="sec">
      <div class="sec-h"><h3>Top destinations</h3><span class="muted">vehicles · click to filter</span></div>
      <div class="bars" id="vProv"></div>
    </section>`;
  barsInto($('#vProv'), [...cnt.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6)
    .map(([p, n]) => ({ key: 'p:' + p, name: provName(p), val: n, txt: fmt(n) })), { red: true });
  $('#zoneSel').onchange = e => { S.zone = e.target.value; buildZoneGeo(); refresh('range'); writeHash(); };
  $('#minDur').onchange = e => { S.minDur = +e.target.value; refresh('range'); };
  $('#exDepot').onchange = e => { S.exDepot = e.target.checked; refresh('range'); };
  seg($('#sevSeg'), v => { S.sev = v; renderZone(); });
  $('#csv').onclick = downloadCSV;
  $$('#vTable th button').forEach(b => b.onclick = () => {
    const c = b.dataset.k; if (S.sortK === c) S.sortDir *= -1; else { S.sortK = c; S.sortDir = c === 'plate' ? 1 : -1; }
    renderZone();
  });
  $$('#vTable tbody tr[data-v]').forEach(tr => {
    tr.onclick = () => selectVehicle(+tr.dataset.v, true, 'hide');
    tr.onkeydown = e => { if (e.key === 'Enter') selectVehicle(+tr.dataset.v, true, 'hide'); };
  });
}
