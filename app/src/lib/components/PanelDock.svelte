<script lang="ts">
  // A dock: the panels it holds in order, drop markers while a panel is
  // dragged, and (bottom strip only) a tab bar collecting the folded panels.
  import { panels as layoutPanels, type Dock, type AnyPanels, type Meta } from '$lib/panels.svelte';
  import type { Snippet } from 'svelte';
  let { dock, panel, meta, store }: { dock: Dock; panel: Snippet<[any]>; meta: (id: any) => Meta; store?: AnyPanels } = $props();
  let panels = $derived(store ?? (layoutPanels as unknown as AnyPanels));
  // a panel whose meta says `hidden` (nothing to show right now) takes no room
  let all = $derived(panels.a.docks[dock]);
  let ids = $derived(all.filter((id) => !meta(id).hidden));
  let dragging = $derived(!!panels.dragging);
  let over = $derived(panels.over?.dock === dock ? panels.over.index : -1);
  let open = $derived(dock === 'bottom' ? ids.filter((id) => !panels.isFolded(id)) : ids);
  let tabs = $derived(dock === 'bottom' ? ids.filter((id) => panels.isFolded(id)) : []);
</script>

<div class="dock {dock}" class:hot={dragging} data-dock={dock}>
  {#each open as id, i (id)}
    {#if dragging && over === all.indexOf(id)}<div class="ins"></div>{/if}
    <div class="slot" data-panel-slot={id}>{@render panel(id)}</div>
  {/each}
  {#if dragging && over >= 0 && (over >= all.length || !open.includes(all[over]))}<div class="ins"></div>{/if}
  {#if dock === 'bottom' && tabs.length}
    <div class="tabbar">
      {#each tabs as id (id)}
        {@const m = meta(id)}
        <button class="tab" data-panel-slot={id} data-panel={id} title="Open {m.title}" onclick={() => panels.setFolded(id, false)}>
          <span class="grip" onpointerdown={(e) => { e.preventDefault(); e.stopPropagation(); panels.dragging = id; panels.pointer = { x: e.clientX, y: e.clientY }; panels.over = null; }}>⠿</span>
          <span class="chev">▸</span>{m.title}{#if m.badge != null && m.badge !== ''}<span class="bdg" class:warn={m.warn}>{m.badge}</span>{/if}
          {#if m.summary}<span class="sum">{m.summary}</span>{/if}
        </button>
      {/each}
    </div>
  {/if}
  {#if ids.length === 0}
    <div class="empty">{dragging ? 'drop here' : ''}</div>
  {/if}
</div>

<style>
  .dock { display: flex; flex-direction: column; gap: 6px; min-width: 0; min-height: 0; position: relative; }
  .dock.left, .dock.right { padding: var(--s-2); overflow: auto; height: 100%; }
  .dock.left > .slot, .dock.right > .slot { min-width: 230px; }
  .dock.bottom { padding: var(--s-2); overflow: auto; height: 100%; }
  .dock.hot { outline: 2px dashed var(--accent); outline-offset: -2px; background: var(--accent-bg); }
  .slot { min-width: 0; }
  .ins { height: 0; border-top: 3px solid var(--accent); margin: -3px 0 0; position: relative; z-index: 3; }
  .tabbar { display: flex; flex-wrap: wrap; gap: 2px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--bg-2); padding: 2px; margin-top: auto; }
  .tab { display: inline-flex; align-items: center; gap: 5px; height: 24px; padding: 0 8px 0 4px; border: 0; background: transparent; font-size: var(--t-sm); font-weight: 600; }
  .tab:hover { background: var(--bg-3); }
  .tab .grip { color: var(--fg-2); cursor: grab; font-size: 12px; touch-action: none; }
  .tab .chev { color: var(--fg-2); font-size: 10px; }
  .tab .sum { font-weight: 400; color: var(--fg-2); font-size: var(--t-xs); }
  .bdg { font-size: var(--t-xs); border: 1px solid var(--line); border-radius: 9px; padding: 0 6px; line-height: 15px; color: var(--fg-2); font-weight: 400; }
  .bdg.warn { border-color: var(--warn); color: var(--warn); }
  .empty { flex: 1; min-height: 40px; display: flex; align-items: center; justify-content: center; color: var(--accent); font-size: var(--t-sm); }
</style>
