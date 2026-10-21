<script lang="ts">
  import * as I from '$lib/icons';
  import { onMount, tick } from 'svelte';
  import { page } from '$app/state';
  import { replaceState } from '$app/navigation';
  import { api, type Design, type Layout, type Relationship } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { editor, attachGap, bumpGap, gapValue, gapEntryIndex } from '$lib/editor.svelte';
  import { elementLabel, anchorNames, elementNames, clampZoom, zoomScroll } from '$lib/shape';
  import { applyRuleEdit, combosOf, entriesOf } from '$lib/rules';
  import WordCanvas, { type Arrow, type Edge } from '$lib/components/WordCanvas.svelte';
  import CenterPanel from '$lib/components/CenterPanel.svelte';
  import WordTester from '$lib/components/WordTester.svelte';
  import AreaPanel from '$lib/components/AreaPanel.svelte';
  import RulePanel from '$lib/components/RulePanel.svelte';
  import RuleEditor from '$lib/components/RuleEditor.svelte';
  import StructurePanel from '$lib/components/StructurePanel.svelte';
  import WordTypesPanel from '$lib/components/WordTypesPanel.svelte';
  import PageCenterPanel from '$lib/components/PageCenterPanel.svelte';
  import FontBudgetPanel from '$lib/components/FontBudgetPanel.svelte';
  import PanelWorkspace from '$lib/components/PanelWorkspace.svelte';
  import { usedIn } from '$lib/areas';
  import { panels, type Meta, type PanelId } from '$lib/panels.svelte';
  import { LAYOUTS_HELP } from '$lib/help';

  const d = $derived(app.design!);
  // canvas zoom: 1 = the word fits the canvas area; more scrolls
  let zoom = $state(1);
  let wrapW = $state(0);
  let wrapEl = $state<HTMLDivElement>();
  async function setZoom(z: number, at?: { x: number; y: number }) {
    const nz = clampZoom(z), el = wrapEl;
    if (!el || nz === zoom) return;
    const f = nz / zoom, r = el.getBoundingClientRect();
    const px = at ? at.x - r.left : el.clientWidth / 2, py = at ? at.y - r.top : el.clientHeight / 2;
    const sx = el.scrollLeft, sy = el.scrollTop;
    zoom = nz;
    await tick();
    el.scrollLeft = zoomScroll(sx, px, f); el.scrollTop = zoomScroll(sy, py, f);
  }
  function onWheel(e: WheelEvent) {
    if (!e.ctrlKey && !e.metaKey) return;   // ⌘ + wheel, or a trackpad pinch (sent as ctrl + wheel)
    e.preventDefault();
    setZoom(zoom * Math.exp(-e.deltaY / 300), { x: e.clientX, y: e.clientY });
  }
  function onZoomKey(e: KeyboardEvent) {
    const t = e.target as HTMLElement;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === '!' || (e.shiftKey && e.code === 'Digit1')) { e.preventDefault(); setZoom(1); }
    else if (e.key === '=' || e.key === '+') { e.preventDefault(); setZoom(zoom * 1.25); }
    else if (e.key === '-' || e.key === '_') { e.preventDefault(); setZoom(zoom / 1.25); }
  }
  let wrapH = $state(0);
  let canvasEl: WordCanvas;
  let status = $state<string>('');   // what the last canvas action did; its own line above the status line
  $effect(() => { void editor.selected; void editor.layoutName; status = ''; });

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
    // ?area=<id>&g=<glyph>: show that area (and preview the glyph) in Area Properties
    const area = page.url.searchParams.get('area');
    if (area && d.areas[area]) { editor.showArea(area, page.url.searchParams.get('g')); panels.setFolded('glyphs', false); }
    else editor.syncChoice();
    if (area) {   // one-shot: a reload after switching areas shouldn't jump back
      const u = new URL(page.url); u.searchParams.delete('area'); u.searchParams.delete('g');
      replaceState(u, page.state);
    }
  });

  $effect(() => { void app.design; if (editor.layoutName && !app.design?.layouts.some((l) => l.name === editor.layoutName)) editor.setLayout(app.design?.layouts[0]?.name ?? ''); else editor.syncChoice(); });

  // resolve: one request at a time, the latest waiting one runs next. Edits are debounced; a drag
  // isn't (each move restarting the timer would show nothing until the mouse stops), so the
  // part follows the pointer as fast as the server answers.
  let seq = 0, shown = 0, timer: ReturnType<typeof setTimeout> | null = null;
  let inflight = false, waiting: (() => Promise<void>) | null = null;
  function run(job: () => Promise<void>) {
    if (inflight) { waiting = job; return; }
    inflight = true;
    job().finally(() => { inflight = false; const next = waiting; waiting = null; if (next) run(next); });
  }
  $effect(() => {
    const re = editor.ruleEdit ? $state.snapshot(editor.ruleEdit) : null;
    const name = editor.layoutName, choice = $state.snapshot(editor.choice), pinned = $state.snapshot(effPinned);
    const design = re && app.design ? applyRuleEdit(app.design, name, re, re.liveDelta) : editor.dragDesign ?? app.design;
    if (!design || !name || !choice.length) return;
    const dragging = !!editor.dragDesign || !!re?.liveDelta;
    if (timer) clearTimeout(timer);
    const id = ++seq;
    editor.resolving = true;
    const job = async () => {
      try {
        const r = await api.resolve(design, name, choice, pinned);
        if (id > shown) { shown = id; editor.resolved = r; }   // answers arrive in order; skip only older ones
        if (id === seq) editor.resolving = false;
      } catch (e) { if (id === seq) { editor.resolving = false; status = (e as Error).message; } }
    };
    if (dragging) run(job);
    else timer = setTimeout(() => run(job), 50);
  });

  let elements = $derived.by(() => {
    const res = editor.resolved;
    const anchors = anchorNames(editor.elements, d.areas);
    return editor.elements.map((e) => {
      const r = res?.elements.find((x) => x.name === e.name);
      const miss = res?.unplaced?.[e.name];
      return { name: e.name, area: e.area, glyph: effPinned[e.name], x: r?.x ?? null, y: r?.y ?? null, size: (r?.size ?? d.areas[e.area].size) as [number, number],
        error: !!miss || (!!res?.error && r?.x == null), missing: miss ? (Object.keys(miss) as ('x' | 'y')[]) : undefined,
        problem: miss ? unplacedNote(e.name, miss) : undefined, anchor: anchors.has(e.name) };
    });
  });
  /** Tooltip for a part the resolver parked at 0: which placement rule it lacks, and why. */
  function unplacedNote(name: string, miss: Partial<Record<'x' | 'y', string>>) {
    const what = [miss.y ? 'vertical' : '', miss.x ? 'horizontal' : ''].filter(Boolean).join(' and ');
    const at = [miss.x ? 'x = 0' : '', miss.y ? 'y = 0' : ''].filter(Boolean).join(', ');
    const why = [miss.y, miss.x].filter(Boolean).join(' · ');
    return `${name} needs a ${what} placement rule in this shape. Shown at ${at} until it has one; add a rule in Spacing.\n${why}`;
  }
  let selectedEl = $derived(editor.selected ? editor.elements.find((e) => e.name === editor.selected) ?? null : null);
  const areaLabel = (a: string) => app.areaLabel(a);

  type Box = { x: number; y: number; size: [number, number] };
  /** Arrow geometry for one rule of the selected part, if both ends are drawable, plus bars on the two edges it ties. */
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
    // a ghost is a fallback in the part's chain ("relative to A, else B…"): the gap it would get if the bases before it were missing
    const label = ghost ? `else ${v ?? '?'}${who}` : `${v ?? '?'}${cond}`;
    const title = ghost ? `Fallback: ${v ?? '?'}${who}, used only in words without the parts before it in the chain. Not in effect for this word. Click to look at its rules.` : `${v ?? '?'}${who}: in effect. Click to edit this rule; drag the part to change its gap.`;
    const id = `${axis}:${index}`;
    if (axis === 'y') {
      const myEdge = (rel.elem_edge ?? 'top') === 'top' ? me.y + me.size[1] : me.y;
      if (rel.base == null) { const x = me.x + me.size[0] / 2; const c = centredStart('y', me.name); return ghost ? null : { id, x, y1: 0, y2: me.y, label: `start ${Math.round(me.y)}${c ? '*' : ''}`, axis, title: c ? CENTRED_NOTE.y : title, bars: { at: x, me: { name: me.name, box: me as Box, edge: 'bottom' } } }; }
      if (!base || base.x == null || base.y == null) return null;
      const be = (rel.base_edge ?? 'bottom') as Edge, mine = (rel.elem_edge ?? 'top') as Edge;
      const baseEdge = be === 'bottom' ? base.y : base.y + base.size[1];
      const x = ghost ? Math.min(me.x, base.x) - 30 - 70 * k : Math.max(me.x, base.x) + Math.min(me.size[0], base.size[0]) / 2;
      const mid = Math.max(me.x, base.x) + Math.min(me.size[0], base.size[0]) / 2;
      return { id, x, y1: baseEdge, y2: myEdge, label, axis, ghost, title, bars: { at: mid, base: { name: base.name, box: base as Box, edge: be }, me: { name: me.name, box: me as Box, edge: mine } } };
    }
    const myEdge = (rel.elem_edge ?? 'right') === 'right' ? me.x + me.size[0] : me.x;
    const midY = me.y + me.size[1] / 2;
    if (rel.base == null) { const c = centredStart('x', me.name); return ghost ? null : { id, y: midY, x1: 0, x2: me.x, label: `x ${Math.round(me.x)}${c ? '*' : ''}`, axis, title: c ? CENTRED_NOTE.x : title, bars: { at: midY, me: { name: me.name, box: me as Box, edge: 'left' } } }; }
    if (!base || base.x == null || base.y == null) return null;
    const be = (rel.base_edge ?? 'left') as Edge, mine = (rel.elem_edge ?? 'right') as Edge;
    const baseEdge = be === 'left' ? base.x : base.x + base.size[0];
    const y = ghost ? Math.max(me.y + me.size[1], base.y + base.size[1]) + 30 + 50 * k : midY;
    return { id, y, x1: baseEdge, x2: myEdge, label, axis, ghost, title, bars: { at: midY, base: { name: base.name, box: base as Box, edge: be }, me: { name: me.name, box: me as Box, edge: mine } } };
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
        // else gaps: all of them when the panel's checkbox is on, otherwise only the one whose pill is hovered or viewed
        if (ghost && !editor.showElse && i !== editor.hoverRel && !(axis === editor.axis && i === editor.viewedRel) && editor.selectedArrow !== `${axis}:${i}`) return;
        const a = arrowFor(axis, i, r, me, ghost, k);
        if (a && ghost) a.emph = i === editor.hoverRel || (axis === editor.axis && i === editor.viewedRel);
        if (a) { out.push(a); if (ghost) k++; }
      });
    }
    return out;
  });

  // ---- drag: edits the active rule of the dragged part (or the rule being edited)
  let dragFrom: { design: Design; gaps: Record<'x' | 'y', number | null> } | null = null;
  const edgeOf = (r: { x: number | null; y: number | null; size: [number, number] }, ed: Edge) =>
    ed === 'top' ? r.y! + r.size[1] : ed === 'bottom' ? r.y! : ed === 'left' ? r.x! : r.x! + r.size[0];
  /** The gap a part's rule in effect has on screen right now (edge to edge, or from the page), or null. */
  function shownGap(axis: 'x' | 'y', name: string): number | null {
    const a = editor.activeRel(axis, name);
    const me = elements.find((x) => x.name === name);
    if (!a || !me || me.x == null || me.y == null) return null;
    const rel = editor.layout!.relationships[a.index];
    if (rel.base == null) return Math.round(axis === 'y' ? me.y : me.x);
    const bn = editor.baseName(name, rel);
    const base = bn ? elements.find((x) => x.name === bn) : null;
    if (!base || base.x == null || base.y == null) return null;
    const be = (rel.base_edge ?? (axis === 'y' ? 'bottom' : 'left')) as Edge, mine = (rel.elem_edge ?? (axis === 'y' ? 'top' : 'right')) as Edge;
    return Math.round(edgeOf(me, mine) - edgeOf(base, be));
  }
  /** `shown`: the rule's gap on screen before the drag, used when no gap row applies to the shown glyphs (the "?" arrow). */
  function applyDelta(design: Design, name: string, dx: number, dy: number, shown?: number | null): string | null {
    const l = design.layouts.find((x) => x.name === editor.layoutName)!;
    const axis = dx ? 'x' : 'y', delta = dx || dy;
    const a = editor.activeRel(axis, name);
    if (!a) return null;
    const rel = l.relationships[a.index];
    const bn = editor.baseName(name, rel);
    const baseGlyph = bn ? editor.pinned[bn] ?? null : null, elemGlyph = editor.pinned[name] ?? null;
    const before = gapValue(rel.gap, baseGlyph, elemGlyph);
    const ei = gapEntryIndex(rel.gap, baseGlyph, elemGlyph);
    let after = bumpGap(rel, delta, baseGlyph, elemGlyph);
    if (after == null) {
      // no gap row for these glyphs: start an "otherwise" row from where the part sits now
      const from = shown ?? shownGap(axis, name);
      if (from == null) return null;
      after = Math.round(from + delta);
      attachGap(rel, after, baseGlyph, elemGlyph);
    }
    const cond = ei < 0 ? (before == null ? ' (new otherwise row)' : '') : entriesOf(rel.gap)[ei].when_base || entriesOf(rel.gap)[ei].when_elem ? ` rule ${ei + 1}` : ' otherwise';
    const who = elementLabel(l, name, areaLabel);
    const what = axis === 'y' ? (rel.base == null ? 'start height' : `gap above${bn ? ` after ${elementLabel(l, bn, areaLabel)}` : rel.base === 'prev' ? ' after previous row' : ''}`) : (rel.base == null ? 'x position' : 'horizontal gap');
    return `${l.label ?? l.name}: ${what} of ${who}${cond} ${before ?? '?'} → ${after}`;
  }
  function commit(name: string, dx: number, dy: number) {
    let label = '';
    const shown = dragFrom?.gaps[dx ? 'x' : 'y'];
    app.edit('drag', (dd) => { label = applyDelta(dd, name, dx, dy, shown) ?? 'drag'; });
    if (app.undoStack.length) { app.undoStack[app.undoStack.length - 1].label = label; app.changes[app.changes.length - 1] = label; }
    status = label;
  }
  function ondrag(e: { name: string; dx: number; dy: number; phase: 'start' | 'move' | 'end' | 'cancel' }) {
    if (e.phase === 'start') status = '';
    const re = editor.ruleEdit;
    if (re) {
      const delta = re.axis === 'y' ? e.dy : e.dx;
      if (e.phase === 'move') re.liveDelta = delta;
      else if (e.phase === 'end') { re.value = Math.round(re.value + delta); re.liveDelta = 0; }
      else re.liveDelta = 0;
      return;
    }
    if (e.phase === 'start') { dragFrom = { design: JSON.parse(JSON.stringify(app.design)), gaps: { x: shownGap('x', e.name), y: shownGap('y', e.name) } }; return; }
    if (e.phase === 'cancel') { editor.dragDesign = null; editor.dragLabel = null; dragFrom = null; return; }
    if (!dragFrom) return;
    if (e.phase === 'move') {
      if (!e.dx && !e.dy) { editor.dragDesign = null; editor.dragLabel = null; return; }
      if (centredStart(e.dx ? 'x' : 'y', e.name)) { editor.dragDesign = null; editor.dragLabel = CENTRED_NOTE[e.dx ? 'x' : 'y'].slice(2); return; }
      const copy: Design = JSON.parse(JSON.stringify(dragFrom.design));
      const label = applyDelta(copy, e.name, e.dx, e.dy, dragFrom.gaps[e.dx ? 'x' : 'y']);
      if (label) { editor.dragDesign = copy; editor.dragLabel = label; } else editor.dragLabel = 'This part has no rule to change for the current glyphs';
      return;
    }
    editor.dragDesign = null; editor.dragLabel = null;
    if ((e.dx || e.dy) && centredStart(e.dx ? 'x' : 'y', e.name)) { dragFrom = null; return; }   // the footnote says why
    if (e.dx || e.dy) commit(e.name, e.dx, e.dy);
    dragFrom = null;
  }
  function nudge(dx: number, dy: number) {
    const re = editor.ruleEdit;
    if (re) { re.value += re.axis === 'y' ? dy : dx; return; }
    if (!editor.selected) return;
    if (centredStart(dx ? 'x' : 'y', editor.selected)) return;   // the footnote says why
    commit(editor.selected, dx, dy);
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
  /** A start height (or page x) that Centering overrides: the word is centred on this axis and the
   *  centred parts hang off this part, so the whole word, this part included, is shifted back to the
   *  target. The canvas marks it "start 910*" and a drag explains instead of recording a no-op edit. */
  function centredStart(axis: 'x' | 'y', name: string): boolean {
    const l = editor.layout;
    const on = l?.center?.[axis];
    const active = editor.activeRel(axis, name);
    if (!l || !on?.length || !active || l.relationships[active.index].base != null) return false;
    return on.some((c) => dependsOn(l, axis, c, name));
  }
  const CENTRED_NOTE = {
    y: '* Set by Centering: the word is centred vertically, so changing this start height doesn\'t move it. To move this part, change the gaps of the parts below it; to move the whole word, change the y target in Centering.',
    x: '* Set by Centering: the word is centred horizontally, so changing this x doesn\'t move it. To move this part, change the gaps of the parts beside it; to move the whole word, change the x target in Centering.'
  };
  let centredNotes = $derived(editor.selected && !editing ? (['y', 'x'] as const).filter((ax) => arrows.some((a) => a.axis === ax && !a.ghost && a.label.endsWith('*'))) : []);

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
    const gap = Math.round(edgeOf(meR, e.edge) - edgeOf(tgR, e.targetEdge));
    const who = elementLabel(l, e.name, areaLabel), whom = base === 'prev' ? 'the previous row' : elementLabel(l, e.target, areaLabel);
    let how = 'set' as 'set' | 'kept' | 'otherwise';   // set inside app.edit's callback
    app.edit(`${l.label ?? l.name}: attach ${who}'s ${e.edge} edge to ${whom}'s ${e.targetEdge} (gap ${gap})`, (dd) => {
      const rels = dd.layouts.find((x) => x.name === l.name)!.relationships;
      let active = editor.activeRel(axis, e.name)?.index ?? null;
      const existing = rels.findIndex((r) => r.axis === axis && r.elem === me.el && (r.base ?? null) === base);
      let rel: Relationship;
      if (existing >= 0) {
        rel = rels.splice(existing, 1)[0];
        if (active != null && existing < active) active--;
        how = attachGap(rel, gap, effPinned[e.target] ?? null, effPinned[e.name] ?? null);
      } else rel = { axis, elem: me.el, base, gap };
      rel.base_edge = e.targetEdge; rel.elem_edge = e.edge;
      rels.splice(active ?? rels.length, 0, rel);
    });
    status = how === 'kept'
      ? `${who} now attaches to ${whom} (${e.edge} → ${e.targetEdge}) and takes its existing gap for these glyphs. Drag it to change that gap.`
      : how === 'otherwise'
        ? `${who} now attaches to ${whom} (${e.edge} → ${e.targetEdge}) at ${gap}, where it sits now: added as the "otherwise" gap of that rule, so it also covers glyphs without their own row. Drag it to adjust.`
        : `${who} now attaches to ${whom} (${e.edge} → ${e.targetEdge}) at ${gap}, where it sits now. Drag it to adjust.`;
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
    onZoomKey(e); if (e.defaultPrevented) return;
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

  // ---- panels: what each one shows in its header (the frame is PanelWorkspace)
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
      case 'glyphs': {
        const a = editor.shownArea, ar = a ? d.areas[a] : null;
        return { title: 'Area Properties', badge: ar ? ar.glyphs.length : null, summary: ar ? `${ar.label || a} · ${ar.size[0]} × ${ar.size[1]}${selectedEl ? ` · ${editor.pinned[selectedEl.name] ?? ''} previewed` : ''}` : 'click a part' };
      }
      case 'tester': return { title: 'Tester', summary: '' };
    }
  }
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
  {:else if id === 'glyphs'}<div class:greyed={editing}><AreaPanel /></div>
  {:else if id === 'tester'}<div class:greyed={editing}><WordTester design={editor.dragDesign ?? app.design} storageKey="jzp-strip-words" showBoxes={editor.showBoxes} onpick={(p) => editor.loadWord(p)} /></div>
  {/if}
{/snippet}
<PanelWorkspace store={panels} {meta} {body} help={LAYOUTS_HELP}>
  {#if editor.layout}
    {#if app.lockOf(`design:layout:${editor.layout.name}`)}
      <div class="banner info locked"><span class="ic"><I.Lock /></span><span>{app.lockMessage(`design:layout:${editor.layout.name}`)} You can look and try words; changes are refused.</span></div>
    {/if}
    <div class="toolbar row wrap">
      <label><input type="checkbox" bind:checked={editor.showBoxes} /> boxes</label>
      <label><input type="checkbox" bind:checked={editor.showGlyphs} /> glyphs</label>
      <span class="spacer"></span>
      <span class="zoom" title="Zoom: ⌘ + scroll or pinch on the canvas, + / − keys; ⇧1 fits">
        <button class="ghost" onclick={() => setZoom(zoom / 1.25)} disabled={zoom <= 0.25} aria-label="Zoom out" data-tip="Zoom out (−)"><I.Minus /></button>
        <span class="pct">{Math.round(zoom * 100)}%</span>
        <button class="ghost" onclick={() => setZoom(zoom * 1.25)} disabled={zoom >= 8} aria-label="Zoom in" data-tip="Zoom in (+)"><I.Plus /></button>
        <button class="ghost" onclick={() => setZoom(1)} disabled={zoom === 1} title="Fit the word to the canvas (⇧1)">Fit</button>
      </span>
      {#if editor.resolving}<span class="muted">Updating…</span>{/if}
    </div>
    <div class="canvas-wrap" role="presentation" bind:this={wrapEl} bind:clientHeight={wrapH} bind:clientWidth={wrapW} onwheel={onWheel}
      onpointerdown={(e) => { if (!(e.target as Element).closest('svg') && !editing) { editor.select(null); editor.selectedArrow = null; } }}>
      <WordCanvas bind:this={canvasEl} {elements} width={Math.max(240, wrapW - 26) * zoom} maxHeight={Math.max(240, wrapH - 26) * zoom} showBoxes={editor.showBoxes} showGlyphs={editor.showGlyphs} showPage={true}
        emBox={d.center}
        center={{ x: editor.layout.center.x_target ?? d.center.x, y: editor.layout.center.y_target ?? d.center.y }}
        selected={editor.selected} hoverable={true} {arrows} hotBar={editor.hoverEdge} labels={editor.showBoxes} handles={!editing} selectedArrow={editing ? null : editor.selectedArrow}
        dimmed={editing ? elements.map((e) => e.name).filter((n) => n !== editor.selected && n !== editBase) : []}
        dragOnly={editing ? editor.selected : null} lockAxis={editing ? editing.axis : null} {overlay} baseMark={editing ? editBase : null}
        marked={editor.boxEdit ? elements.filter((e) => e.area === editor.boxEdit!.area).map((e) => e.name) : []} ghosts={editor.boxEdit && editor.dragDesign ? editor.boxEdit.before : []}
        onselect={(n) => { if (!editing) editor.select(n); }} {ondrag} {onlink} onselectarrow={selectArrow} />
    </div>
    {#if status}<div class="note" role="status"><span>{status}</span><button class="quiet sm" aria-label="Dismiss" onclick={() => (status = '')}><I.Close /></button></div>{/if}
    <div class="status">
      {#if editor.boxEdit && editor.dragDesign}{@const be = editor.boxEdit}{@const old = d.areas[be.area]?.size ?? be.size}Box of {app.areaLabel(be.area)} {old[0]} × {old[1]} → <b>{be.size[0]} × {be.size[1]}</b>, not applied: moves parts in {usedIn(d, be.area).length} word type{usedIn(d, be.area).length === 1 ? '' : 's'}. <b>Enter</b> applies · <b>Esc</b> cancels.
    {:else if editor.dragLabel}{editor.dragLabel}
      {:else if editor.resolved?.unplaced && Object.keys(editor.resolved.unplaced).length}{@const un = Object.entries(editor.resolved.unplaced)}<span class="error"><I.Problem size={14} /> <b>Not placed:</b> {un.map(([n, m]) => `${n} has no ${[m.y ? 'vertical' : '', m.x ? 'horizontal' : ''].filter(Boolean).join(' or ')} rule in this shape`).join('; ')}. Shown at 0 with a red dashed box; select it to add a rule in Spacing.</span>{:else if editor.resolved?.error}<span class="error">{editor.resolved.error}</span>
      {:else if editing && selectedEl}Editing a rule of {elementLabel(editor.layout, selectedEl.name, areaLabel)}: drag it {editing.axis === 'y' ? 'up or down' : 'left or right'} to set the gap ({Math.round(editing.value + editing.liveDelta)}), then Confirm.
      {:else if selectedEl}{elementLabel(editor.layout, selectedEl.name, areaLabel)}{#if elements.find((e) => e.name === selectedEl!.name)?.anchor} · <span class="anchor-word">anchor</span>: first glyph of the chain, carries the word's absolute position{/if} · {status || 'drag to change its active rule · drag a ○ handle onto another part to attach it there'}
      {:else}Click a part to see and edit its spacing.{/if}
    </div>
    {#each centredNotes as ax}<div class="foot">{CENTRED_NOTE[ax]}</div>{/each}
  {:else}
    <p class="muted" style="padding: var(--space-7)">No word types yet. Turn on Advanced and add one in the Word types panel.</p>
  {/if}
</PanelWorkspace>

<style>
  .toolbar { padding: var(--space-4) var(--space-5); border-bottom: 1px solid var(--border); gap: var(--space-5); }
  .spacer { flex: 1; }
  /* the canvas centres with auto margins, not justify-content: a zoomed canvas wider than the area must still scroll to its left edge */
  .canvas-wrap { flex: 1 1 auto; min-height: 240px; padding: var(--space-5); display: flex; align-items: flex-start; overflow: auto; }
  .canvas-wrap > :global(svg) { margin: 0 auto; flex: none; }
  .zoom { display: inline-flex; align-items: center; gap: 2px; }
  .zoom button { min-width: 28px; }
  .zoom .pct { min-width: 42px; text-align: center; font-variant-numeric: tabular-nums; font-size: var(--t-small); }
  .note { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-2) var(--space-5); border-top: 1px solid var(--border); background: var(--status-info-bg); font-size: var(--t-small); }
  .note span { flex: 1; min-width: 0; }
  .foot { padding: 0 var(--space-5) 4px; font-size: var(--t-small); color: var(--ink-muted); }
  .status { padding: 4px var(--space-5); border-top: 1px solid var(--border); font-size: var(--t-small); color: var(--ink-muted); min-height: 26px; }
  .greyed { opacity: .45; pointer-events: none; }
  .small { font-size: var(--t-caption); }
  .wrap { flex-wrap: wrap; }
  .anchor-word { color: var(--accent); font-weight: 600; }
</style>
