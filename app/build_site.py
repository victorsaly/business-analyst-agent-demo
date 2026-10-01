"""Build the online copy into ../site/ (published to GitHub Pages by .github/workflows/pages.yml): the same screens, playing back recorded live runs.

No server online, so every answer the page needs is exported here as a JSON file, produced by the very
same API code the local app uses (in Replay mode). Live AI, dry runs and your own questions stay local.

    .venv/bin/python build_site.py        (or ./demo.sh site)

Re-run after recording new live runs, then commit and push site/. site/media/ (the pitch video) is kept.
"""
import json
import os
import shutil

import server
from analyst import briefing, cases, tools as T

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "site")
DATA = os.path.join(OUT, "data")


def collect(job, what=""):
    """Stand-in for server._stream: run the job and keep its events instead of streaming them."""
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


def main():
    server._stream = collect
    os.makedirs(OUT, exist_ok=True)
    for item in os.listdir(OUT):          # start clean, but keep site/media (the pitch video)
        if item != "media":
            path = os.path.join(OUT, item)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    # the screens: same files, asset paths made relative, flagged as the online copy
    shutil.copytree(os.path.join(HERE, "web"), OUT, ignore=shutil.ignore_patterns("promo.html", ".DS_Store"), dirs_exist_ok=True)
    html = open(os.path.join(OUT, "index.html"), encoding="utf-8").read()
    html = html.replace('href="/static/', 'href="').replace('src="/static/', 'src="')
    html = html.replace('<script src="app.js"></script>', '<script>window.STATIC_SITE = true;</script>\n<script src="app.js"></script>')
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
    open(os.path.join(OUT, ".nojekyll"), "w").close()

    # recorded runs, one file per track
    exported = []
    for c in cases.CASES:
        server.HISTORY.clear()
        events = server.run(mode="replay", case=c["id"])
        if finished(events):
            write(f"run/{c['id']}.json", events)
            exported.append(c["id"])
    print(f"tracks: {len(exported)} of {len(cases.CASES)} exported ({', '.join(sorted(set(c['id'] for c in cases.CASES) - set(exported))) or 'all'} missing)")

    # weekly briefings that have a recording
    meta = server.meta()
    weeks = []
    for w in meta["briefing_recorded"]:
        events = server.run_briefing(mode="replay", week=w)
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
    for metric in ("revenue", "margin", "margin_pct", "units", "orders", "avg_discount_pct"):
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
