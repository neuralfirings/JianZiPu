# Additive per-rank centering for `dynamic_positioning`

## Context

`dynamic_positioning/build.py` generates one literal contextual GPOS `pos`
rule per (topology, signifier, optional-element presence-combination) —
2^N combos per signifier, where N is the topology's optional-element
count. This is what overflows the 64KB `Offset16` subtable-offset ceiling
for the `chords` layout (confirmed: an 8,722-rule revision estimated at
~208KB via `estimate_dynamic_pos_bytes`, ~3.2x over budget).

Root cause, isolated through conversation: it's not the per-element
relationship gaps that vary combinatorially (those are already narrowly
scoped, per-neighbor, via `anchors.resolve_gap`'s `base_signifiers`/
`elem_signifiers`). It's `chain.resolve`'s **whole-stack vertical
centering shift** — one number computed from which optional elements are
present *anywhere* in the word (`vertical_center_order`'s topmost/
bottommost present rank span) and applied uniformly to every resolved
element. Because that shift can differ across combos even when an
element's own local relationship to its neighbor never changes,
`build.py`'s pivot/leaf rules need a disambiguating `optional_lookahead`
listing every present optional element — that's the actual combinatorial
driver (see README.md's "Scoping" section, `_signifier_rules` lines
176-219).

Agreed direction: let a layout author an **approximate, additive**
centering model instead of the exact topmost/bottommost calculation —
trading pixel-perfect centering for a small, fixed number of rank-based
contributions, opt-in per `LAYOUTS` entry, fully backward compatible
(existing layouts with no `centering` key keep today's exact behavior
unchanged).

**First implementation target: `default_jzp`, not `chords`.** Its
`vertical_center_order` is `[["fy"], ["left","hui"], ["jc"], ["zhu"],
["right"]]` — 5 ranks, 4 combinatorially-relevant (the 5th, `right`, is
the always-present pivot, so its own `per_rank` entry is just a constant
baseline, never needs disambiguating). `default_jzp` isn't overflowing
today, so this is a correctness check on the mechanism (hand-verifiable
against the existing exact output for all 32 combos) before it's ever
relied on to fix `chords`' real overflow. `chords`' `per_rank` tuning
(where `chord`'s own rank is expected to dominate enough that little/no
tuning is needed) stays a deliberate follow-up, per "Non-goals" below.

## Schema addition

One new optional key per `LAYOUTS` entry, positionally aligned with the
existing `vertical_center_order` list:

```json
"vertical_center_order": [
  ["fy_1"], ["left_1", "hui_1"], ["jc_1"], ["chord"], ["fy_2"], ["hui_2", "jc_2"]
],
"centering": {
  "mode": "additive",
  "per_rank": [-50, -100, -20, 0, -50, -20]
}
```

- `per_rank[i]` is the shift contribution for `vertical_center_order[i]`.
- OR-then-sum semantics: a rank contributes its value **once** if *any*
  of its member areas is present and resolved in this word — not once
  per present member (this is what makes `["left_1","hui_1"]` behave as
  one visual row instead of double-counting when both happen to be
  typed).
- Absent `centering` key → today's exact `_centering_bounds` behavior,
  byte-for-byte unchanged. This is the only way `default_jzp`/
  `chord_left`/`chord_right`/`vert` (none of which opt in) are guaranteed
  untouched.

## Implementation

### 1. `dynamic_positioning/anchors.py` — `AnchorEngine.__init__`

Parse the optional `centering` key once at construction (same place
`self.pivot`/`self.flat_optional` are already derived):

```python
centering = layout.get("centering")
self.centering_mode = centering["mode"] if centering else "exact"
self.centering_per_rank = centering.get("per_rank") if centering else None
if self.centering_mode == "additive":
    if len(self.centering_per_rank) != len(self.vertical_center_order):
        raise ValueError(
            f"layout {self.name!r}'s centering.per_rank must have one entry per "
            f"vertical_center_order rank ({len(self.vertical_center_order)}), "
            f"got {len(self.centering_per_rank)}")
```

Fail loudly at construction (same discipline as the existing single-pivot
check), not lazily at resolve time.

### 2. `dynamic_positioning/chain.py` — `resolve()` / new `_additive_shift`

Add a sibling to `_centering_bounds`:

```python
def _additive_shift(engine: "anchors.AnchorEngine", resolved: dict, present: dict) -> float:
    total = 0.0
    for rank, contribution in zip(engine.vertical_center_order, engine.centering_per_rank):
        if any(present.get(e) and e in resolved for e in rank):
            total += contribution
    return total
```

In `resolve()`, where `shift` is currently always computed via
`_centering_bounds`:

```python
if center:
    present_for_centering = {**present, **{e: True for e in always_present}}
    if engine.centering_mode == "additive":
        shift = _additive_shift(engine, resolved, present_for_centering)
    else:
        top, bottom = _centering_bounds(engine, resolved, present_for_centering)
        shift = geometry.CENTER_Y - (top + bottom) / 2
else:
    shift = 0
```

`bare_fy()` is left untouched — it's already hardcoded to `default_jzp`
only (per its own existing comment), which won't opt into additive mode.
Note this explicitly as a known limitation if a future additive-mode
topology ever needs a bare-pivot-less case.

### 3. `dynamic_positioning/build.py` — shrink `optional_lookahead` under additive mode

This is what actually reduces rule count/bytes — Phase 1 alone only
makes values coarser, it doesn't shrink any rule by itself, since
`optional_lookahead` still lists every literal present optional element
regardless of whether it can change the (now coarser) value.

Precompute an area→rank-index map once per `_signifier_rules` call:

```python
rank_of = {area: i for i, rank in enumerate(engine.vertical_center_order) for area in rank}
```

Change `optional_lookahead` so that, under additive mode, an element is
only included if it's the *first* present member of its rank in this
combo (a second present member of the same rank can't change the OR-sum
result, so it carries zero disambiguating value and is safe to omit —
this is a "less specific" rule per the existing sort discipline, i.e.
strictly correct, not a special case fontTools needs to know about):

```python
def optional_lookahead(elems: list[str]) -> list[str]:
    kept = []
    for e in elems:
        if e not in flat_optional:
            continue
        if (engine.centering_mode == "additive" and e in rank_of
                and any(present.get(sib) for sib in engine.vertical_center_order[rank_of[e]] if sib != e)):
            continue  # a same-rank sibling already covers this rank's contribution
        kept.append(e)
    return [token(e) for e in kept]
```

Exact-mode layouts get zero behavior change (the new branch is gated on
`centering_mode == "additive"`). For `chords`, once its `per_rank` makes
most non-`chord` ranks' contributions negligible relative to `chord`'s
own, many combos will additionally end up with byte-identical
`(backtrack, marked, lookahead, x, y)` rules — worth a follow-up trivial
exact-duplicate dedup pass in `_signifier_rules`'s return (`dict.fromkeys`
keyed by rule identity) since it's free correctness-preserving cleanup,
but the real savings come from the shorter lookaheads themselves.

### 4. `dynamic_positioning/README.md`

Add a subsection (next to "Whole-character vertical centering") documenting
the `centering` schema, OR-then-sum semantics, the additive-mode
`optional_lookahead` shrinking rule, and why it's opt-in/backward compatible
— consistent with this file's existing practice of explaining every
non-obvious mechanism in prose.

## Non-goals (per discussion)

- No `tools/jzpbuilder-dynamic.html` UI for editing `per_rank` — authored
  by hand in JSON for now.
- No `chords` work in this pass at all — `default_jzp` is the target.
  Applying this to `chords` (adding its own `centering` block, tuning
  `per_rank` so `chord`'s rank dominates) is explicit follow-up work once
  the mechanism is verified correct here.
- `bare_fy()` / any layout without `vertical_center_order` entries stays
  on exact mode; additive mode requires opting in explicitly.

## Verification

1. **No-regression check**: implement against a *copy* of
   `layouts_data.json` first (don't touch the real file's `default_jzp`
   entry until the mechanism is verified) — with `centering` absent
   everywhere, run `cd builder && python3 tests/test_shaping.py` and
   confirm the existing 78-case corpus is still 0 mismatches. Additive
   mode must be fully inert until a layout requests it.
2. **Toy-layout sanity check**: in a Python snippet, take `default_jzp`'s
   real layout dict, add a `centering` block, call `chain.resolve` for a
   handful of hand-picked presence combos (e.g. bare `right`+`string`;
   `fy`+`right`+`string`; all five optional elements present) with and
   without the `centering` key, and confirm: (a) stripped → reproduces
   today's exact `_centering_bounds` value exactly, (b) present → equals
   the hand-computed sum of matching `per_rank` entries.
3. **Rule-count/byte comparison**: call `build.count_dynamic_pos_rules`/
   `estimate_dynamic_pos_bytes` (or the live `/api/dynamic/rule_count`
   endpoint) on `default_jzp` before and after adding `centering`,
   confirming a real drop in rule count once `optional_lookahead`
   shrinks — this is the mechanism's real payoff, worth seeing concretely
   even though `default_jzp` was never overflowing.
4. **Real build**: `python3 -m jzpbuild --dynamic_pos_only -o
   /tmp/test.ttf` against the `centering`-enabled `default_jzp` and
   confirm it still builds clean and `tests/test_shaping.py` still passes
   with 0 position differences for every gou/io/li case — proof the
   approximation doesn't visibly break the one topology every existing
   dynamic_pos word currently depends on.
