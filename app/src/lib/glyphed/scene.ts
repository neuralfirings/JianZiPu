// The glyph editor's scene: a Paper.js project on a canvas, with the
// editable outline in one layer, compare overlays above it, and the area
// box behind. Coordinates are the SVG's own (y down, 1 unit = 1 font unit),
// so what you see is what inputs/svg/<name>.svg will contain.
//
// Closed paths are filled shapes. Open paths are *lines*: drawn as strokes
// of the reference weight with round ends, and turned into filled outlines
// on export (the font build ignores stroke attributes).
import paper from 'paper';
import { offsetStroke } from 'paperjs-offset';

export type Box = [number, number];
export type PathLike = paper.Path | paper.CompoundPath;

export const BLUE = [31, 111, 229] as const;
export const ghostColor = (alpha: number) => new paper.Color(BLUE[0] / 255, BLUE[1] / 255, BLUE[2] / 255, alpha);

/** Walk an imported SVG item and return its paths, flattened out of groups and clip masks. */
export function collectPaths(item: paper.Item): PathLike[] {
  const out: PathLike[] = [];
  const walk = (it: paper.Item) => {
    if (it.clipMask) return;
    if (it instanceof paper.CompoundPath || it instanceof paper.Path) { out.push(it); return; }
    if (it instanceof paper.Shape) { out.push(it.toPath(false) as paper.Path); return; }
    for (const c of [...(it.children ?? [])]) walk(c);
  };
  walk(item);
  return out;
}

export function isOpen(p: PathLike): boolean {
  return p instanceof paper.Path ? !p.closed : (p.children as paper.Path[]).some((c) => !c.closed);
}

export type Overlay = 'dot' | 'ghost';

export class Scene {
  canvas: HTMLCanvasElement;
  bg!: paper.Layer;
  glyph!: paper.Layer;
  ghost!: paper.Layer;
  ui!: paper.Layer;
  box: Box = [350, 350];
  weight = 36;                       // reference stroke weight (line width of open paths)
  ink = new paper.Color('black');
  accent = new paper.Color('#0a5cbf');
  showGrid = false;
  private history: string[] = [];
  private future: string[] = [];
  private labels: string[] = [];
  saved = '';
  onChange: () => void = () => {};

  constructor(canvas: HTMLCanvasElement, box: Box, weight: number) {
    this.canvas = canvas;
    paper.setup(canvas);
    paper.settings.handleSize = 6;
    paper.settings.hitTolerance = 5;
    this.box = box;
    this.weight = weight;
    this.bg = new paper.Layer({ name: 'bg' });
    this.glyph = new paper.Layer({ name: 'glyph' });
    this.ghost = new paper.Layer({ name: 'ghost' });
    this.ui = new paper.Layer({ name: 'ui' });
    this.readTheme();
    this.drawBox();
    this.glyph.activate();
  }

  readTheme() {
    const css = getComputedStyle(document.documentElement);
    this.ink = new paper.Color(css.getPropertyValue('--glyph').trim() || '#121212');
    this.accent = new paper.Color(css.getPropertyValue('--ov-active').trim() || '#0a5cbf');
    this.glyph.selectedColor = this.accent;
    this.restyle();
  }

  // ---- background: the area box, an optional grid, a tint outside the box when something sticks out
  drawBox() {
    this.bg.removeChildren();
    const [w, h] = this.box;
    const css = getComputedStyle(document.documentElement);
    const line = css.getPropertyValue('--ov-part').trim() || '#3f6fd8';
    const paperBg = css.getPropertyValue('--bg-canvas').trim() || '#fff';
    new paper.Path.Rectangle({ parent: this.bg, point: [0, 0], size: [w, h], fillColor: paperBg, strokeColor: line, strokeWidth: 1, strokeScaling: false });
    if (this.showGrid) {
      const step = paper.view.zoom >= 2 ? 10 : paper.view.zoom >= 0.8 ? 50 : 100;
      for (let x = step; x < w; x += step) new paper.Path.Line({ parent: this.bg, from: [x, 0], to: [x, h], strokeColor: line, strokeWidth: 0.5, strokeScaling: false, opacity: x % 100 === 0 ? 0.7 : 0.3 });
      for (let y = step; y < h; y += step) new paper.Path.Line({ parent: this.bg, from: [0, y], to: [w, y], strokeColor: line, strokeWidth: 0.5, strokeScaling: false, opacity: y % 100 === 0 ? 0.7 : 0.3 });
    }
    this.glyph.activate();
  }
  setGrid(on: boolean) { this.showGrid = on; this.drawBox(); }
  setBox(box: Box) { this.box = box; this.drawBox(); }
  setWeight(w: number) { this.weight = w; this.restyle(); }

  // ---- load / export
  /** Replace the outline with the paths of an SVG document. Returns how many paths came in. */
  loadSvg(text: string | null): number {
    this.glyph.removeChildren();
    let n = 0;
    if (text) {
      const vb = text.match(/viewBox="([^"]+)"/)?.[1]?.split(/[\s,]+/).map(Number);
      if (vb && vb.length === 4 && vb[2] > 0 && vb[3] > 0) this.setBox([vb[2], vb[3]]);
      const item = paper.project.importSVG(text, { insert: false, expandShapes: true, applyMatrix: true });
      for (const p of collectPaths(item)) { this.adopt(p); n++; }
      item.remove();
    }
    this.history = []; this.future = []; this.labels = [];
    this.saved = this.snapshot();
    this.onChange();
    return n;
  }

  /** Give a path the glyph's look (fill if closed, line if open) and put it in the glyph layer. */
  adopt(p: PathLike): PathLike {
    this.glyph.addChild(p);
    this.style(p);
    p.selected = false;
    return p;
  }
  style(p: PathLike) {
    const open = p instanceof paper.Path ? !p.closed : false;
    if (open) {
      p.fillColor = null; p.strokeColor = this.ink; p.strokeWidth = this.weight; p.strokeCap = 'round'; p.strokeJoin = 'round'; p.strokeScaling = true;
    } else {
      p.fillColor = this.ink; p.strokeColor = null; p.strokeWidth = 0;
      if (p instanceof paper.CompoundPath) for (const c of p.children as paper.Path[]) c.strokeColor = null;
    }
    p.opacity = 1;
  }
  /** Re-apply the look to every path (after an edit that may open or close one). */
  restyle() { for (const p of this.paths) this.style(p); }

  get paths(): PathLike[] {
    return this.glyph.children.filter((c) => c instanceof paper.Path || c instanceof paper.CompoundPath) as PathLike[];
  }

  /** Turn an open path into the filled outline of its stroke. Returns the new path (in place). */
  outline(p: paper.Path): PathLike | null {
    if (p.closed || p.segments.length < 2) return null;
    const idx = p.index;
    let r: PathLike;
    try { r = offsetStroke(p, this.weight / 2, { cap: 'round', join: 'round', insert: false } as any) as PathLike; }
    catch { return null; }
    p.remove();
    this.adopt(r);
    this.glyph.insertChild(idx, r);
    return r;
  }
  /** Outline every open path; returns how many were converted. */
  outlineAll(): number {
    let n = 0;
    for (const p of this.paths) if (p instanceof paper.Path && !p.closed) { if (this.outline(p)) n++; }
    return n;
  }

  /** The SVG file text, in the style of the existing files: one filled path per shape, viewBox = box,
   *  coordinates to 0.1 unit. Open paths are written as their outlines. */
  exportSvg(): string {
    const [w, h] = this.box;
    const pathData = (p: paper.Item) => (p as unknown as { getPathData(m: null, precision: number): string }).getPathData(null, 1); // to 0.1 unit
    const lines: string[] = [];
    for (const p of this.paths) {
      if (p.isEmpty()) continue;
      let item: PathLike = p;
      let temp: PathLike | null = null;
      if (p instanceof paper.Path && !p.closed) {
        if (p.segments.length < 2) continue;
        try { temp = offsetStroke(p, this.weight / 2, { cap: 'round', join: 'round', insert: false } as any) as PathLike; item = temp; }
        catch { continue; }
      }
      const rule = item.fillRule === 'evenodd' ? ' fill-rule="evenodd" clip-rule="evenodd"' : '';
      lines.push(`<path${rule} d="${pathData(item)}" fill="black"/>`);
      temp?.remove();
    }
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" fill="none" xmlns="http://www.w3.org/2000/svg">\n${lines.join('\n')}\n</svg>\n`;
  }

  // ---- history (one snapshot per committed edit)
  snapshot(): string { return JSON.stringify(this.paths.map((p) => p.exportJSON({ asString: false }))); }
  /** Replace the outline with a snapshot (no history entry). */
  restoreSnapshot(snap: string) {
    this.glyph.removeChildren();
    for (const j of JSON.parse(snap) as unknown[]) this.adopt(paper.project.importJSON(JSON.stringify(j)) as PathLike);
  }
  /** Call after an edit is complete; `label` names it for undo. */
  commit(label: string): boolean {
    this.restyle();
    const now = this.snapshot();
    const last = this.history.at(-1) ?? this.saved;
    if (now === last) return false;
    this.history.push(now); this.labels.push(label); this.future = [];
    if (this.history.length > 200) { this.history.shift(); this.labels.shift(); }
    this.onChange();
    return true;
  }
  get canUndo() { return this.history.length > 0; }
  get canRedo() { return this.future.length > 0; }
  get undoLabel() { return this.labels.at(-1) ?? null; }
  get changeCount() { return this.history.length; }
  undo() {
    const cur = this.history.pop(); if (cur === undefined) return;
    this.labels.pop();
    this.future.push(cur);
    this.restoreSnapshot(this.history.at(-1) ?? this.saved);
    this.onChange();
  }
  redo() {
    const next = this.future.pop(); if (next === undefined) return;
    this.history.push(next); this.labels.push('redo');
    this.restoreSnapshot(next);
    this.onChange();
  }
  get current() { return this.history.at(-1) ?? this.saved; }
  get dirty() { return this.current !== this.saved; }
  markSaved() { this.saved = this.current; this.onChange(); }
  /** Back to the file as loaded, as one undo step. */
  discard() { this.restoreSnapshot(this.saved); this.commit('discard'); }
  /** Load a draft snapshot as one undo step (after a reload). */
  loadDraft(snap: string) { this.restoreSnapshot(snap); this.commit('restored draft'); }

  // ---- view
  resize(w: number, h: number) { paper.view.viewSize = new paper.Size(w, h); }
  /** Fit the box (plus a margin) into the canvas. */
  fit() {
    const [w, h] = this.box;
    const vs = paper.view.viewSize;
    paper.view.zoom = Math.min(vs.width / (w * 1.25), vs.height / (h * 1.25));
    paper.view.center = new paper.Point(w / 2, h / 2);
    this.drawBox();
    this.onChange();
  }
  fitRect(r: paper.Rectangle) {
    const vs = paper.view.viewSize;
    paper.view.zoom = Math.min(40, Math.min(vs.width / (r.width * 1.4 + 1), vs.height / (r.height * 1.4 + 1)));
    paper.view.center = r.center;
    this.drawBox();
    this.onChange();
  }
  get zoom() { return paper.view.zoom; }
  setZoom(z: number) { this.zoomAt(z / paper.view.zoom); }
  zoomAt(factor: number, viewPoint?: paper.Point) {
    const v = paper.view;
    const vp = viewPoint ?? new paper.Point(v.viewSize.width / 2, v.viewSize.height / 2);
    const before = v.viewToProject(vp);
    v.zoom = Math.min(40, Math.max(0.05, v.zoom * factor));
    const after = v.viewToProject(vp);
    v.center = v.center.add(before.subtract(after));
    this.drawBox();
    this.drawOverlaySel();
    this.onChange();
  }
  pan(dx: number, dy: number) { paper.view.center = paper.view.center.subtract(new paper.Point(dx, dy).divide(paper.view.zoom)); }
  toProject(clientX: number, clientY: number): paper.Point {
    const r = this.canvas.getBoundingClientRect();
    return paper.view.viewToProject(new paper.Point(clientX - r.left, clientY - r.top));
  }

  // ---- compare overlays (translucent blue, on top, never editable, never saved)
  private dot: paper.Path | null = null;
  private ghostGlyph: paper.Item | null = null;
  private ghostSaved: paper.Item | null = null;
  private overlayFrame: paper.Item | null = null;
  dotPos: [number, number] | null = null;
  /** Where the compare glyph was dragged to, relative to its Line up position. */
  ghostOffset: [number, number] = [0, 0];
  /** The overlays picked with the pointer: they drag and nudge together, never into undo. */
  overlaySel = new Set<Overlay>();
  /** A filled circle of the reference weight's diameter; drag it over a stroke to compare thickness. */
  setDot(on: boolean) {
    this.dot?.remove(); this.dot = null;
    if (on) {
      const c = this.dotPos ?? [this.box[0] / 2, this.box[1] / 2];
      this.dotPos = c;
      this.dot = new paper.Path.Circle({ parent: this.ghost, center: c, radius: this.weight / 2, fillColor: ghostColor(0.4) });
      this.glyph.activate();
    }
    this.drawOverlaySel();
  }
  get dotItem() { return this.dot; }
  /** Another glyph's SVG, filled blue, lined up by box top-left or centred on this box. */
  setGhostGlyph(svg: string | null, align: 'origin' | 'center' = 'origin') {
    this.ghostGlyph?.remove(); this.ghostGlyph = null;
    if (!svg) return;
    const g = this.ghostItem(svg, 'fill');
    if (align === 'center') {
      const vb = svg.match(/viewBox="([^"]+)"/)?.[1]?.split(/[\s,]+/).map(Number);
      const [gw, gh] = vb && vb.length === 4 ? [vb[2], vb[3]] : [this.box[0], this.box[1]];
      g.translate(new paper.Point((this.box[0] - gw) / 2, (this.box[1] - gh) / 2));
    }
    g.translate(new paper.Point(this.ghostOffset[0], this.ghostOffset[1]));
    this.ghostGlyph = g;
    this.drawOverlaySel();
  }
  /** The overlay under a point: the dot first (it is meant to sit on a stroke), then the compare glyph's ink. */
  overlayAt(p: paper.Point): Overlay | null {
    if (this.dot?.contains(p)) return 'dot';
    if (this.ghostGlyph && this.ghostGlyph.bounds.contains(p) && collectPaths(this.ghostGlyph).some((c) => c.contains(p))) return 'ghost';
    return null;
  }
  selectOverlay(o: Overlay | null, add = false) {
    if (!add) this.overlaySel.clear();
    if (o) { if (add && this.overlaySel.has(o)) this.overlaySel.delete(o); else this.overlaySel.add(o); }
    this.drawOverlaySel();
  }
  /** Move the selected overlays; returns false when none is selected. */
  moveOverlays(dx: number, dy: number): boolean {
    if (!this.overlaySel.size) return false;
    const d = new paper.Point(dx, dy);
    if (this.overlaySel.has('dot') && this.dot) { this.dot.translate(d); this.dotPos = [this.dot.position.x, this.dot.position.y]; }
    if (this.overlaySel.has('ghost') && this.ghostGlyph) { this.ghostGlyph.translate(d); this.ghostOffset = [this.ghostOffset[0] + dx, this.ghostOffset[1] + dy]; }
    this.drawOverlaySel();
    return true;
  }
  /** A dashed frame around each selected overlay. */
  drawOverlaySel() {
    this.overlayFrame?.remove(); this.overlayFrame = null;
    for (const o of [...this.overlaySel]) if (!(o === 'dot' ? this.dot : this.ghostGlyph)) this.overlaySel.delete(o);
    if (!this.overlaySel.size) return;
    const z = paper.view.zoom, pad = 4 / z;
    const g = new paper.Group({ parent: this.ui });
    for (const o of this.overlaySel) {
      const b = (o === 'dot' ? this.dot! : this.ghostGlyph!).bounds.expand(pad * 2);
      new paper.Path.Rectangle({ parent: g, rectangle: b, strokeColor: this.accent, strokeWidth: 1, strokeScaling: false, dashArray: [4 / z, 3 / z] });
    }
    this.overlayFrame = g;
    this.glyph.activate();
  }
  /** The last-saved version of this glyph as a dashed blue outline (shows what changed). */
  setGhostSaved(svg: string | null) {
    this.ghostSaved?.remove(); this.ghostSaved = null;
    if (svg) this.ghostSaved = this.ghostItem(svg, 'dash');
  }
  private ghostItem(svg: string, look: 'fill' | 'dash'): paper.Item {
    const item = paper.project.importSVG(svg, { insert: false, expandShapes: true, applyMatrix: true });
    const g = new paper.Group({ parent: this.ghost });
    for (const p of collectPaths(item)) {
      if (look === 'fill') { p.fillColor = ghostColor(0.35); p.strokeColor = null; }
      else { p.fillColor = null; p.strokeColor = ghostColor(0.9); p.strokeWidth = 1; p.strokeScaling = false; p.dashArray = [4, 3]; }
      g.addChild(p);
    }
    item.remove();
    g.locked = true;
    this.glyph.activate();
    return g;
  }

  // ---- stats
  get stats() {
    const ps = this.paths;
    let nodes = 0, open = 0, specks = 0;
    for (const p of ps) {
      nodes += p instanceof paper.CompoundPath ? (p.children as paper.Path[]).reduce((n, c) => n + c.segments.length, 0) : p.segments.length;
      if (isOpen(p)) open++;
      if (!isOpen(p) && p.bounds.width < 6 && p.bounds.height < 6) specks++;
    }
    const b = ps.length ? this.glyph.bounds : null;
    const [w, h] = this.box;
    const outside = !!b && (b.left < -0.5 || b.top < -0.5 || b.right > w + 0.5 || b.bottom > h + 0.5);
    return { paths: ps.length, nodes, bounds: b, outside, open, specks };
  }
  removeSpecks(): number {
    let n = 0;
    for (const p of this.paths) if (!isOpen(p) && p.bounds.width < 6 && p.bounds.height < 6) { p.remove(); n++; }
    if (n) this.commit('remove specks');
    return n;
  }

  destroy() { paper.project.clear(); }
}
