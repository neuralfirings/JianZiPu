# Architecture review: `src-fonttools/` (2026-10-12)

Scope: the font build pipeline (`jzpbuild/`, `dynamic_positioning/`, `tools/`,
`tests/`, `inputs/`) on branch `feat/dynpos-ui` at `eaab07f`, read against
`docs/ROADMAP.md`. `src-fontforge/` is out of scope and should stay untouched.

Everything below was checked by running the code, not by reading docstrings.
Numbers quoted are from this machine (fontTools 4.59, uharfbuzz, Python 3.13):

| measurement | result |
|---|---|
| `python3 -m jzpbuild` (classic) | 12.0 s wall; 433 glyphs; `JianZiPu.ttf` 359,820 B |
| `python3 -m jzpbuild --dynamic_pos` | 12.4 s; 439,308 B (+80 KB, see §1.2) |
| `--fea-only` | 0.16 s. Classic `.fea` 1,169 lines / 104 KB; dynamic 3,719 lines / 297 KB |
| `.fea` determinism | byte-identical across runs and against the pre-tightening baseline |
| `tests/test_shaping.py` golden vs fresh classic | 73/78 (5 pre-existing diffs: `U9,6` and the four cuo chord inputs) |
| classic vs `--dynamic_pos` | 33/78 identical — expected, every family sits ~200 units higher (`center_y` 500 vs ~300, already in the roadmap) |
| classic vs `--dynamic_pos_only` | 27 corpus words contain a glyph at (0,0): the "no right hand" words, the cuo words, and li's second string (§2.5) |
| dynamic rules | 2,448 `pos` statements in 20 lookups; largest lookup 208 rules (`lg_li`) |
| compiled GPOS, dynamic font | 272 lookups (22 in `kern` + 250 nested single-pos lookups feaLib generates for the marked glyphs) |
| real per-lookup ceiling (§2.3) | feaLib rejects a lookup whose *unpromoted* subtables exceed 64 KB; measured cost ≈ 2 B × context tokens + 14 B per rule; e.g. 2,900 five-token rules compile, 3,000 do not |

Scratch scripts used for the measurements live in the session scratchpad
(`analyze_dyn.py`, `lookup_sizes.py`, `ceiling2.py`, `vert_scaling.py`,
`gsub_lint.py`, `parity.py`); the ones worth keeping are proposed as tests in §5.

---

## 1. State of the architecture

### 1.1 What is clean

- **`jzpbuild/` has one concern per module and is deterministic.** `base.py`
  (subset + rename), `glyphs.py` (SVG → quadratic outlines), `features.py`
  (GSUB), `gpos.py` (classic GPOS), `genfea.py` (assembly), `build.py` (CLI).
  The generated `.fea` is byte-stable, which is what makes every refactor
  cheaply verifiable. `data.py` + `validate.py` make `components.csv` a real
  single source of truth with namespace-collision checks that produce
  actionable messages. Keep all of this.
- **The geometric core of `dynamic_positioning/` is small and genuinely
  generic.** `anchors.AnchorEngine` (155 lines) and `chain.resolve` (246
  lines) are pure functions over plain dicts: no area names, no fontTools, no
  I/O. `identity.py` and `classes.py` derive the glyph-identity classes from
  the same function so rule branching and class emission cannot disagree.
  This is the asset the roadmap wants to run in the browser, and it is
  already fontTools-free: `from dynamic_positioning import build` succeeds
  with `fontTools`, `pathops`, `picosvg` and `requests` blocked from
  `sys.modules`; the only non-stdlib imports it pulls are `jzpbuild.config`
  and `jzpbuild.data`.
- **`feadiff.py`** is a real semantic `.fea` differ (class sets, statement
  order, prefix-shadow detection). It is the basis for the GSUB lint in §2.6.
- **The one-lookup-per-signifier split and the most-specific-first sort**
  (`build._collect_rules`, `build.py:251-309`) are the right shape: every
  rule carries its pivot class, so lookups never co-match a word, and I
  verified there are zero duplicate (backtrack, marked, lookahead) contexts
  across all 2,448 rules.

### 1.2 Load-bearing but fragile

- **Import-time state in `dynamic_positioning/`.** `geometry.py:58` reads
  `config.DYNAMIC_LAYOUTS_JSON` at import; `signifiers.py:48-52` builds
  `KEY_TO_GLYPH` at import from `data.load_components()` (a file read);
  `build.py:47` builds `_ENGINES` at import and binds them as default
  arguments (`build.py:251-253`); `chain.py:188-191,244-245` reads
  `geometry.CENTER_X/Y` at call time; `devserver.py:257-280` therefore has
  to mutate and restore `geometry.CENTER_X/Y` around every `/api/dynamic/
  resolve`, and `build.py:94-101` has to patch `config` *before* the first
  import of `geometry`. Each piece works; together they make the package
  impossible to instantiate twice (two layouts files, two centers, an
  editor's unsaved state) without monkey-patching. `geometry.py:80-81`
  attaching the *same* `AREA_SIZES` dict to every layout as `layout["areas"]`
  is the same pattern: an implementation detail that `devserver.py:220-221,
  243-244` then has to reproduce by hand for request payloads.
- **Classic GPOS is one 628-rule lookup at first-match-wins**
  (`gpos.py:277-356`). Rule order is an emergent property of the loop
  sequence, including things like `blank_rules[:8] + extra + blank_rules[8:]`
  (`gpos.py:348`). It is correct today and the shaping corpus proves it, but
  it cannot be extended safely; it should be frozen, not refactored (§2.6, §4).
- **The classic/dynamic overlap is held together by zeroing**
  (`gpos.py:264-354`, `skip_right_keys`/`zero_others`). It is the right
  mechanism while both live in one font, and the `Cfys5` double-counting
  story in `dynamic_positioning/README.md` shows how easy it is to miss a
  fallback. It should have a short life (§2.5).
- **feaLib's overflow handling is already active in the dynamic font.** The
  classic lookup compiles to 15,530 B in the classic font but 53,902 B in the
  dynamic font: once total GPOS passes 64 KB, fontTools promotes lookups to
  Extension (type 9), and promoted subtables stop sharing Coverage tables.
  That is where the +80 KB comes from. Harmless, but it means "the font
  compiled" is not evidence of headroom; see §2.3 for the actual limit.
- **Area classes overlap and the dynamic generator does not know it.**
  Digits 1–7 are in both `@area_hui` and `@area_string`. Classic handles this
  with explicit context (`gpos.py:176-177, 342-345`). The dynamic generator
  emits `pos <pivot> @area_hui' <...>;` and `pos <pivot> @area_string' <...>;`
  with equal specificity whenever both are adjacent to the pivot, so which one
  wins is generation order. Observable today: `TT3` under `--dynamic_pos_only`
  puts `md_3` at the hui position (500, 450) instead of the string position.
  This will bite cuo and the "blank" words before it bites `default_jzp`
  (where the pivot sits between hui and string).

### 1.3 Accidental

- **Two namespaces for one concept.** `selector.contains` lists ASCII *keys*
  (`"k"`, `"U"`, `"|"`); gap overrides list *glyph names* (`lg_gou`).
  `signifiers.py:35-52` exists only to map keys to glyphs and documents a real
  collision (`V`/`lun`/`banlun`) resolved by area precedence order. Lookup and
  class names are already derived from the glyph (`build.py:54-55`,
  `classes.py:86-92`), so the JSON could name glyphs directly and the
  precedence hack disappears.
- **`AREA_TO_CSV_COLUMN` exists three times**: `signifiers.py:81-93`,
  a top-level key in `layouts_data.json`, and a JS constant in
  `jzpbuilder-dynamic.html:2654`. The editor lets you edit the JSON copy
  ("Area sizes" panel, `:2535-2542`), `devserver.py:150` overwrites it with the
  Python copy on every GET, and the build (`signifiers.csv_column_for`) never
  reads the JSON copy at all. So the editable field is a no-op in the build:
  the exact editor/build drift the roadmap says Pyodide is meant to prevent.
- **Dead and duplicate data in `layouts_data.json`.** `chord_left` declares
  `{y, jc ← chord, top, -300}` twice (indices 11 and 17) and `{y, string ← jc}`
  twice with *different* gaps (index 15: 0, index 19: 10). `chain._choose_
  relationships` takes the first, so the `10` is dead. Nothing validates the
  file. Serialization is also inconsistent: 37 gap entries are written
  `signifiers`-then-`value`, 4 are `value`-first (hand-edit vs `seed_from_
  classic.py`), and `devserver.py:206` writes no trailing newline while
  `seed_from_classic.py:123` adds one. Six commits so far; the last one is
  +299 lines for seeding four families. This file is about to become the
  thing every proposal PR diffs.
- **A wrong claim about rule order in `features.py:9-11`.** The docstring says
  order within the hui ligature lookups is load-bearing. It is not: feaLib
  sorts ligatures longest-first per first glyph
  (`fontTools/ttLib/tables/otTables.py:1528`), and I verified that reversing
  every plain ligature lookup (`s2j_liga`, `s2j_lat_ch_period_liga`,
  `c2j_char_deci_period_liga`, `l2j_liga`, `c2j_char_liga`, `c2j_trad_liga`)
  shapes the whole corpus identically (78/78). What *is* load-bearing in GSUB
  is the lookup sequence in `gen_liga_feature` and the relative order of
  contextual rules whose contexts overlap. `gen_l2j_liga`'s longest-first sort
  is therefore cosmetic (fine to keep; say so).
- **`string` is declared always-present in `default_jzp` although real words
  often lack it**, and `chain.resolve` tolerates `KeyError` from always-present
  elements as "doesn't apply" (`chain.py:168-175`). That control flow exists
  to make li's double-string work without a flag, and `build.py:167-177`
  then has to explain why always-present elements must be excluded from
  lookahead. Three pieces of code compensate for one missing concept: a slot
  with alternatives (§2.3).
- **Prose has outgrown code.** `build.py` is 62% comment/docstring lines,
  `signifiers.py` 71%, `classes.py` 64%, `chain.py` 52%; `dynamic_positioning/
  README.md` is 936 lines and includes bug narratives (`Cfys5`), history ("an
  earlier version used mark attachment"), and editor UI documentation. A new
  reader cannot tell the invariant from the anecdote.
- **Demo cruft shipped as package code**: `layout_test.py` and
  `layout_data_sdf.json` (the roadmap's own note says it is only a demo
  input). They are the seed of a unit-test fixture, not package modules.
- **`tests/JianZiPu.ttf`** is a 360 KB binary golden (a jzpbuild-era build,
  "Version 3.01") that is already stale on 5 inputs. A binary golden can
  neither be diffed in a PR nor regenerated with confidence.

---

## 2. Big-ticket items

Ordered by when they should land, not by size. Each lists the verification
gate; "byte-identical" means `python3 -m jzpbuild --fea-only --fea-out X`
for both the classic and `--dynamic_pos` variants compared with `cmp`.

### 2.1 Replace the binary golden with a text shaping snapshot, and add a real test pyramid

**Problem.** The only guard is `tests/test_shaping.py` comparing against
`tests/JianZiPu.ttf`, which is stale and opaque. Every roadmap step from here
(cuo, vert, the default flip, the center_y decision) *changes positions on
purpose*, so a pass/fail golden is the wrong instrument: you need to see what
moved, by how much, and accept it in the same PR.

**Design.**

- `tests/snapshot_shaping.json`: `{word: [[glyph, x_adv, y_adv, x_off,
  y_off], ...]}` for the corpus, produced from a fresh build. Text, sorted
  keys, one word per line, ~80 lines. Regenerated with `pytest --update-
  snapshot` (or `python3 tests/test_shaping.py --update`). The PR diff of this
  file *is* the parity report the roadmap asks for in Phase 0.6.
- Keep the corpus list in a module, extend it with the per-family template
  words the earlier parity script used (`s7{k}5`, `fy{k}5`, `s7>\\{k}5`, …
  for every signifier key) so every signifier is covered, not just the ones
  the tutorial happens to use.
- `tests/test_dynamic_core.py`: pure-Python unit tests with inline layout
  dicts (no files): `anchors.resolve_gap` first-match semantics incl.
  catch-all and conjunction; `AnchorEngine.anchor` for all four edge
  pairings; `chain.plan` candidate preference (ranked > always > root);
  `chain.resolve` centering (vertical, horizontal, `center=False`), the
  "always-present element may fail" path, the cycle error; `identity.
  area_glyph_buckets` with and without catch-all; `build._identity_choices`.
  `layout_test.py`'s two layouts become fixtures here.
- `tests/test_fea_order.py`: the GSUB lint from §2.6.
- `tests/test_build_smoke.py`: build both variants into a temp dir, assert
  snapshot equality, assert every `kern` lookup compiled below a budget.
- `pyproject.toml` already declares `pytest`/`uharfbuzz` under `test`; add a
  `[tool.pytest.ini_options] testpaths = ["tests"]` and a
  `.github/workflows/font.yml` that runs it on push. The build is 12 s; the
  whole suite will be under a minute.

**Replaces** `tests/JianZiPu.ttf` (delete; `config.CURRENT_FONT` goes with it).

**Risk / verification.** None to the font. Gate: the new snapshot test passes
on `main` with the current build; the 5 known diffs are accepted explicitly by
regenerating (and noted in the commit message).

**Size.** 1 day. **Phase.** Before anything else; it is the gate for every
later item and for Phase 0.4–0.6.

### 2.2 Make `dynamic_positioning` a self-contained data-in/data-out package (the Pyodide boundary)

**Problem.** See §1.2 (import-time state). The roadmap wants the *same* code
resolving positions in the browser and in Actions. Today the package can only
be driven by files at paths named in `jzpbuild.config`, read at import, with
one global center. In Pyodide that means writing files into the virtual FS
before `import`, and the editor's "unsaved state" would still need the
`_editor_rules` and `CENTER_X` workarounds.

**Design.** Two frozen value objects and a tiny public module; no module
globals anywhere in the package.

```python
# dynamic_positioning/catalog.py  — what the engine needs to know about glyphs
@dataclass(frozen=True)
class Catalog:
    area_glyphs: dict[str, tuple[str, ...]]   # csv column -> glyph names, csv order
    families: dict[str, tuple[str, ...]]      # config.RIGHT_SELECTORS
    control_glyphs: dict[str, str]            # {"|": "blank_bar", ":": "blank_colon"}
    @classmethod
    def from_rows(cls, rows, families, control_glyphs) -> "Catalog": ...
    @classmethod
    def from_components_csv(cls, text, families, control_glyphs) -> "Catalog": ...  # stdlib csv; usable in Pyodide

# dynamic_positioning/layout_data.py — parsed, validated layouts_data.json
@dataclass(frozen=True)
class LayoutData:
    center: tuple[float, float]
    area_sizes: dict[str, tuple[float, float]]
    layouts: tuple[dict, ...]                 # TypedDict Layout (see §3)
    @classmethod
    def from_json(cls, text_or_obj) -> "LayoutData": ...   # runs validate()
    def to_json(self) -> str: ...                            # canonical serializer (§2.4)

# dynamic_positioning/api.py — the only thing callers import
def resolve(data, layout_name, present, glyphs, *, center=True) -> Resolved   # positions + chosen bases
def validate(data, catalog) -> list[Problem]
def rule_stats(data, catalog, families=None) -> dict[str, LookupStats]       # rules, est_bytes per lookup
def generate_fea(data, catalog, families=None) -> str
```

- `AnchorEngine(layout, area_sizes, center)` takes its inputs; `chain.resolve`
  takes `center` from the engine; `geometry.py` shrinks to the loader (or is
  folded into `layout_data.py`); `signifiers.KEY_TO_GLYPH` and
  `identity.area_glyphs` become methods/lookups on `Catalog`; `classes.py`
  and `build.py` take `(data, catalog)` instead of reading `geometry.LAYOUTS`.
- `jzpbuild/genfea.py` builds the two objects:
  `Catalog.from_rows(load_components(), config.RIGHT_SELECTORS, …)` and
  `LayoutData.from_json(config.DYNAMIC_LAYOUTS_JSON.read_text())`, then calls
  `api.generate_fea`. `jzpbuild` keeps importing `dynamic_positioning`; the
  reverse import goes away.
- `devserver.py` routes become five-line wrappers over `api.*` with no state
  mutation. The same five calls are what the SvelteKit app makes through
  Pyodide.
- Ship it as a zero-dependency wheel (`pip wheel src-fonttools/
  dynamic_positioning`) from Actions so the app installs it with `micropip`
  from a URL; add a CI step that imports it under Pyodide (node) and resolves
  one word, so "pure Python" stays true by test rather than by convention.

**The `config.py` globals question (candidate 2).** Accept for
`dynamic_positioning` (above). For `jzpbuild` itself: modify, narrowly.
`config.py` is fine as a constants module (metrics, names, PUA); the only
harmful part is `setattr(config, …)` from the CLI plus the `@cache`d loaders
that then need `cache_clear()` from the devserver. Replace with an `Inputs`
dataclass (`components_csv`, `glyph_rename_csv`, `edge_cases_fea`,
`layouts_json`, `svg_dir`, `dynamic_layouts_json`) built by `build.main` from
the flags and passed to `build()`/`generate()`; loaders take a path argument
and lose the cache (the build reads each file at most a handful of times;
`load_components` is 93 rows). This is ~40 lines across `build.py`,
`genfea.py`, `features.py:472-476`, `base.py:17-22`, `data.py`, `devserver.py`.
Do it inside this same PR if it stays under that, otherwise skip: jzpbuild
never runs in the browser (skia-pathops is not available in Pyodide), so the
pattern only affects CLI ergonomics and tests.

**Replaces** `geometry.py`'s globals, `build._ENGINES`, `build._editor_rules`,
`devserver`'s center mutation and `layout["areas"]` filling,
`signifiers.KEY_TO_GLYPH`'s import-time scan.

**Risk / verification.** Byte-identical `.fea` (classic and dynamic). For the
devserver, record ~10 request/response pairs from the current server (resolve,
rule_count, data) into a JSON fixture and replay them against the new handlers.
Blast radius from grep: `geometry.` is referenced in 5 package modules and
`devserver.py`; `KEY_TO_GLYPH`/`selector` in `build.py` (8), `classes.py` (4),
`signifiers.py` (11), `devserver.py` (6), `seed_from_classic.py` (4).

**Size.** 1–2 days. **Phase.** Must land before Phase 1's layout editor;
should land before 0.4 so cuo/vert work is done against the stable API.

### 2.3 Fix the combination model: slots with alternatives, correct ceiling, overlap-aware lookahead

**Problem.** `order` entries carry a single bit (`optional`). The combination
space is therefore 2^(optional elements) per signifier, and a real word's
*structure* has to be faked: `string` is "always present" but absent in real
words; li's two strings "ride along in the same slot" (`build.py:212-230`);
`chord_left` makes `jc` non-optional (which is the `TT3` bug in §1.2). The
roadmap's vert mode is where this stops working. I measured a vert topology
expressed in the current model (per row: `left_i`, `hui_i`, `char_i` each
optional):

| rows | optional elems | combos | rules | est. bytes (one lookup) |
|---|---|---|---|---|
| 1 | 3 | 8 | 21 | 352 |
| 2 | 6 | 64 | 257 | 5,312 |
| 3 | 9 | 512 | 2,817 | 67,072 (over) |
| 4 | 12 | 4,096 | 28,673 | 770,048 |

Classic covers 4 rows with 16 rules (`gpos.py:137-155`) because a row is
*exactly one of* {`char`, `left hui`}: the combination space is a product of
alternatives, not a power set of independent bits. The current model cannot
say that.

The size model is right but the thresholds are wrong. The hard limit is
feaLib's per-lookup check on *unpromoted* subtable bytes (64 KB), applied
before any Extension promotion: with 4 context tokens, 2,900 rules compile
(63.9 KB) and 3,000 fail; with 2 tokens 3,000 pass and 4,000 fail; with 6
tokens 2,000 pass and 2,200 fail. Marginal cost is 2 B/token + ~14 B/rule,
which is what `estimate_dynamic_pos_bytes` computes (`build.py:381-394`);
the only missing term is a fixed ~0.7–1 KB of Coverage tables per lookup.
`jzpbuilder-dynamic.html:675-676` warns at 35% and blocks at 55% of the
ceiling because the estimate was believed to be badly low; it is not.
Today's worst lookup (`lg_li`, 208 rules) is 4.4 KB estimated, 7% of the
ceiling; its 144-rule siblings that compiled as plain type-8 lookups measure
3.5 KB against a 2.9 KB estimate, so the model is close.

**Design.**

- `order` becomes a list of *slots*; each slot is `{"one_of": [[areas...],
  ...], "optional": bool}` with the pivot slot marked. Today's entries map
  1:1 (`{"area": "fy", "optional": true}` ≡ `{"one_of": [["fy"]], "optional":
  true}`), so the loader can accept both shapes during migration. Examples:
  `default_jzp`'s last slot `{"one_of": [["string"], ["string_top",
  "string_bottom"]], "optional": true}`; a vert row `{"one_of": [["char"],
  ["left", "hui"]], "optional": false}` with numbered repeats; cuo's `jc`
  optional as it is in classic.
- `_signifier_rules` enumerates `itertools.product` over slots (each slot
  contributes its alternatives, plus `None` if optional). Combos = Π(options
  per slot). Vert with 4 rows = 16 combos; `default_jzp` = 2^5 × 3 = 96
  combos (vs 32 today but with `string` genuinely modelled); li needs no
  special case and `chain.resolve`'s "always-present may fail" path goes away.
- Emit **one multi-marked rule per combo** (`pos a' <…> b' <…> pivot' <…>
  c' <…>;`), which classic already does for vert and which feaLib/HarfBuzz
  handle (each marked glyph gets a nested single-pos lookup; the font already
  has 250 of those). Rules per signifier drop from 144 to 96; bytes per
  lookup stay roughly flat (a marked glyph costs 4 B more than a context
  token), but there is no longer a per-element rule whose lookahead must be
  hand-reasoned. Keep `_Rule` with a `marked: list[tuple[token, x, y]]`
  field; the specificity sort still applies (longest context first).
- **Overlap-aware disambiguation.** From `Catalog`, compute which area
  classes intersect (today: `hui`∩`string` = `md_1..md_7`, `hui`∩`char`,
  `right`∩`char` via vert variants). When two adjacent slots' classes
  intersect, the generator must emit the combo *with* the later element before
  the combo *without* it, and the shorter combo must not be able to match the
  longer sequence as a prefix. With multi-marked whole-word rules this reduces
  to: sort by token count, and for equal counts prefer the combo that
  consumes the ambiguous glyph as the later area only when a following
  element pins it. Write this as a unit test with `[chord, 3]`, `[chord, 7,
  5]`, `[s, 7]`, `[s, 7, 5]` before implementing; it is exactly the classic
  rules at `gpos.py:176-177` and `:342-345` restated.
- Replace the badge thresholds with 80% warn / 95% block on
  `est_bytes + 1024` per lookup (close to the wireframe's f5·7 numbers; the
  UX review's objection that the estimate undercounts is answered by the
  measurement above). Optionally, in
  the browser, compute the exact number by compiling the single lookup with
  fontTools (pure Python, available in Pyodide) — `rule_stats(..., exact=
  True)`.

**Replaces** `build._signifier_rules`'s before/pivot/after branches
(`build.py:155-230`), the li special case, `chain.resolve`'s `failed` set,
`optional_lookahead`.

**Risk / verification.** Not byte-identical by construction (rule shapes
change), so the gate is the shaping snapshot from §2.1 over the extended
corpus: identical positions for every word, before and after. Do the slot
migration first (byte-identical: same combos, same rules), then multi-marked
emission (snapshot-identical), then overlap handling (snapshot changes only
for the words that were wrong, e.g. `TT3`).

**Size.** 2–3 days including tests. **Phase.** With Phase 0.4 (cuo needs
optional `jc` and the overlap rule) and before 0.5 (vert is infeasible without
slots).

### 2.4 `layouts_data.json` v2: glyph-named selectors, canonical serialization, validation

**Problem.** §1.3: two namespaces, three copies of the column map, duplicate
relationships, inconsistent serialization, no validation. For the editor this
file is the whole product; for PR review it is the whole diff.

**Design.**

- **Schema** (documented in `docs/LAYOUTS-DATA.md`, enforced by
  `api.validate`, no external jsonschema dependency):
  - top level: `{"version": 2, "center": [x, y], "area_sizes": {...},
    "layouts": [...]}`; drop `area_to_csv_column` (it is catalog data: either
    implement it end to end by moving it to `components.csv` as the area's
    canonical column, or delete the editor field; today it is a no-op, delete).
  - layout: `{"name", "pivot_glyphs": ["lg_gou", "lg_da", ...], "slots":
    [...], "vertical_center_order", "horizontal_center", "relationships"}`.
    `pivot_glyphs` replaces `selector.contains`; the editor shows the key
    next to the glyph using `Catalog`. Lookup/class names are already
    derived from the glyph, so the generated `.fea` is unchanged.
  - relationship: as today, plus the rule that `(axis, elem, base, base_edge,
    elem_edge)` is unique within a layout.
  - gap list: when any entry has a signifier key, the last entry must be the
    catch-all (the roadmap already decided "first match, with a final
    otherwise"); entries are serialized with keys in the fixed order
    `base_signifiers, elem_signifiers, value`.
- **Validation** (`api.validate` → `list[Problem(layout, path, message)]`,
  run by the loader, the devserver, Actions, and the editor on every edit):
  exactly one pivot slot; every area in slots/relationships has a size; every
  relationship's areas exist in slots; no duplicate relationships; catch-all
  present where needed; every pivot glyph belongs to the pivot area's column
  in the catalog; every signifier glyph in a gap list belongs to the
  relationship's base/elem area; **every slot combination resolves** for every
  pivot glyph (this is cheap: it is what rule generation does, and it turns
  today's build-time `KeyError` into an editor-time message with the combo
  named).
- **Canonical serializer** `LayoutData.to_json()`: `indent=2`,
  `ensure_ascii=False`, fixed key order per object type, trailing newline,
  relationships kept in declaration order (it is semantic). Every writer —
  devserver, `seed_from_classic.py`, the future proposal bot — goes through
  it. A test asserts `to_json(from_json(file)) == file` on the committed
  file so reformat-only diffs can never appear in a proposal.
- **Migration**: one script `tools/migrate_layouts_v2.py` (keys → glyphs via
  `KEY_TO_GLYPH`, `order` → `slots`, dedupe relationships, drop the no-op
  key), run once; the loader refuses `version < 2` with a pointer to the
  script. Fix `chord_left`'s duplicates in the same change and decide which
  `string ← jc` gap (0 or 10) was intended.

**Replaces** `signifiers.py` almost entirely (becomes `Catalog.key_to_glyph`
for the editor's benefit only), the three column maps, hand-rolled
`json.dumps` calls in `devserver.py:206` and `seed_from_classic.py:123`.

**Risk / verification.** Byte-identical `.fea` after migration (names are
glyph-derived already). Round-trip test on the committed file.

**Size.** 1 day (+ 0.5 for the editor to read v2, if the HTML tool is kept
alive until the app replaces it). **Phase.** Before Phase 1 (the editor's
contract) and ideally before 0.4 (so cuo is authored in the final shape).

### 2.5 Classic/dynamic coexistence: the end state, the minimal intermediate, and the hole in the roadmap

**Problem.** `gen_gpos(layouts, skip_right_keys, zero_others)` emits classic
rules zeroed when dynamic owns a family. That is correct and necessary
*while both live in one font*, but the roadmap's Phase 0 list (cuo, vert,
flip) is missing a family: **words with no right-hand glyph at all**
(`layout_blank`, `layout_blank2`, `layout_blank3`, `gpos.py:337-354`:
`s7`, `s7,5`, `7.5`, `13+`, `fys7`, `名七五`, `s7_5`, …). Under
`--dynamic_pos_only` roughly two thirds of the 27 broken corpus words are
these (`s7,5`, `s76`, `10.2`, `13+`, `7.5`, `0.5`, `1,3`, `13`, `名七五`,
`名十一`, `綽`, `註`, `s7_5`, …), the rest are cuo and li's second string;
`fy`-only is the only blank shape dynamic covers (`build.FY_LOOKUP`). They also expose the
hui/string overlap head-on (`7` alone is a string, `7` before `5` is a hui),
and they have no mandatory element, so the current "exactly one pivot"
requirement cannot express them.

**End state (after the flip).** `genfea.generate()` calls
`api.generate_fea` only; `gpos.py` and `inputs/layouts.json` are not imported
by the default build; `--classic_pos` builds the old way for comparison;
`skip_right_keys`/`zero_others`/`--dynamic_pos_only` are deleted. The `kern`
cleanup rules at `gpos.py:357-366` (hide stray glyphs after `#`/`:`; give
space its advance back) are not layout and must move to `features.py` or a
small `gpos_common.py` *before* `gpos.py` is retired — easy to forget.

**Minimal intermediate state.** Keep the zeroing exactly as is (it is the
cheapest correct thing); do not spend effort making it elegant. Add
`--classic_pos` now as the inverse of `--dynamic_pos` so the flip is a
one-line default change. Add a *coverage* test: build `--dynamic_pos_only`,
shape the corpus, and assert the set of words with an unpositioned glyph is
exactly a committed allow-list (`tests/dynamic_uncovered.txt`); each roadmap
step shrinks the list, and the flip requires it to be empty.

**Blank words in the dynamic model.** Two options; both need §2.3's slots:
(a) a layout whose pivot is a *virtual* always-present element with no glyph
(the generator emits no token for it) — small change to `build.py`, keeps one
topology; (b) two layouts, `blank_hui` (pivot `hui`) and `blank_left` (pivot
`left`, no hui), the way `chord_left`/`chord_right` already split. (b) needs
no engine change and is consistent with "exactly one pivot"; (a) is cleaner
data. Decide with the owner (§6). Either way the `:大息` special case
(`gpos.py:281-285`) and the two bare-hui fallbacks need an explicit home.

**Size.** Intermediate: 0.5 day. Blank topology: 1–2 days after §2.3. The
flip itself: 0.5 day once the coverage list is empty. **Phase.** 0.4–0.6.

### 2.6 `features.py` / `gpos.py`: reject the rule-object refactor; make order a tested property instead

**Verdict on the candidate.** Reject for both files, for different reasons.

- `gpos.py` becomes legacy at Phase 0.6. Rewriting its loop structure into
  prioritized rule objects would be a byte-identical refactor of code whose
  only remaining job is to be a stable comparison baseline. Freeze it: add a
  module-level note that it is legacy, and stop touching it except for the
  cleanup-rule extraction in §2.5.
- `features.py`'s in-lookup order is *not* load-bearing for the ligature
  lookups (proved above). The load-bearing orders are (1) the lookup
  sequence in `gen_liga_feature` (`features.py:408-466`), which is already
  explicit and readable, and (2) contextual rules whose contexts overlap —
  today there are none (my lint found 257 prefix-overlap pairs, all in plain
  ligature lookups, zero involving a marked rule; reversing the two `_part1`
  contextual lookups shapes 78/78 identical). A rule-object layer would add a
  representation without removing a hazard.
- "Testable without a shaper": uharfbuzz shapes the full corpus in 0.1 s and
  is installed. A pure-Python GSUB simulator would be a second OpenType
  implementation to maintain. The right cheap guard is a **lint**, using
  `feadiff.parse`: for every lookup, for every pair of rules whose inputs
  overlap class-wise with one a prefix of the other, if either is contextual
  (marked), the longer must come first. Also assert the lookup sequence in
  `feature liga` matches a committed list. Both are ~40 lines and run in
  milliseconds.

**Also fix**: the docstring at `features.py:9-11` and the comment at
`:224-225` (longest-first is a readability choice, feaLib sorts anyway).

**Size.** 0.5 day. **Phase.** With §2.1.

### 2.7 The app-facing API and where each devserver route goes

**Problem.** `devserver.py` is a 350-line stdlib HTTP server that is both the
static file host for two HTML tools and a JSON API. The roadmap replaces the
tools with a SvelteKit app, runs geometry in Pyodide, and builds in Actions.
What survives is not the server but the five Python calls behind it.

**Design.** `dynamic_positioning.api` (§2.2) is the contract. Route by route:

| today (`devserver.py`) | future home | notes |
|---|---|---|
| `GET /api/dynamic/data` | fetch `layouts_data.json` from the proposal branch (raw GitHub URL or the serverless proxy) | plus `Catalog` built in-browser from `components.csv` |
| `POST /api/dynamic/resolve` | browser, `api.resolve` via Pyodide | no server round-trip per drag |
| `POST /api/dynamic/rule_count` | browser, `api.rule_stats` | same |
| `POST /api/dynamic/save`, `POST /api/save` | serverless function with the bot token: validate with `api.validate`, write through `LayoutData.to_json()`, commit to `proposal/<id>` | the only write path; must use the canonical serializer |
| `POST /api/build` | GitHub Actions on `proposal/**` push; status read back via the Actions API | synchronous build-on-request goes away |
| `GET /api/svgs`, `/inputs/components.csv` | static from the branch | |
| `GET /api/config` | nowhere: `right_selectors` and control glyphs are in `Catalog`; input paths are a CLI concern | |

Keep `devserver.py` alive, as a 60-line shim over `api.*` plus static files,
until the app covers the layout editor (Phase 1); then delete it with the
HTML tools. Do not grow it. `/api/build`'s `--input-*` plumbing
(`BUILD_INPUT_FLAGS` mirroring `INPUT_OVERRIDES`) can be deleted at the same
time as the `Inputs` dataclass lands.

**Pyodide vs a TypeScript port** (not asked, but it is the main cost of the
decided direction): Pyodide is a multi-megabyte download and a few seconds
of startup before the first resolve; after that calls are sub-millisecond.
The API shape above (pure functions over plain dicts, fixture-testable)
keeps a later TS port of `anchors`/`chain` (~400 lines) possible with a
generated fixture of `(layout, present, glyphs) → positions` as the parity
test. Recommend starting with Pyodide as decided and revisiting only if
startup is a measured problem.

**Size.** With §2.2; +0.5 day for the shim. **Phase.** 1.

---

## 3. Elegance / maintainability items

**Documentation (do after §2.2–2.4, when the shapes are final).**
- Split `dynamic_positioning/README.md` (936 lines) into: a 150-line
  reference (data model, the three orderings, scoping invariant, how to add
  a topology) and `docs/DECISIONS.md` for history and bug narratives ("why
  not mark attachment", `Cfys5`, the `repeatIndex`-style war stories). The
  editor sections (`Visual editor and JSON sidecar`, `Relationship panel`,
  `Dimension lines`) describe a tool the roadmap is retiring; move them next
  to the tool or drop them.
- `build.py` (62% prose): keep the module docstring to the invariant
  ("every rule carries its pivot class; most-specific-first; one lookup per
  signifier") and move the rest. Same for `signifiers.py` (71%) and
  `classes.py` (64%); `classes.repeated_area_token`'s 15-line docstring is a
  decision record, not an API doc.
- `src-fonttools/README.md` "Verification" still references `src/JianZiPu.ttf`
  paths; `tools/index.html` says "no server needed" while `jzpbuilder.html`
  requires the devserver.

**Naming.**
- `_Rule` (`build.py`) vs `Rule = list` (`gpos.py:21`); `signifier` / `key` /
  `glyph` used for the same thing; `FAMILIES` (`geometry.py:56`) vs
  `RIGHT_KEYS` (`config.py:128`) vs `RIGHT_SELECTORS`; `count_dynamic_pos_
  rules` returns a font-wide total while the ceiling is per lookup (rename to
  `total_rules`, return per-lookup stats from one function).
- Class names `@area_right__chord_left__xl_tt`: `area_right` is wrong for a
  chord pivot; derive the prefix from the pivot area.
- `--dynamic_pos` / `--dynamic_pos_only` / `--positions`: after the flip the
  flags are `--classic_pos` and `--layouts <path>`.

**Duplicated concepts.**
- `AREA_TO_CSV_COLUMN` ×3 (§1.3). `devserver.BUILD_INPUT_FLAGS` mirrors
  `build.INPUT_OVERRIDES` by hand (`devserver.py:154-163`). JSON-body parsing
  is copy-pasted four times in `do_POST`; one `_read_json()` helper.
  `layout["areas"] = area_sizes` is written in `geometry.py:81`,
  `devserver.py:221` and `:244`. `identity.area_glyph_buckets` is called once
  with a real layout and once with a fake `{"relationships": …}` dict
  (`build.py:114`); give it `relationships` as the parameter.

**Error handling.**
- `chain.resolve` uses `KeyError` for three different meanings (missing gap
  override, missing relationship, "element doesn't apply"). Introduce
  `class Unresolvable(Exception)` with `layout`, `elem`, `axis`, `present`
  fields; the devserver and the editor can then show "no gap for lg_tiao when
  hui is md_9 in default_jzp / y / right ← hui" instead of a Python repr.
  After §2.3 the "doesn't apply" meaning disappears entirely.
- `validate.ValidationError` messages are good; `api.validate` should return
  the same style for layout data.

**Types.**
- One `dynamic_positioning/types.py` with `TypedDict`s `Relationship`,
  `GapEntry`, `Slot`, `Layout`, and `Resolved`; `_Rule` → `@dataclass(frozen=
  True, slots=True)`. `GlyphRow.areas: dict` → `dict[str, str]`.
  `anchors.resolve_gap(gap, …)` → `gap: float | list[GapEntry]`.

**Small cleanups (safe any time).**
- `layout_test.py` + `layout_data_sdf.json` → `tests/fixtures/` (§2.1).
- `seed_from_classic.py` is a one-shot migration tool; move under
  `tools/oneoff/` with a header saying when it was run, or delete after the
  values are tuned in the editor.
- `build._collect_rules` hardcodes `"default_jzp"` for the bare-fy rule
  (`build.py:294`); make it "the layout whose pivot area is `right`" or an
  explicit `bare_fy_layout` field.
- `features.py:224-225` comment and `:9-11` docstring (§1.3).
- `package.json` targets point at the renamed `src/`; either fix or remove the
  Parcel scripts (the roadmap replaces them with the SvelteKit app).

---

## 4. What NOT to change

- **The zeroed-not-omitted classic rules** (`gpos.py:304-354`) and the
  `zero_others` coverage of the blank fallbacks. Omitting instead of zeroing
  re-enables the double-counting bug. Keep until the flip, then delete whole.
- **Classic rule order** in `gpos.py`, including the oddities (`li2` string
  limit, `blank_rules[:8] + extra`): they reproduce the shipped font. Freeze.
- **`features.py`'s Safari two-step ligatures** (`gen_c2j_char_deci_liga_
  parts`, `gen_char_deci_liga_parts`), `hui_and_commas` spelled per glyph,
  `edge_cases.fea` included verbatim, the `feature liga` lookup sequence.
  All are browser-compat facts, not style.
- **`glyphs.py`'s coordinate mapping** (`font_y = (h − 20) − svg_y`, `lsb =
  xMin`) and **`base.py`'s non-rescaled 1024-unit TW-Kai outlines**; the
  `CONTROL_GLYPHS` codepoints and sorted-filename PUA assignment
  (`config.py:102-112`, `glyphs.py:78-87`). Existing documents depend on them.
- **The three separate orderings** in a layout (`order`/slots, `relationships`,
  `vertical_center_order`). The temptation is to derive one from another;
  `geometry.py:8-17` is right that they are three different facts.
- **One lookup per signifier and the most-specific-first sort.** The 64 KB
  ceiling is per lookup; this is what keeps every family at <10% of it.
- **`data.py`'s validation and `feadiff.py`.** Both are small and correct.
- **`src-fontforge/`** and `figma.py` (one-way importer, per the roadmap).
- **The decision to run real Python in the editor.** Keep it; just make the
  package instantiable (§2.2) so it is honest.

---

## 5. Sequenced plan

Each step is one PR with a gate. "Snapshot" = `tests/snapshot_shaping.json`.

| # | step | gate | phase |
|---|---|---|---|
| 1 | Test pyramid: shaping snapshot, dynamic-core unit tests, GSUB order lint, pytest config, Actions workflow | suite green on `main`; 5 known diffs accepted in the regenerated snapshot | before 0.4 |
| 2 | `layouts_data.json` hygiene: validator, canonical serializer, round-trip test, fix `chord_left` duplicates, delete the no-op `area_to_csv_column`, `--classic_pos` flag, coverage allow-list test | byte-identical `.fea` (classic + dynamic); round-trip equality; allow-list committed | before 0.4 |
| 3 | Package boundary: `Catalog`, `LayoutData`, `api.py`; no `jzpbuild` imports in `dynamic_positioning`; devserver as a shim; `Inputs` dataclass if it fits | byte-identical `.fea`; devserver record/replay fixture; Pyodide import smoke in CI | before 0.4 |
| 4 | Schema v2: glyph-named pivots, slots (1:1 migration only), migration script | byte-identical `.fea`; validator green | 0.4 |
| 5 | Emission v2: product over slot alternatives, `string` optional, li via alternative slot, multi-marked rules; remove `chain` "may fail" path | snapshot identical over the extended corpus | 0.4 |
| 6 | Overlap-aware ordering (hui/string, hui/char); badge thresholds 80/95 with `+1 KB` | snapshot changes only on listed words (`TT3`, …); unit test for the four ambiguous sequences | 0.4 |
| 7 | cuo: `fy`/`left`/`hui` on `chord_left`, optional `jc`, remaining chord keys; zero classic cuo under `--dynamic_pos` | allow-list shrinks by the cuo words; snapshot diff reviewed | 0.4 |
| 8 | Blank-word topology (decision from §6) + `:大息` home | allow-list shrinks to vert only | 0.4b |
| 9 | vert topology with `one_of` rows; extract `kern` cleanup rules out of `gpos.py` | allow-list empty; `lg_*` lookups unchanged | 0.5 |
| 10 | Flip the default; delete zeroing/`--dynamic_pos_only`; freeze `gpos.py` as legacy; regenerate snapshot (center_y decision applied here) | snapshot diff is the parity report; CI green | 0.6 |
| 11 | README split + DECISIONS.md; naming/type cleanups from §3 | byte-identical `.fea` | 0.6 / 1 |
| 12 | Wheel build in Actions; SvelteKit editor consumes `api.*` via Pyodide | editor resolve == `api.resolve` for a fixture of 50 states | 1 |

### Step 1 in detail (start tomorrow)

1. `tests/corpus.py`: move `CORPUS` out of `test_shaping.py`; add
   `TEMPLATE_WORDS = [t.format(k=k) for k in KEYS for t in (…)]` using every
   `selector.contains` key (the earlier parity script's list is a good start:
   `s7{k}5`, `fys7{k}5`, `s7>{k}5`, `7{k}5`, `{k}5`, `fy{k}5`, `fy>{k}5`,
   `s7>\\{k}5`, `d10.8{k}6`), plus blank words (`s7`, `fys7`, `7`, `s7,5`,
   `13+`) and the cuo/vert words already present.
2. `tests/test_shaping.py`: `shape()` unchanged; `test_snapshot(built_font)`
   compares against `snapshot_shaping.json`; `--update-snapshot` option via a
   `conftest.py` fixture that builds once per session into `tmp_path_factory`
   (`python3 -m jzpbuild -o … --fea-out ""`). Delete the golden-font path and
   `config.CURRENT_FONT`; `git rm tests/JianZiPu.ttf`.
3. `tests/test_dynamic_core.py`: port `layout_test.py`'s two layouts as
   fixtures; cover the cases listed in §2.1. Target: ~25 tests, <0.1 s.
4. `tests/test_fea_order.py`: generate the classic `.fea` in-process
   (`genfea.generate()`), parse with `feadiff.parse`, assert (a) no
   contextual rule is shadowed by an earlier overlapping prefix, (b) the
   `feature liga` lookup sequence equals the committed list.
5. `tests/test_build_smoke.py`: for each of classic / `--dynamic_pos`, build,
   open with fontTools, assert every `kern` lookup's compiled size < 60 KB
   (use `OTTableWriter` as in the scratch script) and the glyph count is 433.
6. `pyproject.toml`: `[tool.pytest.ini_options] testpaths=["tests"]`;
   `.github/workflows/font.yml`: checkout, `pip install -e ".[test]"`, fetch
   the base font from a secret-protected artifact or skip build tests when
   absent (the base font is gitignored — decide where CI gets it, §6), run
   `pytest`, upload the two `.ttf`s as artifacts.

### Step 2 in detail

1. `dynamic_positioning/layout_data.py`: `load(text) -> dict` that runs
   `validate_structure(data) -> list[str]` (pivot count, sizes present,
   relationship areas exist, duplicate `(axis, elem, base, base_edge,
   elem_edge)`, catch-all-last) and `dumps(data) -> str` with the fixed key
   orders (`center_x, center_y, area_sizes, layouts`; layout: `name, selector,
   order, vertical_center_order, horizontal_center, relationships`;
   relationship: `axis, elem, base, base_edge, elem_edge, gap`; gap entry:
   `base_signifiers, elem_signifiers, value`), `indent=2`, `ensure_ascii=
   False`, trailing newline. Wire `geometry.py`, `devserver.py:206`,
   `seed_from_classic.py:123` through it.
2. Fix `chord_left`: remove index 17; keep one `string ← jc` (confirm 0 vs
   10 with the owner; the current behaviour is 0). Remove the top-level
   `area_to_csv_column` key and the editor field that writes it
   (`jzpbuilder-dynamic.html:2535-2542, 2602-2604, 2632`).
3. `tests/test_layout_data.py`: round-trip equality on the committed file;
   validator catches each error class on hand-built bad inputs.
4. `jzpbuild/build.py`: `--classic_pos` (no-op today, documented as the
   inverse of the future default). `tests/test_coverage.py`: build
   `--dynamic_pos_only`, shape the corpus, assert the set of words with any
   glyph at offset (0,0) that classic positions equals
   `tests/dynamic_uncovered.txt` (27 words today).
5. Gate: `cmp` of both `.fea` outputs before/after; snapshot unchanged.

### Step 3 in detail

1. `dynamic_positioning/catalog.py` and `layout_data.py` (`LayoutData`
   wrapping step 2's loader) as in §2.2; `AnchorEngine.__init__(self, layout,
   area_sizes, center)`; `chain.resolve(engine, present, glyphs, *, center=
   True)` reads `engine.center`; `bare_fy(engine)` likewise.
2. `build.py`: `collect_rules(data, catalog, families) -> dict[str,
   list[_Rule]]`, `generate_fea(data, catalog, families) -> str`; delete
   `_ENGINES`, `_editor_rules`, the default-argument binding; `classes.py`
   functions take `(data, catalog)`; `identity.area_glyphs(area, catalog)`;
   `signifiers.py` reduces to `csv_column_for` + `key_to_glyph(catalog)`
   (the latter used only by the devserver/editor).
3. `dynamic_positioning/api.py` with the four functions; `__init__.py`
   exports only `api`.
4. `jzpbuild/genfea.py`: build `Catalog` from `load_components()` +
   `config.RIGHT_SELECTORS` + `config.CONTROL_GLYPHS`, `LayoutData.from_json
   (config.DYNAMIC_LAYOUTS_JSON.read_text())`, call `api.generate_fea`.
   Everything `geometry.FAMILIES` did becomes `catalog.families`.
5. `devserver.py`: each dynamic route = parse body → `api.*` → JSON; no
   `geometry` import, no mutation. Record 10 request/response pairs from the
   old server into `tests/fixtures/devserver_replay.json` *before* the
   change; replay after.
6. CI: `python -m build --wheel src-fonttools` for the package, plus a node
   script that loads Pyodide, `micropip.install`s the wheel, and resolves one
   word; assert it equals `api.resolve` run natively.
7. Gate: `cmp` on both `.fea`s; replay fixture identical; snapshot unchanged.
   Grep gate: `grep -r "from jzpbuild" dynamic_positioning/` returns nothing.

---

## 6. Open questions for the owner

1. **`center_y` 500 vs 300** (roadmap Phase 0 note): the snapshot regeneration
   in step 10 is where this lands; deciding earlier lets the cuo/vert work be
   tuned against the final baseline.
2. **Blank words**: virtual no-glyph pivot (one topology, small engine change)
   or two topologies pivoting on `hui` / `left` (no engine change)? This is
   not in the roadmap's Phase 0 list and blocks the flip.
3. **`chord_left`'s `string ← jc` gap**: 0 (current effective) or 10 (the
   dead later entry)?
4. **Selectors by glyph name** (schema v2): any reason to keep ASCII keys in
   the data file? The editor can still display them.
5. **`area_to_csv_column` in the JSON**: delete (recommended) or make it real
   by moving the area→column relationship into the catalog?
6. **Where does CI get `TW-Kai-98.ttf`?** It is gitignored; Actions needs it
   (release artifact, LFS, or a private bucket). Licensing may decide this.
7. **Golden diffs**: accept the 5 current differences (`U9,6` and the four
   cuo words) as the new baseline in step 1, or investigate first?
8. **Pyodide startup cost** in the editor: acceptable for the first slice, or
   should the API fixture (step 12's 50-state parity set) be designed from
   the start to support a TS port?
9. **`--dynamic_pos_only` after the flip**: delete (recommended; the coverage
   allow-list test replaces its purpose) or keep as a debugging mode?
10. **`RIGHT_SELECTORS` in `config.py`** vs a `family` column in
    `components.csv`: moving it makes the catalog self-contained for Phase 2's
    glyph editor (adding a right-hand glyph = one CSV row), at the cost of a
    one-time, byte-identical class-order check.
