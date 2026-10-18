import { describe, expect, it } from 'vitest';
import { anchorNames, choiceForNames, defaultChoice, elementLabel, elementNames, shapeElements, slotIsSimple } from './shape';
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
