"""Hosted (pilot) mode for the web server: the Builder on a public host for invited testers.

In hosted mode the server is read-only: it serves the font as checked in (main), never writes
inputs/, and every tester's work lives in their own draft (in Supabase, kept by the app). The
server only checks who is asking (a Supabase access token) and builds a tester's draft in a temp
folder on request. Settings come from the environment:

  JZP_HOSTED=1               turn hosted mode on (or --hosted)
  SUPABASE_URL               https://<project>.supabase.co
  SUPABASE_ANON_KEY          the public anon key (also handed to the app)
  SUPABASE_SERVICE_KEY       server-only key, used to fetch the base font from Storage
  JZP_BASE_FONT_OBJECT       Storage object of the base font (default assets/TW-Kai-98.ttf)
  JZP_COMMIT                 the deployed commit (set by the Cloud Run deploy, .github/workflows/cloudrun.yml)
  RAILWAY_GIT_COMMIT_SHA     the same, set by Railway; with neither, `git rev-parse HEAD`

Stdlib only (urllib), like the rest of the server.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import config


def load_env_file(path: Path) -> list[str]:
    """Read KEY=VALUE lines from a local .env (gitignored) into os.environ, without overriding
    what the shell already set. Blank lines, # comments, `export ` and surrounding quotes are
    fine. Returns the names it set (never the values)."""
    if not path.is_file():
        return []
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            names.append(key)
    return names


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    hosted: bool = False
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = field(default="", repr=False)
    base_font_object: str = "assets/TW-Kai-98.ttf"
    commit: str | None = None

    @classmethod
    def from_env(cls, hosted: bool | None = None) -> "Settings":
        return cls(
            hosted=_env_flag("JZP_HOSTED") if hosted is None else hosted,
            supabase_url=os.environ.get("SUPABASE_URL", "").rstrip("/"),
            supabase_anon_key=os.environ.get("SUPABASE_ANON_KEY", ""),
            supabase_service_key=os.environ.get("SUPABASE_SERVICE_KEY", ""),
            base_font_object=os.environ.get("JZP_BASE_FONT_OBJECT", "assets/TW-Kai-98.ttf"),
            commit=current_commit(),
        )

    def public(self) -> dict:
        """What the app may know (GET /api/config). Never the service key."""
        return {"mode": "hosted" if self.hosted else "local", "commit": self.commit,
                "supabase_url": self.supabase_url or None, "supabase_anon_key": self.supabase_anon_key or None}


def current_commit() -> str | None:
    sha = os.environ.get("JZP_COMMIT") or os.environ.get("RAILWAY_GIT_COMMIT_SHA")
    if sha:
        return sha
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(config.BUILDER_DIR),
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def font_date(files: list[Path]) -> str | None:
    """When the font's inputs last changed, as an ISO date: the last commit touching them, else
    (a Docker image has no .git) the newest file time."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", *map(str, files)], cwd=str(config.BUILDER_DIR),
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    times = [f.stat().st_mtime for f in files if f.exists()]
    if not times:
        return None
    return datetime.fromtimestamp(max(times), tz=timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- who is asking

class AuthUnavailable(Exception):
    """Supabase couldn't be asked who a token belongs to (network, outage). Not the tester's fault:
    the server answers 503 with a plain sentence, never the underlying error."""


class Auth:
    """Checks a Supabase access token by asking Supabase who it belongs to (GET /auth/v1/user).
    Answers are cached for a few minutes so a busy editing session costs one lookup."""

    TTL = 300

    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache: dict[str, tuple[float, dict | None]] = {}
        self._lock = threading.Lock()

    def fetch_user(self, token: str) -> dict | None:
        s = self.settings
        req = urllib.request.Request(f"{s.supabase_url}/auth/v1/user",
                                     headers={"apikey": s.supabase_anon_key, "Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                user = json.loads(resp.read())
        except urllib.error.HTTPError as err:
            if err.code >= 500:
                raise AuthUnavailable("The sign-in service isn't answering. Try again in a minute.") from err
            return None                      # 401/403: not a valid token
        except (urllib.error.URLError, OSError, ValueError) as err:
            raise AuthUnavailable("The sign-in service isn't answering. Try again in a minute.") from err
        return user if isinstance(user, dict) and user.get("id") else None

    def user(self, token: str | None) -> dict | None:
        if not token:
            return None
        now = time.time()
        with self._lock:
            hit = self._cache.get(token)
            if hit and hit[0] > now:
                return hit[1]
        u = self.fetch_user(token)
        with self._lock:
            # forget failures quickly (a token may be checked again right after sign-in)
            self._cache[token] = (now + (self.TTL if u else 10), u)
            if len(self._cache) > 500:
                for k in [k for k, (t, _) in self._cache.items() if t <= now]:
                    del self._cache[k]
        return u


# ---------------------------------------------------------------- base font

def fetch_base_font(settings: Settings, dest: Path | None = None) -> str:
    """Put the base font (TW-Kai, gitignored) in place for builds: download it from Supabase
    Storage with the service key when it isn't on disk. Returns what happened, for the log."""
    dest = dest or config.SOURCE_FONT
    if dest.exists():
        return f"base font: {dest.name} present"
    if not (settings.supabase_url and settings.supabase_service_key):
        return f"base font: {dest} missing and no SUPABASE_URL / SUPABASE_SERVICE_KEY to fetch it -- builds will fail"
    url = f"{settings.supabase_url}/storage/v1/object/{settings.base_font_object}"
    req = urllib.request.Request(url, headers={"apikey": settings.supabase_service_key,
                                               "Authorization": f"Bearer {settings.supabase_service_key}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
    except urllib.error.URLError as err:
        return f"base font: download from {settings.base_font_object} failed ({err}) -- builds will fail"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(body)
    tmp.replace(dest)
    return f"base font: fetched {settings.base_font_object} ({len(body) // 1024} KB)"
