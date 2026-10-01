"""Local web server for the demo: the existing analyst package behind a small JSON + streaming API.

Run:  ./demo.sh app      (or: .venv/bin/python server.py)   then open http://localhost:8501
"""
import json
import os
import queue
import threading

import pandas as pd
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from analyst import agent, briefing, cases, data, evals, story, tools as T

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
NOTEBOOK = os.path.join(os.path.dirname(HERE), "notebooks", "capstone2_business_analyst_adventureworks.ipynb")   # its first SYSTEM_PROMPT cell is the starting rulebook

app = FastAPI(title="Business Performance Analyst Agent")
app.mount("/static", StaticFiles(directory=WEB), name="static")
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


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join(WEB, "index.html"))


@app.get("/api/meta")
def meta():
    recorded = {c["id"]: bool(cases.load_recording(cases.case_key(c))) for c in cases.CASES}
    tracks = [{k: c.get(k) for k in ("id", "side", "budget", "title", "question", "point", "judging", "db", "page")}
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
            "history": [h["question"] for h in HISTORY[-2:]]}


@app.get("/api/changes")
def changes():
    old = ""
    if os.path.exists(NOTEBOOK):
        cells = json.load(open(NOTEBOOK, encoding="utf-8"))["cells"]
        old = next(("".join(c["source"]) for c in cells if "".join(c["source"]).startswith("SYSTEM_PROMPT = f")), "")
    return {"old_prompt": old, "new_prompt": agent.SYSTEM_PROMPT,
            "tools": [{"name": t["function"]["name"], "description": t["function"]["description"]} for t in T.AW_TOOL_SCHEMAS]}


@app.get("/api/run")
def run(mode: str = "dry", case: str = "", question: str = "", delay: float = 0.0):
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


@app.post("/api/new-chat")
def new_chat():
    HISTORY.clear()
    return {"ok": True}


def _kpi_rows(kpis):
    return [{"label": k["label"], "now": briefing._aw_fmt(k["metric"], k["now"]),
             "last": briefing._aw_fmt(k["metric"], k["last"]), "vs_last": k["vs_last"],
             "avg4": briefing._aw_fmt(k["metric"], k["avg4"]), "vs_avg4": k["vs_avg4"]} for k in kpis]


@app.get("/api/briefing")
def run_briefing(mode: str = "dry", week: str = "", delay: float = 0.0):
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


@app.get("/api/scorecard")
def scorecard(mode: str = "dry"):
    key = evals.build_aw_eval_set()

    def job(emit):
        emit({"type": "start", "mode": mode, "total": int((~key["skip"]).sum())})
        evals.run_scorecard(lambda q: cases.answer(q, mode, on_think=_think_event(emit)), on_result=lambda rec: emit({"type": "result", "row": rec}),
                            pause_seconds=3 if mode == "live" else 0)
        emit({"type": "done"})
    return _stream(job, what="the scorecard")


@app.get("/api/scorecard/key")
def scorecard_key():
    key = evals.build_aw_eval_set()
    return [{"qid": r.qid, "category": r.category, "question": r.question, "needs": r.why} for r in key.itertuples()]


@app.post("/api/story")
async def story_chat(request: Request):
    """The Story chat: questions about how the project was built, answered from docs/history.md."""
    body = await request.json()
    return JSONResponse(await run_in_threadpool(story.answer, body.get("question", ""), body.get("history", [])))


@app.get("/api/anomalies")
def anomalies(metric: str = "revenue", by: str = "channel", grain: str = "month", period: str = ""):
    return JSONResponse(_clean(T.detect_anomalies(metric, by=by, grain=grain, period=period or T.AW_PERIODS["latest_quarter"])))


@app.post("/api/sql")
async def sql(request: Request):
    body = await request.json()
    r = T.run_sql(body.get("query", ""))
    if "result_id" in r:
        r["summary"] = f"{r['row_count']} row{'s' if r['row_count'] != 1 else ''}, saved as {r['result_id']}"
    return JSONResponse(_clean(r))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 8501)), log_level="warning")
