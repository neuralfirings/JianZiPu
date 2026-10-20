<script lang="ts">
  // A dock: the panels it holds in order, drop markers while a panel is
  // dragged, and (bottom strip only) a tab bar collecting the folded panels.
  import * as I from '$lib/icons';
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
          <span class="grip" onpointerdown={(e) => { e.preventDefault(); e.stopPropagation(); panels.dragging = id; panels.pointer = { x: e.clientX, y: e.clientY }; panels.over = null; }}><I.Grip size={14} /></span>
          <span class="chev"><I.Folded size={14} /></span>{m.title}{#if m.badge != null && m.badge !== ''}<span class="bdg" class:warn={m.warn}>{m.badge}</span>{/if}
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
  .dock.left, .dock.right { padding: var(--space-4); overflow: auto; height: 100%; }
  .dock.left > .slot, .dock.right > .slot { min-width: 230px; }
  .dock.bottom { padding: var(--space-4); overflow: auto; height: 100%; }
  .dock.hot { outline: 2px dashed var(--link); outline-offset: -2px; background: var(--sel-bg); }
  .slot { min-width: 0; }
  .ins { height: 0; border-top: 3px solid var(--link); margin: -3px 0 0; position: relative; z-index: 3; }
  .tabbar { display: flex; flex-wrap: wrap; gap: 2px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--bg-panel); padding: 2px; margin-top: auto; }
  .tab { display: inline-flex; align-items: center; gap: 5px; height: var(--control-sm); padding: 0 8px 0 4px; border: 0; background: transparent; font: 600 var(--t-label)/1 var(--font-display); }
  .tab:hover { background: var(--bg-hover); }
  .tab .grip { display: inline-flex; color: var(--ink-faint); cursor: grab; touch-action: none; }
  .tab .chev { display: inline-flex; color: var(--ink-muted); }
  .tab .sum { font-weight: 400; color: var(--ink-muted); font-size: var(--t-caption); }
  .bdg { font-size: var(--t-caption); border: 1px solid var(--border); border-radius: var(--radius-pill); padding: 0 6px; line-height: 15px; color: var(--ink-muted); font-weight: 400; }
  .bdg.warn { border-color: var(--status-draft); color: var(--status-draft); }
  .empty { flex: 1; min-height: 40px; display: flex; align-items: center; justify-content: center; color: var(--link); font-size: var(--t-small); }
</style>
