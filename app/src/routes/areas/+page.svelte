<script lang="ts">
  import { app } from '$lib/state.svelte';
  import * as TY from '$lib/typing';
  import Glyph from '$lib/components/Glyph.svelte';
  import AddGlyphsDialog from '$lib/components/AddGlyphsDialog.svelte';
  import { page } from '$app/state';

  const d = $derived(app.design!);
  let areaNames = $derived(Object.keys(d.areas));
  let current = $state<string>(page.url.searchParams.get('area') || '');
  $effect(() => { if (!current || !d.areas[current]) current = areaNames[0]; });
  let area = $derived(d.areas[current]);
  let member = $state<string | null>(page.url.searchParams.get('g'));
  let advanced = $state(false);
  let picker = $state(false);

  let usedIn = $derived(d.layouts.filter((l) => l.slots.some((s) => s.alternatives.some((alt) => alt.some((t) => (t.includes(':') ? t.split(':')[1] : t) === current)))));
  const label = (g: string) => TY.firstSpelling(app.typing, g)?.text || g.replace(/^(md|lg|xl|mod)_/, '');
  const typedAs = (g: string) => TY.TYPED.map((f) => TY.shown(app.typing, g, f).value).filter(Boolean);

  function remove(g: string) { app.removeFromArea(current, g); }
  function setSize(i: 0 | 1, v: number) {
    if (!isFinite(v) || v <= 0) return;
    app.edit(`Area ${current}: box ${i === 0 ? 'width' : 'height'} ${area.size[i]} → ${v}`, (x) => { x.areas[current].size[i] = v; });
  }
  function setLabel(v: string) { app.edit(`Area ${current}: label "${v}"`, (x) => { x.areas[current].label = v; }); }
  function setAdvance(v: number) { app.edit(`Area ${current}: advance ${v}`, (x) => { if (v) x.areas[current].advance = v; else delete x.areas[current].advance; }); }

  let newName = $state('');
  function newArea() {
    const n = newName.trim();
    if (!n || d.areas[n]) return;
    app.edit(`New area ${n}`, (x) => { x.areas[n] = { label: n, size: [350, 350], glyphs: [] }; });
    current = n; newName = '';
  }
  function deleteArea() {
    if (usedIn.length) { alert(`"${current}" is used by ${usedIn.map((l) => l.label ?? l.name).join(', ')}. Remove it from those word types first.`); return; }
    if (!confirm(`Delete area "${current}"?`)) return;
    const n = current;
    app.edit(`Delete area ${n}`, (x) => { delete x.areas[n]; });
    current = areaNames[0]; app.syncCatalog();
  }
</script>

<div class="page">
  <aside class="list">
    {#each areaNames as n}
      <button class:on={current === n} onclick={() => { current = n; member = null; }}>
        <span class="id">{n}</span><span>{d.areas[n].label || n}</span><span class="muted">{d.areas[n].glyphs.length}</span>
      </button>
    {/each}
    <hr />
    <label class="adv"><input type="checkbox" bind:checked={advanced} /> Advanced</label>
    {#if advanced}
      <div class="row"><input type="text" placeholder="new area id" bind:value={newName} style="width: 110px" /><button onclick={newArea}>+ New</button></div>
      <p class="muted" style="font-size: var(--t-xs)">A new area needs glyphs and a place in a word type's structure before it does anything.</p>
    {/if}
  </aside>
  {#if area}
    <section class="detail">
      <div class="head">
        <h2>{area.label || current} <span class="id">{current}</span></h2>
        <div class="row wrap">
          <label>Shown as <input type="text" value={area.label ?? ''} onchange={(e) => setLabel((e.target as HTMLInputElement).value)} /></label>
          <label>Box <input type="number" value={area.size[0]} onchange={(e) => setSize(0, +(e.target as HTMLInputElement).value)} /> ×
            <input type="number" value={area.size[1]} onchange={(e) => setSize(1, +(e.target as HTMLInputElement).value)} /></label>
          {#if advanced}
            <label title="A part with an advance moves the pen (the colon and the bar). 0 for ordinary parts."
              >Advance <input type="number" value={area.advance ?? 0} onchange={(e) => setAdvance(+(e.target as HTMLInputElement).value)} /></label>
            <button onclick={deleteArea}>Delete area</button>
          {/if}
        </div>
        <div class="muted">Used in: {#if usedIn.length}{#each usedIn as l, i}{i ? ' · ' : ''}<a href="/layouts?layout={l.name}">{l.label ?? l.name}</a>{/each}{:else}no word type yet{/if}
          · box size changes move every word that uses this part.</div>
      </div>

      <div class="members-head"><strong>Members ({area.glyphs.length})</strong>
        <button class="primary" onclick={() => (picker = true)}>+ Add glyphs</button></div>
      {#if area.glyphs.length === 0}<p class="muted">No glyphs yet. Add glyphs so words can use this part.</p>{/if}
      <div class="members">
        {#each area.glyphs as g (g)}
          <div class="mem" class:on={member === g}>
            <button class="art" onclick={() => (member = g)} title={g}><Glyph name={g} size={56} /></button>
            <div class="row" style="justify-content: space-between">
              <span class="id">{label(g)}</span>
              <button class="x" title="Remove from area" onclick={() => remove(g)}>×</button>
            </div>
          </div>
        {/each}
      </div>

      {#if member && area.glyphs.includes(member)}
        <div class="keys panel row wrap">
          <span class="art-sm"><Glyph name={member} size={40} /></span>
          <strong class="mono">{member}</strong>
          <span>Typed as {#if typedAs(member).length}{typedAs(member).join(' · ')}{:else if TY.isDecimal(member)}{TY.decimalPatterns(member).join(' · ')} <span class="muted">(by pattern)</span>{:else}<span class="muted">nothing yet</span>{/if}
            {#if app.typing[member]?.pinyin}<span class="muted">({app.typing[member].pinyin})</span>{/if}</span>
          <a href="/glyphs?g={encodeURIComponent(member)}&view=typing">Edit in Glyphs →</a>
        </div>
      {/if}
    </section>
  {/if}

  {#if picker}<AddGlyphsDialog area={current} onclose={() => (picker = false)} />{/if}
</div>

<style>
  .page { display: flex; height: 100%; }
  .list { width: 240px; border-right: 1px solid var(--line); padding: var(--s-2); display: flex; flex-direction: column; gap: 2px; overflow: auto; }
  .list > button { display: grid; grid-template-columns: 56px 1fr auto; gap: var(--s-2); border: 0; background: transparent; text-align: left; }
  .list > button.on { background: var(--accent-bg); color: var(--accent); }
  .list hr { border: 0; border-top: 1px solid var(--line); margin: var(--s-2) 0; }
  .adv { font-size: var(--t-sm); color: var(--fg-2); }
  .detail { flex: 1; overflow: auto; padding: var(--s-4); display: flex; flex-direction: column; gap: var(--s-3); }
  h2 { margin: 0 0 var(--s-2); font-size: var(--t-xl); }
  .wrap { flex-wrap: wrap; gap: var(--s-3); }
  .members-head { display: flex; justify-content: space-between; align-items: center; }
  .members { display: grid; grid-template-columns: repeat(auto-fill, 76px); gap: var(--s-2); }
  .mem { width: 76px; border: 1px solid var(--line); border-radius: var(--radius); padding: 4px; background: var(--bg); }
  .mem.on { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
  .art { height: auto; width: 100%; padding: 2px; display: flex; justify-content: center; border: 0; background: transparent; }
  .x { height: 18px; padding: 0 4px; border: 0; background: transparent; color: var(--fg-2); }
</style>
