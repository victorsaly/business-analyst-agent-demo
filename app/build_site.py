"""Build the website into ../site/ (published to GitHub Pages by .github/workflows/pages.yml).

    site/            the cover (web/cover/): one screen, the pitch video, links to the demo and home/
    site/demo/       the demo app: the same screens, playing back recorded live runs
    site/blog/       docs/*.md as pages ("How this was made" first)
    site/api/        the API reference (Redoc), from the server's OpenAPI spec plus the online chat's endpoints
    site/pitch/, site/deck/, site/home/, site/media/   the pitch video, the presentation, the landing page with every service on it

No server online, so every answer the demo needs is exported as a JSON file, produced by the very same API
code the local app uses (in Replay mode). Live AI, dry runs and your own questions stay local; the Ask chat
works online through its Cloudflare Worker.

    .venv/bin/python build_site.py        (or ./demo.sh site)

Re-run after recording new live runs, then commit and push site/. site/media/ (the pitch video) is kept.
"""
import json
import os
import shutil

import api_docs
import blog
import server
from analyst import briefing, cases, tools as T

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "site")
DEMO = os.path.join(OUT, "demo")
DATA = os.path.join(DEMO, "data")
DEMO_FILES = ["index.html", "app.js", "app.css", "explain", "story", "fonts", "favicon.svg", "logo.svg"]   # the app's own files
NOT_AT_ROOT = {"index.html", "app.js", "app.css", "explain", "story", "promo.html", ".DS_Store"}


def collect(job, what=""):
    """Stand-in for server._stream: run the job and keep its events instead of streaming them.
    (The endpoints are called as plain functions here, so pass every argument: their defaults are FastAPI Query objects.)"""
    events = []
    try:
        job(events.append)
    except Exception as exc:          # e.g. no recording for this case: left out of the online copy
        events.append({"type": "error", "message": str(exc)})
    return [server._clean(e) for e in events]


def body(resp):
    return json.loads(resp.body) if hasattr(resp, "body") else server._clean(resp)


def write(rel, obj):
    path = os.path.join(DATA, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"))


def finished(events):
    return bool(events) and events[-1].get("type") == "done"


def build_blog():
    """Every docs/*.md as a page in site/blog/ (blog.py renders them), docs/index.md as the front page."""
    out = os.path.join(OUT, "blog")
    os.makedirs(out, exist_ok=True)
    names = blog.pages()
    for name in names:
        with open(os.path.join(out, f"{name}.html"), "w", encoding="utf-8") as f:
            f.write(blog.render(name, blog.SITE_LINKS))
    with open(os.path.join(out, "search.json"), "w", encoding="utf-8") as f:
        f.write(blog.search_index())
    print(f"blog: {len(names)} pages from docs/, plus the search index")


def build_api():
    """site/api/: the OpenAPI spec (the local server's, plus the online chat's endpoints) shown with Redoc."""
    spec = server.app.openapi()
    spec["servers"] = [{"url": "http://localhost:8501", "description": "The demo app on your machine (./demo.sh app)"}]
    spec["paths"].update(api_docs.WORKER_PATHS)
    out = os.path.join(OUT, "api")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "openapi.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1)
    theme = {"colors": {"primary": {"main": "#1e3a8a"}, "success": {"main": "#2e7d32"}, "error": {"main": "#b71c1c"},
                        "text": {"primary": "#1d2433", "secondary": "#3f5a9e"}},
             "typography": {"fontSize": "15px", "lineHeight": "1.6", "fontFamily": "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
                            "headings": {"fontFamily": "'Patrick Hand SC', 'Marker Felt', cursive", "fontWeight": "400"},
                            "code": {"fontFamily": "'Courier Prime', 'Courier New', monospace"}},
             "sidebar": {"backgroundColor": "#fcfbf7", "textColor": "#1e3a8a", "activeTextColor": "#b71c1c"},
             "rightPanel": {"backgroundColor": "#1e2a4f"}}
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>API reference · Business Performance Analyst Agent</title>
<meta name="description" content="API reference for the Business Performance Analyst Agent demo (a course demonstration): every endpoint, with examples.">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<style>
@font-face {{ font-family: "Patrick Hand SC"; src: url("../fonts/PatrickHandSC-Regular.ttf") format("truetype"); font-display: swap; }}
@font-face {{ font-family: "Courier Prime"; src: url("../fonts/CourierPrime-Regular.ttf") format("truetype"); font-display: swap; }}
body {{ margin: 0; background: #fcfbf7; }}
.top {{ border-bottom: 2px solid #1e3a8a; background: #fcfbf7; font-family: "Patrick Hand SC", cursive; }}
.top .stripe {{ height: 4px; background: repeating-linear-gradient(to bottom, #c62828 0 1px, transparent 1px 2px); }}
.top .in {{ padding: 0.5rem 16px; display: flex; align-items: center; gap: 0.5rem 1rem; flex-wrap: wrap; }}
.top a {{ color: #1e3a8a; text-decoration: none; }}
.top .brand {{ display: flex; align-items: center; gap: 0.55rem; font-size: 1.25rem; }}
.top nav {{ display: flex; gap: 0.3rem 1.1rem; flex-wrap: wrap; margin-left: auto; font-size: 1.05rem; }}
.top nav a[aria-current="page"] {{ border-bottom: 2px solid #c62828; }}
.top a:focus-visible {{ outline: 2px solid #c62828; outline-offset: 2px; }}
@media (max-width: 700px) {{ .top nav {{ margin-left: 0; }} }}
</style></head>
<body><header class="top"><div class="stripe"></div><div class="in">
<a class="brand" href="../"><img src="../logo.svg" alt="" width="32" height="32"> Business Performance Analyst Agent</a>
<nav aria-label="Site"><a href="./" aria-current="page">API reference</a><a href="openapi.json">openapi.json</a><a href="../blog/">Blog</a><a href="../demo/">Open the demo</a><a href="../">Home</a></nav></div></header>
<div id="redoc"></div>
<script src="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js"></script>
<script>Redoc.init("openapi.json", {{ theme: {json.dumps(theme)}, hideDownloadButton: false, expandResponses: "200",
  pathInMiddlePanel: true, nativeScrollbars: true, sortTagsAlphabetically: false }}, document.getElementById("redoc"));</script>
</body></html>
"""
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"api: {sum(len(v) for v in spec['paths'].values())} endpoints documented")


def main():
    server._stream = collect
    os.makedirs(OUT, exist_ok=True)
    for item in os.listdir(OUT):          # start clean, but keep site/media (the pitch video)
        if item != "media":
            path = os.path.join(OUT, item)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    web = os.path.join(HERE, "web")
    # the root: the landing page and everything shared (fonts, logo, blog and landing styles, pitch, deck)
    for item in os.listdir(web):
        if item not in NOT_AT_ROOT:
            src, dst = os.path.join(web, item), os.path.join(OUT, item)
            shutil.copytree(src, dst, dirs_exist_ok=True) if os.path.isdir(src) else shutil.copy2(src, dst)
    cover = open(os.path.join(web, "cover", "index.html"), encoding="utf-8").read()   # the one-screen cover with the pitch
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(cover.replace('="../', '="'))
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    # the demo app: same files, asset paths made relative, flagged as the online copy
    os.makedirs(DEMO, exist_ok=True)
    for item in DEMO_FILES:
        src, dst = os.path.join(web, item), os.path.join(DEMO, item)
        shutil.copytree(src, dst, dirs_exist_ok=True) if os.path.isdir(src) else shutil.copy2(src, dst)
    html = open(os.path.join(DEMO, "index.html"), encoding="utf-8").read()
    html = html.replace('href="/static/', 'href="').replace('src="/static/', 'src="')
    html = html.replace('<script src="app.js"></script>', '<script>window.STATIC_SITE = true;</script>\n<script src="app.js"></script>')
    open(os.path.join(DEMO, "index.html"), "w", encoding="utf-8").write(html)

    build_blog()
    build_api()

    # recorded runs, one file per track
    exported = []
    for c in cases.CASES:
        server.HISTORY.clear()
        events = server.run(mode="replay", case=c["id"], question="", delay=0.0)
        if finished(events):
            write(f"run/{c['id']}.json", events)
            exported.append(c["id"])
    missing = sorted(set(c["id"] for c in cases.CASES) - set(exported))
    print(f"tracks: {len(exported)} of {len(cases.CASES)} exported" + (f" (no recording: {', '.join(missing)})" if missing else ""))

    # weekly briefings that have a recording
    meta = server.meta()
    weeks = []
    for w in meta["briefing_recorded"]:
        events = server.run_briefing(mode="replay", week=w, delay=0.0)
        if finished(events):
            write(f"briefing/{w}.json", events)
            weeks.append(w)
    print(f"briefings: {weeks or 'none recorded'}")

    # scorecard, marked against the recordings
    events = server.scorecard(mode="replay")
    write("scorecard.json", events)
    rows = [e["row"] for e in events if e["type"] == "result"]
    print(f"scorecard: {sum(r['passed'] for r in rows)} of {len(rows)} passed on the recordings")
    write("scorecard_key.json", server.scorecard_key())
    write("changes.json", server.changes())

    # the Tools screen: every anomaly scan for the default period, and the two SQL buttons
    for metric in ("revenue", "margin", "cost", "margin_pct", "units", "orders", "avg_discount_pct"):
        for by in ("total", "channel", "territory", "category", "country", "territory_group", "subcategory"):
            for grain in ("month", "week"):
                write(f"anomalies/{metric}-{by}-{grain}.json", body(server.anomalies(metric, by, grain, "")))
    default_sql = ("SELECT channel, year, ROUND(SUM(revenue)) AS revenue,\n"
                   "       ROUND(100.0 * SUM(margin) / SUM(revenue), 1) AS margin_pct\n"
                   "FROM sales_lines\nGROUP BY channel, year\nORDER BY year, channel")
    for name, q in (("default", default_sql), ("delete", "DELETE FROM SalesOrderHeader WHERE OrderDate < '2023-01-01'")):
        r = T.run_sql(q)
        if "result_id" in r:
            r["summary"] = f"{r['row_count']} row{'s' if r['row_count'] != 1 else ''}, saved as {r['result_id']}"
        write(f"sql/{name}.json", server._clean(r))

    # meta, adjusted for the online copy
    for t in meta["tracks"]:
        t["recorded"] = t["id"] in exported
    meta.update(ai_ready=False, any_recordings=True, history=[], weeks=weeks,
                latest_week=weeks[0] if weeks else meta["latest_week"])
    write("meta.json", meta)
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs)
    print(f"site/ built: {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
