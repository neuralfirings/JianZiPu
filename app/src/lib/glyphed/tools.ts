// The editing tools on top of the scene. The pointer picks shapes: a click selects one and draws a
// box round the selection (drag inside it to move, its corners and edges to scale, ⇧ keeps the
// proportions), ⇧-click adds or removes one; a double-click opens a shape's points (Esc, or a click
// off it, closes them). Pen draws, Pencil
// sketches, Rect/Ellipse stamp, Hand pans, Zoom zooms. One paper.Tool
// dispatches on `mode`; keyboard shortcuts live in the Svelte component.
import paper from 'paper';
import type { Scene, PathLike, Overlay } from './scene';

export type Mode = 'select' | 'pen' | 'pencil' | 'rect' | 'ellipse' | 'hand' | 'zoom';

/** The DOM event behind a Paper.js event (present at runtime, missing from the typings). */
const native = <T extends Event>(e: paper.ToolEvent | paper.KeyEvent) => (e as unknown as { event: T }).event;

type Drag =
  | { kind: 'pan'; moved: boolean }
  | { kind: 'overlay'; moved: boolean; last: paper.Point; start: paper.Point }
  | { kind: 'move'; moved: boolean; last: paper.Point; start: paper.Point }
  | { kind: 'points'; moved: boolean; last: paper.Point; start: paper.Point }
  | { kind: 'handle'; moved: boolean; seg: paper.Segment; which: 'handleIn' | 'handleOut'; alone: boolean; smooth: boolean }
  | { kind: 'marquee'; moved: boolean; start: paper.Point; add: boolean }
  | { kind: 'pen'; moved: boolean; seg: paper.Segment; closing: boolean }
  | { kind: 'pencil'; moved: boolean; path: paper.Path }
  | { kind: 'shape'; moved: boolean; start: paper.Point; path: paper.Path | null; ellipse: boolean }
  | { kind: 'zoom'; moved: boolean; start: paper.Point }
  | { kind: 'scale'; moved: boolean; from: paper.Rectangle; anchor: paper.Point; hx: number; hy: number; sx: number; sy: number };

/** The box's 8 handles, as which side each is on: -1 left/top, 0 middle, 1 right/bottom. */
const HANDLES: [number, number][] = [[-1, -1], [0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0]];
const POINT_SIZE = 7;      // a point's square while a shape's points are open (px); 0 hides them otherwise

/** Draw a picked shape's points (and curve handles) or only its outline. Paper's segmentSize must be a
 *  number: its default, null, draws no point squares at all. */
function showPoints(on: boolean) { paper.settings.handleSize = on ? POINT_SIZE : 0; paper.settings.segmentSize = on ? POINT_SIZE : 0; }

export class Tools {
  scene: Scene;
  tool: paper.Tool;
  mode: Mode = 'select';
  private before: Mode | null = null;      // mode to return to after a temporary hand (space)
  onChange: () => void = () => {};
  onCursor: (p: paper.Point | null) => void = () => {};
  onPan: () => void = () => {};
  /** Set while the pen has an unfinished path. */
  drawing: paper.Path | null = null;
  private drag: Drag | null = null;
  private marquee: paper.Path | null = null;
  private penPreview: paper.Path | null = null;
  /** The shape whose points are open (a double-click), or null: shapes are picked and boxed. */
  editing: PathLike | null = null;
  private box: paper.Group | null = null;

  constructor(scene: Scene) {
    this.scene = scene;
    this.tool = new paper.Tool();
    this.tool.minDistance = 0;
    this.tool.onMouseDown = (e: paper.ToolEvent) => this.down(e);
    this.tool.onMouseDrag = (e: paper.ToolEvent) => this.dragMove(e);
    this.tool.onMouseUp = (e: paper.ToolEvent) => this.up(e);
    this.tool.onMouseMove = (e: paper.ToolEvent) => this.move(e);
    this.tool.activate();
    showPoints(false);                       // shapes show their outline when picked, not their points
  }

  /** Open a shape's points (null: close them and go back to picking shapes). */
  setEditing(p: PathLike | null) {
    this.editing = p;
    showPoints(!!p);
    if (p) { for (const q of this.scene.paths) q.selected = q === p; this.scene.selectOverlay(null); }
    else this.clearPoints();
    this.changed();
  }
  /** onChange, after redrawing the selection's box. */
  changed() { this.drawBox(); this.onChange(); }

  /** The selection's bounds, or null. */
  private selBounds(): paper.Rectangle | null {
    const sel = this.selectedPaths;
    if (!sel.length) return null;
    return sel.map((p) => p.bounds).reduce((a, b) => a.unite(b));
  }
  private handleAt(b: paper.Rectangle, [hx, hy]: [number, number]): paper.Point {
    return new paper.Point(b.center.x + (hx * b.width) / 2, b.center.y + (hy * b.height) / 2);
  }
  /** The box round the picked shapes, with a square at each corner and edge (redrawn on every change and zoom). */
  drawBox() {
    this.box?.remove(); this.box = null;
    const b = this.mode === 'select' && !this.editing ? this.selBounds() : null;
    if (!b) return;
    const z = paper.view.zoom, hs = 8 / z;
    const g = new paper.Group({ parent: this.scene.ui });
    new paper.Path.Rectangle({ parent: g, rectangle: b, strokeColor: this.scene.accent, strokeWidth: 1, strokeScaling: false });
    for (const h of HANDLES) {
      const c = this.handleAt(b, h);
      new paper.Path.Rectangle({ parent: g, rectangle: new paper.Rectangle(c.subtract(hs / 2), new paper.Size(hs, hs)),
        fillColor: 'white', strokeColor: this.scene.accent, strokeWidth: 1, strokeScaling: false });
    }
    this.box = g;
    this.scene.glyph.activate();
  }
  /** The box handle under `p`, or null. */
  private boxHandle(p: paper.Point): [number, number] | null {
    const b = this.selBounds();
    if (!b || this.editing) return null;
    const tol = 7 / paper.view.zoom;
    return HANDLES.find((h) => this.handleAt(b, h).getDistance(p) <= tol) ?? null;
  }

  // ---- selection
  /** The top-level glyph item an inner path belongs to. */
  top(item: paper.Item): PathLike | null {
    let it: paper.Item | null = item;
    while (it && it.parent && it.parent !== this.scene.glyph) it = it.parent;
    return it && it.parent === this.scene.glyph ? (it as PathLike) : null;
  }
  /** Every simple path, including the children of compound paths. */
  allPaths(): paper.Path[] {
    const out: paper.Path[] = [];
    for (const p of this.scene.paths) if (p instanceof paper.CompoundPath) out.push(...(p.children as paper.Path[])); else out.push(p);
    return out;
  }
  get selectedPaths(): PathLike[] { return this.scene.paths.filter((p) => p.selected); }
  get selectedSegments(): paper.Segment[] {
    const out: paper.Segment[] = [];
    for (const p of this.allPaths()) if (p.selected) for (const s of p.segments) if (s.selected) out.push(s);
    return out;
  }
  /** Paths to operate on: the selection, or everything when nothing is selected. */
  get targets(): PathLike[] { const s = this.selectedPaths; return s.length ? s : this.scene.paths; }

  selectPaths(items: PathLike[], add = false) {
    this.scene.selectOverlay(null);
    if (!add) for (const p of this.scene.paths) p.selected = false;
    for (const p of items) p.selected = true;
    this.changed();
  }
  selectAll() { for (const p of this.scene.paths) p.selected = true; this.changed(); }
  clearSelection() { this.editing = null; showPoints(this.mode === 'pen'); for (const p of this.scene.paths) p.selected = false; this.scene.selectOverlay(null); this.changed(); }
  private clearPoints() { for (const s of this.selectedSegments) s.selected = false; }

  setMode(m: Mode) {
    if (m === this.mode) return;
    if (this.drawing) this.finishPen(false);
    this.mode = m;
    // the pen adds and removes points on the picked shapes, so it shows them
    showPoints(m === 'pen' || !!this.editing);
    this.penPreview?.remove(); this.penPreview = null;
    this.changed();
  }
  /** Space held: hand until released. */
  holdHand(on: boolean) {
    if (on && this.mode !== 'hand') { this.before = this.mode; this.mode = 'hand'; this.changed(); }
    else if (!on && this.before) { this.mode = this.before; this.before = null; this.changed(); }
  }

  /** `selected: true` = only the selected shapes, and only the handles of their selected points
   *  (the ones drawn). Tested shape by shape: Paper's own `selected` hit filter, applied from the
   *  glyph layer, matched nothing, so a click on a point fell through to moving the whole shape. */
  private hit(point: paper.Point, opts: Record<string, unknown>): paper.HitResult | null {
    const tol = paper.settings.hitTolerance / paper.view.zoom;
    const { selected, ...rest } = opts;
    if (!selected) return this.scene.glyph.hitTest(point, { tolerance: tol, ...rest }) ?? null;
    for (const p of [...this.selectedPaths].reverse()) {      // topmost first
      const h = p.hitTest(point, { tolerance: tol, ...rest, match: (r: paper.HitResult) => !r.type.startsWith('handle') || r.segment.selected });
      if (h) return h;
    }
    return null;
  }

  // ---- events
  private down(e: paper.ToolEvent) {
    const p = e.point;
    const ev = native<MouseEvent>(e);
    if (this.mode === 'hand' || ev.button === 1) { this.drag = { kind: 'pan', moved: false }; return; }
    if (this.mode === 'select' && this.scene.overlayAt(p) === 'dot') return this.grabOverlay('dot', e);
    switch (this.mode) {
      case 'select': return this.downSelect(e);
      case 'pen': return this.downPen(e);
      case 'pencil': { const path = new paper.Path({ segments: [p], closed: false }); this.scene.adopt(path); this.clearSelection(); this.drag = { kind: 'pencil', moved: false, path }; return; }
      case 'rect': case 'ellipse': this.clearSelection(); this.drag = { kind: 'shape', moved: false, start: p, path: null, ellipse: this.mode === 'ellipse' }; return;
      case 'zoom': this.drag = { kind: 'zoom', moved: false, start: p }; return;
    }
  }

  private downSelect(e: paper.ToolEvent): void {
    const p = e.point;
    const shift = e.modifiers.shift || !!native<MouseEvent>(e)?.shiftKey;
    if (this.editing) {
      if (this.editing.parent !== this.scene.glyph) { this.setEditing(null); return this.downSelect(e); }   // undone away
      const alt = e.modifiers.alt || e.modifiers.option;
      // 1. a handle of a selected point
      let hit = this.hit(p, { handles: true, selected: true });
      if (hit && (hit.type === 'handle-in' || hit.type === 'handle-out')) {
        const seg = hit.segment;
        this.drag = { kind: 'handle', moved: false, seg, which: hit.type === 'handle-in' ? 'handleIn' : 'handleOut', alone: alt, smooth: seg.isSmooth() };
        return;
      }
      // 2. a point of the open shape
      hit = this.hit(p, { segments: true, selected: true });
      if (hit && hit.type === 'segment') {
        const sg = hit.segment;
        if (shift) sg.selected = !sg.selected;
        else if (!sg.selected) { this.clearPoints(); sg.selected = true; }
        this.drag = { kind: 'points', moved: false, last: p, start: p };
        this.changed();
        return;
      }
      // 3. the open shape itself: move it whole; empty: a marquee picks its points; another shape: close the points
      hit = this.hit(p, { fill: true, stroke: true });
      const item = hit ? this.top(hit.item) : null;
      if (item === this.editing) { this.clearPoints(); this.drag = { kind: 'move', moved: false, last: p, start: p }; this.changed(); return; }
      if (!item) { this.drag = { kind: 'marquee', moved: false, start: p, add: shift }; return; }
      this.setEditing(null);
    }
    // the picked shapes' box: a corner or an edge scales them
    const h = this.boxHandle(p);
    if (h) {
      const from = this.selBounds()!;
      const anchor = this.handleAt(from, [-h[0], -h[1]] as [number, number]);
      this.drag = { kind: 'scale', moved: false, from, anchor, hx: h[0], hy: h[1], sx: 1, sy: 1 };
      return;
    }
    // a shape: pick it (⇧ adds or removes it) and drag them all
    const hit = this.hit(p, { fill: true, stroke: true });
    const item = hit ? this.top(hit.item) : null;
    if (item) {
      if (shift) { item.selected = !item.selected; this.scene.selectOverlay(null); this.changed(); }
      else if (!item.selected) this.selectPaths([item]);
      this.drag = { kind: 'move', moved: false, last: p, start: p };
      return;
    }
    // inside the box, between shapes: drag them all
    const b = this.selBounds();
    if (b && !shift && b.contains(p)) { this.drag = { kind: 'move', moved: false, last: p, start: p }; return; }
    // the compare glyph (under the outline, so the outline stays editable where they overlap)
    const ov = this.scene.overlayAt(p);
    if (ov) return this.grabOverlay(ov, e);
    // empty: marquee (shift adds)
    if (!shift) this.clearSelection();
    this.drag = { kind: 'marquee', moved: false, start: p, add: shift };
  }

  /** Pick the dot or the compare glyph (⇧ adds to the picked ones) and start dragging them. */
  private grabOverlay(o: Overlay, e: paper.ToolEvent) {
    // the mouse event's own shift flag too: Paper only tracks modifiers from key events
    if (e.modifiers.shift || native<MouseEvent>(e)?.shiftKey) this.scene.selectOverlay(o, true);
    else if (!this.scene.overlaySel.has(o)) {
      for (const p of this.scene.paths) p.selected = false;
      this.scene.selectOverlay(o);
    }
    this.drag = { kind: 'overlay', moved: false, last: e.point, start: e.point };
    this.changed();
  }

  private downPen(e: paper.ToolEvent) {
    const p = e.point;
    const tol = 8 / paper.view.zoom;
    if (this.drawing) {
      const first = this.drawing.firstSegment;
      if (this.drawing.segments.length > 1 && first.point.getDistance(p) < tol) {
        this.drawing.closed = true;
        this.drag = { kind: 'pen', moved: false, seg: first, closing: true };
        return;
      }
      const seg = this.drawing.add(p) as paper.Segment;
      this.drag = { kind: 'pen', moved: false, seg, closing: false };
      return;
    }
    // pen over a point of a selected shape removes it; over its curve adds one
    let hit = this.hit(p, { segments: true, selected: true });
    if (hit && hit.type === 'segment') {
      const path = hit.segment.path as paper.Path;
      if (path.closed || path.segments.length > 2 || !(hit.segment === path.lastSegment || hit.segment === path.firstSegment)) {
        if (!path.closed && (hit.segment === path.lastSegment || hit.segment === path.firstSegment)) { /* continue the line below */ }
        else { hit.segment.remove(); if (path.segments.length < 2) this.top(path)?.remove(); this.scene.commit('remove point'); this.changed(); return; }
      }
    }
    hit = this.hit(p, { curves: true, stroke: true, selected: true });
    if (hit && hit.location && (hit.type === 'curve' || hit.type === 'stroke')) {
      const path = hit.location.path as paper.Path;
      const seg = path.divideAt(hit.location);
      this.clearPoints();
      if (seg) seg.selected = true;
      this.scene.commit('add point');
      this.changed();
      return;
    }
    // start on an open path's end to continue it
    hit = this.hit(p, { segments: true, ends: true });
    if (hit && hit.type === 'segment') {
      const path = hit.segment.path as paper.Path;
      if (!path.closed) {
        if (hit.segment === path.firstSegment) path.reverse();
        this.drawing = path;
        path.selected = true;
        this.drag = null;
        return;
      }
    }
    const path = new paper.Path({ segments: [p], closed: false });
    this.scene.adopt(path);
    this.clearSelection();
    path.selected = true;
    this.drawing = path;
    this.drag = { kind: 'pen', moved: false, seg: path.firstSegment, closing: false };
  }

  private dragMove(e: paper.ToolEvent) {
    const d = this.drag; if (!d) return;
    d.moved = true;
    const p = e.point;
    switch (d.kind) {
      case 'pan': this.scene.pan(e.delta.x * paper.view.zoom, e.delta.y * paper.view.zoom); this.onPan(); break;
      case 'overlay': {
        let target = p;
        if (e.modifiers.shift) { const t = p.subtract(d.start); target = Math.abs(t.x) > Math.abs(t.y) ? new paper.Point(p.x, d.start.y) : new paper.Point(d.start.x, p.y); }
        const delta = target.subtract(d.last);
        this.scene.moveOverlays(delta.x, delta.y);
        d.last = target;
        break;
      }
      case 'move': case 'points': {
        let target = p;
        if (e.modifiers.shift) { const t = p.subtract(d.start); target = Math.abs(t.x) > Math.abs(t.y) ? new paper.Point(p.x, d.start.y) : new paper.Point(d.start.x, p.y); }
        const delta = target.subtract(d.last);
        if (d.kind === 'move') { for (const it of this.selectedPaths) it.translate(delta); this.box?.translate(delta); }   // the box goes with them
        else for (const s of this.selectedSegments) s.point = s.point.add(delta);
        d.last = target;
        break;
      }
      case 'scale': {
        const b = d.from;
        // the scale along each axis the handle moves, from the side across from it; no flipping through
        let sx = d.hx ? Math.max(0.01, ((p.x - d.anchor.x) * d.hx) / b.width) : 1;
        let sy = d.hy ? Math.max(0.01, ((p.y - d.anchor.y) * d.hy) / b.height) : 1;
        if (e.modifiers.shift || native<MouseEvent>(e)?.shiftKey) { const k = d.hx && d.hy ? Math.max(sx, sy) : d.hx ? sx : sy; sx = k; sy = k; }
        for (const it of this.selectedPaths) it.scale(sx / d.sx, sy / d.sy, d.anchor);
        d.sx = sx; d.sy = sy;
        this.drawBox();
        break;
      }
      case 'handle': {
        const v = p.subtract(d.seg.point);
        const other = d.which === 'handleIn' ? 'handleOut' : 'handleIn';
        d.seg[d.which] = v;
        if (d.smooth && !d.alone) d.seg[other] = v.normalize(-(d.seg[other] as paper.Point).length || -v.length);
        break;
      }
      case 'pen': {
        const v = p.subtract(d.seg.point);
        d.seg.handleOut = v; d.seg.handleIn = v.multiply(-1);
        break;
      }
      case 'pencil': if (p.getDistance(d.path.lastSegment.point) > 2 / paper.view.zoom) d.path.add(p); break;
      case 'shape': {
        d.path?.remove();
        let r = new paper.Rectangle(d.start, p);
        if (e.modifiers.shift) { const s = Math.max(r.width, r.height); r = new paper.Rectangle(d.start, d.start.add(new paper.Point(Math.sign(p.x - d.start.x || 1) * s, Math.sign(p.y - d.start.y || 1) * s))); }
        d.path = d.ellipse ? new paper.Path.Ellipse({ rectangle: r, insert: false }) : new paper.Path.Rectangle({ rectangle: r, insert: false });
        this.scene.adopt(d.path);
        break;
      }
      case 'marquee': {
        this.marquee?.remove();
        this.marquee = new paper.Path.Rectangle({ parent: this.scene.ui, rectangle: new paper.Rectangle(d.start, p), strokeColor: this.scene.accent, strokeWidth: 1, strokeScaling: false, dashArray: [4 / paper.view.zoom, 3 / paper.view.zoom] });
        this.scene.glyph.activate();
        break;
      }
    }
  }

  private up(e: paper.ToolEvent) {
    const d = this.drag; this.drag = null;
    if (!d) return;
    switch (d.kind) {
      case 'move': if (d.moved) this.scene.commit('move'); break;
      case 'scale': if (d.moved) this.scene.commit('scale'); this.changed(); break;
      case 'points': if (d.moved) this.scene.commit('move point'); break;
      case 'handle': if (d.moved) this.scene.commit('adjust curve'); break;
      case 'pen': if (d.closing) this.finishPen(true); else this.changed(); break;
      case 'pencil': {
        if (d.path.segments.length < 2) { d.path.remove(); break; }
        d.path.simplify(2.5);
        d.path.selected = true;
        this.scene.commit('pencil');
        break;
      }
      case 'shape': if (d.path) { d.path.selected = true; this.scene.commit(d.ellipse ? 'ellipse' : 'rectangle'); } break;
      case 'zoom': this.scene.zoomAt(e.modifiers.alt || e.modifiers.option ? 1 / 1.5 : 1.5, paper.view.projectToView(d.start)); break;
      case 'overlay': this.changed(); break;
      case 'marquee': {
        this.marquee?.remove(); this.marquee = null;
        if (!d.moved) { if (this.editing) this.setEditing(null); break; }
        const r = new paper.Rectangle(d.start, e.point);
        // a shape's points open: pick its points; otherwise pick shapes
        if (this.editing) {
          if (!d.add) this.clearPoints();
          const ed = this.editing;
          for (const s of (ed instanceof paper.CompoundPath ? (ed.children as paper.Path[]).flatMap((c) => c.segments) : ed.segments)) if (r.contains(s.point)) s.selected = true;
        } else this.selectPaths(this.scene.paths.filter((p) => r.intersects(p.bounds) || r.contains(p.bounds)), d.add);
        this.changed();
        break;
      }
    }
  }

  private move(e: paper.ToolEvent) {
    this.onCursor(e.point);
    if (this.mode === 'pen' && this.drawing) {
      this.penPreview?.remove();
      this.penPreview = new paper.Path.Line({ parent: this.scene.ui, from: this.drawing.lastSegment.point, to: e.point, strokeColor: this.scene.accent, strokeWidth: 1, strokeScaling: false, dashArray: [3 / paper.view.zoom, 3 / paper.view.zoom] });
      this.scene.glyph.activate();
    } else if (this.penPreview) { this.penPreview.remove(); this.penPreview = null; }
  }

  /** End the pen path: closed = a filled shape, open = a line at the reference weight. */
  finishPen(closed: boolean) {
    const d = this.drawing; if (!d) return;
    this.drawing = null;
    this.penPreview?.remove(); this.penPreview = null;
    if (d.segments.length < 2) { d.remove(); this.changed(); return; }
    if (closed) d.closed = true;
    this.scene.commit(d.closed ? 'draw shape' : 'draw line');
    this.changed();
  }
  cancelPen() {
    const d = this.drawing; if (!d) return;
    this.drawing = null;
    this.penPreview?.remove(); this.penPreview = null;
    if (d.segments.length < 2) d.remove(); else this.scene.commit('draw line');
    this.changed();
  }

  /** Double-click: on a shape, open its points; on an open shape's point, toggle corner / smooth. */
  doubleClick(point: paper.Point) {
    if (this.mode !== 'select') return;
    if (this.editing) {
      const hit = this.hit(point, { segments: true, selected: true });
      if (hit && hit.type === 'segment') {
        const s = hit.segment;
        if (s.handleIn.isZero() && s.handleOut.isZero()) s.smooth({ type: 'catmull-rom', factor: 0.5 });
        else s.clearHandles();
        this.scene.commit(s.hasHandles() ? 'smooth point' : 'corner point');
        this.changed();
        return;
      }
    }
    const hit = this.hit(point, { fill: true, stroke: true });
    const item = hit ? this.top(hit.item) : null;
    if (item && item !== this.editing) this.setEditing(item);
  }

  /** Make the selected points corners, smooth, or free (handles kept, no longer linked). */
  setPointKind(kind: 'corner' | 'smooth') {
    const segs = this.selectedSegments; if (!segs.length) return;
    for (const s of segs) { if (kind === 'corner') s.clearHandles(); else s.smooth({ type: 'catmull-rom', factor: 0.5 }); }
    this.scene.commit(kind === 'corner' ? 'corner points' : 'smooth points');
    this.changed();
  }

  deleteSelection() {
    const segs = this.selectedSegments;
    if (segs.length) {
      const paths = new Set(segs.map((s) => s.path as paper.Path));
      for (const s of segs) s.remove();
      for (const p of paths) if (p.segments.length < 2) { if (p.parent instanceof paper.CompoundPath && p.parent.children.length > 1) p.remove(); else this.top(p)?.remove(); }
      this.scene.commit('delete points');
    } else {
      const sel = this.selectedPaths;
      if (!sel.length) return;
      for (const p of sel) p.remove();
      this.scene.commit('delete');
    }
    this.changed();
  }

  nudge(dx: number, dy: number) {
    if (this.scene.moveOverlays(dx, dy)) { this.changed(); return; }   // overlays are never saved: no undo step
    const delta = new paper.Point(dx, dy);
    const segs = this.selectedSegments;
    if (segs.length) { for (const s of segs) s.point = s.point.add(delta); this.scene.commit('nudge point'); }
    else { const sel = this.selectedPaths; if (!sel.length) return; for (const p of sel) p.translate(delta); this.scene.commit('nudge'); }
    this.changed();
  }

  destroy() { this.tool.remove(); }
}
