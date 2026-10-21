// App state with glyph files in the undo history (Review → Apply), local Save of merged glyph
// files, and the hosted draft: load on top of the font, save, "saved elsewhere", builds, update.
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Design } from './api';

const SVG = (d: string) => `<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="${d}"/></svg>`;
const design = (): Design => ({
  version: 2, center: { x: 500, y: 300 },
  areas: { left: { label: 'Left hand', size: [350, 350], glyphs: ['md_ming'] } },
  layouts: [{ name: 'standard', slots: [{ name: 'left', alternatives: [['left']] }], relationships: [], center: {} }]
} as unknown as Design);

const disk = { md_ming: SVG('M0 0h10v10z'), md_7: SVG('M1 1h10v10z') };
const api = vi.hoisted(() => ({
  design: vi.fn(), glyphs: vi.fn(), svgs: vi.fn(), base: vi.fn(), check: vi.fn(async () => ({ ok: true, warnings: [] })),
  saveSvg: vi.fn(async () => ({ ok: true })), deleteSvg: vi.fn(async () => ({ ok: true })),
  saveDesign: vi.fn(async () => ({ ok: true, hash: 'd1' })), saveGlyphs: vi.fn(async () => ({ ok: true, hash: 'c1' }))
}));
vi.mock('./api', () => ({ api }));
const store = vi.hoisted(() => ({ draft: null as null | { text: string; stamp: string }, n: 0 }));
vi.mock('./drafts', async () => {
  const { fromJson, toJson } = await import('./bundle');
  class DraftConflict extends Error {}
  return {
    DraftConflict,
    draftStamp: vi.fn(async () => store.draft?.stamp ?? null),
    loadDraft: vi.fn(async () => (store.draft ? { bundle: fromJson(store.draft.text), stamp: store.draft.stamp } : null)),
    // like save_draft(): only over the stamp the caller loaded
    saveDraft: vi.fn(async (_c: unknown, _u: string, b: Parameters<typeof toJson>[0], expected: string | null) => {
      if (expected !== (store.draft?.stamp ?? null)) throw new DraftConflict();
      store.draft = { text: toJson(b), stamp: `t${++store.n}` };
      return store.draft.stamp;
    }),
    deleteDraft: vi.fn(async () => { store.draft = null; }),
    loadRequestDraft: vi.fn(async () => null),
    saveRequestDraft: vi.fn(async () => {})
  };
});
const hosted = vi.hoisted(() => ({ isHosted: false, client: {}, user: { id: 'u1', name: 'Mei', email: 'mei@example.com' } as { id: string; name: string; email: string } | null, signedOut: false, firstName: 'Mei' }));
vi.mock('./hosted.svelte', () => ({ hosted }));

const { app, withPending } = await import('./state.svelte');

function serve(d = design(), svgs: Record<string, string> = disk) {
  api.design.mockResolvedValue({ design: d, hash: 'd0', warnings: [], stats: null });
  api.glyphs.mockResolvedValue({ fields: [], glyphs: [{ glyph: 'md_ming', svg: true, areas: ['left'], latin: 'ming' }, { glyph: 'md_7', svg: true, areas: [] }], control: [], order: ['md_ming'], hash: 'c0' });
  api.svgs.mockResolvedValue({ ...svgs });
  api.base.mockResolvedValue({ commit: 'abc', date: '2026-10-15T10:00:00Z', design_hash: 'd0', csv_hash: 'c0', svg_hashes: {} });
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  store.draft = null;
  hosted.isHosted = false;
  serve();
});

describe('the error banner offers the right next step', () => {
  it('a failed Save offers Try again, and a good save clears it', async () => {
    await app.load();
    app.edit('x', (d) => { d.center.x = 510; });
    api.saveDesign.mockResolvedValueOnce({ ok: false, error: 'disk full' } as never);
    expect(await app.save()).toBe(false);
    expect(app.error).toBe('Not saved: disk full');
    expect(app.errorFix).toBe('save');
    app.recheck();
    await new Promise((r) => setTimeout(r, 350));          // the check after an edit passes…
    expect(app.error).toBe('Not saved: disk full');        // …and leaves the save's error alone
    api.saveDesign.mockRejectedValueOnce(new Error('Failed to fetch'));
    expect(await app.save()).toBe(false);
    expect(app.error).toMatch(/^Not saved: can't reach the web server/);
    expect(await app.save()).toBe(true);
    expect(app.error).toBeNull();
  });
});

describe('glyph files wait for Save', () => {
  it('overlays pending writes and deletes', () => {
    expect(withPending({ a: '1', b: '2' }, { b: null, c: '3' })).toEqual({ a: '1', c: '3' });
  });

  it('Apply is one undo step with glyph files, and Save writes them first', async () => {
    await app.load();
    expect(app.dirty).toBe(false);
    const d = design();
    d.areas.left.glyphs.push('md_new');
    app.applyChanges('From Mei: 3 changes', { design: d, svgWrites: { md_new: SVG('M3 3h9v9z') }, svgDeletes: ['md_7'] });
    expect(app.pendingSvgs).toEqual({ md_new: SVG('M3 3h9v9z'), md_7: null });
    expect(Object.keys(app.svgs).sort()).toEqual(['md_ming', 'md_new']);
    expect(app.glyphs.find((g) => g.glyph === 'md_new')?.svg).toBe(true);
    expect(app.extraGlyphs).toEqual(['md_new']);
    expect(app.dirty).toBe(true);

    app.undo();
    expect(app.pendingSvgs).toEqual({});
    expect(app.svgs).toEqual(disk);
    expect(app.glyphs.some((g) => g.glyph === 'md_new')).toBe(false);
    expect(app.dirty).toBe(false);
    app.redo();
    expect(app.svgsDirty).toBe(true);

    expect(await app.save()).toBe(true);
    expect(api.saveSvg).toHaveBeenCalledWith('md_new', SVG('M3 3h9v9z'), null, true);
    expect(api.deleteSvg).toHaveBeenCalledWith('md_7');
    expect(api.saveSvg.mock.invocationCallOrder[0]).toBeLessThan(api.saveDesign.mock.invocationCallOrder[0]);
    expect(app.dirty).toBe(false);
    expect(app.savedSvgs.md_new).toBe(SVG('M3 3h9v9z'));
  });

  it('writing the saved outline back is not a change', async () => {
    await app.load();
    app.applyChanges('same', { svgWrites: { md_7: disk.md_7 } });
    expect(app.svgsDirty).toBe(false);
  });

  it('unsaved glyph files survive a reload of the page', async () => {
    await app.load();
    app.applyChanges('From Mei', { svgWrites: { md_new: SVG('M3 3h9v9z') } });
    await app.load();
    expect(app.draftRestored).toBe(true);
    expect(app.pendingSvgs).toEqual({ md_new: SVG('M3 3h9v9z') });
  });
});

describe('hosted draft', () => {
  beforeEach(() => { hosted.isHosted = true; });

  it('starts from the font, saves the draft, and loads it back on top of the font', async () => {
    await app.load();
    expect(app.draftStamp).toBeNull();
    expect(app.draftBase?.version.date).toBe('2026-10-15T10:00:00Z');
    app.applyChanges('Glyph md_7: new outline', { svgWrites: { md_7: SVG('M1 1h20v20z') } });
    app.edit('Area left: resize', (d) => { d.areas.left.size = [380, 350]; });
    expect(await app.save()).toBe(true);
    expect(api.saveDesign).not.toHaveBeenCalled();
    expect(api.saveSvg).not.toHaveBeenCalled();
    expect(app.draftStamp).toBe('t1');
    expect(app.dirty).toBe(false);
    expect(app.buildInputs()).toMatchObject({ svgs: { md_7: SVG('M1 1h20v20z') }, deleted: [] });

    // next visit: the font has a new outline for a glyph the draft never touched
    serve(design(), { ...disk, md_ming: SVG('M0 0h99v99z') });
    await app.load();
    expect(app.design!.areas.left.size).toEqual([380, 350]);
    expect(app.svgs.md_7).toBe(SVG('M1 1h20v20z'));
    expect(app.svgs.md_ming).toBe(SVG('M0 0h99v99z'));    // rides the font
    expect(app.dirty).toBe(false);
    expect(app.fontMoved).toBe(false);
  });

  it('counts rules and skipped shapes again for a loaded draft', async () => {
    await app.load();
    app.edit('Area left: resize', (d) => { d.areas.left.size = [380, 350]; });
    await app.save();
    api.check.mockClear();
    await app.load();
    await new Promise((ok) => setTimeout(ok, 350));
    expect(api.check).toHaveBeenCalledWith(expect.objectContaining({ areas: expect.objectContaining({ left: expect.objectContaining({ size: [380, 350] }) }) }));
  });

  it('undoes one change of the draft as one step, leaving the others', async () => {
    const { diffBundle, revertItems } = await import('./merge');
    await app.load();
    app.edit('Area left: resize', (d) => { d.areas.left.size = [380, 350]; });
    app.edit('Page center', (d) => { d.center.x = 510; });
    const b = app.bundle();
    const items = diffBundle(b, { design: b.base.design, typing: b.base.typing, svgs: app.mainSvgs });
    const area = items.filter((i) => i.id === 'design:area:left');
    app.applyChanges('Undo: Area · Left hand', revertItems(area, { design: app.design!, typing: app.typing, svgs: app.svgs }));
    expect(app.design!.areas.left.size).toEqual([350, 350]);
    expect(app.design!.center.x).toBe(510);
    app.undo();
    expect(app.design!.areas.left.size).toEqual([380, 350]);
  });

  it('refuses edits to a change a sent Change Request holds, but lets the font update it', async () => {
    await app.load();
    app.requests = [{ id: 'r1', title: 'Wider left', status: 'sent', item_ids: ['design:area:left'], decisions: {}, created_at: '2026-10-20T10:00:00Z' } as never];
    app.edit('Area left: resize', (d) => { d.areas.left.size = [380, 350]; });
    expect(app.design!.areas.left.size).toEqual([350, 350]);          // refused
    app.edit('Page center', (d) => { d.center.x = 510; });
    expect(app.design!.center.x).toBe(510);                           // anything else is fine
    app.applyChanges('From a .zip', { design: { ...app.design!, areas: { ...app.design!.areas, left: { ...app.design!.areas.left, label: 'L' } } } });
    expect(app.design!.areas.left.label).toBe('Left hand');            // refused too
    expect(app.lockMessage('design:area:left')).toMatch(/^The area Left hand is in your Change Request "Wider left", sent /);
    const moved = design();
    moved.areas.left.size = [360, 350];
    app.applyChanges('Update to the font', { design: moved, draftBase: { ...app.draftBase!, design: moved } });
    expect(app.design!.areas.left.size).toEqual([360, 350]);          // the font's own update comes in
    app.requests = [];
  });

  it('refuses to overwrite a draft saved elsewhere unless told to', async () => {
    await app.load();
    store.draft = { text: '', stamp: 'other' };
    app.edit('x', (d) => { d.center.x = 510; });
    expect(await app.save()).toBe(false);
    expect(app.savedElsewhere).toBe('other');
    expect(await app.save(true)).toBe(true);
    expect(app.savedElsewhere).toBeNull();
  });

  it('keeps edits in the browser when the save fails, and retries', async () => {
    await app.load();
    const drafts = await import('./drafts');
    vi.mocked(drafts.saveDraft).mockRejectedValueOnce(new Error('Failed to fetch'));
    app.edit('x', (d) => { d.center.x = 510; });
    expect(await app.save()).toBe(false);
    expect(app.offline).toBe(true);
    expect(app.saveRefused).toBeNull();
    expect(app.dirty).toBe(true);
    expect(await app.save()).toBe(true);
    expect(app.offline).toBe(false);
  });

  it("tells a refused save from being offline", async () => {
    await app.load();
    const drafts = await import('./drafts');
    vi.mocked(drafts.saveDraft).mockRejectedValueOnce(new Error('new row violates row-level security policy'));
    app.edit('x', (d) => { d.center.x = 510; });
    expect(await app.save()).toBe(false);
    expect(app.offline).toBe(false);
    expect(app.saveRefused).toBe('new row violates row-level security policy');
    expect(app.dirty).toBe(true);
    expect(await app.save()).toBe(true);
    expect(app.saveRefused).toBeNull();
  });

  it("says a stored draft can't be opened, rather than that the server is away", async () => {
    store.draft = { text: '{"manifest":', stamp: 't9' };
    await app.load();
    expect(app.error).toMatch(/^Your saved draft can't be opened: The stored draft is not valid JSON\. It is still stored/);
    expect(app.errorFix).toBe('feedback');
    store.draft = { text: JSON.stringify({ manifest: { kind: 'jzp-draft', format: 999 } }), stamp: 't9' };
    await app.load();
    expect(app.error).toMatch(/newer version of the Builder.*Reload the page/);
    expect(app.errorFix).toBe('reload');
    api.design.mockRejectedValueOnce(new Error('Failed to fetch'));
    store.draft = null;
    await app.load();
    expect(app.error).toMatch(/taking a break/);
    expect(app.errorFix).toBe('load');
  });

  it('notices the font moved and updates the draft in one undo step', async () => {
    await app.load();
    app.applyChanges('Glyph md_7', { svgWrites: { md_7: SVG('M1 1h20v20z') } });
    await app.save();
    const moved = design();
    moved.areas.left.size = [360, 350];
    serve(moved, { ...disk, md_7: SVG('M1 1h40v40z') });
    api.base.mockResolvedValue({ commit: 'def', date: '2026-10-18T10:00:00Z', design_hash: 'd2', csv_hash: 'c0', svg_hashes: {} });
    await app.load();
    expect(app.fontMoved).toBe(true);
    const items = app.fontUpdate();
    expect(items.map((i) => [i.id, i.conflict])).toEqual([['glyph:md_7', true], ['design:area:left', false]]);
    const r = await app.updateToFont(items, { 'glyph:md_7': false, 'design:area:left': true }, 'Update to the font of 18 Oct');
    expect(r).toEqual({ came: 1, kept: 1 });
    expect(app.design!.areas.left.size).toEqual([360, 350]);
    expect(app.svgs.md_7).toBe(SVG('M1 1h20v20z'));
    expect(app.fontMoved).toBe(false);
    expect(app.draftBase?.version.date).toBe('2026-10-18T10:00:00Z');
    app.undo();
    expect(app.fontMoved).toBe(true);
    expect(app.design!.areas.left.size).toEqual([350, 350]);
  });
});
