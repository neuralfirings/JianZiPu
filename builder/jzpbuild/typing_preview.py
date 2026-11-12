"""Spelling preview for the Builder's Typing view.

Generates the GSUB half of the feature file from *unsaved* spelling rows and an
unsaved design, compiles it into a copy of the last built font (GSUB only, in
memory, about half a second), and shapes with HarfBuzz. The same font answers
three questions without a Build:

- `shape(words)`: what typed words become (glyph names, plus the source text
  of every glyph so the app can show leftover letters and missing characters);
- `roundtrip()`: does every spelling, typed alone, give its own glyph?
- `issues(rows)`: clashes and malformed spellings, which pause Save.

A glyph the last build doesn't have but whose drawing exists (`svg`: its SVG
file, or a draft's) is drawn into the preview font from that file (about 0.06 s
each), so a new glyph can be typed and checked without a Build; it is listed in
`drawn`. Anything else the build doesn't contain (a glyph with no drawing, a
Chinese character neither the font nor the base font has) is left out of the
preview font and reported, never guessed. A Chinese character the last build
lacks is copied in from the base font (src_font/TW-Kai-98.ttf) when it's there,
as a build would, under the same name. With `gpos`, the positioning rules are compiled
too (about 2 s), so the font can also draw words (Check the glossary).
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont

from . import config, features
from .data import GlyphRow, resolve_char_to_glyph_name
from .positioning import schema

ROW_FIELDS = ("glyph_name", "vert_variant", "common", "latin", "latin_alt",
              "simplified", "traditional", "pinyin", "glossary", "glossary_order", "meaning")   # the last four: not typed (glossary.py)
SPELLING_FIELDS = ("latin", "latin_alt", "simplified", "traditional")
# letters and digits, starting with a letter (a leading digit reads as a string or position number);
# [ and ] too (features.spell_latin: bracketleft / bracketright), so 【 】 type through them
LATIN_RE = re.compile(r"^[A-Za-z\[\]][A-Za-z0-9\[\]]*$")
HAN_RE = re.compile(r"^[㐀-鿿豈-﫿\U00020000-\U0002ffff]+$")
RESERVED = {"点", "點", "徽", "。", "，"}
# CJK punctuation a Chinese spelling may hold (【 】 《 》 「 」 、 ！ …), not the marks the font reads
# itself: 。 (a position, with 点 / 徽), and ， ： ｜, which become , : | (features.gen_c2j_char_symbols)
NOT_SPELLABLE = {"。", "，", "：", "｜"}
PUNCT = "\u3001-\u3003\u3008-\u3011\u3014-\u301f\uff01-\uff0f\uff1a-\uff20\uff3b-\uff40\uff5b-\uff60"
CHINESE_RE = re.compile("^[" + HAN_RE.pattern[2:-3] + PUNCT + "]+$")


# ---------------------------------------------------------------- rows + checks

def clean_record(rec: dict) -> dict:
    return {k: str(rec.get(k) or "").strip() for k in ROW_FIELDS}


def rows_from(records: list[dict], design: dict) -> list[GlyphRow]:
    """GlyphRows from client records, with area membership from `design`."""
    areas_of: dict[str, set] = {}
    for name, a in design.get("areas", {}).items():
        for g in a.get("glyphs", []):
            areas_of.setdefault(g, set()).add(name)
    out = []
    for rec in records:
        r = clean_record(rec)
        if not r["glyph_name"]:
            continue
        out.append(GlyphRow(glyph_name=r["glyph_name"], areas=set(areas_of.get(r["glyph_name"], ())),
                            vert_variant=r["vert_variant"], common=r["common"], latin=r["latin"],
                            latin_alt=r["latin_alt"], simplified=r["simplified"],
                            traditional=r["traditional"]))
    return out


def _latin_keys(r: GlyphRow) -> list[tuple[str, str]]:
    keys = [(f, getattr(r, f)) for f in ("latin", "latin_alt") if getattr(r, f)]
    if r.common and len(r.common) > 1 and r.common.isalpha():
        keys.append(("common", r.common))
    return keys


def known_glyphs(design: dict | None = None) -> set:
    """Every glyph name that exists: the component SVGs, plus the glyphs of `design`'s areas.
    A vertical form needs no CSV row of its own, so the rows alone don't list it."""
    names = {p.stem for p in config.COMPONENTS_DIR.glob("*.svg")}
    for a in (design or {}).get("areas", {}).values():
        names.update(a.get("glyphs", []))
    return names


def issues(rows: list[GlyphRow], known: set | None = None) -> dict:
    """Errors (pause Save) per spelling: clashes between glyphs that aren't a vertical
    pair, and spellings the generator can't express. Same rules as validate.py.
    `known`: every glyph name that exists; defaults to the SVGs plus the rows' names."""
    pairs = {frozenset((r.glyph_name, r.vert_variant)) for r in rows if r.vert_variant}
    errors = []
    namespaces = {
        "latin": lambda r: _latin_keys(r),
        "simplified": lambda r: [("simplified", r.simplified)] if r.simplified else [],
        "traditional": lambda r: [("traditional", r.traditional)] if r.traditional else [],
    }
    for space, keyfn in namespaces.items():
        claims: dict[str, list[tuple[str, str]]] = {}
        for r in rows:
            for fld, key in keyfn(r):
                claims.setdefault(key, []).append((r.glyph_name, fld))
        for key, who in claims.items():
            glyphs = sorted({g for g, _ in who})
            if len(glyphs) < 2:
                continue
            if len(glyphs) == 2 and frozenset(glyphs) in pairs:
                continue
            errors.append({"kind": "clash", "space": space, "value": key, "glyphs": glyphs,
                           "fields": [{"glyph": g, "field": f} for g, f in who],
                           "message": f"“{key}” types {len(glyphs)} glyphs ({', '.join(glyphs)}). "
                                      f"A spelling can make only one glyph."})
    names = known if known is not None else known_glyphs() | {r.glyph_name for r in rows}
    for r in rows:
        for f in ("latin", "latin_alt"):
            v = getattr(r, f)
            if v and not LATIN_RE.match(v):
                why = ("start with a letter: a leading digit is read as a string or position number"
                       if v[0].isdigit() else "use only letters a–z, A–Z, digits, [ and ]")
                errors.append({"kind": "invalid", "glyph": r.glyph_name, "field": f, "value": v,
                               "message": f"“{v}”: {why}."})
        for f in ("simplified", "traditional"):
            v = getattr(r, f)
            if v and v in RESERVED:
                errors.append({"kind": "invalid", "glyph": r.glyph_name, "field": f, "value": v,
                               "message": f"“{v}” alone marks a position; it can't type a glyph."})
            elif v and (not CHINESE_RE.match(v) or NOT_SPELLABLE.intersection(v)):
                bad = NOT_SPELLABLE.intersection(v)
                why = (f"“{v}”: {'、'.join(sorted(bad))} is read by the font itself (a position, a comma, the vertical "
                       "colon or the chord bar), so a spelling can't hold it." if bad else
                       f"“{v}”: Chinese characters and Chinese punctuation (【 】 《 》…) only.")
                errors.append({"kind": "invalid", "glyph": r.glyph_name, "field": f, "value": v, "message": why})
        if r.vert_variant and r.vert_variant not in names:
            errors.append({"kind": "invalid", "glyph": r.glyph_name, "field": "vert_variant",
                           "value": r.vert_variant, "message": f"Vertical form {r.vert_variant} doesn't exist."})
    return {"errors": errors}


# ---------------------------------------------------------------- preview font

@dataclass
class Preview:
    hb_font: object
    glyphs: set
    not_built: list = field(default_factory=list)     # glyphs the last build doesn't have
    missing_chars: dict = field(default_factory=dict)  # glyph -> [values whose characters aren't in the font]
    vertical_only: set = field(default_factory=set)    # glyphs that get their colon untyped (shang = :shang)
    seconds: float = 0.0
    drawn: list = field(default_factory=list)         # glyphs not in the build, drawn in from their SVGs
    lacking: set = field(default_factory=set)         # the characters behind missing_chars: no font here has them
    copied: list = field(default_factory=list)        # characters the build lacks, copied in from the base font
    key: str = ""                                     # the cache key, to serve font_bytes by
    font_bytes: bytes = b""                           # the compiled preview font


def _shapeable(rows: list[GlyphRow], design: dict, font_glyphs: set) -> tuple[list[GlyphRow], dict, list, dict, set]:
    """Drop what the font can't carry yet, so the generated rules compile."""
    rows = [copy.copy(r) for r in rows]
    not_built = sorted({r.glyph_name for r in rows if r.glyph_name not in font_glyphs})
    rows = [r for r in rows if r.glyph_name in font_glyphs]
    for r in rows:
        if r.vert_variant and r.vert_variant not in font_glyphs:
            r.vert_variant = ""
    c2g = resolve_char_to_glyph_name(rows)
    missing: dict[str, list[str]] = {}
    lacking: set[str] = set()
    for r in rows:
        for f in ("simplified", "traditional"):
            v = getattr(r, f)
            gone = {ch for ch in v if c2g.get(ch) not in font_glyphs}
            if gone:
                missing.setdefault(r.glyph_name, []).append(v)
                lacking |= gone
                setattr(r, f, "")
    d = copy.deepcopy(design)
    for a in d.get("areas", {}).values():
        a["glyphs"] = [g for g in a.get("glyphs", []) if g in font_glyphs]
    return rows, d, not_built, missing, lacking


_SOURCE: dict = {}


def _source_font() -> TTFont | None:
    """The base font a build subsets (TW-Kai), loaded once; None when it isn't on this machine."""
    p = config.SOURCE_FONT
    if not p.exists():
        return None
    mtime = p.stat().st_mtime
    if _SOURCE.get("mtime") != mtime:
        f = TTFont(str(p), lazy=True)
        _SOURCE.update(mtime=mtime, font=f, cmap=f.getBestCmap())
    return _SOURCE["font"]


def _copy_chars(font: TTFont, rows: list[GlyphRow]) -> list[str]:
    """Copy the Chinese characters the spellings use that `font` lacks from the base font, as
    build_base() keeps them (outlines as they are, the name resolve_char_to_glyph_name gives);
    return the ones copied."""
    import copy as _copy
    from . import glyphs
    c2g = resolve_char_to_glyph_name(rows)
    have = set(font.getGlyphOrder())
    cmap = font.getBestCmap() or {}
    want = sorted({ch for r in rows for ch in r.simplified + r.traditional
                   if c2g.get(ch) not in have and ord(ch) not in cmap})
    src = _source_font() if want else None
    if src is None:
        return []
    added = []
    for ch in want:
        name = _SOURCE["cmap"].get(ord(ch))
        if not name:
            continue                                    # the base font hasn't got it either
        g = src["glyf"][name]
        if g.isComposite():
            continue
        g = _copy.deepcopy(g)
        g.expand(src["glyf"])
        advance, lsb = src["hmtx"][name]
        glyphs.add_glyph(font, c2g[ch], g, advance=advance, lsb=lsb, codepoint=ord(ch))
        added.append(ch)
    return added


def _draw_in(font: TTFont, names: list[str], svg: Callable[[str], str | None]) -> list[str]:
    """Add the glyphs `names` the font hasn't got from their SVGs, as a build would (no advance,
    lsb = xMin), each at the next free private-use code point; return the ones added."""
    from . import glyphs
    if not names:
        return []
    have = set(font.getGlyphOrder())
    gs = font.getGlyphSet()
    code = max([c for t in font["cmap"].tables for c in t.cmap] + [config.COMPONENT_GLYPHS_BASE]) + 1
    added = []
    for n in names:
        text = None if n in have else svg(n)
        if not text:
            continue
        try:
            g = glyphs.svg_to_ttglyph(io.StringIO(text), gs)
        except Exception:  # noqa: BLE001 -- a drawing the build couldn't read either: leave it out
            continue
        xmin = min((x for x, y in g.coordinates), default=0) if g.numberOfContours else 0
        glyphs.add_glyph(font, n, g, advance=0, lsb=xmin, codepoint=code)
        code += 1
        added.append(n)
    return added


class PreviewFonts:
    """A few compiled preview fonts, keyed by (base font, rows, design areas, drawn-in SVGs)."""

    KEEP = 6

    def __init__(self):
        self.lock = threading.Lock()
        self.cache: OrderedDict[str, Preview] = OrderedDict()
        self._base: tuple[str, float, bytes] | None = None

    def _glyph_names(self, path: Path) -> set:
        """The base font's glyph names (cached with its bytes)."""
        b = self._base_bytes(path)
        if getattr(self, "_names_for", None) is not b:
            self._names_for, self._names = b, set(TTFont(io.BytesIO(b)).getGlyphOrder())
        return self._names

    def by_key(self, key: str) -> Preview | None:
        with self.lock:
            return self.cache.get(key)

    def _base_bytes(self, path: Path) -> bytes:
        mtime = path.stat().st_mtime
        if not self._base or self._base[0] != str(path) or self._base[1] != mtime:
            self._base = (str(path), mtime, path.read_bytes())
        return self._base[2]

    def get(self, base_font: Path, rows: list[GlyphRow], design: dict,
            svg: Callable[[str], str | None] | None = None, gpos: bool = False) -> Preview:
        """`svg(name)`: the SVG text of a glyph the font may not have, or None; `gpos`: compile the
        positioning rules too (a font that draws words, not only types them)."""
        import time

        import uharfbuzz as hb
        with self.lock:
            return self._get(base_font, rows, design, svg, gpos, time, hb)

    def _get(self, base_font, rows, design, svg, gpos, time, hb) -> Preview:
        wanted = sorted({n for r in rows for n in (r.glyph_name, r.vert_variant) if n}
                        | {g for a in design.get("areas", {}).values() for g in a.get("glyphs", [])})
        missing = [n for n in wanted if n not in self._glyph_names(base_font)]
        drawings = {n: t for n in missing if svg and (t := svg(n))}
        key = hashlib.sha256(json.dumps([gpos, {n: hashlib.sha256(t.encode()).hexdigest() for n, t in drawings.items()},
            config.SOURCE_FONT.exists(),
            str(base_font), base_font.stat().st_mtime,
            [[r.glyph_name, r.vert_variant, r.common, r.latin, r.latin_alt, r.simplified, r.traditional,
              sorted(r.areas)] for r in rows],
            {n: a.get("glyphs", []) for n, a in design.get("areas", {}).items()},
            [l.get("slots") for l in design.get("layouts", [])],     # which glyphs are vertical-only
        ], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        t0 = time.time()
        font = TTFont(io.BytesIO(self._base_bytes(base_font)))
        drawn = _draw_in(font, sorted(drawings), drawings.get)
        copied = _copy_chars(font, rows)
        font_glyphs = set(font.getGlyphOrder())
        srows, sdesign, not_built, missing_chars, lacking = _shapeable(rows, design, font_glyphs)
        parsed = schema.parse_design(sdesign)
        token = features._DESIGN_OVERRIDE.set(parsed)
        try:
            lines = features.gen_gsub(srows, validate=False)
            vertical_only = set(features.vertical_only_glyphs())
        finally:
            features._DESIGN_OVERRIDE.reset(token)
        tables = ["GSUB"]
        if gpos:
            from .positioning.emit import gen_gpos
            lines = lines + [""] + gen_gpos(parsed).lines
            tables.append("GPOS")
        for t in tables:
            if t in font:
                del font[t]
        addOpenTypeFeaturesFromString(font, "\n".join(lines) + "\n", tables=tables)
        buf = io.BytesIO()
        font.save(buf)
        p = Preview(hb_font=hb.Font(hb.Face(buf.getvalue())), glyphs=font_glyphs,
                    not_built=not_built, missing_chars=missing_chars,
                    vertical_only=vertical_only, seconds=round(time.time() - t0, 3),
                    drawn=drawn, key=key, font_bytes=buf.getvalue(), lacking=lacking, copied=copied)
        self.cache[key] = p
        while len(self.cache) > self.KEEP:
            self.cache.popitem(last=False)
        return p


FONTS = PreviewFonts()


# ---------------------------------------------------------------- shaping

def shape(p: Preview, words: list[str]) -> list[dict]:
    """Glyph names per word, with the source text of each glyph's cluster."""
    import uharfbuzz as hb
    out = []
    for w in words:
        buf = hb.Buffer()
        buf.add_str(w)
        buf.guess_segment_properties()
        hb.shape(p.hb_font, buf, {"liga": True, "kern": False})
        infos = buf.glyph_infos
        # uharfbuzz's add_str fills the buffer with code points, so clusters are
        # character indexes into `w`
        starts = sorted({i.cluster for i in infos})
        text_of = {s: w[s:(starts[k + 1] if k + 1 < len(starts) else len(w))] for k, s in enumerate(starts)}
        glyphs = [p.hb_font.glyph_to_string(i.codepoint) for i in infos]
        out.append({"word": w, "glyphs": glyphs, "texts": [text_of.get(i.cluster, "") for i in infos]})
    return out


def roundtrip(p: Preview, rows: list[GlyphRow]) -> list[dict]:
    """Each spelling typed alone must give its own glyph (after the colon the font adds
    for a glyph only a vertical word can place); a vertical form must come out after a
    colon from its partner's first spelling. Returns the failures."""
    checks = []
    for r in rows:
        if r.glyph_name not in p.glyphs:
            continue
        for f in SPELLING_FIELDS:
            v = getattr(r, f)
            if v and v not in p.missing_chars.get(r.glyph_name, []):
                colon = ["blank_colon"] if r.glyph_name in p.vertical_only else []
                checks.append((r.glyph_name, f, v, colon + [r.glyph_name]))
        if r.vert_variant and r.vert_variant in p.glyphs:
            first = next((getattr(r, f) for f in SPELLING_FIELDS if getattr(r, f)
                          and getattr(r, f) not in p.missing_chars.get(r.glyph_name, [])), None)
            if first:
                checks.append((r.vert_variant, "vertical", ":" + first, ["blank_colon", r.vert_variant]))
    shaped = shape(p, [c[2] for c in checks])
    fails = []
    for (glyph, f, v, want), s in zip(checks, shaped):
        if s["glyphs"] != want:
            fails.append({"glyph": glyph, "field": f, "value": v, "got": s["glyphs"], "texts": s["texts"],
                          "message": f"Typing “{v}” gives {' + '.join(s['glyphs'])}, not {glyph}."})
    return fails
