"""Stdlib-only dev server for the offline browser tools.

  python -m jzpbuild.devserver              # serve on http://127.0.0.1:5713/
  python -m jzpbuild.devserver --port 9000

Serves src-fonttools/ over plain HTTP so tools/jzpbuilder.html can fetch()
inputs/components.csv, inputs/layouts.json, and inputs/svg/*.svg directly.
This is the only supported way to open the tool — a plain file:// double
click can't fetch() sibling files (Chromium blocks it), so devserver must
be running.

Small JSON routes on top of static file serving:
  GET  /api/svgs   -> {glyph_name: svg_text, ...} for every inputs/svg/*.svg
  GET  /api/config -> {right_selectors, input_paths, output_path} straight
                       from config.py — lets the page restrict "area_right"
                       candidates to the current layout's RIGHT_SELECTORS
                       family, and prefill the Build Font modal's default
                       input paths, without hardcoding a JS copy of either.
  POST /api/build  -> runs `python3 -m jzpbuild` in src-fonttools/ with optional
                       --input-* overrides from the JSON body
                       ({components, glyph_rename, edge_cases, layouts,
                       svg_dir}, any/all optional), returns
                       {ok, returncode, stdout, stderr}
  POST /api/save   -> writes JSON body values straight to their config.py
                       default paths ({layouts: <json text>, components:
                       <csv text>, svgs: {glyph_name: svg_text, ...}}, any/all
                       optional) — the "Save Configs" button, so Build Font
                       (which only ever reads what's on disk) picks up
                       in-browser edits without a manual download-then-move
                       step. `svgs` writes each entry to
                       inputs/svg/<glyph_name>.svg, overwriting existing files
                       of the same name.

  GET  /api/dynamic/data    -> the full contents of
                       config.DYNAMIC_LAYOUTS_JSON (dynamic_positioning's own
                       area_sizes/layouts data) parsed as JSON — for
                       tools/jzpbuilder-dynamic.html.
  POST /api/dynamic/save    -> writes the JSON body straight to
                       config.DYNAMIC_LAYOUTS_JSON (same shape as the GET
                       above).
  POST /api/dynamic/rule_count -> body: {area_sizes, layouts}. Fills each
                       layout's "areas" from area_sizes and calls
                       dynamic_positioning.build.count_dynamic_pos_rules /
                       estimate_dynamic_pos_bytes on the given (possibly
                       unsaved/in-editor) layouts list. `est_bytes` is the
                       metric that actually predicts a real build's
                       OTLOffsetOverflowError ("All candidates overflowed")
                       -- raw `count` alone is a weak predictor (two real
                       layouts_data.json revisions overflowed at 17,431 and
                       8,722 rules respectively; what determines overflow is
                       total subtable bytes vs. `ceiling_bytes`, a hard 64KB
                       Offset16 limit -- see estimate_dynamic_pos_bytes's
                       docstring for the estimation method). For
                       tools/jzpbuilder-dynamic.html's live complexity
                       warning badge. Returns {ok: true, count, est_bytes,
                       ceiling_bytes} or {ok: false, error} (still HTTP 200)
                       if a layout fails to build an AnchorEngine at all
                       (e.g. a mid-edit malformed relationship) -- a real
                       possibility while editing, not a server error.
  POST /api/dynamic/resolve -> body: {area_sizes, center_x, center_y, center,
                       layout, present, signifier_glyph, area_glyphs}.
                       `center` (bool, default True) is whether to apply
                       chain.resolve's whole-stack vertical centering shift
                       at all -- distinct from center_x/center_y, which say
                       WHERE to center if so. Resolves
                       absolute (x, y) for `layout` (one geometry.LAYOUTS-
                       shaped dict, `areas` is filled in from `area_sizes`)
                       using the REAL dynamic_positioning.anchors.AnchorEngine
                       + dynamic_positioning.chain.resolve — this is
                       jzpbuilder-dynamic.html's only way to compute box
                       positions, so the preview can never drift from what an
                       actual font build produces. `signifier_glyph` is the
                       pivot's own glyph (a legacy ASCII-key `signifier` is
                       still accepted and resolved via signifiers.KEY_TO_GLYPH
                       for backward compatibility); `area_glyphs` is an
                       optional {area: glyph} map for previewing a specific
                       glyph-identity bucket of any OTHER area's gap override
                       (e.g. area_hui's md_5) — see
                       dynamic_positioning/identity.py. Returns
                       {ok, resolved: {area: [x, y]}, chosen: {area: {axis:
                       base_or_null}}} on success (`chosen` identifies, per
                       resolved area/axis, which relationship candidate
                       chain.py picked — lets the frontend grey out any
                       other declared candidates for the same (elem, axis)),
                       or {ok: false, error} (still HTTP 200) if resolution
                       fails for this present/signifier combination (missing
                       gap override, cyclic dependency, etc.) — a real
                       possibility while editing, not a server error.

--figma_pull and --output aren't wired up here — this is a "Build Font"
button for the common case, not a full CLI proxy.
"""

import argparse
import json
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import config, data


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(config.BUILDER_DIR), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/svgs":
            svgs = {p.stem: p.read_text() for p in sorted(config.COMPONENTS_DIR.glob("*.svg"))}
            self._send_json(200, svgs)
            return
        if self.path == "/api/config":
            self._send_json(200, {
                "right_selectors": config.RIGHT_SELECTORS,
                "input_paths": {
                    "components": str(config.COMPONENTS_CSV),
                    "glyph_rename": str(config.GLYPH_RENAME_CSV),
                    "edge_cases": str(config.EDGE_CASES_FEA),
                    "layouts": str(config.LAYOUTS_JSON),
                    "svg_dir": str(config.COMPONENTS_DIR),
                },
                "output_path": str(config.OUTPUT_FONT),
            })
            return
        if self.path == "/api/dynamic/data":
            from dynamic_positioning import signifiers
            data = json.loads(config.DYNAMIC_LAYOUTS_JSON.read_text())
            # key_to_glyph isn't part of the saved sidecar (it's derived from
            # components.csv, not editable layout geometry) — merged in only
            # for the response, so jzpbuilder-dynamic.html can restrict a
            # layout's pivot-area candidates to its selector.contains keys.
            data["key_to_glyph"] = signifiers.KEY_TO_GLYPH
            # area -> components.csv area column, so jzpbuilder-dynamic.html
            # can look up any area's own candidate glyphs (e.g. area_hui's
            # md_5/md_9) for gap-override signifier chips, instead of
            # hardcoding its own copy of this mapping.
            data["area_to_csv_column"] = signifiers.AREA_TO_CSV_COLUMN
            self._send_json(200, data)
            return
        super().do_GET()

    # POST /api/build body -> --input-* CLI flag, mirrors build.py's
    # INPUT_OVERRIDES table (kept in sync manually since one side is Python
    # argparse dests and the other is a JS payload shape).
    BUILD_INPUT_FLAGS = {
        "components": "--input-components",
        "glyph_rename": "--input-glyph-rename",
        "edge_cases": "--input-edge-cases",
        "layouts": "--input-layouts",
        "svg_dir": "--input-svg-dir",
    }

    # POST /api/save body key -> config.py path it overwrites
    SAVE_TARGETS = {
        "layouts": config.LAYOUTS_JSON,
        "components": config.COMPONENTS_CSV,
    }

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        if self.path == "/api/save":
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json(400, {"ok": False, "error": "invalid JSON body"})
                return
            saved = {}
            for key, path in self.SAVE_TARGETS.items():
                if key in payload:
                    path.write_text(payload[key])
                    saved[key] = str(path)
            if "components" in saved:
                data.load_components.cache_clear()
            svgs = payload.get("svgs")
            if isinstance(svgs, dict):
                written = []
                for name, text in svgs.items():
                    if not name or "/" in name or "\\" in name or ".." in name:
                        continue
                    (config.COMPONENTS_DIR / f"{name}.svg").write_text(text)
                    written.append(name)
                saved["svgs"] = f"{len(written)} file(s) -> {config.COMPONENTS_DIR}"
            self._send_json(200, {"ok": True, "saved": saved})
            return

        if self.path == "/api/dynamic/save":
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json(400, {"ok": False, "error": "invalid JSON body"})
                return
            config.DYNAMIC_LAYOUTS_JSON.write_text(json.dumps(payload, indent=2))
            self._send_json(200, {"ok": True, "saved": str(config.DYNAMIC_LAYOUTS_JSON)})
            return

        if self.path == "/api/dynamic/rule_count":
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json(400, {"ok": False, "error": "invalid JSON body"})
                return
            from dynamic_positioning import build

            area_sizes = {k: tuple(v) for k, v in (payload.get("area_sizes") or {}).items()}
            layouts = [dict(l) for l in (payload.get("layouts") or [])]
            for layout in layouts:
                layout["areas"] = area_sizes
            try:
                count = build.count_dynamic_pos_rules(layouts)
                est_bytes = build.estimate_dynamic_pos_bytes(layouts)
            except (KeyError, ValueError) as e:
                self._send_json(200, {"ok": False, "error": str(e)})
                return
            self._send_json(200, {
                "ok": True, "count": count, "est_bytes": est_bytes,
                "ceiling_bytes": build.GPOS_LOOKUP_OFFSET_CEILING_BYTES,
            })
            return

        if self.path == "/api/dynamic/resolve":
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json(400, {"ok": False, "error": "invalid JSON body"})
                return
            from dynamic_positioning import anchors, chain, geometry, signifiers

            layout = dict(payload.get("layout") or {})
            layout["areas"] = {k: tuple(v) for k, v in (payload.get("area_sizes") or {}).items()}
            present = payload.get("present") or {}
            # `signifier_glyph`: the pivot's own glyph (preferred -- what the
            # frontend should send now). `signifier`: an ASCII key, kept for
            # backward compatibility with the pre-generalization payload
            # shape, resolved to a glyph the same way build.py does.
            # `area_glyphs`: {area: glyph} for previewing a specific bucket
            # of any other identity-sensitive area's gap override (e.g.
            # area_hui's md_5) -- see dynamic_positioning/identity.py.
            signifier_glyph = payload.get("signifier_glyph")
            if not signifier_glyph and payload.get("signifier"):
                signifier_glyph = signifiers.KEY_TO_GLYPH.get(payload["signifier"])
            area_glyphs = payload.get("area_glyphs") or {}

            prev_center = (geometry.CENTER_X, geometry.CENTER_Y)
            geometry.CENTER_X = payload.get("center_x", prev_center[0])
            geometry.CENTER_Y = payload.get("center_y", prev_center[1])
            try:
                engine = anchors.AnchorEngine(layout)
                # {area: glyph} -- the pivot's own area gets signifier_glyph
                # (a legacy caller might send an area_glyphs entry for the
                # pivot area directly instead; signifier_glyph wins if both
                # are present, since it's the more specific/intentional one).
                present_glyphs = dict(area_glyphs)
                if signifier_glyph:
                    present_glyphs[engine.pivot] = signifier_glyph
                _, chosen = chain.plan(engine, present)
                # `center`: whether to apply the whole-stack vertical
                # centering shift at all (jzpbuilder-dynamic.html's
                # "vertically center character" checkbox) -- distinct from
                # center_x/center_y above, which say WHERE to center if so.
                resolved = chain.resolve(engine, present, present_glyphs,
                                          center=payload.get("center", True))
            except (KeyError, ValueError) as e:
                self._send_json(200, {"ok": False, "error": str(e)})
                return
            finally:
                geometry.CENTER_X, geometry.CENTER_Y = prev_center

            self._send_json(200, {
                "ok": True,
                "resolved": {elem: list(xy) for elem, xy in resolved.items()},
                "chosen": {
                    elem: {axis: rel.get("base") for axis, rel in by_axis.items()}
                    for elem, by_axis in chosen.items()
                },
            })
            return

        if self.path == "/api/build":
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = {}
            argv = []
            for key, flag in self.BUILD_INPUT_FLAGS.items():
                val = (payload.get(key) or "").strip()
                if val:
                    argv += [flag, val]
            result = subprocess.run(
                [sys.executable, "-m", "jzpbuild", *argv],
                cwd=str(config.BUILDER_DIR), capture_output=True, text=True,
            )
            self._send_json(200, {
                "ok": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            })
            return

        self._send_json(404, {"error": f"no such route: {self.path}"})


class DevServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # A browser aborting/superseding a fetch() (e.g. a second /api/svgs
        # request firing before the first finished writing) closes the
        # socket mid-response — not a real server error, so don't dump a
        # traceback for it.
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="jzpbuild.devserver",
        description="Serve src-fonttools/ over HTTP for tools/*.html (fetch()-based "
                     "auto-load + the Build Font modal).")
    p.add_argument("--port", type=int, default=5713)
    args = p.parse_args(argv)

    httpd = DevServer(("127.0.0.1", args.port), Handler)
    base = f"http://127.0.0.1:{args.port}"
    print(f"serving {config.BUILDER_DIR} at {base}/")
    print(f"open {base}/tools/jzpbuilder.html")
    print("Ctrl-C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
