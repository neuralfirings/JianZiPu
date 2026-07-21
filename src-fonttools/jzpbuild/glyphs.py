"""Import the JZP component SVGs as glyphs (replaces fontForgeAddJZPGlyphs.py).

Coordinate mapping (matches the FontForge-era import exactly):
    font_x = svg_x
    font_y = (viewBox_height - 20) - svg_y
i.e. the SVG's bottom edge lands at y = -20 (FontForge placed the SVG top at
ascent 800 and then shifted by -(820 - height)). Advance width is 0 —
components overstrike and are positioned purely by GPOS.

Codepoints start at 58101 (decimal), assigned in sorted-filename order, which
keeps every component at the same codepoint as the current font.
"""

import xml.etree.ElementTree as ET

import pathops
from picosvg.svg import SVG as PicoSVG
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import SVGPath
from fontTools.ttLib import TTFont

from . import config


def svg_to_ttglyph(svg_file, glyph_set):
    root = ET.parse(svg_file).getroot()
    viewbox = root.get("viewBox")
    height = float(viewbox.split()[3]) if viewbox else float(root.get("height"))

    # Strip clip-paths first: they are Figma frame-cropping noise, and the
    # historical FontForge import ignored them (md_4.blank's digit extends
    # above its frame and must not be chopped).
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    for el in root.iter():
        el.attrib.pop("clip-path", None)
        for child in list(el):
            if child.tag.endswith(("clipPath", "defs")):
                el.remove(child)
    # normalize with picosvg: resolves groups and transforms to plain paths
    svg_text = PicoSVG.fromstring(
        ET.tostring(root, encoding="unicode")).topicosvg().tostring()

    # draw all SVG shapes into a skia path (handles cubics), then simplify:
    # removes overlaps and converts the evenodd fill rule to nonzero winding
    path = pathops.Path()
    path.fillType = pathops.FillType.EVEN_ODD
    SVGPath.fromstring(svg_text.encode()).draw(
        TransformPen(path.getPen(), (1, 0, 0, -1, 0, height - 20)))
    path.simplify(fix_winding=True)

    pen = TTGlyphPen(glyph_set)
    path.draw(Cu2QuPen(pen, max_err=config.UPEM / 1000, reverse_direction=False))
    return pen.glyph()


def add_component_glyphs(font: TTFont, components_dir=None) -> None:
    components_dir = components_dir or config.COMPONENTS_DIR
    svgs = sorted(components_dir.glob("*.svg"))
    if not svgs:
        raise RuntimeError(f"no SVGs found in {components_dir}")

    glyf, hmtx = font["glyf"], font["hmtx"]
    cmap_tables = [t for t in font["cmap"].tables if t.format in (4, 12)]
    order = font.getGlyphOrder()
    glyph_set = font.getGlyphSet()
    code = config.COMPONENT_GLYPHS_BASE
    for svg in svgs:
        name = svg.stem
        if name in glyf.glyphs:
            continue
        glyph = svg_to_ttglyph(svg, glyph_set)
        glyf.glyphs[name] = glyph
        # TrueType renderers shift outlines by (lsb - xMin), so lsb must
        # equal xMin for the outline to render at its stored coordinates
        xmin = min((x for x, y in glyph.coordinates), default=0) if glyph.numberOfContours else 0
        hmtx.metrics[name] = (0, xmin)
        order.append(name)
        for t in cmap_tables:
            t.cmap[code] = name
        code += 1
    font.setGlyphOrder(order)
    if hasattr(font, "_reverseGlyphOrderDict"):
        del font._reverseGlyphOrderDict
