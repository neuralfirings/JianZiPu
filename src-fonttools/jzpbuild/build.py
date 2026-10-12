"""Build orchestration and CLI: python -m jzpbuild [options]."""

import argparse
import sys

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

from . import config
from .base import build_base
from .genfea import generate
from .glyphs import add_component_glyphs


def build(out_path=None, fea_out=None, verbose=False, dynamic_pos=False,
          dynamic_pos_only=False):
    out_path = out_path or config.OUTPUT_FONT
    vlog = print if verbose else (lambda *a: None)

    print("generating feature file ...")
    fea_text = generate(dynamic_pos=dynamic_pos, dynamic_pos_only=dynamic_pos_only)
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
    p.add_argument("--figma_pull", action="store_true",
                   help="fetch SVGs + layouts from Figma first (needs FIGMA_TOKEN)")
    p.add_argument("--dynamic_pos", action="store_true",
                   help="use the experimental mark-attachment GPOS prototype "
                        "for the gou/io/li right-hand families (proof of "
                        "concept, see dynamic_positioning/README.md)")
    p.add_argument("--dynamic_pos_only", action="store_true",
                   help="like --dynamic_pos, but additionally zero out every "
                        "classic-positioned shape dynamic_positioning doesn't "
                        "cover (other right-hand families, vertical-mode "
                        "words, cuo chords) so they render visibly broken "
                        "instead of silently working via classic -- a test "
                        "build for checking dynamic_positioning's actual "
                        "coverage without classic quietly filling the gaps")
    for flag, attr, desc in INPUT_OVERRIDES:
        p.add_argument(f"--{flag.replace('_', '-')}", type=str, default=None,
                       help=f"override the {desc} input path "
                            f"(default {getattr(config, attr)})")
    p.add_argument("--positions", type=str, default=None,
                   help="override dynamic_positioning's own layouts_data.json "
                        f"(default {config.DYNAMIC_LAYOUTS_JSON}) -- only takes "
                        "effect with --dynamic_pos/--dynamic_pos_only, since "
                        "that's the only time dynamic_positioning/ is imported "
                        "at all")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    from pathlib import Path
    for flag, attr, _ in INPUT_OVERRIDES:
        val = getattr(args, flag)
        if val is not None:
            setattr(config, attr, Path(val))
    if args.positions is not None:
        # Must be set before dynamic_positioning.geometry's first import
        # (inside generate(), only reached under --dynamic_pos/
        # --dynamic_pos_only) -- that module reads config.DYNAMIC_LAYOUTS_JSON
        # once, at import time, same as every other INPUT_OVERRIDES path.
        config.DYNAMIC_LAYOUTS_JSON = Path(args.positions)

    if args.figma_pull:
        from .figma import fetch
        fetch()
    fea_out = Path(args.fea_out) if args.fea_out else None
    if args.fea_only:
        text = generate(dynamic_pos=args.dynamic_pos, dynamic_pos_only=args.dynamic_pos_only)
        if fea_out:
            fea_out.write_text(text)
            print(f"wrote {fea_out}")
        else:
            sys.stdout.write(text)
        return 0

    build(out_path=Path(args.output) if args.output else None,
          fea_out=fea_out, verbose=args.verbose, dynamic_pos=args.dynamic_pos,
          dynamic_pos_only=args.dynamic_pos_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
