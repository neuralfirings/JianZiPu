"""Build the base font: subset TW-Kai, rename glyphs, set metrics.

Replaces fontForgeCreateBase / ExportGlyphInfo / ImportGlyphInfo /
GlyphRename and the manual Font Info dialogs.
"""

from fontTools.ttLib import TTFont, newTable
from fontTools.subset import Subsetter, Options

from . import config
from .data import load_char_to_glyph_name


def build_base() -> TTFont:
    renames = load_char_to_glyph_name()
    keep = config.BASE_KEEP_CODEPOINTS + [ord(ch) for ch in renames]

    font = TTFont(config.SOURCE_FONT)
    options = Options(notdef_outline=True, glyph_names=True,
                      recalc_bounds=True, drop_tables=["vhea", "vmtx", "morx", "feat"])
    options.layout_features = []  # drop source GSUB rules, we build our own
    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=keep)
    subsetter.subset(font)

    # The FontForge pipeline never rescaled TW-Kai's 1024-unit outlines when
    # it set the em to 1000 — glyph coordinates are kept as-is for fidelity.
    font["head"].unitsPerEm = config.UPEM

    rename_glyphs(font, renames)
    add_control_glyphs(font)
    blank_out(font, "numbersign", width=config.UPEM)
    font["hmtx"]["space"] = (config.UPEM, 0)
    set_metadata(font)
    return font


def rename_glyphs(font: TTFont, renames: dict[str, str]) -> None:
    """Rename encoded glyphs to their CSV names (Han chars get ch_*)."""
    cmap = font.getBestCmap()
    old_to_new = {}
    for ch, target in renames.items():
        code = ord(ch)
        if code not in cmap:
            continue
        if cmap[code] != target:
            old_to_new[cmap[code]] = target

    glyf = font["glyf"]
    for g in font.getGlyphOrder():
        if glyf[g].isComposite():
            raise RuntimeError(f"unexpected composite glyph {g}; rename would break components")

    new_order = [old_to_new.get(g, g) for g in font.getGlyphOrder()]
    glyf.glyphs = {old_to_new.get(g, g): v for g, v in glyf.glyphs.items()}
    hmtx = font["hmtx"]
    hmtx.metrics = {old_to_new.get(g, g): v for g, v in hmtx.metrics.items()}
    for table in font["cmap"].tables:
        table.cmap = {c: old_to_new.get(g, g) for c, g in table.cmap.items()}
    font.setGlyphOrder(new_order)
    if hasattr(font, "_reverseGlyphOrderDict"):
        del font._reverseGlyphOrderDict
    font["post"].glyphOrder = None  # re-derive names on compile


def add_control_glyphs(font: TTFont) -> None:
    from fontTools.ttLib.tables._g_l_y_f import Glyph

    glyf = font["glyf"]
    hmtx = font["hmtx"]
    cmap_tables = [t for t in font["cmap"].tables if t.format in (4, 12)]
    order = font.getGlyphOrder()
    for name, (code, width) in config.CONTROL_GLYPHS.items():
        glyf.glyphs[name] = Glyph()
        hmtx.metrics[name] = (width, 0)
        order.append(name)
        for t in cmap_tables:
            if t.format == 12 or code <= 0xFFFF:
                t.cmap[code] = name
    font.setGlyphOrder(order)
    if hasattr(font, "_reverseGlyphOrderDict"):
        del font._reverseGlyphOrderDict


def blank_out(font: TTFont, name: str, width: int) -> None:
    from fontTools.ttLib.tables._g_l_y_f import Glyph

    font["glyf"].glyphs[name] = Glyph()
    font["hmtx"].metrics[name] = (width, 0)


def set_metadata(font: TTFont) -> None:
    head, hhea, os2 = font["head"], font["hhea"], font["OS/2"]
    hhea.ascent, hhea.descent, hhea.lineGap = (
        config.HHEA_ASCENT, config.HHEA_DESCENT, config.HHEA_LINEGAP)
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = (
        config.TYPO_ASCENT, config.TYPO_DESCENT, config.TYPO_LINEGAP)
    os2.usWinAscent, os2.usWinDescent = config.WIN_ASCENT, config.WIN_DESCENT
    os2.fsType = 0
    for attr, val in config.OS2.items():
        setattr(os2, attr, val)

    name = newTable("name")
    name.names = []
    font["name"] = name
    ids = {0: "copyright", 1: "familyName", 2: "styleName",
           3: "uniqueFontIdentifier", 4: "fullName", 5: "version", 6: "psName"}
    for nid, key in ids.items():
        name.setName(config.NAMES[key], nid, 3, 1, 0x409)
        name.setName(config.NAMES[key], nid, 1, 0, 0)
