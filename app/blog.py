"""The blog: every docs/*.md as a page in the app's style (paper, ink, hand-lettered headings, three columns).

Used in two places, with different links:
- server.py serves it live at http://localhost:8501/blog/ (LOCAL links), so an edited doc shows on reload;
- build_site.py writes it into site/blog/ for the public website (SITE links).
docs/index.md ("How this was made") is the front page.
search_index() is the text of every section, for the search box (web/blog.js loads it as blog/search.json).
"""
import html
import json
import os
import re

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
REPO = "https://github.com/victorsaly/business-analyst-agent-demo"
SITE = "https://victorsaly.github.io/business-analyst-agent-demo/"

NAV = [("index", "How this was made"), ("history", "History"), ("requirements", "Requirements"), ("build-guide", "Build guide")]
AREAS = [   # the sidebar on every page: every document, grouped by area
    ("Start here", [("getting-started", "Run it on your laptop (Mac and Windows)")]),
    ("The story", [("index", "How this was made"), ("history", "Timeline, step by step")]),
    ("The brief", [("requirements", "Every requirement, with evidence"), ("build-guide", "The 13 build steps")]),
    ("The app", [("running-the-app", "Running the demo"), ("product", "Who it's for"), ("design", "How it looks")]),
    ("Behind the scenes", [("prompt-optimization", "Cutting the AI cost"), ("audio-sources", "Audio sources")]),
]

# Where the shared files and the other services are, seen from a blog page.
SITE_LINKS = {"assets": "../", "home": "../home/", "demo": "../demo/", "ask": "../demo/?page=story", "api": "../api/",
              "pitch": "../pitch/", "deck": "../deck/"}
LOCAL_LINKS = {"assets": "/static/", "home": "/home/", "demo": "/demo/", "ask": "/demo/?page=story", "api": "/redoc",
               "pitch": "/pitch/", "deck": "/deck/"}


def pages():
    """The docs, by name (without .md). Every one must have a place in AREAS, so none is missing from the sidebar."""
    names = sorted(f[:-3] for f in os.listdir(DOCS) if f.endswith(".md"))
    missing = set(names) - {n for _, items in AREAS for n, _ in items}
    if missing:
        raise SystemExit(f"Add these docs to AREAS in app/blog.py: {sorted(missing)}")
    return names


def gh_slug(text, sep="-"):
    """Heading ids the way GitHub makes them, so the same #links work on GitHub and on the blog."""
    text = re.sub(r"[^\w\- ]", "", html.unescape(re.sub(r"<[^>]+>", "", text)).strip().lower())
    return text.replace(" ", sep)


def link(target):
    """docs/x.md -> x.html; anything else in the repo -> the file on GitHub."""
    if re.match(r"^(https?:|mailto:|#)", target):
        return target
    path, _, anchor = target.partition("#")
    anchor = f"#{anchor}" if anchor else ""
    full = os.path.normpath(os.path.join(DOCS, path))
    if full.startswith(DOCS) and path.endswith(".md"):
        return os.path.splitext(os.path.relpath(full, DOCS))[0] + ".html" + anchor
    rel = os.path.relpath(full, ROOT)
    return f"{REPO}/{'tree' if os.path.isdir(full) else 'blob'}/main/{rel}{anchor}"


def order():
    """Every doc once, in sidebar order: the reading order for the previous / next links."""
    seen = []
    for _, items in AREAS:
        seen += [n for n, _ in items if n not in seen]
    return seen


def nest(text):
    """Make GitHub-style lists render here too. Python-Markdown wants list content indented 4 spaces and has no
    code fences inside list items; GitHub accepts 2 or 3 spaces and fences anywhere. So: inside a list, 1 to 3 spaces
    become 4, and an indented fence becomes a placeholder that unnest() swaps for the finished code block."""
    out, blocks, lines, i, in_list = [], [], text.split("\n"), 0, False
    while i < len(lines):
        line = lines[i]
        fence = re.match(r"^( *)(`{3,}|~{3,})([\w-]*)", line)
        if fence and not fence.group(1):              # a top-level fence: copy it as it is
            out.append(line)
            i += 1
            while i < len(lines) and not lines[i].startswith(fence.group(2)):
                out.append(lines[i])
                i += 1
            out.extend(lines[i:i + 1])
            i += 1
            continue
        if fence:                                     # a fence inside a list item
            pad, mark, lang = fence.groups()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(mark):
                code.append(lines[i][len(pad):] if lines[i].startswith(pad) else lines[i].lstrip())
                i += 1
            i += 1
            cls = f' class="language-{lang}"' if lang else ""
            blocks.append(f'<pre><code{cls}>{html.escape(chr(10).join(code))}\n</code></pre>')
            out += ["", f"    XCODEBLOCK{len(blocks) - 1}X", ""]
            continue
        if line.strip() and not line.startswith(" "):
            in_list = bool(re.match(r"([-*+]|\d+\.) ", line))
        out.append("    " + line.lstrip() if in_list and re.match(r" {1,3}\S", line) else line)
        i += 1
    return "\n".join(out), blocks


def unnest(body, blocks):
    return re.sub(r"(?:<p>)?XCODEBLOCK(\d+)X(?:</p>)?", lambda m: blocks[int(m.group(1))], body)


def convert(name):
    """A doc's Markdown as HTML, plus the parser (its table of contents)."""
    text = open(os.path.join(DOCS, f"{name}.md"), encoding="utf-8").read()
    text = re.sub(r"\]\(([^)\s]+)\)", lambda m: f"]({link(m.group(1))})", text)
    text, blocks = nest(text)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"],
                           extension_configs={"toc": {"slugify": gh_slug}})
    return diagrams(unnest(md.convert(text), blocks)), md


DIAGRAM = re.compile(r'<pre><code class="language-mermaid">(.*?)</code></pre>', re.S)

# Mermaid drawn in the blog's own paper and ink: white boxes with an ink outline, hand-lettered labels,
# and a "red" class for the one thing each diagram is about (a guardrail, the cost, the step people miss).
MERMAID = """<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
mermaid.initialize({ startOnLoad: false, theme: "base", securityLevel: "strict",
  flowchart: { curve: "basis", padding: 14, nodeSpacing: 34, rankSpacing: 40 }, sequence: { mirrorActors: false },
  themeVariables: { fontFamily: '"Patrick Hand SC", "Marker Felt", cursive', fontSize: "17px",
    background: "#fcfbf7", primaryColor: "#ffffff", primaryTextColor: "#1e3a8a", primaryBorderColor: "#1e3a8a",
    secondaryColor: "#eef2fb", tertiaryColor: "#eef2fb", lineColor: "#3f5a9e", textColor: "#1d2433",
    clusterBkg: "#eef2fb", clusterBorder: "#a9b8dc", edgeLabelBackground: "#ffffff",
    noteBkgColor: "#eef2fb", noteBorderColor: "#a9b8dc", noteTextColor: "#1e3a8a", actorLineColor: "#a9b8dc", signalColor: "#3f5a9e",
    cScale0: "#eef2fb", cScale1: "#ffffff", cScale2: "#eef2fb", cScale3: "#ffffff", cScale4: "#eef2fb",
    cScaleLabel0: "#1e3a8a", cScaleLabel1: "#1e3a8a", cScaleLabel2: "#1e3a8a", cScaleLabel3: "#1e3a8a", cScaleLabel4: "#1e3a8a",
    cScalePeer0: "#a9b8dc", cScalePeer1: "#a9b8dc", cScalePeer2: "#a9b8dc", cScalePeer3: "#a9b8dc", cScalePeer4: "#a9b8dc" } });
await document.fonts.ready;   // measure the labels in the hand-lettered font, not the fallback
await mermaid.run({ querySelector: "pre.mermaid" });
</script>"""


def diagrams(body):
    """```mermaid blocks -> <pre class="mermaid"> in a figure; GitHub draws the same blocks natively."""
    return DIAGRAM.sub(lambda m: f'<figure class="diagram"><pre class="mermaid">{m.group(1)}</pre></figure>', body)


def plain(fragment):
    """HTML to searchable text: block tags become spaces, inline tags (code, links, bold) just vanish."""
    text = re.sub(r"</?(p|li|ul|ol|h\d|pre|div|table|tr|td|th|blockquote|br|hr)\b[^>]*>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()


def search_index():
    """One entry per section (h2 or h3) of every doc: page, page title, heading, anchor and text."""
    entries = []
    for name in pages():
        body, _ = convert(name)
        body = re.sub(r'<figure class="diagram">.*?</figure>', "", body, flags=re.S)   # diagram source isn't prose
        title = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
        title = plain(title.group(1)) if title else name
        parts = re.split(r'<h([23]) id="([^"]+)">(.*?)</h\1>', body, flags=re.S)
        entries.append({"p": name, "t": title, "h": title, "id": "", "x": plain(re.sub(r"<h1.*?</h1>", "", parts[0], flags=re.S))[:3000]})
        for i in range(1, len(parts), 4):
            entries.append({"p": name, "t": title, "h": plain(parts[i + 2]), "id": parts[i + 1], "x": plain(parts[i + 3])[:3000]})
    return json.dumps(entries, ensure_ascii=False, separators=(",", ":"))


def render(name, links=SITE_LINKS):
    """One doc as a complete HTML page."""
    body, md = convert(name)
    sections = [t for top in md.toc_tokens for t in top.get("children", [])] or md.toc_tokens[1:]   # the h2s
    on_page = "".join(f'<li><a href="#{t["id"]}">{t["name"]}</a></li>' for t in sections)
    body = body.replace("<table>", '<div class="table"><table>').replace("</table>", "</table></div>")
    title = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    title = re.sub(r"<[^>]+>", "", title.group(1)) if title else name
    L, a = links, links["assets"]
    here = ' aria-current="page"'
    nav = "".join(f'<a href="{n}.html"{here if n == name else ""}>{label}</a>' for n, label in NAV)
    areas = "".join(f"<h2>{area}</h2><ul>" + "".join(f'<li><a href="{n}.html"{here if n == name else ""}>{label}</a></li>'
                                                      for n, label in items) + "</ul>" for area, items in AREAS)
    toc = f'<nav class="toc" aria-label="On this page"><h2>On this page</h2><ul>{on_page}</ul></nav>' if on_page else ""
    labels = {n: label for _, items in AREAS for n, label in items}
    seq = order()
    i = seq.index(name)
    prev = f'<a class="prev" href="{seq[i - 1]}.html"><span>Previous</span>{labels[seq[i - 1]]}</a>' if i > 0 else ""
    nxt = f'<a class="next" href="{seq[i + 1]}.html"><span>Next</span>{labels[seq[i + 1]]}</a>' if i + 1 < len(seq) else ""
    pager = f'<nav class="pager" aria-label="Previous and next page">{prev}{nxt}</nav>'
    search = ('<div class="search" role="search"><label class="sr" for="q">Search the docs</label>'
              '<input id="q" type="search" placeholder="Search the docs" autocomplete="off" spellcheck="false" '
              'aria-controls="hits" aria-expanded="false" aria-autocomplete="list"><kbd aria-hidden="true">/</kbd>'
              '<div id="hits" role="listbox" aria-label="Search results" hidden></div></div>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · Business Performance Analyst Agent</title>
<meta name="description" content="A course demonstration (Agentic AI Workshop 2026, Capstone 2): how we built an AI analyst agent, step by step.">
<link rel="icon" href="{a}favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{a}blog.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js" defer></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/sql.min.js" defer></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/diff.min.js" defer></script>
<script>addEventListener("DOMContentLoaded", () => window.hljs && hljs.highlightAll());</script>{MERMAID if 'class="mermaid"' in body else ""}
<script src="{a}blog.js" defer></script></head>
<body><header class="top"><div class="stripe"></div><div class="in">
<a class="brand" href="index.html"><img src="{a}logo.svg" alt="" width="32" height="32"> Business Performance Analyst Agent</a>
{search}<nav aria-label="Blog">{nav}<a href="{L['demo']}">Open the demo</a><a href="{L['api']}">API</a><a href="{L['home']}">Home</a></nav></div></header>
<div class="wrap"><main><span class="course">Course demonstration · Capstone 2 · Agentic AI Workshop 2026</span>
{body}
{pager}
<p class="foot">A learning project, not a product. AdventureWorks is Microsoft's public sample data about a made-up bicycle
company. Source of this page: <a href="{REPO}/blob/main/docs/{name}.md">docs/{name}.md</a>.</p></main>
<aside class="areas" aria-label="All documents"><details open><summary>All pages</summary>{areas}<h2>Try it</h2><ul><li><a href="{L['home']}">Home: every area</a></li><li><a href="{L['demo']}">Open the demo</a></li><li><a href="{L['ask']}">Ask the course chat</a></li><li><a href="{L['api']}">API reference</a></li><li><a href="{L['pitch']}">60-second pitch video</a></li><li><a href="{L['deck']}">The presentation</a></li><li><a href="getting-started.html">Run it on your laptop</a></li><li><a href="{REPO}">The code on GitHub</a></li></ul></details></aside>
{toc}</div></body></html>
"""
