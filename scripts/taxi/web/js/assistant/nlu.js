/* js/assistant/nlu.js — understand a question (Thai or English) without any server
   same intents and slots as the trained model in scripts/taxi/qa/taxi_qa_local.ipynb:
     cars_in_area · car_status · car_track · out_of_zone · fleet_stats · nearest_charger · action_request · other
   (+ peak_time · data_info — small extras that need no slot)
   uses: model.js · utils.js
   provides: NLU.parse() · NLU.place() · NLU.time() · NLU.plate() · LANDMARKS */

/* well-known places that are not a province or district — radius search around the point
   coordinates are approximate (public map positions) */
const LANDMARKS = [
  { names: ['สนามบินสุวรรณภูมิ', 'สุวรรณภูมิ', 'suvarnabhumi', 'bkk airport'], en: 'Suvarnabhumi Airport', lat: 13.690, lon: 100.750, r: 3 },
  { names: ['สนามบินดอนเมือง', 'don mueang airport', 'dmk'], en: 'Don Mueang Airport', lat: 13.913, lon: 100.607, r: 2.5 },
  { names: ['สยาม', 'สยามพารากอน', 'siam', 'siam paragon'], en: 'Siam', lat: 13.746, lon: 100.535, r: 1.5 },
  { names: ['เซ็นทรัลเวิลด์', 'centralworld', 'central world'], en: 'CentralWorld', lat: 13.747, lon: 100.539, r: 1.2 },
  { names: ['มาบุญครอง', 'mbk'], en: 'MBK Center', lat: 13.745, lon: 100.530, r: 1.2 },
  { names: ['อนุสาวรีย์ชัยสมรภูมิ', 'อนุสาวรีย์ชัย', 'อนุสาวรีย์', 'victory monument'], en: 'Victory Monument', lat: 13.765, lon: 100.538, r: 1.5 },
  { names: ['ตลาดนัดจตุจักร', 'สวนจตุจักร', 'chatuchak market', 'jj market'], en: 'Chatuchak Market', lat: 13.800, lon: 100.550, r: 1.5 },
  { names: ['หมอชิต', 'mo chit', 'mochit'], en: 'Mo Chit', lat: 13.812, lon: 100.548, r: 1.5 },
  { names: ['สถานีกลางบางซื่อ', 'กรุงเทพอภิวัฒน์', 'bang sue grand', 'krung thep aphiwat'], en: 'Krung Thep Aphiwat Station', lat: 13.804, lon: 100.540, r: 1.5 },
  { names: ['หัวลำโพง', 'hua lamphong'], en: 'Hua Lamphong', lat: 13.739, lon: 100.517, r: 1.2 },
  { names: ['อโศก', 'asok', 'asoke', 'terminal 21'], en: 'Asok', lat: 13.737, lon: 100.560, r: 1.2 },
  { names: ['สีลม', 'silom'], en: 'Silom', lat: 13.729, lon: 100.534, r: 1.5 },
  { names: ['ข้าวสาร', 'khao san', 'khaosan'], en: 'Khao San Road', lat: 13.759, lon: 100.497, r: 1 },
  { names: ['พระบรมมหาราชวัง', 'วัดพระแก้ว', 'grand palace'], en: 'Grand Palace', lat: 13.750, lon: 100.491, r: 1.2 },
  { names: ['ไอคอนสยาม', 'iconsiam'], en: 'ICONSIAM', lat: 13.727, lon: 100.511, r: 1.2 },
  { names: ['พระราม 9', 'พระราม9', 'rama 9', 'rama ix'], en: 'Rama 9', lat: 13.759, lon: 100.566, r: 1.5 },
  { names: ['เอกมัย', 'ekkamai'], en: 'Ekkamai', lat: 13.720, lon: 100.585, r: 1.2 },
  { names: ['เมกาบางนา', 'mega bangna'], en: 'Mega Bangna', lat: 13.647, lon: 100.680, r: 1.5 },
  { names: ['ฟิวเจอร์พาร์ค', 'future park'], en: 'Future Park Rangsit', lat: 13.989, lon: 100.617, r: 1.5 },
  { names: ['เมืองทองธานี', 'อิมแพ็ค', 'impact', 'muang thong thani'], en: 'IMPACT Muang Thong Thani', lat: 13.912, lon: 100.548, r: 1.5 },
  { names: ['พัทยา', 'pattaya'], en: 'Pattaya', lat: 12.924, lon: 100.883, r: 5 },
];
const PROV_ALIAS = { 'กทม': 'TH10', 'กรุงเทพ': 'TH10', 'กรุงเทพฯ': 'TH10', 'บางกอก': 'TH10', 'bkk': 'TH10', 'bangkok': 'TH10',
  'โคราช': 'TH30', 'korat': 'TH30', 'อยุธยา': 'TH14', 'ayutthaya': 'TH14' };

const NLU = {
  PLATE_RE: /(?<![ก-๙A-Za-z])((?:[ก-ฮ]{1,3}|[A-Za-z]{1,2})\s*-?\s*\d{3,4})(?!\d)/,
  EN_STOP: new Set(['in', 'at', 'on', 'to', 'by', 'of', 'is', 'am', 'pm', 'no', 'or', 'as', 'an', 'a', 'i', 'it', 'be', 'do', 'up', 'top']),
  _plates: null, _gaz: null,

  /* ── plate → vehicle index ─────────────────────────────────────── */
  plateIndex() {
    if (this._plates) return this._plates;
    const m = new Map(), V = D.vehicles;
    V.plate.forEach((p, v) => {
      const k = p.split(' · ')[0].replace(/[\s-]/g, '').toUpperCase();
      if (!m.has(k)) m.set(k, v);
      m.set(V.vin[v].toUpperCase(), v);
    });
    return (this._plates = m);
  },
  plate(q) {
    const m = this.PLATE_RE.exec(q);
    if (!m) return this.loosePlate(q);
    const raw = m[1], key = raw.replace(/[\s-]/g, '').toUpperCase();
    const v = D ? this.plateIndex().get(key) : undefined;
    const letters = key.replace(/\d+$/, '');
    // English 1–2 letters + digits is often just words ("in 2026") — accept only if it is a real plate
    if (v === undefined && /^[A-Z]+$/.test(letters) && (this.EN_STOP.has(letters.toLowerCase()) || D)) return this.loosePlate(q);
    return { raw, key, v: v === undefined ? -1 : v };
  },
  /* a plate glued to a Thai word ("ขอทอ-4141") — try the last 1–3 letters, accept only a real plate */
  loosePlate(q) {
    if (!D) return null;
    const re = /([ก-ฮ]{1,6})\s*-?\s*(\d{3,4})(?!\d)/g; let m;
    while ((m = re.exec(q))) {
      for (let n = Math.min(3, m[1].length); n >= 1; n--) {
        const key = m[1].slice(-n) + m[2], v = this.plateIndex().get(key);
        if (v !== undefined) { const at = m[0].lastIndexOf(m[1].slice(-n)); return { raw: m[0].slice(at), key, v }; }
      }
    }
    return null;
  },

  /* ── time — the data is a batch, so "now" = the latest point in the data ── */
  time(q) {
    const tmax = D.meta.tmax, d = tDate(tmax); d.setHours(0, 0, 0, 0);
    const day0 = (d.getTime() - t0ms) / 1000;
    let a = null, b = tmax, label = 'latest data', at = null;
    if (/เมื่อวาน|yesterday/i.test(q)) { a = day0 - 86400; b = day0 - 1; label = 'yesterday'; }
    else if (/วันนี้|today/i.test(q)) { a = day0; b = tmax; label = 'today'; }
    let hh = null, mm = 0, m;
    if ((m = /(\d{1,2})\s*[:.]\s*(\d{2})\s*(น\.?|am|pm)?/i.exec(q))) { hh = +m[1]; mm = +m[2]; if (/pm/i.test(m[3] || '') && hh < 12) hh += 12; if (/am/i.test(m[3] || '') && hh === 12) hh = 0; }
    else if ((m = /ตี\s*(\d{1,2})/.exec(q))) hh = +m[1];
    else if ((m = /บ่าย\s*(\d{1,2})/.exec(q))) hh = +m[1] + (+m[1] < 12 ? 12 : 0);
    else if ((m = /(\d{1,2})\s*ทุ่ม/.exec(q))) hh = +m[1] + 18;
    else if ((m = /(\d{1,2})\s*โมง\s*(เย็น|ค่ำ)/.exec(q))) hh = +m[1] + (+m[1] < 12 ? 12 : 0);
    else if ((m = /(\d{1,2})\s*โมง/.exec(q))) hh = +m[1];
    else if ((m = /\b(\d{1,2})\s*(am|pm)\b/i.exec(q))) { hh = +m[1] % 12 + (/pm/i.test(m[2]) ? 12 : 0); }
    else if (/เที่ยงคืน|midnight/i.test(q)) hh = 0;
    else if (/เที่ยง|noon/i.test(q)) hh = 12;
    if (hh != null && hh < 24 && mm < 60) {
      const base = a != null ? a : day0;
      at = base + hh * 3600 + mm * 60;
      b = at; label = (a != null ? label + ' ' : '') + p2(hh) + ':' + p2(mm);
    }
    if (at == null) at = b;
    const clamp = t => Math.max(0, Math.min(tmax, t));
    const outside = at < 0 || at > tmax;
    return { a: a == null ? 0 : clamp(a), b: clamp(b), at: clamp(at), label, outside, explicit: a != null || hh != null };
  },
  stripTime(q) {
    return q.replace(/เมื่อวาน|วันนี้|ตอนนี้|ล่าสุด|yesterday|today|right now|now/gi, ' ')
      .replace(/(\d{1,2})\s*[:.]\s*(\d{2})\s*(น\.?|am|pm)?|ตี\s*\d{1,2}|บ่าย\s*\d{1,2}(\s*โมง)?|\d{1,2}\s*ทุ่ม|\d{1,2}\s*โมง(\s*(เย็น|ค่ำ|เช้า))?|\b\d{1,2}\s*(am|pm)\b|เที่ยงคืน|เที่ยง|midnight|noon/gi, ' ');
  },

  /* ── place: province · district · landmark (exact, then fuzzy for typos) ── */
  gazetteer() {
    if (this._gaz) return this._gaz;
    const g = [];
    const add = (name, item) => { name = name.toLowerCase().trim(); if (name.length >= 2) g.push({ name, item, L: name.length, latin: /^[a-z0-9 .'-]+$/.test(name), bg: grams(name) }); };
    const pIdx = new Map(PROV.map((p, i) => [p.pc, i]));
    PROV.forEach((p, i) => {
      const it = { kind: 'prov', idx: i, key: 'p:' + i };
      add(p.th, it); add('จังหวัด' + p.th, it); if (p.en) add(p.en, it);
    });
    DIST.forEach((d, i) => {
      const it = { kind: 'dist', idx: i, key: 'd:' + i };
      const pre = PROV[d.p].pc === 'TH10' ? 'เขต' : 'อำเภอ';      // "เขต" only in Bangkok
      add(d.th, it); add(pre + d.th, it); if (d.en) add(d.en, it);
    });
    for (const [a, pc] of Object.entries(PROV_ALIAS)) if (pIdx.has(pc)) add(a, { kind: 'prov', idx: pIdx.get(pc), key: 'p:' + pIdx.get(pc) });
    LANDMARKS.forEach(l => l.names.forEach(n => add(n, { kind: 'poi', poi: l })));
    const seen = new Set();
    return (this._gaz = g.filter(x => !seen.has(x.name) && seen.add(x.name)));
  },
  // everyday words that are one letter away from a place name (ประเทศ ~ ประเวศ, ผู้โดยสาร ~ สารภี)
  COMMON: /ประเทศ|ผู้โดยสาร|โดยสาร|เปอร์เซ็นต์|ออนไลน์|ทั้งหมด|สถานี|ทะเบียน|ตำแหน่ง|สถานะ|ประวัติ|เส้นทาง|ภาพรวม|อันดับ/g,
  place(q, minScore = 0.88) {
    const s = q.toLowerCase(), sf = s.replace(this.COMMON, ' '), sg = grams(sf);
    let best = null, bs = 0;
    for (const x of this.gazetteer()) {
      let score = 0;
      if (!x.latin && x.L <= 2) continue;                           // 2-letter Thai names hide inside ordinary words — only "อำเภอ…" / "เขต…" forms
      const exact = x.latin ? new RegExp('(^|[^a-z])' + x.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '($|[^a-z])').test(s) : s.includes(x.name);
      if (exact) score = 1 + x.L / 100;                             // exact: the longer name wins
      else {
        if (x.L < 4) continue;                                      // short names must match exactly
        const s = sf;                                               // fuzzy only on the text without everyday words
        let hit = 0; for (const b of x.bg) if (sg.has(b)) hit++;
        if (hit < 0.4 * x.bg.size) continue;                        // quick filter on letter pairs
        for (let w = x.L - 1; w <= x.L + 1; w++) for (let i = 0; i + w <= s.length; i++) score = Math.max(score, simRatio(x.name, s.slice(i, i + w)));
      }
      if (x.item.kind === 'prov') score += 0.001;                   // tie → province
      if (score > bs) { bs = score; best = x; }
    }
    if (!best || bs < minScore) return null;
    return Object.assign({ matched: best.name, score: Math.min(1, +bs.toFixed(2)) }, placeInfo(best.item));
  },

  /* ── intent (rules tuned on the training templates + hand-written test set) ── */
  R: {
    action: /ตัด(สัญญาณ|ไฟ|เครื่อง)|ล็อ[คก]|ปลดล็อ|ดับเครื่อง|ปิด(รถ|เครื่อง)|หยุดรถ|บล็อ[คก]|ยึดรถ|ส่งข้อความ|โทรหาคนขับ|\b(un)?lock\b|immobili[sz]e|shut (it |the car )?down|cut (the )?(power|engine|signal)|kill switch|stop the (car|vehicle)|block (the )?(car|vehicle)|disable (the )?(car|vehicle)|(send|text) (a )?message|call the driver/i,
    charger: /ชาร์จ|ชาร์ต|ปั[๊้]ม|แบต(เตอรี่)?(ใกล้)?หมด|charg|plug|battery|ev station/i,
    track: /ไป(ไหน|ที่ไหน)(มา)?บ้าง|ไปไหนมา|เส้นทาง|กี่(กิโล|โล)|กิโลเมตร|ระยะทาง|ผ่าน(จังหวัด|ที่ไหน)|ประวัติ|ย้อน(ดู)?|สรุปการ(เดินทาง|วิ่ง)|ต่างจังหวัด|\btrack|route|history|how far|distance|\bkm\b|kilomet|been\b|travel|drove|driven|trips?\b/i,
    ooz: /นอก(เขต|พื้นที่|โซน)|หลุดโซน|ผิดพื้นที่|(ออก|ไป|วิ่ง)(นอก|ต่างจังหวัด)|out of (the )?zone|outside (the )?(zone|bangkok|area)|left (the zone|bangkok)|leave (the zone|bangkok)|violat|upcountry/i,
    rank: /(จังหวัด|เขต|อำเภอ|พื้นที่|ที่)ไหน.*(เยอะ|มาก)|อันดับ|\btop\s*\d*\b|\bmost\b|busiest|which (province|district|area|region)|\brank/i,
    stats: /ภาพรวม|สรุป|สถิติ|ทั้งหมด|ออนไลน์|กี่คัน|เปอร์เซ็นต์|อัตรา|สัดส่วน|ไม่มีสัญญาณ|overview|summary|stats|statistic|how many|online|utili[sz]|fleet|percent|ratio/i,
    peak: /กี่โมง|ช่วงไหน|ช่วงเวลา|เวลาไหน|what time|which hour|\bwhen\b|peak/i,
    peak2: /(มาก|เยอะ)(ที่)?สุด|most|peak|busiest/i,
    info: /ข้อมูล.*(วันไหน|ช่วงไหน|ถึงวันไหน|ถึงเมื่อไหร่|ล่าสุดเมื่อไหร่)|what (dates|period)|data (range|cover|from)|how (old|recent) is the data/i,
    greet: /^(สวัสดี|หวัดดี|ดีครับ|ดีค่ะ|hello|hi|hey|ขอบคุณ|thank)/i,
    who: /คุณเป็นใคร|ทำอะไรได้|ช่วยอะไรได้|who are you|what can you do|help$/i,
    thisCar: /คันนี้|คันนั้น|คันเดิม|this (car|vehicle|one)|that (car|vehicle)|\bit\b/i,
  },
  status(q) {
    if (/ว่าง|available|free|vacant|empty/i.test(q)) return 'vacant';
    if (/มีผู้โดยสาร|รับผู้โดยสาร|ผู้โดยสาร|on (a )?trip|occupied|hired|passenger/i.test(q)) return 'hired';
    if (/จอด|parked|parking|idle/i.test(q)) return 'park';
    return null;
  },
  parse(q, ctx = {}) {
    const lang = /[ก-๙]/.test(q) ? 'th' : 'en';
    const R = this.R;
    // time words glued to a plate ("เมื่อวานทอ-4141") would hide it from the plate pattern
    const qs = q.replace(/(เมื่อวาน|วันนี้|ตอนนี้|ล่าสุด)/g, ' $1 ');
    const plate = this.plate(qs);
    const rest0 = plate ? qs.replace(plate.raw, ' ') : qs;
    const time = this.time(rest0);
    const place = this.place(this.stripTime(rest0));
    let v = plate ? plate.v : -1;
    if (!plate && R.thisCar.test(q) && ctx.lastV >= 0) v = ctx.lastV;
    const hasCar = !!plate || v >= 0;
    let intent;
    if (R.action.test(q)) intent = 'action_request';
    else if (R.charger.test(q)) intent = 'nearest_charger';
    else if (hasCar) intent = R.track.test(q) ? 'car_track' : 'car_status';
    else if (R.info.test(q)) intent = 'data_info';
    else if (R.ooz.test(q)) intent = 'out_of_zone';
    else if (R.peak.test(q) && R.peak2.test(q)) intent = 'peak_time';
    else if (R.rank.test(q)) intent = 'fleet_stats';
    else if (place) intent = 'cars_in_area';
    else if (R.stats.test(q)) intent = 'fleet_stats';
    else intent = R.greet.test(q.trim()) || R.who.test(q) ? 'hello' : 'other';
    return { intent, lang, plate, v, time, place, status: this.status(q), rank: R.rank.test(q) };
  },
};

/* place item → name + centre point */
function placeInfo(it) {
  if (it.kind === 'poi') return { kind: 'poi', name: it.poi.en, lat: it.poi.lat, lon: it.poi.lon, r: it.poi.r };
  const c = areaCenter(it.key);
  return { kind: it.kind, idx: it.idx, key: it.key, name: areaName(it.key), lat: c ? c[1] : null, lon: c ? c[0] : null };
}
function grams(s) { const g = new Set(); for (let i = 0; i + 1 < s.length; i++) g.add(s.slice(i, i + 2)); return g; }
/* similarity like difflib's ratio: (len a + len b − edits) / (len a + len b) */
function simRatio(a, b) {
  const m = a.length, n = b.length;
  let prev = new Array(n + 1), cur = new Array(n + 1);
  for (let j = 0; j <= n; j++) prev[j] = j;
  for (let i = 1; i <= m; i++) {
    cur[0] = i;
    for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    [prev, cur] = [cur, prev];
  }
  return (m + n - prev[n]) / (m + n);
}
