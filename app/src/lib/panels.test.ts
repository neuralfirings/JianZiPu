import { beforeEach, describe, expect, it } from 'vitest';
import { DOCK_HIDE_BELOW, DOCK_MIN, panels, editorPanels } from './panels.svelte';

beforeEach(() => { localStorage.clear(); panels.reset(); panels.mode = 'wide'; });

describe('panels store', () => {
  it('starts from the wide defaults and knows where each panel is', () => {
    expect(panels.isDefault).toBe(true);
    expect(panels.dockOf('spacing')).toBe('right');
    expect(panels.dockOf('tester')).toBe('bottom');
    expect(panels.isFolded('budget')).toBe(true);
    expect(panels.isFolded('spacing')).toBe(false);
  });
  it('move puts a panel at an index in another dock and persists', () => {
    panels.move('centering', 'left', 1);
    expect(panels.a.docks.left).toEqual(['types', 'centering', 'structure', 'pagecenter', 'budget']);
    expect(panels.a.docks.right).toEqual(['spacing']);
    expect(panels.isDefault).toBe(false);
    expect(JSON.parse(localStorage.getItem('jzp-panels-v1')!).wide.docks.left[1]).toBe('centering');
  });
  it('moving within a dock keeps the right order', () => {
    panels.move('budget', 'left', 0);
    expect(panels.a.docks.left).toEqual(['budget', 'types', 'structure', 'pagecenter']);
    panels.move('budget', 'left', 4);
    expect(panels.a.docks.left).toEqual(['types', 'structure', 'pagecenter', 'budget']);
  });
  it('nudge moves up and down and stops at the ends', () => {
    panels.nudge('types', -1);
    expect(panels.a.docks.left[0]).toBe('types');
    panels.nudge('types', 1);
    expect(panels.a.docks.left.slice(0, 2)).toEqual(['structure', 'types']);
  });
  it('fold toggles and persists', () => {
    panels.toggle('spacing');
    expect(panels.isFolded('spacing')).toBe(true);
    panels.setFolded('spacing', false);
    expect(panels.isFolded('spacing')).toBe(false);
  });
  it('setSize clamps to the minimum, hides below the threshold and keeps the pre-drag size', () => {
    panels.setSize('right', 100, 420);
    expect(panels.visible('right')).toBe(false);
    expect(panels.a.size.right).toBe(420);
    panels.show('right');
    expect(panels.visible('right')).toBe(true);
    expect(panels.a.size.right).toBe(420);
    panels.setSize('right', DOCK_MIN.right - 30);
    expect(panels.a.size.right).toBe(DOCK_MIN.right);
    expect(panels.visible('right')).toBe(true);
    panels.setSize('bottom', DOCK_HIDE_BELOW.bottom - 1);
    expect(panels.visible('bottom')).toBe(false);
    panels.show('bottom');
    expect(panels.a.size.bottom).toBeGreaterThanOrEqual(DOCK_MIN.bottom);
  });
  it('an empty dock is not visible; the two modes have separate arrangements', () => {
    panels.mode = 'narrow';
    expect(panels.visible('left')).toBe(false);
    expect(panels.dockOf('types')).toBe('right');
    panels.move('types', 'left', 0);
    panels.mode = 'wide';
    expect(panels.dockOf('types')).toBe('left');
    expect(panels.a.docks.left[0]).toBe('types');
    expect(panels.arr.narrow.docks.left).toEqual(['types']);
  });
  it('load tolerates garbage and fills in missing panels', () => {
    localStorage.setItem('jzp-panels-v1', JSON.stringify({ wide: { docks: { left: ['tester', 'bogus'], right: [], bottom: [] } } }));
    panels.loaded = false;
    panels.load();                      // picks the mode from window.innerWidth (jsdom: narrow)
    panels.mode = 'wide';
    expect(panels.a.docks.left[0]).toBe('tester');
    expect(panels.a.docks.left).not.toContain('bogus');
    const all = [...panels.a.docks.left, ...panels.a.docks.right, ...panels.a.docks.bottom].sort();
    expect(all).toEqual(['budget', 'centering', 'glyphs', 'pagecenter', 'spacing', 'structure', 'tester', 'types']);
  });
});

describe('glyph editor panels', () => {
  beforeEach(() => { editorPanels.reset(); editorPanels.mode = 'wide'; });
  it('keeps its own arrangement under its own key, apart from Layouts', () => {
    expect(editorPanels.dockOf('typing')).toBe('right');
    expect(editorPanels.dockOf('tester')).toBe('bottom');
    editorPanels.move('typing', 'bottom', 0);
    expect(editorPanels.a.docks.bottom[0]).toBe('typing');
    expect(JSON.parse(localStorage.getItem('jzp-editor-panels-v1')!).wide.docks.bottom[0]).toBe('typing');
    expect(panels.isDefault).toBe(true);                       // Layouts untouched
  });
  it('loads a saved arrangement, dropping unknown ids and adding new panels back', () => {
    localStorage.setItem('jzp-editor-panels-v1', JSON.stringify({ wide: { docks: { left: ['checks', 'nope'], right: ['selection'], bottom: [] }, folded: { checks: false } } }));
    editorPanels.loaded = false;
    editorPanels.load();
    editorPanels.mode = 'wide';
    expect(editorPanels.a.docks.left).toEqual(['checks']);
    expect(editorPanels.a.docks.right[0]).toBe('selection');
    const all = [...editorPanels.a.docks.left, ...editorPanels.a.docks.right, ...editorPanels.a.docks.bottom].sort();
    expect(all).toEqual(['checks', 'compare', 'glyph', 'selection', 'tester', 'trace', 'tryit', 'typing']);
  });
});

