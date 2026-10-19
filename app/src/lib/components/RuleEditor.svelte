<script lang="ts">
  // Edit one rule: which glyphs of the part and of its base it covers, and
  // the gap. The canvas previews the rule live (overlay or one combination).
  import { app } from '$lib/state.svelte';
  import { editor } from '$lib/editor.svelte';
  import { elementLabel, elementNames } from '$lib/shape';
  import { applyRuleEdit, combosOf, entriesOf, isOtherwise, presetsFor, shadowedBy, stepFor } from '$lib/rules';
  import Glyph from './Glyph.svelte';
  import GlyphPopover from './GlyphPopover.svelte';

  let re = $derived(editor.ruleEdit!);
  let layout = $derived(app.design!.layouts.find((l) => l.name === editor.layoutName)!);
  let rel = $derived(layout.relationships[re.relIndex]);
  let el = $derived(editor.elements.find((e) => e.name === editor.selected)!);
  const areaLabel = (a: string) => app.areaLabel(a);
  let label = $derived(elementLabel(layout, el.name, areaLabel));
  let baseName = $derived(editor.baseName(el.name, rel));
  let baseEl = $derived(baseName ? editor.elements.find((e) => e.name === baseName) ?? null : null);
  let baseArea = $derived(baseEl?.area ?? (rel.base && rel.base !== 'prev' ? elementNames(layout).find((x) => x.name === rel.base)?.area ?? null : null));
  let baseLabel = $derived(rel.base == null ? 'the page' : rel.base === 'prev' ? 'previous row' : elementLabel(layout, rel.base, areaLabel));
  let elemGlyphs = $derived(app.design!.areas[el.area].glyphs);
  let baseGlyphs = $derived(baseArea ? app.design!.areas[baseArea].glyphs : []);
  let showElem = $derived(elemGlyphs.length > 1);
  let showBase = $derived(baseGlyphs.length > 1 && !!rel.base && rel.base !== 'prev');

  // entries other than the one being edited, and where the edited one lands among them
  let entries = $derived(entriesOf(rel.gap));
  let others = $derived(entries.filter((_, i) => i !== re.entryIndex));
  let before = $derived(re.entryIndex != null && re.insertAt > re.entryIndex ? re.insertAt - 1 : re.insertAt);
  function shadow(side: 'elem' | 'base', g: string): number {
    const i = shadowedBy(others, before, side, g, side === 'elem' ? re.whenBase : re.whenElem);
    return i < 0 ? -1 : i + (re.entryIndex != null && i >= re.entryIndex ? 1 : 0) + 1;  // display number
  }
  let conflicts = $derived.by(() => {
    const out: { side: 'elem' | 'base'; g: string; n: number }[] = [];
    for (const g of re.whenElem) { const n = shadow('elem', g); if (n > 0) out.push({ side: 'elem', g, n }); }
    for (const g of re.whenBase) { const n = shadow('base', g); if (n > 0) out.push({ side: 'base', g, n }); }
    return out;
  });
  let firstConflict = $derived(conflicts.length ? Math.min(...conflicts.map((c) => c.n)) : 0);
  let isOther = $derived(!re.whenElem.length && !re.whenBase.length);
  let otherwiseExists = $derived(others.some(isOtherwise));

  function toggle(side: 'elem' | 'base', g: string) {
    const arr = side === 'elem' ? re.whenElem : re.whenBase;
    const i = arr.indexOf(g);
    if (i < 0) arr.push(g); else arr.splice(i, 1);
    re.step = 0;
  }
  function setAll(side: 'elem' | 'base', glyphs: string[]) {
    if (side === 'elem') re.whenElem = [...glyphs]; else re.whenBase = [...glyphs];
    re.step = 0;
  }
  let search = $state('');
  let baseShown = $derived(search ? baseGlyphs.filter((g) => g.toLowerCase().includes(search.toLowerCase())) : baseGlyphs);
  let presets = $derived(presetsFor(baseGlyphs));

  let combos = $derived(combosOf(re, showElem ? elemGlyphs : editor.pinned[el.name] ? [editor.pinned[el.name]] : [], showBase ? baseGlyphs : baseName && editor.pinned[baseName] ? [editor.pinned[baseName]] : []));
  function randomCombo() { re.step = Math.floor(Math.random() * combos.n); }
  /** Preview one exact glyph of a side (overlay off), keeping the other side's choice. */
  function preview(side: 'elem' | 'base', g: string) {
    re.overlay = false;
    re.step = stepFor(combos, side, g);
  }
  const canPreview = (side: 'elem' | 'base', g: string) => (side === 'elem' ? combos.elems : combos.bases).includes(g);
  const isShown = (side: 'elem' | 'base', g: string) => !re.overlay && combos.n > 1 && (side === 'elem' ? combos.shown.elem : combos.shown.base) === g;
  let menu = $state<{ side: 'elem' | 'base'; x: number; y: number } | null>(null);
  function openMenu(ev: MouseEvent, side: 'elem' | 'base') {
    if (menu?.side === side) { menu = null; return; }
    const r = (ev.currentTarget as HTMLElement).getBoundingClientRect();
    menu = { side, x: r.right, y: r.bottom };
  }
  function cellClick(ev: MouseEvent, side: 'elem' | 'base', g: string) {
    if (ev.shiftKey && canPreview(side, g)) { preview(side, g); return; }
    toggle(side, g);
  }
  let shownValue = $derived(Math.round(re.value + re.liveDelta));

  function confirm() {
    const edited = re.entryIndex == null ? 'new rule' : `rule ${re.entryIndex + 1}`;
    const snap = $state.snapshot(re);
    app.edit(`${layout.label ?? layout.name}: ${label} ${edited} (relative to ${baseLabel}) → ${snap.value}`, (d) => {
      d.layouts = applyRuleEdit(d, layout.name, snap).layouts;
    });
    editor.viewedRel = snap.relIndex;
    editor.ruleEdit = null;
  }
  function cancel() { editor.ruleEdit = null; }
  function onkey(e: KeyboardEvent) {
    const t = e.target as HTMLElement;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return;
    if (e.key === 'Enter') { e.preventDefault(); confirm(); }
  }
</script>

<svelte:window onkeydown={onkey} />

<div class="ed">
  <div class="row head">
    <h3 style="margin:0">{re.entryIndex == null ? 'New rule' : `Rule ${re.entryIndex + 1}`} · {label}</h3>
    <span class="spacer"></span>
    <button onclick={cancel}>Cancel</button>
    <button class="primary" onclick={confirm}>Confirm</button>
  </div>
  <div class="muted small">{editor.axis === 'y' ? 'Gap above' : 'Position'} relative to <b>{baseLabel}</b>{#if rel.base != null} ({rel.elem_edge ?? (editor.axis === 'y' ? 'top' : 'right')} edge to its {rel.base_edge ?? (editor.axis === 'y' ? 'bottom' : 'left')}){/if}.
    {#if isOther}This rule has no glyph condition: it is the <b>otherwise</b> row{#if otherwiseExists && re.entryIndex == null} (one already exists; tick a glyph to make this a specific rule){/if}.{:else}Tick the glyphs it applies to; an unticked side means any glyph.{/if}</div>

  {#if showElem}
    <div class="grid-head"><span>when <b>{label}</b> is</span>{#if !re.whenElem.length}<span class="muted small">any (all {elemGlyphs.length})</span>{/if}<span class="spacer"></span>
      <button class="tiny" class:on={!re.whenElem.length} onclick={() => setAll('elem', [])}>any</button><button class="tiny" onclick={() => setAll('elem', elemGlyphs)}>all</button><button class="tiny" onclick={() => setAll('elem', [])}>none</button></div>
    <div class="grid" class:any={!re.whenElem.length}>
      {#each elemGlyphs as g (g)}
        {@const on = re.whenElem.includes(g)}
        {@const sh = on ? shadow('elem', g) : -1}
        <span class="cellwrap" class:shown={isShown('elem', g)}>
          <button class="cell" class:on class:shadow={sh > 0} title={sh > 0 ? `${g}: already caught by rule ${sh}, this rule will not reach it` : `${g} (shift-click to preview)`} onclick={(ev) => cellClick(ev, 'elem', g)}>
            <Glyph name={g} size={30} />{#if sh > 0}<span class="sn">{sh}</span>{/if}
          </button>
          {#if canPreview('elem', g)}<button class="eye" title="Preview {g} on the canvas" onclick={() => preview('elem', g)}>◉</button>{/if}
        </span>
      {/each}
    </div>
  {/if}
  {#if showBase}
    <div class="grid-head"><span>and <b>{baseLabel}</b> is</span>{#if !re.whenBase.length}<span class="muted small">any (all {baseGlyphs.length})</span>{/if}<span class="spacer"></span>
      <button class="tiny" class:on={!re.whenBase.length} onclick={() => setAll('base', [])}>any</button><button class="tiny" onclick={() => setAll('base', baseGlyphs)}>all</button>
      {#each presets as p}<button class="tiny" onclick={() => setAll('base', p.glyphs)}>{p.label}</button>{/each}
      {#if baseGlyphs.length > 24}<input class="search" placeholder="find…" bind:value={search} />{/if}</div>
    <div class="grid" class:any={!re.whenBase.length}>
      {#each baseShown as g (g)}
        {@const on = re.whenBase.includes(g)}
        {@const sh = on ? shadow('base', g) : -1}
        <span class="cellwrap" class:shown={isShown('base', g)}>
          <button class="cell" class:on class:shadow={sh > 0} title={sh > 0 ? `${g}: already caught by rule ${sh}` : `${g} (shift-click to preview)`} onclick={(ev) => cellClick(ev, 'base', g)}>
            <Glyph name={g} size={30} />{#if sh > 0}<span class="sn">{sh}</span>{/if}
          </button>
          {#if canPreview('base', g)}<button class="eye" title="Preview {g} on the canvas" onclick={() => preview('base', g)}>◉</button>{/if}
        </span>
      {/each}
    </div>
  {/if}

  {#if conflicts.length}
    <div class="conflict">
      <div>{conflicts.length} ticked {conflicts.length === 1 ? 'glyph is' : 'glyphs are'} already caught by an earlier rule (rule {firstConflict}{#if conflicts.some((c) => c.n !== firstConflict)} and later{/if}), so this rule would not reach {conflicts.length === 1 ? 'it' : 'them'}.</div>
      <div class="row wrap">
        <button class="tiny" onclick={() => (re.insertAt = firstConflict - 1)}>Move this rule above rule {firstConflict}</button>
        <button class="tiny" onclick={() => { for (const c of conflicts) toggle(c.side, c.g); }}>Untick {conflicts.length === 1 ? 'it' : 'them'}</button>
      </div>
    </div>
  {:else if re.entryIndex != null && re.insertAt !== re.entryIndex}
    <div class="muted small">Will move to position {re.insertAt + 1}. <button class="tiny" onclick={() => (re.insertAt = re.entryIndex!)}>Keep position {re.entryIndex + 1}</button></div>
  {/if}

  <div class="row gaprow">
    <label>gap <input type="number" value={shownValue} onchange={(e) => { re.value = +(e.target as HTMLInputElement).value; re.liveDelta = 0; }} /></label>
    <span class="muted small">{editor.axis === 'y' ? '+ overlaps the base, − leaves space' : ''}. Or drag {label} on the canvas.</span>
  </div>
  {#if combos.n > 1}
    <div class="row preview">
      <label><input type="checkbox" bind:checked={re.overlay} /> overlay all {combos.n} combinations</label>
      {#if !re.overlay}
        <span class="spacer"></span>
        <button class="tiny" onclick={() => (re.step -= 1)}>◀</button>
        <span class="small mono">{combos.k + 1}/{combos.n}</span>
        <button class="tiny" onclick={() => (re.step += 1)}>▶</button>
        <button class="tiny" title="Show a random combination" onclick={randomCombo}>random</button>
        <span class="shown">
          {#if combos.shown.elem}<button class="thumb" data-gpop-anchor title="Choose which {label} glyph to preview" onclick={(ev) => openMenu(ev, 'elem')}><Glyph name={combos.shown.elem} size={18} />{#if combos.elems.length > 1}<span class="dd">▾</span>{/if}</button>{/if}
          {#if combos.shown.elem && combos.shown.base}<span class="muted">·</span>{/if}
          {#if combos.shown.base}<button class="thumb" data-gpop-anchor title="Choose which {baseLabel} glyph to preview" onclick={(ev) => openMenu(ev, 'base')}><Glyph name={combos.shown.base} size={18} />{#if combos.bases.length > 1}<span class="dd">▾</span>{/if}</button>{/if}
        </span>
      {/if}
    </div>
  {/if}
  <div class="muted small">Enter confirms, Esc cancels. Confirming is one undo step.</div>
</div>
{#if menu}
  {@const side = menu.side}
  <GlyphPopover title="preview {side === 'elem' ? label : baseLabel} as" glyphs={side === 'elem' ? combos.elems : combos.bases}
    current={side === 'elem' ? combos.shown.elem : combos.shown.base} anchor={{ x: menu.x, y: menu.y }}
    onpick={(g) => { preview(side, g); menu = null; }} onclose={() => (menu = null)} />
{/if}

<style>
  .ed { display: flex; flex-direction: column; gap: var(--space-4); }
  .head { gap: 6px; }
  .spacer { flex: 1; }
  .small { font-size: var(--t-caption); }
  .tiny { height: 20px; padding: 0 6px; font-size: var(--t-caption); }
  .tiny.on { border-color: var(--link); color: var(--link); }
  .grid-head { display: flex; align-items: center; gap: 4px; font-size: var(--t-small); flex-wrap: wrap; }
  .search { height: 20px; width: 80px; font-size: var(--t-caption); }
  .grid { display: flex; flex-wrap: wrap; gap: 3px; max-height: 180px; overflow: auto; padding: 2px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-field); }
  .cellwrap { position: relative; display: inline-block; border-radius: 4px; }
  .cellwrap.shown { box-shadow: 0 0 0 2px var(--ink); }
  .cell { position: relative; width: 36px; height: 36px; padding: 2px; border: 1px solid transparent; background: transparent; border-radius: 4px; }
  .eye { position: absolute; left: -3px; bottom: -3px; width: 16px; height: 16px; padding: 0; border: 1px solid var(--border); border-radius: 50%; background: var(--bg-field); color: var(--ink-muted); font-size: 10px; line-height: 14px; display: none; }
  .cellwrap:hover .eye, .cellwrap.shown .eye { display: block; }
  .cellwrap.shown .eye { color: var(--ink); border-color: var(--ink); }
  .eye:hover { color: var(--link); border-color: var(--link); }
  .cell:hover { border-color: var(--border); }
  .cell.on { border-color: var(--link); background: var(--sel-bg); }
  .grid.any .cell { border-color: var(--sel-bg); background: var(--sel-bg); opacity: .75; }
  .grid.any .cell:hover { opacity: 1; border-color: var(--link); }
  .cell.shadow { border-style: dashed; border-color: var(--status-draft); background: transparent; opacity: .7; }
  .sn { position: absolute; top: -4px; right: -4px; min-width: 14px; height: 14px; border-radius: 7px; background: var(--status-draft); color: var(--on-accent); font-size: 10px; line-height: 14px; text-align: center; padding: 0 3px; }
  .conflict { border: 1px solid var(--status-draft); border-radius: var(--radius-md); padding: 6px 8px; font-size: var(--t-caption); display: flex; flex-direction: column; gap: 4px; }
  .gaprow { gap: var(--space-4); align-items: center; }
  .gaprow input { width: 70px; }
  .preview { gap: 4px; align-items: center; border-top: 1px dashed var(--border); padding-top: var(--space-4); }
  .mono { font-family: var(--font-mono); }
  .shown { display: inline-flex; align-items: center; gap: 3px; }
  .thumb { display: inline-flex; align-items: center; gap: 2px; height: 26px; padding: 0 5px; border: 1px solid var(--border); border-radius: 4px; background: var(--bg-field); }
  .thumb:hover { border-color: var(--link); }
  .dd { font-size: 9px; color: var(--ink-muted); }
  .wrap { flex-wrap: wrap; }
</style>
