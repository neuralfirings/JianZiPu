"""The Supabase auth email templates in supabase/emails/ (see its README)."""
import json
import re
from pathlib import Path

EMAILS = Path(__file__).resolve().parents[2] / "supabase" / "emails"
# Variables Supabase passes to auth email templates; .Data.<key> is user metadata.
SUPABASE_VARS = {"ConfirmationURL", "Token", "TokenHash", "SiteURL", "Email", "NewEmail", "RedirectTo", "Data"}
ACTION = re.compile(r"\{\{-?\s*(.*?)\s*-?\}\}", re.S)
FIELD = re.compile(r"(?:^|[\s(|])\.([A-Za-z_]\w*)")


def templates():
    return json.loads((EMAILS / "templates.json").read_text())["templates"]


def variables(text):
    return {f for body in ACTION.findall(text) for f in FIELD.findall(body)}


def test_every_template_is_listed_and_present():
    listed = {t["file"] for t in templates()}
    on_disk = {p.name for p in EMAILS.glob("*.html")} - {"preview.html"}
    assert listed == on_disk
    for t in templates():
        assert t["subject"].strip(), t["id"]
        assert t["dashboard"].strip(), t["id"]


def test_templates_use_only_supabase_variables():
    for t in templates():
        text = (EMAILS / t["file"]).read_text() + t["subject"]
        unknown = variables(text) - SUPABASE_VARS
        assert not unknown, f"{t['file']}: {sorted(unknown)}"
        # a single-brace "{ .Email }" is a typo Supabase would send as written
        assert not re.search(r"(?<!\{)\{\s*\.[A-Za-z]", text), t["file"]


def test_each_template_gives_a_way_to_finish():
    for t in templates():
        used = variables((EMAILS / t["file"]).read_text())
        assert used & {"ConfirmationURL", "Token", "TokenHash"}, t["file"]
