# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JianZiPu is a font system for rendering traditional Chinese guqin notation (减字谱). It uses OpenType glyph layering/substitution so that typed ASCII/Chinese characters are substituted and positioned into composite musical notation glyphs.

The website lives at https://guqintabs.com/jianzipu. Glyph designs historically
lived in Figma (`figma.py` can still import from it); the web editor in `app/`
(the JZP Font Builder, served by the Python dev server) is now the design
path, and `inputs/design.json` + `jzpbuild/positioning/` (cursive-attachment
GPOS) is the only layout model — see `docs/ROADMAP.md` for decisions and phases.

## Commands

```bash
# Development server (port 1664)
npm run dev

# Production build (outputs to web/ and dist/)
npm run build

# Watch mode
npm run watch

# Font build (Python pipeline in src-fonttools/, no FontForge)
npm run font                     # = cd src-fonttools && python3 -m jzpbuild → src-fonttools/JianZiPu.ttf
cd src-fonttools && python3 -m jzpbuild --figma_pull  # refresh SVGs/layouts from Figma (needs FIGMA_TOKEN)
cd src-fonttools && python3 -m jzpbuild --fea-only  # regenerate feature file only
cd src-fonttools && python3 -m jzpbuild -o /path/to/JianZiPu.ttf  # write the font somewhere else
cd src-fonttools && python3 tests/test_shaping.py NEW.ttf  # shaping regression vs tests/JianZiPu.ttf (golden)
cd src-fonttools && python3 -m jzpbuild --classic_pos  # legacy positioning from inputs/layouts.json + gpos.py (parity only)
cd src-fonttools && python3 -m pytest tests/test_positioning.py tests/test_glyphs.py tests/test_devserver.py tests/test_typing.py  # unit tests (positioning model, SVG flattening, SVG endpoints, spellings/typing preview)
cd app && npm test                    # Vitest unit tests (rules, shapes, gaps, panels store, glyph editor scene/ops/tools, typing, cmap)
cd src-fonttools && python3 -m jzpbuild.devserver      # API + Builder app at http://127.0.0.1:5713/
cd app && npm install && npm run build                 # build the Builder app (served by the devserver); npm run dev for HMR on :5173
```

Default build output is `src-fonttools/JianZiPu.ttf` (gitignored, as is the
`--fea-out` copy `src-fonttools/JianZiPu.fea`); nothing tracked is
overwritten unless you pass `-o`. A plain build reads only from
`src-fonttools/inputs/` (tracked: `design.json`, `components.csv`, the
Figma-fetched `svg/`; `layouts.json` only for `--classic_pos`). The base font
`src-fonttools/src_font/TW-Kai-98.ttf` is gitignored and must be copied in
by hand once. Dev tools: the Builder app (`app/`, see below) and
`src-fonttools/tools/font_tester.html` (no build tooling needed, open directly in
a browser — live-test a built .ttf, points at `../JianZiPu.ttf` by default).
`.claude/launch.json` has a `builder` entry that starts the dev server.

Legacy pipeline (deprecated, reference only, kept as a regression
fallback): `src-fontforge/` — `scripts/scripts.cjs` (--compile /
--add-positions), the `scripts/fontForge*.py` scripts that ran inside
FontForge, the `.sfd` sources and the hand-maintained `input/` files. See
src-fonttools/README.md for the current architecture.

Run both test suites after any code change (`npm test` in `app/`, `python3 -m pytest tests` in
`src-fonttools/`; `tests/test_shaping.py` additionally needs a freshly built font and compares it
with the golden).

## Architecture

### Repo layout

- **`src-fonttools/`** — the font build pipeline (below). `README.md` there is the detailed reference.
- **`src-fonttools/jzpbuild/positioning/`** — the positioning model: `schema.py` (design file) → `shapes.py` (word shapes) → `resolve.py` (x/y) → `emit.py` (cursive-attachment GPOS). `tests/test_positioning.py` covers it.
- **`src-fonttools/jzpbuild/devserver.py`** — stdlib HTTP server: JSON API (`/api/design`, `/api/resolve`, `/api/words`, `/api/glyphs`, `/api/typing/preview`, `/api/build`…) plus the built app at `/`.
- **`app/`** — the JZP Font Builder (SvelteKit 2 / Svelte 5, static build, no backend of its own). Screens: Glyphs (grouped by area; Tiles | Typing switch, Typing = spreadsheet of the `components.csv` spellings with clash checks, paste, CSV import/export, and Try it through the unsaved spellings via `/api/typing/preview` — see `docs/KEY-ENTRY-UX.md`; + the glyph editor at `/glyphs/<name>/edit` and `/glyphs/new`: Paper.js canvas, paperjs-offset for thicken/outline, esm-potrace-wasm for tracing; writes `inputs/svg/<name>.svg` via `PUT /api/svg/<name>`), Areas, Layouts (canvas + dockable panels: Structure/Spacing/Centering…), Test & Build (each build goes to its own temp dir, served at `/api/builds/<id>/JianZiPu.ttf`, downloadable), Tester (`/tester`: one exact TTF loaded via FontFace under its own family, from a build or a local file); Import/Export of `design.json`. Design and spelling edits stay in the browser until Save (hash-checked, writes `design.json` and/or `components.csv`, waits while a spelling clashes); glyph files save from the editor at once. Characters a font lacks show in red (cmap parsed in `app/src/lib/cmap.ts`).
- **`src-fontforge/`** — legacy FontForge pipeline plus the old demo page (`demo/index.html`).
- **`mockups/`** — lo-fi wireframes for the web editor roles; `docs/BUILDER-UX.md` is the UX spec the app follows (written against the previous data model; the app maps its Areas/Layouts screens onto `design.json`).
- `package.json`'s Parcel targets (`web/`, `dist/`) still point at a `src/` folder that was renamed to `src-fontforge/`; `npm run dev`/`build` are broken until that's re-pointed.

### Font pipeline (src-fonttools/, pure Python)

```
Figma ──(jzpbuild/figma.py, REST API)──▶ src-fonttools/inputs/{svg/, layouts.json}
src-fonttools/src_font/TW-Kai-98.ttf ──(jzpbuild/base.py: subset + ch_* rename + metrics)──▶ base glyphs
inputs/svg/*.svg ──(jzpbuild/glyphs.py: picosvg + pathops + cu2qu)──▶ PUA component glyphs
src-fonttools/inputs/{components.csv, edge_cases.fea} ──(features.py)──▶ GSUB .fea
src-fonttools/inputs/design.json ──(jzpbuild/positioning/)──▶ GPOS .fea   (--classic_pos: gpos.py + layouts.json)
                                  └──(fontTools feaLib)──▶ src-fonttools/JianZiPu.ttf
```

### Key input files (sources of truth)

- `src-fonttools/inputs/design.json` — the positioning design (version 2): `areas` (box size, member glyphs, advance), `layouts` (word types: slots with alternatives/repeat, spacing `relationships` with glyph-conditional gaps, `center`). Edited by the Builder app; also importable/exportable there.
- `src-fonttools/inputs/components.csv` — the spellings: `glyph_name,vert_variant,common,latin,latin_alt,simplified,traditional,pinyin` (glyph_name is the ID; pinyin is reference only; a vertical form stores only the `vert_variant` link on its partner plus spellings of its own). Drives ALL generated substitution rules, including `l2j_digit_liga` for Latin spellings with a digit (zhi4/xi4/fu4). Edited in the Builder's Glyphs → Typing view; area membership lives in `design.json`.
- `src-fonttools/inputs/glyphRename.csv` — optional overrides: unicode char → ch_* glyph name for Han chars that want a mnemonic name; any other referenced character still builds fine with an auto-derived uniXXXX name
- `src-fonttools/inputs/edge_cases.fea` — the few hand-maintained disambiguation rules (today only `ch_dc_sub`)
- `src-fonttools/inputs/layouts.json` + `src-fonttools/jzpbuild/gpos.py` — legacy classic positioning (Figma frame geometry + declarative rule builders), only used by `--classic_pos` and `tests/parity_report.py`
- `src-fonttools/jzpbuild/config.py` — metrics, name table, PUA codepoints, Figma file key, all generated-artifact paths (single source of truth, no fallbacks)

Deprecated (legacy pipeline only): `src-fontforge/input/figma.css`, `src-fontforge/input/fontForgeFeatures.fea`, `src-fontforge/input/areaKeySVGMap.csv` (now `src-fonttools/inputs/components.csv`), `src-fontforge/input/fontforgeGlyphRename.csv` (now `src-fonttools/inputs/glyphRename.csv`), `src-fontforge/scripts/`.

### SVG components

`src-fonttools/inputs/svg/` contains all PUA glyph SVGs, fetched from Figma (`src-fontforge/components/` is the legacy hand-exported set):
- `lg_*` — large glyphs (strokes: 勾 gou, 挑 tiao, etc.)
- `md_*` — medium glyphs (finger positions, strings)
- Other prefixes for hui markers, decorations, etc.

### Demo page (`src-fontforge/demo/index.html`)

Self-contained HTML file. Loads `JianZiPu.ttf` and `TW-Kai-98.ttf` via `@font-face`. Uses Bootstrap 5. The font is applied via `font-family: 'JianZiPu'` and OpenType features are enabled with `font-feature-settings: "kern", "liga"` (required for Firefox).
