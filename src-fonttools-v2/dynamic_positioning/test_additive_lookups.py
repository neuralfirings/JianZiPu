"""Verifies build.py's "additive_lookups" centering mode (ACCUM_LOOKUPS_PLAN.md)
reproduces chain.resolve's own additive-mode output, WITHOUT touching the
real layouts_data.json / font build -- this only ever constructs its own
in-memory copy of default_jzp with a fitted `centering` block, so
`--dynamic_pos` and every real build stay byte-for-byte unaffected (see
plan's "Design decisions"). Two things are checked independently:

1. The rule-generation + FEA-style first-match-wins simulation
   (_signifier_rules_lookups' stack_rules/center_rules) reproduces
   chain.resolve(..., center=True)'s per-element (x, y) exactly, for every
   presence combo x identity-bucket x right-hand key this layout selects.
   This is the mechanism check the plan's step 5.1 calls for.
2. Reports the fitted per_rank model's max deviation from the EXACT
   (non-additive) centering chain.py computes today -- this is NOT
   expected to be small for default_jzp (see below); it's printed so a
   human can judge whether default_jzp should ever actually ship on this
   mode, independent of whether the mechanism itself is correct.

Run directly: `python3 -m dynamic_positioning.test_additive_lookups`
"""

import copy
import itertools

import numpy as np

from . import anchors, build, chain, classes, geometry, identity, signifiers

_DEFAULT_JZP = next(layout for layout in geometry.LAYOUTS if layout["name"] == "default_jzp")


def _fit_per_rank(engine: anchors.AnchorEngine, right_glyph: str) -> tuple[list[float], float]:
    """Least-squares fit of an OR-then-sum per-rank model against the exact
    centering shift, over every presence combo, computed off ONE canonical
    signifier's raw (glyph-identity-dependent) values -- the per_rank model
    is inherently signifier-independent (one list per layout), so this is
    already an approximation baked into the "additive"/"additive_lookups"
    design itself, not something this fit can improve on. Returns
    (per_rank, max_abs_residual)."""
    flat_optional = engine.flat_optional
    rows, targets = [], []
    for combo in itertools.product((True, False), repeat=len(flat_optional)):
        present = dict(zip(flat_optional, combo))
        present_glyphs = {engine.pivot: right_glyph}
        raw = chain.resolve(engine, present, present_glyphs, center=False)
        resolved = {e: {"x": v[0], "y": v[1]} for e, v in raw.items()}
        present_for_centering = {**present, **{e: True for e in engine.always_present}}
        top, bottom = chain._centering_bounds(engine, resolved, present_for_centering)
        exact_shift = geometry.CENTER_Y - (top + bottom) / 2
        rows.append([1.0 if any(present_for_centering.get(e) for e in rank) else 0.0
                      for rank in engine.vertical_center_order])
        targets.append(exact_shift)
    A, b = np.array(rows), np.array(targets)
    per_rank, *_ = np.linalg.lstsq(A, b, rcond=None)
    max_residual = float(np.max(np.abs(A @ per_rank - b)))
    return [round(float(c), 4) for c in per_rank], max_residual


def _seq_tokens(engine: anchors.AnchorEngine, seq: list[str], right_token: str,
                 identity_choice: dict, generic: bool) -> list[str]:
    """The literal FEA class name each position in `seq` maps to for THIS
    specific combo/identity_choice -- ground truth for the matching
    simulation below, built from the exact same token-naming functions
    build.py's rule generation uses, so a string-equality match here is
    exactly as reliable as real feaLib glyph-class matching (classes.py's
    buckets partition each area's glyphs, see its own module docstring)."""
    tokens = []
    for area in seq:
        if area == engine.pivot:
            tokens.append(right_token)
        elif not generic and area in identity_choice:
            glyph = identity_choice[area]
            if glyph is None:
                tokens.append(classes.area_glyph_other_token(engine.name, area))
            else:
                tokens.append(classes.area_glyph_token(engine.name, area, glyph))
        elif area in classes._CLASSIC_BASE_AREAS:
            tokens.append(f"@area_{area}")
        else:
            tokens.append(classes.repeated_area_token(area))
    return tokens


def _first_match(rules: list["build._Rule"], seq_tokens: list[str], i: int):
    """First rule (rules already sorted most-specific-first, matching real
    FEA lookup semantics) whose marked/backtrack/lookahead exactly match
    seq_tokens around position i, contiguously -- or None."""
    for rule in rules:
        if rule.marked != seq_tokens[i]:
            continue
        bt = rule.backtrack
        if bt and (i - len(bt) < 0 or seq_tokens[i - len(bt):i] != bt):
            continue
        la = rule.lookahead
        if la and seq_tokens[i + 1:i + 1 + len(la)] != la:
            continue
        return rule
    return None


def verify_mechanism(per_rank: list[float]) -> None:
    layout = copy.deepcopy(_DEFAULT_JZP)
    layout["areas"] = geometry.AREA_SIZES
    layout["centering"] = {"mode": "additive_lookups", "per_rank": per_rank}
    engine = anchors.AnchorEngine(layout)
    engines = {"default_jzp": engine}

    checked = 0
    for key in layout["selector"]["contains"]:
        family = signifiers.family_for_key(key)
        right_token = f"@area_right__{family}__{signifiers.KEY_TO_GLYPH[key]}"
        stack_rules, center_rules = build._signifier_rules_lookups(
            family, key, [layout], engines)

        flat_optional = engine.flat_optional
        buckets_for_id = identity.area_glyph_buckets({"relationships": engine.relationships})

        for combo in itertools.product((True, False), repeat=len(flat_optional)):
            present = dict(zip(flat_optional, combo))
            seq = [e["area"] for e in engine.order if not e["optional"] or present.get(e["area"])]
            for identity_choice in build._identity_choices(present, buckets_for_id):
                present_glyphs = {engine.pivot: signifiers.KEY_TO_GLYPH[key]}
                present_glyphs.update({a: g for a, g in identity_choice.items() if g is not None})
                expected = chain.resolve(engine, present, present_glyphs, center=True)

                seq_tokens = _seq_tokens(engine, seq, right_token, identity_choice, generic=False)
                seq_tokens_generic = _seq_tokens(engine, seq, right_token, identity_choice, generic=True)

                for elem, (ex_x, ex_y) in expected.items():
                    if elem not in seq:
                        continue  # string_top/string_bottom -- checked via "string"'s slot below
                    i = seq.index(elem)
                    winner = _first_match(stack_rules, seq_tokens, i)
                    assert winner is not None, (
                        f"{key=} {present=} {identity_choice=}: no stacking rule matched {elem!r}")
                    total_y = winner.y
                    for rank_rules in center_rules.values():
                        hit = _first_match(rank_rules, seq_tokens_generic, i)
                        if hit is not None:
                            total_y += hit.y
                    assert abs(winner.x - ex_x) < 1e-6, f"{key=} {present=} {elem=}: x {winner.x} != {ex_x}"
                    assert abs(total_y - ex_y) < 1e-6, (
                        f"{key=} {present=} {identity_choice=} {elem=}: y {total_y} != {ex_y}")
                    checked += 1
    print(f"verify_mechanism: {checked} element resolutions checked, all matched chain.resolve exactly")


if __name__ == "__main__":
    right_glyph = signifiers.KEY_TO_GLYPH["k"]  # lg_gou -- canonical signifier for the fit
    engine_exact = anchors.AnchorEngine(copy.deepcopy(_DEFAULT_JZP) | {"areas": geometry.AREA_SIZES})
    per_rank, max_residual = _fit_per_rank(engine_exact, right_glyph)
    print(f"fitted per_rank (vs {engine_exact.vertical_center_order}): {per_rank}")
    print(f"max |exact - additive| residual across all combos: {max_residual:.1f} design units "
          "-- NOT expected to be small for default_jzp; see module docstring")
    verify_mechanism(per_rank)
