<script lang="ts">
  import { api, type WordPayload } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { editor } from '$lib/editor.svelte';
  import { anchorNames, wordPage } from '$lib/shape';
  import WordCanvas from './WordCanvas.svelte';
  import { SAMPLE_SETS, DEFAULT_STRIP } from '$lib/words';
  let text = $state(localStorage.getItem('jzp-strip-words') ?? DEFAULT_STRIP);
  let result = $state<WordPayload | null>(null);
  let composing = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let words = $derived(text.split(/\s+/).filter(Boolean));
  $effect(() => {
    const d = editor.dragDesign ?? app.design, ws = words;
    if (!d) return;
    try { localStorage.setItem('jzp-strip-words', text); } catch {}
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => { if (composing) return; const r = await api.words(d, ws); if (r.ok) result = r; }, 120);
  });
  function random() {
    const all = Object.values(SAMPLE_SETS).flat();
    text = Array.from({ length: 8 }, () => all[Math.floor(Math.random() * all.length)]).join(' ');
  }
</script>

<div class="strip">
  <div class="row">
    <input type="text" bind:value={text} style="flex: 1; font-family: var(--mono)" placeholder="test words"
      oncompositionstart={() => (composing = true)} oncompositionend={() => { composing = false; text = text + ''; }} />
    <select onchange={(e) => { const v = (e.target as HTMLSelectElement).value; if (v) text = SAMPLE_SETS[v].join(' '); (e.target as HTMLSelectElement).value = ''; }}>
      <option value="">Sample set…</option>{#each Object.keys(SAMPLE_SETS) as s}<option value={s}>{s}</option>{/each}
    </select>
    <button onclick={random}>Random</button>
  </div>
  <div class="words">
    {#each result?.words ?? [] as w (w.word)}
      {@const piece = w.pieces.find((p) => p.layout)}
      <button class="word" title={piece ? `Open ${piece.layout} with this word` : 'No word type matched'} onclick={() => piece && editor.loadWord(piece)}>
        <WordCanvas elements={w.pieces.flatMap((p, pi) => { const an = anchorNames(p.elements, app.design!.areas); return p.elements.map((e) => ({ ...e, name: `${pi}:${e.name}`, anchor: an.has(e.name) })); })} width={72} height={116} showBoxes={editor.showBoxes} showGlyphs={true} showPage={true} page={wordPage(w)} fit={false} />
        <span class="id">{w.word}</span>
      </button>
    {/each}
  </div>
</div>

<style>
  .strip { display: flex; flex-direction: column; gap: var(--s-2); }
  .words { display: flex; gap: var(--s-2); overflow-x: auto; padding-bottom: 4px; }
  .word { height: auto; display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 4px; background: var(--bg); }
</style>
