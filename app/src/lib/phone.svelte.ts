// The Builder on a phone. Desktop is the Builder; below one breakpoint (the design system's 760 px)
// screens stack, controls grow to touch size and the tools that need a mouse and a big screen say
// so. Looks belong in CSS under PHONE_MEDIA; anything that changes behaviour or what gets built
// reads `phone.on`. Every screen says what it is on a phone in SCREENS below: a screen missing
// from it needs a computer (phone.test.ts checks every route has an entry).

/** The one phone query: narrower than 760 px. CSS writes it as `@media (max-width: 759.98px)`. */
export const PHONE_MEDIA = '(max-width: 759.98px)';

export const phone = $state({
  /** narrower than the breakpoint */
  on: false,
  /** a finger rather than a mouse is the main pointer */
  coarse: false
});

/** Follow the window size; runs once in routes/+layout.svelte. Returns a function that stops it. */
export function installPhone(win: Window = window): () => void {
  if (!win.matchMedia) return () => {};
  const narrow = win.matchMedia(PHONE_MEDIA), finger = win.matchMedia('(pointer: coarse)');
  const set = () => { phone.on = narrow.matches; phone.coarse = finger.matches; };
  set();
  narrow.addEventListener('change', set); finger.addEventListener('change', set);
  return () => { narrow.removeEventListener('change', set); finger.removeEventListener('change', set); };
}

/** What a screen is on a phone: usable there, or a tool that needs a computer (named in the note). */
export type OnPhone = 'phone' | { computer: string };

/** Route → what it is on a phone. Paths are SvelteKit route ids. */
export const SCREENS: Record<string, OnPhone | ((q: URLSearchParams) => OnPhone)> = {
  '/': 'phone',                                   // goes on to Layouts
  '/glyphs': 'phone',
  '/glyphs/new': { computer: 'The glyph editor' },
  '/glyphs/[name]/edit': { computer: 'The glyph editor' },
  '/layouts': 'phone',
  '/test': 'phone',
  '/tester': 'phone',                             // goes on to Build & test
  '/help': 'phone',
  '/requests': 'phone',
  // a tester's own changes and sending them read fine; deciding on other people's changes is at a desk
  '/review': (q) => (q.has('mine') ? 'phone' : { computer: 'Review' }),
  '/release': { computer: 'Making a release' }
};

/** A screen's name in the phone's one-row top bar. */
export const TITLES: Record<string, string | ((q: URLSearchParams, params: Record<string, string>) => string)> = {
  '/glyphs': 'Glyphs',
  '/glyphs/new': 'New glyph',
  '/glyphs/[name]/edit': (_, p) => p.name ?? 'Glyph',
  '/layouts': 'Layouts',
  '/test': 'Build & test',
  '/help': 'Help',
  '/requests': 'Change Requests',
  '/review': (q) => (q.has('mine') ? 'Your changes' : 'Review'),
  '/release': 'Release'
};
export function screenTitle(routeId: string | null, q: URLSearchParams, params: Record<string, string> = {}): string {
  const t = routeId === null ? undefined : TITLES[routeId];
  return typeof t === 'function' ? t(q, params) : t ?? 'Font Builder';
}

/** What the screen at `routeId` (page.route.id) is on a phone; a screen not in SCREENS needs a computer. */
export function screenOnPhone(routeId: string | null, q: URLSearchParams = new URLSearchParams()): OnPhone {
  const s = routeId === null ? undefined : SCREENS[routeId];
  if (!s) return { computer: 'This screen' };
  return typeof s === 'function' ? s(q) : s;
}

/** Tools opened anyway on a phone, for this visit only (gone when the page reloads). */
export const openedAnyway = $state<Record<string, boolean>>({});
