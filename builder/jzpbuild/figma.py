"""Fetch glyph SVGs and layout geometry straight from the Figma file.

Replaces the manual Figma export ritual (detach / outline stroke / slice /
rename / copy) and the hand-exported figma.css.

Requires FIGMA_TOKEN in the environment (a Figma personal access token) and
the file key (from the file's URL) in config.FIGMA_FILE_KEY. Only scans the
page named config.FIGMA_PAGE_NAME (default "main") — other pages (drafts,
archive, WIP) are ignored entirely, even if they contain nodes that would
otherwise look like glyphs or layouts.

  python -m jzpbuild.figma                    # fetch everything into builder/generated_inputs
  python -m jzpbuild.figma --browser-data-only # just refresh positions.js/svg_data.js from what's on disk

Fetched artifacts:
  builder/generated_inputs/svg/<glyph>.svg   component SVGs (API-rendered, bounds-corrected)
  builder/generated_inputs/positions.json    layout/area geometry
  builder/generated_inputs/meta.json         figma file version, for cache invalidation
  builder/generated_inputs/positions.js      positions.json mirrored for tools/positions_checker.html
  builder/generated_inputs/svg_data.js       svg/*.svg mirrored for tools/positions_checker.html

Bounds correction: Figma's image-render endpoint crops each exported SVG's
canvas to the tight bounding box of its rendered ink (node["absoluteRenderBounds"]),
discarding where that ink sat relative to the component's own declared frame
size (node["absoluteBoundingBox"]). Several JZP glyphs (e.g. mod_zhu, mod_chuo)
intentionally draw outside their frame — that bleed is load-bearing for
positioning (glyphs.py measures height from the frame, not the ink). Each
downloaded SVG is rewritten post-download to restore the frame as the canvas,
translating content by (render_bounds - frame_bounds) so bleed is preserved
as negative/overflowing coordinates, matching the historical manual "export
Slice" SVGs.
"""

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

import requests

from . import config

ET.register_namespace("", "http://www.w3.org/2000/svg")

API = "https://api.figma.com"

# node names that are glyph components: md_*, lg_*, mod_*, xl_*, blank*
GLYPH_NAME_RE = re.compile(r"^(md|lg|mod|xl)_[\w.+]+$|^blank(_\w+)?$")
# tolerate the export-era "_slice" suffix on node names
SLICE_SUFFIX = "_slice"


def token() -> str:
    t = os.environ.get("FIGMA_TOKEN")
    if not t:
        sys.exit("FIGMA_TOKEN not set — create a personal access token in "
                 "Figma (Settings > Security > Personal access tokens)")
    return t


# Figma's own reported wait is honored up to this cap; a longer one usually
# means a hard daily/monthly image-export quota, not a transient throttle,
# and blindly sleeping through it would hang the command for hours or days.
MAX_AUTO_RETRY_WAIT = 60


def get(path: str, max_retries=6, **params) -> dict:
    """GET against the Figma API, retrying on rate limits (429) and
    transient server errors (5xx) with backoff. Figma's own Retry-After
    header is honored (capped at MAX_AUTO_RETRY_WAIT); otherwise backs off
    2s, 4s, 8s, ...
    """
    for attempt in range(max_retries + 1):
        r = requests.get(f"{API}{path}", headers={"X-Figma-Token": token()},
                         params=params, timeout=120)
        if r.status_code == 429 or r.status_code >= 500:
            raw = r.headers.get("Retry-After")
            wait = float(raw) if raw else 2 ** (attempt + 1)
            if wait > MAX_AUTO_RETRY_WAIT:
                sys.exit(
                    f"figma API {r.status_code}: server asked us to wait "
                    f"{wait:.0f}s (~{wait / 3600:.1f}h) before retrying "
                    f"{path!r}. This is longer than a transient rate limit "
                    f"and likely means a daily/monthly image-export quota "
                    f"was hit (common on Figma's free tier). Not auto-"
                    f"retrying — try again later, request a smaller batch, "
                    f"or check your plan's API limits.")
            if attempt == max_retries:
                r.raise_for_status()
            print(f"  figma API {r.status_code}, retrying in {wait:.0f}s "
                 f"(attempt {attempt + 1}/{max_retries}) ...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()


def find_page(document, page_name: str) -> dict:
    """The top-level CANVAS node (Figma "page") matching page_name."""
    pages = [c for c in document.get("children", []) if c.get("type") == "CANVAS"]
    for p in pages:
        if p.get("name", "").strip().lower() == page_name.strip().lower():
            return p
    available = ", ".join(repr(p.get("name", "")) for p in pages)
    sys.exit(f"no Figma page named {page_name!r} — available pages: {available}")


def walk(node, visit, parents=()):
    visit(node, parents)
    for child in node.get("children", []):
        walk(child, visit, parents + (node,))


def find_areas(node) -> list[dict]:
    """All area_* descendants under a layout node, at any nesting depth.

    Stops descending into a nested layout_* frame (its areas belong to that
    layout, not this one) so areas can't leak across layouts if one is
    nested inside another (e.g. a reference/instance).
    """
    found = []
    for child in node.get("children", []):
        cname = child.get("name", "").strip()
        if cname.startswith("layout_"):
            continue
        if cname.startswith("area_") and child.get("absoluteBoundingBox"):
            found.append(child)
        found.extend(find_areas(child))
    return found


def glyph_node_name(node) -> str | None:
    name = node.get("name", "").strip()
    if name.endswith(SLICE_SUFFIX):
        name = name[: -len(SLICE_SUFFIX)]
    return name if GLYPH_NAME_RE.match(name) else None


def _box(b: dict | None) -> dict | None:
    if b is None:
        return None
    return {"x": b["x"], "y": b["y"], "width": b["width"], "height": b["height"]}


def collect(document) -> tuple[dict[str, str], dict, dict]:
    """Return (glyph name -> node id, glyph name -> frame/render geometry, positions dict)."""
    glyph_ids: dict[str, str] = {}
    glyph_geom: dict[str, dict] = {}
    positions: dict[str, dict] = {}

    def visit(node, parents):
        gname = glyph_node_name(node)
        if gname and node.get("type") in ("COMPONENT", "FRAME", "GROUP", "INSTANCE"):
            # keep the first (top-most) node for each glyph name
            if gname not in glyph_ids:
                glyph_ids[gname] = node["id"]
                glyph_geom[gname] = {
                    "frame": _box(node.get("absoluteBoundingBox")),
                    "render": _box(node.get("absoluteRenderBounds")),
                }

        name = node.get("name", "").strip()
        if name.startswith("layout_") and node.get("absoluteBoundingBox"):
            box = node["absoluteBoundingBox"]
            layout = positions.setdefault(name, {"width": round(box["width"])})
            for child in find_areas(node):
                cname = child.get("name", "").strip()
                cbox = child["absoluteBoundingBox"]
                x = round(cbox["x"] - box["x"])
                y = round(cbox["y"] - box["y"])
                w, h = round(cbox["width"]), round(cbox["height"])
                layout[cname] = {
                    "x": x, "y": y, "w": w, "h": h,
                    # baseline flip used by the GPOS generator (see gpos.py);
                    # same formula scripts.cjs applied to figma.css
                    "yd": 1000 - y - h - 200,
                }

    walk(document, visit)
    return glyph_ids, glyph_geom, positions


def restore_frame_bounds(svg_bytes: bytes, geom: dict | None) -> bytes:
    """Undo Figma's ink-cropping: recanvas the SVG to the node's declared
    frame size, translating content so out-of-frame bleed is preserved.

    Falls back to returning svg_bytes unchanged if geometry is missing (e.g.
    absoluteRenderBounds absent for this node type) or the ink already fits
    the frame (nothing to correct).
    """
    if not geom or not geom.get("frame") or not geom.get("render"):
        return svg_bytes
    frame, render = geom["frame"], geom["render"]
    dx = round(render["x"] - frame["x"], 3)
    dy = round(render["y"] - frame["y"], 3)
    fw, fh = frame["width"], frame["height"]
    if dx == 0 and dy == 0 and abs(render["width"] - fw) < 0.5 and abs(render["height"] - fh) < 0.5:
        return svg_bytes  # ink already matches the frame; no correction needed

    root = ET.fromstring(svg_bytes)
    children = list(root)
    for c in children:
        root.remove(c)
    group = ET.SubElement(root, "g")
    group.set("transform", f"translate({dx} {dy})")
    for c in children:
        group.append(c)
    root.set("width", str(fw))
    root.set("height", str(fh))
    root.set("viewBox", f"0 0 {fw} {fh}")
    return ET.tostring(root, encoding="unicode").encode()


def write_browser_data() -> None:
    """Mirror positions.json and every SVG in COMPONENTS_DIR into .js files
    tools/positions_checker.html loads via <script src> (see config.py's
    POSITIONS_JS/SVG_DATA_JS for why: fetch()/XHR can't load file:// sibling
    files in Chromium, but a script tag can).

    Written by fetch() after every download; also safe to call standalone
    (--browser-data-only) to refresh these for SVGs placed by hand rather
    than via --figma_pull, or if positions.json was hand-edited.
    """
    positions = json.loads(config.POSITIONS_JSON.read_text())
    config.POSITIONS_JS.write_text(
        "window.JZP_POSITIONS = " + json.dumps(positions) + ";\n")

    svg_data = {p.stem: p.read_text() for p in sorted(config.COMPONENTS_DIR.glob("*.svg"))}
    config.SVG_DATA_JS.write_text(
        "window.JZP_SVG_DATA = " + json.dumps(svg_data) + ";\n")

    print(f"  wrote {config.POSITIONS_JS.name} and {config.SVG_DATA_JS.name} "
          f"({len(svg_data)} SVGs) for tools/positions_checker.html")


def fetch(force=False) -> None:
    config.GENERATED_INPUTS_DIR.mkdir(exist_ok=True)
    config.COMPONENTS_DIR.mkdir(exist_ok=True)

    doc = get(f"/v1/files/{config.FIGMA_FILE_KEY}")
    version = doc.get("version")
    if not force and config.META_JSON.exists():
        if json.loads(config.META_JSON.read_text()).get("version") == version:
            print(f"cache is current (figma version {version})")
            return

    page = find_page(doc["document"], config.FIGMA_PAGE_NAME)
    glyph_ids, glyph_geom, positions = collect(page)
    print(f"found {len(glyph_ids)} glyph components, "
          f"{len(positions)} layouts on page {config.FIGMA_PAGE_NAME!r}")

    config.POSITIONS_JSON.write_text(json.dumps(positions, indent=1))

    ids = list(glyph_ids.values())
    id_to_name = {v: k for k, v in glyph_ids.items()}
    corrected = 0
    for i in range(0, len(ids), 50):
        if i > 0:
            time.sleep(1)  # image rendering is rate-limited more strictly than other endpoints
        batch = ids[i:i + 50]
        result = get(f"/v1/images/{config.FIGMA_FILE_KEY}",
                     ids=",".join(batch), format="svg")
        for node_id, url in result["images"].items():
            name = id_to_name[node_id]
            if not url:
                print(f"  WARNING: no image for {name}")
                continue
            svg = requests.get(url, timeout=120)
            svg.raise_for_status()
            content = svg.content
            geom = glyph_geom.get(name)
            fixed = restore_frame_bounds(content, geom)
            if fixed != content:
                corrected += 1
            (config.COMPONENTS_DIR / f"{name}.svg").write_bytes(fixed)
        print(f"  downloaded {min(i + 50, len(ids))}/{len(ids)} SVGs")
    print(f"  restored frame bounds on {corrected} glyph(s) with out-of-frame bleed")

    write_browser_data()
    config.META_JSON.write_text(json.dumps({"version": version}))
    print(f"cached figma version {version} in {config.GENERATED_INPUTS_DIR}")


if __name__ == "__main__":
    if "--browser-data-only" in sys.argv:
        write_browser_data()
    else:
        fetch(force="--force" in sys.argv)
