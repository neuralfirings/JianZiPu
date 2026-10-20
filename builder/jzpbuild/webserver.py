"""The web server for the JZP Font Builder app (local, or hosted with --hosted).

    cd builder && python3 -m jzpbuild.webserver [--port 5713]

Serves the built app (app/build/, if present) and this folder as static
files, plus a JSON API over the repo's input files. Local mode (default): single user,
binds 127.0.0.1, every write goes to the real files under inputs/.

Every request first passes request_problem(): locally the Host header must name this machine
(DNS-rebinding guard), a write carrying a foreign Origin is refused, and POST/PUT bodies must be
application/json. URL paths with `..` segments get a 404.

Hosted mode (--hosted or JZP_HOSTED=1, see hosted.py): the pilot on a public host. Read-only
(PUTs answer 403; testers' work lives in their own drafts, kept by the app in Supabase), every
POST needs a signed-in tester (Supabase access token in `Authorization: Bearer`), builds take the
tester's draft in the request body and belong to that tester.

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
  DELETE /api/svg/<name>           remove inputs/svg/<name>.svg (local mode; applying a reviewed draft)
  PUT  /api/svg/<name>             {svg, base_hash?, overwrite?} -> write inputs/svg/<name>.svg; 409 when the file
                                   exists (no base_hash) or changed on disk since it was loaded (hash mismatch)
  GET  /api/config                 {mode: local|hosted, commit, supabase_url, supabase_anon_key}
  GET  /api/base                   the checked-in version drafts start from: {commit, design_hash, csv_hash,
                                   svg_hashes}
  POST /api/build                  start a build (one at a time); each build goes to its own temp dir.
                                   Optional body {design?, rows?, svgs?: {name: text}, deleted?: [name]}
                                   builds those instead of the files on disk (a tester's draft)
  GET  /api/build/status           {state, log, started, finished, ok, build, builds} (the caller's builds)
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
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import config, data, glyphs, hosted, typing_preview
from .positioning import emit, resolve, schema, shapes

APP_BUILD_DIR = config.BUILDER_DIR.parent / "app" / "build"

SETTINGS = hosted.Settings()          # replaced in main(); local mode by default
AUTH: hosted.Auth | None = None
MAIN = "main"                         # owner of the checked-in font's build (hosted mode)
MAX_BODY = 32 * 1024 * 1024


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
    unplaced: dict[str, dict[str, str]] = {}
    try:
        pos = resolve.resolve(design, layout, shape, pinned, center=center)
        error = None
    except resolve.Unresolvable as err:
        # still draw the shape: what can be placed is, a part with no rule on an axis sits at 0
        # there and `unplaced` says which part and axis, and why
        error = str(err)
        pos = resolve.resolve(design, layout, shape, pinned, center=center, missing=unplaced)
    chosen = resolve.plan(layout, shape)
    return {
        "ok": error is None,
        "error": error,
        "unplaced": unplaced,
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
        self._fonts: dict[tuple[str, float], object] = {}      # (path, mtime) -> hb.Font, a few kept
        self._lock = threading.Lock()

    def _font(self, path: Path):
        import uharfbuzz as hb
        key = (str(path), path.stat().st_mtime)
        with self._lock:
            f = self._fonts.get(key)
            if f is None:
                f = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
                self._fonts[key] = f
                while len(self._fonts) > 6:
                    self._fonts.pop(next(iter(self._fonts)))
            return f

    def glyph_runs(self, words: list[str], font: Path | None = None) -> list[list[str]] | None:
        import uharfbuzz as hb
        f = self._font(font or BUILD.font_for("local"))
        out = []
        for w in words:
            buf = hb.Buffer()
            buf.add_str(w)
            buf.guess_segment_properties()
            hb.shape(f, buf, {"liga": True, "kern": False})
            out.append([f.glyph_to_string(i.codepoint) for i in buf.glyph_infos])
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


def words_payload(design: schema.Design, words: list[str], runs: list[list[str]] | None = None,
                  font: Path | None = None) -> dict:
    rules, _, reg = emit.build_rules(design)
    runs = WORDS.glyph_runs(words, font) if runs is None else runs
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
    download and for the Tester at /api/builds/<id>/JianZiPu.ttf. Builds belong to an owner:
    "local" on your own machine; in hosted mode the signed-in tester, or MAIN for the checked-in
    font built at start-up. Ids are random, so a build's URL is only known to its owner."""

    KEEP = 8                                  # per owner

    def __init__(self):
        self.lock = threading.Lock()
        self.jobs: dict[str, dict] = {}       # owner -> {state, log, started, finished, ok}
        self.builds: list[dict] = []          # newest last: {id, owner, path, time, bytes, ok, seconds}
        self.running: str | None = None       # owner of the build in progress
        self._seq = 0
        atexit.register(self.cleanup)

    def job(self, owner: str) -> dict:
        return self.jobs.setdefault(owner, {"state": "idle", "log": [], "started": None, "finished": None, "ok": None})

    def start(self, owner: str = "local", inputs: dict | None = None) -> tuple[bool, str | None]:
        """Start a build of the files on disk, or of `inputs` (a draft). False + why when busy."""
        with self.lock:
            if self.running is not None:
                return False, ("a build is already running" if self.running == owner
                               else "Another font is being built right now; try again in a minute.")
            self._seq += 1
            work = Path(tempfile.mkdtemp(prefix=f"jzp-build-{self._seq}-"))
            job = self.job(owner)
            job.update(state="running", log=[], ok=None, started=time.time(), finished=None)
            self.running = owner
        try:
            extra = write_build_inputs(work, inputs) if inputs else []
        except Exception:
            with self.lock:
                job.update(state="done", ok=False, finished=time.time())
                self.running = None
            shutil.rmtree(work, ignore_errors=True)
            raise
        threading.Thread(target=self._run, args=(owner, work, extra), daemon=True).start()
        return True, None

    def _run(self, owner: str, work: Path, extra: list[str]):
        out = work / "JianZiPu.ttf"
        job = self.job(owner)
        cmd = [sys.executable, "-m", "jzpbuild", "-o", str(out), "--fea-out", "", *extra]
        try:
            proc = subprocess.Popen(cmd, cwd=str(config.BUILDER_DIR), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                job["log"].append(line.rstrip("\n"))
            rc = proc.wait()
        except OSError as err:
            job["log"].append(f"could not start the build: {err}")
            rc = -1
        with self.lock:
            ok = rc == 0 and out.exists()
            job.update(ok=ok, state="done", finished=time.time())
            self.running = None
            if ok:
                self.register(out, seconds=job["finished"] - job["started"], owner=owner)
            else:
                shutil.rmtree(work, ignore_errors=True)     # failed builds keep only their log

    def register(self, path: Path, seconds: float | None = None, owner: str = "local") -> dict:
        """Keep a finished font: list it, prune the owner's old ones."""
        b = {"id": f"b{self._seq}{secrets.token_hex(5)}", "owner": owner, "path": path, "time": time.time(),
             "bytes": path.stat().st_size, "ok": True, "seconds": seconds}
        self.builds.append(b)
        mine = [x for x in self.builds if x["owner"] == owner]
        for old in mine[:-self.KEEP]:
            shutil.rmtree(old["path"].parent, ignore_errors=True)
            self.builds.remove(old)
        return b

    def get(self, build_id: str) -> dict | None:
        return next((b for b in self.builds if b["id"] == build_id), None)

    def latest_for(self, owner: str) -> Path | None:
        mine = [b for b in self.builds if b["owner"] == owner]
        return mine[-1]["path"] if mine else None

    @property
    def latest(self) -> Path | None:
        return self.latest_for("local")

    def font_for(self, owner: str) -> Path:
        """The font previews use for `owner`: their latest build, else the checked-in font's
        build, else the last plain build on disk, else the golden."""
        for p in (self.latest_for(owner), self.latest_for(MAIN),
                  config.OUTPUT_FONT if config.OUTPUT_FONT.exists() else None):
            if p and p.exists():
                return p
        return config.CURRENT_FONT

    def cleanup(self):
        for b in self.builds:
            shutil.rmtree(b["path"].parent, ignore_errors=True)
        self.builds = []

    def public(self, b: dict) -> dict:
        out = {"id": b["id"], "time": b["time"], "bytes": b["bytes"], "ok": b["ok"], "seconds": b["seconds"],
               "url": f"/api/builds/{b['id']}/JianZiPu.ttf"}
        if not SETTINGS.hosted:              # where it sits on the server is only your business locally
            out["file"] = str(b["path"])
        return out

    def status(self, owner: str = "local") -> dict:
        job = self.job(owner)
        mine = [b for b in self.builds if b["owner"] == owner]
        latest = mine[-1] if mine else None
        return {"state": job["state"], "log": job["log"], "started": job["started"], "finished": job["finished"],
                "ok": job["ok"], "font_exists": latest is not None,
                "font_mtime": latest["time"] if latest else None,
                "build": self.public(latest) if latest else None,
                "builds": [self.public(b) for b in reversed(mine)]}


def write_build_inputs(work: Path, inputs: dict) -> list[str]:
    """Write a draft's files into a build folder; return the jzpbuild flags that point at them.
    Only what the draft carries is overridden: design.json, components.csv, and the svg/ folder
    (the checked-in SVGs minus `deleted`, plus the draft's own)."""
    args: list[str] = []
    if inputs.get("design") is not None:
        schema.parse_design(inputs["design"])                       # validates
        p = work / "design.json"
        p.write_text(schema.dump_design(inputs["design"]), encoding="utf-8")
        args += ["--design", str(p)]
    if inputs.get("rows") is not None:
        p = work / "components.csv"
        p.write_text(rows_to_csv(inputs["rows"], _read_csv_text()), encoding="utf-8")
        args += ["--input-components", str(p)]
    svgs = inputs.get("svgs") or {}
    deleted = set(inputs.get("deleted") or [])
    if svgs or deleted:
        d = work / "svg"
        d.mkdir()
        for src in config.COMPONENTS_DIR.glob("*.svg"):
            if src.stem not in deleted:
                shutil.copy2(src, d / src.name)
        for name, text in svgs.items():
            svg_path_for(name)                                      # checks the name
            glyphs.flatten_svg_text(text)                           # raises on what the build can't use
            (d / f"{name}.svg").write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        args += ["--input-svg-dir", str(d)]
    return args


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
    text = rows_to_csv(recs, current)
    config.COMPONENTS_CSV.write_text(text, encoding="utf-8")
    data.cache_clear_all()
    return {"ok": True, "rows": len(recs), "hash": _hash(text)}


def rows_to_csv(rows: list[dict], order_from: str) -> str:
    """components.csv text for `rows`, in the row order of `order_from` (new glyphs at the end);
    rows with nothing to say are dropped."""
    recs = [typing_preview.clean_record(r) for r in rows]
    recs = [r for r in recs if r["glyph_name"] and any(r[k] for k in CSV_FIELDS if k != "glyph_name")]
    order = {r["glyph_name"].strip(): i for i, r in enumerate(csv.DictReader(io.StringIO(order_from)))}
    recs.sort(key=lambda r: order.get(r["glyph_name"], len(order)))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    w.writeheader()
    for r in recs:
        w.writerow(r)
    return buf.getvalue()


def base_payload() -> dict:
    """The checked-in version a draft starts from, as hashes (same hash as GET /api/design etc.)."""
    svgs = sorted(config.COMPONENTS_DIR.glob("*.svg"))
    return {"commit": SETTINGS.commit, "date": hosted.font_date([config.DESIGN_JSON, config.COMPONENTS_CSV, config.COMPONENTS_DIR]),
            "design_hash": _hash(_read_design_text()), "csv_hash": _hash(_read_csv_text()),
            "svg_hashes": {p.stem: _hash(p.read_text(encoding="utf-8")) for p in svgs}}



def _preview_base_font(owner: str = "local") -> Path | None:
    p = BUILD.font_for(owner)
    return p if p.exists() else None


def typing_payload(body: dict, owner: str = "local") -> dict:
    """Unsaved spellings -> preview font -> typed words, the spelling round trip,
    clashes, and which sample words change against the saved spellings.
    `svg_names`: glyphs a draft adds (not on disk), so their spellings aren't flagged unknown."""
    design = body.get("design") or json.loads(_read_design_text())
    rows = typing_preview.rows_from(body.get("rows", []), design)
    known = typing_preview.known_glyphs(design) | set(body.get("svg_names") or [])
    out = {"ok": True, **typing_preview.issues(rows, known)}
    base = _preview_base_font(owner)
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

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
EXTRA_HOSTS: set[str] = set()          # main(): the --host address, when it isn't a wildcard


def _hostname(value: str | None) -> str | None:
    """'localhost:5713' / '[::1]:5713' / 'http://x.y:1' -> the bare, lower-case host name."""
    if not value:
        return None
    try:
        return urlparse(value if "//" in value else f"//{value}").hostname
    except ValueError:
        return None


def request_problem(method: str, headers, hosted_mode: bool) -> tuple[int, str] | None:
    """Why a request is refused before it is handled, or None. Guards the local server against
    DNS rebinding (a site whose name points at 127.0.0.1) and cross-site requests:
      - local mode: the Host header must name this machine (loopback, or the --host address);
      - writes (POST/PUT/DELETE) carrying an Origin must come from the same host the request
        names (hosted, behind the proxy) or from a loopback origin (local, incl. the Vite dev server);
      - a POST/PUT body must be JSON, so a plain cross-site form can't send one."""
    host = _hostname(headers.get("Host"))
    if not hosted_mode and host not in LOOPBACK | EXTRA_HOSTS:
        return 403, "This Builder only answers on localhost."
    if method in ("POST", "PUT", "DELETE"):
        origin = headers.get("Origin")
        if origin:
            o = _hostname(origin)
            ok = (o == host) if hosted_mode else (o in LOOPBACK | EXTRA_HOSTS)
            if not ok:
                return 403, "Cross-site request refused."
    if method in ("POST", "PUT") and int(headers.get("Content-Length") or 0) > 0:
        ctype = (headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return 415, "Send JSON (Content-Type: application/json)."
    return None


def _safe_path(path: str) -> bool:
    """False for a URL path that tries to leave the folder it names: a `..` or `.` segment
    (also percent-encoded), a backslash or a NUL. Such a request gets a 404 before any
    file lookup."""
    p = unquote(path)
    if "\\" in p or "\x00" in p:
        return False
    return not any(seg in ("..", ".") for seg in p.split("/"))


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
        if n > MAX_BODY:
            raise ValueError("request too large")
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

    def _owner(self) -> str | None:
        """Who is asking: "local" on your own machine; in hosted mode the signed-in tester's id,
        or None when the request carries no valid Supabase token."""
        if not SETTINGS.hosted:
            return "local"
        auth = self.headers.get("Authorization") or ""
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else None
        user = AUTH.user(token) if AUTH else None
        return user["id"] if user else None

    def _fail(self, err: Exception, status: int = 500):
        """An unexpected error. Locally the message and traceback go to the app (it's your machine);
        hosted, they go to the server log and the tester gets a plain sentence."""
        import traceback
        tb = traceback.format_exc()
        if SETTINGS.hosted:
            sys.stderr.write(f"error {self.command} {urlparse(self.path).path}: {tb}\n")
            return self._json({"ok": False, "error": "Something went wrong on the server. Try again, or send feedback."}, status)
        return self._json({"ok": False, "error": str(err), "traceback": tb}, status)

    def _refused(self, method: str) -> bool:
        """Answer and return True when request_problem() refuses this request."""
        why = request_problem(method, self.headers, SETTINGS.hosted)
        if why is None:
            return False
        self._json({"ok": False, "error": why[1]}, why[0])
        return True

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            return
        super().log_message(fmt, *args)

    def _serve_app(self, path: str) -> bool:
        """Serve the built SvelteKit app (SPA fallback to index.html). Never a file outside
        app/build: the target is resolved (symlinks and all) and must stay inside it."""
        if not APP_BUILD_DIR.exists():
            return False
        root = APP_BUILD_DIR.resolve()
        rel = unquote(path).lstrip("/") or "index.html"
        target = (root / rel).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            target = root / "index.html"
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
        if self._refused("GET"):
            return
        path = urlparse(self.path).path
        if not _safe_path(path):
            return self._json({"ok": False, "error": "not found"}, 404)
        try:
            if path == "/api/design":
                return self._json(_design_payload())
            if path == "/api/glyphs":
                return self._json(glyphs_payload())
            if path == "/api/svgs":
                return self._json({p.stem: p.read_text(encoding="utf-8")
                                   for p in sorted(config.COMPONENTS_DIR.glob("*.svg"))})
            if path == "/api/config":
                return self._json(SETTINGS.public())
            if path == "/api/base":
                return self._json(base_payload())
            if path == "/api/build/status":
                owner = self._owner()
                if owner is None:
                    return self._json({"ok": False, "error": "Sign in first.", "auth": True}, 401)
                return self._json(BUILD.status(owner))
            m = re.match(r"^/api/builds/([A-Za-z0-9]+)/JianZiPu\.ttf$", path)
            if m:
                b = BUILD.get(m.group(1))
                if not b or not b["path"].exists():
                    return self._json({"ok": False, "error": f"no build {m.group(1)} (builds live only while this server runs)"}, 404)
                return self._font(b["path"], attachment="download=1" in (urlparse(self.path).query or ""))
            if path.startswith("/api/"):
                return self._json({"ok": False, "error": f"unknown endpoint {path}"}, 404)
        except hosted.AuthUnavailable as err:
            return self._json({"ok": False, "error": str(err)}, 503)
        except Exception as err:  # noqa: BLE001
            return self._fail(err)
        if path == "/JianZiPu.ttf":
            font = BUILD.latest_for(MAIN if SETTINGS.hosted else "local") or (
                config.OUTPUT_FONT if config.OUTPUT_FONT.exists() else None)
            if font is None:
                return self._json({"ok": False, "error": "no build yet"}, 404)
            return self._font(font)
        if path.startswith("/inputs/") or (path.startswith("/tests/") and not SETTINGS.hosted):
            return super().do_GET()
        if self._serve_app(path):
            return
        if SETTINGS.hosted:                       # never browse the server's folder (src_font/ etc.)
            return self._json({"ok": False, "error": "not found"}, 404)
        return super().do_GET()

    def do_POST(self):
        if self._refused("POST"):
            return
        path = urlparse(self.path).path
        try:
            owner = self._owner()
            if owner is None:
                return self._json({"ok": False, "error": "Sign in first.", "auth": True}, 401)
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
                return self._json(words_payload(design, list(body.get("words", [])), font=BUILD.font_for(owner)))
            if path == "/api/typing/preview":
                return self._json(typing_payload(body, owner))
            if path == "/api/svg/check":
                try:
                    return self._json({"ok": True, **glyphs.flatten_svg_text(body["svg"])})
                except Exception as err:  # noqa: BLE001 — anything the build would choke on
                    return self._json({"ok": False, "error": str(err)})
            if path == "/api/build":
                inputs = {k: body[k] for k in ("design", "rows", "svgs", "deleted") if body.get(k) is not None}
                started, why = BUILD.start(owner, inputs or None)
                return self._json({"ok": started, "status": BUILD.status(owner), "error": why})
            return self._json({"ok": False, "error": f"unknown endpoint {path}"}, 404)
        except hosted.AuthUnavailable as err:
            return self._json({"ok": False, "error": str(err)}, 503)
        except (schema.DesignError, ValueError, KeyError) as err:
            return self._json({"ok": False, "error": str(err)}, 400)
        except Exception as err:  # noqa: BLE001
            return self._fail(err)

    def do_PUT(self):
        if self._refused("PUT"):
            return
        path = urlparse(self.path).path
        if SETTINGS.hosted:
            return self._json({"ok": False, "readonly": True,
                               "error": "This Builder is read-only: your changes are kept in your own draft."}, 403)
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
            return self._fail(err)


    def do_DELETE(self):
        if self._refused("DELETE"):
            return
        path = urlparse(self.path).path
        if SETTINGS.hosted:
            return self._json({"ok": False, "readonly": True,
                               "error": "This Builder is read-only: your changes are kept in your own draft."}, 403)
        if not path.startswith("/api/svg/"):
            return self._json({"ok": False, "error": f"unknown endpoint {path}"}, 404)
        try:
            p = svg_path_for(path[len("/api/svg/"):])
        except ValueError as err:
            return self._json({"ok": False, "error": str(err)}, 400)
        if not p.exists():
            return self._json({"ok": False, "error": f"{p.name} does not exist"}, 404)
        p.unlink()
        data.cache_clear_all()
        return self._json({"ok": True, "file": f"inputs/svg/{p.name}"})


def main(argv=None):
    global SETTINGS, AUTH
    p = argparse.ArgumentParser(description="JianZiPu Font Builder web server")
    p.add_argument("--host", default="127.0.0.1", help="address to listen on (0.0.0.0 in a container)")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT") or 5713))
    p.add_argument("--hosted", action="store_true", help="hosted pilot mode (also JZP_HOSTED=1); see hosted.py")
    args = p.parse_args(argv)
    # local settings (Supabase URL and anon key for the Review screen) from builder/.env
    names = hosted.load_env_file(config.BUILDER_DIR / ".env")
    if names:
        print(f"read {', '.join(sorted(names))} from {config.BUILDER_DIR / '.env'}")
    SETTINGS = hosted.Settings.from_env(hosted=True if args.hosted else None)
    if args.host not in ("0.0.0.0", "::", ""):
        EXTRA_HOSTS.add(args.host.lower())
    if not SETTINGS.hosted and SETTINGS.supabase_service_key:
        print("note: SUPABASE_SERVICE_KEY is only for the hosted server; this local server doesn't need it")
    if SETTINGS.hosted:
        if not (SETTINGS.supabase_url and SETTINGS.supabase_anon_key):
            sys.exit("hosted mode needs SUPABASE_URL and SUPABASE_ANON_KEY")
        AUTH = hosted.Auth(SETTINGS)
        print(hosted.fetch_base_font(SETTINGS))
        if config.SOURCE_FONT.exists():
            BUILD.start(MAIN)                     # the checked-in font, for previews and the Tester
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"JianZiPu Font Builder ({'hosted' if SETTINGS.hosted else 'local'}): http://{args.host}:{args.port}/  "
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
