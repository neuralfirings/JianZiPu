"""Loaders for the human-maintained data files.

inputs/components.csv is the glyph catalog: one row per component glyph
with its input spellings (ASCII, latin, Chinese). Which layout area(s) a
glyph belongs to lives in inputs/design.json (see jzpbuild.positioning) and
is merged onto each row here. inputs/glyphRename.csv maps unicode characters
to their glyph names in the font (Han characters get readable ch_* names).

Both loaders are cached: a build reads each file once, however many
modules ask for it. The CLI's --input-* overrides are applied to config
before the first load, so they're honored; a long-running process that
rewrites a file (devserver.py's /api/save) must call the loader's
`cache_clear()` afterwards.
"""

import csv
from dataclasses import dataclass, field
from functools import cache

from . import config


@dataclass
class GlyphRow:
    glyph_name: str
    areas: set = field(default_factory=set)   # design.json area names this glyph belongs to
    vert_variant: str = ""
    common: str = ""
    latin: str = ""
    latin_alt: str = ""
    simplified: str = ""
    traditional: str = ""

    def in_area(self, name: str) -> bool:
        """`name` is a design.json area ("left"); the legacy CSV column
        spellings ("area_left", "area_mod_jc") are accepted too."""
        return _LEGACY_AREA_NAMES.get(name, name) in self.areas


_LEGACY_AREA_NAMES = {
    "area_char": "char", "area_chord": "chord", "area_fy": "fy", "area_left": "left",
    "area_hui": "hui", "area_mod_jc": "jc", "area_mod_zhu": "zhu", "area_right": "right",
    "area_string": "string",
}


@cache
def load_design():
    """The parsed design file (jzpbuild.positioning.schema.Design)."""
    from .positioning.schema import load_design as _load
    return _load(config.DESIGN_JSON)


def cache_clear_all() -> None:
    load_design.cache_clear()
    load_components.cache_clear()
    load_char_to_glyph_name_rows.cache_clear()


@cache
def load_components() -> list[GlyphRow]:
    rows = []
    with open(config.COMPONENTS_CSV, newline="", encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f):
            rows.append(GlyphRow(
                glyph_name=rec["glyph_name"].strip(),
                vert_variant=rec["vert_variant"].strip(),
                common=rec["common"].strip(),
                latin=rec["latin"].strip(),
                latin_alt=rec["latin_alt"].strip(),
                simplified=rec["simplified"].strip(),
                traditional=rec["traditional"].strip(),
            ))
    by_name = {r.glyph_name: r for r in rows}
    for area in load_design().areas.values():
        for g in area.glyphs:
            if g in by_name:
                by_name[g].areas.add(area.name)
    return rows


@cache
def load_char_to_glyph_name_rows() -> list[tuple[str, str]]:
    """Raw (char, glyph_name) pairs from glyphRename.csv, duplicates included."""
    with open(config.GLYPH_RENAME_CSV, newline="", encoding="utf-8-sig") as f:
        return [(rec["char"], rec["glyph_name"].strip()) for rec in csv.DictReader(f)]


def load_char_to_glyph_name() -> dict[str, str]:
    """unicode char -> renamed glyph name in the font (e.g. '七' -> 'ch_7')."""
    return dict(load_char_to_glyph_name_rows())


def referenced_chars(rows: list[GlyphRow]) -> set[str]:
    """Every character used anywhere in components.csv's simplified/traditional
    columns, including individual characters inside multi-char spellings
    (e.g. both 应 and 合 from md_yinghe's 应合)."""
    chars: set[str] = set()
    for r in rows:
        chars.update(r.simplified)
        chars.update(r.traditional)
    return chars


def resolve_char_to_glyph_name(rows: list[GlyphRow]) -> dict[str, str]:
    """char -> glyph name, for every character referenced in components.csv.

    glyphRename.csv rows are overrides (readable ch_* names); any referenced
    character with no override row still gets a valid name, matching
    fontTools' own default naming for an un-renamed glyph (uniXXXX).
    """
    overrides = load_char_to_glyph_name()
    c2g = dict(overrides)
    for ch in referenced_chars(rows):
        if ch not in c2g:
            c2g[ch] = f"uni{ord(ch):04X}"
    return c2g
