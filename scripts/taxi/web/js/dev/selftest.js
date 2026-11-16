/* js/dev/selftest.js — automatic check (open with ?selftest) — writes the numbers to <pre id="st">
   The numbers must equal the previous version's for the same data (same analysis, new UI).
   provides: selftest() */

function selftest() {
  computeDepots();
  const out = { N, NV, active: AREA.active };
  for (const z of ['bkk', 'bkk_air', 'metro']) {
    S.zone = z; S.minDur = 10; computeExcursions();
    const rows = violRows();
    out[z] = { cars: rows.length, trips: EXC.length, hrs: Math.round(EXC.reduce((s, x) => s + x.dur, 0) / 3600),
               far: rows.filter(r => r.sev === 'far').length, all: rows.filter(r => r.sev === 'all').length };
  }
  computeStays();
  let stays = 0; for (const st of STAYS_BY_V.values()) stays += st.length;
  let ob = 0, om = 0;
  const metro = new Set(['TH10', ...CFG.METRO]);
  for (const x of NIGHT.values()) { const pc = PROV[distProv[x.d]].pc; if (pc !== 'TH10') ob++; if (!metro.has(pc)) om++; }
  out.stays = { stays, night: NIGHT.size, night_out_bkk: ob, night_out_metro: om,
                depots: DEPOTS.length, depot_cars: DEPOTS.reduce((s, d) => s + d.n, 0), near_pts: NEARDEP.reduce((s, x) => s + x, 0) };
  S.exDepot = true;
  for (const z of ['bkk', 'metro']) {
    S.zone = z; computeExcursions();
    out['dep_' + z] = { cars: EXC_BY_V.size, trips: EXC.length, hrs: Math.round(EXC.reduce((s, x) => s + x.dur, 0) / 3600) };
  }
  S.exDepot = false; S.zone = 'bkk'; computeExcursions();
  const pre = document.createElement('pre'); pre.id = 'st'; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
}
/* ?asktest — runs the offline assistant on the training questions and writes intent + answer to <pre id="ask"> */
function asktest() {
  let vb = 0; for (let v = 1; v < NV; v++) if (D.vehicles.count[v] > D.vehicles.count[vb]) vb = v;   // car with most data
  const plate = plateOf(vb).split(' · ')[0];
  const qs = ['ภูเก็ตตอนนี้มีรถเรามั้ย', 'แถวบางนามีแท็กซี่ว่างกี่คันครับ', `${plate} ตอนนี้ไปถึงไหนแล้ว`, `เมื่อวาน${plate} วิ่งไปไหนบ้าง`,
    'วันนี้มีใครออกนอกเขตบ้าง', 'จังหวัดไหนรถเยอะที่สุดตอนนี้', 'ที่ชาร์จรถไฟฟ้าแถวหาดใหญ่', `ช่วยตัดไฟรถ ${plate} ที`, 'ขอสูตรต้มยำ',
    'How many cars are in Phuket now?', 'EV chargers near Siam', 'Which cars left the zone today?', 'When are the most cars on a trip?',
    'สนามบินสุวรรณภูมิมีรถจอดรอกี่คัน', 'ตอนตี 3 มีรถออนไลน์กี่คัน', 'มีข้อมูลของวันไหนบ้าง', 'คันนี้มีผู้โดยสารไหม'];
  const out = qs.map(q => { const p = NLU.parse(q, { lastV: Agent.ctx.lastV }); const r = Agent.askOffline(q); return `${p.intent}\t${q}\t→ ${r.text.replace(/\n/g, ' ⏎ ')}`; });
  const pre = document.createElement('pre'); pre.id = 'ask'; pre.textContent = out.join('\n'); document.body.appendChild(pre);
}
/* ?triptest — trip summary for busy vehicles at several cursor times + one replay start; writes to <pre id="trip"> */
function triptest() {
  const vs = [...Array(NV).keys()].sort((a, b) => D.vehicles.count[b] - D.vehicles.count[a]).slice(0, 40);
  const tally = { stopped: 0, moving: 0, data: 0, estimate: 0, direction: 0, none: 0, origin: 0 }, ex = [];
  for (const T of [D.meta.tmax * 0.3, D.meta.tmax * 0.6, D.meta.tmax]) for (const v of vs) {
    const r = tripInfo(v, T); if (!r) continue;
    if (r.stopped) { tally.stopped++; continue; }
    tally.moving++; if (r.origin) tally.origin++;
    tally[r.next ? r.next.kind : 'none']++;
    if (r.next && ex.length < 6) ex.push(`car:${v} ${fHM(T)} ${r.next.kind} ${r.next.km ? r.next.km.toFixed(1) + 'km' : ''} ${r.next.confidence || ''}`);
  }
  S.others = 'hide'; selectVehicle(vs[0], false); replayTrip(); setPlaying(false);
  const pre = document.createElement('pre'); pre.id = 'trip';
  pre.textContent = JSON.stringify(tally) + '\n' + ex.join('\n') + `\nreplay: live=${isLive()} T=${fDT(S.T)} trk=${S.trk} panel=${S.panel}`;
  document.body.appendChild(pre);
}
/* ?refreshtest — reloads data/taxi-data.js through the live-update path; selection and numbers must survive */
function refreshtestDone() {
  const pre = document.createElement('pre'); pre.id = 'refresh';
  pre.textContent = JSON.stringify({ live: isLive(), sel: S.sel, N, NV, active: AREA.active, outside: EXC_BY_V.size, online: NOWSTAT.on, panel: S.panel });
  document.body.appendChild(pre);
}
/* ?layertest — counts what is actually drawn per car layer at a few zoom levels (pick buffer) → <pre id="layers"> */
async function layertest() {
  const out = [], wait = ms => new Promise(ok => setTimeout(ok, ms));
  for (const z of [9.6, 11, 13, 15]) {
    map.jumpTo({ center: [100.53, 13.75], zoom: z }); await wait(2500);
    const c = map.getCanvas(), box = { x: 0, y: 0, width: c.clientWidth, height: c.clientHeight };
    const n = id => deckOverlay.pickObjects(Object.assign({ layerIds: [id] }, box)).length;
    out.push(`zoom ${z} · ZS ${ZS.toFixed(2)} · puck px ${puckPx().toFixed(1)} · dots ${n('now')} · moving markers ${n('now-puck')} · offline ${n('offline')}`);
  }
  const pre = document.createElement('pre'); pre.id = 'layers'; pre.textContent = out.join('\n'); document.body.appendChild(pre);
}
/* ?roadtest — once data/taxi-roads.js is in: at several times, how many cars on screen sit on a road leg
   (instead of hopping) → <pre id="roads"> */
async function roadtest() {
  const t0 = performance.now();
  while (!ROADS && performance.now() - t0 < 60000) await new Promise(ok => setTimeout(ok, 200));
  const out = [`roads loaded: ${!!ROADS} · legs ${ROADS ? ROADS.a.length.toLocaleString() : 0} · after ${Math.round(performance.now() - t0)} ms`];
  for (const f of [0.35, 0.5, 0.8]) {
    S.T = D.meta.tmax * f; computeNow();
    let on = 0, mid = 0;
    for (const d of NOW) { const i = d.i; const r = roadPosAt(d.v, i, S.T); if (r) { on++; if (Math.abs(r[0] - POS[2 * i]) + Math.abs(r[1] - POS[2 * i + 1]) > 1e-4) mid++; } }
    out.push(`${fDT(S.T)} · cars ${NOW.length} · on a road leg ${on} (${Math.round(on / NOW.length * 100)}%) · between fixes now ${mid}`);
  }
  const pre = document.createElement('pre'); pre.id = 'roads'; pre.textContent = out.join('\n'); document.body.appendChild(pre);
}
/* ?followtest — replay the busiest car: does the map move with it, does the car stay on screen, does a drag stop following? */
async function followtest() {
  const wait = ms => new Promise(ok => setTimeout(ok, ms));
  while (!ROADS) await wait(200);
  const v = [...Array(NV).keys()].sort((a, b) => D.vehicles.count[b] - D.vehicles.count[a])[0];
  selectVehicle(v, true, 'hide'); await wait(1500);
  replayTrip(); await wait(300);
  cancelAnimationFrame(raf);                                     // headless: frame timestamps are frozen → step time by hand
  { const d = NOW.find(x => x.v === S.sel); if (d) map.jumpTo({ center: [d.x, d.y], zoom: 15 }); } await wait(300);
  const c = map.getContainer(), w = c.clientWidth, h = c.clientHeight, out = [];
  const c0 = map.getCenter(), t0 = S.T, d0 = NOW.find(x => x.v === S.sel);
  let onScreen = 0, n = 0;
  for (let k = 0; k < 20; k++) {
    for (let f = 0; f < 15; f++) { setT(S.T + 10); await wait(16); }     // 15 frames × 10 s of data = like playing at 10 min/s
    const d = NOW.find(x => x.v === S.sel); if (!d) continue;
    const p = map.project([d.x, d.y]); n++;
    if (p.x >= 0 && p.x <= w && p.y >= 0 && p.y <= h) onScreen++;
  }
  const c1 = map.getCenter(), d1 = NOW.find(x => x.v === S.sel);
  out.push(`cursor advanced ${fDur(S.T - t0)} · car moved ${d0 && d1 ? (hav(d0.x, d0.y, d1.x, d1.y) * 1000).toFixed(0) : '?'} m`);
  out.push(`playing ${S.playing} · follow ${S.follow} · map moved ${(hav(c0.lng, c0.lat, c1.lng, c1.lat) * 1000).toFixed(0)} m in 5 s · car on screen ${onScreen}/${n} frames`);
  map.fire('dragstart', { originalEvent: new MouseEvent('mousedown') });
  const c2 = map.getCenter();
  for (let f = 0; f < 60; f++) { setT(S.T + 10); await wait(16); }
  const c3 = map.getCenter();
  out.push(`after a drag: follow ${S.follow} · map moved ${(hav(c2.lng, c2.lat, c3.lng, c3.lat) * 1000).toFixed(0)} m in 2 s (should be 0)`);
  setFollow(true); await wait(2000);
  out.push(`Follow car again: follow ${S.follow} · badge "${(document.getElementById('mmFollow') || {}).textContent}"`);
  setPlaying(false);
  const pre = document.createElement('pre'); pre.id = 'follow'; pre.textContent = out.join('\n'); document.body.appendChild(pre);
}
/* ?clocktest — Live runs on a clock: does the cursor move with real time, do cars move between batches, does it wait at the end?
   real time for 3 s, then ×60 so the 5 minutes to the newest data pass in 5 s */
async function clocktest() {
  const wait = ms => new Promise(ok => setTimeout(ok, ms));
  while (!ROADS) await wait(200);
  const out = [], pos = () => { computeNow(); return new Map(NOW.map(d => [d.v, [d.x, d.y]])); };
  const moved = (a, b) => [...b].filter(([v, p]) => a.has(v) && hav(a.get(v)[0], a.get(v)[1], p[0], p[1]) > 0.001).length;
  out.push(`open: live ${isLive()} · ${Math.round(D.meta.tmax - S.T)} s behind the newest data`);
  let T = S.T, p = pos();
  await wait(3000);
  out.push(`after 3 s: cursor +${(S.T - T).toFixed(1)} s · cars moved ${moved(p, pos())} of ${NOW.length}`);
  liveAnchor(S.T, 60);
  T = S.T; p = pos();
  await wait(2000);
  out.push(`×60 for 2 s: cursor +${Math.round(S.T - T)} s · cars moved ${moved(p, pos())}`);
  await wait(4000);
  out.push(`end: ${Math.round(D.meta.tmax - S.T)} s behind · waiting ${liveWaiting()} · badge "${$('#mapMode').textContent.replace(/\s+/g, ' ').trim()}"`);
  setT(S.T - 1800); out.push(`moved back 30 min: live ${isLive()}`);
  goLive(); out.push(`Go live: live ${isLive()} · ${Math.round(D.meta.tmax - S.T)} s behind`);
  const pre = document.createElement('pre'); pre.id = 'clock'; pre.textContent = out.join('\n'); document.body.appendChild(pre);
}
/* ?layoutdump — sizes of the main regions (checks for anything wider than the screen) → <pre id="layout"> */
function layoutdump() {
  const r = s => { const e = document.querySelector(s); if (!e) return s + ' –'; const b = e.getBoundingClientRect(); return `${s} x${Math.round(b.left)} w${Math.round(b.width)} sw${e.scrollWidth}`; };
  const pre = document.createElement('pre'); pre.id = 'layout';
  pre.textContent = [`inner ${innerWidth} · doc scroll ${document.documentElement.scrollWidth}`, r('.top'), r('.brand'), r('.search'), r('#askBtn'), r('.chat'), r('.chat-log'), r('.msg.bot'), r('.side')].join('\n');
  document.body.appendChild(pre);
}
/* ?cleartest — the reported case: ask the chat for one car, then do something else → the page must not stay stuck on that car;
   then "Clear all" must reset filters, the car, the time and the chat */
async function cleartest() {
  const wait = ms => new Promise(ok => setTimeout(ok, ms));
  const out = [], shown = () => { computeNow(); return nowData().length; }, b = $('#clrAll');
  const all = shown();
  out.push(`start: clear button shown ${!b.hidden}`);
  const v = NOW.find(d => d.st === 'vacant').v;
  await Chat.send(`where is ${plateOf(v)}`);
  out.push(`asked for one car: selected ${S.sel === v} · follow ${S.follow} · button "${b.textContent}"`);
  await Chat.send('How many cars are in Phuket now?');
  out.push(`then asked about an area: selected car released ${S.sel === -1} · cars drawn ${shown()} of ${all}`);
  await Chat.send(`where is ${plateOf(v)}`);
  const c0 = map.getCenter(); map.jumpTo({ center: [100.9, 13.1] }); await wait(1500);
  out.push(`car picked again, map moved away: map stays where moved ${hav(map.getCenter().lng, map.getCenter().lat, 100.9, 13.1) < 0.1}`);
  $('#fStatus').value = 'hired'; $('#fStatus').onchange({ target: $('#fStatus') });
  $('#fPreset').value = 'bkk'; $('#fPreset').onchange({ target: $('#fPreset') });
  S.sev = 'far'; S.pPlace = 'charger'; S.vehQ = '12';
  setT(S.T - 3600);
  render();
  out.push(`filters + car + history: live ${isLive()} · button "${b.textContent}"`);
  b.click(); await wait(300);
  out.push(`after Clear all: car ${S.sel} · live ${isLive()} · cars drawn ${shown()} · button shown ${!b.hidden} · status "${$('#fStatus').value}" · area "${$('#fPreset').value}" · chat messages ${$$('#chatLog .msg').length} · AI history ${Agent.history.length}`);
  const pre = document.createElement('pre'); pre.id = 'clear'; pre.textContent = out.join('\n'); document.body.appendChild(pre);
}
