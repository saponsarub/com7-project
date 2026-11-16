/* js/ui/widgets.js — small pieces shared by the panels: bar lists · stat tiles · segmented controls · empty states
   provides: barsInto() · stat() · segHtml() · empty() */

/* clickable horizontal bars — click = filter to that area */
function barsInto(el, items, opt = {}) {
  const mx = Math.max(1, ...items.map(x => x.val));
  el.innerHTML = items.map(x => `<button type="button" class="bar${opt.red ? ' red' : ''}${S.areas.has(x.key) ? ' on' : ''}" data-key="${x.key}" title="Filter to ${esc(x.name)}">
      <i style="width:${(x.val / mx * 100).toFixed(1)}%"></i><span class="n">${esc(x.name)}${x.sub ? `<small>${esc(x.sub)}</small>` : ''}</span><span class="c num">${x.txt}</span></button>`).join('')
    || empty(opt.empty || 'Nothing in this period.');
  el.querySelectorAll('.bar').forEach(b => b.onclick = () => toggleArea(b.dataset.key));
}
function stat(label, value, sub, cls = '') {
  return `<div class="stat ${cls}"><span class="k">${label}</span><span class="v num">${value}</span>${sub ? `<span class="s">${sub}</span>` : ''}</div>`;
}
function segHtml(id, opts, cur, label) {
  return `<div class="seg" id="${id}" role="group" aria-label="${label}">${opts.map(([v, t]) => `<button type="button" data-v="${v}" aria-pressed="${String(v) === String(cur)}">${t}</button>`).join('')}</div>`;
}
const empty = msg => `<div class="empty">${msg}</div>`;
