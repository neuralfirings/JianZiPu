"""Generate the GSUB half of the feature file (classes + substitution lookups).

The goal is semantic equivalence with the previously hand-maintained
src-fontforge/input/fontForgeFeatures.fea: every glyph class and
substitution rule is derived from components.csv, glyphRename.csv, and
algorithmic hui/decimal matrices. Hand-written disambiguation rules live in
inputs/edge_cases.fea and are included verbatim.

Rule ORDER within the hui lookups is load-bearing (a 2-token hui like
`one one` must be tried before its 1-token prefix `one`); hui_sequence()
below is the one place that order is spelled out.
"""

from . import config
from .data import (
    GlyphRow, load_components, load_char_to_glyph_name_rows, resolve_char_to_glyph_name,
)
from .validate import validate_or_raise

# ---------------------------------------------------------------------------
# static configuration that is not derivable from the CSV

# ASCII digit glyph names
DIGIT = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
         6: "six", 7: "seven", 8: "eight", 9: "nine"}

# hui number -> ascii glyph token sequence
def hui_ascii(n: int) -> str:
    if n <= 9:
        return DIGIT[n]
    return f"one {DIGIT[n - 10]}"

# hui number -> Chinese ch_* glyph token sequence
def hui_ch(n: int) -> str:
    if n <= 10:
        return f"ch_{n}"
    return f"ch_10 ch_{n - 10}"

PERIOD_SUBS = ["ch_period", "ch_dian", "ch_dian_trad", "ch_hui"]


def hui_sequence(spell, wai: str = "ch_wai", last: int = 10) -> list[tuple[str, int]]:
    """(input token sequence, hui number) pairs in the order every hui lookup
    enumerates them: 11-13 first (so they aren't shadowed by their shorter
    1-token prefixes), then 外 as 13, then 1..`last`. `spell` renders one
    hui number as tokens (hui_ascii, hui_ch, ...); `wai` is 外's own glyph
    in the same spelling system."""
    return ([(spell(h), h) for h in (11, 12, 13)] + [(wai, 13)]
            + [(spell(h), h) for h in range(1, last + 1)])


def decimals(spell) -> list[tuple[str, int]]:
    """(decimal token, md_* suffix) for the decimals 1..9 plus 半 (= .5)."""
    return [(spell(d), d) for d in range(1, 10)] + [("ch_ban", 5)]


def hui_class_glyphs(rows: list[GlyphRow]) -> list[str]:
    base = [r.glyph_name for r in rows if r.in_area("area_hui")]
    decimals = []
    for n in range(1, 14):
        decimals.append(f"md_{n}.blank")
        decimals.extend(f"md_{n}.{d}" for d in range(1, 10))
    return base + decimals + ["blank"]


def area_glyphs(rows: list[GlyphRow], col: str) -> list[str]:
    return [r.glyph_name for r in rows if r.in_area(col)]


def all_component_glyphs(rows: list[GlyphRow]) -> list[str]:
    """Everything that can appear inside a composed word (@area_wild)."""
    names = {r.glyph_name for r in rows}
    for n in range(1, 14):
        names.add(f"md_{n}.blank")
        names.update(f"md_{n}.{d}" for d in range(1, 10))
    names.update(["blank", "blank_bar", "blank_colon"])
    return sorted(names)


# ---------------------------------------------------------------------------
# class definitions


def gen_classes(rows: list[GlyphRow]) -> list[str]:
    hui = hui_class_glyphs(rows)
    char_glyphs = area_glyphs(rows, "area_char")
    vert_pairs = [(r.glyph_name, r.vert_variant) for r in rows if r.vert_variant]
    lines = [
        "# base classes (generated from components.csv)",
        f"  @area_fy = [ {' '.join(area_glyphs(rows, 'area_fy'))} ];",
        f"  @area_left = [ {' '.join(area_glyphs(rows, 'area_left'))} ];",
        f"  @area_hui = [ {' '.join(hui)} ];",
        f"  @area_jc = [ {' '.join(area_glyphs(rows, 'area_mod_jc'))} ];",
        f"  @area_zhu = [ {' '.join(area_glyphs(rows, 'area_mod_zhu'))} ];",
        f"  @area_right_all = [ {' '.join(area_glyphs(rows, 'area_right'))} ];",
        f"  @area_string = [ {' '.join(area_glyphs(rows, 'area_string'))} ];",
        "",
        "  @area_cuo_bar = [ blank_bar ];",
        "  @area_left_rt = @area_left;",
        "  @area_hui_rt = @area_hui;",
        "  @area_jc_rt = @area_jc;",
        "  @area_zhu_rt = @area_zhu;",
        "  @area_string_rt = @area_string;",
        "  @area_string_top = @area_string;",
        "  @area_string_bottom = @area_string;",
        "",
        f"  @area_period_subs = [ {' '.join(PERIOD_SUBS)} ];",
        "",
        "  @area_char_colon = [ blank_colon ];",
        f"  @area_char = [ {' '.join(char_glyphs)} ];",
    ]
    for i in (1, 2, 3, 4):
        lines += [
            f"  @area_char{i} = @area_char;",
            f"  @area_left_{i} = @area_left;",
            f"  @area_hui_{i} = @area_hui;",
        ]
    lines += [
        "",
        "  # vert-mode conversions: left-aligned glyph -> centered variant when in char layout",
        f"  @area_to_md_for_vert_from = [ {' '.join(p[0] for p in vert_pairs)} ];",
        f"  @area_to_md_for_vert_to =   [ {' '.join(p[1] for p in vert_pairs)} ];",
        "",
        f"  @area_wild = [ {' '.join(all_component_glyphs(rows))} ];",
        "",
        "  # right-hand technique selectors (one layout family each)",
    ]
    for key, members in config.RIGHT_SELECTORS.items():
        lines.append(f"  @area_right__{key} = [ {' '.join(members)} ];")
    lines += [
        f"  @area_chord__cuo = [ {' '.join(area_glyphs(rows, 'area_chord'))} ];",
        "",
        "  # special characters",
        "  @new_word_char = [ numbersign blank_colon ];",
        "  @space_char = [ space advance ];",
    ]
    return lines


# ---------------------------------------------------------------------------
# symbol (ASCII digit) lookups


def gen_s2j_lat_ch_period_liga() -> list[str]:
    """<ascii hui> <period-like char> <ascii decimal> -> md_H.D (e.g. 7点6)."""
    lines = ["lookup s2j_lat_ch_period_liga {"]
    for dd, target in decimals(DIGIT.__getitem__):
        parts = [f"sub {tok} @area_period_subs {dd} by md_{h}.{target};"
                 for tok, h in hui_sequence(hui_ascii)]
        lines.append("  " + "  ".join(parts))
    lines.append("} s2j_lat_ch_period_liga;")
    return lines


def gen_s2j_liga() -> list[str]:
    lines = ["lookup s2j_liga {", "  # decimal liga"]
    for h in range(1, 14):
        parts = [f"sub {hui_ascii(h)} period by md_{h}.blank;"]
        parts += [f"sub {hui_ascii(h)} period {DIGIT[d]} by md_{h}.{d};" for d in range(1, 10)]
        lines.append("  " + " ".join(parts))
    lines += [
        "",
        "  # whole hui liga",
        "  sub one comma by md_1; # :1,3 (one three) v. :13 (thirteen)",
        "  sub one zero by md_10;",
        "  sub one one by md_11;",
        "  sub one two by md_12;",
        "  sub one three plus by md_wai;",
        "  sub one three by md_13;",
        "} s2j_liga;",
    ]
    return lines


def gen_s2j_single() -> list[str]:
    return [
        "lookup s2j_single {",
        "  sub [  zero one two three four five six seven eight nine ]",
        "    by [ md_san md_1 md_2 md_3 md_4 md_5 md_6 md_7 md_8 md_9 ];",
        "  sub slash by mod_chuo;",
        "  sub backslash by mod_zhu;",
        "  sub greater by mod_ji;",
        "  sub asterisk by md_placeholder;",
        "} s2j_single;",
    ]


# ---------------------------------------------------------------------------
# latin lookups


def spell_latin(key: str) -> str:
    """'zhi4' -> 'z h i four' (letters stay letters, digits become names)."""
    return " ".join(DIGIT[int(c)] if c.isdigit() else c for c in key)


def latin_entries(rows: list[GlyphRow]) -> dict[str, str]:
    """latin spelling -> glyph, deduped: non-area_char rows win.

    The area_char duplicates (md_lun, md_banlun, md_yan, md_jiu2, ...) are the
    centered vert-mode variants; they are reached via @area_to_md_for_vert
    conversion, not by direct input, so the lg_*/original glyph wins the key.
    """
    entries: dict[str, tuple[str, bool]] = {}  # key -> (glyph, is_char_row)
    for r in rows:
        keys = []
        if r.latin:
            keys.append(r.latin)
        if r.latin_alt:
            keys.append(r.latin_alt)
        # uppercase multi-letter chord keys live in the `common` column
        if r.common and len(r.common) > 1 and r.common.isalpha():
            keys.append(r.common)
        is_char = r.in_area("area_char") and len(r.areas) == 1
        for k in keys:
            if k not in entries or (entries[k][1] and not is_char):
                entries[k] = (r.glyph_name, is_char)
    return {k: g for k, (g, _) in entries.items()}


def gen_l2j_liga(rows: list[GlyphRow]) -> list[str]:
    entries = latin_entries(rows)
    multi = [(k, g) for k, g in entries.items() if len(k) > 1]
    # longest first so greedy ligature matching prefers the longer spelling
    multi.sort(key=lambda kg: -len(kg[0]))
    lines = ["lookup l2j_liga {"]
    lines += [f"  sub {spell_latin(k)} by {g};" for k, g in multi]
    lines.append("} l2j_liga;")
    return lines


def gen_l2j_single(rows: list[GlyphRow]) -> list[str]:
    entries = latin_entries(rows)
    single = [(k, g) for k, g in entries.items() if len(k) == 1 and k.isalpha()]
    lines = ["lookup l2j_single {"]
    lines += [f"  sub {k} by {g};" for k, g in single]
    lines.append("} l2j_single;")
    return lines


# ---------------------------------------------------------------------------
# Chinese lookups


def gen_c2j_char_symbols() -> list[str]:
    return [
        "lookup c2j_char_symbols {",
        "  sub [ ch_bracketleft ch_bracketright ch_comma ch_colon ch_bar ]",
        "  by [ bracketleft bracketright comma colon bar ];",
        "} c2j_char_symbols;",
    ]


def gen_c2j_char_left(rows: list[GlyphRow], c2g: dict[str, str]) -> list[str]:
    lines = ["lookup c2j_char_left { # this way, 名七五 is interpreted as s7.5"]
    for r in rows:
        if r.in_area("area_left") and r.simplified:
            lines.append(
                f"  sub {c2g[r.simplified]} by {r.glyph_name}; "
                f"# {c2g[r.simplified]}={r.simplified}")
    lines.append("} c2j_char_left;")
    return lines


def gen_c2j_char_deci_period_liga() -> list[str]:
    """Chinese hui + period-like char (+ optional Chinese decimal)."""
    lines = ["lookup c2j_char_deci_period_liga {"]
    # bare hui + period char (十二徽 -> md_12)
    parts = [f"sub {tok} @area_period_subs by md_{h};" for tok, h in hui_sequence(hui_ch)]
    lines.append("  " + "  ".join(parts))
    # hui + period char + decimal (十点二 -> md_10.2)
    for dd, target in decimals(hui_ch):
        parts = [f"sub {tok} @area_period_subs {dd} by md_{h}.{target};"
                 for tok, h in hui_sequence(hui_ch)]
        lines.append("  " + "  ".join(parts))
    lines.append("} c2j_char_deci_period_liga;")
    return lines


def gen_c2j_char_deci_liga_parts() -> list[str]:
    """Safari-compatible multi-step Chinese decimal ligatures.

    Safari can't handle `a b' c' -> d` contextual ligatures, only
    `a b c' -> d`, so hui+decimal collapses in two steps: first the decimal
    glyph absorbs the pair meaning (part1), then the leftover hui glyph is
    merged away (part2). ch_10 alone ("十二" = 10+2 vs 12) needs its own
    pass (parts 3/4) so that 十一/十二/十三 aren't shadowed.
    """
    # ch_10 is left out of parts 1/2 (last=9) and handled in parts 3/4 --
    # here it would shadow 十一/十二/十三.
    lines = ["lookup c2j_char_deci_liga_part1 {"]
    for dd, target in decimals(hui_ch):
        parts = [f"sub @area_left {tok} {dd}' by md_{h}.{target};"
                 for tok, h in hui_sequence(hui_ch, last=9)]
        lines.append("  " + "  ".join(parts))
    lines.append("} c2j_char_deci_liga_part1;")

    lines.append("lookup c2j_char_deci_liga_part2 {")
    for d in range(1, 10):
        parts = [f"sub {tok} md_{h}.{d} by md_{h}.{d};" for tok, h in hui_sequence(hui_ch, last=9)]
        lines.append("  " + "  ".join(parts))
    lines.append("} c2j_char_deci_liga_part2;")

    lines.append("lookup c2j_char_deci_liga_part3 {")
    for dd, target in decimals(hui_ch):
        lines.append(f"  sub @area_left ch_10 {dd}' by md_10.{target};")
    lines.append("} c2j_char_deci_liga_part3;")

    lines.append("lookup c2j_char_deci_liga_part4 {")
    for d in range(1, 10):
        lines.append(f"  sub ch_10 md_10.{d} by md_10.{d};")
    lines.append("} c2j_char_deci_liga_part4;")
    return lines


def chinese_entries(rows: list[GlyphRow], col: str) -> dict[str, str]:
    """Chinese spelling -> glyph for the given column, non-area_char rows win."""
    entries: dict[str, tuple[str, bool]] = {}
    for r in rows:
        key = getattr(r, col)
        if not key:
            continue
        is_char = r.in_area("area_char") and len(r.areas) == 1
        if key not in entries or (entries[key][1] and not is_char):
            entries[key] = (r.glyph_name, is_char)
    return {k: g for k, (g, _) in entries.items()}


# Chinese number spellings handled by the deci lookups, not the generic ones
CH_NUMERIC = {"一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
              "十一", "十二", "十三", "外", "就", "半", "散"}


def gen_c2j_liga(rows: list[GlyphRow], c2g: dict[str, str], col: str, name: str) -> list[str]:
    entries = chinese_entries(rows, col)
    lines = [f"lookup {name} {{"]
    # 十一/十二/十三 must still ligate to md_11/12/13 ahead of single 十
    if col == "simplified":
        for key in ("十一", "十三", "十二"):
            names = " ".join(c2g[c] for c in key)
            note = " ".join(f"{c2g[c]}={c}" for c in key)
            lines.append(f"  sub {names} by {entries.pop(key)}; # {note}")
    for key, glyph in entries.items():
        if len(key) > 1 and key not in CH_NUMERIC:
            names = " ".join(c2g[c] for c in key)
            note = " ".join(f"{c2g[c]}={c}" for c in key)
            lines.append(f"  sub {names} by {glyph}; # {note}")
    lines.append(f"}} {name};")
    return lines


def gen_c2j_single(rows: list[GlyphRow], c2g: dict[str, str], col: str, name: str) -> list[str]:
    # left-hand chars (名中食大跪) are handled earlier by c2j_char_left
    left_keys = {getattr(r, col) for r in rows if r.in_area("area_left")}
    entries = chinese_entries(rows, col)
    lines = [f"lookup {name} {{"]
    for key, glyph in entries.items():
        if len(key) == 1 and key not in left_keys:
            lines.append(f"  sub {c2g[key]} by {glyph}; # {c2g[key]}={key}")
    lines.append(f"}} {name};")
    return lines


# ---------------------------------------------------------------------------
# md-glyph number lookups (post-conversion, shared by ASCII and Chinese input)


def gen_char_deci_liga_parts() -> list[str]:
    """hui-glyph + string-glyph collapse (s7 5 -> s7.5) in Safari-safe steps."""
    md_hui = "md_{}".format
    lines = ["lookup char_deci_liga_part1 {"]
    for d in range(1, 10):
        parts = [f"sub @area_left {tok} md_{d}' by md_{h}.{d};"
                 for tok, h in hui_sequence(md_hui, wai="md_wai")]
        lines.append("  " + "  ".join(parts))
    lines.append("} char_deci_liga_part1;")

    lines.append("lookup char_deci_liga_part2 {")
    for d in range(1, 10):
        parts = [f"sub {tok} md_{h}.{d} by md_{h}.{d};" for tok, h in hui_sequence(md_hui, wai="md_wai")]
        lines.append("  " + "  ".join(parts))
    lines.append("} char_deci_liga_part2;")
    return lines


def gen_hui_and_commas(rows: list[GlyphRow]) -> list[str]:
    """A comma after a hui glyph is consumed (s7,5 = hui 7 + string 5).

    Must be spelled out per glyph: `sub @area_hui comma by @area_hui;`
    doesn't work.
    """
    lines = ["lookup hui_and_commas {"]
    parts = [f"sub {g} comma by {g};" for g in hui_class_glyphs(rows)]
    lines.append("  " + " ".join(parts))
    lines += [
        "  # special case for :名九，半轮六 otherwise it would get s9.5 (wrong) instead of s9 (right)",
        "  sub comma md_banlun by md_banlun;",
        "  sub comma lg_banlun by lg_banlun;",
        "} hui_and_commas;",
    ]
    return lines


# ---------------------------------------------------------------------------
# feature block


def gen_liga_feature() -> list[str]:
    wild_repeat = lambda n: " ".join(["@area_wild"] * n)
    lines = [
        "feature liga {",
        "  # for showing correctly in font pickers",
        "  sub J lg_ti' a lg_pi Z lg_ti P lg_tiao by i;",
        "  sub J i a lg_pi' Z lg_ti P lg_tiao by n;",
        "  sub J i a n Z lg_ti' P lg_tiao by i;",
        "  sub J i a n Z i P lg_tiao' by u;",
        "",
        "  # some special symbols",
        "  sub underscore by blank;",
        "  sub bar by blank_bar;",
        "  sub colon by blank_colon;",
        "  sub asterisk by md_placeholder; # not sure why but this doesn't work when inside lookup",
        "  sub plus by advance; # for music programs where space separates words per note",
        "",
        "  # special cases (hand-maintained, see edge_cases.fea)",
        "  lookup lat_zhi4_sub;",
        "  lookup ch_dc_sub;",
        "",
        "  # common inputs",
        "  lookup s2j_lat_ch_period_liga; # 7点6",
        "  lookup s2j_liga; # 7.6",
        "  lookup s2j_single; # > /",
        "",
        "  # chinese input",
        "  lookup c2j_char_symbols;",
        "  lookup c2j_char_left;",
        "  lookup c2j_char_deci_period_liga;",
        "  lookup c2j_char_deci_liga_part1;",
        "  lookup c2j_char_deci_liga_part2;",
        "  lookup c2j_char_deci_liga_part3;",
        "  lookup c2j_char_deci_liga_part4;",
        "  lookup c2j_char_liga;",
        "  lookup c2j_trad_liga;",
        "  lookup c2j_char_single;",
        "  lookup c2j_trad_single;",
        "",
        "  # latin input",
        "  lookup l2j_liga;",
        "  lookup l2j_single;",
        "",
        "  # numbers",
        "  lookup hui_and_commas;",
        "  lookup char_deci_liga_part1;",
        "  lookup char_deci_liga_part2;",
        "",
        "  # vert mode: convert to centered variants when following colon",
    ]
    for n in range(6, -1, -1):
        ctx = f" {wild_repeat(n)}" if n else ""
        lines.append(f"  sub blank_colon{ctx} @area_to_md_for_vert_from' by @area_to_md_for_vert_to;")
    lines += [
        "",
        "  sub comma by NULL; # removes all remaining commas",
        "} liga;",
    ]
    return lines


# ---------------------------------------------------------------------------


def gen_gsub() -> list[str]:
    rows = load_components()
    validate_or_raise(rows, load_char_to_glyph_name_rows())
    c2g = resolve_char_to_glyph_name(rows)
    edge_cases = config.EDGE_CASES_FEA.read_text().splitlines()

    sections = [
        ["languagesystem DFLT dflt;",
         "languagesystem hani dflt;",
         "languagesystem latn dflt;", ""],
        gen_classes(rows), [""],
        edge_cases, [""],
        gen_s2j_lat_ch_period_liga(),
        gen_s2j_liga(),
        gen_s2j_single(), [""],
        gen_l2j_liga(rows),
        gen_l2j_single(rows), [""],
        gen_c2j_char_symbols(),
        gen_c2j_char_left(rows, c2g),
        gen_c2j_char_deci_period_liga(),
        gen_c2j_char_deci_liga_parts(),
        gen_c2j_liga(rows, c2g, "simplified", "c2j_char_liga"),
        gen_c2j_liga(rows, c2g, "traditional", "c2j_trad_liga"),
        gen_c2j_single(rows, c2g, "simplified", "c2j_char_single"),
        gen_c2j_single(rows, c2g, "traditional", "c2j_trad_single"), [""],
        gen_char_deci_liga_parts(),
        gen_hui_and_commas(rows), [""],
        gen_liga_feature(),
    ]
    out = []
    for s in sections:
        out.extend(s)
    return out
