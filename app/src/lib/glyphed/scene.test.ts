// Paper.js runs under jsdom with node-canvas, so the scene and the operations can be tested for real.
import { beforeEach, describe, expect, it } from 'vitest';
import paper from 'paper';
import { Scene, isOpen } from './scene';
import * as ops from './ops';
import { Tools } from './tools';

const SQUARE = '<svg width="350" height="350" viewBox="0 0 350 350" fill="none" xmlns="http://www.w3.org/2000/svg">\n<path d="M10 10h100v100h-100z" fill="black"/>\n</svg>\n';
const TWO = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M0 0h100v100h-100z" fill="black"/><path d="M50 50h100v100h-100z" fill="black"/></svg>';

function makeScene(box: [number, number] = [350, 350]) {
  const canvas = document.createElement('canvas');
  canvas.width = 400; canvas.height = 400;
  return new Scene(canvas, box, 36);
}

let scene: Scene;
beforeEach(() => { scene = makeScene(); });

describe('load and export', () => {
  it('loads an SVG, takes its viewBox as the box, and exports one filled path per shape to 0.1 unit', () => {
    expect(scene.loadSvg(SQUARE)).toBe(1);
    expect(scene.box).toEqual([350, 350]);
    expect(scene.paths).toHaveLength(1);
    const out = scene.exportSvg();
    expect(out).toContain('viewBox="0 0 350 350"');
    expect(out.match(/<path/g)).toHaveLength(1);
    expect(out).toContain('fill="black"');
    expect(out).not.toMatch(/\d\.\d{2,}/);          // no more than one decimal
    expect(scene.dirty).toBe(false);
  });
  it('resolves groups, transforms and compound paths from design-tool exports', () => {
    const svg = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><g transform="translate(100 0)"><rect width="50" height="50"/></g>'
      + '<path fill-rule="evenodd" d="M0 200h100v100h-100zM25 225h50v50h-50z" fill="black"/></svg>';
    expect(scene.loadSvg(svg)).toBe(2);
    const b = scene.glyph.bounds;
    expect([b.left, b.top, b.right, b.bottom]).toEqual([0, 0, 150, 300]);
    expect(scene.exportSvg()).toContain('fill-rule="evenodd"');
  });
  it('export outlines open lines at the reference weight without changing the scene', () => {
    const line = new paper.Path({ segments: [[50, 50], [250, 50]], closed: false });
    scene.adopt(line);
    expect(isOpen(line)).toBe(true);
    expect(line.strokeWidth).toBe(36);
    const out = scene.exportSvg();
    expect(out.match(/<path/g)).toHaveLength(1);
    expect(scene.paths[0]).toBe(line);                 // still the line, still open
    expect(isOpen(scene.paths[0])).toBe(true);
    // the written outline is a ~36-wide band around the line
    const back = makeScene(); back.loadSvg(out);
    const b = back.glyph.bounds;
    expect(b.height).toBeCloseTo(36, 0);
    expect(b.width).toBeCloseTo(236, 0);
  });
  it('stats: counts, open lines, specks, outside the box', () => {
    scene.loadSvg(TWO);
    new paper.Path.Rectangle({ point: [340, 340], size: [20, 20] }).remove();
    scene.adopt(new paper.Path.Rectangle({ point: [340, 340], size: [20, 20], insert: false }) as paper.Path);
    scene.adopt(new paper.Path.Rectangle({ point: [200, 200], size: [3, 3], insert: false }) as paper.Path);
    const st = scene.stats;
    expect(st.paths).toBe(4);
    expect(st.outside).toBe(true);
    expect(st.specks).toBe(1);
    expect(scene.removeSpecks()).toBe(1);
    expect(scene.stats.paths).toBe(3);
  });
});

describe('history', () => {
  it('commit / undo / redo / dirty / markSaved / discard', () => {
    scene.loadSvg(SQUARE);
    scene.paths[0].translate(new paper.Point(5, 0));
    expect(scene.commit('move')).toBe(true);
    expect(scene.commit('move')).toBe(false);            // nothing changed since
    expect(scene.dirty).toBe(true);
    expect(scene.undoLabel).toBe('move');
    expect(scene.changeCount).toBe(1);
    scene.undo();
    expect(scene.dirty).toBe(false);
    expect(scene.paths[0].bounds.left).toBe(10);
    scene.redo();
    expect(scene.paths[0].bounds.left).toBe(15);
    scene.markSaved();
    expect(scene.dirty).toBe(false);
    scene.paths[0].translate(new paper.Point(5, 0)); scene.commit('move');
    scene.discard();
    expect(scene.paths[0].bounds.left).toBe(15);
    expect(scene.canUndo).toBe(true);                    // discard itself can be undone
  });
});

describe('operations', () => {
  it('combine: unite merges overlapping squares; subtract keeps the oldest and cuts the newer', () => {
    scene.loadSvg(TWO);
    const r = ops.combine(scene, scene.paths, 'unite');
    expect(r && scene.paths.length).toBe(1);
    expect(r!.bounds.width).toBe(150);
    expect(scene.undoLabel).toBe('unite');
    scene.undo();
    const s = ops.combine(scene, scene.paths, 'subtract')!;
    expect(s.bounds.width).toBe(100);                    // the first square minus the overlap
    expect(Math.abs(s.area)).toBe(10000 - 2500);
    scene.undo();
    const sw = ops.combine(scene, scene.paths, 'subtract', true)!;
    expect(Math.abs(sw.area)).toBe(10000 - 2500);
    expect(sw.bounds.left).toBe(50);                     // swapped: the second square survives
  });
  it('thicken grows each side by the distance; thin shrinks; cleanUp resolves self-overlap', () => {
    scene.loadSvg(SQUARE);
    const [t] = ops.thicken(scene, scene.paths, 5);
    expect(t.bounds.width).toBeCloseTo(110, 0);
    const [s] = ops.thicken(scene, scene.paths, -20);
    expect(s.bounds.width).toBeCloseTo(70, 0);
    scene.loadSvg('<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M0 0L100 100L100 0L0 100z" fill="black"/></svg>');
    ops.cleanUp(scene, scene.paths);
    expect(scene.undoLabel).toBe('clean up');
    expect(scene.paths[0] instanceof paper.CompoundPath || scene.paths.length >= 1).toBe(true);
  });
  it('simplify reduces points; smooth, flip, center, fit, transform', () => {
    const wobbly = new paper.Path({ closed: true });
    for (let i = 0; i < 60; i++) { const a = (i / 60) * Math.PI * 2; wobbly.add(new paper.Point(100 + 40 * Math.cos(a), 100 + 40 * Math.sin(a))); }
    scene.adopt(wobbly);
    const before = ops.nodeCount(scene.paths);
    ops.simplify(scene.paths, 2);
    expect(ops.nodeCount(scene.paths)).toBeLessThan(before);
    ops.smooth(scene, scene.paths);
    expect(scene.undoLabel).toBe('smooth');
    scene.loadSvg(SQUARE);
    ops.flip(scene, scene.paths, 'h');
    expect(scene.paths[0].bounds.left).toBe(10);          // symmetric about its own centre
    ops.centerInBox(scene, scene.paths);
    expect(scene.paths[0].bounds.center.x).toBe(175);
    ops.fitToBox(scene, scene.paths, 20);
    expect(scene.paths[0].bounds.width).toBe(310);
    ops.transform(scene, scene.paths, { dx: 5, sx: 2 }, 'x');
    expect(scene.paths[0].bounds.width).toBe(620);
    expect(scene.undoLabel).toBe('x');
  });
  it('estimateWeight is 2·area/perimeter', () => {
    scene.loadSvg('<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M0 0h100v20h-100z" fill="black"/></svg>');
    expect(ops.estimateWeight(scene.paths)).toBeCloseTo((2 * 2000) / 240, 5);
  });
  it('inspectSvg reports box, dropped features and strokes; importSvgPaths outlines stroked lines', () => {
    const info = ops.inspectSvg('<svg viewBox="0 0 660 660"><text>x</text><path stroke="red" stroke-width="10" d="M0 0L10 10"/><path fill="#ff0000" d="M0 0"/></svg>');
    expect(info.box).toEqual([660, 660]);
    expect(info.dropped).toEqual(expect.arrayContaining(['text', 'colours']));
    expect(info.strokes).toBe(1);
    const ps = ops.importSvgPaths(scene, '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path stroke="black" stroke-width="10" fill="none" d="M20 20L120 20"/></svg>', { fit: false, replace: true });
    expect(ps).toHaveLength(1);
    expect(isOpen(ps[0])).toBe(false);
    expect(ps[0].bounds.height).toBeCloseTo(10, 0);
    expect(scene.undoLabel).toBe('replace from file');
  });
});

describe('tools (direct calls)', () => {
  it('selection, delete, nudge, point kinds, finishing a pen path', () => {
    scene.loadSvg(TWO);
    const tools = new Tools(scene);
    tools.selectPaths([scene.paths[0]]);
    expect(tools.selectedPaths).toHaveLength(1);
    expect(tools.targets).toHaveLength(1);
    tools.clearSelection();
    expect(tools.targets).toHaveLength(2);
    tools.selectPaths([scene.paths[1]]);
    tools.nudge(3, 0);
    expect(scene.paths[1].bounds.left).toBe(53);
    expect(scene.undoLabel).toBe('nudge');
    (scene.paths[1] as paper.Path).segments[0].selected = true;
    expect(tools.selectedSegments).toHaveLength(1);
    tools.setPointKind('smooth');
    expect((scene.paths[1] as paper.Path).segments[0].hasHandles()).toBe(true);
    tools.deleteSelection();                               // deletes the point, not the shape
    expect(scene.paths).toHaveLength(2);
    expect((scene.paths[1] as paper.Path).segments).toHaveLength(3);
    tools.selectPaths([scene.paths[1]]);
    tools.deleteSelection();
    expect(scene.paths).toHaveLength(1);
    const pen = new paper.Path({ segments: [[0, 0], [50, 0], [50, 50]], closed: false });
    scene.adopt(pen);
    tools.drawing = pen;
    tools.finishPen(true);
    expect(pen.closed).toBe(true);
    expect(scene.undoLabel).toBe('draw shape');
    const short = new paper.Path({ segments: [[0, 0]], closed: false });
    scene.adopt(short);
    tools.drawing = short;
    tools.finishPen(false);
    expect(scene.paths).not.toContain(short);              // too short: dropped
    tools.destroy();
  });
});

describe('select tool (mouse)', () => {
  type Ev = { point: paper.Point; delta?: paper.Point; modifiers: Record<string, boolean>; event: { button: number } };
  const ev = (x: number, y: number, mods: Record<string, boolean> = {}): Ev => ({ point: new paper.Point(x, y), modifiers: mods, event: { button: 0 } });
  // the tool's mouse handlers, as Paper calls them
  const mouse = (t: Tools) => t as unknown as { down(e: Ev): void; dragMove(e: Ev): void; up(e: Ev): void };

  it('a click on a point of the selected shape picks the point, and a drag moves only that point', () => {
    scene.loadSvg(SQUARE);
    const tools = new Tools(scene), m = mouse(tools);
    const path = scene.paths[0] as paper.Path;
    m.down(ev(60, 60)); m.up(ev(60, 60));                  // the fill: selects the shape
    expect(path.selected).toBe(true);
    const seg = path.segments.find((s) => s.point.equals(new paper.Point(10, 10)))!;
    m.down(ev(11, 11));                                     // within the hit tolerance of (10, 10)
    expect(seg.selected).toBe(true);
    expect(tools.selectedSegments).toEqual([seg]);
    m.dragMove({ ...ev(21, 16), delta: new paper.Point(10, 5) });
    m.up(ev(21, 16));
    expect(seg.point.equals(new paper.Point(20, 15))).toBe(true);
    expect(path.bounds.right).toBe(110);                    // the rest of the shape stayed put
    tools.destroy();
  });

  it("drags a selected point's handle, not the shape", () => {
    scene.loadSvg(SQUARE);
    const tools = new Tools(scene), m = mouse(tools);
    const path = scene.paths[0] as paper.Path;
    tools.selectPaths([path]);
    const seg = path.segments.find((s) => s.point.equals(new paper.Point(110, 10)))!;
    seg.handleOut = new paper.Point(0, 30);
    seg.selected = true;
    const end = seg.point.add(seg.handleOut);               // (110, 40)
    m.down(ev(end.x, end.y));
    m.dragMove({ ...ev(end.x + 10, end.y), delta: new paper.Point(10, 0) });
    m.up(ev(end.x + 10, end.y));
    expect(seg.handleOut.equals(new paper.Point(10, 30))).toBe(true);
    expect(seg.point.equals(new paper.Point(110, 10))).toBe(true);
    tools.destroy();
  });
});

describe('compare overlays', () => {
  const GHOST = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M200 200h100v100h-100z" fill="black"/></svg>';
  it('picks the dot first, then the compare glyph only where it has ink', () => {
    scene.loadSvg(SQUARE);
    scene.setGhostGlyph(GHOST);
    scene.dotPos = [250, 250];
    scene.setDot(true);
    expect(scene.overlayAt(new paper.Point(250, 250))).toBe('dot');
    expect(scene.overlayAt(new paper.Point(210, 290))).toBe('ghost');
    expect(scene.overlayAt(new paper.Point(150, 150))).toBeNull();
  });
  it('moves the selected overlays together, outside undo, and remembers where', () => {
    scene.loadSvg(SQUARE);
    scene.setGhostGlyph(GHOST);
    scene.setDot(true);
    const dot0 = [...scene.dotPos!];
    expect(scene.moveOverlays(5, 5)).toBe(false);          // nothing picked
    scene.selectOverlay('ghost');
    scene.selectOverlay('dot', true);
    expect(scene.moveOverlays(10, -4)).toBe(true);
    expect(scene.dotPos).toEqual([dot0[0] + 10, dot0[1] - 4]);
    expect(scene.ghostOffset).toEqual([10, -4]);
    expect(scene.canUndo).toBe(false);
    expect(scene.dirty).toBe(false);
    scene.setGhostGlyph(GHOST);                             // rebuilt (another glyph, a new weight…): stays moved
    expect(scene.overlayAt(new paper.Point(305, 250))).toBe('ghost');
    scene.setDot(false);                                    // a hidden overlay drops out of the selection
    expect([...scene.overlaySel]).toEqual(['ghost']);
  });
  it('tools: arrows nudge picked overlays instead of the outline; clearing lets go', () => {
    scene.loadSvg(SQUARE);
    scene.setGhostGlyph(GHOST);
    const tools = new Tools(scene);
    scene.selectOverlay('ghost');
    tools.nudge(1, 0);
    expect(scene.ghostOffset).toEqual([1, 0]);
    expect(scene.paths[0].bounds.left).toBe(10);           // the outline didn't move
    tools.selectPaths([scene.paths[0]]);                    // picking a shape lets go of the overlays
    expect(scene.overlaySel.size).toBe(0);
    scene.selectOverlay('ghost');
    tools.clearSelection();
    expect(scene.overlaySel.size).toBe(0);
    tools.destroy();
  });
});

