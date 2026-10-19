<script lang="ts">
  import { app } from '$lib/state.svelte';
  import { parseSvg } from '$lib/svg';
  let { name, size = 48, title = name }: { name: string; size?: number; title?: string } = $props();
  let parsed = $derived(parseSvg(app.preview[name] ?? app.svgs[name]));
</script>

{#if parsed}
  <svg width={size} height={size} viewBox={parsed.viewBox} class="glyph" aria-label={name}><title>{title}</title>{@html parsed.inner}</svg>
{:else}
  <span class="missing" style="width:{size}px;height:{size}px;font-size:{Math.max(9, size / 5)}px" title={name}>{name.replace(/^(md|lg|xl|mod)_/, '')}</span>
{/if}

<style>
  .glyph { display: block; color: var(--ink); }
  .missing { display: inline-flex; align-items: center; justify-content: center; border: 1px dashed var(--border); border-radius: 4px; color: var(--ink-muted); font-family: var(--font-mono); overflow: hidden; }
</style>
