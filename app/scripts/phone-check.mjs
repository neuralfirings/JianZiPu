// The phone check: every screen that works on a phone (lib/phone.svelte.ts SCREENS), opened at
// 390 × 844 with touch, must not scroll sideways, and every button must say what it does (its words,
// or an aria-label) and be big enough for a finger (24 px at least, WCAG 2.5.8). Screens that need a
// computer must show the note that says so. Runs against a running Builder, in CI too (tests.yml):
//   cd builder && python3 -m jzpbuild.webserver          (or any port; set BASE)
//   cd app && npm run build && npm run phone:check     (CHROME=/path/to/chrome to pick the browser)
// Your Change Requests and Your changes need a signed-in tester: check those by hand on the hosted Builder.
import { chromium } from 'playwright-core';

const BASE = process.env.BASE ?? 'http://127.0.0.1:5713';

/** [path, what it is on a phone]: 'phone' screens get every check, 'computer' ones the note. */
const SCREENS = [
  ['/help', 'phone'],
  ['signin', 'phone'],
  ['/glyphs/lg_gou/edit', 'computer'],
  ['/release', 'computer'],
  ['/review', 'computer']
];
/** Screens on their way to working on a phone: checked and reported, but not yet a failure. */
const TODO = new Set(['/glyphs?view=tiles&group=right&g=lg_gou', '/glyphs?view=typing&group=left', '/layouts', '/test?view=words', '/test?view=text']);

const browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : { channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, colorScheme: 'light' });
const page = await ctx.newPage();
// nothing leaves the machine (fonts, Supabase); the sign-in screen is the hosted one, faked
await page.route((url) => !url.href.startsWith(BASE), (r) => r.abort());

/** What's wrong with the screen as it stands, in words. */
async function problems(kind) {
  return page.evaluate((kind) => {
    const out = [];
    const main = document.querySelector('main');
    const wide = (el) => el.scrollWidth > el.clientWidth + 1;
    if (wide(document.documentElement)) out.push(`the page scrolls sideways (${document.documentElement.scrollWidth} px wide)`);
    if (main && wide(main)) out.push(`the screen scrolls sideways (${main.scrollWidth} px wide)`);
    const note = document.querySelector('[data-needs-computer]');
    if (kind === 'computer') { if (!note) out.push('no "needs a computer" note'); return out; }
    for (const b of document.querySelectorAll('button, [role=button], select, a.pill')) {
      const r = b.getBoundingClientRect(), cs = getComputedStyle(b);
      if (!r.width || !r.height || cs.visibility === 'hidden' || b.closest('[hidden], .tip')) continue;
      const what = (b.textContent ?? '').trim() || b.getAttribute('aria-label') || b.getAttribute('title');
      const name = what ? `"${what.slice(0, 30)}"` : b.outerHTML.slice(0, 60);
      if (!what) out.push(`a button without words or an aria-label: ${name}`);
      // parts on a canvas are as big as the design draws them
      if (!b.closest('svg') && (r.height < 24 || r.width < 24)) out.push(`${name} is ${Math.round(r.width)} × ${Math.round(r.height)} px, under 24`);
    }
    return out;
  }, kind);
}

async function open(path) {
  if (path === 'signin') {
    await page.route(`${BASE}/api/config`, (r) => r.fulfill({ json: { mode: 'hosted', commit: null, supabase_url: 'https://example.supabase.co', supabase_anon_key: 'x' } }));
    await page.goto(`${BASE}/glyphs`);
  } else {
    await page.unroute(`${BASE}/api/config`);
    await page.goto(`${BASE}${path}`);
  }
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(600);   // fonts, canvases and panels settle
}

let failed = 0;
for (const [path, kind] of [...SCREENS, ...[...TODO].filter((p) => !SCREENS.some(([s]) => s === p)).map((p) => [p, 'phone'])]) {
  await open(path);
  const p = await problems(kind);
  const todo = TODO.has(path);
  if (p.length && !todo) failed++;
  console.log(`${p.length ? (todo ? '…' : '✗') : '✓'} ${path}${todo ? ' (not phone-ready yet)' : ''}`);
  for (const line of p.slice(0, 12)) console.log(`    ${line}`);
  if (p.length > 12) console.log(`    … and ${p.length - 12} more`);
}
await browser.close();
if (failed) { console.error(`\n${failed} screen${failed === 1 ? '' : 's'} not right on a phone`); process.exit(1); }
