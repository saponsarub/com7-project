/* js/data/source.js — load and decode the data (base64 → gzip → typed arrays) · future API hook
   uses: window.TAXI_DATA (data/taxi-data.js, written by build_dashboard.py)
   provides: EMBEDDED · DataSource · decodeEmbedded()

   Now:    data embedded in data/taxi-data.js (a .js file, not .json, because fetch() of local
           files is blocked when the page is opened from file://)
   Later:  an API that returns the same structure, then set DataSource.mode = 'api'
     GET {base}/meta?from&to        -> { meta, vehicles, areas, dtype }
     GET {base}/cols/{name}?from&to -> binary (gzip) per dtype
     GET {base}/geo/{prov|dist}     -> GeoJSON (gzip)                                              */

const EMBEDDED = window.TAXI_DATA || null;
const DataSource = {
  mode: 'embedded',
  base: '',
  async load(progress) {
    if (this.mode === 'embedded') return decodeEmbedded(EMBEDDED, progress);
    throw new Error('API data source is not connected yet — see the comment in js/data/source.js');
  },
};

/* live updates — the server (or a scheduled build) rewrites data/taxi-data.js; the page checks its Last-Modified / ETag
   every CFG.REFRESH_SEC and reloads it when it changed. Opened from file:// (or the single-file bundle) = fixed snapshot. */
DataSource.canWatch = () => /^https?:$/.test(location.protocol) && !!document.querySelector('script[src^="data/taxi-data.js"]');
DataSource.reload = function () {
  return new Promise((ok, fail) => {
    const s = document.createElement('script');
    s.src = 'data/taxi-data.js?t=' + Date.now();
    s.onload = () => { s.remove(); decodeEmbedded(window.TAXI_DATA, () => {}).then(ok, fail); };
    s.onerror = () => { s.remove(); fail(new Error('could not reload data/taxi-data.js')); };
    document.head.appendChild(s);
  });
};
DataSource.watch = function (onNew) {
  if (!this.canWatch()) return false;
  let tag = null;
  const check = async () => {
    try {
      const r = await fetch('data/taxi-data.js', { method: 'HEAD', cache: 'no-store' });
      const t = r.headers.get('etag') || r.headers.get('last-modified');
      if (t && tag && t !== tag) onNew(await this.reload());
      if (t) tag = t;
    } catch (e) { /* offline for a moment — try again next round */ }
    setTimeout(check, CFG.REFRESH_SEC * 1000);
  };
  check();
  return true;
};

async function b64gunzip(b64) {
  const blob = await (await fetch('data:application/octet-stream;base64,' + b64)).blob();
  const ds = blob.stream().pipeThrough(new DecompressionStream('gzip'));
  return await new Response(ds).arrayBuffer();
}
const TYPED = { u8: Uint8Array, u16: Uint16Array, f32: Float32Array };

async function decodeEmbedded(E, progress) {
  if (!E) throw new Error('No data found (data/taxi-data.js). Build it with: python scripts/taxi/build_dashboard.py --web <folder>');
  const names = Object.keys(E.cols);
  let done = 0;
  const step = () => progress(++done / (names.length + 2));
  // all columns decode in parallel — the browser streams the gzip work off the main thread
  const cols = {};
  const dec = new TextDecoder();
  await Promise.all([
    ...names.map(async n => { cols[n] = new TYPED[E.dtype[n]](await b64gunzip(E.cols[n])); step(); }),
    (async () => { E._prov = JSON.parse(dec.decode(await b64gunzip(E.geo.prov))); step(); })(),
    (async () => { E._dist = JSON.parse(dec.decode(await b64gunzip(E.geo.dist))); step(); })(),
  ]);
  return { meta: E.meta, vehicles: E.vehicles, areas: E.areas, cols, geo: { prov: E._prov, dist: E._dist } };
}
