"""The one-off copy of drafts from the Storage bucket into the drafts table (jzpbuild/migrate_drafts.py).
Supabase is a fake in memory; nothing leaves the machine.

Run:  cd builder && python3 -m pytest tests/test_migrate_drafts.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild.migrate_drafts import Migration  # noqa: E402


def bundle(commit="abc"):
    return {"manifest": {"kind": "jzp-draft", "format": 1, "base": {"commit": commit}}, "design": {}, "typing": {}, "svgs": {}, "base": {}}


class FakeSupabase:
    def __init__(self, files, rows=()):
        self.files = files            # uid -> (bundle or raw bytes, updated_at)
        self.rows = {r: {"user_id": r} for r in rows}
        self.calls = []

    def __call__(self, method, url, headers, body):
        assert headers["Authorization"] == "Bearer service"
        path = url.removeprefix("https://p.supabase.co")
        self.calls.append((method, path))
        data = json.loads(body) if body else None
        if path == "/storage/v1/object/list/drafts":
            if data["prefix"] == "":
                return 200, json.dumps([{"name": u, "id": None} for u in self.files] + [{"name": ".emptyFolderPlaceholder", "id": "x"}]).encode()
            uid = data["prefix"].rstrip("/")
            return 200, json.dumps([{"name": "draft.json", "id": "f", "updated_at": self.files[uid][1]}] if self.files[uid][0] is not None else []).encode()
        if path.startswith("/storage/v1/object/drafts/"):
            uid = path.split("/")[-2]
            content = self.files[uid][0]
            return 200, content if isinstance(content, bytes) else json.dumps(content).encode()
        if path == "/rest/v1/drafts?select=user_id":
            return 200, json.dumps(list(self.rows.values())).encode()
        if path == "/rest/v1/drafts" and method == "POST":
            assert "ignore-duplicates" in headers["Prefer"]
            for r in data:
                self.rows.setdefault(r["user_id"], r)
            return 201, b""
        return 404, b"{}"


def test_copies_each_draft_once_keeping_its_time_and_commit():
    fake = FakeSupabase({"u1": (bundle("c1"), "2026-10-20T06:35:37Z"), "u2": (bundle("c2"), "2026-10-19T10:00:00Z")}, rows=["u2"])
    counts = Migration("https://p.supabase.co", "service", fake).run(say=lambda _: None)
    assert counts == {"copied": 1, "skipped": 1, "failed": 0}
    assert fake.rows["u1"] == {"user_id": "u1", "bundle": bundle("c1"), "base_commit": "c1", "updated_at": "2026-10-20T06:35:37Z"}
    assert fake.rows["u2"] == {"user_id": "u2"}  # already there: untouched


def test_dry_run_writes_nothing():
    fake = FakeSupabase({"u1": (bundle(), "2026-10-20T06:35:37Z")})
    counts = Migration("https://p.supabase.co", "service", fake).run(dry_run=True, say=lambda _: None)
    assert counts["copied"] == 1
    assert not fake.rows
    assert not any(m == "POST" and p == "/rest/v1/drafts" for m, p in fake.calls)


def test_reports_a_file_that_is_not_a_draft_and_carries_on():
    fake = FakeSupabase({"bad": (b"not json", "t"), "empty": (None, None), "u1": (bundle(), "t1")})
    said = []
    counts = Migration("https://p.supabase.co", "service", fake).run(say=said.append)
    assert counts == {"copied": 1, "skipped": 1, "failed": 1}
    assert any("bad: FAILED" in s for s in said)
    assert "u1" in fake.rows
