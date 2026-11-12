<script lang="ts">
  // Rename a glyph: the new name, what it changes, then one undo step (app.renameGlyph).
  import { app } from '$lib/state.svelte';
  import { hosted } from '$lib/hosted.svelte';
  import { pilot } from '$lib/pilot.svelte';
  import { renaming } from '$lib/renaming.svelte';

  const from = renaming.name!;
  let to = $state(from);
  let refused = $derived(app.renameRefusal(from));
  let failed = $state<string | null>(null);     // the state refused it after all
  let problem = $derived(refused ?? failed ?? app.renameRefusal(from, to));
  let impact = $derived(app.renameImpact(from));

  function rename() {
    if (problem) return;
    const n = to.trim();
    const why = app.renameGlyph(from, n);
    if (why) { failed = why; return; }
    const { done, undone } = renaming;
    renaming.close();
    pilot.say(`Renamed ${from} to ${n}.${hosted.isHosted ? '' : ' Its file moves when you Save.'}`,
      { undo: true, onundo: () => undone?.(from, n) });
    done?.(from, n);
  }
</script>

<div class="modal-bg" role="presentation" onclick={() => renaming.close()}>
  <div class="modal rename" role="dialog" aria-modal="true" aria-labelledby="rename-title" tabindex="-1"
    onclick={(e) => e.stopPropagation()} onkeydown={(e) => { if (e.key === 'Escape') renaming.close(); }}>
    <h3 id="rename-title">Rename <span class="mono">{from}</span></h3>
    {#if refused}
      <p>{refused}</p>
      <div class="row end"><button class="primary" onclick={() => renaming.close()}>Close</button></div>
    {:else}
      <label class="row">New name
        <!-- svelte-ignore a11y_autofocus -->
        <input type="text" class="mono" bind:value={to} oninput={() => (failed = null)} autofocus spellcheck="false" autocomplete="off"
          onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); rename(); } }} /></label>
      {#if problem && to.trim() !== from}<p class="small bad">{problem}</p>{/if}
      <p>The name is the glyph's ID, so it changes everywhere it's used:</p>
      <ul class="small">
        {#if impact.drawing}<li>its drawing: <span class="mono">{from}.svg</span> becomes <span class="mono">{to.trim() || '…'}.svg</span>{hosted.isHosted ? ' in your draft' : ' when you Save'}</li>{/if}
        {#if impact.spellings}<li>its spellings</li>{/if}
        {#if impact.areas.length}<li>its place in {impact.areas.map((a) => app.areaLabel(a)).join(', ')}</li>{/if}
        {#if impact.rules}<li>{impact.rules} spacing rule{impact.rules === 1 ? '' : 's'} that name it</li>{/if}
        {#if impact.vertical.length}<li>the Vertical form of {impact.vertical.join(', ')}</li>{/if}
      </ul>
      {#if !hosted.isHosted}<p class="small muted">If <span class="mono">site/glossary.json</span> lists it by name, change it there too: Check the glossary will point it out.</p>{/if}
      <p class="small muted">It's one step: Undo takes all of it back.</p>
      <div class="row end"><button onclick={() => renaming.close()}>Cancel</button><button class="primary" onclick={rename} disabled={!!problem}>Rename</button></div>
    {/if}
  </div>
</div>

<style>
  .rename { width: min(480px, 94vw); display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-7); }
  h3 { margin: 0; }
  p { margin: 0; }
  label { gap: var(--space-3); }
  input { flex: 1; }
  ul { margin: 0; padding-left: 20px; }
  .end { justify-content: flex-end; }
  .bad { color: var(--status-danger); }
</style>
