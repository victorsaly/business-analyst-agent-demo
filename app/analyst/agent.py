"""The agent: rulebook + tool loop, talking to any OpenAI-compatible chat API (Groq by default).

Same design as the notebook (Section 5 loop + Section 6E rulebook + 6F "show the working").
Settings come from environment variables (or app/.env):
  GROQ_API_KEY                 Groq (the default first choice), model LLM_MODEL (default openai/gpt-oss-20b)
  OPENAI_API_KEY               OpenAI, model OPENAI_MODEL (default gpt-5.4-mini). Used as the automatic
                               fallback when Groq runs out (daily limit, credit), or first if LLM_PROVIDER=openai
  LLM_BASE_URL + LLM_API_KEY   any other OpenAI-compatible service, e.g. Ollama at http://localhost:11434/v1
"""
import json
import os
import re
import time

import requests

from . import tools as T
from .data import AW_START, AW_END


def _load_env():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()
def _providers():
    """The AI services to use, in order. If the first runs out, the agent moves to the next."""
    env = os.environ.get
    out = []
    if env("LLM_BASE_URL"):
        out.append({"name": "custom", "base": env("LLM_BASE_URL").rstrip("/"), "key": env("LLM_API_KEY", ""),
                    "model": env("LLM_MODEL", "openai/gpt-oss-20b")})
    if env("GROQ_API_KEY") or (env("LLM_API_KEY") and not env("LLM_BASE_URL")):
        out.append({"name": "groq", "base": "https://api.groq.com/openai/v1",
                    "key": env("GROQ_API_KEY") or env("LLM_API_KEY"), "model": env("LLM_MODEL", "openai/gpt-oss-20b")})
    if env("OPENAI_API_KEY"):
        out.append({"name": "openai", "base": "https://api.openai.com/v1", "key": env("OPENAI_API_KEY"),
                    "model": env("OPENAI_MODEL", "gpt-5.4-mini")})
    first = env("LLM_PROVIDER", "").lower()
    out.sort(key=lambda p: p["name"] != first)   # LLM_PROVIDER=openai puts OpenAI first
    return out


PROVIDERS = _providers()
_ACTIVE = {"i": 0}


def current():
    return PROVIDERS[_ACTIVE["i"]] if PROVIDERS else {"name": "none", "base": "", "key": "", "model": "none"}


BASE_URL = current()["base"]          # kept for older callers; reflects the first provider
MODEL = current()["model"]
API_KEY = current()["key"]
MAX_ITERATIONS = 8
TEMPERATURE = 0.2


def llm_ready():
    p = current()
    return bool(p["key"]) or "localhost" in p["base"] or "127.0.0.1" in p["base"]


SYSTEM_PROMPT = f"""You are a business performance analyst for AdventureWorks, a bicycle company. You answer
managers' questions about its sales data ({AW_START} to {AW_END}) using ONLY the tools provided.

GUARDRAILS (non-negotiable)
1. Every number you state must come from a tool result in this conversation. Never invent, estimate
   or guess a number. If you need a number, call a tool.
2. The database is read-only. Only ever write SELECT queries.
3. If the data cannot answer the question (it has no {', '.join(T.AW_DICTIONARY['not_in_data'][:-1])}),
   say plainly "The data does not include <topic>" and say what data would be needed. Do not
   answer with a different metric instead.
4. Never present a forecast or a guess as a fact. The data only covers the past. If asked about
   the future, show the past trend; if you add any projection, label it "ESTIMATE, not a fact" and
   state the assumption. Only give a reason for a change if a tool result shows it; otherwise
   call it "a possible reason, to be checked".

HOW TO WORK
5. Call get_schema first (once) to see the tables, the data dictionary and the dates.
6. Use run_sql on the sales_lines view. Revenue = SUM(revenue). Margin = SUM(margin)
   (LineTotal - OrderQty x StandardCost). Margin % = 100.0 * SUM(margin) / SUM(revenue): never
   average percentages. Let SQL do the adding up (GROUP BY) so results are small.
7. If a tool returns an error, read it, fix your query or arguments, and try again (up to 3 times).
8. Dates: {T.AW_PERIODS['note']} If a quarter is named without a year, say which year you used.
   "Why did X drop in Q2?" compares Q2 with the quarter before it (Q1 of the same year). With no
   year named, check Q1 to Q2 in every year, answer for the year(s) where it dropped, and say so.
   Call out any period the data only partly covers.
9. "Why did X change?": compare the two periods, then break the change down by channel
   (Online vs Reseller margins are very different), category / subcategory and discount
   (avg_discount_pct) to find what drove it. Use explain_change for volume / price / mix if available.
   When the question names a territory, category or channel, pass it in filters (e.g.
   {{"territory": "Northwest"}}) and check the result's scope before you answer.
10. "Anything unusual?": call detect_anomalies with by="total" and by="channel" first, then by
    territory or category for the period asked, then run_sql to find out why.
11. "Growing fastest?": compare the same complete periods year on year (e.g. 2024 vs 2023) and give
    the % change. Mention when a fast grower starts from a small base.
12. For every answer with numbers by group or over time, make exactly one chart with make_chart
    (pass the run_sql result_id as data) and mention its chart_id.
13. Money is in US dollars ($). Changes in a % metric are in percentage points (pts).

ANSWER FORMAT: a one-sentence headline answer, then 2-4 short bullets with the key numbers, then
one line "Checked with: <the result ids you used>". The exact queries are shown to the reader
automatically under your answer, so do not repeat the SQL.
"""


# ---------------------------------------------------------------- tool switchboard
def run_tool(name, args):
    fn = T.AW_TOOLS.get(name)
    if fn is None:
        return {"error": f"There is no tool called '{name}'.", "available": list(T.AW_TOOLS)}
    clean = {k: v for k, v in (args or {}).items() if v not in (None, "", [], {}) and str(v).lower() not in ("none", "null")}
    aliases = {"make_chart": {"result_id": "data", "type": "chart_type", "kind": "chart_type"},
               "run_python": {"result_id": "data"}, "run_sql": {"sql": "query"}}
    for wrong, right in aliases.get(name, {}).items():   # names the AI often uses instead
        if wrong in clean and right not in clean:
            clean[right] = clean.pop(wrong)
    if isinstance(clean.get("filters"), str):
        try:
            clean["filters"] = json.loads(clean["filters"])
        except Exception:
            clean.pop("filters")
    try:
        result = fn(**clean)
        return result if isinstance(result, dict) else {"result": result}
    except TypeError as exc:
        return {"error": f"Wrong arguments for {name}: {exc}"}
    except Exception as exc:
        return {"error": f"{name} failed: {exc}"}


def compact(name, result, max_chars=2400):
    """A shorter copy of a tool result for the AI (the full result stays in the trace)."""
    if not isinstance(result, dict) or "error" in result:
        return result
    if name == "get_schema":
        return {"periods": result["periods"], "dictionary": result["dictionary"], "raw_tables": result["tables_and_columns"]}
    r = json.loads(json.dumps(result, default=str))
    if len(json.dumps(r)) > max_chars and "rows" in r:
        while len(json.dumps(r)) > max_chars and len(r["rows"]) > 5:
            r["rows"] = r["rows"][: len(r["rows"]) // 2]
        r["note"] = "rows trimmed to save space - ask a narrower question for the rest"
    if len(json.dumps(r)) > max_chars:
        r = {k: r[k] for k in ("summary", "runs", "result_id", "chart_id", "note") if k in r}
        if "runs" in r:
            r["runs"] = r["runs"][:5]
    return r


def queries_used(trace):
    """'Always show the query': taken from the tool log, never from the AI's own words."""
    out = []
    for t in trace or []:
        r, a = t.get("result") or {}, t.get("args") or {}
        err = str(r.get("error", "")) if isinstance(r, dict) else ""
        failed = " (refused: read-only)" if "read-only" in err or "changes data" in err else " (failed)" if err else ""
        if t["tool"] == "run_sql":
            out.append({"label": f"run_sql {r.get('result_id', '')}{failed}", "lang": "sql", "text": a.get("query", "")})
        elif t["tool"] == "run_python":
            out.append({"label": f"run_python {r.get('result_id', '')}{failed}", "lang": "python", "text": a.get("code", "")})
        elif t["tool"] in ("detect_anomalies", "explain_change") and isinstance(r, dict) and r.get("query"):
            args = ", ".join(f"{k}={v!r}" for k, v in a.items())
            out.append({"label": f"{t['tool']}({args})", "lang": "sql", "text": r["query"]})
    return out


def describe_step(name, args, result):
    """One readable line per tool call, for the live trace."""
    if isinstance(result, dict) and "error" in result:
        return f"⚠️ {result['error']}"
    if isinstance(result, dict) and result.get("summary"):
        return str(result["summary"])
    return json.dumps(result, default=str)[:200]


# ---------------------------------------------------------------- talking to the AI
def _estimate_tokens(messages):
    return int(len(json.dumps(messages)) / 3.3)


def _shrink_old_results(messages, budget_tokens=5200):
    """Stay under the free-tier request size by shortening the OLDEST tool results first."""
    for m in messages:
        if _estimate_tokens(messages) <= budget_tokens:
            break
        if m.get("role") == "tool" and len(m["content"]) > 400:
            try:
                short = json.loads(m["content"]).get("summary")
            except Exception:
                short = None
            m["content"] = json.dumps({"summary": short} if short else {"note": "older result trimmed", "start": m["content"][:300]})


class LLMError(Exception):
    pass


def _seconds(text):
    total = 0.0
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)(ms|m|s|h)", text or ""):
        total += float(num) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
    return total


def _adapt_to_provider(body, error_text):
    """Some providers reject settings others accept. Adjust the request once per setting and retry."""
    low = error_text.lower()
    if "max_tokens" in body and "max_completion_tokens" in low:
        body["max_completion_tokens"] = body.pop("max_tokens")
        return True
    for key in ("temperature", "reasoning_effort"):
        if key in body and key in low and ("unsupported" in low or "not support" in low or "invalid" in low):
            body.pop(key)
            return True
    return False


def _out_of_allowance(status, text):
    low = text.lower()
    return (status == 429 and ("per day" in low or "perday" in low or "daily" in low)) or status in (401, 402, 403) \
        or "insufficient_quota" in low or "credit" in low and status >= 400


def _chat(messages, with_tools=True, max_tokens=1500, on_wait=None, usage=None):
    if not llm_ready():
        raise LLMError("No AI key set. Put GROQ_API_KEY=... or OPENAI_API_KEY=... in app/.env (or use Replay / Dry run).")
    while True:
        p = current()
        body = {"model": p["model"], "messages": messages, "temperature": TEMPERATURE, "max_tokens": max_tokens}
        if "gpt-oss" in p["model"]:
            body["reasoning_effort"] = "low"
        if with_tools:
            body.update(tools=T.AW_TOOL_SCHEMAS, tool_choice="auto")
        headers = {"Content-Type": "application/json"}
        if p["key"]:
            headers["Authorization"] = f"Bearer {p['key']}"
        switched = False
        for attempt in range(1, 7):
            _shrink_old_results(messages)
            resp = requests.post(f"{p['base']}/chat/completions", headers=headers, json=body, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                if usage is not None and data.get("usage"):
                    usage["tokens"] += data["usage"].get("total_tokens", 0)
                if usage is not None:
                    usage["model"] = f"{p['name']} · {p['model']}"
                return data["choices"][0]["message"]
            text = resp.text
            if _out_of_allowance(resp.status_code, text) and _ACTIVE["i"] + 1 < len(PROVIDERS):
                _ACTIVE["i"] += 1   # move to the next service for the rest of this session
                if on_wait:
                    on_wait(f"{p['name']} is out of allowance: switching to {current()['name']} ({current()['model']})")
                switched = True
                break
            if resp.status_code in (429, 503) and not _out_of_allowance(resp.status_code, text) and attempt < 6:
                m = re.search(r"try again in ((?:\d+(?:\.\d+)?(?:ms|m|s|h))+)", text)
                wait = min(60.0, (_seconds(m.group(1)) if m else 0) or float(resp.headers.get("retry-after", 0) or 0) or 4.0 * attempt) + 0.5
                if on_wait:
                    on_wait(f"waiting {wait:.0f}s for the rate limit")
                time.sleep(wait)
                continue
            if resp.status_code == 400 and ("tool_use_failed" in text or "failed_generation" in text):
                raise LLMError("BAD_TOOL_CALL:" + text[:300])
            if resp.status_code == 400 and _adapt_to_provider(body, text):
                continue   # e.g. OpenAI's newer models: max_completion_tokens instead of max_tokens, default temperature
            raise LLMError(f"AI service error {resp.status_code} from {p['name']}: {text[:400]}")
        if not switched:
            raise LLMError("AI service kept refusing (rate limit). Try again in a minute.")


def run_agent(question, on_step=None, on_wait=None, max_iterations=MAX_ITERATIONS, max_tokens=1500, on_think=None):
    """One question in -> {"answer", "trace", "charts", "queries", "tokens", "seconds"}.

    on_step(step_number, tool_name, args, result) is called after every tool call (for the live screen),
    on_think(round_number, model) just before each request to the AI.
    """
    t0 = time.time()
    first_chart = len(T.CHARTS)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    trace, usage = [], {"tokens": 0}
    answer = ""
    for rnd in range(1, max_iterations + 1):
        if on_think:
            on_think(rnd, f"{current()['name']} · {current()['model']}")
        try:
            msg = _chat(messages, on_wait=on_wait, usage=usage, max_tokens=max_tokens)
        except LLMError as exc:
            if not str(exc).startswith("BAD_TOOL_CALL:"):
                raise
            messages.append({"role": "user", "content": "Your last tool call was rejected: " + str(exc)[14:250]
                             + " Fix the arguments and try again."})
            continue
        calls = msg.get("tool_calls") or []
        if not calls:
            if (msg.get("content") or "").strip():
                answer = msg["content"].strip()
                break
            messages.append({"role": "user", "content": "Continue: call the next tool you need, or write the final answer."})
            continue
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for tc in calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = run_tool(name, args)
            trace.append({"tool": name, "args": args, "result": result})
            if on_step:
                on_step(len(trace), name, args, result)
            messages.append({"role": "tool", "tool_call_id": tc["id"], "name": name,
                             "content": json.dumps(compact(name, result), default=str)})
    if not answer:   # out of rounds: answer from what was gathered, no more tools
        digest = "\n".join(f"- {t['tool']}({json.dumps(t['args'])}) -> {json.dumps(compact(t['tool'], t['result']), default=str)[:700]}"
                           for t in trace)
        final = [{"role": "system", "content": SYSTEM_PROMPT},
                 {"role": "user", "content": question + "\n\nTOOL RESULTS YOU ALREADY GATHERED:\n" + digest +
                  "\n\nNo more tools are available. Write your final answer now, using only these results."}]
        if on_think:
            on_think(max_iterations + 1, f"{current()['name']} · {current()['model']}")
        answer = (_chat(final, with_tools=False, on_wait=on_wait, usage=usage, max_tokens=max_tokens).get("content") or "").strip()
    answer = answer.translate({0x2011: "-", 0x2010: "-", 0x00A0: " ", 0x202F: " ", 0x2009: " "}) or \
        "(The agent did not produce an answer. Try asking again.)"
    return {"question": question, "answer": answer, "trace": trace,
            "charts": [c for c in T.CHARTS[first_chart:]],
            "queries": queries_used(trace), "tokens": usage["tokens"], "seconds": round(time.time() - t0, 1),
            "mode": "live", "model": usage.get("model") or f"{current()['name']} · {current()['model']}"}


def with_history(question, history, remember=2):
    """Follow-up questions: prepend the last couple of questions, answers and queries."""
    if not history:
        return question
    lines = []
    for h in history[-remember:]:
        lines.append(f"Q: {h['question']}\nA: {h['answer'][:600]}\nQueries: " +
                     " | ".join(q["text"][:300] for q in h.get("queries", [])))
    return ("EARLIER IN THIS CONVERSATION (context only; run queries again if you need numbers):\n" +
            "\n".join(lines) + "\n\nNEW QUESTION: " + question)
