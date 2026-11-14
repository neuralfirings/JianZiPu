<script lang="ts">
  // One glyph's facts: name, the areas it belongs to (× removes, + adds: a design edit,
  // saved with the design), the box it gets from its first area, and its SVG file.
  // Shown in the Glyphs inspector and in the glyph editor's Glyph panel.
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import { renaming } from '$lib/renaming.svelte';
  let { glyph, showBox = true, showName = true, onrenamed }: {
    glyph: string; showBox?: boolean; showName?: boolean;
    /** after a rename (to the new name) and after its Undo (back to the old one) */
    onrenamed?: (name: string) => void;
  } = $props();

  let d = $derived(app.design!);
  let areaNames = $derived(Object.keys(d.areas));
  let mine = $derived(areaNames.filter((a) => d.areas[a].glyphs.includes(glyph)));
  let svg = $derived(app.svgs[glyph] ?? null);
  const rename = () => renaming.ask(glyph, { done: (_f, to) => onrenamed?.(to), undone: (f) => onrenamed?.(f) });
  let info = $derived(svg ? { paths: (svg.match(/<path/g) ?? []).length, kb: (new Blob([svg]).size / 1024).toFixed(1) } : null);
</script>

<div class="gf">
  {#if showName}
    <div class="h"><button class="name mono" onclick={rename} data-tip="Rename {glyph}">{glyph}</button>
      <button class="quiet sm ren" onclick={rename} aria-label="Rename {glyph}" data-tip="Rename {glyph}"><I.EditRow size={14} /></button>{#if !svg}<span class="badge-warn"> · no SVG on disk</span>{/if}</div>
  {/if}
  <div class="row"><span class="k">In areas</span>
    {#each mine as a (a)}<span class="chip">{app.areaLabel(a)} <span class="id">{a}</span> <button class="x" title="Remove from {a}" onclick={() => app.removeFromArea(a, glyph)} aria-label="Remove from {a}"><I.Close size={12} /></button></span>{/each}
    <select onchange={(e) => { const v = (e.target as HTMLSelectElement).value; if (v) app.addToArea(v, [glyph]); (e.target as HTMLSelectElement).value = ''; }}>
      <option value="">+ Add to area…</option>
      {#each areaNames.filter((a) => !mine.includes(a)) as a}<option value={a}>{app.areaLabel(a)} ({a})</option>{/each}
    </select>
  </div>
  {#if showBox}
    <div><span class="k">Box</span> {#if mine[0]}{d.areas[mine[0]].size.join(' × ')} <span class="muted">from</span> <a href="/layouts?area={mine[0]}&g={encodeURIComponent(glyph)}" title="Area Properties on the Layouts screen (box size)">{app.areaLabel(mine[0])}</a>{:else}<span class="muted">set by the area it joins</span>{/if}</div>
  {/if}
  <div><span class="k">File</span> {#if svg}inputs/svg/{glyph}.svg{#if info} · {info.paths} path{info.paths === 1 ? '' : 's'} · {info.kb} KB{/if}{:else}<span class="muted">none</span>{/if}</div>
</div>

<style>
  .name { border: 0; background: transparent; padding: 3px 0; min-height: 24px; height: auto; font-weight: 600; font-size: inherit; cursor: text; text-decoration: underline dotted var(--border); text-underline-offset: 3px; }
  .name:hover { text-decoration-color: var(--link); color: var(--link); }
  .h { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
  .ren { padding: 0 var(--space-2); }
  .gf { display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; font-size: var(--t-small); }
  .row { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
  .mono { font-family: var(--font-mono); }
  .k { display: inline-block; width: 70px; color: var(--ink-muted); }
  .x { height: 16px; padding: 0 4px; border: 0; background: transparent; }
  select { height: 26px; }
  @media (max-width: 759.98px) { .x { width: var(--control-sm); height: var(--control-sm); } }
</style>
