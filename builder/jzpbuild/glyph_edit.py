"""Rename or delete a drawn glyph everywhere the inputs name it (the local Builder, admin only).

A glyph's name is its id: the SVG's file name, its components.csv row (and any `vert_variant`
pointing at it), its areas and the glyph conditions of spacing rules in design.json, and
edge_cases.fea. Both operations change all of those in one go, refuse while design.json or
components.csv changed since the app loaded them, and keep the glyph's character code stable
(glyph_ids.py): a renamed glyph keeps its code, a deleted glyph's code is retired.

Names the build's own code spells out (the hui and decimal glyphs, the right-hand techniques,
the typed symbols: features.py) can't be renamed or deleted here; hardcoded() finds them by
generating the feature file with every glyph renamed and seeing which names are still in it.
"""

from __future__ import annotations

import csv
import dataclasses
import hashlib
import io
import json
import re
from pathlib import Path

from . import config, data, glyph_ids
from .positioning import schema

TOKEN = re.compile(r"[A-Za-z0-9_.]+")
FIELDS = ("glyph_name", "vert_variant", "common", "latin", "latin_alt", "simplified", "traditional", "pinyin")


class GlyphEditError(ValueError):
    pass


class GlyphEditConflict(Exception):
    pass


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _svg(name: str) -> Path:
    return config.COMPONENTS_DIR / f"{name}.svg"


def _svg_names() -> set[str]:
    return {p.stem for p in config.COMPONENTS_DIR.glob("*.svg")}


def hardcoded(names: set[str] | None = None) -> set[str]:
    """Glyph names the build's code itself writes into the feature file (not from the inputs)."""
    from . import features
    from .positioning import emit
    names = _svg_names() if names is None else set(names)
    ren = lambda g: f"zz_renamed_{g}" if g in names else g          # noqa: E731
    d = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    _rename_in_design(d, ren)
    rows = [dataclasses.replace(r, glyph_name=ren(r.glyph_name), vert_variant=ren(r.vert_variant))
            for r in data.load_components()]
    design = schema.parse_design(d)
    tok = features._DESIGN_OVERRIDE.set(design)
    try:
        lines = features.gen_gsub(rows, validate=False) + emit.gen_gpos(design).lines
    finally:
        features._DESIGN_OVERRIDE.reset(tok)
    text = re.sub(r"#.*", "", "\n".join(lines))
    return (names & set(TOKEN.findall(text))) | (names & set(config.CONTROL_GLYPHS))


def locked_reason(name: str) -> str | None:
    if name in config.CONTROL_GLYPHS:
        return f"{name} is a control glyph with a fixed character code."
    if name in hardcoded({name}):
        return f"The font's build code uses {name} by name (jzpbuild/features.py), so it can't be renamed or deleted here."
    return None


def _rename_in_design(d: dict, ren) -> None:
    for a in d.get("areas", {}).values():
        a["glyphs"] = [ren(g) for g in a.get("glyphs", [])]
    for l in d.get("layouts", []):
        for r in l.get("relationships", []):
            if isinstance(r.get("gap"), list):
                for e in r["gap"]:
                    for k in ("when_base", "when_elem"):
                        if e.get(k) is not None:
                            e[k] = [ren(g) for g in e[k]]


def _drop_from_design(d: dict, name: str) -> int:
    """Take `name` out of every area and spacing condition. A spacing row that only applied to
    `name` can never match again, so it goes; returns how many rows went."""
    dropped = 0
    for a in d.get("areas", {}).values():
        a["glyphs"] = [g for g in a.get("glyphs", []) if g != name]
    for l in d.get("layouts", []):
        for r in l.get("relationships", []):
            if not isinstance(r.get("gap"), list):
                continue
            keep = []
            for e in r["gap"]:
                gone = False
                for k in ("when_base", "when_elem"):
                    if e.get(k) and name in e[k]:
                        e[k] = [g for g in e[k] if g != name]
                        gone = gone or not e[k]
                if gone:
                    dropped += 1
                else:
                    keep.append(e)
            r["gap"] = keep
    return dropped


def _rows(text: str) -> list[dict]:
    return [{k: (rec.get(k) or "").strip() for k in FIELDS} for rec in csv.DictReader(io.StringIO(text))]


def _csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(FIELDS), lineterminator="\n")
    w.writeheader()
    for r in rows:
        if r["glyph_name"] and any(r[k] for k in FIELDS if k != "glyph_name"):
            w.writerow(r)
    return buf.getvalue()


def uses(name: str) -> dict:
    """Where `name` is used, for the Rename and Delete dialogs."""
    d = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    rows = _rows(config.COMPONENTS_CSV.read_text(encoding="utf-8-sig"))
    rules = 0
    for l in d.get("layouts", []):
        for r in l.get("relationships", []):
            if isinstance(r.get("gap"), list):
                rules += sum(1 for e in r["gap"] if name in (e.get("when_base") or []) + (e.get("when_elem") or []))
    only = sum(1 for l in d.get("layouts", []) for r in l.get("relationships", []) if isinstance(r.get("gap"), list)
               for e in r["gap"] if (e.get("when_base") == [name]) or (e.get("when_elem") == [name]))
    ids = glyph_ids.load()
    return {
        "name": name, "svg": _svg(name).exists(),
        "spelling": any(r["glyph_name"] == name for r in rows),
        "vertical_of": [r["glyph_name"] for r in rows if r["vert_variant"] == name],
        "areas": [a for a, v in d.get("areas", {}).items() if name in v.get("glyphs", [])],
        "spacing_rows": rules, "spacing_rows_only": only,
        "edge_cases": name in TOKEN.findall(config.EDGE_CASES_FEA.read_text(encoding="utf-8")),
        "code": ids["codes"].get(name),
        "locked": locked_reason(name),
    }


def _check_hashes(design_hash: str | None, csv_hash: str | None) -> tuple[str, str]:
    design_text = config.DESIGN_JSON.read_text(encoding="utf-8")
    csv_text = config.COMPONENTS_CSV.read_text(encoding="utf-8-sig")
    if design_hash is not None and design_hash != _hash(design_text):
        raise GlyphEditConflict("design.json changed on disk since it was loaded")
    if csv_hash is not None and csv_hash != _hash(csv_text):
        raise GlyphEditConflict("components.csv changed on disk since it was loaded")
    return design_text, csv_text


def _check_glyph(name: str) -> None:
    if not _svg(name).exists():
        raise GlyphEditError(f"There is no glyph {name}.")
    why = locked_reason(name)
    if why:
        raise GlyphEditError(why)


def name_problem(new: str, old: str | None = None) -> str | None:
    """Why `new` can't name a glyph, or None."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", new) or new.endswith("."):
        return "glyph names use letters, digits, '_', '-' and '.', e.g. md_9 or lg_gou"
    if new == old:
        return "That is already its name."
    d = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    rows = _rows(config.COMPONENTS_CSV.read_text(encoding="utf-8-sig"))
    if (_svg(new).exists() or new in config.CONTROL_GLYPHS or any(r["glyph_name"] == new for r in rows)
            or any(new in a.get("glyphs", []) for a in d.get("areas", {}).values())):
        return f"{new} is already a glyph."
    ids = glyph_ids.load()
    if new in glyph_ids.renamed_from(ids) and translate(new, ids) != old:
        return f"{new} was the name of a glyph before a rename; drafts may still use it for that glyph."
    return None


def translate(name: str, ids: dict | None = None) -> str:
    """A name from before any recorded rename, as the glyph is called now."""
    for r in (glyph_ids.load() if ids is None else ids)["renamed"]:
        if name == r["from"]:
            name = r["to"]
    return name


def rename(old: str, new: str, design_hash: str | None = None, csv_hash: str | None = None) -> dict:
    """Rename a glyph everywhere. Returns the new hashes of design.json and components.csv."""
    _check_glyph(old)
    why = name_problem(new, old)
    if why:
        raise GlyphEditError(why)
    design_text, csv_text = _check_hashes(design_hash, csv_hash)
    ren = lambda g: new if g == old else g          # noqa: E731
    d = json.loads(design_text)
    _rename_in_design(d, ren)
    schema.parse_design(d)                                            # validates
    rows = _rows(csv_text)
    for r in rows:
        r["glyph_name"], r["vert_variant"] = ren(r["glyph_name"]), ren(r["vert_variant"])
    edge = config.EDGE_CASES_FEA.read_text(encoding="utf-8")
    new_edge = TOKEN.sub(lambda m: ren(m.group(0)), edge)

    new_design, new_csv = schema.dump_design(d), _csv(rows)
    config.DESIGN_JSON.write_text(new_design, encoding="utf-8")
    config.COMPONENTS_CSV.write_text(new_csv, encoding="utf-8")
    if new_edge != edge:
        config.EDGE_CASES_FEA.write_text(new_edge, encoding="utf-8")
    _svg(old).rename(_svg(new))
    glyph_ids.rename(old, new)
    data.cache_clear_all()
    return {"ok": True, "name": new, "design_hash": _hash(new_design), "csv_hash": _hash(new_csv)}


def delete(name: str, design_hash: str | None = None, csv_hash: str | None = None) -> dict:
    """Delete a glyph and everything that names it; its code is retired."""
    _check_glyph(name)
    if name in TOKEN.findall(config.EDGE_CASES_FEA.read_text(encoding="utf-8")):
        raise GlyphEditError(f"inputs/edge_cases.fea uses {name}; take it out of that file first.")
    design_text, csv_text = _check_hashes(design_hash, csv_hash)
    d = json.loads(design_text)
    dropped = _drop_from_design(d, name)
    schema.parse_design(d)                                            # validates
    rows = [r for r in _rows(csv_text) if r["glyph_name"] != name]
    for r in rows:
        if r["vert_variant"] == name:
            r["vert_variant"] = ""

    new_design, new_csv = schema.dump_design(d), _csv(rows)
    config.DESIGN_JSON.write_text(new_design, encoding="utf-8")
    config.COMPONENTS_CSV.write_text(new_csv, encoding="utf-8")
    _svg(name).unlink()
    glyph_ids.retire(name)
    data.cache_clear_all()
    return {"ok": True, "name": name, "spacing_rows_dropped": dropped,
            "design_hash": _hash(new_design), "csv_hash": _hash(new_csv)}
