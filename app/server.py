"""Local web server for the demo: the existing analyst package behind a small JSON + streaming API.

Run:  ./demo.sh app      (or: .venv/bin/python server.py)   then open http://localhost:8501 (the cover; the app is at /demo/)
"""
import json
import os
import queue
import threading

import pandas as pd
import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

import api_docs as D
import blog
from analyst import agent, briefing, cases, competitors, data, evals, story, tools as T

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
NOTEBOOK = os.path.join(os.path.dirname(HERE), "notebooks", "capstone2_business_analyst_adventureworks.ipynb")   # its first SYSTEM_PROMPT cell is the starting rulebook

app = FastAPI(title="Business Performance Analyst Agent", version=D.VERSION, description=D.DESCRIPTION,
              openapi_tags=D.TAGS)   # the API reference: /redoc or /docs while the app runs
app.mount("/static", StaticFiles(directory=WEB), name="static")
# the same paths as the website: the cover at /, the app at /demo/, and the pages around it
SITE_MEDIA = os.path.join(os.path.dirname(HERE), "site", "media")   # the pitch video lives with the website
for _name in ("home", "pitch", "deck", "fonts"):
    app.mount(f"/{_name}", StaticFiles(directory=os.path.join(WEB, _name), html=True), name=_name)
if os.path.isdir(SITE_MEDIA):
    app.mount("/media", StaticFiles(directory=SITE_MEDIA), name="media")
_openapi = app.openapi
app.openapi = lambda: D.tidy(_openapi())   # streaming endpoints document only their event stream
HISTORY = []               # follow-up memory for the presenter's conversation (one presenter, one machine)
LOCK = threading.Lock()    # one run at a time: the tools keep shared result ids


def _clean(obj):
    return json.loads(json.dumps(obj, default=lambda o: None if pd.isna(o) else str(o)))


def _step_event(i, name, args, result):
    r = result if isinstance(result, dict) else {}
    summary = agent.describe_step(name, args, result)[:400]
    if name == "run_sql" and "result_id" in r:
        summary = f"{r['row_count']} row{'s' if r['row_count'] != 1 else ''} back, saved as {r['result_id']}"
    return {"type": "step", "n": i, "tool": name, "args": _clean(args),
            "summary": summary, "error": r.get("error"),
            "body": args.get("query") or args.get("code") or r.get("query") or "",
            "lang": "python" if "code" in args else "sql"}


class Cancelled(Exception):
    pass


ACTIVE = {"cancel": None, "what": ""}   # the run holding LOCK, so a new run can stop an abandoned one


def _stream(job, what="a run"):
    """Run job(emit) in a thread and stream every emitted event as Server-Sent Events.

    One run at a time (LOCK). A new run cancels the previous one, and a run stops at its next step
    when the browser goes away, so a run left behind on another screen can't block the next.
    """
    q = queue.Queue()
    cancel = threading.Event()

    def emit(event):
        if cancel.is_set():
            raise Cancelled()
        q.put(event)

    def worker():
        if not LOCK.acquire(blocking=False):
            q.put({"type": "wait", "message": f"Stopping the previous run ({ACTIVE['what']}) first…"})
            if ACTIVE["cancel"]:
                ACTIVE["cancel"].set()
            LOCK.acquire()
        ACTIVE.update(cancel=cancel, what=what)
        try:
            if not cancel.is_set():
                job(emit)
        except Cancelled:
            pass
        except Exception as exc:
            q.put({"type": "error", "message": str(exc)})
        finally:
            ACTIVE.update(cancel=None, what="")
            LOCK.release()
            q.put(None)

    if ACTIVE["cancel"]:
        ACTIVE["cancel"].set()      # single presenter: the newest request wins
    threading.Thread(target=worker, daemon=True).start()

    def gen():
        try:
            while True:
                try:
                    ev = q.get(timeout=2)
                except queue.Empty:
                    yield ": still working\n\n"   # keep-alive; also how we notice a closed browser tab
                    continue
                if ev is None:
                    break
                yield f"data: {json.dumps(_clean(ev))}\n\n"
        finally:
            cancel.set()
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _think_event(emit):
    return lambda n, model: emit({"type": "think", "n": n, "model": model})


def _result_payload(res):
    return {"answer": res["answer"], "queries": res.get("queries", []),
            "charts": [{"id": c["chart_id"], "caption": c["caption"], "png": c["png_base64"]} for c in res.get("charts", [])],
            "tokens": res.get("tokens", 0), "seconds": res.get("seconds", 0), "mode": res.get("mode"),
            "model": res.get("model", ""), "recorded_at": res.get("recorded_at"), "steps": len(res.get("trace", []))}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def cover(request: Request):
    if request.url.query:   # old links (/?page=…, /?presenter=1) go to the app
        return RedirectResponse(f"/demo/?{request.url.query}")
    html = open(os.path.join(WEB, "cover", "index.html"), encoding="utf-8").read()
    return HTMLResponse(html.replace('="../', '="/'))


@app.get("/demo", include_in_schema=False)
def demo_root(request: Request):
    return RedirectResponse("/demo/" + (f"?{request.url.query}" if request.url.query else ""))


@app.get("/demo/", response_class=HTMLResponse, include_in_schema=False)
def index():
    return FileResponse(os.path.join(WEB, "index.html"))


@app.get("/api/", include_in_schema=False)
def api_reference():
    return RedirectResponse("/redoc")


# ---- the blog: docs/*.md rendered live in the app's style (the public website has the same pages in site/blog/) ----
@app.get("/blog", include_in_schema=False)
def blog_root():
    return RedirectResponse("/blog/")


@app.get("/blog/search.json", include_in_schema=False)
def blog_search():
    return Response(blog.search_index(), media_type="application/json")


@app.get("/blog/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/blog/{name}.html", response_class=HTMLResponse, include_in_schema=False)
def blog_page(name: str = "index"):
    if name not in blog.pages():
        return HTMLResponse("<p>No such page. <a href='/blog/'>Back to the blog</a></p>", status_code=404)
    return HTMLResponse(blog.render(name, blog.LOCAL_LINKS))


@app.get("/api/meta", tags=["App"], summary="Everything the screens need to start")
def meta():
    """Data range, demo tracks (and whether each has a recording), weeks for the briefing, AI services in
    order, the agent's tools, the follow-up memory and the competitor-price status."""
    recorded = {c["id"]: bool(cases.load_recording(cases.case_key(c))) for c in cases.CASES}
    tracks = [{k: c.get(k) for k in ("id", "side", "budget", "title", "question", "point", "judging", "db", "page", "competitors")}
              for c in cases.CASES + cases.EXTRA_TRACKS]
    for t in tracks:
        t["recorded"] = recorded.get(t["id"], False)
    with data.connect() as con:
        weeks = [w for (w,) in con.execute("SELECT DISTINCT week_start FROM sales_lines ORDER BY 1 DESC")]
    latest = briefing.latest_full_week()
    return {"data_from": data.AW_START, "data_to": data.AW_END, "orders": 31465,
            "model": agent.current()["model"], "ai_host": agent.current()["name"],
            "providers": [f"{p['name']} · {p['model']}" for p in agent.PROVIDERS],
            "ai_ready": agent.llm_ready(), "any_recordings": any(recorded.values()),
            "tracks": tracks, "weeks": [w for w in weeks if w <= latest], "latest_week": latest,
            "periods": T.AW_PERIODS, "tools": [t["function"]["name"] for t in T.AW_TOOL_SCHEMAS],
            "briefing_recorded": [w for w in weeks if w <= latest and os.path.exists(cases._rec_path(f"briefing:{w}"))],
            "history": [h["question"] for h in HISTORY[-2:]], "competitors": competitors.status()}


@app.get("/api/changes", tags=["App"], summary="The agent's rulebook before and after, and its tool cards")
def changes():
    """The starting notebook's system prompt, today's, and each tool's description exactly as the AI reads it."""
    old = ""
    if os.path.exists(NOTEBOOK):
        cells = json.load(open(NOTEBOOK, encoding="utf-8"))["cells"]
        old = next(("".join(c["source"]) for c in cells if "".join(c["source"]).startswith("SYSTEM_PROMPT = f")), "")
    return {"old_prompt": old, "new_prompt": agent.SYSTEM_PROMPT,
            "tools": [{"name": t["function"]["name"], "description": t["function"]["description"]} for t in T.AW_TOOL_SCHEMAS]}


@app.get("/api/run", tags=["Agent runs"], summary="Ask the agent a question (streamed)", responses=D.SSE)
def run(mode: str = Query("dry", **D.MODE),
        case: str = Query("", description="A demo track's id (from `/api/meta` `tracks`), e.g. `northwest_margin`. "
                                          "Takes priority over `question`."),
        question: str = Query("", description="Your own question, in plain English. `live` mode only, unless it "
                                              "matches a demo track.", examples=["What were total sales by territory last year?"]),
        delay: float = Query(0.0, **D.DELAY)):
    """The agent plans, runs read-only tools, and answers. `done.result` holds `answer`, `queries` (the exact
    SQL or code, from the tool log), `charts` (PNG, base64), `tokens`, `seconds` and `model`. Follow-up
    questions remember the last answers until `POST /api/new-chat`."""
    c = cases.CASE_BY_ID.get(case)
    q = c["question"] if c else question.strip()

    def job(emit):
        emit({"type": "start", "question": q, "mode": mode, "case": case, "planted": bool(c and c.get("db") == "planted")})
        hist = list(HISTORY)
        if c and c.get("follow_up_of") and not hist:
            parent = cases.load_recording(cases.case_key(cases.CASE_BY_ID[c["follow_up_of"]]))
            hist = [parent] if parent else []
        res = cases.answer(q, mode, case=c, history=hist, step_delay=delay,
                           on_step=lambda *a: emit(_step_event(*a)), on_think=_think_event(emit),
                           on_wait=lambda m: emit({"type": "wait", "message": m}))
        HISTORY.append({"question": q, "answer": res["answer"], "queries": res.get("queries", [])})
        del HISTORY[:-4]
        emit({"type": "done", "result": _result_payload(res)})
    return _stream(job, what=f"“{q[:50]}”")


@app.post("/api/new-chat", tags=["Agent runs"], summary="Forget earlier questions")
def new_chat():
    """Clears the follow-up memory, so the next question starts a new conversation."""
    HISTORY.clear()
    return {"ok": True}


def _kpi_rows(kpis):
    return [{"label": k["label"], "now": briefing._aw_fmt(k["metric"], k["now"]),
             "last": briefing._aw_fmt(k["metric"], k["last"]), "vs_last": k["vs_last"],
             "avg4": briefing._aw_fmt(k["metric"], k["avg4"]), "vs_avg4": k["vs_avg4"]} for k in kpis]


@app.get("/api/briefing", tags=["Agent runs"], summary="Write the weekly leadership briefing (streamed)", responses=D.SSE)
def run_briefing(mode: str = Query("dry", **D.MODE),
                 week: str = Query("", description="Monday the week starts, `YYYY-MM-DD` (from `/api/meta` `weeks`). "
                                                   "Default: the latest full week.", examples=["2025-06-23"]),
                 delay: float = Query(0.0, **D.DELAY)):
    """A `kpis` event comes first: the KPI table straight from SQL, final before the AI starts. `done.result`
    holds `headline` and the sections in `parts`, `kpis`, `charts`, `queries`, and `html`: the whole page,
    ready to save or email."""
    def job(emit):
        emit({"type": "start", "mode": mode, "week": week or briefing.latest_full_week()})
        b = briefing.build(week or None, mode=mode, step_delay=delay, on_step=lambda *a: emit(_step_event(*a)),
                           on_kpis=lambda kpis, sql: emit({"type": "kpis", "kpis": _kpi_rows(kpis), "query": sql}),
                           on_think=_think_event(emit), on_wait=lambda m: emit({"type": "wait", "message": m}))
        parts = briefing._parse_briefing(b["answer"])
        emit({"type": "done", "result": {"week": b["week"], "parts": parts, "kpis": _kpi_rows(b["kpis"]), "queries": b["queries"],
                                         "charts": [{"id": c["chart_id"], "caption": c["caption"], "png": c["png_base64"]}
                                                    for c in b["charts"]], "html": b["html"], "mode": mode,
                                         "tokens": b.get("tokens", 0), "seconds": b.get("seconds", 0), "model": b.get("model", ""),
                                         "steps": len(b.get("trace", []))}})
    return _stream(job, what="the weekly briefing")


@app.get("/api/scorecard", tags=["Agent runs"], summary="Mark the agent's answers (streamed)", responses=D.SSE)
def scorecard(mode: str = Query("dry", **D.MODE)):
    """Asks the brief's four questions and three guardrail traps, and streams one `result` event per question,
    marked against answers worked out from the database."""
    key = evals.build_aw_eval_set()

    def job(emit):
        emit({"type": "start", "mode": mode, "total": int((~key["skip"]).sum())})
        evals.run_scorecard(lambda q: cases.answer(q, mode, on_think=_think_event(emit), competitors=None),
                            on_result=lambda rec: emit({"type": "result", "row": rec}),
                            pause_seconds=3 if mode == "live" else 0)
        emit({"type": "done"})
    return _stream(job, what="the scorecard")


@app.get("/api/scorecard/key", tags=["Agent runs"], summary="The scorecard's questions and what each answer needs")
def scorecard_key():
    key = evals.build_aw_eval_set()
    return [{"qid": r.qid, "category": r.category, "question": r.question, "needs": r.why} for r in key.itertuples()]


@app.post("/api/story", tags=["Ask chat"], summary="Ask the course chat (local)", openapi_extra=D.ASK_BODY,
          responses=D.ASK_ANSWER)
async def story_chat(request: Request):
    """Answers only from the brief, the build guide and the history (docs/), plus the passages that best match the
    question from the course's training guide and starting notebook and our notebook, cited as [1], [2]. Uses the
    AI service in `.env`. Errors come back as `{"error": "..."}`."""
    body = await request.json()
    return JSONResponse(await run_in_threadpool(story.answer, body.get("question", ""), body.get("history", [])))


@app.post("/api/story/stream", tags=["Ask chat"], summary="Ask the course chat, streamed (local)", openapi_extra=D.ASK_BODY,
          responses={200: {"description": "Server-Sent Events: `status` events (searching, then the passages found), `delta` events with each piece of the answer as it's written, "
                                          "then `done` with the whole `answer`, its `sources` and the `model` (or `error`).",
                           "content": {"text/event-stream": {"example": 'data: {"type": "delta", "text": "The training guide"}\n\n'
                                                                       'data: {"type": "done", "answer": "...", "sources": [], "model": "openai · gpt-5.4-mini"}\n\n'}}}})
async def story_chat_stream(request: Request):
    """Same as `POST /api/story`, but the answer arrives word by word."""
    body = await request.json()

    def gen():
        for ev in story.stream_answer(body.get("question", ""), body.get("history", [])):
            yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/anomalies", tags=["Tools (no AI)"], summary="Scan for values off their own recent trend")
def anomalies(metric: str = Query("revenue", description="What to scan.",
                                  json_schema_extra={"enum": ["revenue", "margin", "cost", "margin_pct", "units", "orders", "avg_discount_pct"]}),
              by: str = Query("channel", description="Split by.",
                              json_schema_extra={"enum": ["total", "channel", "territory", "category", "country", "territory_group", "subcategory"]}),
              grain: str = Query("month", description="Compare months or weeks.", json_schema_extra={"enum": ["month", "week"]}),
              period: str = Query("", description="`YYYY-Qn`, `YYYY-MM`, `YYYY` or `all`. Default: the latest quarter.",
                                  examples=["2025-Q2"])):
    """The `detect_anomalies` tool. Returns a plain-English `summary`, the unusual `runs` (segment, periods, value,
    expected value, z-score) and the `query` it ran. Bad arguments come back as `{"error", "available"}`."""
    return JSONResponse(_clean(T.detect_anomalies(metric, by=by, grain=grain, period=period or T.AW_PERIODS["latest_quarter"])))


@app.post("/api/sql", tags=["Tools (no AI)"], summary="Run one read-only SELECT",
          openapi_extra=D.json_body({"query": "SELECT channel, ROUND(SUM(revenue)) AS revenue FROM sales_lines GROUP BY channel"},
                                    "`query`: one SELECT (or WITH … SELECT) on the `sales_lines` view or the raw tables."))
async def sql(request: Request):
    """The `run_sql` tool: `columns`, `rows`, `row_count` and a `result_id` the agent can chart. Anything that
    changes data is refused: try `DELETE FROM SalesOrderHeader` to see the `error`."""
    body = await request.json()
    r = T.run_sql(body.get("query", ""))
    if "result_id" in r:
        r["summary"] = f"{r['row_count']} row{'s' if r['row_count'] != 1 else ''}, saved as {r['result_id']}"
    return JSONResponse(_clean(r))


# ---- competitor prices: optional, for demos (mock list or your own CSV) ----
def _busy():
    return JSONResponse({"error": "A run is in progress. Try again when it has finished."}, status_code=409)


@app.get("/api/competitors", tags=["Competitor prices"], summary="Which competitor list is attached")
def competitors_status():
    return competitors.status()


@app.get("/api/competitors/template.csv", tags=["Competitor prices"], summary="Download a CSV template")
def competitors_template():
    return PlainTextResponse(competitors.template_csv(), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="competitor_prices_template.csv"'})


@app.post("/api/competitors/use", tags=["Competitor prices"], summary="Attach the mock list, your upload, or none",
          openapi_extra=D.json_body({"source": "mock"}, "`source`: `mock`, `uploaded` or `null` (none)."))
async def competitors_use(request: Request):
    """{"source": "mock" | "uploaded" | null}: which list your own questions can see."""
    source = (await request.json()).get("source")
    if source not in (None, "mock", "uploaded"):
        return JSONResponse({"error": "source must be mock, uploaded or null."}, status_code=400)
    if not LOCK.acquire(blocking=False):   # never switch lists under a running answer
        return _busy()
    try:
        if source == "mock":
            competitors.build_mock()
        data.select_competitors(source)
    except LookupError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        LOCK.release()
    return competitors.status()


@app.post("/api/competitors/upload", tags=["Competitor prices"], summary="Upload your own competitor price list",
          openapi_extra={"requestBody": {"required": True, "description": "The CSV file as the raw body; its name in `X-Filename`. "
                                         "Columns: product, competitor, competitor_price, observed_date (optional).",
                                         "content": {"text/csv": {"schema": {"type": "string"},
                                                                  "example": "product,competitor,competitor_price,observed_date\nRoad-150 Red, 62,Velo Direct,3299.00,2025-06-01"}}}})
async def competitors_upload(request: Request):
    """The CSV file as the raw request body; its name in the X-Filename header."""
    raw = await request.body()
    if not LOCK.acquire(blocking=False):
        return _busy()
    try:
        res = competitors.import_csv(raw, request.headers.get("x-filename") or "competitor_prices.csv")
        if "error" in res:
            return JSONResponse(res, status_code=400)
        data.select_competitors("uploaded")
    finally:
        LOCK.release()
    return competitors.status()


# last, so it never shadows a named route
@app.get("/{name}", include_in_schema=False)
def shared_file(name: str):   # landing.css, the logos, team.json: the files the pages share at the root
    if name not in ("landing.css", "blog.css", "favicon.svg", "logo.svg", "sensiwise.svg", "essex.svg", "team.json"):
        return Response(status_code=404)
    return FileResponse(os.path.join(WEB, name))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 8501)), log_level="warning")
