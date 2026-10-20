<script lang="ts">
  // One dockable panel: the shared header (drag grip, fold chevron, title,
  // badge, summary when folded, ? help, ⋯ menu) and the body.
  import { panels as layoutPanels, panelHelp, DOCKS, DOCK_LABEL, type AnyPanels } from '$lib/panels.svelte';
  import type { HelpTopic } from '$lib/help';
  import type { Snippet } from 'svelte';
  let { id, title, badge = null, warn = false, summary = '', tag = '', store, help, helpHref, children }: {
    id: string; title: string; badge?: string | number | null; warn?: boolean; summary?: string; tag?: string;
    /** The screen's panel store (Layouts' by default). */
    store?: AnyPanels;
    /** What ? shows (lib/help.ts, the same text as the help page) and where "More in Help" goes. */
    help?: HelpTopic; helpHref?: string;
    children: Snippet;
  } = $props();
  let panels = $derived(store ?? (layoutPanels as unknown as AnyPanels));
  let folded = $derived(panels.isFolded(id));
  let dock = $derived(panels.dockOf(id));
  let menu = $state(false);
  let lifted = $derived(panels.dragging === id);
  let helpBtn = $state<HTMLButtonElement>();
  let helpOpen = $derived(panelHelp.open === id);
  let helpAt = $state({ top: 0, left: 0, width: 300 });
  let titleId = $derived(`pn-title-${id}`), helpId = $derived(`pn-help-${id}`);

  /** The popover is fixed to the viewport (docks scroll and would clip it), right-aligned under ?, kept on screen. */
  function toggleHelp() {
    if (helpOpen) { panelHelp.open = null; return; }
    menu = false;
    const r = helpBtn!.getBoundingClientRect();
    const width = Math.min(300, window.innerWidth - 32);
    const left = Math.max(16, Math.min(r.right - width, window.innerWidth - 16 - width));
    helpAt = { top: r.bottom + 2, left, width };
    panelHelp.open = id;
  }
  function closeHelp(refocus = false) { if (helpOpen) { panelHelp.open = null; if (refocus) helpBtn?.focus(); } }
  $effect(() => { if (lifted) closeHelp(); });   // help works on folded panels too

  function gripDown(e: PointerEvent) {
    e.preventDefault(); e.stopPropagation();
    panels.dragging = id;
    panels.pointer = { x: e.clientX, y: e.clientY };
    panels.over = null;
  }
  function onkey(e: KeyboardEvent) {
    if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); panels.toggle(id); }
  }
</script>

<svelte:window onpointerdown={() => { menu = false; closeHelp(); }} onkeydown={(e) => { if (e.key === 'Escape') closeHelp(true); }} />

<section class="pn" class:folded class:lifted data-panel={id}>
  <div class="ph" class:warn>
    <span class="grip" title="Drag to move this panel" onpointerdown={gripDown}>⠿</span>
    <button class="fold" title={folded ? 'Unfold' : 'Fold'} onclick={() => panels.toggle(id)} onkeydown={onkey}>
      <span class="chev">{folded ? '▸' : '▾'}</span><span class="t" id={titleId}>{title}</span>
    </button>
    {#if badge != null && badge !== ''}<span class="bdg" class:warn>{badge}</span>{/if}
    {#if tag}<span class="tag">{tag}</span>{/if}
    {#if folded && summary}<span class="sum" title={summary}>{summary}</span>{:else}<span class="sp"></span>{/if}
    {#if help}
      <button class="ph-help" bind:this={helpBtn} title="About this panel" aria-label="About {title}" aria-haspopup="dialog" aria-expanded={helpOpen} aria-controls={helpId}
        onpointerdown={(e) => e.stopPropagation()} onclick={(e) => { e.stopPropagation(); toggleHelp(); }}><span class="q">?</span></button>
    {/if}
    <span class="mw">
      <button class="pm" title="Panel menu" onpointerdown={(e) => e.stopPropagation()} onclick={(e) => { e.stopPropagation(); menu = !menu; if (menu) closeHelp(); }}>⋯</button>
      {#if menu}
        <div class="menu" onpointerdown={(e) => e.stopPropagation()}>
          {#if help}<button onclick={() => { menu = false; toggleHelp(); }}>About this panel</button><hr />{/if}
          <button onclick={() => { panels.toggle(id); menu = false; }}>{folded ? 'Unfold' : 'Fold'}</button>
          <hr />
          {#each DOCKS as d (d)}
            <button disabled={d === dock} onclick={() => { panels.move(id, d, panels.a.docks[d].length); menu = false; }}>{d === dock ? '✓ ' : 'Move to '}{DOCK_LABEL[d]}</button>
          {/each}
          <hr />
          <button onclick={() => { panels.nudge(id, -1); menu = false; }}>Move up</button>
          <button onclick={() => { panels.nudge(id, 1); menu = false; }}>Move down</button>
        </div>
      {/if}
    </span>
  </div>
  <!-- outside .ph so it sits above the panels after this one -->
    {#if help && helpOpen}
      <div class="help-pop float" id={helpId} role="dialog" aria-labelledby={titleId} tabindex="-1" style="top: {helpAt.top}px; left: {helpAt.left}px; width: {helpAt.width}px"
        onpointerdown={(e) => e.stopPropagation()}>
        <p>{@html help.html}</p>
        {#if helpHref}<a class="more" href={helpHref} onclick={() => (panelHelp.open = null)}>More in Help →</a>{/if}
      </div>
    {/if}
  {#if !folded && !panels.dragging}
    <div class="pb">{@render children()}</div>
  {/if}
</section>

<style>
  .pn { border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--bg-panel); min-width: 0; }
  .pn.lifted { opacity: .35; border-style: dashed; }
  .ph { display: flex; align-items: center; gap: 4px; height: 36px; padding: 0 var(--space-3) 0 var(--space-4); border-bottom: 1px solid var(--hairline); background: var(--bg-panel); border-radius: var(--radius-lg) var(--radius-lg) 0 0; white-space: nowrap; }
  .folded .ph { border-bottom: 0; border-radius: var(--radius-lg); }
  .grip { color: var(--ink-faint); font-size: 13px; cursor: grab; padding: 0 2px; user-select: none; touch-action: none; }
  .grip:active { cursor: grabbing; }
  .fold { display: inline-flex; align-items: center; gap: var(--space-3); height: 28px; padding: 0 var(--space-1); border: 0; background: transparent; font: 600 var(--t-panel)/20px var(--font-display); min-width: 0; }
  .fold:hover { background: transparent; color: var(--link); }
  .chev { color: var(--ink-muted); font-size: 10px; width: 9px; }
  .t { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bdg { font-size: var(--t-caption); border: 1px solid var(--border); border-radius: var(--radius-pill); padding: 0 7px; line-height: 18px; color: var(--ink-muted); }
  .bdg.warn { border-color: var(--status-draft); border-style: dashed; color: var(--status-draft); background: var(--status-draft-bg); }
  .tag { color: var(--link); border-color: var(--link); }
  .sum { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; color: var(--ink-muted); font-size: var(--t-caption); }
  .sp { flex: 1; }
  .mw { position: relative; }
  .pm { height: 22px; width: 22px; padding: 0; border: 0; background: transparent; color: var(--ink-faint); }
  .ph:hover .pm, .pm:focus { color: var(--ink-muted); }
  /* ? : chrome, not content — faint at rest, ink on hover, link blue while its popover is open */
  .ph-help { display: inline-flex; align-items: center; justify-content: center; flex: none; height: 22px; width: 22px; padding: 0; border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--ink-faint); }
  .ph-help:hover { color: var(--ink); background: var(--bg-hover); }
  .ph-help[aria-expanded="true"] { color: var(--link); background: var(--sel-bg); }
  .ph-help .q { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; border: 1.5px solid currentColor; border-radius: var(--radius-pill); font: 600 var(--t-caption)/1 var(--font-serif); }
  .help-pop { position: fixed; z-index: 60; padding: var(--space-4) var(--space-5); white-space: normal; font: var(--t-label)/20px var(--font-serif); color: var(--ink); }
  .help-pop p { margin: 0; }
  .help-pop .more { display: block; margin-top: var(--space-3); padding-top: var(--space-3); border-top: 1px solid var(--hairline); color: var(--link); }
  .menu { position: absolute; right: 0; top: 100%; z-index: 40; margin-top: 2px; min-width: 190px; display: flex; flex-direction: column; background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: var(--shadow-float); padding: 4px; }
  .menu button { text-align: left; justify-content: flex-start; border: 0; background: transparent; height: 26px; font-size: var(--t-small); font-weight: 400; }
  .menu button:hover:not(:disabled) { background: var(--bg-hover); }
  .menu hr { border: 0; border-top: 1px solid var(--hairline); margin: 3px 0; }
  .pb { padding: var(--space-4) var(--space-5) var(--space-5); display: flex; flex-direction: column; gap: var(--space-4); min-width: 0; }
</style>
