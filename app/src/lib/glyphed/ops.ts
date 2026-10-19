// Whole-path operations: booleans, simplify, smooth, thicken (offset),
// flips, centering and fitting, clean-up. Each edits the scene; the caller
// (or the op itself) commits one undo step.
import paper from 'paper';
import { offset as paperOffset } from 'paperjs-offset';
import { collectPaths, isOpen, type PathLike, type Scene } from './scene';

export type BoolOp = 'unite' | 'subtract' | 'intersect' | 'exclude';

/** Combine shapes: unite / intersect / exclude fold all of them; subtract keeps the oldest
 *  (lowest in the stack) and cuts the newer ones out of it; `swap` reverses that. */
export function combine(scene: Scene, items: PathLike[], op: BoolOp, swap = false, commit = true): PathLike | null {
  if (items.length < 2) return null;
  let ordered = [...items].sort((a, b) => a.index - b.index);
  if (op === 'subtract' && swap) ordered = [ordered[ordered.length - 1], ...ordered.slice(0, -1)];
  const index = Math.min(...ordered.map((p) => p.index));
  let acc: paper.PathItem = ordered[0];
  for (const other of ordered.slice(1)) acc = acc[op](other, { insert: false });
  for (const it of ordered) it.remove();
  const result = acc as PathLike;
  scene.adopt(result);
  scene.glyph.insertChild(index, result);
  if (commit) scene.commit(op);
  return result;
}

/** Remove self-overlaps and fix winding so what the font builds matches what is shown. */
export function cleanUp(scene: Scene, items: PathLike[]) {
  for (const it of items) {
    if (isOpen(it)) continue;
    const idx = it.index;
    const r = (it as any).resolveCrossings() as paper.PathItem;
    r.reorient(true, true);
    if (r !== it) { it.remove(); scene.adopt(r as PathLike); scene.glyph.insertChild(idx, r); }
  }
  scene.commit('clean up');
}

function eachPath(items: PathLike[], fn: (p: paper.Path) => void) {
  for (const it of items) if (it instanceof paper.CompoundPath) (it.children as paper.Path[]).forEach(fn); else fn(it);
}
export function nodeCount(items: PathLike[]): number { let n = 0; eachPath(items, (p) => (n += p.segments.length)); return n; }

/** Re-fit the curves with fewer points; `tolerance` in units (higher = fewer points). No commit. */
export function simplify(items: PathLike[], tolerance: number) {
  eachPath(items, (p) => p.simplify(tolerance));
}

export function smooth(scene: Scene, items: PathLike[]) {
  eachPath(items, (p) => p.smooth({ type: 'continuous' }));
  scene.commit('smooth');
}

/** Grow (+) or shrink (−) filled shapes by `distance` units each side (open lines just change weight elsewhere). No commit. */
export function thicken(scene: Scene, items: PathLike[], distance: number, sharp = false): PathLike[] {
  const out: PathLike[] = [];
  for (const it of items) {
    if (isOpen(it)) { out.push(it); continue; }
    const idx = it.index;
    let r: PathLike;
    try { r = paperOffset(it, distance, { join: sharp ? 'miter' : 'round', insert: false } as any) as PathLike; }
    catch { out.push(it); continue; }
    it.remove();
    if (r.isEmpty()) { r.remove(); continue; }
    scene.adopt(r);
    scene.glyph.insertChild(idx, r);
    out.push(r);
  }
  return out;
}

export function bounds(items: PathLike[]): paper.Rectangle | null {
  return items.length ? items.reduce((r, p) => r.unite(p.bounds), items[0].bounds) : null;
}

export function flip(scene: Scene, items: PathLike[], axis: 'h' | 'v') {
  const b = bounds(items); if (!b) return;
  for (const it of items) it.scale(axis === 'h' ? -1 : 1, axis === 'v' ? -1 : 1, b.center);
  scene.commit(axis === 'h' ? 'flip horizontal' : 'flip vertical');
}

export function centerInBox(scene: Scene, items: PathLike[], which: 'both' | 'h' | 'v' = 'both') {
  const b = bounds(items); if (!b) return;
  const d = new paper.Point(scene.box[0] / 2, scene.box[1] / 2).subtract(b.center);
  for (const it of items) it.translate(new paper.Point(which === 'v' ? 0 : d.x, which === 'h' ? 0 : d.y));
  scene.commit('center in box');
}

/** Scale everything uniformly so it fits the box with `margin` units all round, and center it. */
export function fitToBox(scene: Scene, items: PathLike[], margin = 20, commit = true) {
  const b = bounds(items); if (!b) return;
  const [w, h] = scene.box;
  const s = Math.min((w - 2 * margin) / b.width, (h - 2 * margin) / b.height);
  if (!isFinite(s) || s <= 0) return;
  for (const it of items) it.scale(s, b.center);
  const b2 = bounds(items)!;
  const delta = new paper.Point(w / 2, h / 2).subtract(b2.center);
  for (const it of items) it.translate(delta);
  if (commit) scene.commit('fit to box');
}

export function transform(scene: Scene, items: PathLike[], t: { dx?: number; dy?: number; sx?: number; sy?: number; rotate?: number }, label: string) {
  const b = bounds(items); if (!b) return;
  for (const it of items) {
    if (t.sx != null || t.sy != null) it.scale(t.sx ?? 1, t.sy ?? 1, b.topLeft);
    if (t.rotate) it.rotate(t.rotate, b.center);
    if (t.dx || t.dy) it.translate(new paper.Point(t.dx ?? 0, t.dy ?? 0));
  }
  scene.commit(label);
}

/** Estimated stroke weight of the filled outline: 2 × area ÷ perimeter (exact for a long straight stroke). */
export function estimateWeight(items: PathLike[]): number | null {
  let area = 0, len = 0;
  for (const it of items) { if (isOpen(it)) continue; area += Math.abs(it.area); len += it.length; }
  return len > 0 ? (2 * area) / len : null;
}

/** What an SVG file brings in, before importing: its viewBox and what gets dropped. */
export function inspectSvg(text: string) {
  const vb = text.match(/viewBox="([^"]+)"/)?.[1]?.split(/[\s,]+/).map(Number) ?? null;
  const w = Number(text.match(/<svg[^>]*\swidth="([\d.]+)/)?.[1]), h = Number(text.match(/<svg[^>]*\sheight="([\d.]+)/)?.[1]);
  const box: [number, number] | null = vb && vb.length === 4 ? [vb[2], vb[3]] : w && h ? [w, h] : null;
  const dropped: string[] = [];
  if (/<text[\s>]/.test(text)) dropped.push('text');
  if (/<image[\s>]/.test(text)) dropped.push('images');
  if (/<linearGradient|<radialGradient/.test(text)) dropped.push('gradients');
  if (/fill="(?!none|black|#000(000)?|currentColor)[^"]+"/i.test(text)) dropped.push('colours');
  if (/opacity="/.test(text)) dropped.push('opacity');
  const strokes = (text.match(/stroke="(?!none)[^"]+"/g) ?? []).length;
  const paths = (text.match(/<path|<rect|<circle|<ellipse|<polygon|<polyline|<line/g) ?? []).length;
  return { box, dropped, strokes, paths };
}

/** Import an SVG's paths next to (or instead of) the existing ones. Stroked lines become filled outlines of their width. */
export function importSvgPaths(scene: Scene, text: string, o: { fit: boolean; replace: boolean }): PathLike[] {
  if (o.replace) scene.glyph.removeChildren();
  const item = paper.project.importSVG(text, { insert: false, expandShapes: true, applyMatrix: true });
  const paths = collectPaths(item);
  const out: PathLike[] = [];
  for (const p of paths) {
    const sw = p.strokeWidth, hasStroke = !!p.strokeColor && sw > 0;
    const hasFill = !!p.fillColor;
    scene.adopt(p);
    if (hasStroke && !hasFill) {
      // a stroked centre line: keep it as a line of its own width by outlining at that width
      const keep = scene.weight; scene.weight = sw; const r = p instanceof paper.Path ? scene.outline(p) : null; scene.weight = keep;
      out.push(r ?? p);
    } else out.push(p);
  }
  item.remove();
  if (o.fit && out.length) fitToBox(scene, out, 20, false);
  scene.commit(o.replace ? 'replace from file' : 'import');
  return out;
}
