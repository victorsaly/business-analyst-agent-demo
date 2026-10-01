# Prompt and Tool Optimization: Business Analyst Agent

The original and optimized versions of every prompt the agent reads, side by side, to cut token use
on the Groq free tier (about 8,000 tokens per minute and 200,000 per day) without weakening the
grounding rules.

> **Status:** token counts below are **measured** with the notebook's own estimate
> (characters ÷ 3.3, as in `_estimate_tokens`). The optimized cells were run against the real
> tools and data. They have **not** yet been scored against the live model: run the scorecard
> (§5.15) before adopting them.

## Why the agent is expensive

Every round of the agent loop re-sends the system prompt **and** the full tool menu. Tool results
themselves are small (100–460 tokens). So the cost is driven by **fixed text × number of rounds**.
The recorded run of *"Was anything unusual going on in operations this year?"* took 3 rounds of one
`detect_anomalies` call each, used about 10,100 tokens, and waited on the rate limit between every step.

## Summary of changes

| What | Original | Optimized | Change |
|---|---|---|---|
| Tool menu (`TOOL_SCHEMAS`), sent every round | ~2,021 tokens | ~1,257 tokens | **−38%** |
| System prompt, sent every round | ~629 tokens | ~554 tokens | −12% |
| **Fixed cost per round** | **~2,650** | **~1,811** | **−32%** |
| Anomaly scan of 5 metrics | 5 calls, often 5 rounds | **1 call, 1 round** (~323-token result) | −4 rounds |
| Briefing instructions | ~315 tokens | ~256 tokens | −19% |
| Answer room held back per call by the rate-limit guard | 750 tokens | 400 tokens | −350 per call |

Per tool menu card: `get_data_overview` 106 → 72, `query_metric` 464 → 300,
`compare_periods` 548 → 345, `make_chart` 426 → 309, `detect_anomalies` 472 → 227.

The optimized system prompt is shorter and also adds rules the original lacked: no causes without
a tool result, challenge false premises, no proxies for missing data, relative-time definitions,
and an explicit metric list for anomaly scans.

## How to apply

Edit these cells in order, then choose *Runtime → Run after* from §2.5:

1. **§2.5** tool menu cards (analysis tools): Change 1
2. **§3** "How the agent sees these two tools" (chart and anomaly tools): Change 2
3. **§5.4** the agent's toolbox: Change 3 (append to the end of the cell)
4. **§5.5** system prompt: Change 4
5. **§5.7 / §5.8** agent loops: Change 5 (two one-line edits)
6. **§5.9** `run_agent`: Change 6
7. **§5.11** weekly briefing: Change 7

The workshop lever is unchanged: attendees still edit tool descriptions in §2.5 and §3. The oracle
(§4) keeps using the original single-metric `detect_anomalies`, so its 15/15 baseline is unaffected.

---

## Change 1: Analysis tool menu cards (§2.5)

**Why:** the list of 15 metric names was written out in every tool (4 times in total), and guidance was
repeated between the tool descriptions and the system prompt. Shared pieces are now defined once,
and guidance lives in one place (the system prompt).

### Original

```python
_PERIOD_HELP = ('Time period: "all", a quarter "Q1"/"Q2"/"Q3", a month "2026-04", '
                'an ISO week "W23", or a week range "W20-W24".')
_FILTERS_SCHEMA = {
    "type": "object",
    "description": "Optional. Only include rows matching these values. Operations metrics can only be filtered by region.",
    "properties": {
        "region": {"type": "string", "enum": _REGIONS},
        "category": {"type": "string", "enum": _CATEGORIES},
        "channel": {"type": "string", "enum": _CHANNELS},
    },
}

ANALYSIS_TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_data_overview",
        "description": ("Describe the data available: tables, date range, regions, categories, channels, "
                        "every metric with its meaning, and the period formats. Call this first if unsure "
                        "whether the data can answer a question."),
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "query_metric",
        "description": ("Get the value of one business metric, optionally split by up to two dimensions "
                        "(e.g. revenue by region, margin_pct by category and channel), filtered and for a "
                        "period. Percentages are returned as numbers like 31.5 meaning 31.5%."),
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string", "enum": list(METRICS), "description": "Which metric to measure."},
            "group_by": {"type": "string",
                         "description": ("Optional. One dimension, or two separated by a comma "
                                         f"(e.g. \"region,category\"). Options: {', '.join(_ALL_DIMS)}. "
                                         "Operations metrics support region, quarter, week.")},
            "filters": _FILTERS_SCHEMA,
            "period": {"type": "string", "description": _PERIOD_HELP + ' Default "all".'},
        }, "required": ["metric"]},
    }},
    {"type": "function", "function": {
        "name": "compare_periods",
        "description": ("Compare a metric between two periods (e.g. Q1 vs Q2) and show the change. "
                        "Add a dimension to see which regions/categories/channels drove the change. "
                        "For margin_pct it also returns a 'margin bridge' that splits the change into "
                        "discount, product cost, freight and sales-mix effects - use it to answer WHY margin moved."),
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string", "enum": list(METRICS), "description": "Which metric to compare."},
            "period_a": {"type": "string", "description": "The earlier / baseline period. " + _PERIOD_HELP},
            "period_b": {"type": "string", "description": "The later period to compare against period_a. " + _PERIOD_HELP},
            "dimension": {"type": "string", "enum": ["region", "category", "channel"],
                          "description": "Optional. Break the change down by this dimension, ranked by impact."},
            "filters": _FILTERS_SCHEMA,
        }, "required": ["metric", "period_a", "period_b"]},
    }},
]
```

### Optimized

```python
# Shared pieces, defined once (the metric list used to be repeated in every tool)
_METRIC = {"type": "string", "enum": list(METRICS)}
_PERIOD = {"type": "string", "description": "all | Q1-Q3 | 2026-04 | W23 | W20-W24"}
_FILTERS = {"type": "object", "properties": {
    "region": {"type": "string", "enum": _REGIONS},
    "category": {"type": "string", "enum": _CATEGORIES},
    "channel": {"type": "string", "enum": _CHANNELS}}}

ANALYSIS_TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_data_overview",
        "description": "List tables, dates, regions, categories, channels and metrics. Only if unsure the data covers a question.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "query_metric",
        "description": "Value of one metric, optionally split by up to 2 dimensions (comma-separated).",
        "parameters": {"type": "object", "properties": {
            "metric": _METRIC,
            "group_by": {"type": "string", "description": "e.g. region or region,category; ops metrics: region/quarter/week"},
            "filters": _FILTERS, "period": _PERIOD}, "required": ["metric"]}}},
    {"type": "function", "function": {
        "name": "compare_periods",
        "description": "Change in a metric from period_a to period_b. dimension ranks which segment drove it. "
                       "margin_pct adds a margin_bridge (discount/cogs/freight/mix).",
        "parameters": {"type": "object", "properties": {
            "metric": _METRIC, "period_a": _PERIOD, "period_b": _PERIOD,
            "dimension": {"type": "string", "enum": ["region", "category", "channel"]},
            "filters": _FILTERS}, "required": ["metric", "period_a", "period_b"]}}},
]
```

Keep the `_REGIONS`, `_CATEGORIES`, `_CHANNELS` and `_ALL_DIMS` lines above this block, and the
`ANALYSIS_TOOLS = {...}` dictionary below it, unchanged.

---

## Change 2: Chart and anomaly tool menu cards (§3)

**Why:** `detect_anomalies` now takes a **list** of metrics, so one call replaces up to seven.
The rarely used `method` and `threshold` arguments are hidden from the model (the Python defaults
still apply, including `ANOMALY_THRESHOLD`). Long per-argument descriptions are removed.

### Original

```python
VIZ_TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "make_chart",
        "description": ("Draw a chart of one metric and save it for the weekly briefing. Use 'line' to show how a "
                        "metric changed week by week (one line per group), or 'bar' to compare totals between "
                        "groups for a period. Returns a caption and a short summary of the key numbers. Mention "
                        "the chart_id in your answer so the reader knows a chart was made."),
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string", "enum": _ALL_METRICS, "description": "Which number to chart."},
            "group_by": {"type": "string", "enum": ["region", "category", "channel"],
                         "description": "Draw one line/bar per region, category or channel. Leave out for a single total line. Operations metrics can only be split by region."},
            "period": {"type": "string", "description": "'all', 'Q1'/'Q2'/'Q3', a month like '2026-04', a week like 'W23', or a range like 'W20-W24'."},
            "chart_type": {"type": "string", "enum": ["line", "bar"], "description": "'line' = weekly trend over time; 'bar' = one total per group."},
            "filters": {"type": "object", "description": "Optional, e.g. {\"region\": \"North\"} or {\"category\": \"Electronics\"}."},
        }, "required": ["metric"]}}},
    {"type": "function", "function": {
        "name": "detect_anomalies",
        "description": ("Find unusual weeks: weeks where a metric was far higher or lower than its recent normal, "
                        "checked separately for each region (or category / channel). Use this for questions like "
                        "'anything unusual?', 'any spikes?', 'what went wrong last month?'. Returns the flagged "
                        "weeks, back-to-back flagged weeks grouped into runs, and which groups looked normal."),
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string", "enum": _ALL_METRICS, "description": "Which number to check."},
            "dimension": {"type": "string", "enum": ["region", "category", "channel", "total"],
                          "description": "Check each region / category / channel separately (default 'region'), or 'total' for the whole company. Operations metrics only support region or total."},
            "method": {"type": "string", "enum": ["rolling_zscore", "zscore"],
                       "description": "'rolling_zscore' (default, compares each week with the 8 weeks before it) or 'zscore' (compares with the whole period's average)."},
            "threshold": {"type": "number", "description": "How unusual a week must be to be flagged. Leave out to use the notebook's ANOMALY_THRESHOLD."},
            "period": {"type": "string", "description": "Only report unusual weeks inside this period: 'all', 'Q2', '2026-05', 'W31', 'W20-W24'."},
        }, "required": ["metric"]}}},
]
```

### Optimized

```python
VIZ_TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "make_chart",
        "description": "Draw a chart; returns chart_id and summary. line = weekly trend, bar = totals per group.",
        "parameters": {"type": "object", "properties": {
            "metric": _METRIC,
            "group_by": {"type": "string", "enum": ["region", "category", "channel"]},
            "period": _PERIOD,
            "chart_type": {"type": "string", "enum": ["line", "bar"]},
            "filters": _FILTERS}, "required": ["metric"]}}},
    {"type": "function", "function": {
        "name": "detect_anomalies",
        "description": "Unusual weeks vs the previous 8 weeks, per region (or category/channel/total). "
                       "Pass ALL metrics to check in one call.",
        "parameters": {"type": "object", "properties": {
            "metrics": {"type": "array", "items": _METRIC, "maxItems": 7},
            "dimension": {"type": "string", "enum": ["region", "category", "channel", "total"]},
            "period": _PERIOD}, "required": ["metrics"]}}},
]
```

Keep `VIZ_TOOLS = {"make_chart": make_chart, "detect_anomalies": detect_anomalies}` below it unchanged.

---

## Change 3: Multi-metric anomaly tool (append to §5.4)

**Why:** the new schema needs a function that accepts `metrics`. Each metric is still recorded as its
own trace entry, so the weekly briefing, its chart safety net, the app's anomaly table and the
scorecard's tool check all keep working without changes. The model receives one compact combined
result: a summary and the list of normal segments per metric.

### Original

None. The agent called `detect_anomalies` once per metric.

### Optimized (add at the end of the §5.4 cell)

```python
# --- detect_anomalies for several metrics in ONE call (one round instead of one per metric) ---
def detect_anomalies_multi(metrics=None, dimension="region", period="all", metric=None):
    metrics = metrics or metric or []
    metrics = [metrics] if isinstance(metrics, str) else list(metrics)
    if not metrics:
        return {"error": "Give at least one metric in 'metrics'.", "available": list(METRICS)}
    results = [detect_anomalies(m, dimension=dimension, period=period) for m in dict.fromkeys(metrics[:7])]
    summary = " | ".join(r.get("summary") or r.get("error", "") for r in results)
    return {"metric": "multiple", "results": results, "summary": summary}


# The agent gets the multi-metric version; the oracle in Section 4 still uses the original via VIZ_TOOLS.
TOOLS = {**ANALYSIS_TOOLS, **VIZ_TOOLS, "detect_anomalies": detect_anomalies_multi}


def _trace_entries(name, args, result):
    """One trace entry per metric, so the briefing, app and scorecard read results exactly as before."""
    if name == "detect_anomalies" and isinstance(result, dict) and "results" in result:
        base = {k: v for k, v in args.items() if k not in ("metrics", "metric")}
        return [{"tool": name, "args": {**base, "metric": r.get("metric")}, "result": r} for r in result["results"]]
    return [{"tool": name, "args": args, "result": result}]


_compact_for_llm_original = _compact_for_llm
def _compact_for_llm(name, result, max_chars=1800):
    if name == "detect_anomalies" and isinstance(result, dict) and "results" in result:
        return {"results": [{"metric": r.get("metric"), "summary": r.get("summary") or r.get("error"),
                             "normal": r.get("segments_without_flags")} for r in result["results"]]}
    return _compact_for_llm_original(name, result, max_chars)
```

---

## Change 4: System prompt (§5.5)

**Why:** shorter, and closes gaps seen in the recorded runs. The operations question checked
`return_rate` (a sales metric) and missed `on_time_pct`. The briefing skipped a required check.
Nothing stopped "I don't have competitor data, but…" followed by a guess.

### Original

```python
SYSTEM_PROMPT = f"""You are a business performance analyst. You answer questions from busy managers
about the company's sales and operations data (Jan-Sep 2026), using ONLY the tools provided.

RULES
1. Every number you state must come from a tool result in this conversation. Never invent,
   estimate or guess a number. If you need a number, call a tool.
2. If unsure what data exists, call get_data_overview first.
3. "Why did X change?" -> call compare_periods. For margin_pct its margin_bridge splits the
   change into discount, freight, product cost (cogs) and mix: name the top 2 drivers with
   their pts, and where they happened (region / category).
4. "Anything unusual / wrong / any spikes?" -> call detect_anomalies, for several metrics if
   needed, including operations metrics (stockout_rate, on_time_pct, avg_delivery_days).
   Prefer rates (return_rate, margin_pct, stockout_rate) over raw counts, and check by region
   (the default) so you can say WHERE. Report each unusual run: where, which weeks, peak value
   vs the expected value.
5. "Is X growing / what's the trend?" -> compare the first and the latest quarter (Q1 vs Q3;
   Q3 is complete) and give the % change.
6. Make a chart with make_chart when a trend or comparison helps (at most 1-2 per question)
   and mention its chart_id.
7. If the question is about something this data does not contain (e.g. competitors or their
   prices, customer satisfaction, marketing spend, weather, website traffic, staff morale),
   do NOT answer with other metrics. Say plainly: "The data does not include <topic>", and
   suggest what data would be needed to answer it.
8. Percentages from tools are already in % (31.5 means 31.5%). Changes in % metrics are
   percentage points (pts).
9. Periods: quarters "Q1".."Q3", months "2026-04", weeks "W23" or "W20-W24". The latest full
   week of sales data is W{LATEST_FULL_WEEK}.
10. You may call several tools at once. Stop calling tools as soon as you can answer.

ANSWER FORMAT: start with a one-sentence headline answer, then 2-4 short bullets with the key
numbers. Plain English, no preamble.
"""
```

### Optimized

```python
_quarters = sorted(sales_df["quarter"].astype(str).unique())
FIRST_Q, LATEST_Q = _quarters[0], _quarters[-1]
DATE_FROM, DATE_TO = f"{sales_df['date'].min():%d %b %Y}", f"{sales_df['date'].max():%d %b %Y}"

SYSTEM_PROMPT = f"""You are a business performance analyst for a retailer. Answer managers' questions about
sales and warehouse data ({DATE_FROM} to {DATE_TO}) using ONLY the tools.

GROUNDING
1. Every number must come from a tool result in this conversation. Never invent or estimate one.
2. Only state a cause if a tool result shows it; otherwise say it needs checking.
3. If the question assumes something the data contradicts, say so with the numbers.

SCOPE
4. The data covers sales (revenue, units, margin, discount, cogs, freight, returns) and warehouse
   operations (stockouts, on-time %, delivery days, orders, headcount) by region, category,
   channel and week. For anything else (competitors, satisfaction/NPS, marketing, weather,
   web traffic, staff morale) reply "The data does not include <topic>." with no proxies or
   estimates, and name the data that would be needed. No tool call is needed for this.

TIME
5. Latest full week = W{LATEST_FULL_WEEK}; last quarter = {LATEST_Q}; "this year" = all.
   Trends: compare {FIRST_Q} with {LATEST_Q} and give the % change.

TOOLS
6. Request every tool you need in ONE turn; stop as soon as you can answer.
7. Why did X change -> compare_periods. For margin_pct give the top 2 margin_bridge drivers in pts
   and where_it_happened. Use filters to focus; use dimension to find who drove a change.
8. Anything unusual -> ONE detect_anomalies call with all relevant metrics:
   sales: margin_pct, return_rate, revenue; operations: stockout_rate, on_time_pct,
   avg_delivery_days, orders_fulfilled. Report each run: where, weeks, peak vs expected.
   If none: say "nothing unusual" and list what you checked.
9. Chart (max 2) only for a trend or comparison; cite its chart_id.
10. % values are already percentages; changes in % metrics are pts.

FORMAT: one-sentence headline, then 2-4 bullets, each with a number and its period."""
```

| Rule | What it fixes |
|---|---|
| 2 | Rule 1 covered numbers but not causes ("due to seasonal promotions") |
| 3 | False-premise questions ("Why did East's margin collapse?") |
| 4 | Lists what the data **does** cover, so out-of-scope questions need no `get_data_overview` call (~655 tokens) and no proxies or estimates are given |
| 5 | Defines "last quarter" and "latest week"; quarters come from the data instead of a hard-coded "Q1 vs Q3" |
| 6 | Request every tool in one turn, which cuts rounds |
| 8 | Names the exact metrics for "anything unusual" and requires one combined call |

The phrases the scorecard looks for are kept: "The data does not include" (X1–X3) and
"nothing unusual" (N1–N3).

---

## Change 5: Agent loops (§5.7 and §5.8)

**Why:** record one trace entry per metric for the multi-metric tool (see Change 3).

### Original

```python
# §5.7 (Groq loop)
            trace.append({"tool": tc.function.name, "args": args, "result": result})

# §5.8 (Gemini loop)
            trace.append({"tool": fc.name, "args": args, "result": result})
```

### Optimized

```python
# §5.7 (Groq loop)
            trace.extend(_trace_entries(tc.function.name, args, result))

# §5.8 (Gemini loop)
            trace.extend(_trace_entries(fc.name, args, result))
```

---

## Change 6: Answer room (§5.9)

**Why:** `_groq_wait_for_budget` holds back half of `max_answer_tokens` before every call. Answers are
4–6 lines, so 1,500 reserves far more than needed and causes avoidable waits.

### Original

```python
def run_agent(question, system_prompt=None, max_iterations=None, max_answer_tokens=1500):
```

### Optimized

```python
def run_agent(question, system_prompt=None, max_iterations=None, max_answer_tokens=800):
```

If answers come back cut off (`gpt-oss` counts its reasoning against this limit), raise it to 1000.

---

## Change 7: Weekly briefing (§5.11)

**Why:** the original listed five anomaly checks in prose, and the recorded run made them one per round
(and skipped `on_time_pct`). The optimized version asks for one combined anomaly call, the
comparison and the first chart in a single turn. The reply format is unchanged because
`_parse_briefing` depends on it.

### Original

```python
BRIEFING_INSTRUCTIONS = """Write the weekly leadership briefing for week W{week}.
The KPI table was already looked up for you (do not re-query it):
{kpi_text}

Investigate with your tools (call several at once where you can):
1. detect_anomalies with period "{recent}" for revenue, margin_pct, return_rate, stockout_rate
   and on_time_pct (by region).
2. compare_periods with period_a "W{prev}" and period_b "W{week}" and dimension "region" for the
   KPI with the biggest change above, to see which region drove it.
3. make_chart at least twice with period "{recent}": revenue by region (line), plus a line chart
   of any anomaly you found (e.g. return_rate by region).

Only give a reason for a change if a tool result shows it; otherwise say it needs checking.
Then reply in EXACTLY this format (plain text, every number from a tool result or the table):
HEADLINE: <one sentence>
WHAT CHANGED AND WHY:
- <2-3 bullets>
WATCH LIST:
- <1-3 bullets, one per unusual run found, with weeks and numbers>
FOLLOW-UPS:
- <2-3 recommended actions or questions for the team>
"""
```

### Optimized

```python
BRIEFING_INSTRUCTIONS = """Write the weekly leadership briefing for W{week}.
KPI table (already looked up, do not re-query):
{kpi_text}

Make ALL of these calls in ONE turn:
1. detect_anomalies: metrics [revenue, margin_pct, return_rate, stockout_rate, on_time_pct], period "{recent}".
2. compare_periods: period_a "W{prev}", period_b "W{week}", dimension "region", for the KPI with the
   largest vs-last-week change.
3. make_chart (line, group_by region, period "{recent}"): revenue.
Then one more turn at most: make_chart for one metric with an unusual run, if any.

Only give a cause if a tool result shows it. Reply in EXACTLY this format, every number from a tool or the table:
HEADLINE: <one sentence>
WHAT CHANGED AND WHY:
- <2-3 bullets>
WATCH LIST:
- <1-3 bullets, one per unusual run, with weeks and numbers>
FOLLOW-UPS:
- <2-3 recommended actions or questions>
"""
```

And in `weekly_briefing()`:

```python
# Original
                       max_iterations=MAX_ITERATIONS + 4, max_answer_tokens=2500)
# Optimized
                       max_iterations=MAX_ITERATIONS + 4, max_answer_tokens=1500)
```

---

## Testing the change

Run each line before and after, and fill in the right-hand columns. The "before" figures are from
the recorded Colab run.

| Run | Tokens before | Tokens after | Result before | Result after |
|---|---|---|---|---|
| `ask("Why did margin drop in the North region in Q2?")` | 4,966 | | correct | |
| `ask("Was anything unusual going on in operations this year?")` | 10,103 | | 3 metrics checked | |
| `ask("How do our prices compare with our competitors'?")` | 2,155 | | declined | |
| `weekly_briefing()` | ~30,000 | | 4 of 5 checks | |
| `run_eval(agent_fn)` | ~65,000 | | 15/15 | |

For a quick check that stays within the daily allowance: `run_eval(agent_fn, qids=["A1", "N2", "N3", "X1"])`.

## Risks to watch

- **Fewer argument descriptions.** For example, "operations metrics can only be filtered by region" is
  gone from the menu. A wrong call returns an error that lists the allowed values, which costs one extra
  round when it happens. If the trace shows this often, put that one sentence back.
- **"Everything in one turn"** can make the model request a chart before it has seen the numbers.
  Check that charts still match what the answer says.
- **Lower answer room** can truncate long answers. See Change 6.
- **The scorecard is lenient.** It can pass some wrong answers (an invented figure in the same sentence
  as "I don't have the data", "normal" counted as "nothing unusual", "not growing" matching "grow").
  Read the answers, not only the score, when comparing versions.
