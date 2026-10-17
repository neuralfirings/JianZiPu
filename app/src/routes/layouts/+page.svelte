<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { api, type Design, type Layout, type Relationship } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { editor, bumpGap, gapValue, gapEntryIndex } from '$lib/editor.svelte';
  import { elementLabel, anchorNames, elementNames } from '$lib/shape';
  import { applyRuleEdit, combosOf, entriesOf } from '$lib/rules';
  import WordCanvas, { type Arrow, type Edge } from '$lib/components/WordCanvas.svelte';
  import CenterPanel from '$lib/components/CenterPanel.svelte';
  import TestStrip from '$lib/components/TestStrip.svelte';
  import GlyphTray from '$lib/components/GlyphTray.svelte';
  import RulePanel from '$lib/components/RulePanel.svelte';
  import RuleEditor from '$lib/components/RuleEditor.svelte';
  import StructurePanel from '$lib/components/StructurePanel.svelte';
  import WordTypesPanel from '$lib/components/WordTypesPanel.svelte';
  import PageCenterPanel from '$lib/components/PageCenterPanel.svelte';
  import FontBudgetPanel from '$lib/components/FontBudgetPanel.svelte';
  import Panel from '$lib/components/Panel.svelte';
  import PanelDock, { type Meta } from '$lib/components/PanelDock.svelte';
  import { panels, DOCK_LABEL, type Dock, type PanelId } from '$lib/panels.svelte';

  const d = $derived(app.design!);
  let canvasWidth = $state(560);
  let wrapH = $state(0);
  let canvasEl: WordCanvas;
  let status = $state<string>('');

  // ---- rule editing mode: the design previewed is the one with the edit applied,
  // and the glyphs shown are the combination the editor picked
  let editing = $derived(editor.ruleEdit);
  let editBase = $derived.by(() => {
    const re = editing; if (!re || !editor.selected || !editor.layout) return null;
    return editor.baseName(editor.selected, editor.layout.relationships[re.relIndex]);
  });
  let editCombos = $derived.by(() => {
    const re = editing; if (!re || !editor.selected) return null;
    const side = (name: string | null) => {
      if (!name) return [];
      const e = editor.elements.find((x) => x.name === name);
      const glyphs = e ? d.areas[e.area].glyphs : [];
      return glyphs.length > 1 ? glyphs : editor.pinned[name] ? [editor.pinned[name]] : [];
    };
    return combosOf(re, side(editor.selected), side(editBase));
  });
  let effPinned = $derived.by(() => {
    const c = editCombos; if (!c || !editor.selected) return editor.pinned;
    const out = { ...editor.pinned };
    if (c.shown.elem) out[editor.selected] = c.shown.elem;
    if (editBase && c.shown.base) out[editBase] = c.shown.base;
    return out;
  });
  let overlay = $derived.by(() => {
    const re = editing, c = editCombos;
    if (!re || !c || !re.overlay || c.n <= 1 || !editor.selected) return {};
    const out: Record<string, string[]> = {};
    if (c.elems.length > 1) out[editor.selected] = c.elems;
    if (editBase && c.bases.length > 1) out[editBase] = c.bases;
    return out;
  });

  onMount(() => {
    panels.load();
    if (page.url.searchParams.get('budget') === '1') panels.setFolded('budget', false);
    const onResize = () => panels.syncMode();
    window.addEventListener('resize', onResize);
    window.addEventListener('pointermove', dragMove);
    window.addEventListener('pointerup', dragUp);
    return () => { window.removeEventListener('resize', onResize); window.removeEventListener('pointermove', dragMove); window.removeEventListener('pointerup', dragUp); };
  });
  onMount(async () => {
    const want = page.url.searchParams.get('layout');
    const word = page.url.searchParams.get('word');
    if (word) {
      const r = await api.words(app.design!, [word]);
      const piece = r.ok ? r.words[0]?.pieces.find((p) => p.layout) : null;
      if (piece) { editor.loadWord(piece); return; }
    }
    if (want && d.layouts.some((l) => l.name === want)) editor.setLayout(want);
    else if (!editor.layout) editor.setLayout(d.layouts[0]?.name ?? '');
    else editor.syncChoice();
  });

  $effect(() => { void app.design; if (editor.layoutName && !app.design?.layouts.some((l) => l.name === editor.layoutName)) editor.setLayout(app.design?.layouts[0]?.name ?? ''); else editor.syncChoice(); });

  // resolve (debounced, latest wins)
  let seq = 0, timer: ReturnType<typeof setTimeout> | null = null;
  $effect(() => {
    const re = editor.ruleEdit ? $state.snapshot(editor.ruleEdit) : null;
    const name = editor.layoutName, choice = $state.snapshot(editor.choice), pinned = $state.snapshot(effPinned);
    const design = re && app.design ? applyRuleEdit(app.design, name, re, re.liveDelta) : editor.dragDesign ?? app.design;
    if (!design || !name || !choice.length) return;
    if (timer) clearTimeout(timer);
    const id = ++seq;
    editor.resolving = true;
    timer = setTimeout(async () => {
      try {
        const r = await api.resolve(design, name, choice, pinned);
        if (id === seq) { editor.resolved = r; editor.resolving = false; }
      } catch (e) { if (id === seq) { editor.resolving = false; status = (e as Error).message; } }
    }, 50);
  });

  let elements = $derived.by(() => {
    const res = editor.resolved;
    const anchors = anchorNames(editor.elements, d.areas);
    return editor.elements.map((e) => {
      const r = res?.elements.find((x) => x.name === e.name);
      return { name: e.name, area: e.area, glyph: effPinned[e.name], x: r?.x ?? null, y: r?.y ?? null, size: (r?.size ?? d.areas[e.area].size) as [number, number], error: !!res?.error && r?.x == null, anchor: anchors.has(e.name) };
    });
  });
  let selectedEl = $derived(editor.selected ? editor.elements.find((e) => e.name === editor.selected) ?? null : null);
  const areaLabel = (a: string) => app.areaLabel(a);

  /** Arrow geometry for one rule of the selected part, if both ends are drawable. */
  function arrowFor(axis: 'x' | 'y', index: number, rel: Relationship, me: (typeof elements)[number], ghost: boolean, k = 0): Arrow | null {
    if (me.x == null || me.y == null) return null;
    const bn = editor.baseName(me.name, rel);
    const base = bn ? elements.find((e) => e.name === bn) : null;
    const bg = bn ? effPinned[bn] ?? null : null;
    const eg = effPinned[me.name] ?? null;
    const v = gapValue(rel.gap, bg, eg);
    const ei = gapEntryIndex(rel.gap, bg, eg);
    const cond = ei >= 0 ? ` (rule ${entriesOf(rel.gap)[ei].when_base || entriesOf(rel.gap)[ei].when_elem ? ei + 1 : 'otherwise'})` : '';
    const who = rel.base == null ? '' : rel.base === 'prev' ? ' after previous row' : ` after ${elementLabel(editor.layout!, bn ?? rel.base, areaLabel)}`;
    const label = ghost ? `${v ?? '?'} after ${bn ?? rel.base}` : `${v ?? '?'}${cond}`;
    const title = ghost ? `${v ?? '?'}${who}: not in effect for this word. Click to look at its rules.` : `${v ?? '?'}${who}: in effect. Click to edit this rule; drag the part to change its gap.`;
    const id = `${axis}:${index}`;
    if (axis === 'y') {
      const myEdge = (rel.elem_edge ?? 'top') === 'top' ? me.y + me.size[1] : me.y;
      if (rel.base == null) return ghost ? null : { id, x: me.x + me.size[0] / 2, y1: 0, y2: me.y, label: `start ${Math.round(me.y)}`, axis, title };
      if (!base || base.x == null || base.y == null) return null;
      const baseEdge = (rel.base_edge ?? 'bottom') === 'bottom' ? base.y : base.y + base.size[1];
      const x = ghost ? Math.min(me.x, base.x) - 30 - 70 * k : Math.max(me.x, base.x) + Math.min(me.size[0], base.size[0]) / 2;
      return { id, x, y1: baseEdge, y2: myEdge, label, axis, ghost, title };
    }
    const myEdge = (rel.elem_edge ?? 'right') === 'right' ? me.x + me.size[0] : me.x;
    if (rel.base == null) return ghost ? null : { id, y: me.y + me.size[1] / 2, x1: 0, x2: me.x, label: `x ${Math.round(me.x)}`, axis, title };
    if (!base || base.x == null || base.y == null) return null;
    const baseEdge = (rel.base_edge ?? 'left') === 'left' ? base.x : base.x + base.size[0];
    const y = ghost ? Math.max(me.y + me.size[1], base.y + base.size[1]) + 30 + 50 * k : me.y + me.size[1] / 2;
    return { id, y, x1: baseEdge, x2: myEdge, label, axis, ghost, title };
  }

  let arrows = $derived.by(() => {
    const out: Arrow[] = [];
    const sel = editor.selected, l = editor.layout;
    if (!sel || !editor.resolved || !l) return out;
    if (editing) {
      const me = elements.find((e) => e.name === sel);
      const r = l.relationships[editing.relIndex];
      const a = me && r ? arrowFor(editing.axis, editing.relIndex, r, me, false) : null;
      if (a) out.push(a);
      return out;
    }
    const me = elements.find((e) => e.name === sel);
    const el = editor.elements.find((e) => e.name === sel);
    if (!me || !el) return out;
    for (const axis of ['y', 'x'] as const) {
      const active = editor.activeRel(axis, sel)?.index;
      let k = 0;
      l.relationships.forEach((r, i) => {
        if (r.axis !== axis || (r.elem !== el.el && r.elem !== el.slot)) return;
        const ghost = i !== active;
        const a = arrowFor(axis, i, r, me, ghost, k);
        if (a) { out.push(a); if (ghost) k++; }
      });
    }
    return out;
  });

  // ---- drag: edits the active rule of the dragged part (or the rule being edited)
  let dragFrom: { design: Design } | null = null;
  function applyDelta(design: Design, name: string, dx: number, dy: number): string | null {
    const l = design.layouts.find((x) => x.name === editor.layoutName)!;
    const axis = dx ? 'x' : 'y', delta = dx || dy;
    const a = editor.activeRel(axis, name);
    if (!a) return null;
    const rel = l.relationships[a.index];
    const bn = editor.baseName(name, rel);
    const baseGlyph = bn ? editor.pinned[bn] ?? null : null, elemGlyph = editor.pinned[name] ?? null;
    const before = gapValue(rel.gap, baseGlyph, elemGlyph);
    const ei = gapEntryIndex(rel.gap, baseGlyph, elemGlyph);
    const after = bumpGap(rel, delta, baseGlyph, elemGlyph);
    if (after == null) return null;
    const cond = ei < 0 ? '' : entriesOf(rel.gap)[ei].when_base || entriesOf(rel.gap)[ei].when_elem ? ` rule ${ei + 1}` : ' otherwise';
    const who = elementLabel(l, name, areaLabel);
    const what = axis === 'y' ? (rel.base == null ? 'start height' : `gap above${bn ? ` after ${elementLabel(l, bn, areaLabel)}` : rel.base === 'prev' ? ' after previous row' : ''}`) : (rel.base == null ? 'x position' : 'horizontal gap');
    return `${l.label ?? l.name}: ${what} of ${who}${cond} ${before} → ${after}`;
  }
  function commit(name: string, dx: number, dy: number) {
    let label = '';
    app.edit('drag', (dd) => { label = applyDelta(dd, name, dx, dy) ?? 'drag'; });
    if (app.undoStack.length) { app.undoStack[app.undoStack.length - 1].label = label; app.changes[app.changes.length - 1] = label; }
    status = label;
  }
  function ondrag(e: { name: string; dx: number; dy: number; phase: 'start' | 'move' | 'end' | 'cancel' }) {
    const re = editor.ruleEdit;
    if (re) {
      const delta = re.axis === 'y' ? e.dy : e.dx;
      if (e.phase === 'move') re.liveDelta = delta;
      else if (e.phase === 'end') { re.value = Math.round(re.value + delta); re.liveDelta = 0; }
      else re.liveDelta = 0;
      return;
    }
    if (e.phase === 'start') { dragFrom = { design: JSON.parse(JSON.stringify(app.design)) }; return; }
    if (e.phase === 'cancel') { editor.dragDesign = null; editor.dragLabel = null; dragFrom = null; return; }
    if (!dragFrom) return;
    if (e.phase === 'move') {
      if (!e.dx && !e.dy) { editor.dragDesign = null; editor.dragLabel = null; return; }
      const copy: Design = JSON.parse(JSON.stringify(dragFrom.design));
      const label = applyDelta(copy, e.name, e.dx, e.dy);
      if (label) { editor.dragDesign = copy; editor.dragLabel = label; } else editor.dragLabel = 'This part has no rule to change for the current glyphs';
      return;
    }
    editor.dragDesign = null; editor.dragLabel = null;
    if (e.dx || e.dy) commit(e.name, e.dx, e.dy);
    dragFrom = null;
  }
  function nudge(dx: number, dy: number) {
    const re = editor.ruleEdit;
    if (re) { re.value += re.axis === 'y' ? dy : dx; return; }
    if (editor.selected) commit(editor.selected, dx, dy);
  }
  /** Clicking the active arrow opens the rule in effect in the editor; a ghost arrow shows its rule in the panel. */
  function selectArrow(id: string | null) {
    if (editing) return;
    editor.selectedArrow = id;
    if (!id || !editor.selected) return;
    const [ax, i] = id.split(':');
    const axis = ax as 'x' | 'y', index = +i;
    editor.axis = axis;
    editor.viewedRel = index;
    if (editor.activeRel(axis, editor.selected)?.index !== index) return;
    const rel = editor.layout!.relationships[index];
    const bn = editor.baseName(editor.selected, rel);
    const ei = gapEntryIndex(rel.gap, bn ? editor.pinned[bn] ?? null : null, editor.pinned[editor.selected] ?? null);
    editor.openRule(axis, index, Array.isArray(rel.gap) ? (ei < 0 ? null : ei) : 0);
  }

  /** Does `from` (an element id or slot) end up placed relative to `to` on `axis`, through any rule? */
  function dependsOn(l: Layout, axis: 'x' | 'y', from: string, to: string, seen = new Set<string>()): boolean {
    if (from === to) return true;
    if (seen.has(from)) return false;
    seen.add(from);
    const names = elementNames(l);
    const mine = names.find((n) => n.name === from);
    for (const r of l.relationships) {
      if (r.axis !== axis || (r.elem !== from && r.elem !== mine?.slot)) continue;
      if (r.base == null || r.base === 'prev') continue;
      const b = r.base;
      const targets = names.filter((n) => n.name === b || n.slot === b).map((n) => n.name);
      if (targets.length === 0 && b === to) return true;
      for (const t of targets) if (dependsOn(l, axis, t, to, seen)) return true;
    }
    return false;
  }
  // ---- link: a handle dropped on another part's edge creates / re-attaches a rule
  function onlink(e: { name: string; edge: Edge; target: string; targetEdge: Edge }) {
    const l = editor.layout!;
    const me = editor.elements.find((x) => x.name === e.name)!, tgt = editor.elements.find((x) => x.name === e.target)!;
    const meR = elements.find((x) => x.name === e.name)!, tgR = elements.find((x) => x.name === e.target)!;
    if (meR.x == null || meR.y == null || tgR.x == null || tgR.y == null) return;
    const axis: 'x' | 'y' = e.edge === 'top' || e.edge === 'bottom' ? 'y' : 'x';
    const base = me.slot === tgt.slot && me.instance > 0 && tgt.instance === me.instance - 1 ? 'prev' : tgt.el;
    if (base !== 'prev' && dependsOn(l, axis, tgt.el, me.el)) {
      status = `Can't attach ${elementLabel(l, e.name, areaLabel)} to ${elementLabel(l, e.target, areaLabel)}: ${elementLabel(l, e.target, areaLabel)} is already placed relative to ${elementLabel(l, e.name, areaLabel)} (that would go round in a circle). Attach the other way round, or remove that rule first.`;
      return;
    }
    const edgeVal = (r: typeof meR, ed: Edge) => ed === 'top' ? r.y! + r.size[1] : ed === 'bottom' ? r.y! : ed === 'left' ? r.x! : r.x! + r.size[0];
    const gap = Math.round(edgeVal(meR, e.edge) - edgeVal(tgR, e.targetEdge));
    const who = elementLabel(l, e.name, areaLabel), whom = base === 'prev' ? 'the previous row' : elementLabel(l, e.target, areaLabel);
    app.edit(`${l.label ?? l.name}: attach ${who}'s ${e.edge} edge to ${whom}'s ${e.targetEdge} (gap ${gap})`, (dd) => {
      const rels = dd.layouts.find((x) => x.name === l.name)!.relationships;
      let active = editor.activeRel(axis, e.name)?.index ?? null;
      const existing = rels.findIndex((r) => r.axis === axis && r.elem === me.el && (r.base ?? null) === base);
      let rel: Relationship;
      if (existing >= 0) {
        rel = rels.splice(existing, 1)[0];
        if (active != null && existing < active) active--;
        if (!Array.isArray(rel.gap)) rel.gap = gap;
      } else rel = { axis, elem: me.el, base, gap };
      rel.base_edge = e.targetEdge; rel.elem_edge = e.edge;
      rels.splice(active ?? rels.length, 0, rel);
    });
    status = `${who} now attaches to ${whom} (${e.edge} → ${e.targetEdge}). Drag it to set the gap.`;
  }
  function removeRule(index: number) {
    const l = editor.layout!, r = l.relationships[index];
    if (!r) return;
    app.edit(`${l.label ?? l.name}: remove ${r.axis} rule of ${r.elem} after ${r.base ?? 'the page'}`, (dd) => { dd.layouts.find((x) => x.name === l.name)!.relationships.splice(index, 1); });
    editor.selectedArrow = null;
    editor.viewedRel = null;
    status = 'Rule removed (⌘Z to undo).';
  }
  function onkey(e: KeyboardEvent) {
    const t = e.target as HTMLElement;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return;
    const step = e.shiftKey ? 10 : 1;
    if (e.key === 'ArrowUp') { e.preventDefault(); nudge(0, step); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); nudge(0, -step); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); nudge(-step, 0); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); nudge(step, 0); }
    else if (e.key === 'Escape') { canvasEl?.cancelDrag(); if (panels.dragging) { panels.dragging = null; panels.over = null; } else if (editor.ruleEdit) editor.ruleEdit = null; else editor.selectedArrow = null; }
    else if ((e.key === 'Delete' || e.key === 'Backspace') && editor.selectedArrow && !editor.ruleEdit) { e.preventDefault(); removeRule(+editor.selectedArrow.split(':')[1]); }
    else if (e.key === 'b' && !e.metaKey && !e.ctrlKey) editor.showBoxes = !editor.showBoxes;
    else if (e.key === 'Tab' && editor.elements.length) {
      e.preventDefault();
      const i = editor.elements.findIndex((x) => x.name === editor.selected);
      const n = editor.elements.length;
      editor.select(editor.elements[((i < 0 ? 0 : i + (e.shiftKey ? -1 : 1)) + n) % n].name);
    }
  }

  // ---- panels: meta, drag between docks, dock resizing
  let perLayout = $derived(app.stats?.per_layout ?? {});
  let lastSel: string | null = null;
  $effect(() => {
    const sel = editor.selected;
    if (sel && sel !== lastSel && panels.isFolded('spacing')) panels.setFolded('spacing', false);
    lastSel = sel;
  });
  function meta(id: PanelId): Meta {
    const l = editor.layout;
    const label = selectedEl && l ? elementLabel(l, selectedEl.name, areaLabel) : null;
    switch (id) {
      case 'types': return { title: 'Word types', badge: d.layouts.length, summary: l ? (l.label ?? l.name) : '' };
      case 'structure': { const n = l?.slots.length ?? 0; const shown = l ? l.slots.filter((_, i) => editor.choice[i] != null).length : 0; return { title: 'Structure', badge: `${n} parts`, summary: `${shown} shown`, tag: editor.advanced ? 'Advanced' : '' }; }
      case 'pagecenter': return { title: 'Page center', summary: `${d.center.x}, ${d.center.y}` };
      case 'budget': { const st = app.stats; return { title: 'Font budget', badge: st?.skipped ? `${st.skipped} skipped` : null, warn: !!st?.skipped, summary: st ? `${st.rules} rules · ${(st.est_bytes / 1024).toFixed(0)} KB` : '' }; }
      case 'spacing': {
        if (!label || !selectedEl) return { title: 'Spacing', summary: 'click a part' };
        const a = editor.activeRel(editor.axis, selectedEl.name);
        const bn = a ? editor.baseName(selectedEl.name, a.rel) : null;
        const v = a ? gapValue(a.rel.gap, bn ? editor.pinned[bn] ?? null : null, editor.pinned[selectedEl.name] ?? null) : null;
        return { title: `Spacing · ${label}`, summary: a ? `${editor.axis === 'y' ? '↕' : '⇆'} ${a.rel.base == null ? 'page' : bn ?? a.rel.base} → ${v ?? '?'}` : 'no rule in effect', tag: elements.find((e) => e.name === selectedEl!.name)?.anchor ? 'anchor' : '' };
      }
      case 'centering': { const c = l?.center; return { title: 'Centering', summary: c ? `↕ ${c.y?.length ? `on ${c.y.length} parts` : 'off'} · ⇆ ${c.x?.length ? 'on' : 'off'}` : '' }; }
      case 'glyphs': { const n = selectedEl ? d.areas[selectedEl.area]?.glyphs.length ?? 0 : 0; return { title: label ? `Glyphs of ${label}` : 'Glyphs', badge: selectedEl ? n : null, summary: selectedEl ? `${editor.pinned[selectedEl.name] ?? ''} selected` : 'click a part' }; }
      case 'tester': return { title: 'Tester', summary: '' };
    }
  }
  function dragMove(e: PointerEvent) {
    if (!panels.dragging) return;
    panels.pointer = { x: e.clientX, y: e.clientY };
    const el = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null;
    const dockEl = el?.closest('[data-dock]') as HTMLElement | null;
    if (!dockEl) { panels.over = null; return; }
    const dock = dockEl.dataset.dock as Dock;
    const ids = panels.a.docks[dock];
    const slots = [...dockEl.querySelectorAll<HTMLElement>('[data-panel-slot]')];
    let index = ids.length;
    for (const sl of slots) {
      const r = sl.getBoundingClientRect();
      const before = dock === 'bottom' && sl.tagName === 'BUTTON' ? e.clientX < r.left + r.width / 2 : e.clientY < r.top + r.height / 2;
      if (before) { index = ids.indexOf(sl.dataset.panelSlot as PanelId); break; }
    }
    panels.over = { dock, index: Math.max(0, index) };
  }
  function dragUp() {
    if (!panels.dragging) return;
    if (panels.over) panels.move(panels.dragging, panels.over.dock, panels.over.index);
    panels.dragging = null; panels.over = null;
  }
  function startResize(dock: Dock, e: PointerEvent) {
    e.preventDefault();
    const start = { x: e.clientX, y: e.clientY, size: panels.a.size[dock] };
    const move = (ev: PointerEvent) => {
      const d = dock === 'left' ? ev.clientX - start.x : dock === 'right' ? start.x - ev.clientX : start.y - ev.clientY;
      panels.setSize(dock, start.size + d, start.size);
    };
    const up = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
  }
  let cols = $derived.by(() => {
    const a = panels.a;
    const side = (dock: 'left' | 'right') => (panels.visible(dock) ? (dock === 'left' ? `${a.size.left}px 6px` : `6px ${a.size.right}px`) : a.docks[dock].length || panels.dragging ? '24px' : '');
    return `${side('left')} minmax(360px, 1fr) ${side('right')}`.trim();
  });
  const dockNames = (dock: Dock) => panels.a.docks[dock].map((id) => meta(id).title).join(' · ');
</script>

<svelte:window onkeydown={onkey} />

{#snippet body(id: PanelId)}
  {#if id === 'types'}<WordTypesPanel />
  {:else if id === 'structure'}{#if editor.layout}<StructurePanel />{:else}<p class="muted">No word type open.</p>{/if}
  {:else if id === 'pagecenter'}<PageCenterPanel />
  {:else if id === 'budget'}<FontBudgetPanel />
  {:else if id === 'spacing'}
    {#if editor.layout && selectedEl && editing}<RuleEditor />
    {:else if editor.layout && selectedEl}<RulePanel />
    {:else}<div class="muted small">Click a part on the canvas to see and edit its spacing rules.</div>{/if}
  {:else if id === 'centering'}{#if editor.layout}<CenterPanel />{/if}
  {:else if id === 'glyphs'}<div class:greyed={editing}><GlyphTray /></div>
  {:else if id === 'tester'}<div class:greyed={editing}><TestStrip /></div>
  {/if}
{/snippet}
{#snippet panel(id: PanelId)}
  {@const m = meta(id)}
  <Panel {id} title={m.title} badge={m.badge} warn={m.warn} summary={m.summary} tag={m.tag}>{@render body(id)}</Panel>
{/snippet}
{#snippet sideDock(dock: 'left' | 'right')}
  {#if panels.visible(dock)}
    {#if dock === 'right'}<div class="split v" title="Drag to resize; drag shut to hide" onpointerdown={(e) => startResize(dock, e)}></div>{/if}
    <PanelDock {dock} {panel} {meta} />
    {#if dock === 'left'}<div class="split v" title="Drag to resize; drag shut to hide" onpointerdown={(e) => startResize(dock, e)}></div>{/if}
  {:else if panels.a.docks[dock].length}
    <button class="rail" data-dock={dock} title="Show the {DOCK_LABEL[dock]}" onclick={() => panels.show(dock)}><span>{dockNames(dock)}</span></button>
  {:else if panels.dragging}
    <div class="rail drop" data-dock={dock}><span>drop: new {DOCK_LABEL[dock]}</span></div>
  {/if}
{/snippet}

<div class="page" class:dragging={!!panels.dragging} style="grid-template-columns: {cols}">
  {@render sideDock('left')}

  <section class="center">
    {#if editor.layout}
      <div class="toolbar row wrap">
        <label><input type="checkbox" bind:checked={editor.showBoxes} /> boxes</label>
        <label><input type="checkbox" bind:checked={editor.showGlyphs} /> glyphs</label>
        <span class="spacer"></span>
        <label>width <input type="range" min="320" max="900" bind:value={canvasWidth} /></label>
        {#if editor.resolving}<span class="muted">Updating…</span>{/if}
      </div>
      <div class="canvas-wrap" bind:clientHeight={wrapH}>
        <WordCanvas bind:this={canvasEl} {elements} width={canvasWidth} maxHeight={Math.max(300, wrapH - 24)} showBoxes={editor.showBoxes} showGlyphs={editor.showGlyphs} showPage={true}
          center={{ x: editor.layout.center.x_target ?? d.center.x, y: editor.layout.center.y_target ?? d.center.y }}
          selected={editor.selected} hoverable={true} {arrows} labels={editor.showBoxes} handles={!editing} selectedArrow={editing ? null : editor.selectedArrow}
          dimmed={editing ? elements.map((e) => e.name).filter((n) => n !== editor.selected && n !== editBase) : []}
          dragOnly={editing ? editor.selected : null} lockAxis={editing ? editing.axis : null} {overlay} baseMark={editing ? editBase : null}
          onselect={(n) => { if (!editing) editor.select(n); }} {ondrag} {onlink} onselectarrow={selectArrow} />
      </div>
      <div class="status">
        {#if editor.dragLabel}{editor.dragLabel}
        {:else if editor.resolved?.error}<span class="error">{editor.resolved.error}</span>
        {:else if editing && selectedEl}Editing a rule of {elementLabel(editor.layout, selectedEl.name, areaLabel)}: drag it {editing.axis === 'y' ? 'up or down' : 'left or right'} to set the gap ({Math.round(editing.value + editing.liveDelta)}), then Confirm.
        {:else if selectedEl}{elementLabel(editor.layout, selectedEl.name, areaLabel)}{#if elements.find((e) => e.name === selectedEl!.name)?.anchor} · <span class="anchor-word">anchor</span>: first glyph of the chain, carries the word's absolute position{/if} · {status || 'drag to change its active rule · drag a ○ handle onto another part to attach it there'}
        {:else}Click a part to see and edit its spacing. {status}{/if}
      </div>
    {:else}
      <p class="muted" style="padding: var(--s-5)">No word types yet. Turn on Advanced and add one in the Word types panel.</p>
    {/if}
    {#if panels.visible('bottom')}
      <div class="split h" title="Drag to resize; drag shut to hide" onpointerdown={(e) => startResize('bottom', e)}></div>
      <div class="bottom" style="height: {panels.a.size.bottom}px"><PanelDock dock="bottom" {panel} {meta} /></div>
    {:else if panels.a.docks.bottom.length}
      <button class="rail hrail" data-dock="bottom" title="Show the bottom strip" onclick={() => panels.show('bottom')}>{dockNames('bottom')}</button>
    {:else if panels.dragging}
      <div class="rail hrail drop" data-dock="bottom">drop: new bottom strip</div>
    {/if}
  </section>

  {@render sideDock('right')}
</div>
{#if panels.dragging}
  <div class="ghost" style="left: {panels.pointer.x + 12}px; top: {panels.pointer.y - 12}px">⠿ {meta(panels.dragging).title}</div>
{/if}

<style>
  .page { display: grid; height: 100%; min-width: 0; }
  .page.dragging { user-select: none; cursor: grabbing; }
  .center { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .toolbar { padding: var(--s-2) var(--s-3); border-bottom: 1px solid var(--line); gap: var(--s-3); }
  .spacer { flex: 1; }
  .canvas-wrap { flex: 1 1 auto; min-height: 240px; padding: var(--s-3); display: flex; justify-content: center; align-items: flex-start; overflow: auto; }
  .status { padding: 4px var(--s-3); border-top: 1px solid var(--line); font-size: var(--t-sm); color: var(--fg-2); min-height: 26px; }
  .bottom { flex: none; min-height: 0; overflow: hidden; border-top: 1px solid var(--line); background: var(--bg); }
  .split { background: transparent; touch-action: none; }
  .split.v { cursor: col-resize; border-left: 1px solid var(--line); }
  .split.v:hover { background: var(--accent-bg); }
  .split.h { height: 6px; cursor: row-resize; border-top: 1px solid var(--line); flex: none; }
  .split.h:hover { background: var(--accent-bg); }
  .rail { border: 0; border-radius: 0; background: var(--bg-2); color: var(--fg-2); font-size: var(--t-xs); padding: 0; height: auto; width: 24px; display: flex; align-items: flex-start; justify-content: center; border-right: 1px solid var(--line); }
  .rail span { writing-mode: vertical-rl; padding: var(--s-2) 0; white-space: nowrap; }
  .rail:hover { background: var(--accent-bg); color: var(--accent); }
  .rail.drop { border: 2px dashed var(--accent); background: var(--accent-bg); color: var(--accent); }
  .rail.hrail { width: auto; height: 24px; flex: none; align-items: center; border-right: 0; border-top: 1px solid var(--line); }
  .rail.hrail span { writing-mode: horizontal-tb; }
  .ghost { position: fixed; z-index: 60; pointer-events: none; padding: 3px 8px; border: 1px solid var(--accent); border-radius: var(--radius); background: var(--bg); color: var(--accent); font-size: var(--t-sm); font-weight: 600; box-shadow: 0 6px 18px rgba(0,0,0,.2); }
  .greyed { opacity: .45; pointer-events: none; }
  .small { font-size: var(--t-xs); }
  .wrap { flex-wrap: wrap; }
  .anchor-word { color: var(--arrow); font-weight: 600; }
  :global(.page.dragging [data-dock]) { min-height: 48px; }
</style>
