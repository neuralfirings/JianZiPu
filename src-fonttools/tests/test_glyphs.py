"""Unit tests for jzpbuild.glyphs: SVG -> flattened outline (what the font build makes of a file).

Run:  cd src-fonttools && python3 -m pytest tests/test_glyphs.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from jzpbuild import config, glyphs  # noqa: E402

SQUARE = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M10 10h100v100h-100z" fill="black"/></svg>'


def test_flatten_square():
    r = glyphs.flatten_svg_text(SQUARE)
    assert r["contours"] == 1
    assert r["points"] == 4
    assert r["bounds"] == [10.0, 10.0, 110.0, 110.0]
    assert r["viewBox"] == [0, 0, 350, 350]
    assert r["d"].startswith("M10 10")


def _area(svg_text):
    import xml.etree.ElementTree as ET
    from fontTools.pens.areaPen import AreaPen
    pen = AreaPen()
    glyphs._skia_path(ET.fromstring(svg_text), None).draw(pen)
    return abs(pen.value)


def _svg(*paths, extra=""):
    return ('<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg">'
            + "".join(f'<path d="{d}" fill="black"{extra}/>' for d in paths) + "</svg>")


def test_overlapping_paths_are_unioned_like_a_browser_paints_them():
    # two overlapping squares: one outline, no hole where they overlap
    r = glyphs.flatten_svg_text(_svg("M0 0h100v100h-100z", "M50 50h100v100h-100z"))
    assert r["contours"] == 1
    assert r["bounds"] == [0.0, 0.0, 150.0, 150.0]
    assert _area(_svg("M0 0h100v100h-100z", "M50 50h100v100h-100z")) == pytest.approx(17500)


def test_a_path_stacked_on_itself_stays_filled():
    # Figma exports sometimes hold a stroke twice; even-odd used to cancel it to a hairline
    sq = "M10 10h100v100h-100z"
    assert _area(_svg(sq, sq)) == pytest.approx(10000)
    # ... also when the copy runs the other way round
    assert _area(_svg(sq, "M10 10v100h100v-100z")) == pytest.approx(10000)


def test_a_hole_inside_one_evenodd_path_is_kept():
    ring = "M0 0h100v100h-100z M25 25h50v50h-50z"
    assert _area(_svg(ring, extra=' fill-rule="evenodd"')) == pytest.approx(7500)
    # under nonzero the same two same-direction squares fill solid, as in a browser
    assert _area(_svg(ring)) == pytest.approx(10000)


@pytest.mark.parametrize("name", ["md_fenkai", "md_wai", "md_2"])
def test_glyphs_that_used_to_come_out_hollow_are_solid(name):
    """These overlap their own strokes. Their ink must be at least that of their biggest path."""
    from picosvg.svg import SVG as PicoSVG
    from picosvg.svg_pathops import skia_path
    from fontTools.pens.areaPen import AreaPen
    text = (config.COMPONENTS_DIR / f"{name}.svg").read_text()
    biggest = 0
    for shape in PicoSVG.fromstring(text).topicosvg().shapes():
        p = skia_path(shape.as_cmd_seq(), shape.fill_rule)
        p.simplify(fix_winding=True)
        pen = AreaPen()
        p.draw(pen)
        biggest = max(biggest, abs(pen.value))
    assert _area(text) >= biggest * 0.999


def test_strokes_are_expanded_to_outlines():
    """picosvg turns `stroke=` into filled outlines: a stroked square becomes a ring, an open
    stroked line a band. The glyph editor outlines lines itself, so it never depends on this."""
    svg = ('<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg">'
           '<path d="M10 10h100v100h-100z" stroke="black" stroke-width="20" fill="none"/></svg>')
    r = glyphs.flatten_svg_text(svg)
    assert r["contours"] == 2                                 # outer edge + the hole
    assert r["bounds"] == [0.0, 0.0, 120.0, 120.0]            # 10 units each side of the square
    line = ('<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M10 10L100 100" stroke="black" stroke-width="20" fill="none"/></svg>')
    r = glyphs.flatten_svg_text(line)
    assert r["contours"] == 1 and r["bounds"][2] > 100


def test_fill_none_without_stroke_contributes_nothing():
    svg = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M10 10h100v100h-100z" fill="none"/></svg>'
    r = glyphs.flatten_svg_text(svg)
    assert r["contours"] == 0 and r["bounds"] is None


def test_groups_and_transforms_are_resolved():
    svg = ('<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg">'
           '<g transform="translate(100 0)"><rect x="0" y="0" width="50" height="50" fill="black"/></g></svg>')
    r = glyphs.flatten_svg_text(svg)
    assert r["bounds"] == [100.0, 0.0, 150.0, 50.0]


def test_clip_path_is_ignored():
    # Figma frame clips must not chop the outline (md_4.blank's digit extends above its frame)
    svg = ('<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg">'
           '<g clip-path="url(#c)"><path d="M-20 -20h100v100h-100z" fill="black"/></g>'
           '<defs><clipPath id="c"><rect width="350" height="350"/></clipPath></defs></svg>')
    r = glyphs.flatten_svg_text(svg)
    assert r["bounds"] == [-20.0, -20.0, 80.0, 80.0]


def test_width_height_without_viewbox_is_accepted():
    svg = '<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg"><path d="M0 0h10v10h-10z"/></svg>'
    assert glyphs.flatten_svg_text(svg)["viewBox"] == [0, 0, 200, 100]


def test_missing_size_is_rejected():
    with pytest.raises(ValueError):
        glyphs.flatten_svg_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h10v10z"/></svg>')


def test_malformed_xml_is_rejected():
    with pytest.raises(Exception):
        glyphs.flatten_svg_text("<svg viewBox='0 0 1 1'><path d='M0 0h1'></svg")


@pytest.mark.skipif(not config.COMPONENTS_DIR.exists(), reason="inputs/svg/ not present")
def test_every_shipped_svg_flattens_to_something():
    files = sorted(config.COMPONENTS_DIR.glob("*.svg"))
    assert files, "no SVGs in inputs/svg/"
    for f in files:
        r = glyphs.flatten_svg_text(f.read_text(encoding="utf-8"))
        assert r["contours"] >= 1, f.name
        assert r["viewBox"][2] > 0 and r["viewBox"][3] > 0, f.name


@pytest.mark.skipif(not (config.COMPONENTS_DIR / "lg_gou.svg").exists(), reason="inputs/svg/lg_gou.svg not present")
def test_flatten_matches_ttglyph_bounds_up_to_the_y_flip():
    """flatten_svg_text (SVG coordinates) and svg_to_ttglyph (font coordinates) see the same outline."""
    from fontTools.ttLib import TTFont
    from fontTools.pens.boundsPen import BoundsPen

    f = config.COMPONENTS_DIR / "lg_gou.svg"
    flat = glyphs.flatten_svg_text(f.read_text(encoding="utf-8"))
    font = TTFont()
    font.setGlyphOrder([".notdef"])
    glyph = glyphs.svg_to_ttglyph(f, {})
    xs = [x for x, _ in glyph.coordinates]
    ys = [y for _, y in glyph.coordinates]
    height = flat["viewBox"][3]
    assert min(xs) == pytest.approx(flat["bounds"][0], abs=1)
    assert max(xs) == pytest.approx(flat["bounds"][2], abs=1)
    # font_y = (height - 20) - svg_y
    assert max(ys) == pytest.approx(height - 20 - flat["bounds"][1], abs=1)
    assert min(ys) == pytest.approx(height - 20 - flat["bounds"][3], abs=1)


def test_every_shipped_svg_converts_to_a_font_glyph():
    """The y-flipped (font) conversion has its own failure modes: skia's simplify once failed
    on the flipped md_zhua. Every file must convert, with contours running the same way as in
    the FontForge-era font (positive area in fontTools' AreaPen, for every glyph there)."""
    from fontTools.pens.areaPen import AreaPen
    for f in sorted(config.COMPONENTS_DIR.glob("*.svg")):
        glyph = glyphs.svg_to_ttglyph(f, {})
        assert glyph.numberOfContours >= 1, f.name
        pen = AreaPen()
        glyph.draw(pen, {})
        assert pen.value > 0, f"{f.name}: contours run the wrong way"
