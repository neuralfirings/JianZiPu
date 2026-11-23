import { describe, expect, it } from 'vitest';
import { defaultTextSize, missingNote, textSvg } from './text';

const ONE = { char: '名', d: 'M0 0L100 0L100 -100Z', advance: 1024 };

describe('the Text tool', () => {
  it('starts at the box height', () => {
    expect(defaultTextSize([350, 350])).toBe(350);
    expect(defaultTextSize([500, 280.4])).toBe(280);
  });

  it('scales each character to the size and sets them side by side by their advances', () => {
    const svg = textSvg({ upm: 1024, chars: [ONE, { ...ONE, char: '起' }] }, 512)!;
    expect(svg).toContain('transform="translate(0 0) scale(0.5)"');
    expect(svg).toContain('transform="translate(512 0) scale(0.5)"');
    expect(svg.match(/<path /g)).toHaveLength(2);
  });

  it('keeps the space a character without an outline takes', () => {
    const svg = textSvg({ upm: 1000, chars: [{ char: '一', d: '', advance: 1000 }, ONE] }, 100)!;
    expect(svg.match(/<path /g)).toHaveLength(1);
    expect(svg).toContain('translate(100 0)');
  });

  it('draws nothing for nothing', () => {
    expect(textSvg({ upm: 1000, chars: [] }, 350)).toBeNull();
    expect(textSvg({ upm: 1000, chars: [ONE] }, 0)).toBeNull();
  });

  it('names the characters the font lacks', () => {
    expect(missingNote([])).toBeNull();
    expect(missingNote(['这'])).toMatch(/^TW-Kai has no 这\./);
    expect(missingNote(['这', '么', '们'])).toMatch(/^TW-Kai has no 这, 么 or 们\./);
  });
});
