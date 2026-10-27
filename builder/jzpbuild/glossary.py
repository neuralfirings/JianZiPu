"""The glossary on the public font page (site/index.html, "6. Glossary"), generated from
components.csv so its spellings can't drift from the font's.

A glyph's `glossary` column in components.csv names the section(s) where it gets a row of its own,
by title ("1c: Left Hand Techniques", two separated by "; "; the id before the colon is the key); site/glossary.json says how each section's table is laid out (an example word per
row, or a vertical table, and the order of its rows, words like :带起 included). This module
rewrites each table between `<!-- glossary <id> -->` and `<!-- /glossary <id> -->` in the page;
the headings and text around the tables stay as written.

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
FIELDS = ("glyph_name", "vert_variant", "common", "latin", "latin_alt", "simplified", "traditional", "pinyin", "glossary")

BLOCK_RE = re.compile(r"(<!-- glossary (\S+)[^>]*-->)(.*?)(<!-- /glossary \2 -->)", re.S)
INDENT = " " * 8


class GlossaryError(Exception):
    """components.csv and site/glossary.json don't agree; the message says how."""


@dataclass
class Row:
    ascii: str
    chinese: str
    pinyin: str
    usage: str                  # the fourth cell's HTML
    examples: list[list[str]]   # each example's spellings as plain text, to type in check_typing()


def load_rows(path: Path | None = None) -> dict[str, dict]:
    with open(path or config.COMPONENTS_CSV, newline="", encoding="utf-8-sig") as f:
        recs = [{k: str(r.get(k) or "").strip() for k in FIELDS} for r in csv.DictReader(f)]
    return {r["glyph_name"]: r for r in recs if r["glyph_name"]}


def load_sections(path: Path | None = None) -> dict[str, dict]:
    return json.loads((path or config.GLOSSARY_SECTIONS).read_text(encoding="utf-8"))["sections"]


SEP = ";"   # between two sections in the glossary column (titles have spaces)


def section_items(rec: dict) -> list[tuple[str, str]]:
    """The glossary column as (id, what it says): "1c: Left Hand Techniques" -> ("1c", that title)."""
    items = [x.strip() for x in rec.get("glossary", "").split(SEP)]
    return [(x.split(":", 1)[0].strip(), x) for x in items if x]


def section_ids(rec: dict) -> list[str]:
    return [sid for sid, _ in section_items(rec)]


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


def entries(sid: str, sec: dict, rows: dict[str, dict]) -> list[str | list[str]]:
    """The section's rows in order: glyph names, and lists of glyph names for words."""
    placed = [g for g, r in rows.items() if sid in section_ids(r)]
    listed = sec.get("rows", [])
    for e in listed:
        for g in (e if isinstance(e, list) else [e]):
            if g not in rows:
                raise GlossaryError(f"site/glossary.json section {sid} lists {g}, which has no row in components.csv.")
        if isinstance(e, str) and e not in placed:
            raise GlossaryError(f"site/glossary.json section {sid} lists {e}, but its glossary column in "
                                f"components.csv is {rows[e]['glossary'] or 'empty'!r}; add {sid} there.")
    return listed + [g for g in placed if g not in listed]


def chinese(rec: dict) -> list[str]:
    """The glyph's Chinese spellings: simplified, then traditional when it differs."""
    return [c for i, c in enumerate((rec["simplified"], rec["traditional"])) if c and c not in (rec["simplified"], rec["traditional"])[:i]]


def _usage_row(sec: dict, g: str, rec: dict) -> Row:
    sp, zh = spellings(rec), chinese(rec)
    if not sp or not rec["simplified"]:
        raise GlossaryError(f"{g} needs an ASCII and a Chinese spelling for an example word.")
    ta, tz = sec.get("examples", {}).get(g, sec["usage"])
    a, z = _fill(ta, sp[0]), _fill(tz, rec["simplified"])
    # the same example with each other spelling: Chinese (traditional) under Chinese, ASCII under ASCII
    zs, as_ = [z] + [_fill(tz, c) for c in zh[1:]], [a] + [_fill(ta, s) for s in sp[1:]]
    usage = (f"\n{INDENT}      <jzp>{a}</jzp>\n" + "".join(f"{INDENT}      <txs>{x}</txs>\n" for x in zs + as_)
             + f"{INDENT}    ")
    return Row(_list(sp), _list(zh), _esc(rec["pinyin"]), usage,
               [[_plain(x) for x in zs + as_]])


def _vertical_row(rows: dict[str, dict], e: str | list[str]) -> Row:
    if isinstance(e, list):          # a word: each glyph's main spelling, run together
        recs = [rows[g] for g in e]
        if not all(spellings(r) and r["simplified"] for r in recs):
            raise GlossaryError(f"every glyph of the word {' + '.join(e)} needs an ASCII and a Chinese spelling.")
        a = ":" + "".join(spellings(r)[0] for r in recs)
        z = ":" + "".join(r["simplified"] for r in recs)
        return Row(_esc(a), _esc(z), _esc(" ".join(r["pinyin"] for r in recs if r["pinyin"])),
                   f"<jzp>{_esc(z)}</jzp>", [[a, z]])
    rec, other = rows[e], _partner(rows, e)
    sp = spellings(rec) + (spellings(other) if other else [])
    zhs = chinese(rec) or (chinese(other) if other else [])
    zh = zhs[0] if zhs else ""
    py = rec["pinyin"] or (other or {}).get("pinyin", "")
    examples = [[":" + s] + [":" + c for c in zhs] for s in sp] or ([[":" + c for c in zhs]] if zhs else [])
    out = ":" + (zh or (sp[0] if sp else ""))
    return Row(_list([":" + s for s in sp]) if sp else "", _list([":" + c for c in zhs]) if zhs else "", _esc(py),
               f"<jzp>{_esc(out)}</jzp>", examples)


def _number_row(recs: list[dict]) -> Row:
    first, last = recs[0], recs[-1]
    a = f":{first['common']}..:{last['common']}"
    z = f":{first['simplified']}..:{last['simplified']}"
    usage = " ".join(f"<jzp>:{_esc(r['simplified'])}</jzp>" for r in (first, last))
    return Row(_esc(a), _esc(z), "", usage,
               [[f":{r['common']}", f":{r['simplified']}"] for r in recs])


def section_rows(sid: str, sec: dict, rows: dict[str, dict]) -> list[Row]:
    out: list[Row] = []
    numbers: list[dict] = []
    for e in entries(sid, sec, rows) + [None]:
        if sec["kind"] == "vertical" and isinstance(e, str) and _is_number(rows[e]):
            numbers.append(rows[e])
            continue
        if numbers:
            out.append(_number_row(numbers))
            numbers = []
        if e is None:
            break
        if sec["kind"] == "usage":
            if isinstance(e, list):
                raise GlossaryError(f"section {sid} has example words; a word goes in a vertical section.")
            out.append(_usage_row(sec, e, rows[e]))
        elif sec["kind"] == "vertical":
            out.append(_vertical_row(rows, e))
        else:
            raise GlossaryError(f"section {sid}: kind {sec['kind']!r} is neither 'usage' nor 'vertical'.")
    return out


def table_html(sid: str, sec: dict, rows: dict[str, dict], start: int = 1) -> str:
    """The section's table; its rows are numbered `start`, `start` + 1… after the section's id."""
    cls, last = ("table table-sm", "Usage") if sec["kind"] == "usage" else ("table", "Output")
    lines = [f'<table class="{cls}">', "  <thead>", "    <tr>", '      <th class="gid" width="10%">ID</th>']
    lines += [f'      <th width="22%">{h}</th>' for h in ("ASCII", "中文", "拼音")] + [f'      <th width="24%">{last}</th>']
    lines += ["    </tr>", "  </thead>"]
    base = sid.split("-")[0]          # 1d-v (1d's vertical table) goes on counting 1d's rows
    for n, r in enumerate(section_rows(sid, sec, rows), start):
        rid = f"{base}.{n}"           # by position: a row added above renumbers the ones below it
        lines += [f'  <tr id="{rid}">', f'    <td class="gid"><a href="#{rid}">{rid}</a></td>', f"    <td>{r.ascii}</td>",
                  f"    <td>{r.chinese}</td>", f"    <td>{r.pinyin}</td>", f"    <td>{r.usage}</td>", "  </tr>"]
    lines.append("</table>")
    return "\n".join(INDENT + l if l else l for l in lines)


def missing(rows: dict[str, dict], sections: dict[str, dict]) -> list[str]:
    """Problems that leave a glyph out of the glossary, or point at a section that isn't there."""
    problems = []
    shown: set[str] = set()
    for sid, sec in sections.items():
        for e in entries(sid, sec, rows):
            for g in (e if isinstance(e, list) else [e]):
                shown.add(g)
                if sec["kind"] == "vertical" and isinstance(e, str) and _partner(rows, g):
                    shown.add(rows[g]["vert_variant"])
    for sid, sec in sections.items():
        if not sec.get("title", "").startswith(sid + ": "):
            problems.append(f"site/glossary.json: section {sid}'s title should start with \"{sid}: \".")
    for g, r in rows.items():
        for sid, said in section_items(r):
            if sid not in sections:
                problems.append(f"{g}: glossary section {said!r} isn't in site/glossary.json "
                                f"(sections: {', '.join(s['title'] for s in sections.values())}).")
            elif said != sections[sid].get("title"):
                problems.append(f"{g}: the glossary column says {said!r}; site/glossary.json calls {sid} "
                                f"{sections[sid].get('title')!r}. Use the same title in both.")
        if has_spelling(r) and g not in shown:
            problems.append(f"{g} ({r['simplified'] or spellings(r)[0]}) has spellings but no row in the glossary: "
                            f"give it a glossary section in components.csv, or put it in a word in site/glossary.json.")
    return problems


def render(page: str, rows: dict[str, dict] | None = None, sections: dict[str, dict] | None = None) -> str:
    """`page` with every glossary table regenerated."""
    rows = load_rows() if rows is None else rows
    sections = load_sections() if sections is None else sections
    seen = set()
    count: dict[str, int] = {}        # rows numbered so far, per section id before the "-"

    def sub(m: re.Match) -> str:
        sid = m.group(2)
        if sid not in sections:
            raise GlossaryError(f"site/index.html has a glossary marker for {sid}, which site/glossary.json doesn't define.")
        seen.add(sid)
        base = sid.split("-")[0]
        html = table_html(sid, sections[sid], rows, count.get(base, 0) + 1)
        count[base] = count.get(base, 0) + len(section_rows(sid, sections[sid], rows))
        return f"{m.group(1)}\n{html}\n{INDENT}{m.group(4)}"

    out = BLOCK_RE.sub(sub, page)
    if unused := [s for s in sections if s not in seen]:
        raise GlossaryError(f"site/index.html has no glossary marker for section(s) {', '.join(unused)}.")
    return out


def strip_generated(page: str) -> str:
    """`page` with the generated tables emptied: what's left is written by hand."""
    return BLOCK_RE.sub(lambda m: m.group(1) + m.group(4), page)


def examples(page: str | None = None, rows: dict[str, dict] | None = None,
             sections: dict[str, dict] | None = None) -> list[tuple[str, list[str]]]:
    """Every example on the page as (where, spellings that must type the same glyph): the generated
    tables' rows, and the hand-written ones (<text>/<txs> spellings and the <jzp> rendering they
    give, in the lessons and around the tables)."""
    page = config.SITE_INDEX.read_text(encoding="utf-8") if page is None else page
    rows = load_rows() if rows is None else rows
    sections = load_sections() if sections is None else sections
    out = []
    for sid, sec in sections.items():
        for r in section_rows(sid, sec, rows):
            out += [(f"glossary {sid}", ex) for ex in r.examples]
    text = re.sub(r"<script.*?</script>|<style.*?</style>|<!--(?! glossary| /glossary).*?-->", " ",
                  strip_generated(page), flags=re.S)
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


def check_typing(font: Path | None = None, page: str | None = None) -> list[str]:
    """Type every example through components.csv's spellings (compiled onto the released font, the
    way the Builder's Typing preview does, so a release's new spellings count before it's built) and
    return the examples whose spellings give different glyphs (a vertical form counts as its glyph),
    or letters the font didn't turn into a glyph. Examples using a glyph the font doesn't have yet are skipped."""
    from . import typing_preview
    font = font or config.SITE_FONT
    design = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    rows = load_rows()
    grows = typing_preview.rows_from(list(rows.values()), design)
    prev = typing_preview.FONTS.get(font, grows, design)
    skip = set(prev.not_built)
    horizontal = {r["vert_variant"]: g for g, r in rows.items() if r["vert_variant"]}
    problems = []
    for where, ex in examples(page, rows):
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
    return problems


def write(path: Path | None = None, csv_path: Path | None = None, sections_path: Path | None = None) -> bool:
    """Rewrite the page's glossary tables; True when the file changed."""
    path = path or config.SITE_INDEX
    old = path.read_text(encoding="utf-8")
    new = render(old, load_rows(csv_path), load_sections(sections_path))
    if new != old:
        path.write_text(new, encoding="utf-8")
    return new != old


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jzpbuild.glossary", description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if the page is out of date")
    args = ap.parse_args(argv)
    try:
        rows, sections = load_rows(), load_sections()
        problems = missing(rows, sections)
        page = config.SITE_INDEX.read_text(encoding="utf-8")
        new = render(page, rows, sections)
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
