"""Shaping regression test: the new font must shape identically to the old.

Shapes a corpus of tutorial inputs with HarfBuzz against both fonts and
compares the resulting glyph names, advances, and offsets. This exercises the
full GSUB (input -> components) and GPOS (component positioning) pipeline —
the strongest equivalence check we have.

Run directly for a diff report:
    python tests/test_shaping.py [OLD.ttf NEW.ttf]
"""

import sys
from pathlib import Path

import uharfbuzz as hb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jzpbuild import config  # noqa: E402

# tutorial + edge-case corpus (demo page examples and disambiguation cases)
CORPUS = [
    # basic words: left hand + hui + right hand + string
    "s7k5", "d10u6", "f9j3", "v8h2", "x5l1",
    "s7.5k5", "s7,5", "s76", "s7.5>k5",
    # decimals and hui spellings
    "10.2", "13.9", "13+", "11.5", "7.5", "0.5", "1,3", "13",
    # modifiers
    "/u2", "\\k3", ">i4", "fyd10.8ju6", "fys9k5",
    # multi-char latin
    "jiul7", "0k3", "banlunl7", "blk5", "lun6", "sanu1",
    "diejuan", "quanfu3", "banfu2",
    # combined techniques
    "s7ju5", "s7ki5", "s7lo5", "U9,6", "s9U5,6",
    # chords
    "Cv9,6|03", "C88|99", "DCs7,5|02", "TT3", "BL5",
    # vertical words
    ":shang79", ":fenkai", ":banlun", ":大息", ":jiu",
    ":shang", ":xia", ":zhi4", "shang34", "lun3shang",
    # Chinese input
    "名七半急勾五", "名七五", "大九挑五", "中十点二抹一",
    "散挑三", "跪十一剔二", "食外勾一", "名九，半轮六",
    "泛音名七挑五", "大撮", "反撮", "抹挑", "打摘", "勾剔",
    "名十一二", "名十一", "名七徽六挑五", "名七点六挑五",
    # traditional
    "綽", "註", "歴", "雙彈", "撥剌",
    # words with blanks / placeholders / advance
    "s7_5", "*", "s7k5 0k3", "s7k5+0k3", "#s7k5",
    # multi-word text
    "s7.5>k5 jiul7 0k3 s9,4 C88|99",
]

FEATURES = {"liga": True, "kern": True}

# The old FontForge-compiled font has a ligature bug: when a LONGER ligature
# candidate (e.g. 'xiao' over input 'xia', 'three period' over input '13')
# partially matches and runs into the end of the text, the whole position is
# abandoned and no shorter ligature is tried. The feaLib-compiled font is
# spec-correct. For inputs that end in such a prefix, compare with a trailing
# space appended to both sides (which sidesteps the old bug) and separately
# assert the new font shapes the bare input the same as the padded one.
OLD_FONT_EOT_QUIRK = {"13", "0.5", ":xia"}

# Words holding a glyph only a vertical word can place get their colon from the font
# (features.gen_auto_colon); the old font left them unplaced. They must shape like the
# old font shapes them with the colon typed.
AUTO_COLON = {"shang34", "lun3shang", "sanu1", "diejuan", "quanfu3", "banfu2", "*"}


def shape(font_path: str, text: str):
    blob = hb.Blob.from_file_path(font_path)
    face = hb.Face(blob)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, FEATURES)
    names = [font.glyph_to_string(i.codepoint) for i in buf.glyph_infos]
    pos = [(p.x_advance, p.y_advance, p.x_offset, p.y_offset)
           for p in buf.glyph_positions]
    return list(zip(names, pos))


def compare_fonts(old_path: str, new_path: str) -> int:
    failures = 0
    for text in CORPUS:
        if text in OLD_FONT_EOT_QUIRK:
            old = shape(old_path, text + " ")
            new = shape(new_path, text + " ")
            # new font must shape bare and padded input consistently
            if shape(new_path, text) != new[:-1]:
                failures += 1
                print(f"DIFF for {text!r}: new font pads inconsistently")
                continue
        elif text in AUTO_COLON:
            old = shape(old_path, ":" + text)
            new = shape(new_path, text)
        else:
            old = shape(old_path, text)
            new = shape(new_path, text)
        if old != new:
            failures += 1
            print(f"DIFF for {text!r}:")
            width = max(len(str(g)) for g in old + new)
            for i in range(max(len(old), len(new))):
                o = old[i] if i < len(old) else "—"
                n = new[i] if i < len(new) else "—"
                mark = "   " if o == n else ">> "
                print(f"  {mark}{str(o):<{width}}   {n}")
    print(f"{len(CORPUS) - failures}/{len(CORPUS)} inputs shape identically")
    return failures


def test_shaping_matches_current_font():
    import subprocess, tempfile
    import pytest
    if not config.SOURCE_FONT.exists():
        pytest.skip("needs the base font (src_font/TW-Kai-98.ttf), which isn't in the repo")
    new = Path(tempfile.mkdtemp()) / "JianZiPu.new.ttf"
    subprocess.run(
        [sys.executable, "-m", "jzpbuild", "--classic_pos", "-o", str(new), "--fea-out", ""],  # golden is classic-positioned
        cwd=config.BUILDER_DIR, check=True)
    assert compare_fonts(str(config.CURRENT_FONT), str(new)) == 0


# Safari and every iPhone browser shape each word and each space on its own, so a line must come
# out the same shaped a word at a time as shaped whole: no rule may reach over a word to its space.
APART = [
    "shang34 xia34 s9k3 s8k4", ":shang34 :xia34 s9k3", "上三四 下三四 名九勾三",
    "s7.5>k5 jiul7 0k3 k3 fyd9u6 v5.6V5 s9c C03|s6,5 v7U43 :v8.5banlun7 :shang51 :jin ",
    "名七半急勾五 就打七 散勾三 勾三 泛音中九挑六 大五六掩五 名九掐起 撮散三｜名六，五 大七历四三 ：大八五半轮七 ：上五一 ：进 ",
    "Cv9,6|03 :shang34 C88|99", ":fanqi+s9u6 s9k3",
]
# A word's main glyph and where its pen starts, in units: each word one 1000-unit cell.
SEPARATED = {
    "s9k5 :shang34 d7u3": [0, 1000, 2000],
    "s9k5:shang34 d7u3": [0, 1000, 2000],      # a colon with no space before it
    ":shang34:xia34 d7u3": [0, 1000, 2000],
    ":shang34#d7u3": [0, 1000],                # a # straight after a vertical word
    ":shang34:xia34#d7u3": [0, 1000, 2000],
    "#s9k5#:shang34#d7u3": [0, 1000, 2000],
    "#s9k5:shang34#d7u3": [0, 1000, 2000],
    "#:shang34#d7u3": [0, 1000],
}
MAIN = {"md_ming": 150, "md_zhong": 150, "md_shang": 325, "md_xia": 325}


def _shape_whole(font: str, text: str):
    out, pen = [], 0
    for name, (xa, _, xo, yo) in shape(font, text):
        out.append((name, pen + xo, yo))
        pen += xa
    return out, pen


def _shape_apart(font: str, text: str):
    import re
    out, pen = [], 0
    for part in re.findall(r" |[^ ]+", text):
        glyphs, width = _shape_whole(font, part)
        out += [(n, x + pen, y) for n, x, y in glyphs]
        pen += width
    return out, pen


def _built_font():
    import subprocess, tempfile
    import pytest
    if not config.SOURCE_FONT.exists():
        pytest.skip("needs the base font (src_font/TW-Kai-98.ttf), which isn't in the repo")
    out = Path(tempfile.mkdtemp()) / "JianZiPu.ttf"
    subprocess.run([sys.executable, "-m", "jzpbuild", "-o", str(out), "--fea-out", ""],
                   cwd=config.BUILDER_DIR, check=True)
    return str(out)


def test_words_shape_alone_as_in_a_line():
    font = _built_font()
    for text in APART:
        assert _shape_apart(font, text) == _shape_whole(font, text), text
    for text, cells in SEPARATED.items():
        glyphs, _ = _shape_whole(font, text)
        assert [x - MAIN[n] for n, x, _ in glyphs if n in MAIN] == cells, text


if __name__ == "__main__":
    old = sys.argv[1] if len(sys.argv) > 2 else str(config.CURRENT_FONT)
    new = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
    sys.exit(1 if compare_fonts(old, new) else 0)
