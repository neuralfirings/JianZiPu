"""Glyph identity: each drawn glyph's character code, kept in inputs/glyph_ids.json.

A component glyph's code (Private Use Area, from config.COMPONENT_GLYPHS_BASE) is what a
document stores when it holds the glyph itself rather than its spelling, so it must never move:

    {
      "codes":   {"lg_ban": "E2F5", ...},            # name -> code (hex), one per glyph
      "retired": {"E3B0": "md_old"},                 # codes of deleted glyphs, never handed out again
      "renamed": [{"from": "mod_fy", "to": "mod_fanyin", "date": "2026-10-22"}]
    }

The build (glyphs.py) gives a glyph its pinned code; a glyph with none (an SVG added outside the
Builder, or one in a tester's draft) gets the next code after every pinned and retired one, in
file-name order, which is what the local Builder pins when it saves the file. `renamed` is the
record drafts and Change Requests made before a rename are translated with (the app's
renames.ts), so an old name is never used again for a different glyph.
"""

from __future__ import annotations

import json
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


def rename(old: str, new: str, d: dict | None = None, today: str | None = None) -> dict:
    """The glyph keeps its code under its new name, and the rename is recorded. Writes the file."""
    d = load() if d is None else d
    if old in d["codes"]:
        d["codes"][new] = d["codes"].pop(old)
    d["renamed"].append({"from": old, "to": new, "date": today or date.today().isoformat()})
    save(d)
    return d


def renamed_from(d: dict | None = None) -> set[str]:
    """Names a glyph had before a rename: never used again (drafts still say them)."""
    d = load() if d is None else d
    return {r["from"] for r in d["renamed"]}
