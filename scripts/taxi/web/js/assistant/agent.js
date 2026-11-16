/* js/assistant/agent.js — answers questions: offline (rules, in the browser) or AI agent (server proxy → Claude)
   AI mode: the server holds the API key and only relays messages; every tool runs here in the browser
   (runTool), and plates in the question are replaced by [[car:<id>]] before anything is sent.
   uses: nlu.js · tools.js · config.js (AI)
   provides: Agent */

const Agent = {
  mode: 'offline', endpoint: null, ctx: { lastV: -1 }, history: [],

  /* AI mode only when an endpoint is configured, or the page is served by our server and /api/health says so */
  async detect() {
    let ep = AI.endpoint;
    if (!ep && /^https?:$/.test(location.protocol)) {
      try {
        const r = await fetchTimeout(AI.health, {}, 3000);
        const j = r.ok ? await r.json() : null;
        if (j && j.ai) ep = j.endpoint || '/api/agent';
      } catch (e) { /* no server → offline */ }
    }
    this.endpoint = ep || null;
    this.mode = ep ? 'ai' : 'offline';
    return this.mode;
  },
  reset() { this.history = []; this.ctx = { lastV: -1 }; },

  async ask(q) {
    if (this.mode === 'ai') {
      try { return await this.askRemote(q); }
      catch (e) {
        const off = this.askOffline(q);
        return { text: off.text, note: `AI agent unavailable (${e.message}) — answered offline.` };
      }
    }
    return this.askOffline(q);
  },

  /* ── offline: rules → tool → sentence ─────────────────────────────── */
  askOffline(q) {
    const P = NLU.parse(q, { lastV: S.sel >= 0 ? S.sel : this.ctx.lastV });
    const th = P.lang === 'th', L = (en, t) => th ? t : en;
    const carIn = P.v >= 0 ? P.v : null;
    const carErr = r => ({ text: `[[${r.car}]] ` + (th ? (/before/.test(r.error) ? 'ไม่มีข้อมูล GPS ก่อนเวลาที่ถาม' : 'ไม่มีจุด GPS ในช่วงเวลานั้น') : r.error) });
    if (P.plate && P.v < 0 && ['car_status', 'car_track', 'nearest_charger'].includes(P.intent))
      return { text: L(`I can't find a vehicle with plate **${P.plate.raw}** in this data.`, `ไม่พบรถทะเบียน **${P.plate.raw}** ในข้อมูลชุดนี้` ) };
    if (carIn != null) this.ctx.lastV = carIn;
    let r;
    switch (P.intent) {
      case 'action_request': {
        const base = L('This monitor is **read-only** — it cannot cut power, lock, stop or message a vehicle; use the telematics system.',
          'ระบบนี้**ดูข้อมูลได้อย่างเดียว** — สั่งตัดไฟ ล็อก ดับเครื่อง หรือส่งข้อความหารถไม่ได้ ต้องสั่งผ่านระบบ telematics');
        if (carIn == null) return { text: base };
        // a car was named: add the safety check so the operator knows whether a cut is reasonable right now
        r = TOOLS.parking_status({ car: carIn });
        if (r.error) return { text: base };
        const pc = r.power_cut, why = (pc.safe ? pc.cautions : pc.reasons_not_safe).join('; ');
        const stTh = { parked: 'จอด', stopped: 'หยุดชั่วคราว', moving: 'กำลังวิ่ง', offline: 'ออฟไลน์' }[r.state];
        const plTh = { 'EV charger': 'สถานีชาร์จ EV', Depot: 'ลานจอด (depot)', 'Home (usual overnight spot)': 'บ้าน (จุดที่จอดค้างคืนประจำ)', 'Street / other': 'ริมถนน/อื่น ๆ' }[r.place];
        return { text: base + '\n' + L(
          `[[${r.car}]]: ${r.state}${r.state === 'parked' ? ` ${fDur(r.parked_minutes * 60)}` : ''} at **${r.place}** (${r.where}) · engine ${r.engine}. `
            + (pc.safe ? `✅ **Safe to cut power** (${pc.confidence} confidence)` : '⛔ **Not safe to cut power now**') + (why ? ` — ${why}.` : '.'),
          `[[${r.car}]]: ${stTh}${r.state === 'parked' ? ` ${fDur(r.parked_minutes * 60)}` : ''} ที่ **${plTh}** (${r.where}) · เครื่อง ${r.engine === 'off' ? 'ดับ' : r.engine === 'on' ? 'ทำงาน' : 'ไม่ทราบ'} · `
            + (pc.safe ? `✅ **ตัดไฟได้อย่างปลอดภัย** (ความมั่นใจ ${pc.confidence})` : '⛔ **ยังไม่ควรตัดไฟตอนนี้**') + (why ? ` — ${why}` : '')) };
      }
      case 'hello':
        return { text: L('Hi! Ask me about the fleet — for example where a car is, how many cars are in an area, who left the zone, or the nearest EV chargers.',
          'สวัสดีครับ ถามเรื่องรถได้เลย เช่น รถคันนี้อยู่ไหน · พื้นที่นี้มีรถกี่คัน · ใครออกนอกเขต · ที่ชาร์จใกล้ที่สุด') };
      case 'other':
        return { text: L("I can only answer questions about the EV7 taxi fleet: vehicle location and route, vehicles in an area, out-of-zone trips, fleet numbers and EV chargers.",
          'ตอบได้เฉพาะเรื่องรถแท็กซี่ EV7: ตำแหน่ง/เส้นทางรถ · รถในพื้นที่ · รถออกนอกเขต · ภาพรวมรถ · สถานีชาร์จ') };
      case 'data_info': {
        r = TOOLS.data_info();
        return { text: L(`The data covers **${r.from} – ${r.to}**: ${fmt(r.vehicles)} vehicles, ${fmt(r.gps_points)} GPS points. "Now" means the latest point in the data.`,
          `ข้อมูลช่วง **${r.from} – ${r.to}** · รถ ${fmt(r.vehicles)} คัน · จุด GPS ${fmt(r.gps_points)} จุด ("ตอนนี้" = จุดล่าสุดในข้อมูล)`) };
      }
      case 'peak_time': {
        r = TOOLS.peak_time();
        return { text: L(`Most vehicles on a trip at **${r.most_on_trip.time}** (${fmt(r.most_on_trip.vehicles)} vehicles). Most online at ${r.most_online.time} (${fmt(r.most_online.vehicles)}).${r.fewest_online ? ` Quietest: ${r.fewest_online.time} (${fmt(r.fewest_online.vehicles)} online).` : ''} The timeline now points at the busiest time.`,
          `มีผู้โดยสารมากที่สุดช่วง **${r.most_on_trip.time}** (${fmt(r.most_on_trip.vehicles)} คัน) · ออนไลน์มากสุด ${r.most_online.time} (${fmt(r.most_online.vehicles)} คัน)${r.fewest_online ? ` · เงียบสุด ${r.fewest_online.time} (${fmt(r.fewest_online.vehicles)} คัน)` : ''} — เลื่อนไทม์ไลน์ไปช่วงที่มากสุดให้แล้ว`) };
      }
      case 'cars_in_area': {
        r = TOOLS.cars_in_area({ place: P.place, time: P.time.label, status: P.status && ST_OUT[P.status] });
        if (r.error) return { text: r.error };
        const stName = P.status ? STATUS_WORD[P.lang][ST_OUT[P.status]] : '';
        const poi = r.place_kind === 'poi';
        const where = poi ? L(`within ${r.radius_km} km of ${r.place}`, `ในรัศมี ${r.radius_km} กม. รอบ ${r.place}`) : L('in ' + r.place, r.place);
        if (!r.count) return { text: L(`No ${stName ? stName + ' ' : ''}vehicles online ${where} at ${r.as_of}.`, `ไม่มีรถ${stName}ออนไลน์${poi ? '' : 'ใน'} ${where} ณ ${r.as_of}`) };
        return { text: L(`**${fmt(r.count)}** ${stName ? stName + ' ' : ''}vehicles online ${where} at ${r.as_of}`, `${where} มีรถ${stName}ออนไลน์ **${fmt(r.count)}** คัน ณ ${r.as_of}`)
          + (P.status ? '' : ' (' + statusLine(r.by_status, P.lang) + ')') + ':\n' + carList(r.vehicles, P.lang) + more(r.count - Math.min(10, r.vehicles.length), P.lang)
          + '\n' + L('Highlighted on the map.', 'ไฮไลต์บนแผนที่ให้แล้ว') };
      }
      case 'car_status': {
        r = TOOLS.vehicle_status({ car: carIn, time: P.time.label });
        if (r.error) return carErr(r);
        const ago = r.minutes_since_gps > 1 ? L(` · last GPS ${r.gps_time} (${r.minutes_since_gps} min before)`, ` · GPS ล่าสุด ${r.gps_time} (${r.minutes_since_gps} นาทีก่อน)`) : '';
        const off = r.online ? '' : L(' — **offline** (no recent GPS)', ' — **ออฟไลน์** (ไม่มีสัญญาณล่าสุด)');
        return { text: L(`[[${r.car}]] is in **${r.where}** · ${STATUS_WORD.en[r.status]} · ${r.speed_kmh} km/h${off}${ago}.`,
          `[[${r.car}]] อยู่ที่ **${r.where}** · ${STATUS_WORD.th[r.status]} · ${r.speed_kmh} กม./ชม.${off}${ago}`)
          + (r.outside_allowed_zone ? L(' ⚠ Outside the allowed zone.', ' ⚠ อยู่นอกเขตที่อนุญาต') : '') };
      }
      case 'car_track': {
        r = TOOLS.vehicle_track({ car: carIn, time: P.time.explicit ? P.time.label : '' });
        if (r.error) return carErr(r);
        const pv = r.provinces.slice(0, 5).map(p => p.name + (p.outside_zone ? ' ⚠' : '')).join(', ');
        return { text: L(`[[${r.car}]] ${r.from} – ${r.to}: about **${fmt(r.km)} km**, top speed ${r.max_speed_kmh} km/h, on trip ${r.on_trip} of ${r.online} online. From ${r.start.where} to ${r.end.where}. Provinces: ${pv}. The route is drawn on the map.`,
          `[[${r.car}]] ช่วง ${r.from} – ${r.to} วิ่งประมาณ **${fmt(r.km)} กม.** เร็วสุด ${r.max_speed_kmh} กม./ชม. มีผู้โดยสาร ${r.on_trip} จากออนไลน์ ${r.online} · จาก ${r.start.where} ถึง ${r.end.where} · ผ่าน ${pv} — แสดงเส้นทางบนแผนที่แล้ว`) };
      }
      case 'out_of_zone': {
        r = TOOLS.out_of_zone({ time: P.time.explicit ? P.time.label : 'all' });
        const lst = r.top.slice(0, 6).map(x => `[[${x.car}]] ${x.provinces.slice(0, 2).join(', ')}`).join('\n• ');
        const b = r.by_level;
        return { text: L(`${r.from} – ${r.to}: **${fmt(r.vehicles)} vehicles** left the zone (${r.zone}) — ${fmt(r.trips)} trips, ${fmt(r.hours)} h. Upcountry ${fmt(b.upcountry)} · always outside ${fmt(b.always_outside)} · vicinity ${fmt(b.vicinity)}.`,
          `ช่วง ${r.from} – ${r.to} มีรถออกนอกเขต (${r.zone}) **${fmt(r.vehicles)} คัน** · ${fmt(r.trips)} ครั้ง ${fmt(r.hours)} ชม. · ต่างจังหวัด ${fmt(b.upcountry)} · อยู่นอกตลอด ${fmt(b.always_outside)} · ปริมณฑล ${fmt(b.vicinity)}`)
          + (lst ? '\n• ' + lst : '') + '\n' + L('Full list in the Out of zone panel.', 'ดูรายการทั้งหมดในแผง Out of zone') };
      }
      case 'fleet_stats': {
        r = TOOLS.fleet_stats({ time: P.time.label, place: P.place });
        const top = r.top_areas.slice(0, 5).map(a => `${a.name} ${fmt(a.vehicles_online)}`).join(' · ');
        return { text: L(`At ${r.as_of} (${r.scope}): **${fmt(r.online)} vehicles online** — ${statusLine(r.by_status, 'en')}. On trip: ${r.share_on_trip || '–'}. Outside the zone: ${fmt(r.outside_zone)}.\nMost vehicles: ${top}`,
          `ณ ${r.as_of} (${r.scope === 'whole fleet' ? 'ทั้งหมด' : r.scope}) รถออนไลน์ **${fmt(r.online)} คัน** — ${statusLine(r.by_status, 'th')} · สัดส่วนมีผู้โดยสาร ${r.share_on_trip || '–'} · นอกเขต ${fmt(r.outside_zone)} คัน\nรถเยอะสุด: ${top}`) };
      }
      case 'nearest_charger': {
        r = TOOLS.nearest_chargers({ car: carIn, place: P.place, time: P.time.label });
        if (r.error) return { text: r.error };
        const from = /^car:/.test(r.from) ? `[[${r.from}]]` : r.from;
        const lst = r.items.map(x => `${x.n}. ${x.name}${x.operator ? ' (' + x.operator + ')' : ''} — ${x.km} km`).join('\n');
        const inside = r.chargers_in_area != null ? L(` ${r.chargers_in_area} chargers mapped inside ${from}.`, ` ใน ${from} มีสถานีชาร์จในข้อมูล ${r.chargers_in_area} แห่ง`) : '';
        return { text: L(`Nearest EV chargers to ${from}:${inside}\n${lst}\nShown on the map (purple, numbered). ${r.note}`,
          `สถานีชาร์จใกล้ ${from}:${inside}\n${lst}\nแสดงบนแผนที่แล้ว (สีม่วง มีเลขลำดับ) — ข้อมูลจาก OpenStreetMap มีแค่บางส่วนของสถานีจริง`) };
      }
    }
    return { text: '…' };
  },

  /* ── AI agent: stateless server proxy · tools run here ────────────── */
  async askRemote(q) {
    const msg = sanitizePlates(q);
    this.history.push({ role: 'user', content: msg });
    for (let step = 0; step < 8; step++) {
      const r = await fetchTimeout(this.endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: this.history, context: pageContext() }),
      }, AI.timeoutMs);
      if (!r.ok) { this.history.pop(); throw new Error('server ' + r.status); }
      const j = await r.json();
      if (j.error) { this.history.pop(); throw new Error(j.error); }
      this.history.push({ role: 'assistant', content: j.content });           // echoed back exactly as received
      const uses = j.content.filter(b => b.type === 'tool_use');
      if (j.stop_reason !== 'tool_use' || !uses.length) {
        this.trim();
        const text = j.content.filter(b => b.type === 'text').map(b => b.text).join('\n').trim();
        return { text: text || (j.stop_reason === 'refusal' ? 'The assistant declined to answer that.' : '…') };
      }
      const results = uses.map(b => ({ type: 'tool_result', tool_use_id: b.id, content: JSON.stringify(runTool(b.name, b.input)) }));
      this.history.push({ role: 'user', content: results });
    }
    this.trim();
    return { text: 'Stopped after too many steps — try a simpler question.' };
  },
  trim() {   // keep the last ~6 questions; always cut at a plain user question so tool_use/tool_result pairs stay together
    const starts = this.history.map((m, i) => m.role === 'user' && typeof m.content === 'string' ? i : -1).filter(i => i >= 0);
    if (starts.length > 6) this.history = this.history.slice(starts[starts.length - 6]);
  },
};

const STATUS_WORD = {
  en: { on_trip: 'on trip', available: 'available', parked: 'parked', no_signal: 'no GPS signal' },
  th: { on_trip: 'มีผู้โดยสาร', available: 'ว่าง', parked: 'จอด', no_signal: 'ไม่มีสัญญาณ GPS' },
};
function statusLine(by, lang) {
  return ['on_trip', 'available', 'parked', 'no_signal'].filter(k => by[k]).map(k => `${STATUS_WORD[lang][k]} ${fmt(by[k])}`).join(' · ');
}
function carList(vs, lang) {
  return vs.slice(0, 10).map(x => `• [[${x.car}]] ${STATUS_WORD[lang][x.status]} · ${x.where}`).join('\n');
}
function more(n, lang) { return n > 0 ? (lang === 'th' ? `\n…และอีก ${fmt(n)} คัน` : `\n…and ${fmt(n)} more`) : ''; }
/* replace plates in the user's text by [[car:<id>]] so plates never go to the server */
function sanitizePlates(q) {
  let out = q;
  for (let k = 0; k < 5; k++) {
    const p = NLU.plate(out); if (!p || p.v < 0) break;
    out = out.replace(p.raw, `[[car:${p.v}]]`);
  }
  return out;
}
function pageContext() {
  return { data_from: fISO(0), data_to: fISO(D.meta.tmax), timeline_cursor: fISO(S.T), selected_range: [fISO(S.a), fISO(S.b)],
    zone: CFG.ZONES[S.zone].label, selected_car: S.sel >= 0 ? 'car:' + S.sel : null, open_panel: S.panel };
}
function fetchTimeout(url, opt, ms) {
  const c = new AbortController(), t = setTimeout(() => c.abort(), ms);
  return fetch(url, Object.assign({ signal: c.signal }, opt)).finally(() => clearTimeout(t));
}
