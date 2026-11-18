import { describe, expect, it } from 'vitest';
import { withSizeAdjust } from './webfonts';

describe('withSizeAdjust', () => {
  it('adds size-adjust to every @font-face and leaves the rest alone', () => {
    const css = "@font-face {\n  font-family: 'CNSKai';\n  src: url(a.woff2);\n}\n@font-face{font-family:'CNSKai';src:url(b.woff2)}";
    const out = withSizeAdjust(css, '110%');
    expect(out.match(/size-adjust: 110%;/g)).toHaveLength(2);
    expect(out).toContain("src: url(a.woff2);");
    expect(out).toContain("src:url(b.woff2)");
  });
});
