<script lang="ts">
  // A screen built from dockable panels around a center: left and right columns,
  // a bottom strip under the center, drag a panel's grip to another dock, drag a
  // splitter to resize (shut to hide; a rail brings the dock back). Used by Layouts
  // and the glyph editor, each with its own store (src/lib/panels.svelte.ts). On a phone
  // (store.mode 'phone') it is one column instead: the center pinned on top, every panel a
  // section under it in the phone arrangement's order, nothing to drag or resize.
  import * as I from '$lib/icons';
  import { onMount, type Snippet } from 'svelte';
  import { DOCK_LABEL, DOCK_MIN, type AnyPanels, type Dock, type Meta } from '$lib/panels.svelte';
  import PanelDock from './PanelDock.svelte';
  import Panel from './Panel.svelte';
  import { helpAnchor, type PanelHelp } from '$lib/help';

  let { store, meta, body, children, centerMin = 360, help }: {
    store: AnyPanels;
    /** Each panel's ? text (lib/help.ts), shared with the help page. */
    help?: PanelHelp<any>;
    meta: (id: any) => Meta;
    /** The body of one panel. */
    body: Snippet<[any]>;
    /** The center column (the bottom strip goes under it). */
    children: Snippet;
    centerMin?: number;
  } = $props();

  onMount(() => {
    store.load();
    const onResize = () => store.syncMode();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && store.dragging) { store.dragging = null; store.over = null; } };
    window.addEventListener('resize', onResize);
    window.addEventListener('pointermove', dragMove);
    window.addEventListener('pointerup', dragUp);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('resize', onResize); window.removeEventListener('pointermove', dragMove);
      window.removeEventListener('pointerup', dragUp); window.removeEventListener('keydown', onKey);
    };
  });

  function dragMove(e: PointerEvent) {
    if (!store.dragging) return;
    store.pointer = { x: e.clientX, y: e.clientY };
    const el = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null;
    const dockEl = el?.closest('[data-dock]') as HTMLElement | null;
    if (!dockEl) { store.over = null; return; }
    const dock = dockEl.dataset.dock as Dock;
    const ids = store.a.docks[dock];
    const slots = [...dockEl.querySelectorAll<HTMLElement>('[data-panel-slot]')];
    let index = ids.length;
    for (const sl of slots) {
      const r = sl.getBoundingClientRect();
      const before = dock === 'bottom' && sl.tagName === 'BUTTON' ? e.clientX < r.left + r.width / 2 : e.clientY < r.top + r.height / 2;
      if (before) { index = ids.indexOf(sl.dataset.panelSlot!); break; }
    }
    store.over = { dock, index: Math.max(0, index) };
  }
  function dragUp() {
    if (!store.dragging) return;
    if (store.over) store.move(store.dragging, store.over.dock, store.over.index);
    store.dragging = null; store.over = null;
  }
  function startResize(dock: Dock, e: PointerEvent) {
    e.preventDefault();
    const start = { x: e.clientX, y: e.clientY, size: store.a.size[dock] };
    const move = (ev: PointerEvent) => {
      const d = dock === 'left' ? ev.clientX - start.x : dock === 'right' ? start.x - ev.clientX : start.y - ev.clientY;
      store.setSize(dock, start.size + d, start.size);
    };
    const up = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
  }
  /** Panels that have something to show right now. */
  const shown = (dock: Dock) => store.a.docks[dock].filter((id) => !meta(id).hidden);
  const visible = (dock: Dock) => shown(dock).length > 0 && !store.a.hidden[dock];
  let cols = $derived.by(() => {
    const a = store.a;
    // a dock keeps its saved width while there is room and gives way (down to DOCK_MIN) when the
    // window is narrower, so the three columns always fit the window
    const w = (dock: 'left' | 'right') => `minmax(${Math.min(DOCK_MIN[dock], a.size[dock])}px, ${a.size[dock]}px)`;
    const side = (dock: 'left' | 'right') => (visible(dock) ? (dock === 'left' ? `${w('left')} 6px` : `6px ${w('right')}`) : shown(dock).length || store.dragging ? '24px' : '');
    return `${side('left')} minmax(min(${centerMin}px, 100%), 1fr) ${side('right')}`.trim();
  });
  // on a phone: the column scrolls; a revealed panel (store.open) lands just under the pinned center
  let col = $state<HTMLElement>();
  let centerEl = $state<HTMLElement>();
  $effect(() => {
    const id = store.reveal;
    if (!id) return;
    store.reveal = null;
    if (store.mode !== 'phone' || !col) return;
    requestAnimationFrame(() => {
      const el = col!.querySelector<HTMLElement>(`[data-panel="${id}"]`);
      if (!el) return;
      const top = el.getBoundingClientRect().top - col!.getBoundingClientRect().top + col!.scrollTop - (centerEl?.offsetHeight ?? 0) - 8;
      col!.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    });
  });
  const phoneIds = () => [...store.a.docks.left, ...store.a.docks.right, ...store.a.docks.bottom].filter((id) => !meta(id).hidden);
  const dockNames = (dock: Dock) => shown(dock).map((id) => meta(id).title).join(' · ');
</script>

{#snippet panel(id: string)}
  {@const m = meta(id)}
  <Panel {id} {store} help={help?.topics[id]} helpHref={help ? `/help#${helpAnchor(help.section, id)}` : undefined} title={m.title} badge={m.badge} warn={m.warn} summary={m.summary} tag={m.tag}>{@render body(id)}</Panel>
{/snippet}
{#snippet sideDock(dock: 'left' | 'right')}
  {#if visible(dock)}
    {#if dock === 'right'}<div class="split v" title="Drag to resize; drag shut to hide" onpointerdown={(e) => startResize(dock, e)}></div>{/if}
    <PanelDock {dock} {panel} {meta} {store} />
    {#if dock === 'left'}<div class="split v" title="Drag to resize; drag shut to hide" onpointerdown={(e) => startResize(dock, e)}></div>{/if}
  {:else if shown(dock).length}
    <button class="rail" data-dock={dock} title="Show the {DOCK_LABEL[dock]}" onclick={() => store.show(dock)}><span>{dockNames(dock)}</span></button>
  {:else if store.dragging}
    <div class="rail drop" data-dock={dock}><span>drop: new {DOCK_LABEL[dock]}</span></div>
  {/if}
{/snippet}

{#if store.mode === 'phone'}
<div class="phone" bind:this={col}>
  <section class="center pinned" bind:this={centerEl}>{@render children()}</section>
  <div class="stack">
    {#each phoneIds() as id (id)}<div class="slot" data-panel-slot={id}>{@render panel(id)}</div>{/each}
  </div>
</div>
{:else}
<div class="ws" class:dragging={!!store.dragging} style="grid-template-columns: {cols}">
  {@render sideDock('left')}
  <section class="center">
    {@render children()}
    {#if visible('bottom')}
      <div class="split h" title="Drag to resize; drag shut to hide" onpointerdown={(e) => startResize('bottom', e)}></div>
      <div class="bottom" style="height: {store.a.size.bottom}px"><PanelDock dock="bottom" {panel} {meta} {store} /></div>
    {:else if shown('bottom').length}
      <button class="rail hrail" data-dock="bottom" title="Show the bottom strip" onclick={() => store.show('bottom')}>{dockNames('bottom')}</button>
    {:else if store.dragging}
      <div class="rail hrail drop" data-dock="bottom">drop: new bottom strip</div>
    {/if}
  </section>
  {@render sideDock('right')}
</div>
{/if}
{#if store.dragging}
  <div class="ghost" style="left: {store.pointer.x + 12}px; top: {store.pointer.y - 12}px"><I.Grip size={14} /> {meta(store.dragging).title}</div>
{/if}

<style>
  .ws { display: grid; height: 100%; min-width: 0; min-height: 0; flex: 1; overflow: hidden; }
  .ws.dragging { user-select: none; cursor: grabbing; }
  .center { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .bottom { flex: none; min-height: 0; max-height: 60%; overflow: hidden; border-top: 1px solid var(--border); background: var(--bg-app); }
  .split { background: transparent; touch-action: none; }
  .split.v { cursor: col-resize; border-left: 1px solid var(--border); }
  .split.v:hover { background: var(--sel-bg); }
  .split.h { height: 6px; cursor: row-resize; border-top: 1px solid var(--border); flex: none; }
  .split.h:hover { background: var(--sel-bg); }
  .rail { border: 0; border-radius: 0; background: var(--bg-panel); color: var(--ink-muted); font-size: var(--t-caption); padding: 0; height: auto; width: 24px; display: flex; align-items: flex-start; justify-content: center; border-right: 1px solid var(--border); }
  .rail span { writing-mode: vertical-rl; padding: var(--space-4) 0; white-space: nowrap; }
  .rail:hover { background: var(--sel-bg); color: var(--ink); }
  .rail.drop { border: 2px dashed var(--link); background: var(--sel-bg); color: var(--ink); }
  .rail.hrail { width: auto; height: 24px; flex: none; align-items: center; border-right: 0; border-top: 1px solid var(--border); }
  .ghost { position: fixed; z-index: 60; pointer-events: none; padding: 3px 8px; border: 1px solid var(--link); border-radius: var(--radius-md); background: var(--bg-panel); color: var(--ink); font-family: var(--font-display); font-size: var(--t-small); font-weight: 600; box-shadow: var(--shadow-drag); }
  :global(.ws.dragging [data-dock]) { min-height: 48px; }
  .phone { height: 100%; overflow: auto; overscroll-behavior: contain; }
  .pinned { position: sticky; top: 0; z-index: 2; height: min(52dvh, 460px); background: var(--bg-app); border-bottom: 1px solid var(--border); }
  .stack { display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-4); }
</style>
