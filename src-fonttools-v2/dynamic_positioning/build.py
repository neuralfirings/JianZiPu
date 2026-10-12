"""Generate literal contextual `pos` rules per right-hand SIGNIFIER (an
ASCII key, e.g. "k" for lg_gou vs "l" for lg_da -- finer than family)
from geometry.LAYOUTS (via chain.py/anchors.py), instead of GPOS mark
attachment.

Why not mark attachment: an earlier version of this module used GPOS
mark-to-base/mark-to-mark anchors (types 4/6). Those anchors fire whenever
their glyph shapes match, with no way to require "and only within a
gou/io/li word" -- fy/hui/left/jc/zhu are the same shared glyphs across
every right-hand-technique family, so the mark rules also fired (and
additively stacked on top of) the classic pipeline's own positioning for
loki/nc/tiao/mo words. Literal contextual single-adjustment rules (this
module) can require the exact backtrack/lookahead glyph sequence --
including the specific per-signifier class from classes.py -- so they
only ever match words that actually contain that exact right-hand glyph,
same scoping mechanism jzpbuild/gpos.py::word_layout_rules already relies
on via its `R_` context.

Rule ORDER is load-bearing, same as jzpbuild/gpos.py: within the lookup,
the FIRST matching rule wins. Rules are emitted most-specific (longest
backtrack+lookahead) first, so e.g. a rule requiring "@area_fy" in the
backtrack is tried before the otherwise-identical rule that doesn't --
letting real fy-less sequences correctly fall through to it. See
README.md.

Backtrack/lookahead context reflects the real TYPED/glyph-sequence order
(engine.optional_order) -- a fact about the shaped text, unrelated to
which element's POSITION a given element is computed relative to
(chain.py's concern, see geometry.py's module docstring). area_zhu still
gets its own `pos` rule with correct backtrack/lookahead here even though
chain.py computes its value as an offset from area_right rather than
from whatever preceded it in typed order.

geometry.LAYOUTS is what actually drives this module's coverage: iterate
its entries, and each entry's own selector.contains gives the keys to
generate rules for -- adding a new LAYOUTS entry is picked up here
automatically, no separate registration needed. Every token except the
pivot (engine.pivot, e.g. "right"/"chord") is generic ("@area_{elem}");
the pivot gets classes.signifier_token(...) instead, since that's the one
element whose glyph IS the signifier.
"""

import itertools

from jzpbuild import config

from . import anchors, chain, classes, geometry, identity, signifiers

_ENGINES = {layout["name"]: anchors.AnchorEngine(layout) for layout in geometry.LAYOUTS}


def _engine_for_key(key: str, layouts: list[dict] = geometry.LAYOUTS,
                     engines: dict[str, anchors.AnchorEngine] = _ENGINES) -> anchors.AnchorEngine:
    """`layouts`/`engines` default to the real, cached geometry.LAYOUTS/
    _ENGINES globals (every existing caller's prior behavior, unchanged).
    count_dynamic_pos_rules passes its own throwaway pair instead, so it can
    count rules for an arbitrary (possibly unsaved/in-editor) layouts list
    without touching those globals."""
    for layout in layouts:
        if key in layout["selector"].get("contains", ()):
            return engines[layout["name"]]
    raise KeyError(f"no geometry.LAYOUTS entry selects key={key!r}")


class _Rule:
    def __init__(self, backtrack: list[str], marked: str, x: float, y: float,
                 lookahead: list[str]):
        self.backtrack = backtrack
        self.marked = marked
        self.x = x
        self.y = y
        self.lookahead = lookahead

    @property
    def specificity(self) -> int:
        return len(self.backtrack) + len(self.lookahead)

    def render(self) -> str:
        parts = list(self.backtrack)
        parts.append(f"{self.marked}' <{round(self.x)} {round(self.y)} 0 0>")
        parts += self.lookahead
        return "  pos " + " ".join(parts) + ";"


def _identity_choices(present: dict[str, bool],
                       buckets: dict[str, dict[str, object]]) -> list[dict[str, str | None]]:
    """One dict per combination of concrete glyph-bucket choices for whichever
    identity-sensitive areas (`buckets`, see identity.area_glyph_buckets) are
    actually present in this combo. A value of `None` means "the catch-all
    bucket" -- present_glyphs gets nothing added for that area, so
    resolve_gap naturally falls through to the catch-all entry. Areas not
    present, or with no bucket at all, aren't iterated -- their token stays
    the generic `@area_{name}` (see _signifier_rules' `token()`)."""
    axes = [(area, list(bucket["glyphs"]) + ([None] if bucket["catch_all"] else []))
            for area, bucket in buckets.items() if present.get(area)]
    if not axes:
        return [{}]
    return [dict(zip((a for a, _ in axes), combo))
            for combo in itertools.product(*(opts for _, opts in axes))]


def _signifier_rules(family: str, key: str, layouts: list[dict] = geometry.LAYOUTS,
                      engines: dict[str, anchors.AnchorEngine] = _ENGINES) -> list[_Rule]:
    engine = _engine_for_key(key, layouts, engines)
    rules: list[_Rule] = []
    right_token = classes.signifier_token(family, key)
    right_glyph = signifiers.KEY_TO_GLYPH[key]
    flat_optional = engine.flat_optional
    # Which non-pivot areas this layout's own gap overrides reference by
    # glyph identity (e.g. area_hui's md_5/md_9) -- see identity.py. Areas
    # not referenced here never branch below; `token()` stays generic for
    # them exactly as before this feature existed.
    buckets = identity.area_glyph_buckets({"relationships": engine.relationships})
    # area -> its vertical_center_order rank index, only consulted under
    # engine.centering_mode == "additive" (see optional_lookahead below).
    rank_of = {area: i for i, rank in enumerate(engine.vertical_center_order) for area in rank}

    for combo in itertools.product((True, False), repeat=len(flat_optional)):
        present = dict(zip(flat_optional, combo))
        # the real full sequence for this combo: every always-present
        # element (in its engine.order position -- the pivot might come
        # first, as for cuo's chord, or last, as for default_jzp's right;
        # nothing here assumes either) plus whichever optional elements
        # are present, all in engine.order's declared order.
        seq = [e["area"] for e in engine.order if not e["optional"] or present.get(e["area"])]
        pivot_i = seq.index(engine.pivot)
        before, after = seq[:pivot_i], seq[pivot_i + 1:]

        # For each present identity-sensitive area, branch over its
        # declared glyph buckets (plus catch-all if any) -- e.g. if `hui`
        # is present and its own glyph affects some gap, generate one full
        # rule-set variant per hui glyph bucket, each requiring that
        # bucket's specific class (disjoint from every other bucket for
        # the same area -- see classes.area_glyph_token/
        # area_glyph_other_token) instead of the generic `@area_hui`. No
        # FEA rule-ordering concern between these variants: the classes
        # partition the area's glyphs, so a real word only ever matches
        # exactly one of them.
        for identity_choice in _identity_choices(present, buckets):
            present_glyphs = {engine.pivot: right_glyph}
            present_glyphs.update({a: g for a, g in identity_choice.items() if g is not None})

            def token(area: str, _choice=identity_choice) -> str:
                if area == engine.pivot:
                    return right_token
                if area in _choice:
                    glyph = _choice[area]
                    if glyph is None:
                        return classes.area_glyph_other_token(engine.name, area)
                    return classes.area_glyph_token(engine.name, area, glyph)
                if area in classes._CLASSIC_BASE_AREAS:
                    return f"@area_{area}"
                return classes.repeated_area_token(area)

            positions = chain.resolve(engine, present, present_glyphs)

            # Elements BEFORE the pivot chain together (each attaches to
            # whichever preceded it), with lookahead always ending in
            # right_token -- that's the scoping mechanism (ensures these
            # only ever match words that actually contain THIS signifier,
            # not some other family's word that happens to share the same
            # fy/left/hui/jc glyphs -- see module docstring).
            for i, area in enumerate(before):
                backtrack = [token(e) for e in before[:i]]
                lookahead = [token(e) for e in before[i + 1:]] + [right_token]
                x, y = positions[area]
                rules.append(_Rule(backtrack, token(area), x, y, lookahead))

            # Disambiguating lookahead for anything at-or-after the pivot:
            # only OPTIONAL elements carry any combo-distinguishing
            # information at all (non-optional/always-present ones, e.g.
            # `string`, are attempted in EVERY combo regardless of whether a
            # real word actually has that glyph -- chain.resolve silently
            # tolerates them failing to resolve, see its own docstring --
            # so requiring one in a lookahead would wrongly reject a real
            # word that genuinely lacks it, for zero disambiguating benefit
            # since its presence never varies across combos to begin with).
            # `elems` is `before`/`after`[i+1:] filtered to flat_optional.
            # Under additive centering mode, an element is further dropped
            # if a same-rank sibling is ALREADY present anywhere else in
            # this combo -- chain._additive_shift counts a rank's
            # contribution once per present member (OR-then-sum), so a
            # second present sibling can't change the computed value and
            # carries zero disambiguating information; omitting it makes
            # this rule strictly less specific (matches more real words),
            # which is safe under the existing most-specific-first sort.
            # Exact-mode layouts (engine.centering_mode != "additive") get
            # zero behavior change here -- this is the mechanism that
            # actually shrinks rule count once a layout opts into
            # `centering` (see README.md's "Approximate additive
            # centering"), not the value computation alone.
            def optional_lookahead(elems: list[str]) -> list[str]:
                kept = []
                for e in elems:
                    if e not in flat_optional:
                        continue
                    if engine.centering_mode == "additive" and e in rank_of and any(
                            present.get(sib) for sib in engine.vertical_center_order[rank_of[e]]
                            if sib != e):
                        continue
                    kept.append(e)
                return [token(e) for e in kept]

            # The pivot itself: backtrack is whatever preceded it in this
            # combo. Its own resolved value can depend on which optional
            # elements come AFTER it too (same whole-stack centering-shift
            # coupling as the leaves below), not just which preceded it --
            # so it needs the same kind of disambiguating lookahead, filtered
            # to optional elements only so a genuinely leaf-less/string-less
            # real word (the valid "bare pivot" case) still matches the
            # variant generated for that same absence. A real bug this
            # caused before lookahead was added here: every combo's pivot
            # rule shared byte-identical (empty) backtrack/lookahead, so only
            # whichever combo happened to be generated first ever won, for
            # every real word regardless of what actually followed the
            # pivot -- e.g. cuo's own chord glyph rendering at the wrong
            # height whenever the real word's optional elements didn't match
            # the arbitrary first-generated combo.
            pivot_backtrack = [token(e) for e in before]
            x, y = positions[engine.pivot]
            rules.append(_Rule(pivot_backtrack, right_token, x, y, optional_lookahead(after)))

            # Elements AFTER the pivot (leaves: string, and anything
            # future topologies add here) each independently attach right
            # after whatever precedes them. Scoping against OTHER families
            # already comes from right_token sitting in their backtrack (the
            # pivot precedes them) -- but scoping against OTHER PRESENCE
            # COMBOS of THIS SAME family still needs a lookahead, for the
            # identical reason as the pivot above: a leaf's own resolved
            # (x, y) can depend on which later OPTIONAL leaves are present
            # too, not just its own presence. Listing whichever later
            # OPTIONAL leaves this specific combo actually has (in order) as
            # lookahead lets rules.sort's existing most-specific-first
            # ordering pick the correct one: a real word missing one of
            # those later leaves fails this lookahead and falls through to
            # the next, less-specific (fewer leaves listed) matching combo's
            # rule instead, exactly mirroring how BEFORE-pivot elements
            # already use their own remaining-siblings-then-right_token
            # lookahead for the identical reason.
            running_backtrack = pivot_backtrack + [right_token]
            for i, area in enumerate(after):
                after_lookahead = optional_lookahead(after[i + 1:])
                x, y = positions[area]
                rules.append(_Rule(running_backtrack, token(area), x, y, after_lookahead))

                # li's double-string case: string_top/string_bottom ride
                # along in the SAME sequence slot "string" occupies
                # (variants of the same leaf, deliberately not separate
                # entries in `order` -- see geometry.py). Emitted alongside
                # (not instead of) the generic "string" rule above -- li
                # words can use either. Their own paired backtrack/
                # lookahead (string_bottom requires string_top immediately
                # before it, then whichever later leaves this combo has,
                # same as the generic "string" rule above) is a real
                # rule-matching coordination between the two, not a generic
                # independent-leaf case, so it's special-cased here. Whether
                # string_top/string_bottom actually show up in `positions`
                # for THIS signifier at all IS the "is this signifier
                # double-string" signal (see chain.resolve's docstring) --
                # no separate flag.
                if area == "string" and "string_top" in positions and "string_bottom" in positions:
                    top_x, top_y = positions["string_top"]
                    bottom_x, bottom_y = positions["string_bottom"]
                    rules.append(_Rule(running_backtrack, "@area_string_top", top_x, top_y,
                                        ["@area_string_bottom"] + after_lookahead))
                    rules.append(_Rule(running_backtrack + ["@area_string_top"], "@area_string_bottom",
                                        bottom_x, bottom_y, after_lookahead))
                running_backtrack = running_backtrack + [token(area)]

    return rules


def _rule_key(rule: "_Rule") -> tuple:
    """Dedup key for a rendered rule -- rounded to match _Rule.render's own
    rounding, so float noise across combos/identity-choices doesn't defeat
    dedup."""
    return (tuple(rule.backtrack), rule.marked, round(rule.x), round(rule.y), tuple(rule.lookahead))


def _generic_token(engine: "anchors.AnchorEngine", right_token: str, area: str) -> str:
    """Like _signifier_rules' per-combo token(), but never branches by
    glyph identity -- used for centering-lookup rules, whose value never
    depends on any area's specific glyph (see _signifier_rules_lookups)."""
    if area == engine.pivot:
        return right_token
    if area in classes._CLASSIC_BASE_AREAS:
        return f"@area_{area}"
    return classes.repeated_area_token(area)


def _closure(chosen: dict[str, dict[str, dict]], elem: str) -> set[str]:
    """Every area `elem`'s resolved value transitively depends on, given one
    combo's `chosen` relationships (chain._choose_relationships' output) --
    i.e. `elem`'s own chosen bases, their own chosen bases, etc. Doesn't
    include `elem` itself. Every member is guaranteed present in this combo
    by construction: _choose_relationships only ever selects a base that's
    either present-and-ranked or unconditionally always-present (see its
    own docstring's preference order), never an absent one."""
    seen: set[str] = set()
    frontier = [elem]
    while frontier:
        for rel in chosen.get(frontier.pop(), {}).values():
            base = rel["base"]
            if base is not None and base not in seen:
                seen.add(base)
                frontier.append(base)
    return seen


def _span_tokens(seq: list[str], elem_i: int, keep_indices: set[int],
                  token) -> tuple[list[str], list[str]]:
    """backtrack/lookahead token lists for one rule: the smallest CONTIGUOUS
    slice of `seq` spanning every index in `keep_indices` (plus elem_i
    itself) -- never a sparse subset. Chained-context backtrack/lookahead
    match glyphs immediately adjacent in the real sequence, so any area
    that sits between two areas we care about must still appear in the
    rule even though its own identity/presence carries no information --
    dropping it would make the rule match a sequence that was never
    actually produced. See ACCUM_LOOKUPS_PLAN.md's "Pitfalls" section."""
    keep_indices = keep_indices | {elem_i}
    lo, hi = min(keep_indices), max(keep_indices)
    backtrack = [token(a) for a in seq[lo:elem_i]]
    lookahead = [token(a) for a in seq[elem_i + 1:hi + 1]]
    return backtrack, lookahead


def _signifier_rules_lookups(family: str, key: str, layouts: list[dict] = geometry.LAYOUTS,
                              engines: dict[str, anchors.AnchorEngine] = _ENGINES
                              ) -> tuple[list["_Rule"], dict[int, list["_Rule"]]]:
    """`engine.centering_mode == "additive_lookups"` counterpart to
    _signifier_rules: instead of one lookup with a literal pre-summed total
    per (presence-combo x identity-bucket x element), returns a stacking
    rule-list (raw, uncentered positions, context trimmed to each element's
    own transitive dependency closure -- so combos that don't change an
    element's closure collapse into identical, deduplicated rules) plus one
    rule-list per vertical_center_order rank with a nonzero per_rank
    contribution (each rule just adds that one rank's contribution to one
    element, whenever that rank has a present member -- see
    ACCUM_LOOKUPS_PLAN.md). GPOS's own cross-lookup accumulation (spec:
    "adjustments are accumulated as each lookup is processed") does the
    summing that a single literal-total rule used to do in Python.

    Returns (stack_rules, {rank_index: [rules, ...]}) -- gen_dynamic_gpos
    renders each into its own `lookup` block."""
    engine = _engine_for_key(key, layouts, engines)
    right_token = classes.signifier_token(family, key)
    right_glyph = signifiers.KEY_TO_GLYPH[key]
    flat_optional = engine.flat_optional
    buckets = identity.area_glyph_buckets({"relationships": engine.relationships})

    stack_seen: set[tuple] = set()
    stack_rules: list[_Rule] = []
    center_rules: dict[int, list[_Rule]] = {
        i: [] for i, c in enumerate(engine.centering_per_rank) if c
    }
    center_seen: dict[int, set[tuple]] = {i: set() for i in center_rules}

    for combo in itertools.product((True, False), repeat=len(flat_optional)):
        present = dict(zip(flat_optional, combo))
        seq = [e["area"] for e in engine.order if not e["optional"] or present.get(e["area"])]
        seq_index = {area: i for i, area in enumerate(seq)}
        pivot_i = seq_index[engine.pivot]
        to_resolve = {e for e in flat_optional if present.get(e)} | engine.always_present
        chosen = chain._choose_relationships(engine, present, to_resolve)

        resolved_elems: set[str] | None = None
        for identity_choice in _identity_choices(present, buckets):
            present_glyphs = {engine.pivot: right_glyph}
            present_glyphs.update({a: g for a, g in identity_choice.items() if g is not None})

            def token(area: str, _choice=identity_choice) -> str:
                if area == engine.pivot:
                    return right_token
                if area in _choice:
                    glyph = _choice[area]
                    if glyph is None:
                        return classes.area_glyph_other_token(engine.name, area)
                    return classes.area_glyph_token(engine.name, area, glyph)
                if area in classes._CLASSIC_BASE_AREAS:
                    return f"@area_{area}"
                return classes.repeated_area_token(area)

            positions = chain.resolve(engine, present, present_glyphs, center=False)
            if resolved_elems is None:
                # Which of to_resolve actually resolve is identity-
                # independent -- identity.area_glyph_buckets only ever
                # creates a None/catch-all identity_choice branch when an
                # unconditional gap entry guarantees resolvability, so
                # resolvability can't differ across identity_choice
                # variants of the same combo (see ACCUM_LOOKUPS_PLAN.md).
                resolved_elems = set(positions)

            for elem in to_resolve:
                if elem in ("string_top", "string_bottom"):
                    continue  # handled below, alongside "string"
                if elem not in positions:
                    continue  # always-present element that opted out (e.g. non-li string_top)
                elem_i = seq_index[elem]
                keep = {seq_index[a] for a in _closure(chosen, elem)} | {pivot_i}
                backtrack, lookahead = _span_tokens(seq, elem_i, keep, token)
                x, y = positions[elem]
                rule = _Rule(backtrack, token(elem), x, y, lookahead)
                rkey = _rule_key(rule)
                if rkey not in stack_seen:
                    stack_seen.add(rkey)
                    stack_rules.append(rule)

            # li's double-string case, mirroring _signifier_rules exactly:
            # string_top/string_bottom occupy the SAME sequence slot
            # "string" does (not a separate `order` entry, see
            # geometry.py), so they aren't in `seq` at all -- borrow
            # "string"'s own slot/context instead.
            if "string" in positions and "string_top" in positions and "string_bottom" in positions:
                str_i = seq_index["string"]
                keep = {seq_index[a] for a in _closure(chosen, "string_top")} | {pivot_i}
                backtrack, _ = _span_tokens(seq, str_i, keep, token)
                keep_bottom = {seq_index[a] for a in _closure(chosen, "string_bottom")} | {pivot_i}
                _, lookahead_after_string = _span_tokens(seq, str_i, keep_bottom, token)
                top_x, top_y = positions["string_top"]
                bottom_x, bottom_y = positions["string_bottom"]
                rules_here = [
                    _Rule(backtrack, "@area_string_top", top_x, top_y,
                          ["@area_string_bottom"] + lookahead_after_string),
                    _Rule(backtrack + ["@area_string_top"], "@area_string_bottom",
                          bottom_x, bottom_y, lookahead_after_string),
                ]
                for rule in rules_here:
                    rkey = _rule_key(rule)
                    if rkey not in stack_seen:
                        stack_seen.add(rkey)
                        stack_rules.append(rule)

        # Centering rules: identity-independent (per_rank contributions
        # never vary by glyph), so generated once per combo, not per
        # identity_choice -- see _generic_token.
        present_for_centering = {**present, **{e: True for e in engine.always_present}}
        for rank_i, contribution in enumerate(engine.centering_per_rank):
            if not contribution or rank_i not in center_rules:
                continue
            rank = engine.vertical_center_order[rank_i]
            trigger_members = [e for e in rank if present_for_centering.get(e)]
            if not trigger_members:
                continue
            trigger_indices = {seq_index[e] for e in trigger_members}
            for target in resolved_elems or ():
                if target in ("string_top", "string_bottom"):
                    continue  # ride along with "string"'s own rule below
                target_i = seq_index[target]
                keep = trigger_indices | {pivot_i}
                backtrack, lookahead = _span_tokens(
                    seq, target_i, keep, lambda a: _generic_token(engine, right_token, a))
                rule = _Rule(backtrack, _generic_token(engine, right_token, target),
                             0, contribution, lookahead)
                rkey = _rule_key(rule)
                if rkey not in center_seen[rank_i]:
                    center_seen[rank_i].add(rkey)
                    center_rules[rank_i].append(rule)
            if "string_top" in (resolved_elems or ()) and "string_bottom" in resolved_elems:
                str_i = seq_index["string"]
                keep = trigger_indices | {pivot_i}
                backtrack, lookahead = _span_tokens(
                    seq, str_i, keep, lambda a: _generic_token(engine, right_token, a))
                rules_here = [
                    _Rule(backtrack, "@area_string_top", 0, contribution,
                          ["@area_string_bottom"] + lookahead),
                    _Rule(backtrack + ["@area_string_top"], "@area_string_bottom",
                          0, contribution, lookahead),
                ]
                for rule in rules_here:
                    rkey = _rule_key(rule)
                    if rkey not in center_seen[rank_i]:
                        center_seen[rank_i].add(rkey)
                        center_rules[rank_i].append(rule)

    stack_rules.sort(key=lambda r: -r.specificity)
    for rules_here in center_rules.values():
        rules_here.sort(key=lambda r: -r.specificity)
    return stack_rules, center_rules


def gen_dynamic_gpos(layouts: dict, right_keys: tuple[str, ...] = geometry.RIGHT_KEYS) -> list[str]:
    """Entry point genfea.py calls. `layouts` is accepted for interface
    parity with jzpbuild.gpos.gen_gpos but unused -- this prototype's
    geometry lives entirely in geometry.py, not inputs/layouts.json.
    """
    del layouts  # unused, see docstring

    rules: list[_Rule] = []
    stack_rules: list[_Rule] = []
    # {(layout_name, rank_index): [rules]} -- one accumulating GPOS lookup
    # per entry, see _signifier_rules_lookups.
    center_rules: dict[tuple[str, int], list[_Rule]] = {}
    for layout in geometry.LAYOUTS:
        engine = _ENGINES[layout["name"]]
        for key in layout["selector"].get("contains", ()):
            family = signifiers.family_for_key(key)
            if family is not None:
                # A RIGHT_SELECTORS family (gou/io/li/...) -- `right_keys`
                # is genfea.py's opt-in list for that specific system;
                # respect it same as always.
                if family not in right_keys:
                    continue
            # else: this key isn't part of the RIGHT_SELECTORS/family
            # system at all (e.g. cuo's chord keys) -- there's no
            # per-family opt-in/opt-out for it, presence in geometry.LAYOUTS
            # is what turns it on. Fall back to the layout's own name for
            # class-naming/scoping purposes (see _signifier_rules).
            if engine.centering_mode == "additive_lookups":
                key_stack, key_center = _signifier_rules_lookups(family or layout["name"], key)
                stack_rules += key_stack
                for rank_i, rank_rules in key_center.items():
                    center_rules.setdefault((layout["name"], rank_i), []).extend(rank_rules)
            else:
                rules += _signifier_rules(family or layout["name"], key)

    # The one case with no right-hand glyph at all: bare area_fy, nothing
    # else. Safe as a zero-context (always-matches) rule specifically
    # because it sorts last (specificity 0) -- every other rule that could
    # apply to an actual "fy + more" sequence, including the blocker
    # below, is strictly more specific and tried first. Resolved against
    # "default_jzp" specifically -- once a second LAYOUTS entry with its
    # own area_fy exists, this may need to become per-layout too. Guarded
    # on "default_jzp" actually being loaded -- e.g. a geometry.LAYOUTS
    # swapped out entirely for a different topology set (no area_fy
    # anywhere) has no bare-fy case to speak of.
    if "default_jzp" in _ENGINES:
        fx, fy = chain.bare_fy(_ENGINES["default_jzp"])
        rules.append(_Rule([], "@area_fy", fx, fy, []))

    # Blocks area_fy's positioning from leaking into words that aren't
    # actually gou/io/li: any word where area_fy is immediately followed
    # by hui/left/jc/zhu (i.e. this is really a "blank"/other-family word
    # that classic's own layout_blank/layout_<other> rules already
    # position for real -- see README.md) or directly by another family's
    # right-hand glyph. Every genuine rule above requires its own
    # per-signifier class (disjoint from this blocker class, and a subset
    # of the classic per-family class this blocker uses) somewhere in its
    # own lookahead, so it's always at least as specific and never
    # shadowed by this blocker.
    rules.append(_Rule([], "@area_fy", 0, 0, ["@area_fy_blocker"]))

    rules.sort(key=lambda r: -r.specificity)

    other_families = [f for f in config.RIGHT_KEYS if f not in right_keys]
    other_right_class = " ".join(f"@area_right__{f}" for f in other_families)
    class_lines = [
        f"@area_right_other = [ {other_right_class} ];",
        "@area_fy_blocker = [ @area_left @area_hui @area_jc @area_zhu @area_right_other ];",
    ]

    lines = ["# --- dynamic_positioning: per-signifier word positioning (literal, geometry-derived) ---"]
    lines += classes.gen_signifier_classes()
    lines += classes.gen_area_glyph_classes()
    lines += classes.gen_repeated_area_classes()
    lines += class_lines
    lines.append("lookup dynamic_pos {")
    lines += [r.render() for r in rules]
    lines.append("} dynamic_pos;")

    lookup_names = ["dynamic_pos"]
    if stack_rules:
        lines.append("lookup dynamic_stack {")
        lines += [r.render() for r in stack_rules]
        lines.append("} dynamic_stack;")
        lookup_names.append("dynamic_stack")
    # One small accumulating lookup per (layout, rank) -- see
    # _signifier_rules_lookups and ACCUM_LOOKUPS_PLAN.md. GPOS sums each
    # rank's contribution across lookups (spec: "adjustments are
    # accumulated as each lookup is processed"), reproducing
    # chain._additive_shift's OR-then-sum total without ever baking a
    # whole-word-presence-dependent number into one rule.
    for (layout_name, rank_i), rank_rules in center_rules.items():
        lookup_name = f"dynamic_center_{layout_name}_{rank_i}"
        lines.append(f"lookup {lookup_name} {{")
        lines += [r.render() for r in rank_rules]
        lines.append(f"}} {lookup_name};")
        lookup_names.append(lookup_name)

    lines.append("")
    lines.append("feature kern {")
    lines += [f"  lookup {name};" for name in lookup_names]
    lines.append("} kern;")
    return lines


def _collect_rules(layouts: list[dict],
                    right_keys: tuple[str, ...] = geometry.RIGHT_KEYS) -> dict[object, list[_Rule]]:
    """Every `_Rule` gen_dynamic_gpos would end up emitting for `layouts`
    (same shape as geometry.LAYOUTS, i.e. one parsed layouts_data.json's
    "layouts" list, each entry's own "areas" already filled in from
    area_sizes -- see anchors.AnchorEngine), bucketed by which LOOKUP each
    rule lands in: `"dynamic_pos"` for exact/"additive"-mode layouts (plus
    bare_fy/blocker), `"dynamic_stack"` for every "additive_lookups"-mode
    layout's stacking rules, and one `(layout_name, rank_index)` tuple key
    per that mode's centering lookups. Bucketing matters because the 64KB
    Offset16 ceiling is PER SUBTABLE/lookup, not global -- see
    estimate_dynamic_pos_bytes. Mirrors gen_dynamic_gpos's own rule-
    collection loop, minus the bare_fy/blocker rules' real (x, y)
    (irrelevant to count/size estimation, so left at (0, 0) here rather
    than resolving chain.bare_fy for real), minus sorting and FEA class/
    text rendering entirely. Builds a throwaway engines dict from `layouts`
    instead of touching the real _ENGINES/geometry.LAYOUTS globals, so this
    reflects in-editor/unsaved layouts_data.json edits without a
    save-to-disk + reimport round trip -- shared by count_dynamic_pos_rules
    and estimate_dynamic_pos_bytes below (jzpbuilder-dynamic.html's live
    complexity-warning badge, see devserver.py's /api/dynamic/rule_count),
    and stays cheap enough to call on every edit.
    """
    engines = {layout["name"]: anchors.AnchorEngine(layout) for layout in layouts}
    buckets: dict[object, list[_Rule]] = {"dynamic_pos": []}
    for layout in layouts:
        engine = engines[layout["name"]]
        for key in layout["selector"].get("contains", ()):
            family = signifiers.family_for_key(key)
            if family is not None and family not in right_keys:
                continue
            if engine.centering_mode == "additive_lookups":
                key_stack, key_center = _signifier_rules_lookups(
                    family or layout["name"], key, layouts, engines)
                buckets.setdefault("dynamic_stack", []).extend(key_stack)
                for rank_i, rank_rules in key_center.items():
                    buckets.setdefault((layout["name"], rank_i), []).extend(rank_rules)
            else:
                buckets["dynamic_pos"] += _signifier_rules(family or layout["name"], key, layouts, engines)
    if any(layout["name"] == "default_jzp" for layout in layouts):
        buckets["dynamic_pos"].append(_Rule([], "@area_fy", 0, 0, []))  # bare_fy, see gen_dynamic_gpos
    buckets["dynamic_pos"].append(_Rule([], "@area_fy", 0, 0, ["@area_fy_blocker"]))  # fy_blocker
    return buckets


def count_dynamic_pos_rules(layouts: list[dict], right_keys: tuple[str, ...] = geometry.RIGHT_KEYS) -> int:
    """Total `pos` statements gen_dynamic_gpos would emit across every
    lookup for `layouts` -- see _collect_rules.

    On its own this is a WEAK overflow predictor: two layouts_data.json
    revisions with 17,431 and 8,722 rules respectively both overflowed a
    real build (OTLOffsetOverflowError, "All candidates overflowed") --
    what actually overflows is total SUBTABLE BYTES in one Lookup (a hard
    64KB ceiling, 16-bit offsets), which depends on each rule's
    backtrack+lookahead length just as much as rule count -- a "chords"-
    style layout with long per-rule context chains can overflow at a
    fraction of the rule count a "default_jzp"-style layout (short chains)
    would need. See estimate_dynamic_pos_bytes, the actually-predictive
    metric; this is kept only as a secondary, human-readable number for the
    UI (see devserver.py's /api/dynamic/rule_count response).
    """
    return sum(len(rules) for rules in _collect_rules(layouts, right_keys).values())


# Per-rule byte estimate for one ChainContextPos format-3 subtable (what
# feaLib compiles every dynamic_pos `pos ... ' ...;` statement to): a
# 2-byte Offset16 per backtrack/input/lookahead glyph-class Coverage table,
# plus a fixed ~12 bytes of subtable header (format, 3x glyph-count fields,
# 1x PosLookupRecord -- always exactly one marked/input position here).
# Deliberately does NOT add each Coverage table's own payload bytes (glyph
# lists) -- those are real but small relative to the offset table for this
# codebase's class sizes, and would need per-class dedup logic to estimate
# correctly (fontTools shares one Coverage table across every rule
# referencing the same class) -- so this is a LOWER BOUND, calibrated
# against two known real data points: a working ~863-rule layouts_data.json
# estimated at ~17KB (well under the 64KB ceiling, and did build), and an
# overflowing ~8,722-rule one estimated at ~208KB (see count_dynamic_pos_rules's
# docstring) -- both consistent with "closer to 64KB = closer to failing,"
# even though this estimate isn't exact.
_BYTES_PER_CONTEXT_TOKEN = 2
_SUBTABLE_OVERHEAD_BYTES = 12
GPOS_LOOKUP_OFFSET_CEILING_BYTES = 65536  # Offset16 -- the real hard limit


def _lookup_bytes(rules: list[_Rule]) -> int:
    return sum((r.specificity + 1) * _BYTES_PER_CONTEXT_TOKEN + _SUBTABLE_OVERHEAD_BYTES for r in rules)


def estimate_dynamic_pos_bytes(layouts: list[dict], right_keys: tuple[str, ...] = geometry.RIGHT_KEYS) -> int:
    """Estimated subtable bytes of the LARGEST single lookup gen_dynamic_gpos
    would emit for `layouts` -- see _collect_rules and the
    _BYTES_PER_CONTEXT_TOKEN/_SUBTABLE_OVERHEAD_BYTES comment above for the
    estimation method and its known slight-underestimate bias. Compare
    against GPOS_LOOKUP_OFFSET_CEILING_BYTES -- this is the metric that
    actually predicts real-build overflow, unlike raw rule count. The
    ceiling is PER LOOKUP (each compiles to its own subtable), so once a
    layout splits into multiple lookups (additive_lookups mode -- see
    _signifier_rules_lookups), what matters is the worst single one, not
    the sum across all of them."""
    buckets = _collect_rules(layouts, right_keys)
    return max((_lookup_bytes(rules) for rules in buckets.values()), default=0)
