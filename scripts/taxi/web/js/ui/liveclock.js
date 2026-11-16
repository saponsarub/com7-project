/* js/ui/liveclock.js — LIVE runs on a clock
   The GPS provider sends every car's position in one batch every 5 min. Pinning Live to the newest point froze the
   picture between batches (and for good on a file:// snapshot). Live instead plays CFG.LIVE_LAG_SEC behind the newest
   data at real speed: every car is always between two fixes that have already arrived, so it drives along its road
   leg (data/taxi-roads.js) without stopping, and a car whose new fix arrives heads for it at once. Nothing is guessed
   ahead of the data. When no newer data comes (a fixed snapshot, or the feed is late) the clock reaches the newest
   point and waits there — the map badge says so.
   uses: ui/actions.js (setT · syncLive) · analysis/livetest.js (SIM — the live test runs the clock at its speed)
   provides: LC · liveAnchor() · liveTarget() · liveWaiting() · startLiveClock() */

const LC = { T0: 0, wall0: 0, speed: 1 };
/* the clock shows data time T0 at wall time wall0 and runs at speed (data seconds per real second) */
function liveAnchor(T, speed = SIM.on ? SIM.speed : 1, wall = Date.now()) {
  Object.assign(LC, { T0: Math.max(0, T), wall0: wall, speed });
}
const liveTarget = () => Math.min(D.meta.tmax, LC.T0 + (Date.now() - LC.wall0) / 1000 * LC.speed);
/* live and caught up with the newest data — nothing newer to show yet */
const liveWaiting = () => isLive() && S.T >= D.meta.tmax - 0.5;

function startLiveClock() {
  setInterval(() => {
    if (!isLive() || S.playing || document.hidden) return;
    const t = liveTarget();
    if (t > S.T + 0.05) setT(t, true);
  }, 100);                                   // 10 steps a second — drawing is held to one per frame anyway
}
