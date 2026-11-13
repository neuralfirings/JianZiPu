"""Write site/vnext.html: the font page as it will be once the next release is out.

It's site/index.html with the next release's changes applied, so the two never drift apart:

- the notation is drawn in a preview build of the next font (site/JianZiPu-vnext.ttf; `--font`
  rebuilds it from builder/inputs), and the glossary is written as the next font reads it (no colon
  before a word only a vertical word can hold);
- the lessons say what the next release changes (CHANGES below);
- a "What's new in <next>" section shows each change in today's font beside the next one.

    cd builder && python3 -m jzpbuild.vnext            # rewrite site/vnext.html
    cd builder && python3 -m jzpbuild.vnext --font     # and rebuild site/JianZiPu-vnext.ttf
    cd builder && python3 -m jzpbuild.vnext --check    # exit 1 when it's out of date (a test runs this)

Once the release is out, its changes move into index.html for good (docs/maintainers/releasing.md,
"The coming-next page") and the lists below start over.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from . import config, glossary

VNEXT = config.SITE_DIR / "vnext.html"
VNEXT_FONT = config.SITE_DIR / "JianZiPu-vnext.ttf"


def next_version() -> str:
    """The version after builder/VERSION (3.200 -> 3.300): the next release's, as the Release screen offers it."""
    major, minor = (config.BUILDER_DIR / "VERSION").read_text(encoding="utf-8").strip().split(".")
    return f"{major}.{int(minor) + 100:03d}"


# what the lessons on index.html say differently once the next release is out: (as today, as next), each
# found exactly once (a test fails when index.html moves on and one no longer matches)
CHANGES: list[tuple[str, str]] = [
    # the example in the top box: vertical words without their colon
    ("：大八五半轮七 ：上五一 ：进 ", "：大八五半轮七 上五一 进 "),
    (":v8.5banlun7 :shang51 :jin ", ":v8.5banlun7 shang51 jin "),
    # How to type: the vertical words
    ("""<li id="vertical">A word written down the side (上, 下, 泛起…) starts with a colon. Chinese is safest here, as some pinyin spellings are alike. <text><r>：</r>上七九</text> or <text><r>:</r>shang79</text> → <jzp>:shang79</jzp>. A coming version of the font lets you leave the colon out: <a href="./vnext.html#whats-new-vertical">see the next release</a>.</li>""",
     """<li id="vertical">A word written down the side (上, 下, 泛起…) starts with a colon. Chinese is safest here, as some pinyin spellings are alike. <text><r>：</r>上七九</text> or <text><r>:</r>shang79</text> → <jzp>:shang79</jzp>. A word with a character only a vertical word can hold (上, 下, 退, 分开, 少息…) needs no colon: <text>上七九</text> or <text>shang79</text> → <jzp>shang79</jzp>.</li>"""),
    # More rules: the hui numbers
    ("""<li>The next release reads 十一 to 十三 as hui 11 to 13, and adds 弦 to mark a string: <a href="./vnext.html#whats-new-hui">see what's coming</a>.</li>""",
     """<li><text>名十二勾五</text> or <text>s12k5</text> → <jzp>s12k5</jzp> 十一 to 十三 are hui 11 to 13. 10.2 is <text>名十徽二</text> or <text>名十点二</text>.</li>
        <li><text>名九徽半轮六</text> or <text>s9,banlun6</text> → <jzp>s9,banlun6</jzp> 徽 before a word that starts with 半 ends the number: 9, then 半轮. Without it, <text>名九半轮六</text> is 9.5, then 轮.</li>
        <li><text>名九七弦</text> or <text>s9,7</text> → <jzp>s9,7</jzp> 弦 marks a string: hui 9, string 7, not 9.7. In a chord it closes the first half: <text>撥大九四六弦｜散五</text> or <text>Bv9.4,6|05</text> → <jzp>Bv9.4,6|05</jzp></li>"""),
]

HEAD = """    /* vnext.html: today's font, beside the next one in What's new */
    @font-face { font-family: 'JZP-now'; src: url('./JianZiPu.ttf'); font-display: swap; font-feature-settings: "kern", "liga"; }
    .vnext-banner { background: var(--target); border: 1px solid var(--border); border-radius: 6px; padding: 10px 14px; }
    .whats-new table.cmp { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    .whats-new table.cmp th { text-align: left; font-weight: 600; padding: 6px 10px; border-bottom: 2px solid var(--border-strong); background: var(--bg-sunken); vertical-align: bottom; }
    .whats-new table.cmp td { padding: 6px 10px; border-bottom: 1px solid var(--hairline); vertical-align: middle; }
    .whats-new td.n { color: var(--ink-faint); text-align: right; width: 2.5em; font-size: .9em; }
    .whats-new td.typed { font-family: "LXGW WenKai TC", "Roboto Mono", serif; font-size: 1.15rem; white-space: nowrap; }
    .whats-new td.now, .whats-new td.next { font-size: 44px; line-height: 1.3; white-space: nowrap; }
    .whats-new td.now { font-family: 'JZP-now'; color: var(--ink-faint); }
    .whats-new td.next { font-family: 'JianZiPu'; }
    .whats-new .cmp-scroll { overflow-x: auto; }
    @media (max-width: 759.98px) { .whats-new td.now, .whats-new td.next { font-size: 34px; } }
"""


def _row(n: int, typed: str, *cells: str) -> str:
    mid = "".join(f"<td>{c}</td>" for c in cells)
    return (f'        <tr><td class="n">{n}</td><td class="typed">{typed}</td>{mid}'
            f'<td class="now">{typed}</td><td class="next">{typed}</td></tr>')


def _table(head: list[str], rows: list[tuple]) -> str:
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "\n".join(_row(i, *r) for i, r in enumerate(rows, 1))
    return (f'    <div class="cmp-scroll"><table class="cmp">\n'
            f'        <tr><th></th><th>Typed</th>{th}<th class="now">Today</th><th class="next">Next</th></tr>\n'
            f"{body}\n    </table></div>")


def whats_new(version: str) -> str:
    vertical = [("shang34",), ("上三四",), ("xia79",), ("分开",), ("退",), ("少息",), ("带起",)]
    hui = [("名九半轮六", "9.5", "轮", "6"), ("名九，半轮六", "9", "半轮", "6"), ("名九徽半轮六", "9", "半轮", "6"),
           ("名九半勾六", "9.5", "勾", "6"), ("名九徽半勾六", "9.5", "勾", "6"), ("名十二勾五", "12", "勾", "5"),
           ("名十二徽勾五", "12", "勾", "5"), ("名十徽勾五", "10", "勾", "5"), ("名十徽二勾五", "10.2", "勾", "5"),
           ("名十徽二分勾五", "10.2", "勾", "5"), ("名十点二勾五", "10.2", "勾", "5"), ("名七六挑五", "7.6", "挑", "5"),
           ("名七徽六挑五", "7.6", "挑", "5")]
    xian = [("名九七", "hui 9.7"), ("名九七弦", "hui 9, string 7"),
            ("撥大九四六弦|散五", "撥: thumb, hui 9.4, string 6 | open string 5"),
            ("撥大九四弦|散五", "撥: thumb, hui 9, string 4 | open string 5")]
    return f"""    <div class="whats-new">
    <h3 id="whats-new">What's new in {version}</h3>
    <p>Each example drawn in today's font (grey) and in {version}.</p>
    <h4 id="whats-new-vertical">Vertical words without the colon</h4>
    <p>A word with a character only a vertical word can hold (上, 下, 退, 分开, 少息, 带起…) is set vertically without typing the colon:
      <text>shang34</text> gives the same as <text>:shang34</text>. The colon still works, and words that need it to stand vertically (<text>:lun</text>, <text>:0</text>) still do.</p>
{_table([], vertical)}
    <h4 id="whats-new-hui">Hui numbers in Chinese</h4>
    <ul>
      <li><strong>十一, 十二 and 十三 are always hui 11, 12 and 13.</strong> 10.2 is written <text>十徽二</text>, <text>十徽二分</text> or <text>十点二</text>. 十四 to 十九 and 十半 are still 10.4 to 10.9 and 10.5.</li>
      <li><strong>徽 is a decimal point, as 点 is:</strong> <text>十徽二</text> is 10.2 and <text>七徽六</text> is 7.6. 分 may close the decimal (<text>十徽二分</text>). 徽 with nothing after it closes the number: <text>十徽</text> is 10.</li>
      <li><strong>徽 before a 半 that starts a word ends the number</strong>, as a comma does: <text>名九徽半轮六</text> is 9, then 半轮. Without 徽, 9.5 comes first: <text>名九半轮六</text> is 9.5, then 轮.</li>
    </ul>
{_table(["Hui", "Right hand", "String"], hui)}
    <h4 id="whats-new-xian">弦 marks a string</h4>
    <p>弦 (or 絃) after a number marks it as a string, and keeps it from joining the number before it. In a chord it closes the first half before the bar:
      <text>撥大九四六弦|散五</text> is 撥 with the thumb at hui 9.4 on string 6, and the open string 5, the same as <text>Bv9.4,6|05</text>.</p>
{_table(["Reads as"], xian)}
    </div>
"""


def _once(page: str, old: str, new: str, what: str) -> str:
    n = page.count(old)
    if n != 1:
        raise ValueError(f"site/index.html: {what} is there {n} times, not once: update CHANGES in "
                         f"builder/jzpbuild/vnext.py to match the page ({old[:60]!r}…)")
    return page.replace(old, new)


def render(index: str, version: str | None = None) -> str:
    """vnext.html from index.html's text."""
    version = version or next_version()
    page = index
    page = _once(page, '<meta name="viewport" content="width=device-width, initial-scale=1">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                 f'  <!-- written by `cd builder && python3 -m jzpbuild.vnext` from index.html: edit those, not this -->\n'
                 '  <meta name="robots" content="noindex">', "the viewport meta")
    page = re.sub(r"<title>[^<]*</title>", f"<title>JianZiPu Font {version} (preview)</title>", page, count=1)
    page = _once(page, "src: url('./JianZiPu.ttf');", "src: url('./JianZiPu-vnext.ttf');", "the font's @font-face src")
    page = _once(page, "  </style>", HEAD + "  </style>", "the end of the page's style")
    banner = (f'<p class="vnext-banner"><small>A preview of this page once JianZiPu {version} is out, its notation drawn in a '
              f'preview build of {version}. <a href="#whats-new">What\'s new in {version}</a> · '
              '<a href="./">The page for today\'s font</a>. The download is still today\'s font.</small></p>')
    page = re.sub(r'<p class="vnext-link">.*?</p>', lambda _: banner, page, count=1, flags=re.S)
    if banner not in page:
        raise ValueError("site/index.html: the coming-next link at the top (<p class=\"vnext-link\">) isn't there")
    page = _once(page, '<a href="#how-to-type">How to type</a>',
                 f'<a href="#whats-new">What\'s new in {version}</a>\n        <a href="#how-to-type">How to type</a>', "the contents link to How to type")
    page = _once(page, '<h3 id="how-to-type">', whats_new(version).lstrip() + '\n    <h3 id="how-to-type">', "the How to type title")
    for old, new in CHANGES:
        page = _once(page, old, new, "a lesson the next release changes")
    # the glossary as the next font reads it: no colon where it sets the word vertically by itself
    return glossary.render(page, vertical_only=glossary.vertical_only_for())


def build_font() -> None:
    subprocess.run([sys.executable, "-m", "jzpbuild", "-o", str(VNEXT_FONT), "--fea-out", ""], cwd=config.BUILDER_DIR, check=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jzpbuild.vnext", description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if site/vnext.html is out of date")
    ap.add_argument("--font", action="store_true", help="also rebuild site/JianZiPu-vnext.ttf (needs the base font)")
    args = ap.parse_args(argv)
    try:
        new = render(config.SITE_INDEX.read_text(encoding="utf-8"))
    except (ValueError, glossary.GlossaryError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    old = VNEXT.read_text(encoding="utf-8") if VNEXT.exists() else ""
    if args.check:
        if new != old:
            print("error: site/vnext.html is out of date: run `cd builder && python3 -m jzpbuild.vnext`.", file=sys.stderr)
            return 1
        print("site/vnext.html is up to date")
        return 0
    if args.font:
        build_font()
    if new != old:
        VNEXT.write_text(new, encoding="utf-8")
        print("wrote site/vnext.html")
    else:
        print("site/vnext.html is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
