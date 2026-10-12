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
4. **`builder/inputs/`** holds everything the build reads — both the
   hand-maintained sources (`components.csv`, `glyphRename.csv`,
   `edge_cases.fea`) and the Figma-fetched artifacts (`svg/`,
   `layouts.json`) — and is tracked in git, so a fresh checkout already has
   it — nothing to do here. Refresh the Figma-fetched half whenever you want
   the latest:
   ```bash
   export FIGMA_TOKEN=figd_...   # see "Figma access" below for where to get one
   python3 -m jzpbuild --figma_pull
   ```
   A plain build reads `builder/inputs/svg/` and `layouts.json`
   unconditionally, with no fallback location — if this directory is ever
   missing or emptied, the build fails fast with `FileNotFoundError` rather
   than silently reading something stale (see "config.py's paths are the
   single source of truth" below for why).

With those in place (base font placed, deps installed), you're set up —
everything from here on is just `python3 -m jzpbuild`.

## Commands

```bash
cd builder
python3 -m jzpbuild                          # build from builder/inputs
python3 -m jzpbuild --figma_pull             # pull latest SVGs + layouts from Figma first
python3 -m jzpbuild --fea-only               # just regenerate the feature file (fast)
python3 -m jzpbuild -o ../src/JianZiPu.ttf   # overwrite the tracked, released font
python3 -m jzpbuild --output ../src/JianZiPu.ttf   # same as -o, long form
python3 -m jzpbuild --input-components ./experiment/components.csv  # override one input file
python3 -m jzpbuild --help                   # full list of --input-* overrides
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

**`builder/inputs/` is the only source read at build time — no fallback.**
`config.py`'s paths are the single source of truth: a plain build reads SVGs
from `config.COMPONENTS_DIR` (`builder/inputs/svg/`) and layout geometry from
`config.LAYOUTS_JSON` (`builder/inputs/layouts.json`) with no alternate
location to fall back to (unless overridden on the CLI — see "Overriding
individual input paths" below). Unlike `builder/cache/` (a leftover,
gitignored, safe to delete), `builder/inputs/` is tracked in git in full —
the Figma-fetched half (`svg/`, `layouts.json`, `meta.json`) is committed
after each `--figma_pull` refresh, not regenerated on every checkout, so
treat a `git status` diff under it after `--figma_pull` as something to
review and commit like any other source change.

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
Figma file ──(figma.py, REST API)──▶ builder/inputs/{svg/*.svg, layouts.json}
builder/src_font/TW-Kai-98.ttf ──(base.py: fontTools subset + ch_* rename + metrics)──▶ base glyphs
inputs/svg/*.svg ──(glyphs.py: picosvg + pathops + cu2qu)──▶ PUA component glyphs
builder/inputs/{components.csv, glyphRename.csv, edge_cases.fea} + gpos.py layouts ──(features.py/gpos.py)──▶ features.fea
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
- **GPOS — `gpos.py::gen_gpos(layouts)`.** `layouts` comes from
  `genfea.py::load_layouts()`, which just reads `config.LAYOUTS_JSON`
  (`inputs/layouts.json`) — no code generation here, purely
  data. `gen_gpos()`'s rule-builder functions (`word_layout_rules()`,
  `no_left_layout_rules()`, `vert_rules()`, `cuo_rules()`) enumerate, for
  each layout family, every valid area-class sequence a composed word can
  take (see the module docstring on why rule *order* is load-bearing), and
  `fill_rule()` looks up each marked token's `x`/`yd` in `layouts` to bake
  in a literal `pos ... <x yd 0 0>;` line per rule.

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
filename order, and for each: strips Figma clip-path noise, normalizes with
`picosvg`, draws into a `pathops.Path` to remove overlaps and resolve the
fill rule, converts to quadratic curves with `cu2qu`, and adds it to the
font as a new glyph (named from the SVG's filename stem) at a PUA codepoint
starting from `config.COMPONENT_GLYPHS_BASE`. This is also the step where a
`components.csv` row whose `glyph_name` has no matching SVG file would
surface — not here directly, but as a `feaLib` "glyph missing from glyph
set" error in the next step, since the GSUB text from step 1 already
references it by name.

**4. Compile and save.** `addOpenTypeFeaturesFromString(font, fea_text)`
hands the step-1 text and the step-2/3 font (base Han glyphs + PUA
components, no OpenType tables yet) to `fontTools.feaLib`, which resolves
every class/lookup reference against the font's actual glyph set and
produces real `GSUB`/`GPOS` tables. `font.save(out_path)` writes the `.ttf`.

Upstream of all this, `--figma_pull` (`figma.py::fetch()`) is a separate,
optional step that populates `builder/inputs/` in the first place —
nothing in the four steps above talks to Figma directly, they only ever
read what's already sitting in `builder/inputs/`.

## Sources of truth (what you edit)

| To change...              | Edit...                                        |
|---------------------------|------------------------------------------------|
| glyph shapes              | Figma GLYPH pages (then `--figma_pull`)        |
| layout positions          | Figma LAYOUT frames (then `--figma_pull`)      |
| input keys / spellings    | `builder/inputs/components.csv`                |
| Han char glyph names      | `builder/inputs/glyphRename.csv`               |
| disambiguation rules      | `builder/inputs/edge_cases.fea`                |
| layout structure          | `jzpbuild/gpos.py` (declarative rule builders) |
| metrics / naming / config | `jzpbuild/config.py`                           |

Everything else — glyph classes, all substitution lookups, the 13×9 hui/
decimal matrices, and every positioning rule — is generated.

### `builder/components.csv`

(Named `areaKeySVGMap.csv` in the legacy pipeline, then `glyphAreas.csv`
early in this pipeline, renamed again to `components.csv` since it's really
the catalog of every component glyph — its area membership is one of
several things it tracks, not the whole story.) One row per component glyph
(91 rows) — the join between "what can
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
  `layout_area_layouts.json`, an `area_left` glyph simply has nothing to
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
  a planned string-indicator feature described in `versions.md`, but never
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
looks up that area's `x`/`yd` in `inputs/layouts.json` (from Figma)
to produce the final `pos ... <x yd 0 0>;` line. Edit this file when a
*layout's structure* changes (a new area combination becomes possible, a new
right-hand technique family is added) — not for anything expressible as
per-glyph area membership, which belongs in `components.csv` instead.
Rule order inside each generated lookup is load-bearing (see the module
docstring), so treat reordering existing rules as a behavioral change, not a
cleanup.

### How a layout gets picked

There's no runtime "choose a layout" step — every rule for every layout
variant is baked into one big contextual `pos` lookup
(`jzp_glyph_positioning`) at build time, and for a given glyph sequence
HarfBuzz just matches it against these rules in emission order, first match
wins. What looks like layout selection is really two things baked into which
rule matches:

1. **Which right-hand-technique family.** `config.RIGHT_SELECTORS` maps a
   family key (`loki`, `nc`, `tiao`, `mo`, `gou`, `io`, `li`) to the `lg_*`
   glyphs that belong to it; `gen_classes()` in `features.py` turns each key
   into an `@area_right__<key>` glyph class. `RIGHT_KEYS` (every key but
   `li`, which needs its own two-string rules) drives the loop in
   `gpos.py::gen_gpos()` that emits three GPOS layouts per family —
   `layout_<right>`, `layout_<right>2`, `layout_<right>3`. A word with no
   right-hand glyph at all falls into the `layout_blank*` family instead.
2. **Which of the 3 variants within that family.** Decided purely by which
   *other* area-glyphs are present in the word, via `word_layout_rules()` and
   `no_left_layout_rules()`: the `2` variant is the `jc=True` case (an
   `@area_jc` 急/绰 marker glyph is present), the plain variant is `jc=False`,
   and the `3` variant (`no_left_layout_rules`) is for words with no
   `@area_left` glyph at all. Within each, rules enumerate every legal
   presence-combination of `@area_fy`/`@area_left`/`@area_hui`/`@area_zhu`/
   `@area_string`, each keyed to its own x/y in `layouts.json` for that
   specific layout name.

A few families sit outside this scheme entirely: `layout_vertjzpN` (leading
`:`, stacked vertical char mode — `vert_rules()`), `layout_li*` (历 takes two
strings, so it gets bespoke rules despite being a `RIGHT_SELECTORS` key), and
`layout_cuo_*` (撮 chords, anchored on `@area_chord__cuo` or the `|` bar glyph
— `cuo_rules()`).

Because it's all first-match-wins in one lookup, rule *emission* order across
these blocks matters too, not just within a single block — e.g. the
`:大息` special case is emitted before the generic vertical/word rules so it
isn't misread as a word-layout left-hand glyph, and the bare-hui fallback is
emitted dead last in `gen_gpos()`.

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
the SVG into `builder/inputs/svg/`, add one row to
`builder/inputs/components.csv`, rebuild. Neither needs a `gpos.py` change,
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
  `traditional`) in `components.csv` must not already be used by another
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

Vertical/char-stack mode (input starting with `:`) positions each row from
the shared `@area_char` glyph class — see `vert_rules()` in `gpos.py` and
the `area_char{1..4}` entries in `layouts.json`. Any glyph tagged
`area_char` in `components.csv` is eligible, so:

1. Get the glyph's SVG into `builder/inputs/svg/<glyph_name>.svg`
   (via `--figma_pull` if it's a new Figma GLYPH-page component, or drop it
   in by hand if you're not using Figma for this one).
2. Add a row to `builder/inputs/components.csv` with that `glyph_name`, put
   any non-empty value in the `area_char` column, and fill in whichever
   spelling column(s) should trigger it (`latin`/`common` and/or
   `simplified`/`traditional`) — pick a key that isn't already claimed
   elsewhere in the CSV. Existing char-only examples to copy the shape of:
   `md_shang` (上, `area_char` only) or `md_xi` (息).
   - *Truly optional, even with a `simplified`/`traditional` spelling:*
     `builder/inputs/glyphRename.csv` is now an overrides file, not a
     requirement — a Chinese character with no row there still gets kept
     during subsetting and still resolves to a valid glyph name
     automatically (fontTools' own default `uniXXXX` codepoint name; see the
     `glyphRename.csv` section below). Add a `char,ch_glyphname` row only if
     you want that character to get a readable `ch_*` name in the generated
     `.fea` instead of `uniXXXX` — purely a legibility choice, not something
     the build needs. Either way the generated substitution line carries a
     trailing `# name=char` comment, so the `.fea` stays readable regardless.
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

**Known limitation: `:` immediately after Han text can silently drop out of
vertical mode.** The trigger is `sub colon by blank_colon;` (`features.py`),
and `vert_rules()`/`@area_to_md_for_vert` only fire when that `blank_colon`
glyph sits in the *same shaping run* as the glyphs after it. `:` (U+003A) is
Unicode "Common" script, so when it directly follows Chinese text (e.g.
`名九淌上 :shang34`), browsers' per-script text-itemization (splitting a text
node into separate shaping runs for `hani` vs `latn`/`Common`, independent of
which font is used — this happens even though everything renders through
one `@font-face`) can fold that `:` into the *preceding* Han run instead of
the following Latin one. The stranded word then shapes with plain
(non-vertical) positioning instead of the intended centered variant — no
error, just the wrong layout, and it only shows up when a colon-triggered
word directly abuts prior Han text with nothing else between them. Confirmed
with `hb-shape`: shaping `:名九淌上 :shang34` as one buffer positions the
second word correctly (`md_shang@-675,510` etc.), but shaping `shang34` in
isolation (simulating the stranded-colon run split) gives completely
different offsets (`md_shang@0,0`, `md_3@500,318`, ...). This is a
consequence of the colon being a script-neutral character, not a bug in
`gpos.py`/`features.py` — no `.fea` change fixes it, since the split happens
on raw input codepoints before GSUB ever runs. Workaround: don't chain a
`:`-triggered word directly after Han-script notation in the same run.

### Case 2: add a new SVG for `area_jc` (a third 急/绰-style marker)

`area_jc` (CSV column `area_mod_jc`) currently has two members — `mod_chuo`
(`/`, 绰) and `mod_ji` (`>`, 急). It's a shared class referenced by every
layout family's rules (the `jc` parameter throughout `word_layout_rules()`,
`no_left_layout_rules()`, and `cuo_rules()` in `gpos.py`), each with its own
`area_jc` x/y in `layouts.json`. Adding a third member doesn't require
touching any of that:

1. Get the new SVG into `builder/inputs/svg/<glyph_name>.svg`
   (same as Case 1 — `--figma_pull` or manual drop).
2. Add a row to `components.csv`: `glyph_name` matching the SVG filename,
   any non-empty value in the `area_mod_jc` column, and a spelling key that
   doesn't collide with `/`, `>`, or anything else already in the CSV.
   - *Truly optional, even with a `simplified`/`traditional` spelling:* same
     `glyphRename.csv` note as Case 1 step 2 — add a row only if you want a
     readable `ch_*` name for this character instead of the auto-derived
     `uniXXXX`; the build works either way.
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
`builder/inputs/` by file version (`meta.json`), so a repeat
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
  if it recurs: split fetching into a cheap `--fetch-layouts` (`/v1/files`
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
inert data (present in `layouts.json`, but no glyph is ever routed to
them).

**Decision (file owner, current):** leave as-is for now — the 3 extra
layouts/areas can stay unused in the fetched data without being wired into
`gpos.py`. Revisit if/when those layouts are actually needed.

## Dev Server

A **required**, **stdlib-only** local HTTP server for the browser tools
below — no extra dependency beyond the Python standard library already
installed in "Setup" above. `tools/jzpbuilder.html` only works served
through this; opening it as a plain `file://` page doesn't work at all
(Chromium blocks `fetch`/`XMLHttpRequest` against `file://` sibling files,
so auto-load, Import/Save, and Build Font all have nothing to talk to).

**Spin it up:**

```bash
cd builder
python3 -m jzpbuild.devserver          # serves at http://127.0.0.1:5713/
python3 -m jzpbuild.devserver --port 9000   # or pick a different port
```

Then open **`http://127.0.0.1:5713/tools/jzpbuilder.html`** in your browser
(through the server's URL, not by double-clicking the file — that's the
difference that makes fetch/Build Font/Save Configs work). Leave the
command running in that terminal for as long as you want the tool's server
features available; `Ctrl-C` stops it. `tools/font_tester.html` doesn't need
the server at all — it only ever reads a built `.ttf` file directly.

`jzpbuild/devserver.py` serves `builder/` as static files, plus four small
JSON routes:
- `GET /api/svgs` — every `inputs/svg/*.svg` as `{glyph_name: svg_text}`.
- `GET /api/config` — `config.py`'s `RIGHT_SELECTORS` map plus the default
  `--input-*` paths, straight from the source of truth — powers the
  `area_right` restriction and the Build Font modal's prefilled paths below.
- `POST /api/build` — runs `python3 -m jzpbuild` in `builder/`, with
  optional `--input-*` overrides from the request body, returns
  `{ok, returncode, stdout, stderr}`.
- `POST /api/save` — writes request-body values straight to their
  `config.py` default path (`layouts` → `inputs/layouts.json`,
  `components` → `inputs/components.csv`, `svgs` → one file per entry,
  `inputs/svg/<glyph_name>.svg`, overwriting existing files of the same
  name) — the "Save Configs" button, so a build afterward (which only ever
  reads what's on disk) picks up in-browser edits without a manual
  download-then-move-the-file step.

## Helpful Tools

Two self-contained HTML tools live in `tools/` — open `tools/index.html` for
a landing page linking both. `tools/font_tester.html` works with **no
server at all** (open directly with a plain `file://` double-click) since it
only ever reads a built `.ttf` file directly; `jzpbuilder.html` requires the
Dev Server above.

### JianZiPu Font Builder (no-Figma workflow)

`tools/jzpbuilder.html` — auto-loads the current
`builder/inputs/layouts.json`, every SVG in `builder/inputs/svg/`, and
`builder/inputs/components.csv` on open, so it's ready to explore immediately
with no manual load step, and has a **Build Font** button (top toolbar) that
opens a modal listing every input file `python3 -m jzpbuild` would read
(prefilled with `config.py`'s defaults via `/api/config`, each editable as
plain text — matching the `--input-*` CLI flags) plus a **Build** action
that POSTs those paths to `/api/build`, shows a loading state, then
success/failure and a link to open Font Tester next. The modal also carries
a red reminder: Build Font only ever reads what's on disk, so any in-browser
edit not yet pushed out via "Save Configs" (below) won't be picked up. Both
auto-load and the Build Font modal require the dev server above.

A **File-menu-style bar** sits in the top toolbar, alongside Help/Build
Font — three dropdowns (click to open, click anywhere else to close):
- **Import ▾** — `layouts.json`, `components.csv`, `svgs` — each loads from
  disk and replaces what's currently loaded in the browser.
- **Save ▾** — `layouts.json`, `components.csv`, and `svgs` each POST their
  current in-memory state to `/api/save`, overwriting the real files under
  `builder/inputs/` (`svgs` writes one file per loaded SVG, to
  `inputs/svg/<glyph_name>.svg` — needs the dev server; without it you just
  get a "no dev server running" alert); **Save All** does all three in one
  request, one combined confirmation.
- **Export ▾** — downloads `layouts.json` (recomputing its `yd` field from
  `y`/`h` on the way out — `yd` is the baseline-flipped offset the font's
  GPOS rules actually use, so it's kept in sync automatically rather than
  ever being hand-edited), `components.csv`, and `svgs.zip` (every loaded
  SVG, zipped client-side by a small dependency-free stored/no-compression
  ZIP writer — no external library, keeps the tool self-contained) to your
  Downloads folder, independent of any server.
- **Edit ▾** — Undo/Redo (`Ctrl/Cmd+Z`, `Ctrl/Cmd+Shift+Z` or `Ctrl+Y`);
  most edits (drags, area/layout add/delete, glyph assignment, CSV field
  edits) are one undo step each, snapshot-based (see `historyStack`/
  `redoStack` in the script).

The toolbar spans the full page width (a sibling of the side/canvas/tools
row, not nested inside it) and also holds a **&minus; / percentage / + /
reset** zoom control group just left of Help — mouse wheel over the canvas
zooms too, and dragging on empty canvas pans. Area name labels on the
canvas boost their own font size as you zoom out (countering the shrink
from the canvas-wide `transform: scale()`), so they stay legible instead of
vanishing at low zoom.

The **left panel** has the **Layouts** list (plus Add/Duplicate/Delete),
plus a **Layouts (Double Sided)** section below it — a dedicated left/right
picker for the six cuo layouts (`layout_cuo_left`/`right` and their `2`/`3`
variants) that lets you mix and match any left variant with any right
variant (e.g. preview `layout_cuo_left3` paired with `layout_cuo_right`),
overriding the fixed `left`↔`right`, `left2`↔`right2`, `left3`↔`right3`
pairing described below. Picking one from each column previews that custom
pairing; picking only one side falls back to the normal fixed pair; picking
any other (non-cuo) layout from the main Layouts list clears both picks —
the two pickers and the main list all drive the same underlying
selection, they're just different ways to set it.
Everything else that used to live in the left panel moved to a **Tools
panel** on the right, which (like the left panel and the bottom panel) is
resizable by dragging its edge. Tools holds **Preview** (the "exact font
placement" checkbox, **Test random components**, **Clear Components**) and
**Areas** (the click-a-canvas-area editor: name/x/y/w/h/svg fields). **Test
random components** fills every area of the current layout with a random
glyph from its `components.csv` candidates (re-rolls on every click, useful
for spot-checking fit across many shapes), with two rules layered on top of
plain per-area randomness:
- `area_right` only ever gets a glyph from the *current layout's*
  `RIGHT_SELECTORS` family (e.g. `layout_gou3` only ever picks
  `lg_gou`/`lg_da`, never an `lg_pi` or `lg_li`) — that restriction comes
  from `/api/config`, so it's a no-op (unrestricted) without the dev server
  running.
- In `layout_vertjzpN` (N ≥ 2), each numbered row is either `area_char{row}`
  *or* `area_left_{row}` + `area_hui_{row}` together, never all three at
  once — matches the actual choice `gpos.py::vert_rules()` enumerates, so
  the preview can't show an illegal combination.
- `layout_cuo_left`/`layout_cuo_right` (and their `2`/`3` jc/no-left
  variants) are two halves of the same 撮 chord, so selecting either one
  renders **both** on canvas together — the paired layout appears as a
  dashed, read-only overlay offset 500 (font design units) to the right of
  the primary one — and clicking "Test random components" fills both sides
  at once so the whole chord previews correctly, not just half of it.

**Clear Components** empties every area's assigned glyph for the *current
layout only* (other layouts, including a cuo pair, and the loaded SVG
library are untouched), leaving bare area outlines.

The auto-load itself makes real `fetch()`/`/api/svgs` calls (works only when
served by `jzpbuild.devserver`); if the dev server isn't running, the page
falls back cleanly to the manual controls below — you'll see "auto-load
unavailable" in the status line instead of a broken page.

For users who author glyph SVGs and `layouts.json` with their own tools
(or want to try something different from what's checked in): load a
layouts JSON, CSV, and/or any subset of SVGs via the Import menu (file
picker) to replace the auto-loaded set, preview how glyphs sit in each area
(natural size, bottom-anchored at `y + h`, toggleable via the "exact font
placement" checkbox — off by default, since the alternative stretch-to-fill
rendering doesn't tell you anything real about whether an area is sized
right), then move/resize areas by drag or numeric input, add/duplicate/delete
layouts and areas, then get the changes back to `builder/inputs/` one of two
ways: use the Save menu (needs the dev server, writes directly, no manual
step) or download a corrected `layouts.json` (with `yd` recomputed)
and/or `components.csv` from the Export menu and drop them in yourself as
`builder/inputs/layouts.json` / `builder/inputs/components.csv`. "Test random components" prefers real
`components.csv` membership when it's loaded (falling back to a small
hardcoded candidate pool only for areas with no matching CSV rows), applying
the same `area_right`-family restriction described above. The left panel,
right Tools panel, and bottom panel are all resizable by dragging their edge
(`#sideResizer` / `#toolsResizer` / `#bottomResizer`).

**Area → components panel** (bottom of the page): click any area on the
canvas to see every glyph whose `components.csv` row includes that area
(matched via the area name → CSV column mapping — e.g. canvas area
`area_hui_2` / `area_left_rt` both map to the `area_hui`/`area_left`
columns respectively, and `area_jc`/`area_zhu` map to the historically-named
`area_mod_jc`/`area_mod_zhu` columns), shown as clickable preview chips with
a `×` to remove that glyph from the area. Clicking an unassigned chip
assigns it to the currently-selected area; clicking the already-assigned
chip again unassigns it (toggle). For `area_right`, chips outside the
current layout's `RIGHT_SELECTORS` family are shown but grayed out and
unclickable (not hidden — makes clear *why* e.g. `lg_pi` can't go in
`layout_gou3`'s `area_right`), same restriction "Test random components"
applies. Add another glyph via "Add New SVG", which opens a modal listing
every loaded SVG as a click-to-select chip (multi-select, already-assigned
ones shown pre-highlighted) — "Add selected" adds them all to the current
area (creating a minimal CSV row for any that don't have one yet),
"Cancel" discards the selection. The modal's own "Upload SVG" button reads
one or more `.svg` files straight into memory (`registerSvg()` — no
dev-server round trip needed for this step); if an uploaded file's name
collides with one already loaded, you're prompted with a suggested rename
(`foo` → `foo_2`, `foo_2` → `foo_3`, ...) before it's added — re-prompting
until you pick a free name or cancel (which skips just that file). Either
way, a newly uploaded SVG only exists in memory until you use **Save ▾ >
svgs** (or Save All) to write it to `builder/inputs/svg/`. Clicking a
candidate chip both toggles its assignment to the
currently-selected area in the main canvas *and* opens an inspector panel on
the right showing every area that glyph belongs to across the whole CSV
(editable checkboxes — this is where you'd add/remove other area
memberships, not just the current one), its
`common`/`latin`/`latin_alt`/`simplified`/`traditional` spellings (editable
text fields; `vert_variant` is shown read-only), and a "Download SVG" button
to save that glyph's raw SVG back out. All of this edits the in-memory CSV
rows directly — use "Download components.csv" in the side panel to save
your changes out.

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
  reference. The builder's slimmed CSVs (`builder/inputs/components.csv`,
  `builder/inputs/glyphRename.csv`) are the live sources of truth: dead columns
  (ID/keys/filename/area_hui_deci/pinyin, identity ASCII rename rows) were
  dropped, and the per-glyph exceptions that used to be Python constants in
  `features.py` now live in the CSV (md_8/md_9 tagged `area_string`, md_jiu
  tagged `area_char`, and a `vert_variant` column pairing left-aligned
  glyphs with their centered vert-mode variants).
