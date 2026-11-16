/* js/ui/icons.js — inline SVG icons (stroke = currentColor) · no icon font, works offline
   provides: ICON · icon() */

const _svg = (d, extra = '') => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"${extra}>${d}</svg>`;
const ICON = {
  overview: _svg('<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>'),
  vehicles: _svg('<path d="M5 16V11l2-5h10l2 5v5"/><path d="M3 16h18v3H3z"/><circle cx="7.5" cy="13" r=".8" fill="currentColor"/><circle cx="16.5" cy="13" r=".8" fill="currentColor"/><path d="M9 6V4h6v2"/>'),
  zone: _svg('<path d="M12 21s-7-5.6-7-11a7 7 0 0 1 14 0c0 5.4-7 11-7 11z"/><path d="M12 7v4"/><circle cx="12" cy="14" r=".6" fill="currentColor"/>'),
  parking: _svg('<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M9.5 17V7h3.5a3 3 0 0 1 0 6H9.5"/>'),
  away: _svg('<path d="M3 12a9 9 0 1 0 9-9"/><path d="M12 8v4l2.5 2.5"/><path d="M14 3h7v7"/><path d="M21 3l-6 6"/>'),
  areas: _svg('<path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15M15 6v15"/>'),
  search: _svg('<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>'),
  x: _svg('<path d="M6 6l12 12M18 6L6 18"/>'),
  play: _svg('<path d="M7 4.5v15l12-7.5z" fill="currentColor"/>'),
  pause: _svg('<rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor"/><rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor"/>'),
  layers: _svg('<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>'),
  home: _svg('<path d="M4 11l8-7 8 7"/><path d="M6 10v10h12V10"/>'),
  globe: _svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/>'),
  chat: _svg('<path d="M4 5h16v11H9l-5 4z"/><path d="M8.5 10.5h.01M12 10.5h.01M15.5 10.5h.01" stroke-width="2.6"/>'),
  spark: _svg('<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>'),
  send: _svg('<path d="M4 12l16-8-6 16-2.5-6.5z"/><path d="M11.5 13.5L20 4"/>'),
  back: _svg('<path d="M15 5l-7 7 7 7"/>'),
  collapse: _svg('<path d="M14 6l-6 6 6 6"/><path d="M19 4v16"/>'),
  expand: _svg('<path d="M10 6l6 6-6 6"/><path d="M5 4v16"/>'),
  download: _svg('<path d="M12 4v11M7 10l5 5 5-5"/><path d="M5 20h14"/>'),
  pin: _svg('<path d="M12 21s-6-5.4-6-10.5a6 6 0 0 1 12 0C18 15.6 12 21 12 21z"/><circle cx="12" cy="10.5" r="2.2"/>'),
  moon: _svg('<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>'),
  filter: _svg('<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>'),
  plug: _svg('<path d="M9 3v5M15 3v5"/><path d="M6 8h12v3a6 6 0 0 1-12 0z"/><path d="M12 17v4"/>'),
  info: _svg('<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="8" r=".6" fill="currentColor"/>'),
  reset: _svg('<path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 4v4h4"/>'),
};
