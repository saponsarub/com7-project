/* js/ui/shell.js — left navigation rail · side panel switching · collapse
   Only the open panel is drawn; the others are marked dirty and drawn when opened (keeps every change fast).
   uses: ui/panels-*.js
   provides: PANELS · openPanel() · renderPanel() · markDirty() · initShell() · toggleSide() */

const PANELS = {
  overview: { label: 'Overview', title: 'Fleet overview', icon: 'overview', render: () => renderOverview() },
  vehicles: { label: 'Vehicles', title: 'Vehicles', icon: 'vehicles', render: () => renderVehicles() },
  zone:     { label: 'Zone', title: 'Out of zone', icon: 'zone', render: () => renderZone() },
  // the Parking tab (ui/parking.js) is off the rail since 2026-11-10 — put this line back to restore it:
  // parking:  { label: 'Parking', title: 'Parking', icon: 'parking', render: () => renderParking() },
  away:     { label: 'Outside', title: 'Outside Bangkok + vicinity', icon: 'away', render: () => renderAway() },
  areas:    { label: 'Areas', title: 'Areas', icon: 'areas', render: () => renderAreas() },
};
const DIRTY = new Set(Object.keys(PANELS));
function markDirty() { Object.keys(PANELS).forEach(k => DIRTY.add(k)); }
function renderPanel(name = S.panel) {
  PANELS[name].render();
  DIRTY.delete(name);
}
function openPanel(name, quiet = false) {
  if (!PANELS[name]) return;
  const changed = S.panel !== name;
  S.panel = name;
  if (!quiet) document.body.classList.remove('side-collapsed');   // quiet = start-up: keep a folded panel folded (phones)
  $$('.rail [data-panel]').forEach(b => b.setAttribute('aria-current', b.dataset.panel === name ? 'page' : 'false'));
  $$('.panel').forEach(p => p.hidden = p.id !== 'p-' + name);
  $('#panelTitle').textContent = PANELS[name].title;
  if (DIRTY.has(name) || changed) renderPanel(name);
  render();                                 // some map layers belong to a panel (overnight spots, stops of a car)
  writeHash();
}
function toggleSide(force) {
  const on = force != null ? force : !document.body.classList.contains('side-collapsed');
  document.body.classList.toggle('side-collapsed', on);
  $('#railCollapse').innerHTML = on ? ICON.expand : ICON.collapse;
  $('#railCollapse').setAttribute('aria-label', on ? 'Show panel' : 'Hide panel');
  store.set('ev7.side', on ? 'collapsed' : null);
}
function initShell() {
  $('#rail').innerHTML = Object.entries(PANELS).map(([k, p]) =>
    `<button type="button" data-panel="${k}" aria-current="false" title="${p.title}">${ICON[p.icon]}<span>${p.label}</span>${k === 'zone' ? '<b class="rail-badge" id="zoneBadge"></b>' : k === 'away' ? '<b class="rail-badge" id="awayBadge"></b>' : ''}</button>`).join('')
    + `<span class="rail-gap"></span><button type="button" id="railCollapse" class="rail-mini" aria-label="Hide panel">${ICON.collapse}</button>`;
  $$('.rail [data-panel]').forEach(b => b.onclick = () => {
    // clicking the open section again folds the panel away (more map)
    if (S.panel === b.dataset.panel && !document.body.classList.contains('side-collapsed')) toggleSide(true);
    else openPanel(b.dataset.panel);
  });
  $('#railCollapse').onclick = () => toggleSide();
  if (store.get('ev7.side') === 'collapsed' && window.innerWidth > 800) toggleSide(true);
  if (window.innerWidth <= 800) toggleSide(true);
}
