"""Compare two .fea files for semantic equivalence (development aid).

Parses both files into named blocks (lookups, features, class definitions)
and compares:
  - class definitions as glyph sets (member order is irrelevant)
  - lookup/feature statement lists, order-sensitively (GSUB/GPOS rule order
    matters), after stripping comments and collapsing whitespace

Usage: python -m jzpbuild.feadiff GOLDEN.fea GENERATED.fea
"""

import re
import sys


def strip_comments(text: str) -> str:
    return re.sub(r"#[^\n]*", "", text)


def tokenize_statements(text: str) -> list[str]:
    stmts = []
    for raw in text.split(";"):
        s = " ".join(raw.split())
        if s:
            stmts.append(s)
    return stmts


def parse(text: str):
    """Return (classes: name->frozenset, blocks: name->[statements])."""
    text = strip_comments(text)
    classes: dict[str, object] = {}
    blocks: dict[str, list[str]] = {}
    toplevel: list[str] = []

    # class definitions: @name = [ ... ]; or @name = @other;
    def grab_class(m):
        name, body = m.group(1), m.group(2).strip()
        if body.startswith("["):
            classes[name] = frozenset(body.strip("[]").split())
        else:
            classes[name] = body  # alias
        return ""

    text = re.sub(r"@([\w.]+)\s*=\s*(\[[^\]]*\]|@[\w.]+)\s*;", grab_class, text)

    # resolve aliases to sets
    for name, val in list(classes.items()):
        seen = set()
        while isinstance(val, str):
            ref = val.lstrip("@")
            if ref in seen or ref not in classes:
                break
            seen.add(ref)
            val = classes[ref]
        classes[name] = val

    # named blocks: lookup NAME { ... } NAME; and feature TAG { ... } TAG;
    def grab_block(m):
        kind, name, body = m.group(1), m.group(2), m.group(3)
        key = f"{kind} {name}"
        blocks.setdefault(key, []).extend(tokenize_statements(body))
        return ""

    # features may contain nested lookup blocks — pull those out first
    pattern = re.compile(r"(lookup)\s+([\w.]+)\s*\{(.*?)\}\s*\2\s*;", re.S)
    while True:
        new_text = pattern.sub(grab_block, text)
        if new_text == text:
            break
        text = new_text
    text = re.sub(r"(feature)\s+([\w.]+)\s*\{(.*?)\}\s*\2\s*;", grab_block, text)

    toplevel = tokenize_statements(text)
    return classes, blocks, toplevel


def sub_input(stmt: str) -> tuple | None:
    """Input glyph sequence of a `sub ... by ...` statement (marks stripped)."""
    if not stmt.startswith("sub "):
        return None
    body = stmt[4:].split(" by ")[0]
    return tuple(t.rstrip("'") for t in body.split())


def order_conflicts(a: list[str], b: list[str]) -> list[tuple[str, str]]:
    """Pairs of rules whose relative order differs between a and b AND whose
    input sequences prefix-shadow each other (so the order is meaningful)."""
    pos_b = {s: i for i, s in enumerate(b)}
    bad = []
    for i, x in enumerate(a):
        for y in a[i + 1:]:
            ix, iy = sub_input(x), sub_input(y)
            if ix is None or iy is None:
                continue
            if ix[: len(iy)] == iy or iy[: len(ix)] == ix:
                if pos_b[x] > pos_b[y]:
                    bad.append((x, y))
    return bad


def compare(golden_path: str, generated_path: str) -> int:
    with open(golden_path) as f:
        g_classes, g_blocks, g_top = parse(f.read())
    with open(generated_path) as f:
        n_classes, n_blocks, n_top = parse(f.read())

    failures = 0

    for name in sorted(set(g_classes) | set(n_classes)):
        a, b = g_classes.get(name), n_classes.get(name)
        if a != b:
            failures += 1
            print(f"CLASS @{name} differs:")
            if isinstance(a, frozenset) and isinstance(b, frozenset):
                if a - b:
                    print(f"  only in golden:    {' '.join(sorted(a - b))}")
                if b - a:
                    print(f"  only in generated: {' '.join(sorted(b - a))}")
            else:
                print(f"  golden:    {a}\n  generated: {b}")

    for name in sorted(set(g_blocks) | set(n_blocks)):
        # exact duplicate statements within a lookup are no-ops (the golden
        # file has a few copy-pasted rows) — dedupe, preserving order
        a = list(dict.fromkeys(g_blocks.get(name, [])))
        b = list(dict.fromkeys(n_blocks.get(name, [])))
        if a == b:
            continue
        sa, sb = set(a), set(b)
        if sa == sb:
            # same rules, different order. Order only matters when rules can
            # shadow each other: for `sub` ligatures, when one input sequence
            # is a prefix of another, the longer must come first in both.
            bad = order_conflicts(a, b)
            if not bad:
                continue
            failures += 1
            print(f"BLOCK {name}: prefix-conflicting rules ordered differently:")
            for x, y in bad[:8]:
                print(f"  {x[:110]}  <vs>  {y[:110]}")
            continue
        failures += 1
        print(f"BLOCK {name} differs ({len(a)} vs {len(b)} statements):")
        for s in [x for x in a if x not in sb][:12]:
            print(f"  only in golden:    {s[:160]}")
        for s in [x for x in b if x not in sa][:12]:
            print(f"  only in generated: {s[:160]}")

    if g_top != n_top:
        sa, sb = set(g_top), set(n_top)
        if sa != sb:
            failures += 1
            print("TOPLEVEL statements differ:")
            for s in sorted(sa - sb)[:10]:
                print(f"  only in golden:    {s[:160]}")
            for s in sorted(sb - sa)[:10]:
                print(f"  only in generated: {s[:160]}")

    print("EQUIVALENT" if failures == 0 else f"{failures} difference group(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(compare(sys.argv[1], sys.argv[2]))
