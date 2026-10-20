/* js/map/interaction.js — tooltip และการคลิกบนแผนที่
   ใช้: ui/*
   ให้: tooltip() · onMapClick() · tooltipV2() · onClickV2()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

function tooltip(info) {
  const o = info.object; if (!o) return null;
  const t2 = tooltipV2(info); if (t2) return t2;
  if (info.layer.id === 'ev') {
    const [, , name, op, sock, cap] = o;
    return { html: `<b>${esc(name || 'สถานีชาร์จ EV')}</b>${op ? `<br>${esc(op)}` : ''}
      ${sock ? `<br><span class="tt-k">หัวชาร์จ</span> ${esc(sock)}` : ''}${cap ? ` · ${esc(cap)} ช่อง` : ''}
      <br><span class="tt-k">ที่มา OpenStreetMap — มีแค่บางส่วนของจุดชาร์จจริง</span>` };
  }
  if (info.layer.id === 'now' || info.layer.id === 'now-car') {
    const i = o.i, v = o.v, dI = DI[i];
    const st = { hired: 'มีผู้โดยสาร', vacant: 'ว่าง · กำลังวิ่ง', park: 'จอด', nosig: 'ไม่มีสัญญาณ GPS' }[o.st];
    return { html: `<b>${D.vehicles.plate[v]}</b> <span class="tt-k">${CFG.CENTER_NAMES[D.vehicles.center[v]] || D.vehicles.center[v]}</span><br>
      ${st} · ${SPD[i]} กม./ชม.<br><span class="tt-k">${dI === 65535 ? '–' : DIST[dI].th + ', ' + PROV[distProv[dI]].th}</span><br>
      <span class="tt-k">เวลา GPS</span> ${fDT(TT[i])}${o.out ? '<br><b style="color:#ff9ea2">อยู่นอกเขตที่อนุญาต</b>' : ''}` };
  }
  if (info.layer.id === 'track') {
    const i = o, dI = DI[i];
    return { html: `<b>${D.vehicles.plate[VV[i]]}</b><br>${fDT(TT[i])} · ${SPD[i]} กม./ชม. · ${FLG[i] & 1 ? 'มีผู้โดยสาร' : 'ว่าง'}<br><span class="tt-k">${dI === 65535 ? '–' : DIST[dI].th + ', ' + PROV[distProv[dI]].th}</span>` };
  }
  if (info.layer.id === 'areas') {
    const pc = o.properties.pc;
    const isP = S.level === 'prov', idx = (isP ? pcToProv : pcToDist).get(pc);
    const name = isP ? PROV[idx].th : DIST[idx].th + ' · ' + PROV[distProv[idx]].th;
    const A = AREA;
    const veh = isP ? A.vehP[idx] : A.vehD[idx], hrs = isP ? A.hrsP[idx] : A.hrsD[idx], hir = isP ? A.hirP[idx] : A.hirD[idx];
    return { html: `<b style="font-family:var(--sans)">${name}</b><br>รถ ${fmt(veh)} คัน · ${fmt(hrs)} ชม.<br><span class="tt-k">มีผู้โดยสาร</span> ${fmt(hir)} ชม. (${hrs ? pct(hir / hrs) : '–'})<br><span class="tt-k">คลิกเพื่อกรองพื้นที่นี้</span>` };
  }
  return null;
}
function onMapClick(info) {
  if (!info.object) return;
  if (onClickV2(info)) return;
  if (info.layer.id === 'now' || info.layer.id === 'now-car') { selectVehicle(info.object.v); return; }
  if (info.layer.id === 'areas') {
    const pc = info.object.properties.pc;
    const key = (S.level === 'prov' ? 'p:' + pcToProv.get(pc) : 'd:' + pcToDist.get(pc));
    toggleArea(key);
  }
}
function tooltipV2(info) {
  const o = info.object, id = info.layer.id;
  if (id === 'night') {
    const g = Geo.peek(o.lat, o.lon);
    return { html: `<b>${D.vehicles.plate[o.v]}</b> <span class="tt-k">ค้างคืน</span><br>${fDT(o.s)} – ${fDT(o.e)}<br>
      <span class="tt-k">${DIST[o.d].th}, ${PROV[distProv[o.d]].th}</span>${g ? '<br>' + g.short : ''}<br><span class="tt-k">คลิกดูที่อยู่และภาพถนน</span>` };
  }
  if (id === 'depot') {
    const g = Geo.peek(o.lat, o.lon);
    return { html: `<b style="font-family:var(--sans)">ลานจอด · ${o.n} คันค้างคืน</b><br><span class="tt-k">${DIST[o.d].th}, ${PROV[distProv[o.d]].th}</span>${g ? '<br>' + g.short : ''}` };
  }
  if (id === 'vstays') {
    return { html: `<b>จอด ${fDur(o.dur)}</b>${o.night >= 3600 ? ' 🌙' : ''}<br>${fDT(o.s)} – ${fDT(o.e)}<br><span class="tt-k">${DIST[o.d].th}, ${PROV[distProv[o.d]].th}</span>` };
  }
  return null;
}
function onClickV2(info) {
  const o = info.object, id = info.layer.id;
  if (id === 'night') { selectVehicle(o.v, false); switchTab('stay'); showPlace(o.lat, o.lon, D.vehicles.plate[o.v], `ค้างคืน ${fDT(o.s)}`); return true; }
  if (id === 'depot') { showPlace(o.lat, o.lon, `ลานจอด · ${o.n} คันค้างคืน`, `${DIST[o.d].th}, ${PROV[distProv[o.d]].th}`); return true; }
  if (id === 'vstays') { setT(o.s); showPlace(o.lat, o.lon, D.vehicles.plate[o.v], `จอด ${fDur(o.dur)} · ${fDT(o.s)}`); return true; }
  return false;
}
