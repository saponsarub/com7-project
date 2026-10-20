/* js/analysis/excursions.js — วิเคราะห์ออกนอกเขต (ช่วงที่รถอยู่นอกเขตต่อเนื่อง)
   ใช้: filters.js
   ให้: computeExcursions() · violRows()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

function computeExcursions() {
  const { pIdx, dIdx } = zoneSets();
  const metro = new Set(CFG.METRO.map(pc => PROV.findIndex(p => p.pc === pc)));
  const allowed = new Uint8Array(DIST.length);
  for (let j = 0; j < DIST.length; j++) allowed[j] = pIdx.has(distProv[j]) || dIdx.has(j) ? 1 : 0;
  const GAP = CFG.GAP_MIN * 60, MIN = S.minDur * 60;
  const [bx, by] = CFG.BKK_CENTER;
  const out = [];
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const s = D.vehicles.start[v], e = s + D.vehicles.count[v];
    let cur = null, lastT = -1e9, nIn = 0, nAll = 0;
    const close = () => {
      if (!cur) return;
      cur.dur = cur.e - cur.s;
      if (cur.dur >= MIN && (MIN > 0 || cur.n >= 1)) out.push(cur);
      cur = null;
    };
    for (let i = s; i < e; i++) {
      const t = TT[i];
      if (t < S.a || t > S.b) continue;
      if (FLG[i] & 2 || DI[i] === 65535) continue;          // ไม่มีสัญญาณ ไม่นับ
      nAll++;
      const isOut = !allowed[DI[i]] && !(S.exDepot && NEARDEP && NEARDEP[i]);
      if (!isOut) { nIn++; close(); lastT = t; continue; }
      if (!cur || t - lastT > GAP) {
        close();
        cur = { v, s: t, e: t, n: 1, provs: new Map(), km: 0, i0: i };
      } else {
        cur.e = t; cur.n++;
      }
      const p = distProv[DI[i]];
      cur.provs.set(p, (cur.provs.get(p) || 0) + Math.min(DUR[i], GAP));
      const km = hav(POS[2 * i], POS[2 * i + 1], bx, by);
      if (km > cur.km) { cur.km = km; cur.far = p; }
      lastT = t;
    }
    close();
    // ทั้งช่วงไม่เคยเข้าเขตเลย = "อยู่นอกตลอด"
    if (nAll && !nIn) for (const x of out) if (x.v === v) x.allOut = true;
  }
  for (const x of out) {
    let far = false;
    for (const p of x.provs.keys()) if (!pIdx.has(p) && !metro.has(p)) { far = true; break; }
    x.sev = far ? 'far' : 'near';
  }
  EXC = out;
  EXC_BY_V = new Map();
  for (const x of out) { if (!EXC_BY_V.has(x.v)) EXC_BY_V.set(x.v, []); EXC_BY_V.get(x.v).push(x); }
}
function violRows() {
  const rows = [];
  for (const [v, xs] of EXC_BY_V) {
    const provs = new Map(); let hrs = 0, km = 0, far = false, allOut = false;
    for (const x of xs) {
      hrs += x.dur / 3600; km = Math.max(km, x.km); far = far || x.sev === 'far'; allOut = allOut || !!x.allOut;
      for (const [p, s] of x.provs) provs.set(p, (provs.get(p) || 0) + s);
    }
    const top = [...provs.entries()].sort((a, b) => b[1] - a[1]).map(e => PROV[e[0]].th);
    const sev = allOut ? 'all' : far ? 'far' : 'near';
    rows.push({ v, plate: D.vehicles.plate[v], n: xs.length, hrs, km, provs: top, sev,
                sevRank: sev === 'far' ? 3 : sev === 'all' ? 2 : 1 });
  }
  return rows;
}
