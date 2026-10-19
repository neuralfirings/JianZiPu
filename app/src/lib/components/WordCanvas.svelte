<script lang="ts">
  // Draws positioned boxes/glyphs in font units. Optional interaction:
  // click to select, drag to move (reported in font units, axis-locked),
  // rule arrows (active / ghost, selectable), and edge handles on the
  // selected box that can be dragged onto another box's edge to link them.
  import { parseSvg } from '$lib/svg';
  import { app } from '$lib/state.svelte';
  import { canvasBox, labelWidth, placeLabels, edgeBar, barLength, barsCoincide, type BoxEdge } from '$lib/shape';

  type El = { name: string; area: string; glyph?: string | null; x: number | null; y: number | null; size: [number, number]; error?: boolean; anchor?: boolean; missing?: ('x' | 'y')[]; problem?: string };
  type BarEnd = { name: string; box: { x: number; y: number; size: [number, number] }; edge: BoxEdge };
  /** `bars`: the two edges the rule ties together (base's in orange, this part's in the selection blue), `at` = where
   *  the arrow crosses; drawn for rules in effect and for `emph` ghosts. */
  type ArrowBase = { id?: string; label: string; axis: 'x' | 'y'; ghost?: boolean; title?: string; bars?: { at: number; base?: BarEnd; me: BarEnd }; emph?: boolean };
  export type Arrow = (ArrowBase & { x: number; y1: number; y2: number }) | (ArrowBase & { y: number; x1: number; x2: number });
  export type Edge = 'top' | 'bottom' | 'left' | 'right';
  let {
    elements, width = 320, height, showBoxes = true, showGlyphs = true, showPage = false,
    page = [0, 1000], pageHeight = [-500, 1100], center = null, emBox = null, selected = null, hoverable = false,
    arrows = [], hotBar = null, labels = false, fit = true, maxHeight = 0, handles = false, selectedArrow = null,
    dimmed = [], dragOnly = null, lockAxis = null, overlay = {}, baseMark = null, marked = [], ghosts = [],
    onselect, ondrag, onlink, onselectarrow
  }: {
    elements: El[]; width?: number; height?: number; showBoxes?: boolean; showGlyphs?: boolean; showPage?: boolean;
    page?: [number, number]; pageHeight?: [number, number]; center?: { x: number; y: number } | null;
    /** Center of a faint 1000 × 1000 square: the size of a typical character, for scale. */
    emBox?: { x: number; y: number } | null;
    selected?: string | null; hoverable?: boolean; arrows?: Arrow[];
    /** One bar to brighten (the panel sentence phrase under the pointer). */
    hotBar?: { id: string; side: 'base' | 'me' } | null; labels?: boolean; fit?: boolean; maxHeight?: number;
    handles?: boolean; selectedArrow?: string | null;
    dimmed?: string[]; dragOnly?: string | null; lockAxis?: 'x' | 'y' | null; overlay?: Record<string, string[]>; baseMark?: string | null;
    /** Parts outlined in the accent colour (the area whose box is being edited). */
    marked?: string[];
    /** Boxes drawn dashed: where the parts were before a pending edit. */
    ghosts?: { x: number; y: number; size: [number, number] }[];
    onselect?: (name: string | null) => void;
    ondrag?: (e: { name: string; dx: number; dy: number; phase: 'start' | 'move' | 'end' | 'cancel' }) => void;
    onlink?: (e: { name: string; edge: Edge; target: string; targetEdge: Edge }) => void;
    onselectarrow?: (id: string | null) => void;
  } = $props();

  // viewBox in canvas units (y flipped: sy = -y)
  let box = $derived(canvasBox(elements, { page, pageHeight, showPage, fit }, (g) => !!app.svgs[g]));
  let w = $derived(maxHeight > 0 ? Math.min(width, Math.round((maxHeight * box.w) / box.h)) : width);
  let h = $derived(height ?? Math.round((w * box.h) / box.w));
  const fs = $derived(Math.max(14, box.w / 30));
  // edge bars (font units): centred on the box outline, one length per rule (≤ 160 px on screen);
  // only when the two bars would cover each other (touching edges, gap ~0) does each step 3 px into its own box
  const upp = $derived(box.w / Math.max(1, w));
  const bars = $derived(arrows.map((a) => {
    const b = a.bars;
    if (!b || !(!a.ghost || a.emph || (a.id != null && a.id === selectedArrow))) return null;
    const ends = b.base ? [b.me, b.base] : [b.me];
    const len = barLength(ends, 160 * upp);
    let me = edgeBar(b.me.box, b.me.edge, b.at, len), base = b.base ? edgeBar(b.base.box, b.base.edge, b.at, len) : null;
    if (b.base && base && barsCoincide(me, base, 2 * upp)) {
      me = edgeBar(b.me.box, b.me.edge, b.at, len, 3 * upp);
      base = edgeBar(b.base.box, b.base.edge, b.at, len, 3 * upp);
    }
    return { dim: selectedArrow != null && a.id !== selectedArrow, me, base, baseName: b.base?.name ?? null };
  }));
  // parts that are the base of a shown rule get the base colour on their outline; faint when only unfocused rules use them
  const ruleBases = $derived.by(() => {
    const m = new Map<string, boolean>();   // name → focused
    for (const b of bars) if (b?.baseName) m.set(b.baseName, (m.get(b.baseName) ?? false) || !b.dim);
    return m;
  });
  // where each arrow's label goes: rules in effect keep their spot, fallback (ghost) labels step down out of the way
  const labelAt = $derived.by(() => {
    const at = arrows.map((a) => {
      const f = a.ghost ? fs * 0.85 : fs, w = labelWidth(a.label, f);
      const x = 'y1' in a ? a.x + 26 : (a.x1 + a.x2) / 2 - w / 2;
      const y = 'y1' in a ? -(a.y1 + a.y2) / 2 + fs / 3 : -a.y - 8;
      return { x, y, f, w };
    });
    const dy = placeLabels(at.map((p, i) => ({ x: p.x, y: p.y - p.f * 0.8, w: p.w, h: p.f, fixed: !arrows[i].ghost })));
    return at.map((p, i) => ({ ...p, y: p.y + dy[i] }));
  });
  const hr = $derived(Math.max(8, box.w / 60));           // handle radius

  let svgEl: SVGSVGElement;
  let drag: { name: string; sx: number; sy: number; axis: 'x' | 'y' | null; scale: number } | null = null;
  let link = $state<{ name: string; edge: Edge; x: number; y: number; cx: number; cy: number; sx: number; sy: number; target: { name: string; edge: Edge } | null } | null>(null);

  function toUnits(e: PointerEvent): { x: number; y: number } {
    const pt = svgEl.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(svgEl.getScreenCTM()!.inverse());
    return { x: p.x, y: -p.y };
  }
  function down(e: PointerEvent, name: string) {
    if (dragOnly) { if (name !== dragOnly) return; } else { onselect?.(name); onselectarrow?.(null); }
    if (!ondrag) return;
    const r = svgEl.getBoundingClientRect();
    drag = { name, sx: e.clientX, sy: e.clientY, axis: null, scale: box.w / r.width };
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
    ondrag({ name, dx: 0, dy: 0, phase: 'start' });
  }
  function move(e: PointerEvent) {
    if (link) {
      if (Math.hypot(e.clientX - link.sx, e.clientY - link.sy) <= 6) return;
      const p = toUnits(e); link = { ...link, cx: p.x, cy: p.y, target: hitEdge(p, link.name, link.edge) }; return;
    }
    if (!drag) return;
    let dx = (e.clientX - drag.sx) * drag.scale, dy = -(e.clientY - drag.sy) * drag.scale;
    if (!drag.axis && Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) > 4)
      drag.axis = lockAxis ?? (Math.abs(e.clientX - drag.sx) > Math.abs(e.clientY - drag.sy) ? 'x' : 'y');
    if (!drag.axis) return;
    if (drag.axis === 'x') dy = 0; else dx = 0;
    ondrag?.({ name: drag.name, dx: Math.round(dx), dy: Math.round(dy), phase: 'move' });
  }
  function up(e: PointerEvent) {
    if (link) {
      // a click on a handle (no real drag) is not a drop
      const moved = Math.hypot(e.clientX - link.sx, e.clientY - link.sy) > 6;
      const p = toUnits(e);
      const t = moved ? hitEdge(p, link.name, link.edge) : null;
      if (t) onlink?.({ name: link.name, edge: link.edge, target: t.name, targetEdge: t.edge });
      link = null;
      return;
    }
    if (!drag) return;
    const dx = drag.axis === 'x' ? Math.round((e.clientX - drag.sx) * drag.scale) : 0;
    const dy = drag.axis === 'y' ? Math.round(-(e.clientY - drag.sy) * drag.scale) : 0;
    ondrag?.({ name: drag.name, dx, dy, phase: 'end' });
    drag = null;
  }
  export function cancelDrag() {
    if (link) link = null;
    if (drag) { ondrag?.({ name: drag.name, dx: 0, dy: 0, phase: 'cancel' }); drag = null; }
  }
  function handleDown(e: PointerEvent, name: string, edge: Edge, x: number, y: number) {
    e.stopPropagation();
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
    link = { name, edge, x, y, cx: x, cy: y, sx: e.clientX, sy: e.clientY, target: null };
  }
  /** Nearest compatible edge of another box within reach of the point. */
  function hitEdge(p: { x: number; y: number }, self: string, edge: Edge): { name: string; edge: Edge } | null {
    const vertical = edge === 'top' || edge === 'bottom';
    let best: { name: string; edge: Edge; d: number } | null = null;
    const reach = box.w / 12;
    for (const e of elements) {
      if (e.name === self || e.x == null || e.y == null) continue;
      const [ew, eh] = e.size;
      const cands: [Edge, number, boolean][] = vertical
        ? [['top', Math.abs(p.y - (e.y + eh)), p.x > e.x - reach && p.x < e.x + ew + reach], ['bottom', Math.abs(p.y - e.y), p.x > e.x - reach && p.x < e.x + ew + reach]]
        : [['left', Math.abs(p.x - e.x), p.y > e.y - reach && p.y < e.y + eh + reach], ['right', Math.abs(p.x - (e.x + ew)), p.y > e.y - reach && p.y < e.y + eh + reach]];
      for (const [ed, d, inSpan] of cands) if (inSpan && d < reach && (!best || d < best.d)) best = { name: e.name, edge: ed, d };
    }
    return best;
  }
  let sel = $derived(elements.find((e) => e.name === selected) ?? null);

</script>


<svg bind:this={svgEl} width={w} height={h} viewBox="{box.x} {box.y} {box.w} {box.h}" class="canvas" class:interactive={!!onselect} class:linking={!!link}
  onpointermove={move} onpointerup={up} onpointercancel={cancelDrag}
  onpointerdown={(e) => { if (e.target === svgEl) { onselect?.(null); onselectarrow?.(null); } }} role="img">
  {#if showPage}
    <rect x={page[0]} y={-pageHeight[1]} width={page[1] - page[0]} height={pageHeight[1] - pageHeight[0]} class="page" />
    <line x1={page[0]} x2={page[1]} y1="0" y2="0" class="baseline" />
    {#if emBox}
      <rect x={emBox.x - 500} y={-(emBox.y + 500)} width="1000" height="1000" class="embox"><title>1000 × 1000: a typical character</title></rect>
      <text x={emBox.x - 500 + 8} y={-(emBox.y - 500) + fs * 0.6 + 4} font-size={fs * 0.6} class="emlbl">1000 × 1000 character</text>
    {/if}
    {#if center}
      <line x1={center.x - 40} x2={center.x + 40} y1={-center.y} y2={-center.y} class="cross" />
      <line x1={center.x} x2={center.x} y1={-center.y - 40} y2={-center.y + 40} class="cross" />
    {/if}
  {/if}
  {#each ghosts as gh, i (i)}
    <rect x={gh.x} y={-(gh.y + gh.size[1])} width={gh.size[0]} height={gh.size[1]} class="ghostbox" />
  {/each}
  {#each bars as b, bi (bi)}
    {#if b}
      {@const id = arrows[bi].id}
      {#if b.base}<line x1={b.base.x1} x2={b.base.x2} y1={-b.base.y1} y2={-b.base.y2} class="edgebar base" class:dim={b.dim} class:hot={hotBar?.id === id && hotBar?.side === 'base'} />{/if}
      <line x1={b.me.x1} x2={b.me.x2} y1={-b.me.y1} y2={-b.me.y2} class="edgebar me" class:dim={b.dim} class:hot={hotBar?.id === id && hotBar?.side === 'me'} />
    {/if}
  {/each}
  {#each elements as e (e.name)}
    {#if e.x != null && e.y != null}
      {@const g = e.glyph ? parseSvg(app.svgs[e.glyph]) : null}
      {@const tgt = link?.target?.name === e.name ? link.target.edge : null}
      {@const ov = overlay[e.name]}
      <g class="el" class:selected={selected === e.name} class:hoverable class:error={e.error} class:anchor={e.anchor} class:target={!!tgt}
         class:dim={dimmed.includes(e.name)} class:marked={marked.includes(e.name)} class:base={baseMark === e.name} class:rulebase={ruleBases.has(e.name)} class:rulebasedim={ruleBases.get(e.name) === false} class:locked={!!dragOnly && dragOnly !== e.name}
         onpointerdown={(ev) => { ev.stopPropagation(); down(ev, e.name); }} role="button" tabindex="-1">
        {#if ov && ov.length}
          {#each ov as og, oi (og)}
            {@const pg = parseSvg(app.svgs[og])}
            {#if pg}<svg x={e.x} y={-(e.y + e.size[1])} width={e.size[0]} height={e.size[1]} viewBox={pg.viewBox} class="g ov ov{(oi % 4) + 1}">{@html pg.inner}</svg>{/if}
          {/each}
        {:else if showGlyphs && g}
          <svg x={e.x} y={-(e.y + e.size[1])} width={e.size[0]} height={e.size[1]} viewBox={g.viewBox} class="g">{@html g.inner}</svg>
        {/if}
        {#if e.problem}<title>{e.problem}</title>{/if}
        <rect x={e.x} y={-(e.y + e.size[1])} width={e.size[0]} height={e.size[1]} class="box" class:hidden={!showBoxes && !e.error} />
        {#if e.missing?.length}
          <text x={e.x + 6} y={-e.y - 6} font-size={fs * 0.9} class="needs-tag">needs {e.missing.map((a) => (a === 'y' ? '↕' : '⇆')).join(' ')} rule</text>
        {/if}
        {#if tgt}
          {#if tgt === 'top'}<line x1={e.x} x2={e.x + e.size[0]} y1={-(e.y + e.size[1])} y2={-(e.y + e.size[1])} class="tedge" />
          {:else if tgt === 'bottom'}<line x1={e.x} x2={e.x + e.size[0]} y1={-e.y} y2={-e.y} class="tedge" />
          {:else if tgt === 'left'}<line x1={e.x} x2={e.x} y1={-e.y} y2={-(e.y + e.size[1])} class="tedge" />
          {:else}<line x1={e.x + e.size[0]} x2={e.x + e.size[0]} y1={-e.y} y2={-(e.y + e.size[1])} class="tedge" />{/if}
        {/if}
        {#if labels}
          <text x={e.x + 6} y={-(e.y + e.size[1]) + fs + 2} font-size={fs} class="lbl">{e.name}</text>
        {/if}
        {#if e.anchor && (labels || showBoxes)}
          <text x={e.x + e.size[0] - 6} y={-e.y - 6} font-size={fs * 0.9} text-anchor="end" class="anchor-tag">anchor</text>
        {/if}
      </g>
    {/if}
  {/each}
  {#each arrows as a, ai (a.id ?? a.label)}
    {@const la = labelAt[ai]}
    {@const on = a.id != null && a.id === selectedArrow}
    <g class="arrow" class:ghost={a.ghost} class:on role="button" tabindex="-1"
       onpointerdown={(ev) => { ev.stopPropagation(); if (a.id) onselectarrow?.(a.id); }}>
      <title>{a.title ?? a.label}</title>
      {#if 'y1' in a}
        <line x1={a.x} x2={a.x} y1={-a.y1} y2={-a.y2} class="hit" />
        <line x1={a.x} x2={a.x} y1={-a.y1} y2={-a.y2} class="ln" />
        <line x1={a.x - 20} x2={a.x + 20} y1={-a.y1} y2={-a.y1} class="ln" />
        <line x1={a.x - 20} x2={a.x + 20} y1={-a.y2} y2={-a.y2} class="ln" />
        <text x={la.x} y={la.y} font-size={la.f} class="albl">{a.label}</text>
      {:else}
        <line y1={-a.y} y2={-a.y} x1={a.x1} x2={a.x2} class="hit" />
        <line y1={-a.y} y2={-a.y} x1={a.x1} x2={a.x2} class="ln" />
        <line y1={-a.y - 20} y2={-a.y + 20} x1={a.x1} x2={a.x1} class="ln" />
        <line y1={-a.y - 20} y2={-a.y + 20} x1={a.x2} x2={a.x2} class="ln" />
        <text x={la.x + la.w / 2} y={la.y} font-size={la.f} text-anchor="middle" class="albl">{a.label}</text>
      {/if}
    </g>
  {/each}
  {#if handles && sel && sel.x != null && sel.y != null}
    {@const cx = sel.x + sel.size[0] / 2}
    {@const cy = sel.y + sel.size[1] / 2}
    {#each [['top', cx, sel.y + sel.size[1]], ['bottom', cx, sel.y], ['left', sel.x, cy], ['right', sel.x + sel.size[0], cy]] as [edge, hx, hy]}
      <circle cx={hx} cy={-(hy as number)} r={hr} class="handle" role="button" tabindex="-1"
        onpointerdown={(ev) => handleDown(ev, sel!.name, edge as Edge, hx as number, hy as number)}>
        <title>Drag this {edge} edge onto another part's edge to attach it there</title>
      </circle>
    {/each}
  {/if}
  {#if link}
    <line x1={link.x} y1={-link.y} x2={link.cx} y2={-link.cy} class="linkline" />
    <text x={link.cx + 12} y={-link.cy - 8} font-size={fs} class="albl">{link.target ? `${link.edge} edge → ${link.target.name}'s ${link.target.edge}` : `${link.edge} edge → drop on another part's edge`}</text>
  {/if}
</svg>

<style>
  .canvas { display: block; background: var(--bg-canvas); border-radius: var(--radius-md); touch-action: none; overflow: visible; }
  .page { fill: none; stroke: var(--ov-guide); stroke-dasharray: 12 12; stroke-width: 2; }
  .baseline { stroke: var(--ov-guide); stroke-width: 2; }
  .embox { fill: none; stroke: var(--ov-guide); stroke-width: 1; stroke-dasharray: 4 4; vector-effect: non-scaling-stroke; pointer-events: none; }
  .emlbl { fill: var(--ink-muted); opacity: .55; font-family: var(--font-serif); pointer-events: none; }
  .cross { stroke: var(--ink-muted); stroke-width: 2; }
  .box { fill: var(--ov-part-fill); stroke: var(--ov-part); stroke-width: 1; vector-effect: non-scaling-stroke; }
  .box.hidden { fill: transparent; stroke: transparent; }
  .el.hoverable:hover .box { stroke: var(--ov-active); }
  .el.selected .box { stroke: var(--ov-active); stroke-width: 2; fill: var(--ov-part-fill); }
  .el.error .box, .el.error .box.hidden { stroke: var(--status-danger); stroke-width: 2; stroke-dasharray: 8 5; fill: var(--status-danger-bg); fill-opacity: .55; }
  .needs-tag { fill: var(--status-danger); font-family: var(--font-serif); font-weight: 600; letter-spacing: .02em; pointer-events: none; paint-order: stroke; stroke: var(--bg-canvas); stroke-width: 4px; }
  .el.anchor .box:not(.hidden) { stroke: var(--ov-anchor); stroke-width: 2; fill: var(--ov-anchor-fill); }
  .el.anchor.selected .box:not(.hidden) { stroke: var(--ov-anchor); stroke-width: 2; outline: none; }
  .ghostbox { fill: none; stroke: var(--ink-muted); stroke-width: 1.5; stroke-dasharray: 8 6; vector-effect: non-scaling-stroke; pointer-events: none; }
  .el.marked .box, .el.marked .box.hidden { stroke: var(--link); stroke-width: 3; }
  .el.target .box { stroke: var(--status-saved); stroke-width: 3; }
  .el.dim { opacity: .28; }
  .el.locked { cursor: default; }
  .el.base .box { stroke: var(--ink); stroke-width: 3; fill: transparent; }
  /* the base of a rule of the selected part (wins over the anchor's red outline; the label still says anchor) */
  .el.rulebase .box:not(.hidden) { stroke: var(--ov-area); stroke-width: 2; }
  .el.rulebasedim .box:not(.hidden) { stroke-opacity: .35; }
  .g.ov { opacity: .6; }
  .g.ov1 { color: var(--ov1); } .g.ov2 { color: var(--ov2); } .g.ov3 { color: var(--ov3); } .g.ov4 { color: var(--ov4); }
  .tedge { stroke: var(--status-saved); stroke-width: 6; vector-effect: non-scaling-stroke; }
  .anchor-tag { fill: var(--ov-anchor); font-family: var(--font-serif); font-weight: 600; letter-spacing: .02em; pointer-events: none; paint-order: stroke; stroke: var(--bg-canvas); stroke-width: 4px; }
  .interactive .el { cursor: grab; }
  .linking .el { cursor: crosshair; }
  .g { color: var(--glyph); overflow: visible; }
  .lbl { fill: var(--ink-muted); font-family: var(--font-mono); pointer-events: none; }
  /* each bar = its outline's width + 4 px, so it reads as that edge thickening: selected 3 → 7, base 2 → 6 */
  .edgebar { stroke-linecap: round; vector-effect: non-scaling-stroke; pointer-events: none; }
  .edgebar.dim { opacity: .35; }
  .edgebar.hot { stroke-width: 9; }
  .edgebar.base { stroke: var(--ov-area); stroke-width: 6; }
  .edgebar.me { stroke: var(--ov-active); stroke-width: 6; }
  .edgebar.base.hot { stroke-width: 8; }
  .arrow { cursor: pointer; }
  .arrow .ln { stroke: var(--ov-measure); stroke-width: 2; vector-effect: non-scaling-stroke; pointer-events: none; }
  .arrow .hit { stroke: transparent; stroke-width: 14; vector-effect: non-scaling-stroke; }
  .arrow .albl { fill: var(--ov-measure); font-family: var(--font-serif); paint-order: stroke; stroke: var(--bg-canvas); stroke-width: 4px; pointer-events: all; cursor: pointer; }
  .arrow:hover .albl { text-decoration: underline; }
  .arrow.ghost .ln { stroke: var(--ink-muted); stroke-dasharray: 6 5; opacity: .7; }
  .arrow.ghost .albl { fill: var(--ink-muted); }
  .arrow.on .ln { stroke-width: 4; opacity: 1; }
  .arrow.on .albl { font-weight: 600; }
  .arrow.ghost.on .ln { stroke: var(--link); }
  .arrow.ghost.on .albl { fill: var(--link); }
  .handle { fill: var(--ov-handle); stroke: var(--ov-active); stroke-width: 2; vector-effect: non-scaling-stroke; cursor: crosshair; }
  .handle:hover { fill: var(--ov-active); }
  .linkline { stroke: var(--link); stroke-width: 2; stroke-dasharray: 4 4; vector-effect: non-scaling-stroke; pointer-events: none; }
  .albl { fill: var(--link); font-family: var(--font-serif); paint-order: stroke; stroke: var(--bg-canvas); stroke-width: 4px; pointer-events: none; }
</style>
