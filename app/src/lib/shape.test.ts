import { describe, expect, it } from 'vitest';
import { anchorNames, choiceForNames, defaultChoice, elementLabel, elementNames, shapeElements, slotIsSimple, wordPage, canvasBox, labelWidth, placeLabels, clampZoom, zoomScroll, edgeBar, barLength, barsCoincide } from './shape';
import type { Layout } from './api';

const vert: Layout = {
  name: 'vert',
  slots: [
    { name: 'fy', alternatives: [['fy']], optional: true },
    { name: 'row', alternatives: [['char'], ['left', 'hui']], repeat: [1, 4] },
    { name: 'col', alternatives: [['colon:col']] }
  ],
  relationships: []
} as unknown as Layout;

describe('choices and elements', () => {
  it('defaultChoice picks option 0 and two rows for repeats', () => {
    expect(defaultChoice(vert)).toEqual([0, [0, 0], 0]);
  });
  it('shapeElements names repeated rows el@n and resolves el:area', () => {
    const els = shapeElements(vert, [null, [0, 1], 0]);
    expect(els.map((e) => e.name)).toEqual(['char@1', 'left@2', 'hui@2', 'colon']);
    expect(els[3]).toMatchObject({ el: 'colon', area: 'col', slot: 'col', instance: 0 });
    expect(els[1]).toMatchObject({ el: 'left', area: 'left', slot: 'row', instance: 2 });
  });
  it('choiceForNames inverts shapeElements', () => {
    const names = ['fy', 'left@1', 'hui@1', 'char@2', 'colon'];
    const c = choiceForNames(vert, names);
    expect(c).toEqual([0, [1, 0], 0]);
    expect(shapeElements(vert, c).map((e) => e.name)).toEqual(names);
    expect(choiceForNames(vert, ['char@1', 'colon'])).toEqual([null, [0], 0]);
  });
  it('elementNames and labels', () => {
    expect(elementNames(vert).map((e) => e.name)).toEqual(['fy', 'char', 'left', 'hui', 'colon']);
    const label = (a: string) => ({ fy: 'Harmonic', col: 'Colon', left: 'Left' } as Record<string, string>)[a] ?? a;
    expect(elementLabel(vert, 'left@2', label)).toBe('Left, row 2');
    expect(elementLabel(vert, 'colon', label)).toBe('Colon (colon)');
    expect(slotIsSimple(vert.slots[0])).toBe(true);
    expect(slotIsSimple(vert.slots[1])).toBe(false);
  });
});

describe('anchorNames', () => {
  it('first part starts a chain; an advancing part (colon) starts a new one and is never an anchor', () => {
    const els = [{ name: 'a', area: 'x' }, { name: 'b', area: 'x' }, { name: 'colon', area: 'col' }, { name: 'c', area: 'x' }];
    expect([...anchorNames(els, { x: {}, col: { advance: 1000 } })]).toEqual(['a', 'c']);
  });
});

describe('wordPage', () => {
  const el = (x: number, w: number) => ({ x, size: [w, w] as [number, number] });
  it('gives a vertical word the same one-em page as a standard word', () => {
    // :s9banlun3: the colon box spans the em and advances 1000
    const vertical = { advance: 1000, pieces: [{ elements: [el(0, 1000), el(150, 350), el(500, 350), el(325, 350)] }] };
    const standard = { advance: 0, pieces: [{ elements: [el(150, 350), el(500, 350), el(170, 660)] }] };
    expect(wordPage(vertical)).toEqual([0, 1000]);
    expect(wordPage(standard)).toEqual([0, 1000]);
  });
  it('widens for parts past the em and for trailing advance', () => {
    expect(wordPage({ advance: 0, pieces: [{ elements: [el(900, 350)] }] })).toEqual([0, 1250]);
    expect(wordPage({ advance: 2000, pieces: [] })).toEqual([0, 2000]);
  });
});

describe('canvasBox', () => {
  // :s9banlun3 and s9banlun3 as the server positions them
  const vertical = [
    { x: 0, y: 510, size: [1000, 1000] as [number, number], glyph: 'blank_colon' },
    { x: 150, y: 510, size: [350, 350] as [number, number], glyph: 'md_ming' },
    { x: 325, y: -260, size: [350, 350] as [number, number], glyph: 'md_3' }
  ];
  const standard = [
    { x: 150, y: 507.5, size: [350, 350] as [number, number], glyph: 'md_ming' },
    { x: 170, y: -182.5, size: [660, 660] as [number, number], glyph: 'lg_banlun' },
    { x: 325, y: -257.5, size: [350, 350] as [number, number], glyph: 'md_3' }
  ];
  const page = { page: [0, 1000] as [number, number], pageHeight: [-500, 1100] as [number, number], showPage: true, fit: false };
  const ink = (g: string) => g !== 'blank_colon';
  it('gives a vertical word the same page as a standard word: the colon spacer has no ink', () => {
    expect(canvasBox(vertical, page, ink)).toEqual(canvasBox(standard, page, ink));
    expect(canvasBox(standard, page, ink)).toEqual({ x: 0, y: -1100, w: 1000, h: 1600 });
  });
  it('still frames the spacer box in the editors', () => {
    expect(canvasBox(vertical, { ...page, showPage: false, fit: true }, ink).h).toBe(1510 + 260 + 120);
  });
});

describe('canvas labels', () => {
  it('measures CJK at a full em and the rest narrower', () => {
    expect(labelWidth('徽', 20)).toBe(20);
    expect(labelWidth('ab', 20)).toBeCloseTo(22);
  });
  it('keeps fixed labels in place and steps others down until clear', () => {
    const dy = placeLabels([
      { x: 0, y: 0, w: 100, h: 10, fixed: true },
      { x: 50, y: 0, w: 100, h: 10 },
      { x: 60, y: 0, w: 100, h: 10 },
      { x: 500, y: 0, w: 100, h: 10 }
    ]);
    expect(dy[0]).toBe(0);
    expect(dy[1]).toBeCloseTo(11.5);
    expect(dy[2]).toBeCloseTo(23);
    expect(dy[3]).toBe(0);
  });
  it('places fixed labels first even when listed later', () => {
    const dy = placeLabels([{ x: 0, y: 0, w: 10, h: 10 }, { x: 0, y: 0, w: 10, h: 10, fixed: true }]);
    expect(dy).toEqual([11.5, 0]);
  });
});

describe('canvas zoom', () => {
  it('clamps to 25 %–800 %', () => {
    expect(clampZoom(0.1)).toBe(0.25);
    expect(clampZoom(20)).toBe(8);
    expect(clampZoom(1.25 * 1.25)).toBe(1.563);
  });
  it('keeps the point under the pointer still', () => {
    // content x under the pointer: 100 scrolled + 50 in = 150; doubled → 300, minus 50 visible = 250
    expect(zoomScroll(100, 50, 2)).toBe(250);
    expect(zoomScroll(0, 50, 0.5)).toBe(0);
  });
});

describe('edge bars', () => {
  const b = { x: 100, y: 0, size: [400, 200] as [number, number] };
  it('sits just inside the named edge, centred on the arrow', () => {
    expect(edgeBar(b, 'top', 300, 240)).toEqual({ x1: 180, y1: 200, x2: 420, y2: 200 });
    expect(edgeBar(b, 'top', 300, 240, 5)).toEqual({ x1: 180, y1: 195, x2: 420, y2: 195 });
    expect(edgeBar(b, 'left', 100, 100, 5)).toEqual({ x1: 105, y1: 50, x2: 105, y2: 150 });
  });
  it('stays inside the edge near a corner and never outgrows it', () => {
    expect(edgeBar(b, 'bottom', 110, 240)).toEqual({ x1: 100, y1: 0, x2: 340, y2: 0 });
    expect(edgeBar(b, 'right', 500, 120)).toEqual({ x1: 500, y1: 80, x2: 500, y2: 200 });
    expect(edgeBar(b, 'right', 100, 999)).toEqual({ x1: 500, y1: 0, x2: 500, y2: 200 });
  });
  it('gives both bars of a rule one length: 60 % of the shorter edge, capped', () => {
    const small = { x: 0, y: 0, size: [100, 300] as [number, number] };
    expect(barLength([{ box: b, edge: 'top' }, { box: small, edge: 'top' }], 1000)).toBe(60);
    expect(barLength([{ box: b, edge: 'left' }, { box: small, edge: 'left' }], 1000)).toBe(120);
    expect(barLength([{ box: b, edge: 'top' }], 50)).toBe(50);
  });
});

describe('touching edge bars', () => {
  it('coincide only on the same line with overlapping spans', () => {
    const a = { x1: 0, y1: 100, x2: 50, y2: 100 };
    expect(barsCoincide(a, { x1: 40, y1: 101, x2: 90, y2: 101 }, 2)).toBe(true);
    expect(barsCoincide(a, { x1: 40, y1: 110, x2: 90, y2: 110 }, 2)).toBe(false);
    expect(barsCoincide(a, { x1: 60, y1: 100, x2: 90, y2: 100 }, 2)).toBe(false);
    expect(barsCoincide(a, { x1: 10, y1: 0, x2: 10, y2: 200 }, 2)).toBe(false);
  });
});
