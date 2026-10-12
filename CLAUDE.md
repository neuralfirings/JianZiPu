# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JianZiPu is a font system for rendering traditional Chinese guqin notation (减字谱). It uses OpenType glyph layering/substitution so that typed ASCII/Chinese characters are substituted and positioned into composite musical notation glyphs.

The website lives at https://guqintabs.com/jianzipu. Glyph designs are in Figma.

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
cd src-fonttools && python3 -m jzpbuild -o ../src/JianZiPu.ttf  # overwrite the tracked, released font
cd src-fonttools && python3 tests/test_shaping.py NEW.ttf  # shaping regression vs src/JianZiPu.ttf
```

Default build output is `src-fonttools/JianZiPu.ttf`, NOT `src/JianZiPu.ttf`
— the tracked font is only overwritten via explicit `-o`. A plain build
reads only from `src-fonttools/inputs/` (no fallback), so a fresh checkout needs
`--figma_pull` at least once before it will succeed. Dev tools:
`src-fonttools/tools/font_tester.html` (no build tooling needed, open directly in
a browser — live-test a built .ttf, points at `../JianZiPu.ttf` by default)
and `src-fonttools/tools/jzpbuilder.html` (edit/preview `layouts.json` + SVGs
without Figma access, also builds the font — requires `python3 -m
jzpbuild.devserver` running; opening it as a plain `file://` page doesn't
work, since Chromium blocks `fetch()` against `file://` sibling files).

Legacy pipeline (deprecated, reference only): `src/scripts/scripts.cjs`
(--compile / --add-positions) and the `src/scripts/fontForge*.py` scripts
that ran inside FontForge. See src-fonttools/README.md for the current
architecture, and its "Status / open items" section for unresolved issues
(a Figma image-export quota was hit and not confirmed clear; a 37-vs-34
layout count mismatch on the Figma file needs a decision from the file
owner before `gpos.py` is extended to cover it).

## Architecture

### Two outputs from one build

- **`web/`** — demo website (`src/demo/index.html` is the source, built by Parcel `frontend` target)
- **`dist/`** — JS library (`src/jianzipu.js` is the source, built by Parcel `backend` target as ESM)

### Font pipeline (src-fonttools/, pure Python)

```
Figma ──(jzpbuild/figma.py, REST API)──▶ src-fonttools/inputs/{svg/, layouts.json}
src-fonttools/src_font/TW-Kai-98.ttf ──(jzpbuild/base.py: subset + ch_* rename + metrics)──▶ base glyphs
inputs/svg/*.svg ──(jzpbuild/glyphs.py: picosvg + pathops + cu2qu)──▶ PUA component glyphs
src-fonttools/inputs/{components.csv, edge_cases.fea} + gpos.py ──(features.py/gpos.py)──▶ generated .fea
                                  └──(fontTools feaLib)──▶ src-fonttools/JianZiPu.ttf
```

### Key input files (sources of truth)

- `src-fonttools/inputs/components.csv` — maps input chars → glyph names → layout areas (plus vert-mode variants); drives ALL generated substitution rules
- `src-fonttools/inputs/glyphRename.csv` — optional overrides: unicode char → ch_* glyph name for Han chars that want a mnemonic name; any other referenced character still builds fine with an auto-derived uniXXXX name
- `src-fonttools/inputs/edge_cases.fea` — the few hand-maintained disambiguation rules
- `src-fonttools/inputs/layouts.json` — layout/area geometry (x/y/w/h per area, per layout), fetched from Figma
- `src-fonttools/jzpbuild/gpos.py` — declarative layout structure (which areas, in what order, per layout family)
- `src-fonttools/jzpbuild/config.py` — metrics, name table, PUA codepoints, Figma file key, all generated-artifact paths (single source of truth, no fallbacks)

Deprecated (legacy pipeline only): `src/input/figma.css`, `src/input/fontForgeFeatures.fea`, `src/input/areaKeySVGMap.csv` (now `src-fonttools/inputs/components.csv`), `src/input/fontforgeGlyphRename.csv` (now `src-fonttools/inputs/glyphRename.csv`), `src/scripts/`.

### SVG components

`src/components/` contains all PUA glyph SVGs exported from Figma:
- `lg_*` — large glyphs (strokes: 勾 gou, 挑 tiao, etc.)
- `md_*` — medium glyphs (finger positions, strings)
- Other prefixes for hui markers, decorations, etc.

### Demo page (`src/demo/index.html`)

Self-contained HTML file. Loads `JianZiPu.ttf` and `TW-Kai-98.ttf` via `@font-face`. Uses Bootstrap 5. The font is applied via `font-family: 'JianZiPu'` and OpenType features are enabled with `font-feature-settings: "kern", "liga"` (required for Firefox).
