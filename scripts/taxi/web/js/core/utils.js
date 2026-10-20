/* js/core/utils.js — ฟังก์ชันช่วยทั่วไป — จัดรูปแบบตัวเลข/วันเวลา · ระยะทาง · DOM · localStorage
   ใช้: t0ms (state)
   ให้: $ · fmt · fmt1 · pct · fDay · fHM · fDT · fDur · hav · rgba · hexRgb · seg · store
   ⚠️ ไฟล์ทั้งหมดใช้ scope ร่วมกัน (classic script ไม่ใช่ ES module) เพื่อให้เปิดจาก file:// ได้
      ลำดับการโหลดอยู่ใน index.html — ไฟล์ที่ประกาศก่อนต้องโหลดก่อน */

const $ = s => document.querySelector(s);
const fmt = n => n == null || isNaN(n) ? '–' : Math.round(n).toLocaleString('th-TH');
const fmt1 = n => n == null || isNaN(n) ? '–' : n.toLocaleString('th-TH', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const pct = x => isNaN(x) ? '–' : (x * 100).toFixed(0) + '%';
const TH_MON = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
function tDate(t) { return new Date(t0ms + t * 1000); }
function fDay(t) { const d = tDate(t); return `${d.getDate()} ${TH_MON[d.getMonth()]} ${d.getFullYear() + 543}`; }
function fHM(t) { const d = tDate(t); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); }
function fDT(t) { const d = tDate(t); return `${d.getDate()} ${TH_MON[d.getMonth()]} ${fHM(t)}`; }
function fDur(sec) { const m = Math.round(sec / 60); if (m < 60) return m + ' นาที'; const h = Math.floor(m / 60); return h + ' ชม.' + (m % 60 ? ' ' + (m % 60) + ' น.' : ''); }
function hav(lon1, lat1, lon2, lat2) {
  const r = Math.PI / 180, a = Math.sin((lat2 - lat1) * r / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin((lon2 - lon1) * r / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(a));
}
function rgba(c, a) { return [c[0], c[1], c[2], a]; }
function hexRgb(h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }
// ข้อความจากภายนอก (เช่น ชื่อสถานีใน OSM) ต้อง escape ก่อนใส่ใน tooltip ที่เป็น HTML
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function seg(el, fn) {
  el.querySelectorAll('button').forEach(b => b.onclick = () => {
    el.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
    fn(b.dataset.v, b);
  });
}
const store = {     // localStorage อาจถูกปิด (private mode) — ห่อ try ทุกครั้ง
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } },
  set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { /* ไม่เป็นไร */ } },
};
