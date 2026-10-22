# jzpbuild — the JianZiPu font build pipeline

The font is designed in the **JZP Font Builder**, a web app served by this
folder's web server: glyphs, how they're typed, and how words are laid out are
all edited there, and its Save writes the files in `inputs/`. Start with
"The Builder app" below. The rest of this README is the reference for what
runs underneath: one Python build, with no FontForge and no hand-edited
feature files.

## Setup (first time on a fresh checkout)

1. **Python >= 3.10.**
2. **Install dependencies:**
   ```bash
   cd builder
   pip install -e .          # fonttools, picosvg, skia-pathops, uharfbuzz
   pip install -e '.[test]'  # + pytest (uharfbuzz is a main dependency: the web server shapes test words with it)
   ```
3. **Base font.** The pipeline subsets glyphs from a base Kai typeface, and
   expects it at `builder/src_font/TW-Kai-98.ttf`. This file is **gitignored
   and not included in the repo** (36MB, binary, not something git handles
   well) — copy/paste your own copy of `TW-Kai-98.ttf` there before your
   first build. Using a different base font, or a different filename? Change
   `SOURCE_FONT` in `jzpbuild/config.py` (`SOURCE_FONT = BUILDER_DIR /
   "src_font/TW-Kai-98.ttf"`) to point at it — everything downstream
   (`base.py`) just reads whatever path is set there.
4. **The Builder app.** `cd ../app && npm install && npm run build` once (and
   after pulling app changes); the web server then serves it.
5. **`builder/inputs/`** holds everything the build reads — what the
   Builder edits (`design.json`, `components.csv`, `svg/`, and `glyph_ids.json`,
   each glyph's pinned character code plus retired codes and renames), the hand-maintained
   `glyphRename.csv` and `edge_cases.fea`, and `layouts.json` for the legacy
   `--classic_pos` build — and is tracked in git, so a fresh checkout already
   has it — nothing to do here. A plain build reads `builder/inputs/svg/` and `design.json`
   unconditionally, with no fallback location — if this directory is ever
   missing or emptied, the build fails fast with `FileNotFoundError` rather
   than silently reading something stale (see "config.py's paths are the
   single source of truth" below for why).

With those in place (base font placed, deps installed, app built), you're set
up: `python3 -m jzpbuild.webserver` and open http://127.0.0.1:5713/.

## The Builder app (start here)

`jzpbuild/webserver.py` is a stdlib-only local HTTP server (no extra
dependency). It serves the built Builder app (`app/build/`, SPA fallback)
at `/`, `inputs/` and `tests/` as static files (`/inputs/svg/...`,
`/JianZiPu.ttf`, which is the latest UI build when there is one), and the JSON API the app uses:

```bash
cd builder
python3 -m jzpbuild.webserver          # http://127.0.0.1:5713/
python3 -m jzpbuild.webserver --port 9000
```

| Route | Does |
|---|---|
| `GET /api/design` | `design.json` + content hash + validation warnings + rule stats |
| `PUT /api/design` | `{design, base_hash}` → validates, writes `design.json`; 409 if the file changed on disk since `base_hash` (empty hash = force) |
| `POST /api/design/check` | validate + stats for an unsaved design (the app calls this after every edit) |
| `POST /api/resolve` | `{design?, layout, choice, pinned?, center?}` → positions of one word shape; `choice` is per slot `null` / alternative index / list per row |
| `POST /api/words` | `{design?, words}` → each typed word shaped through GSUB (HarfBuzz on the last built font) and positioned by the unsaved design — the live preview |
| `GET /api/glyphs` | every glyph (SVGs + CSV rows) with its spellings, areas and SVG, plus the CSV's row order and content hash |
| `PUT /api/glyphs` | `{rows, base_hash, design}` → checks the spellings (400 with `errors` on a clash or invalid spelling), rewrites `components.csv` keeping its row order and dropping empty rows; 409 if the file changed since `base_hash` |
| `POST /api/typing/preview` | `{design, rows, words, base_rows?, compare_words?, roundtrip?}` → GSUB from the *unsaved* spellings compiled into a copy of the last build (≈0.5 s, cached): each word's glyphs, `issues`, a round trip of every spelling, `changed` sample words vs `base_rows`, `not_built` glyphs and `missing_chars` |
| `POST /api/svg/check` | what the build makes of an SVG text: flattened outline `d`, contour / point counts, bounds (`glyphs.flatten_svg_text`) |
| `PUT /api/svg/<name>` | write `inputs/svg/<name>.svg` (validated the same way); 409 when the file exists and no `base_hash` was sent, or when it changed on disk since it was loaded |
| `DELETE /api/svg/<name>` | delete `inputs/svg/<name>.svg` (a merged draft that deletes a glyph; local mode only); its code is retired in `glyph_ids.json` |
| `GET /api/glyph/<name>/uses` | where a glyph is named (spellings, vertical links, areas, spacing rows, `edge_cases.fea`), its code, and `locked`: why it can't be renamed or deleted (`glyph_edit.py`) |
| `PUT /api/glyph/<name>/rename` | `{to, design_hash, csv_hash}` → rename the glyph in the SVG file name, `components.csv`, `design.json`, `edge_cases.fea` and `glyph_ids.json` at once (local mode; 409 when a file changed on disk, 400 with the reason it can't) |
| `DELETE /api/glyph/<name>?design_hash=…&csv_hash=…` | delete the glyph and everything that names it; spacing rows that only applied to it go, its code is retired (local mode) |
| `GET /api/svgs` | every `inputs/svg/*.svg` as `{glyph_name: svg_text}` |
| `POST /api/build`, `GET /api/build/status` | run `python3 -m jzpbuild -o <temp dir>/JianZiPu.ttf` (one at a time) and poll its log; status lists the caller's builds (`build` = latest, `builds` = newest first, last 8 kept). The body may carry a draft, `{design, rows, svgs, deleted}`, built instead of the files on disk (hosted mode) |
| `GET /api/config` | `{mode: local|hosted, commit, supabase_url, supabase_anon_key}` (never the service key) |
| `GET /api/base` | the font version on disk: `{commit, date, design_hash, csv_hash, svg_hashes}`; a draft records it to notice when the font moves on |
| `GET /api/builds/<id>/JianZiPu.ttf` | that exact build; `?download=1` sends it as an attachment. Build folders live in the system temp dir and are removed when the server stops |

The app itself lives in `app/` (SvelteKit 2 + Svelte 5, static build):

```bash
cd app && npm install
npm run dev      # Vite dev server on :5173, proxies /api etc. to the Python server on :5713
npm run build    # writes app/build/, which the Python server then serves at /
```

Screens: **Glyphs** (every SVG on disk, grouped by area, with the
unassigned ones called out; a **Tile view | Table view** switch, where Table view is a
spreadsheet of every glyph's spellings — the `components.csv` columns —
with paste-a-range, CSV import/export, clash checks as you type, and an
inspector with Try it, What changes and Issues; see `docs/KEY-ENTRY-UX.md`;
the **glyph editor** at `/glyphs/<name>/edit` and `/glyphs/new`
edits outlines on a Paper.js canvas, imports SVGs, traces images with
potrace, and writes the file through `PUT /api/svg/<name>`; see
`docs/GLYPH-EDITOR-UX.md`), **Layouts** (word types; eight dockable, foldable,
resizable panels around the canvas, arrangement kept in the browser; canvas with draggable parts;
Structure, Spacing as a rule builder (base chain, rule rows, glyph-grid
rule editor with live canvas preview), Centering, Area Properties (the
shared areas: switcher, box size previewed on the canvas until Enter,
members with the position decimals as a grid, + New area under Advanced;
see `docs/AREAS-PLACEMENT-UX.md`; the old Areas screen is gone); a live test strip;
Advanced toggle for structural edits), **Build & test** (`/test`: Build button
with log, each build a separate file in a temp folder with Download; one font
picker, a build from this session or a `.ttf` opened from disk, loaded under its
own font name so an installed JianZiPu never stands in, characters the file lacks
drawn in red by a system font; a **Test the design** view, live preview vs the font per
word over sample sets, and a **Test the font file** view, running text with liga / kern
switches, vertical columns and an optional second font side by side; the old
`/tester?build=…` links land on the font-file view),
**Review** (a tester's draft, from Supabase or a `.zip`, item by item: glyphs before / after / overlay,
spellings, design units with sample words and the JSON diff; Keep / Skip, conflicts picked by hand;
Apply makes them unsaved changes; see "Hosted pilot" below). Edits are held in the
browser until **Save (⌘S)**, which writes `design.json` and/or `components.csv` (and glyph files a Review
Apply brought in); Save refuses to clobber a file that
changed on disk, and waits while a spelling clashes. **⋯ → Import/Export** moves the whole design as one JSON
file; **⋯ → Download as draft .zip** packs your unsaved changes the way a tester's Export does.
`.claude/launch.json` has a `builder` entry that starts the server.

## Hosted pilot

A few invited testers use the Builder online; each works in a private **draft**; nothing they do
changes the repo. Spec and copy: `docs/PILOT-UX.md` (local notes).

```
browser (app/, hosted mode) ──magic link──▶ Supabase Auth (invite-only)
        │  draft (bundle JSON) ◀─────────▶ Supabase table drafts (one row per tester)
        └─ /api/* + Bearer token ──▶ Railway: webserver --hosted (read-only; builds a draft's font
                                      in a temp dir; base font fetched from Storage assets/)
        └─ Change Requests ──▶ Supabase table change_requests ──webhook──▶ Edge Function notify ──▶ email
your machine: webserver (local) → /review (decide) → /release (candidate branch, tags) → GitHub
```

- **Server** (`webserver --hosted` or `JZP_HOSTED=1`, `jzpbuild/hosted.py`): PUT and DELETE answer 403;
  every POST needs a signed-in tester (the token is checked with Supabase `GET /auth/v1/user`, cached
  5 min); builds are per tester, random ids, and take the draft as inputs (`--design`,
  `--input-components`, `--input-svg-dir`); `/api/words` and typing previews use the tester's latest
  build, else main's. At start it downloads the base font from Storage (`JZP_BASE_FONT_OBJECT`, default
  `assets/TW-Kai-98.ttf`, with `SUPABASE_SERVICE_KEY`) and builds main's font once.
- **App** (`app/src/lib/hosted.svelte.ts`, `drafts.ts`, `bundle.ts`, `merge.ts`, `state.svelte.ts`):
  sign-in gate, "✎ Your draft" pill, Save and 30-second autosave to the draft (also on screen change and
  tab close), an offline buffer in the browser, "saved somewhere else" when another tab saved first
  (`save_draft()` writes only over the row this tab loaded, so the check and the write are one step),
  the new-release banner with Set reference font (three-way: the font's changes come in, conflicts are
  Keep mine / Take the font's), ⋯ → Export / Import a draft (.zip), Discard my draft, See my changes.
- **Bundle** (a draft, an Export .zip, what Review opens): `manifest.json`, `design.json`,
  `components.csv`, `svg/` (added and changed glyphs only), `base/` (the versions the draft started
  from, for the three-way merge). Glyph files from someone else are sanitised before they are shown.

To look at the hosted screens (the sign-in page, the draft pill) on your own machine, start the
server in hosted mode with placeholder Supabase settings; the pages render, sign-in itself won't
send anything:

```bash
cd builder && SUPABASE_URL=https://placeholder.supabase.co SUPABASE_ANON_KEY=placeholder python3 -m jzpbuild.webserver --hosted --port 5716
```

### Setting it up

Supabase (the SQL files in order, auth settings, email templates, invites, the base font in
`assets`), Railway (the variables, the domain) and your local `builder/.env` are in
[docs/maintainers/setup.md](../docs/maintainers/setup.md). To run the hosted image locally:

```bash
cd builder && cp .env.example .env    # then edit .env
cd builder && python3 -m jzpbuild.webserver
docker build -t jzp-builder . && docker run --rm -p 5713:5713 --env-file .env jzp-builder   # the hosted image, locally
```

### Moving drafts from the old bucket

Drafts used to be files, `drafts/<user id>/draft.json` in a Storage bucket. To move a project that
has them: run `supabase/002_drafts_table.sql`, then copy the files into the table with the service
key given to this one command only (Dashboard → Project Settings → API keys; don't save it in
`.env`):

```bash
cd builder && SUPABASE_SERVICE_KEY=... python3 -m jzpbuild.migrate_drafts --dry-run   # what it would copy
cd builder && SUPABASE_SERVICE_KEY=... python3 -m jzpbuild.migrate_drafts             # copy; never overwrites a row
```

Check the rows (Table Editor → drafts), run `supabase/003_drop_drafts_bucket.sql`, then delete the
`drafts` bucket in Storage.

### Change Requests

A tester sends chosen changes from their draft as a **Change Request** (Your changes → Send Change
Request…: title, notes, how to credit them). Before it goes, the draft is saved, the chosen spellings
are checked and a font is built from just those changes. Sent changes are locked in the tester's
draft until the request is withdrawn (possible until an admin keeps one of its changes) or
declined. Table, row rules and the two RPCs: `supabase/004_change_requests.sql`; app side
`app/src/lib/requests.ts`; emails `supabase/functions/notify/` (its README has the setup). **Save as draft** in the Send form keeps it unsent in `drafts.request_draft` (`supabase/005_request_drafts.sql`), shown on Your Change Requests with Continue.

Review (local, signed in as the admin) lists them: Keep or Skip each change, reply, **Save
decisions**; nothing goes into the font until a release candidate. The maintainer's side is in
[docs/maintainers/reviewing.md](../docs/maintainers/reviewing.md).

### Merging a tester's draft directly

Review → Current drafts → the tester's row (or Open a .zip) → each item shows what changed; Keep or
Skip it (a conflict, where your Builder also changed the same thing since the draft started, needs a
pick). **Apply** turns the kept items into one undoable step of unsaved changes, glyph files
included. Look them over in Layouts and Build & test, **Save**, then commit with the message the
toast copies ("Apply Mei Chen's draft: …"). The row is marked "reviewed" in this browser; a later
save by the tester shows "new since you looked".

## Releases

A release turns kept changes into a new version of the font, from the local Builder's **Release**
screen (`jzpbuild/release.py`; the same steps on the command line: `python3 -m jzpbuild.release
status|start|candidate|publish`): a `release/<version>` branch from main, the kept changes, a
candidate tagged `v<version>-rc.N` (two commits: the design, then the font built from it, which
records the design commit's hash), the pull request merged with a merge commit, then Publish tags
`v<version>` on main. `.github/workflows/release.yml` turns each tag into a GitHub Release with
`site/JianZiPu.ttf` attached; `scope.yml` keeps font files (`FONT_PATHS`) on release branches and
code off them.

The whole process, versions, scope rules, the ruleset on main and troubleshooting:
[docs/maintainers/releasing.md](../docs/maintainers/releasing.md).

## Command line

The Builder runs builds and checks for you; these are for scripting, CI and the tests.

```bash
cd builder
python3 -m jzpbuild                          # build from inputs/ -> JianZiPu.ttf
python3 -m jzpbuild --fea-only               # just regenerate the feature file (fast)
python3 -m jzpbuild -o /path/to/JianZiPu.ttf # write the font somewhere else (e.g. a release copy)
python3 -m jzpbuild --design ./scratch/design.json   # position from another design file
python3 -m jzpbuild --classic_pos            # legacy: position from inputs/layouts.json + gpos.py
python3 -m jzpbuild --input-components ./experiment/components.csv  # override one input file
python3 -m jzpbuild --help                   # full list of --input-* overrides
python3 -m jzpbuild.webserver                # API + the Builder app at http://127.0.0.1:5713/
```

By default the build writes to `builder/JianZiPu.ttf`, and the
`--fea-out` inspection copy of the generated feature text to
`builder/JianZiPu.fea` — both build artifacts, both gitignored. So
running the pipeline never touches anything tracked: the shaping regression
test always has an untouched golden reference (`config.CURRENT_FONT`,
`tests/JianZiPu.ttf`) to compare against, and you can preview a build (via
the Builder's Build & test screen) before
copying it anywhere with `-o`.

**`builder/inputs/` is the only source read at build time — no fallback.**
`config.py`'s paths are the single source of truth: a plain build reads SVGs
from `config.COMPONENTS_DIR` (`builder/inputs/svg/`) and the positioning
design from `config.DESIGN_JSON` (`builder/inputs/design.json`) with no
alternate location to fall back to (unless overridden on the CLI — see
"Overriding individual input paths" below). `builder/inputs/` is tracked
in git in full: a Save in the Builder shows up as a `git status` diff under it,
to review and commit like any other source change.

### Overriding individual input paths

Every path `config.py` defines under `builder/inputs/` can be pointed
elsewhere for a single build via a matching `--input-*` flag, without
touching `config.py`:

```bash
python3 -m jzpbuild --input-components ./scratch/components.csv
python3 -m jzpbuild --input-glyph-rename ./scratch/glyphRename.csv
python3 -m jzpbuild --input-edge-cases ./scratch/edge_cases.fea
python3 -m jzpbuild --input-layouts ./scratch/layouts.json
python3 -m jzpbuild --input-svg-dir ./scratch/svg
```

Each defaults to the matching `config.py` constant (`COMPONENTS_CSV`,
`GLYPH_RENAME_CSV`, `EDGE_CASES_FEA`, `LAYOUTS_JSON`, `COMPONENTS_DIR`)
and only affects that one build invocation — nothing is written back to
`builder/inputs/`. Run `python3 -m jzpbuild --help` for the full, current
list (it's generated from the same argparse definitions, so it can't drift
from this doc).

## What it does

```
app/ (the Builder, served by jzpbuild.webserver) ──Save──▶ inputs/{design.json, components.csv, svg/}
builder/src_font/TW-Kai-98.ttf ──(base.py: fontTools subset + ch_* rename + metrics)──▶ base glyphs
inputs/svg/*.svg ──(glyphs.py: picosvg + pathops + cu2qu)──▶ PUA component glyphs
inputs/{components.csv, glyphRename.csv, edge_cases.fea} ──(features.py)──▶ GSUB feature text
inputs/design.json ──(positioning/: shapes → resolve → emit)──▶ GPOS feature text
                                       └──(feaLib)──▶ GSUB/GPOS ──▶ builder/JianZiPu.ttf
```

## How compilation works

`python3 -m jzpbuild` (`build.py::main()` → `build.py::build()`) runs four
steps in order, all in-memory until the final save:

**1. Generate the feature text — `genfea.py::generate()`.** Produces the
complete `.fea` source as a string, before anything is compiled. Two halves,
concatenated:

- **GSUB — `features.py::gen_gsub()`.** Loads `components.csv` via
  `data.py::load_components()`, then immediately calls
  `validate.py::validate_or_raise()` (the uniqueness checks — see "What must
  be unique" above) before generating anything, so a bad CSV aborts here,
  before any lookup text is even built. Then, in order: `gen_classes()`
  builds every `@area_*` glyph class from `design.json`'s area membership;
  the hand-written `edge_cases.fea` is spliced in verbatim; then
  `l2j_digit_liga` (Latin spellings that contain a digit, see below); then one lookup
  per input pathway — ASCII/decimal (`s2j_*`), latin (`l2j_*`), Chinese
  (`c2j_*`, several passes since Safari can't do single-step contextual
  ligatures — see `gen_c2j_char_deci_liga_parts()`'s docstring), the
  hui-glyph-level decimal collapse (`char_deci_liga_part1/2`), and finally
  `gen_liga_feature()` assembles all of those lookups into one `liga`
  feature block in the specific order that makes longest/most-specific
  matches win before more general fallbacks (see the `ch_shang`-vs-`ch_1`
  trace pattern: single fallback substitutions always sit last).
- **GPOS — `positioning/emit.py::gen_gpos(design)`.** `design` is
  `inputs/design.json` parsed by `positioning/schema.py`. For every word
  type (`layouts[]`) `shapes.py` enumerates the concrete word shapes
  (which optional parts are present, which alternative each slot holds,
  how many rows a repeated slot has), `resolve.py` turns each shape into
  absolute x/y per part from the spacing relationships, and `emit.py`
  writes one chained-context rule per shape (longest first) whose glyphs
  dispatch cursive-attachment pair lookups carrying the y-delta to the
  previous part, a single-adjust lookup with the first part's absolute y,
  and a separate x pass. See "`jzpbuild/positioning/` and `design.json`"
  below. `--classic_pos` swaps this for the legacy `gpos.py` builder.

At this point `fea_text` is a complete, self-contained string — nothing has
touched a font yet. This is exactly what `--fea-only` writes out and what
`feadiff` compares.

**2. Build the base font — `base.py::build_base()`.** Subsets
`builder/src_font/TW-Kai-98.ttf` down to printable ASCII/NBSP
(`config.BASE_KEEP_CODEPOINTS`) plus every character referenced anywhere in
`components.csv`'s `simplified`/`traditional` columns *or* listed in
`glyphRename.csv` (`data.py::referenced_chars()` ∪ the override dict — a
character doesn't need a `glyphRename.csv` row to survive subsetting
anymore), via `fontTools.subset`. `rename_glyphs()` then renames only the
characters that have an explicit `glyphRename.csv` override to their `ch_*`
name; every other kept Han character keeps fontTools' default `uniXXXX`
codepoint name (see the `ch_shang`/`ch_gu` trace above for exactly what this
does to one glyph, and `data.py::resolve_char_to_glyph_name()` for how
`features.py` resolves the same character to the same name when generating
GSUB rules). Also sets metrics, name table, and OS/2 fields from
`config.py`.

**3. Import component glyphs — `glyphs.py::add_component_glyphs()`.** Reads
every SVG in `config.COMPONENTS_DIR` (`inputs/svg/`), in sorted
filename order, and for each: strips clip-path noise (frame cropping from exported SVGs), normalizes with
`picosvg`, draws into a `pathops.Path` to remove overlaps and resolve the
fill rule, converts to quadratic curves with `cu2qu`, and adds it to the
font as a new glyph (named from the SVG's filename stem) at its PUA codepoint:
the one pinned for it in `inputs/glyph_ids.json` (`glyph_ids.py`), or, for a
glyph with none yet, the next one after every pinned and retired code, from
`config.COMPONENT_GLYPHS_BASE` up. The local Builder pins a new glyph's code
when it saves the file, so renaming, deleting or adding a glyph never moves
another glyph's code (`tests/test_glyph_edit.py` checks every SVG is pinned). This is also the step where a
`components.csv` row whose `glyph_name` has no matching SVG file would
surface — not here directly, but as a `feaLib` "glyph missing from glyph
set" error in the next step, since the GSUB text from step 1 already
references it by name.

**4. Compile and save.** `addOpenTypeFeaturesFromString(font, fea_text)`
hands the step-1 text and the step-2/3 font (base Han glyphs + PUA
components, no OpenType tables yet) to `fontTools.feaLib`, which resolves
every class/lookup reference against the font's actual glyph set and
produces real `GSUB`/`GPOS` tables. `font.save(out_path)` writes the `.ttf`.

Upstream of all this, the Builder's Save writes `builder/inputs/`;
the four steps above only ever read what's already sitting there.

## Sources of truth (what you edit)

| To change...                       | Edit...                                                       |
|------------------------------------|---------------------------------------------------------------|
| glyph shapes                       | Builder → Glyphs → Edit (draw, import or trace; writes `inputs/svg/`) |
| a glyph's name, or the glyph itself | Builder → Glyphs → Rename… / Delete… (local; rewrites every input that names it, `glyph_edit.py`) |
| which glyphs belong to which part  | Builder → Layouts → Area Properties, or Glyphs (writes `inputs/design.json`) |
| word types, spacing, centering     | Builder → Layouts (writes `inputs/design.json`)                |
| input keys / spellings             | Builder → Glyphs → Table view (writes `inputs/components.csv`)     |
| Han char glyph names               | `builder/inputs/glyphRename.csv`                         |
| disambiguation rules               | `builder/inputs/edge_cases.fea`                          |
| metrics / naming / config          | `jzpbuild/config.py`                                           |

Everything else — glyph classes, all substitution lookups, the 13×9 hui/
decimal matrices, and every positioning rule — is generated.

### `inputs/components`

(Named `areaKeySVGMap.csv` in the legacy pipeline, then `glyphAreas.csv`
early in this pipeline, renamed again to `components.csv` since it's really
the catalog of every component glyph — its area membership is one of
several things it tracks, not the whole story.) One row per component glyph
(≈90 rows) — the join between "what can
someone type" and "what layout area does the resulting glyph belong in."
`features.py`/`gpos.py` derive almost every GSUB class and rule from it.
Columns:

- `glyph_name` — the PUA component glyph this row describes. This string is
  used twice: it's the filename `glyphs.py` looks for under
  `src/components/` (`glyph_name.svg`), and it's the name that glyph gets in
  the compiled font (fontTools names it from the SVG's filename stem). The
  two uses are coupled by convention, not enforced — renaming a row here
  without renaming the matching SVG breaks the build.
- *(area membership is no longer a CSV column.)* Which glyphs belong to
  which area (`left`, `hui`, `right`, `char`, …) lives in
  `inputs/design.json` → `areas.<name>.glyphs`, edited in the Builder's
  Area Properties panel (Layouts) or from a glyph's "In areas" chips. A glyph can belong to more than one area, e.g. the
  hui-number glyphs (`md_1`..`md_13`) are both `hui` and `char` (chars for
  vertical-word mode, hui for normal word layout). `gen_classes()` in
  `features.py` turns each area into an `@area_*` glyph class (plus the
  legacy `@area_mod_jc`-style aliases); the positioning rules then match
  words by those classes. So area membership decides which *part* of a word
  a glyph can be — where that part sits is decided by the word type's
  spacing rules.
- `vert_variant` — for glyphs whose normal (left-aligned) form needs a
  centered replacement when it appears in vertical/char-stack mode (after
  `:`), the target glyph name (e.g. `lg_lun` → `md_lun`). Empty for glyphs
  with no vert-mode variant. Drives the `@area_to_md_for_vert_from/_to`
  substitution pair.
- `common`, `latin`, `latin_alt` — the ASCII/latin spellings that trigger
  this glyph (`common` is the "primary" one shown in docs/tooltips; `latin`
  and `latin_alt` are alternate spellings that map to the same glyph, e.g.
  `banlun`/`bl`). Multi-letter uppercase spellings for chords also live in
  `common`.
- `simplified`, `traditional` — the Chinese-character spelling(s) that
  trigger this glyph, one column per script variant. Multi-character
  spellings (e.g. `半轮` for 半轮) become multi-glyph ligature rules;
  single-character ones become single substitution rules.

A blank cell means "not applicable," not "unset" — e.g. chord glyphs
(`xl_cuo` etc.) have no `latin`/`latin_alt`, only `common`.

### `inputs/glyphRename`

**Optional overrides file** (25 rows) — not every Chinese-spelled character
needs a row here anymore. `char` (a single unicode character) and
`glyph_name` (the name that character's glyph should have in the compiled
font) are the two columns the build actually reads; two more,
`type`/`notes`, are documentation-only (ignored by every loader —
`data.py`'s `csv.DictReader`-based readers only ever look up `rec["char"]`/
`rec["glyph_name"]` by key), used to record *why* a row exists:

- `type=load_bearing` — the `glyph_name` is referenced as a literal string
  constant somewhere in `features.py` or `edge_cases.fea` (e.g. `ch_1`
  through `ch_10` in `hui_ch()`, `ch_ban`/`ch_wai` for the special hui
  values, `PERIOD_SUBS`, `ch_v`/`ch_cuo` in `edge_cases.fea`'s
  `ch_dc_sub`). Renaming or removing one of these rows breaks the build
  unless the matching Python/`.fea` literal is updated too — `notes` says
  which file/function to also touch.
- `type=unreferenced` — kept for a future feature, not currently used by
  anything (`弦`/`絃` `ch_xian`/`ch_xian_trad`: added to the font ahead of
  a planned string-indicator feature described in `CHANGELOG.md`, but never
  wired into `components.csv`).

Every other Chinese-spelled character (the vast majority — anything used in
`components.csv`'s `simplified`/`traditional` columns with no row here) is
resolved automatically by `data.py::resolve_char_to_glyph_name()`: it starts
from this file's override dict, then for any referenced character with no
override, synthesizes `uni{codepoint:04X}` — the same default name
fontTools' subsetter already gives any un-renamed Han glyph (see below), so
no rename step is needed for it either. This is also why *keeping* a
character during subsetting no longer depends on this file — see the
`base.py` step above; only the character's *name* does.

Why rename at all (for the rows that do get one): FEA substitution rules
reference glyphs by bare ASCII-word tokens (`sub ch_k by lg_gou;`), and
fontTools' default subsetted name for an unrenamed Han glyph is a `uniXXXX`
codepoint name (e.g. `uni52FE`) — which would technically also work as an
FEA token, just less legibly. The rename isn't a hard technical requirement,
it's a deliberate convention: it keeps Han glyphs under the same
short-mnemonic naming scheme as everything else in the font (`md_*`, `lg_*`,
`xl_*`, `mod_*`, now `ch_*`) for the characters worth naming that way —
load-bearing ones, or anyone who wants a specific character to read cleanly
in the generated `.fea`. To keep *that* legible even for auto-derived
`uniXXXX` names, every Chinese-input substitution `features.py` generates
carries a trailing comment mapping each token back to its source character,
e.g. `sub uni5E94 uni5408 by md_yinghe; # uni5E94=应 uni5408=合`.

The `ch_*` suffix is usually derived from the glyph's latin key in
`components.csv` (勾's key is `k`, so `ch_k`) but the two files aren't
mechanically linked — changing a key in `components.csv` does not
auto-update the matching rename here.

Printable ASCII + NBSP are kept unconditionally via
`config.BASE_KEEP_CODEPOINTS` and pass through with their original TW-Kai
glyph names, so they never need rows in this file.

### `builder/inputs/edge_cases.fea`

Raw FEA `lookup { ... }` blocks, included verbatim into the generated
feature file's `liga` feature. This is the one place where hand-written
substitution logic is allowed to bypass the CSV-driven generator — reserved
for disambiguation that the generic rules can't express (today only
`ch_dc_sub`). Latin spellings with a digit in them (`zhi4`, `xi4`, `fu4`) used
to need a hand rule here, since the number lookups read the `4` first; they
are now generated (`features.py::gen_l2j_digit_liga`, one lookup defined
before the number lookups: OpenType runs lookups in the order they are
*defined*, not the order a feature lists them). Keep this file small; anything expressible as a
CSV row (a new spelling, a new area membership) belongs there instead, since
CSV-driven rules get maintained (reordered, regenerated) automatically while
hand-written FEA does not.

### `jzpbuild/positioning/` and `inputs/design.json`

The positioning model, replacing `gpos.py` + the classic layout frames. `design.json`
(version 2) holds:

- **`areas`** — the reusable parts a word is made of: a box size, the
  glyphs allowed in it, a label, and (for the `:` colon and the `|` bar) an
  `advance` that moves the pen. An area is defined once and used by any
  number of word types.
- **`layouts`** — the word types (`standard`, `vertical`, `chord`,
  `chord_right`). Each lists its **slots** in typing order; a slot is
  optional or required, holds one of several **alternatives** (lists of
  `element:area` parts, so the same area can appear twice, as in 歷's two
  strings), and may **repeat** (`[min, max]` rows, as in vertical words).
  `requires_any`/`priority` decide which reading wins when the same glyphs
  fit two shapes.
- **`relationships`** — the spacing rules: `elem`'s `elem_edge` lands at
  `base`'s `base_edge` plus `gap`, per axis. `base: null` is an absolute
  position, `base: "prev"` the previous row. The first rule whose base is
  present in the word wins, so a part can say "below jc if there is one,
  else below hui, else below left". `gap` is a number or an ordered list of
  `{when_base, when_elem, value}` exceptions, first match wins, so 勾 and
  歷 can sit at different heights without separate word types.
- **`center`** — which parts the vertical/horizontal centering spans, parts
  that count even when absent (`y_phantom`, so a word keeps its height with
  or without a string), and the target.

The package (`schema.py` → `shapes.py` → `resolve.py` → `emit.py`) turns
that into GPOS: one rule per concrete word shape, all shapes of all word
types in one `pos_y` lookup (longest first, a matched rule consumes its
glyphs, which is the only scoping needed) and one `pos_x` lookup. Each rule
marks every glyph; the first glyph of a chain dispatches `cen_<y>` (the
word's absolute, centred y) and each later glyph a `cur<n>` cursive pair
lookup whose entry anchor carries the delta to the previous glyph. Parts
with an `advance` (colon, bar) are chain breakers: what follows starts a
new chain and its x is pen-relative. When a gap depends on glyph identity
the shape is split into per-glyph buckets plus an `@pos_…_other` class, so
only the parts named in exceptions multiply rules. `emit.stats()` is the
"font budget" the app shows. This shapes identically under HarfBuzz and
CoreText (`tests/shaper_parity.py`); the only engine constraints are that
cursive rules use the default lookup flag and that x is a separate pass
(cursive zeroes x offsets in HarfBuzz and chains them in CoreText).

`jzpbuild/gpos.py` + `inputs/layouts.json` remain only for `--classic_pos`,
used by `tests/parity_report.py` to compare the two models.

### `jzpbuild/config.py`

Static configuration that isn't derivable from the inputs: file
paths, font metrics (upm, ascent/descent, OS/2 fields),
the name table, PUA codepoint ranges for control/component glyphs, and the
`RIGHT_SELECTORS` map (which `lg_*` glyphs select which right-hand-technique
layout family — `RIGHT_KEYS` is derived from it). Edit this when the font's
identity/metrics change or a new right-hand technique family is added to
`gpos.py` and needs a selector class.

## Common tasks

Two worked examples of adding new content. Both follow the same shape: get
the SVG into `builder/inputs/svg/`, add the glyph to an area and give
it spellings in the Builder (Glyphs → Table view), rebuild. Neither needs a
code change: a new *member* of an existing area is positionable everywhere
that area already appears. New word types, parts and spacing rules are
edited in the Builder's Layouts screen (Advanced toggle for structure).

**What must be unique, and what happens if it isn't.** `jzpbuild/validate.py`
checks the three riskiest ones automatically — `gen_gsub()` calls
`validate_or_raise()` before generating any lookups, so a real violation now
aborts the build immediately with a message naming the exact conflicting
glyphs/characters, rather than silently compiling something wrong. It knows
about the one legitimate exception (a horizontal glyph and its
`vert_variant` sharing a spelling on purpose — see `lg_lun`/`md_lun`) and
doesn't flag that pattern. Still worth understanding *why*, since the
underlying mechanism explains what "conflict" means here:

- **Any spelling key** (`latin`, `latin_alt`, `common`, `simplified`,
  `traditional`) in `components.csv` must not already be used by another
  row: Latin Entry, Latin Entry (Alt) and alphabetic Number/Symbol values
  share one namespace, 简体 and 繁體 each have their own. The Builder checks
  this as you type and holds Save until a clash is fixed
  (`typing_preview.issues()`, the same check `PUT /api/glyphs` runs).
  `latin_entries()`/`chinese_entries()` in `features.py` resolve raw
  collisions with a "non-`char`-only row wins" preference rule; the
  validator now catches any collision that isn't the known
  horizontal/`vert_variant` pattern, but the rule itself is why a
  *tolerated* collision (the vert-variant case) silently picks a winner
  instead of erroring.
- **`char` in `glyphRename.csv`** must be unique — `validate.py` catches
  duplicates. Underlying mechanism if it didn't: `load_char_to_glyph_name()`
  is a plain dict comprehension, so an unchecked duplicate would silently
  keep whichever row comes last in the file.
- **`glyph_name` (the `ch_*` target) in `glyphRename.csv`** must be unique
  too — also caught by `validate.py`. Underlying mechanism: reusing an
  existing `ch_*` name for a *different* character doesn't error in
  `rename_glyphs()` (`base.py`) either; it ends up mapping two different
  source TW-Kai glyphs onto the same target name, and the dict-based rename
  silently keeps only one of the two outlines.
- **Every resolved name** (overrides from `glyphRename.csv` *plus*
  auto-derived `uniXXXX` fallback names) **must be unique across the merged
  namespace** — `validate.py` recomputes
  `data.py::resolve_char_to_glyph_name()` and checks this too, catching the
  unlikely edge case where a hand-picked override collides with another
  character's `uniXXXX` name (auto-derived names can never collide with each
  other, since one codepoint always maps to one deterministic name).
- **`glyph_name` in `components.csv`** must match its SVG's filename
  exactly (`glyph_name.svg`) — that's a hard requirement, not just a style
  preference, since `glyphs.py` imports by filename stem. **Not checked by
  `validate.py`** (it's a missing-file problem, not a uniqueness one — it
  surfaces as a `feaLib` "glyph names referenced but missing from the glyph
  set" error at compile time instead, still before a font is written).
  Reusing an existing `glyph_name` across two rows isn't dangerous the way
  the above are (worst case, two spellings just resolve to the same glyph)
  — if that's what you actually want, prefer adding a second key via
  `latin_alt`/`common` on the *same* row instead of a duplicate row.

### Case 1: add a character for use in the vertical (`:`) layouts

1. Export the glyph as `inputs/svg/md_<name>.svg` (a 350×350 box, like the
   other `md_*` glyphs).
2. Builder → Glyphs → **Character** (`char`) in the sidebar → **+ Add glyphs**
   → pick it (or Layouts → Area Properties → switch to Character →
   Manage → + Add glyphs).
   Then Glyphs → select it → fill in its spellings (Latin Entry, 简体, 繁體,
   …) in the inspector or the Typing table; Save writes `components.csv`.
3. **Save**, then Build & test → **Build font**. Type `:<key>` in the test
   box: the live preview shows it as a row of a vertical word before the
   build finishes; the built font afterwards.

If the character should also work as a hui number or a left-hand glyph,
add it to those areas too; one glyph can be in several.

### Case 2: add a new SVG for the `jc` area (a third 急/绰-style marker)

1. `inputs/svg/mod_<name>.svg`, 200×200 like `mod_chuo`/`mod_ji`.
2. Glyphs → **急/绰 modifier** (`jc`) → + Add glyphs; set its typing key
   (Glyphs → Table view).
3. Save and build. It is positioned by the existing `jc` rules in every
   word type that has a `jc` part; if it needs its own gap, open Layouts,
   select the part whose gap depends on it, and add an exception row
   ("by glyph") naming the new glyph.

## Helpful Tools

The Builder's **Build & test** screen (`/test`) loads one exact `.ttf` (a build
from the running server, or any file from disk) under its own font name, so
an installed JianZiPu never stands in; characters the file lacks are drawn
in red. Its **Test the design** view puts the live preview and that font side by
side over sample sets (basic words, decimals, modifiers, chords, vertical
words, Chinese input, edge cases); its **Test the font file** view shows running text, with
a second font to compare.

## Verification

```bash
python3 tests/test_positioning.py                  # unit tests for positioning/ (no pytest needed)
python3 -m pytest tests/test_positioning.py tests/test_glyphs.py tests/test_webserver.py   # all unit tests: positioning, SVG flattening, SVG endpoints
python3 -m pytest tests/test_shaping.py            # shaping regression against the golden font (needs a build)
(cd ../app && npm test)                            # Vitest: rules, shapes, gap helpers, panels store, glyph editor scene / ops / tools
python3 tests/test_shaping.py NEW.ttf              # compare an existing NEW.ttf vs tests/JianZiPu.ttf (golden)
python3 tests/test_shaping.py OLD.ttf NEW.ttf      # or compare two specific fonts directly
python3 -m jzpbuild --classic_pos -o /tmp/classic.ttf --fea-out "" && python3 -m jzpbuild -o /tmp/cursive.ttf --fea-out ""
python3 tests/parity_report.py /tmp/classic.ttf /tmp/cursive.ttf   # classic vs design.json positions, per word
python3 tests/shaper_parity.py /tmp/cursive.ttf    # HarfBuzz vs CoreText (macOS, needs swift)
python3 -m jzpbuild.feadiff GOLDEN.fea NEW.fea     # semantic .fea diff
```

`tests/test_shaping.py` shapes ~80 tutorial inputs with HarfBuzz against two
fonts and requires identical glyph sequences and positions. The golden
`tests/JianZiPu.ttf` is still the classic-positioned font, so the pytest
entry builds with `--classic_pos`; regenerate the golden from a default
build once the design.json positions are accepted (the parity report is
the acceptance check — the remaining differences are documented classic
quirks, see `docs/ROADMAP.md`).

## Notes

- TW-Kai's 1024-unit outlines are intentionally not rescaled to the 1000
  upem — the FontForge pipeline never did, and JZP components are drawn to
  match.
- The old font also shipped AAT tables (`morx`, `feat`) and vertical metrics
  (`vhea`/`vmtx`) that FontForge generated; this pipeline emits pure
  OpenType (GSUB/GPOS), which is what browsers and modern apps use.
- The legacy pipeline (FontForge scripts, `scripts.cjs`, the
  hand-maintained `fontForgeFeatures.fea` and the wide CSVs, all in
  `src-fontforge/`) was removed on 2026-10-18 and is in git history under the
  tag `fontforge-final`. The builder's slimmed CSVs (`builder/inputs/components.csv`,
  `builder/inputs/glyphRename.csv`) are the live sources of truth.
  `components.csv` is now `glyph_name,vert_variant,common,latin,latin_alt,
  simplified,traditional,pinyin`: `glyph_name` is the ID (the old
  ID/keys/filename columns duplicated it and were dropped), area membership
  lives in `design.json`, `pinyin` is reference only (the build doesn't read
  it), and `vert_variant` pairs a left-aligned glyph with its centered
  vert-mode form. A vertical form needs no row of its own: it is typed with
  its partner's spellings after a colon, and only spellings of its own
  (`md_san2`'s `san`) are stored for it.
