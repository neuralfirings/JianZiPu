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

Kept as its own module, separate from both geometry.py (which needs key
names for its gap overrides) and classes.py (which needs glyph names for
FEA class emission), so neither has to import the other for this and
there's no import cycle with geometry.py's own RIGHT_KEYS.
"""

from jzpbuild import config, data

# area_right: gou/io/li/loki/nc/tiao/mo's own technique glyphs.
# area_chord: cuo's C/DC/FC chord markers.
_RELEVANT_AREAS = ("area_right", "area_chord")

KEY_TO_GLYPH: dict[str, str] = {
    row.latin: row.glyph_name
    for row in data.load_components()
    if row.latin and any(row.in_area(a) for a in _RELEVANT_AREAS)
}

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

GLYPH_TO_KEY = {glyph: key for key, glyph in KEY_TO_GLYPH.items()}

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
}


def keys_for(family: str) -> list[str]:
    """ASCII keys for every glyph in `family`, in config.RIGHT_SELECTORS order."""
    missing = [g for g in config.RIGHT_SELECTORS[family] if g not in GLYPH_TO_KEY]
    if missing:
        raise KeyError(f"no components.csv row (with a 'latin' key) found for glyphs: {missing}")
    return [GLYPH_TO_KEY[glyph] for glyph in config.RIGHT_SELECTORS[family]]


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
