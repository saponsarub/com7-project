/* js/services/geocode.js — coordinates → address via OpenStreetMap Nominatim (max 1 request/s · cached in the browser)
   uses: utils.js (store)
   provides: PLACES · Geo · fmtAddr()
   ⚠️ results are text from the internet — always esc() before putting them in HTML

   Nominatim rules: at most 1 request per second, no bulk lookups.
   So only points the user clicks are looked up; depot addresses are fetched at build time (PLACES). */

const PLACES = (EMBEDDED && EMBEDDED.places) || [];
const GEO_BLOCK = 'OpenStreetMap is rate-limiting this network for a while — try again later, or use the Google Maps link.';
const Geo = {
  cache: {}, q: [], busy: false, wait: {}, blockedUntil: 0,
  init() { try { this.cache = JSON.parse(store.get('ev7.geo', '{}')) || {}; } catch (e) { this.cache = {}; } },
  save() { store.set('ev7.geo', JSON.stringify(this.cache)); },
  clear() { this.cache = {}; this.save(); },
  size() { return Object.keys(this.cache).length; },
  key(lat, lon) { return lat.toFixed(4) + ',' + lon.toFixed(4); },
  peek(lat, lon) {
    const c = this.cache[this.key(lat, lon)]; if (c) return c;
    for (const p of PLACES) if (hav(lon, lat, p.lon, p.lat) <= 0.05) return p;
    return null;
  },
  get(lat, lon) {
    const k = this.key(lat, lon), have = this.peek(lat, lon);
    if (have) return Promise.resolve(have);
    if (Date.now() < this.blockedUntil) return Promise.resolve({ err: true, line: GEO_BLOCK });
    if (!this.wait[k]) { this.wait[k] = []; this.q.push({ k, lat, lon }); this.pump(); }
    return new Promise(res => this.wait[k].push(res));
  },
  async pump() {
    if (this.busy) return; this.busy = true;
    while (this.q.length) {
      const { k, lat, lon } = this.q.shift();
      let r;
      try {
        const u = `${CFG2.NOMINATIM}?format=jsonv2&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1&accept-language=en,th`;
        const res = await fetch(u);
        if (res.status === 429 || res.status === 403) {
          this.blockedUntil = Date.now() + 10 * 60 * 1000;
          r = { err: true, line: GEO_BLOCK };
          for (const x of this.q) { (this.wait[x.k] || []).forEach(f => f(r)); delete this.wait[x.k]; }
          this.q = [];
        } else {
          const j = await res.json();
          r = j && !j.error ? fmtAddr(j) : { err: true, line: 'No address found here.' };
        }
      } catch (e) { r = { err: true, line: 'Could not look up the address — offline or blocked.' }; }
      if (!r.err) { this.cache[k] = r; this.save(); }
      (this.wait[k] || []).forEach(f => f(r)); delete this.wait[k];
      await new Promise(ok => setTimeout(ok, 1100));
    }
    this.busy = false;
  },
};
function fmtAddr(j) {
  const a = j.address || {};
  const name = j.name || a.amenity || a.shop || a.building || a.tourism || '';
  const road = a.road || a.pedestrian || a.residential || '';
  const area = a.city || a.town || a.village || a.suburb || a.quarter || '';
  const short = [name, road, area].filter(Boolean).filter((x, i, arr) => arr.indexOf(x) === i).join(' · ');
  return { name, short: short || (j.display_name || '').split(',').slice(0, 2).join(','), full: j.display_name || '' };
}
