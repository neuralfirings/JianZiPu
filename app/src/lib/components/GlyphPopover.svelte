<script lang="ts">
  // A floating glyph chooser: fixed to the viewport, anchored at a screen
  // point (right-aligned to it), with search when the list is long.
  import Glyph from './Glyph.svelte';
  let { title, glyphs, current = null, anchor, onpick, onclose }: {
    title: string; glyphs: string[]; current?: string | null;
    anchor: { x: number; y: number };            // screen coordinates of the anchor's bottom-right
    onpick: (g: string) => void; onclose: () => void;
  } = $props();
  const W = 460;
  let q = $state('');
  let width = $derived(Math.min(W, window.innerWidth - 16));
  let left = $derived(Math.max(8, Math.min(anchor.x - width, window.innerWidth - width - 8)));
  let top = $derived(Math.max(8, Math.min(anchor.y + 6, window.innerHeight - 120)));
  let shown = $derived(q ? glyphs.filter((g) => g.toLowerCase().includes(q.toLowerCase())) : glyphs);
</script>

<svelte:window onpointerdown={(e) => { if (!(e.target as Element).closest?.('.gpop, [data-gpop-anchor]')) onclose(); }} onkeydown={(e) => { if (e.key === 'Escape') { e.stopPropagation(); onclose(); } }} />

<div class="gpop" style="left:{left}px; top:{top}px; width:{width}px">
  <div class="phead"><span class="ptitle">{title}</span><span class="muted">{glyphs.length} glyphs</span>
    {#if glyphs.length > 24}<input class="psearch" placeholder="find…" bind:value={q} />{/if}
    <button class="pclose" title="Close" onclick={onclose}>×</button></div>
  <div class="pgrid">
    {#each shown as g (g)}
      <button class="pcell" class:on={g === current} title={g} onclick={() => onpick(g)}><Glyph name={g} size={36} /></button>
    {/each}
  </div>
</div>

<style>
  .gpop { position: fixed; z-index: 30; background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: 0 10px 32px rgba(0,0,0,.22); padding: 8px; box-sizing: border-box; }
  .phead { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: var(--t-sm); }
  .ptitle { font-weight: 600; white-space: nowrap; }
  .psearch { height: 24px; width: 110px; font-size: var(--t-xs); margin-left: auto; }
  .pclose { height: 24px; width: 24px; padding: 0; border: 0; background: transparent; color: var(--fg-2); font-size: 16px; }
  .phead .muted { color: var(--fg-2); font-size: var(--t-xs); }
  .pgrid { display: grid; grid-template-columns: repeat(auto-fill, 44px); gap: 3px; max-height: min(400px, 60vh); overflow: auto; }
  .pcell { width: 44px; height: 44px; padding: 3px; border: 1px solid var(--line); border-radius: 5px; background: var(--bg); }
  .pcell:hover { border-color: var(--accent); }
  .pcell.on { border-color: var(--accent); background: var(--accent-bg); }
</style>
