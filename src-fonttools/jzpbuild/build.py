"""Build orchestration and CLI: python -m jzpbuild [options]."""

import argparse
import sys
from pathlib import Path

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

from . import config
from .base import build_base
from .genfea import generate
from .glyphs import add_component_glyphs


def build(out_path=None, fea_out=None, verbose=False, classic_pos=False):
    out_path = out_path or config.OUTPUT_FONT
    vlog = print if verbose else (lambda *a: None)

    print("generating feature file ...")
    fea_text = generate(classic_pos=classic_pos)
    if fea_out:
        fea_out.write_text(fea_text)
        print(f"  wrote {fea_out}")

    print(f"subsetting base font from {config.SOURCE_FONT.name} ...")
    font = build_base()
    vlog(f"  base font has {font['maxp'].numGlyphs} glyphs after subsetting")

    svg_count = len(list(config.COMPONENTS_DIR.glob("*.svg")))
    print(f"importing {svg_count} component SVGs from {config.COMPONENTS_DIR} ...")
    add_component_glyphs(font)

    print("compiling OpenType features ...")
    addOpenTypeFeaturesFromString(font, fea_text)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(out_path)
    print(f"wrote {out_path} ({font['maxp'].numGlyphs} glyphs)")
    return font


# CLI flag -> config.py attribute it overrides, for the individual input
# files/dirs a build reads. Kept as one table so the --input-* flags, their
# --help text, and the config attributes they patch can't drift apart.
INPUT_OVERRIDES = [
    ("input_components", "COMPONENTS_CSV", "components.csv"),
    ("input_glyph_rename", "GLYPH_RENAME_CSV", "glyphRename.csv"),
    ("input_edge_cases", "EDGE_CASES_FEA", "edge_cases.fea"),
    ("input_layouts", "LAYOUTS_JSON", "layouts.json"),
    ("input_svg_dir", "COMPONENTS_DIR", "svg/ directory"),
]


def main(argv=None):
    p = argparse.ArgumentParser(prog="jzpbuild",
                                description="Build the JianZiPu font")
    p.add_argument("-o", "--output", type=str, default=None,
                   help=f"output font path (default {config.OUTPUT_FONT})")
    p.add_argument("--fea-out", type=str, default=str(config.FEA_OUT_DEFAULT),
                   help="also write the generated .fea here for inspection")
    p.add_argument("--fea-only", action="store_true",
                   help="only generate the feature file, don't build the font")
    p.add_argument("--classic_pos", action="store_true",
                   help="legacy positioning from inputs/layouts.json + gpos.py "
                        "instead of the cursive rules from inputs/design.json "
                        "(only for comparing against the released font)")
    for flag, attr, desc in INPUT_OVERRIDES:
        p.add_argument(f"--{flag.replace('_', '-')}", type=str, default=None,
                       help=f"override the {desc} input path "
                            f"(default {getattr(config, attr)})")
    p.add_argument("--design", type=str, default=None,
                   help=f"override the design file (default {config.DESIGN_JSON})")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    for flag, attr, _ in INPUT_OVERRIDES:
        val = getattr(args, flag)
        if val is not None:
            setattr(config, attr, Path(val))
    if args.design is not None:
        config.DESIGN_JSON = Path(args.design)

    fea_out = Path(args.fea_out) if args.fea_out else None
    if args.fea_only:
        text = generate(classic_pos=args.classic_pos)
        if fea_out:
            fea_out.write_text(text)
            print(f"wrote {fea_out}")
        else:
            sys.stdout.write(text)
        return 0

    build(out_path=Path(args.output) if args.output else None,
          fea_out=fea_out, verbose=args.verbose, classic_pos=args.classic_pos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
