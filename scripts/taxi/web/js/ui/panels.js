/* js/ui/panels.js — แผงด้านซ้าย — ภาพรวม · นอกเขต · พื้นที่ · รถ · จุดจอด
   ใช้: analysis/*
   ให้: renderOverview() · renderViolations() · renderAreas() · renderVehCard() · renderStays() · …
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ══════════════════════════════════════════════════════════════════════
   แผง
   ══════════════════════════════════════════════════════════════════════ */
function renderOverview() {
  $('#ovRange').textContent = `${fDT(S.a)} – ${fDT(S.b)}`;
  const tot = D.vehicles.vin.filter((_, v) => vehPass(v)).length;
  $('#ovActive').textContent = fmt(AREA.active);
  $('#ovActiveS').textContent = `จาก ${fmt(tot)} คันในระบบ`;
  $('#ovUtil').textContent = pct(AREA.util);
  const vc = EXC_BY_V.size;
  $('#ovViol').textContent = fmt(vc);
  $('#ovViolS').textContent = `${pct(vc / Math.max(1, AREA.active))} ของรถที่มีสัญญาณ · ${$('#zone').selectedOptions[0].text}`;
  $('#ovOff').textContent = fmt(tot - AREA.active);
  const arr = PROV.map((p, i) => [i, AREA.hrsP[i]]).filter(x => x[1] > 0).sort((a, b) => b[1] - a[1]).slice(0, 10);
  barsInto($('#ovProv'), arr.map(([i, h]) => ({ key: 'p:' + i, name: PROV[i].th, val: h, txt: fmt(h) })));
  const m = D.meta, c = m.clean;
  $('#dq').innerHTML = `ดึงจาก <b>${m.source}</b> รอบ ${m.pulled_from} – ${m.pulled_to}<br>
    แถวดิบ <b class="num">${fmt(c.raw_rows)}</b> → จุดใช้งาน <b class="num">${fmt(c.clean_points)}</b><br>
    ตัดจุดซ้ำ (API ส่งจุดเดิมซ้ำทุกรอบ) <span class="num">${fmt(c.repeated_rows)}</span> ·
    จุดค้างเก่า <span class="num">${fmt(c.stale_points)}</span> · เวลาเครื่องผิด (อนาคต) <span class="num">${fmt(c.future_clock_rows)}</span><br>
    จุดไม่มีสัญญาณ GPS (V) <span class="num">${fmt(c.signal_v_points)}</span> — แสดงได้แต่<b>ไม่นับ</b>ในการวิเคราะห์นอกเขต<br>
    คีย์รถใช้ <b>VIN</b> เพราะ car_id ซ้ำกันข้ามศูนย์ · ทะเบียนซ้ำ ${D.vehicles.plate.filter(p => p.includes(' · ')).length} คันแสดงท้าย VIN 5 ตัว`;
}
function barsInto(el, items, red) {
  const mx = Math.max(1, ...items.map(x => x.val));
  el.innerHTML = items.map(x => `<div class="bar${red ? ' red' : ''}${S.areas.has(x.key) ? ' on' : ''}" data-key="${x.key}" title="คลิกเพื่อกรอง">
      <i style="width:${(x.val / mx * 100).toFixed(1)}%"></i><span class="n">${x.name}${x.sub ? `<small>${x.sub}</small>` : ''}</span><span class="c">${x.txt}</span></div>`).join('')
    || '<div class="muted">ไม่มีข้อมูล</div>';
  el.querySelectorAll('.bar').forEach(b => b.onclick = () => toggleArea(b.dataset.key));
}
function renderViolations() {
  const rows = violRows();
  const trips = EXC.length, hrs = EXC.reduce((s, x) => s + x.dur, 0) / 3600;
  $('#violBadge').textContent = fmt(rows.length);
  $('#vCars').textContent = fmt(rows.length);
  const far = rows.filter(r => r.sev === 'far').length, all = rows.filter(r => r.sev === 'all').length;
  $('#vCarsS').textContent = `ต่างจังหวัด ${fmt(far)} · อยู่นอกตลอด ${fmt(all)} · ปริมณฑล ${fmt(rows.length - far - all)}`;
  $('#vTrips').textContent = fmt(trips);
  $('#vHours').textContent = `ครั้ง · รวม ${fmt(hrs)} ชม.`;
  // จังหวัด: จำนวนรถ
  const cnt = new Map();
  for (const [v, xs] of EXC_BY_V) { const ps = new Set(); xs.forEach(x => x.provs.forEach((_, p) => ps.add(p))); ps.forEach(p => cnt.set(p, (cnt.get(p) || 0) + 1)); }
  barsInto($('#vProv'), [...cnt.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12)
    .map(([p, n]) => ({ key: 'p:' + p, name: PROV[p].th, val: n, txt: fmt(n) })), true);
  // ตาราง
  let list = S.sev ? rows.filter(r => r.sev === S.sev) : rows;
  const k = S.sortK, dir = S.sortDir;
  list.sort((a, b) => {
    const x = k === 'sev' ? a.sevRank : a[k], y = k === 'sev' ? b.sevRank : b[k];
    return (x > y ? 1 : x < y ? -1 : 0) * dir || b.hrs - a.hrs;
  });
  VROWS = list;
  const show = list.slice(0, 300);
  const lbl = { far: 'ต่างจังหวัด', near: 'ปริมณฑล', all: 'อยู่นอกตลอด' };
  $('#vTable tbody').innerHTML = show.map(r => `<tr data-v="${r.v}" class="${r.v === S.sel ? 'on' : ''}">
      <td><span class="plate">${r.plate}</span><div class="muted" style="font-size:11px">${r.provs.slice(0, 2).join(' · ')}${r.provs.length > 2 ? ` +${r.provs.length - 2}` : ''}</div></td>
      <td><span class="sev ${r.sev}">${lbl[r.sev]}</span></td>
      <td class="r">${r.n}</td><td class="r">${fmt1(r.hrs)}</td><td class="r">${fmt(r.km)}</td></tr>`).join('')
    || '<tr><td colspan="5" class="muted" style="padding:14px 6px">ไม่มีรถออกนอกเขตในช่วงเวลา/ตัวกรองนี้</td></tr>';
  $('#vMore').textContent = list.length > 300 ? `แสดง 300 จาก ${fmt(list.length)} คัน — ดาวน์โหลด CSV เพื่อดูทั้งหมด` : 'ไกลสุด = ระยะทางตรงจากใจกลางกรุงเทพฯ (กม.)';
  $('#vTable tbody').querySelectorAll('tr[data-v]').forEach(tr => tr.onclick = () => selectVehicle(+tr.dataset.v, true));
  document.querySelectorAll('#vTable th').forEach(th => {
    th.removeAttribute('aria-sort');
    if (th.dataset.k === S.sortK) th.setAttribute('aria-sort', S.sortDir < 0 ? 'descending' : 'ascending');
  });
}
let VROWS = [];
function renderAreas() {
  const isP = S.level === 'prov', n = isP ? PROV.length : DIST.length;
  const items = [];
  for (let i = 0; i < n; i++) {
    const val = areaVal(S.level, i); if (!val) continue;
    items.push({ key: (isP ? 'p:' : 'd:') + i, name: isP ? PROV[i].th : DIST[i].th, sub: isP ? '' : PROV[distProv[i]].th, val,
      txt: S.metric === 'veh' ? fmt(val) + ' คัน' : fmt(val) + ' ชม.' });
  }
  items.sort((a, b) => b.val - a.val);
  $('#areaTot').textContent = `${fmt(items.length)} พื้นที่`;
  barsInto($('#areaList'), items.slice(0, 60));
}
function renderVehCard() {
  const el = $('#vehCard');
  if (S.sel < 0) { el.innerHTML = '<div class="note">เลือกรถจากรายการ ตาราง "นอกเขต" ช่องค้นหา หรือคลิกจุดบนแผนที่ เพื่อดูเส้นทางเป็นจุดตามเวลา</div>'; return; }
  const v = S.sel, V = D.vehicles;
  const km = VSTAT[v * 4], hir = VSTAT[v * 4 + 1], idle = VSTAT[v * 4 + 2], onl = VSTAT[v * 4 + 3];
  const s = V.start[v], n = V.count[v];
  let mx = 0, provs = new Map();
  for (let i = s; i < s + n; i++) {
    if (TT[i] < S.a || TT[i] > S.b) continue;
    mx = Math.max(mx, SPD[i]);
    if (DI[i] !== 65535) { const p = distProv[DI[i]]; provs.set(p, (provs.get(p) || 0) + DUR[i]); }
  }
  const pv = [...provs.entries()].sort((a, b) => b[1] - a[1]);
  const xs = (EXC_BY_V.get(v) || []).slice().sort((a, b) => a.s - b.s);
  const ii = lastIdxAt(v, S.T);
  el.innerHTML = `<div class="card" style="background:var(--panel)">
    <div class="vhead"><div><div class="p">${V.plate[v]}</div><div class="m">VIN ${V.vin[v]}<br>${CFG.CENTER_NAMES[V.center[v]] || V.center[v]} · car_id ${V.car[v]}</div></div>
      <button class="btn" id="unsel" aria-label="ยกเลิกเลือก">✕</button></div>
    <div class="kv" style="margin-top:10px">
      <span>ระยะทางในช่วง</span><span>${fmt1(km)} กม.</span>
      <span>ออนไลน์</span><span>${fDur(onl)}</span>
      <span>มีผู้โดยสาร</span><span>${fDur(hir)} (${onl ? pct(hir / onl) : '–'})</span>
      <span>จอดว่าง</span><span>${fDur(idle)}</span>
      <span>เร็วสุด</span><span>${mx} กม./ชม.</span>
      <span>จุด GPS ล่าสุดที่รู้</span><span>${V.last[v] || '–'}</span>
      <span>ณ เวลาที่เลือก</span><span>${ii >= 0 && S.T - TT[ii] <= CFG.STALE_MIN * 60 ? (DI[ii] === 65535 ? '–' : DIST[DI[ii]].th) : 'ไม่มีสัญญาณ'}</span>
    </div>
    <div style="margin-top:10px"><div class="muted" style="font-size:11px;margin-bottom:4px">เส้นทางบนแผนที่</div>
      <div class="seg" id="trkSeg">
        <button aria-pressed="${S.trk === 'all'}" data-v="all">ทั้งช่วงที่เลือก</button>
        <button aria-pressed="${S.trk === 'live'}" data-v="live">ตามเวลา (realtime)</button>
      </div>
      <div class="muted" style="font-size:11px;margin-top:4px">${S.trk === 'live' ? 'กด ▶ ที่ timeline ด้านล่าง เส้นทางจะงอกตามรถ · ● แดง = ตำแหน่ง ณ เวลานั้น' : '○ = จุดเริ่ม · ● แดง = จุดสุดท้าย · ลูกศร = ทิศที่รถวิ่ง'}</div></div>
    <div style="margin-top:10px"><div class="muted" style="font-size:11px;margin-bottom:2px">ความเร็วตามเวลา · <span style="color:var(--blue)">■</span> มีผู้โดยสาร</div><canvas class="spark" id="spark"></canvas></div>
    <div style="margin-top:8px;font-size:12px"><span class="muted">จังหวัดที่ไป</span> ${pv.map(([p, s]) => `${PROV[p].th} <span class="muted num">${fDur(s)}</span>`).join(' · ') || '–'}</div>
  </div>
  <div class="sec"><h3>ออกนอกเขต <span>${xs.length} ครั้ง · คลิกเพื่อเลื่อนเวลาไปดู</span></h3>
    <div class="exlist">${xs.map((x, k) => `<div class="ex" data-t="${x.s}"><span class="sev ${x.allOut ? 'all' : x.sev}">${k + 1}</span>
      <span>${fDT(x.s)} – ${fDay(x.s) === fDay(x.e) ? fHM(x.e) : fDT(x.e)}<div class="muted" style="font-size:11px">${[...x.provs.keys()].map(p => PROV[p].th).join(' · ')}</div></span>
      <span class="num">${fDur(x.dur)}</span></div>`).join('') || '<div class="muted">ไม่ออกนอกเขตในช่วงนี้</div>'}</div></div>`;
  $('#unsel').onclick = () => selectVehicle(-1);
  seg($('#trkSeg'), v => { S.trk = v; renderVehCard(); render(); });
  el.querySelectorAll('.ex').forEach(x => x.onclick = () => setT(+x.dataset.t));
  drawSpark(v);
  renderVehStays(v);
}
function drawSpark(v) {
  const cv = $('#spark'); if (!cv) return;
  const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w * dpr; cv.height = h * dpr;
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0);
  const s = D.vehicles.start[v], n = D.vehicles.count[v], span = Math.max(1, S.b - S.a);
  c.fillStyle = '#f6f8f7'; c.fillRect(0, 0, w, h);
  for (let i = s; i < s + n; i++) {
    if (TT[i] < S.a || TT[i] > S.b) continue;
    const x = (TT[i] - S.a) / span * w, y = h - Math.min(1, SPD[i] / 120) * (h - 4);
    c.fillStyle = FLG[i] & 1 ? '#0d93d6' : '#86a596';
    c.fillRect(x, y, Math.max(1, w / 400), h - y);
  }
  const x = (S.T - S.a) / span * w; c.fillStyle = '#10231a'; c.fillRect(x - .5, 0, 1, h);
}
function renderVehList() {
  const rows = [];
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const onl = VSTAT[v * 4 + 3];
    if (S.areas.size && !onl) continue;
    rows.push({ v, km: VSTAT[v * 4], hired: VSTAT[v * 4 + 1], idle: VSTAT[v * 4 + 2], off: (S.b - S.a) - onl });
  }
  rows.sort((a, b) => b[S.vehSort] - a[S.vehSort]);
  $('#vehCount').textContent = `${fmt(rows.length)} คัน`;
  const now = new Map(NOW.map(x => [x.v, x]));
  $('#vehList').innerHTML = rows.slice(0, 200).map(r => {
    const nw = now.get(r.v), c = nw ? COL[nw.st] : [220, 226, 223];
    const val = S.vehSort === 'km' ? fmt1(r.km) + ' กม.' : fDur(r[S.vehSort]);
    return `<div class="vrow${r.v === S.sel ? ' on' : ''}" data-v="${r.v}"><i class="dot" style="background:rgb(${c})"></i>
      <span><span class="plate">${D.vehicles.plate[r.v]}</span> <span class="muted" style="font-size:11px">${D.vehicles.center[r.v]}</span></span>
      <span class="num muted" style="font-size:12px">${val}</span></div>`;
  }).join('');
  $('#vehList').querySelectorAll('.vrow').forEach(x => x.onclick = () => selectVehicle(+x.dataset.v, true));
}
function renderLegend() {
  const ch = S.choro ? `<div style="margin-top:6px"><span class="lbl">${{ veh: 'จำนวนรถ (คัน)', hrs: 'ชั่วโมงรวม', hired: 'ชม. มีผู้โดยสาร' }[S.metric]} · ${S.level === 'prov' ? 'จังหวัด' : 'อำเภอ/เขต'}</span>
    <div class="ramp">${RAMP.map(c => `<i style="background:${c}"></i>`).join('')}</div>
    <div class="rampl"><span>1</span><span>${fmt(choroScale.max)}</span></div></div>` : '';
  $('#legend').innerHTML = `<span class="lbl">สถานะรถ</span>
    <div class="row"><i class="dot" style="background:var(--blue)"></i>มีผู้โดยสาร</div>
    <div class="row"><i class="dot" style="background:var(--green)"></i>ว่าง · กำลังวิ่ง</div>
    <div class="row"><i class="dot" style="background:var(--slate)"></i>จอด</div>
    <div class="row"><i class="dot" style="background:#fff;box-shadow:0 0 0 2px var(--red)"></i>อยู่นอกเขตที่อนุญาต</div>
    ${EMBEDDED && EMBEDDED.car ? '<div class="row muted" style="font-size:11px">รูปรถ: สถานะดูจากวงสีใต้ล้อ</div>' : ''}
    <div class="row"><i style="width:14px;border-top:2px solid var(--blue)"></i>ขอบเขตที่อนุญาต</div>${S.mly ? '<div class="row"><i style="width:14px;border-top:3px solid #05cb63"></i>ถนนที่มีภาพ · คลิกเพื่อดู</div>' : ''}${ch}`;
}
function renderAreaChips() {
  $('#areaRow').style.display = S.areas.size ? 'flex' : 'none';
  $('#fArea').innerHTML = [...S.areas].map(k => `<span class="chip area">${areaName(k)}<button data-k="${k}" aria-label="ลบ">×</button></span>`).join('')
    + (S.areas.size > 1 ? '<button class="chip" id="clrArea">ล้างทั้งหมด</button>' : '');
  $('#fArea').querySelectorAll('button[data-k]').forEach(b => b.onclick = () => toggleArea(b.dataset.k));
  const c = $('#clrArea'); if (c) c.onclick = () => { S.areas.clear(); onFilterChange(); };
}
function renderRangeText() {
  $('#rngTxt').textContent = `${fDT(S.a)} – ${fDT(S.b)}`;
}
function renderStays() {
  let on = 0, out = 0, far = 0, near = 0, dep = 0;
  const rows = [];
  for (const [v, x] of NIGHT) {
    if (S.areas.size && !areaMatchDist(x.d)) continue;
    on++;
    const sev = nightSev(x);
    if (sev === 'in') continue;
    out++; if (sev === 'far') far++; else near++;
    const dp = depotOf(x.lat, x.lon); if (dp) dep++;
    rows.push({ v, x, sev, dp });
  }
  $('#sOn').textContent = fmt(on);
  $('#sOnS').textContent = `จาก ${fmt(AREA.active)} คันที่มีสัญญาณ`;
  $('#sOut').textContent = fmt(out);
  $('#sOutS').textContent = `ต่างจังหวัด ${fmt(far)} · ปริมณฑล ${fmt(near)} · ในลานจอด ${fmt(dep)}`;
  renderDepots();
  let list = rows;
  if (S.sSev === 'far' || S.sSev === 'near') list = rows.filter(r => r.sev === S.sSev);
  if (S.sSev === 'nodep') list = rows.filter(r => !r.dp);
  list.sort((a, b) => (b.sev === 'far') - (a.sev === 'far') || b.x.night - a.x.night);
  $('#sTblN').textContent = `${fmt(list.length)} คัน`;
  $('#sList').innerHTML = list.slice(0, 250).map(r => {
    const g = Geo.peek(r.x.lat, r.x.lon);
    return `<div class="vrow${r.v === S.sel ? ' on' : ''}" data-v="${r.v}">
      <span class="sev ${r.sev}">${r.sev === 'far' ? 'ต่างจ.' : 'ปริมณฑล'}</span>
      <span><span class="plate">${D.vehicles.plate[r.v]}</span> <span class="muted" style="font-size:11.5px">${DIST[r.x.d].th}, ${PROV[distProv[r.x.d]].th}</span>
        ${r.dp ? '<span class="sev all" style="margin-left:4px">ลานจอด</span>' : ''}
        ${g ? `<div class="muted" style="font-size:11px">${g.short}</div>` : ''}</span>
      <span class="num muted" style="font-size:12px">${fDur(r.x.dur)}</span></div>`;
  }).join('') || '<div class="muted" style="padding:8px 0">ไม่มีรถค้างคืนนอกเขตในตัวกรองนี้</div>';
  $('#sList').querySelectorAll('.vrow').forEach(el => el.onclick = () => {
    const v = +el.dataset.v, x = NIGHT.get(v);
    selectVehicle(v, false); switchTab('stay');
    map.flyTo({ center: [x.lon, x.lat], zoom: 16, duration: 800 });
    showPlace(x.lat, x.lon, D.vehicles.plate[v], `ค้างคืน ${fDT(x.s)} – ${fDT(x.e)}`);
  });
}
function renderDepots() {
  $('#depN').textContent = `${DEPOTS.length} แห่ง · ${fmt(DEPOTS.reduce((s, d) => s + d.n, 0))} คัน`;
  $('#depList').innerHTML = DEPOTS.map(dp => {
    const g = Geo.peek(dp.lat, dp.lon), out = !inZone(dp.d);
    return `<div class="dep" data-k="${dp.k}"><span class="n">${dp.n}</span>
      <span>${DIST[dp.d].th}, ${PROV[distProv[dp.d]].th} ${out ? '<span class="sev near">นอกเขต</span>' : ''}
        <div class="ad">${g ? g.short : 'คลิกเพื่อดูที่อยู่ · ภาพถนน'}</div></span>
      <span class="muted" style="font-size:11px">คัน</span></div>`;
  }).join('');
  $('#depList').querySelectorAll('.dep').forEach(el => el.onclick = () => {
    const dp = DEPOTS[+el.dataset.k];
    map.flyTo({ center: [dp.lon, dp.lat], zoom: 16, duration: 800 });
    showPlace(dp.lat, dp.lon, `ลานจอด · ${dp.n} คันค้างคืน`, `${DIST[dp.d].th}, ${PROV[distProv[dp.d]].th}`);
  });
  updGeoQ();
}
function renderVehStays(v) {
  const st = (STAYS_BY_V.get(v) || []).slice().sort((a, b) => a.s - b.s);
  const sec = document.createElement('div');
  sec.className = 'sec';
  const iNow = lastIdxAt(v, S.T);
  if (iNow >= 0 && !(FLG[iNow] & 2)) {
    const b = document.createElement('button');
    b.className = 'btn'; b.style.alignSelf = 'flex-start';
    b.textContent = `📍 ที่อยู่ · ภาพถนน ตำแหน่ง ${fHM(TT[iNow])}`;
    b.onclick = () => {
      const la = POS[2 * iNow + 1], lo = POS[2 * iNow];
      map.flyTo({ center: [lo, la], zoom: 16, duration: 800 });
      showPlace(la, lo, D.vehicles.plate[v], `ตำแหน่ง ${fDT(TT[iNow])} · ${SPD[iNow]} กม./ชม.`);
    };
    $('#vehCard').appendChild(b);
  }
  sec.innerHTML = `<h3>จุดจอด ≥ ${CFG2.STAY_MIN} นาที <span>${st.length} จุด · 🌙 = ค้างคืน · คลิกดูที่อยู่/ภาพถนน</span></h3>
    <div class="exlist">${st.map((x, k) => {
      const g = Geo.peek(x.lat, x.lon), night = x.night >= CFG2.NIGHT_MIN_H * 3600, out = !inZone(x.d), dp = depotOf(x.lat, x.lon);
      return `<div class="stay" data-k="${k}"><span class="ic${night ? ' night' : ''}${out ? ' out' : ''}">${night ? '🌙' : k + 1}</span>
        <span>${fDT(x.s)} – ${fDay(x.s) === fDay(x.e) ? fHM(x.e) : fDT(x.e)}
          <div class="ad">${dp ? 'ลานจอด · ' : ''}${g ? g.short : DIST[x.d].th + ', ' + PROV[distProv[x.d]].th}</div></span>
        <span class="num">${fDur(x.dur)}</span></div>`;
    }).join('') || '<div class="muted">ไม่มีจุดจอดนานในช่วงนี้</div>'}</div>`;
  $('#vehCard').appendChild(sec);
  sec.querySelectorAll('.stay').forEach(el => el.onclick = () => {
    const x = st[+el.dataset.k];
    setT(x.s);
    map.flyTo({ center: [x.lon, x.lat], zoom: 16, duration: 800 });
    showPlace(x.lat, x.lon, D.vehicles.plate[v], `จอด ${fDur(x.dur)} · ${fDT(x.s)}`);
  });
}
