<script lang="ts">
  // One draft's changes, item by item (docs/PILOT-UX.md "Review"). Three uses:
  //   owner  — Nancy reviewing a tester's draft or .zip: Keep / Skip, pick conflicts, Apply
  //   import — a tester opening a .zip into their own draft: the same, into their draft
  //   mine   — a tester's "Your changes" (against what the draft started from): Undo this change
  //            puts one item, or one spacing rule, back the way the draft started
  //   sent   — a Change Request as it was sent (read-only, against what it started from)
  //   decide — an admin's review of a Change Request: Keep / Skip each change, saved on the
  //            request (nothing is applied; kept changes go into a release candidate later)
  // Apply and each Undo make one undo step of unsaved changes (glyph files included); nothing is
  // written until Save.
  import * as I from '$lib/icons';
  import type { Bundle } from '$lib/bundle';
  import type { Layout } from '$lib/api';
  import { applyMerge, diffBundle, gapText, hunks, lineDiff, pretty, revertItems, revertRule, ruleChanges, usesOfGlyph, type DesignItem, type Item, type RuleChange } from '$lib/merge';
  import { app } from '$lib/state.svelte';
  import { canWithdraw, startSvgs } from '$lib/requests';
  import { day, hhmm, pilot } from '$lib/pilot.svelte';
  import * as T from '$lib/typing';
  import SendRequestDialog from './SendRequestDialog.svelte';
  import SvgText from './SvgText.svelte';
  import WordTester from './WordTester.svelte';

  let { bundle, mode, name, onapplied, onexport, decisions = {}, ondecide, send = false }: {
    bundle: Bundle; mode: 'owner' | 'import' | 'mine' | 'sent' | 'decide'; name: string;
    onapplied?: (r: { count: number; message: string }) => void;
    onexport?: () => void;
    /** mine: open Send Change Request straight away (Continue from Your Change Requests). */
    send?: boolean;
    /** decide: the saved decisions to start from, and what Save decisions hands back. */
    decisions?: Record<string, 'keep' | 'skip'>;
    ondecide?: (d: Record<string, 'keep' | 'skip'>) => void;
  } = $props();

  /** What the draft is compared with: the app now, or (mine) what the draft started from. */
  let current = $derived.by(() => {
    if (mode !== 'mine' && mode !== 'sent' && mode !== 'decide') return { design: app.design!, typing: app.typing, svgs: app.svgs };
    return { design: bundle.base.design, typing: bundle.base.typing, svgs: startSvgs(bundle, app.mainSvgs) };
  });
  let items = $derived(diffBundle(bundle, current));
  // true = take the draft's, false = keep what the Builder has, undefined = conflict not picked yet
  let picks = $state<Record<string, boolean | undefined>>({});
  let seeded = '';
  $effect(() => {
    const key = items.map((i) => i.id).join('|');
    if (key === seeded) return;
    seeded = key;
    picks = Object.fromEntries(items.map((i) => [i.id, i.conflict ? undefined : decisions[i.id] !== 'skip']));
  });
  let filter = $state<'all' | 'conflicts' | 'skipped'>('all');
  let open = $state<Record<string, boolean>>({});

  const readOnly = $derived(mode === 'mine' || mode === 'sent');
  const who = $derived(mode === 'owner' ? `${name}'s` : mode === 'mine' || mode === 'sent' ? 'Your' : 'The draft’s');
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

  /** Your changes: items a sent Change Request holds can't be undone (or sent again). */
  const lockOf = (it: Item) => (mode === 'mine' ? app.lockOf(it.id) : undefined);
  /** Why Undo is off for a sent change (the button's tooltip). A disabled button gets no hover,
   *  so a locked one stays enabled but marked aria-disabled and does nothing. */
  const lockTip = (it: Item) => {
    const l = lockOf(it);
    if (!l) return '';
    const r = app.requests.find((x) => x.id === l.id);
    const how = r && canWithdraw(r) ? 'Withdraw the request to undo it.' : 'It was kept for the font, so it stays as sent.';
    return `Locked: this change is in your Change Request "${l.title}", sent ${day(l.sent)}. ${how}`;
  };
  let sendable = $derived(mode === 'mine' ? items.filter((i) => !app.lockOf(i.id)) : []);
  let sending = $state(false);
  $effect(() => { if (send && mode === 'mine') sending = true; });
  const nameOf = (it: Item) => (it.kind === 'design' ? it.label : it.key);
  /** A new glyph that spellings or areas still use: its id while "undo all of it?" is showing. */
  let asking = $state<string | null>(null);
  function usesText(g: string) {
    const u = usesOfGlyph(g, app.design!, app.typing);
    return [...(u.spellings ? ['its spellings'] : []), ...u.areas.map((a) => `the area ${app.areaLabel(a)}`)].join(' and ');
  }
  /** Your changes: put one item back the way the draft started (one undo step). */
  function undoItem(it: Item) {
    if (!app.design) return;
    let these = [it];
    const newGlyph = it.kind === 'glyph' && it.status === 'added';
    if (newGlyph) {
      if (usesText(it.key) && asking !== it.id) { asking = it.id; return; }
      const sp = items.find((i) => i.id === `spelling:${it.key}`);
      if (sp) these = [it, sp];
    }
    asking = null;
    const m = revertItems(these, { design: app.design, typing: app.typing, svgs: app.svgs });
    if (newGlyph) for (const a of Object.values(m.design.areas)) a.glyphs = a.glyphs.filter((g) => g !== it.key);
    app.applyChanges(`Undo: ${nameOf(it)}`, m);
    pilot.say(`${nameOf(it)} is back the way your draft started.`, { undo: true });
  }
  function undoRule(it: DesignItem, r: RuleChange) {
    const base = it.base as Layout;
    app.edit(`Undo: ${it.label} · ${r.label}`, (d) => {
      const i = d.layouts.findIndex((l) => l.name === it.unit.name);
      if (i >= 0) d.layouts[i] = revertRule(d.layouts[i], base, r.key);
    });
    pilot.say(`That spacing rule of ${it.label.replace(/^Word type · /, '')} is back the way your draft started.`, { undo: true });
  }
  /** The spacing rules a changed word type differs in. */
  const rulesOf = (it: Item) => (it.kind === 'design' && it.unit.type === 'layout' && it.status === 'changed'
    ? ruleChanges(it.base as Layout, it.theirs as Layout) : []);

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

{#if sending}<SendRequestDialog items={sendable} onclose={() => (sending = false)} />{/if}

<div class="review">
  {#if mode !== 'sent'}
  <div class="head">
    <div>
      <h2>{mode === 'mine' ? 'Your changes' : mode === 'import' ? `Import ${name}` : mode === 'decide' ? 'The changes' : `${name}'s draft`}</h2>
      <p class="muted">
        saved {day(m.updated)} {hhmm(m.updated)}
        {#if m.base.date}· based on the font of {day(m.base.date)}{/if}
        {#if mode === 'owner' && app.main?.date}· your Builder is on {day(app.main.date)}{/if}
        {#if m.note}<br />“{m.note}”{/if}
      </p>
    </div>
    <span class="spacer"></span>
    {#if readOnly}
      {#if mode === 'mine'}<a class="btnlink" href="/requests">Your Change Requests</a>{/if}
      {#if onexport}<button onclick={onexport}>Export…</button>{/if}
      {#if mode === 'mine'}
        <button class="primary" onclick={() => (sending = true)} disabled={!sendable.length}
          title={sendable.length ? '' : items.length ? 'Every change is already in a Change Request' : 'No changes to send yet'}><I.Send size={14} /> Send Change Request…</button>
      {/if}
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
  {/if}

  {#if !items.length}
    <p class="empty">{mode === 'sent' ? 'Everything in this request is already in the font.' : mode === 'mine' ? 'No changes yet: your draft is the same as the font.' : 'Nothing to apply: the Builder already has every change in this draft.'}</p>
  {/if}

  {#each sections as sec}
    {#if sec.items.length}
      <h3>{sec.title} <span class="muted">{sec.items.length}</span></h3>
      {#each sec.items as it (it.id)}
        <div class="item" class:skip={picks[it.id] === false && !readOnly} class:conflict={it.conflict && !readOnly}>
          <div class="ihead">
            <b class="key">{it.kind === 'design' ? it.label : it.key}</b>
            <span class="tag {it.status}">{it.status}</span>
            {#if it.conflict && !readOnly}<span class="pill danger"><I.Problem size={14} />Conflict</span>{/if}
            {#if it.kind === 'design'}<span class="muted sum">{it.summary.join(' · ')}</span>{/if}
            <span class="spacer"></span>
            {#if it.kind === 'design' && it.unit.type === 'area' && !readOnly}<a href="/layouts?area={it.unit.name}">Open in Layouts</a>{/if}
            {#if lockOf(it)}
              {@const l = lockOf(it)!}
              <a class="pill info" href="/requests#{l.id}"><I.Lock size={14} />Sent {day(l.sent)} · {l.title}</a>
              <button class="sm" aria-disabled="true" data-tip={lockTip(it)}><I.Undo size={14} /> Undo this change</button>
            {:else if mode === 'mine'}
              <button class="sm" onclick={() => undoItem(it)}><I.Undo size={14} /> Undo this change</button>
            {/if}
            {#if !readOnly && !it.conflict}
              <div class="seg">
                <button class:on={picks[it.id] === true} onclick={() => pick(it, true)}>Keep</button>
                <button class:on={picks[it.id] === false} onclick={() => pick(it, false)}>Skip</button>
              </div>
            {/if}
          </div>
          {#if asking === it.id}
            <div class="banner draft" role="alert">
              <span class="ic"><I.Warn /></span>
              <span>{it.key} is still used by {usesText(it.key)}. Undoing the glyph takes those out too.</span>
              <span class="spacer"></span>
              <button class="sm" onclick={() => (asking = null)}>Cancel</button>
              <button class="sm danger" onclick={() => undoItem(it)}>Undo all of it</button>
            </div>
          {/if}

          {#if it.kind === 'glyph'}
            <div class="views">
              {#if it.conflict && !readOnly}
                <SvgText text={svgOf(it.base)} tone="before" label="Before{m.base.date ? ` (${day(m.base.date)})` : ''}" />
                <SvgText text={svgOf(it.theirs)} tone="after" label="{who} draft" />
                <SvgText text={svgOf(it.current)} label="Your Builder now" />
              {:else}
                <SvgText text={svgOf(it.base ?? it.current)} tone="before" label="Before" />
                <SvgText text={svgOf(it.theirs)} tone="after" label="After" />
                {#if it.status === 'changed'}<SvgText text={svgOf(it.theirs)} ghost={svgOf(it.base ?? it.current)} label="Before / After" />{/if}
              {/if}
            </div>
          {:else if it.kind === 'spelling'}
            <table class="cells">
              <thead><tr><th></th><th>before</th><th>{readOnly ? 'yours' : 'draft'}</th>{#if it.conflict && !readOnly}<th>your Builder now</th>{/if}</tr></thead>
              <tbody>
                {#each it.fields as f}
                  <tr class:cf={f.conflict && !readOnly}><th>{FIELD[f.field] ?? f.field}</th><td>{f.base || '—'}</td><td class="new">{f.theirs || '—'}</td>{#if it.conflict && !readOnly}<td>{f.current || '—'}</td>{/if}</tr>
                {/each}
              </tbody>
            </table>
          {:else}
            <div class="more">
              <button class="link" onclick={() => (open = { ...open, [it.id + ':w']: !open[it.id + ':w'] })}>{open[it.id + ':w'] ? 'Hide' : 'Show'} sample words, before and after</button>
              {#if rulesOf(it).length}
                <button class="link" onclick={() => (open = { ...open, [it.id + ':r']: !open[it.id + ':r'] })}>{open[it.id + ':r'] ? 'Hide' : 'Show'} the {rulesOf(it).length} spacing rule{rulesOf(it).length === 1 ? '' : 's'}</button>
              {/if}
              <button class="link" onclick={() => (open = { ...open, [it.id]: !open[it.id] })}>{open[it.id] ? 'Hide' : 'Show'} JSON changes ({diffLines(it).filter((l) => l.op === '+' || l.op === '-').length} lines)</button>
            </div>
            {#if open[it.id + ':r'] && it.kind === 'design'}
              <ul class="rules">
                {#each rulesOf(it) as r (r.key)}
                  <li>
                    <span class="tag {r.status}">{r.status}</span>
                    <span>{r.label}</span>
                    {#if r.status === 'changed' && r.base}<span class="muted">was {gapText(r.base)}</span>{/if}
                    <span class="spacer"></span>
                    {#if mode === 'mine' && lockOf(it)}<button class="sm" aria-disabled="true" data-tip={lockTip(it)}><I.Undo size={14} /> Undo</button>
                    {:else if mode === 'mine'}<button class="sm" onclick={() => undoRule(it, r)}><I.Undo size={14} /> Undo</button>{/if}
                  </li>
                {/each}
              </ul>
            {/if}
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

  {#if mode === 'decide' && items.length}
    <div class="applybar">
      <span>Keeping {keeping.length} of {items.length}</span>
      <span class="muted small">Decisions are saved on the request; nothing goes into the font yet. Kept changes go into the next release candidate.</span>
      <span class="spacer"></span>
      <button class="primary" onclick={() => ondecide?.(Object.fromEntries(items.map((i) => [i.id, picks[i.id] ? 'keep' : 'skip'])))}>Save decisions</button>
    </div>
  {:else if !readOnly && items.length}
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
  .review { display: flex; flex-direction: column; gap: var(--space-5); max-width: 980px; }
  .head { display: flex; align-items: flex-start; gap: var(--space-4); flex-wrap: wrap; }
  h2 { margin: 0; }
  h3 { margin: var(--space-5) 0 0; }
  .head p { margin: 2px 0 0; }
  .spacer { flex: 1; }
  .seg { display: inline-flex; }
  .seg button { border-radius: 0; margin-left: -1px; }
  .seg button:first-child { border-radius: var(--radius-md) 0 0 var(--radius-md); margin-left: 0; }
  .seg button:last-child { border-radius: 0 var(--radius-md) var(--radius-md) 0; }
  button.on { background: var(--sel-bg); color: var(--ink); border-color: var(--link); position: relative; }
  .item { border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-4); background: var(--bg-panel); }
  .item.skip { opacity: .55; }
  .item.conflict { border-color: var(--status-danger); }
  .ihead { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
  .key { font-family: var(--font-mono); font-size: var(--t-label); }
  .sum { font-size: var(--t-small); }
  .tag.added { color: var(--status-saved); border-color: currentColor; }
  .tag.deleted { color: var(--status-danger); border-color: currentColor; }
  .views { display: flex; gap: var(--space-5); flex-wrap: wrap; }
  .cells { border-collapse: collapse; font-size: var(--t-small); }
  .cells th, .cells td { border-bottom: 1px solid var(--hairline); padding: var(--space-2) var(--space-4); text-align: left; }
  .cells thead th { font-weight: 600; border-bottom-color: var(--border-strong); }
  .cells td { font-family: var(--font-mono); }
  .cells .new { color: var(--link); }
  .cells tr.cf td { background: var(--status-danger-bg); }
  .more { display: flex; gap: var(--space-5); flex-wrap: wrap; }
  .link { border: 0; background: none; color: var(--link); padding: 0; height: auto; }
  .words { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-5); }
  .words > div { min-width: 0; }
  .diff { margin: 0; max-height: 320px; overflow: auto; font-family: var(--font-mono); font-size: var(--t-caption); background: var(--bg-sunken); border-radius: var(--radius-sm); padding: var(--space-4); }
  .opadd { color: var(--status-saved); }
  .opdel { color: var(--status-danger); }
  .opgap { color: var(--ink-muted); }
  .btnlink { align-self: center; }
  button[aria-disabled='true'], button[aria-disabled='true']:hover { color: var(--ink-faint); border-color: var(--border); background: transparent; cursor: not-allowed; }
  a.pill { text-decoration: none; }
  .rules { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); font-size: var(--t-small); }
  .rules li { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-2) 0; border-bottom: 1px solid var(--hairline); }
  .banner .spacer { flex: 1; }
  .pickrow { display: flex; gap: var(--space-4); align-items: center; }
  .applybar { position: sticky; bottom: 0; display: flex; gap: var(--space-5); align-items: center; flex-wrap: wrap; padding: var(--space-5); border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--bg-panel); box-shadow: var(--shadow-float); }
  .warn { color: var(--status-draft); }
  .small { font-size: var(--t-small); }
  .empty { color: var(--ink-muted); }
</style>
