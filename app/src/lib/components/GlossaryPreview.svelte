<script lang="ts" module>
  // The font page as this server serves it (/site/: main's on the online Builder, your working copy
  // locally), read once, and its font, so the real rows around a coming character draw as on the page.
  let page: Promise<Document | null> | null = null;
  function sitePage(): Promise<Document | null> {
    // its inline handlers (onClick='fillIn(…)') come out of the text first: the content policy reports one even in a parsed copy
    page ??= fetch('/site/').then((r) => (r.ok ? r.text() : null))
      .then((t) => (t ? inert(new DOMParser().parseFromString(t.replace(/\s+on[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, ''), 'text/html')) : null)).catch(() => null);
    return page;
  }
  /** A picture of the page, not the page: none of its script, handlers or links come along. */
  function inert(d: Document): Document {
    d.querySelectorAll('script, button, iframe, form').forEach((e) => e.remove());
    d.querySelectorAll('*').forEach((e) => {
      for (const a of [...e.attributes]) if (/^on/i.test(a.name) || a.name === 'href' || a.name === 'src') e.removeAttribute(a.name);
    });
    return d;
  }
  let font: Promise<unknown> | null = null;
  function pageFont() {
    if (typeof FontFace === 'undefined') return;
    font ??= new FontFace('JianZiPu page', 'url(/site/JianZiPu.ttf)').load().then((f) => document.fonts.add(f)).catch(() => null);
  }
</script>

<script lang="ts">
  // Review › Glossary drafts: one coming character as the font page shows it, in its section's own
  // table between the rows around it (the page's script, placeGhosts in site/index.html, puts it there
  // the same way: after the row named in `after`, else at the section's end). Built from what's typed,
  // so an edit shows before it's saved.
  import type { Stage } from '$lib/upcoming';

  type Ghost = { zh: string; pinyin: string | null; ascii: string | null; meaning: string | null; section: string | null; after: string | null;
    stage: Stage; note: string | null; version: string | null; example?: string[] | null };
  let { g, drawing = null }: { g: Ghost; drawing?: string | null } = $props();

  let host = $state<HTMLDivElement | null>(null);
  let doc = $state<Document | null | undefined>(undefined);
  $effect(() => { pageFont(); void sitePage().then((d) => (doc = d)); });

  const STAGE: Record<Exclude<Stage, 'released'>, (g: Ghost) => string> = {
    planned: () => 'Planned', draft: () => 'Draft design · comments welcome',
    test: (g) => `In release ${(g.version ?? '').replace(/-rc\.\d+$/, '')}`.trim()
  };
  function el(tag: string, cls = '', txt: string | null = null) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  /** The subtitle's table on the page (as tableOf in site/index.html). */
  function tableOf(d: Document, section: string): HTMLTableElement | null {
    const label = d.getElementById(`glossary-${section}`);
    for (let e = label?.nextElementSibling; e; e = e.nextElementSibling) {
      if (e.tagName === 'TABLE') return e.querySelector('td.gid') ? (e as HTMLTableElement) : null;
      if (e.tagName === 'LABEL' || e.tagName === 'H4') return null;
    }
    return null;
  }
  const zhOf = (tr: Element) => {
    const c = tr.querySelector('td.zh')?.cloneNode(true) as Element | undefined;
    c?.querySelector('.py')?.remove();
    return (c?.textContent ?? '').replace(/\s+/g, ' ').trim();
  };
  /** A typed line, red where the Builder marked it (<r>…</r>), as the page writes it. */
  function marked(line: string) {
    const t = el('txs');
    for (const part of line.split(/(<r>[^<]*<\/r>)/)) {
      const m = /^<r>([^<]*)<\/r>$/.exec(part);
      if (m) t.appendChild(el('r', '', m[1])); else if (part) t.appendChild(document.createTextNode(part));
    }
    return t;
  }
  /** The ghost's row, as ghostRow() in site/index.html builds it (without the comment button). */
  function ghostRow(g: Ghost, cols: number): HTMLTableRowElement {
    const tr = el('tr', `ghost ${g.stage}`) as HTMLTableRowElement;
    tr.appendChild(el('td', 'gid')).appendChild(el('span', 'gh-tbd', '—'));
    const zh = tr.appendChild(el('td', 'zh'));
    g.zh.split(' · ').forEach((part, i) => {
      if (i) zh.appendChild(el('span', 'sep', ' · '));
      zh.appendChild(el('span', 'nw', part));
    });
    if (g.pinyin) zh.appendChild(el('span', 'py', g.pinyin));
    const ascii = tr.appendChild(el('td', 'ascii'));
    if (g.ascii) ascii.textContent = g.ascii; else ascii.appendChild(el('span', 'gh-tbd', 'to come'));
    const slip = tr.appendChild(el('td', 'ex')).appendChild(el('div', 'slip'));
    const inn = slip.appendChild(el('div', 'ex-in'));
    if (g.example?.length) { if (g.example[0]) inn.appendChild(marked(g.example[0])); if (g.example[1]) inn.appendChild(marked(g.example[1])); }
    else if (g.stage === 'test' && g.ascii) inn.appendChild(el('txs', '', g.ascii));
    slip.appendChild(el('span', 'ex-arrow', drawing ? '→' : ''));
    const out = slip.appendChild(el('div', 'ex-out'));
    if (drawing) {
      const im = el('img', 'gh-draw' + (g.example?.length ? ' word' : '')) as HTMLImageElement;
      im.src = drawing;
      im.alt = `Draft drawing of ${g.zh}`;
      // a whole example word is drawn in font units (1000 to the em): at the size the rows' examples are set in
      if (g.example?.length) im.addEventListener('load', () => { if (im.naturalWidth) im.style.width = `${Math.round(im.naturalWidth * 40 / 1000)}px`; });
      out.appendChild(im);
    } else out.appendChild(el('div', 'gh-notdrawn', 'not drawn yet'));
    if (cols >= 5) {
      const m = tr.appendChild(el('td', 'meaning'));
      if (g.stage !== 'released') m.appendChild(el('span', `gh-badge ${g.stage}`, STAGE[g.stage](g)));
      if (g.meaning) m.appendChild(el('span', 'gh-def', g.meaning));
      if (g.note) m.appendChild(el('span', 'gh-note', g.note));
    }
    return tr;
  }
  /** A note across the table: how many of the section's rows are left out above or below. */
  function more(n: number, cols: number, where: string) {
    const tr = el('tr', 'more');
    const td = tr.appendChild(el('td', '', `${n} more row${n === 1 ? '' : 's'} ${where}`)) as HTMLTableCellElement;
    td.colSpan = cols;
    return tr;
  }

  let where = $state('');
  $effect(() => {
    if (!host || doc === undefined) return;
    const real = g.section && doc ? tableOf(doc, g.section) : null;
    const table = el('table', real?.className || 'table') as HTMLTableElement;
    let cols = 5;
    if (real) {
      const head = real.tHead?.cloneNode(true) as HTMLTableSectionElement | undefined;
      cols = head?.rows[0]?.cells.length ?? 5;
      // a section with no definitions yet gets the column for the ghost's badge, as the page would show it
      if (head && cols < 5) { head.rows[0].appendChild(el('th', '', 'Definition')); cols = 5; }
      if (head) table.appendChild(head);
      const rows = [...(real.tBodies[0] ?? real).rows].filter((r) => r.querySelector('td.gid'));
      let at = g.after ? rows.findIndex((r) => zhOf(r).split(' · ')[0] === g.after || zhOf(r) === g.after) : -1;
      if (at < 0) at = rows.length - 1;
      const from = Math.max(0, at - 1), to = Math.min(rows.length, at + 2);
      const body = table.appendChild(el('tbody'));
      if (from > 0) body.appendChild(more(from, cols, 'above'));
      rows.slice(from, at + 1).forEach((r) => body.appendChild(r.cloneNode(true)));
      body.appendChild(ghostRow(g, cols));
      rows.slice(at + 1, to).forEach((r) => body.appendChild(r.cloneNode(true)));
      if (to < rows.length) body.appendChild(more(rows.length - to, cols, 'below'));
      // a definition column added above: fill the real rows' empty cell
      body.querySelectorAll('tr:not(.ghost):not(.more)').forEach((r) => { while ((r as HTMLTableRowElement).cells.length < cols) r.appendChild(el('td', 'meaning')); });
      // the page hides a coming row once its character is there (arrived() in site/index.html: the same 中文 in the section)
      const here = rows.find((r) => zhOf(r).split(' · ')[0] === g.zh.split(' · ')[0]);
      where = here ? `The page already has ${g.zh.split(' · ')[0]} in this section (row ${here.querySelector('td.gid')?.textContent?.trim()}), so it hides this coming row.`
        : !g.after ? 'At the end of its section.' : at >= 0 && rows[at] && (zhOf(rows[at]).split(' · ')[0] === g.after || zhOf(rows[at]) === g.after) ? '' : `${g.after} isn't in this section on the page: it goes at the end`;
    } else {
      const head = table.appendChild(el('thead')).appendChild(el('tr'));
      for (const h of ['ID', '中文', 'ASCII', 'Example', 'Definition']) head.appendChild(el('th', h === 'ID' ? 'gid' : '', h));
      table.appendChild(el('tbody')).appendChild(ghostRow(g, 5));
      where = !g.section ? 'Not on the page: give it a section.' : doc ? `The page has no table for section ${g.section}.` : "Couldn't load the font page; the row is shown on its own.";
    }
    host.replaceChildren(table);
  });
</script>

<div class="page" bind:this={host} aria-label="As the font page shows it"></div>
{#if where}<p class="where muted small">{where}</p>{/if}

<style>
  /* the font page's glossary table (site/index.html), in the Builder's tokens */
  .page { overflow-x: auto; border: 1px solid var(--hairline); border-radius: var(--radius-md); background: var(--bg-app); padding: var(--space-2) var(--space-4); }
  .where { margin: var(--space-2) 0 0; }
  .page :global(table) { width: 100%; border-collapse: collapse; font-family: var(--font-serif); color: var(--ink); }
  .page :global(th) { text-align: left; font-weight: 600; font-size: var(--t-small); padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--ink); }
  .page :global(td) { padding: var(--space-3); border-bottom: 1px solid var(--hairline); vertical-align: middle; }
  .page :global(td.gid), .page :global(td.gid a) { font-family: var(--font-mono); font-size: var(--t-caption); color: var(--ink-faint); white-space: nowrap; text-decoration: none; }
  .page :global(td.zh .nw) { white-space: nowrap; font-family: var(--font-cjk); font-size: var(--t-panel); }
  .page :global(td.zh .sep) { color: var(--ink-faint); }
  .page :global(td.zh .py) { display: block; font-size: var(--t-small); color: var(--ink-muted); }
  .page :global(td.ascii) { font-family: var(--font-mono); font-size: var(--t-small); }
  .page :global(.slip) { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; column-gap: var(--space-4); }
  .page :global(.ex-in), .page :global(.ex-out) { justify-self: center; text-align: center; min-width: 0; }
  .page :global(.ex-arrow) { color: var(--ink-faint); }
  .page :global(txs) { display: block; font-family: var(--font-mono), var(--font-cjk); font-size: var(--t-small); word-break: keep-all; }
  .page :global(jzp) { display: inline-block; min-width: 1em; white-space: pre; font-size: 40px; line-height: 1.5em; font-family: 'JianZiPu page', var(--font-cjk); }
  .page :global(r) { color: var(--accent); }
  .page :global(tr.ghost) { background: var(--bg-field); }
  .page :global(tr.ghost > td) { border-bottom-style: dashed; }
  .page :global(tr.ghost.planned td.zh), .page :global(tr.ghost.planned .gh-def) { opacity: .75; }
  .page :global(.gh-def), .page :global(.gh-note) { display: block; margin-top: var(--space-2); }
  .page :global(.gh-note) { font-size: var(--t-small); color: var(--ink-muted); }
  .page :global(.gh-tbd) { color: var(--ink-faint); font-style: italic; font-size: var(--t-small); }
  .page :global(.gh-badge) { display: inline-flex; font-size: var(--t-caption); font-weight: 600; line-height: 1; border-radius: var(--radius-pill); padding: var(--space-2) var(--space-3); border: 1px solid currentColor; white-space: nowrap; }
  .page :global(.gh-badge.planned) { color: var(--ink-muted); border-style: dashed; }
  .page :global(.gh-badge.draft) { color: var(--status-draft); background: var(--status-draft-bg); }
  .page :global(.gh-badge.test) { color: var(--status-saved); background: var(--status-saved-bg); }
  .page :global(.gh-draw) { display: block; width: 64px; height: 64px; object-fit: contain; }
  .page :global(.gh-draw.word) { width: auto; height: auto; max-width: 100%; }
  .page :global(.gh-notdrawn) { width: 64px; height: 64px; border: 1.5px dashed var(--border-strong); border-radius: var(--radius-sm); display: grid; place-items: center; color: var(--ink-faint); font-size: var(--t-caption); text-align: center; line-height: 1.2; }
  .page :global(tr.more td) { padding: var(--space-1) var(--space-3); font-size: var(--t-caption); color: var(--ink-faint); font-style: italic; }
</style>
