"""Loaders for the human-maintained data files.

inputs/components.csv is the master mapping table: one row per component
glyph, with the input spellings (ASCII, latin, Chinese) and the layout
area(s) the glyph belongs to. inputs/glyphRename.csv maps unicode characters
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
    areas: dict = field(default_factory=dict)  # column name -> value
    vert_variant: str = ""
    common: str = ""
    latin: str = ""
    latin_alt: str = ""
    simplified: str = ""
    traditional: str = ""

    def in_area(self, col: str) -> bool:
        return bool(self.areas.get(col))


AREA_COLUMNS = [
    "area_char", "area_chord", "area_fy", "area_left", "area_hui",
    "area_mod_jc", "area_mod_zhu", "area_right", "area_string",
]


@cache
def load_components() -> list[GlyphRow]:
    rows = []
    with open(config.COMPONENTS_CSV, newline="", encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f):
            rows.append(GlyphRow(
                glyph_name=rec["glyph_name"].strip(),
                areas={c: rec[c].strip() for c in AREA_COLUMNS if rec.get(c, "").strip()},
                vert_variant=rec["vert_variant"].strip(),
                common=rec["common"].strip(),
                latin=rec["latin"].strip(),
                latin_alt=rec["latin_alt"].strip(),
                simplified=rec["simplified"].strip(),
                traditional=rec["traditional"].strip(),
            ))
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
