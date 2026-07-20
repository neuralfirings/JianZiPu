"""Generate the GPOS half of the feature file (glyph positioning).

Each composed JZP word is laid out by contextual single-position rules: a rule
matches the sequence of area classes that make up a word shape and moves the
marked glyph to its area's x/y for the active layout. Layout geometry comes
from layouts.json (derived from Figma).

Rules are plain token lists: "@area_left'" positions the left-hand glyph
(trailing apostrophe = marked), "@area_left" is context. The marked token's
area name (with any "__variant" suffix stripped) is looked up in the active
layout to produce the `<x yd 0 0>` value record — replicating what
`scripts.cjs --add-positions` used to do with the `<>` placeholders.

Rule ORDER is load-bearing: within the lookup, earlier rules win for a given
glyph, and several fallbacks (e.g. bare @area_hui at the very end) rely on
being last. Don't reorder blocks casually.
"""

from . import config

Rule = list  # of str tokens; trailing "'" marks the positioned glyph


class FillError(Exception):
    pass


def _lh_combos(jc: bool) -> list[list[str]]:
    """The (left||hui) presence combinations, in canonical order."""
    tail = ["@area_jc"] if jc else []
    return [
        ["@area_left", "@area_hui"] + tail,
        ["@area_left"] + tail,
        ["@area_hui"] + tail,
    ]


def word_layout_rules(right: str | None, jc: bool,
                      strings: str = "single") -> list[Rule]:
    """Rules for one word layout: fy? (left||hui) jc? zhu? right? string?.

    right: right-hand class suffix ("gou", "li", ...) or None for the blank
    (no right hand) layouts. jc: whether the 急/绰 marker area is part of this
    layout (always present in its rules when so). strings: "single" for one
    string area, "li" for the two-string 历 variant, matching the historical
    rule sets.
    """
    R_ = [f"@area_right__{right}"] if right else []
    rules: list[Rule] = []

    # In the blank (no right hand) layouts the word ends before zhu can
    # follow fy/left/hui/jc, so those groups only have the no-zhu variant.
    head_zhus = (["@area_zhu"], []) if right else ([],)

    # fy' — with zhu, then without
    for zhu in head_zhus:
        for lh in _lh_combos(jc):
            rules.append(["@area_fy'"] + lh + zhu + R_)

    # left'
    for zhu in head_zhus:
        for hui in (["@area_hui"], []):
            rules.append(["@area_left'"] + hui + (["@area_jc"] if jc else []) + zhu + R_)

    # hui'
    for zhu in head_zhus:
        rule = ["@area_hui'"] + (["@area_jc"] if jc else []) + zhu + R_
        if not jc and not zhu and not R_:
            continue  # bare hui fallback handled separately (blank layouts)
        rules.append(rule)

    # jc'
    if jc:
        for zhu in head_zhus:
            for lh in (["@area_left", "@area_hui"], ["@area_left"], ["@area_hui"]):
                rules.append(lh + ["@area_jc'"] + zhu + R_)

    # zhu'
    for lh in (["@area_left", "@area_hui"], ["@area_left"], ["@area_hui"]):
        rules.append(lh + (["@area_jc"] if jc else []) + ["@area_zhu'"] + R_)

    # right'
    if right:
        for zhu in (["@area_zhu"], []):
            for lh in (["@area_left", "@area_hui"], ["@area_left"], ["@area_hui"]):
                rules.append(lh + (["@area_jc"] if jc else []) + zhu + [f"@area_right__{right}'"])

    # strings
    prefix_combos = []
    for zhu in (["@area_zhu"], []):
        for lh in (["@area_left", "@area_hui"], ["@area_left"], ["@area_hui"]):
            prefix_combos.append(lh + (["@area_jc"] if jc else []) + zhu + R_)
    if strings == "li":
        for p in prefix_combos:
            rules.append(p + ["@area_string_top'", "@area_string_bottom'"])
        # historical quirk: the single-string rules for li2 only cover the
        # with-zhu combos; plain li covers all six
        limit = 3 if jc else 6
        for p in prefix_combos[:limit]:
            rules.append(p + ["@area_string'"])
    else:
        for p in prefix_combos:
            rules.append(p + ["@area_string'"])
    return rules


def no_left_layout_rules(right: str | None, jc: bool = True) -> list[Rule]:
    """The *3 layouts: fy? jc? zhu? right string? — no left hand at all.

    layout_li3 historically has no jc rules (jc=False).
    """
    R_ = [f"@area_right__{right}"] if right else []
    if right:
        rules: list[Rule] = []
        if jc:
            rules += [
                ["@area_fy'", "@area_jc", "@area_zhu"] + R_,
                ["@area_fy'", "@area_jc"] + R_,
            ]
        rules += [
            ["@area_fy'", "@area_zhu"] + R_,
            ["@area_fy'"] + R_,
        ]
        if jc:
            rules += [
                ["@area_jc'", "@area_zhu"] + R_,
                ["@area_jc'"] + R_,
            ]
        rules += [
            ["@area_zhu'"] + R_,
            [f"@area_right__{right}'"],
        ]
        if right == "li":
            rules += [
                R_ + ["@area_string_top'", "@area_string_bottom'"],
                R_ + ["@area_string'"],
            ]
        else:
            rules += [R_ + ["@area_string'"]]
    else:
        # layout_blank3
        rules = [["@area_jc'"], ["@area_zhu'"], ["@area_string'"]]
    return rules


def vert_rules(n: int) -> list[Rule]:
    """layout_vertjzpN: after ':', N stacked rows of (left+hui | one char).

    All rows are positioned by a single rule; every presence combination is
    enumerated in binary-count order (row 1 = least significant bit,
    char = 1).
    """
    rules = []
    if n == 1:
        return [["@area_char_colon", "@area_char1'"]]
    for combo in range(2 ** n):
        rule = ["@area_char_colon"]
        for row in range(1, n + 1):
            if combo & (1 << (row - 1)):
                rule.append(f"@area_char{row}'")
            else:
                rule += [f"@area_left_{row}'", f"@area_hui_{row}'"]
        rules.append(rule)
    return rules


def cuo_rules(anchor: str) -> list[dict]:
    """The 撮 chord segments: anchor is '@area_chord__cuo' (left segment,
    after the chord glyph) or '@area_cuo_bar' (right segment, after '|').

    Returns (layout, rules) blocks; the left/right segments share rule
    structure but read positions from their own layout frames.
    """
    A = anchor
    side = "left" if "chord" in anchor else "right"
    blocks = []
    # common rules (positions from the base cuo layout)
    common: list[Rule] = []
    if side == "left":
        common += [["@area_fy'", A], [A + "'"]]
    common += [
        [A, "@area_left'"],
        [A, "@area_left", "@area_hui'"],
        # 1-7 default to strings; force hui reading before zhu/string (7z7, 77)
        [A, "@area_hui'", "@area_zhu"],
        [A, "@area_hui'", "@area_string"],
    ]
    blocks.append((f"layout_cuo_{side}", common))

    # jc variant ("2" geometry)
    b2: list[Rule] = [
        [A, "@area_left", "@area_hui'", "@area_jc"],
        [A, "@area_hui'", "@area_jc"],
        [A, "@area_left", "@area_hui", "@area_jc'"],
        [A, "@area_hui", "@area_jc'"],
    ]
    for lh in (["@area_left", "@area_hui"], ["@area_left"], ["@area_hui"]):
        b2.append([A] + lh + ["@area_jc", "@area_zhu'"])
    for zhu in (["@area_zhu"], []):
        for lh in (["@area_left", "@area_hui"], ["@area_left"], ["@area_hui"]):
            b2.append([A] + lh + ["@area_jc"] + zhu + ["@area_string'"])
    blocks.append((f"layout_cuo_{side}2", b2))

    # plain variant
    b1: list[Rule] = []
    for lh in (["@area_left", "@area_hui"], ["@area_left"], ["@area_hui"]):
        b1.append([A] + lh + ["@area_zhu'"])
    for zhu in (["@area_zhu"], []):
        for lh in (["@area_left", "@area_hui"], ["@area_left"], ["@area_hui"]):
            b1.append([A] + lh + zhu + ["@area_string'"])
    blocks.append((f"layout_cuo_{side}", b1))

    # no-left-hand variant ("3" geometry)
    b3: list[Rule] = [
        [A, "@area_jc'"],
        [A, "@area_jc", "@area_zhu'"],
        [A, "@area_zhu'"],
        [A, "@area_jc", "@area_zhu", "@area_string'"],
        [A, "@area_jc", "@area_string'"],
        [A, "@area_zhu", "@area_string'"],
        [A, "@area_string'"],
    ]
    blocks.append((f"layout_cuo_{side}3", b3))

    # hui fallback (must come after the *3 string rules)
    blocks.append((f"layout_cuo_{side}2", [[A, "@area_hui'"]]))
    return blocks


# ---------------------------------------------------------------------------
# position filling


def token_area(token: str) -> str:
    """'@area_right__li'' -> 'area_right'; '@area_hui_1'' -> 'area_hui_1'."""
    return token.rstrip("'").lstrip("@").split("__")[0]


def fill_rule(rule: Rule, layout: str, layouts: dict,
              overrides: dict[str, str] | None = None) -> str:
    areas = layouts.get(layout)
    if areas is None:
        raise FillError(f"no geometry for layout {layout}")
    parts = ["pos"]
    for token in rule:
        if token.endswith("'"):
            area = (overrides or {}).get(token.rstrip("'")) or token_area(token)
            p = areas.get(area)
            if p is None:
                raise FillError(f"{layout} has no area {area} (token {token})")
            parts.append(f"{token} <{p['x']} {p['yd']} 0 0>")
        else:
            parts.append(token)
    return " ".join(parts) + ";"


def emit_block(lines: list[str], layout: str, rules: list[Rule],
               layouts: dict, comment: str | None = None,
               overrides: dict[str, str] | None = None) -> None:
    lines.append(f"  # layout: {layout}" + (f" — {comment}" if comment else ""))
    for r in rules:
        lines.append("  " + fill_rule(r, layout, layouts, overrides))


def gen_gpos(layouts: dict) -> list[str]:
    lines = ["lookup jzp_glyph_positioning {"]

    # vertical stacks. Special case first: ':大息' would otherwise be read as
    # 大 = left hand and positioned by a word layout.
    emit_block(lines, "layout_vertjzp2",
               [["@area_char_colon", "md_da'", "md_xi'"]], layouts,
               comment="special case :大息",
               overrides={"md_da": "area_char1", "md_xi": "area_char2"})
    for n in (4, 3, 2, 1):
        emit_block(lines, f"layout_vertjzp{n}", vert_rules(n), layouts)

    # 历 (li) — takes two strings
    emit_block(lines, "layout_li2", word_layout_rules("li", jc=True, strings="li"), layouts)
    emit_block(lines, "layout_li", word_layout_rules("li", jc=False, strings="li"), layouts)
    emit_block(lines, "layout_li3", no_left_layout_rules("li", jc=False), layouts)

    # 撮 chords: left segment then right segment
    for anchor in ("@area_chord__cuo", "@area_cuo_bar"):
        for layout, rules in cuo_rules(anchor):
            emit_block(lines, layout, rules, layouts)

    # the six standard right-hand techniques
    for right in config.RIGHT_KEYS:
        emit_block(lines, f"layout_{right}2", word_layout_rules(right, jc=True), layouts)
        emit_block(lines, f"layout_{right}", word_layout_rules(right, jc=False), layouts)
        emit_block(lines, f"layout_{right}3", no_left_layout_rules(right), layouts)

    # blanks (no right hand)
    emit_block(lines, "layout_blank2", word_layout_rules(None, jc=True), layouts)

    blank_rules = word_layout_rules(None, jc=False)
    # the bare-hui cases need explicit zhu/string context (7z7, 77) and a
    # left-context variant so lone 1-7 can fall through to layout_blank3
    extra = [
        ["@area_left", "@area_hui'"],
        ["@area_hui'", "@area_zhu"],
        ["@area_hui'", "@area_string"],
    ]
    # insert after the left' rules (2 fy-groups of 3, then 2 left rules... )
    emit_block(lines, "layout_blank", blank_rules[:8] + extra + blank_rules[8:], layouts)

    emit_block(lines, "layout_blank3", no_left_layout_rules(None), layouts)

    # final fallback: hui position for 8+ when nothing else matched
    emit_block(lines, "layout_blank", [["@area_hui'"]], layouts,
               comment="hui fallback for 8-13 after string rules")

    lines.append("} jzp_glyph_positioning;")
    lines += ["", "feature kern {", "  lookup jzp_glyph_positioning;", ""]
    # cleanup: hide stray glyphs of half-formed words, and give space its
    # advance back at word boundaries
    for n in range(10, -1, -1):
        wilds = " ".join(["@area_wild"] * n)
        sep = " " if n else ""
        lines.append(f"  pos numbersign {wilds}{sep}@area_wild' <-1000 0 0 0>;")
    for n in range(10, -1, -1):
        wilds = " ".join(["@area_wild"] * n)
        sep = " " if n else ""
        lines.append(f"  pos blank_colon {wilds}{sep}@area_wild' <-1000 0 0 0>;")
    for n in range(10, -1, -1):
        wilds = " ".join(["@area_wild"] * n)
        sep = " " if n else ""
        lines.append(f"  pos @new_word_char {wilds}{sep}@space_char' <0 0 -1000 0>;")
    lines.append("} kern;")
    return lines
