<script lang="ts">
  // Words typed through the live rules: GSUB of the last build, the unsaved design for
  // positions, unsaved outlines (Glyph.svelte reads app.preview first). One component for
  // every screen: the Layouts Tester panel (click a word to open it) and the glyph editor
  // (`glyph`: starts from sample words that use it and dims the words that don't).
  import { api, type Design, type WordPayload, type WordPiece } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { anchorNames, wordPage } from '$lib/shape';
  import { SAMPLE_SETS, DEFAULT_STRIP } from '$lib/words';
  import WordCanvas from './WordCanvas.svelte';

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
    /** Clicking a word: its first matched piece (Layouts opens that word type). */
    onpick?: (piece: WordPiece) => void;
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
    api.words(dd, all).then((r) => { if (r.ok && !text) text = r.words.filter((w) => w.glyphs.includes(g)).slice(0, 6).map((w) => w.word).join(' ') || DEFAULT_STRIP; }).catch(() => {});
  });
  $effect(() => {
    const dd = d, ws = words;
    if (!dd || !ws.length) { result = null; return; }
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => { if (composing) return; const r = await api.words(dd, ws); if (r.ok) result = r; }, 120);
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
    <span class="sizes" title="Size">{#each SIZES as s}<button class:on={size === s} onclick={() => (size = s)}>{s}</button>{/each}</span>
    <a href="/test?words={encodeURIComponent(text)}" title="These words on Test & Build, next to the built font">Test & Build ↗</a>
  </div>
  <div class="words">
    {#each result?.words ?? [] as w (w.word)}
      {@const piece = w.pieces.find((p) => p.layout)}
      {@const pg = wordPage(w)}
      <svelte:element this={onpick ? 'button' : 'div'} role={onpick ? undefined : 'figure'} class="word" class:dim={!!glyph && !w.glyphs.includes(glyph)}
        title={onpick ? (piece ? `Open ${piece.layout} with this word` : 'No word type matched') : w.glyphs.join(' ')}
        onclick={() => piece && onpick?.(piece)}>
        <WordCanvas elements={w.pieces.flatMap((p, pi) => { const an = anchorNames(p.elements, app.design!.areas); return p.elements.map((e) => ({ ...e, name: `${pi}:${e.name}`, anchor: an.has(e.name) })); })}
          width={Math.round((size * pg[1]) / 1600)} height={size} {showBoxes} showGlyphs={true} showPage={true} page={pg} fit={false} />
        <span class="id">{w.word}</span>
      </svelte:element>
    {/each}
  </div>
</div>

<style>
  .wt { display: flex; flex-direction: column; gap: var(--s-2); min-width: 0; }
  .row { display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap; }
  .row input { flex: 1; min-width: 140px; font-family: var(--mono); }
  .sizes { display: inline-flex; border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
  .sizes button { height: 24px; padding: 0 8px; border: 0; border-radius: 0; font-size: var(--t-xs); }
  .sizes button.on { background: var(--accent-bg); color: var(--accent); }
  a { font-size: var(--t-sm); white-space: nowrap; }
  .words { display: flex; gap: var(--s-2); overflow-x: auto; padding-bottom: 4px; align-items: flex-end; }
  .word { height: auto; display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 4px; background: var(--bg); border: 1px solid transparent; border-radius: var(--radius); }
  button.word { border-color: var(--line); }
  .word.dim { opacity: .45; }
</style>
