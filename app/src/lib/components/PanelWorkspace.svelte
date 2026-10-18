<script lang="ts">
  // A screen built from dockable panels around a center: left and right columns,
  // a bottom strip under the center, drag a panel's grip to another dock, drag a
  // splitter to resize (shut to hide; a rail brings the dock back). Used by Layouts
  // and the glyph editor, each with its own store (src/lib/panels.svelte.ts).
  import { onMount, type Snippet } from 'svelte';
  import { DOCK_LABEL, type AnyPanels, type Dock, type Meta } from '$lib/panels.svelte';
  import PanelDock from './PanelDock.svelte';
  import Panel from './Panel.svelte';

  let { store, meta, body, children, centerMin = 360 }: {
    store: AnyPanels;
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
    const side = (dock: 'left' | 'right') => (visible(dock) ? (dock === 'left' ? `${a.size.left}px 6px` : `6px ${a.size.right}px`) : shown(dock).length || store.dragging ? '24px' : '');
    return `${side('left')} minmax(${centerMin}px, 1fr) ${side('right')}`.trim();
  });
  const dockNames = (dock: Dock) => shown(dock).map((id) => meta(id).title).join(' · ');
</script>

{#snippet panel(id: string)}
  {@const m = meta(id)}
  <Panel {id} {store} title={m.title} badge={m.badge} warn={m.warn} summary={m.summary} tag={m.tag}>{@render body(id)}</Panel>
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
{#if store.dragging}
  <div class="ghost" style="left: {store.pointer.x + 12}px; top: {store.pointer.y - 12}px">⠿ {meta(store.dragging).title}</div>
{/if}

<style>
  .ws { display: grid; height: 100%; min-width: 0; min-height: 0; flex: 1; }
  .ws.dragging { user-select: none; cursor: grabbing; }
  .center { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .bottom { flex: none; min-height: 0; overflow: hidden; border-top: 1px solid var(--line); background: var(--bg); }
  .split { background: transparent; touch-action: none; }
  .split.v { cursor: col-resize; border-left: 1px solid var(--line); }
  .split.v:hover { background: var(--accent-bg); }
  .split.h { height: 6px; cursor: row-resize; border-top: 1px solid var(--line); flex: none; }
  .split.h:hover { background: var(--accent-bg); }
  .rail { border: 0; border-radius: 0; background: var(--bg-2); color: var(--fg-2); font-size: var(--t-xs); padding: 0; height: auto; width: 24px; display: flex; align-items: flex-start; justify-content: center; border-right: 1px solid var(--line); }
  .rail span { writing-mode: vertical-rl; padding: var(--s-2) 0; white-space: nowrap; }
  .rail:hover { background: var(--accent-bg); color: var(--accent); }
  .rail.drop { border: 2px dashed var(--accent); background: var(--accent-bg); color: var(--accent); }
  .rail.hrail { width: auto; height: 24px; flex: none; align-items: center; border-right: 0; border-top: 1px solid var(--line); }
  .ghost { position: fixed; z-index: 60; pointer-events: none; padding: 3px 8px; border: 1px solid var(--accent); border-radius: var(--radius); background: var(--bg); color: var(--accent); font-size: var(--t-sm); font-weight: 600; box-shadow: 0 6px 18px rgba(0,0,0,.2); }
  :global(.ws.dragging [data-dock]) { min-height: 48px; }
</style>
