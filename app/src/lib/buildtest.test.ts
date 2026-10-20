import { describe, it, expect } from 'vitest';
import { parseView, pickBuild, testerRedirect } from './buildtest';
import type { Build } from './api';

const b = (id: string): Build => ({ id, time: 0, bytes: 1, ok: true, seconds: 1, url: `/api/builds/${id}/JianZiPu.ttf`, file: '' });

describe('parseView', () => {
  it('is the words view unless the link asks for text', () => {
    expect(parseView(null)).toBe('words');
    expect(parseView('nonsense')).toBe('words');
    expect(parseView('text')).toBe('text');
  });
});

describe('pickBuild', () => {
  const builds = [b('b3'), b('b2'), b('b1')];
  it('takes the build a link names', () => expect(pickBuild(builds, 'b2')?.id).toBe('b2'));
  it('falls back to the newest when the named one is gone or none is named', () => {
    expect(pickBuild(builds, 'b9')?.id).toBe('b3');
    expect(pickBuild(builds, null)?.id).toBe('b3');
  });
  it('is null with no builds', () => expect(pickBuild([], 'b1')).toBeNull());
});

describe('testerRedirect', () => {
  it('sends old Tester links to the text view, keeping the build', () => {
    expect(testerRedirect(new URLSearchParams('build=b2'))).toBe('/test?view=text&build=b2');
    expect(testerRedirect(new URLSearchParams())).toBe('/test?view=text');
  });
});
