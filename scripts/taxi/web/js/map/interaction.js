/* js/map/interaction.js — map tooltips and clicks
   uses: ui/*
   provides: tooltip() · onMapClick() */

const tt = (title, ...lines) => ({ html: `<b>${title}</b>${lines.filter(Boolean).map(l => '<br>' + l).join('')}` });
const ttk = s => `<span class="tt-k">${s}</span>`;
function chargerHtml(o) {
  const [, , name, op, sock, cap] = o;
  return tt(esc(name || 'EV charger'), op && esc(op),
    (sock ? `${ttk('Sockets')} ${esc(sock)}` : '') + (cap ? ` · ${esc(cap)} bays` : ''),
    ttk('Source: OpenStreetMap — not every real charger is mapped'));
}

function tooltip(info) {
  const o = info.object; if (!o) return null;
  const id = info.layer.id;
  if (id === 'ev' || id === 'ev-focus') return chargerHtml(o);
  if (id === 'now' || id === 'now-puck' || id === 'car3d') {
    const i = o.i, v = o.v;
    const lm = o.st === 'park' ? lastMovedAt(v, i) : -1;
    return tt(`${esc(plateOf(v))} ${ttk(esc(centerName(D.vehicles.center[v])))}`,
      `${STATUS_LABEL[o.st]} · ${SPD[i]} km/h`, ttk(esc(whereOf(DI[i]))),
      `${ttk('GPS time')} ${fDT(TT[i])}`, lm >= 0 && `${ttk('Last moved')} ${fDT(lm)} (${fDur(S.T - lm)} ago)`,
      o.out && '<b class="tt-out">Outside the allowed zone</b>', ttk(S.sel === v ? 'Selected' : 'Click to focus on this vehicle'));
  }
  if (id === 'offline') {
    const i = o.i, v = o.v, lm = lastMovedAt(v, i);
    return tt(`${esc(plateOf(v))} ${ttk('offline')}`, `${ttk('Last seen')} ${fDT(TT[i])} (${fDur(S.T - TT[i])} ago)`,
      ttk(esc(whereOf(DI[i]))), lm >= 0 && `${ttk('Last moved')} ${fDT(lm)}`, ttk('Click to focus on this vehicle'));
  }
  if (id === 'track') {
    const i = o;
    return tt(esc(plateOf(VV[i])), `${fDT(TT[i])} · ${SPD[i]} km/h · ${FLG[i] & 1 ? 'on trip' : 'available'}`, ttk(esc(whereOf(DI[i]))));
  }
  if (id === 'areas') {
    const isP = S.level === 'prov', idx = (isP ? pcToProv : pcToDist).get(o.properties.pc);
    if (idx == null) return null;
    const A = AREA;
    const veh = isP ? A.vehP[idx] : A.vehD[idx], hrs = isP ? A.hrsP[idx] : A.hrsD[idx], hir = isP ? A.hirP[idx] : A.hirD[idx];
    return tt(esc(areaName((isP ? 'p:' : 'd:') + idx)), `${fmt(veh)} vehicles · ${fmt(hrs)} h online`,
      `${ttk('On trip')} ${fmt(hir)} h (${hrs ? pct(hir / hrs) : '–'})`, ttk('Click to filter to this area'));
  }
  if (id === 'night') {
    const g = Geo.peek(o.lat, o.lon);
    return tt(`${esc(plateOf(o.v))} ${ttk('overnight')}`, `${fDT(o.s)} – ${fDT(o.e)}`, ttk(esc(whereOf(o.d))), g && esc(g.short), ttk('Click for address'));
  }
  if (id === 'depot') {
    const g = Geo.peek(o.lat, o.lon);
    return tt(`Depot · ${o.n} vehicles overnight`, ttk(esc(whereOf(o.d))), g && esc(g.short));
  }
  if (id === 'vstays') {
    return tt(`Stopped ${fDur(o.dur)}${isNight(o) ? ' · overnight' : ''}`, `${fDT(o.s)} – ${fDT(o.e)}`, ttk(esc(whereOf(o.d))));
  }
  return null;
}

function onMapClick(info) {
  const o = info.object; if (!o) return;
  const id = info.layer.id;
  // a car clicked on the map: keep the view, fade the other vehicles
  if (id === 'now' || id === 'now-puck' || id === 'car3d' || id === 'offline') { S.others = 'dim'; selectVehicle(o.v, false); }
  else if (id === 'areas') {
    const pc = o.properties.pc;
    toggleArea(S.level === 'prov' ? 'p:' + pcToProv.get(pc) : 'd:' + pcToDist.get(pc));
  } else if (id === 'ev' || id === 'ev-focus') showPlace(o[0], o[1], o[2] || 'EV charger', o[3] || 'EV charger');
  else if (id === 'night') { selectVehicle(o.v, false); showPlace(o.lat, o.lon, plateOf(o.v), `Overnight ${fDT(o.s)}`); }
  else if (id === 'depot') showPlace(o.lat, o.lon, `Depot · ${o.n} vehicles overnight`, whereOf(o.d));
  else if (id === 'vstays') { setT(o.s); showPlace(o.lat, o.lon, plateOf(o.v), `Stopped ${fDur(o.dur)} · ${fDT(o.s)}`); }
}
