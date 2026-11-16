/* js/ui/place.js — place card over the map (address from OpenStreetMap · links to Street View / Google Maps)
   uses: geocode.js
   provides: PLACE · showPlace() · hidePlace() */

let PLACE = null;
function showPlace(lat, lon, title, sub) {
  PLACE = { lat, lon };
  const el = $('#place');
  const sv = `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lon}`;
  const gm = `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;
  const osm = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=18/${lat}/${lon}`;
  el.innerHTML = `<div class="ph"><div><b>${esc(title)}</b><small>${sub ? esc(sub) + ' · ' : ''}<span class="num">${lat.toFixed(5)}, ${lon.toFixed(5)}</span></small></div>
      <button class="icon-btn" id="plX" aria-label="Close">${ICON.x}</button></div>
    <div class="addr" id="plAddr"><span class="muted">Looking up the address…</span></div>
    <div class="links"><a class="pri" href="${sv}" target="_blank" rel="noopener">Street View</a>
      <a href="${gm}" target="_blank" rel="noopener">Google Maps</a>
      <a href="${osm}" target="_blank" rel="noopener">OpenStreetMap</a></div>`;
  el.hidden = false;
  $('#plX').onclick = hidePlace;
  const same = () => PLACE && PLACE.lat === lat && PLACE.lon === lon;
  Geo.get(lat, lon).then(r => {
    if (!same()) return;
    $('#plAddr').innerHTML = r.err ? `<span class="muted">${esc(r.line)}</span>` : `${r.name ? `<b>${esc(r.name)}</b><br>` : ''}${esc(r.full)}`;
  });
  render();
}
function hidePlace() { $('#place').hidden = true; PLACE = null; render(); }
