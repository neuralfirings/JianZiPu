<script lang="ts">
  // One example word drawn from the live preview's layout (api.words): its glyphs at their places,
  // the row's glyph in the accent colour, as the font page marks it (Glyphs > Glossary, Usage).
  import type { WordPiece } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { parseSvg } from '$lib/svg';
  /** `scale`: px per font unit, so every character is the same size (a vertical word grows taller); else `height`. */
  /** `mark`: the glyphs drawn red (the row's glyph or its word's), none when the example is only the row. */
  let { pieces, mark, height = 56, scale = 0 }: { pieces: WordPiece[]; mark: string[]; height?: number; scale?: number } = $props();
  // the blank control glyphs (the colon before a vertical word, the chord bar's space) draw nothing: leave
  // them out of the size, or a vertical word sits under an empty gap
  let els = $derived(pieces.flatMap((p) => p.elements).filter((e) => e.glyph && !app.control.includes(e.glyph)));
  let box = $derived.by(() => {
    if (!els.length) return null;
    const x0 = Math.min(...els.map((e) => e.x)), x1 = Math.max(...els.map((e) => e.x + e.size[0]));
    const y0 = Math.min(...els.map((e) => e.y)), y1 = Math.max(...els.map((e) => e.y + e.size[1]));
    // a drawing can reach past its part's box (散's top over its box): leave room for it, and don't clip
    const pad = 0.1 * Math.max(x1 - x0, y1 - y0);
    return { x: x0 - pad, y: -(y1 + pad), w: x1 - x0 + 2 * pad, h: y1 - y0 + 2 * pad };
  });
</script>

{#if box}
  {@const h = scale ? Math.min(160, Math.round(box.h * scale)) : height}
  <svg class="ex" viewBox="{box.x} {box.y} {box.w} {box.h}" height={h} width={Math.max(16, Math.round((h * box.w) / box.h))} aria-hidden="true">
    {#each els as e, i (i)}
      {@const g = parseSvg(app.svgs[e.glyph])}
      {#if g}<svg x={e.x} y={-(e.y + e.size[1])} width={e.size[0]} height={e.size[1]} viewBox={g.viewBox} class:mark={mark.includes(e.glyph)}>{@html g.inner}</svg>{/if}
    {/each}
  </svg>
{/if}

<style>
  .ex { display: block; color: var(--glyph, var(--ink)); overflow: visible; }
  .ex svg { overflow: visible; }
  .mark { color: var(--accent); }
</style>
