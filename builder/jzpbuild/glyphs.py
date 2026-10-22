"""Import the JZP component SVGs as glyphs (replaces fontForgeAddJZPGlyphs.py).

Coordinate mapping (matches the FontForge-era import exactly):
    font_x = svg_x
    font_y = (viewBox_height - 20) - svg_y
i.e. the SVG's bottom edge lands at y = -20 (FontForge placed the SVG top at
ascent 800 and then shifted by -(820 - height)). Advance width is 0 —
components overstrike and are positioned purely by GPOS.

Codepoints start at 58101 (decimal, U+E2F5). Each glyph's code is pinned in
inputs/glyph_ids.json, so renaming, deleting or adding a glyph never moves
another glyph's code; a glyph with no pin gets the next free one (glyph_ids.py).
"""

import xml.etree.ElementTree as ET

import pathops
from picosvg.svg import SVG as PicoSVG
from picosvg.svg_pathops import skia_path
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont

from . import config, glyph_ids


def _skia_path(root, flip_height: float | None):
    """The SVG's shapes as one skia path: clip-paths stripped, groups and
    transforms resolved (picosvg), overlaps removed and winding fixed.
    With `flip_height` the result is in font coordinates (y up); without,
    it stays in SVG coordinates."""
    # Strip clip-paths first: they are frame-cropping noise from design-tool exports, and the
    # historical FontForge import ignored them (md_4.blank's digit extends
    # above its frame and must not be chopped).
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    for el in root.iter():
        el.attrib.pop("clip-path", None)
        for child in list(el):
            if child.tag.endswith(("clipPath", "defs")):
                el.remove(child)
    # normalize with picosvg: resolves groups and transforms to plain paths,
    # each with its own fill rule
    pico = PicoSVG.fromstring(ET.tostring(root, encoding="unicode")).topicosvg()

    # An SVG paints each path on its own, so the glyph is the union of its paths.
    # Clean each path first under its own fill rule (self-intersections, holes,
    # contour direction), then merge them under nonzero winding. Drawing all paths
    # into one even-odd path instead made overlapping strokes cancel each other
    # (md_fenkai, md_wai, md_2 came out as thin outlines).
    path = pathops.Path()
    path.fillType = pathops.FillType.WINDING
    pen = path.getPen()
    for shape in pico.shapes():
        part = skia_path(shape.as_cmd_seq(), shape.fill_rule)
        part.simplify(fix_winding=True)
        part.draw(pen)
    # merge in SVG coordinates: skia's simplify can fail on the flipped copy
    # of the same outline (md_zhua), so flip afterwards
    path.simplify(fix_winding=True)
    if flip_height is None:
        return path
    clockwise = path.clockwise
    flipped = path.transform(1, 0, 0, -1, 0, flip_height - 20)
    if flipped.clockwise != clockwise:
        flipped.reverse()        # a mirror flips every contour; keep skia's direction
    return flipped


def _viewbox_height(root) -> float:
    viewbox = root.get("viewBox")
    return float(viewbox.split()[3]) if viewbox else float(root.get("height"))


def svg_to_ttglyph(svg_file, glyph_set):
    root = ET.parse(svg_file).getroot()
    path = _skia_path(root, _viewbox_height(root))
    pen = TTGlyphPen(glyph_set)
    path.draw(Cu2QuPen(pen, max_err=config.UPEM / 1000, reverse_direction=False))
    return pen.glyph()


def flatten_svg_text(svg_text: str) -> dict:
    """What the font build will make of an SVG, in SVG coordinates: the
    flattened outline as one path `d`, its contour / point counts and
    bounds. Raises on anything the build could not use."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.recordingPen import RecordingPen

    root = ET.fromstring(svg_text)
    viewbox = root.get("viewBox")
    if not viewbox and not (root.get("width") and root.get("height")):
        raise ValueError("the SVG needs a viewBox (or width and height)")
    path = _skia_path(root, None)
    d_pen = SVGPathPen(None, ntos=lambda v: f"{round(v, 2):g}")
    path.draw(d_pen)
    rec = RecordingPen()
    path.draw(rec)
    bounds = BoundsPen(None)
    path.draw(bounds)
    contours = sum(1 for op, _ in rec.value if op == "moveTo")
    # on-curve points: each contour's start plus each segment's end, not counting a
    # last segment that only returns to the start (skia may or may not draw that one)
    points, start, last = 0, None, None
    for op, args in rec.value:
        if op == "moveTo":
            start = last = args[0]
            points += 1
        elif op in ("lineTo", "curveTo", "qCurveTo"):
            last = args[-1]
            points += 1
        elif op == "closePath" and last == start and start is not None:
            points -= 1
    vb = [float(v) for v in viewbox.split()] if viewbox else [0, 0, float(root.get("width")), float(root.get("height"))]
    return {"d": d_pen.getCommands(), "contours": contours, "points": points,
            "bounds": list(bounds.bounds) if bounds.bounds else None, "viewBox": vb}


def add_glyph(font: TTFont, name: str, glyph, advance: int, lsb: int,
              codepoint: int | None = None) -> None:
    """Append one glyph: outline, metrics, glyph order, and (if given) a
    cmap entry in every format-4/12 subtable that can hold the codepoint."""
    font["glyf"].glyphs[name] = glyph
    font["hmtx"].metrics[name] = (advance, lsb)
    font.setGlyphOrder(font.getGlyphOrder() + [name])
    if codepoint is not None:
        for t in font["cmap"].tables:
            if t.format == 12 or (t.format == 4 and codepoint <= 0xFFFF):
                t.cmap[codepoint] = name


def add_component_glyphs(font: TTFont, components_dir=None) -> None:
    components_dir = components_dir or config.COMPONENTS_DIR
    svgs = sorted(components_dir.glob("*.svg"))
    if not svgs:
        raise RuntimeError(f"no SVGs found in {components_dir}")

    glyph_set = font.getGlyphSet()
    codes = glyph_ids.code_map(svg.stem for svg in svgs)
    for svg in svgs:
        name = svg.stem
        if name in font["glyf"].glyphs:
            continue
        glyph = svg_to_ttglyph(svg, glyph_set)
        # TrueType renderers shift outlines by (lsb - xMin), so lsb must
        # equal xMin for the outline to render at its stored coordinates
        xmin = min((x for x, y in glyph.coordinates), default=0) if glyph.numberOfContours else 0
        add_glyph(font, name, glyph, advance=0, lsb=xmin, codepoint=codes[name])
