/* js/core/errors.js — แสดง error บนจอ (กล่องแดงบนแผนที่) + ดัก error ทั้งหน้า
   ใช้: –
   ให้: ERRS · showErr()
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

/* แสดง error บนจอ — ถ้ามีอะไรพังในเครื่องผู้ใช้ จะได้แคปหน้าจอส่งมาดูได้ */
const ERRS = [];
function showErr(where, e) {
  const m = `[${where}] ${(e && (e.message || e.reason && e.reason.message || e.error && e.error.message)) || e}`;
  ERRS.push(m); console.error(where, e);
  const b = document.getElementById('errbox');
  if (b) { b.style.display = 'block'; b.textContent = 'เกิดข้อผิดพลาด — แคปหน้าจอนี้ส่งให้ทีม data ได้เลย\n' + ERRS.slice(-4).join('\n'); }
}
window.addEventListener('error', e => showErr('page', e));
window.addEventListener('unhandledrejection', e => showErr('promise', e));
