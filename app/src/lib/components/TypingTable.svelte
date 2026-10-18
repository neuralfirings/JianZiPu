<script module lang="ts">
  export type Section = { key: string; title: string; sub?: string; glyphs: string[]; decimals?: boolean };
</script>

<script lang="ts">
  // The Typing view: one row per glyph, spellings edited in place like a spreadsheet.
  // Enter saves and moves down, Tab moves right, Esc puts the old value back; a pasted range
  // of cells (tab-separated, from a spreadsheet) fills down and across in one undo step.
  // Position decimals are typed by pattern: one folded, read-only group.
  import { app } from '$lib/state.svelte';
  import { typingCheck } from '$lib/typingcheck.svelte';
  import * as T from '$lib/typing';
  import Glyph from './Glyph.svelte';
  import SpellInput from './SpellInput.svelte';

  let {
    sections, selected, onselect, flat = false, showAreas = false, onnotice
  }: {
    sections: Section[]; selected: string | null; onselect: (g: string) => void;
    flat?: boolean; showAreas?: boolean; onnotice?: (text: string, undo?: boolean) => void;
  } = $props();

  const COLS: T.SpellField[] = ['latin', 'latin_alt', 'common', 'simplified', 'traditional', 'vert_variant', 'pinyin'];
  const PASTE: T.SpellField[] = ['latin', 'latin_alt', 'simplified', 'traditional', 'vert_variant', 'pinyin'];
  let openDecimals = $state(false);
  let table: HTMLTableElement;

  let editable = $derived(sections.filter((s) => !s.decimals).flatMap((s) => s.glyphs));
  let partnerOf = $derived(T.partners(app.typing));
  let errGlyphs = $derived(new Set(app.typingErrors.flatMap((e) => (e.kind === 'clash' ? e.glyphs : [e.glyph]))));
  const status = (g: string) => errGlyphs.has(g) ? 'err' : typingCheck.warningsFor(g).length ? 'warn' : '';
  const issueText = (g: string) => [
    ...app.typingErrors.filter((e) => (e.kind === 'clash' ? e.glyphs.includes(g) : e.glyph === g)).map((e) => e.message),
    ...typingCheck.warningsFor(g)
  ].join(' · ');

  function move(g: string, f: T.SpellField, dir: 1 | -1) {
    const i = editable.indexOf(g) + dir;
    if (i < 0 || i >= editable.length) return;
    const next = editable[i];
    onselect(next);
    queueMicrotask(() => table?.querySelector<HTMLInputElement>(`tr[data-g="${CSS.escape(next)}"] td[data-f="${f}"] input`)?.focus());
  }

  function paste(g: string, f: T.SpellField, grid: string[][]) {
    const r0 = editable.indexOf(g), c0 = PASTE.indexOf(f);
    if (r0 < 0 || c0 < 0) return;
    const rows = Math.min(grid.length, editable.length - r0);
    const cols = Math.min(Math.max(...grid.map((r) => r.length)), PASTE.length - c0);
    app.editTyping(`Paste ${rows} × ${cols} cells into ${editable[r0]}…`, (t) => {
      for (let i = 0; i < rows; i++)
        for (let j = 0; j < cols; j++) {
          const v = grid[i][j];
          if (v === undefined) continue;
          (t[editable[r0 + i]] ??= T.empty())[PASTE[c0 + j]] = v.trim();
        }
    });
    onnotice?.(`Pasted ${rows} × ${cols} cells, from ${editable[r0]} ${T.LABEL[f]}.`, true);
  }
</script>

<table class="kt" bind:this={table}>
  <thead>
    <tr>
      <th class="st"></th><th>Glyph Name</th>
      {#each COLS as f}<th title={T.HELP[f]}>{T.LABEL[f]}</th>{/each}
      {#if showAreas}<th>Areas</th>{/if}
      {#if flat}<th>Issue</th>{/if}
    </tr>
  </thead>
  {#each sections as s (s.key)}
    <tbody>
      {#if !flat}
        <tr class="grp"><td colspan={COLS.length + 2 + (showAreas ? 1 : 0)}>
          <strong>{s.title}</strong> <span class="muted">{s.sub ?? ''} · {s.glyphs.length}</span>
          {#if s.decimals}<button class="lnk" onclick={() => (openDecimals = !openDecimals)}>{openDecimals ? '▾ hide' : '▸ show'}</button> <span class="muted">typed by pattern, nothing to fill</span>{/if}
        </td></tr>
      {/if}
      {#if !s.decimals}
        {#each s.glyphs as g (g)}
          {@const partner = partnerOf[g]}
          <tr data-g={g} class:on={selected === g} class:bad={status(g) === 'err'} onfocusin={() => onselect(g)} onclick={() => onselect(g)}>
            <td class="st {status(g)}" title={issueText(g)}>{status(g) === 'err' ? '✕' : status(g) === 'warn' ? '⚠' : ''}</td>
            <td class="gl"><span class="ga"><Glyph name={g} size={26} /></span><span class="gn">{g}</span></td>
            {#each COLS as f}
              <td data-f={f}>
                {#if f === 'vert_variant' && partner}<span class="muted small" title="This is the vertical form of {partner}: typed after a colon">↖ of {partner}</span>
                {:else}<SpellInput glyph={g} field={f} cell onenter={(dir) => move(g, f, dir)} onpastegrid={(grid) => paste(g, f, grid)} />{/if}
              </td>
            {/each}
            {#if showAreas}<td class="small muted">{app.glyphs.find((r) => r.glyph === g)?.areas.map((a) => app.areaLabel(a)).join(', ')}</td>{/if}
            {#if flat}<td class="small issue">{issueText(g)}</td>{/if}
          </tr>
        {/each}
      {:else if openDecimals || flat}
        {#each s.glyphs as g (g)}
          <tr data-g={g} class="ro" class:on={selected === g} onclick={() => onselect(g)}>
            <td class="st"></td>
            <td class="gl"><span class="ga"><Glyph name={g} size={26} /></span><span class="gn">{g}</span></td>
            <td colspan={COLS.length} class="small muted">{T.decimalPatterns(g).join(' · ')}</td>
            {#if showAreas}<td></td>{/if}
            {#if flat}<td></td>{/if}
          </tr>
        {/each}
      {/if}
    </tbody>
  {/each}
</table>

<style>
  .kt { border-collapse: collapse; width: 100%; font-size: var(--t-sm); }
  thead th { position: sticky; top: 0; z-index: 2; background: var(--bg-2); text-align: left; font-weight: 500; color: var(--fg-2); padding: 4px; border-bottom: 1px solid var(--line); white-space: nowrap; font-size: var(--t-xs); }
  td { padding: 1px 3px; border-bottom: 1px solid color-mix(in srgb, var(--line) 50%, transparent); vertical-align: middle; }
  tr.grp td { background: var(--bg-3); padding: 3px 8px; }
  tr.on td { background: var(--accent-bg); }
  tr.bad td { background: color-mix(in srgb, var(--danger) 8%, transparent); }
  tr.ro td { color: var(--fg-2); }
  td[data-f] { min-width: 70px; }
  td[data-f='pinyin'] { min-width: 90px; }
  .st { width: 18px; text-align: center; }
  .st.err { color: var(--danger); }
  .st.warn { color: var(--warn); }
  .gl { display: flex; align-items: center; gap: 6px; white-space: nowrap; }
  .ga { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; }
  .gn { font-family: var(--mono); font-size: var(--t-xs); }
  .issue { color: var(--fg-2); max-width: 280px; }
  .small { font-size: var(--t-xs); }
  .lnk { height: 20px; padding: 0 6px; border-style: dashed; background: transparent; font-size: var(--t-xs); }
</style>
