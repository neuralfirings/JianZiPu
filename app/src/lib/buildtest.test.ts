import { describe, it, expect } from 'vitest';
import { parseView, pickBuild, testerRedirect, buildFailure } from './buildtest';
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

describe('buildFailure', () => {
  const trace = (...tail: string[]) => [
    'base: subsetting TW-Kai-98.ttf',
    'Traceback (most recent call last):',
    '  File "/repo/builder/jzpbuild/build.py", line 40, in build',
    '    validate.check_inputs()',
    '    ~~~~~~~~~~~~~~~~~~~~~^^',
    '  File "/repo/builder/jzpbuild/validate.py", line 106, in check_inputs',
    '    raise ValidationError(',
    ...tail
  ];

  it('shows the exception, not the source line that raised it', () => {
    const log = trace(
      'jzpbuild.validate.ValidationError: input validation failed (1 issue(s)):',
      "  - components.csv: latin spelling 'k' is claimed by multiple glyphs (a, b) — pick a unique key per glyph"
    );
    expect(buildFailure(log)).toBe(
      "ValidationError: input validation failed (1 issue(s)):\n  - components.csv: latin spelling 'k' is claimed by multiple glyphs (a, b) — pick a unique key per glyph"
    );
  });

  it('takes the last exception of a chained traceback', () => {
    const log = trace(
      "KeyError: 'md_9'",
      '',
      'During handling of the above exception, another exception occurred:',
      '',
      '    raise FeatureLibError(',
      'fontTools.feaLib.error.FeatureLibError: The following glyph names are referenced but are missing from the glyph set:',
      ' md_9 (first found at JianZiPu.fea:12:5)'
    );
    expect(buildFailure(log)).toBe(
      'FeatureLibError: The following glyph names are referenced but are missing from the glyph set:\n md_9 (first found at JianZiPu.fea:12:5)'
    );
  });

  it('reads a missing base font as itself', () => {
    const log = trace("FileNotFoundError: [Errno 2] No such file or directory: '/repo/builder/src_font/TW-Kai-98.ttf'");
    expect(buildFailure(log)).toBe("FileNotFoundError: [Errno 2] No such file or directory: '/repo/builder/src_font/TW-Kai-98.ttf'");
  });

  it('falls back to a size complaint, then to the log', () => {
    expect(buildFailure(['packing GPOS', 'the GPOS table is too large to pack'])).toBe('the GPOS table is too large to pack');
    expect(buildFailure(['could not start the build: [Errno 2] No such file'])).toBe('Build failed: see the log.');
  });
});
