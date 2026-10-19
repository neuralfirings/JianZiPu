import { describe, expect, it } from 'vitest';
import { applyRuleEdit, catches, chainFor, combosOf, entriesOf, isOtherwise, normalizeGap, presetsFor, shadowedBy, stepFor, uncovered } from './rules';
import type { Design, GapEntry, Layout } from './api';
import type { RuleEdit } from './editor.svelte';

const layout: Layout = {
  name: 'std', slots: [{ name: 'left', alternatives: [['left']] }, { name: 'right', alternatives: [['right']] }],
  relationships: [
    { axis: 'y', elem: 'right', base: 'left', gap: 10 },
    { axis: 'x', elem: 'right', base: 'left', gap: [{ when_elem: ['g1'], value: 5 }, { value: 0 }] },
    { axis: 'y', elem: 'right', base: null, gap: 100 }
  ]
} as unknown as Layout;
const design = { version: 2, center: { x: 500, y: 500 }, areas: {}, layouts: [layout] } as unknown as Design;

describe('gap entries', () => {
  it('a plain number is one otherwise entry', () => {
    expect(entriesOf(10)).toEqual([{ value: 10 }]);
    expect(isOtherwise({ value: 1 })).toBe(true);
    expect(isOtherwise({ when_elem: ['a'], value: 1 })).toBe(false);
  });
  it('normalizeGap collapses a lone otherwise and drops empty conditions', () => {
    expect(normalizeGap([{ value: 7, when_elem: [] }])).toBe(7);
    expect(normalizeGap([{ when_base: ['b'], value: 1 }, { value: 2 }])).toEqual([{ value: 1, when_base: ['b'] }, { value: 2 }]);
  });
  it('catches: empty side means any glyph', () => {
    const e: GapEntry = { when_elem: ['g1'], value: 0 };
    expect(catches(e, 'g1', null)).toBe(true);
    expect(catches(e, 'g2', 'x')).toBe(false);
    expect(catches({ value: 0 }, null, null)).toBe(true);
  });
});

describe('coverage and shadowing', () => {
  const entries: GapEntry[] = [{ when_elem: ['g1'], value: 5 }, { when_elem: ['g2'], when_base: ['b1'], value: 6 }];
  it('uncovered lists glyphs no unconditional-on-the-other-side entry reaches', () => {
    expect(uncovered(entries, 'elem', ['g1', 'g2', 'g3'])).toEqual(['g2', 'g3']);
    expect(uncovered([...entries, { value: 0 }], 'elem', ['g1', 'g2', 'g3'])).toEqual([]);
  });
  it('shadowedBy finds the earlier entry that would catch first', () => {
    expect(shadowedBy(entries, 2, 'elem', 'g1', [])).toBe(0);
    expect(shadowedBy(entries, 2, 'elem', 'g2', ['b2'])).toBe(-1);   // base b2 is not b1
    expect(shadowedBy(entries, 2, 'elem', 'g2', ['b1'])).toBe(1);
    expect(shadowedBy(entries, 0, 'elem', 'g1', [])).toBe(-1);
  });
  it('presetsFor splits whole and fractional position numbers', () => {
    expect(presetsFor(['md_7', 'md_7.5', 'md_8']).map((p) => p.glyphs)).toEqual([['md_7', 'md_8'], ['md_7.5']]);
    expect(presetsFor(['md_7', 'md_8'])).toEqual([]);
  });
});

describe('chainFor', () => {
  it('returns the relationships for the element on one axis, in file order', () => {
    const el = { name: 'right', el: 'right', area: 'right', slot: 'right', instance: 0 };
    expect(chainFor(layout, el, 'y').map((c) => c.index)).toEqual([0, 2]);
    expect(chainFor(layout, el, 'x').map((c) => c.index)).toEqual([1]);
  });
});

describe('rule edits', () => {
  const base: RuleEdit = { axis: 'x', relIndex: 1, entryIndex: null, insertAt: 0, whenElem: ['g2'], whenBase: [], value: 9, overlay: true, step: 0, liveDelta: 0 };
  it('a new rule lands at insertAt', () => {
    const d = applyRuleEdit(design, 'std', base);
    expect(d.layouts[0].relationships[1].gap).toEqual([{ when_elem: ['g2'], value: 9 }, { when_elem: ['g1'], value: 5 }, { value: 0 }]);
    expect(design.layouts[0].relationships[1].gap).toHaveLength(2);   // input untouched
  });
  it('editing an entry replaces it and can move it', () => {
    const d = applyRuleEdit(design, 'std', { ...base, entryIndex: 0, insertAt: 2, whenElem: ['g1', 'g3'], value: 4 });
    expect(d.layouts[0].relationships[1].gap).toEqual([{ value: 0 }, { when_elem: ['g1', 'g3'], value: 4 }]);
  });
  it('a plain-number relationship turns into a list; delta is applied and rounded', () => {
    const d = applyRuleEdit(design, 'std', { ...base, relIndex: 0, whenElem: ['g1'], value: 2.2 }, 0.6);
    expect(d.layouts[0].relationships[0].gap).toEqual([{ when_elem: ['g1'], value: 3 }, { value: 10 }]);
  });
});

describe('combosOf / stepFor', () => {
  it('unticked sides mean every glyph; step walks elem-major', () => {
    const re: RuleEdit = { axis: 'y', relIndex: 0, entryIndex: null, insertAt: 0, whenElem: [], whenBase: ['b2'], value: 0, overlay: false, step: 3, liveDelta: 0 };
    const c = combosOf(re, ['e1', 'e2', 'e3'], ['b1', 'b2']);
    expect(c.n).toBe(3);
    expect(c.k).toBe(0);                                         // 3 % 3
    expect(c.shown).toEqual({ elem: 'e1', base: 'b2' });
    expect(stepFor(c, 'elem', 'e3')).toBe(2);
  });
  it('negative steps wrap', () => {
    const re: RuleEdit = { axis: 'y', relIndex: 0, entryIndex: null, insertAt: 0, whenElem: ['a', 'b'], whenBase: ['x', 'y'], value: 0, overlay: false, step: -1, liveDelta: 0 };
    const c = combosOf(re, [], []);
    expect(c.k).toBe(3);
    expect(c.shown).toEqual({ elem: 'b', base: 'y' });
    expect(stepFor(c, 'base', 'x')).toBe(2);
  });
});
