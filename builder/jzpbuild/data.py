"""Loaders for the human-maintained data files.

builder/glyphAreas.csv is the master mapping table: one row per component
glyph, with the input spellings (ASCII, latin, Chinese) and the layout
area(s) the glyph belongs to. builder/glyphRename.csv maps unicode
characters to their glyph names in the font (Han characters get readable
ch_* names).
"""

import csv
from dataclasses import dataclass, field

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


def load_area_map() -> list[GlyphRow]:
    rows = []
    with open(config.AREA_KEY_CSV, newline="", encoding="utf-8-sig") as f:
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


def load_char_to_glyph_name_rows() -> list[tuple[str, str]]:
    """Raw (char, glyph_name) pairs from glyphRename.csv, duplicates included."""
    with open(config.GLYPH_RENAME_CSV, newline="", encoding="utf-8-sig") as f:
        return [(rec["char"], rec["glyph_name"].strip()) for rec in csv.DictReader(f)]


def load_char_to_glyph_name() -> dict[str, str]:
    """unicode char -> renamed glyph name in the font (e.g. '七' -> 'ch_7')."""
    return dict(load_char_to_glyph_name_rows())
