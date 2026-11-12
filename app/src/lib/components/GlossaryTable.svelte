<script lang="ts">
  // Glyphs > Glossary: the font page's glossary (site/glossary.json), a section at a time, rows in
  // page order. A row is one glyph or a word written together (:少息); its ASCII, Chinese and
  // pinyin come from the spellings, its meaning is its own; in a usage section, its example word
  // too (Usage: type it in ASCII or Chinese and the other is made from the glyphs' spellings). Drag a
  // row by its grip to move it (a finger: press and hold the grip first); fold a section by its
  // title. + Add types a glyph or a word as in the font (unsaved spellings and new glyphs
  // included). Every edit is one undo step, saved with Save.
  import * as I from '$lib/icons';
  import { api, type WordPiece } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { Hold } from '$lib/hold';
  import * as T from '$lib/typing';
  import { exampleHtml, exampleText, glyphsOfRow, isWord, mainSpellings, moveRow, refuse, rowKey, rowName, usageFrom,
    type GlyphRow, type GRow, type Section } from '$lib/glossary';
  import Glyph from './Glyph.svelte';
  import GlossaryExample from './GlossaryExample.svelte';

  let { q = '', focus = null, onnotice, onopen }: {
    q?: string;
    /** from List view's Glossary column: the glyph to show, in this section ('' = it's in none yet) */
    focus?: { sid: string; glyph: string } | null;
    onnotice?: (text: string, undo?: boolean) => void;
    onopen?: (glyph: string) => void;
  } = $props();
  // the glyph shown: from List view, then wherever it's added from here
  let shownGlyph = $state<{ sid: string; glyph: string } | null>(null);
  $effect(() => { shownGlyph = focus; });

  let sections = $derived(app.glossarySections);
  let saved = $derived(JSON.parse(app.savedGlossaryJson) as Record<string, GRow[]>);
  const rowsOf = (sid: string) => app.glossary[sid] ?? [];
  const sec = (sid: string) => sections.find((s) => s.id === sid)!;
  const KIND: Record<Section['kind'], string> = {
    usage: 'each glyph in an example word', vertical: 'each typed on its own, after a colon', hidden: 'not on the page'
  };

  // ---------------------------------------------------------------- what a row shows

  const vertical = (s: Section) => s.kind !== 'usage';
  function asciiOf(g: string): string[] {
    const sp = T.get(app.typing, g), p = T.partners(app.typing);
    const own = [sp.latin, sp.latin_alt, sp.common].filter(Boolean);
    const v = sp.vert_variant ? T.get(app.typing, sp.vert_variant) : null;
    return own.length || !p[g] ? [...own, ...(v ? [v.latin, v.latin_alt, v.common].filter(Boolean) : [])] : [T.shown(app.typing, g, 'latin').value].filter(Boolean);
  }
  const zhOf = (g: string) => { const s = T.get(app.typing, g); return [...new Set([s.simplified || T.shown(app.typing, g, 'simplified').value, s.traditional].filter(Boolean))]; };
  const pyOf = (g: string) => T.get(app.typing, g).pinyin || T.shown(app.typing, g, 'pinyin').value;
  function ascii(r: GRow, s: Section): string {
    const pre = vertical(s) ? ':' : '';
    if (isWord(r)) return pre + r.glyphs.map((g) => asciiOf(g)[0] ?? '?').join('');
    return asciiOf(r.glyph).map((a) => pre + a).join(', ');
  }
  function chinese(r: GRow, s: Section): string {
    const pre = vertical(s) ? ':' : '';
    if (isWord(r)) return pre + r.glyphs.map((g) => zhOf(g)[0] ?? '?').join('');
    return zhOf(r.glyph).map((z) => pre + z).join(', ');
  }
  const pinyin = (r: GRow) => glyphsOfRow(r).map(pyOf).filter(Boolean).join(' ');
  /** A glyph the row names that isn't one any more (renamed or deleted elsewhere). */
  const lost = (r: GRow) => glyphsOfRow(r).filter((g) => !app.known.has(g) && !(g in app.typing) && !(g in app.svgs));
  /** Not in the saved file at this place: marked until Save. */
  const changed = (sid: string, i: number) => JSON.stringify(saved[sid]?.[i] ?? null) !== JSON.stringify(rowsOf(sid)[i]);
  const matches = (r: GRow, s: Section) => {
    const t = q.trim().toLowerCase();
    return !t || [rowName(r), ...glyphsOfRow(r), ascii(r, s), chinese(r, s), pinyin(r), r.meaning ?? ''].join(' ').toLowerCase().includes(t);
  };

  // ---------------------------------------------------------------- edits

  function edit(label: string, fn: (rows: Record<string, GRow[]>) => Record<string, GRow[]>) {
    app.editGlossary(label, fn);
  }
  function move(from: { sid: string; index: number }, to: { sid: string; index: number }) {
    const r = rowsOf(from.sid)[from.index];
    if (!r) return;
    if (from.sid === to.sid && (to.index === from.index || to.index === from.index + 1)) return;
    if (from.sid !== to.sid) {
      const why = refuse(app.glossary, r, sec(to.sid));
      if (why) { onnotice?.(why); return; }
    }
    edit(from.sid === to.sid ? `Move ${rowName(r)} in ${from.sid}` : `Move ${rowName(r)} to ${to.sid}`, (rows) => moveRow(rows, from, to));
    if (from.sid !== to.sid) onnotice?.(`Moved ${rowName(r)} to ${sec(to.sid).title}.`, true);
  }
  function setMeaning(sid: string, i: number, v: string) {
    const r = rowsOf(sid)[i], m = v.trim();
    if (!r || (r.meaning ?? '') === m) return;
    edit(`${rowName(r)}: meaning in ${sid}`, (rows) => {
      const list = [...rows[sid]];
      const { meaning: _, ...rest } = list[i];
      list[i] = (m ? { ...rest, meaning: m } : rest) as GRow;
      return { ...rows, [sid]: list };
    });
  }
  function remove(sid: string, i: number) {
    const r = rowsOf(sid)[i];
    edit(`Remove ${rowName(r)} from ${sid}`, (rows) => ({ ...rows, [sid]: rows[sid].filter((_, j) => j !== i) }));
    onnotice?.(`Removed ${rowName(r)} from ${sec(sid).title}.`, true);
  }

  // ---------------------------------------------------------------- folding

  const FOLD_KEY = 'jzp-glossary-folded';
  let folded = $state<string[]>((() => { try { return JSON.parse(localStorage.getItem(FOLD_KEY) ?? '[]'); } catch { return []; } })());
  $effect(() => { const v = JSON.stringify(folded); try { localStorage.setItem(FOLD_KEY, v); } catch { /* not kept */ } });
  /** Folded, unless a search or a glyph from List view needs it open. */
  const isFolded = (sid: string) => folded.includes(sid) && !q.trim() && shownGlyph?.sid !== sid;
  const fold = (sid: string) => (folded = folded.includes(sid) ? folded.filter((x) => x !== sid) : [...folded, sid]);

  // ---------------------------------------------------------------- Usage: a row's example word

  /** The example a usage row shows: its own, else the section's. */
  const templateOf = (r: GRow, s: Section): [string, string] => (!isWord(r) && r.usage) || s.usage || ['', ''];
  /** The example as typed in the font (ASCII, else Chinese), to draw it. */
  function exampleOf(r: GRow, s: Section): string {
    if (isWord(r)) return '';
    const [a, z] = templateOf(r, s), [sa, sz] = mainSpellings(app.typing, r.glyph);
    return a ? exampleText(a, sa) : z ? exampleText(z, sz) : '';
  }
  // every example in view, drawn by one request through the unsaved spellings (as Try it does)
  let drawn = $state<Record<string, WordPiece[]>>({});
  let drawKey = '';
  let drawTimer: ReturnType<typeof setTimeout> | null = null;
  $effect(() => {
    const words = [...new Set(sections.filter((s) => s.kind === 'usage' && !isFolded(s.id))
      .flatMap((s) => rowsOf(s.id).map((r) => exampleOf(r, s))).filter((w) => w && !(w in drawn)))];
    const typed = app.typedWith, design = app.design;
    const key = JSON.stringify([words, typed.rows.length, Object.keys(typed.svgs)]);
    if (!words.length || !design || key === drawKey) return;
    if (drawTimer) clearTimeout(drawTimer);
    drawTimer = setTimeout(async () => {
      drawKey = key;
      try {
        const r = await api.words(design, words, typed);
        if (r.ok) drawn = { ...drawn, ...Object.fromEntries(r.words.map((w) => [w.word, w.pieces])) };
      } catch { /* the example shows as text only */ }
    }, 250);
  });
  // a spelling or a drawing changed: draw the examples again
  $effect(() => { JSON.stringify(app.typing); Object.keys(app.extraSvgs).join(); drawn = {}; drawKey = ''; });

  let editing = $state<string | null>(null);          // `${sid}:${i}:${'a' | 'z'}`
  let usageNote = $state<{ key: string; level: 'error' | 'warn'; text: string } | null>(null);
  let usageBusy = $state<string | null>(null);

  /** The example, typed in one language: the other is made from the glyphs' spellings and typed back
   *  to check it gives the same glyphs. Empty: the row takes the section's example again. */
  async function setUsage(sid: string, i: number, value: string, zh: boolean) {
    editing = null;
    const r = rowsOf(sid)[i] as GlyphRow, s = sec(sid), key = `${sid}:${i}`;
    if (!r || isWord(r) || !app.design) return;
    const cur = templateOf(r, s), [sa, sz] = mainSpellings(app.typing, r.glyph);
    const text = value.trim();
    if (text === exampleText(cur[zh ? 1 : 0], zh ? sz : sa)) return;
    usageNote = null;
    const put = (u: [string, string] | null) => edit(u ? `${r.glyph}: example in ${sid}` : `${r.glyph}: the section's example in ${sid}`, (rows) => {
      const list = [...rows[sid]];
      const { usage: _, ...rest } = list[i] as GlyphRow;
      list[i] = u ? { ...rest, usage: u } : rest;
      return { ...rows, [sid]: list };
    });
    if (!text) { if (r.usage) put(null); return; }
    usageBusy = key;
    try {
      const typed = (await api.words(app.design, [text], app.typedWith)).words?.[0] as unknown as { glyphs: string[]; texts: string[]; clusters?: number[] } | undefined;
      if (!typed?.texts) { usageNote = { key, level: 'error', text: "It couldn't be typed: is the Builder's server running?" }; return; }
      const u = usageFrom(text, typed, r.glyph, app.typing);
      if ('error' in u) { usageNote = { key, level: 'error', text: u.error }; return; }
      const otherLang = zh ? 'ASCII' : 'Chinese';
      let other = u.other;
      if (other === null) {
        other = cur[zh ? 0 : 1];
        usageNote = { key, level: 'warn', text: `${u.missing.join(', ')} has no ${otherLang} spelling, so the ${otherLang} stays as it was: click it to change it.` };
      } else {
        const made = exampleText(other, zh ? sa : sz);
        const back = (await api.words(app.design, [made], app.typedWith)).words?.[0];
        const strip = (gs: string[]) => gs.filter((g) => g !== 'blank_colon').join(' ');
        if (back && strip(back.glyphs) !== strip(typed.glyphs))
          usageNote = { key, level: 'warn', text: `The ${otherLang} made from it, ${made}, types something else: click it to fix it.` };
      }
      put(zh ? [other, u.source] : [u.source, other]);
    } catch (e) { usageNote = { key, level: 'error', text: (e as Error).message }; }
    finally { usageBusy = null; }
  }

  // ---------------------------------------------------------------- editing a row: type it again

  /** How the row was entered, to edit it: what was typed, else its ASCII spelling, else its Chinese. */
  function entryOf(r: GRow, s: Section): string {
    if (r.typed) return r.typed;
    const a = ascii(r, s).split(', ')[0];
    return a && !a.includes('?') ? a : chinese(r, s).split(', ')[0] || rowName(r);
  }
  let rowEdit = $state<{ sid: string; i: number; text: string } | null>(null);
  let rowNote = $state<{ sid: string; i: number; text: string } | null>(null);
  let rowBusy = $state(false);
  async function saveRow() {
    if (!rowEdit) return;
    const { sid, i, text } = rowEdit, old = rowsOf(sid)[i];
    if (!old) { rowEdit = null; return; }
    if (text.trim() === entryOf(old, sec(sid))) { rowEdit = null; return; }
    rowBusy = true; rowNote = null;
    try {
      const r = await resolve(text);
      if ('error' in r) { rowNote = { sid, i, text: r.error }; return; }
      const why = refuse(app.glossary, r, sec(sid), i);
      if (why) { rowNote = { sid, i, text: why }; return; }
      // the meaning stays; the example too while the glyph is the same
      const keepUsage = !isWord(old) && !isWord(r) && old.glyph === r.glyph && old.usage ? { usage: old.usage } : {};
      const next = { ...r, ...(old.meaning ? { meaning: old.meaning } : {}), ...keepUsage, typed: text.trim() } as GRow;
      edit(`Edit ${rowName(old)} in ${sid}`, (rows) => ({ ...rows, [sid]: rows[sid].map((x, j) => (j === i ? next : x)) }));
      rowEdit = null;
    } catch (e) { rowNote = { sid, i, text: (e as Error).message }; }
    finally { rowBusy = false; }
  }

  // ---------------------------------------------------------------- + Add

  let adding = $state<Record<string, string>>({});
  let addNote = $state<{ sid: string; level: 'error' | 'ok'; text: string } | null>(null);
  let busy = $state<string | null>(null);

  /** What typing `text` gives: one glyph, or a word's glyphs and the Chinese they spell (少息). */
  async function resolve(text: string): Promise<GRow | { error: string }> {
    const t = text.trim().replace(/^[:：]/, '');
    if (!t) return { error: 'Type a glyph or a word as in the font (k, 勾, :shaoxi), or a glyph name (lg_gou).' };
    if (app.known.has(t) || t in app.typing || t in app.svgs) return { glyph: t };
    if (!app.design) return { error: 'Nothing loaded yet.' };
    const r = await api.typingPreview({ design: app.design, rows: T.toRecords(app.typing), words: [':' + t], roundtrip: false,
      svg_names: app.extraGlyphs, svgs: app.extraSvgs });
    if (!r.ok || !r.words?.length) return { error: r.error ?? "it couldn't be typed" };
    const typed = r.words[0];
    // a vertical form counts as its glyph (:san types md_san2, the row is md_san's)
    const horizontal = Object.fromEntries(Object.entries(app.typing).filter(([, s]) => s.vert_variant).map(([g, s]) => [s.vert_variant, g]));
    const gs = typed.glyphs.filter((g) => g !== 'blank_colon').map((g) => horizontal[g] ?? g);
    const stray = typed.glyphs.map((g, i) => ({ g, text: typed.texts?.[i] ?? g }))
      .filter(({ g }) => g !== 'blank_colon' && (g === '.notdef' || !app.known.has(g))).map(({ text }) => text);
    const lacking = new Set(Object.values(r.missing_chars ?? {}).flat().join(''));
    if (stray.length && stray.every((x) => [...x].every((ch) => lacking.has(ch) || /[㐀-鿿]/.test(ch))))
      return { error: `${stray.join(' ')} isn't in the font yet (Build font once, or add the base font), so it can't be typed in Chinese here: type it in Latin (:shaoxi), or give the glyph name.` };
    if (stray.length) return { error: `${stray.join(' ')} isn't a glyph's spelling: check the spellings, or give the glyph name.` };
    if (!gs.length) return { error: 'That types no glyph.' };
    if (gs.length === 1) return { glyph: gs[0] };
    const zh = gs.map((g) => zhOf(g)[0]);
    return { word: zh.every(Boolean) ? zh.join('') : t, glyphs: gs };
  }

  async function add(sid: string) {
    busy = sid; addNote = null;
    try {
      const r = await resolve(adding[sid] ?? '');
      if ('error' in r) { addNote = { sid, level: 'error', text: r.error }; return; }
      const why = refuse(app.glossary, r, sec(sid));
      if (why) { addNote = { sid, level: 'error', text: why }; return; }
      const typed = (adding[sid] ?? '').trim();
      edit(`Add ${rowName(r)} to ${sid}`, (rows) => ({ ...rows, [sid]: [...(rows[sid] ?? []), { ...r, typed }] }));
      addNote = { sid, level: 'ok', text: `Added ${rowName(r)}${isWord(r) ? ` (${r.glyphs.join(' + ')})` : ''} at the end: drag it where it goes.` };
      adding[sid] = '';
      if (shownGlyph?.sid === '' && glyphsOfRow(r).includes(shownGlyph.glyph)) shownGlyph = { sid, glyph: shownGlyph.glyph };
    } catch (e) { addNote = { sid, level: 'error', text: (e as Error).message }; }
    finally { busy = null; }
  }

  // a glyph from List view's "not in the glossary": which section to put it in
  let target = $state('');
  function addFocused() {
    if (!shownGlyph || !target) return;
    const r: GRow = { glyph: shownGlyph.glyph };
    const why = refuse(app.glossary, r, sec(target));
    if (why) { onnotice?.(why); return; }
    edit(`Add ${shownGlyph.glyph} to ${target}`, (rows) => ({ ...rows, [target]: [...(rows[target] ?? []), r] }));
    shownGlyph = { sid: target, glyph: shownGlyph.glyph };
  }
  $effect(() => {
    if (!shownGlyph?.sid) return;
    const el = document.querySelector(`[data-sid="${CSS.escape(shownGlyph.sid)}"][data-glyphs~="${CSS.escape(shownGlyph.glyph)}"]`);
    el?.scrollIntoView({ block: 'center' });
  });

  // ---------------------------------------------------------------- drag

  let drag = $state<{ sid: string; index: number; x: number; y: number; name: string } | null>(null);
  let drop = $state<{ sid: string; index: number } | null>(null);
  let root = $state<HTMLElement>();
  let scrollTimer: ReturnType<typeof setInterval> | null = null;
  let lastY = 0;

  function grab(e: PointerEvent, sid: string, index: number) {
    if (e.button !== 0) return;
    e.preventDefault();
    const name = rowName(rowsOf(sid)[index]);
    const begin = () => { drag = { sid, index, x: e.clientX, y: e.clientY, name }; drop = null; };
    const hold = e.pointerType === 'mouse' ? null : new Hold({ onlift: begin, ontap: () => {} });
    if (hold) hold.down(e.clientX, e.clientY); else begin();
    const mv = (ev: PointerEvent) => {
      if (hold && !hold.move(ev.clientX, ev.clientY)) return;
      if (!drag) return;
      ev.preventDefault();
      drag = { ...drag, x: ev.clientX, y: ev.clientY };
      lastY = ev.clientY;
      drop = targetAt(ev.clientX, ev.clientY);
    };
    const up = () => {
      if (hold) hold.up();
      window.removeEventListener('pointermove', mv);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('pointercancel', cancel);
      window.removeEventListener('keydown', esc);
      if (scrollTimer) { clearInterval(scrollTimer); scrollTimer = null; }
      const d = drag, t = drop;
      drag = null; drop = null;
      if (d && t) move({ sid: d.sid, index: d.index }, t);
    };
    const cancel = () => { drop = null; up(); };
    const esc = (ev: KeyboardEvent) => { if (ev.key === 'Escape') cancel(); };
    window.addEventListener('pointermove', mv, { passive: false });
    window.addEventListener('pointerup', up);
    window.addEventListener('pointercancel', cancel);
    window.addEventListener('keydown', esc);
    // near the top or bottom of the list, keep scrolling while the row is held there
    scrollTimer = setInterval(() => {
      const box = scroller();
      if (!drag || !box) return;
      const r = box.getBoundingClientRect(), edge = 48;
      const dy = lastY < r.top + edge ? -14 : lastY > r.bottom - edge ? 14 : 0;
      if (dy) { box.scrollTop += dy; drop = targetAt(drag.x, drag.y); }
    }, 30);
  }
  const scroller = () => root?.closest<HTMLElement>('.grid-wrap') ?? null;

  /** The gap under the pointer: before the row it's over (upper half) or after it (lower half);
   *  over a section's add line or folded title: at its end; over an open section's title: at its top. */
  function targetAt(x: number, y: number): { sid: string; index: number } | null {
    const el = document.elementFromPoint(x, y)?.closest<HTMLElement>('[data-drop]');
    if (!el) return drop;
    const sid = el.dataset.sid!, i = Number(el.dataset.i);
    if (el.dataset.drop === 'end') return { sid, index: rowsOf(sid).length };
    if (el.dataset.drop === 'start') return { sid, index: 0 };
    const r = el.getBoundingClientRect();
    return { sid, index: y < r.top + r.height / 2 ? i : i + 1 };
  }
  const gapBefore = (sid: string, i: number) => !!drag && drop?.sid === sid && drop.index === i;
  const okDrop = $derived.by(() => {
    if (!drag || !drop || drop.sid === drag.sid) return true;
    return !refuse(app.glossary, rowsOf(drag.sid)[drag.index], sec(drop.sid));
  });
</script>

<div class="gloss" bind:this={root} class:dragging={!!drag}>
  <p class="muted small intro">
    The font page's glossary, a section at a time, in page order. A row is one glyph, or a word written together (:少息);
    its ASCII, 中文 and 拼音 come from the spellings. Drag a row by its grip to move it, within a section or to another.
    Fold a section by its title. Save writes site/glossary.json; a release puts it on jianzipufont.com.
    <button class="lnk" onclick={() => (folded = folded.length ? [] : sections.map((x) => x.id))}>{folded.length ? 'Unfold every section' : 'Fold every section'}</button>
  </p>
  {#if !sections.length}
    <div class="banner info"><span class="ic"><I.Info /></span> This copy of the Builder has no site/glossary.json, so there's no glossary to edit here.</div>
  {/if}
  {#if shownGlyph && !shownGlyph.sid}
    <div class="banner draft"><span class="ic"><I.Warn /></span>
      <span>{shownGlyph.glyph} isn't in the glossary, so the glossary check reports it. Add it to</span>
      <select bind:value={target} aria-label="Section to add {shownGlyph.glyph} to">
        <option value="" disabled>a section…</option>
        {#each sections as s (s.id)}<option value={s.id}>{s.title}</option>{/each}
      </select>
      <button onclick={addFocused} disabled={!target}>Add</button>
      <button class="quiet" onclick={() => (shownGlyph = null)} aria-label="Close" data-tip="Close"><I.Close size={14} /></button>
    </div>
  {/if}

  {#each sections as s (s.id)}
    {@const rows = rowsOf(s.id)}
    {@const shown = rows.map((r, i) => ({ r, i })).filter(({ r }) => matches(r, s))}
    {#if !q.trim() || shown.length}
    {@const usage = s.kind === 'usage'}
    <section class="sec" class:hidden={s.kind === 'hidden'} aria-labelledby="gs-{s.id}">
      <h3 id="gs-{s.id}" data-drop={isFolded(s.id) ? 'end' : 'start'} data-sid={s.id} data-i={rows.length} class:gap={!!drag && isFolded(s.id) && drop?.sid === s.id} class:no={!okDrop && drop?.sid === s.id}>
        <button class="quiet fold" onclick={() => fold(s.id)} aria-expanded={!isFolded(s.id)} aria-controls="gb-{s.id}">
          {#if isFolded(s.id)}<I.Folded size={14} />{:else}<I.Unfolded size={14} />{/if}<span>{s.title}</span></button>
        <span class="muted small">· {rows.length} row{rows.length === 1 ? '' : 's'} · {KIND[s.kind]}</span>
        {#if JSON.stringify(saved[s.id] ?? []) !== JSON.stringify(rows)}<span class="pill draft"><I.Unsaved size={12} /> unsaved</span>{/if}</h3>
      {#if !isFolded(s.id)}
      <div class="scroll" id="gb-{s.id}">
      <table class:usage>
        <colgroup><col class="c-grip" /><col class="c-out" /><col class="c-a" /><col class="c-z" /><col class="c-p" /><col class="c-m" />{#if usage}<col class="c-u" />{/if}<col class="c-act" /></colgroup>
        <thead><tr><th></th><th>Output</th><th>ASCII</th><th>中文</th><th>拼音</th><th>Meaning</th>{#if usage}<th title="The example word the page shows for it: click a line to type it, in ASCII or Chinese; the other is made from the glyphs' spellings. Faded: the section's example.">Usage</th>{/if}<th></th></tr></thead>
        <tbody>
          {#each shown as { r, i } (rowKey(r) + i)}
            {@const gone = lost(r)}
            <tr data-drop="row" data-sid={s.id} data-i={i} data-glyphs={glyphsOfRow(r).join(' ')}
              class:changed={changed(s.id, i)} class:on={shownGlyph?.sid === s.id && glyphsOfRow(r).includes(shownGlyph.glyph)}
              class:lifted={drag?.sid === s.id && drag.index === i}
              class:gap-before={gapBefore(s.id, i)} class:gap-after={gapBefore(s.id, i + 1) && i === rows.length - 1}
              class:no={!okDrop && drop?.sid === s.id}>
              <td class="grip"><button class="quiet g" onpointerdown={(e) => grab(e, s.id, i)} disabled={!!q.trim()}
                aria-label="Drag {rowName(r)} to move it" data-tip={q.trim() ? 'Clear the search to drag' : 'Drag to move · a finger: press and hold first'}><I.Grip size={14} /></button></td>
              {#if rowEdit?.sid === s.id && rowEdit.i === i}
                <td colspan="4" class="redit">
                  <!-- svelte-ignore a11y_autofocus -->
                  <input type="text" bind:value={rowEdit.text} autofocus spellcheck="false" aria-label="Type {rowName(r)} again"
                    onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void saveRow(); } else if (e.key === 'Escape') { rowEdit = null; rowNote = null; } }} />
                  <button class="sm" onclick={saveRow} disabled={rowBusy}>{#if rowBusy}<I.Working size={14} />{/if} Done</button>
                  <button class="sm quiet" onclick={() => { rowEdit = null; rowNote = null; }}>Cancel</button>
                  {#if rowNote?.sid === s.id && rowNote.i === i}<span class="small bad" role="status"><I.Problem size={12} /> {rowNote.text}</span>{/if}
                </td>
              {:else}
              <td class="out">
                {#each glyphsOfRow(r) as g, k (g + k)}<button class="ga" onclick={() => onopen?.(g)} aria-label="Show {g}" data-tip="{g}: show it in the glyph panel"><Glyph name={g} size={24} /></button>{/each}
                {#if gone.length}<span class="bad small" title="{gone.join(', ')} isn't a glyph any more: edit the row or remove it"><I.Problem size={12} /> {gone.join(', ')}</span>{/if}
              </td>
              <td class="mono">{ascii(r, s)}</td>
              <td class="zh">{chinese(r, s)}</td>
              <td>{pinyin(r)}</td>
              {/if}
              <td><input type="text" class="meaning" value={r.meaning ?? ''} aria-label="Meaning of {rowName(r)} in {s.id}" placeholder="what it means"
                onchange={(e) => setMeaning(s.id, i, (e.target as HTMLInputElement).value)} /></td>
              {#if usage}
                {@const tpl = templateOf(r, s)}
                {@const sp = isWord(r) ? ['', ''] : mainSpellings(app.typing, r.glyph)}
                {@const key = `${s.id}:${i}`}
                <td class="use" class:def={isWord(r) || !r.usage}>
                  <div class="ex">
                    {#if drawn[exampleOf(r, s)] && !isWord(r)}<GlossaryExample pieces={drawn[exampleOf(r, s)]} mark={r.glyph} />{/if}
                    <div class="lines">
                      {#each [1, 0] as k (k)}
                        {#if editing === `${key}:${k}`}
                          <!-- svelte-ignore a11y_autofocus -->
                          <input type="text" class:zh={k === 1} class:mono={k === 0} value={exampleText(tpl[k], sp[k])} autofocus spellcheck="false"
                            aria-label="{k ? 'Chinese' : 'ASCII'} example for {rowName(r)}"
                            onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); (e.target as HTMLInputElement).blur(); } else if (e.key === 'Escape') { editing = null; } }}
                            onblur={(e) => { if (editing === `${key}:${k}`) void setUsage(s.id, i, (e.target as HTMLInputElement).value, k === 1); }} />
                        {:else}
                          <button class="line" class:zh={k === 1} class:mono={k === 0} disabled={isWord(r) || usageBusy === key}
                            onclick={() => { usageNote = null; editing = `${key}:${k}`; }}
                            data-tip={!isWord(r) && !r.usage ? "The section's example: type this row's own" : 'Click to change it; the other line follows'}>
                            {#if tpl[k]}{@html exampleHtml(tpl[k], sp[k])}{:else}<span class="muted">{k ? '中文' : 'ASCII'} example</span>{/if}</button>
                        {/if}
                      {/each}
                    </div>
                  </div>
                  {#if usageBusy === key}<span class="small muted"><I.Working size={12} /> typing it…</span>{/if}
                  {#if usageNote?.key === key}<span class="small note" class:bad={usageNote.level === 'error'} role="status">{#if usageNote.level === 'error'}<I.Problem size={12} />{:else}<I.Warn size={12} />{/if} {usageNote.text}</span>{/if}
                </td>
              {/if}
              <td class="act">
                <button class="quiet ic" onclick={() => { rowNote = null; rowEdit = { sid: s.id, i, text: entryOf(r, s) }; }} disabled={!!rowEdit && rowEdit.sid === s.id && rowEdit.i === i}
                  aria-label="Edit {rowName(r)}" data-tip="Edit: type it again, as it was entered"><I.EditRow size={14} /></button>
                <button class="quiet ic" onclick={() => remove(s.id, i)} aria-label="Remove {rowName(r)} from {s.id}" data-tip="Remove from this section (Undo brings it back)"><I.Close size={14} /></button>
              </td>
            </tr>
          {/each}
          <tr class="addrow" data-drop="end" data-sid={s.id} data-i={rows.length} class:gap-before={gapBefore(s.id, rows.length) && !rows.length}
            class:no={!okDrop && drop?.sid === s.id}>
            <td></td>
            <td colspan={usage ? 7 : 6}>
              {#if !rows.length}<span class="muted small empty">No rows yet{drag ? ': drop here' : ''}.</span>{/if}
              <span class="add">
                <input type="text" bind:value={adding[s.id]} placeholder={s.kind === 'usage' ? 'Add a glyph: k, 勾 or lg_gou' : 'Add a glyph or a word: 勾, :shaoxi'}
                  aria-label="Add to {s.title}" spellcheck="false"
                  onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void add(s.id); } }} />
                <button class="sm" onclick={() => add(s.id)} disabled={busy === s.id || !adding[s.id]?.trim()}>{#if busy === s.id}<I.Working size={14} />{:else}<I.Plus size={14} />{/if} Add</button>
                {#if addNote?.sid === s.id}<span class="small" class:bad={addNote.level === 'error'} role="status">{#if addNote.level === 'error'}<I.Problem size={12} />{:else}<I.Check size={12} />{/if} {addNote.text}</span>{/if}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
      {/if}
    </section>
    {/if}
  {/each}
  {#if q.trim() && !sections.some((s) => rowsOf(s.id).some((r) => matches(r, s)))}<p class="muted small">No row matches.</p>{/if}
</div>

{#if drag}
  <div class="ghost" style:left="{drag.x + 12}px" style:top="{drag.y - 12}px" aria-hidden="true">{drag.name}</div>
  <div class="sr" role="status">Moving {drag.name}{drop ? ` to ${drop.sid}, place ${drop.index + 1}` : ''}</div>
{/if}

<style>
  .gloss { display: flex; flex-direction: column; gap: var(--space-5); padding-bottom: var(--space-7); }
  .gloss.dragging { user-select: none; cursor: grabbing; }
  .intro { margin: 0; max-width: 760px; }
  .banner select { height: 26px; }
  .sec h3 { margin: 0 0 var(--space-2); font-family: var(--font-display); font-size: var(--t-label); font-weight: 600; display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
  .sec.hidden h3 > span:first-child { color: var(--ink-muted); }
  .scroll { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; min-width: 760px; table-layout: fixed; font-size: var(--t-small); }
  .c-grip { width: 32px; } .c-out { width: 150px; } .c-a { width: 18%; } .c-z { width: 14%; } .c-p { width: 14%; } .c-act { width: 64px; } .c-u { width: 22%; }
  table.usage .c-a, table.usage .c-z, table.usage .c-p { width: 11%; }
  th { text-align: left; font-weight: 600; padding: var(--space-1) var(--space-2); border-bottom: 1px solid var(--border); white-space: nowrap; font-size: var(--t-caption); color: var(--ink-muted); }
  td { padding: 1px var(--space-2); border-bottom: 1px solid var(--hairline); vertical-align: middle; overflow: hidden; text-overflow: ellipsis; }
  tr.changed td:first-child { box-shadow: inset 3px 0 0 var(--status-draft); }
  tr.on td { background: var(--sel-bg); }
  tr.lifted td { opacity: .4; }
  tr.gap-before td { box-shadow: inset 0 2px 0 var(--link); }
  tr.gap-after td { box-shadow: inset 0 -2px 0 var(--link); }
  tr.no.gap-before td, tr.no.gap-after td { box-shadow: inset 0 2px 0 var(--status-danger); }
  td.grip, td.act, td.out { text-overflow: clip; }
  td.grip { padding: 0 3px; }
  .grip .g { width: 24px; min-height: 24px; height: 24px; padding: 0; cursor: grab; touch-action: none; color: var(--ink-muted); }
  .grip .g:disabled { cursor: default; opacity: .4; }
  .out { white-space: normal; line-height: 0; padding-top: 2px; padding-bottom: 2px; }
  .redit { white-space: nowrap; }
  .redit input { width: 280px; height: 26px; font-family: var(--font-mono); margin-right: var(--space-2); }
  .redit .bad { margin-left: var(--space-2); white-space: normal; }
  .ga { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; padding: 0; border: 1px solid transparent; border-radius: var(--radius-sm); background: transparent; cursor: pointer; vertical-align: middle; }
  .ga:hover { border-color: var(--sel-border); background: var(--sel-bg); }
  .zh { font-family: var(--font-serif); font-size: 15px; }
  .mono { font-family: var(--font-mono); }
  .meaning { width: 100%; height: 26px; border-color: transparent; background: transparent; }
  .meaning:hover { border-color: var(--border); }
  .meaning:focus { border-color: var(--link); background: var(--bg-field); }
  .act { white-space: nowrap; text-align: right; }
  .act .ic { width: 24px; min-height: 24px; height: 24px; padding: 0; }
  .sec h3 { padding: 2px 0; border-radius: var(--radius-sm); }
  .sec h3.gap { box-shadow: inset 0 -2px 0 var(--link); }
  .sec h3.gap.no { box-shadow: inset 0 -2px 0 var(--status-danger); }
  .fold { display: inline-flex; align-items: center; gap: var(--space-1); height: auto; min-height: 24px; padding: 0 var(--space-1) 0 0; font: inherit; color: var(--ink); }
  .lnk { margin-left: var(--space-2); border: 0; background: transparent; padding: 0; height: auto; min-height: 24px; color: var(--link); font-size: inherit; cursor: pointer; }
  td.use { padding-top: var(--space-1); padding-bottom: var(--space-1); white-space: normal; }
  .ex { display: flex; align-items: center; gap: var(--space-3); }
  .lines { display: flex; flex-direction: column; min-width: 0; flex: 1; }
  .line { display: block; width: 100%; text-align: left; border: 1px solid transparent; background: transparent; padding: 0 4px; min-height: 24px; height: auto; font-size: var(--t-small); color: var(--ink); cursor: text; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .line:hover:not(:disabled) { border-color: var(--border); }
  .line:disabled { cursor: default; }
  .line :global(.r) { color: var(--accent); }
  td.use.def .line, td.use.def :global(svg.ex) { opacity: .55; }
  .lines input { height: 24px; width: 100%; font-size: var(--t-small); }
  .note { display: block; color: var(--status-draft); white-space: normal; }
  .note.bad { color: var(--status-danger); }
  .addrow td { border-bottom: 0; padding-top: var(--space-2); }
  .add { display: inline-flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
  .add input { width: 260px; height: 26px; font-family: var(--font-mono); }
  .empty { margin-right: var(--space-3); }
  .bad { color: var(--status-danger); }
  .small { font-size: var(--t-caption); }
  .ghost { position: fixed; z-index: 50; pointer-events: none; padding: 2px 8px; background: var(--bg-panel); border: 1px solid var(--sel-border); border-radius: var(--radius-sm); box-shadow: 0 4px 12px rgba(0,0,0,.15); font-size: var(--t-small); }
  .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  @media (max-width: 759.98px) {
    .act .ic, .grip .g { width: var(--control-sm); min-height: var(--control-sm); height: var(--control-sm); }
    .c-grip { width: 40px; } .c-act { width: 80px; }
    .add input { width: 100%; }
  }
</style>
