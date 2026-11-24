"""Characters typed with the glyph editor's Text tool: their outlines in the base font (TW-Kai).

`outlines(text)` -> each character's outline as SVG path data in the base font's own units, y down
(SVG's way), the baseline at y 0 and the character's origin at x 0, with its advance; characters the
base font has no glyph for come back in `missing`. The editor scales and places them, then they're
ordinary shapes. Served by GET /api/base-font/outline?text=… (webserver.py), locally and online:
the hosted server downloads the same file at start (hosted.fetch_base_font).
"""

from __future__ import annotations

import threading
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from . import config

MAX_CHARS = 20          # one request's characters: a word or two, not a page


class NoBaseFont(Exception):
    """The base font file isn't on this server."""


_lock = threading.Lock()
_cache: dict = {}       # path -> (mtime, TTFont, cmap)


def _font(path: Path):
    try:
        mtime = path.stat().st_mtime
    except OSError:
        raise NoBaseFont(f"The base font isn't here: copy {path.name} into builder/{path.parent.name}/.") from None
    with _lock:
        hit = _cache.get(path)
        if hit and hit[0] == mtime:
            return hit[1], hit[2]
        font = TTFont(path, lazy=True)
        cmap = font.getBestCmap() or {}
        _cache.clear()
        _cache[path] = (mtime, font, cmap)
        return font, cmap


def _chars(text: str) -> list[str]:
    """The characters to draw, in order: whitespace dropped, at most MAX_CHARS."""
    return [c for c in text if not c.isspace()][:MAX_CHARS]


def outlines(text: str, path: Path | None = None) -> dict:
    font, cmap = _font(Path(path or config.SOURCE_FONT))
    chars, missing = [], []
    with _lock:                      # a lazily loaded TTFont isn't safe to read from two threads at once
        gs = font.getGlyphSet()
        hmtx = font["hmtx"]
        for ch in _chars(text):
            name = cmap.get(ord(ch))
            if name is None:
                if ch not in missing:
                    missing.append(ch)
                continue
            pen = SVGPathPen(gs, ntos=lambda v: f"{v:g}")
            gs[name].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))     # y up (font) -> y down (SVG)
            chars.append({"char": ch, "d": pen.getCommands(), "advance": hmtx[name][0]})
        upm = font["head"].unitsPerEm
    return {"ok": True, "upm": upm, "chars": chars, "missing": missing, "font": Path(path or config.SOURCE_FONT).stem}
