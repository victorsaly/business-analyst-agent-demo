"""Checks that run without any AI key:  ./demo.sh test

1. Guardrails in the tools (read-only, sandbox).
2. Every demo case in dry-run mode, plus the briefing.
3. The examiner passes good answers and fails bad ones.
4. The LIVE agent loop against a fake AI server on this machine (tool calls, a rate-limit retry,
   the final answer, and the recording that Replay mode plays back).
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ["LLM_BASE_URL"] = "http://127.0.0.1:8765/v1"     # must be set before importing the agent
os.environ["LLM_API_KEY"] = "test"

from analyst import agent, briefing, cases, competitors, data, evals, tools as T  # noqa: E402

failures = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


# 1. guardrails
check("SELECT works", "rows" in T.run_sql("SELECT COUNT(*) AS n FROM sales_lines"))
check("DELETE refused", "error" in T.run_sql("DELETE FROM SalesOrderHeader"))
check("two statements refused", "error" in T.run_sql("SELECT 1; DROP TABLE Product"))
check("bad column gives a hint", "hint" in T.run_sql("SELECT nope FROM sales_lines"))
try:
    with T._aw_connect() as con:
        con.execute("DELETE FROM Product")
    check("database is read-only at file level", False, "delete succeeded")
except Exception:
    check("database is read-only at file level", True)
check("sandbox blocks imports", "error" in T.run_python("import os"))
check("sandbox blocks dunder escapes", "error" in T.run_python("result = ().__class__"))

# 2. dry run of every case + briefing
for c in cases.CASES:
    r = cases.answer(c["question"], "dry", case=c)
    check(f"dry case {c['id']}", bool(r["answer"]) and bool(r["trace"]))
b = briefing.build(mode="dry")
check("dry briefing builds", "<table" in b["html"] and len(b["queries"]) >= 2)

# 2b. competitor prices: off by default, attachable for demos, never seen by the guardrail track
check("no competitor view by default", "error" in T.run_sql("SELECT * FROM price_comparison"))
competitors.build_mock()
data.select_competitors("mock")
try:
    check("mock list is queryable", T.run_sql("SELECT COUNT(*) AS n FROM price_comparison")["rows"][0]["n"] > 100)
    check("prompt drops the competitor guardrail", "competitors or their prices" not in agent.system_prompt())
    check("competitor list refuses writes", "error" in T.run_sql("DELETE FROM competitor_prices"))
    g = cases.answer(cases.CASE_BY_ID["guard_competitors"]["question"], "dry", case=cases.CASE_BY_ID["guard_competitors"])
    check("guardrail track ignores an attached list", "does not include competitors" in g["answer"])
    check("selection restored after a track", data.competitors() == "mock")
    check("bad CSV refused", "error" in competitors.import_csv(b"name,cost\nFoo,1\n"))
    check("CSV with unknown products refused", "error" in competitors.import_csv(b"product,competitor,competitor_price\nNope,A,1\n"))
finally:
    data.select_competitors(None)

# 3. examiner
key = evals.build_aw_eval_set().set_index("qid")
row = key.loc["T1"].copy()
row["qid"] = "T1"
good = {"answer": "In 2024 Southwest led with $9,121,932.", "tool_trace": [{"tool": "run_sql"}]}
bad = {"answer": "Northwest led with $5M.", "tool_trace": []}
check("examiner passes a good answer", evals.score_answer(row, good)[0])
check("examiner fails a bad answer", not evals.score_answer(row, bad)[0])
row = key.loc["X3"].copy()
check("examiner fails a forecast stated as fact",
      not evals.score_answer(row, {"answer": "Revenue will be $5,000,000 next quarter.", "tool_trace": []})[0])

# 4. live loop against a fake OpenAI-compatible server
calls = {"n": 0}


class FakeAI(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        calls["n"] += 1
        if self.headers.get("Authorization") == "Bearer exhausted":   # a provider whose daily allowance is used up
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b'{"error": {"message": "Rate limit reached for tokens per day (TPD). Please try again in 2h."}}')
            return
        if calls.get("strict") and "max_tokens" in body:   # behave like OpenAI's newer models
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": {"message": "Unsupported parameter: \'max_tokens\' is not supported with this model. Use \'max_completion_tokens\' instead."}}')
            return
        if calls["n"] == 1:   # first call: pretend we hit the free-tier limit
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b'{"error": {"message": "Rate limit reached. Please try again in 0.2s."}}')
            return
        has_tool_result = any(m["role"] == "tool" for m in body["messages"])
        if not has_tool_result:
            msg = {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {
                "name": "run_sql", "arguments": json.dumps({"query": "SELECT territory, SUM(revenue) AS revenue "
                                                                     "FROM sales_lines WHERE year = 2024 GROUP BY territory "
                                                                     "ORDER BY revenue DESC"})}}]}
        else:
            msg = {"role": "assistant", "content": "Southwest led in 2024.\n\nChecked with: q1"}
        out = json.dumps({"choices": [{"message": msg}], "usage": {"total_tokens": 123}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)


srv = HTTPServer(("127.0.0.1", 8765), FakeAI)
threading.Thread(target=srv.serve_forever, daemon=True).start()
case = cases.CASE_BY_ID["sales_territory"]
saved = cases.load_recording(cases.case_key(case))      # keep a real recording safe
waits = []
res = cases.answer(case["question"], "live", case=case, on_wait=waits.append)
check("live: retried after a rate limit", bool(waits))
check("live: ran the tool the AI asked for", [t["tool"] for t in res["trace"]] == ["run_sql"])
check("live: shows the query from the tool log", "SELECT territory" in res["queries"][0]["text"])
check("live: final answer", res["answer"].startswith("Southwest"))
rep = cases.answer(case["question"], "replay", case=case)
check("replay plays back the recording", rep["answer"] == res["answer"] and rep["mode"] == "replay")
calls["strict"] = True
res2 = cases.answer(case["question"], "live", case=case)
check("live: adapts to an OpenAI-style provider (max_completion_tokens)", res2["answer"].startswith("Southwest"))
calls["strict"] = False
fake = "http://127.0.0.1:8765/v1"
agent.PROVIDERS[:] = [{"name": "groq", "base": fake, "key": "exhausted", "model": "m1"},
                      {"name": "openai", "base": fake, "key": "ok", "model": "m2"}]
agent._ACTIVE["i"] = 0
notes = []
res3 = cases.answer(case["question"], "live", case=case, on_wait=notes.append)
check("live: falls back to the next AI service when one is out of allowance",
      res3["answer"].startswith("Southwest") and any("switching to openai" in n for n in notes) and "openai" in res3["model"])
if saved:
    cases.save_recording(cases.case_key(case), saved)
else:
    os.remove(cases._rec_path(cases.case_key(case)))
srv.shutdown()

print(f"\n{'ALL CHECKS PASSED' if not failures else str(len(failures)) + ' FAILED: ' + ', '.join(failures)}")
raise SystemExit(1 if failures else 0)
