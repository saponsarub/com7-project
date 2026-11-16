/* js/ui/search.js — one search box: plate / VIN → vehicle · province / district → filter + zoom · landmark → zoom
   anything else → "Ask the assistant"
   provides: initSearch() */

function initSearch() {
  const q = $('#q'), dd = $('#qdd');
  const V = D.vehicles;
  const idx = V.plate.map((p, v) => [p.replace(/[\s-]/g, '').toLowerCase(), V.vin[v].toLowerCase(), v]);
  let items = [], hi = 0;
  const draw = () => {
    dd.innerHTML = items.map((x, i) => `<div class="opt${i === hi ? ' on' : ''}" id="qo${i}" data-i="${i}" role="option" aria-selected="${i === hi}">
      <span class="ic">${x.icon}</span><span>${esc(x.label)}</span><small>${esc(x.sub)}</small></div>`).join('');
    dd.hidden = !items.length;
    q.setAttribute('aria-expanded', String(items.length > 0));
    if (items.length) q.setAttribute('aria-activedescendant', 'qo' + hi);
    dd.querySelectorAll('.opt').forEach(d => d.onmousedown = e => { e.preventDefault(); pick(items[+d.dataset.i]); });
  };
  const pick = x => {
    if (!x) return;
    dd.hidden = true; q.value = ''; q.blur();
    if (x.kind === 'veh') selectVehicle(x.v, true, 'hide');
    else if (x.kind === 'area') { if (!S.areas.has(x.key)) toggleArea(x.key); UI_ACT.fitArea(x.key); }
    else if (x.kind === 'poi') map.flyTo({ center: [x.p.lon, x.p.lat], zoom: 14, duration: 800 });
    else if (x.kind === 'ask') Chat.open(x.text);
  };
  q.oninput = () => {
    const raw = q.value.trim(), s = raw.toLowerCase(), sk = s.replace(/[\s-]/g, '');
    items = []; hi = 0;
    if (!s) return draw();
    if (sk.length >= 2) for (const [p, vin, v] of idx) {
      if (p.includes(sk) || vin.includes(sk)) { items.push({ kind: 'veh', v, icon: ICON.vehicles, label: V.plate[v], sub: centerName(V.center[v]) }); if (items.length >= 6) break; }
    }
    const has = n => n && n.toLowerCase().includes(s);
    PROV.forEach((p, i) => { if (has(p.th) || has(p.en)) items.push({ kind: 'area', key: 'p:' + i, icon: ICON.areas, label: provName(i), sub: 'Province' + (p.en ? ' · ' + p.th : '') }); });
    let k = 0;
    DIST.forEach((d, i) => { if (k < 6 && (has(d.th) || has(d.en))) { k++; items.push({ kind: 'area', key: 'd:' + i, icon: ICON.areas, label: distName(i), sub: 'District · ' + provName(d.p) }); } });
    LANDMARKS.forEach(l => { if (l.names.some(has)) items.push({ kind: 'poi', p: l, icon: ICON.pin, label: l.en, sub: 'Place' }); });
    items = items.slice(0, 12);
    if (raw.length >= 3) items.push({ kind: 'ask', text: raw, icon: ICON.spark, label: `Ask: “${raw}”`, sub: 'Assistant' });
    draw();
  };
  q.onkeydown = e => {
    if (e.key === 'ArrowDown') { hi = Math.min(items.length - 1, hi + 1); draw(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { hi = Math.max(0, hi - 1); draw(); e.preventDefault(); }
    else if (e.key === 'Enter') { e.preventDefault(); pick(items[hi]); }
    else if (e.key === 'Escape') { dd.hidden = true; q.setAttribute('aria-expanded', 'false'); }
  };
  q.onblur = () => setTimeout(() => { dd.hidden = true; q.setAttribute('aria-expanded', 'false'); }, 120);
  // "/" focuses the search box from anywhere
  document.addEventListener('keydown', e => {
    if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) { e.preventDefault(); q.focus(); }
  });
}
