// @vitest-environment node
import { describe, expect, it } from 'vitest';
import type { Design } from './api';
import { makeBundle } from './bundle';
import { commitMessage, forRelease, missing, nextVersion, releaseNotes, unreleasedLines } from './release';
import type { ChangeRequest } from './requests';
import { applyMerge } from './merge';

const design = (): Design => ({
  version: 2, center: { x: 500, y: 300 },
  areas: { hui: { label: '徽', size: [350, 350], glyphs: ['md_7'] }, left: { label: 'Left', size: [350, 350], glyphs: [] } },
  layouts: []
} as unknown as Design);

function req(o: Partial<ChangeRequest>): ChangeRequest {
  const d = design();
  d.areas.hui.size = [380, 350];
  d.areas.left.size = [300, 300];
  const bundle = makeBundle({ design: d, typing: {}, svgs: {}, baseDesign: design(), baseTyping: {}, baseSvgs: {}, base: { commit: 'a', design_hash: 'd', csv_hash: 'c' }, author: {} });
  return {
    id: 'r1', author: 'u1', title: 'Hui spacing', notes: '', credit: 'Mei Chen', bundle, item_ids: ['design:area:hui', 'design:area:left'],
    base_commit: 'a', status: 'in_review', decisions: { 'design:area:hui': 'keep', 'design:area:left': 'skip' }, reply: '', release: null,
    created_at: '2026-10-20T10:00:00Z', updated_at: '', reviewed_at: null, released_at: null, author_name: 'Mei', ...o
  };
}

describe('release candidate', () => {
  it('numbers the next minor release', () => {
    expect(nextVersion('3.100')).toBe('3.200');
    expect(nextVersion('3.201')).toBe('3.300');
    expect(nextVersion('3.900')).toBe('4.000');
    expect(nextVersion(null)).toBe('3.200');
  });
  it('takes reviewed requests with kept changes, and those already in this candidate', () => {
    const rs = [req({ id: 'a', created_at: '2026-10-21' }), req({ id: 'b', created_at: '2026-10-19' }),
      req({ id: 'c', decisions: { 'design:area:hui': 'skip' } }), req({ id: 'd', status: 'in_candidate', release: '3.200' }),
      req({ id: 'e', status: 'in_candidate', release: '3.300' }), req({ id: 'f', status: 'sent', decisions: {} })];
    expect(forRelease(rs, '3.200').map((r) => r.id)).toEqual(['b', 'd', 'a']);
  });
  it('knows when a request’s kept changes are in, and leaves its skipped ones out', () => {
    const r = req({});
    const cur = { design: design(), typing: {}, svgs: {} };
    const todo = missing(r, {}, cur);
    expect(todo.map((i) => i.id)).toEqual(['design:area:hui']);
    const after = applyMerge(todo, { 'design:area:hui': true }, cur);
    expect(missing(r, {}, { ...cur, design: after.design })).toEqual([]);
  });
  it('writes the changelog entry and the commit message with credit', () => {
    const rs = [req({}), req({ id: 'r2', title: 'New glyph 歴', credit: '' })];
    expect(releaseNotes(rs)).toBe('### Changed\n\n- Hui spacing (thanks to Mei Chen)\n- New glyph 歴\n');
    expect(commitMessage('3.200', rs).split('\n')[0]).toBe('3.200: changes from 2 Change Requests');
    expect(commitMessage('3.200', rs)).toContain('- Hui spacing (Mei, 1 of 2 kept)');
  });
});

describe('changes queued for the next release', () => {
  const queued = '### Added\n\n- `shang34` gives the same as `:shang34`\n';
  it('starts the entry from the queued lines, then the requests', () => {
    expect(releaseNotes([req({})], queued)).toBe('### Added\n\n- `shang34` gives the same as `:shang34`\n\n### Changed\n\n- Hui spacing (thanks to Mei Chen)\n');
    expect(releaseNotes([], queued)).toBe('### Added\n\n- `shang34` gives the same as `:shang34`\n');
  });
  it("a second candidate keeps the first one's entry and adds only what's new", () => {
    const previous = '### Added\n\n- `shang34` gives the same as `:shang34`\n\n### Changed\n\n- Hui spacing (thanks to Mei Chen)';
    const later = '### Fixed\n\n- chord spacing';
    expect(releaseNotes([req({}), req({ id: 'r2', title: 'New glyph 歴', credit: '' })], later, previous)).toBe(
      '### Added\n\n- `shang34` gives the same as `:shang34`\n\n### Changed\n\n- Hui spacing (thanks to Mei Chen)\n- New glyph 歴\n\n### Fixed\n\n- chord spacing\n');
  });
  it('lists the queued lines for Build & test', () => {
    expect(unreleasedLines(queued)).toEqual(['`shang34` gives the same as `:shang34`']);
    expect(unreleasedLines('')).toEqual([]);
    expect(unreleasedLines(undefined)).toEqual([]);
  });
});
