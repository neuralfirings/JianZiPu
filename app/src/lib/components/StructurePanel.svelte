<script lang="ts">
  // Structure: one line per part of the open word type, in typing order.
  // Everyday: include in the preview, preview glyph (popover), select the part,
  // pick an option / row count. Advanced: drag to reorder, "edit ▸" card with
  // the structural settings, add part, recognition fold.
  import { app, parseElement } from '$lib/state.svelte';
  import { editor } from '$lib/editor.svelte';
  import { panels } from '$lib/panels.svelte';
  import { addArea, areaIdProblem } from '$lib/areas';
  import { slotIsSimple, elementNames, anchorNames, shapeElements, type ShapeElement } from '$lib/shape';
  import type { Layout, Slot } from '$lib/api';
  import Glyph from './Glyph.svelte';
  import GlyphPopover from './GlyphPopover.svelte';

  let layout = $derived(editor.layout!);
  let lname = $derived(layout.label ?? layout.name);
  let anchors = $derived(anchorNames(editor.elements, app.design!.areas));
  const areaLabel = (a: string) => app.areaLabel(a);
  let advanced = $derived(editor.advanced);

  function editLayout(label: string, fn: (l: Layout) => void) {
    app.edit(`${lname}: ${label}`, (d) => { const l = d.layouts.find((x) => x.name === layout.name)!; fn(l); });
    editor.syncChoice();
  }
  const present = (i: number) => editor.choice[i] !== null && editor.choice[i] !== undefined;
  const elemsOf = (s: Slot) => editor.elements.filter((e) => e.slot === s.name);
  /** The elements a left-out slot would contribute if put back (its first option). */
  function wouldBe(i: number): ShapeElement[] {
    const c = [...editor.choice];
    c[i] = layout.slots[i].repeat ? [0] : 0;
    return shapeElements(layout, c).filter((e) => e.slot === layout.slots[i].name);
  }
  const glyphOf = (e: ShapeElement) => editor.pinned[e.name] ?? editor.pinByArea[e.area] ?? app.design!.areas[e.area]?.glyphs[0] ?? '';
  const slotLabel = (s: Slot) => (slotIsSimple(s) ? areaLabel(parseElement(s.alternatives[0][0]).area) : s.name);
  const elLabel = (e: ShapeElement) => (e.el === e.area ? areaLabel(e.area) : `${areaLabel(e.area)} (${e.el})`);
  function altLabel(alt: string[]) {
    return alt.map((t) => { const { name, area } = parseElement(t); return name === area ? areaLabel(area) : `${areaLabel(area)} (${name})`; }).join(' + ');
  }
  const slotSelected = (s: Slot) => elemsOf(s).some((e) => e.name === editor.selected);
  function selectSlot(s: Slot) { const e = elemsOf(s)[0]; if (e) editor.select(e.name); }

  // preview glyph popover
  let menu = $state<{ name: string; area: string; x: number; y: number } | null>(null);
  function openMenu(ev: MouseEvent, e: ShapeElement) {
    ev.stopPropagation();
    if (menu?.name === e.name) { menu = null; return; }
    const r = (ev.currentTarget as HTMLElement).getBoundingClientRect();
    menu = { name: e.name, area: e.area, x: r.right, y: r.bottom };
  }

  // rows (repeat slots)
  function setRows(i: number, n: number) {
    const s = layout.slots[i];
    const cur = Array.isArray(editor.choice[i]) ? (editor.choice[i] as number[]) : [];
    n = Math.min(s.repeat![1], Math.max(s.repeat![0], n));
    editor.setChoice(i, Array.from({ length: n }, (_, j) => cur[j] ?? 0));
  }
  function setInstanceAlt(i: number, j: number, k: number) {
    const cur = [...(editor.choice[i] as number[])];
    cur[j] = k;
    editor.setChoice(i, cur);
  }

  // ---- Advanced: structural edits
  let editing = $state<string | null>(null);
  let dragSlot = $state<number | null>(null);
  function dropSlot(to: number) {
    if (dragSlot == null || dragSlot === to) { dragSlot = null; return; }
    const from = dragSlot; dragSlot = null;
    editLayout(`move ${layout.slots[from].name}`, (l) => { const [s] = l.slots.splice(from, 1); l.slots.splice(to > from ? to - 1 : to, 0, s); });
  }
  function setOptional(i: number, v: boolean) {
    editLayout(`${layout.slots[i].name} ${v ? 'optional' : 'always present'}`, (l) => { if (v) l.slots[i].optional = true; else delete l.slots[i].optional; });
  }
  function toggleRepeat(i: number) {
    const s = layout.slots[i];
    editLayout(`${s.name}: ${s.repeat ? 'single' : 'repeated'}`, (l) => { if (l.slots[i].repeat) delete l.slots[i].repeat; else l.slots[i].repeat = [1, 4]; });
  }
  function setRange(i: number, lo: number, hi: number) {
    if (lo < 1 || hi < lo) return;
    editLayout(`${layout.slots[i].name}: ${lo}–${hi} rows`, (l) => { l.slots[i].repeat = [lo, hi]; });
  }
  function setRequires(i: number, list: string[]) {
    editLayout(`${layout.slots[i].name} requires ${list.join(', ') || 'nothing'}`, (l) => { if (list.length) l.slots[i].requires = list; else delete l.slots[i].requires; });
  }
  /** A fresh element id for an area in this layout. */
  function freshName(area: string) {
    const taken = new Set([...layout.slots.map((s) => s.name), ...elementNames(layout).map((e) => e.name)]);
    if (!taken.has(area)) return area;
    let n = 2; while (taken.has(`${area}_${n}`)) n++;
    return `${area}_${n}`;
  }
  const token = (name: string, area: string) => (name === area ? area : `${name}:${area}`);
  function addToAlt(i: number, a: number, area: string) {
    if (!area) return;
    const name = freshName(area);
    editLayout(`${layout.slots[i].name}: option ${a + 1} + ${areaLabel(area)}`, (l) => { l.slots[i].alternatives[a].push(token(name, area)); });
  }
  function removeFromAlt(i: number, a: number, k: number) {
    const s = layout.slots[i];
    if (s.alternatives[a].length === 1 && s.alternatives.length === 1) { alert('A part needs at least one area. Remove the part instead.'); return; }
    const { name } = parseElement(s.alternatives[a][k]);
    editLayout(`${s.name}: remove ${name} from option ${a + 1}`, (l) => {
      l.slots[i].alternatives[a].splice(k, 1);
      if (!l.slots[i].alternatives[a].length) l.slots[i].alternatives.splice(a, 1);
      dropElementRefs(l, name);
    });
  }
  function dropElementRefs(l: Layout, name: string) {
    const still = l.slots.some((s) => s.alternatives.some((alt) => alt.some((t) => parseElement(t).name === name)));
    if (still) return;
    l.relationships = l.relationships.filter((r) => r.elem !== name && r.base !== name);
    for (const k of ['y', 'x', 'y_phantom', 'x_phantom'] as const) if (Array.isArray(l.center[k])) l.center[k] = (l.center[k] as string[]).filter((x) => x !== name);
    if (l.requires_any) l.requires_any = l.requires_any.filter((x) => x !== name);
    if (l.priority) l.priority = l.priority.filter((x) => x !== name);
  }
  function renameEl(i: number, a: number, k: number, next: string) {
    const s = layout.slots[i];
    const { name, area } = parseElement(s.alternatives[a][k]);
    next = next.trim();
    if (!next || next === name) return;
    if (!/^[a-z][a-z0-9_]*$/i.test(next) || layout.slots.some((x) => x.name === next && x.name !== s.name) || elementNames(layout).some((e) => e.name === next)) { alert(`"${next}" is not free or not a valid id (letters, digits, _).`); return; }
    editLayout(`rename ${name} → ${next}`, (l) => {
      l.slots[i].alternatives[a][k] = token(next, area);
      for (const r of l.relationships) { if (r.elem === name) r.elem = next; if (r.base === name) r.base = next; }
      for (const key of ['y', 'x', 'y_phantom', 'x_phantom'] as const) if (Array.isArray(l.center[key])) l.center[key] = (l.center[key] as string[]).map((x) => (x === name ? next : x));
      if (l.requires_any) l.requires_any = l.requires_any.map((x) => (x === name ? next : x));
      if (l.priority) l.priority = l.priority.map((x) => (x === name ? next : x));
      for (const x of l.slots) if (x.requires) x.requires = x.requires.map((y) => (y === name ? next : y));
    });
  }
  function changeArea(i: number, a: number, k: number, area: string) {
    const { name } = parseElement(layout.slots[i].alternatives[a][k]);
    editLayout(`${name} now takes ${areaLabel(area)}`, (l) => { l.slots[i].alternatives[a][k] = token(name, area); });
  }
  function addAlt(i: number) {
    const s = layout.slots[i];
    const first = parseElement(s.alternatives[0][0]).area;
    const name = freshName(first);
    editLayout(`${s.name}: another option`, (l) => { l.slots[i].alternatives.push([token(name, first)]); });
  }
  function removeSlot(i: number) {
    const s = layout.slots[i];
    const els = new Set(s.alternatives.flat().map((t) => parseElement(t).name).concat(s.name));
    const n = layout.relationships.filter((r) => els.has(r.elem) || (r.base && els.has(r.base))).length;
    if (!confirm(`Remove part "${slotLabel(s)}" (${s.name}) from ${lname}?${n ? ` ${n} spacing rules that mention it will go too.` : ''}`)) return;
    editing = null;
    editLayout(`remove part ${s.name}`, (l) => {
      l.slots.splice(i, 1);
      l.relationships = l.relationships.filter((r) => !els.has(r.elem) && !(r.base && els.has(r.base)));
      for (const k of ['y', 'x', 'y_phantom', 'x_phantom'] as const) if (Array.isArray(l.center[k])) l.center[k] = (l.center[k] as string[]).filter((x) => !els.has(x));
      if (l.requires_any) l.requires_any = l.requires_any.filter((x) => !els.has(x));
      if (l.priority) l.priority = l.priority.filter((x) => !els.has(x));
      for (const x of l.slots) if (x.requires) { x.requires = x.requires.filter((y) => !els.has(y)); if (!x.requires.length) delete x.requires; }
    });
  }
  function addSlot(area: string) {
    if (!area) return;
    const n = freshName(area);
    editLayout(`add part ${n}`, (l) => {
      l.slots.push({ name: n, optional: true, alternatives: [[token(n, area)]] });
      l.relationships.push({ axis: 'y', elem: n, base: null, gap: 0 }, { axis: 'x', elem: n, base: null, gap: 0 });
    });
    editing = n;
  }
  // + Add part → New area…: the area and the part in one step (one undo step)
  let newArea = $state<{ id: string; label: string } | null>(null);
  let newAreaProblem = $derived(newArea ? areaIdProblem(app.design!, newArea.id.trim()) : null);
  function addNewAreaPart() {
    if (!newArea || newAreaProblem) return;
    const id = newArea.id.trim(), label = newArea.label, n = freshName(id), lname = layout.name;
    app.edit(`New area ${id} + part in ${lname}`, (x) => {
      addArea(x, id, label, [350, 350]);
      const l = x.layouts.find((y) => y.name === lname)!;
      l.slots.push({ name: n, optional: true, alternatives: [[token(n, id)]] });
      l.relationships.push({ axis: 'y', elem: n, base: null, gap: 0 }, { axis: 'x', elem: n, base: null, gap: 0 });
    });
    newArea = null;
    editing = n;
    editor.syncChoice();
    editor.showArea(id);
    panels.setFolded('glyphs', false);
  }
  let allNames = $derived([...new Set([...layout.slots.map((s) => s.name), ...elementNames(layout).map((e) => e.name)])]);
  const nameLabel = (n: string) => { const s = layout.slots.find((x) => x.name === n); if (s) return slotLabel(s); const e = elementNames(layout).find((x) => x.name === n); return e ? (e.name === e.area ? areaLabel(e.area) : `${areaLabel(e.area)} (${n})`) : n; };
  function toggleList(key: 'requires_any' | 'priority', n: string) {
    editLayout(`${key === 'requires_any' ? 'recognised by' : 'prefer'} ${n}`, (l) => {
      const cur = l[key] ?? [];
      l[key] = cur.includes(n) ? cur.filter((x) => x !== n) : [...cur, n];
      if (!l[key]!.length) delete l[key];
    });
  }
  const areaKeys = $derived(Object.keys(app.design!.areas));
</script>

<div class="stack">
  {#each layout.slots as s, i (s.name)}
    {@const on = present(i)}
    {@const c = editor.choice[i]}
    <div class="line" class:sel={slotSelected(s)} class:off={!on} class:dragover={dragSlot != null && dragSlot !== i}
      ondragover={(e) => { if (dragSlot != null) e.preventDefault(); }} ondrop={() => dropSlot(i)} role="group">
      <span class="grip" draggable="true" ondragstart={() => (dragSlot = i)} ondragend={() => (dragSlot = null)} title="Drag to change the typing order">⠿</span>
      {#if s.optional}
        <input type="checkbox" checked={on} title={on ? 'Leave this part out of the preview word' : 'Put this part back into the preview word'} onchange={() => editor.setChoice(i, on ? null : s.repeat ? [0] : 0)} />
      {:else}
        <span class="req" title="Always in the word">●</span>
      {/if}
      {#if s.repeat}
        <button class="lbl" onclick={() => selectSlot(s)}>{slotLabel(s)} <span class="id">{s.name}</span></button>
        {#if on}
          <span class="seg"><button onclick={() => setRows(i, (c as number[]).length - 1)} disabled={(c as number[]).length <= s.repeat[0]}>−</button><span class="n">{(c as number[]).length}</span><button onclick={() => setRows(i, (c as number[]).length + 1)} disabled={(c as number[]).length >= s.repeat[1]}>+</button></span>
          <span class="tiny">rows</span>
        {/if}
      {:else if on}
        {#each elemsOf(s) as e, k (e.name)}
          {#if k > 0}<span class="plus">+</span>{/if}
          <button class="gp" data-gpop-anchor title="{e.name}: choose the preview glyph" onclick={(ev) => openMenu(ev, e)}><Glyph name={glyphOf(e)} size={20} /><span class="dd">▾</span></button>
          <button class="lbl" class:on={editor.selected === e.name} title="Select {e.name}" onclick={() => editor.select(e.name)}>{elemsOf(s).length > 1 ? elLabel(e) : slotLabel(s)} <span class="id">{e.name}</span></button>
          {#if anchors.has(e.name)}<span class="tag red" title="First glyph of the attachment chain: carries the word's absolute position">anchor</span>{/if}
          {#if editor.resolved?.pins?.[e.name]}<span class="tag dot" title="A spacing rule depends on which glyph this part shows">by glyph</span>{/if}
        {/each}
      {:else}
        {#each wouldBe(i) as e, k (e.name)}
          {#if k > 0}<span class="plus">+</span>{/if}
          <span class="gp dim"><Glyph name={glyphOf(e)} size={20} /></span>
          <span class="lbl dim">{wouldBe(i).length > 1 ? elLabel(e) : slotLabel(s)} <span class="id">{e.name}</span></span>
        {/each}
        <span class="tiny">left out</span>
      {/if}
      <span class="spacer"></span>
      {#if advanced}
        {#if s.optional}<span class="tag">optional</span>{/if}
        {#if s.repeat}<span class="tag">{s.repeat[0]}–{s.repeat[1]} rows</span>{/if}
        {#if s.alternatives.length > 1}<span class="tag">{s.alternatives.length} options</span>{/if}
        {#if s.requires?.length}<span class="tag" title="only when {s.requires.join(', ')} is also there">needs {s.requires.join(', ')}</span>{/if}
        <button class="exp" class:on={editing === s.name} onclick={() => (editing = editing === s.name ? null : s.name)}>edit {editing === s.name ? '▾' : '▸'}</button>
      {/if}
    </div>

    {#if on && !s.repeat && s.alternatives.length > 1}
      <div class="sub"><span class="tiny">one of</span>
        <span class="segs">{#each s.alternatives as alt, a}<button class:on={c === a} onclick={() => editor.setChoice(i, a)}>{altLabel(alt)}</button>{/each}</span>
      </div>
    {/if}
    {#if on && s.repeat}
      {#each c as number[] as k, j}
        <div class="sub">
          <span class="tiny">row {j + 1}</span>
          {#if s.alternatives.length > 1}
            <span class="segs">{#each s.alternatives as alt, a}<button class:on={k === a} onclick={() => setInstanceAlt(i, j, a)}>{altLabel(alt)}</button>{/each}</span>
          {/if}
          {#each editor.elements.filter((e) => e.slot === s.name && e.instance === j + 1) as e (e.name)}
            <button class="gp" data-gpop-anchor title="{e.name}: choose the preview glyph" onclick={(ev) => openMenu(ev, e)}><Glyph name={glyphOf(e)} size={20} /><span class="dd">▾</span></button>
            <button class="lbl small" class:on={editor.selected === e.name} onclick={() => editor.select(e.name)}>{elLabel(e)}{#if anchors.has(e.name)} <span class="tag red">anchor</span>{/if}</button>
          {/each}
        </div>
      {/each}
    {/if}

    {#if advanced && editing === s.name}
      <div class="card">
        <div class="row wrap">
          <label><input type="checkbox" checked={!!s.optional} onchange={(e) => setOptional(i, (e.target as HTMLInputElement).checked)} /> optional (can be left out of a word)</label>
          <span class="spacer"></span>
          <label><input type="checkbox" checked={!!s.repeat} onchange={() => toggleRepeat(i)} /> repeats</label>
          {#if s.repeat}<input type="number" value={s.repeat[0]} style="width:50px" onchange={(e) => setRange(i, +(e.target as HTMLInputElement).value, s.repeat![1])} />–<input type="number" value={s.repeat[1]} style="width:50px" onchange={(e) => setRange(i, s.repeat![0], +(e.target as HTMLInputElement).value)} /><span class="tiny">rows</span>{/if}
        </div>
        <div class="row wrap">
          <span class="tiny">only when this part is also there:</span>
          {#each s.requires ?? [] as r (r)}<span class="ec">{nameLabel(r)}<button class="x" onclick={() => setRequires(i, (s.requires ?? []).filter((x) => x !== r))}>×</button></span>{/each}
          <select class="add" value="" onchange={(e) => { const v = (e.target as HTMLSelectElement).value; if (v) setRequires(i, [...(s.requires ?? []), v]); (e.target as HTMLSelectElement).value = ''; }}>
            <option value="">+ ▾</option>{#each layout.slots.filter((x) => x.name !== s.name && !(s.requires ?? []).includes(x.name)) as x}<option value={x.name}>{slotLabel(x)} ({x.name})</option>{/each}
          </select>
        </div>
        <div class="tiny">{s.repeat ? 'each row holds one of:' : 'holds one of:'}</div>
        {#each s.alternatives as alt, a (a)}
          {#if a > 0}<div class="or">or</div>{/if}
          <div class="alt">
            <span class="tiny" style="width:52px">option {a + 1}</span>
            {#each alt as t, k (t)}
              {@const pe = parseElement(t)}
              {#if k > 0}<span class="plus">+</span>{/if}
              <span class="ec edit">
                <select value={pe.area} title="area" onchange={(e) => changeArea(i, a, k, (e.target as HTMLSelectElement).value)}>{#each areaKeys as ak}<option value={ak}>{areaLabel(ak)}</option>{/each}</select>
                <input type="text" class="idin" value={pe.name} title="element id (used by spacing rules)" onchange={(e) => renameEl(i, a, k, (e.target as HTMLInputElement).value)} />
                <button class="x" title="Remove from this option" onclick={() => removeFromAlt(i, a, k)}>×</button>
                <button class="arealink" title="Show this area in Area Properties (name, box, glyphs)" onclick={() => { editor.showArea(pe.area); panels.setFolded('glyphs', false); }}>area ↗</button>
              </span>
            {/each}
            <select class="add" value="" title="Add an area to this option" onchange={(e) => { addToAlt(i, a, (e.target as HTMLSelectElement).value); (e.target as HTMLSelectElement).value = ''; }}>
              <option value="">+</option>{#each areaKeys as ak}<option value={ak}>{areaLabel(ak)} ({ak})</option>{/each}
            </select>
          </div>
        {/each}
        <div class="row">
          <button class="lnk" onclick={() => addAlt(i)}>+ another option</button>
          <span class="spacer"></span>
          <button class="danger" onclick={() => removeSlot(i)}>Remove part…</button>
        </div>
      </div>
    {/if}
  {/each}
  {#if layout.slots.length === 0}<p class="muted">No parts yet. {advanced ? 'Add one below.' : 'Turn on Advanced to add parts.'}</p>{/if}

  {#if advanced}
    <select class="addpart" value="" onchange={(e) => { const v = (e.target as HTMLSelectElement).value; if (v === '__new') newArea = { id: '', label: '' }; else addSlot(v); (e.target as HTMLSelectElement).value = ''; }}>
      <option value="">+ Add part ▾ (pick an area; it lands at the bottom)</option>
      {#each areaKeys as ak}<option value={ak}>{areaLabel(ak)} ({ak})</option>{/each}
      <option value="__new">New area… (makes the area and the part)</option>
    </select>
    {#if newArea}
      <div class="newarea">
        <label>id <input type="text" bind:value={newArea.id} placeholder="thumb" style="width: 90px" /></label>
        <label>Shown as <input type="text" bind:value={newArea.label} placeholder="Thumb mark" style="width: 110px" /></label>
        <span class="tiny">box 350 × 350, change it in Area Properties</span>
        {#if newArea.id && newAreaProblem}<span class="tiny err">{newAreaProblem}</span>{/if}
        <button onclick={() => (newArea = null)}>Cancel</button><button class="primary" disabled={!!newAreaProblem} onclick={addNewAreaPart}>Create</button>
      </div>
    {/if}
    <div class="tiny">Areas (their names, boxes and glyphs) are shared by every word type: their properties are in the Area Properties panel; New area… is in its switcher (Advanced).</div>
    <details class="rec">
      <summary>Recognition <span class="tiny">which typed words become a {lname}</span></summary>
      <div class="tiny">Used when the typed word has at least one of:</div>
      <div class="chips">{#each allNames as n (n)}<button class="tg" class:on={layout.requires_any?.includes(n)} onclick={() => toggleList('requires_any', n)}>{nameLabel(n)}</button>{/each}</div>
      <div class="tiny" title="When two readings of the same keys are equally long, the one whose present parts come first here wins">If the same keys can be read two ways, prefer the reading with (first wins):</div>
      <div class="chips">{#each allNames as n (n)}{@const k = layout.priority?.indexOf(n) ?? -1}<button class="tg" class:on={k >= 0} onclick={() => toggleList('priority', n)}>{#if k >= 0}<span class="rk">{k + 1}</span>{/if}{nameLabel(n)}</button>{/each}</div>
    </details>
  {/if}
</div>

{#if menu}
  <GlyphPopover title="preview {menu.name} as" glyphs={app.design!.areas[menu.area]?.glyphs ?? []} current={editor.pinned[menu.name] ?? null}
    anchor={{ x: menu.x, y: menu.y }} onpick={(g) => { editor.pin(menu!.name, g); menu = null; }} onclose={() => (menu = null)} />
{/if}

<style>
  .stack { display: flex; flex-direction: column; gap: 3px; }
  .line { display: flex; align-items: center; gap: 5px; min-height: 30px; padding: 1px 4px; border-radius: 4px; border: 1px solid transparent; flex-wrap: wrap; }
  .line.sel { background: var(--sel-bg); border-color: var(--link); }
  .line.off { opacity: .55; }
  .line.dragover { border-top-color: var(--link); }
  .grip { color: var(--ink-muted); cursor: grab; font-size: 13px; }
  .req { color: var(--ink-muted); font-size: 8px; width: 13px; text-align: center; }
  .gp { display: inline-flex; align-items: center; gap: 1px; height: 26px; padding: 0 3px; border: 1px solid var(--border); border-radius: 4px; background: var(--bg-field); }
  .gp .dd { font-size: 9px; color: var(--ink-muted); }
  .gp.dim { opacity: .8; }
  .lbl { height: 26px; padding: 0 4px; border: 0; background: transparent; font-weight: 500; text-align: left; white-space: nowrap; }
  .lbl:hover { color: var(--link); background: transparent; }
  .lbl.on { color: var(--link); }
  .lbl.small { font-weight: 400; font-size: var(--t-small); }
  .lbl.dim { display: inline-flex; align-items: center; }
  .plus { color: var(--ink-muted); font-size: var(--t-caption); }
  .spacer { flex: 1; }
  .tag { font-size: var(--t-caption); border: 1px solid var(--border); border-radius: 3px; padding: 0 4px; color: var(--ink-muted); line-height: 16px; white-space: nowrap; }
  .tag.red { color: var(--accent); border-color: var(--accent); font-weight: 600; }
  .tag.dot { border-style: dotted; }
  .tiny { font-size: var(--t-caption); color: var(--ink-muted); white-space: nowrap; }
  .exp { height: 22px; padding: 0 6px; font-size: var(--t-caption); border: 0; background: transparent; color: var(--ink-muted); }
  .exp.on, .exp:hover { color: var(--link); background: transparent; }
  .sub { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; padding: 0 4px 2px 26px; }
  .seg, .segs { display: inline-flex; border: 1px solid var(--border); border-radius: 5px; overflow: hidden; }
  .seg button, .segs button { height: 22px; padding: 0 7px; border: 0; border-radius: 0; background: var(--bg-field); font-size: var(--t-caption); }
  .seg button + button, .segs button + button, .seg .n + button { border-left: 1px solid var(--border); }
  .seg .n { padding: 0 7px; line-height: 22px; font-family: var(--font-mono); font-size: var(--t-small); border-left: 1px solid var(--border); }
  /* option labels can be long ("String (string_top) + String (string_bottom)"): grow, don't clip */
  .segs { max-width: 100%; }
  .segs button { height: auto; min-height: 22px; padding: 2px 7px; line-height: 16px; white-space: normal; text-align: left; }
  .segs button.on { background: var(--sel-bg); color: var(--ink); box-shadow: inset 0 0 0 1px var(--sel-border); }
  .card { margin: 0 0 4px 22px; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 6px 8px; background: var(--bg-field); display: flex; flex-direction: column; gap: 5px; font-size: var(--t-small); }
  .wrap { flex-wrap: wrap; }
  .alt { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; border: 1px solid var(--border); border-radius: 5px; padding: 3px 5px; background: var(--bg-panel); }
  .or { font-size: var(--t-caption); color: var(--ink-muted); padding-left: 14px; }
  .ec { display: inline-flex; align-items: center; gap: 3px; border: 1px solid var(--border); border-radius: 12px; padding: 0 2px 0 8px; height: 24px; background: var(--bg-field); font-size: var(--t-small); }
  .ec.edit { padding-left: 2px; }
  .ec select { height: 20px; font-size: var(--t-caption); padding: 0 2px; border: 0; background: transparent; }
  .idin { height: 20px; width: 90px; font-family: var(--font-mono); font-size: var(--t-caption); border: 0; border-left: 1px solid var(--border); border-radius: 0; background: transparent; padding: 0 4px; }
  .x { height: 18px; width: 18px; padding: 0; border: 0; background: transparent; color: var(--ink-muted); font-size: 12px; }
  .add { height: 22px; font-size: var(--t-caption); padding: 0 4px; border-style: dashed; background: transparent; width: auto; }
  .lnk { height: 22px; font-size: var(--t-caption); border-style: dashed; background: transparent; }
  .arealink { height: 22px; border: 0; background: transparent; color: var(--link); padding: 0 2px; white-space: nowrap; font-size: var(--t-caption); }
  .arealink:hover { text-decoration: underline; background: transparent; }
  .danger { height: 22px; font-size: var(--t-caption); color: var(--status-danger); border-color: var(--status-danger); background: transparent; }
  .addpart { width: 100%; border-style: dashed; background: transparent; font-size: var(--t-small); color: var(--ink-muted); }
  .rec { border-top: 1px dashed var(--border); padding-top: 4px; margin-top: 2px; display: flex; flex-direction: column; gap: 4px; font-size: var(--t-small); }
  .rec summary { cursor: pointer; }
  .chips { display: flex; flex-wrap: wrap; gap: 3px; }
  .tg { display: inline-flex; align-items: center; gap: 4px; height: 22px; padding: 0 8px; border-radius: 11px; font-size: var(--t-caption); background: var(--bg-field); }
  .tg.on { background: var(--sel-bg); color: var(--ink); border-color: var(--sel-border); }
  .tg .rk { font-family: var(--font-mono); font-size: 10px; opacity: .8; }
  .newarea { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; padding: 6px; border: 1px dashed var(--border); border-radius: var(--radius-md); }
  .newarea label { display: inline-flex; gap: 4px; align-items: center; font-size: var(--t-small); }
  .err { color: var(--status-danger); }
</style>
