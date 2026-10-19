<script lang="ts">
  // One outline from its SVG text (not by name): Review's before / after / overlay.
  import { parseSvg } from '$lib/svg';
  let { text, size = 96, ghost = null, label = '' }: { text: string | null | undefined; size?: number; ghost?: string | null; label?: string } = $props();
  let p = $derived(parseSvg(text ?? undefined));
  let g = $derived(parseSvg(ghost ?? undefined));
</script>

<figure style="width:{size}px">
  <div class="box" style="width:{size}px;height:{size}px">
    {#if g}<svg class="ghost" viewBox={g.viewBox} width={size} height={size} aria-hidden="true">{@html g.inner}</svg>{/if}
    {#if p}<svg viewBox={p.viewBox} width={size} height={size} class:over={!!g} aria-label={label}>{@html p.inner}</svg>
    {:else}<span class="none">none</span>{/if}
  </div>
  {#if label}<figcaption>{label}</figcaption>{/if}
</figure>

<style>
  figure { margin: 0; display: flex; flex-direction: column; gap: 2px; align-items: center; }
  .box { position: relative; border: 1px solid var(--line); border-radius: 4px; background: var(--canvas); color: var(--fg); }
  .box svg { position: absolute; inset: 0; }
  .ghost { color: var(--danger); opacity: .45; }
  .over { color: var(--accent); opacity: .75; }
  .none { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--fg-2); font-size: var(--t-sm); }
  figcaption { font-size: var(--t-xs); color: var(--fg-2); }
</style>
