/* js/dev/selftest.js — ทดสอบอัตโนมัติ (เรียกผ่าน ?selftest หรือ #test=car|tilt|wheel) — ไม่กระทบผู้ใช้
   ใช้: ทุกโมดูล
   ให้: selftest() · selftestV2() · testCar() · testTilt() · testWheel()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

async function testWheel() {       // ใช้ทดสอบอัตโนมัติ: เริ่มมุมมองปกติ (อัตโนมัติ) แล้วหมุนลูกกลิ้งซูมเข้าเหมือนผู้ใช้
  const out = [], wait = ms => new Promise(ok => setTimeout(ok, ms));
  const gl = map.getCanvas().getContext('webgl2') || map.getCanvas().getContext('webgl');
  const dbg = gl && gl.getExtension('WEBGL_debug_renderer_info');
  out.push('GPU: ' + (dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : '?') + ' · ' + (gl instanceof WebGL2RenderingContext ? 'WebGL2' : 'WebGL1'));
  const c = map.getCanvas(), r = c.getBoundingClientRect();
  const count = () => {
    const pk = deckOverlay.pickObjects({ x: 0, y: 0, width: c.clientWidth, height: c.clientHeight, layerIds: ['now', 'now-car', 'now-ring'] });
    return `zoom ${map.getZoom().toFixed(1)} · รูปรถ=${useCarIcons()} · วาดในจอ ${pk.length}`;
  };
  out.push('เริ่ม ' + count());
  map.jumpTo({ center: [100.5348, 13.7465] });
  for (let k = 0; k < 24; k++) {                                   // หมุนลูกกลิ้งทีละขั้น ให้เลยเกณฑ์รูปรถ
    c.dispatchEvent(new WheelEvent('wheel', { deltaY: -240, deltaMode: 0, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, bubbles: true, cancelable: true }));
    await wait(350);
    if (k % 3 === 2) out.push('หมุน ' + (k + 1) + ' ครั้ง → ' + count());
  }
  await wait(3000); out.push('รอ 3 วิ → ' + count());
  out.push('errors: ' + (ERRS.length ? ERRS.join(' | ') : 'ไม่มี'));
  const pre = document.createElement('pre'); pre.id = 'wheeltest'; pre.textContent = out.join('\n'); document.body.appendChild(pre);
}
async function testCar() {         // ใช้ทดสอบอัตโนมัติ: บังคับรูปรถ ซูมย่านสยาม แล้วนับรูปรถที่วาดได้จริง
  const out = [], wait = ms => new Promise(ok => setTimeout(ok, ms));
  const gl = map.getCanvas().getContext('webgl2') || map.getCanvas().getContext('webgl');
  const dbg = gl && gl.getExtension('WEBGL_debug_renderer_info');
  out.push('GPU: ' + (dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'ไม่ทราบ'));
  map.jumpTo({ center: [100.5348, 13.7465], zoom: 15, pitch: 0 });
  await wait(2000);
  const c0 = map.getCanvas();
  out.push('มุมตรง → รูปรถ=' + useCarIcons() + ' · วาดรูปรถ ' + deckOverlay.pickObjects({ x: 0, y: 0, width: c0.clientWidth, height: c0.clientHeight, layerIds: ['now-car'] }).length
    + ' · วาดจุด ' + deckOverlay.pickObjects({ x: 0, y: 0, width: c0.clientWidth, height: c0.clientHeight, layerIds: ['now'] }).length);
  $('#viewSeg').querySelector('[data-v="3d"]').click();
  await wait(4000);
  out.push('zoom ' + map.getZoom().toFixed(1) + ' · ใช้รูปรถ: ' + useCarIcons() + ' · atlas: ' + (CAR_ATLAS ? CAR_ATLAS.length + ' ตัวอักษร' : 'ไม่มี'));
  out.push('รถใน NOW: ' + NOW.length);
  const c = map.getCanvas();
  const picked = deckOverlay.pickObjects({ x: 0, y: 0, width: c.clientWidth, height: c.clientHeight, layerIds: ['now', 'now-car'] });
  out.push('รูปรถที่วาดในจอ (pick): ' + picked.length);
  const pre = document.createElement('pre'); pre.id = 'cartest'; pre.textContent = out.join('\n'); document.body.appendChild(pre);
}
async function testTilt() {        // ใช้ทดสอบอัตโนมัติ: จำลองปุ่มกลางเมาส์ + ปุ่มเอียง 3D แล้วรายงานมุม
  const r = [], log = k => r.push(`${k}: pitch=${map.getPitch().toFixed(1)} bearing=${map.getBearing().toFixed(1)}`);
  const wait = ms => new Promise(ok => setTimeout(ok, ms));
  const el = map.getContainer(), box = el.getBoundingClientRect(), cx = box.left + box.width / 2, cy = box.top + box.height / 2;
  log('เริ่ม');
  el.dispatchEvent(new MouseEvent('mousedown', { button: 1, buttons: 4, clientX: cx, clientY: cy, bubbles: true }));
  window.dispatchEvent(new MouseEvent('mousemove', { buttons: 4, clientX: cx + 100, clientY: cy - 150, bubbles: true }));
  window.dispatchEvent(new MouseEvent('mouseup', { button: 1, clientX: cx + 100, clientY: cy - 150, bubbles: true }));
  log('ปุ่มกลาง ลากขึ้น 150 ขวา 100');
  $('#viewSeg').querySelector('[data-v="2d"]').click(); await wait(1500); log('กดมุมตรง');
  $('#viewSeg').querySelector('[data-v="3d"]').click(); await wait(2500); log('กดเอียง 3D');
  const pre = document.createElement('pre'); pre.id = 'tilt'; pre.textContent = r.join('\n'); document.body.appendChild(pre);
}
function selftestV2(out) {
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
}
function selftest() {   // ใช้ตอนทดสอบอัตโนมัติ (?selftest) — เขียนผลลง <pre id=st>
  const out = { N, NV, active: AREA.active };
  for (const z of ['bkk', 'bkk_air', 'metro']) {
    S.zone = z; S.minDur = 10; computeExcursions();
    const rows = violRows();
    out[z] = { cars: rows.length, trips: EXC.length, hrs: Math.round(EXC.reduce((s, x) => s + x.dur, 0) / 3600),
               far: rows.filter(r => r.sev === 'far').length, all: rows.filter(r => r.sev === 'all').length };
  }
  S.zone = 'bkk'; computeExcursions();
  selftestV2(out);
  const pre = document.createElement('pre'); pre.id = 'st'; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
}
