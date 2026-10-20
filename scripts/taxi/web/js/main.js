/* js/main.js — จุดเริ่มต้น — โหลดข้อมูล แล้วเรียก init ตามลำดับ (ต้องโหลดเป็นไฟล์สุดท้าย)
   ใช้: ทุกโมดูล
   ให้: –
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

(async function main() {
  const msg = $('#loadMsg');
  try {
    initMap();
    const data = await DataSource.load(m => msg.textContent = m);
    prepare(data);
    pcToProv = new Map(PROV.map((p, i) => [p.pc, i]));
    pcToDist = new Map(DIST.map((d, i) => [d.pc, i]));
    // ลำดับ feature ใน geo ไม่จำเป็นต้องตรงกับลำดับใน areas — ใช้ pc เป็นคีย์
    $('#subtitle').textContent = `${fmt(NV)} คัน · ${fmt(N)} จุด GPS · ${fDT(0)} – ${fDT(D.meta.tmax)}`;
    msg.textContent = 'คำนวณ…';
    rebuildMask(); buildTimelineBins(); buildZoneGeo();
    msg.textContent = 'หาจุดจอดและลานจอด…'; computeDepots();
    initUI(); initV2(); initTimeline();
    refreshPanels(); setT(S.T);
    $('#loading').classList.add('hide');
    applyHash();
    if (location.search.includes('selftest')) selftest();
  } catch (e) {
    console.error(e);
    msg.innerHTML = `<b style="color:var(--red)">โหลดไม่สำเร็จ</b><br>${e.message}<br><span class="muted">ต้องเปิดด้วย Chrome / Edge รุ่นใหม่ และต่ออินเทอร์เน็ต (โหลดแผนที่)</span>`;
    document.querySelector('.spin').style.display = 'none';
  }
})();
