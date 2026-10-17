"""HarfBuzz vs CoreText (macOS) on one font over the corpus (+extras).

    cd src-fonttools && python3 tests/shaper_parity.py JianZiPu.ttf

Uses tests/ctshape.swift (run with the system `swift`). Every word must
shape identically on both engines; a difference means a GPOS construct one
engine does not support (see jzpbuild/positioning/__init__.py).
"""
import subprocess, sys
import os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_shaping import shape, CORPUS
font = sys.argv[1]
swift = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "ctshape.swift")
KEYS = ["k","l","i","o","U","ki","lo","n","c","u","h","j","V","lun","banlun","ju"]
extra = [t.format(k=k) for k in KEYS for t in ("s7{k}5","fys7{k}5","s7>{k}5","7{k}5","{k}5","fy{k}5","fy>{k}5","s7>\\{k}5","d10.8{k}6")]
extra += ["s7", "7.5", "s7,5", "s7>5", "s7\\5", "fys7", "7\\5", ":v8", ":shang7", ":v8.5banlun7", "Cv9,6|03", "BLv9\\6|05", "TT3", "Cs7>5|03", "fyC88|99", "C7|7"]
words = list(dict.fromkeys(CORPUS + extra))
ct = subprocess.run(["swift", swift, font] + words, capture_output=True, text=True).stdout.splitlines()
same = 0; bad = []
for w, line in zip(words, ct):
    pen = 0; hb = []
    for g, (xa, ya, xo, yo) in shape(font, w):
        hb.append(f"{g}:{pen + xo},{yo}"); pen += xa
    hbs = " ".join(hb); cts = line.split("\t", 1)[1] if "\t" in line else line
    if hbs == cts: same += 1
    else: bad.append((w, hbs, cts))
print(f"HarfBuzz vs CoreText: {same}/{len(words)} identical")
for w, h, c in bad[:15]:
    print(repr(w)); print("  HB", h); print("  CT", c)
