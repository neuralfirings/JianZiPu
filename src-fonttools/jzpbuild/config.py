"""Paths and static configuration for the JianZiPu build."""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# path roots — internal only, used here to build the paths below

BUILDER_DIR = Path(__file__).resolve().parent.parent   # this pipeline's directory (src-fonttools/)

# ---------------------------------------------------------------------------
# input files — used by: data.py, features.py, glyphs.py, genfea.py, figma.py
#
# One folder (inputs/) for everything the build reads: both the
# human-maintained sources (components.csv, glyphRename.csv, edge_cases.fea)
# and the Figma-fetched artifacts (svg/, layouts.json, meta.json — tracked
# in git, refreshed via --figma_pull, no fallback to some other copy). Every
# path below is also individually overridable from the CLI (see build.py's
# --input-* flags) — these are just the defaults.
#
# Naming note: COMPONENTS_CSV (the glyph/area/spelling catalog) and
# COMPONENTS_DIR (the svg/ folder of drawn component glyphs) are deliberately
# two different things sharing the word "component" — one's metadata, one's
# artwork. Distinguished by suffix (_CSV vs _DIR); don't conflate them.

INPUTS_DIR = BUILDER_DIR / "inputs"                        # glyphs.py, genfea.py, figma.py, build.py

COMPONENTS_CSV = INPUTS_DIR / "components.csv"               # data.py
GLYPH_RENAME_CSV = INPUTS_DIR / "glyphRename.csv"            # data.py
EDGE_CASES_FEA = INPUTS_DIR / "edge_cases.fea"                # features.py

COMPONENTS_DIR = INPUTS_DIR / "svg"                    # glyphs.py, build.py — SVGs, one per component glyph
META_JSON = INPUTS_DIR / "meta.json"                   # figma.py — Figma file version, for cache invalidation
LAYOUTS_JSON = INPUTS_DIR / "layouts.json"             # genfea.py, figma.py — layout/area geometry

# dynamic_positioning/'s own layout data (area sizes + relationship graphs,
# see geometry.py) — separate from LAYOUTS_JSON above, which belongs to the
# classic Figma-driven pipeline. Edited by tools/jzpbuilder-dynamic.html.
DYNAMIC_LAYOUTS_JSON = BUILDER_DIR / "dynamic_positioning" / "layouts_data.json"  # geometry.py, devserver.py

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
# Build artifacts (gitignored): the font, and an inspection copy of the
# generated feature text (--fea-out). Neither ever clobbers CURRENT_FONT.
OUTPUT_FONT = BUILDER_DIR / "JianZiPu.ttf"                      # build.py
FEA_OUT_DEFAULT = BUILDER_DIR / "JianZiPu.fea"                  # build.py

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

# PUA assignments — must stay stable so existing documents keep rendering.

# zero-ink control glyphs: name -> (codepoint, advance width)
CONTROL_GLYPHS = {                                            # base.py
    "blank": (0x58001, 0),
    "blank_bar": (0x58002, 1000),
    "blank_colon": (0x58003, 1000),
    "advance": (0x58004, 1000),
    "half_advance": (0x58005, 500),
}
# First codepoint for the imported component glyphs; glyphs.py assigns them
# in sorted-filename order from here.
COMPONENT_GLYPHS_BASE = 58101                                 # glyphs.py

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
