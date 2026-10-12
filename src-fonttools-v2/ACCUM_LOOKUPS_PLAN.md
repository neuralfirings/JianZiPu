# Plan: accumulating multi-lookup GPOS for `dynamic_positioning`

## Problem being solved

`dynamic_positioning/build.py` emits one literal contextual `pos` rule per
(presence-combination × glyph-identity-bucket × positioned element), all
inside a single `dynamic_pos` lookup. Rule count is exponential in the
number of optional elements (2^N combos), and the `chords` layout
overflows the hard 64KB `Offset16` subtable ceiling (~8,722 rules,
~208KB — see `estimate_dynamic_pos_bytes`'s docstring and MARKS_PLAN.md).

Root cause (established in MARKS_PLAN.md): each rule bakes in a **global**
number — the whole-stack vertical centering shift, which depends on which
optional elements are present *anywhere* in the word. Encoding a global
sum as per-rule literal totals forces enumeration of every combo, with
full-word disambiguating lookahead.

## The architecture change

Exploit a core OpenType GPOS guarantee (spec, "GPOS — Glyph Positioning
Table"): *"The positioning adjustment of each lookup is applied to the
result of previous lookups... adjustments are accumulated as each lookup
is processed."* X/Y placement values from separate lookups **sum**. (This
codebase has already confirmed this empirically — it's the very behavior
that broke the old mark-attachment prototype, see
`dynamic_positioning/README.md` "Why not GPOS mark attachment".)

So: decompose each element's final Y into additive contributions, each
needing only **local** context, and let the shaper do the summing:

1. **Stacking lookup** (`dynamic_stack`): each element's *raw*,
   uncentered position (`chain.resolve(..., center=False)`). A raw value
   depends only on the element's transitive chain of chosen bases — never
   on unrelated elements' presence — so contexts shrink and duplicate
   rules collapse.
2. **Centering lookups** (`dynamic_center_<layout>_<rank_i>`, one per
   `vertical_center_order` rank with a nonzero contribution): "if any
   member of rank *i* is present in this word, add `per_rank[i]` to the Y
   of every element." Each present rank fires its lookup once per glyph;
   accumulation produces exactly `chain._additive_shift`'s OR-then-sum
   total, with no rule ever mentioning more than one rank.

This **requires the additive centering model** (already implemented:
`anchors.AnchorEngine.centering_mode == "additive"`,
`chain._additive_shift`, MARKS_PLAN.md). Exact max/min centering is not
additive and cannot be decomposed this way — exact-mode layouts keep the
current single-lookup path unchanged.

Rule-count effect: adding an optional element stops doubling the rule set;
it adds a handful of stacking rules plus one small centering lookup. Also,
the 64KB ceiling is **per subtable**, so splitting into N+1 lookups
multiplies the byte budget even before the count reduction.

### Worked toy example (keep handy while implementing)

Areas A (glyphs 1,2,3), B (a,b,c), C (x,y,z; pivot, always present).
Typed order A B C. Heights 100. Gaps: A over B = 10 (glyph 1) / 20
(glyphs 2,3); B over C = 5; A over C when B absent = 1/2/3 per glyph.
Ranks `[[A],[B],[C]]`, `per_rank = [-15, -8, 0]`.

Raw values: B = 105; A-via-B = 215 (glyph 1) / 225 (2,3); A-via-C =
101/102/103.

```fea
lookup dynamic_stack {
  pos @A_1'  <0 215 0 0> @B @C;   # via B, most-specific first
  pos @A_23' <0 225 0 0> @B @C;
  pos @A_1'  <0 101 0 0> @C;      # B absent -> falls through to via-C
  pos @A_2'  <0 102 0 0> @C;
  pos @A_3'  <0 103 0 0> @C;
  pos @B'    <0 105 0 0> @C;
} dynamic_stack;                   # C stays at 0

lookup center_A {                  # A present => everyone -15
  pos @A' <0 -15 0 0> @B @C;       # A itself (context pins the word shape)
  pos @A' <0 -15 0 0> @C;
  pos @A @B' <0 -15 0 0> @C;
  pos @A @C' <0 -15 0 0>;          # C one after A (B absent)
  pos @A @B @C' <0 -15 0 0>;       # C two after A
} center_A;

lookup center_B {                  # B present => everyone -8
  pos @B' <0 -8 0 0> @C;
  pos @A' <0 -8 0 0> @B @C;
  pos @B @C' <0 -8 0 0>;
} center_B;                        # rank C contributes 0 -> no lookup
```

Word `2 a x`: stack 225/105/0; center_A −15 each; center_B −8 each →
202/82/−23 == old literal-total arch. Word `3 x`: stack falls through to
via-C → 103/0; only center_A fires → 88/−15. ✓

Note contexts in centering rules are **exact consecutive sequences** —
chained-context matching is consecutive, so a word `A X B` never matches
backtrack `[A] B'` (the glyph immediately before B is X). Exact contexts
from different combos are therefore mutually exclusive; no ordering
subtleties between them.

## Design decisions (made — do not re-litigate)

- **Opt-in per layout** via a new `centering.mode` value:
  `"additive_lookups"`. Layouts with no `centering` key ("exact") and
  layouts with `"additive"` (literal-total additive, the existing
  MARKS_PLAN implementation) are **byte-for-byte unchanged**. This is the
  same backward-compat discipline as MARKS_PLAN.
- **Keep the combo-enumeration loop** in `build.py` rather than writing a
  new per-relationship generator. Correct rule shrinkage comes from
  (a) trimming each rule's context to only the elements that can affect
  its value, then (b) **deduplicating identical rules**. Combos that
  differ only outside a rule's trimmed context produce byte-identical
  rules and collapse. This is the minimal-change, hardest-to-get-wrong
  implementation; a smarter direct generator is a non-goal.
- **Scoping**: every rule — stacking and centering — must still contain
  this layout's pivot/signifier token (`classes.signifier_token(...)`) in
  its context, or centering rules will fire on other families' words that
  share fy/hui/left/jc/zhu glyphs (the exact leak that killed the
  mark-attachment prototype; see README.md). The combo loop's existing
  token machinery already guarantees this for stacking; centering rules
  must keep the span-through-pivot context (see step 3).
- **Lookup registration order**: `dynamic_stack` first, then centering
  lookups, all registered in the `kern` feature. (Order is irrelevant to
  the sum, but keep it deterministic.)
- **`bare_fy` and the `@area_fy_blocker` rule** stay in the stacking
  lookup exactly as today, with `bare_fy` keeping its own literal centered
  value (a bare-fy word has no pivot glyph, so centering lookups can never
  fire on it — its centering must stay baked in).
- Exact-mode and `"additive"` layouts keep emitting into the existing
  single `dynamic_pos` lookup via the existing code path. Mixed modes
  coexist: rules are family-scoped, lookups don't interfere.

## Implementation steps

### Step 1 — `anchors.py`: accept the new mode

In `AnchorEngine.__init__`, where `centering_mode` is parsed: allow
`"additive_lookups"` and validate its `per_rank` with the same
length-check as `"additive"` (share the branch:
`if self.centering_mode in ("additive", "additive_lookups")`). Also make
`chain.resolve`'s mode dispatch treat `"additive_lookups"` like
`"additive"` when `center=True` (used only by the devserver preview and
tests — the font build for these layouts always passes `center=False`,
see step 2). One-line change in `chain.resolve`'s
`if engine.centering_mode == "additive":` condition.

### Step 2 — `build.py`: split `_signifier_rules` output by mode

Give `_Rule` an `__eq__`/`__hash__` (or dedupe via a
`(tuple(backtrack), marked, round(x), round(y), tuple(lookahead))` seen-
set) — needed for dedup below.

In `_signifier_rules`, when `engine.centering_mode == "additive_lookups"`:

**(a) Stacking rules.** Call
`chain.resolve(engine, present, present_glyphs, center=False)`. Trim each
rule's context to the marked element's **transitive candidate-base
closure**: starting from the marked element, repeatedly add every area
that appears as `base` in any relationship declared for an
already-included element (`engine.relationships_for(axis, elem)`, both
axes). Context tokens kept = present members of that closure, in typed
(`engine.order`) position — before the marked element → backtrack, after
→ lookahead — **plus** the pivot token (always, for scoping) and, for
before-pivot elements, nothing else. Why the closure: a rule's literal
value bakes in its base's raw value, which bakes in *its* base's, etc. —
so the context must pin down every choice `chain._choose_relationships`
makes anywhere up the chain, and nothing more. Elements outside the
closure carry zero information about the value; dropping them is what
makes combos collapse under dedup. (`optional_lookahead` and its
additive-mode rank-sibling trimming are irrelevant on this path — do not
call it; it exists for the literal-total centering coupling, which
`center=False` removes.)

Keep the `string_top`/`string_bottom` double-string special case as-is
(same trimming applies; their closure includes each other).

**(b) Centering rules.** For each rank `i` with `per_rank[i] != 0`: for
each combo where at least one member of `vertical_center_order[i]` is
present, for each element `T` present in that combo (including
always-present ones that resolved, and including the trigger member
itself): emit a rule marking `T` with value `<0 per_rank[i] 0 0>` and
context = the present elements spanning from the leftmost of
{trigger member(s), `T`, pivot} through the rightmost of them, in typed
order (consecutive — chained contexts match consecutive glyphs, so every
present element inside the span must appear). Use the same `token()`
function as stacking so identity-bucket classes stay consistent — but
note identity buckets are irrelevant to centering values, so pass an
empty `identity_choice` for centering-rule tokens (generic `@area_*`
classes), which maximizes dedup. Dedupe. Bucket these rules per
`(layout_name, rank_i)`.

OR-then-sum correctness falls out automatically: a combo with two present
same-rank siblings emits **one** rule per target for that rank (the combo
is a single iteration), so the contribution is never double-counted.

**(c) Plumbing.** Restructure so rule generation returns
`{"stack": [...], "center": {(layout_name, rank_i): [...]}, "classic": [...]}`
(where `"classic"` is the untouched exact/`"additive"`-mode output).
`gen_dynamic_gpos` then renders:

```
lookup dynamic_pos { <classic rules, sorted as today> } dynamic_pos;      # only if non-empty
lookup dynamic_stack { <stack rules, sorted most-specific-first> } dynamic_stack;
lookup dynamic_center_<layout>_<i> { ... } ...;                            # one per (layout, rank)
feature kern {
  lookup dynamic_pos;        # if present
  lookup dynamic_stack;
  lookup dynamic_center_...;  # each
} kern;
```

`bare_fy` + blocker rules go in `dynamic_pos` if it exists, else
`dynamic_stack`.

### Step 3 — estimator: `_collect_rules` / `estimate_dynamic_pos_bytes`

The overflow ceiling is per subtable, and rules now live in several
lookups. Update `_collect_rules` to return the per-lookup buckets from
step 2c, and `estimate_dynamic_pos_bytes` to report the **max per-lookup
estimate** (plus total, for the UI). Update
`devserver.py::/api/dynamic/rule_count`'s response shape minimally —
`tools/jzpbuilder-dynamic.html` reads it for the complexity badge; keep
the existing top-level keys working (feed it the max) so the JS doesn't
need rework in this pass.

### Step 4 — derive `per_rank` for `default_jzp` and flip it on

In the layouts JSON (`dynamic_positioning/layouts_data.json` — see
`config.DYNAMIC_LAYOUTS_JSON`; note `layouts_jzp.json`/
`layouts_jzp_nocenter.json` and the various `layouts_data.*.json`
siblings are older experiment snapshots — only touch the file `config`
points at), add to `default_jzp`:

```json
"centering": {"mode": "additive_lookups", "per_rank": [r_fy, r_lh, r_jc, r_zhu, r_right]}
```

Derive `per_rank` by fitting: compute the exact shift
(`chain._centering_bounds` path) for all 2^4 presence combos of
`default_jzp`'s optional ranks, then least-squares-fit the additive model
(a tiny script — 16 equations, 5 unknowns; `numpy.linalg.lstsq` or solve
by hand; the always-present `right` rank's coefficient is just the
constant baseline). Print the per-combo residual; a few units of error is
acceptable, but report the max residual in the final summary so a human
can judge.

### Step 5 — verify

1. **Pure-Python check first** (no font build): a test that, for every
   `default_jzp` presence combo × signifier, simulates the rule system —
   take the generated stacking rules + centering rules, find for each
   element the matching stacking rule (most-specific-first,
   consecutive-context matching against the combo's typed sequence) and
   every matching centering rule across lookups, sum them — and asserts
   the total equals
   `chain.resolve(engine, present, present_glyphs, center=True)` (additive
   mode) exactly, element by element. This catches trimming/dedup bugs
   without any shaper in the loop. Put it in `tests/`.
2. **Real shaping**: build the font (`python3 -m jzpbuild --dynamic_pos`)
   and run `cd . && python3 tests/test_shaping.py JianZiPu.ttf` (uharfbuzz
   regression vs the tracked font). Expect positional diffs bounded by
   step 4's fitting residual for gou/io/li words; anything larger, or any
   diff in non-dynamic words, is a bug.
3. **Eyeball**: `python3 -m jzpbuild.devserver`, open
   `tools/font_tester.html` against the new build; check words with and
   without fy/left/hui/jc/zhu present, plus a `loki`/`nc` word to confirm
   no centering leak into other families (THE historical failure mode —
   test this explicitly).
4. **The actual goal**: run `estimate_dynamic_pos_bytes` on the chords
   layouts revision that overflowed (see MARKS_PLAN.md: 8,722 rules,
   ~208KB) with `chords` switched to `additive_lookups` (rough `per_rank`
   is fine for the size check) and confirm max per-lookup estimate is
   comfortably under 64KB. Don't tune chords' values in this pass — size
   check only.

## Pitfalls / invariants

- **Consecutive matching**: FEA chained contexts match consecutive glyph
  sequences. Every context you emit must list *every* present element
  between its outermost tokens — never "skip" one. The span construction
  in step 2b and the closure trimming in 2a must both respect this: when
  trimming drops an element that sits *between* two kept tokens in typed
  order, the trimmed context is wrong (would never match). Correct
  handling: a context is a *contiguous* window of the typed sequence; you
  may only shrink it from the ends, not punch holes. So "trim to closure"
  means: shrink the window to the smallest contiguous span containing the
  marked element, all present closure members, and the pivot — elements
  inside that span stay in the context even if outside the closure.
  (They'll limit dedup slightly; correctness first.)
- **First-match-wins** within a lookup: keep the existing
  most-specific-first sort for stacking. Centering rules from different
  combos are mutually exclusive (exact consecutive contexts), but sort
  them the same way anyway for determinism.
- **Value records accumulate; attachment overrides**: fine here (all
  lookups are type-1 single adjustments via chained dispatch), but don't
  introduce any mark/cursive lookups into this stack without rechecking.
- **Do not touch** `jzpbuild/features.py` (GSUB), the classic
  `jzpbuild/gpos.py` families, or any layout not opted into
  `additive_lookups`. `--dynamic_pos` off must remain byte-identical.
- `_Rule.render()` rounds x/y — dedupe on the *rounded* values so
  float noise doesn't defeat it.
- feaLib compiles each `pos ... ' ...;` to a ChainContextPos format-3
  subtable; the estimator's per-rule byte model
  (`estimate_dynamic_pos_bytes`'s comment) still applies per lookup.

## Execution findings (steps 1-4 and 5.1 done; 5.2-5.4 blocked/deferred)

Implemented: `anchors.py`/`chain.py` accept `"additive_lookups"`;
`build.py` gained `_signifier_rules_lookups` (closure-trimmed stacking
rules + per-rank centering lookups, deduped), `gen_dynamic_gpos` renders
them as separate lookups, `_collect_rules`/`estimate_dynamic_pos_bytes`
report per-lookup (not summed) bytes. Verification lives in
`dynamic_positioning/test_additive_lookups.py`
(`python3 -m dynamic_positioning.test_additive_lookups`) — it builds an
in-memory `additive_lookups` copy of `default_jzp` (layouts_data.json
itself was deliberately left untouched, see below) and confirms, via a
real first-match-wins FEA-style simulation against the generated rules,
that every (presence-combo x identity-bucket x element) resolution
matches `chain.resolve`'s own additive output exactly — **720/720
checks passed**.

**Important negative result, found while measuring the actual byte
payoff (step 5.4's spirit, since the real overflowing chords revision no
longer exists in this repo to test against directly):** the mechanism's
promised win — "no rule ever mentions more than one rank" — only holds
when a rank's trigger area and a target element sit CLOSE TOGETHER in
`order`'s typed sequence. Chained-context backtrack/lookahead must match
a real contiguous glyph run (no skipping "irrelevant" glyphs), so a
centering rule still has to list every present element *between* its
trigger and its target, whatever rank they belong to. When triggers and
targets are scattered across a long optional-element sequence, that
in-between list is itself combo-dependent, and the centering lookups stop
collapsing under dedup — measured directly:

- **`default_jzp`** (5 optional elements, ranks track typed order
  closely): stacking+centering split gives a real but modest win — max
  single-lookup bytes 15,902 -> 12,858 (~19%), though *total* bytes across
  all lookups combined is actually higher (34,110 vs 15,902) since
  centering lookups add rules rather than replacing them.
- **Synthetic stress test** (N independent optional leaves, one rank
  each, mimicking MARKS_PLAN's literal "root cause" scenario): rule count
  still grows ~2^N under `additive_lookups` (33 / 193 / 1,025 / 5,121 /
  24,577 rules for N=3/5/7/9/11) — **not fixed**, because with leaves
  scattered arbitrarily across the sequence, span-trimming can't shrink
  contexts below what's still combo-dependent.

**Conclusion: this architecture is a real fix only for topologies whose
`vertical_center_order` ranks stay adjacent-ish in `order`'s typed
sequence** (true for `default_jzp`, unconfirmed for `chords` since its
historical overflowing `layouts_data.json` revision isn't preserved
anywhere in this repo to check). Before applying this to `chords`:

1. Check whether chords' real (re-authored) optional-element `order`
   keeps same-rank-adjacent-in-sequence structure. If yes, this mechanism
   should work close to as designed.
2. If no, the `MarkFilteringSet`/GDEF-based context-skipping idea listed
   under "Non-goals" below stops being a nice-to-have and becomes
   *required* to make span length independent of how far apart a
   trigger/target pair sit — do that first, or this won't fix chords'
   real overflow either.

**`default_jzp`'s real `layouts_data.json` was deliberately left in
`"exact"` mode** (per the "Design decisions" backward-compat guarantee) —
its fitted `per_rank` has an 86.4-design-unit max residual against exact
centering, too large to ship, and the byte win for this topology is
marginal anyway. `--dynamic_pos` real-build output is therefore verified
byte-identical to before this change (confirmed: a real `python3 -m
jzpbuild --dynamic_pos` build succeeds, and since no `LAYOUTS` entry now
sets `centering.mode == "additive_lookups"`, `gen_dynamic_gpos`'s new
code paths are never taken — `stack_rules`/`center_rules` stay empty).

Steps 5.2 (shaping regression), 5.3 (font_tester.html eyeball check), and
5.4 (chords-specific byte confirmation) were not run: 5.2/5.3 have no new
production behavior to check yet (nothing switched modes for real), and
5.4 needs a decision from the two open items above before it's
meaningful.

## Non-goals (explicitly out of scope)

- Tuning chords' `per_rank` / shipping chords on the new mode (size-check
  only, per step 5.4).
- A direct per-relationship rule generator (dedup over the combo loop is
  the chosen mechanism).
- `MarkFilteringSet`/GDEF-based context skipping (a future compression if
  spans ever get long; requires reclassifying shared glyphs — risky).
- Cursive-attachment stacking (candidate future architecture; blocked on
  CoreText confidence — see conversation notes in git history).
- Removing the literal-total `"additive"` mode or `optional_lookahead`
  (still the shipped behavior for any layout using them).
