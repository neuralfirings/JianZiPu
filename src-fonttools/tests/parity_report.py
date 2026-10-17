"""Position parity between two builds of the font (HarfBuzz).

    cd src-fonttools
    python3 -m jzpbuild --classic_pos -o /tmp/classic.ttf --fea-out ""
    python3 -m jzpbuild -o /tmp/cursive.ttf --fea-out ""
    python3 tests/parity_report.py /tmp/classic.ttf /tmp/cursive.ttf

GSUB must be identical (same glyph names per word); positions are reported
as deltas (second minus first) with a histogram of the largest per word.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_shaping import shape, CORPUS
a, b = sys.argv[1], sys.argv[2]
KEYS = ["k","l","i","o","U","ki","lo","n","c","u","h","j","V","lun","banlun","ju"]
extra = [t.format(k=k) for k in KEYS for t in ("s7{k}5","fys7{k}5","s7>{k}5","7{k}5","{k}5","fy{k}5","fy>{k}5","s7>\\{k}5","d10.8{k}6")]
extra += ["s7", "7.5", "s7,5", "s7>5", "s7\\5", "fys7", "7\\5", ":v8", ":shang7", ":v8.5banlun7", "Cv9,6|03", "BLv9\\6|05", "TT3", "Cs7>5|03", "fyC88|99", "C7|7"]
words = list(dict.fromkeys(CORPUS + extra))
same = gsub_diff = 0; rows = []
for w in words:
    sa, sb = shape(a, w), shape(b, w)
    if [g for g,_ in sa] != [g for g,_ in sb]:
        gsub_diff += 1; print("GSUB DIFF", repr(w), [g for g,_ in sa], [g for g,_ in sb]); continue
    if sa == sb: same += 1; continue
    def absx(s):
        pen=0; out=[]
        for g,(xa,ya,xo,yo) in s: out.append((g, pen+xo, yo)); pen += xa
        return out
    d = [(g, x2-x1, y2-y1) for (g,x1,y1),(_,x2,y2) in zip(absx(sa), absx(sb)) if (x1,y1)!=(x2,y2)]
    mx = max(abs(v) for _,dx,dy in d for v in (dx,dy))
    rows.append((mx, w, d))
print(f"{len(words)} words: {same} identical, {gsub_diff} GSUB diffs, {len(rows)} position diffs")
rows.sort(reverse=True)
import collections
hist = collections.Counter("<=10" if m<=10 else "<=40" if m<=40 else "<=100" if m<=100 else ">100" for m,_,_ in rows)
print("max |delta| histogram:", dict(hist))
for mx, w, d in rows[:40]:
    print(f"{mx:5.0f} {w!r:16} " + " ".join(f"{g}:{dx:+.0f},{dy:+.0f}" for g,dx,dy in d))
