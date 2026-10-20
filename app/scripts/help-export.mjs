// The Builder's help for people and AI tools outside the app. The app renders its pages in the
// browser and asks testers to sign in, so a crawler or an agent fetching builder.jianzipufont.com
// sees an empty page. This renders routes/help/+page.svelte (with both the online and the
// own-computer wording) and writes the public copies:
//   site/help/index.html   the help page on jianzipufont.com, screenshots from the Builder
//   site/help.md           the same as Markdown, for AI tools
//   site/llms.txt          the index AI tools look for (https://llmstxt.org); also app/static/llms.txt
// Run after changing the help text, then commit:   cd app && npm run help:export
// CI runs `npm run help:export -- --check`, which fails when the committed copies are stale.
import { createServer } from 'vite';
import { JSDOM } from 'jsdom';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { resolve, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const BUILDER = 'https://builder.jianzipufont.com';
const SITE = 'https://jianzipufont.com';
const HELP_URL = `${SITE}/help/`;
const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SITE_DIR = resolve(APP, '../site');
const check = process.argv.includes('--check');

const vite = await createServer({ root: APP, server: { middlewareMode: true }, appType: 'custom', logLevel: 'error' });
let html, sections;
try {
  // svelte/server through Vite too, so the page and the renderer share one copy of Svelte
  const { render } = await vite.ssrLoadModule('svelte/server');
  const page = await vite.ssrLoadModule('/src/routes/help/+page.svelte');
  ({ HELP_SECTIONS: sections } = await vite.ssrLoadModule('/src/lib/help.ts'));
  html = render(page.default, { props: { everyone: true } }).body;
} finally {
  await vite.close();
}

const doc = new JSDOM(html).window.document;
const article = doc.querySelector('article');

/** An app link → where it works from outside: screens on the Builder, sections on the help page. */
function absolute(href, hashBase) {
  if (href.startsWith('#')) return hashBase + href;
  if (href.startsWith('/')) return BUILDER + href;
  return href;
}

// ── Markdown ───────────────────────────────────────────────────────────────────────────────────

const squash = (s) => s.replace(/\s+/g, ' ');
const tick = (s) => (s.includes('`') ? `\`\` ${s} \`\`` : `\`${s}\``);

function inline(node) {
  if (node.nodeType === 3) return squash(node.textContent);
  if (node.nodeType !== 1) return '';
  const el = node;
  const tag = el.tagName.toLowerCase();
  const kids = () => [...el.childNodes].map(inline).join('');
  if (tag === 'svg') {
    // an icon: its job when it has one (More, Undo, ?), else nothing (the words around it say it)
    const label = el.getAttribute('aria-label');
    return label ? `**${label}**` : '';
  }
  if (tag === 'code' || tag === 'kbd') return tick(el.textContent.trim());
  if (tag === 'strong' || tag === 'b') return `**${kids().trim()}**`;
  if (tag === 'em' || tag === 'i') return `*${kids().trim()}*`;
  if (tag === 'br') return '\n';
  if (tag === 'a') {
    const text = kids().trim();
    const href = el.getAttribute('href') ?? '';
    return `[${text}](${absolute(href, HELP_URL)})`;
  }
  if (el.classList.contains('pill') || el.classList.contains('chip')) return `**${kids().trim()}**`;
  return kids();
}

const clean = (s) => s.replace(/[ \t]+/g, ' ').replace(/ ?\n ?/g, '\n').replace(/\*\*\*\*/g, '').trim();

/** A table: a Markdown table when it has a header row, else a list of "row head: row text". */
function table(el) {
  const head = el.querySelector('thead tr');
  const rows = [...el.querySelectorAll('tbody tr')];
  const cells = (tr) => [...tr.children].map((c) => clean(inline(c)).replace(/\|/g, '\\|'));
  if (head) {
    const h = cells(head);
    return [`| ${h.join(' | ')} |`, `| ${h.map(() => '---').join(' | ')} |`, ...rows.map((r) => `| ${cells(r).join(' | ')} |`)].join('\n');
  }
  const out = [];
  for (const r of rows) {
    const c = cells(r);
    if (c.length === 1) out.push(`${out.length ? '\n' : ''}**${c[0]}**\n`);
    else out.push(`- ${c[0]}: ${c.slice(1).join(' ')}`);
  }
  return out.join('\n');
}

function blocks(parent) {
  const out = [];
  for (const node of parent.childNodes) {
    if (node.nodeType === 3) {
      if (node.textContent.trim()) out.push(clean(squash(node.textContent)));
      continue;
    }
    if (node.nodeType !== 1) continue;
    const el = node;
    const tag = el.tagName.toLowerCase();
    if (tag === 'section') out.push(...blocks(el));
    else if (/^h[1-6]$/.test(tag)) out.push(`${'#'.repeat(+tag[1])} ${clean(inline(el))}`);
    else if (tag === 'p') out.push(clean(inline(el)));
    else if (tag === 'ul' || tag === 'ol') out.push([...el.children].map((li, i) => `${tag === 'ol' ? `${i + 1}.` : '-'} ${clean(inline(li))}`).join('\n'));
    else if (tag === 'dl') {
      const items = [];
      for (const c of el.children) {
        if (c.tagName === 'DT') items.push(`- **${clean(inline(c)).replace(/\*\*/g, '')}**:`);
        else if (c.tagName === 'DD' && items.length) items[items.length - 1] += ` ${clean(inline(c))}`;
      }
      out.push(items.join('\n'));
    } else if (tag === 'table') out.push(table(el));
    else if (tag === 'figure') {
      const img = el.querySelector('img');
      const cap = el.querySelector('figcaption');
      out.push(`![${img.getAttribute('alt')}](${absolute(img.getAttribute('src'), HELP_URL)})${cap ? `\n*${clean(inline(cap))}*` : ''}`);
    } else if (el.classList.contains('banner')) out.push(`> ${clean(inline(el))}`);
    else out.push(...blocks(el));
  }
  return out.filter(Boolean);
}

const lede = clean(inline(article.querySelector('.lede')));
const md = [
  '<!-- Generated from app/src/routes/help/+page.svelte by `npm run help:export` in app/. Edit the page, not this file. -->',
  '',
  ...blocks(article).join('\n\n').split('\n'),
  '',
  '---',
  '',
  `This is the help page of the JZP Font Builder (${BUILDER}) as plain text. The same page with screenshots: ${HELP_URL}. The JianZiPu font itself, with its typing guide: ${SITE}/.`,
  ''
].join('\n');

// ── llms.txt ───────────────────────────────────────────────────────────────────────────────────

const llms = [
  '# JianZiPu Font',
  '',
  '> JianZiPu (减字谱) is a font for guqin tablature: you type a short code such as `s7k5` (or 名七勾五) and the font swaps each piece for a drawn part and stacks them into one 减字 character. The JZP Font Builder is the web app where the font is made: the drawn parts (glyphs), how each part is typed (spellings), and how the parts sit together (layouts).',
  '',
  `The Builder (${BUILDER}) runs in the browser and asks testers to sign in, so its pages can't be read without one. Its help is published here instead.`,
  '',
  '## Docs',
  '',
  `- [Builder help, full text](${SITE}/help.md): every screen, how words are typed, saving, drafts, keyboard shortcuts, and what each message means and how to fix it`,
  `- [Builder help, with screenshots](${HELP_URL})`,
  `- [The JianZiPu font](${SITE}/): download, and the typing guide (layout, numbers and decimals, modifiers, chords, vertical text, glossary)`,
  '',
  '## Help sections',
  '',
  ...sections.map((s) => `- [${s.title}](${HELP_URL}#${s.id})`),
  ''
].join('\n');

// ── The public help page ───────────────────────────────────────────────────────────────────────

// Svelte's hydration comments and scoped class names mean nothing outside the app
const strip = (root) => {
  const walker = doc.createTreeWalker(root, 128 /* comments */);
  const dead = [];
  while (walker.nextNode()) dead.push(walker.currentNode);
  dead.forEach((c) => c.remove());
  for (const el of root.querySelectorAll('[class]')) {
    const keep = [...el.classList].filter((c) => !/^s-/.test(c));
    if (keep.length) el.setAttribute('class', keep.join(' '));
    else el.removeAttribute('class');
  }
  for (const a of root.querySelectorAll('a[href]')) a.setAttribute('href', absolute(a.getAttribute('href'), ''));
  for (const img of root.querySelectorAll('img[src]')) img.setAttribute('src', absolute(img.getAttribute('src'), ''));
  for (const el of root.querySelectorAll('[aria-current]')) el.removeAttribute('aria-current');
};
const nav = doc.querySelector('nav.toc');
strip(nav);
strip(article);

const page = `<!DOCTYPE html>
<!-- Generated from app/src/routes/help/+page.svelte by \`npm run help:export\` in app/. Edit the page, not this file. -->
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JZP Font Builder help</title>
  <meta name="description" content="${lede.replace(/"/g, '&quot;')}">
  <link rel="canonical" href="${HELP_URL}">
  <link rel="alternate" type="text/markdown" href="/help.md" title="The help as Markdown">
  <link rel="icon" href="/favicon.ico">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400..700&family=Literata:opsz,wght@7..72,400..700&display=swap" rel="stylesheet">
  <style>
    :root { --bg: #f4f3f0; --panel: #ebe9e4; --ink: #1d1c1a; --muted: #5f5b54; --border: #d6d3cc; --link: #2456a6; --accent: #b03a2e; --sel: #e3ebf7; }
    @media (prefers-color-scheme: dark) { :root { --bg: #1c1b19; --panel: #262522; --ink: #ecebe7; --muted: #a8a49c; --border: #3a3834; --link: #8db4f0; --accent: #e0705f; --sel: #24324a; } }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.55 Literata, "Noto Serif SC", "Songti SC", serif; }
    a { color: var(--link); }
    header { border-bottom: 1px solid var(--border); padding: 12px 24px; display: flex; gap: 20px; align-items: baseline; flex-wrap: wrap; }
    header .name { font: 600 20px "EB Garamond", serif; color: var(--ink); text-decoration: none; }
    .layout { display: grid; grid-template-columns: 200px minmax(0, 720px); gap: 48px; padding: 32px 24px 96px; justify-content: center; }
    .toc { position: sticky; top: 24px; align-self: start; display: flex; flex-direction: column; gap: 2px; }
    .toc-title { font: 600 17px "EB Garamond", serif; margin: 0 0 8px; }
    .toc a { padding: 4px 10px; border-left: 2px solid transparent; color: var(--muted); text-decoration: none; }
    .toc a:hover { color: var(--ink); border-left-color: var(--link); background: var(--sel); }
    h1, h2, h3 { font-family: "EB Garamond", serif; font-weight: 600; line-height: 1.2; }
    h1 { font-size: 34px; margin: 0 0 12px; } h2 { font-size: 26px; margin: 0 0 12px; } h3 { font-size: 19px; margin: 28px 0 8px; }
    .lede { font-size: 17px; color: var(--muted); margin: 0 0 32px; }
    section { padding-top: 24px; margin-bottom: 32px; border-top: 1px solid var(--border); scroll-margin-top: 16px; }
    code, kbd { font: 13px ui-monospace, Menlo, Consolas, monospace; background: var(--panel); border: 1px solid var(--border); border-radius: 3px; padding: 0 4px; white-space: nowrap; }
    dl { display: grid; grid-template-columns: max-content 1fr; gap: 8px 24px; } dt { font-weight: 600; } dd { margin: 0; }
    table { width: 100%; border-collapse: collapse; margin: 0 0 20px; }
    th, td { text-align: left; vertical-align: top; padding: 6px 10px; border-bottom: 1px solid var(--border); }
    thead th { font-size: 13px; color: var(--muted); }
    figure { margin: 16px 0 24px; } figure img { width: 100%; height: auto; border: 1px solid var(--border); border-radius: 4px; }
    figcaption { font-size: 13px; color: var(--muted); margin-top: 6px; }
    svg { width: 16px; height: 16px; stroke-width: 1.5; vertical-align: -3px; stroke-linecap: square; }
    .pill, .chip { display: inline-flex; align-items: center; gap: 4px; padding: 0 8px; border: 1px solid var(--border); border-radius: 999px; font-size: 13px; white-space: nowrap; }
    .pill.danger { color: var(--accent); border-color: currentColor; } .pill.draft, .chip.dashed { border-style: dashed; }
    .banner { display: flex; gap: 10px; padding: 10px 14px; border: 1px solid var(--border); border-radius: 4px; background: var(--panel); }
    .miss { color: var(--accent); }
    @media (max-width: 760px) { .layout { grid-template-columns: minmax(0, 1fr); gap: 24px; padding: 24px 16px 64px; } .toc { position: static; } dl { grid-template-columns: minmax(0, 1fr); } }
  </style>
</head>
<body>
  <header>
    <a class="name" href="/">JianZiPu Font</a>
    <a href="${BUILDER}/">Open the Builder</a>
    <a href="/help.md">This page as plain text (Markdown)</a>
  </header>
  <div class="layout">
    ${nav.outerHTML}
    ${article.outerHTML}
  </div>
</body>
</html>
`;

// ── Write, or check ────────────────────────────────────────────────────────────────────────────

const outputs = [
  [resolve(SITE_DIR, 'help/index.html'), page],
  [resolve(SITE_DIR, 'help.md'), md],
  [resolve(SITE_DIR, 'llms.txt'), llms],
  [resolve(APP, 'static/llms.txt'), llms]
];
let stale = 0;
for (const [path, text] of outputs) {
  const name = relative(resolve(APP, '..'), path);
  if (check) {
    if (!existsSync(path) || readFileSync(path, 'utf8') !== text) { console.error(`stale: ${name}`); stale++; }
  } else {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, text);
    console.log(`wrote ${name}`);
  }
}
if (stale) {
  console.error('The public help is out of date with app/src/routes/help/+page.svelte: run `npm run help:export` in app/ and commit.');
  process.exit(1);
}
