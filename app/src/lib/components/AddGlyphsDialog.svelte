<script lang="ts">
  // Pick glyphs (not yet in `area`) to add to it. Shared by Areas and the glyph tray.
  import { app } from '$lib/state.svelte';
  import Glyph from './Glyph.svelte';
  let { area, onclose }: { area: string; onclose: () => void } = $props();
  let q = $state('');
  let picked = $state<string[]>([]);
  let members = $derived(app.design!.areas[area]?.glyphs ?? []);
  let candidates = $derived(app.glyphs.filter((r) => !members.includes(r.glyph) && (!q || [r.glyph, r.keys, r.simplified, r.pinyin].join(' ').toLowerCase().includes(q.toLowerCase()))));
  function add() { app.addToArea(area, picked); onclose(); }
</script>

<div class="modal-bg" role="presentation" onclick={onclose}>
  <div class="modal" role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => { if (e.key === 'Escape') onclose(); }}>
    <div class="row"><h3 style="margin:0">Add glyphs to {app.areaLabel(area)} <span class="id">{area}</span></h3><span class="spacer"></span>
      <input type="text" placeholder="search name / key / pinyin" bind:value={q} />
      <button class="primary" disabled={!picked.length} onclick={add}>Add {picked.length || ''}</button>
      <button onclick={onclose}>Cancel</button></div>
    <div class="pick-grid">
      {#each candidates as r (r.glyph)}
        <label class="pick" class:on={picked.includes(r.glyph)}>
          <input type="checkbox" checked={picked.includes(r.glyph)} onchange={() => (picked = picked.includes(r.glyph) ? picked.filter((x) => x !== r.glyph) : [...picked, r.glyph])} />
          <Glyph name={r.glyph} size={44} />
          <span class="id">{r.glyph}</span>
          <span class="muted" style="font-size: var(--t-xs)">{r.areas.join(', ') || 'unassigned'}</span>
        </label>
      {/each}
      {#if !candidates.length}<p class="muted">No glyph matches.</p>{/if}
    </div>
  </div>
</div>

<style>
  .spacer { flex: 1; }
  .modal-bg { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 50; }
  .modal { background: var(--bg); border-radius: var(--radius); padding: var(--s-4); width: min(900px, 92vw); max-height: 85vh; display: flex; flex-direction: column; gap: var(--s-3); }
  .pick-grid { overflow: auto; display: grid; grid-template-columns: repeat(auto-fill, 150px); gap: 4px; }
  .pick { display: flex; align-items: center; gap: 4px; padding: 4px; border-radius: 4px; cursor: pointer; }
  .pick.on { background: var(--accent-bg); }
</style>
