<script lang="ts">
  // Area Properties (Layouts, docs/AREAS-PLACEMENT-UX.md): the area of the selected part, or
  // the one picked in the switcher. Its name, box (typed sizes preview on the canvas and only
  // apply on Enter / leaving the fields), advance and delete (Advanced), the word types that
  // use it, and its glyphs: click = preview, double-click or "edit" = glyph editor, Manage =
  // remove / add. Position decimals sit in a text grid (13 hui × blank, .1–.9).
  import { goto } from '$app/navigation';
  import { api, type ResolvedElement } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { editor } from '$lib/editor.svelte';
  import { panels } from '$lib/panels.svelte';
  import { defaultChoice, shapeElements } from '$lib/shape';
  import { addArea, areaIdProblem, decimalGrid, splitMembers, usedIn } from '$lib/areas';
  import { searchText, decimalPatterns } from '$lib/typing';
  import Glyph from './Glyph.svelte';
  import WordCanvas from './WordCanvas.svelte';
  import AddGlyphsDialog from './AddGlyphsDialog.svelte';

  let d = $derived(app.design!);
  let areaId = $derived(editor.shownArea);
  let area = $derived(areaId ? d.areas[areaId] ?? null : null);
  let el = $derived(areaId && editor.selected ? editor.elements.find((e) => e.name === editor.selected && e.area === areaId) ?? null : null);
  let uses = $derived(areaId ? usedIn(d, areaId) : []);
  let members = $derived(splitMembers(area?.glyphs ?? []));
  let manage = $state(false);
  let q = $state('');
  let showAll = $state(false);
  let adding = $state(false);
  let switcher = $state(false);
  let more = $state(false);
  const LIMIT = 28;
  let wide = $derived(panels.dockOf('glyphs') === 'bottom');

  const matches = (g: string) => !q || searchText(app.typing, g).includes(q.toLowerCase());
  let chips = $derived(members.chips.filter(matches));
  let shown = $derived(showAll || chips.length <= LIMIT ? chips : chips.slice(0, LIMIT));
  let grid = $derived(decimalGrid(members.decimals, (g) => !!app.svgs[g]));
  const editUrl = (g: string) => `/glyphs/${encodeURIComponent(g)}/edit?back=${encodeURIComponent('/layouts')}`;
  const previewed = (g: string) => !!el && editor.pinned[el.name] === g;

  function preview(g: string) { if (el) editor.pin(el.name, g); }
  function remove(g: string) { if (areaId && app.removeFromArea(areaId, g)) editor.ensurePins(); }

  // ---- name, advance
  function setLabel(v: string) { const a = areaId!; app.edit(`Area ${a}: shown as "${v}"`, (x) => { x.areas[a].label = v; }); }
  function setAdvance(v: number) { const a = areaId!; app.edit(`Area ${a}: advance ${v}`, (x) => { if (v) x.areas[a].advance = v; else delete x.areas[a].advance; }); }

  // ---- box: typed sizes are previewed (editor.boxEdit + dragDesign), applied on Enter / leaving
  let pending = $derived(editor.boxEdit && editor.boxEdit.area === areaId ? editor.boxEdit : null);
  let boxShown = $derived(pending ? pending.size : area?.size ?? [0, 0]);
  let changed = $derived(!!pending && !!area && (pending.size[0] !== area.size[0] || pending.size[1] !== area.size[1]));
  function beginBox() {
    if (!areaId || !area || pending) return;
    const before = (editor.resolved?.elements ?? []).filter((e): e is ResolvedElement & { x: number; y: number } => e.x != null && e.y != null).map((e) => ({ x: e.x, y: e.y, size: e.size as [number, number] }));
    editor.boxEdit = { area: areaId, size: [area.size[0], area.size[1]], before };
  }
  function setPending(i: 0 | 1, v: number) {
    if (!pending || !isFinite(v) || v <= 0) return;
    const size: [number, number] = i === 0 ? [Math.round(v), pending.size[1]] : [pending.size[0], Math.round(v)];
    editor.boxEdit = { ...pending, size };
    const next = JSON.parse(JSON.stringify(app.design));
    next.areas[pending.area].size = size;
    editor.dragDesign = size[0] !== area!.size[0] || size[1] !== area!.size[1] ? next : null;
  }
  function applyBox() {
    const p = editor.boxEdit; if (!p) return;
    editor.boxEdit = null; editor.dragDesign = null;
    const a = p.area, old = d.areas[a]?.size;
    if (!old || (old[0] === p.size[0] && old[1] === p.size[1])) return;
    app.edit(`Area ${a}: box ${old[0]} × ${old[1]} → ${p.size[0]} × ${p.size[1]}`, (x) => { x.areas[a].size = [p.size[0], p.size[1]]; });
  }
  function cancelBox() { editor.boxEdit = null; editor.dragDesign = null; }
  function boxKey(i: 0 | 1, e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); applyBox(); (e.target as HTMLInputElement).blur(); }
    else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cancelBox(); (e.target as HTMLInputElement).blur(); }
    else if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      e.preventDefault(); beginBox();
      setPending(i, (pending ?? editor.boxEdit)!.size[i] + (e.key === 'ArrowUp' ? 1 : -1) * (e.shiftKey ? 10 : 1));
    }
  }
  // leaving both box fields applies; moving between W and H keeps the edit open
  function boxBlur(e: FocusEvent) {
    const to = e.relatedTarget as HTMLElement | null;
    if (to?.closest('[data-box-fields]')) return;
    if (editor.boxEdit) applyBox();
  }

  // ---- while a box edit is pending: the other word types that use the area, before and after
  type Mini = { name: string; title: string; now: { name: string; area: string; glyph: string | null; x: number | null; y: number | null; size: [number, number] }[]; before: { x: number; y: number; size: [number, number] }[] };
  let minis = $state<Mini[]>([]);
  let miniSeq = 0;
  $effect(() => {
    const p = pending, dd = editor.dragDesign, base = app.design, others = uses.filter((l) => l.name !== editor.layoutName);
    if (!p || !dd || !base || !changed) { minis = []; return; }
    const id = ++miniSeq;
    const t = setTimeout(async () => {
      const out: Mini[] = [];
      for (const l of others) {
        const choice = defaultChoice(l);
        const els = shapeElements(l, choice);
        const [a, b] = await Promise.all([api.resolve(base, l.name, choice, {}), api.resolve(dd, l.name, choice, {})]).catch(() => [null, null]);
        if (!a || !b || id !== miniSeq) continue;
        out.push({
          name: l.name, title: l.label ?? l.name,
          now: els.map((e) => { const r = b.elements.find((x) => x.name === e.name); return { name: e.name, area: e.area, glyph: dd.areas[e.area]?.glyphs[0] ?? null, x: r?.x ?? null, y: r?.y ?? null, size: (r?.size ?? dd.areas[e.area].size) as [number, number] }; }),
          before: a.elements.filter((x) => x.x != null && x.y != null).map((x) => ({ x: x.x!, y: x.y!, size: x.size as [number, number] }))
        });
      }
      if (id === miniSeq) minis = out;
    }, 150);
    return () => clearTimeout(t);
  });

  // ---- switcher and new area
  let newId = $state(''), newLabel = $state(''), newOpen = $state(false);
  let newProblem = $derived(areaIdProblem(d, newId.trim()));
  function pick(a: string) { switcher = false; editor.showArea(a); }
  function createArea() {
    const id = newId.trim();
    if (areaIdProblem(d, id)) return;
    const size: [number, number] = area ? [area.size[0], area.size[1]] : [350, 350];
    app.edit(`New area ${id}`, (x) => addArea(x, id, newLabel, size));
    newId = ''; newLabel = ''; newOpen = false; switcher = false;
    editor.areaView = id;
  }
  function deleteArea() {
    const a = areaId; if (!a || uses.length) return;
    if (!confirm(`Delete the area "${app.areaLabel(a)}" (${a})? Its ${area?.glyphs.length ?? 0} glyphs stay on disk.`)) return;
    more = false;
    app.edit(`Delete area ${a}`, (x) => { delete x.areas[a]; });
    editor.areaView = null; app.syncCatalog();
  }
  let groups = $derived.by(() => {
    const here = editor.layout;
    const ids = Object.keys(d.areas);
    const inHere = here ? ids.filter((a) => usedIn(d, a).some((l) => l.name === here.name)) : [];
    const other = ids.filter((a) => !inHere.includes(a) && usedIn(d, a).length);
    const none = ids.filter((a) => !usedIn(d, a).length);
    return [
      { title: here ? `In ${here.label ?? here.name}: picking one selects its part` : 'In this word type', ids: inHere },
      { title: 'Other word types: picking one opens it there', ids: other },
      { title: 'Not in any word type', ids: none }
    ];
  });
</script>

<svelte:window onpointerdown={(e) => { if (!(e.target as HTMLElement).closest('.sw, .more')) { switcher = false; more = false; } }} />

<div class="ap">
  <div class="props">
    <span class="sw">
      <button class="pick" title="Show another area" onclick={() => (switcher = !switcher)}>{#if area}{area.label || areaId} <span class="id">{areaId}</span>{:else}Pick an area{/if} ▾</button>
      {#if switcher}
        <div class="menu" role="menu">
          <table><tbody>
            {#each groups as g (g.title)}
              <tr class="grp"><td colspan="4">{g.title}</td></tr>
              {#each g.ids as a (a)}
                <tr class:on={a === areaId} onclick={() => pick(a)}>
                  <td>{d.areas[a].label || a}{#if g.ids === groups[1].ids}<span class="tiny"> → {usedIn(d, a)[0]?.label ?? usedIn(d, a)[0]?.name}</span>{/if}</td>
                  <td class="id">{a}</td><td class="n">{d.areas[a].size[0]} × {d.areas[a].size[1]}</td><td class="n">{d.areas[a].glyphs.length}</td>
                </tr>
              {:else}<tr><td colspan="4" class="tiny">none</td></tr>{/each}
            {/each}
          </tbody></table>
          {#if editor.advanced}
            {#if newOpen}
              <div class="new">
                <label>id <input type="text" bind:value={newId} placeholder="thumb" /></label>
                <label>Shown as <input type="text" bind:value={newLabel} placeholder="Thumb mark" /></label>
                <span class="tiny">box {area ? `${area.size[0]} × ${area.size[1]}, copied from ${area.label || areaId}` : '350 × 350'}</span>
                {#if newId && newProblem}<span class="err tiny">{newProblem}</span>{/if}
                <div class="row"><button onclick={() => (newOpen = false)}>Cancel</button><button class="primary" disabled={!!newProblem} onclick={createArea}>Create</button></div>
              </div>
            {:else}<button class="lnk" onclick={() => (newOpen = true)}>+ New area…</button>{/if}
          {/if}
        </div>
      {/if}
    </span>
    {#if area && areaId}
      <label class="f">Shown as <input type="text" value={area.label ?? ''} onchange={(e) => setLabel((e.target as HTMLInputElement).value)} style="width: 110px" /></label>
      <span class="f" data-box-fields title="Every word that uses this area moves. Type to preview; Enter applies, Esc cancels.">Box
        <input type="number" class="num" class:hot={changed} value={boxShown[0]} onfocus={beginBox} onblur={boxBlur} onkeydown={(e) => boxKey(0, e)} oninput={(e) => { beginBox(); setPending(0, +(e.target as HTMLInputElement).value); }} /> ×
        <input type="number" class="num" class:hot={changed} value={boxShown[1]} onfocus={beginBox} onblur={boxBlur} onkeydown={(e) => boxKey(1, e)} oninput={(e) => { beginBox(); setPending(1, +(e.target as HTMLInputElement).value); }} />
      </span>
      {#if editor.advanced}
        <label class="f" title="A part with an advance moves the pen (the colon and the bar); 0 for ordinary parts">Advance <input type="number" class="num" value={area.advance ?? 0} onchange={(e) => setAdvance(+(e.target as HTMLInputElement).value)} /></label>
      {/if}
      <span class="f used">Used in
        {#each uses as l (l.name)}<button class="pill" class:on={l.name === editor.layoutName} title="Open {l.label ?? l.name} with this area" onclick={() => { if (l.name !== editor.layoutName) editor.setLayout(l.name); editor.showArea(areaId!); }}>{l.label ?? l.name}</button>{:else}<span class="muted">no word type yet</span>{/each}
      </span>
      {#if editor.advanced}
        <span class="more">
          <button class="pm" title="More" onclick={() => (more = !more)}>⋯</button>
          {#if more}
            <div class="menu right">
              <button disabled={uses.length > 0} title={uses.length ? `Used by ${uses.map((l) => l.label ?? l.name).join(', ')}: remove it from those word types first` : ''} onclick={deleteArea}>Delete area</button>
              {#if uses.length}<span class="tiny">used by {uses.map((l) => l.label ?? l.name).join(', ')}</span>{/if}
            </div>
          {/if}
        </span>
      {/if}
    {/if}
  </div>

  {#if area && areaId}
    {#if changed && pending}
      <div class="pending">Box {area.size[0]} × {area.size[1]} → <b>{pending.size[0]} × {pending.size[1]}</b>, not applied: moves parts in {uses.length} word type{uses.length === 1 ? '' : 's'}. <b>Enter</b> applies · <b>Esc</b> cancels.</div>
      {#if minis.length}
        <div class="minis">
          {#each minis as m (m.name)}
            <div class="mini"><span class="tiny">{m.title}</span>
              <WordCanvas elements={m.now} ghosts={m.before} marked={m.now.filter((e) => e.area === areaId).map((e) => e.name)} width={110} showBoxes={true} showGlyphs={true} />
            </div>
          {/each}
        </div>
      {/if}
    {/if}
    {#if !el && !uses.length}<p class="muted small">Not in any word type yet: add it as a part (Structure, Advanced, + Add part).</p>
    {:else if !el}<p class="muted small">No part of this word shows it right now; clicking a glyph won't preview it here.</p>{/if}

    <div class="hd">
      <span class="muted small">{area.glyphs.length} glyph{area.glyphs.length === 1 ? '' : 's'}{#if members.decimals.length} · {members.chips.length} + {members.decimals.length} position decimals{/if}</span>
      <span class="spacer"></span>
      {#if area.glyphs.length > LIMIT}<input type="text" placeholder="search name / key / 7.6" bind:value={q} style="width: 170px" />{/if}
      <label class="muted small"><input type="checkbox" bind:checked={manage} /> Manage</label>
      {#if manage}<button class="primary small" onclick={() => (adding = true)}>+ Add glyphs</button>{/if}
      <a class="small" href="/glyphs?group={encodeURIComponent(areaId)}">Open in Glyphs →</a>
    </div>
    <div class="chips" class:tall={showAll}>
      {#each shown as g (g)}
        <span class="cell">
          <button class="chip" class:on={previewed(g)} title="{g} · double-click to edit" onclick={() => preview(g)} ondblclick={() => goto(editUrl(g))}>
            <Glyph name={g} size={30} />
            {#if manage}<span class="x" role="button" tabindex="-1" title="Remove from {areaId}" onclick={(e) => { e.stopPropagation(); remove(g); }} onkeydown={() => {}}>×</span>{/if}
          </button>
          <a class="edit" href={editUrl(g)} title="Edit the outline of {g}">edit</a>
        </span>
      {/each}
      {#if area.glyphs.length === 1 && el}<span class="muted small">preview fixed: this part has one glyph</span>{/if}
      {#if chips.length > LIMIT}<button class="small" onclick={() => (showAll = !showAll)}>{showAll ? 'show less ▴' : `show all ${chips.length} ▾`}</button>{/if}
    </div>
    {#if members.decimals.length}
      <div class="tiny">Position decimals · {wide ? 'hui across, decimal down' : 'hui down, decimal across'}{#if el} · click one to preview it{/if}</div>
      <div class="dg" style="grid-template-columns: 22px repeat({wide ? 13 : 10}, minmax(26px, 1fr))">
        {#if wide}
          <span class="h"></span>{#each grid as row (row[0].hui)}<span class="h">{row[0].hui}</span>{/each}
          {#each grid[0] as _, j (j)}
            <span class="h">{j === 0 ? '·' : `.${j}`}</span>
            {#each grid as row (row[j].glyph)}{@render cell(row[j])}{/each}
          {/each}
        {:else}
          <span class="h"></span>{#each grid[0] as c, j (j)}<span class="h">{j === 0 ? '·' : `.${j}`}</span>{/each}
          {#each grid as row (row[0].hui)}
            <span class="h">{row[0].hui}</span>
            {#each row as c (c.glyph)}{@render cell(c)}{/each}
          {/each}
        {/if}
      </div>
    {/if}
  {:else}
    <p class="muted small">Click a part on the canvas to see its area, or pick one above.</p>
  {/if}
</div>
{#if adding && areaId}<AddGlyphsDialog area={areaId} onclose={() => { adding = false; editor.ensurePins(); }} />{/if}

{#snippet cell(c: ReturnType<typeof decimalGrid>[number][number])}
  {#if c.member}
    <span class="c" class:on={previewed(c.glyph)} class:hit={!!q && matches(c.glyph)} role="button" tabindex="0"
      title="{c.glyph} · {decimalPatterns(c.glyph).join(' · ')}{manage ? '' : ' · double-click to edit'}"
      onclick={() => preview(c.glyph)} ondblclick={() => goto(editUrl(c.glyph))} onkeydown={(e) => { if (e.key === 'Enter') preview(c.glyph); }}>
      {c.label}{#if manage}<span class="cx" role="button" tabindex="-1" title="Remove from {areaId}" onclick={(e) => { e.stopPropagation(); remove(c.glyph); }} onkeydown={() => {}}>×</span>{/if}
    </span>
  {:else if manage && c.exists}
    <button class="c miss" title="Add {c.glyph} to {areaId}" onclick={() => app.addToArea(areaId!, [c.glyph])}>+ {c.label}</button>
  {:else}
    <span class="c none" title="{c.glyph}: {c.exists ? 'not in this area' : 'no glyph yet'}">{c.label}</span>
  {/if}
{/snippet}

<style>
  .ap { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .props { display: flex; align-items: center; gap: 6px 12px; flex-wrap: wrap; font-size: var(--t-sm); padding-bottom: 6px; border-bottom: 1px dashed var(--line); }
  .f { display: inline-flex; align-items: center; gap: 4px; color: var(--fg-2); }
  .f input { color: var(--fg); }
  .num { width: 58px; height: 24px; font-family: var(--mono); }
  .num.hot { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
  .used { flex-wrap: wrap; }
  .pill { height: 22px; padding: 0 8px; border-radius: 11px; font-size: var(--t-xs); }
  .pill.on { border-color: var(--accent); color: var(--accent); background: var(--accent-bg); }
  .sw, .more { position: relative; }
  .pick { height: 26px; font-weight: 600; }
  .pm { height: 22px; width: 24px; padding: 0; }
  .menu { position: absolute; left: 0; top: 100%; z-index: 30; margin-top: 2px; min-width: 330px; background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: 0 8px 24px rgba(0,0,0,.18); padding: 4px; display: flex; flex-direction: column; gap: 4px; }
  .menu.right { left: auto; right: 0; min-width: 200px; }
  .menu table { border-collapse: collapse; width: 100%; font-size: var(--t-sm); }
  .menu td { padding: 2px 6px; white-space: nowrap; }
  .menu tr:not(.grp) { cursor: pointer; }
  .menu tr:not(.grp):hover td { background: var(--bg-3); }
  .menu tr.on td { background: var(--accent-bg); color: var(--accent); }
  .menu tr.grp td { font-size: var(--t-xs); color: var(--fg-2); padding-top: 6px; border-bottom: 1px dashed var(--line); cursor: default; }
  .menu td.n { text-align: right; font-family: var(--mono); font-size: var(--t-xs); color: var(--fg-2); }
  .menu .new { display: flex; flex-direction: column; gap: 4px; border-top: 1px solid var(--line); padding-top: 6px; }
  .menu .new label { display: flex; gap: 6px; align-items: center; font-size: var(--t-sm); }
  .lnk { border-style: dashed; background: transparent; height: 24px; font-size: var(--t-sm); align-self: flex-start; }
  .pending { font-size: var(--t-sm); color: var(--accent); background: var(--accent-bg); border-radius: var(--radius); padding: 3px 8px; }
  .minis { display: flex; gap: var(--s-2); flex-wrap: wrap; }
  .mini { display: flex; flex-direction: column; gap: 2px; border: 1px solid var(--line); border-radius: var(--radius); padding: 4px; background: var(--bg); }
  .hd { display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap; }
  .spacer { flex: 1; }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; align-items: flex-start; max-height: 104px; overflow: hidden; }
  .chips.tall { max-height: 30vh; overflow: auto; }
  .cell { display: inline-flex; flex-direction: column; align-items: center; }
  .chip { position: relative; height: 36px; width: 36px; padding: 2px; display: inline-flex; align-items: center; justify-content: center; background: var(--bg); }
  .chip.on { border-color: var(--accent); box-shadow: 0 0 0 1.5px var(--accent); }
  .x { position: absolute; top: -6px; right: -6px; width: 16px; height: 16px; border-radius: 50%; background: var(--bg); border: 1px solid var(--line); font-size: 11px; line-height: 13px; text-align: center; color: var(--fg-2); }
  .edit { font-size: var(--t-xs); line-height: 16px; color: var(--fg-2); text-decoration: none; padding: 0 4px; border-radius: 3px; }
  .edit:hover { color: var(--accent); background: var(--accent-bg); }
  .dg { display: grid; gap: 2px; font-family: var(--mono); font-size: 11px; max-width: 640px; }
  .dg .h { color: var(--fg-2); text-align: center; line-height: 18px; font-size: var(--t-xs); }
  .dg .c { position: relative; border: 1px solid var(--line); border-radius: 3px; text-align: center; line-height: 18px; height: 20px; padding: 0; background: var(--bg); white-space: nowrap; cursor: pointer; font-family: var(--mono); font-size: 11px; }
  .dg .c:hover { border-color: var(--accent); }
  .dg .c.on { border-color: var(--accent); box-shadow: 0 0 0 1.5px var(--accent); color: var(--accent); font-weight: 700; }
  .dg .c.hit { background: color-mix(in srgb, var(--warn) 18%, var(--bg)); border-color: var(--warn); }
  .dg .c.miss { border-style: dashed; color: var(--fg-2); background: transparent; }
  .dg .c.none { border-style: dotted; color: var(--fg-2); opacity: .5; cursor: default; }
  .cx { display: none; position: absolute; top: -6px; right: -5px; width: 14px; height: 14px; border-radius: 50%; border: 1px solid var(--line); background: var(--bg); font-size: 10px; line-height: 12px; color: var(--fg-2); }
  .dg .c:hover .cx { display: block; }
  .small { font-size: var(--t-xs); }
  .tiny { font-size: var(--t-xs); color: var(--fg-2); }
  .err { color: var(--danger); }
  .row { display: flex; gap: 6px; justify-content: flex-end; }
</style>
