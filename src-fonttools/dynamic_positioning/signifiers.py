"""ASCII-key <-> glyph mapping, derived from components.csv via
jzpbuild.data's existing (shared, read-only) loader -- so plain jzpbuild
(no --dynamic_pos) is unaffected regardless of anything in this file.

Uses GlyphRow.latin rather than the CSV's own "keys" column (which
jzpbuild.data.load_components() doesn't currently load into GlyphRow at
all) -- confirmed identical to "keys" for every right-hand technique row
(lg_gou/lg_da/lg_ti/lg_zhai/lg_li all have keys == latin).

KEY_TO_GLYPH is scoped to _RELEVANT_AREAS, NOT every row in
components.csv -- some input keys are genuinely ambiguous across areas
(e.g. "V"/"jiu"/"lun"/"banlun" each name two DIFFERENT glyphs depending on
whether they're being used in area_right/area_hui or their vert_variant
area_char form; GSUB picks the right one from surrounding context, which
this module has no equivalent of). Add an area to _RELEVANT_AREAS only
after checking (like this module's own test suite/git history did for
area_chord) that it doesn't introduce that kind of collision with what's
already there.

Kept as its own module, separate from both geometry.py (which only
exposes layout data) and classes.py (which needs glyph names for FEA class
emission), so neither has to import the other for this.
"""

import re

from jzpbuild import config, data

# area_right: gou/io/li/loki/nc/tiao/mo's own technique glyphs.
# area_chord: cuo's C/DC/FC chord markers.
# area_left: layout_test's s/d/f pivot glyphs (md_ming/md_zhong/md_shi).
# area_char: layout_test's "middle" pivot glyphs (vertical-mode Han chars) --
# both added for dynamic_positioning/layout_data_sdf.json.
#
# ORDER IS LOAD-BEARING: this is a real collision, not just the theoretical
# risk this module's docstring already warned about -- "V"/"lun"/"banlun"
# each name TWO different glyphs, one row in area_right/area_chord and a
# separate vert_variant row in area_char. KEY_TO_GLYPH below builds
# earlier-listed areas first and never overwrites an already-claimed key,
# so area_right/area_chord's glyphs win those 3 keys, preserving the real
# default_jzp/cuo pipeline's existing behavior; area_char only fills in the
# ~40 keys nothing else already claimed. area_left has zero overlap with
# any other area here as of this writing, so its position doesn't matter,
# but it's kept ahead of area_char for the same "specific system wins over
# the generic char system" precedence.
_RELEVANT_AREAS = ("area_right", "area_chord", "area_left", "area_char")

KEY_TO_GLYPH: dict[str, str] = {}
for _area in _RELEVANT_AREAS:
    for _row in data.load_components():
        if _row.latin and _row.in_area(_area) and _row.latin not in KEY_TO_GLYPH:
            KEY_TO_GLYPH[_row.latin] = _row.glyph_name

# Control-glyph substitutions hardcoded in features.py's gen_liga_feature()
# (e.g. "sub bar by blank_bar;", for cuo's '|' segment divider) -- these
# live entirely outside components.csv (blank_bar is one of
# config.CONTROL_GLYPHS instead), so KEY_TO_GLYPH can't discover them by
# scanning rows. Keyed by the raw input character (matching how a LAYOUTS
# entry's selector.contains references it), valued by the FINAL
# substituted glyph that actually needs positioning. Add an entry here
# whenever a new LAYOUTS entry's pivot is one of these control glyphs
# rather than a components.csv row.
KEY_TO_GLYPH["|"] = "blank_bar"

# ':' (vert-mode trigger, "layout_vertjzpN" in jzpbuild/gpos.py) -- same
# deal as "|" above, substituted to blank_colon via features.py's
# c2j_char_symbols/gen_liga_feature ("sub colon by blank_colon;"), not a
# components.csv row. The fullwidth Chinese input colon "：" (ch_colon)
# doesn't need its own entry here -- gen_c2j_char_symbols() normalizes it
# to plain ASCII colon upstream of that substitution, so it collapses into
# this same key before dynamic_positioning ever sees it.
KEY_TO_GLYPH[":"] = "blank_colon"

# dynamic_positioning area name -> components.csv area column. Used to look
# up which glyphs live in a given LAYOUTS area (e.g. for gap overrides keyed
# by that area's own glyph identity, see identity.py) and by
# jzpbuild.devserver's /api/dynamic/data (so tools/jzpbuilder-dynamic.html
# reads this same mapping instead of hardcoding its own copy). "bar" has no
# entry -- it's a hardcoded control-glyph substitution (KEY_TO_GLYPH["|"]
# above), not a components.csv row.
AREA_TO_CSV_COLUMN = {
    "fy": "area_fy",
    "left": "area_left",
    "hui": "area_hui",
    "jc": "area_mod_jc",
    "zhu": "area_mod_zhu",
    "right": "area_right",
    "string": "area_string",
    "string_top": "area_string",
    "string_bottom": "area_string",
    "chord": "area_chord",
    "char": "area_char",
}

_TRAILING_INDEX = re.compile(r"_\d+$")


def csv_column_for(area: str) -> str:
    """Real components.csv column for `area` -- generalizes AREA_TO_CSV_COLUMN
    with one fallback: if `area` itself isn't registered, strip a trailing
    "_N" (e.g. "char_2" -> "char") and look up that base name instead. This
    is what lets a LAYOUTS entry invent as many numbered "repeat slots" of an
    existing area as a topology needs (char_1, char_2, ..., left_5, ...)
    with zero registration beyond geometry.LAYOUTS itself -- classes.py's
    gen_repeated_area_classes() uses this to auto-generate each one's FEA
    class straight from the base area's real glyph set, no hand-maintained
    per-number table (unlike classic jzpbuild/features.py's own row-numbered
    vert-mode aliases, which stop at a hardcoded 4 and use an inconsistent
    char{i}-vs-left_{i} naming convention this module deliberately doesn't
    inherit -- see README's "Adding a custom signifier").

    Raises KeyError if neither `area` nor its stripped base is registered --
    a genuinely unregistered area (real authoring gap) or a control-glyph
    area (colon/bar: no real column at all, always a pivot -- callers that
    might hit one of these should catch KeyError and skip, not propagate."""
    if area in AREA_TO_CSV_COLUMN:
        return AREA_TO_CSV_COLUMN[area]
    base = _TRAILING_INDEX.sub("", area)
    if base != area and base in AREA_TO_CSV_COLUMN:
        return AREA_TO_CSV_COLUMN[base]
    raise KeyError(f"no components.csv column known for area {area!r} (or base {base!r})")


def family_for_key(key: str) -> str | None:
    """Which config.RIGHT_SELECTORS family this key's glyph belongs to, or
    None if it isn't part of that system at all (e.g. cuo's chord keys,
    which live in area_chord and were never grouped into RIGHT_SELECTORS
    families -- callers should fall back to something else for naming/
    scoping purposes, see build.py/classes.py)."""
    glyph = KEY_TO_GLYPH.get(key)
    if glyph is None:
        return None
    for family, glyphs in config.RIGHT_SELECTORS.items():
        if glyph in glyphs:
            return family
    return None
