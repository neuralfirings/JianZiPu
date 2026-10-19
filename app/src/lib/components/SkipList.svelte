<script lang="ts">
  // Why some word shapes of a layout get no positioning rule, grouped by
  // cause, with examples that open in the editor.
  import { app } from '$lib/state.svelte';
  import { editor } from '$lib/editor.svelte';
  import { elementLabel } from '$lib/shape';
  import type { SkipGroup } from '$lib/api';
  import Glyph from './Glyph.svelte';
  let { layoutName, onclose }: { layoutName: string; onclose: () => void } = $props();
  let layout = $derived(app.design!.layouts.find((l) => l.name === layoutName)!);
  let groups = $derived(app.stats?.skipped_by_layout?.[layoutName] ?? []);
  let unsupported = $derived(!app.stats?.skipped_by_layout);   // server predates the per-cause breakdown
  const areaLabel = (a: string) => app.areaLabel(a);
  const lab = (n: string | null | undefined) => (n ? elementLabel(layout, n, areaLabel) : 'the page');
  const axisWord = (a: SkipGroup['axis']) => (a === 'y' ? 'vertical' : a === 'x' ? 'horizontal' : Array.isArray(a) ? a.map((x) => (x === 'y' ? 'vertical' : 'horizontal')).join(' and ') : '');
  function open(g: SkipGroup, ex: SkipGroup['examples'][number]) {
    editor.openShape(layoutName, ex.names, ex.pinned, g.elem ?? g.elems?.[0] ?? null);
    if (g.axis === 'x' || g.axis === 'y') editor.axis = g.axis;
  }
  let openGroup = $state(0);
</script>

<div class="skips">
  <div class="row"><strong>Why {groups.reduce((n, g) => n + g.count, 0)} shapes are skipped</strong><span class="spacer"></span><button class="tiny" onclick={onclose}>×</button></div>
  <div class="muted small">A skipped shape gets no positioning rule: those words shape, but the parts are not placed. Each line is one cause; open an example to fix it in the editor.</div>
  {#if unsupported}
    <div class="warn small">The running web server is older than this app build and does not report causes. Restart it, then reload this page:
      <code>cd src-fonttools && python3 -m jzpbuild.webserver --port 5713</code></div>
  {:else if groups.length === 0}
    <div class="muted small">Nothing skipped for this word type.</div>
  {/if}
  {#each groups as g, i (i)}
    <div class="grp" class:open={openGroup === i}>
      <button class="ghead" onclick={() => (openGroup = openGroup === i ? -1 : i)}>
        <span class="n">{g.count}</span>
        <span class="what">
          {#if g.kind === 'no_gap'}
            <b>{lab(g.elem)}</b> relative to <b>{lab(g.base)}</b> ({axisWord(g.axis)}): no rule row for
            {#if g.base_glyphs.length}{lab(g.base)} = {#each g.base_glyphs as x (x)}<span class="chip"><Glyph name={x} size={16} /></span>{/each}{/if}
            {#if g.elem_glyphs.length}{lab(g.elem)} = {#each g.elem_glyphs as x (x)}<span class="chip"><Glyph name={x} size={16} /></span>{/each}{/if}
            {#if !g.base_glyphs.length && !g.elem_glyphs.length}the glyphs not listed{/if}
            and no "otherwise".
          {:else if g.kind === 'no_rule'}
            <b>{lab(g.elem)}</b> has no {axisWord(g.axis)} rule that applies in these shapes (its bases are absent and there is no page rule).
          {:else if g.kind === 'base_absent'}
            <b>{lab(g.elem)}</b>: base {lab(g.base)} is absent from the shape.
          {:else if g.kind === 'circular'}
            {axisWord(g.axis)} rules of <b>{(g.elems ?? []).map(lab).join(', ')}</b> go round in a circle or hang on nothing.
          {:else}
            {g.examples[0]?.message}
          {/if}
        </span>
      </button>
      {#if openGroup === i}
        <div class="ex">
          {#each g.examples as ex, j (j)}
            <div class="exrow">
              <span class="names">{ex.names.map((n) => n.split('@')[0]).join(' + ')}</span>
              <span class="pins">{#each Object.entries(ex.pinned) as [n, gl] (n)}<span class="chip" title="{n} = {gl}"><Glyph name={gl} size={16} /></span>{/each}</span>
              <button class="tiny" onclick={() => open(g, ex)}>open</button>
            </div>
          {/each}
          {#if g.count > g.examples.length}<div class="muted small">… and {g.count - g.examples.length} more like these</div>{/if}
        </div>
      {/if}
    </div>
  {/each}
</div>

<style>
  .warn { color: var(--warn); }
  .warn code { display: block; margin-top: 4px; font-family: var(--mono); color: var(--fg); }
  .skips { display: flex; flex-direction: column; gap: 6px; border: 1px solid var(--warn); border-radius: var(--radius); padding: 8px; font-size: var(--t-sm); }
  .spacer { flex: 1; }
  .small { font-size: var(--t-xs); }
  .tiny { height: 20px; padding: 0 6px; font-size: var(--t-xs); }
  .grp { border: 1px solid var(--line); border-radius: var(--radius); background: var(--bg); }
  .ghead { display: flex; gap: 8px; align-items: flex-start; width: 100%; height: auto; padding: 6px 8px; border: 0; background: transparent; text-align: left; font-size: var(--t-xs); line-height: 1.4; }
  .grp.open .ghead { border-bottom: 1px solid var(--line); }
  .n { flex: none; min-width: 28px; font-family: var(--mono); font-weight: 600; color: var(--warn); }
  .what { flex: 1; min-width: 0; }
  .chip { display: inline-flex; vertical-align: middle; border: 1px solid var(--line); border-radius: 3px; padding: 1px; margin: 0 1px; background: var(--bg); }
  .ex { display: flex; flex-direction: column; gap: 3px; padding: 6px 8px; }
  .exrow { display: flex; align-items: center; gap: 6px; font-size: var(--t-xs); }
  .names { font-family: var(--mono); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pins { display: inline-flex; gap: 2px; }
</style>
