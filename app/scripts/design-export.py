"""The Builder's design guide (app/static/help/design.html, served at /help/design.html): the
design system artifact (https://claude.ai/artifact/SNGE3ACTZxtP2PLRatJnv8) as one static page.
The design system is the source; this page is a snapshot of it. To refresh it after a change there:
read the system's project/ files into a folder (Claude: Artifact read with their paths), then
    pip install markdown
    python3 app/scripts/design-export.py <folder>/project app/static/help/design.html <version id>
and commit what it writes."""
import json, re, sys, html, datetime
from pathlib import Path
import markdown

SRC = Path(sys.argv[1])          # the design system's project/ folder
OUT = Path(sys.argv[2])
VERSION = sys.argv[3]
URL = 'https://claude.ai/artifact/SNGE3ACTZxtP2PLRatJnv8'

tokens = json.loads((SRC / 'tokens.json').read_text())
bundle = (SRC / 'components/bundle.css').read_text()

def val(v):
    return re.sub(r'\{([A-Za-z0-9_.-]+)\}', r'var(--\1)', v)

light, dark = [], []
for t in tokens['color']['tokens']:
    v = t['value']
    if isinstance(v, str): v = {'light': v}
    light.append(f"--{t['name']}: {val(v['light'])};")
    if 'dark' in v: dark.append(f"--{t['name']}: {val(v['dark'])};")
for fam, stack in tokens['type']['families'].items():
    light.append(f"--font-{fam}: {stack};")
for famname in ('spacing', 'radius', 'size', 'zindex'):
    for t in tokens.get(famname, {}).get('tokens', []):
        light.append(f"--{t['name']}: {t['value']};")
for t in tokens.get('shadow', {}).get('tokens', []):
    v = t['value']
    light.append(f"--{t['name']}: {v['light'] if isinstance(v, dict) else v};")
    if isinstance(v, dict) and 'dark' in v: dark.append(f"--{t['name']}: {v['dark']};")
TOKENS_CSS = (":root { " + " ".join(light) + " }\n"
              "@media (prefers-color-scheme: dark) { :root:not([data-theme=\"light\"]) { " + " ".join(dark) + " color-scheme: dark; } }\n"
              ":root[data-theme=\"dark\"] { " + " ".join(dark) + " color-scheme: dark; }\n")

md = lambda s: markdown.markdown(s, extensions=['tables'])
def section(sid, title, body):
    return sid, title, f'<section id="{sid}"><h2>{html.escape(title)}</h2>{body}</section>'

sections = []
readme = (SRC / 'README.md').read_text()
sections.append(section('principles', 'Principles', md(readme)))
for f, sid in [('phone.md', 'phone'), ('layout-and-density.md', 'layout'), ('states.md', 'states'), ('canvas-and-overlays.md', 'canvas')]:
    text = (SRC / f).read_text()
    m = re.match(r'#\s+(.+)\n', text)
    title = m.group(1).strip() if m else f
    body = text[m.end():] if m else text
    sections.append(section(sid, title, md(body)))

# tokens
def colour_rows():
    out = []
    for t in tokens['color']['tokens']:
        v = t['value'] if isinstance(t['value'], dict) else {'light': t['value']}
        sw = lambda theme: f'<span class="sw" style="background:{html.escape(val(v.get(theme, v["light"])))}"></span><code>{html.escape(v.get(theme, v["light"]))}</code>'
        out.append(f'<tr><td><code>{t["name"]}</code></td><td>{sw("light")}</td><td>{sw("dark")}</td><td>{md(t.get("usage", ""))}</td></tr>')
    return '<table class="tok"><thead><tr><th>Token</th><th>Light</th><th>Dark</th><th>Use</th></tr></thead><tbody>' + ''.join(out) + '</tbody></table>'
def type_rows():
    out = []
    fams = tokens['type']['families']
    for g in tokens['type']['groups']:
        for s in g['styles']:
            fam = s.get('family', g['family'])
            st = f"font-family: var(--font-{fam}); font-size: {s['fontSize']}; line-height: {s['lineHeight']}; font-weight: {s['fontWeight']};" + (f" letter-spacing: {s['letterSpacing']};" if 'letterSpacing' in s else '')
            out.append(f'<tr><td><code>{s["name"]}</code><br><span class="muted">{s["fontSize"]} / {s["lineHeight"]} · {s["fontWeight"]} · {fam}</span></td><td><span style="{st}">{html.escape(s.get("sample", ""))}</span></td><td>{md(s.get("usage", ""))}</td></tr>')
    return '<table class="tok"><thead><tr><th>Style</th><th>Sample</th><th>Use</th></tr></thead><tbody>' + ''.join(out) + '</tbody></table>'
def plain_rows(fam):
    out = [f'<tr><td><code>{t["name"]}</code></td><td><code>{html.escape(t["value"] if isinstance(t["value"], str) else t["value"].get("light", ""))}</code></td><td>{md(t.get("usage", ""))}</td></tr>' for t in tokens.get(fam, {}).get('tokens', [])]
    return '<table class="tok"><thead><tr><th>Token</th><th>Value</th><th>Use</th></tr></thead><tbody>' + ''.join(out) + '</tbody></table>'
tok_body = ('<p>The tokens live in <code>app/src/app.css</code> under these names (CSS custom properties: <code>--bg-app</code>, <code>--control-touch</code>…).</p>'
            '<h3>Colour</h3>' + colour_rows() + '<h3>Type</h3>' + type_rows() +
            ''.join(f'<h3>{name}</h3>' + plain_rows(fam) for fam, name in [('spacing', 'Spacing'), ('radius', 'Radius'), ('size', 'Sizes'), ('shadow', 'Shadows'), ('zindex', 'Layers')]))
sections.append(section('tokens', 'Tokens', tok_body))

# components: README + live preview in an iframe (each preview is a whole document)
def frame(path):
    doc = path.read_text()
    m = re.match(r'<!--\s*@dsCard([^>]*)-->', doc)
    attrs = m.group(1) if m else ''
    h = re.search(r'height=(\d+)', attrs)
    sub = re.search(r'subtitle="([^"]*)"', attrs)
    doc = doc.replace('<head>', '<head><style>' + TOKENS_CSS + bundle + 'html,body{margin:0}</style>', 1)
    return (sub.group(1) if sub else ''), f'<div class="pwrap"><iframe class="preview" title="Preview" loading="lazy" style="height:{int(h.group(1)) if h else 200}px" srcdoc="{html.escape(doc, quote=True)}"></iframe></div>'
comp_html = []
names = sorted(p.name for p in (SRC / 'components').iterdir() if p.is_dir() and p.name != 'Cover')
for n in names:
    d = SRC / 'components' / n
    readme = (d / 'README.md').read_text() if (d / 'README.md').exists() else ''
    sub, fr = frame(d / 'preview.html') if (d / 'preview.html').exists() else ('', '')
    comp_html.append(f'<article class="comp" id="c-{n.lower()}"><h3>{n}</h3>{f"<p class=muted>{html.escape(sub)}</p>" if sub else ""}{md(readme)}{fr}</article>')
sections.append(section('components', 'Components', ''.join(comp_html)))

_, cover = frame(SRC / 'components/Cover/preview.html')
# the cover is drawn at 960 × 320: shown whole, scaled to the column (the script below sets the scale)
cover = '<div class="cover" aria-hidden="true">' + re.sub(r'class="preview"[^>]*style="[^"]*"', 'class="cover-frame" tabindex="-1"', cover, count=1) + '</div>'
toc = ''.join(f'<a href="#{sid}">{html.escape(t)}</a>' for sid, t, _ in sections)
today = datetime.date.today().isoformat()

page = f'''<!DOCTYPE html>
<!-- The JZP Font Builder design guide: a snapshot of the design system ({URL}, version {VERSION}, {today}).
     The design system is the source; to refresh this page, export it again. Not edited by hand. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Design guide · JZP Font Builder</title>
<meta name="description" content="The JZP Font Builder's design system: principles, phone rules, layout, states, canvas overlays, tokens and components.">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@500;600&family=Literata:opsz,wght@7..72,400;7..72,600&family=Noto+Serif+SC:wght@400;600&display=swap">
<style>
{TOKENS_CSS}
* {{ box-sizing: border-box; }}
html {{ scroll-padding-top: 16px; }}
body {{ margin: 0; background: var(--bg-app); color: var(--ink); font: 400 14px/22px var(--font-serif); }}
a {{ color: var(--link); }}
:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
header.top {{ display: flex; align-items: center; gap: var(--space-5); min-height: 48px; padding: var(--space-3) var(--space-6); background: var(--bg-panel); border-bottom: 1px solid var(--border); }}
header.top .name {{ font: 600 20px/1 var(--font-display); color: var(--ink); text-decoration: none; }}
header.top .spacer {{ flex: 1; }}
.layout {{ display: grid; grid-template-columns: 200px minmax(0, 820px); gap: var(--space-8); padding: var(--space-7) var(--space-6) var(--space-9); justify-content: center; }}
.toc {{ position: sticky; top: var(--space-7); align-self: start; display: flex; flex-direction: column; gap: var(--space-1); }}
.toc-title {{ font: 600 16px/20px var(--font-display); margin: 0 0 var(--space-3); }}
.toc a {{ padding: var(--space-2) var(--space-4); border-left: 2px solid transparent; color: var(--ink-muted); text-decoration: none; }}
.toc a:hover {{ color: var(--ink); background: var(--bg-hover); }}
h1, h2, h3 {{ font-family: var(--font-display); font-weight: 600; line-height: 1.2; }}
h1 {{ font-size: 32px; margin: 0 0 var(--space-4); }}
h2 {{ font-size: 22px; margin: 0 0 var(--space-5); }}
h3 {{ font-size: 16px; margin: var(--space-7) 0 var(--space-4); }}
.lede {{ color: var(--ink-muted); margin: 0 0 var(--space-7); }}
section {{ padding-top: var(--space-7); margin-bottom: var(--space-8); border-top: 1px solid var(--border); }}
code {{ font: 400 13px/18px var(--font-mono); background: var(--bg-sunken); border-radius: var(--radius-sm); padding: 0 4px; }}
table {{ width: 100%; border-collapse: collapse; margin: var(--space-4) 0 var(--space-6); font-size: 13px; line-height: 18px; }}
th, td {{ text-align: left; vertical-align: top; padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--hairline); }}
th {{ font-weight: 600; color: var(--ink-muted); }}
td p {{ margin: 0; }}
blockquote {{ margin: var(--space-4) 0; padding: var(--space-4) var(--space-5); border: 1px solid var(--status-info); border-radius: var(--radius-md); background: var(--status-info-bg); }}
blockquote p {{ margin: 0; }}
.muted {{ color: var(--ink-muted); }}
.sw {{ display: inline-block; width: 18px; height: 18px; vertical-align: -4px; margin-right: var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-sm); }}
.tok td:first-child {{ white-space: nowrap; }}
.comp {{ margin-bottom: var(--space-8); }}
.comp h3 {{ margin-top: 0; }}
.preview {{ display: block; width: 100%; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--bg-panel); }}
.cover {{ width: 100%; aspect-ratio: 3 / 1; overflow: hidden; border-radius: var(--radius-lg); margin-bottom: var(--space-7); }}
.cover-frame {{ width: 960px; height: 320px; border: 0; transform-origin: 0 0; pointer-events: none; }}
.pwrap {{ overflow-x: auto; }}
.otp {{ display: none; }}
@media (max-width: 759.98px) {{
  header.top {{ padding: var(--space-2) var(--space-4); }}
  .layout {{ grid-template-columns: minmax(0, 1fr); gap: var(--space-5); padding: var(--space-5) var(--space-4) var(--space-8); }}
  .toc {{ display: none; }}
  html {{ scroll-padding-top: 60px; }}
  .otp {{ display: block; position: sticky; top: 0; z-index: 3; background: var(--bg-panel); border-bottom: 1px solid var(--border); }}
  .otp summary {{ display: flex; align-items: center; gap: var(--space-4); min-height: var(--control-touch); padding: 0 var(--space-5); cursor: pointer; list-style: none; font: 600 16px/1.2 var(--font-display); }}
  .otp summary::-webkit-details-marker {{ display: none; }}
  .otp summary::after {{ content: "▾"; margin-left: auto; color: var(--ink-muted); }}
  .otp nav {{ position: absolute; left: 0; right: 0; top: 100%; max-height: 65dvh; overflow: auto; display: flex; flex-direction: column; background: var(--bg-panel); border-bottom: 1px solid var(--border); box-shadow: var(--shadow-float); }}
  .otp nav a {{ display: flex; align-items: center; min-height: var(--control-touch); padding: 0 var(--space-5); color: var(--ink); text-decoration: none; }}
  .tok {{ display: block; overflow-x: auto; }}
  .preview {{ min-width: 600px; }}   /* a desktop component scrolls sideways in its own frame rather than squashing */
  #c-needscomputer .preview {{ min-width: 0; }}
  .cover {{ display: none; }}
}}
</style>
</head>
<body>
<header class="top"><a class="name" href="/help">JZP Font Builder</a><span class="spacer"></span><a href="/help">Help</a><a href="{URL}">Design system</a></header>
<details class="otp"><summary>Contents</summary><nav aria-label="Contents">{toc}</nav></details>
<div class="layout">
  <nav class="toc" aria-label="Contents"><p class="toc-title">Contents</p>{toc}</nav>
  <main>
    {cover}
    <h1>Design guide</h1>
    <p class="lede">How the JZP Font Builder looks and behaves, on a computer and on a phone: the principles, the rules for each part of the screen, the tokens and the components. A snapshot of the design system from {today}.</p>
    {''.join(s for _, _, s in sections)}
  </main>
</div>
<script>
  // the cover keeps its drawing whole at any width
  const fit = () => document.querySelectorAll('.cover').forEach((c) => (c.querySelector('iframe').style.transform = `scale(${{c.clientWidth / 960}})`));
  fit(); addEventListener('resize', fit);
  // a phone: picking a section from the contents line closes it
  document.querySelectorAll('.otp nav a').forEach((a) => a.addEventListener('click', () => (document.querySelector('.otp').open = false)));
</script>
</body>
</html>
'''
OUT.write_text(page)
print('wrote', OUT, len(page), 'bytes')
