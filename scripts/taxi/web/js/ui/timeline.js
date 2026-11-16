/* js/ui/timeline.js — bottom timeline: activity chart · drag to pick a period · cursor · playback · day presets
   uses: fleet.js · actions.js
   provides: buildTimelineBins() · drawTimeline() · initTimeline() · setPlaying() · syncPresets() · BIN */

let TLBINS = null; const BIN = 600;
function buildTimelineBins() {
  const nb = Math.ceil((D.meta.tmax + 1) / BIN);
  const on = new Uint16Array(nb), hi = new Uint16Array(nb);
  for (let v = 0; v < NV; v++) {
    if (!vehPass(v)) continue;
    const s = D.vehicles.start[v], e = s + D.vehicles.count[v];
    let lb = -1, lbh = -1;
    for (let i = s; i < e; i++) {
      if (!MASK[i]) continue;
      const b = Math.floor(TT[i] / BIN);
      if (b !== lb) { on[b]++; lb = b; }
      if (FLG[i] & 1 && b !== lbh) { hi[b]++; lbh = b; }
    }
  }
  TLBINS = { nb, on, hi };
}
const tl = { cv: null, ctx: null, w: 0, h: 0, pad: 8, drag: null };
function tlX(t) { return tl.pad + (t / D.meta.tmax) * (tl.w - 2 * tl.pad); }
function tlT(x) { return Math.max(0, Math.min(D.meta.tmax, (x - tl.pad) / (tl.w - 2 * tl.pad) * D.meta.tmax)); }
function drawTimeline() {
  const cv = tl.cv; if (!cv || !TLBINS) return;
  const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  if (!w) return;
  if (cv.width !== w * dpr || cv.height !== h * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
  tl.w = w; tl.h = h;
  const c = tl.ctx; c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, w, h);
  const top = 4, bot = h - 16, ch = bot - top;
  c.fillStyle = 'rgba(0,163,50,.08)';                               // selected period
  c.fillRect(tlX(S.a), top, tlX(S.b) - tlX(S.a), ch);
  // day lines + hour labels
  c.font = '10px "IBM Plex Mono", monospace'; c.lineWidth = 1;
  const d0 = tDate(0), firstH = new Date(d0); firstH.setMinutes(0, 0, 0); firstH.setHours(firstH.getHours() + 1);
  const stepH = w < 520 ? 12 : w < 900 ? 6 : 3;
  for (let ms = firstH.getTime(); ms <= t0ms + D.meta.tmax * 1000; ms += 3600 * 1000) {
    const t = (ms - t0ms) / 1000, x = tlX(t), dd = new Date(ms);
    if (dd.getHours() === 0) {
      c.beginPath(); c.moveTo(x + .5, top); c.lineTo(x + .5, bot); c.strokeStyle = '#b9c4be'; c.stroke();
      c.fillStyle = '#3c4c44'; c.fillText(`${dd.getDate()} ${MON[dd.getMonth()]}`, x + 3, h - 4);
    } else if (dd.getHours() % stepH === 0) {
      c.fillStyle = '#7d8b84'; c.fillText(p2(dd.getHours()) + ':00', x - 14, h - 4);
    }
  }
  // chart: online (grey-green) · on trip (blue)
  const B = TLBINS; let mx = 1; for (let i = 0; i < B.nb; i++) mx = Math.max(mx, B.on[i]);
  const bw = (tl.w - 2 * tl.pad) / B.nb;
  for (let i = 0; i < B.nb; i++) {
    const x = tl.pad + i * bw, ho = B.on[i] / mx * ch, hh = B.hi[i] / mx * ch;
    const inR = (i + 1) * BIN >= S.a && i * BIN <= S.b;
    c.fillStyle = inR ? '#b9d8c3' : '#dde5e0'; c.fillRect(x, bot - ho, Math.max(1, bw - 0.6), ho);
    c.fillStyle = inR ? '#f08c00' : '#f6cf99'; c.fillRect(x, bot - hh, Math.max(1, bw - 0.6), hh);
  }
  c.fillStyle = '#4a5a52'; c.font = '10px "IBM Plex Sans Thai", sans-serif';
  c.fillText(`peak ${mx.toLocaleString('en-US')} online per 10 min`, tl.pad + 2, top + 10);
  c.fillStyle = '#00a332';                                          // period edges
  for (const t of [S.a, S.b]) { const x = tlX(t); c.fillRect(x - 1, top, 2, ch); }
  const x = tlX(S.T);                                               // cursor
  c.fillStyle = '#10231a'; c.fillRect(x - 1, 0, 2, bot);
  c.beginPath(); c.moveTo(x - 6, 0); c.lineTo(x + 6, 0); c.lineTo(x, 7); c.closePath(); c.fill();
}
let PRESETS = [];
/* presets: whole data + one per calendar day */
function buildPresets() {
  PRESETS = [['All', 0, D.meta.tmax]];
  const seen = new Map();
  for (let t = 0; t <= D.meta.tmax; t += 300) {
    const k = fDay(t);
    if (!seen.has(k)) seen.set(k, [t, t]); else seen.get(k)[1] = t;
  }
  for (const [, [a, b]] of seen) PRESETS.push([fDayShort(a), a, Math.min(b + 299, D.meta.tmax)]);
  $('#presets').innerHTML = PRESETS.map((p, i) => `<button type="button" data-v="${i}" aria-pressed="${i === 0}">${p[0]}</button>`).join('');
  seg($('#presets'), v => { const p = PRESETS[+v]; S.a = p[1]; S.b = p[2]; S.T = Math.max(S.a, Math.min(S.b, S.T)); refresh('range'); setT(S.T); });
}
function initTimeline() {
  tl.cv = $('#tlc'); tl.ctx = tl.cv.getContext('2d');
  buildPresets();
  $('#play').innerHTML = ICON.play;
  $('#speed').value = String(S.speed);
  $('#play').onclick = () => setPlaying(!S.playing);
  $('#liveBtn').onclick = goLive;
  $('#tlClose').innerHTML = ICON.x;
  $('#tlClose').onclick = goLive;
  $('#speed').onchange = e => { S.speed = +e.target.value; };

  const pos = e => e.clientX - tl.cv.getBoundingClientRect().left;
  tl.cv.addEventListener('pointerdown', e => {
    const x = pos(e); tl.cv.setPointerCapture(e.pointerId);
    if (Math.abs(x - tlX(S.T)) < 8) tl.drag = { k: 'head' };
    else if (Math.abs(x - tlX(S.a)) < 6) tl.drag = { k: 'a' };
    else if (Math.abs(x - tlX(S.b)) < 6) tl.drag = { k: 'b' };
    else tl.drag = { k: 'brush', x0: x, moved: false };
  });
  tl.cv.addEventListener('pointermove', e => {
    const x = pos(e);
    if (!tl.drag) {
      tl.cv.style.cursor = Math.abs(x - tlX(S.T)) < 8 ? 'ew-resize' : (Math.abs(x - tlX(S.a)) < 6 || Math.abs(x - tlX(S.b)) < 6) ? 'col-resize' : 'crosshair';
      return;
    }
    const t = tlT(x);
    if (tl.drag.k === 'head') setT(Math.max(S.a, Math.min(S.b, t)));
    else if (tl.drag.k === 'a') { S.a = Math.min(t, S.b - 600); S.T = Math.max(S.T, S.a); drawTimeline(); }
    else if (tl.drag.k === 'b') { S.b = Math.max(t, S.a + 600); S.T = Math.min(S.T, S.b); drawTimeline(); }
    else if (Math.abs(x - tl.drag.x0) > 4) {
      tl.drag.moved = true; const t0 = tlT(tl.drag.x0);
      S.a = Math.min(t0, t); S.b = Math.max(t0, t); S.T = Math.max(S.a, Math.min(S.b, S.T)); drawTimeline();
    }
  });
  const end = e => {
    if (!tl.drag) return;
    const k = tl.drag; tl.drag = null;
    if (k.k === 'brush' && !k.moved) {                               // plain click = move the cursor
      const t = tlT(pos(e));
      if (t < S.a || t > S.b) { S.a = 0; S.b = D.meta.tmax; refresh('range'); }
      setT(t); return;
    }
    if (k.k !== 'head') refresh('range');
  };
  tl.cv.addEventListener('pointerup', end);
  tl.cv.addEventListener('pointercancel', end);
  window.addEventListener('resize', rafThrottle(() => { drawTimeline(); if (S.sel >= 0) drawSpark(S.sel); }));
}
/* highlight the preset that matches the period exactly (none after a custom drag) */
function syncPresets() {
  const i = PRESETS.findIndex(p => Math.abs(p[1] - S.a) < 1 && Math.abs(p[2] - S.b) < 1);
  $$('#presets button').forEach((b, k) => b.setAttribute('aria-pressed', String(k === i)));
  $('#rngTxt').textContent = i >= 0 ? '' : `${fDT(S.a)} – ${fDT(S.b)}`;
}
let raf = 0, lastTs = 0;
function loop(ts) {
  if (!S.playing) return;
  const dt = lastTs ? (ts - lastTs) / 1000 : 0; lastTs = ts;
  let t = S.T + dt * S.speed;
  if (t > S.b) t = S.a;
  setT(t);
  raf = requestAnimationFrame(loop);
}
function setPlaying(on) {
  S.playing = on;
  $('#play').innerHTML = on ? ICON.pause : ICON.play;
  $('#play').setAttribute('aria-label', on ? 'Pause' : 'Play');
  syncLive();
  lastTs = 0; if (on) raf = requestAnimationFrame(loop); else cancelAnimationFrame(raf);
  if (!on && D) render();                                          // paused: the planned route can be fetched now
}
