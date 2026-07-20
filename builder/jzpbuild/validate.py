"""Pre-build validation of the human-maintained input files.

Catches the uniqueness violations documented in builder/README.md that
would otherwise fail silently at build time — a shadowed spelling, a
dropped glyphRename.csv row, or two characters silently sharing one glyph —
instead of erroring. Run automatically by features.py::gen_gsub() before
any lookups are generated.
"""

from collections import defaultdict

from .data import GlyphRow


class ValidationError(Exception):
    pass


def _dupe_groups(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    """key -> [values] for every key that appears more than once."""
    groups: dict[str, list[str]] = defaultdict(list)
    for k, v in pairs:
        groups[k].append(v)
    return {k: v for k, v in groups.items() if len(v) > 1}


def _latin_keys(r: GlyphRow) -> list[str]:
    keys = []
    if r.latin:
        keys.append(r.latin)
    if r.latin_alt:
        keys.append(r.latin_alt)
    if r.common and len(r.common) > 1 and r.common.isalpha():
        keys.append(r.common)
    return keys


def _is_known_vert_pair(g1: str, g2: str, rows: list[GlyphRow]) -> bool:
    """True if g1/g2 are exactly a {source, vert_variant} pair — the
    intentional pattern where a centered vert-mode glyph (e.g. md_lun)
    deliberately reuses its horizontal counterpart's (lg_lun) spelling,
    since it's only ever reached via @area_to_md_for_vert conversion, never
    typed directly."""
    return any(r.vert_variant and {r.glyph_name, r.vert_variant} == {g1, g2}
               for r in rows)


def _check_spelling_namespace(rows: list[GlyphRow], label: str, keyfn) -> list[str]:
    pairs = [(k, r.glyph_name) for r in rows for k in keyfn(r)]
    errors = []
    for key, glyphs in _dupe_groups(pairs).items():
        uniq = sorted(set(glyphs))
        if len(uniq) == 2 and _is_known_vert_pair(uniq[0], uniq[1], rows):
            continue  # expected: horizontal glyph + its linked vert_variant
        errors.append(
            f"glyphAreas.csv: {label} spelling {key!r} is claimed by multiple "
            f"glyphs ({', '.join(uniq)}) — pick a unique key per glyph, or if "
            f"this is really a horizontal/vert-mode pair, link them with "
            f"vert_variant instead of duplicating the spelling")
    return errors


def validate(rows: list[GlyphRow], raw_rename_rows: list[tuple[str, str]]) -> list[str]:
    errors = []

    errors += _check_spelling_namespace(rows, "latin", _latin_keys)
    errors += _check_spelling_namespace(
        rows, "simplified", lambda r: [r.simplified] if r.simplified else [])
    errors += _check_spelling_namespace(
        rows, "traditional", lambda r: [r.traditional] if r.traditional else [])

    for char, targets in _dupe_groups(raw_rename_rows).items():
        errors.append(
            f"glyphRename.csv: char {char!r} is listed more than once "
            f"(targets: {', '.join(sorted(set(targets)))}) — only the last row "
            f"wins silently; remove the duplicate(s)")

    target_pairs = [(target, char) for char, target in raw_rename_rows]
    for target, chars in _dupe_groups(target_pairs).items():
        errors.append(
            f"glyphRename.csv: glyph name {target!r} is reused for multiple "
            f"characters ({', '.join(sorted(set(chars)))}) — each character "
            f"needs its own unique ch_* name, or they will silently collide "
            f"onto a single glyph")

    return errors


def validate_or_raise(rows: list[GlyphRow], raw_rename_rows: list[tuple[str, str]]) -> None:
    errors = validate(rows, raw_rename_rows)
    if errors:
        raise ValidationError(
            f"input validation failed ({len(errors)} issue(s)):\n  - " +
            "\n  - ".join(errors))
