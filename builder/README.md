# jzpbuild — the JianZiPu font build pipeline

One command builds the font from sources, with no FontForge and no
hand-edited feature files.

## Setup (first time on a fresh checkout)

1. **Python >= 3.10.**
2. **Install dependencies:**
   ```bash
   cd builder
   pip install -e .          # fonttools, picosvg, requests, skia-pathops
   pip install -e '.[test]'  # + uharfbuzz, pytest — needed for tests/test_shaping.py
   ```
3. **Base font.** The pipeline subsets glyphs from a base Kai typeface, and
   expects it at `builder/src_font/TW-Kai-98.ttf`. This file is **gitignored
   and not included in the repo** (36MB, binary, not something git handles
   well) — copy/paste your own copy of `TW-Kai-98.ttf` there before your
   first build. Using a different base font, or a different filename? Change
   `SOURCE_FONT` in `jzpbuild/config.py` (`SOURCE_FONT = BUILDER_DIR /
   "src_font/TW-Kai-98.ttf"`) to point at it — everything downstream
   (`base.py`) just reads whatever path is set there.
4. **`builder/generated_inputs/`** (Figma-fetched SVGs + `positions.json`)
   is tracked in git, so a fresh checkout already has it — nothing to do
   here. Refresh it from Figma whenever you want the latest:
   ```bash
   export FIGMA_TOKEN=figd_...   # see "Figma access" below for where to get one
   python3 -m jzpbuild --figma_pull
   ```
   A plain build reads `builder/generated_inputs/svg/` and `positions.json`
   unconditionally, with no fallback location — if this directory is ever
   missing or emptied, the build fails fast with `FileNotFoundError` rather
   than silently reading something stale (see "config.py's paths are the
   single source of truth" below for why).

With those in place (base font placed, deps installed), you're set up —
everything from here on is just `python3 -m jzpbuild`.

## Commands

```bash
cd builder
python3 -m jzpbuild                          # build from builder/generated_inputs
python3 -m jzpbuild --figma_pull             # pull latest SVGs + positions from Figma first
python3 -m jzpbuild --fea-only               # just regenerate the feature file (fast)
python3 -m jzpbuild -o ../src/JianZiPu.ttf   # overwrite the tracked, released font
```

By default the build writes to `builder/JianZiPu.ttf` — a build artifact,
not the tracked font — so running the pipeline never touches
`src/JianZiPu.ttf` unless you explicitly pass `-o ../src/JianZiPu.ttf` (or
`npm run font -- -o ../src/JianZiPu.ttf` from the repo root). This also
means the shaping regression test always has an untouched golden reference
(`config.CURRENT_FONT`) to compare against, and lets you preview a build
(via `tools/font_tester.html`) before deciding to overwrite the release.

`npm run font` at the repo root does the default build.

If a build ever does clobber `src/JianZiPu.ttf` unexpectedly: it's a
tracked file, so `git checkout -- src/JianZiPu.ttf` restores the last
committed version (or `git log -- src/JianZiPu.ttf` + `git checkout
<commit> -- src/JianZiPu.ttf` to go further back).

**`builder/generated_inputs/` is the only source read at build time — no
fallback.** `config.py`'s paths are the single source of truth: a plain
build reads SVGs from `config.COMPONENTS_DIR`
(`builder/generated_inputs/svg/`) and layout geometry from
`config.POSITIONS_JSON` (`builder/generated_inputs/positions.json`) with no
alternate location to fall back to. Unlike `builder/cache/` (a leftover,
gitignored, safe to delete), `builder/generated_inputs/` is tracked in git —
it's committed after each `--figma_pull` refresh, not regenerated on every
checkout, so treat a `git status` diff under it after `--figma_pull` as
something to review and commit like any other source change.

## What it does

```
Figma file ──(figma.py, REST API)──▶ builder/generated_inputs/{svg/*.svg, positions.json}
builder/src_font/TW-Kai-98.ttf ──(base.py: fontTools subset + ch_* rename + metrics)──▶ base glyphs
generated_inputs/svg/*.svg ──(glyphs.py: picosvg + pathops + cu2qu)──▶ PUA component glyphs
builder/inputs/{glyphAreas.csv, glyphRename.csv, edge_cases.fea} + gpos.py layouts ──(features.py/gpos.py)──▶ features.fea
                                       └──(feaLib)──▶ GSUB/GPOS ──▶ builder/JianZiPu.ttf
```

## How compilation works

`python3 -m jzpbuild` (`build.py::main()` → `build.py::build()`) runs four
steps in order, all in-memory until the final save:

**1. Generate the feature text — `genfea.py::generate()`.** Produces the
complete `.fea` source as a string, before anything is compiled. Two halves,
concatenated:

- **GSUB — `features.py::gen_gsub()`.** Loads `glyphAreas.csv` via
  `data.py::load_area_map()`, then immediately calls
  `validate.py::validate_or_raise()` (the uniqueness checks — see "What must
  be unique" above) before generating anything, so a bad CSV aborts here,
  before any lookup text is even built. Then, in order: `gen_classes()`
  builds every `@area_*` glyph class straight from the CSV's area columns;
  the hand-written `edge_cases.fea` is spliced in verbatim; then one lookup
  per input pathway — ASCII/decimal (`s2j_*`), latin (`l2j_*`), Chinese
  (`c2j_*`, several passes since Safari can't do single-step contextual
  ligatures — see `gen_c2j_char_deci_liga_parts()`'s docstring), the
  hui-glyph-level decimal collapse (`char_deci_liga_part1/2`), and finally
  `gen_liga_feature()` assembles all of those lookups into one `liga`
  feature block in the specific order that makes longest/most-specific
  matches win before more general fallbacks (see the `ch_shang`-vs-`ch_1`
  trace pattern: single fallback substitutions always sit last).
- **GPOS — `gpos.py::gen_gpos(positions)`.** `positions` comes from
  `genfea.py::load_positions()`, which just reads `config.POSITIONS_JSON`
  (`generated_inputs/positions.json`) — no code generation here, purely
  data. `gen_gpos()`'s rule-builder functions (`word_layout_rules()`,
  `no_left_layout_rules()`, `vert_rules()`, `cuo_rules()`) enumerate, for
  each layout family, every valid area-class sequence a composed word can
  take (see the module docstring on why rule *order* is load-bearing), and
  `fill_rule()` looks up each marked token's `x`/`yd` in `positions` to bake
  in a literal `pos ... <x yd 0 0>;` line per rule.

At this point `fea_text` is a complete, self-contained string — nothing has
touched a font yet. This is exactly what `--fea-only` writes out and what
`feadiff` compares.

**2. Build the base font — `base.py::build_base()`.** Subsets
`builder/src_font/TW-Kai-98.ttf` down to printable ASCII/NBSP
(`config.BASE_KEEP_CODEPOINTS`) plus every character listed in
`glyphRename.csv`, via `fontTools.subset`. `rename_glyphs()` then renames
each kept Han character's default `uniXXXX` glyph name to its `ch_*` name
and remaps `cmap` accordingly (see the `ch_shang`/`ch_gu` trace above for
exactly what this does to one glyph). Also sets metrics, name table, and
OS/2 fields from `config.py`.

**3. Import component glyphs — `glyphs.py::add_component_glyphs()`.** Reads
every SVG in `config.COMPONENTS_DIR` (`generated_inputs/svg/`), in sorted
filename order, and for each: strips Figma clip-path noise, normalizes with
`picosvg`, draws into a `pathops.Path` to remove overlaps and resolve the
fill rule, converts to quadratic curves with `cu2qu`, and adds it to the
font as a new glyph (named from the SVG's filename stem) at a PUA codepoint
starting from `config.COMPONENT_GLYPHS_BASE`. This is also the step where a
`glyphAreas.csv` row whose `glyph_name` has no matching SVG file would
surface — not here directly, but as a `feaLib` "glyph missing from glyph
set" error in the next step, since the GSUB text from step 1 already
references it by name.

**4. Compile and save.** `addOpenTypeFeaturesFromString(font, fea_text)`
hands the step-1 text and the step-2/3 font (base Han glyphs + PUA
components, no OpenType tables yet) to `fontTools.feaLib`, which resolves
every class/lookup reference against the font's actual glyph set and
produces real `GSUB`/`GPOS` tables. `font.save(out_path)` writes the `.ttf`.

Upstream of all this, `--figma_pull` (`figma.py::fetch()`) is a separate,
optional step that populates `generated_inputs/` in the first place —
nothing in the four steps above talks to Figma directly, they only ever
read what's already sitting in `generated_inputs/`.

## Sources of truth (what you edit)

| To change...              | Edit...                                        |
|---------------------------|------------------------------------------------|
| glyph shapes              | Figma GLYPH pages (then `--figma_pull`)        |
| layout positions          | Figma LAYOUT frames (then `--figma_pull`)      |
| input keys / spellings    | `builder/inputs/glyphAreas.csv`                |
| Han char glyph names      | `builder/inputs/glyphRename.csv`               |
| disambiguation rules      | `builder/inputs/edge_cases.fea`                |
| layout structure          | `jzpbuild/gpos.py` (declarative rule builders) |
| metrics / naming / config | `jzpbuild/config.py`                           |

Everything else — glyph classes, all substitution lookups, the 13×9 hui/
decimal matrices, and every positioning rule — is generated.

### `builder/glyphAreas.csv`

(Named `areaKeySVGMap.csv` in the legacy pipeline; renamed here since it
carries both input spellings and area membership, not just an SVG↔area
map.) One row per component glyph (91 rows) — the join between "what can
someone type" and "what layout area does the resulting glyph belong in."
`features.py`/`gpos.py` derive almost every GSUB class and rule from it.
Columns:

- `glyph_name` — the PUA component glyph this row describes. This string is
  used twice: it's the filename `glyphs.py` looks for under
  `src/components/` (`glyph_name.svg`), and it's the name that glyph gets in
  the compiled font (fontTools names it from the SVG's filename stem). The
  two uses are coupled by convention, not enforced — renaming a row here
  without renaming the matching SVG breaks the build.
- `area_*` (`area_char`, `area_chord`, `area_fy`, `area_left`, `area_hui`,
  `area_mod_jc`, `area_mod_zhu`, `area_right`, `area_string`) — one-hot
  membership flags (any non-empty value counts as "yes"). A glyph can belong
  to more than one area, e.g. the hui-number glyphs (`md_1`..`md_13`) are
  both `area_hui` and `area_char` (chars for vertical-word mode, hui for
  normal word layout). `gen_classes()` in `features.py` turns each flag into
  an `@area_*` glyph class; `gpos.py` then emits, per layout, "wherever a
  member of `@area_left` appears in this word shape, move it to this
  layout's `area_left` x/y." So area membership decides which *slot type* a
  glyph can occupy in a composed word — it doesn't grant access to a
  specific layout's coordinates by itself. Which layout is active (and
  therefore which x/y a shared area like `area_left` resolves to) is decided
  separately, usually by which right-hand-technique glyph is present in the
  same word. If a given layout has no `area_left` entry in
  `layout_area_positions.json`, an `area_left` glyph simply has nothing to
  resolve to there.
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

### `builder/glyphRename.csv`

Two columns, `char` (a single unicode character) and `glyph_name` (the name
that character's glyph should have after subsetting from `src/TW-Kai-98.ttf`).
Only real renames are listed (108 rows) — Han characters get readable `ch_*`
names (e.g. 勾 → `ch_k`).

Why rename at all: FEA substitution rules reference glyphs by bare ASCII-word
tokens (`sub ch_k by lg_gou;`), and fontTools' default subsetted name for an
unrenamed Han glyph is a `uniXXXX` codepoint name (e.g. `uni52FE`) — which
would technically also work as an FEA token. The rename isn't a hard
technical requirement, it's a deliberate convention: it keeps Han glyphs
under the same short-mnemonic naming scheme as everything else in the font
(`md_*`, `lg_*`, `xl_*`, `mod_*`, now `ch_*`), which makes the generated
`.fea` legible instead of a wall of `uniXXXX` tokens, and gives `features.py`
one simple `char → glyph_name` table (`c2g`) to drive every Chinese-input
lookup from.

The `ch_*` suffix is usually derived from the glyph's latin key in
`glyphAreas.csv` (勾's key is `k`, so `ch_k`) but the two files aren't
mechanically linked — changing a key in `glyphAreas.csv` does not
auto-update the matching rename here.

Every character listed here is also implicitly added to the subsetter's
keep-list; printable ASCII + NBSP are kept unconditionally via
`config.BASE_KEEP_CODEPOINTS` and pass through with their original TW-Kai
glyph names, so they don't need rows in this file.

### `builder/inputs/edge_cases.fea`

Raw FEA `lookup { ... }` blocks, included verbatim into the generated
feature file's `liga` feature. This is the one place where hand-written
substitution logic is allowed to bypass the CSV-driven generator — reserved
for disambiguation that the generic rules can't express, e.g. `z h i 4`
normally ligates greedily as `zhi` + `four`, but `lat_zhi4_sub` special-cases
it to `md_zhi4` first. Keep this file small; anything expressible as a
CSV row (a new spelling, a new area membership) belongs there instead, since
CSV-driven rules get maintained (reordered, regenerated) automatically while
hand-written FEA does not.

### `jzpbuild/gpos.py`

Not a data file — Python functions that declaratively enumerate the GPOS
positioning rules for each layout family (word layouts, vertical stacks, the
two-string 历 variant, 撮-chord segments). Each rule is a list of area-class
tokens with one token marked `'` (the glyph being positioned); `fill_rule()`
looks up that area's `x`/`yd` in `generated_inputs/positions.json` (from Figma)
to produce the final `pos ... <x yd 0 0>;` line. Edit this file when a
*layout's structure* changes (a new area combination becomes possible, a new
right-hand technique family is added) — not for anything expressible as
per-glyph area membership, which belongs in `glyphAreas.csv` instead.
Rule order inside each generated lookup is load-bearing (see the module
docstring), so treat reordering existing rules as a behavioral change, not a
cleanup.

### `jzpbuild/config.py`

Static configuration that isn't derivable from the CSVs or Figma: file
paths, the Figma file key, font metrics (upm, ascent/descent, OS/2 fields),
the name table, PUA codepoint ranges for control/component glyphs, and the
`RIGHT_SELECTORS` map (which `lg_*` glyphs select which right-hand-technique
layout family — `RIGHT_KEYS` is derived from it). Edit this when the font's
identity/metrics change or a new right-hand technique family is added to
`gpos.py` and needs a selector class.

## Common tasks

Two worked examples of adding new content. Both follow the same shape: get
the SVG into `builder/generated_inputs/svg/`, add one row to
`builder/inputs/glyphAreas.csv`, rebuild. Neither needs a `gpos.py` change,
because both areas (`area_char`, `area_mod_jc`) are shared glyph classes
already wired into every layout's rules — a new *member* of an existing
area is automatically positionable everywhere that area already appears;
you only touch `gpos.py` when the *shape* of a layout changes (a new area
combination, a new right-hand technique family).

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
  `traditional`) in `glyphAreas.csv` must not already be used by another
  row, *anywhere in the file* — not just within the same column.
  `latin_entries()`/`chinese_entries()` in `features.py` resolve raw
  collisions with a "non-`area_char`-only row wins" preference rule; the
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
- **`glyph_name` in `glyphAreas.csv`** must match its SVG's filename
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

Vertical/char-stack mode (input starting with `:`) positions each row from
the shared `@area_char` glyph class — see `vert_rules()` in `gpos.py` and
the `area_char{1..4}` entries in `positions.json`. Any glyph tagged
`area_char` in `glyphAreas.csv` is eligible, so:

1. Get the glyph's SVG into `builder/generated_inputs/svg/<glyph_name>.svg`
   (via `--figma_pull` if it's a new Figma GLYPH-page component, or drop it
   in by hand if you're not using Figma for this one).
2. Add a row to `builder/inputs/glyphAreas.csv` with that `glyph_name`, put
   any non-empty value in the `area_char` column, and fill in whichever
   spelling column(s) should trigger it (`latin`/`common` and/or
   `simplified`/`traditional`) — pick a key that isn't already claimed
   elsewhere in the CSV. Existing char-only examples to copy the shape of:
   `md_shang` (上, `area_char` only) or `md_xi` (息).
   - *Optional, only if using a `simplified`/`traditional` spelling:* that
     Chinese character also needs an entry in `builder/inputs/glyphRename.csv`
     (`char,ch_glyphname`) — it's what tells `base.py` to keep that
     character's codepoint when subsetting `TW-Kai-98.ttf`, and what
     `features.py`'s Chinese-input lookups use to find its glyph. Most common
     notation characters (上/下/大/小/etc.) are already in there — check
     first. If it's genuinely missing, the build fails loudly with a
     `KeyError` in `gen_c2j_char_left`/`gen_c2j_liga`/`gen_c2j_single`
     rather than silently ignoring the spelling, so this is easy to notice
     if skipped by mistake. Purely `latin`/`common`-triggered glyphs never
     need this file.
3. If this glyph *also* has a left-aligned form used in normal horizontal
   word layouts and needs a distinct centered look when stacked vertically,
   set `vert_variant` to the name of that centered glyph (which needs its
   own SVG + row too) — see `lg_lun` → `md_lun` for a working example. If
   it's vert-only, leave `vert_variant` blank.
4. Rebuild: `python3 -m jzpbuild`. The new glyph is picked up automatically
   into the generated `@area_char` class; no `gpos.py` edit needed.
5. Verify: try it in `tools/font_tester.html` (`:` + your new spelling), and
   run `python3 tests/test_shaping.py JianZiPu.ttf`-style regression
   check — add a line to `CORPUS` in `tests/test_shaping.py` if you want the
   new spelling itself covered going forward (existing entries won't catch
   it; see the shaping-test discussion above on what that test does and
   doesn't verify).

### Case 2: add a new SVG for `area_jc` (a third 急/绰-style marker)

`area_jc` (CSV column `area_mod_jc`) currently has two members — `mod_chuo`
(`/`, 绰) and `mod_ji` (`>`, 急). It's a shared class referenced by every
layout family's rules (the `jc` parameter throughout `word_layout_rules()`,
`no_left_layout_rules()`, and `cuo_rules()` in `gpos.py`), each with its own
`area_jc` x/y in `positions.json`. Adding a third member doesn't require
touching any of that:

1. Get the new SVG into `builder/generated_inputs/svg/<glyph_name>.svg`
   (same as Case 1 — `--figma_pull` or manual drop).
2. Add a row to `glyphAreas.csv`: `glyph_name` matching the SVG filename,
   any non-empty value in the `area_mod_jc` column, and a spelling key that
   doesn't collide with `/`, `>`, or anything else already in the CSV.
   - *Optional, only if using a `simplified`/`traditional` spelling:* same
     `glyphRename.csv` caveat as Case 1 step 2 applies here too — both
     existing `area_jc` members (`mod_chuo`/绰, `mod_ji`/急) have Chinese
     spellings, so this isn't hypothetical for this area. Check
     `glyphRename.csv` first; add a row only if the character is missing.
3. Rebuild: `python3 -m jzpbuild`. The new glyph joins the generated
   `@area_jc` class and is immediately positionable in every layout that
   has an `area_jc` slot — same mechanism as Case 1.
4. Verify the same way: `tools/font_tester.html` with your new spelling in
   a few different word shapes (with/without left hand, with/without a
   right-hand technique) to confirm it picks up each layout's `area_jc`
   position correctly, plus the shaping-test regression check.

## Figma access

`--figma_pull` needs `FIGMA_TOKEN` in the environment (Figma → Settings →
Security → Personal access tokens; `export FIGMA_TOKEN=figd_...` or put it
in `builder/.env` and source it). The file key lives in
`config.FIGMA_FILE_KEY`; only the page named `config.FIGMA_PAGE_NAME`
(default `"main"`, override via `FIGMA_PAGE_NAME` env var) is scanned —
other pages (drafts, archive, WIP) are ignored, and an unknown page name
fails fast listing the real page names in the file. Fetches are cached in
`builder/generated_inputs/` by file version (`meta.json`), so a repeat
`--figma_pull` against an unchanged Figma file is a no-op.

Two Figma-specific quirks this pipeline works around — worth knowing before
touching `figma.py` again:

- **Ink-cropped SVG exports.** Figma's `/v1/images?format=svg` endpoint
  crops each exported SVG's canvas to the tight bounding box of rendered
  ink (`absoluteRenderBounds`), discarding where that ink sat relative to
  the component's own declared frame (`absoluteBoundingBox`). Several JZP
  glyphs (`mod_zhu`, `mod_chuo`, ...) intentionally draw outside their
  frame — that bleed is load-bearing for positioning. `restore_frame_bounds()`
  undoes this per glyph, translating content back by
  `render_bounds − frame_bounds` and recanvasing to the frame size. Verified
  against the checked-in `src/components/mod_zhu.svg` to within ~0.7 units.
- **Image-export rate limits.** `/v1/images` is throttled harder than the
  rest of the API. `get()` retries 429/5xx with backoff (honoring
  `Retry-After`, capped at `MAX_AUTO_RETRY_WAIT = 60s`) — if Figma reports a
  longer wait, the fetch aborts loudly instead of hanging, since that
  usually means a **daily/monthly image-export quota** was hit (common on
  free-tier tokens), not a transient throttle. **We hit this quota during
  this session and it was never confirmed to reset/clear** — if `--figma_pull`
  fails with a multi-hour retry estimate, that's why. A possible follow-up
  if it recurs: split fetching into a cheap `--fetch-positions` (`/v1/files`
  only, not quota-limited) and a separate `--fetch-svgs` step, so layout
  tweaks don't burn the image quota.

### Layout count: 37 on Figma, 34 wired up

After the page-scoping fix, `--figma_pull` finds **37 layouts** on Figma's
"main" page vs. the legacy hand-maintained set's **34** (`layout_bo`,
`layout_char1-4` etc. showed up before page-scoping — page-scoping cut a
75-layout mismatch down to 37, but 3 extra remain). Several matching
layouts also have extra areas not in the legacy design
(`area_hui_small_top`/`_bottom`, `area_left_mod1`/`_mod2`, and `area_right`
newly present in `layout_li`). `gpos.py`'s declarative layout builders only
emit rules for the original 34-layout scheme and silently ignore the rest as
inert data (present in `positions.json`, but no glyph is ever routed to
them).

**Decision (file owner, current):** leave as-is for now — the 3 extra
layouts/areas can stay unused in the fetched data without being wired into
`gpos.py`. Revisit if/when those layouts are actually needed.

## Helpful Tools

Two self-contained, offline HTML tools live in `tools/` (no server, no
build tooling) — open `tools/index.html` for a landing page linking both.

### Positions checker (no-Figma workflow)

`tools/positions_checker.html` — auto-loads the current
`builder/generated_inputs/positions.json`, every SVG in
`builder/generated_inputs/svg/`, and `builder/inputs/glyphAreas.csv` on
open, so it's ready to explore immediately with no manual load step. (The
auto-load can't use `fetch`/`XMLHttpRequest` — Chromium refuses both for
`file://` sibling files — so it works by loading generated `.js` files
instead (`generated_inputs/positions.js`, `generated_inputs/svg_data.js`,
`inputs/glyphAreas.js`), each just assigning their data to a `window`
global via a `<script src>` tag, which *does* work over `file://`. The
first two are written by `figma.py::write_browser_data()` after every
`--figma_pull`; the CSV mirror is written by
`python3 -m jzpbuild.toolsdata`. All three are tracked in git alongside
their sources so a fresh checkout has them too; if you hand-edit
`positions.json`/`glyphAreas.csv` or drop in an SVG by hand instead of via
`--figma_pull`, refresh the relevant mirror with
`python3 -m jzpbuild.figma --browser-data-only` and/or
`python3 -m jzpbuild.toolsdata`. If a file is missing or stale, the page
falls back cleanly to the manual controls below — you'll see "auto-load
unavailable" in the status line instead of a broken page.)

For users who author glyph SVGs and `positions.json` with their own tools
(or want to try something different from what's checked in): load a
positions JSON, CSV, and/or any subset of SVGs (file picker or drag & drop)
to replace the auto-loaded set, preview how glyphs sit in each area using
the font's exact placement rule (natural size, bottom-anchored at
`y + h + 20`), then move/resize areas by drag or numeric input,
add/duplicate/delete layouts and areas, and download a corrected
`positions.json` (with `yd` recomputed) and/or `glyphAreas.csv` — drop them
in as `builder/generated_inputs/positions.json` /
`builder/inputs/glyphAreas.csv` for the build to pick up (then re-run
`--browser-data-only`/`toolsdata` to refresh this tool's own mirrors).
"Auto-assign SVGs by area name" prefers real `glyphAreas.csv` membership
when it's loaded (falling back to a small hardcoded candidate pool only for
areas with no matching CSV rows), and re-rolls on every click, so clicking
repeatedly is a quick way to spot bad fits across many glyph shapes.

**Area → components panel** (bottom of the page): click any area on the
canvas to see every glyph whose `glyphAreas.csv` row includes that area
(matched via the area name → CSV column mapping — e.g. canvas area
`area_hui_2` / `area_left_rt` both map to the `area_hui`/`area_left`
columns respectively, and `area_jc`/`area_zhu` map to the historically-named
`area_mod_jc`/`area_mod_zhu` columns), shown as clickable preview chips with
a `×` to remove that glyph from the area. Add another glyph via the
dropdown + "Add to area" (creates a minimal CSV row if the SVG has none
yet). Clicking a chip both assigns it to the currently-selected area in the
main canvas *and* opens an inspector panel on the right showing every area
that glyph belongs to across the whole CSV (editable checkboxes — this is
where you'd add/remove other area memberships, not just the current one)
plus its `common`/`latin`/`latin_alt`/`simplified`/`traditional` spellings
(editable text fields; `vert_variant` is shown read-only). All of this
edits the in-memory CSV rows directly — use "Download glyphAreas.csv" in
the side panel to save your changes out.

### Font tester (no-build-tooling workflow)

`tools/font_tester.html` — points at `../JianZiPu.ttf` by default; a
"Load / reload font" button cache-busts with a timestamp so it always
picks up your latest build, no hard-refresh needed. Includes a live
input/output pair, a 中文/ASCII toggle that loads two equivalent spellings
of the same passage (same pattern as `src/demo/index.html`), and example
chips across basic words, decimals, modifiers, chords, vertical words,
Chinese input, and edge cases. Change the path field to
`../../src/JianZiPu.ttf` to eyeball-compare against the released font
instead.

## Verification

```bash
pytest tests/test_shaping.py                      # builds into a temp dir, compares vs src/JianZiPu.ttf
python3 tests/test_shaping.py NEW.ttf              # compare an existing NEW.ttf vs src/JianZiPu.ttf
python3 tests/test_shaping.py OLD.ttf NEW.ttf      # or compare two specific fonts directly
python3 -m jzpbuild.feadiff GOLDEN.fea NEW.fea     # semantic .fea diff
```

`tests/test_shaping.py` shapes ~80 tutorial inputs with HarfBuzz against two
fonts and requires identical glyph sequences and positions. When the
pipeline was introduced this passed 78/78 (three inputs are compared with a
trailing space because the old FontForge-compiled font had an end-of-text
ligature bug — see `OLD_FONT_EOT_QUIRK` in the test). Also worth using:
`tools/font_tester.html` for a quick visual check after a rebuild.

## Notes

- TW-Kai's 1024-unit outlines are intentionally not rescaled to the 1000
  upem — the FontForge pipeline never did, and JZP components are drawn to
  match.
- The old font also shipped AAT tables (`morx`, `feat`) and vertical metrics
  (`vhea`/`vmtx`) that FontForge generated; this pipeline emits pure
  OpenType (GSUB/GPOS), which is what browsers and modern apps use.
- The legacy pipeline (FontForge scripts in `src/scripts/`, `scripts.cjs`,
  `src/input/figma.css`, hand-maintained `src/input/fontForgeFeatures.fea`,
  and the wide `src/input/*.csv` files) is deprecated and kept only for
  reference. The builder's slimmed CSVs (`builder/inputs/glyphAreas.csv`,
  `builder/inputs/glyphRename.csv`) are the live sources of truth: dead columns
  (ID/keys/filename/area_hui_deci/pinyin, identity ASCII rename rows) were
  dropped, and the per-glyph exceptions that used to be Python constants in
  `features.py` now live in the CSV (md_8/md_9 tagged `area_string`, md_jiu
  tagged `area_char`, and a `vert_variant` column pairing left-aligned
  glyphs with their centered vert-mode variants).
