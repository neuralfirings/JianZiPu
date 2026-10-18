"""Local dev server for the JZP Font Builder app.

    cd src-fonttools && python3 -m jzpbuild.devserver [--port 5713]

Serves the built app (app/build/, if present) and this folder as static
files, plus a JSON API over the repo's input files. Single user, local only
(binds 127.0.0.1); every write goes to the real files under inputs/.

API (all JSON):
  GET  /api/design                 design.json + hash + warnings + stats
  PUT  /api/design                 {design, base_hash} -> write (409 on conflict)
  POST /api/design/check           {design} -> errors/warnings/stats, no write
  POST /api/resolve                {design?, layout, choice, pinned?, center?} -> positions
  POST /api/words                  {design?, words:[...]} -> per word: glyphs, layout, positions
  GET  /api/glyphs                 catalog rows (components.csv) + areas + svg presence
  PUT  /api/glyphs                 {rows, base_hash, design?} -> rewrite components.csv (409 if it changed
                                   on disk, 400 with `errors` if a spelling clashes or is malformed)
  POST /api/typing/preview         {design?, rows, words?, base_rows?, compare_words?} -> unsaved spellings
                                   compiled into the last build (GSUB only): typed words, round trip,
                                   clashes, characters the font doesn't carry yet, words that change
  GET  /api/svgs                   {name: svg text}
  POST /api/svg/check              {svg} -> what the build makes of it (flattened outline, counts, bounds)
  PUT  /api/svg/<name>             {svg, base_hash?, overwrite?} -> write inputs/svg/<name>.svg; 409 when the file
                                   exists (no base_hash) or changed on disk since it was loaded (hash mismatch)
  POST /api/build                  start a build (one at a time); each build goes to its own temp dir
  GET  /api/build/status           {state, log, started, finished, ok, build, builds}
  GET  /api/builds/<id>/JianZiPu.ttf   that exact build (?download=1 sets Content-Disposition)
  GET  /JianZiPu.ttf               the latest build (cache-busted by the client)
"""

from __future__ import annotations

import argparse
import csv
import atexit
import signal
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import config, data, glyphs, typing_preview
from .positioning import emit, resolve, schema, shapes

APP_BUILD_DIR = config.BUILDER_DIR.parent / "app" / "build"


# ---------------------------------------------------------------- helpers

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _read_design_text() -> str:
    return config.DESIGN_JSON.read_text(encoding="utf-8")


def _design_payload(d: dict | None = None, text: str | None = None) -> dict:
    text = text if text is not None else _read_design_text()
    d = d if d is not None else json.loads(text)
    design = schema.parse_design(d)
    warnings = schema.validate(design)
    st = emit.stats(design)
    return {"design": d, "hash": _hash(text), "warnings": warnings, "stats": st}


def _design_from(body: dict) -> schema.Design:
    if body.get("design"):
        return schema.parse_design(body["design"])
    return data.load_design()


def shape_from_choice(layout: schema.Layout, choice: list) -> shapes.Shape:
    """Build the shape the editor describes: per slot null (absent), an
    alternative index, or a list of alternative indices (repeated slot)."""
    for s in shapes.enumerate_shapes(layout):
        if [list(c) if isinstance(c, tuple) else c for c in s.choice] == choice:
            return s
    raise ValueError(f"no such shape {choice!r} in layout {layout.name!r}")


def resolve_payload(design: schema.Design, layout_name: str, choice: list,
                    pinned: dict[str, str] | None, center: bool = True) -> dict:
    layout = design.layout(layout_name)
    shape = shape_from_choice(layout, choice)
    pinned = {k: v for k, v in (pinned or {}).items() if v}
    try:
        pos = resolve.resolve(design, layout, shape, pinned, center=center)
        error = None
    except resolve.Unresolvable as err:
        pos, error = {}, str(err)
    chosen = resolve.plan(layout, shape)
    return {
        "ok": error is None,
        "error": error,
        "elements": [{"name": e.name, "el": e.el, "area": e.area, "slot": e.slot, "instance": e.instance,
                      "size": design.areas[e.area].size,
                      "x": pos.get(e.name, (None, None))[0], "y": pos.get(e.name, (None, None))[1]}
                     for e in shape.elements],
        "chosen": {f"{axis}:{name}": (rel.raw if rel else None) for (axis, name), rel in chosen.items()},
        "pins": resolve.pins_needed(layout, shape, design),
    }


class WordShaper:
    """Software model of the font's positioning for typed test words: GSUB
    through HarfBuzz on the last built font (glyph names only), then the
    same longest-rule-first matching the emitted GPOS performs, then the
    resolver. Lets the app preview unsaved design changes on real words."""

    def __init__(self):
        self._font = None
        self._font_mtime = None

    def glyph_runs(self, words: list[str]) -> list[list[str]] | None:
        import uharfbuzz as hb
        path = BUILD.latest or (config.OUTPUT_FONT if config.OUTPUT_FONT.exists() else config.CURRENT_FONT)
        mtime = path.stat().st_mtime
        if self._font is None or self._font_mtime != mtime:
            self._font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
            self._font_mtime = mtime
        out = []
        for w in words:
            buf = hb.Buffer()
            buf.add_str(w)
            buf.guess_segment_properties()
            hb.shape(self._font, buf, {"liga": True, "kern": False})
            out.append([self._font.glyph_to_string(i.codepoint) for i in buf.glyph_infos])
        return out

    @staticmethod
    def match(design: schema.Design, rules: list[emit.Rule], glyphs: list[str],
              other: dict[str, list[str]] | None = None) -> list[dict]:
        """Walk the glyph run the way the pos_y lookup does: at each position
        the first rule (longest first) whose tokens cover the next glyphs wins
        and consumes them."""
        def covers(token: str, glyph: str) -> bool:
            if token.startswith("@area_"):
                return glyph in design.areas[token[len("@area_"):]].glyphs
            if token.startswith("@"):
                return glyph in (other or {}).get(token, ())
            return token == glyph
        words = []
        i = 0
        while i < len(glyphs):
            hit = None
            for r in rules:
                n = len(r.tokens)
                if i + n <= len(glyphs) and all(covers(t, g) for t, g in zip(r.tokens, glyphs[i:i + n])):
                    hit = r
                    break
            if hit is None:
                words.append({"glyphs": [glyphs[i]], "layout": None})
                i += 1
                continue
            words.append({"glyphs": glyphs[i:i + len(hit.tokens)], "layout": hit.layout, "rule": hit})
            i += len(hit.tokens)
        return words


WORDS = WordShaper()


def words_payload(design: schema.Design, words: list[str], runs: list[list[str]] | None = None) -> dict:
    rules, _, reg = emit.build_rules(design)
    runs = WORDS.glyph_runs(words) if runs is None else runs
    out = []
    for word, glyphs in zip(words, runs):
        pieces = []
        pen = 0
        for piece in WordShaper.match(design, rules, glyphs, reg.other):
            if piece["layout"] is None:
                g = piece["glyphs"][0]
                adv = next((a.advance for a in design.areas.values() if g in a.glyphs), 0)
                pieces.append({"glyphs": [g], "layout": None, "elements": [], "pen": pen})
                pen += adv or (1000 if g in ("space", "advance", "numbersign") else 0)
                continue
            r = piece["rule"]
            layout = design.layout(r.layout)
            pinned = {k: v for k, v in r.bucket if v}
            pos = resolve.resolve(design, layout, r.shape, pinned)
            els = []
            for e, g in zip(r.shape.elements, piece["glyphs"]):
                x, y = pos[e.name]
                els.append({"name": e.name, "area": e.area, "glyph": g, "x": x + pen, "y": y,
                            "size": design.areas[e.area].size})
            pieces.append({"glyphs": piece["glyphs"], "layout": r.layout, "shape": r.shape.names,
                           "choice": [list(c) if isinstance(c, tuple) else c for c in r.shape.choice],
                           "pinned": pinned, "elements": els, "pen": pen})
            pen += sum(design.areas[e.area].advance for e in r.shape.elements)
        out.append({"word": word, "glyphs": glyphs, "pieces": pieces, "advance": pen})
    return {"ok": True, "words": out}


# ---------------------------------------------------------------- build runner

class BuildRunner:
    """Runs `python3 -m jzpbuild` one at a time. Every build writes its own JianZiPu.ttf into a
    fresh temporary directory (never the repo), and the last few builds stay available for
    download and for the Tester at /api/builds/<id>/JianZiPu.ttf."""

    KEEP = 8

    def __init__(self):
        self.lock = threading.Lock()
        self.state = "idle"
        self.log: list[str] = []
        self.started = self.finished = None
        self.ok = None
        self.builds: list[dict] = []        # newest last: {id, path, time, bytes, ok, seconds}
        self._seq = 0
        self._current: Path | None = None
        atexit.register(self.cleanup)

    def start(self) -> bool:
        with self.lock:
            if self.state == "running":
                return False
            self.state, self.log, self.ok = "running", [], None
            self.started, self.finished = time.time(), None
            self._seq += 1
            self._current = Path(tempfile.mkdtemp(prefix=f"jzp-build-{self._seq}-")) / "JianZiPu.ttf"
        threading.Thread(target=self._run, daemon=True).start()
        return True

    def _run(self):
        out = self._current
        cmd = [sys.executable, "-m", "jzpbuild", "-o", str(out), "--fea-out", ""]
        proc = subprocess.Popen(cmd, cwd=str(config.BUILDER_DIR), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            self.log.append(line.rstrip("\n"))
        rc = proc.wait()
        with self.lock:
            self.ok = rc == 0 and out.exists()
            self.state = "done"
            self.finished = time.time()
            if self.ok:
                self.register(out, seconds=self.finished - self.started)

    def register(self, path: Path, seconds: float | None = None) -> dict:
        """Keep a finished font: list it, prune old ones."""
        b = {"id": f"b{self._seq}", "path": path, "time": time.time(), "bytes": path.stat().st_size,
             "ok": True, "seconds": seconds}
        self.builds.append(b)
        for old in self.builds[:-self.KEEP]:
            shutil.rmtree(old["path"].parent, ignore_errors=True)
        self.builds = self.builds[-self.KEEP:]
        return b

    def get(self, build_id: str) -> dict | None:
        return next((b for b in self.builds if b["id"] == build_id), None)

    @property
    def latest(self) -> Path | None:
        return self.builds[-1]["path"] if self.builds else None

    def cleanup(self):
        for b in self.builds:
            shutil.rmtree(b["path"].parent, ignore_errors=True)
        self.builds = []

    def public(self, b: dict) -> dict:
        return {"id": b["id"], "time": b["time"], "bytes": b["bytes"], "ok": b["ok"], "seconds": b["seconds"],
                "url": f"/api/builds/{b['id']}/JianZiPu.ttf", "file": str(b["path"])}

    def status(self) -> dict:
        latest = self.builds[-1] if self.builds else None
        return {"state": self.state, "log": self.log, "started": self.started, "finished": self.finished,
                "ok": self.ok, "font_exists": latest is not None,
                "font_mtime": latest["time"] if latest else None,
                "build": self.public(latest) if latest else None,
                "builds": [self.public(b) for b in reversed(self.builds)]}


BUILD = BuildRunner()


# ---------------------------------------------------------------- glyph SVG files

SVG_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def svg_path_for(name: str) -> Path:
    if not SVG_NAME.match(name) or name.endswith("."):
        raise ValueError("glyph names use letters, digits, '_', '-' and '.', e.g. md_9 or lg_gou")
    return config.COMPONENTS_DIR / f"{name}.svg"


class SvgConflict(Exception):
    pass


def write_svg(name: str, svg_text: str, overwrite: bool, base_hash: str | None = None) -> dict:
    """Write one glyph file. A new file needs `overwrite` to be false and no file on disk; an
    existing file is replaced only when `base_hash` matches what is on disk (or `overwrite`)."""
    path = svg_path_for(name)
    existed = path.exists()
    if existed and not overwrite:
        if base_hash is None:
            raise FileExistsError(f"{path.name} already exists")
        if _hash(path.read_text(encoding="utf-8")) != base_hash:
            raise SvgConflict(f"{path.name} changed on disk since it was loaded")
    info = glyphs.flatten_svg_text(svg_text)       # validates: raises on anything the build can't use
    path.write_text(svg_text if svg_text.endswith("\n") else svg_text + "\n", encoding="utf-8")
    return {"ok": True, "name": name, "file": f"inputs/svg/{path.name}", "bytes": len(svg_text.encode("utf-8")),
            "existed": existed, "hash": _hash(path.read_text(encoding="utf-8")),
            **{k: v for k, v in info.items() if k != "d"}}


# ---------------------------------------------------------------- glyph catalog

CSV_FIELDS = list(typing_preview.ROW_FIELDS)


class CsvConflict(Exception):
    pass


class SpellingErrors(Exception):
    def __init__(self, errors):
        super().__init__(f"{len(errors)} spelling problem(s)")
        self.errors = errors


def _read_csv_text() -> str:
    return config.COMPONENTS_CSV.read_text(encoding="utf-8-sig")


def glyphs_payload() -> dict:
    text = _read_csv_text()
    rows = list(csv.DictReader(io.StringIO(text)))
    design = data.load_design()
    svgs = {p.stem for p in config.COMPONENTS_DIR.glob("*.svg")}
    by_glyph = {r["glyph_name"].strip(): r for r in rows}
    areas_of = {}
    for a in design.areas.values():
        for g in a.glyphs:
            areas_of.setdefault(g, []).append(a.name)
    catalog = []
    for g in sorted(svgs | set(by_glyph) | set(areas_of)):
        r = by_glyph.get(g, {})
        catalog.append({"glyph": g, "svg": g in svgs, "areas": areas_of.get(g, []), "row": g in by_glyph,
                        **{k: (r.get(k) or "").strip() for k in CSV_FIELDS if k != "glyph_name"}})
    return {"fields": CSV_FIELDS, "glyphs": catalog, "control": sorted(config.CONTROL_GLYPHS),
            "order": [r["glyph_name"].strip() for r in rows], "hash": _hash(text)}


def write_glyph_rows(rows: list[dict], base_hash: str | None = None, design: dict | None = None) -> dict:
    """Rewrite components.csv from the app's rows. Refuses when the file changed on disk since
    `base_hash`, and when any spelling clashes or can't be generated (the build would fail).
    Rows keep the file's order; new glyphs go at the end; rows with nothing to say are dropped."""
    current = _read_csv_text()
    if base_hash and base_hash != _hash(current):
        raise CsvConflict("components.csv changed on disk since it was loaded")
    recs = [typing_preview.clean_record(r) for r in rows]
    recs = [r for r in recs if r["glyph_name"] and any(r[k] for k in CSV_FIELDS if k != "glyph_name")]
    d = design if design is not None else json.loads(_read_design_text())
    errors = typing_preview.issues(typing_preview.rows_from(recs, d), typing_preview.known_glyphs(d))["errors"]
    if errors:
        raise SpellingErrors(errors)
    order = {r["glyph_name"].strip(): i for i, r in enumerate(csv.DictReader(io.StringIO(current)))}
    recs.sort(key=lambda r: order.get(r["glyph_name"], len(order)))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    w.writeheader()
    for r in recs:
        w.writerow(r)
    config.COMPONENTS_CSV.write_text(buf.getvalue(), encoding="utf-8")
    data.cache_clear_all()
    return {"ok": True, "rows": len(recs), "hash": _hash(buf.getvalue())}



def _preview_base_font() -> Path | None:
    for p in (BUILD.latest, config.OUTPUT_FONT, config.CURRENT_FONT):
        if p and Path(p).exists():
            return Path(p)
    return None


def typing_payload(body: dict) -> dict:
    """Unsaved spellings -> preview font -> typed words, the spelling round trip,
    clashes, and which sample words change against the saved spellings."""
    design = body.get("design") or json.loads(_read_design_text())
    rows = typing_preview.rows_from(body.get("rows", []), design)
    out = {"ok": True, **typing_preview.issues(rows, typing_preview.known_glyphs(design))}
    base = _preview_base_font()
    if base is None:
        return {**out, "ok": False, "error": "Build the font once to preview spellings."}
    prev = typing_preview.FONTS.get(base, rows, design)
    out.update(seconds=prev.seconds, not_built=prev.not_built, missing_chars=prev.missing_chars,
               roundtrip=typing_preview.roundtrip(prev, rows) if body.get("roundtrip", True) else [])
    words = [w for w in body.get("words", []) if w]
    if words:
        shaped = typing_preview.shape(prev, words)
        sd = schema.parse_design(design)
        laid = words_payload(sd, words, runs=[s["glyphs"] for s in shaped])["words"]
        for w, s in zip(laid, shaped):
            w["texts"] = s["texts"]
        out["words"] = laid
    compare = [w for w in body.get("compare_words", []) if w]
    if compare and body.get("base_rows") is not None:
        before = typing_preview.shape(typing_preview.FONTS.get(base, typing_preview.rows_from(body["base_rows"], design), design), compare)
        after = typing_preview.shape(prev, compare)
        out["changed"] = [{"word": a["word"], "before": a["glyphs"], "after": b["glyphs"], "after_texts": b["texts"]}
                          for a, b in zip(before, after) if a["glyphs"] != b["glyphs"]]
    return out


# ---------------------------------------------------------------- HTTP

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(config.BUILDER_DIR), **kw)

    # -- plumbing
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _font(self, path: Path, attachment: bool = False):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "font/ttf")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if attachment:
            self.send_header("Content-Disposition", 'attachment; filename="JianZiPu.ttf"')
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            return
        super().log_message(fmt, *args)

    def _serve_app(self, path: str) -> bool:
        """Serve the built SvelteKit app (SPA fallback to index.html)."""
        if not APP_BUILD_DIR.exists():
            return False
        rel = path.lstrip("/") or "index.html"
        target = (APP_BUILD_DIR / rel)
        if not target.is_file():
            target = APP_BUILD_DIR / "index.html"
        ctype = self.guess_type(str(target))
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        return True

    # -- routes
    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/design":
                return self._json(_design_payload())
            if path == "/api/glyphs":
                return self._json(glyphs_payload())
            if path == "/api/svgs":
                return self._json({p.stem: p.read_text(encoding="utf-8")
                                   for p in sorted(config.COMPONENTS_DIR.glob("*.svg"))})
            if path == "/api/build/status":
                return self._json(BUILD.status())
            m = re.match(r"^/api/builds/([A-Za-z0-9]+)/JianZiPu\.ttf$", path)
            if m:
                b = BUILD.get(m.group(1))
                if not b or not b["path"].exists():
                    return self._json({"ok": False, "error": f"no build {m.group(1)} (builds live only while this server runs)"}, 404)
                return self._font(b["path"], attachment="download=1" in (urlparse(self.path).query or ""))
            if path.startswith("/api/"):
                return self._json({"ok": False, "error": f"unknown endpoint {path}"}, 404)
        except Exception as err:  # noqa: BLE001
            return self._json({"ok": False, "error": str(err)}, 500)
        if path == "/JianZiPu.ttf":
            font = BUILD.latest or (config.OUTPUT_FONT if config.OUTPUT_FONT.exists() else None)
            if font is None:
                return self._json({"ok": False, "error": "no build yet"}, 404)
            return self._font(font)
        if path.startswith("/inputs/") or path.startswith("/tests/") or path.startswith("/tools/") or path.startswith("/app/"):
            return super().do_GET()
        if self._serve_app(path):
            return
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/design/check":
                try:
                    return self._json({"ok": True, **{k: v for k, v in _design_payload(body["design"], json.dumps(body["design"])).items() if k != "design"}})
                except schema.DesignError as err:
                    return self._json({"ok": False, "error": str(err)})
            if path == "/api/resolve":
                design = _design_from(body)
                return self._json(resolve_payload(design, body["layout"], body["choice"], body.get("pinned"),
                                                  body.get("center", True)))
            if path == "/api/words":
                design = _design_from(body)
                return self._json(words_payload(design, list(body.get("words", []))))
            if path == "/api/typing/preview":
                return self._json(typing_payload(body))
            if path == "/api/svg/check":
                try:
                    return self._json({"ok": True, **glyphs.flatten_svg_text(body["svg"])})
                except Exception as err:  # noqa: BLE001 — anything the build would choke on
                    return self._json({"ok": False, "error": str(err)})
            if path == "/api/build":
                started = BUILD.start()
                return self._json({"ok": started, "status": BUILD.status(),
                                   "error": None if started else "a build is already running"})
            return self._json({"ok": False, "error": f"unknown endpoint {path}"}, 404)
        except (schema.DesignError, ValueError, KeyError) as err:
            return self._json({"ok": False, "error": str(err)}, 400)
        except Exception as err:  # noqa: BLE001
            import traceback
            return self._json({"ok": False, "error": str(err), "traceback": traceback.format_exc()}, 500)

    def do_PUT(self):
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/design":
                current = _read_design_text()
                if body.get("base_hash") and body["base_hash"] != _hash(current):
                    return self._json({"ok": False, "error": "design.json changed on disk since it was loaded",
                                       "conflict": True, "hash": _hash(current)}, 409)
                design = schema.parse_design(body["design"])          # validates
                text = schema.dump_design(body["design"])
                config.DESIGN_JSON.write_text(text, encoding="utf-8")
                data.cache_clear_all()
                return self._json({"ok": True, **{k: v for k, v in _design_payload(body["design"], text).items() if k != "design"}})
            if path == "/api/glyphs":
                try:
                    return self._json(write_glyph_rows(body["rows"], body.get("base_hash"), body.get("design")))
                except CsvConflict as err:
                    return self._json({"ok": False, "error": str(err), "conflict": True, "hash": _hash(_read_csv_text())}, 409)
                except SpellingErrors as err:
                    return self._json({"ok": False, "error": str(err), "errors": err.errors}, 400)
            if path.startswith("/api/svg/"):
                name = path[len("/api/svg/"):]
                try:
                    return self._json(write_svg(name, body["svg"], bool(body.get("overwrite")), body.get("base_hash")))
                except FileExistsError as err:
                    return self._json({"ok": False, "error": str(err), "exists": True}, 409)
                except SvgConflict as err:
                    return self._json({"ok": False, "error": str(err), "conflict": True,
                                       "disk": svg_path_for(name).read_text(encoding="utf-8")}, 409)
                except Exception as err:  # noqa: BLE001
                    return self._json({"ok": False, "error": str(err)}, 400)
            return self._json({"ok": False, "error": f"unknown endpoint {path}"}, 404)
        except schema.DesignError as err:
            return self._json({"ok": False, "error": str(err)}, 400)
        except Exception as err:  # noqa: BLE001
            import traceback
            return self._json({"ok": False, "error": str(err), "traceback": traceback.format_exc()}, 500)


def main(argv=None):
    p = argparse.ArgumentParser(description="JZP Font Builder dev server")
    p.add_argument("--port", type=int, default=5713)
    args = p.parse_args(argv)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"JZP Font Builder: http://127.0.0.1:{args.port}/  "
          f"(app: {'built' if APP_BUILD_DIR.exists() else 'not built -- run npm run build in app/, or npm run dev'})")
    # A plain `kill` (or a launcher stopping the server) skips atexit; turn it into a normal
    # exit so the temp build folders are removed either way.
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        BUILD.cleanup()


if __name__ == "__main__":
    main()
