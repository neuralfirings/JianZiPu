// The help page's links must keep pointing somewhere real as screens move.
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { HELP_SECTIONS, LAYOUTS_HELP, EDITOR_HELP, helpAnchor } from './help';
import { PANEL_IDS, EDITOR_PANEL_IDS } from './panels.svelte';

const routes = resolve(__dirname, '../routes');
const staticDir = resolve(__dirname, '../../static');
const pageSrc = readFileSync(resolve(routes, 'help/+page.svelte'), 'utf8');
// literal links only; the contents list's href="#{s.id}" comes from HELP_SECTIONS itself
const hrefs = [...pageSrc.matchAll(/href="([^"]+)"/g)].map((m) => m[1]).filter((h) => !h.includes('{'));
const topicHtml = [LAYOUTS_HELP, EDITOR_HELP].flatMap((h) => Object.values(h.topics).map((t) => t.html)).join('\n');
const topicHrefs = [...topicHtml.matchAll(/href="([^"]+)"/g)].map((m) => m[1]);
const imgs = [...pageSrc.matchAll(/<img src="([^"]+)"/g)].map((m) => m[1]);

/** /glyphs/new → routes/glyphs/new; /glyphs/x/edit → routes/glyphs/[name]/edit. */
function routeExists(path: string): boolean {
  let dir = routes;
  for (const seg of path.split('/').filter(Boolean)) {
    if (existsSync(resolve(dir, seg))) dir = resolve(dir, seg);
    else if (existsSync(resolve(dir, '[name]'))) dir = resolve(dir, '[name]');
    else return false;
  }
  return existsSync(resolve(dir, '+page.svelte')) || existsSync(resolve(dir, '+page.ts'));
}

describe('help page', () => {
  it('has one section per contents entry, ids unique', () => {
    const ids = HELP_SECTIONS.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(pageSrc).toContain(`id="${id}"`);
  });

  it('links only to screens and files that exist', () => {
    const inApp = hrefs.filter((h) => h.startsWith('/')).map((h) => h.split(/[?#]/)[0]);
    expect(inApp.length).toBeGreaterThan(0);
    for (const p of inApp) expect(routeExists(p) || existsSync(resolve(staticDir, p.slice(1))), p).toBe(true);
  });

  it('shows only screenshots that exist (npm run help:shots retakes them)', () => {
    expect(imgs.length).toBeGreaterThan(0);
    for (const src of imgs) expect(existsSync(resolve(staticDir, src.slice(1))), src).toBe(true);
  });

  it('jumps only to sections that exist', () => {
    const ids = new Set(HELP_SECTIONS.map((s) => s.id));
    for (const h of hrefs.filter((x) => x.startsWith('#'))) expect(ids.has(h.slice(1)), h).toBe(true);
  });

  it('has help for every panel, on both screens, under a section that exists', () => {
    expect(Object.keys(LAYOUTS_HELP.topics).sort()).toEqual([...PANEL_IDS].sort());
    expect(Object.keys(EDITOR_HELP.topics).sort()).toEqual([...EDITOR_PANEL_IDS].sort());
    const sections = new Set(HELP_SECTIONS.map((s) => s.id));
    for (const h of [LAYOUTS_HELP, EDITOR_HELP]) {
      expect(sections.has(h.section)).toBe(true);
      for (const [id, t] of Object.entries(h.topics)) {
        expect(t.html.trim(), id).not.toBe('');
        expect(sections.has(helpAnchor(h.section, id)), `${id} anchor clashes with a section`).toBe(false);
      }
    }
  });

  it('panel help links only to screens that exist', () => {
    for (const h of topicHrefs) expect(routeExists(h.split(/[?#]/)[0]), h).toBe(true);
  });

  it('knows the old Tester route redirects rather than dangling', () => {
    expect(routeExists('/tester')).toBe(true);
  });
});
