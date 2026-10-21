"""One-off: copy testers' drafts from the old Storage bucket (drafts/<user id>/draft.json) into the
drafts table (supabase/002_drafts_table.sql). Run once, on your own computer, after 002:

    cd builder && python3 -m jzpbuild.migrate_drafts            # copies, never overwrites a row
    cd builder && python3 -m jzpbuild.migrate_drafts --dry-run  # only lists what it would copy

It reads SUPABASE_URL and SUPABASE_SERVICE_KEY from the shell or builder/.env (the service key
never leaves this computer). A row that already exists is left as it is, so running it again is
safe. Each copied row keeps the file's last-saved time. Then check the rows and run
supabase/003_drop_drafts_bucket.sql. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Callable

from . import config
from .hosted import load_env_file

BUCKET = "drafts"
FILE = "draft.json"

# (method, url, headers, body) -> (status, bytes); swapped out by the tests
Request = Callable[[str, str, dict, bytes | None], tuple[int, bytes]]


def _urlopen(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class Migration:
    def __init__(self, url: str, key: str, request: Request = _urlopen):
        self.url, self.request = url.rstrip("/"), request
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    def _json(self, method: str, path: str, body=None, extra: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        headers = {**self.headers, **({"Content-Type": "application/json"} if data is not None else {}), **(extra or {})}
        status, raw = self.request(method, self.url + path, headers, data)
        if status >= 300:
            raise RuntimeError(f"{method} {path}: HTTP {status} {raw[:200].decode(errors='replace')}")
        return json.loads(raw) if raw else None

    def folders(self) -> list[str]:
        """The user ids that have a folder in the bucket."""
        rows = self._json("POST", f"/storage/v1/object/list/{BUCKET}", {"prefix": "", "limit": 1000})
        return [r["name"] for r in rows or [] if r.get("id") is None]  # folders have no id

    def stamp(self, uid: str) -> str | None:
        rows = self._json("POST", f"/storage/v1/object/list/{BUCKET}", {"prefix": f"{uid}/", "limit": 10, "search": FILE})
        hit = next((r for r in rows or [] if r.get("name") == FILE), None)
        return hit and (hit.get("updated_at") or hit.get("created_at"))

    def download(self, uid: str) -> dict:
        status, raw = self.request("GET", f"{self.url}/storage/v1/object/{BUCKET}/{uid}/{FILE}", self.headers, None)
        if status >= 300:
            raise RuntimeError(f"download {uid}/{FILE}: HTTP {status}")
        return json.loads(raw)

    def existing(self) -> set[str]:
        rows = self._json("GET", "/rest/v1/drafts?select=user_id")
        return {r["user_id"] for r in rows or []}

    def insert(self, uid: str, bundle: dict, stamp: str | None):
        row = {"user_id": uid, "bundle": bundle, "base_commit": (bundle.get("manifest") or {}).get("base", {}).get("commit")}
        if stamp:
            row["updated_at"] = stamp
        self._json("POST", "/rest/v1/drafts", [row], {"Prefer": "resolution=ignore-duplicates,return=minimal"})

    def run(self, dry_run: bool = False, say: Callable[[str], None] = print) -> dict:
        have = self.existing()
        counts = {"copied": 0, "skipped": 0, "failed": 0}
        for uid in self.folders():
            if uid in have:
                say(f"  {uid}: already in the table, left as it is")
                counts["skipped"] += 1
                continue
            stamp = self.stamp(uid)
            if not stamp:
                say(f"  {uid}: no {FILE} in the folder")
                counts["skipped"] += 1
                continue
            try:
                bundle = self.download(uid)
                if bundle.get("manifest", {}).get("kind") != "jzp-draft":
                    raise RuntimeError("not a draft bundle")
                if not dry_run:
                    self.insert(uid, bundle, stamp)
                say(f"  {uid}: {'would copy' if dry_run else 'copied'} (saved {stamp})")
                counts["copied"] += 1
            except (RuntimeError, ValueError) as e:
                say(f"  {uid}: FAILED, {e}")
                counts["failed"] += 1
        return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="list what would be copied, write nothing")
    args = ap.parse_args(argv)
    load_env_file(config.BUILDER_DIR / ".env")
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY (shell or builder/.env).", file=sys.stderr)
        return 2
    print(f"Drafts in {url}, bucket {BUCKET}:")
    c = Migration(url, key).run(dry_run=args.dry_run)
    print(f"{c['copied']} {'to copy' if args.dry_run else 'copied'}, {c['skipped']} skipped, {c['failed']} failed.")
    return 1 if c["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
