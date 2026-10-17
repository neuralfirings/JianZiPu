<script lang="ts">
  import { app } from '$lib/state.svelte';
  import { editor } from '$lib/editor.svelte';
  import { elementNames } from '$lib/shape';
  import type { Layout } from '$lib/api';
  let layout = $derived(editor.layout!);
  let lname = $derived(layout.label ?? layout.name);
  let names = $derived([...new Set([...layout.slots.map((s) => s.name), ...elementNames(layout).map((e) => e.name)])]);
  function edit(label: string, fn: (l: Layout) => void) {
    app.edit(`${lname}: ${label}`, (d) => fn(d.layouts.find((x) => x.name === layout.name)!));
  }
  function toggle(key: 'y' | 'x' | 'y_phantom' | 'x_phantom', n: string) {
    edit(`centering ${key} ${n}`, (l) => {
      const cur = (l.center[key] as string[] | null | undefined) ?? [];
      const next = cur.includes(n) ? cur.filter((x) => x !== n) : [...cur, n];
      if (key === 'y' || key === 'x') l.center[key] = next.length ? next : null;
      else if (next.length) l.center[key] = next; else delete l.center[key];
    });
  }
  function setTarget(key: 'y_target' | 'x_target', v: string) {
    edit(`${key} ${v || 'default'}`, (l) => { if (v === '') delete l.center[key]; else l.center[key] = +v; });
  }
  let open = $state(false);
</script>

<div class="cp">
  <div class="row" style="justify-content: flex-end"><button class="tiny" onclick={() => (open = !open)}>{open ? 'done' : 'edit'}</button></div>
  <div class="muted small">
    {#if layout.center.y?.length}Vertically centred on {layout.center.y.join(', ')}{#if layout.center.y_phantom?.length} (counting {layout.center.y_phantom.join(', ')} even when absent){/if} at y {layout.center.y_target ?? app.design!.center.y}.{:else}Not centred vertically (absolute heights).{/if}
    {#if layout.center.x?.length} Horizontally centred on {layout.center.x.join(', ')} at x {layout.center.x_target ?? app.design!.center.x}.{:else} Not centred horizontally.{/if}
  </div>
  {#if open}
    {#each [['y', 'Vertical: span these parts'], ['y_phantom', 'Vertical: count even when absent'], ['x', 'Horizontal: span these parts'], ['x_phantom', 'Horizontal: count even when absent']] as [key, title]}
      <div class="grp"><div class="muted">{title}</div>
        {#each names as n}<label class="inl"><input type="checkbox" checked={(layout.center[key as 'y'] as string[] | null | undefined)?.includes(n)} onchange={() => toggle(key as 'y', n)} />{n}</label>{/each}
      </div>
    {/each}
    <div class="row">
      <label>y target <input type="number" value={layout.center.y_target ?? ''} placeholder={String(app.design!.center.y)} onchange={(e) => setTarget('y_target', (e.target as HTMLInputElement).value)} /></label>
      <label>x target <input type="number" value={layout.center.x_target ?? ''} placeholder={String(app.design!.center.x)} onchange={(e) => setTarget('x_target', (e.target as HTMLInputElement).value)} /></label>
    </div>
  {/if}
</div>

<style>
  .cp { display: flex; flex-direction: column; gap: 4px; }
  .small { font-size: var(--t-sm); }
  .grp { margin-top: 6px; }
  .inl { margin-right: 8px; white-space: nowrap; } .inl input { margin: 0 2px 0 0; }
  .tiny { height: 20px; padding: 0 6px; font-size: var(--t-xs); }
</style>
