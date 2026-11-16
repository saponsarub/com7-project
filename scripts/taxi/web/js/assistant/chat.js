/* js/assistant/chat.js — the chat drawer: messages · example questions · [[car:<id>]] → clickable plate
   uses: agent.js
   provides: Chat (init · open · close · send · reset · hasTalk) · ASK_EXAMPLES */

const ASK_EXAMPLES = [
  'How many cars are in Phuket now?',
  'Fleet overview right now',
  'Which cars left the zone today?',
  'EV chargers near Siam',
  'รถว่างแถวบางนามีกี่คัน',
  'ที่ชาร์จใกล้หาดใหญ่',
  'When are the most cars on a trip?',
];
const Chat = {
  busy: false,
  init() {
    $('#askBtn').innerHTML = `${ICON.spark}<span>Ask</span>`;
    $('#askBtn').onclick = () => document.body.classList.contains('chat-open') ? this.close() : this.open();
    $('#chatX').innerHTML = ICON.x;
    $('#chatX').onclick = () => this.close();
    $('#chatReset').onclick = () => { this.reset(); UI_ACT.clear(); renderLegend(); };
    $('#chatSend').innerHTML = ICON.send;
    const ta = $('#chatQ');
    ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = Math.min(120, ta.scrollHeight) + 'px'; });
    ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#chatForm').requestSubmit(); } });
    $('#chatForm').onsubmit = e => { e.preventDefault(); const q = ta.value.trim(); if (q) { ta.value = ''; ta.style.height = 'auto'; this.send(q); } };
    $('#chatLog').addEventListener('click', e => {
      const b = e.target.closest('[data-car]'); if (b) selectVehicle(+b.dataset.car, true);
      const s = e.target.closest('[data-ask]'); if (s) this.send(s.dataset.ask);
    });
    this.hello();
    Agent.detect().then(m => this.badge(m));
    this.badge('offline');
  },
  /* forget the conversation (the AI's history too) and start over with the welcome message */
  reset() { Agent.reset(); $('#chatLog').innerHTML = ''; this.hello(); },
  hasTalk: () => !!$('#chatLog .msg.me'),
  badge(m) {
    const b = $('#aiMode');
    b.textContent = m === 'ai' ? 'AI agent' : 'Offline';
    b.className = 'badge ' + (m === 'ai' ? 'ai' : '');
    b.title = m === 'ai' ? 'Answers by Claude through your server. Plates are replaced by codes before sending.'
      : 'Rule-based answers computed in this browser. No data leaves the page.';
  },
  hello() {
    this.add('bot', `Hi — I answer questions about the fleet in English or Thai, and show the answer on the map.\n`
      + `I can't control vehicles. Try one of these:`, ASK_EXAMPLES.slice(0, 6));
  },
  open(q) {
    document.body.classList.add('chat-open');
    $('#chat').hidden = false;
    $('#askBtn').setAttribute('aria-expanded', 'true');
    if (q) this.send(q); else setTimeout(() => $('#chatQ').focus(), 50);
  },
  close() {
    document.body.classList.remove('chat-open');
    $('#chat').hidden = true;
    $('#askBtn').setAttribute('aria-expanded', 'false');
    $('#askBtn').focus();
  },
  add(who, text, sugg, note) {
    const el = document.createElement('div');
    el.className = 'msg ' + who;
    el.innerHTML = (who === 'me' ? esc(text).replace(/\n/g, '<br>') : richText(text))
      + (note ? `<div class="note">${esc(note)}</div>` : '')
      + (sugg ? `<div class="chips">${sugg.map(s => `<button type="button" class="chip" data-ask="${esc(s)}">${esc(s)}</button>`).join('')}</div>` : '');
    $('#chatLog').appendChild(el);
    el.scrollIntoView({ block: 'end', behavior: 'smooth' });
    return el;
  },
  async send(q) {
    if (this.busy) return;
    if (!document.body.classList.contains('chat-open')) this.open();
    this.busy = true; $('#chatSend').disabled = true;
    this.add('me', q);
    const wait = this.add('bot wait', '<span class="typing"><i></i><i></i><i></i></span>');
    wait.innerHTML = '<span class="typing" aria-label="Thinking"><i></i><i></i><i></i></span>';
    try {
      const r = await Agent.ask(q);
      wait.remove();
      this.add('bot', r.text, null, r.note);
    } catch (e) {
      wait.remove();
      this.add('bot', 'Something went wrong: ' + e.message);
      showErr('assistant', e);
    } finally {
      this.busy = false; $('#chatSend').disabled = false;
      renderLegend();
    }
  },
};
/* assistant text → HTML: escape, then **bold**, line breaks, [[car:<id>]] → plate button */
function richText(s) {
  return esc(s)
    .replace(/\[\[car:(\d+)\]\]/g, (_, v) => +v < NV ? `<button type="button" class="carchip" data-car="${v}" title="Show this vehicle">${esc(plateOf(+v))}</button>` : 'unknown vehicle')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\n/g, '<br>');
}
