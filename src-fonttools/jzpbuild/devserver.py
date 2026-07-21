"""Stdlib-only dev server for the offline browser tools.

  python -m jzpbuild.devserver              # serve on http://127.0.0.1:5713/
  python -m jzpbuild.devserver --port 9000

Serves builder/ over plain HTTP so tools/jzpbuilder.html can fetch()
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
  POST /api/build  -> runs `python3 -m jzpbuild` in builder/ with optional
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

--figma_pull and --output aren't wired up here — this is a "Build Font"
button for the common case, not a full CLI proxy.
"""

import argparse
import json
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import config


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
        description="Serve builder/ over HTTP for tools/*.html (fetch()-based "
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
