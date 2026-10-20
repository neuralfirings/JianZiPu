<script lang="ts">
  // Area Properties (Layouts, docs/AREAS-PLACEMENT-UX.md): the area of the selected part, or
  // the one picked in the switcher. Its name, box (typed sizes preview on the canvas and only
  // apply on Enter / leaving the fields), advance (Advanced), + New area and Delete area (only an
  // empty area no word type uses; otherwise a banner says why), the word types that use it, and its glyphs: click = preview, double-click or "edit" = glyph editor, Manage =
  // remove / add. Position decimals sit in a text grid (13 hui × blank, .1–.9).
  import * as I from '$lib/icons';
  import { goto } from '$app/navigation';
  import { api, type ResolvedElement } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { editor } from '$lib/editor.svelte';
  import { panels } from '$lib/panels.svelte';
  import { defaultChoice, shapeElements } from '$lib/shape';
  import { addArea, areaIdProblem, decimalGrid, deleteAreaProblems, splitMembers, usedIn } from '$lib/areas';
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
  function openNew() { newOpen = !newOpen; switcher = false; delState = null; }
  function createArea() {
    const id = newId.trim();
    if (areaIdProblem(d, id)) return;
    const size: [number, number] = area ? [area.size[0], area.size[1]] : [350, 350];
    app.edit(`New area ${id}`, (x) => addArea(x, id, newLabel, size));
    newId = ''; newLabel = ''; newOpen = false; switcher = false; delState = null;
    editor.areaView = id;
  }
  // ---- delete: a dialog when it can go, a banner naming what keeps it otherwise
  let delState = $state<{ area: string; problems: string[] } | null>(null);
  function askDelete() {
    const a = areaId; if (!a) return;
    newOpen = false;
    delState = { area: a, problems: deleteAreaProblems(d, a) };
  }
  function deleteArea() {
    const a = delState?.area; delState = null;
    if (!a || deleteAreaProblems(d, a).length) return;
    app.edit(`Delete area ${a}`, (x) => { delete x.areas[a]; });
    editor.areaView = null; app.syncCatalog();
  }
  // the banner goes away once the area changes or the reasons are fixed
  $effect(() => { if (delState && (delState.area !== areaId || !deleteAreaProblems(d, delState.area).length) && delState.problems.length) delState = null; });
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

<svelte:window onpointerdown={(e) => { const t = e.target as HTMLElement; if (!t.closest('.sw')) switcher = false; if (!t.closest('.newwrap')) newOpen = false; }} />

<div class="ap">
  <div class="props">
    <span class="sw">
      <button class="pick" title="Show another area" onclick={() => (switcher = !switcher)}>{#if area}{area.label || areaId} <span class="id">{areaId}</span>{:else}Pick an area{/if} <I.Dropdown size={14} /></button>
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
        {#each uses as l (l.name)}<button class="opt" class:on={l.name === editor.layoutName} title="Open {l.label ?? l.name} with this area" onclick={() => { if (l.name !== editor.layoutName) editor.setLayout(l.name); editor.showArea(areaId!); }}>{l.label ?? l.name}</button>{:else}<span class="muted">no word type yet</span>{/each}
      </span>
    {/if}
    <span class="acts">
      <span class="newwrap">
        <button class="sm" onclick={openNew} aria-expanded={newOpen}>+ New area</button>
        {#if newOpen}
          <div class="menu right new" role="dialog" aria-label="New area">
            <label>Id <input type="text" bind:value={newId} placeholder="thumb" class="mono" /></label>
            <label>Shown as <input type="text" bind:value={newLabel} placeholder="Thumb mark" /></label>
            <span class="tiny">Box {area ? `${area.size[0]} × ${area.size[1]}, copied from ${area.label || areaId}` : '350 × 350'}. Add glyphs with Manage, then use it in a word type's Structure.</span>
            {#if newId && newProblem}<span class="err tiny"><I.Problem size={12} /> {newProblem}</span>{/if}
            <div class="row"><span class="spacer"></span><button class="quiet" onclick={() => (newOpen = false)}>Cancel</button><button class="primary" disabled={!!newProblem} onclick={createArea}>Create area</button></div>
          </div>
        {/if}
      </span>
      {#if area && areaId}<button class="sm danger" onclick={askDelete}>Delete area</button>{/if}
    </span>
  </div>

  {#if delState && delState.problems.length && delState.area === areaId}
    <div class="banner danger" role="alert">
      <span class="ic"><I.Problem /></span>
      <div class="why"><b>Can't delete {app.areaLabel(delState.area)} ({delState.area}).</b>
        <ul>{#each delState.problems as p (p)}<li>{p}</li>{/each}</ul>
      </div>
      <button class="quiet sm" aria-label="Close" onclick={() => (delState = null)}><I.Close /></button>
    </div>
  {/if}
  {#if delState && !delState.problems.length}
    <div class="modal-bg" role="presentation" onclick={() => (delState = null)}>
      <div class="modal del" role="dialog" aria-modal="true" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && (delState = null)}>
        <h3>Delete the area {app.areaLabel(delState.area)}?</h3>
        <p>{delState.area} has no glyphs and no word type uses it. Nothing else changes, and Undo brings it back.</p>
        <div class="row"><span class="spacer"></span><button class="quiet" onclick={() => (delState = null)}>Cancel</button><button class="danger" onclick={deleteArea}>Delete area</button></div>
      </div>
    </div>
  {/if}

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
            {#if manage}<span class="x" role="button" tabindex="-1" title="Remove from {areaId}" onclick={(e) => { e.stopPropagation(); remove(g); }} onkeydown={() => {}}><I.Close size={10} /></span>{/if}
          </button>
          <a class="edit" href={editUrl(g)} title="Edit the outline of {g}">edit</a>
        </span>
      {/each}
      {#if area.glyphs.length === 1 && el}<span class="muted small">preview fixed: this part has one glyph</span>{/if}
      {#if chips.length > LIMIT}<button class="small" onclick={() => (showAll = !showAll)}>{#if showAll}show less <I.Less size={12} />{:else}show all {chips.length} <I.Dropdown size={12} />{/if}</button>{/if}
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
      {c.label}{#if manage}<span class="cx" role="button" tabindex="-1" title="Remove from {areaId}" onclick={(e) => { e.stopPropagation(); remove(c.glyph); }} onkeydown={() => {}}><I.Close size={10} /></span>{/if}
    </span>
  {:else if manage && c.exists}
    <button class="c miss" title="Add {c.glyph} to {areaId}" onclick={() => app.addToArea(areaId!, [c.glyph])}>+ {c.label}</button>
  {:else}
    <span class="c none" title="{c.glyph}: {c.exists ? 'not in this area' : 'no glyph yet'}">{c.label}</span>
  {/if}
{/snippet}

<style>
  .ap { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .props { display: flex; align-items: center; gap: 6px 12px; flex-wrap: wrap; font-size: var(--t-small); padding-bottom: 6px; border-bottom: 1px dashed var(--border); }
  .f { display: inline-flex; align-items: center; gap: 4px; color: var(--ink-muted); }
  .f input { color: var(--ink); }
  .num { width: 58px; height: 24px; font-family: var(--font-mono); }
  .num.hot { border-color: var(--link); box-shadow: 0 0 0 1px var(--link); }
  .used { flex-wrap: wrap; }
  .opt { height: var(--control-sm); padding: 0 var(--space-4); border-color: var(--border); font-size: var(--t-small); }
  .opt.on { border-color: var(--sel-border); color: var(--ink); background: var(--sel-bg); }
  .sw, .newwrap { position: relative; }
  .acts { margin-left: auto; display: inline-flex; gap: var(--space-4); align-items: center; }
  .new { min-width: 280px; padding: var(--space-5); gap: var(--space-4); }
  .new label { display: flex; flex-direction: column; gap: var(--space-2); font-weight: 600; color: var(--ink); }
  .new .mono { font-family: var(--font-mono); }
  .ap .banner { flex-wrap: nowrap; align-items: flex-start; font-size: var(--t-small); }
  .why { flex: 1; min-width: 0; }
  .why ul { margin: var(--space-2) 0 0; padding-left: 18px; }
  .banner .quiet { flex: none; width: var(--control-sm); padding: 0; }
  .del { max-width: 440px; display: flex; flex-direction: column; gap: var(--space-4); }
  .del p { margin: 0; }
  .spacer { flex: 1; }
  .pick { height: 26px; font-weight: 600; }
  .menu { position: absolute; left: 0; top: 100%; z-index: 30; margin-top: 2px; min-width: 330px; background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: var(--shadow-float); padding: 4px; display: flex; flex-direction: column; gap: 4px; }
  .menu.right { left: auto; right: 0; min-width: 200px; }
  .menu table { border-collapse: collapse; width: 100%; font-size: var(--t-small); }
  .menu td { padding: 2px 6px; white-space: nowrap; }
  .menu tr:not(.grp) { cursor: pointer; }
  .menu tr:not(.grp):hover td { background: var(--bg-hover); }
  .menu tr.on td { background: var(--sel-bg); color: var(--ink); }
  .menu tr.grp td { font-size: var(--t-caption); color: var(--ink-muted); padding-top: 6px; border-bottom: 1px dashed var(--border); cursor: default; }
  .menu td.n { text-align: right; font-family: var(--font-mono); font-size: var(--t-caption); color: var(--ink-muted); }
  .pending { font-size: var(--t-small); color: var(--link); background: var(--sel-bg); border-radius: var(--radius-md); padding: 3px 8px; }
  .minis { display: flex; gap: var(--space-4); flex-wrap: wrap; }
  .mini { display: flex; flex-direction: column; gap: 2px; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 4px; background: var(--bg-field); }
  .hd { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
  .spacer { flex: 1; }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; align-items: flex-start; max-height: 104px; overflow: hidden; }
  .chips.tall { max-height: 30vh; overflow: auto; }
  .cell { display: inline-flex; flex-direction: column; align-items: center; }
  .chip { position: relative; height: 36px; width: 36px; padding: 2px; display: inline-flex; align-items: center; justify-content: center; background: var(--bg-field); }
  .chip.on { border-color: var(--link); box-shadow: 0 0 0 1.5px var(--link); }
  .x { display: inline-flex; align-items: center; justify-content: center; position: absolute; top: -6px; right: -6px; width: 16px; height: 16px; border-radius: 50%; background: var(--bg-field); border: 1px solid var(--border); font-size: 11px; line-height: 13px; text-align: center; color: var(--ink-muted); }
  .edit { font-size: var(--t-caption); line-height: 16px; color: var(--ink-muted); text-decoration: none; padding: 0 4px; border-radius: 3px; }
  .edit:hover { color: var(--link); background: var(--sel-bg); }
  .dg { display: grid; gap: 2px; font-family: var(--font-mono); font-size: 11px; max-width: 640px; }
  .dg .h { color: var(--ink-muted); text-align: center; line-height: 18px; font-size: var(--t-caption); }
  .dg .c { position: relative; border: 1px solid var(--border); border-radius: 3px; text-align: center; line-height: 18px; height: 20px; padding: 0; background: var(--bg-field); white-space: nowrap; cursor: pointer; font-family: var(--font-mono); font-size: 11px; }
  .dg .c:hover { border-color: var(--link); }
  .dg .c.on { border-color: var(--link); box-shadow: 0 0 0 1.5px var(--link); color: var(--link); font-weight: 700; }
  .dg .c.hit { background: color-mix(in srgb, var(--status-draft) 18%, var(--bg-field)); border-color: var(--status-draft); }
  .dg .c.miss { border-style: dashed; color: var(--ink-muted); background: transparent; }
  .dg .c.none { border-style: dotted; color: var(--ink-muted); opacity: .5; cursor: default; }
  .cx { display: none; align-items: center; justify-content: center; position: absolute; top: -6px; right: -5px; width: 14px; height: 14px; border-radius: 50%; border: 1px solid var(--border); background: var(--bg-field); font-size: 10px; line-height: 12px; color: var(--ink-muted); }
  .dg .c:hover .cx { display: inline-flex; }
  .small { font-size: var(--t-caption); }
  .tiny { font-size: var(--t-caption); color: var(--ink-muted); }
  .err { color: var(--status-danger); }
  .row { display: flex; gap: 6px; justify-content: flex-end; }
</style>
