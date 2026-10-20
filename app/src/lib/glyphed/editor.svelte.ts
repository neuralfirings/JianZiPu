// Reactive facade over the Paper.js scene and tools, for the Svelte UI.
// Paper's objects are not reactive; `sync()` copies what the panels show
// into runes after every change.
import paper from 'paper';
import { Scene, isOpen, type Box, type PathLike } from './scene';
import { Tools, type Mode } from './tools';
import * as ops from './ops';
import { loadImage, thresholdImage, traceCanvas, TRACE_DEFAULTS, type TraceOptions } from './trace';
import { api, type SvgCheck } from '$lib/api';
import { app } from '$lib/state.svelte';
import { hosted } from '$lib/hosted.svelte';
import { sha256 } from '$lib/sha256';

export const DEFAULT_WEIGHT = 36;
const DRAFT_PREFIX = 'jzp-glyph-draft:';

export async function sha16(text: string): Promise<string> {
  return (await sha256(text)).slice(0, 16);   // matches the server's file hash
}

export type Selection =
  | { kind: 'none' }
  | { kind: 'points'; n: number; x: number; y: number; pointKind: 'corner' | 'smooth' | 'free' | 'mixed' }
  | { kind: 'shapes'; n: number; x: number; y: number; w: number; h: number; lines: number }
  | { kind: 'overlay'; dot: boolean; ghost: boolean };

export type PreviewOp = { kind: 'simplify'; value: number; from: number; to: number } | { kind: 'thicken'; value: number; sharp: boolean } | { kind: 'combine'; op: ops.BoolOp; swap: boolean };

export class GlyphEditor {
  scene: Scene | null = null;
  tools: Tools | null = null;
  name = $state('');
  isNew = $state(false);
  area = $state<string | null>(null);
  box = $state<Box>([350, 350]);
  mode = $state<Mode>('select');
  zoom = $state(1);
  cursor = $state<{ x: number; y: number } | null>(null);
  dirty = $state(false);
  changeCount = $state(0);
  canUndo = $state(false);
  canRedo = $state(false);
  undoLabel = $state<string | null>(null);
  stats = $state({ paths: 0, nodes: 0, outside: false, open: 0, specks: 0, selPaths: 0, selNodes: 0 });
  selection = $state<Selection>({ kind: 'none' });
  weightEstimate = $state<number | null>(null);
  drawing = $state(false);
  grid = $state(false);
  // compare overlays
  dot = $state(false);
  ghostName = $state<string | null>(null);
  ghostAlign = $state<'origin' | 'center'>('origin');
  ghostSaved = $state(false);
  /** The compare glyph was dragged away from its Line up position. */
  ghostMoved = $state(false);
  sessionWeight = $state<number | null>(null);     // reference weight for this session only
  // ops with live preview
  preview = $state<PreviewOp | null>(null);
  private previewSnap: string | null = null;
  private previewIdx: number[] | null = null;
  // trace mode
  trace = $state<null | { file: File; img: HTMLImageElement; opts: TraceOptions; svg: string | null; busy: boolean; showImage: boolean; scale: number; dx: number; dy: number; edited: boolean }>(null);
  private traceRaster: paper.Raster | null = null;
  private tracePreview: paper.Group | null = null;
  private traceTimer: ReturnType<typeof setTimeout> | null = null;
  // file
  built = $state<SvgCheck | null>(null);
  error = $state<string | null>(null);
  saving = $state(false);
  savedText = $state<string | null>(null);     // SVG text on disk as loaded (null = new glyph)
  savedAt = $state<Date | null>(null);
  loadedHash = $state<string | null>(null);
  conflictDisk = $state<string | null>(null);
  draftRestored = $state(false);
  /** Hand-off from the New glyph dialog: a file to import or trace once the editor is up. */
  pendingStart: { kind: 'svg' | 'image'; file: File } | null = null;
  private previewTimer: ReturnType<typeof setTimeout> | null = null;

  get referenceWeight(): number { return this.sessionWeight ?? app.design?.glyph_weight ?? DEFAULT_WEIGHT; }

  // ---- lifecycle
  async mount(canvas: HTMLCanvasElement, name: string, svg: string | null, box: Box, o: { isNew: boolean; area: string | null }) {
    this.unmount();
    this.name = name; this.isNew = o.isNew; this.area = o.area;
    this.savedText = svg; this.savedAt = null; this.error = null; this.conflictDisk = null; this.built = null;
    this.loadedHash = svg ? await sha16(svg) : null;
    this.scene = new Scene(canvas, box, this.referenceWeight);
    this.tools = new Tools(this.scene);
    this.scene.onChange = () => this.sync();
    this.tools.onChange = () => this.sync();
    this.tools.onPan = () => { this.userViewed = true; };
    this.tools.onCursor = (p) => { this.cursor = p ? { x: Math.round(p.x * 10) / 10, y: Math.round(p.y * 10) / 10 } : null; };
    this.scene.loadSvg(svg);
    if (!svg) this.scene.setBox(box);
    this.box = this.scene.box;
    this.restoreDraft();
    this.scene.fit();
    this.applyOverlays();
    this.sync();
  }
  unmount() {
    if (this.previewTimer) clearTimeout(this.previewTimer);
    if (this.name) { const { [this.name]: _, ...rest } = app.preview; app.preview = rest; }
    this.tools?.destroy(); this.scene?.destroy();
    this.tools = null; this.scene = null; this.trace = null; this.preview = null;
  }
  /** Load (or reload) the file text once it is known. */
  async setSource(svg: string) {
    if (!this.scene) return;
    this.savedText = svg; this.loadedHash = await sha16(svg);
    this.scene.loadSvg(svg); this.box = this.scene.box; this.restoreDraft(); this.scene.fit(); this.applyOverlays(); this.sync();
  }
  /** The canvas keeps fitting the box on resize until the user zooms or pans. */
  userViewed = false;
  resize(w: number, h: number) { this.scene?.resize(w, h); if (!this.userViewed) this.scene?.fit(); }

  sync() {
    const s = this.scene, t = this.tools;
    if (!s || !t) return;
    this.mode = t.mode;
    this.zoom = s.zoom;
    this.dirty = s.dirty;
    this.changeCount = s.changeCount;
    this.canUndo = s.canUndo; this.canRedo = s.canRedo; this.undoLabel = s.undoLabel;
    const st = s.stats;
    const segs = t.selectedSegments, sel = t.selectedPaths;
    this.stats = { paths: st.paths, nodes: st.nodes, outside: st.outside, open: st.open, specks: st.specks, selPaths: sel.length, selNodes: segs.length };
    if (segs.length) {
      const kinds = new Set(segs.map((g) => (g.handleIn.isZero() && g.handleOut.isZero() ? 'corner' : g.isSmooth() ? 'smooth' : 'free')));
      const c = segs.reduce((a, g) => a.add(g.point), new paper.Point(0, 0)).divide(segs.length);
      this.selection = { kind: 'points', n: segs.length, x: r1(c.x), y: r1(c.y), pointKind: kinds.size === 1 ? ([...kinds][0] as 'corner' | 'smooth' | 'free') : 'mixed' };
    } else if (sel.length) {
      const b = ops.bounds(sel)!;
      this.selection = { kind: 'shapes', n: sel.length, x: r1(b.x), y: r1(b.y), w: r1(b.width), h: r1(b.height), lines: sel.filter(isOpen).length };
    } else if (s.overlaySel.size) this.selection = { kind: 'overlay', dot: s.overlaySel.has('dot'), ghost: s.overlaySel.has('ghost') };
    else this.selection = { kind: 'none' };
    this.ghostMoved = s.ghostOffset[0] !== 0 || s.ghostOffset[1] !== 0;
    this.weightEstimate = ops.estimateWeight(s.paths);
    this.drawing = !!t.drawing;
    this.box = s.box;
    this.built = null;
    this.persistDraft();
    this.publishPreview();
  }

  // ---- tools & view
  setMode(m: Mode) { this.tools?.setMode(m); }
  holdHand(on: boolean) { this.tools?.holdHand(on); }
  undo() { this.scene?.undo(); }
  redo() { this.scene?.redo(); }
  discard() { this.scene?.discard(); }
  fit() { this.scene?.fit(); }
  zoom100() { this.userViewed = true; this.scene?.setZoom(1); }
  fitSelection() { this.userViewed = true; const b = ops.bounds(this.selection.kind === 'none' ? this.scene?.paths ?? [] : this.tools!.selectedPaths); if (b && this.scene) this.scene.fitRect(b); }
  zoomBy(f: number) { this.userViewed = true; this.scene?.zoomAt(f); }
  setGrid(on: boolean) { this.grid = on; this.scene?.setGrid(on); }
  wheel(e: WheelEvent) {
    if (!this.scene) return;
    e.preventDefault();
    this.userViewed = true;
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    if (e.ctrlKey || e.metaKey) this.scene.zoomAt(Math.exp(-e.deltaY * 0.01), new paper.Point(e.clientX - r.left, e.clientY - r.top));
    else this.scene.pan(-e.deltaX, -e.deltaY);
    this.zoom = this.scene.zoom;
  }
  doubleClick(e: MouseEvent) { if (this.scene && this.tools) this.tools.doubleClick(this.scene.toProject(e.clientX, e.clientY)); }

  // ---- operations (on the selection, or everything)
  get targets(): PathLike[] { return this.tools?.targets ?? []; }
  get selectedPaths(): PathLike[] { return this.tools?.selectedPaths ?? []; }
  private get shapesOrAll(): PathLike[] { const s = this.selectedPaths; return s.length ? s : this.scene?.paths ?? []; }
  cleanUp() { if (this.scene) ops.cleanUp(this.scene, this.targets); }
  smooth() { if (this.scene) ops.smooth(this.scene, this.targets); }
  flip(axis: 'h' | 'v') { if (this.scene) ops.flip(this.scene, this.shapesOrAll, axis); }
  center(which: 'both' | 'h' | 'v' = 'both') { if (this.scene) ops.centerInBox(this.scene, this.shapesOrAll, which); }
  fitToBox() { if (this.scene) ops.fitToBox(this.scene, this.scene.paths); }
  transform(t: Parameters<typeof ops.transform>[2], label: string) { if (this.scene) ops.transform(this.scene, this.shapesOrAll, t, label); }
  setPointKind(k: 'corner' | 'smooth') { this.tools?.setPointKind(k); }
  setPointPos(x: number, y: number) {
    const segs = this.tools?.selectedSegments ?? []; if (!segs.length || !this.scene) return;
    const c = segs.reduce((a, g) => a.add(g.point), new paper.Point(0, 0)).divide(segs.length);
    const d = new paper.Point(x, y).subtract(c);
    for (const g of segs) g.point = g.point.add(d);
    this.scene.commit('move point');
  }
  deleteSelection() { this.tools?.deleteSelection(); }
  selectAll() { this.tools?.selectAll(); }
  clearSelection() { this.tools?.clearSelection(); }
  nudge(dx: number, dy: number) { this.tools?.nudge(dx, dy); }
  finishPen() { this.tools?.finishPen(false); }
  cancelPen() { this.tools?.cancelPen(); }
  /** Turn the selected (or all) open lines into filled outlines. */
  outlineLines() {
    const s = this.scene; if (!s) return;
    const sel = this.selectedPaths.filter(isOpen);
    let n = 0;
    if (sel.length) { for (const p of sel) if (p instanceof paper.Path && s.outline(p)) n++; } else n = s.outlineAll();
    if (n) s.commit(n === 1 ? 'outline line' : `outline ${n} lines`);
  }
  removeSpecks() { this.scene?.removeSpecks(); }

  /** Live-preview ops: begin* restores the pre-edit state and applies the value each time; apply = one undo step. */
  private beginPreview() {
    const s = this.scene!, t = this.tools!;
    if (this.previewSnap == null) { this.previewSnap = s.snapshot(); this.previewWasSelection = t.selectedPaths.length > 0; this.previewIdx = (t.selectedPaths.length ? t.selectedPaths : s.paths).map((p) => p.index); }
    else s.restoreSnapshot(this.previewSnap);
    return this.previewIdx!.map((i) => s.paths[i]).filter(Boolean);
  }
  previewSimplify(tol: number) {
    if (!this.scene) return;
    const items = this.beginPreview();
    const from = ops.nodeCount(items);
    ops.simplify(items, tol);
    this.preview = { kind: 'simplify', value: tol, from, to: ops.nodeCount(items) };
    this.reselect(items);
  }
  previewThicken(total: number, sharp: boolean) {
    if (!this.scene) return;
    let items = this.beginPreview();
    if (total !== 0) items = ops.thicken(this.scene, items, total / 2, sharp);
    this.preview = { kind: 'thicken', value: total, sharp };
    this.reselect(items);
  }
  previewCombine(op: ops.BoolOp, swap: boolean) {
    if (!this.scene) return;
    const items = this.beginPreview();
    const r = ops.combine(this.scene, items, op, swap, false);
    this.preview = { kind: 'combine', op, swap };
    this.reselect(r ? [r] : items);
  }
  /** Keep the preview's result selected only when the targets were a selection (not the whole glyph). */
  private reselect(items: PathLike[]) {
    if (this.previewWasSelection) for (const p of items) p.selected = true;
    this.sync();
  }
  private previewWasSelection = false;
  applyPreview() {
    const s = this.scene; if (!s || !this.preview) return;
    const label = this.preview.kind === 'combine' ? this.preview.op : this.preview.kind === 'thicken' ? (this.preview.value >= 0 ? 'thicken' : 'thin') : 'simplify';
    const keep = this.previewWasSelection ? s.paths.filter((p) => p.selected).map((p) => p.index) : [];
    this.previewSnap = null; this.previewIdx = null; this.preview = null;
    s.commit(label);
    for (const i of keep) if (s.paths[i]) s.paths[i].selected = true;
    this.sync();
  }
  cancelPreview() {
    const s = this.scene; if (!s) return;
    if (this.previewSnap != null) {
      const idx = this.previewWasSelection ? this.previewIdx ?? [] : [];
      s.restoreSnapshot(this.previewSnap);
      for (const i of idx) if (s.paths[i]) s.paths[i].selected = true;
    }
    this.previewSnap = null; this.previewIdx = null; this.preview = null;
    this.sync();
  }

  inspectSvg(text: string) { return ops.inspectSvg(text); }
  importSvg(text: string, o: { fit: boolean; replace: boolean }) {
    if (!this.scene || !this.tools) return;
    const ps = ops.importSvgPaths(this.scene, text, o);
    this.tools.selectPaths(ps);
  }

  // ---- trace mode
  async startTrace(file: File) {
    if (!this.scene) return;
    const img = await loadImage(file);
    const [w, h] = this.box;
    const scale = Math.min((w - 40) / img.width, (h - 40) / img.height);
    this.trace = { file, img, opts: { ...TRACE_DEFAULTS }, svg: null, busy: false, showImage: true, scale, dx: (w - img.width * scale) / 2, dy: (h - img.height * scale) / 2, edited: false };
    this.tools?.setMode('hand');
    this.tools?.clearSelection();
    this.placeRaster();
    this.retrace();
  }
  private placeRaster() {
    const t = this.trace, s = this.scene; if (!t || !s) return;
    this.traceRaster?.remove();
    const r = new paper.Raster({ image: t.img, parent: s.ghost, insert: true });
    r.opacity = t.showImage ? 0.35 : 0;
    r.locked = true;
    this.fitTraceItem(r, t);
    this.traceRaster = r;
    s.glyph.activate();
  }
  private fitTraceItem(item: paper.Item, t: NonNullable<typeof this.trace>) {
    const b = item.bounds;
    const sx = (t.img.width * t.scale) / b.width, sy = (t.img.height * t.scale) / b.height;
    item.scale(sx, sy, b.topLeft);
    item.position = new paper.Point(t.dx + (t.img.width * t.scale) / 2, t.dy + (t.img.height * t.scale) / 2);
  }
  updateTrace(patch: Partial<NonNullable<typeof this.trace>['opts']> & { showImage?: boolean; scale?: number; dx?: number; dy?: number }) {
    const t = this.trace; if (!t) return;
    const { showImage, scale, dx, dy, ...opts } = patch;
    const reOpts = Object.keys(opts).length > 0;
    this.trace = { ...t, opts: { ...t.opts, ...opts }, showImage: showImage ?? t.showImage, scale: scale ?? t.scale, dx: dx ?? t.dx, dy: dy ?? t.dy };
    if (this.traceRaster) { this.traceRaster.opacity = this.trace.showImage ? 0.35 : 0; }
    if (scale != null || dx != null || dy != null) { this.placeRaster(); this.showTracePreview(); }
    if (reOpts) this.retrace();
  }
  private retrace() {
    if (this.traceTimer) clearTimeout(this.traceTimer);
    this.traceTimer = setTimeout(async () => {
      const t = this.trace; if (!t) return;
      this.trace = { ...t, busy: true };
      try {
        const c = thresholdImage(t.img, t.opts);
        const svg = await traceCanvas(c, t.opts);
        // potrace works at the thresholded canvas size: scale its viewBox back to image pixels
        const sx = t.img.width / c.width;
        const fixed = svg.replace(/<svg[^>]*>/, `<svg viewBox="0 0 ${t.img.width} ${t.img.height}" xmlns="http://www.w3.org/2000/svg"><g transform="scale(${sx})">`).replace(/<\/svg>\s*$/, '</g></svg>');
        if (this.trace) { this.trace = { ...this.trace, svg: fixed, busy: false }; this.showTracePreview(); }
      } catch (e) { this.error = `trace failed: ${(e as Error).message}`; if (this.trace) this.trace = { ...this.trace, busy: false }; }
    }, 150);
  }
  private showTracePreview() {
    const t = this.trace, s = this.scene; if (!t || !s) return;
    this.tracePreview?.remove(); this.tracePreview = null;
    if (!t.svg) return;
    const item = paper.project.importSVG(t.svg, { insert: false, expandShapes: true, applyMatrix: true });
    const g = new paper.Group({ parent: s.ui });
    for (const p of (await_collect(item))) { p.fillColor = new paper.Color(31 / 255, 111 / 255, 229 / 255, 0.5); p.strokeColor = null; g.addChild(p); }
    item.remove();
    // the traced paths are in image pixels: place like the raster
    g.scale(t.scale, new paper.Point(0, 0));
    g.translate(new paper.Point(t.dx, t.dy));
    g.locked = true;
    this.tracePreview = g;
    s.glyph.activate();
  }
  /** Keep the traced outline as the glyph (replace) or next to it (add). One undo step. */
  useTrace(replace: boolean) {
    const t = this.trace, s = this.scene; if (!t || !s || !t.svg) return;
    if (replace) s.glyph.removeChildren();
    const item = paper.project.importSVG(t.svg, { insert: false, expandShapes: true, applyMatrix: true });
    const paths = await_collect(item);
    for (const p of paths) { p.scale(t.scale, new paper.Point(0, 0)); p.translate(new paper.Point(t.dx, t.dy)); s.adopt(p); }
    item.remove();
    this.endTrace(false);
    s.commit('trace image');
    this.tools?.selectPaths(paths);
    this.tools?.setMode('select');
  }
  endTrace(cancel = true) {
    this.traceRaster?.remove(); this.traceRaster = null;
    this.tracePreview?.remove(); this.tracePreview = null;
    this.trace = null;
    if (cancel) { this.tools?.setMode('select'); this.sync(); }
  }

  // ---- compare overlays
  applyOverlays() {
    const s = this.scene; if (!s) return;
    s.setWeight(this.referenceWeight);
    s.setDot(this.dot);
    s.setGhostGlyph(this.ghostName ? app.svgs[this.ghostName] ?? null : null, this.ghostAlign);
    s.setGhostSaved(this.ghostSaved ? this.savedText : null);
  }
  setDot(on: boolean) { this.dot = on; this.applyOverlays(); }
  /** Choose the compare glyph; passing `align` (the Line up buttons) also puts it back where that lines it up. */
  setGhost(name: string | null, align?: 'origin' | 'center') {
    this.ghostName = name;
    if (align) { this.ghostAlign = align; if (this.scene) this.scene.ghostOffset = [0, 0]; }
    this.applyOverlays(); this.sync();
  }
  setGhostSaved(on: boolean) { this.ghostSaved = on; this.applyOverlays(); }
  /** Session-only reference weight (null = back to the design's). */
  setSessionWeight(w: number | null) { this.sessionWeight = w && w > 0 ? Math.round(w) : null; this.applyOverlays(); this.scene?.commit('line weight'); }

  // ---- draft (per glyph, in this browser) and live preview for the rest of the app
  private get draftKey() { return DRAFT_PREFIX + this.name; }
  private persistDraft() {
    const s = this.scene; if (!s) return;
    try {
      if (s.dirty) localStorage.setItem(this.draftKey, JSON.stringify({ hash: this.loadedHash, snap: s.current, box: s.box }));
      else localStorage.removeItem(this.draftKey);
    } catch { /* storage unavailable */ }
  }
  private restoreDraft() {
    const s = this.scene; if (!s) return;
    try {
      const raw = localStorage.getItem(this.draftKey);
      if (!raw) return;
      const d = JSON.parse(raw) as { hash: string | null; snap: string; box: Box };
      if (d.hash !== this.loadedHash) { localStorage.removeItem(this.draftKey); return; }
      if (d.box) s.setBox(d.box);
      s.loadDraft(d.snap);
      this.draftRestored = true;
    } catch { /* ignore a bad draft */ }
  }
  dropDraft() { try { localStorage.removeItem(this.draftKey); } catch {} }
  private publishPreview() {
    if (this.previewTimer) clearTimeout(this.previewTimer);
    this.previewTimer = setTimeout(() => {
      const s = this.scene; if (!s) return;
      if (s.dirty || this.isNew) app.preview = { ...app.preview, [this.name]: s.exportSvg() };
      else if (app.preview[this.name]) { const { [this.name]: _, ...rest } = app.preview; app.preview = rest; }
    }, 200);
  }

  // ---- file
  exportSvg(): string { return this.scene?.exportSvg() ?? ''; }
  async check() { const r = await api.checkSvg(this.exportSvg()); this.built = r; return r; }
  /** Write the file. Returns the server's answer; a conflict leaves `conflictDisk` set for the dialog. */
  async save(overwrite = false): Promise<{ ok: boolean; exists?: boolean; conflict?: boolean; error?: string }> {
    const s = this.scene; if (!s) return { ok: false, error: 'no editor' };
    if (!s.paths.length) return { ok: false, error: 'the glyph is empty' };
    this.saving = true; this.error = null;
    try {
      const text = s.exportSvg();
      if (hosted.isHosted) return await this.saveToDraft(text);
      const r = await api.saveSvg(this.name, text, this.loadedHash, overwrite);
      if (!r.ok) {
        if (r.conflict) this.conflictDisk = r.disk ?? '';
        else if (!r.exists) this.error = r.error ?? 'save failed';
        return r;
      }
      s.markSaved();
      this.savedText = text; this.savedAt = new Date(); this.loadedHash = r.hash ?? (await sha16(text)); this.conflictDisk = null;
      app.svgs = { ...app.svgs, [this.name]: text };
      if (!app.glyphs.some((g) => g.glyph === this.name)) app.glyphs = [...app.glyphs, { glyph: this.name, svg: true, areas: [] }];
      else app.glyphs = app.glyphs.map((g) => (g.glyph === this.name ? { ...g, svg: true } : g));
      if (this.isNew && this.area && app.design?.areas[this.area] && !app.design.areas[this.area].glyphs.includes(this.name)) app.addToArea(this.area, [this.name]);
      this.isNew = false;
      this.dropDraft();
      this.applyOverlays();
      this.sync();
      return r;
    } catch (e) {
      this.error = (e as Error).message; return { ok: false, error: this.error };
    } finally { this.saving = false; }
  }
  /** Hosted: the outline goes into the tester's draft (one undo step, with joining its area when
   *  new), and the draft saves. Offline, it waits in the browser like any other edit. */
  private async saveToDraft(text: string): Promise<{ ok: boolean; error?: string }> {
    const s = this.scene!;
    let design = app.design;
    if (this.isNew && this.area && design?.areas[this.area] && !design.areas[this.area].glyphs.includes(this.name)) {
      design = JSON.parse(JSON.stringify(design)) as NonNullable<typeof design>;
      design.areas[this.area].glyphs.push(this.name);
    }
    app.applyChanges(`Glyph ${this.name}: ${this.isNew ? 'new' : 'new outline'}`, { design: design ?? undefined, svgWrites: { [this.name]: text } });
    s.markSaved();
    this.savedText = text; this.savedAt = new Date(); this.loadedHash = await sha16(text); this.conflictDisk = null;
    this.isNew = false;
    this.dropDraft();
    this.applyOverlays();
    this.sync();
    await app.save();
    return { ok: true };
  }
  /** Conflict: take the disk version (drops my edits) or keep mine and overwrite. */
  async loadDiskVersion() { if (this.conflictDisk != null) { const t = this.conflictDisk; this.conflictDisk = null; this.dropDraft(); await this.setSource(t); } }
}

const r1 = (v: number) => Math.round(v * 10) / 10;
import { collectPaths } from './scene';
const await_collect = collectPaths;

export const glyphEditor = new GlyphEditor();
