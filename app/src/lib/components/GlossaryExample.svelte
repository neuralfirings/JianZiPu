<script lang="ts">
  // One example word drawn from the live preview's layout (api.words): its glyphs at their places,
  // the row's glyph in the accent colour, as the font page marks it (Glyphs > Glossary, Usage).
  import type { WordPiece } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { parseSvg } from '$lib/svg';
  let { pieces, mark, height = 56 }: { pieces: WordPiece[]; mark: string; height?: number } = $props();
  let els = $derived(pieces.flatMap((p) => p.elements).filter((e) => e.glyph));
  let box = $derived.by(() => {
    if (!els.length) return null;
    const x0 = Math.min(...els.map((e) => e.x)), x1 = Math.max(...els.map((e) => e.x + e.size[0]));
    const y0 = Math.min(...els.map((e) => e.y)), y1 = Math.max(...els.map((e) => e.y + e.size[1]));
    const pad = 20;
    return { x: x0 - pad, y: -(y1 + pad), w: x1 - x0 + 2 * pad, h: y1 - y0 + 2 * pad };
  });
</script>

{#if box}
  <svg class="ex" viewBox="{box.x} {box.y} {box.w} {box.h}" height={height} width={Math.max(16, Math.round((height * box.w) / box.h))} aria-hidden="true">
    {#each els as e, i (i)}
      {@const g = parseSvg(app.svgs[e.glyph])}
      {#if g}<svg x={e.x} y={-(e.y + e.size[1])} width={e.size[0]} height={e.size[1]} viewBox={g.viewBox} class:mark={e.glyph === mark}>{@html g.inner}</svg>{/if}
    {/each}
  </svg>
{/if}

<style>
  .ex { display: block; color: var(--glyph, var(--ink)); }
  .mark { color: var(--accent); }
</style>
