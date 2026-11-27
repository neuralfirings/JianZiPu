<script lang="ts">
  // Words typed through the live rules: GSUB of the last build, the unsaved design for
  // positions, unsaved outlines (Glyph.svelte reads app.preview first). One component for
  // every screen: the Layouts Tester panel (click a word to open it) and the glyph editor
  // (`glyph`: starts from sample words that use it and dims the words that don't).
  import * as I from '$lib/icons';
  import { api, type Design, type WordPayload, type WordPiece } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { anchorNames, wordPage } from '$lib/shape';
  import { SAMPLE_SETS, DEFAULT_STRIP } from '$lib/words';
  import WordCanvas from './WordCanvas.svelte';
  import WordInfo from './WordInfo.svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';

  let {
    design = null, glyph = null, storageKey = null, showBoxes = false, size: size0 = 116, onpick
  }: {
    /** The design to position with (default: the app's, unsaved edits included). */
    design?: Design | null;
    glyph?: string | null;
    /** localStorage key that keeps the typed words and size between visits. */
    storageKey?: string | null;
    showBoxes?: boolean;
    size?: number;
    /** Layouts: the info box's Edit in Layouts loads the picked word's piece into the canvas (no page load). */
    onpick?: (piece: WordPiece, at: { area: string; glyph: string | null }) => void;
  } = $props();

  const SIZES = [40, 72, 116];
  const load = (k: string) => { try { return storageKey ? localStorage.getItem(`${storageKey}${k}`) : null; } catch { return null; } };
  // starting values only: the text and size are the viewer's from here on
  // svelte-ignore state_referenced_locally
  let text = $state(load('') ?? (glyph ? '' : DEFAULT_STRIP));
  // svelte-ignore state_referenced_locally
  let size = $state(+(load(':size') ?? 0) || size0);
  let result = $state<WordPayload | null>(null);
  let composing = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let words = $derived(text.split(/\s+/).filter(Boolean));
  /** Each word's page ruled into 1000-unit cells (kept in this browser, shared with Build & test). */
  let cells = $state(((): boolean => { try { return localStorage.getItem('jzp-show-cells') === '1'; } catch { return false; } })());
  $effect(() => { const c = cells; try { localStorage.setItem('jzp-show-cells', c ? '1' : '0'); } catch {} });
  /** The glyph clicked in a word (not in Layouts, where a click loads the word): its word and part. */
  let pick = $state<{ wi: number; name: string } | null>(null);
  $effect(() => { if (pick && !result?.words[pick.wi]) pick = null; });
  const here = () => page.url.pathname + page.url.search;
  /** Double-clicking a glyph opens its editor, coming back here. */
  function open(wi: number, name: string) {
    const w = result?.words[wi]; if (!w) return;
    const at = name.indexOf(':'), el = w.pieces[+name.slice(0, at)]?.elements.find((e) => e.name === name.slice(at + 1));
    if (el?.glyph && el.glyph !== glyph) goto(`/glyphs/${encodeURIComponent(el.glyph)}/edit?back=${encodeURIComponent(here())}`);
  }
  let d = $derived(design ?? app.design);

  $effect(() => {
    const t = text, s = size;
    if (!storageKey) return;
    try { localStorage.setItem(storageKey, t); localStorage.setItem(`${storageKey}:size`, String(s)); } catch {}
  });
  // with a glyph and nothing typed: the sample words whose shaping uses it
  $effect(() => {
    const dd = d, g = glyph;
    if (!dd || !g || text) return;
    const all = [...new Set(Object.values(SAMPLE_SETS).flat())].filter((w) => !/\s/.test(w));
    api.words(dd, all, app.typedWith).then((r) => { if (r.ok && !text) text = r.words.filter((w) => w.glyphs.includes(g)).slice(0, 6).map((w) => w.word).join(' ') || DEFAULT_STRIP; }).catch(() => {});
  });
  $effect(() => {
    const dd = d, ws = words, typed = app.typedWith;
    if (!dd || !ws.length) { result = null; return; }
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => { if (composing) return; const r = await api.words(dd, ws, typed); if (r.ok) result = r; }, 120);
  });
  function random() {
    const all = Object.values(SAMPLE_SETS).flat();
    text = Array.from({ length: 8 }, () => all[Math.floor(Math.random() * all.length)]).join(' ');
  }
</script>

<div class="wt">
  <div class="row">
    <input type="text" bind:value={text} placeholder={glyph ? 'words that use this glyph' : 'test words'} spellcheck="false"
      oncompositionstart={() => (composing = true)} oncompositionend={() => { composing = false; text = text + ''; }} />
    <select title="Fill in a sample set" onchange={(e) => { const v = (e.target as HTMLSelectElement).value; if (v) text = SAMPLE_SETS[v].join(' '); (e.target as HTMLSelectElement).value = ''; }}>
      <option value="">Sample set…</option>{#each Object.keys(SAMPLE_SETS) as s}<option value={s}>{s}</option>{/each}
    </select>
    <button onclick={random} title="Eight random sample words">Random</button>
    <label class="cellsopt"><input type="checkbox" bind:checked={cells} /> Show cells</label>
    <span class="sizes" title="Size">{#each SIZES as s}<button class:on={size === s} onclick={() => (size = s)}>{s}</button>{/each}</span>
    <a href="/test?words={encodeURIComponent(text)}" title="These words on Build & test, next to the built font">Build & test <I.Opens size={12} /></a>
  </div>
  <div class="body">
  <div class="words">
    {#each result?.words ?? [] as w, i (`${i}:${w.word}`)}
      {@const piece = w.pieces.find((p) => p.layout)}
      {@const pg = wordPage(w)}
      <div role="figure" class="word" class:on={pick?.wi === i}
        title={`${w.word}: ${!piece ? 'no word type matched' : glyph && !w.glyphs.includes(glyph) ? `${w.glyphs.join(' ')} (doesn't use ${glyph})` : w.glyphs.join(' ')}`}>
        <WordCanvas elements={w.pieces.flatMap((p, pi) => { const an = anchorNames(p.elements, app.design!.areas); return p.elements.map((e) => ({ ...e, name: `${pi}:${e.name}`, anchor: an.has(e.name) })); })}
          width={Math.round((size * pg[1]) / 1600)} height={size} {showBoxes} showGlyphs={true} showPage={true} page={pg} fit={false} {cells} bare
          picked={pick?.wi === i ? pick.name : null}
          onselect={(n) => { if (n) pick = { wi: i, name: n }; else if (pick?.wi === i) pick = null; }}
          onopen={(n) => open(i, n)} />
      </div>
    {/each}
  </div>
  {#if pick && result?.words[pick.wi]}
    {@const pw = result.words[pick.wi]}
    {@const pp = pw.pieces[+pick.name.slice(0, pick.name.indexOf(':'))]}
    {@const pe = pp?.elements.find((e) => e.name === pick!.name.slice(pick!.name.indexOf(':') + 1))}
    <!-- in Layouts (onpick), Edit loads the word into the canvas there and then, with the area's properties -->
    <WordInfo word={pw} name={pick.name} back={here()} onclose={() => (pick = null)} onedit={onpick && pp?.layout && pe ? () => onpick!(pp, { area: pe.area, glyph: pe.glyph ?? null }) : undefined} />
  {/if}
  </div>
</div>

<style>
  .wt { display: flex; flex-direction: column; gap: var(--space-4); min-width: 0; }
  .row { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
  .row input[type=text] { flex: 1; min-width: 140px; font-family: var(--font-mono); }
  .sizes { display: inline-flex; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
  .sizes button { height: 24px; padding: 0 8px; border: 0; border-radius: 0; font-size: var(--t-caption); }
  .sizes button.on { background: var(--sel-bg); color: var(--ink); }
  a { font-size: var(--t-small); white-space: nowrap; }
  /* the words side by side as in running text: no gaps, each character boxed in light grey */
  .words { display: flex; gap: 0; overflow-x: auto; padding: 1px 0 4px 1px; align-items: flex-end; }
  .word { display: flex; border: 1px solid var(--border); margin-left: -1px; background: var(--bg-canvas); }
  .word :global(.canvas) { border-radius: 0; }
  .word.on { border-color: var(--sel-border); position: relative; z-index: 1; }
  .body { display: flex; gap: var(--space-4); align-items: flex-start; min-width: 0; }
  .body .words { flex: 1; min-width: 0; }
  .cellsopt { display: inline-flex; align-items: center; gap: var(--space-2); font-size: var(--t-small); white-space: nowrap; }
</style>
