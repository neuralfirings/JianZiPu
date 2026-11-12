<script lang="ts">
  // Glyphs > Words: the glossary's words (words.csv), rows written together like :少息. A word is
  // typed through the glyphs' spellings (unsaved ones and new glyphs included, /api/typing/preview),
  // which fills in its glyphs; its ASCII and pinyin come from them. Its Glossary section, order and
  // meaning are its own. Every edit is one undo step, saved with Save.
  import * as I from '$lib/icons';
  import { api } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import * as T from '$lib/typing';
  import { glyphsOf, emptyWord, type GWord } from '$lib/glossaryWords';
  import GlossaryPicker from './GlossaryPicker.svelte';
  let { highlight = null, q = '' }: { highlight?: string | null; q?: string } = $props();

  // the word a List view row's "in words" link opened: bring it into view
  $effect(() => {
    if (highlight) document.getElementById(`word-${highlight}`)?.scrollIntoView({ block: 'center' });
  });

  let adding = $state('');
  let addNote = $state<{ level: 'error' | 'ok'; text: string } | null>(null);
  let busy = $state(false);

  /** What typing `text` gives: its glyphs, and the Chinese word they spell (少息). Null when a part
   *  of it doesn't become a glyph (with why). */
  async function resolve(text: string): Promise<{ glyphs: string[]; word: string } | { error: string }> {
    const t = text.trim().replace(/^[:：]/, '');
    if (!t) return { error: 'Type the word, in Chinese (少息) or Latin (shaoxi).' };
    if (!app.design) return { error: 'Nothing loaded yet.' };
    const r = await api.typingPreview({ design: app.design, rows: T.toRecords(app.typing), words: [':' + t], roundtrip: false,
      svg_names: app.extraGlyphs, svgs: app.extraSvgs });
    if (!r.ok || !r.words?.length) return { error: r.error ?? "it couldn't be typed" };
    const typed = r.words[0];
    const gs = typed.glyphs.filter((g) => g !== 'blank_colon');
    // what didn't become a glyph: a stray letter, a character no spelling claims
    const stray = typed.glyphs.map((g, i) => ({ g, text: typed.texts?.[i] ?? g }))
      .filter(({ g }) => g !== 'blank_colon' && (g === '.notdef' || !app.known.has(g))).map(({ text }) => text);
    // Chinese characters the font hasn't got (no build since they were added, no base font here)
    const lacking = new Set(Object.values(r.missing_chars ?? {}).flat().join(''));
    if (stray.length && stray.every((x) => [...x].every((ch) => lacking.has(ch) || /[\u3400-\u9fff]/.test(ch))))
      return { error: `${stray.join(' ')} isn't in the font yet (Build font once, or add the base font), so it can't be typed in Chinese here: type the word in Latin instead (:shaoxi).` };
    if (stray.length) return { error: `${stray.join(' ')} isn't a glyph's spelling: check the spellings, or type it another way.` };
    if (gs.length < 2) return { error: 'A word is two glyphs or more; one glyph has its own row in List view.' };
    const zh = gs.map((g) => T.get(app.typing, g).simplified);
    return { glyphs: gs, word: zh.every(Boolean) ? zh.join('') : t };
  }

  async function add() {
    busy = true; addNote = null;
    try {
      const r = await resolve(adding);
      if ('error' in r) { addNote = { level: 'error', text: r.error }; return; }
      if (app.words.some((w) => w.word === r.word)) { addNote = { level: 'error', text: `${r.word} is in the list already.` }; return; }
      app.editWords(`Add the word ${r.word}`, (ws) => [...ws, { ...emptyWord(r.word), glyphs: r.glyphs.join(' ') }]);
      addNote = { level: 'ok', text: `Added ${r.word} (${r.glyphs.join(' + ')}). Give it a Glossary section to put it on the font page.` };
      adding = '';
    } catch (e) { addNote = { level: 'error', text: (e as Error).message }; }
    finally { busy = false; }
  }

  function set(word: string, field: keyof GWord, v: string) {
    const cur = app.words.find((w) => w.word === word);
    if (!cur || cur[field] === v) return;
    app.editWords(`${word}: ${field.replace('_', ' ')}`, (ws) => ws.map((w) => (w.word === word ? { ...w, [field]: v.trim() } : w)));
  }
  function remove(word: string) {
    app.editWords(`Delete the word ${word}`, (ws) => ws.filter((w) => w.word !== word));
  }

  const ascii = (w: GWord) => ':' + glyphsOf(w).map((g) => { const s = T.get(app.typing, g); return s.latin || s.latin_alt || s.common || '?'; }).join('');
  const pinyin = (w: GWord) => glyphsOf(w).map((g) => T.get(app.typing, g).pinyin).filter(Boolean).join(' ');
  /** A glyph the word names that isn't there any more (renamed or deleted elsewhere). */
  const missing = (w: GWord) => glyphsOf(w).filter((g) => !app.known.has(g) && !(g in app.typing));
  let saved = $derived(JSON.parse(app.savedWordsJson) as GWord[]);
  const changed = (w: GWord) => JSON.stringify(saved.find((s) => s.word === w.word)) !== JSON.stringify(w);
  let shown = $derived(q.trim()
    ? app.words.filter((w) => [w.word, ascii(w), pinyin(w), w.meaning, w.glossary, w.glyphs].join(' ').toLowerCase().includes(q.trim().toLowerCase()))
    : app.words);
</script>

<div class="words">
  <p class="muted small intro">
    Words written together on the font page's glossary, such as :少息. Type one as you would in the font; its glyphs come from the spellings.
    Its Glossary section, Glossary order and Meaning are its own, and each glyph's row in List view shows the words it's in.
  </p>
  <div class="add">
    <input type="text" bind:value={adding} placeholder="New word: 少息 or :shaoxi" aria-label="New word" spellcheck="false"
      onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void add(); } }} />
    <button onclick={add} disabled={busy || !adding.trim()}>{#if busy}<I.Working size={14} />{/if} Add word</button>
    {#if addNote}<span class="small" class:bad={addNote.level === 'error'} role="status">{addNote.text}</span>{/if}
  </div>

  <table>
    <thead><tr><th>Word</th><th>Glyphs</th><th>ASCII</th><th>PinYin</th><th>Glossary</th><th>Glossary order</th><th>Meaning</th><th></th></tr></thead>
    <tbody>
      {#each shown as w (w.word)}
        {@const lost = missing(w)}
        <tr class:on={highlight === w.word} class:changed={changed(w)} id="word-{w.word}">
          <td class="zh">{w.word}</td>
          <td class="mono small" class:bad={lost.length} title={lost.length ? `${lost.join(', ')} isn't a glyph any more: delete the word and add it again` : undefined}>
            {glyphsOf(w).join(' + ')}{#if lost.length} <I.Problem size={12} />{/if}</td>
          <td class="mono">{ascii(w)}</td>
          <td>{pinyin(w)}</td>
          <td class="gl"><GlossaryPicker value={w.glossary} cell changed={saved.find((s) => s.word === w.word)?.glossary !== w.glossary}
            tip={T.HELP.glossary} onchange={(v) => set(w.word, 'glossary', v)} /></td>
          <td><input type="text" class="mono order" value={w.glossary_order} aria-label="Glossary order of {w.word}" title={T.HELP.glossary_order}
            onchange={(e) => set(w.word, 'glossary_order', (e.target as HTMLInputElement).value)} /></td>
          <td><input type="text" class="meaning" value={w.meaning} aria-label="Meaning of {w.word}" placeholder="what it means"
            onchange={(e) => set(w.word, 'meaning', (e.target as HTMLInputElement).value)} /></td>
          <td><button class="quiet x" onclick={() => remove(w.word)} aria-label="Delete the word {w.word}" data-tip="Delete the word (Undo brings it back)"><I.Close size={14} /></button></td>
        </tr>
      {:else}
        <tr><td colspan="8" class="muted small">{q.trim() ? 'No word matches.' : 'No words yet: type one above.'}</td></tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .words { display: flex; flex-direction: column; gap: var(--space-4); }
  .intro { margin: 0; max-width: 760px; }
  .add { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
  .add input { width: 260px; font-family: var(--font-mono); }
  table { border-collapse: collapse; width: 100%; font-size: var(--t-small); }
  th { text-align: left; font-weight: 600; padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--border); white-space: nowrap; }
  td { padding: var(--space-1) var(--space-3); border-bottom: 1px solid var(--hairline, var(--border)); vertical-align: middle; }
  tr.on td { background: var(--sel-bg); }
  tr.changed td:first-child { box-shadow: inset 3px 0 0 var(--status-draft); }
  .zh { font-family: var(--font-serif); font-size: 16px; white-space: nowrap; }
  .gl { min-width: 220px; }
  .order { width: 70px; }
  .meaning { width: 100%; min-width: 180px; }
  td input { height: 26px; border-color: transparent; background: transparent; }
  td input:hover { border-color: var(--border); }
  td input:focus { border-color: var(--link); background: var(--bg-field); }
  .bad { color: var(--status-danger); }
  .x { padding: 0 var(--space-2); }
</style>
