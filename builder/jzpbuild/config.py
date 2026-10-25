"""Paths and static configuration for the JianZiPu build."""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# path roots — internal only, used here to build the paths below

BUILDER_DIR = Path(__file__).resolve().parent.parent   # this pipeline's directory (builder/)

# ---------------------------------------------------------------------------
# input files — used by: data.py, features.py, glyphs.py, genfea.py
#
# One folder (inputs/) for everything the build reads, all tracked in git:
# design.json, components.csv and svg/ (edited in the Builder app),
# glyphRename.csv and edge_cases.fea (by hand), layouts.json (legacy). Every
# path below is also individually overridable from the CLI (see build.py's
# --input-* flags) — these are just the defaults.
#
# Naming note: COMPONENTS_CSV (the glyph/area/spelling catalog) and
# COMPONENTS_DIR (the svg/ folder of drawn component glyphs) are deliberately
# two different things sharing the word "component" — one's metadata, one's
# artwork. Distinguished by suffix (_CSV vs _DIR); don't conflate them.

INPUTS_DIR = BUILDER_DIR / "inputs"                        # glyphs.py, genfea.py, build.py

COMPONENTS_CSV = INPUTS_DIR / "components.csv"               # data.py
GLYPH_RENAME_CSV = INPUTS_DIR / "glyphRename.csv"            # data.py
EDGE_CASES_FEA = INPUTS_DIR / "edge_cases.fea"                # features.py

COMPONENTS_DIR = INPUTS_DIR / "svg"                    # glyphs.py, build.py — SVGs, one per component glyph
LAYOUTS_JSON = INPUTS_DIR / "layouts.json"             # genfea.py — classic layout/area geometry

# The design file: areas (box size + member glyphs), layouts (slots,
# relationships/gaps, centering). Source of truth for positioning AND for the
# GSUB area classes; edited by the JZP Font Builder app. LAYOUTS_JSON above is
# the classic frame geometry, used only by --classic_pos.
DESIGN_JSON = INPUTS_DIR / "design.json"                     # positioning/, data.py, webserver.py

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
# the public font page (jianzipufont.com) — used by: glossary.py, release.py

SITE_DIR = BUILDER_DIR.parent / "site"
SITE_INDEX = SITE_DIR / "index.html"                   # its glossary tables are generated (glossary.py)
SITE_FONT = SITE_DIR / "JianZiPu.ttf"                  # the released font, written by a release candidate
GLOSSARY_SECTIONS = SITE_DIR / "glossary.json"         # how each glossary section's table is laid out

# ---------------------------------------------------------------------------
# font metrics / identity — used by: base.py, glyphs.py

UPEM = 1000                                                   # glyphs.py, base.py
# The font's version, MAJOR.MINOR with a three-digit minor (3.100, 3.200, 3.201): it is a number
# in the font (head.fontRevision), so 3.10 would equal 3.1. One line in builder/VERSION, written by
# a release (jzpbuild/release.py), so a release never edits Python.
VERSION_FILE = BUILDER_DIR / "VERSION"
FONT_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip()
if not re.fullmatch(r"\d+\.\d{3}", FONT_VERSION):
    raise ValueError(f"{VERSION_FILE}: expected a version like 3.200, got {FONT_VERSION!r}")
# The commit a release font is built from (build --source-commit), added to name ID 5 so a font
# file can be traced to its sources; None for everyday builds.
SOURCE_COMMIT: str | None = None


def version_string() -> str:
    """name ID 5: "Version 3.200", plus "; git-1a2b3c4" for a release build."""
    return f"Version {FONT_VERSION}" + (f"; git-{SOURCE_COMMIT}" if SOURCE_COMMIT else "")


# Vertical metrics (README §1.1: OS/2 uses 1100 asc / 500 desc / 100 gap)
HHEA_ASCENT, HHEA_DESCENT, HHEA_LINEGAP = 1100, -500, 100
TYPO_ASCENT, TYPO_DESCENT, TYPO_LINEGAP = 1100, -500, 100
WIN_ASCENT, WIN_DESCENT = 1100, 500

NAMES = {
    "copyright": (
        'Copyright 2021-2026 Nancy Yi Liang, Nellodee LLC, with Reserved Font Name "JianZiPu". '
        "Portions derived from TW-Kai ((c) 2023 Ministry of Digital Affairs, Taiwan, CNS11643, "
        "Open Government Data License, version 1.0)."
    ),
    "familyName": "JianZiPu",
    "styleName": "Regular",
    "uniqueFontIdentifier": f"{FONT_VERSION};JianZiPu",
    "fullName": "JianZiPu",
    "version": f"Version {FONT_VERSION}",                   # base.py adds the commit (version_string)
    "psName": "JianZiPu",
    "manufacturer": "Nellodee LLC",
    "designer": "Nancy Yi Liang",
    "vendorURL": "https://jianzipufont.com",
    "licenseDescription": "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
    "licenseInfoURL": "https://openfontlicense.org",
}

# name table IDs (OpenType spec) for the NAMES keys above
NAME_IDS = {0: "copyright", 1: "familyName", 2: "styleName", 3: "uniqueFontIdentifier", 4: "fullName",
            5: "version", 6: "psName", 8: "manufacturer", 9: "designer", 11: "vendorURL",
            13: "licenseDescription", 14: "licenseInfoURL"}

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

# zero-ink control glyphs: name -> (codepoint, default advance width). A design area that holds
# one and has an advance sets its width instead (base.control_widths): | and : are set in the Builder.
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
