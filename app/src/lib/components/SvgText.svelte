<script lang="ts">
  // One outline from its SVG text (not by name): Review's before / after / overlay.
  // tone: 'before' = dashed orange edge, 'after' = solid blue edge (design system ov-before / ov-after).
  import { parseSvg } from '$lib/svg';
  let { text, size = 96, ghost = null, label = '', tone = null }: { text: string | null | undefined; size?: number; ghost?: string | null; label?: string; tone?: 'before' | 'after' | null } = $props();
  let p = $derived(parseSvg(text ?? undefined));
  let g = $derived(parseSvg(ghost ?? undefined));
</script>

<figure style="width:{size}px">
  <div class="box {tone ?? ''}" style="width:{size}px;height:{size}px">
    {#if g}<svg class="ghost" viewBox={g.viewBox} width={size} height={size} aria-hidden="true">{@html g.inner}</svg>{/if}
    {#if p}<svg viewBox={p.viewBox} width={size} height={size} class:over={!!g} aria-label={label}>{@html p.inner}</svg>
    {:else}<span class="none">none</span>{/if}
  </div>
  {#if label}<figcaption>{label}</figcaption>{/if}
</figure>

<style>
  figure { margin: 0; display: flex; flex-direction: column; gap: var(--space-2); align-items: center; }
  .box { position: relative; border: 1px solid var(--hairline); border-radius: var(--radius-sm); background: var(--bg-canvas); color: var(--glyph); }
  .box.before { border: 1px dashed var(--ov-before); }
  .box.after { border: 1px solid var(--ov-after); }
  .box svg { position: absolute; inset: 0; }
  .ghost { color: var(--ov-before); opacity: .55; }
  .over { color: var(--ov-after); opacity: .75; }
  .none { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--ink-muted); font-size: var(--t-small); }
  figcaption { font-size: var(--t-small); font-weight: 600; }
</style>
