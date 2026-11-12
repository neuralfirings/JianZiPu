"""The glossary on the public font page (site/index.html, "6. Glossary"), generated from
site/glossary.json and components.csv so its spellings can't drift from the font's.

site/glossary.json lists the sections (by id: "1c"), each with its title, how its table is laid out
(an example word per row, or a vertical table) and its rows in page order. A row is one glyph
({"glyph": "lg_gou"}) or a word written together ({"word": "少息", "glyphs": ["md_shao", "md_xi"]}),
with an optional "meaning". Its ASCII, Chinese and pinyin come from the glyphs' spellings in
components.csv. The Builder edits the rows in Glyphs > Glossary. This module rewrites each table
between `<!-- glossary <id> -->` and `<!-- /glossary <id> -->` in the page; the headings and text
around the tables stay as written.

    python3 -m jzpbuild.glossary            # rewrite the tables
    python3 -m jzpbuild.glossary --check    # exit 1 if a table is out of date or a glyph has no row

`check_typing()` (tests/test_glossary.py) also types every example on the page, the lessons
included, through the spellings in components.csv, and reports the ones whose spellings give
different glyphs.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from . import config

# components.csv's columns (typing_preview.ROW_FIELDS); not imported from there, so the release
# scope check can read the page with the standard library alone
FIELDS = ("glyph_name", "vert_variant", "common", "latin", "latin_alt", "simplified", "traditional", "pinyin")
KINDS = ("usage", "vertical", "hidden")

BLOCK_RE = re.compile(r"(<!-- glossary (\S+)[^>]*-->)(.*?)(<!-- /glossary \2 -->)", re.S)
INDENT = " " * 8
MAX_MEANING = 300
MAX_USAGE = 200
MAX_WORD_GLYPHS = 12
MAX_TITLE = 120
MAX_DESCRIPTION = 4000
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}")
ALL, NAV = "all", "nav"     # the page's two markers: every section title, subtitle and table; the contents links


class GlossaryError(Exception):
    """site/glossary.json and components.csv don't agree; the message says how."""


@dataclass
class Row:
    ascii: str
    chinese: str
    pinyin: str
    usage: str                  # the last cell's HTML
    examples: list[list[str]]   # each example's spellings as plain text, to type in check_typing()
    meaning: str = ""           # what the row means, escaped; a section with any gets a Meaning column
    glyphs: tuple[str, ...] = ()  # the glyph(s) the row is for


@dataclass
class Entry:
    """One row of a section as site/glossary.json lists it: a glyph, or a word (several glyphs)."""
    glyphs: tuple[str, ...]
    word: str = ""              # the word's text (少息); "" for a glyph's row
    meaning: str = ""
    usage: tuple[str, str] | None = None   # its own example word as [ASCII, 中文] templates (a usage section)

    @property
    def glyph(self) -> str:
        return self.glyphs[0]

    @property
    def name(self) -> str:
        return self.word or self.glyph


def load_rows(path: Path | None = None) -> dict[str, dict]:
    """components.csv's rows by glyph name."""
    with open(path or config.COMPONENTS_CSV, newline="", encoding="utf-8-sig") as f:
        recs = [{k: str(r.get(k) or "").strip() for k in FIELDS} for r in csv.DictReader(f)]
    return {r["glyph_name"]: r for r in recs if r["glyph_name"]}


def load_file(path: Path | None = None) -> dict:
    """site/glossary.json as it is: {"about": [...], "sections": {id: {title, kind, ..., rows}}}."""
    return json.loads((path or config.GLOSSARY_SECTIONS).read_text(encoding="utf-8"))


def load_sections(path: Path | None = None) -> dict[str, dict]:
    return load_file(path)["sections"]


def load_groups(path: Path | None = None) -> list[dict]:
    """The section titles ("1: Left Hand"), each with its subtitles (the sections' ids) in page order."""
    return load_file(path).get("groups", [])


def one_group(sections: dict[str, dict]) -> list[dict]:
    """Every section under one untitled section title (a page or a test without groups)."""
    return [{"id": "glossary", "title": "", "sections": list(sections)}]


def section_order(sections: dict[str, dict], groups: list[dict]) -> list[str]:
    """The sections in page order: by their section titles, then any no title holds."""
    seen = [sid for g in groups for sid in g.get("sections", []) if sid in sections]
    return list(dict.fromkeys(seen + list(sections)))


# ---------------------------------------------------------------- descriptions: a little Markdown

# the page's own tags a description may use as they are; anything else is shown as text
_TAGS = re.compile(r"&lt;(/?)(u|jzp|text|small|br ?/?)&gt;")
_LINK = re.compile(r"\[([^\]]+)\]\(((?:https?://|/|#)[^\s()<>\"]*)\)")


def _inline(s: str) -> str:
    codes: list[str] = []
    def keep(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\0{len(codes) - 1}\0"
    s = re.sub(r"`([^`]+)`", keep, s)                      # `s9k3`: a typed example, the page's grey pill
    s = _TAGS.sub(lambda m: "<" + m.group(1) + m.group(2) + ">", s)
    s = _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", s)
    return re.sub(r"\0(\d+)\0", lambda m: f"<text>{codes[int(m.group(1))]}</text>", s)


def markdown(text: str) -> str:
    """A description's HTML: paragraphs (a blank line between), a line break within one, lists of
    "- " lines, **bold**, *italic*, `typed examples`, [links](https://…), and the page's <u>, <jzp>,
    <text>, <small> and <br>. Any other HTML is escaped (app/src/lib/glossary.ts has the same)."""
    out = []
    for block in re.split(r"\n\s*\n", html.escape(text.strip(), quote=False)):
        lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
        if not lines:
            continue
        if all(l.startswith("- ") for l in lines):
            out.append("<ul>" + "".join(f"<li>{_inline(l[2:])}</li>" for l in lines) + "</ul>")
        else:
            out.append("<p>" + "<br />".join(_inline(l) for l in lines) + "</p>")
    return "\n".join(out)


def clean_row(x) -> dict:
    """A row as site/glossary.json keeps it, or ValueError saying what's wrong with it."""
    if not isinstance(x, dict):
        raise ValueError("a glossary row is an object")
    meaning = str(x.get("meaning") or "").strip()
    if len(meaning) > MAX_MEANING:
        raise ValueError(f"a meaning longer than {MAX_MEANING} characters")
    if x.get("word") is not None:
        word = str(x["word"]).strip()
        gs = x.get("glyphs")
        if not word or not isinstance(gs, list) or not all(isinstance(g, str) and g.strip() for g in gs):
            raise ValueError("a word's row has the word and its glyphs")
        if len(gs) > MAX_WORD_GLYPHS:
            raise ValueError(f"a word of more than {MAX_WORD_GLYPHS} glyphs")
        out = {"word": word, "glyphs": [g.strip() for g in gs]}
    elif isinstance(x.get("glyph"), str) and x["glyph"].strip():
        out = {"glyph": x["glyph"].strip()}
    else:
        raise ValueError("a glossary row names a glyph or a word")
    usage = x.get("usage")
    if usage is not None:
        if not (isinstance(usage, list) and len(usage) == 2 and all(isinstance(u, str) for u in usage)):
            raise ValueError("a row's usage is its example as [ASCII, 中文]")
        usage = [u.strip() for u in usage]
        if any(len(u) > MAX_USAGE for u in usage):
            raise ValueError(f"an example longer than {MAX_USAGE} characters")
    typed = str(x.get("typed") or "").strip()
    if len(typed) > MAX_USAGE:
        raise ValueError(f"an entry longer than {MAX_USAGE} characters")
    return {**out, **({"meaning": meaning} if meaning else {}), **({"usage": usage} if usage and any(usage) else {}),
            **({"typed": typed} if typed else {})}


def with_rows(sections: dict[str, dict], rows_by_section: dict) -> dict[str, dict]:
    """`sections` with each section's rows replaced by the Builder's (unsaved ones). Refuses a
    section that isn't there, a row that isn't one, or a glyph or word twice in one section."""
    if not isinstance(rows_by_section, dict):
        raise ValueError("glossary: an object of rows by section")
    out = {sid: dict(sec) for sid, sec in sections.items()}
    for sid, rows in rows_by_section.items():
        if sid not in out:
            raise ValueError(f"glossary: there's no section {sid}")
        if not isinstance(rows, list):
            raise ValueError(f"glossary: section {sid}'s rows are a list")
        out[sid]["rows"] = [clean_row(r) for r in rows]
    return out


def _text(x, what: str, limit: int, required: bool = False) -> str:
    if x is not None and not isinstance(x, str):
        raise ValueError(f"{what}: text, please")
    t = (x or "").strip()
    if required and not t:
        raise ValueError(f"{what} is empty")
    if len(t) > limit:
        raise ValueError(f"{what} is longer than {limit} characters")
    return t


def _id(x, what: str) -> str:
    if not isinstance(x, str) or not ID_RE.fullmatch(x):
        raise ValueError(f"{what}: an id of letters, digits, - and _ (up to 32), please")
    return x


def with_layout(sections: dict[str, dict], layout, rows_by_section: dict | None = None) -> tuple[dict[str, dict], list[dict]]:
    """The Builder's section titles and subtitles (unsaved ones), checked, with each subtitle's rows: the
    Builder's where it sends them, else the file's. `layout` is {"groups": [{id, title, nav?, description?,
    sections: [id…]}], "sections": {id: {title, kind, usage?, description?}}}. A subtitle the layout drops
    goes only when it has no rows. Returns (sections in page order, groups)."""
    if not isinstance(layout, dict) or not isinstance(layout.get("groups"), list) or not isinstance(layout.get("sections"), dict):
        raise ValueError("layout: the section titles and subtitles, please")
    metas = {}
    for sid, m in layout["sections"].items():
        _id(sid, "a subtitle's id")
        if not isinstance(m, dict):
            raise ValueError(f"subtitle {sid}: an object, please")
        kind = m.get("kind", "vertical")
        if kind not in KINDS:
            raise ValueError(f"subtitle {sid}: kind {kind!r} is none of {', '.join(KINDS)}")
        meta = {"title": _text(m.get("title"), f"subtitle {sid}'s title", MAX_TITLE, True), "kind": kind}
        u = m.get("usage")
        if kind == "usage":
            if not (isinstance(u, list) and len(u) == 2 and all(isinstance(x, str) and len(x) <= MAX_USAGE for x in u)):
                u = ["{}", "{}"]
            meta["usage"] = [x.strip() for x in u]
        if d := _text(m.get("description"), f"subtitle {sid}'s description", MAX_DESCRIPTION):
            meta["description"] = d
        metas[sid] = meta
    groups, held = [], set()
    if len(layout["groups"]) > 100:
        raise ValueError("too many section titles")
    for g in layout["groups"]:
        if not isinstance(g, dict):
            raise ValueError("a section title: an object, please")
        gid = _id(g.get("id"), "a section title's id")
        if any(x["id"] == gid for x in groups):
            raise ValueError(f"two section titles have the id {gid}")
        secs = g.get("sections") or []
        if not isinstance(secs, list) or any(not isinstance(x, str) or x not in metas for x in secs):
            raise ValueError(f"the section title {gid} lists a subtitle that isn't there")
        if held.intersection(secs):
            raise ValueError(f"{', '.join(sorted(held.intersection(secs)))} is under two section titles")
        held.update(secs)
        out = {"id": gid, "title": _text(g.get("title"), f"the section title {gid}", MAX_TITLE, True)}
        if nav := _text(g.get("nav"), f"the section title {gid}'s short name", 40):
            out["nav"] = nav
        if d := _text(g.get("description"), f"the section title {gid}'s description", MAX_DESCRIPTION):
            out["description"] = d
        groups.append({**out, "sections": list(secs)})
    rows_by_section = rows_by_section or {}
    for sid in sections:
        if sid not in metas:
            left = rows_by_section.get(sid, sections[sid].get("rows", []))
            if left:
                raise ValueError(f"subtitle {sid} still has {len(left)} row(s): move or remove them before deleting it")
    out = {}
    for sid in section_order(metas, groups):
        rows = rows_by_section[sid] if sid in rows_by_section else sections.get(sid, {}).get("rows", [])
        if not isinstance(rows, list):
            raise ValueError(f"glossary: section {sid}'s rows are a list")
        out[sid] = {**metas[sid], "rows": [clean_row(r) for r in rows]}
    if extra := [sid for sid in rows_by_section if sid not in out]:
        raise ValueError(f"glossary: there's no section {extra[0]}")
    return out, groups


def entries(sid: str, sec: dict, rows: dict[str, dict] | None = None) -> list[Entry]:
    """The section's rows in page order."""
    out = []
    for r in sec.get("rows", []):
        r = clean_row(r)
        if "word" in r:
            out.append(Entry(tuple(r["glyphs"]), r["word"], r.get("meaning", ""), tuple(r["usage"]) if "usage" in r else None))
        else:
            out.append(Entry((r["glyph"],), "", r.get("meaning", ""), tuple(r["usage"]) if "usage" in r else None))
    return out


def spellings(rec: dict) -> list[str]:
    """What types the glyph from an English keyboard, main spelling first."""
    return [rec[f] for f in ("latin", "latin_alt", "common") if rec[f]]


def has_spelling(rec: dict) -> bool:
    return any(rec[f] for f in ("latin", "latin_alt", "common", "simplified", "traditional"))


def _esc(s: str) -> str:
    return html.escape(s, quote=False)


def _list(items: list[str]) -> str:
    """Spellings for one cell, escaped; two or more each kept on one line (a phone breaks at the comma)."""
    items = [_esc(i) for i in items]
    return items[0] if len(items) == 1 else ", ".join(f'<span class="nw">{i}</span>' for i in items)


def _plain(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def _fill(template: str, spelling: str) -> str:
    return template.replace("{}", f"<r>{_esc(spelling)}</r>")


def _partner(rows: dict[str, dict], g: str) -> dict | None:
    """The row of g's vertical form, when that form has spellings of its own (散's :san)."""
    v = rows[g]["vert_variant"]
    return rows.get(v) if v else None


def _is_number(rec: dict) -> bool:
    """md_1 to md_13 (散's 0 is a string, not a number)."""
    return rec["common"].isdigit() and int(rec["common"]) > 0


def _rec(rows: dict[str, dict], sid: str, e: Entry, g: str) -> dict:
    if g not in rows:
        raise GlossaryError(f"glossary {sid}: {e.name} uses {g}, which isn't a glyph in components.csv "
                            f"(renamed or deleted?). Fix the row in Glyphs > Glossary.")
    return rows[g]


def chinese(rec: dict) -> list[str]:
    """The glyph's Chinese spellings: simplified, then traditional when it differs."""
    return [c for i, c in enumerate((rec["simplified"], rec["traditional"])) if c and c not in (rec["simplified"], rec["traditional"])[:i]]


def _usage_row(sec: dict, g: str, rec: dict, meaning: str = "", own: tuple[str, str] | None = None) -> Row:
    """`own`: the row's own example ([ASCII, 中文] templates, either may be empty), else the section's."""
    sp, zh = spellings(rec), chinese(rec)
    if not sp or not rec["simplified"]:
        raise GlossaryError(f"{g} needs an ASCII and a Chinese spelling for an example word.")
    ta, tz = own or sec["usage"]
    # the same example with each spelling: Chinese (traditional too) under Chinese, ASCII under ASCII
    zs = [_fill(tz, c) for c in zh] if tz else []
    as_ = [_fill(ta, s) for s in sp] if ta else []
    a = (as_ or zs)[0]
    usage = (f"\n{INDENT}      <jzp>{a}</jzp>\n" + "".join(f"{INDENT}      <txs>{x}</txs>\n" for x in zs + as_)
             + f"{INDENT}    ")
    return Row(_list(sp), _list(zh), _esc(rec["pinyin"]), usage,
               [[_plain(x) for x in zs + as_]], _esc(meaning), (g,))


def _own_example(e: Entry, sa: str, sz: str) -> tuple[str, list[str]]:
    """A vertical row's own example (the Builder's Example column): its Output, drawn from the ASCII
    (else the Chinese), nothing marked, and the spellings to type it with. {} is the glyph's spelling."""
    ta, tz = e.usage
    a = ta.replace("{}", _esc(sa)) if ta else ""
    z = tz.replace("{}", _esc(sz)) if tz else ""
    return f"<jzp>{a or z}</jzp>", [_plain(x) for x in (a, z) if x]


def _vertical_row(rows: dict[str, dict], e: Entry) -> Row:
    if e.word:                       # a word: each glyph's main spelling, run together
        recs = [rows[g] for g in e.glyphs]
        if not all(spellings(r) and r["simplified"] for r in recs):
            raise GlossaryError(f"every glyph of the word {e.word} ({' + '.join(e.glyphs)}) needs an ASCII and a Chinese spelling.")
        a = ":" + "".join(spellings(r)[0] for r in recs)
        z = ":" + "".join(r["simplified"] for r in recs)
        out, examples = f"<jzp>{_esc(z)}</jzp>", [[a, z]]
        if e.usage:
            out, own = _own_example(e, "", "")
            examples.append(own)
        return Row(_esc(a), _esc(z), _esc(" ".join(r["pinyin"] for r in recs if r["pinyin"])),
                   out, examples, _esc(e.meaning), glyphs=e.glyphs)
    g = e.glyph
    rec, other = rows[g], _partner(rows, g)
    sp = spellings(rec) + (spellings(other) if other else [])
    zhs = chinese(rec) or (chinese(other) if other else [])
    zh = zhs[0] if zhs else ""
    py = rec["pinyin"] or (other or {}).get("pinyin", "")
    examples = [[":" + s] + [":" + c for c in zhs] for s in sp] or ([[":" + c for c in zhs]] if zhs else [])
    out = f"<jzp>{_esc(':' + (zh or (sp[0] if sp else '')))}</jzp>"
    if e.usage:
        out, own = _own_example(e, sp[0] if sp else "", zh)
        examples.append(own)
    return Row(_list([":" + s for s in sp]) if sp else "", _list([":" + c for c in zhs]) if zhs else "", _esc(py),
               out, examples, _esc(e.meaning), (g,))


def _number_row(recs: list[dict]) -> Row:
    first, last = recs[0], recs[-1]
    a = f":{first['common']}..:{last['common']}"
    z = f":{first['simplified']}..:{last['simplified']}"
    usage = " ".join(f"<jzp>:{_esc(r['simplified'])}</jzp>" for r in (first, last))
    return Row(_esc(a), _esc(z), "", usage,
               [[f":{r['common']}", f":{r['simplified']}"] for r in recs], glyphs=tuple(r["glyph_name"] for r in recs))


def section_rows(sid: str, sec: dict, rows: dict[str, dict]) -> list[Row]:
    if sec["kind"] == "hidden":           # 99: Hidden in Glossary: its glyphs are left out on purpose, no table
        return []
    if sec["kind"] not in KINDS:
        raise GlossaryError(f"section {sid}: kind {sec['kind']!r} is none of 'usage', 'vertical' or 'hidden'.")
    out: list[Row] = []
    numbers: list[dict] = []
    for e in entries(sid, sec) + [None]:
        if e is not None:
            for g in e.glyphs:
                _rec(rows, sid, e, g)
        if sec["kind"] == "vertical" and e is not None and not e.word and not e.meaning and not e.usage and _is_number(rows[e.glyph]):
            numbers.append(rows[e.glyph])
            continue
        if numbers:
            out.append(_number_row(numbers))
            numbers = []
        if e is None:
            break
        if sec["kind"] == "usage":
            if e.word:
                raise GlossaryError(f"section {sid} has example words; a word ({e.word}) goes in a vertical section.")
            out.append(_usage_row(sec, e.glyph, rows[e.glyph], e.meaning, e.usage))
        else:
            out.append(_vertical_row(rows, e))
    return out


def table_html(sid: str, sec: dict, rows: dict[str, dict], start: int = 1) -> str:
    """The section's table; its rows are numbered `start`, `start` + 1… (one count down the whole page).
    A Meaning column joins it once any of its glyphs has a meaning in components.csv."""
    cls, last = ("table table-sm", "Usage") if sec["kind"] == "usage" else ("table", "Output")
    body = section_rows(sid, sec, rows)
    meaning = any(r.meaning for r in body)
    widths = (16, 16, 16, 22, 24) if meaning else (23, 23, 23, 0, 25)
    lines = [f'<table class="{cls}">', "  <thead>", "    <tr>", '      <th class="gid" width="6%">ID</th>']
    lines += [f'      <th width="{w}%">{h}</th>' for h, w in zip(("ASCII", "中文", "拼音"), widths)]
    lines += ([f'      <th width="{widths[3]}%">Meaning</th>'] if meaning else []) + [f'      <th width="{widths[4]}%">{last}</th>']
    lines += ["    </tr>", "  </thead>"]
    for n, r in enumerate(body, start):
        rid = str(n)                  # by position: a row added above renumbers the ones below it
        lines += [f'  <tr id="{rid}">', f'    <td class="gid"><a href="#{rid}">{rid}</a></td>', f"    <td>{r.ascii}</td>",
                  f"    <td>{r.chinese}</td>", f"    <td>{r.pinyin}</td>",
                  *([f'    <td class="meaning">{r.meaning}</td>'] if meaning else []), f"    <td>{r.usage}</td>", "  </tr>"]
    lines.append("</table>")
    return "\n".join(INDENT + l if l else l for l in lines)


def missing(rows: dict[str, dict], sections: dict[str, dict]) -> list[str]:
    """Problems that leave a glyph out of the glossary, or a row the page can't show."""
    problems = []
    shown: set[str] = set()
    for sid, sec in sections.items():
        if not sec.get("title", "").strip():
            problems.append(f"site/glossary.json: section {sid} has no title.")
        seen: set[str] = set()
        for e in entries(sid, sec):
            key = "word " + e.word if e.word else e.glyph
            if key in seen:
                problems.append(f"glossary {sid}: {e.name} is in the section twice.")
            seen.add(key)
            if e.word and len(e.glyphs) < 2:
                problems.append(f"glossary {sid}: the word {e.word} is one glyph; give the glyph its own row instead.")
            if e.word and sec.get("kind") == "usage":
                problems.append(f"glossary {sid}: the word {e.word} is in a section of example words; a word goes in a vertical section.")
            for g in e.glyphs:
                if g not in rows:
                    problems.append(f"glossary {sid}: {e.name} uses {g}, which isn't a glyph in components.csv (renamed or deleted?).")
                    continue
                shown.add(g)
                if sec.get("kind") == "vertical" and not e.word and _partner(rows, g):
                    shown.add(rows[g]["vert_variant"])
    for g, r in rows.items():
        if has_spelling(r) and g not in shown:
            problems.append(f"{g} ({r['simplified'] or spellings(r)[0]}) has spellings but no row in the glossary: "
                            f"add it to a section in Glyphs > Glossary (99: Hidden in Glossary leaves it out on purpose).")
    return problems


def missing_layout(sections: dict[str, dict], groups: list[dict]) -> list[str]:
    """A subtitle no section title holds (so the page doesn't show it), or a section title naming one that isn't there."""
    problems, held = [], {}
    for g in groups:
        for sid in g.get("sections", []):
            if sid not in sections:
                problems.append(f"site/glossary.json: the section title {g.get('title') or g.get('id')!r} lists {sid}, which isn't a section.")
            elif sid in held:
                problems.append(f"site/glossary.json: {sid} is under two section titles, {held[sid]!r} and {g.get('title')!r}.")
            held.setdefault(sid, g.get("title") or g.get("id"))
    for sid, sec in sections.items():
        if sid not in held and sec.get("kind") != "hidden":
            problems.append(f"{sec.get('title') or sid} isn't under a section title, so the page doesn't show it: "
                            f"put it under one in Glyphs > Glossary.")
    return problems


def _desc(text: str, cls: str) -> list[str]:
    return [f'<div class="{cls}">', *("  " + l for l in markdown(text).split("\n")), "</div>"] if text.strip() else []


def page_html(sections: dict[str, dict], groups: list[dict], rows: dict[str, dict], start: int = 1) -> tuple[str, int]:
    """Every section title, its description, its subtitles with theirs, and their tables, in page
    order; and how many rows the tables numbered. A section title with only hidden subtitles is left
    out, and a subtitle with the section title's own title shows it once."""
    lines: list[str] = []
    count = start - 1
    for g in groups:
        shown = [sid for sid in g.get("sections", []) if sid in sections and sections[sid].get("kind") != "hidden"]
        if not shown:
            continue
        if lines:
            lines.append("")
        gid = g.get("id", "")
        lines.append(f'<h4 id="glossary-{_esc(gid)}">{_esc(g.get("title", ""))}</h4>')
        lines += _desc(g.get("description", ""), "glossary-desc")
        for sid in shown:
            sec = sections[sid]
            if sec.get("title", "").strip() != g.get("title", "").strip():
                lines.append(f'<label id="glossary-{_esc(sid)}">{_esc(sec.get("title", ""))}</label>')
            lines += _desc(sec.get("description", ""), "glossary-subdesc")
            lines += [l[len(INDENT):] if l.startswith(INDENT) else l for l in table_html(sid, sec, rows, count + 1).split("\n")]
            count += len(section_rows(sid, sec, rows))
    return "\n".join(INDENT + l if l else l for l in lines), count - start + 1


def nav_html(sections: dict[str, dict], groups: list[dict]) -> str:
    """The contents' links to the section titles (each one's short `nav` name, else its title)."""
    out = []
    for g in groups:
        if any(sid in sections and sections[sid].get("kind") != "hidden" for sid in g.get("sections", [])):
            out.append(f'{INDENT}<a class="sub" href="#glossary-{_esc(g.get("id", ""))}">{_esc(g.get("nav") or g.get("title", ""))}</a>')
    return "\n".join(out)


def render(page: str, rows: dict[str, dict] | None = None, sections: dict[str, dict] | None = None,
           groups: list[dict] | None = None) -> str:
    """`page` with the glossary regenerated: the whole of it between `<!-- glossary all -->` markers and
    its contents links between `<!-- glossary nav -->`, or (an older page, the tests) a table per
    section's own marker."""
    rows = load_rows() if rows is None else rows
    if sections is None:
        sections = load_sections()
        groups = load_groups() if groups is None else groups
    groups = one_group(sections) if groups is None else groups
    seen = set()
    count = 0                         # rows numbered so far, in page order

    def sub(m: re.Match) -> str:
        sid = m.group(2)
        nonlocal count
        if sid == ALL:
            seen.update(sections)
            body, n = page_html(sections, groups, rows, count + 1)
            count += n
            return f"{m.group(1)}\n{body}\n{INDENT}{m.group(4)}"
        if sid == NAV:
            return f"{m.group(1)}\n{nav_html(sections, groups)}\n{INDENT}{m.group(4)}"
        if sid not in sections:
            raise GlossaryError(f"site/index.html has a glossary marker for {sid}, which site/glossary.json doesn't define.")
        seen.add(sid)
        html = table_html(sid, sections[sid], rows, count + 1)
        count += len(section_rows(sid, sections[sid], rows))
        return f"{m.group(1)}\n{html}\n{INDENT}{m.group(4)}"

    out = BLOCK_RE.sub(sub, page)
    if unused := [s for s in sections if s not in seen and sections[s]["kind"] != "hidden"]:
        raise GlossaryError(f"site/index.html has no glossary marker for section(s) {', '.join(unused)}.")
    return out


def descriptions_html(sections: dict[str, dict], groups: list[dict]) -> str:
    """Every description as the page shows it, for examples() to type."""
    texts = [g.get("description", "") for g in groups] + [s.get("description", "") for s in sections.values()]
    return "\n".join(markdown(t) for t in texts if t.strip())


def strip_generated(page: str) -> str:
    """`page` with the generated tables emptied: what's left is written by hand."""
    return BLOCK_RE.sub(lambda m: m.group(1) + m.group(4), page)


def examples(page: str | None = None, rows: dict[str, dict] | None = None,
             sections: dict[str, dict] | None = None, skip: set[str] = frozenset(),
             groups: list[dict] | None = None) -> list[tuple[str, list[str]]]:
    """Every example on the page as (where, spellings that must type the same glyph): the generated
    tables' rows, and the hand-written ones (<text>/<txs> spellings and the <jzp> rendering they
    give, in the lessons and around the tables)."""
    page = config.SITE_INDEX.read_text(encoding="utf-8") if page is None else page
    rows = load_rows() if rows is None else rows
    if sections is None:
        sections, groups = load_sections(), load_groups() if groups is None else groups
    groups = groups or []
    out = []
    for sid, sec in sections.items():
        for r in section_rows(sid, sec, rows):
            if not skip.intersection(r.glyphs):          # `skip`: glyphs the font hasn't got yet
                out += [(f"glossary {sid}", ex) for ex in r.examples]
    # the hand-written page, and the descriptions the glossary is written with
    text = re.sub(r"<script.*?</script>|<style.*?</style>|<!--(?! glossary| /glossary).*?-->", " ",
                  strip_generated(page) + "\n" + descriptions_html(sections, groups), flags=re.S)
    for m in re.finditer(r"<(li|td|p)\b[^>]*>(.*?)</\1>", text, re.S):
        where = "page: " + re.sub(r"\s+", " ", _plain(m.group(2))).strip()[:60]
        # an example is a run of spellings and the rendering they give (`a or b → <jzp>`), joined
        # by a few words at most; a sentence end or a longer gap drops the spellings before it
        cur: list[str] = []
        last = 0
        for el in re.finditer(r"<(text|txs|jzp)\b[^>]*>(.*?)</\1>", m.group(2), re.S):
            gap = _plain(m.group(2)[last:el.start()])
            if re.search(r"[.!?;:](\s|$)", gap) or len(gap.strip()) > 30:
                cur = []
            last = el.end()
            if c := _plain(el.group(2)).strip():
                cur.append(c)
            if el.group(1) == "jzp":
                out.append((where, cur))
                cur = []
    return [(w, ex) for w, ex in out if len(ex) > 1 or w.startswith("glossary")]


def check_typing(font: Path | None = None, page: str | None = None, rows: dict[str, dict] | None = None,
                 design: dict | None = None, sections: dict[str, dict] | None = None, svg=None) -> list[str]:
    """Type every example through components.csv's spellings (or `rows`: the Builder's unsaved ones),
    compiled onto the released font (or `font`, a build) the way the Builder's Typing preview does, so
    a release's new spellings count before it's built, and return the examples whose spellings give
    different glyphs (a vertical form counts as its glyph), or letters the font didn't turn into a
    glyph. A glyph the font hasn't got is drawn in from its SVG (`svg(name)`, see typing_preview);
    examples using one with no drawing either are skipped."""
    return _typing(font, page, rows, design, sections, svg)[0]


def _typing(font, page, rows, design, sections, svg=None, gpos=False, groups=None):
    """check_typing(), the glyphs it skipped because the font hasn't got them, and the preview font."""
    from . import typing_preview
    font = font or config.SITE_FONT
    design = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8")) if design is None else design
    rows = load_rows() if rows is None else rows
    grows = typing_preview.rows_from(list(rows.values()), design)
    prev = typing_preview.FONTS.get(font, grows, design, svg, gpos)
    skip = set(prev.not_built)
    horizontal = {r["vert_variant"]: g for g, r in rows.items() if r["vert_variant"]}
    problems = []
    for where, ex in examples(page, rows, sections, skip, groups):
        if prev.lacking and any(ch in prev.lacking for x in ex for ch in x):
            continue                                   # a character only a Build adds: wait for it
        typed = typing_preview.shape(prev, ex)
        # the same glyph, written on its own after a colon or not (外, :wai)
        glyphs = [[horizontal.get(g, g) for g in t["glyphs"] if g != "blank_colon"] for t in typed]
        if any(g in skip for gs in glyphs for g in gs):
            continue
        leftover = sorted({t for s in typed for g, t in zip(s["glyphs"], s["texts"])
                           if g not in prev.glyphs or g == ".notdef" or (len(g) == 1 and g.isalpha())})
        if len({json.dumps(g) for g in glyphs}) > 1 or leftover:
            detail = "; ".join(f"{w} -> {' '.join(g)}" for w, g in zip(ex, glyphs))
            problems.append(f"[{where}] {detail}" + (f" (not a glyph: {', '.join(leftover)})" if leftover else ""))
    return problems, sorted(skip), prev


def records(recs: list[dict]) -> dict[str, dict]:
    """The Builder's spelling records (unsaved ones included) as load_rows() gives the CSV's."""
    out = {}
    for rec in recs:
        r = {k: str(rec.get(k) or "").strip() for k in FIELDS}
        if r["glyph_name"]:
            out[r["glyph_name"]] = r
    return out


def in_glossary(sections: dict[str, dict]) -> set[str]:
    """The glyphs some section shows, on their own or in a word (hidden ones included)."""
    return {g for sid, sec in sections.items() for e in entries(sid, sec) for g in e.glyphs}


def check(rows: dict[str, dict], design: dict | None = None, font: Path | None = None, svg=None,
          sections: dict[str, dict] | None = None, groups: list[dict] | None = None) -> dict:
    """The Builder's "Check the glossary": with these spellings, what the font page's glossary
    would leave out or get wrong, and its tables as they would be written (each section's HTML,
    numbered down the page). `font`: the build to type the examples with (default the released one);
    `svg(name)`: the drawing of a glyph it hasn't got. The examples are typed in a preview font: `font`
    plus those glyphs, these spellings and the design's positioning, which `font_key` names
    (typing_preview.FONTS.by_key) so the Builder can draw the tables in it; `drawn` lists the glyphs
    drawn in from their files. `sections`, `groups`: the glossary with the Builder's unsaved rows and
    titles (with_rows, with_layout)."""
    sections = load_sections() if sections is None else sections
    groups = load_groups() if groups is None else groups
    page = config.SITE_INDEX.read_text(encoding="utf-8")
    out: dict = {"ok": True, "problems": [], "typing": [], "tables": []}
    order = [sid for sid in section_order(sections, groups) if sections[sid].get("kind") != "hidden"]
    try:
        out["problems"] = missing(rows, sections) + missing_layout(sections, groups)
        render(page, rows, sections, groups)          # the same errors a release would stop on
        count = 0
        for sid in order:
            sec = sections[sid]
            out["tables"].append({"id": sid, "title": sec.get("title", sid),
                                  "html": table_html(sid, sec, rows, count + 1)})
            count += len(section_rows(sid, sec, rows))
    except GlossaryError as e:
        return {**out, "ok": False, "error": str(e)}
    out["typing"], unbuilt, prev = _typing(font, page, rows, design, sections, svg, gpos=True, groups=groups)
    # glyphs the glossary shows that have no drawing at all: their examples wait for one
    shown = in_glossary(sections)
    out["not_built"] = [g for g in unbuilt if g in shown]
    out["drawn"] = [g for g in prev.drawn if g in shown]
    out["missing_chars"] = sorted(prev.lacking)
    out["font_key"] = prev.key
    return out


def dumps(data: dict) -> str:
    """site/glossary.json's text: each section's settings on a line of their own and one row per
    line, so a change in the Builder shows in a diff as the rows it moved."""
    j = lambda v: json.dumps(v, ensure_ascii=False, separators=(", ", ": "))
    lines = ["{"]
    rest = [k for k in data if k != "sections"]
    for k in rest:
        v = data[k]
        if isinstance(v, list):
            lines.append(f'  {j(k)}: [' + ("" if v else "],"))
            lines += [f"    {j(x)}," for x in v]
            if v:
                lines[-1] = lines[-1][:-1]
                lines.append("  ],")
        else:
            lines.append(f"  {j(k)}: {j(v)},")
    lines.append('  "sections": {')
    secs = list(data.get("sections", {}).items())
    for i, (sid, sec) in enumerate(secs):
        lines.append(f"    {j(sid)}: {{")
        keys = [k for k in sec if k != "rows"]
        for k in keys:
            lines.append(f"      {j(k)}: {j(sec[k])},")
        rows = sec.get("rows", [])
        lines.append('      "rows": [' + ("]" if not rows else ""))
        if rows:
            lines += [f"        {j(r)}," for r in rows]
            lines[-1] = lines[-1][:-1]
            lines.append("      ]")
        lines.append("    }" + ("," if i < len(secs) - 1 else ""))
    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


def write(path: Path | None = None, csv_path: Path | None = None, sections_path: Path | None = None) -> bool:
    """Rewrite the page's glossary tables; True when the file changed."""
    path = path or config.SITE_INDEX
    old = path.read_text(encoding="utf-8")
    new = render(old, load_rows(csv_path), load_sections(sections_path), load_groups(sections_path))
    if new != old:
        path.write_text(new, encoding="utf-8")
    return new != old


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jzpbuild.glossary", description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if the page is out of date")
    args = ap.parse_args(argv)
    try:
        rows, sections, groups = load_rows(), load_sections(), load_groups()
        problems = missing(rows, sections) + missing_layout(sections, groups)
        page = config.SITE_INDEX.read_text(encoding="utf-8")
        new = render(page, rows, sections, groups)
    except GlossaryError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for p in problems:
        print(f"error: {p}", file=sys.stderr)
    if args.check:
        if new != page:
            print("error: site/index.html's glossary is out of date: run `cd builder && python3 -m jzpbuild.glossary`.",
                  file=sys.stderr)
            return 1
    elif new != page:
        config.SITE_INDEX.write_text(new, encoding="utf-8")
        print(f"wrote {config.SITE_INDEX}")
    else:
        print("the glossary is up to date")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
