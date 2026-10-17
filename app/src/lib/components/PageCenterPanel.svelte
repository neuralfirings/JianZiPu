<script lang="ts">
  // The page centre every word type centres on unless it sets its own target.
  import { app } from '$lib/state.svelte';
  const d = $derived(app.design!);
  function setCenter(k: 'x' | 'y', v: number) { app.edit(`Page center ${k} ${v}`, (dd) => { dd.center[k] = v; }); }
</script>

<div class="muted small">Where words are centred on the page, in font units. A word type can override it in Centering.</div>
<div class="row">
  <label>x <input type="number" value={d.center.x} onchange={(e) => setCenter('x', +(e.target as HTMLInputElement).value)} /></label>
  <label>y <input type="number" value={d.center.y} onchange={(e) => setCenter('y', +(e.target as HTMLInputElement).value)} /></label>
</div>

<style>
  .small { font-size: var(--t-xs); }
</style>
