"""Rename or delete drawn glyphs everywhere the inputs name them (the local Builder, admin only).

A glyph's name is its id: the SVG's file name, its components.csv row (and any `vert_variant`
pointing at it), its areas and the glyph conditions of spacing rows in design.json, and
edge_cases.fea. A rename changes all of those for any number of glyphs at once (a whole naming
scheme, swaps included; check_renames() vets the set first), a delete removes one glyph from all
of them. Both refuse while design.json or components.csv changed since the app loaded them, and
keep character codes stable (glyph_ids.py): renamed glyphs keep theirs, a deleted glyph's is
retired.

The build's code spells some glyphs out by the names they had when it was written (md_7,
lg_gou: features.py); the feature file it writes is translated through the recorded renames, so
those can be renamed too. They can't be deleted: hardcoded() finds them by generating the
feature file with every glyph renamed and seeing which names are still in it. Only the control
glyphs (config.CONTROL_GLYPHS) can't be renamed.

names_csv() is the list to rename from in a spreadsheet: glyph_name and new_name, plus columns
that say which glyph each row is.
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


def rename_lock(name: str) -> str | None:
    if name in config.CONTROL_GLYPHS:
        return f"{name} is a control glyph with a fixed character code."
    return None


def delete_lock(name: str) -> str | None:
    if name in config.CONTROL_GLYPHS:
        return f"{name} is a control glyph with a fixed character code."
    if name in hardcoded({name}):
        return f"The font's build code uses {name} (jzpbuild/features.py), so it can't be deleted."
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
        "locked": {"rename": rename_lock(name), "delete": delete_lock(name)},
    }


def _check_hashes(design_hash: str | None, csv_hash: str | None) -> tuple[str, str]:
    design_text = config.DESIGN_JSON.read_text(encoding="utf-8")
    csv_text = config.COMPONENTS_CSV.read_text(encoding="utf-8-sig")
    if design_hash is not None and design_hash != _hash(design_text):
        raise GlyphEditConflict("design.json changed on disk since it was loaded")
    if csv_hash is not None and csv_hash != _hash(csv_text):
        raise GlyphEditConflict("components.csv changed on disk since it was loaded")
    return design_text, csv_text


NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
BAD_NAME = "glyph names use letters, digits, '_', '-' and '.', e.g. md_9 or lg_gou"


def translate(name: str, ids: dict | None = None) -> str:
    """A name from before any recorded rename, as the glyph is called now."""
    return glyph_ids.current(name, ids)


def _existing() -> set[str]:
    d = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    rows = _rows(config.COMPONENTS_CSV.read_text(encoding="utf-8-sig"))
    return (_svg_names() | set(config.CONTROL_GLYPHS) | {r["glyph_name"] for r in rows}
            | {g for a in d.get("areas", {}).values() for g in a.get("glyphs", [])})


def check_renames(names: dict[str, str]) -> dict:
    """Vet a set of renames (old -> new) as one: what each pair would do or why it can't. A new
    name may be one another glyph in the set is leaving (a swap); an old name of a glyph before
    an earlier rename can only go back to that glyph."""
    names = {o.strip(): n.strip() for o, n in names.items() if o.strip() and n.strip() and o.strip() != n.strip()}
    ids = glyph_ids.load()
    svgs, existing, history = _svg_names(), _existing(), glyph_ids.renamed_from(ids)
    by_new: dict[str, list[str]] = {}
    for o, n in names.items():
        by_new.setdefault(n, []).append(o)
    pairs = []
    for o, n in names.items():
        if rename_lock(o):
            why = rename_lock(o)
        elif o not in svgs:
            why = f"There is no glyph {o}."
        elif not NAME.fullmatch(n) or n.endswith("."):
            why = BAD_NAME
        elif len(by_new[n]) > 1:
            why = f"{n} is the new name of {' and '.join(by_new[n])}."
        elif n in existing and n not in names:
            why = f"{n} is already a glyph."
        elif n in history and glyph_ids.current(n, ids) != o:
            why = f"{n} was the name of a glyph before a rename; drafts may still use it for that glyph."
        else:
            why = None
        pairs.append({"from": o, "to": n, "problem": why})
    problems = [p["problem"] for p in pairs if p["problem"]]
    if not problems and names:
        left = _left_behind(names, ids)
        problems += [f"The font would still use {o} after the rename (jzpbuild/features.py)." for o in left]
    return {"ok": not problems, "pairs": pairs, "problems": problems}


def _left_behind(names: dict[str, str], ids: dict) -> list[str]:
    """Old names the feature file would still hold after renaming `names` (should be none)."""
    from . import features
    from .positioning import emit
    ren = lambda g: names.get(g, g)                    # noqa: E731
    d = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    _rename_in_design(d, ren)
    rows = [dataclasses.replace(r, glyph_name=ren(r.glyph_name), vert_variant=ren(r.vert_variant))
            for r in data.load_components()]
    after = {**ids, "renamed": [*ids["renamed"], {"date": "", "names": names}]}
    design = schema.parse_design(d)
    tok = features._DESIGN_OVERRIDE.set(design)
    try:
        lines = features.gen_gsub(rows, validate=False, ids=after) + emit.gen_gpos(design).lines
    finally:
        features._DESIGN_OVERRIDE.reset(tok)
    tokens = set(TOKEN.findall(re.sub(r"#.*", "", "\n".join(lines))))
    return sorted((set(names) - set(names.values())) & tokens)


def rename_many(names: dict[str, str], design_hash: str | None = None, csv_hash: str | None = None) -> dict:
    """Rename glyphs everywhere, all at once. Returns the new hashes of design.json and components.csv."""
    check = check_renames(names)
    if not check["ok"]:
        raise GlyphEditError(check["problems"][0] if len(check["problems"]) == 1
                             else f"{len(check['problems'])} problems: " + " ".join(check["problems"][:5]))
    m = {p["from"]: p["to"] for p in check["pairs"]}
    if not m:
        raise GlyphEditError("No names to change.")
    design_text, csv_text = _check_hashes(design_hash, csv_hash)
    ren = lambda g: m.get(g, g)          # noqa: E731
    d = json.loads(design_text)
    _rename_in_design(d, ren)
    schema.parse_design(d)                                            # validates
    rows = _rows(csv_text)
    for r in rows:
        r["glyph_name"], r["vert_variant"] = ren(r["glyph_name"]), ren(r["vert_variant"])
    edge = config.EDGE_CASES_FEA.read_text(encoding="utf-8")
    new_edge = TOKEN.sub(lambda t: ren(t.group(0)), edge)

    new_design, new_csv = schema.dump_design(d), _csv(rows)
    config.DESIGN_JSON.write_text(new_design, encoding="utf-8")
    config.COMPONENTS_CSV.write_text(new_csv, encoding="utf-8")
    if new_edge != edge:
        config.EDGE_CASES_FEA.write_text(new_edge, encoding="utf-8")
    for o in m:                                                       # two steps, so swaps work
        _svg(o).rename(config.COMPONENTS_DIR / f"{o}.svg.renaming")
    for o, n in m.items():
        (config.COMPONENTS_DIR / f"{o}.svg.renaming").rename(_svg(n))
    glyph_ids.rename(m)
    data.cache_clear_all()
    return {"ok": True, "renamed": m, "design_hash": _hash(new_design), "csv_hash": _hash(new_csv)}


def rename(old: str, new: str, design_hash: str | None = None, csv_hash: str | None = None) -> dict:
    """Rename one glyph everywhere."""
    if not new.strip() or new.strip() == old:
        raise GlyphEditError("That is already its name.")
    return {**rename_many({old: new}, design_hash, csv_hash), "name": new.strip()}


NAMES_CSV_FIELDS = ("glyph_name", "new_name", "areas", "latin", "simplified", "traditional", "pinyin", "code")


def names_csv() -> str:
    """Every drawn glyph, one row each, for renaming in a spreadsheet: fill in new_name where a
    name should change (empty, or the same name, leaves it); the other columns only say which
    glyph the row is and are not read back. Starts with a BOM so spreadsheets read it as UTF-8."""
    d = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    rows = {r["glyph_name"]: r for r in _rows(config.COMPONENTS_CSV.read_text(encoding="utf-8-sig"))}
    codes = glyph_ids.code_map(_svg_names())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(NAMES_CSV_FIELDS), lineterminator="\n")
    w.writeheader()
    for g in sorted(_svg_names(), key=lambda n: codes[n]):
        r = rows.get(g, {})
        w.writerow({"glyph_name": g, "new_name": "",
                    "areas": " ".join(a for a, v in d.get("areas", {}).items() if g in v.get("glyphs", [])),
                    **{k: r.get(k, "") for k in ("latin", "simplified", "traditional", "pinyin")},
                    "code": f"U+{codes[g]:04X}"})
    return "\ufeff" + buf.getvalue()


def renames_from_csv(text: str) -> dict[str, str]:
    """glyph_name -> new_name from a names CSV (the other columns are ignored)."""
    rd = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not rd.fieldnames or "glyph_name" not in rd.fieldnames or "new_name" not in rd.fieldnames:
        raise GlyphEditError("The CSV needs the columns glyph_name and new_name (download the list to start from).")
    return {(r.get("glyph_name") or "").strip(): (r.get("new_name") or "").strip() for r in rd}


def _check_glyph(name: str) -> None:
    if not _svg(name).exists():
        raise GlyphEditError(f"There is no glyph {name}.")
    why = delete_lock(name)
    if why:
        raise GlyphEditError(why)


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
