<script lang="ts">
  // One draft's changes, item by item (docs/PILOT-UX.md "Review"). Three uses:
  //   owner  — Nancy reviewing a tester's draft or .zip: Keep / Skip, pick conflicts, Apply
  //   import — a tester opening a .zip into their own draft: the same, into their draft
  //   mine   — a tester's read-only "See my changes" (against what the draft started from)
  // Apply makes one undo step of unsaved changes (glyph files included); nothing is written until Save.
  import type { Bundle } from '$lib/bundle';
  import { applyMerge, diffBundle, hunks, lineDiff, pretty, type Item } from '$lib/merge';
  import { app } from '$lib/state.svelte';
  import { day, hhmm } from '$lib/pilot.svelte';
  import * as T from '$lib/typing';
  import SvgText from './SvgText.svelte';
  import WordTester from './WordTester.svelte';

  let { bundle, mode, name, onapplied, onexport }: {
    bundle: Bundle; mode: 'owner' | 'import' | 'mine'; name: string;
    onapplied?: (r: { count: number; message: string }) => void;
    onexport?: () => void;
  } = $props();

  /** What the draft is compared with: the app now, or (mine) what the draft started from. */
  let current = $derived.by(() => {
    if (mode !== 'mine') return { design: app.design!, typing: app.typing, svgs: app.svgs };
    const svgs = { ...app.mainSvgs, ...bundle.base.svgs };
    for (const n of bundle.manifest.svgs.added) delete svgs[n];
    return { design: bundle.base.design, typing: bundle.base.typing, svgs };
  });
  let items = $derived(diffBundle(bundle, current));
  // true = take the draft's, false = keep what the Builder has, undefined = conflict not picked yet
  let picks = $state<Record<string, boolean | undefined>>({});
  let seeded = '';
  $effect(() => {
    const key = items.map((i) => i.id).join('|');
    if (key === seeded) return;
    seeded = key;
    picks = Object.fromEntries(items.map((i) => [i.id, i.conflict ? undefined : true]));
  });
  let filter = $state<'all' | 'conflicts' | 'skipped'>('all');
  let open = $state<Record<string, boolean>>({});

  const readOnly = $derived(mode === 'mine');
  const who = $derived(mode === 'owner' ? `${name}'s` : mode === 'mine' ? 'Your' : 'The draft’s');
  let conflicts = $derived(items.filter((i) => i.conflict));
  let unpicked = $derived(conflicts.filter((i) => picks[i.id] === undefined));
  let skipped = $derived(items.filter((i) => picks[i.id] === false));
  let keeping = $derived(items.filter((i) => picks[i.id] === true));
  let shown = $derived(items.filter((i) => filter === 'all' || (filter === 'conflicts' ? i.conflict : picks[i.id] === false)));
  let sections = $derived([
    { title: 'Glyphs', items: shown.filter((i) => i.kind === 'glyph') },
    { title: 'Spellings', items: shown.filter((i) => i.kind === 'spelling') },
    { title: 'Design', items: shown.filter((i) => i.kind === 'design') }
  ]);

  function setAll(v: boolean) { picks = Object.fromEntries(items.map((i) => [i.id, v])); }
  /** A glyph and its spelling row travel together. */
  function pick(it: Item, v: boolean) {
    const next = { ...picks, [it.id]: v };
    if (it.kind === 'glyph' && it.status === 'added') { const s = `spelling:${it.key}`; if (s in next && !items.find((i) => i.id === s)?.conflict) next[s] = v; }
    picks = next;
  }

  function commitMessage(applied: Item[]): string {
    const g = applied.filter((i) => i.kind === 'glyph').map((i) => i.key);
    const sp = applied.filter((i) => i.kind === 'spelling').length;
    const d = applied.filter((i) => i.kind === 'design').map((i) => (i.kind === 'design' ? i.label.replace(/^Area · |^Word type · /, '') : ''));
    const parts = [
      ...(g.length > 3 ? [`${g.length} glyphs`] : g),
      ...(sp ? [`${sp} spelling${sp === 1 ? '' : 's'}`] : []),
      ...(d.length > 3 ? [`${d.length} design items`] : d)
    ];
    return `Apply ${name}'s draft: ${parts.join(', ')}`;
  }

  function apply() {
    if (unpicked.length || !keeping.length) return;
    const keep = Object.fromEntries(items.map((i) => [i.id, picks[i.id] === true]));
    const m = applyMerge(items, keep, current);
    const label = mode === 'owner' ? `From ${name}: ${m.applied.length} change${m.applied.length === 1 ? '' : 's'}` : `Import ${name}: ${m.applied.length} change${m.applied.length === 1 ? '' : 's'}`;
    app.applyChanges(label, m);
    onapplied?.({ count: m.applied.length, message: commitMessage(m.applied) });
  }

  /** The design with only this item applied (for "after" sample words). */
  function designWith(it: Item) {
    return applyMerge([it], { [it.id]: true }, current).design;
  }
  const FIELD = T.LABEL as Record<string, string>;
  const svgOf = (t: string | undefined) => t ?? null;
  function diffLines(it: Item) {
    if (it.kind !== 'design') return [];
    return hunks(lineDiff(pretty(it.conflict ? it.current : it.base), pretty(it.theirs)), 2);
  }
  const m = $derived(bundle.manifest);
</script>

<div class="review">
  <div class="head">
    <div>
      <h2>{mode === 'mine' ? 'Your changes' : mode === 'import' ? `Import ${name}` : `${name}'s draft`}</h2>
      <p class="muted">
        saved {day(m.updated)} {hhmm(m.updated)}
        {#if m.base.date}· based on the font of {day(m.base.date)}{/if}
        {#if mode === 'owner' && app.main?.date}· your Builder is on {day(app.main.date)}{/if}
        {#if m.note}<br />“{m.note}”{/if}
      </p>
    </div>
    <span class="spacer"></span>
    {#if readOnly}
      {#if onexport}<button onclick={onexport}>Export…</button>{/if}
    {:else}
      <div class="seg" role="tablist">
        <button class:on={filter === 'all'} onclick={() => (filter = 'all')}>All {items.length}</button>
        <button class:on={filter === 'conflicts'} onclick={() => (filter = 'conflicts')}>Conflicts {conflicts.length}</button>
        <button class:on={filter === 'skipped'} onclick={() => (filter = 'skipped')}>Skipped {skipped.length}</button>
      </div>
      <button onclick={() => setAll(true)}>Keep all</button>
      <button onclick={() => setAll(false)}>Skip all</button>
    {/if}
  </div>

  {#if !items.length}
    <p class="empty">{mode === 'mine' ? 'No changes yet: your draft is the same as the font.' : 'Nothing to apply: the Builder already has every change in this draft.'}</p>
  {/if}

  {#each sections as sec}
    {#if sec.items.length}
      <h3>{sec.title} <span class="muted">{sec.items.length}</span></h3>
      {#each sec.items as it (it.id)}
        <div class="item" class:skip={picks[it.id] === false && !readOnly} class:conflict={it.conflict && !readOnly}>
          <div class="ihead">
            <b class="key">{it.kind === 'design' ? it.label : it.key}</b>
            <span class="badge {it.status}">{it.status}</span>
            {#if it.conflict && !readOnly}<span class="badge conflict">conflict</span>{/if}
            {#if it.kind === 'design'}<span class="muted sum">{it.summary.join(' · ')}</span>{/if}
            <span class="spacer"></span>
            {#if it.kind === 'design' && it.unit.type === 'area' && mode !== 'mine'}<a href="/layouts?area={it.unit.name}">Open in Layouts</a>{/if}
            {#if !readOnly && !it.conflict}
              <div class="seg">
                <button class:on={picks[it.id] === true} onclick={() => pick(it, true)}>Keep</button>
                <button class:on={picks[it.id] === false} onclick={() => pick(it, false)}>Skip</button>
              </div>
            {/if}
          </div>

          {#if it.kind === 'glyph'}
            <div class="views">
              {#if it.conflict && !readOnly}
                <SvgText text={svgOf(it.base)} label="Before{m.base.date ? ` (${day(m.base.date)})` : ''}" />
                <SvgText text={svgOf(it.theirs)} label="{who} draft" />
                <SvgText text={svgOf(it.current)} label="Your Builder now" />
              {:else}
                <SvgText text={svgOf(it.base ?? it.current)} label="before" />
                <SvgText text={svgOf(it.theirs)} label="after" />
                {#if it.status === 'changed'}<SvgText text={svgOf(it.theirs)} ghost={svgOf(it.base ?? it.current)} label="before / after" />{/if}
              {/if}
            </div>
          {:else if it.kind === 'spelling'}
            <table class="cells">
              <thead><tr><th></th><th>before</th><th>{mode === 'mine' ? 'yours' : 'draft'}</th>{#if it.conflict && !readOnly}<th>your Builder now</th>{/if}</tr></thead>
              <tbody>
                {#each it.fields as f}
                  <tr class:cf={f.conflict && !readOnly}><th>{FIELD[f.field] ?? f.field}</th><td>{f.base || '—'}</td><td class="new">{f.theirs || '—'}</td>{#if it.conflict && !readOnly}<td>{f.current || '—'}</td>{/if}</tr>
                {/each}
              </tbody>
            </table>
          {:else}
            <div class="more">
              <button class="link" onclick={() => (open = { ...open, [it.id + ':w']: !open[it.id + ':w'] })}>{open[it.id + ':w'] ? 'Hide' : 'Show'} sample words, before and after</button>
              <button class="link" onclick={() => (open = { ...open, [it.id]: !open[it.id] })}>{open[it.id] ? 'Hide' : 'Show'} JSON changes ({diffLines(it).filter((l) => l.op === '+' || l.op === '-').length} lines)</button>
            </div>
            {#if open[it.id + ':w']}
              <div class="words">
                <div><span class="muted">before</span><WordTester design={current.design} size={40} /></div>
                <div><span class="muted">after</span><WordTester design={designWith(it)} size={40} /></div>
              </div>
            {/if}
            {#if open[it.id]}
              <pre class="diff">{#each diffLines(it) as l}<span class="op{l.op === '+' ? 'add' : l.op === '-' ? 'del' : l.op === '…' ? 'gap' : ''}">{l.op === '…' ? `  … ${l.text}` : `${l.op} ${l.text}`}
</span>{/each}</pre>
            {/if}
          {/if}

          {#if it.conflict && !readOnly}
            <div class="pickrow">
              <span class="muted">{picks[it.id] === undefined ? 'pick one to apply' : ''}</span>
              <span class="spacer"></span>
              <button class:on={picks[it.id] === true} onclick={() => pick(it, true)}>Use {mode === 'owner' ? `${name}'s` : 'the draft’s'}</button>
              <button class:on={picks[it.id] === false} onclick={() => pick(it, false)}>Keep yours</button>
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  {/each}

  {#if !readOnly && items.length}
    <div class="applybar">
      <span>Keeping {keeping.length} of {items.length}{#if unpicked.length} · <b class="warn">{unpicked.length} conflict{unpicked.length === 1 ? '' : 's'} to pick</b>{/if}</span>
      <span class="muted small">{mode === 'owner' ? 'Applied changes become unsaved changes in your Builder. Nothing is written until you Save.' : 'Applied changes go into your draft as unsaved changes.'}</span>
      <span class="spacer"></span>
      <button class="primary" onclick={apply} disabled={!!unpicked.length || !keeping.length}
        title={unpicked.length ? `Pick ${unpicked.length} conflict${unpicked.length === 1 ? '' : 's'} first` : ''}>Apply {keeping.length} change{keeping.length === 1 ? '' : 's'}</button>
    </div>
  {/if}
</div>

<style>
  .review { display: flex; flex-direction: column; gap: var(--s-3); max-width: 980px; }
  .head { display: flex; align-items: flex-start; gap: var(--s-2); flex-wrap: wrap; }
  h2 { margin: 0; font-size: var(--t-xl); font-weight: 600; }
  h3 { margin: var(--s-3) 0 0; font-size: var(--t-lg); font-weight: 600; }
  .head p { margin: 2px 0 0; }
  .spacer { flex: 1; }
  .seg { display: inline-flex; }
  .seg button { border-radius: 0; margin-left: -1px; }
  .seg button:first-child { border-radius: var(--radius) 0 0 var(--radius); margin-left: 0; }
  .seg button:last-child { border-radius: 0 var(--radius) var(--radius) 0; }
  button.on { background: var(--accent-bg); color: var(--accent); border-color: var(--accent); position: relative; }
  .item { border: 1px solid var(--line); border-radius: var(--radius); padding: var(--s-3); display: flex; flex-direction: column; gap: var(--s-2); background: var(--bg); }
  .item.skip { opacity: .55; }
  .item.conflict { border-color: var(--warn); }
  .ihead { display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap; }
  .key { font-family: var(--mono); font-size: var(--t-md); }
  .sum { font-size: var(--t-sm); }
  .badge { font-size: var(--t-xs); padding: 1px 6px; border-radius: 8px; background: var(--bg-3); }
  .badge.added { color: var(--ok); }
  .badge.deleted { color: var(--danger); }
  .badge.conflict { color: var(--warn); font-weight: 600; }
  .views { display: flex; gap: var(--s-3); flex-wrap: wrap; }
  .cells { border-collapse: collapse; font-size: var(--t-sm); }
  .cells th, .cells td { border: 1px solid var(--line); padding: 2px 8px; text-align: left; }
  .cells thead th { font-weight: 500; color: var(--fg-2); }
  .cells .new { color: var(--accent); }
  .cells tr.cf td { background: var(--accent-bg); }
  .more { display: flex; gap: var(--s-3); flex-wrap: wrap; }
  .link { border: 0; background: none; color: var(--accent); padding: 0; height: auto; }
  .words { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3); }
  .words > div { min-width: 0; }
  .diff { margin: 0; max-height: 320px; overflow: auto; font-family: var(--mono); font-size: var(--t-xs); background: var(--bg-2); border-radius: 4px; padding: var(--s-2); }
  .opadd { color: var(--ok); }
  .opdel { color: var(--danger); }
  .opgap { color: var(--fg-2); }
  .pickrow { display: flex; gap: var(--s-2); align-items: center; }
  .applybar { position: sticky; bottom: 0; display: flex; gap: var(--s-3); align-items: center; flex-wrap: wrap; padding: var(--s-3); border: 1px solid var(--line); border-radius: var(--radius); background: var(--bg-2); }
  .warn { color: var(--warn); }
  .small { font-size: var(--t-sm); }
  .empty { color: var(--fg-2); }
</style>
