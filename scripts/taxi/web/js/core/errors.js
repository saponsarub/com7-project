/* js/core/errors.js — show errors on screen (small red box over the map) + catch page-wide errors
   provides: ERRS · showErr() */

const ERRS = [];
function showErr(where, e) {
  const m = `[${where}] ${(e && (e.message || e.reason && e.reason.message || e.error && e.error.message)) || e}`;
  ERRS.push(m); console.error(where, e);
  const b = document.getElementById('errbox');
  if (!b) return;
  b.hidden = false;
  b.querySelector('pre').textContent = ERRS.slice(-4).join('\n');
}
window.addEventListener('error', e => { if (e.message) showErr('page', e); });
window.addEventListener('unhandledrejection', e => showErr('promise', e));
