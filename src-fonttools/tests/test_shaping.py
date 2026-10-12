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
    ":shang", ":xia", ":zhi4",
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
    new = Path(tempfile.mkdtemp()) / "JianZiPu.new.ttf"
    subprocess.run(
        [sys.executable, "-m", "jzpbuild", "-o", str(new), "--fea-out", ""],
        cwd=config.BUILDER_DIR, check=True)
    assert compare_fonts(str(config.CURRENT_FONT), str(new)) == 0


if __name__ == "__main__":
    old = sys.argv[1] if len(sys.argv) > 2 else str(config.CURRENT_FONT)
    new = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
    sys.exit(1 if compare_fonts(old, new) else 0)
