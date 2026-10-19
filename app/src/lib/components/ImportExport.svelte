<script lang="ts">
  import { app } from '$lib/state.svelte';
  import type { Design } from '$lib/api';
  import { designSummary } from '$lib/merge';
  let { mode, onclose }: { mode: 'import' | 'export'; onclose: () => void } = $props();

  function download() {
    const d = app.design!;
    const blob = new Blob([JSON.stringify(d, null, 2) + '\n'], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `jzp-design-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    onclose();
  }

  let file = $state<{ name: string; design: Design; diff: string[] } | null>(null);
  let err = $state<string | null>(null);
  let merge = $state<'replace' | 'merge'>('replace');

  async function pick(e: Event) {
    err = null; file = null;
    const f = (e.target as HTMLInputElement).files?.[0];
    if (!f) return;
    try {
      const d = JSON.parse(await f.text());
      if (!d || d.version !== 2 || !Array.isArray(d.layouts) || typeof d.areas !== 'object')
        throw new Error("This isn't a Builder design file (needs version 2, layouts[] and areas{}).");
      const r = await (await import('$lib/api')).api.check(d);
      if (!r.ok) throw new Error(r.error ?? 'invalid design');
      file = { name: f.name, design: d, diff: designSummary(app.design!, d) };
    } catch (ex) {
      err = (ex as Error).message;
    }
  }

  function apply() {
    if (!file) return;
    const d = file.design;
    if (merge === 'replace') app.importDesign(d, `Import ${file.name}`);
    else
      app.edit(`Merge ${file.name}`, (cur) => {
        for (const l of d.layouts) if (!cur.layouts.some((x) => x.name === l.name)) cur.layouts.push(l);
        for (const [name, a] of Object.entries(d.areas)) {
          if (!cur.areas[name]) cur.areas[name] = a;
          else for (const g of a.glyphs) if (!cur.areas[name].glyphs.includes(g)) cur.areas[name].glyphs.push(g);
        }
        if (d.test_sets) cur.test_sets = { ...(d.test_sets ?? {}), ...(cur.test_sets ?? {}) };
      });
    onclose();
  }
  const d = $derived(app.design!);
</script>

<div class="modal-bg" role="presentation" onclick={onclose}>
  <div class="modal" role="dialog" onclick={(e) => e.stopPropagation()}>
    {#if mode === 'export'}
      <h3>Export</h3>
      <p>One file with everything the Builder edits, readable by the font build as <code>inputs/design.json</code>:</p>
      <ul>
        <li>Word types &amp; spacing ({d.layouts.length})</li>
        <li>Areas: box sizes &amp; glyph members ({Object.keys(d.areas).length})</li>
        <li>Test word sets ({Object.keys(d.test_sets ?? {}).length})</li>
      </ul>
      <p class="muted">Spellings live in components.csv: import or export them from Glyphs ⋯ (they save with the same Save). SVG files are not included.</p>
      <div class="row"><button class="primary" onclick={download}>Download JSON</button><button onclick={onclose}>Close</button></div>
    {:else}
      <h3>Import</h3>
      <p>Choose a design file. Nothing is written to disk: the import becomes unsaved changes you can inspect and Save or Discard.</p>
      <input type="file" accept="application/json,.json" onchange={pick} />
      {#if err}<p class="error">{err}</p>{/if}
      {#if file}
        <p><strong>{file.name}</strong> · {file.design.layouts.length} word types · {Object.keys(file.design.areas).length} areas</p>
        {#if file.diff.length}
          <p>Differences from what's loaded:</p>
          <ul>{#each file.diff as line}<li>{line}</li>{/each}</ul>
        {:else}
          <p class="muted">Identical to what's loaded.</p>
        {/if}
        <label><input type="radio" bind:group={merge} value="replace" /> Replace everything</label><br />
        <label><input type="radio" bind:group={merge} value="merge" /> Merge: keep mine, add what's new</label>
        <div class="row" style="margin-top: var(--s-3)"><button class="primary" onclick={apply}>Import</button><button onclick={onclose}>Cancel</button></div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .modal-bg { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 50; }
  .modal { background: var(--bg); border-radius: var(--radius); padding: var(--s-5); width: min(560px, 90vw); max-height: 85vh; overflow: auto; }
  h3 { margin-top: 0; }
</style>
