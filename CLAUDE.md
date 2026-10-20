# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JianZiPu is a font system for rendering traditional Chinese guqin notation (减字谱). It uses OpenType glyph layering/substitution so that typed ASCII/Chinese characters are substituted and positioned into composite musical notation glyphs.

The website lives at https://guqintabs.com/jianzipu. Glyphs, spellings and
layouts are designed in the web editor in `app/` (the JZP Font Builder, served
by the Python web server), and `inputs/design.json` + `jzpbuild/positioning/` (cursive-attachment
GPOS) is the only layout model — see `docs/ROADMAP.md` for decisions and phases.

## Commands

```bash
# The Builder (web UI): the primary interface for glyphs, spellings and layouts
cd app && npm install && npm run build                 # build the Builder app (served by the webserver); npm run dev for HMR on :5173
cd builder && python3 -m jzpbuild.webserver      # API + Builder app at http://127.0.0.1:5713/
cd builder && python3 -m jzpbuild.webserver --hosted   # pilot mode: read-only, Supabase sign-in + drafts (needs SUPABASE_URL/ANON_KEY; see builder/README.md "Hosted pilot")

# Font build from the command line (the Builder runs the same pipeline)
cd builder && python3 -m jzpbuild  # → builder/JianZiPu.ttf
cd builder && python3 -m jzpbuild --fea-only  # regenerate feature file only
cd builder && python3 -m jzpbuild -o /path/to/JianZiPu.ttf  # write the font somewhere else
cd builder && python3 -m jzpbuild -o ../site/JianZiPu.ttf   # publish a font release to the public site (then commit)
cd builder && python3 -m jzpbuild --classic_pos  # legacy positioning from inputs/layouts.json + gpos.py (parity only)

# Tests
cd builder && python3 tests/test_shaping.py NEW.ttf  # shaping regression vs tests/JianZiPu.ttf (golden)
cd builder && python3 -m pytest tests/test_positioning.py tests/test_glyphs.py tests/test_webserver.py tests/test_typing.py tests/test_hosted.py tests/test_emails.py  # unit tests (positioning model, SVG flattening, SVG endpoints, spellings/typing preview, hosted mode, Supabase email templates)
cd app && npm run help:shots          # retake the Help page screenshots (static/help/*.jpg) from a running Builder; BASE=http://127.0.0.1:<port> for another port
cd app && npm test                    # Vitest unit tests (rules, shapes, gaps, panels store, glyph editor scene/ops/tools, typing, cmap, draft bundle/merge, app state)
```

Default build output is `builder/JianZiPu.ttf` (gitignored, as is the
`--fea-out` copy `builder/JianZiPu.fea`); nothing tracked is
overwritten unless you pass `-o`. A plain build reads only from
`builder/inputs/` (tracked: `design.json`, `components.csv`,
`svg/`; `layouts.json` only for `--classic_pos`). The base font
`builder/src_font/TW-Kai-98.ttf` is gitignored and must be copied in
by hand once. Dev tool: the Builder app (`app/`, see below; its Build & test screen
live-tests any built .ttf). `.claude/launch.json` has a `builder` entry that
starts the web server.

The old FontForge pipeline (`src-fontforge/`: `scripts.cjs`, the
`fontForge*.py` scripts, the `.sfd` sources and v3.x backups) was removed on
2026-10-18; it is in git history under the tag `fontforge-final`. The
regression fallback is now the classic positioning path below
(`--classic_pos`, golden `tests/JianZiPu.ttf`).

Help text: the Builder's help lives in `app/src/lib/help.ts` (each panel's ? popover, `LAYOUTS_HELP`
/ `EDITOR_HELP`, and the help page's sections list) and `app/src/routes/help/+page.svelte` (the rest
of the page, which also renders the panel entries). Before committing a feature change, check
whether any help text describes what changed and update it in that one place; retake screenshots
with `npm run help:shots` when a screen's look changed.

Run both test suites after any code change (`npm test` in `app/`, `python3 -m pytest tests` in
`builder/`; `tests/test_shaping.py` additionally needs a freshly built font and compares it
with the golden).

## Architecture

### Repo layout

- **`builder/`** — the font build pipeline (below) and the web server that serves the Builder app (`app/`) at builder.jianzipufont.com; renamed from `font/` on 2026-10-19. `README.md` there is the detailed reference.
- **`site/`** — the public font page at jianzipufont.com (static: `index.html`, `keyboard.png`, and the released `JianZiPu.ttf`), deployed by Cloudflare Pages from `main`. Publishing a font = `cd builder && python3 -m jzpbuild -o ../site/JianZiPu.ttf`, then commit. Preview with the `site` entry in `.claude/launch.json`.
- **`builder/jzpbuild/positioning/`** — the positioning model: `schema.py` (design file) → `shapes.py` (word shapes) → `resolve.py` (x/y) → `emit.py` (cursive-attachment GPOS). `tests/test_positioning.py` covers it.
- **`builder/jzpbuild/webserver.py`** — stdlib HTTP server: JSON API (`/api/design`, `/api/resolve`, `/api/words`, `/api/glyphs`, `/api/typing/preview`, `/api/build`, `/api/config`, `/api/base`…) plus the built app at `/`. `--hosted` (`jzpbuild/hosted.py`) is the pilot mode on Railway: read-only, POSTs need a Supabase-signed-in tester, builds per tester from their draft, base font fetched from Supabase Storage.
- **Hosted pilot** — `Dockerfile` (Railway), `supabase/001_setup.sql` (profiles, private `drafts`/`assets` buckets, row rules), `supabase/emails/` (the auth email templates and subjects, pasted into the dashboard by hand; `preview.html` there fills each template's variables with your values, served by `python3 -m http.server`), spec `docs/PILOT-UX.md`. A tester's work is a draft bundle (`app/src/lib/bundle.ts`: manifest + design.json + components.csv + changed SVGs + base copies) in Supabase Storage; the owner merges drafts in the local Builder's `/review` (three-way, `app/src/lib/merge.ts`) and commits. The Supabase service key stays on the server, never in the app or repo.
- **`app/`** — the JZP Font Builder (SvelteKit 2 / Svelte 5, static build, no backend of its own). Screens: Glyphs (grouped by area; Tiles | Typing switch, Typing = spreadsheet of the `components.csv` spellings with clash checks, paste, CSV import/export, and Try it through the unsaved spellings via `/api/typing/preview` — see `docs/KEY-ENTRY-UX.md`; + the glyph editor at `/glyphs/<name>/edit` and `/glyphs/new`: Paper.js canvas, paperjs-offset for thicken/outline, esm-potrace-wasm for tracing, dockable panels like Layouts (Selection/Compare/Glyph/Typing/Try it/Checks/Tester); writes `inputs/svg/<name>.svg` via `PUT /api/svg/<name>`), Layouts (canvas + dockable panels: Structure/Spacing/Centering/Area Properties…; Area Properties (`AreaPanel.svelte`, helpers in `lib/areas.ts`) replaced the old Areas screen: area switcher, box size with a canvas preview before Enter applies it, members with the position decimals as a 13 × 10 grid, + New area and Delete area (only an empty area no word type uses; otherwise a banner says why); deep link `/layouts?area=<id>&g=<glyph>`; the panel frame is `PanelWorkspace` + one `PanelStore` per screen in `lib/panels.svelte.ts`, the word strip is the shared `WordTester`), Build & test (`/test`: each build goes to its own temp dir, served at `/api/builds/<id>/JianZiPu.ttf`, downloadable; one exact TTF loaded via FontFace under its own family, from a build or a local file; "Test the design" view (`view=words`) = live preview vs font per word, "Test the font file" view (`view=text`) = running text with liga/kern/vertical and a second font; `/tester` redirects to the font-file view, helpers in `lib/buildtest.ts`), Review (`/review`, local mode: testers' drafts or a .zip, Keep/Skip per item, Apply = one undo step; hosted: Import a .zip, `?mine` = See my changes); Import/Export of `design.json`, draft .zip. Design and spelling edits stay in the browser until Save (hash-checked, writes `design.json` and/or `components.csv`, waits while a spelling clashes); glyph files save from the editor at once (hosted: into the draft), glyph files from a Review Apply wait in `app.pendingSvgs` for Save. App state is `lib/state.svelte.ts`; hosted sign-in `lib/hosted.svelte.ts`, draft storage `lib/drafts.ts`, pilot dialogs `lib/pilot.svelte.ts` + `PilotDialogs.svelte`. Characters a font lacks show in red (cmap parsed in `app/src/lib/cmap.ts`).
- **`docs/`** — local only (gitignored since 2026-10-19; older copies are in git history): UX specs, one per screen or feature (`*-UX.md` plus Kat's HTML wireframes); `docs/BUILDER-UX.md` is the main spec (written against the previous data model; the app maps its Layouts screen onto `design.json`; areas live in the Area Properties panel, see `docs/AREAS-PLACEMENT-UX.md`). `docs/ROADMAP.md` holds the decisions. Superseded reviews and wireframes are in `docs/archive/`.

### Font pipeline (builder/, pure Python)

```
Builder app (app/) ──(webserver API)──▶ builder/inputs/{design.json, components.csv, svg/}
builder/src_font/TW-Kai-98.ttf ──(jzpbuild/base.py: subset + ch_* rename + metrics)──▶ base glyphs
inputs/svg/*.svg ──(jzpbuild/glyphs.py: picosvg + pathops + cu2qu)──▶ PUA component glyphs
builder/inputs/{components.csv, edge_cases.fea} ──(features.py)──▶ GSUB .fea
builder/inputs/design.json ──(jzpbuild/positioning/)──▶ GPOS .fea   (--classic_pos: gpos.py + layouts.json)
                                  └──(fontTools feaLib)──▶ builder/JianZiPu.ttf
```

### Key input files (sources of truth)

- `builder/inputs/design.json` — the positioning design (version 2): `areas` (box size, member glyphs, advance), `layouts` (word types: slots with alternatives/repeat, spacing `relationships` with glyph-conditional gaps, `center`). Edited by the Builder app; also importable/exportable there.
- `builder/inputs/components.csv` — the spellings: `glyph_name,vert_variant,common,latin,latin_alt,simplified,traditional,pinyin` (glyph_name is the ID; pinyin is reference only; a vertical form stores only the `vert_variant` link on its partner plus spellings of its own). Drives ALL generated substitution rules, including `l2j_digit_liga` for Latin spellings with a digit (zhi4/xi4/fu4). Edited in the Builder's Glyphs → Typing view; area membership lives in `design.json`.
- `builder/inputs/glyphRename.csv` — optional overrides: unicode char → ch_* glyph name for Han chars that want a mnemonic name; any other referenced character still builds fine with an auto-derived uniXXXX name
- `builder/inputs/edge_cases.fea` — the few hand-maintained disambiguation rules (today only `ch_dc_sub`)
- `builder/inputs/layouts.json` + `builder/jzpbuild/gpos.py` — legacy classic positioning (frame geometry + declarative rule builders), only used by `--classic_pos` and `tests/parity_report.py`
- `builder/jzpbuild/config.py` — metrics, name table, PUA codepoints, all generated-artifact paths (single source of truth, no fallbacks)


### SVG components

`builder/inputs/svg/` contains all PUA glyph SVGs, drawn or imported in the Builder's glyph editor:
- `lg_*` — large glyphs (strokes: 勾 gou, 挑 tiao, etc.)
- `md_*` — medium glyphs (finger positions, strings)
- Other prefixes for hui markers, decorations, etc.

### Design system (Builder UI)

The Builder follows the JZP Font Builder design system:
https://claude.ai/artifact/SNGE3ACTZxtP2PLRatJnv8 (read it with the Artifact tool, `project/README.md`
first, then `tokens.json`, `states.md`, `canvas-and-overlays.md`, `layout-and-density.md` and the
component READMEs). In short: grey paper (`--bg-app`, `--bg-panel`), near-black ink, one seal-red
`--accent` (anchor, highlighted component, destructive actions only); link blue (`--link`) for links,
focus and selection (`--sel-bg` + `--sel-border`); every status is colour + icon + word (`.pill.saved`
✓, `.pill.draft` ● dashed, `.pill.danger` ×, `.pill.info` ◐); EB Garamond for titles and panel titles,
Literata for everything else, mono for spellings and ids; edges not shadows (shadows only on menus,
toasts, dialogs, drags); sentence case, no emoji, no exclamation marks.

- Tokens live in `app/src/app.css` under the system's names (`--bg-*`, `--ink*`, `--border*`,
  `--status-*`, `--ov-*` canvas overlays, `--space-1…9`, `--radius-*`, `--control-*`, `--t-caption…title`,
  `--font-*`), with both themes. Use them; never add literal colours or off-scale spacing.
- Shared classes in `app.css`: buttons (`.primary` one per view, `.quiet`, `.danger`, `.sm`, `.lg`),
  `.chip` (choices; `aria-pressed`/`.accent` for on, `.dashed` for "any"), `.pill` (status), `.tag`,
  `.banner.info|draft|danger|saved` (with a `<span class="ic">` icon), `.toast`, `.modal-bg` + `.modal`
  (dialog), `.float` (menus, popovers).
- Fonts are self-hosted from `@fontsource-variable/{literata,eb-garamond}` (imported in
  `routes/+layout.svelte`); Chinese falls back to Noto Serif SC / Songti.
- Icons are Lucide (`@lucide/svelte`), imported only through `app/src/lib/icons.ts`, which names each
  one by its job (`<I.Close />`, `<I.Folded />`, `<I.Warn />`…); 16px / 1.5px is set once in
  `routes/+layout.svelte`, square caps in `app.css`. Use those names instead of text symbols
  (×, ▾, ⋯, ✓…); `{@html}` help strings can't hold components, so name the button in words there.
- Icon-only buttons say what they do with `data-tip="…"` (instant tooltip, `lib/tooltip.ts`; add
  `data-tip-side="right"` beside a left rail) plus an `aria-label`, not `title`, which shows only after a delay.
- Canvas: part boxes 1px `--ov-part`, anchor `--ov-anchor`, active part 2px `--ov-active` with
  `--ov-handle` handles, area/rule base `--ov-area`, measurements `--ov-measure`, guides dashed
  `--ov-guide`; Review's Before / After use `--ov-before` (dashed) / `--ov-after` (`SvgText` `tone`).
