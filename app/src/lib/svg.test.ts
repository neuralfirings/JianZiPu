import { describe, expect, it } from 'vitest';
import { parseSvg, sanitizeSvg } from './svg';

describe('parseSvg', () => {
  it('extracts the viewBox and inner markup, recolouring black to currentColor', () => {
    const r = parseSvg('<svg width="350" height="350" viewBox="0 0 350 350" xmlns="x"><path d="M0 0" fill="black"/><path stroke="#000"/></svg>');
    expect(r?.viewBox).toBe('0 0 350 350');
    expect(r?.inner).toBe('<path d="M0 0" fill="currentColor"/><path stroke="currentColor"/>');
  });
  it('falls back to width/height, then 1000', () => {
    expect(parseSvg('<svg width="200" height="100"></svg>')?.viewBox).toBe('0 0 200 100');
    expect(parseSvg('<svg></svg>')?.viewBox).toBe('0 0 1000 1000');
  });
  it('returns null for missing or non-SVG text and caches', () => {
    expect(parseSvg(undefined)).toBeNull();
    expect(parseSvg('nope')).toBeNull();
    const t = '<svg viewBox="0 0 1 1"></svg>';
    expect(parseSvg(t)).toBe(parseSvg(t));
  });
});

describe('sanitizeSvg', () => {
  it('keeps shapes and drops scripts, handlers, links and foreign markup', () => {
    const bad = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 350 350" onload="alert(1)">'
      + '<script>alert(2)</script><foreignObject><div>x</div></foreignObject>'
      + '<a href="javascript:alert(3)"><path d="M0 0h1"/></a>'
      + '<g transform="translate(1 1)"><path d="M10 10h100v100h-100z" fill="black" onclick="x()" style="fill:red"/></g>'
      + '<use href="#p"/><rect x="1" y="1" width="2" height="2" fill="url(http://evil/x)"/></svg>';
    const out = sanitizeSvg(bad);
    expect(out).not.toMatch(/script|onload|onclick|foreignObject|javascript|href|style|evil|<a|<use/i);
    expect(out).toContain('d="M10 10h100v100h-100z"');
    expect(out).toContain('fill="black"');
    expect(out).toContain('viewBox="0 0 350 350"');
    expect(out).toContain('transform="translate(1 1)"');
  });
  it('keeps local clip-path references and refuses non-SVG text', () => {
    expect(sanitizeSvg('<svg xmlns="http://www.w3.org/2000/svg"><path clip-path="url(#c)" d="M0 0"/></svg>')).toContain('url(#c)');
    expect(() => sanitizeSvg('<html><body/></html>')).toThrow();
    expect(() => sanitizeSvg('not xml')).toThrow();
  });
  it('returns a clean file unchanged, so a merge can compare it with the file on disk', () => {
    const clean = '<?xml version="1.0"?>\n<svg width="350" height="350" viewBox="0 0 350 350" fill="none" xmlns="http://www.w3.org/2000/svg">\n<path d="M0 0h9" fill="black"/>\n</svg>\n';
    expect(sanitizeSvg(clean)).toBe(clean);
  });
  it('rebuilds a file with comments or CDATA, which parse differently once inlined in HTML', () => {
    const sneaky = '<svg xmlns="http://www.w3.org/2000/svg"><title><![CDATA[<img src=x onerror=alert(1)>]]></title><!-- x --><path d="M0 0"/></svg>';
    const out = sanitizeSvg(sneaky);
    expect(out).not.toContain('CDATA');
    expect(out).not.toContain('<!--');
    expect(out).not.toMatch(/<img/);
  });
});

describe('drafts from others', () => {
  it('are sanitized when opened', async () => {
    const { makeBundle, validate } = await import('./bundle');
    const d = { version: 2, center: { x: 500, y: 300 }, areas: {}, layouts: [] } as never;
    const evil = '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><path d="M0 0h9"/></svg>';
    const b = makeBundle({ design: d, typing: {}, svgs: { md_x: evil }, baseDesign: d, baseTyping: {}, baseSvgs: {},
      base: { commit: null, design_hash: '', csv_hash: '' } });
    const v = validate(JSON.parse(JSON.stringify(b)));
    expect(v.svgs.md_x).not.toContain('onload');
    expect(v.svgs.md_x).toContain('d="M0 0h9"');
  });
});
