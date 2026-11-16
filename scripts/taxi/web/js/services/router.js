/* js/services/router.js — roads for the selected car (OSRM · OpenStreetMap)
     get(a, b)   driving route from a to b (the dashed "next leg")
     track(v)    the car's GPS points snapped to roads: routed through its moving points in order
                 (OSRM's map-matching allows only 10 points per request on the demo server; routing through
                 100 waypoints per request gives the same result for points 4–5 minutes apart)
   Only coordinates are sent — no plate, no vehicle id. The public OSRM demo server is for light use:
   one request at a time, ≥ 1.1 s apart, results cached, only for the selected vehicle.
   For production point CFG2.ROUTER at your own OSRM (…/route/v1/driving/).
   uses: config.js (CFG2.ROUTER)
   provides: Router */

const Router = {
  cache: new Map(), tracks: new Map(), q: [], busy: false, failUntil: 0,
  key(a, b) { return [a.lon, a.lat, b.lon, b.lat].map(x => x.toFixed(3)).join(','); },
  peek(a, b) { return this.cache.get(this.key(a, b)) || null; },

  /* one request at a time — newest first (the cursor may have moved on), stale ones dropped */
  fetchJSON(url, keep = false) {
    if (Date.now() < this.failUntil) return Promise.resolve(null);
    let done; const p = new Promise(ok => { done = ok; });
    this.q.push({ url, done, keep });
    this.pump();
    return p;
  },
  async pump() {
    if (this.busy) return; this.busy = true;
    while (this.q.length) {
      const job = this.q.pop();
      // keep track chunks and the 2 newest route requests; older route requests answer null (cursor moved on)
      const others = this.q.filter(j => !j.keep), drop = others.slice(0, Math.max(0, others.length - 2));
      drop.forEach(j => j.done(null));
      this.q = this.q.filter(j => !drop.includes(j));
      let j = null;
      try {
        const res = await fetch(job.url);
        if (res.status === 429) this.failUntil = Date.now() + 60000;
        j = res.ok ? await res.json() : null;
      } catch (e) { this.failUntil = Date.now() + 30000; }
      job.done(j && j.code === 'Ok' ? j : null);
      await new Promise(ok => setTimeout(ok, 1100));
    }
    this.busy = false;
  },

  /* resolves with { path: [[lon, lat], …], km, min } or null (no route / service down → caller draws a straight line) */
  get(a, b) {
    const k = this.key(a, b);
    if (this.cache.has(k)) return Promise.resolve(this.cache.get(k));
    if (this._wait && this._wait[k]) return this._wait[k];
    this._wait = this._wait || {};
    const p = this.fetchJSON(`${CFG2.ROUTER}${a.lon},${a.lat};${b.lon},${b.lat}?overview=full&geometries=geojson`).then(j => {
      const rt = j && j.routes && j.routes[0];
      const r = rt ? { path: rt.geometry.coordinates, km: rt.distance / 1000, min: rt.duration / 60 } : null;
      this.cache.set(k, r); delete this._wait[k];
      return r;
    });
    return (this._wait[k] = p);
  },

  /* the whole GPS trace of vehicle v snapped to roads
     → { kept: [raw index…], legs: Map(raw index a → { b, path, cum, km }) } — legs connect consecutive kept points */
  track(v) {
    const st = this.tracks.get(v);
    if (st) return st.p;
    const s0 = D.vehicles.start[v], e0 = s0 + D.vehicles.count[v], kept = [];
    for (let i = s0; i < e0; i++) {                    // moving points only — parked jitter would make U-turn detours
      if (FLG[i] & 2) continue;
      const k = kept[kept.length - 1];
      if (k == null || hav(POS[2 * k], POS[2 * k + 1], POS[2 * i], POS[2 * i + 1]) >= 0.06) kept.push(i);
    }
    const res = { kept, legs: new Map(), done: false };
    const chunks = [];
    for (let c = 0; c < kept.length - 1; c += 99) chunks.push(kept.slice(c, c + 100));
    const p = (async () => {
      for (const ch of chunks) {
        const coords = ch.map(i => `${POS[2 * i].toFixed(6)},${POS[2 * i + 1].toFixed(6)}`).join(';');
        const j = await this.fetchJSON(`${CFG2.ROUTER}${coords}?overview=false&steps=true&geometries=geojson&continue_straight=false`, true);
        const rt = j && j.routes && j.routes[0];
        if (!rt) continue;                             // that chunk stays straight
        rt.legs.forEach((leg, l) => {
          const a = ch[l], b = ch[l + 1], path = [];
          for (const stp of leg.steps) for (const c of stp.geometry.coordinates) {
            const q = path[path.length - 1];
            if (!q || q[0] !== c[0] || q[1] !== c[1]) path.push(c);
          }
          if (path.length < 2) return;
          // a leg much longer than the straight line = the point was snapped to the wrong road → keep it straight
          const direct = hav(POS[2 * a], POS[2 * a + 1], POS[2 * b], POS[2 * b + 1]);
          if (leg.distance / 1000 > 3 * direct + 1) return;
          path[0] = [POS[2 * a], POS[2 * a + 1]]; path.push([POS[2 * b], POS[2 * b + 1]]);   // start / end at the GPS points
          const cum = [0];
          for (let k = 1; k < path.length; k++) cum.push(cum[k - 1] + hav(path[k - 1][0], path[k - 1][1], path[k][0], path[k][1]));
          res.legs.set(a, { b, path, cum, km: cum[cum.length - 1] });
        });
      }
      res.done = true;
      return res;
    })();
    this.tracks.set(v, { p, res });
    return p;
  },
  trackPeek(v) { const st = this.tracks.get(v); return st && st.res.done ? st.res : null; },
};
