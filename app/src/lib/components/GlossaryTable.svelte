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
  import { exampleHtml, exampleText, glyphsOfRow, isWord, mainSpellings, markdown, marksGlyph, moveRow, newId, refuse, rowKey, rowName, usageFrom, verticalTemplate,
    type GRow, type Section } from '$lib/glossary';
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
  let savedLayout = $derived(JSON.parse(app.savedLayoutJson) as typeof app.glossaryLayout);
  const rowsOf = (sid: string) => app.glossary[sid] ?? [];
  const sec = (sid: string) => sections.find((s) => s.id === sid)!;
  /** What a subtitle's rows show where they have no example of their own. */
  const layoutTip = (s: Section) => (s.usage ? `Each glyph in the default example ${s.usage.filter(Boolean).join(' / ')}` : 'Each typed on its own, after a colon where it needs one');

  // ---------------------------------------------------------------- what a row shows

  /** No default example: each row typed on its own (a "vertical" section, as they were called). */
  const vertical = (s: Section) => !s.usage;
  function asciiOf(g: string): string[] {
    const sp = T.get(app.typing, g), p = T.partners(app.typing);
    const own = [sp.latin, sp.latin_alt, sp.common].filter(Boolean);
    const v = sp.vert_variant ? T.get(app.typing, sp.vert_variant) : null;
    return own.length || !p[g] ? [...own, ...(v ? [v.latin, v.latin_alt, v.common].filter(Boolean) : [])] : [T.shown(app.typing, g, 'latin').value].filter(Boolean);
  }
  const zhOf = (g: string) => { const s = T.get(app.typing, g); return [...new Set([s.simplified || T.shown(app.typing, g, 'simplified').value, s.traditional].filter(Boolean))]; };
  const pyOf = (g: string) => T.get(app.typing, g).pinyin || T.shown(app.typing, g, 'pinyin').value;
  /** The colon a vertical word starts with, unless the font sets it vertically by itself (shang, not :shang). */
  const colonFor = (...gs: string[]) => (gs.some((g) => app.verticalOnly.has(g)) ? '' : ':');
  /** The row is typed on its own after a colon: a vertical section's row or a word, unless its own example isn't a
   *  vertical word (/ in Vibratos and Slides with the example s9/k3 is spelled /, not :/). As alone() in glossary.py. */
  const alone = (r: GRow, s: Section) => (vertical(s) || isWord(r)) && !(r.usage?.some((l) => l.trim()) && !r.usage.some((l) => /^[:：]/.test(l.trim())));
  function ascii(r: GRow, s: Section): string {
    if (isWord(r)) return (alone(r, s) ? colonFor(...r.glyphs) : '') + r.glyphs.map((g) => asciiOf(g)[0] ?? '?').join('');
    if (!alone(r, s)) return asciiOf(r.glyph).join(', ');
    // each spelling with its own glyph's colon: 散's 0 needs one, its vertical form's san doesn't
    const sp = T.get(app.typing, r.glyph), v = sp.vert_variant;
    const own = [sp.latin, sp.latin_alt, sp.common].filter(Boolean);
    const theirs = v ? [T.get(app.typing, v).latin, T.get(app.typing, v).latin_alt, T.get(app.typing, v).common].filter(Boolean) : [];
    if (!own.length && !theirs.length) return asciiOf(r.glyph).map((a) => colonFor(r.glyph) + a).join(', ');
    return [...own.map((a) => colonFor(r.glyph) + a), ...theirs.map((a) => colonFor(v) + a)].join(', ');
  }
  function chinese(r: GRow, s: Section): string {
    if (isWord(r)) return (alone(r, s) ? colonFor(...r.glyphs) : '') + r.glyphs.map((g) => zhOf(g)[0] ?? '?').join('');
    const pre = alone(r, s) ? colonFor(r.glyph) : '';
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
  /** A section title's rows without a subtitle: the first untitled subtitle under it. */
  /** The section title a dragged row is over (its rows without a subtitle take it). */
  let dropTitle = $state<string | null>(null);
  const untitledOf = (gid: string) => layout.groups.find((g) => g.id === gid)?.sections.find((id) => !layout.sections[id]?.title.trim());
  function move(from: { sid: string; index: number }, to: { sid: string; index: number }) {
    const r = rowsOf(from.sid)[from.index];
    if (!r) return;
    if (to.sid.startsWith('new:')) {                 // straight under a section title: a subtitle without a title, first
      const gid = to.sid.slice(4), src = sec(from.sid), id = newId('', taken());
      const g = layout.groups.find((x) => x.id === gid)!;
      app.editGlossaryLayout(`Move ${rowName(r)} under ${g.title}`, (l, rows) => {
        l.sections[id] = { title: '', ...(src.usage ? { usage: src.usage } : {}) };
        l.groups.find((x) => x.id === gid)!.sections.unshift(id);
        rows[from.sid] = rows[from.sid].filter((_, j) => j !== from.index);
        rows[id] = [r];
        return { layout: l, rows };
      });
      onnotice?.(`Moved ${rowName(r)} under ${g.title}, with no subtitle.`, true);
      return;
    }
    if (from.sid === to.sid && (to.index === from.index || to.index === from.index + 1)) return;
    if (from.sid !== to.sid) {
      const why = refuse(app.glossary, r, sec(to.sid));
      if (why) { onnotice?.(why); return; }
    }
    // the last entry out of the rows straight under a section title: that block goes too
    if (from.sid !== to.sid && !layout.sections[from.sid]?.title.trim() && rowsOf(from.sid).length === 1) {
      app.editGlossaryLayout(`Move ${rowName(r)} to ${to.sid}`, (l, rows) => {
        const out = moveRow(rows, from, to);
        delete out[from.sid]; delete l.sections[from.sid];
        for (const g of l.groups) g.sections = g.sections.filter((x) => x !== from.sid);
        return { layout: l, rows: out };
      });
    } else edit(from.sid === to.sid ? `Move ${rowName(r)} in ${from.sid}` : `Move ${rowName(r)} to ${to.sid}`, (rows) => moveRow(rows, from, to));
    if (from.sid !== to.sid) onnotice?.(`Moved ${rowName(r)} to ${sec(to.sid).title || 'under its section title'}.`, true);
  }
  function setMeaning(sid: string, i: number, v: string) {
    const r = rowsOf(sid)[i], m = v.trim();
    if (!r || (r.meaning ?? '') === m) return;
    edit(`${rowName(r)}: definition in ${sid}`, (rows) => {
      const list = [...rows[sid]];
      const { meaning: _, ...rest } = list[i];
      list[i] = (m ? { ...rest, meaning: m } : rest) as GRow;
      return { ...rows, [sid]: list };
    });
  }
  function remove(sid: string, i: number) {
    const r = rowsOf(sid)[i];
    if (!layout.sections[sid]?.title.trim() && rowsOf(sid).length === 1) {   // the last entry straight under a section title
      app.editGlossaryLayout(`Remove ${rowName(r)}`, (l, rows) => {
        delete rows[sid]; delete l.sections[sid];
        for (const g of l.groups) g.sections = g.sections.filter((x) => x !== sid);
        return { layout: l, rows };
      });
    } else edit(`Remove ${rowName(r)} from ${sid}`, (rows) => ({ ...rows, [sid]: rows[sid].filter((_, j) => j !== i) }));
    onnotice?.(`Removed ${rowName(r)}${sec(sid)?.title ? ` from ${sec(sid).title}` : ''}.`, true);
  }

  // ---------------------------------------------------------------- section titles and subtitles

  let layout = $derived(app.glossaryLayout);
  /** Subtitles no section title holds: not on the page until they're put under one. */
  let loose = $derived(sections.filter((x) => !x.hidden && !layout.groups.some((g) => g.sections.includes(x.id))));
  /** Switch a section title or a subtitle on or off the page: one undo step. */
  function toggleShown(kind: 'g' | 's', id: string) {
    const o = kind === 'g' ? layout.groups.find((g) => g.id === id)! : layout.sections[id];
    editLayout(`${o.hidden ? 'Show' : 'Hide'} ${o.title} ${o.hidden ? 'on' : 'from'} the page`, (l) => {
      const x: { hidden?: boolean } = kind === 'g' ? l.groups.find((g) => g.id === id)! : l.sections[id];
      if (x.hidden) delete x.hidden; else x.hidden = true;
    });
  }
  let titleEdit = $state<{ key: string; value: string; nav?: string } | null>(null);
  let descEdit = $state<{ key: string; value: string } | null>(null);
  let newSub = $state<Record<string, { title: string }>>({});
  let newGroup = $state('');
  /** The one add box showing: `row:<subtitle>`, `sub:<section title>` or `group`; the rest are a + button. */
  let opened = $state<string | null>(null);
  const open = (key: string) => { opened = key; addNote = null; };
  const close = () => { opened = null; };
  let layoutNote = $state<{ key: string; text: string } | null>(null);
  const taken = () => [...layout.groups.map((g) => g.id), ...Object.keys(layout.sections)];

  function editLayout(label: string, fn: (l: typeof layout, rows: Record<string, GRow[]>) => void) {
    app.editGlossaryLayout(label, (l, rows) => { fn(l, rows); return { layout: l, rows }; });
  }
  function saveTitle() {
    if (!titleEdit) return;
    const { key, value, nav } = titleEdit, v = value.trim();
    titleEdit = null;
    const [kind, id] = [key.slice(0, 1), key.slice(2)];
    // a subtitle may have none: its rows sit straight under the section title
    if (!v && kind === 'g') { layoutNote = { key, text: 'A section title can\'t be empty.' }; return; }
    if (kind === 'g') {
      const g = layout.groups.find((x) => x.id === id)!;
      if (g.title === v && (g.nav ?? '') === (nav ?? '').trim()) return;
      editLayout(`Section title: ${v}`, (l) => { const x = l.groups.find((y) => y.id === id)!; x.title = v; if (nav?.trim()) x.nav = nav.trim(); else delete x.nav; });
    } else if (layout.sections[id].title !== v) editLayout(v ? `Subtitle: ${v}` : 'No subtitle', (l) => { l.sections[id].title = v; });
  }
  function saveDesc() {
    if (!descEdit) return;
    const { key, value } = descEdit, v = value.trim();
    descEdit = null;
    const [kind, id] = [key.slice(0, 1), key.slice(2)];
    const cur = kind === 'g' ? layout.groups.find((x) => x.id === id)?.description : layout.sections[id]?.description;
    if ((cur ?? '') === v) return;
    editLayout(`Description of ${kind === 'g' ? layout.groups.find((x) => x.id === id)?.title : layout.sections[id].title}`, (l) => {
      const o: { description?: string } = kind === 'g' ? l.groups.find((x) => x.id === id)! : l.sections[id];
      if (v) o.description = v; else delete o.description;
    });
  }
  function addGroup() {
    const t = newGroup.trim();
    if (!t) return;
    const id = newId(t, taken());
    editLayout(`New section title: ${t}`, (l) => { l.groups.push({ id, title: t, sections: [] }); });
    newGroup = '';
  }
  function addSub(gid: string) {
    const f = newSub[gid];
    const t = f?.title.trim();
    if (!t) return;
    const id = newId(t, taken());
    editLayout(`New subtitle: ${t}`, (l, rows) => {
      l.sections[id] = { title: t };                    // no default example: add one under its title
      l.groups.find((g) => g.id === gid)!.sections.push(id);
      rows[id] = [];
    });
    newSub = { ...newSub, [gid]: { title: '' } };
  }
  /** A subtitle's default example, one language at a time (k: 0 ASCII, 1 中文); both empty: none, each row on its own. */
  function setDefault(id: string, k: 0 | 1, value: string) {
    const cur = layout.sections[id]?.usage ?? ['', ''];
    if ((cur[k] ?? '') === value.trim()) return;
    const next = [...cur] as [string, string];
    next[k] = value.trim();
    if (next.some(Boolean) && !next.some((t) => t.includes('{}') || /<r>/.test(t))) {
      layoutNote = { key: `ex:${id}`, text: 'Put {} where the row\'s glyph goes: s9{}k3, 名九{}勾三.' };
      return;
    }
    layoutNote = null;
    const t = layout.sections[id].title || 'the entries';
    editLayout(next.some(Boolean) ? `Default example of ${t}` : `No default example for ${t}`, (l) => {
      if (next.some(Boolean)) l.sections[id].usage = next; else delete l.sections[id].usage;
    });
  }
  function deleteGroup(gid: string) {
    const g = layout.groups.find((x) => x.id === gid)!;
    if (g.sections.length) { layoutNote = { key: `g:${gid}`, text: 'Delete or move its subtitles first.' }; return; }
    editLayout(`Delete the section title ${g.title}`, (l) => { l.groups = l.groups.filter((x) => x.id !== gid); });
    onnotice?.(`Deleted the section title ${g.title}.`, true);
  }
  function deleteSub(sid: string) {
    const n = rowsOf(sid).length, t = layout.sections[sid].title;
    if (n) { layoutNote = { key: `s:${sid}`, text: `It has ${n} row${n === 1 ? '' : 's'}: move or remove them first.` }; return; }
    editLayout(`Delete the subtitle ${t}`, (l, rows) => {
      delete l.sections[sid]; delete rows[sid];
      for (const g of l.groups) g.sections = g.sections.filter((x) => x !== sid);
    });
    onnotice?.(`Deleted the subtitle ${t}.`, true);
  }
  /** Put a subtitle no section title holds under one (at its end). */
  function adopt(sid: string, gid: string) {
    if (!gid) return;
    editLayout(`Put ${layout.sections[sid].title} under ${layout.groups.find((g) => g.id === gid)?.title}`, (l) => {
      l.groups.find((g) => g.id === gid)!.sections.push(sid);
    });
  }

  // ---------------------------------------------------------------- folding

  const FOLD_KEY = 'jzp-glossary-folded';
  let folded = $state<string[]>((() => { try { return JSON.parse(localStorage.getItem(FOLD_KEY) ?? '[]'); } catch { return []; } })());
  $effect(() => { const v = JSON.stringify(folded); try { localStorage.setItem(FOLD_KEY, v); } catch { /* not kept */ } });
  /** Folded, unless a search or a glyph from List view needs it open. */
  const isFolded = (sid: string) => folded.includes(sid) && !q.trim() && shownGlyph?.sid !== sid;
  const fold = (sid: string) => (folded = folded.includes(sid) ? folded.filter((x) => x !== sid) : [...folded, sid]);
  // section titles fold too: everything under one (its description, subtitles and add button) goes
  const GFOLD_KEY = 'jzp-glossary-folded-titles';
  let gfolded = $state<string[]>((() => { try { return JSON.parse(localStorage.getItem(GFOLD_KEY) ?? '[]'); } catch { return []; } })());
  $effect(() => { const v = JSON.stringify(gfolded); try { localStorage.setItem(GFOLD_KEY, v); } catch { /* not kept */ } });
  const groupFolded = (gid: string) => gfolded.includes(gid) && !q.trim()
    && !(shownGlyph?.sid && layout.groups.find((g) => g.id === gid)?.sections.includes(shownGlyph.sid));
  const gfold = (gid: string) => (gfolded = gfolded.includes(gid) ? gfolded.filter((x) => x !== gid) : [...gfolded, gid]);

  // ---------------------------------------------------------------- Example: a row's example word

  /** The example a row shows: its own, else a glyph in a usage section the section's, else the row
   *  typed on its own after a colon (a vertical section's row, and a word anywhere). */
  const templateOf = (r: GRow, s: Section): [string, string] => {
    const t = r.usage || (s.usage && !isWord(r) ? s.usage : verticalTemplate(app.typing, r, app.verticalOnly)) || ['', ''];
    // a line whose glyph has no spelling in that language (the placeholder * has no Chinese) is empty, not ":"
    const sp = isWord(r) ? ['', ''] : mainSpellings(app.typing, r.glyph);
    return [t[0].includes('{}') && !sp[0] ? '' : t[0], t[1].includes('{}') && !sp[1] ? '' : t[1]];
  };
  /** What {} stands for in each language: the glyph's main spellings (a word has none: it's written out). */
  const spellsOf = (r: GRow): [string, string] => (isWord(r) ? ['', ''] : mainSpellings(app.typing, r.glyph));
  /** The example as typed in the font (ASCII, else Chinese), to draw it. */
  function exampleOf(r: GRow, s: Section): string {
    const [a, z] = templateOf(r, s), [sa, sz] = spellsOf(r);
    return a ? exampleText(a, sa) : z ? exampleText(z, sz) : '';
  }
  /** The row's glyph in red: in a usage section, or an example with more in it than the row itself
   *  (s9k3 for 名, 0k5 for 散; not :san or :vxi). */
  const marked = (r: GRow, s: Section) => !isWord(r) && (!!s.usage || marksGlyph(templateOf(r, s)));
  /** Faded: a usage row showing its section's default example, not one of its own. */
  const shared = (r: GRow, s: Section) => !!s.usage && !isWord(r) && !r.usage;
  // every example in view, drawn by one request through the unsaved spellings (as Try it does)
  let drawn = $state<Record<string, WordPiece[]>>({});
  /** What each example line types (both lines, so a row whose two lines disagree says so). */
  let typedAs = $state<Record<string, string>>({});
  const glyphsKey = (gs: string[]) => gs.filter((g) => g !== 'blank_colon').join(' ');
  /** The two lines of a row's example, as typed text: [ASCII, 中文] ('' where there's none). */
  const lines = (r: GRow, s: Section): [string, string] => {
    const [a, z] = templateOf(r, s), [sa, sz] = spellsOf(r);
    return [a ? exampleText(a, sa) : '', z ? exampleText(z, sz) : ''];
  };
  /** Both lines typed, and they give different glyphs: the page's two spellings of it disagree. */
  const disagree = (r: GRow, s: Section) => {
    const [a, z] = lines(r, s);
    return !!a && !!z && a in typedAs && z in typedAs && typedAs[a] !== typedAs[z];
  };
  let drawKey = '';
  let drawTimer: ReturnType<typeof setTimeout> | null = null;
  $effect(() => {
    const words = [...new Set(sections.filter((s) => !isFolded(s.id))
      .flatMap((s) => rowsOf(s.id).flatMap((r) => [exampleOf(r, s), ...lines(r, s)])).filter((w) => w && !(w in typedAs)))];
    const typed = app.typedWith, design = app.design;
    const key = JSON.stringify([words, typed.rows.length, Object.keys(typed.svgs)]);
    if (!words.length || !design || key === drawKey) return;
    if (drawTimer) clearTimeout(drawTimer);
    drawTimer = setTimeout(async () => {
      drawKey = key;
      try {
        const r = await api.words(design, words, typed);
        if (r.ok) {
          drawn = { ...drawn, ...Object.fromEntries(r.words.map((w) => [w.word, w.pieces])) };
          typedAs = { ...typedAs, ...Object.fromEntries(r.words.map((w) => [w.word, glyphsKey(w.glyphs)])) };
        }
      } catch { /* the example shows as text only */ }
    }, 250);
  });
  // a spelling or a drawing changed: draw the examples again
  $effect(() => { JSON.stringify(app.typing); Object.keys(app.extraSvgs).join(); drawn = {}; typedAs = {}; drawKey = ''; });

  let editing = $state<string | null>(null);          // `${sid}:${i}:${'a' | 'z'}`
  let usageNote = $state<{ key: string; level: 'error' | 'warn'; text: string } | null>(null);
  let usageBusy = $state<string | null>(null);

  /** The example, typed in either language on either line (what was typed decides which it is): the
   *  other is made from the glyphs' spellings and typed back to check it gives the same glyphs. Empty:
   *  the row's own example goes, and it shows the default again. `line`: the line clicked (1: 中文). */
  async function setUsage(sid: string, i: number, value: string, line: boolean) {
    const zh0 = line;
    editing = null;
    const r = rowsOf(sid)[i], s = sec(sid), key = `${sid}:${i}`;
    if (!r || !app.design) return;
    const cur = templateOf(r, s), [sa, sz] = spellsOf(r);
    const text = value.trim();
    if (text === exampleText(cur[zh0 ? 1 : 0], zh0 ? sz : sa)) return;
    usageNote = null;
    const put = (u: [string, string] | null) => edit(u ? `${rowName(r)}: example in ${sid}` : `${rowName(r)}: the default example in ${sid}`, (rows) => {
      const list = [...rows[sid]];
      const { usage: _, ...rest } = list[i];
      list[i] = (u ? { ...rest, usage: u } : rest) as GRow;
      return { ...rows, [sid]: list };
    });
    if (!text) { if (r.usage) put(null); return; }
    usageBusy = key;
    try {
      const typed = (await api.words(app.design, [text], app.typedWith)).words?.[0] as unknown as { glyphs: string[]; texts: string[]; clusters?: number[] } | undefined;
      if (!typed?.texts) { usageNote = { key, level: 'error', text: "It couldn't be typed: is the Builder's server running?" }; return; }
      const u = usageFrom(text, typed, isWord(r) ? r.glyphs : r.glyph, app.typing);
      if ('error' in u) { usageNote = { key, level: 'error', text: u.error }; return; }
      const zh = u.zh;                       // the language typed, whichever line it was typed on
      const otherLang = zh ? 'ASCII' : 'Chinese';
      let other = u.other;
      if (other === null) {
        other = cur[zh ? 0 : 1];
        usageNote = { key, level: 'warn', text: `${u.missing.join(', ')} has no ${otherLang} spelling, so the ${otherLang} stays as it was: click it to change it.` };
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
      const keepUsage = old.usage && JSON.stringify(glyphsOfRow(old)) === JSON.stringify(glyphsOfRow(r)) ? { usage: old.usage } : {};
      const next = { ...r, ...(old.meaning ? { meaning: old.meaning } : {}), ...keepUsage, typed: text.trim() } as GRow;
      edit(`Edit ${rowName(old)} in ${sid}`, (rows) => ({ ...rows, [sid]: rows[sid].map((x, j) => (j === i ? next : x)) }));
      rowEdit = null;
      // typed without the colon where the page still needs it: say why it stays (lun alone is the right hand's 轮)
      const t = text.trim(), gs = glyphsOfRow(next);
      if (!/^[:：]/.test(t) && alone(next, sec(sid)) && colonFor(...gs) === ':') {
        const v = !isWord(next) ? app.typing[gs[0]]?.vert_variant : '';
        usageNote = { key: `${sid}:${i}`, level: 'warn', text: v
          ? `${t} without the colon types ${gs[0]}; its vertical form, ${v}, needs the colon, so the page keeps :${t}.`
          : `${t} without the colon isn't set vertically, so the page keeps :${t}.` };
      }
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

  /** An entry straight under a section title (its rows without a subtitle, made first): the default
   *  example of its first subtitle, so it reads like its neighbours. */
  async function addToGroup(gid: string) {
    const key = `grp:${gid}`;
    busy = key; addNote = null;
    try {
      const r = await resolve(adding[key] ?? '');
      if ('error' in r) { addNote = { sid: key, level: 'error', text: r.error }; return; }
      const g = layout.groups.find((x) => x.id === gid)!, near = g.sections.map((id) => sections.find((x) => x.id === id)).find((x) => x && x.title);
      const id = newId('', taken()), typed = (adding[key] ?? '').trim();
      app.editGlossaryLayout(`Add ${rowName(r)} under ${g.title}`, (l, rows) => {
        l.sections[id] = { title: '', ...(near?.usage ? { usage: near.usage } : {}) };
        l.groups.find((x) => x.id === gid)!.sections.unshift(id);
        rows[id] = [{ ...r, typed }];
        return { layout: l, rows };
      });
      adding[key] = '';
      opened = `row:${id}`;                                   // carry on adding in its own box
    } catch (e) { addNote = { sid: key, level: 'error', text: (e as Error).message }; }
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
  const entries = (n: number) => `${n} ${n === 1 ? 'entry' : 'entries'}`;

  // ---------------------------------------------------------------- dragging section titles and subtitles

  /** A section title ('g') or a subtitle ('s') being moved, and where it would land: before or after
   *  another of its kind, or (a subtitle) at the top of a section title (`id` ''). */
  let headDrag = $state<{ kind: 'g' | 's'; id: string; name: string; x: number; y: number } | null>(null);
  let headDrop = $state<{ kind: 'g' | 's'; id: string; before: boolean; gid?: string } | null>(null);

  function headTarget(kind: 'g' | 's', x: number, y: number): typeof headDrop {
    const el = document.elementFromPoint(x, y);
    if (!el) return headDrop;
    if (kind === 'g') {
      const g = el.closest<HTMLElement>('section.grp[data-gid]');
      if (!g) return headDrop;
      const r = g.getBoundingClientRect();
      return { kind, id: g.dataset.gid!, before: y < r.top + Math.min(r.height / 2, 60) };
    }
    const sec = el.closest<HTMLElement>('section.sec[data-sid]');
    if (sec) {
      const gid = sec.closest<HTMLElement>('section.grp[data-gid]')?.dataset.gid;
      if (!gid) return headDrop;
      const r = sec.getBoundingClientRect();
      return { kind, id: sec.dataset.sid!, gid, before: y < r.top + Math.min(r.height / 2, 30) };
    }
    const h2 = el.closest<HTMLElement>('h2[data-gid]');
    if (h2) return { kind, id: '', gid: h2.dataset.gid!, before: true };
    return headDrop;
  }

  function grabHead(e: PointerEvent, kind: 'g' | 's', id: string) {
    if (e.button !== 0) return;
    e.preventDefault();
    const name = kind === 'g' ? layout.groups.find((g) => g.id === id)?.title ?? id : layout.sections[id]?.title ?? id;
    const begin = () => { headDrag = { kind, id, name, x: e.clientX, y: e.clientY }; headDrop = null; };
    const hold = e.pointerType === 'mouse' ? null : new Hold({ onlift: begin, ontap: () => {} });
    if (hold) hold.down(e.clientX, e.clientY); else begin();
    const mv = (ev: PointerEvent) => {
      if (hold && !hold.move(ev.clientX, ev.clientY)) return;
      if (!headDrag) return;
      ev.preventDefault();
      headDrag = { ...headDrag, x: ev.clientX, y: ev.clientY };
      lastY = ev.clientY;
      headDrop = headTarget(kind, ev.clientX, ev.clientY);
    };
    const finish = (apply: boolean) => {
      if (hold) hold.up();
      window.removeEventListener('pointermove', mv);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('pointercancel', cancel);
      window.removeEventListener('keydown', esc);
      if (scrollTimer) { clearInterval(scrollTimer); scrollTimer = null; }
      const d = headDrag, t = headDrop;
      headDrag = null; headDrop = null;
      if (apply && d && t) moveHead(d.kind, d.id, t);
    };
    const up = () => finish(true);
    const cancel = () => finish(false);
    const esc = (ev: KeyboardEvent) => { if (ev.key === 'Escape') cancel(); };
    window.addEventListener('pointermove', mv, { passive: false });
    window.addEventListener('pointerup', up);
    window.addEventListener('pointercancel', cancel);
    window.addEventListener('keydown', esc);
    scrollTimer = setInterval(() => {
      const box = scroller();
      if (!headDrag || !box) return;
      const r = box.getBoundingClientRect(), edge = 48;
      const dy = lastY < r.top + edge ? -14 : lastY > r.bottom - edge ? 14 : 0;
      if (dy) { box.scrollTop += dy; headDrop = headTarget(kind, headDrag.x, headDrag.y); }
    }, 30);
  }

  /** Move a section title among the others, or a subtitle within its section title or to another. */
  function moveHead(kind: 'g' | 's', id: string, t: NonNullable<typeof headDrop>) {
    if (t.id === id) return;
    if (kind === 'g') {
      const from = layout.groups.findIndex((g) => g.id === id);
      let to = layout.groups.findIndex((g) => g.id === t.id) + (t.before ? 0 : 1);
      if (to === from || to === from + 1) return;
      if (to > from) to--;
      editLayout(`Move the section title ${layout.groups[from].title}`, (l) => { const [g] = l.groups.splice(from, 1); l.groups.splice(to, 0, g); });
      return;
    }
    const gTo = t.gid!;
    editLayout(`Move the subtitle ${layout.sections[id].title}`, (l) => {
      for (const g of l.groups) g.sections = g.sections.filter((x) => x !== id);
      const target = l.groups.find((g) => g.id === gTo)!;
      const at = t.id === '' ? 0 : target.sections.indexOf(t.id) + (t.before ? 0 : 1);
      target.sections.splice(Math.max(0, at), 0, id);
    });
  }

  /** The gap under the pointer: before the row it's over (upper half) or after it (lower half);
   *  over a section's add line or folded title: at its end; over an open section's title: at its top. */
  function targetAt(x: number, y: number): { sid: string; index: number } | null {
    const el = document.elementFromPoint(x, y)?.closest<HTMLElement>('[data-drop]');
    if (!el) return drop;
    dropTitle = el.dataset.drop === 'group' ? el.dataset.gid! : null;
    const sid = el.dataset.sid!, i = Number(el.dataset.i);
    if (el.dataset.drop === 'end') return { sid, index: rowsOf(sid).length };
    if (el.dataset.drop === 'start') return { sid, index: 0 };
    if (el.dataset.drop === 'group') {               // a section title: its rows without a subtitle, made if need be
      const u = untitledOf(el.dataset.gid!);
      return u ? { sid: u, index: rowsOf(u).length } : { sid: `new:${el.dataset.gid}`, index: 0 };
    }
    const r = el.getBoundingClientRect();
    return { sid, index: y < r.top + r.height / 2 ? i : i + 1 };
  }
  const gapBefore = (sid: string, i: number) => !!drag && drop?.sid === sid && drop.index === i;
  const okDrop = $derived.by(() => {
    if (!drag || !drop || drop.sid === drag.sid || drop.sid.startsWith('new:')) return true;
    return !refuse(app.glossary, rowsOf(drag.sid)[drag.index], sec(drop.sid));
  });
</script>

{#snippet subtitle(s: Section & { description?: string })}
    {@const rows = rowsOf(s.id)}
    {@const shown = rows.map((r, i) => ({ r, i })).filter(({ r }) => matches(r, s))}
    {#if !q.trim() || shown.length}
    {@const usage = !!s.usage}
    {@const plain = !s.title.trim()}
    <section class="sec" class:plain class:off={s.hidden} aria-labelledby="gs-{s.id}" data-sid={s.id}
      class:hd-before={headDrop?.kind === 's' && headDrop.id === s.id && headDrop.before} class:hd-after={headDrop?.kind === 's' && headDrop.id === s.id && !headDrop.before}
      class:lifted={headDrag?.kind === 's' && headDrag.id === s.id}>
      {#if !plain}
      <h3 id="gs-{s.id}" data-drop={isFolded(s.id) ? 'end' : 'start'} data-sid={s.id} data-i={rows.length} class:gap={!!drag && isFolded(s.id) && drop?.sid === s.id} class:no={!okDrop && drop?.sid === s.id}>
        <button class="quiet g hg" onpointerdown={(e) => grabHead(e, 's', s.id)} disabled={!!q.trim()}
          aria-label="Drag the subtitle {s.title} to move it" data-tip={q.trim() ? 'Clear the search to drag' : 'Drag to move the subtitle · a finger: press and hold first'}><I.Grip size={14} /></button>
        <button class="quiet fold" onclick={() => fold(s.id)} aria-expanded={!isFolded(s.id)} aria-controls="gb-{s.id}" data-tip={layoutTip(s)}>
          {#if isFolded(s.id)}<I.Folded size={14} />{:else}<I.Unfolded size={14} />{/if}{#if s.title}<span>{s.title}</span>{:else}<span class="untitled">No subtitle</span>{/if}</button>
        <span class="count">({entries(rows.length)})</span>
        {#if JSON.stringify(saved[s.id] ?? []) !== JSON.stringify(rows) || JSON.stringify(savedLayout.sections[s.id] ?? null) !== JSON.stringify(layout.sections[s.id] ?? null)}<span class="pill draft"><I.Unsaved size={12} /> unsaved</span>{/if}
        <span class="hact">
          <button class="quiet ic" onclick={() => toggleShown('s', s.id)} aria-pressed={!layout.sections[s.id]?.hidden}
            aria-label="{layout.sections[s.id]?.hidden ? 'Show' : 'Hide'} {s.title} on the page"
            data-tip={layout.sections[s.id]?.hidden ? 'Hidden from the page: click to show it' : s.hidden ? 'Hidden with its section title' : 'On the page: click to hide it'}>
            {#if layout.sections[s.id]?.hidden}<I.Hidden size={14} />{:else}<I.Shown size={14} />{/if}</button>
          <button class="quiet ic" onclick={() => (titleEdit = { key: `s:${s.id}`, value: s.title })} aria-label="Rename the subtitle {s.title}" data-tip="Rename the subtitle"><I.EditRow size={14} /></button>
          <button class="quiet ic" onclick={() => { descEdit = { key: `s:${s.id}`, value: s.description ?? '' }; folded = folded.filter((x) => x !== s.id); }} aria-label="Describe {s.title}" data-tip="{s.description ? 'Edit' : 'Add'} its description"><I.Description size={14} /></button>
          <button class="quiet ic" onclick={() => deleteSub(s.id)} aria-label="Delete the subtitle {s.title}" data-tip={rows.length ? 'Delete the subtitle (move or remove its rows first)' : 'Delete the subtitle (Undo brings it back)'}><I.Close size={14} /></button>
        </span></h3>
      {@render editors(`s:${s.id}`, s.description ?? '', 'glossary-subdesc', isFolded(s.id))}
      {/if}
      {#if plain || !isFolded(s.id)}
      <div class="defex">
        <span class="small muted" data-tip={'What a row without an example of its own shows, {} for its glyph (s9{}k3). Empty: each row is typed on its own, after a colon where it needs one.'}>Default example</span>
        {#each [0, 1] as k (k)}
          <input type="text" class="meaning" class:mono={k === 0} class:zh={k === 1} value={s.usage?.[k] ?? ''} spellcheck="false"
            placeholder={k ? '中文' : s.usage ? 'ASCII' : 'none: each row on its own'}
            aria-label="Default example of {s.title || 'the entries'} in {k ? 'Chinese' : 'ASCII'}"
            onchange={(e) => setDefault(s.id, k as 0 | 1, (e.target as HTMLInputElement).value)} />
        {/each}
        {#if layoutNote?.key === `ex:${s.id}`}<span class="small bad" role="status"><I.Problem size={12} /> {layoutNote.text}</span>{/if}
      </div>
      <div class="scroll" id="gb-{s.id}">
      <table class:usage>
        <colgroup><col class="c-grip" /><col class="c-a" /><col class="c-z" /><col class="c-p" /><col class="c-in" /><col class="c-out" /><col class="c-m" /><col class="c-act" /></colgroup>
        <thead><tr><th></th><th>ASCII</th><th>中文</th><th>拼音</th><th title={usage ? "How to type the example word the page shows for it, its glyph in red: click a line to type it, in ASCII or Chinese; the other is made from the glyphs' spellings. Faded: the section's default example, with this row's glyph in it, until you give the row its own." : "How to type what the page shows for it, on its own after a colon: click a line to type another, in ASCII or Chinese; the other is made from the glyphs' spellings."}>Input</th><th class="out" title="The Input as the font sets it">Output</th><th>Definition</th><th></th></tr></thead>
        <tbody>
          {#each shown as { r, i } (rowKey(r) + i)}
            {@const gone = lost(r)}
            {@const tpl = templateOf(r, s)}
            {@const sp = spellsOf(r)}
            {@const key = `${s.id}:${i}`}
            <tr data-drop="row" data-sid={s.id} data-i={i} data-glyphs={glyphsOfRow(r).join(' ')}
              class:changed={changed(s.id, i)} class:on={shownGlyph?.sid === s.id && glyphsOfRow(r).includes(shownGlyph.glyph)}
              class:lifted={drag?.sid === s.id && drag.index === i}
              class:gap-before={gapBefore(s.id, i)} class:gap-after={gapBefore(s.id, i + 1) && i === rows.length - 1}
              class:no={!okDrop && drop?.sid === s.id}>
              <td class="grip"><button class="quiet g" onpointerdown={(e) => grab(e, s.id, i)} disabled={!!q.trim()}
                aria-label="Drag {rowName(r)} to move it" data-tip={q.trim() ? 'Clear the search to drag' : 'Drag to move · a finger: press and hold first'}><I.Grip size={14} /></button></td>
              {#if rowEdit?.sid === s.id && rowEdit.i === i}
                <td colspan="3" class="redit">
                  <!-- svelte-ignore a11y_autofocus -->
                  <input type="text" bind:value={rowEdit.text} autofocus spellcheck="false" aria-label="Type {rowName(r)} again"
                    onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void saveRow(); } else if (e.key === 'Escape') { rowEdit = null; rowNote = null; } }} />
                  <button class="sm" onclick={saveRow} disabled={rowBusy}>{#if rowBusy}<I.Working size={14} />{/if} Done</button>
                  <button class="sm quiet" onclick={() => { rowEdit = null; rowNote = null; }}>Cancel</button>
                  {#if rowNote?.sid === s.id && rowNote.i === i}<span class="small bad" role="status"><I.Problem size={12} /> {rowNote.text}</span>{/if}
                </td>
              {:else}
              <td class="mono">{ascii(r, s)}</td>
              <td class="zh">{chinese(r, s)}</td>
              <td>{pinyin(r)}</td>
              {/if}
              <td class="use" class:def={shared(r, s)}>
                  <div class="lines">
                    {#each [1, 0] as k (k)}
                      {#if editing === `${key}:${k}`}
                        <!-- svelte-ignore a11y_autofocus -->
                        <input type="text" class:zh={k === 1} class:mono={k === 0} value={exampleText(tpl[k], sp[k])} autofocus spellcheck="false"
                          aria-label="{k ? 'Chinese' : 'ASCII'} example for {rowName(r)}"
                          onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); (e.target as HTMLInputElement).blur(); } else if (e.key === 'Escape') { editing = null; } }}
                          onblur={(e) => { if (editing === `${key}:${k}`) void setUsage(s.id, i, (e.target as HTMLInputElement).value, k === 1); }} />
                      {:else}
                        <button class="line" class:zh={k === 1} class:mono={k === 0} disabled={usageBusy === key}
                          onclick={() => { usageNote = null; editing = `${key}:${k}`; }}
                          data-tip={shared(r, s) ? "The section's default example, with this glyph in it: click to give this row its own" : 'Click to change it; the other line follows'}>
                          {#if tpl[k]}{@html exampleHtml(tpl[k], sp[k], marked(r, s))}{:else}<span class="muted">{k ? '中文' : 'ASCII'} example</span>{/if}</button>
                      {/if}
                    {/each}
                  </div>
                {#if gone.length}<span class="bad small" title="{gone.join(', ')} isn't a glyph any more: edit the row or remove it"><I.Problem size={12} /> {gone.join(', ')}</span>{/if}
                {#if usageBusy === key}<span class="small muted"><I.Working size={12} /> typing it…</span>{/if}
                {#if disagree(r, s) && usageNote?.key !== key}
                  {@const [la, lz] = lines(r, s)}
                  <span class="small note" role="status"><I.Warn size={12} /> {lz} and {la} type different glyphs: click a line to fix it.</span>
                {/if}
                {#if usageNote?.key === key}<span class="small note" class:bad={usageNote.level === 'error'} role="status">{#if usageNote.level === 'error'}<I.Problem size={12} />{:else}<I.Warn size={12} />{/if} {usageNote.text}</span>{/if}
              </td>
              <td class="out" class:def={shared(r, s)}>
                {#if drawn[exampleOf(r, s)]}
                  <button class="ga vert" onclick={() => onopen?.(glyphsOfRow(r)[0])} aria-label="Show {glyphsOfRow(r)[0]}" data-tip="{exampleOf(r, s)} as the font sets it · click: {glyphsOfRow(r)[0]} in the glyph panel">
                    <GlossaryExample pieces={drawn[exampleOf(r, s)]} mark={marked(r, s) && !isWord(r) ? r.glyph : ''} {...(marked(r, s) ? {} : { scale: 0.04 })} /></button>
                {/if}
              </td>
              <td><input type="text" class="meaning" value={r.meaning ?? ''} aria-label="Definition of {rowName(r)} in {s.id}" placeholder="its definition"
                onchange={(e) => setMeaning(s.id, i, (e.target as HTMLInputElement).value)} /></td>
              <td class="act">
                <button class="quiet ic" onclick={() => onopen?.(glyphsOfRow(r)[0])} aria-label="Show {glyphsOfRow(r)[0]} in the glyph panel"
                  data-tip="Show {glyphsOfRow(r)[0]} in the glyph panel"><I.GlyphPanel size={14} /></button>
                <button class="quiet ic" onclick={() => { rowNote = null; rowEdit = { sid: s.id, i, text: entryOf(r, s) }; }} disabled={!!rowEdit && rowEdit.sid === s.id && rowEdit.i === i}
                  aria-label="Edit {rowName(r)}" data-tip="Edit: type it again, as it was entered"><I.EditRow size={14} /></button>
                <button class="quiet ic" onclick={() => remove(s.id, i)} aria-label="Remove {rowName(r)} from {s.id}" data-tip="Remove from this section (Undo brings it back)"><I.Close size={14} /></button>
              </td>
            </tr>
          {/each}
          <tr class="addrow" data-drop="end" data-sid={s.id} data-i={rows.length} class:gap-before={gapBefore(s.id, rows.length) && !rows.length}
            class:no={!okDrop && drop?.sid === s.id}>
            <td colspan="8" class="addcell">
              {#if !rows.length}<span class="muted small empty">No entries yet{drag ? ': drop here' : ''}.</span>{/if}
              <span class="add">
                {#if opened === `row:${s.id}`}
                  <!-- svelte-ignore a11y_autofocus -->
                  <input type="text" bind:value={adding[s.id]} placeholder={s.usage ? 'A glyph: k, 勾 or lg_gou' : 'A glyph or a word: 勾, :shaoxi'}
                    aria-label="Add to {s.title}" spellcheck="false" autofocus
                    onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void add(s.id); } else if (e.key === 'Escape') close(); }} />
                  <button class="sm" onclick={() => add(s.id)} disabled={busy === s.id || !adding[s.id]?.trim()}>{#if busy === s.id}<I.Working size={14} />{/if} Add an entry</button>
                  <button class="sm quiet" onclick={close}>Done</button>
                {:else}
                  <button class="sm quiet" onclick={() => open(`row:${s.id}`)}><I.Plus size={14} /> Add an entry</button>
                {/if}
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
  {/snippet}

{#snippet editors(key: string, desc: string, cls: string, folded = false)}
  {#if titleEdit?.key === key}
    <div class="tedit">
      <!-- svelte-ignore a11y_autofocus -->
      <label class="fld"><span>Title</span>
        <input type="text" bind:value={titleEdit.value} autofocus placeholder={key.startsWith('s:') ? 'None: its rows sit under the section title' : ''}
          onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveTitle(); } else if (e.key === 'Escape') titleEdit = null; }} /></label>
      {#if key.startsWith('g:')}
        <label class="fld"><span>Name in the page's contents</span>
          <input type="text" class="nav" bind:value={titleEdit.nav} placeholder="optional, e.g. Left hand"
            onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveTitle(); } else if (e.key === 'Escape') titleEdit = null; }} /></label>
      {/if}
      <button class="sm" onclick={saveTitle}>Done</button>
      <button class="sm quiet" onclick={() => (titleEdit = null)}>Cancel</button>
    </div>
  {/if}
  {#if descEdit?.key === key}
    <div class="dedit">
      <!-- svelte-ignore a11y_autofocus -->
      <textarea bind:value={descEdit.value} rows="4" autofocus aria-label="Description"
        onkeydown={(e) => { if (e.key === 'Escape') descEdit = null; else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); saveDesc(); } }}></textarea>
      <div class="dprev {cls}">{@html markdown(descEdit.value)}</div>
      <p class="muted small">Markdown: a blank line starts a paragraph; **bold**, *italic*, `s9k3` for a typed example, [a link](https://…), “- ” for a list, and the page's &lt;u&gt;, &lt;jzp&gt; and &lt;small&gt;. Ctrl+Enter keeps it.</p>
      <div><button class="sm" onclick={saveDesc}>Done</button> <button class="sm quiet" onclick={() => (descEdit = null)}>Cancel</button></div>
    </div>
  {:else if desc && !folded}
    <button class="desc {cls}" onclick={() => (descEdit = { key, value: desc })} data-tip="Click to edit the description">{@html markdown(desc)}</button>
  {/if}
  {#if layoutNote?.key === key}<p class="small bad" role="status"><I.Problem size={12} /> {layoutNote.text}</p>{/if}
{/snippet}

<div class="gloss" bind:this={root} class:dragging={!!drag || !!headDrag}>
  <p class="muted small intro">
    The font page's glossary, a section at a time, in page order. A row is one glyph, or a word written together (:少息);
    its ASCII, 中文 and 拼音 come from the spellings. Drag a row by its grip to move it, within a section or to another.
    Fold a section or a subsection by its title. Save writes site/glossary.json; a release puts it on jianzipufont.com.
    <span class="folds">
      <button class="lnk" onclick={() => (gfolded = layout.groups.map((g) => g.id))}>Fold all sections</button> ·
      <button class="lnk" onclick={() => (gfolded = [])}>Unfold all sections</button> ·
      <button class="lnk" onclick={() => (folded = sections.map((x) => x.id))}>Fold all subsections</button> ·
      <button class="lnk" onclick={() => (folded = [])}>Unfold all subsections</button>
    </span>
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

  {#each layout.groups as g (g.id)}
    {@const subs = g.sections.map((id) => sections.find((x) => x.id === id)).filter((x) => !!x)}
    {#if !q.trim() || subs.some((x) => rowsOf(x.id).some((r) => matches(r, x)))}
    <section class="grp" aria-labelledby="gg-{g.id}" data-gid={g.id} class:off={g.hidden}
      class:hd-before={headDrop?.kind === 'g' && headDrop.id === g.id && headDrop.before} class:hd-after={headDrop?.kind === 'g' && headDrop.id === g.id && !headDrop.before}
      class:lifted={headDrag?.kind === 'g' && headDrag.id === g.id}>
      <h2 id="gg-{g.id}" data-gid={g.id} data-drop="group" class:hd-in={(headDrop?.kind === 's' && headDrop.gid === g.id && headDrop.id === '')
        || (!!drag && dropTitle === g.id)}>
        <button class="quiet g hg" onpointerdown={(e) => grabHead(e, 'g', g.id)} disabled={!!q.trim()}
          aria-label="Drag the section title {g.title} to move it" data-tip={q.trim() ? 'Clear the search to drag' : 'Drag to move the section title · a finger: press and hold first'}><I.Grip size={14} /></button>
        <button class="quiet fold gfold" onclick={() => gfold(g.id)} aria-expanded={!groupFolded(g.id)} aria-controls="gc-{g.id}">
          {#if groupFolded(g.id)}<I.Folded size={18} />{:else}<I.Unfolded size={18} />{/if}<span class="gt" class:untitled={!g.title}>{g.title || 'Untitled section'}</span></button>
        <span class="count" data-tip={[g.nav ? `“${g.nav}” in the page's contents` : '', g.hidden || !subs.some((x) => !x.hidden) ? 'not on the page' : ''].filter(Boolean).join(' · ') || undefined}>({entries(subs.reduce((n, x) => n + rowsOf(x.id).length, 0))})</span>
        {#if JSON.stringify(savedLayout.groups.find((x) => x.id === g.id) ?? null) !== JSON.stringify(g)}<span class="pill draft"><I.Unsaved size={12} /> unsaved</span>{/if}
        <span class="hact">
          <button class="quiet ic" onclick={() => toggleShown('g', g.id)} aria-pressed={!g.hidden}
            aria-label="{g.hidden ? 'Show' : 'Hide'} {g.title} on the page"
            data-tip={g.hidden ? 'Hidden from the page, with all its subtitles: click to show it' : 'On the page: click to hide it and its subtitles'}>
            {#if g.hidden}<I.Hidden size={14} />{:else}<I.Shown size={14} />{/if}</button>
          <button class="quiet ic" onclick={() => (titleEdit = { key: `g:${g.id}`, value: g.title, nav: g.nav ?? '' })} aria-label="Rename the section title {g.title}" data-tip="Rename the section title"><I.EditRow size={14} /></button>
          <button class="quiet ic" onclick={() => { descEdit = { key: `g:${g.id}`, value: g.description ?? '' }; gfolded = gfolded.filter((x) => x !== g.id); }} aria-label="Describe {g.title}" data-tip="{g.description ? 'Edit' : 'Add'} its description"><I.Description size={14} /></button>
          <button class="quiet ic" onclick={() => deleteGroup(g.id)} aria-label="Delete the section title {g.title}" data-tip={g.sections.length ? 'Delete the section title (delete or move its subtitles first)' : 'Delete the section title (Undo brings it back)'}><I.Close size={14} /></button>
        </span>
      </h2>
      {@render editors(`g:${g.id}`, g.description ?? '', 'glossary-desc', groupFolded(g.id))}
      {#if !groupFolded(g.id)}
      <div class="gbody" id="gc-{g.id}">
      {#if !untitledOf(g.id) && !q.trim()}
        {#if drag}
          <div class="gdrop" data-drop="group" data-gid={g.id} class:on={dropTitle === g.id}>Drop here to put it straight under {g.title || 'the section title'}, before its subtitles</div>
        {/if}
        <div class="add gadd">
          {#if opened === `grp:${g.id}`}
            <!-- svelte-ignore a11y_autofocus -->
            <input type="text" bind:value={adding[`grp:${g.id}`]} placeholder="A glyph or a word: 勾, :shaoxi" aria-label="Add an entry under {g.title}" spellcheck="false" autofocus
              onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void addToGroup(g.id); } else if (e.key === 'Escape') close(); }} />
            <button class="sm" onclick={() => addToGroup(g.id)} disabled={busy === `grp:${g.id}` || !adding[`grp:${g.id}`]?.trim()}>{#if busy === `grp:${g.id}`}<I.Working size={14} />{/if} Add an entry</button>
            <button class="sm quiet" onclick={close}>Done</button>
          {:else}
            <button class="sm quiet" onclick={() => open(`grp:${g.id}`)} data-tip="An entry straight under the section title, before its subtitles"><I.Plus size={14} /> Add an entry</button>
          {/if}
          {#if addNote?.sid === `grp:${g.id}`}<span class="small" class:bad={addNote.level === 'error'} role="status"><I.Problem size={12} /> {addNote.text}</span>{/if}
        </div>
      {/if}
      {#each subs as s (s.id)}{@render subtitle(s)}{/each}
      {#if !q.trim()}
        {@const f = newSub[g.id] ?? { title: '' }}
        <div class="addsub">
          {#if opened === `sub:${g.id}`}
          <!-- svelte-ignore a11y_autofocus -->
          <input type="text" value={f.title} placeholder="Its title, e.g. 3f: Ornaments" aria-label="New subtitle under {g.title}" autofocus
            oninput={(e) => (newSub = { ...newSub, [g.id]: { ...f, title: (e.target as HTMLInputElement).value } })}
            onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSub(g.id); } else if (e.key === 'Escape') close(); }} />
          <button class="sm" onclick={() => { addSub(g.id); close(); }} disabled={!f.title.trim()}>Add subtitle</button>
          <button class="sm quiet" onclick={close}>Cancel</button>
          {:else}
          <button class="sm quiet" onclick={() => open(`sub:${g.id}`)}><I.Plus size={14} /> Add subtitle</button>
          {/if}
        </div>
      {/if}
      </div>
      {/if}
    </section>
    {/if}
  {/each}
  {#if loose.length && !q.trim()}
    <section class="grp">
      <h2><span class="gt untitled">Not under a section title</span></h2>
      <p class="muted small">The page doesn't show these until they're under a section title.</p>
      {#each loose as s (s.id)}
        <div class="adopt"><span>{s.title}</span>
          <select aria-label="Section title for {s.title}" onchange={(e) => adopt(s.id, (e.target as HTMLSelectElement).value)}>
            <option value="">Put it under…</option>
            {#each layout.groups as g (g.id)}<option value={g.id}>{g.title}</option>{/each}
          </select></div>
        {@render subtitle(s)}
      {/each}
    </section>
  {/if}
  {#if sections.length && !q.trim()}
    <div class="addgrp">
      {#if opened === 'group'}
        <!-- svelte-ignore a11y_autofocus -->
        <input type="text" bind:value={newGroup} placeholder="Its title, e.g. 5: Ornaments" aria-label="New section title" autofocus
          onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addGroup(); close(); } else if (e.key === 'Escape') close(); }} />
        <button onclick={() => { addGroup(); close(); }} disabled={!newGroup.trim()}>Add section title</button>
        <button class="quiet" onclick={close}>Cancel</button>
      {:else}
        <button class="quiet" onclick={() => open('group')}><I.Plus size={14} /> Add section title</button>
      {/if}
    </div>
  {/if}
  {#if q.trim() && !sections.some((s) => rowsOf(s.id).some((r) => matches(r, s)))}<p class="muted small">No row matches.</p>{/if}
</div>

{#if headDrag}
  <div class="ghost" style:left="{headDrag.x + 12}px" style:top="{headDrag.y - 12}px" aria-hidden="true">{headDrag.name}</div>
  <div class="sr" role="status">Moving {headDrag.name}</div>
{/if}
{#if drag}
  <div class="ghost" style:left="{drag.x + 12}px" style:top="{drag.y - 12}px" aria-hidden="true">{drag.name}</div>
  <div class="sr" role="status">Moving {drag.name}{drop ? ` to ${drop.sid}, place ${drop.index + 1}` : ''}</div>
{/if}

<style>
  .gloss { display: flex; flex-direction: column; gap: var(--space-5); padding-bottom: var(--space-7); }
  .gloss.dragging { user-select: none; cursor: grabbing; }
  .intro { margin: 0; max-width: 760px; }
  .banner select { height: 26px; }
  .sec h3 { margin: 0 0 var(--space-2); font-family: var(--font-display); font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
  /* switched off: faded, so it reads as not on the page (its eye switch stays clear) */
  .grp.off > :not(h2), .grp.off > h2 > :not(.hact), .sec.off > :not(h3), .sec.off > h3 > :not(.hact) { opacity: .45; }
  /* a computer has the width for the table; a phone scrolls it sideways (a scroller here also caught the wheel, and the page stopped scrolling) */
  .scroll { overflow: visible; }
  table { border-collapse: collapse; width: 100%; min-width: 760px; table-layout: fixed; font-size: var(--t-small); }
  .c-grip { width: 32px; } .c-a { width: 14%; } .c-z { width: 12%; } .c-p { width: 12%; } .c-in { width: 22%; } .c-out { width: 12%; } .c-act { width: 92px; }
  th { text-align: left; font-weight: 600; padding: var(--space-1) var(--space-2); border-bottom: 1px solid var(--border); white-space: nowrap; font-size: var(--t-caption); color: var(--ink-muted); }
  /* clip, not hidden: a hidden cell is a scroller, and the wheel over it stopped scrolling the page */
  td { padding: 1px var(--space-2); border-bottom: 1px solid var(--hairline); vertical-align: middle; overflow: clip; text-overflow: ellipsis; }
  tr.changed td:first-child { box-shadow: inset 3px 0 0 var(--status-draft); }
  tr.on td { background: var(--sel-bg); }
  tr.lifted td { opacity: .4; }
  tr.gap-before td { box-shadow: inset 0 2px 0 var(--link); }
  tr.gap-after td { box-shadow: inset 0 -2px 0 var(--link); }
  tr.no.gap-before td, tr.no.gap-after td { box-shadow: inset 0 2px 0 var(--status-danger); }
  td.grip, td.act, td.use, td.out { text-overflow: clip; }
  td.grip { padding: 0 3px; }
  .grip .g { width: 24px; min-height: 24px; height: 24px; padding: 0; cursor: grab; touch-action: none; color: var(--ink-muted); }
  .grip .g:disabled { cursor: default; opacity: .4; }
  .redit { white-space: nowrap; }
  .redit input { width: 280px; height: 26px; font-family: var(--font-mono); margin-right: var(--space-2); }
  .redit .bad { margin-left: var(--space-2); white-space: normal; }
  .ga { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; padding: 0; border: 1px solid transparent; border-radius: var(--radius-sm); background: transparent; cursor: pointer; vertical-align: middle; }
  .ga.vert { width: auto; height: auto; min-width: 28px; min-height: 28px; padding: 2px; }
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
  td.out { padding-top: var(--space-1); padding-bottom: var(--space-1); }
  .defex { display: flex; align-items: center; gap: var(--space-2); margin: 0 0 var(--space-1) var(--space-6); flex-wrap: wrap; }
  .defex input { width: 12rem; height: 24px; font-size: var(--t-small); }
  td.out, th.out { text-align: center; }
  .lines { display: flex; flex-direction: column; min-width: 0; }
  .line { display: block; width: 100%; text-align: left; border: 1px solid transparent; background: transparent; padding: 0 4px; min-height: 24px; height: auto; font-size: var(--t-small); color: var(--ink); cursor: text; white-space: nowrap; overflow: clip; text-overflow: ellipsis; }
  .line:hover:not(:disabled) { border-color: var(--border); }
  .line:disabled { cursor: default; }
  .line :global(.r) { color: var(--accent); }
  td.use.def .line, td.out.def :global(svg.ex) { opacity: .55; }
  .lines input { height: 24px; width: 100%; font-size: var(--t-small); }
  .note { display: block; color: var(--status-draft); white-space: normal; }
  .note.bad { color: var(--status-danger); }
  .addrow td { border-bottom: 0; padding-top: var(--space-2); }
  td.addcell { padding-left: 0; }
  .gadd { padding: 0; }
  .gdrop { border: 1px dashed var(--border); border-radius: var(--radius-sm); padding: var(--space-2) var(--space-3); font-size: var(--t-small); color: var(--ink-muted); }
  .gdrop.on { border-color: var(--link); color: var(--link); background: var(--sel-bg); }
  .add { display: inline-flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
  .add input { width: 260px; height: 26px; font-family: var(--font-mono); }
  .empty { margin-right: var(--space-3); }
  .bad { color: var(--status-danger); }
  .small { font-size: var(--t-caption); }
  .ghost { position: fixed; z-index: 50; pointer-events: none; padding: 2px 8px; background: var(--bg-panel); border: 1px solid var(--sel-border); border-radius: var(--radius-sm); box-shadow: 0 4px 12px rgba(0,0,0,.15); font-size: var(--t-small); }
  .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  @media (max-width: 759.98px) {
    .scroll { overflow-x: auto; overflow-y: hidden; overscroll-behavior-x: contain; }
    .act .ic, .grip .g { width: var(--control-sm); min-height: var(--control-sm); height: var(--control-sm); }
    .c-grip { width: 40px; } .c-act { width: 112px; }
    .add input { width: 100%; }
  }
  .grp { display: flex; flex-direction: column; gap: var(--space-4); padding-top: var(--space-2); }
  .grp + .grp { border-top: 1px solid var(--border); padding-top: var(--space-5); }
  /* 26 px and 18 px as asked: between the type scale's steps (--t-heading 22, --t-title 32; --t-panel 16) */
  .grp h2 { margin: 0; font-family: var(--font-display); font-size: 26px; font-weight: 600; display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
  .count { font-family: var(--font-serif); font-size: var(--t-small); font-weight: 400; color: var(--ink-muted); }
  .hg { width: 24px; min-height: 24px; height: 24px; padding: 0; cursor: grab; touch-action: none; color: var(--ink-muted); }
  .hg:disabled { cursor: default; opacity: .4; }
  section.lifted { opacity: .4; }
  section.hd-before { box-shadow: 0 -2px 0 var(--link); }
  section.hd-after { box-shadow: 0 2px 0 var(--link); }
  h2.hd-in { box-shadow: inset 0 -2px 0 var(--link); }
  .gbody { display: flex; flex-direction: column; gap: var(--space-4); }
  .gfold { font: inherit; font-size: inherit; font-weight: inherit; color: var(--ink); }
  .folds { white-space: nowrap; }
  .folds .lnk { margin-left: 0; }
  .gt.untitled { color: var(--ink-muted); font-style: italic; }
  .hact { display: inline-flex; gap: 2px; margin-left: var(--space-1); }
  .hact .ic { width: 24px; min-height: 24px; height: 24px; padding: 0; }
  button.desc { display: block; text-align: left; width: 100%; height: auto; padding: var(--space-1) var(--space-2); border: 1px solid transparent; background: transparent; font: inherit; font-size: var(--t-small); color: var(--ink); cursor: text; }
  button.desc:hover { border-color: var(--border); }
  .desc :global(p), .dprev :global(p) { margin: 0 0 var(--space-1); }
  .desc :global(text), .dprev :global(text) { font-family: var(--font-mono); background: var(--bg-sunken); padding: 0 3px; border-radius: 3px; }
  .tedit, .addsub, .addgrp, .adopt { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
  .tedit input { width: 360px; height: 28px; } .tedit input.nav { width: 240px; }
  .fld { display: inline-flex; flex-direction: column; gap: 2px; font-size: var(--t-caption); color: var(--ink-muted); font-family: var(--font-serif); font-weight: 400; }
  .sec h3 .untitled { color: var(--ink-muted); font-style: italic; font-weight: 400; }
  .dedit { display: flex; flex-direction: column; gap: var(--space-2); max-width: 760px; }
  .dedit textarea { width: 100%; font-family: var(--font-mono); font-size: var(--t-small); }
  .dprev { border-left: 2px solid var(--border); padding-left: var(--space-3); font-size: var(--t-small); }
  .addsub input, .addgrp input { width: 300px; height: 26px; }
  .addgrp { padding-top: var(--space-4); border-top: 1px solid var(--border); }
  @media (max-width: 759.98px) {
    .hact .ic { width: var(--control-sm); min-height: var(--control-sm); height: var(--control-sm); }
    .tedit input, .tedit input.nav, .addsub input, .addgrp input { width: 100%; }
  }
</style>
