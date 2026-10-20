/* js/analysis/filters.js — ตัวกรองที่ไม่ขึ้นกับเวลา (ศูนย์ · สถานะ · พื้นที่) → MASK ต่อจุด
   ใช้: state.js · model.js
   ให้: areaMatchDist() · vehPass() · rebuildMask() · zoneSets()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* ตัวกรองที่ไม่เกี่ยวกับเวลา → MASK ต่อจุด */
function areaMatchDist(dIdx) {
  if (!S.areas.size) return true;
  if (dIdx === 65535) return false;
  return S.areas.has('d:' + dIdx) || S.areas.has('p:' + distProv[dIdx]);
}
function vehPass(v) {
  if (S.centers.size && !S.centers.has(D.vehicles.center[v])) return false;
  return true;
}
function rebuildMask() {
  MASK = new Uint8Array(N);
  const st = S.status;
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const s = D.vehicles.start[v], e = s + D.vehicles.count[v];
    for (let i = s; i < e; i++) {
      const sx = status(i);
      if (sx !== 'nosig' && !st.has(sx)) continue;
      if (!areaMatchDist(DI[i])) continue;
      MASK[i] = 1;
    }
  }
  maskVer++;
}

/* เขตที่อนุญาต (ตาม preset ที่เลือก) → ชุดดัชนีจังหวัด/อำเภอ — ใช้ทั้งนับนอกเขตและสถานะ ณ เวลา */
function zoneSets() {
  const z = CFG.ZONES[S.zone];
  const pIdx = new Set(z.prov.map(pc => PROV.findIndex(p => p.pc === pc)));
  const dIdx = new Set(z.dist.map(pc => DIST.findIndex(d => d.pc === pc)));
  return { pIdx, dIdx };
}
