<script lang="ts">
  import { app } from '$lib/state.svelte';
  import Glyph from '$lib/components/Glyph.svelte';
  import NewGlyphDialog from '$lib/components/NewGlyphDialog.svelte';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import { DEFAULT_WEIGHT } from '$lib/glyphed/editor.svelte';
  let newDialog = $state(false);
  const editUrl = (g: string, from?: string) => `/glyphs/${encodeURIComponent(g)}/edit${from ? `?from=${from}` : ''}`;
  function setWeight(v: number) { if (v > 0) app.edit(`Reference stroke weight ${Math.round(v)}`, (d) => { d.glyph_weight = Math.round(v); }); }

  let q = $state('');
  let group = $state('all');
  let unassignedOnly = $state(false);
  let selected = $state<string | null>(page.url.searchParams.get('g'));

  const GROUPS: [string, string, (g: string) => boolean][] = [
    ['all', 'All', () => true],
    ['lg', 'Right-hand strokes (lg_)', (g) => g.startsWith('lg_')],
    ['md', 'Fingers, numbers (md_)', (g) => g.startsWith('md_') && !/^md_\d+[.,]\d/.test(g)],
    ['deci', 'Position decimals (md_N.M)', (g) => /^md_\d+[.,]\d/.test(g)],
    ['xl', 'Chords (xl_)', (g) => g.startsWith('xl_')],
    ['mod', 'Modifiers (mod_)', (g) => g.startsWith('mod_')],
    ['other', 'Other', (g) => !/^(lg|md|xl|mod)_/.test(g)]
  ];
  let rows = $derived(app.glyphs);
  let counts = $derived(Object.fromEntries(GROUPS.map(([k, , f]) => [k, rows.filter((r) => f(r.glyph)).length])));
  let unassigned = $derived(rows.filter((r) => r.areas.length === 0));
  let shown = $derived.by(() => {
    const f = GROUPS.find((g) => g[0] === group)![2];
    const needle = q.trim().toLowerCase();
    return rows.filter((r) => f(r.glyph) && (!unassignedOnly || r.areas.length === 0) &&
      (!needle || [r.glyph, r.keys, r.common, r.latin, r.latin_alt, r.simplified, r.traditional, r.pinyin].join(' ').toLowerCase().includes(needle)));
  });
  let sel = $derived(rows.find((r) => r.glyph === selected) ?? null);
  let areaOptions = $derived(Object.keys(app.design!.areas));

  function keysOf(r: typeof rows[number]) {
    return [r.keys, r.simplified, r.traditional].filter(Boolean).join(' · ');
  }
  function addToArea(g: string, area: string) { if (area) app.addToArea(area, [g]); }
  function removeFromArea(g: string, area: string) { app.removeFromArea(area, g); }
  let svgInfo = $derived.by(() => {
    if (!sel) return null;
    const t = app.svgs[sel.glyph];
    if (!t) return null;
    return { paths: (t.match(/<path/g) ?? []).length, kb: (new Blob([t]).size / 1024).toFixed(1) };
  });
</script>

<div class="page">
  <div class="toolbar">
    <input type="text" placeholder="Search  gou · k · 勾 · pinyin" bind:value={q} style="width: 260px" />
    <label><input type="checkbox" bind:checked={unassignedOnly} /> Unassigned only</label>
    <span class="spacer"></span>
    <label class="weight" title="The stroke thickness every glyph should sit around, in units (= font units). The editor's compare dot and new lines use it. Match the body of main strokes, not the tapers.">
      Reference weight <input type="number" min="1" max="200" value={app.design?.glyph_weight ?? DEFAULT_WEIGHT} onchange={(e) => setWeight(+(e.target as HTMLInputElement).value)} /> <span class="muted">units</span>
    </label>
    <button class="primary" onclick={() => (newDialog = true)}>+ New glyph</button>
  </div>
  <div class="body">
    <aside class="groups">
      {#each GROUPS as [k, label]}
        {#if counts[k] > 0 || k === 'all'}
          <button class:on={group === k} onclick={() => (group = k)}><span>{label}</span><span class="muted">{counts[k]}</span></button>
        {/if}
      {/each}
      <hr />
      <button class:on={unassignedOnly} onclick={() => { unassignedOnly = !unassignedOnly; group = 'all'; }}><span>Unassigned</span><span class="muted">{unassigned.length}</span></button>
    </aside>
    <section class="grid-wrap">
      {#if shown.length === 0}
        <p class="muted">No glyph matches “{q}”. Try the pinyin (gou) or the key (k).</p>
      {/if}
      <div class="grid">
        {#each shown as r (r.glyph)}
          <div class="tile" class:on={selected === r.glyph} class:unassigned={r.areas.length === 0} role="button" tabindex="0"
            onclick={() => (selected = r.glyph)} ondblclick={() => goto(editUrl(r.glyph))}
            onkeydown={(e) => { if (e.key === 'Enter') goto(editUrl(r.glyph)); }}>
            <div class="art"><Glyph name={r.glyph} size={72} /></div>
            <div class="name">{r.glyph}</div>
            <div class="sub muted">{r.areas.length ? `${keysOf(r) || '—'} · ${r.areas.join(', ')}` : 'no area yet'}</div>
            <a class="edit" href={editUrl(r.glyph)} title="Edit the outline" onclick={(e) => e.stopPropagation()}>Edit</a>
          </div>
        {/each}
      </div>
    </section>
  </div>
  {#if newDialog}<NewGlyphDialog onclose={() => (newDialog = false)} initialArea={sel?.areas[0] ?? ''} />{/if}
  {#if sel}
    <section class="inspector">
      <div class="big"><Glyph name={sel.glyph} size={120} /></div>
      <div class="facts">
        <div class="h"><strong>{sel.glyph}</strong>{#if !sel.svg}<span class="badge-warn"> · no SVG on disk</span>{/if}</div>
        <div><span class="k">Typed as</span> {keysOf(sel) || '—'} {#if sel.pinyin}<span class="muted">({sel.pinyin})</span>{/if}</div>
        <div class="row"><span class="k">In areas</span>
          {#each sel.areas as a}<span class="chip">{app.areaLabel(a)} <span class="id">{a}</span> <button class="x" title="Remove from {a}" onclick={() => removeFromArea(sel!.glyph, a)}>×</button></span>{/each}
          <select onchange={(e) => { addToArea(sel!.glyph, (e.target as HTMLSelectElement).value); (e.target as HTMLSelectElement).value = ''; }}>
            <option value="">+ Add to area…</option>
            {#each areaOptions.filter((a) => !sel!.areas.includes(a)) as a}<option value={a}>{app.areaLabel(a)} ({a})</option>{/each}
          </select>
        </div>
        <div><span class="k">Box</span> {#if sel.areas[0]}{app.design!.areas[sel.areas[0]].size.join(' × ')} <span class="muted">(from area "{sel.areas[0]}")</span>{:else}<span class="muted">set by the area it joins</span>{/if}</div>
        <div><span class="k">File</span> {#if sel.svg}inputs/svg/{sel.glyph}.svg{#if svgInfo} · {svgInfo.paths} paths · {svgInfo.kb} KB{/if}{:else}<span class="muted">none</span>{/if}</div>
        <div class="row" style="margin-top: var(--s-2)">
          <a href={editUrl(sel.glyph)}><button class="primary">Edit outline</button></a>
          <a href={editUrl(sel.glyph, 'file')}><button title="Open the editor with a new SVG loaded (nothing is written until you save)">Replace from file…</button></a>
          <a href={editUrl(sel.glyph, 'image')}><button title="Open the editor in trace mode">Trace from image…</button></a>
          {#if sel.svg}<a href="/inputs/svg/{sel.glyph}.svg" download><button>Download SVG</button></a>{/if}
          <a href="/areas?area={sel.areas[0] ?? ''}&g={sel.glyph}"><button>Typing keys →</button></a>
        </div>
      </div>
    </section>
  {/if}
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; }
  .toolbar { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); border-bottom: 1px solid var(--line); }
  .spacer { flex: 1; }
  .body { display: flex; flex: 1; min-height: 0; }
  .groups { width: 220px; border-right: 1px solid var(--line); padding: var(--s-2); display: flex; flex-direction: column; gap: 2px; }
  .groups button { display: flex; justify-content: space-between; border: 0; background: transparent; text-align: left; }
  .groups button.on { background: var(--accent-bg); color: var(--accent); }
  .groups hr { border: 0; border-top: 1px solid var(--line); margin: var(--s-2) 0; }
  .grid-wrap { flex: 1; overflow: auto; padding: var(--s-3); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, 120px); gap: var(--s-2); }
  .tile { position: relative; height: auto; width: 120px; padding: var(--s-2) var(--s-2) 26px; display: flex; flex-direction: column; align-items: center; gap: 2px; background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius); cursor: pointer; }
  .tile:hover { background: var(--bg-3); }
  .tile.on { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
  .tile .edit { position: absolute; left: 50%; bottom: 4px; transform: translateX(-50%); display: none; height: 18px; line-height: 18px; padding: 0 10px; border-radius: 9px; background: var(--accent-bg); color: var(--accent); font-size: var(--t-xs); text-decoration: none; }
  .tile:hover .edit, .tile:focus-within .edit, .tile.on .edit { display: block; }
  .weight { display: flex; align-items: center; gap: var(--s-1); font-size: var(--t-sm); }
  .weight input { width: 60px; }
  .tile.unassigned .art { outline: 1px dashed var(--line); outline-offset: 2px; border-radius: 4px; }
  .name { font-family: var(--mono); font-size: var(--t-xs); }
  .sub { font-size: var(--t-xs); max-width: 104px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .inspector { display: flex; gap: var(--s-4); padding: var(--s-3) var(--s-4); border-top: 1px solid var(--line); background: var(--bg-2); }
  .big { padding: var(--s-2); background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius); }
  .facts { display: flex; flex-direction: column; gap: var(--s-1); }
  .k { display: inline-block; width: 80px; color: var(--fg-2); }
  .x { height: 16px; padding: 0 4px; border: 0; background: transparent; }
</style>
