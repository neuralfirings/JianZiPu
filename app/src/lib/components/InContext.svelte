<script lang="ts">
  // The glyph inside real words, rendered with the live rules and the unsaved outline
  // (Glyph.svelte reads app.preview first). Defaults to sample words that use the glyph.
  import { api, type WordPayload } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { anchorNames } from '$lib/shape';
  import WordCanvas from './WordCanvas.svelte';
  import { SAMPLE_SETS } from '$lib/words';
  let { glyph }: { glyph: string } = $props();
  let text = $state('');
  let size = $state(64);
  let result = $state<WordPayload | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;
  let words = $derived(text.split(/\s+/).filter(Boolean));

  // default words: the sample words whose shaping uses this glyph
  $effect(() => {
    const d = app.design, g = glyph;
    if (!d || text) return;
    const all = [...new Set(Object.values(SAMPLE_SETS).flat())].filter((w) => !/\s/.test(w));
    api.words(d, all).then((r) => { if (r.ok && !text) text = r.words.filter((w) => w.glyphs.includes(g)).slice(0, 5).map((w) => w.word).join(' ') || 's7k5 0k3'; }).catch(() => {});
  });
  $effect(() => {
    const d = app.design, ws = words;
    if (!d || !ws.length) return;
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => { const r = await api.words(d, ws); if (r.ok) result = r; }, 120);
  });
</script>

<div class="ctx">
  <div class="row">
    <input type="text" bind:value={text} style="flex: 1; font-family: var(--mono)" placeholder="words that use this glyph" />
    <span class="sizes">{#each [32, 64, 120] as s}<button class:on={size === s} onclick={() => (size = s)}>{s}</button>{/each}</span>
    <a href="/test" title="The full Tester, with the saved outline">Open in Tester ↗</a>
  </div>
  <div class="words">
    {#each result?.words ?? [] as w (w.word)}
      <div class="word" class:uses={w.glyphs.includes(glyph)}>
        <WordCanvas elements={w.pieces.flatMap((p, pi) => { const an = anchorNames(p.elements, app.design!.areas); return p.elements.map((e) => ({ ...e, name: `${pi}:${e.name}`, anchor: an.has(e.name) })); })} width={Math.round(size * 0.62)} height={size} showBoxes={false} showGlyphs={true} showPage={true} page={[0, Math.max(1000, w.advance + 1000)]} fit={false} />
        <span class="id">{w.word}</span>
      </div>
    {/each}
  </div>
</div>

<style>
  .ctx { display: flex; flex-direction: column; gap: var(--s-2); }
  .sizes { display: inline-flex; border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
  .sizes button { height: 24px; padding: 0 8px; border: 0; border-radius: 0; font-size: var(--t-xs); }
  .sizes button.on { background: var(--accent-bg); color: var(--accent); }
  .words { display: flex; gap: var(--s-3); overflow-x: auto; padding-bottom: 4px; align-items: flex-end; }
  .word { display: flex; flex-direction: column; align-items: center; gap: 2px; opacity: .5; }
  .word.uses { opacity: 1; }
  a { font-size: var(--t-sm); white-space: nowrap; }
</style>
