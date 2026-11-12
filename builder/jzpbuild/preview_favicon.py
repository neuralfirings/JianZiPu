"""The browser-tab icon on pull request previews of the hosted Builder (builder-pr-29.up.railway.app):
the PR number in dark brown, the colour of guqin wood, so preview tabs can be told apart from each
other and from production (builder.jianzipufont.com), which keeps its icons. The web server puts it
into the page as it sends it (webserver._serve_app); local mode never matches.
"""

from __future__ import annotations

import re
from urllib.parse import quote

PRODUCTION_DOMAIN = "jianzipufont.com"
COLOR = "#5C3A21"                         # dark brown, like a guqin's wood
PR_RE = re.compile(r"-pr-(\d{1,4})\.")    # Railway's PR environments: <service>-pr-<n>.up.railway.app
ICON_LINK_RE = re.compile(r'[ \t]*<link rel="icon"[^>]*>\n?')


def pr_number(host: str | None) -> str | None:
    """The PR number a preview host carries ("…-pr-29.…" -> "29"); None on production and elsewhere.
    `host`: X-Forwarded-Host (its first value) or Host, with or without a port."""
    h = (host or "").split(",")[0].strip().lower().split(":")[0]
    if not h or h == PRODUCTION_DOMAIN or h.endswith("." + PRODUCTION_DOMAIN):
        return None                          # never touch production
    m = PR_RE.search(h)
    return m.group(1) if m else None


def href(pr: str) -> str:
    """An SVG icon of the number, as a data URL for <link rel="icon">. Only digits ever reach the SVG."""
    if not pr.isdigit():
        raise ValueError("a PR number is digits only")
    size = 26 if len(pr) <= 2 else 19 if len(pr) == 3 else 14   # shrink so 3-4 digits still fit
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
           '<text x="16" y="17" text-anchor="middle" dominant-baseline="central" '
           f'font-family="Arial, Helvetica, sans-serif" font-weight="700" font-size="{size}" fill="{COLOR}">{pr}</text></svg>')
    return "data:image/svg+xml," + quote(svg, safe="")


def apply(html: str, host: str | None) -> str:
    """The page with its rel="icon" links replaced by one icon of the PR number, on a preview host;
    unchanged anywhere else. The apple-touch-icon and the manifest stay."""
    pr = pr_number(host)
    if not pr or not ICON_LINK_RE.search(html):
        return html
    first = True

    def swap(m: re.Match) -> str:
        nonlocal first
        if not first:
            return ""
        first = False
        indent = m.group(0)[: len(m.group(0)) - len(m.group(0).lstrip(" \t"))]
        return f'{indent}<link rel="icon" href="{href(pr)}" type="image/svg+xml" />\n'
    return ICON_LINK_RE.sub(swap, html)
