<script module lang="ts">
  export type Section = { key: string; title: string; sub?: string; glyphs: string[]; decimals?: boolean };
</script>

<script lang="ts">
  // The List view (Glyphs): one row per glyph, spellings edited in place like a spreadsheet.
  // Enter saves and moves down, Tab moves right, Esc puts the old value back; a pasted range
  // of cells (tab-separated, from a spreadsheet) fills down and across in one undo step.
  // Position decimals are typed by pattern: one folded, read-only group.
  import { renaming } from '$lib/renaming.svelte';
  import { describeUses, usesOf } from '$lib/glossary';
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import { typingCheck } from '$lib/typingcheck.svelte';
  import * as T from '$lib/typing';
  import Glyph from './Glyph.svelte';
  import SpellInput from './SpellInput.svelte';

  let {
    sections, selected, onselect, onopen, onglossary, flat = false, showAreas = false, onnotice
  }: {
    sections: Section[]; selected: string | null; onselect: (g: string) => void;
    /** a click on the row's drawing: show the glyph in the glyph panel */
    onopen?: (g: string) => void;
    /** a click on the Glossary column: show the glyph's row in that section in Glyphs > Glossary */
    onglossary?: (sid: string, glyph: string) => void;
    flat?: boolean; showAreas?: boolean; onnotice?: (text: string, undo?: boolean) => void;
  } = $props();

  const COLS = T.FIELDS;
  /** glyph -> where the glossary shows it (Glyphs > Glossary); the Glossary column, read-only */
  let uses = $derived(usesOf(app.glossary, app.glossarySections));
  /** a glyph with spellings the glossary shows nowhere: the glossary check reports it */
  const left = (g: string) => !uses[g] && !!app.glossarySections.length && !T.isEmpty(app.typing[g]) && !partnerOf[g]
    && ['latin', 'latin_alt', 'common', 'simplified', 'traditional'].some((f) => T.get(app.typing, g)[f as T.SpellField]);
  const PASTE: T.SpellField[] = ['latin', 'latin_alt', 'simplified', 'traditional', 'vert_variant', 'pinyin'];
  let openDecimals = $state(false);
  let table: HTMLTableElement;

  let editable = $derived(sections.filter((s) => !s.decimals).flatMap((s) => s.glyphs));
  let partnerOf = $derived(T.partners(app.typing));
  const status = (g: string) => typingCheck.statusOf(g);
  const issueText = (g: string) => typingCheck.issuesFor(g).join(' · ');

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
      <th title="Where the font page's glossary shows the glyph: its own row in a section, or in a word. Edited in Glyphs > Glossary.">Glossary</th>
      {#if showAreas}<th>Areas</th>{/if}
      {#if flat}<th>Issue</th>{/if}
    </tr>
  </thead>
  {#each sections as s (s.key)}
    <tbody>
      {#if !flat}
        <tr class="grp"><td colspan={COLS.length + 3 + (showAreas ? 1 : 0)}>
          <strong>{s.title}</strong> <span class="muted">{s.sub ?? ''} · {s.glyphs.length}</span>
          {#if s.decimals}<button class="lnk" onclick={() => (openDecimals = !openDecimals)}>{#if openDecimals}<I.Unfolded size={12} /> hide{:else}<I.Folded size={12} /> show{/if}</button> <span class="muted">typed by pattern, nothing to fill</span>{/if}
        </td></tr>
      {/if}
      {#if !s.decimals}
        {#each s.glyphs as g (g)}
          {@const partner = partnerOf[g]}
          <tr data-g={g} class:on={selected === g} class:bad={status(g) === 'err'} onfocusin={() => onselect(g)} onclick={() => onselect(g)}>
            <td class="st {status(g)}" title={issueText(g)}>{#if status(g) === 'err'}<I.Problem size={14} />{:else if status(g) === 'warn'}<I.Warn size={14} />{/if}</td>
            <td class="gl"><button class="ga" onclick={() => onopen?.(g)} aria-label="Show {g} in the glyph panel" data-tip="Show it in the glyph panel"><Glyph name={g} size={26} /></button><span class="gnw"><button class="gn" data-tip="Rename {g}"
              onclick={() => renaming.ask(g, { done: (_f, to) => onselect(to), undone: (f) => onselect(f) })}>{g}</button></span></td>
            {#each COLS as f}
              <td data-f={f}>
                {#if f === 'vert_variant' && partner}<span class="muted small" title="This is the vertical form of {partner}: typed after a colon"><I.PartnerOf size={12} /> of {partner}</span>
                {:else}<SpellInput glyph={g} field={f} cell onenter={(dir) => move(g, f, dir)} onpastegrid={(grid) => paste(g, f, grid)} />{/if}
              </td>
            {/each}
            <td class="gu">
              {#each describeUses(uses[g] ?? [], app.glossarySections) as line, i (line)}
                <button class="use" onclick={(e) => { e.stopPropagation(); onglossary?.(uses[g].map((u) => u.sid).filter((x, j, a) => a.indexOf(x) === j)[i], g); }}
                  data-tip="Show it in Glyphs > Glossary">{line}</button>
              {:else}
                {#if left(g)}<button class="use warn" onclick={(e) => { e.stopPropagation(); onglossary?.('', g); }}
                  data-tip="Add it to a section in Glyphs > Glossary (99: Hidden in Glossary leaves it out on purpose)"><I.Warn size={12} /> not in the glossary</button>{/if}
              {/each}
            </td>
            {#if showAreas}<td class="small muted">{app.glyphs.find((r) => r.glyph === g)?.areas.map((a) => app.areaLabel(a)).join(', ')}</td>{/if}
            {#if flat}<td class="small issue">{issueText(g)}</td>{/if}
          </tr>
        {/each}
      {:else if openDecimals || flat}
        {#each s.glyphs as g (g)}
          <tr data-g={g} class="ro" class:on={selected === g} onclick={() => onselect(g)}>
            <td class="st"></td>
            <td class="gl"><button class="ga" onclick={() => onopen?.(g)} aria-label="Show {g} in the glyph panel" data-tip="Show it in the glyph panel"><Glyph name={g} size={26} /></button><span class="gn">{g}</span></td>
            <td colspan={COLS.length + 1} class="small muted">{T.decimalPatterns(g).join(' · ')}</td>
            {#if showAreas}<td></td>{/if}
            {#if flat}<td></td>{/if}
          </tr>
        {/each}
      {/if}
    </tbody>
  {/each}
</table>

<style>
  .kt { border-collapse: collapse; width: 100%; font-size: var(--t-small); }
  thead th { position: sticky; top: 0; z-index: 2; background: var(--bg-panel); text-align: left; font-weight: 600; color: var(--ink); padding: var(--space-3) var(--space-2); border-bottom: 1px solid var(--border-strong); white-space: nowrap; font-size: var(--t-small); }
  td { padding: 1px 3px; border-bottom: 1px solid var(--hairline); vertical-align: middle; }
  tbody tr:not(.grp):hover td { background: var(--bg-hover); }
  tr.grp td { background: var(--bg-sunken); padding: 3px 8px; font-family: var(--font-display); font-weight: 600; font-size: var(--t-label); }
  tr.on td { background: var(--sel-bg); }
  tr.bad td { background: var(--status-danger-bg); }
  tr.ro td { color: var(--ink-muted); }
  td[data-f] { min-width: 70px; }
  td[data-f='pinyin'] { min-width: 90px; }
  .st { width: 18px; text-align: center; }
  .st.err { color: var(--status-danger); }
  .st.warn { color: var(--status-draft); }
  .gl { display: flex; align-items: center; gap: 6px; white-space: nowrap; }
  .ga { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; padding: 0; border: 1px solid transparent; border-radius: var(--radius-sm); background: transparent; cursor: pointer; }
  .ga:hover { border-color: var(--sel-border); background: var(--sel-bg); }
  .gnw { display: inline-flex; flex-direction: column; align-items: flex-start; min-width: 0; }
  .gu { min-width: 150px; }
  .use { display: block; border: 0; background: transparent; padding: 0; min-height: 24px; height: auto; text-align: left; font-family: var(--font-serif); font-size: var(--t-caption); color: var(--ink-muted); cursor: pointer; white-space: nowrap; }
  .use:hover { color: var(--link); }
  .use.warn { color: var(--status-draft); }
  .gn { font-family: var(--font-mono); font-size: var(--t-caption); border: 0; background: transparent; padding: 0; height: auto; cursor: text; text-decoration: underline dotted var(--border); text-underline-offset: 3px; }
  button.gn:hover { text-decoration-color: var(--link); color: var(--link); }
  .issue { color: var(--ink-muted); max-width: 280px; }
  .small { font-size: var(--t-caption); }
  .lnk { height: 20px; padding: 0 6px; border-style: dashed; background: transparent; font-size: var(--t-caption); }
</style>
