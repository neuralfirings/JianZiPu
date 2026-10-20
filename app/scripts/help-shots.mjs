// Screenshots for the help page (static/help/*.jpg), taken from a running Builder in your
// installed Chrome. Retake them when a screen changes:
//   cd builder && python3 -m jzpbuild.webserver          (or any port; set BASE)
//   cd app && npm run build && npm run help:shots       (BASE=http://127.0.0.1:5714 npm run help:shots)
// The Build & test shots need a build; the script starts one if the server has none.
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = process.env.BASE ?? 'http://127.0.0.1:5713';
const OUT = resolve(dirname(fileURLToPath(import.meta.url)), '../static/help');
const WORDS = 's7k5 0k3 s7.6k5 fys9k5 s7>\\k5 :fenkai C03|s6,5 名七勾五';

/** name → [path, what to do before the shot] */
const SHOTS = [
  ['glyphs', '/glyphs?view=tiles&group=right&g=lg_gou', null],
  ['typing', '/glyphs?view=typing&group=left', null],
  ['editor', '/glyphs/lg_gou/edit', null],
  ['layouts', '/layouts', null],
  ['build-design', `/test?view=words&words=${encodeURIComponent(WORDS)}`, async (p) => { await p.getByLabel('Compare both').check(); }],
  ['build-font', `/test?view=text&words=${encodeURIComponent(WORDS)}`, null]
];

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1, colorScheme: 'light' });
const page = await ctx.newPage();

// a build first, so the font-file shots have a font
await page.goto(`${BASE}/test`);
await page.waitForLoadState('networkidle');
if (await page.getByText('No build yet').isVisible()) {
  console.log('no build on the server yet: building…');
  await page.getByRole('button', { name: /build/i }).first().click();
  await page.getByText('last build ok').waitFor({ timeout: 180_000 });
}

for (const [name, path, before] of SHOTS) {
  await page.goto(`${BASE}${path}`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);            // fonts, canvases and panel layout settle
  if (before) { await before(page); await page.waitForTimeout(800); }
  const file = resolve(OUT, `${name}.jpg`);
  await page.screenshot({ path: file, type: 'jpeg', quality: 82 });
  console.log('wrote', file);
}
await browser.close();
