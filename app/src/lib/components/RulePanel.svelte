<script lang="ts">
  // Spacing rules of the selected part: the chain of bases (in search order)
  // and the rule rows of the viewed base, as glyph sentences.
  import { phone } from '$lib/phone.svelte';   // a phone: no HTML drag (iOS starts one on a long press)
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import { editor, gapEntryIndex } from '$lib/editor.svelte';
  import { elementLabel, elementNames } from '$lib/shape';
  import { chainFor, entriesOf, isOtherwise, normalizeGap, uncovered } from '$lib/rules';
  import type { Layout, Relationship } from '$lib/api';
  import Glyph from './Glyph.svelte';

  let layout = $derived(editor.layout!);
  let el = $derived(editor.elements.find((e) => e.name === editor.selected)!);
  const areaLabel = (a: string) => app.areaLabel(a);
  let label = $derived(elementLabel(layout, el.name, areaLabel));
  let axis = $derived(editor.axis);
  let chain = $derived(chainFor(layout, el, axis));
  let active = $derived(editor.activeRel(axis, el.name)?.index ?? null);
  let viewed = $derived(editor.viewedRel != null && chain.some((c) => c.index === editor.viewedRel) ? editor.viewedRel : active ?? chain[0]?.index ?? null);
  let rel = $derived(viewed != null ? layout.relationships[viewed] : null);
  let entries = $derived(rel ? entriesOf(rel.gap) : []);
  let baseName = $derived(rel ? editor.baseName(el.name, rel) : null);
  let baseEl = $derived(baseName ? editor.elements.find((e) => e.name === baseName) ?? null : null);
  let baseAreaName = $derived(baseEl?.area ?? (rel?.base && rel.base !== 'prev' ? elementNames(layout).find((x) => x.name === rel!.base)?.area ?? null : null));
  let elemGlyphs = $derived(app.design!.areas[el.area].glyphs);
  let baseGlyphs = $derived(baseAreaName ? app.design!.areas[baseAreaName].glyphs : []);
  let showElem = $derived(elemGlyphs.length > 1);
  let showBase = $derived(baseGlyphs.length > 1 && !!rel?.base && rel.base !== 'prev');
  let elemGlyph = $derived(editor.pinned[el.name] ?? null);
  let baseGlyph = $derived(baseName ? editor.pinned[baseName] ?? null : null);
  let activeEntry = $derived(rel ? gapEntryIndex(rel.gap, baseGlyph, elemGlyph) : -1);
  let otherwiseIdx = $derived(entries.findIndex(isOtherwise));
  // coverage is checked on the side the rows key on (the base when only base conditions are used)
  let keySide = $derived<'elem' | 'base'>(showBase && entries.some((e) => e.when_base?.length) && !entries.some((e) => e.when_elem?.length) ? 'base' : 'elem');
  let missing = $derived(rel ? uncovered(entries, keySide, keySide === 'elem' ? elemGlyphs : baseGlyphs) : []);
  let missingLabel = $derived(keySide === 'elem' ? label : rel ? pillLabel(rel) : '');

  function edit(label: string, fn: (l: Layout) => void) {
    app.edit(`${layout.label ?? layout.name}: ${label}`, (d) => fn(d.layouts.find((x) => x.name === layout.name)!));
  }
  function pillLabel(r: Relationship) {
    if (r.base == null) return axis === 'y' ? `start ${typeof r.gap === 'number' ? r.gap : ''}` : `x ${typeof r.gap === 'number' ? r.gap : ''}`;
    if (r.base === 'prev') return 'previous row';
    return elementLabel(layout, r.base, areaLabel);
  }
  function basePresent(r: Relationship) {
    if (r.base == null) return true;
    if (r.base === 'prev') return el.instance > 1;
    return !!editor.baseName(el.name, r);
  }
  /** View a base's rows and make the preview word the situation where it applies. */
  function viewPill(index: number) {
    editor.viewedRel = index;
    editor.selectedArrow = `${axis}:${index}`;
    const pos = chain.findIndex((c) => c.index === index);
    for (const c of chain.slice(0, pos)) {
      const bn = editor.baseName(el.name, c.rel);
      if (!bn) continue;
      const be = editor.elements.find((e) => e.name === bn)!;
      const si = layout.slots.findIndex((s) => s.name === be.slot);
      if (layout.slots[si]?.optional && be.slot !== el.slot) editor.setChoice(si, null);
    }
    const r = layout.relationships[index];
    if (r.base && r.base !== 'prev' && !editor.baseName(el.name, r)) {
      const en = elementNames(layout).find((x) => x.name === r.base);
      const si = en ? layout.slots.findIndex((s) => s.name === en.slot) : -1;
      if (si >= 0) {
        const alt = layout.slots[si].alternatives.findIndex((a) => a.some((t) => (t.includes(':') ? t.split(':')[0] : t) === r.base));
        editor.setChoice(si, layout.slots[si].repeat ? [Math.max(0, alt)] : Math.max(0, alt));
      }
    }
  }
  let addOpen = $state(false);
  let addOptions = $derived.by(() => {
    const used = new Set(chain.map((c) => c.rel.base ?? null));
    const opts: { base: string | null; label: string; note: string }[] = [];
    for (const e of elementNames(layout)) {
      if (e.name === el.el) continue;
      opts.push({ base: e.name, label: elementLabel(layout, e.name, areaLabel), note: used.has(e.name) ? 'in the chain' : '' });
    }
    if (layout.slots.find((s) => s.name === el.slot)?.repeat) opts.push({ base: 'prev', label: 'previous row', note: used.has('prev') ? 'in the chain' : '' });
    opts.push({ base: null, label: axis === 'y' ? 'start height (page)' : 'x on the page', note: used.has(null) ? 'in the chain' : '' });
    return opts;
  });
  function addBase(base: string | null) {
    addOpen = false;
    const existing = chain.find((c) => (c.rel.base ?? null) === base);
    if (existing) { viewPill(existing.index); return; }
    const r: Relationship = { axis, elem: el.el, base, gap: 0 };
    if (base != null) { r.base_edge = axis === 'y' ? 'bottom' : 'left'; r.elem_edge = axis === 'y' ? 'top' : 'left'; }
    let at = chain.find((c) => c.rel.base == null)?.index ?? (chain.length ? chain[chain.length - 1].index + 1 : layout.relationships.length);
    edit(`${label}: relative to ${base == null ? 'the page' : pillLabel(r)}`, (l) => { l.relationships.splice(at, 0, r); });
    editor.viewedRel = at;
  }
  let dragPill = $state<number | null>(null);
  function dropPill(to: number) {
    if (dragPill == null || dragPill === to) return;
    const from = dragPill; dragPill = null;
    edit(`${label}: reorder bases`, (l) => { const [r] = l.relationships.splice(from, 1); l.relationships.splice(to > from ? to - 1 : to, 0, r); });
    editor.viewedRel = to > from ? to - 1 : to;
  }
  function removeViewed() {
    if (viewed == null || !rel) return;
    edit(`${label}: remove "relative to ${pillLabel(rel)}"`, (l) => { l.relationships.splice(viewed!, 1); });
    editor.viewedRel = null;
  }
  function setEdge(key: 'base_edge' | 'elem_edge', v: string) {
    if (viewed == null) return;
    edit(`${label}: ${key.replace('_', ' ')} ${v}`, (l) => { l.relationships[viewed!][key] = v; });
  }
  function setValue(i: number, v: number) {
    if (viewed == null) return;
    edit(`${label}: rule ${i + 1} ${entries[i].value} → ${v}`, (l) => { const e = entriesOf(l.relationships[viewed!].gap).map((x) => ({ ...x })); e[i] = { ...e[i], value: v }; l.relationships[viewed!].gap = normalizeGap(e); });
  }
  let dragRow = $state<number | null>(null);
  function dropRow(to: number) {
    if (dragRow == null || viewed == null || dragRow === to) return;
    const from = dragRow; dragRow = null;
    edit(`${label}: move rule ${from + 1} to ${to + 1}`, (l) => {
      const e = entriesOf(l.relationships[viewed!].gap).map((x) => ({ ...x }));
      const [x] = e.splice(from, 1); e.splice(to > from ? to - 1 : to, 0, x);
      l.relationships[viewed!].gap = normalizeGap(e);
    });
  }
  function addOtherwise() {
    if (viewed == null) return;
    edit(`${label}: add otherwise`, (l) => { const e = entriesOf(l.relationships[viewed!].gap).map((x) => ({ ...x })); e.push({ value: e.at(-1)?.value ?? 0 }); l.relationships[viewed!].gap = normalizeGap(e); });
  }
  function removeEntry(i: number) {
    if (viewed == null) return;
    edit(`${label}: remove rule ${i + 1}`, (l) => { const e = entriesOf(l.relationships[viewed!].gap).map((x) => ({ ...x })); e.splice(i, 1); l.relationships[viewed!].gap = e.length ? normalizeGap(e) : 0; });
  }
  function openEditor(entryIndex: number | null, preTick = false) {
    if (viewed == null || !rel) return;
    if (viewed !== active) viewPill(viewed);
    editor.openRule(axis, viewed, entryIndex, preTick && showElem && elemGlyph ? elemGlyph : null);
  }
  const EDGES = $derived(axis === 'y' ? ['top', 'bottom'] : ['left', 'right']);
</script>

<div class="rp">
  <div class="tabs">
    <button class="tab" class:on={axis === 'y'} onclick={() => { editor.axis = 'y'; editor.viewedRel = null; }}><I.Vertical size={14} /> Vertical</button>
    <button class="tab" class:on={axis === 'x'} onclick={() => { editor.axis = 'x'; editor.viewedRel = null; }}><I.Horizontal size={14} /> Horizontal</button>
    <label class="elsegaps" title="Draw the else entries as gray dashed arrows on the canvas: the gap this part gets in words without the bases before them. Hover an else pill to see just its arrow.">
      <input type="checkbox" bind:checked={editor.showElse} /> <svg width="16" height="8" aria-hidden="true"><line x1="0" x2="16" y1="4" y2="4" /></svg> else gaps
    </label>
  </div>

  <div class="chain">
    <span class="muted">{axis === 'y' ? 'gap above, relative to' : 'position, relative to'}</span>
    {#each chain as c, k (c.index)}
      {#if k > 0}<span class="else">else</span>{/if}
      <button class="opt" class:active={c.index === active} class:view={c.index === viewed} class:absent={!basePresent(c.rel)}
        onpointerenter={() => (editor.hoverRel = c.index)} onpointerleave={() => { if (editor.hoverRel === c.index) editor.hoverRel = null; }}
        draggable={!phone.on} ondragstart={() => (dragPill = c.index)} ondragover={(e) => e.preventDefault()} ondrop={() => dropPill(c.index)}
        title={c.index === active ? 'In effect for the preview word' : basePresent(c.rel) ? 'Not in effect: an earlier base wins. Click to look at its rules (the preview drops the parts before it).' : 'Not in effect: this part is not in the word. Click to add it to the preview.'}
        onclick={() => viewPill(c.index)}>{#if c.index === active}<I.Current size={12} />{/if}{pillLabel(c.rel)}</button>
    {/each}
    <span class="addwrap">
      <button class="opt add" onclick={() => (addOpen = !addOpen)} aria-label="Add a base"><I.Plus size={14} /><I.Dropdown size={12} /></button>
      {#if addOpen}
        <div class="menu">
          <div class="muted">relative to…</div>
          {#each addOptions as o}<button class="mi" onclick={() => addBase(o.base)}>{o.label} <span class="muted">{o.note}</span></button>{/each}
        </div>
      {/if}
    </span>
  </div>
  {#if chain.length === 0}
    <p class="muted">No {axis === 'y' ? 'vertical' : 'horizontal'} rule yet: this part is not placed. Add a base with <I.Plus class="inl" aria-label="+" /> or drag a ○ handle on the canvas.</p>
  {:else if rel}
    <div class="sentence muted">
      {#if rel.base == null}
        <span class="em-me" onpointerenter={() => (editor.hoverEdge = { id: `${axis}:${viewed}`, side: 'me' })} onpointerleave={() => (editor.hoverEdge = null)} role="note">{label}'s {axis === 'y' ? 'bottom' : 'left'} edge</span> sits at {axis === 'y' ? 'height' : 'x'} = gap
      {:else}
        <span class="em-me" onpointerenter={() => (editor.hoverEdge = { id: `${axis}:${viewed}`, side: 'me' })} onpointerleave={() => (editor.hoverEdge = null)} role="note">{label}'s
        {#if editor.advanced}<select value={rel.elem_edge ?? (axis === 'y' ? 'top' : 'right')} onchange={(e) => setEdge('elem_edge', (e.target as HTMLSelectElement).value)}>{#each EDGES as ed}<option value={ed}>{ed}</option>{/each}</select>{:else}{rel.elem_edge ?? (axis === 'y' ? 'top' : 'right')}{/if}
        edge</span> sits at <span class="em-base" onpointerenter={() => (editor.hoverEdge = { id: `${axis}:${viewed}`, side: 'base' })} onpointerleave={() => (editor.hoverEdge = null)} role="note">{pillLabel(rel)}'s
        {#if editor.advanced}<select value={rel.base_edge ?? (axis === 'y' ? 'bottom' : 'left')} onchange={(e) => setEdge('base_edge', (e.target as HTMLSelectElement).value)}>{#each EDGES as ed}<option value={ed}>{ed}</option>{/each}</select>{:else}{rel.base_edge ?? (axis === 'y' ? 'bottom' : 'left')}{/if}</span>
        + gap{#if axis === 'y'} <span title="Positive pulls it up into the base's box; negative leaves space">(+ overlaps, − leaves space)</span>{/if}
      {/if}
      <button class="tiny" title="Remove this base from the chain" onclick={removeViewed}>remove <I.Close size={12} /></button>
    </div>
    {#if viewed !== active}
      <div class="info">Viewing <b>{pillLabel(rel)}</b>: not in effect for the current word. <button class="tiny" onclick={() => viewPill(viewed!)}>show the word it applies to</button></div>
    {/if}

    <div class="rules">
      <div class="rhead"><span></span><span></span><span>when {showElem ? label : ''}{showElem && showBase ? ' · ' : ''}{showBase ? pillLabel(rel) : ''}{!showElem && !showBase ? 'always' : ' is'}</span><span></span><span>gap</span></div>
      {#each entries as e, i (i)}
        {@const other = isOtherwise(e)}
        <div class="rr" class:on={i === activeEntry} class:other
          draggable={!other && !phone.on} ondragstart={() => (dragRow = i)} ondragover={(ev) => { if (!other || dragRow != null) ev.preventDefault(); }} ondrop={() => dropRow(other ? i : i)}
          role="button" tabindex="0" onclick={() => openEditor(i)} onkeydown={(ev) => { if (ev.key === 'Enter') openEditor(i); }}>
          <span class="hdl">{#if other}<I.Otherwise size={14} />{:else}<I.Grip size={14} />{/if}</span>
          <span class="rn">{other ? '–' : i + 1}</span>
          <span class="chips">
            {#if other}
              otherwise {#if missing.length === 0 && (showElem || showBase)}<span class="tiny muted">all covered <I.Check size={12} /></span>{/if}
            {:else}
              {#if showElem}{#if e.when_elem?.length}{#each e.when_elem as g}<span class="chip"><Glyph name={g} size={16} /></span>{/each}{:else}<span class="any">any</span>{/if}{/if}
              {#if showElem && showBase}<span class="muted">·</span>{/if}
              {#if showBase}{#if e.when_base?.length}{#each e.when_base as g}<span class="chip"><Glyph name={g} size={16} /></span>{/each}{:else}<span class="any">any</span>{/if}{/if}
            {/if}
          </span>
          <span class="arrow" class:dot={i === activeEntry}>{#if i === activeEntry}<I.Current size={12} />{/if}<I.Gives size={12} /></span>
          <input type="number" value={e.value} onclick={(ev) => ev.stopPropagation()} onchange={(ev) => setValue(i, +(ev.target as HTMLInputElement).value)} />
          {#if !other || entries.length > 1}<button class="x" title="Remove this row" onclick={(ev) => { ev.stopPropagation(); removeEntry(i); }} aria-label="Remove this row"><I.Close size={14} /></button>{/if}
        </div>
      {/each}
      {#if otherwiseIdx < 0}
        <div class="rr other warn"><span class="hdl"><I.Otherwise size={14} /></span><span class="rn">–</span>
          <span class="chips">otherwise: none set{#if missing.length} · {missing.length} {missingLabel} not placed: {#each missing as g (g)}<span class="chip" title={g}><Glyph name={g} size={16} /></span>{/each}{/if}</span>
          <span></span><button class="tiny" onclick={addOtherwise}>+ set</button></div>
      {:else if missing.length}
        <div class="chips warn tiny">{missing.length} {missingLabel} fall through to otherwise: {#each missing as g (g)}<span class="chip" title={g}><Glyph name={g} size={16} /></span>{/each}</div>
      {/if}
    </div>
    <div class="row">
      <button onclick={() => openEditor(null)}>+ new rule</button>
      {#if showElem && elemGlyph}<button class="lnk" onclick={() => openEditor(null, true)}>+ new rule for <Glyph name={elemGlyph} size={16} /></button>{/if}
    </div>
  {/if}
</div>

<style>
  .rp { display: flex; flex-direction: column; gap: var(--space-4); }
  .spacer { flex: 1; }
  .tabs { display: flex; align-items: flex-end; border-bottom: 1px solid var(--border); gap: 4px; }
  .elsegaps { margin-left: auto; align-self: center; display: inline-flex; align-items: center; gap: 4px; font-size: var(--t-small); color: var(--ink-muted); white-space: nowrap; }
  .elsegaps line { stroke: var(--ink-muted); stroke-width: 1.5; stroke-dasharray: 3 2; }
  .tab { border-bottom: 0; border-radius: 6px 6px 0 0; height: 26px; }
  .tab.on { background: var(--bg-field); position: relative; top: 1px; }
  .chain { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
  .opt { height: var(--control-sm); padding: 0 var(--space-4); border-color: var(--border); font-size: var(--t-small); background: var(--bg-field); }
  .opt.active { border-color: var(--sel-border); color: var(--ink); background: var(--sel-bg); }
  .opt.view { box-shadow: 0 0 0 2px var(--ink); }
  .opt.absent { border-style: dashed; color: var(--ink-muted); }
  .opt.add { border-style: dashed; color: var(--ink-muted); background: transparent; }
  .else { font-size: var(--t-caption); color: var(--ink-muted); }
  /* the two edges, highlighted in the colours of the canvas edge bars (a key, not a link) */
  .em-me, .em-base { color: var(--ink); border-radius: 2px; padding: 0 2px; }
  .em-me { background: color-mix(in srgb, var(--ov-active) 22%, transparent); }
  .em-base { background: color-mix(in srgb, var(--ov-area) 22%, transparent); }
  .addwrap { position: relative; }
  .menu { position: absolute; z-index: 20; top: 100%; right: 0; margin-top: 4px; min-width: 220px; background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: var(--shadow-float); padding: 4px; display: flex; flex-direction: column; }
  .mi { text-align: left; border: 0; background: transparent; }
  .mi:hover { background: var(--bg-hover); }
  .sentence { font-size: var(--t-caption); display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  .sentence select { height: 20px; font-size: var(--t-caption); padding: 0 2px; }
  .info { font-size: var(--t-caption); border: 1px dashed var(--border); border-radius: var(--radius-md); padding: 4px 8px; color: var(--ink-muted); }
  .tiny { height: 20px; padding: 0 6px; font-size: var(--t-caption); }
  .rules { display: flex; flex-direction: column; gap: 4px; }
  .rhead, .rr { display: grid; grid-template-columns: 14px 20px 1fr 34px 62px 18px; gap: 4px; align-items: center; }
  .rhead { font-size: var(--t-caption); color: var(--ink-muted); padding: 0 6px; }
  .rr { border: 1px solid var(--border); border-radius: var(--radius-md); padding: 3px 6px; background: var(--bg-field); cursor: pointer; }
  .rr:hover { border-color: var(--link); }
  .rr.on { border-color: var(--link); background: var(--sel-bg); }
  .rr.other { background: var(--bg-panel); }
  .rr.warn { border-style: dashed; color: var(--status-draft); }
  .hdl { display: inline-flex; justify-content: center; color: var(--ink-muted); cursor: grab; }
  .rn { display: inline-flex; width: 19px; height: 19px; border-radius: 50%; border: 1px solid var(--border); font-size: var(--t-caption); align-items: center; justify-content: center; font-family: var(--font-mono); }
  .rr.on .rn { border-color: var(--link); color: var(--link); }
  .chips { display: flex; flex-wrap: wrap; gap: 3px; align-items: center; min-width: 0; }
  .chip { display: inline-flex; padding: 1px; border: 1px solid var(--border); border-radius: 3px; background: var(--bg-field); }
  .any { font-size: var(--t-caption); color: var(--ink-muted); border: 1px dashed var(--border); border-radius: 10px; padding: 0 6px; }
  .arrow { display: inline-flex; justify-content: flex-end; align-items: center; gap: 2px; color: var(--ink-muted); }
  .arrow.dot { color: var(--link); }
  .rr input { width: 62px; height: 24px; }
  .x { height: 18px; width: 18px; padding: 0; border: 0; background: transparent; color: var(--ink-muted); }
  .lnk { display: inline-flex; align-items: center; gap: 4px; border-style: dashed; }
  .warn { color: var(--status-draft); }
  /* a phone: the small buttons at a finger's size */
  @media (max-width: 759.98px) {
    .tiny { height: var(--control-sm); }
    .x { height: var(--control-sm); width: var(--control-sm); }
  }
</style>
