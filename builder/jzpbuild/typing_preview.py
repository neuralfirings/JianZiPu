"""Spelling preview for the Builder's Typing view.

Generates the GSUB half of the feature file from *unsaved* spelling rows and an
unsaved design, compiles it into a copy of the last built font (GSUB only, in
memory, about half a second), and shapes with HarfBuzz. The same font answers
three questions without a Build:

- `shape(words)`: what typed words become (glyph names, plus the source text
  of every glyph so the app can show leftover letters and missing characters);
- `roundtrip()`: does every spelling, typed alone, give its own glyph?
- `issues(rows)`: clashes and malformed spellings, which pause Save.

Anything the last build doesn't contain (a glyph whose SVG was never built, a
Chinese character the font doesn't carry yet) is left out of the preview font
and reported, never guessed.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont

from . import config, features
from .data import GlyphRow, resolve_char_to_glyph_name
from .positioning import schema

ROW_FIELDS = ("glyph_name", "vert_variant", "common", "latin", "latin_alt",
              "simplified", "traditional", "pinyin", "glossary")   # pinyin, glossary: not typed (glossary.py)
SPELLING_FIELDS = ("latin", "latin_alt", "simplified", "traditional")
LATIN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
HAN_RE = re.compile(r"^[㐀-鿿豈-﫿\U00020000-\U0002ffff]+$")
RESERVED = {"点", "點", "徽", "。", "，"}


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
                       if v[0].isdigit() else "use only letters a–z, A–Z and digits")
                errors.append({"kind": "invalid", "glyph": r.glyph_name, "field": f, "value": v,
                               "message": f"“{v}”: {why}."})
        for f in ("simplified", "traditional"):
            v = getattr(r, f)
            if v and v in RESERVED:
                errors.append({"kind": "invalid", "glyph": r.glyph_name, "field": f, "value": v,
                               "message": f"“{v}” alone marks a position; it can't type a glyph."})
            elif v and not HAN_RE.match(v):
                errors.append({"kind": "invalid", "glyph": r.glyph_name, "field": f, "value": v,
                               "message": f"“{v}”: Chinese characters only."})
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


def _shapeable(rows: list[GlyphRow], design: dict, font_glyphs: set) -> tuple[list[GlyphRow], dict, list, dict]:
    """Drop what the font can't carry yet, so the generated rules compile."""
    rows = [copy.copy(r) for r in rows]
    not_built = sorted({r.glyph_name for r in rows if r.glyph_name not in font_glyphs})
    rows = [r for r in rows if r.glyph_name in font_glyphs]
    for r in rows:
        if r.vert_variant and r.vert_variant not in font_glyphs:
            r.vert_variant = ""
    c2g = resolve_char_to_glyph_name(rows)
    missing: dict[str, list[str]] = {}
    for r in rows:
        for f in ("simplified", "traditional"):
            v = getattr(r, f)
            if v and any(c2g.get(ch) not in font_glyphs for ch in v):
                missing.setdefault(r.glyph_name, []).append(v)
                setattr(r, f, "")
    d = copy.deepcopy(design)
    for a in d.get("areas", {}).values():
        a["glyphs"] = [g for g in a.get("glyphs", []) if g in font_glyphs]
    return rows, d, not_built, missing


class PreviewFonts:
    """A few compiled preview fonts, keyed by (base font, rows, design areas)."""

    KEEP = 6

    def __init__(self):
        self.lock = threading.Lock()
        self.cache: OrderedDict[str, Preview] = OrderedDict()
        self._base: tuple[str, float, bytes] | None = None

    def _base_bytes(self, path: Path) -> bytes:
        mtime = path.stat().st_mtime
        if not self._base or self._base[0] != str(path) or self._base[1] != mtime:
            self._base = (str(path), mtime, path.read_bytes())
        return self._base[2]

    def get(self, base_font: Path, rows: list[GlyphRow], design: dict) -> Preview:
        import time

        import uharfbuzz as hb
        key = hashlib.sha256(json.dumps([
            str(base_font), base_font.stat().st_mtime,
            [[r.glyph_name, r.vert_variant, r.common, r.latin, r.latin_alt, r.simplified, r.traditional,
              sorted(r.areas)] for r in rows],
            {n: a.get("glyphs", []) for n, a in design.get("areas", {}).items()},
            [l.get("slots") for l in design.get("layouts", [])],     # which glyphs are vertical-only
        ], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            t0 = time.time()
            font = TTFont(io.BytesIO(self._base_bytes(base_font)))
            font_glyphs = set(font.getGlyphOrder())
            srows, sdesign, not_built, missing = _shapeable(rows, design, font_glyphs)
            token = features._DESIGN_OVERRIDE.set(schema.parse_design(sdesign))
            try:
                fea = "\n".join(features.gen_gsub(srows, validate=False)) + "\n"
                vertical_only = set(features.vertical_only_glyphs())
            finally:
                features._DESIGN_OVERRIDE.reset(token)
            if "GSUB" in font:
                del font["GSUB"]
            addOpenTypeFeaturesFromString(font, fea, tables=["GSUB"])
            buf = io.BytesIO()
            font.save(buf)
            p = Preview(hb_font=hb.Font(hb.Face(buf.getvalue())), glyphs=font_glyphs,
                        not_built=not_built, missing_chars=missing,
                        vertical_only=vertical_only, seconds=round(time.time() - t0, 3))
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
