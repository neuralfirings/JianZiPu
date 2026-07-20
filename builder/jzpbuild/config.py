"""Paths and static configuration for the JianZiPu build."""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# path roots — internal only, used here to build the paths below

BUILDER_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# human-maintained input files — used by: data.py, features.py
# (all now live under builder/, no legacy src/input/ fallback)

AREA_KEY_CSV = BUILDER_DIR / "inputs/glyphAreas.csv"                 # data.py
GLYPH_RENAME_CSV = BUILDER_DIR / "inputs/glyphRename.csv"            # data.py
EDGE_CASES_FEA = BUILDER_DIR / "inputs/edge_cases.fea"                # features.py

# Browser-tool mirror of AREA_KEY_CSV (see toolsdata.py) — same <script src>
# trick as POSITIONS_JS/SVG_DATA_JS below, colocated with its source.
GLYPH_AREAS_JS = BUILDER_DIR / "inputs/glyphAreas.js"

# ---------------------------------------------------------------------------
# generated build artifacts (Figma-fetched, tracked in git) — the only
# source read at build time, no fallback to some other copy

GENERATED_INPUTS_DIR = BUILDER_DIR / "generated_inputs"          # glyphs.py, genfea.py, figma.py, build.py
COMPONENTS_DIR = GENERATED_INPUTS_DIR / "svg"                    # glyphs.py, build.py — SVGs, one per component glyph
META_JSON = GENERATED_INPUTS_DIR / "meta.json"                   # figma.py — Figma file version, for cache invalidation
POSITIONS_JSON = GENERATED_INPUTS_DIR / "positions.json"         # genfea.py, figma.py — layout/area geometry
FEA_OUT_DEFAULT = GENERATED_INPUTS_DIR / "fontForgeFeatures.fea" # build.py — default --fea-out inspection copy

# Browser-tool convenience copies (figma.py) — tools/positions_checker.html
# runs over file://, where fetch()/XHR can't load local sibling files but a
# <script src> tag can (verified: Chromium blocks the former, allows the
# latter), so positions.json/svg/*.svg get mirrored into .js files that just
# assign to a global instead of being fetched as data.
POSITIONS_JS = GENERATED_INPUTS_DIR / "positions.js"
SVG_DATA_JS = GENERATED_INPUTS_DIR / "svg_data.js"

# ---------------------------------------------------------------------------
# Figma access — used by: figma.py

# Figma file key (from the design file URL, see README)
FIGMA_FILE_KEY = os.environ.get("FIGMA_FILE_KEY", "CC89RmepV34CVP9bKWu48b")
# Only this page (Figma "canvas") is scanned for glyphs/layouts; other pages
# (drafts, archive, WIP) are ignored entirely.
FIGMA_PAGE_NAME = os.environ.get("FIGMA_PAGE_NAME", "main")

# ---------------------------------------------------------------------------
# font source / build outputs

SOURCE_FONT = BUILDER_DIR / "src_font/TW-Kai-98.ttf"                      # base.py
# Codepoints subset from TW-Kai besides the renamed chars in glyphRename.csv:
# printable ASCII plus NBSP.
BASE_KEEP_CODEPOINTS = list(range(0x20, 0x7F)) + [0xA0]      # base.py
CURRENT_FONT = BUILDER_DIR / "tests/JianZiPu.ttf"                       # tests/test_shaping.py — tracked, golden reference
OUTPUT_FONT = BUILDER_DIR / "JianZiPu.ttf"                      # build.py — default build destination, never clobbers CURRENT_FONT

# ---------------------------------------------------------------------------
# font metrics / identity — used by: base.py, glyphs.py

UPEM = 1000                                                   # glyphs.py, base.py
FONT_VERSION = "3.1"                                          # internal only (feeds NAMES below)

# Vertical metrics (README §1.1: OS/2 uses 1100 asc / 500 desc / 100 gap)
HHEA_ASCENT, HHEA_DESCENT, HHEA_LINEGAP = 1100, -500, 100
TYPO_ASCENT, TYPO_DESCENT, TYPO_LINEGAP = 1100, -500, 100
WIN_ASCENT, WIN_DESCENT = 1100, 500

NAMES = {
    "copyright": (
        "Copyright (c) 2025, Nancy Yi Liang, Nellodee LLC. This font is licensed "
        "under the SIL Open Font License, Version 1.1 (https://openfontlicense.org/)"
    ),
    "familyName": "JianZiPu",
    "styleName": "Regular",
    "uniqueFontIdentifier": "jzpbuild : JianZiPu",
    "fullName": "JianZiPu",
    "version": f"Version {FONT_VERSION}",
    "psName": "JianZiPu",
}

# OS/2 fields carried over from the FontForge-era font
OS2 = {
    "achVendID": "PfEd",
    "usWeightClass": 400,
    "usWidthClass": 5,
    "ulUnicodeRange1": 0x1,          # Basic Latin
    "ulUnicodeRange2": 0x10810000,   # CJK sym/punct, CJK compat, PUA
    "ulCodePageRange1": 0x140001,    # 1252 Latin-1, 936 Simp Chinese, 950 Trad Chinese
    "sxHeight": 430,
    "sCapHeight": 660,
}

# widths of the zero-ink control glyphs (from the current font)
CONTROL_GLYPHS = {  # name -> (codepoint, advance width)  — used by: base.py
    "blank": (0x58001, 0),
    "blank_bar": (0x58002, 500),
    "blank_colon": (0x58003, 1000),
    "advance": (0x58004, 1000),
    "half_advance": (0x58005, 500),
}

# ---------------------------------------------------------------------------
# right-hand technique classes — used by: features.py, gpos.py

# Right-hand selector classes: which lg_* glyphs use which layout family.
# li takes two strings and has its own layout rules; the other six share the
# standard word layout structure (RIGHT_KEYS, in this order).
RIGHT_SELECTORS = {  # features.py
    "loki": ["lg_dazhai", "lg_gouti"],
    "nc": ["lg_pi", "lg_qiaqi"],
    "tiao": ["lg_tiao", "lg_tuo"],
    "mo": ["lg_mo", "lg_motiao", "lg_yan", "lg_lun", "lg_banlun"],
    "gou": ["lg_gou", "lg_da"],
    "io": ["lg_ti", "lg_zhai"],
    "li": ["lg_li"],
}
RIGHT_KEYS = [k for k in RIGHT_SELECTORS if k != "li"]  # gpos.py

# ---------------------------------------------------------------------------
# defined but currently unused elsewhere (kept as documented intent — features.py
# recomputes its own hui/decimal ranges inline instead of importing these)

# Hui numbers and their ASCII-digit glyph spellings ("one zero" = 10, etc.)
HUI_RANGE = list(range(1, 14))  # 1..13; 13 also reachable as ch_wai / "13+"
DECIMALS = list(range(1, 10))

# PUA assignments (must stay stable so existing documents keep rendering)
CONTROL_GLYPHS_BASE = 0x58001  # duplicates CONTROL_GLYPHS["blank"][0] above
COMPONENT_GLYPHS_BASE = 58101  # duplicates the base implicit in glyphs.py's own codepoint counter
