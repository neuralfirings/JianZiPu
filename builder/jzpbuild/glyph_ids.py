"""Glyph identity: each drawn glyph's character code, kept in inputs/glyph_ids.json.

A component glyph's code (Private Use Area, from config.COMPONENT_GLYPHS_BASE) is what a
document stores when it holds the glyph itself rather than its spelling, so it must never move:

    {
      "codes":   {"lg_ban": "E2F5", ...},            # name -> code (hex), one per glyph
      "retired": {"E3B0": "md_old"},                 # codes of deleted glyphs, never handed out again
      "renamed": [{"date": "2026-10-22", "names": {"mod_fy": "mod_fanyin"}}]
    }

The build (glyphs.py) gives a glyph its pinned code; a glyph with none (an SVG added outside the
Builder, or one in a tester's draft) gets the next code after every pinned and retired one, in
file-name order, which is what the local Builder pins when it saves the file.

`renamed` holds one entry per rename, oldest first; an entry renames all its names at once (a
whole naming scheme, or a swap). Drafts and Change Requests made before a rename are translated
with it (the app's renames.ts), and so is the feature file the build's code writes: features.py
and gpos.py spell out glyphs by the names they had when the code was written (md_7, lg_gou), and
translate_lines() turns those into the names the glyphs have now. So an old name is never used
again for a different glyph.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from . import config


def _path() -> Path:
    return config.GLYPH_IDS_JSON


def load() -> dict:
    """The file as a dict (empty sections when it doesn't exist yet)."""
    p = _path()
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return {"codes": dict(d.get("codes", {})), "retired": dict(d.get("retired", {})),
            "renamed": list(d.get("renamed", []))}


def save(d: dict) -> None:
    out = {"codes": dict(sorted(d["codes"].items(), key=lambda kv: int(kv[1], 16))),
           "retired": dict(sorted(d["retired"].items(), key=lambda kv: int(kv[0], 16))),
           "renamed": d["renamed"]}
    _path().write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hex(code: int) -> str:
    return f"{code:04X}"


def _taken(d: dict) -> set[int]:
    return {int(c, 16) for c in d["codes"].values()} | {int(c, 16) for c in d["retired"]}


def _file_order(names) -> list[str]:
    """The order the build reads the SVGs in (sorted file names: md_1.1.svg before md_1.svg)."""
    return sorted(names, key=lambda n: f"{n}.svg")


def code_map(names, d: dict | None = None) -> dict[str, int]:
    """name -> code for the glyphs being built: pinned codes, then the next free ones."""
    d = load() if d is None else d
    seen: dict[int, str] = {}
    for n, c in d["codes"].items():
        code = int(c, 16)
        if code in seen:
            raise ValueError(f"{config.GLYPH_IDS_JSON.name}: {seen[code]} and {n} share the code {c}")
        seen[code] = n
    nxt = max(_taken(d) | {config.COMPONENT_GLYPHS_BASE - 1}) + 1
    out = {}
    for n in _file_order(names):
        if n in d["codes"]:
            out[n] = int(d["codes"][n], 16)
        else:
            out[n], nxt = nxt, nxt + 1
    return out


def pin(name: str, d: dict | None = None) -> dict:
    """Give a new glyph the next free code (no-op when it has one). Writes the file."""
    d = load() if d is None else d
    if name not in d["codes"]:
        d["codes"][name] = _hex(max(_taken(d) | {config.COMPONENT_GLYPHS_BASE - 1}) + 1)
        save(d)
    return d


def retire(name: str, d: dict | None = None) -> dict:
    """A deleted glyph's code is kept out of use for good. Writes the file."""
    d = load() if d is None else d
    c = d["codes"].pop(name, None)
    if c is not None:
        d["retired"][c] = name
        save(d)
    return d


def rename(names: dict[str, str], d: dict | None = None, today: str | None = None) -> dict:
    """Glyphs keep their codes under their new names (all at once, so swaps work), and the
    renames are recorded as one entry. Writes the file."""
    d = load() if d is None else d
    moved = {new: d["codes"][old] for old, new in names.items() if old in d["codes"]}
    for old in names:
        d["codes"].pop(old, None)
    d["codes"].update(moved)
    d["renamed"].append({"date": today or date.today().isoformat(), "names": dict(names)})
    save(d)
    return d


def renamed_from(d: dict | None = None) -> set[str]:
    """Names a glyph had before a rename: never used again (drafts still say them)."""
    d = load() if d is None else d
    return {old for r in d["renamed"] for old in r["names"]}


def current(name: str, d: dict | None = None) -> str:
    """A name from before any recorded rename, as the glyph is called now."""
    for r in (load() if d is None else d)["renamed"]:
        name = r["names"].get(name, name)
    return name


TOKEN = re.compile(r"[A-Za-z0-9_.]+")


def translate_lines(lines: list[str], d: dict | None = None) -> list[str]:
    """Feature-file lines with every old glyph name (as the build's code writes them) changed to
    the glyph's name now. Names that are current already pass through unchanged."""
    d = load() if d is None else d
    old = renamed_from(d)
    if not old:
        return lines
    sub = lambda m: current(m.group(0), d) if m.group(0) in old else m.group(0)      # noqa: E731
    return [TOKEN.sub(sub, line) for line in lines]
