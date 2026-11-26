// Copy, cut and paste in the glyph editor (GlyphEditor.copySelection / pasteShapes), on a real Paper.js scene.
import { beforeEach, describe, expect, it, vi } from 'vitest';
// the editor imports the image tracer, whose WASM build doesn't load under Node; these tests don't trace
vi.mock('esm-potrace-wasm', () => ({ init: async () => {}, potrace: async () => '' }));
import paper from 'paper';
import { Scene } from './scene';
import { Tools } from './tools';
import { GlyphEditor } from './editor.svelte';

const TWO = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M0 0h100v100h-100z" fill="black"/><path d="M200 200h50v50h-50z" fill="black"/></svg>';

function editor(name: string, svg: string | null = TWO) {
  const canvas = document.createElement('canvas');
  canvas.width = 400; canvas.height = 400;
  const ed = new GlyphEditor();
  ed.scene = new Scene(canvas, [350, 350], 36);
  ed.tools = new Tools(ed.scene);
  ed.name = name;
  if (svg) ed.scene.loadSvg(svg);
  return ed;
}
const box = (p: paper.Item) => [p.bounds.left, p.bounds.top, p.bounds.width, p.bounds.height].map(Math.round);

let ed: GlyphEditor;
beforeEach(() => { ed = editor('md_a'); });

describe('copy and paste', () => {
  it('copies only the selected shapes, as SVG marked with the glyph', () => {
    expect(ed.copySelection()).toBeNull();                       // nothing selected
    ed.tools!.selectPaths([ed.scene!.paths[1]]);
    const r = ed.copySelection()!;
    expect(r.n).toBe(1);
    expect(r.svg).toContain('data-jzp-shapes="md_a"');
    expect(r.svg.match(/<path/g)).toHaveLength(1);
    expect(ed.scene!.paths).toHaveLength(2);                     // a copy leaves them
  });
  it('pastes into the same glyph a step down and right, further each time, selected, one undo step each', () => {
    ed.tools!.selectPaths([ed.scene!.paths[1]]);
    const { svg } = ed.copySelection()!;
    expect(ed.pasteShapes(svg)).toBe(1);
    expect(ed.scene!.paths).toHaveLength(3);
    expect(box(ed.scene!.paths[2])).toEqual([220, 220, 50, 50]);
    expect(ed.tools!.selectedPaths).toEqual([ed.scene!.paths[2]]);
    ed.pasteShapes(svg);
    expect(box(ed.scene!.paths[3])).toEqual([240, 240, 50, 50]);
    ed.undo();
    expect(ed.scene!.paths).toHaveLength(3);
  });
  it('cut takes them out (one undo step) and pastes them back in place', () => {
    ed.tools!.selectPaths([ed.scene!.paths[0]]);
    const { svg } = ed.copySelection(true)!;
    expect(ed.scene!.paths).toHaveLength(1);
    ed.pasteShapes(svg);
    expect(box(ed.scene!.paths[1])).toEqual([0, 0, 100, 100]);
  });
  it('pastes into another glyph where they were', () => {
    ed.tools!.selectPaths(ed.scene!.paths);
    const { svg } = ed.copySelection()!;
    const other = editor('md_b', null);
    expect(other.pasteShapes(svg)).toBe(2);
    expect(other.scene!.paths.map(box)).toEqual([[0, 0, 100, 100], [200, 200, 50, 50]]);
  });
  it('keeps an open line a line (copied here), and takes the SVG of a copy from another tab', () => {
    const line = new paper.Path({ segments: [[10, 300], [100, 300]], closed: false });
    ed.scene!.adopt(line);
    ed.tools!.selectPaths([line]);
    const { svg } = ed.copySelection()!;
    ed.pasteShapes(svg);
    const pasted = ed.scene!.paths.at(-1) as paper.Path;
    expect(pasted.closed).toBe(false);
    // another tab: only the SVG on the clipboard, written by a copy there (its lines as outlines)
    const other = editor('md_c', null);
    const fromTab = svg.replace('md_a', 'md_z');                // not this tab's copy
    expect(other.pasteShapes(fromTab)).toBe(1);
    expect((other.scene!.paths[0] as paper.Path).closed).toBe(true);
  });
  it("leaves SVG that wasn't copied in the editor to the Import dialog", () => {
    expect(ed.pasteShapes(TWO)).toBe(0);
    expect(ed.scene!.paths).toHaveLength(2);
  });
});
