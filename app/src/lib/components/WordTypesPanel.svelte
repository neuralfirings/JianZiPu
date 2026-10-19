<script lang="ts">
  // The word types of the design: pick one to edit; rule / skipped counts;
  // Advanced: rename, duplicate, add, delete.
  import { app } from '$lib/state.svelte';
  import { editor } from '$lib/editor.svelte';
  import SkipList from './SkipList.svelte';
  const d = $derived(app.design!);
  let perLayout = $derived(app.stats?.per_layout ?? {});
  let skipsFor = $state<string | null>(null);
  function addLayout() {
    const name = prompt('Id for the new word type (letters, digits, _):', 'new_word');
    if (!name || !/^[a-z][a-z0-9_]*$/i.test(name) || d.layouts.some((l) => l.name === name)) return;
    app.edit(`New word type ${name}`, (dd) => { dd.layouts.push({ name, label: name, slots: [], relationships: [], center: {} }); });
    editor.setLayout(name);
  }
  function duplicateLayout() {
    const src = editor.layout!;
    const name = prompt('Id for the copy:', `${src.name}_copy`);
    if (!name || d.layouts.some((l) => l.name === name)) return;
    app.edit(`Duplicate ${src.label ?? src.name} as ${name}`, (dd) => { dd.layouts.push({ ...JSON.parse(JSON.stringify(src)), name, label: `${src.label ?? src.name} copy` }); });
    editor.setLayout(name);
  }
  function deleteLayout() {
    const l = editor.layout!;
    if (!confirm(`Delete word type "${l.label ?? l.name}"?`)) return;
    app.edit(`Delete word type ${l.name}`, (dd) => { dd.layouts = dd.layouts.filter((x) => x.name !== l.name); });
  }
  function rename(v: string) {
    const l = editor.layout!;
    app.edit(`${l.label ?? l.name}: shown as "${v}"`, (dd) => { dd.layouts.find((x) => x.name === l.name)!.label = v; });
  }
</script>

<div class="types">
  {#each d.layouts as l (l.name)}
    <div class="type" class:on={editor.layoutName === l.name}>
      <button class="tmain" onclick={() => editor.setLayout(l.name)}>
        <span class="name">{l.label ?? l.name}</span><span class="id">{l.name}</span>
        {#if perLayout[l.name]}<span class="muted small" title="Positioning rules this word type adds to the font: one per word shape and glyph bucket">{perLayout[l.name].rules} rules</span>{/if}
      </button>
      {#if perLayout[l.name]?.skipped}
        <button class="badge-warn tskip" class:on={skipsFor === l.name} title="Word shapes that get no rule. Click to see why." onclick={() => { skipsFor = skipsFor === l.name ? null : l.name; editor.setLayout(l.name); }}>{perLayout[l.name].skipped} skipped {skipsFor === l.name ? '▾' : '▸'}</button>
      {/if}
      {#if skipsFor === l.name}
        <div class="skips"><SkipList layoutName={l.name} onclose={() => (skipsFor = null)} /></div>
      {/if}
    </div>
  {/each}
  {#if editor.advanced}
    {#if editor.layout}
      <label class="row small" style="margin-top: var(--space-4)"><span class="muted">Shown as</span><input type="text" value={editor.layout.label ?? ''} style="flex:1" onchange={(e) => rename((e.target as HTMLInputElement).value)} /></label>
    {/if}
    <div class="row wrap" style="margin-top: var(--space-2)"><button class="small" onclick={addLayout}>+ New</button><button class="small" onclick={duplicateLayout} disabled={!editor.layout}>Duplicate</button><button class="small" onclick={deleteLayout} disabled={!editor.layout}>Delete</button></div>
  {/if}
</div>

<style>
  .types { display: flex; flex-direction: column; gap: 2px; }
  .type { display: flex; flex-direction: column; border: 1px solid transparent; border-radius: var(--radius-md); }
  .type.on { background: var(--sel-bg); border-color: var(--sel-border); }
  .type.on .tmain .name { color: var(--ink); }
  .tmain { display: flex; flex-direction: column; align-items: flex-start; height: auto; padding: 4px 8px; border: 0; background: transparent; text-align: left; }
  .tskip { align-self: flex-start; margin: 0 8px 4px; height: 18px; padding: 0 6px; font-size: var(--t-caption); border: 1px solid transparent; background: transparent; }
  .tskip:hover, .tskip.on { border-color: var(--status-draft); }
  .skips { padding: 0 4px 6px; }
  .small { font-size: var(--t-caption); height: 24px; }
  .wrap { flex-wrap: wrap; }
</style>
