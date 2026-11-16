/* js/ui/overview.js — Overview panel: headline numbers for the selected period · where the fleet spends time · about the data
   provides: renderOverview() */

function renderOverview() {
  const el = $('#p-overview');
  const tot = D.vehicles.vin.reduce((n, _, v) => n + (vehPass(v) ? 1 : 0), 0);
  const vc = EXC_BY_V.size;
  const arr = PROV.map((p, i) => [i, AREA.hrsP[i]]).filter(x => x[1] > 0).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const m = D.meta, c = m.clean || {};
  el.innerHTML = `
    <section class="sec lt-card" id="ltCard" ${SIM.on || SIM.done ? '' : 'hidden'}></section>
    <section class="sec">
      <div class="sec-h"><h3>Selected period</h3><span class="num muted">${fDT(S.a)} – ${fDT(S.b)}</span></div>
      <div class="stats">
        ${stat('Active vehicles', fmt(AREA.active), `of ${fmt(tot)} in the fleet`)}
        ${stat('Time on trip', pct(AREA.util), 'share of online time')}
        <button type="button" class="stat alert" id="ovViol"><span class="k">Left the zone</span><span class="v num">${fmt(vc)}</span>
          <span class="s">${pct(vc / Math.max(1, AREA.active))} of active · ${esc(CFG.ZONES[S.zone].label)}</span></button>
        ${stat('No GPS in period', fmt(tot - AREA.active), 'vehicles without any point')}
      </div>
    </section>
    <section class="sec">
      <div class="sec-h"><h3>Where the fleet spends time</h3><span class="muted">hours online · click to filter</span></div>
      <div class="bars" id="ovProv"></div>
    </section>
    <section class="sec ask-card">
      <div class="sec-h"><h3>${ICON.spark} Ask the assistant</h3></div>
      <div class="chips" id="ovAsk">${ASK_EXAMPLES.slice(0, 4).map(q => `<button type="button" class="chip">${esc(q)}</button>`).join('')}</div>
    </section>
    <details class="sec about">
      <summary>About this data</summary>
      <p>Pulled from <b>${esc(m.source || '–')}</b>, ${esc(m.pulled_from || '')} – ${esc(m.pulled_to || '')}.
        ${fmt(c.raw_rows)} raw rows → <b class="num">${fmt(c.clean_points)}</b> usable GPS points.</p>
      <p>Removed: ${fmt(c.repeated_rows)} repeated rows (the API re-sends old points) · ${fmt(c.stale_points)} stale points ·
        ${fmt(c.future_clock_rows)} rows with a wrong (future) clock. ${fmt(c.signal_v_points)} points have no GPS fix — shown on the map
        but not counted as out of zone.</p>
      <p>Vehicles are keyed by <b>VIN</b> (car_id repeats across centers). Plates shared by two vehicles show the last 5 VIN characters.</p>
      <p>Addresses saved in this browser: <span class="num" id="geoN">${fmt(Geo.size())}</span>
        <button type="button" class="link" id="geoClear">Clear</button></p>
    </details>`;
  barsInto($('#ovProv'), arr.map(([i, h]) => ({ key: 'p:' + i, name: provName(i), val: h, txt: fmt(h) + ' h' })));
  $('#ovViol').onclick = () => openPanel('zone');
  renderLiveTestCard();
  $$('#ovAsk .chip').forEach(b => b.onclick = () => Chat.open(b.textContent));
  $('#geoClear').onclick = () => { Geo.clear(); $('#geoN').textContent = '0'; };
}

/* live test results — predictions made with data up to then, checked against what really happened */
function renderLiveTestCard() {
  const el = $('#ltCard'); if (!el) return;
  el.hidden = !(SIM.on || SIM.done);
  if (el.hidden) return;
  const s = ltSummary(), km = x => isFinite(x) ? fmt1(x) + ' km' : '–', pc = (a, b) => b ? Math.round(a / b * 100) + '%' : '–';
  const prog = Math.min(1, (D.meta.tmax - SIM.h0) / 3600);
  el.innerHTML = `
    <div class="sec-h"><h3>Live test · last hour</h3><span class="muted">${SIM.done ? 'finished' : `${Math.round(prog * 60)} / 60 min arrived`}</span></div>
    <div class="progress lt-prog"><i style="width:${(prog * 100).toFixed(1)}%"></i></div>
    <p class="hint">Every 15 min of data the app predicts each moving car using only what has arrived; when the real data comes in it is scored.
      ${s.rounds} rounds · ${fmt(s.predictions)} predictions (${fmt(s.byKind.estimate)} destination estimates · ${fmt(s.byKind.direction)} direction only) · ${fmt(s.judged)} checked so far.</p>
    <table class="tbl lt-tbl"><thead><tr><th>Where is the car 15 min later?</th><th class="r">median error</th></tr></thead><tbody>
      <tr><td>It stays where it is (baseline)</td><td class="r num">${km(s.stay)}</td></tr>
      <tr><td>It keeps going straight at its speed</td><td class="r num">${km(s.straight)}</td></tr>
      <tr><td>It heads to the estimated destination<small class="muted">same cars, baseline ${km(s.towardStay)}</small></td><td class="r num">${km(s.toward)}</td></tr>
    </tbody></table>
    <div class="stats" style="margin-top:10px">
      ${stat('Direction right', pc(s.dirOk, s.dirN), `${fmt(s.dirOk)} of ${fmt(s.dirN)} that moved ≥ 300 m went within ±45° of the predicted way`)}
      ${stat('Destination reached', pc(s.estReached, s.estN), `${fmt(s.estReached)} of ${fmt(s.estN)} estimates came within 500 m · median closest ${km(s.estClosest)}`)}
    </div>
    <button type="button" class="btn sm" id="ltCsv" style="margin-top:10px">${ICON.download} Predictions CSV</button>`;
  $('#ltCsv').onclick = downloadLiveTestCSV;
}
