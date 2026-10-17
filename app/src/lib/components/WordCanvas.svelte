<script lang="ts">
  // Draws positioned boxes/glyphs in font units. Optional interaction:
  // click to select, drag to move (reported in font units, axis-locked),
  // rule arrows (active / ghost, selectable), and edge handles on the
  // selected box that can be dragged onto another box's edge to link them.
  import { parseSvg } from '$lib/svg';
  import { app } from '$lib/state.svelte';

  type El = { name: string; area: string; glyph?: string | null; x: number | null; y: number | null; size: [number, number]; error?: boolean; anchor?: boolean };
  type ArrowBase = { id?: string; label: string; axis: 'x' | 'y'; ghost?: boolean; title?: string };
  export type Arrow = (ArrowBase & { x: number; y1: number; y2: number }) | (ArrowBase & { y: number; x1: number; x2: number });
  export type Edge = 'top' | 'bottom' | 'left' | 'right';
  let {
    elements, width = 320, height, showBoxes = true, showGlyphs = true, showPage = false,
    page = [0, 1000], pageHeight = [-500, 1100], center = null, selected = null, hoverable = false,
    arrows = [], labels = false, fit = true, maxHeight = 0, handles = false, selectedArrow = null,
    dimmed = [], dragOnly = null, lockAxis = null, overlay = {}, baseMark = null,
    onselect, ondrag, onlink, onselectarrow
  }: {
    elements: El[]; width?: number; height?: number; showBoxes?: boolean; showGlyphs?: boolean; showPage?: boolean;
    page?: [number, number]; pageHeight?: [number, number]; center?: { x: number; y: number } | null;
    selected?: string | null; hoverable?: boolean; arrows?: Arrow[]; labels?: boolean; fit?: boolean; maxHeight?: number;
    handles?: boolean; selectedArrow?: string | null;
    dimmed?: string[]; dragOnly?: string | null; lockAxis?: 'x' | 'y' | null; overlay?: Record<string, string[]>; baseMark?: string | null;
    onselect?: (name: string | null) => void;
    ondrag?: (e: { name: string; dx: number; dy: number; phase: 'start' | 'move' | 'end' | 'cancel' }) => void;
    onlink?: (e: { name: string; edge: Edge; target: string; targetEdge: Edge }) => void;
    onselectarrow?: (id: string | null) => void;
  } = $props();

  // viewBox in canvas units (y flipped: sy = -y)
  let box = $derived.by(() => {
    let x0 = showPage ? page[0] : Infinity, x1 = showPage ? page[1] : -Infinity;
    let y0 = showPage ? pageHeight[0] : Infinity, y1 = showPage ? pageHeight[1] : -Infinity;
    for (const e of elements) {
      if (e.x == null || e.y == null) continue;
      x0 = Math.min(x0, e.x); x1 = Math.max(x1, e.x + e.size[0]);
      y0 = Math.min(y0, e.y); y1 = Math.max(y1, e.y + e.size[1]);
    }
    if (!isFinite(x0)) { x0 = 0; x1 = 1000; y0 = -500; y1 = 1100; }
    const m = fit ? 60 : 0;
    return { x: x0 - m, y: -(y1 + m), w: x1 - x0 + 2 * m, h: y1 - y0 + 2 * m };
  });
  let w = $derived(maxHeight > 0 ? Math.min(width, Math.round((maxHeight * box.w) / box.h)) : width);
  let h = $derived(height ?? Math.round((w * box.h) / box.w));
  const fs = $derived(Math.max(14, box.w / 30));
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
    {#if center}
      <line x1={center.x - 40} x2={center.x + 40} y1={-center.y} y2={-center.y} class="cross" />
      <line x1={center.x} x2={center.x} y1={-center.y - 40} y2={-center.y + 40} class="cross" />
    {/if}
  {/if}
  {#each elements as e (e.name)}
    {#if e.x != null && e.y != null}
      {@const g = e.glyph ? parseSvg(app.svgs[e.glyph]) : null}
      {@const tgt = link?.target?.name === e.name ? link.target.edge : null}
      {@const ov = overlay[e.name]}
      <g class="el" class:selected={selected === e.name} class:hoverable class:error={e.error} class:anchor={e.anchor} class:target={!!tgt}
         class:dim={dimmed.includes(e.name)} class:base={baseMark === e.name} class:locked={!!dragOnly && dragOnly !== e.name}
         onpointerdown={(ev) => { ev.stopPropagation(); down(ev, e.name); }} role="button" tabindex="-1">
        {#if ov && ov.length}
          {#each ov as og, oi (og)}
            {@const pg = parseSvg(app.svgs[og])}
            {#if pg}<svg x={e.x} y={-(e.y + e.size[1])} width={e.size[0]} height={e.size[1]} viewBox={pg.viewBox} class="g ov ov{(oi % 4) + 1}">{@html pg.inner}</svg>{/if}
          {/each}
        {:else if showGlyphs && g}
          <svg x={e.x} y={-(e.y + e.size[1])} width={e.size[0]} height={e.size[1]} viewBox={g.viewBox} class="g">{@html g.inner}</svg>
        {/if}
        <rect x={e.x} y={-(e.y + e.size[1])} width={e.size[0]} height={e.size[1]} class="box" class:hidden={!showBoxes} />
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
  {#each arrows as a (a.id ?? a.label)}
    {@const on = a.id != null && a.id === selectedArrow}
    <g class="arrow" class:ghost={a.ghost} class:on role="button" tabindex="-1"
       onpointerdown={(ev) => { ev.stopPropagation(); if (a.id) onselectarrow?.(a.id); }}>
      <title>{a.title ?? a.label}</title>
      {#if 'y1' in a}
        <line x1={a.x} x2={a.x} y1={-a.y1} y2={-a.y2} class="hit" />
        <line x1={a.x} x2={a.x} y1={-a.y1} y2={-a.y2} class="ln" />
        <line x1={a.x - 20} x2={a.x + 20} y1={-a.y1} y2={-a.y1} class="ln" />
        <line x1={a.x - 20} x2={a.x + 20} y1={-a.y2} y2={-a.y2} class="ln" />
        <text x={a.x + 26} y={-(a.y1 + a.y2) / 2 + fs / 3} font-size={fs} class="albl">{a.label}</text>
      {:else}
        <line y1={-a.y} y2={-a.y} x1={a.x1} x2={a.x2} class="hit" />
        <line y1={-a.y} y2={-a.y} x1={a.x1} x2={a.x2} class="ln" />
        <line y1={-a.y - 20} y2={-a.y + 20} x1={a.x1} x2={a.x1} class="ln" />
        <line y1={-a.y - 20} y2={-a.y + 20} x1={a.x2} x2={a.x2} class="ln" />
        <text x={(a.x1 + a.x2) / 2} y={-a.y - 8} font-size={fs} text-anchor="middle" class="albl">{a.label}</text>
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
  .canvas { display: block; background: var(--canvas); border-radius: var(--radius); touch-action: none; overflow: visible; }
  .page { fill: none; stroke: var(--line); stroke-dasharray: 12 12; stroke-width: 2; }
  .baseline { stroke: var(--line); stroke-width: 2; }
  .cross { stroke: var(--fg-2); stroke-width: 2; }
  .box { fill: var(--box); stroke: var(--box-line); stroke-width: 2; vector-effect: non-scaling-stroke; }
  .box.hidden { fill: transparent; stroke: transparent; }
  .el.hoverable:hover .box { stroke: var(--accent); }
  .el.selected .box { stroke: var(--accent); stroke-width: 3; fill: var(--box); }
  .el.error .box { stroke: var(--danger); }
  .el.anchor .box { stroke: var(--arrow); stroke-width: 3; fill: rgba(217,56,56,.08); }
  .el.anchor.selected .box { stroke: var(--arrow); stroke-width: 4; }
  .el.target .box { stroke: var(--ok); stroke-width: 3; }
  .el.dim { opacity: .28; }
  .el.locked { cursor: default; }
  .el.base .box { stroke: var(--fg); stroke-width: 3; fill: transparent; }
  .g.ov { opacity: .6; }
  .g.ov1 { color: var(--ov1); } .g.ov2 { color: var(--ov2); } .g.ov3 { color: var(--ov3); } .g.ov4 { color: var(--ov4); }
  .tedge { stroke: var(--ok); stroke-width: 6; vector-effect: non-scaling-stroke; }
  .anchor-tag { fill: var(--arrow); font-family: var(--font); font-weight: 600; pointer-events: none; paint-order: stroke; stroke: var(--canvas); stroke-width: 4px; }
  .interactive .el { cursor: grab; }
  .linking .el { cursor: crosshair; }
  .g { color: var(--fg); overflow: visible; }
  .lbl { fill: var(--fg-2); font-family: var(--mono); pointer-events: none; }
  .arrow { cursor: pointer; }
  .arrow .ln { stroke: var(--arrow); stroke-width: 2; vector-effect: non-scaling-stroke; pointer-events: none; }
  .arrow .hit { stroke: transparent; stroke-width: 14; vector-effect: non-scaling-stroke; }
  .arrow .albl { fill: var(--arrow); font-family: var(--font); paint-order: stroke; stroke: var(--canvas); stroke-width: 4px; pointer-events: all; cursor: pointer; }
  .arrow:hover .albl { text-decoration: underline; }
  .arrow.ghost .ln { stroke: var(--fg-2); stroke-dasharray: 6 5; opacity: .7; }
  .arrow.ghost .albl { fill: var(--fg-2); font-size: 85%; }
  .arrow.on .ln { stroke-width: 4; opacity: 1; }
  .arrow.on .albl { font-weight: 600; }
  .arrow.ghost.on .ln { stroke: var(--accent); }
  .arrow.ghost.on .albl { fill: var(--accent); }
  .handle { fill: var(--canvas); stroke: var(--accent); stroke-width: 2; vector-effect: non-scaling-stroke; cursor: crosshair; }
  .handle:hover { fill: var(--accent); }
  .linkline { stroke: var(--accent); stroke-width: 2; stroke-dasharray: 4 4; vector-effect: non-scaling-stroke; pointer-events: none; }
  .albl { fill: var(--accent); font-family: var(--font); paint-order: stroke; stroke: var(--canvas); stroke-width: 4px; pointer-events: none; }
</style>
