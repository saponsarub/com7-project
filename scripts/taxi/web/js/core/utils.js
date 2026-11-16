/* js/core/utils.js — small helpers: number/date formatting · distance · DOM · storage
   uses: t0ms (state.js)
   provides: $ · $$ · fmt · fmt1 · pct · fDay · fHM · fHMS · fDT · fDur · fISO · hav · rgba · hexRgb · esc · seg · store · rafThrottle · idle */

const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const fmt = n => n == null || isNaN(n) ? '–' : Math.round(n).toLocaleString('en-US');
const fmt1 = n => n == null || isNaN(n) ? '–' : n.toLocaleString('en-US', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const pct = x => x == null || isNaN(x) ? '–' : (x * 100).toFixed(0) + '%';
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function tDate(t) { return new Date(t0ms + t * 1000); }
const p2 = n => String(n).padStart(2, '0');
function fDay(t) { const d = tDate(t); return `${d.getDate()} ${MON[d.getMonth()]} ${d.getFullYear()}`; }
function fDayShort(t) { const d = tDate(t); return `${d.getDate()} ${MON[d.getMonth()]}`; }
function fHM(t) { const d = tDate(t); return p2(d.getHours()) + ':' + p2(d.getMinutes()); }
function fHMS(t) { const d = tDate(t); return fHM(t) + ':' + p2(d.getSeconds()); }
function fDT(t) { return `${fDayShort(t)} ${fHM(t)}`; }
function fISO(t) { const d = tDate(t); return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${fHM(t)}`; }
function fDur(sec) {
  const m = Math.round(sec / 60); if (m < 60) return m + ' min';
  const h = Math.floor(m / 60); return h + ' h' + (m % 60 ? ' ' + (m % 60) + ' min' : '');
}
function hav(lon1, lat1, lon2, lat2) {
  const r = Math.PI / 180, a = Math.sin((lat2 - lat1) * r / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin((lon2 - lon1) * r / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(a));
}
function rgba(c, a) { return [c[0], c[1], c[2], a]; }
function hexRgb(h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }
// anything that did not come from our own code (OSM names, user input, AI answers) must be escaped
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
/* segmented control: <div class="seg"><button data-v=…> */
function seg(el, fn) {
  el.querySelectorAll('button').forEach(b => b.onclick = () => {
    setSeg(el, b.dataset.v);
    fn(b.dataset.v, b);
  });
}
function setSeg(el, v) { el.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x.dataset.v === String(v))); }
const store = {     // localStorage may be disabled (private mode) — always wrapped
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } },
  set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { /* ignore */ } },
};
/* run fn at most once per animation frame (timeline drag, playback) */
function rafThrottle(fn) {
  let queued = false, args = null;
  return (...a) => { args = a; if (queued) return; queued = true; requestAnimationFrame(() => { queued = false; fn(...args); }); };
}
const idle = fn => (window.requestIdleCallback ? requestIdleCallback(fn, { timeout: 1500 }) : setTimeout(fn, 60));
const nextFrame = () => new Promise(ok => requestAnimationFrame(() => setTimeout(ok, 0)));
