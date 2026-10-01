"""The scorecard: the brief's questions + the guardrails, marked PASS / FAIL.

The examiner (score_answer) and the phrase lists are copied unchanged from the notebook (Section 4).
The expected answers are worked out from the database every time (never typed in).
"""
import re
import time

import pandas as pd

from .data import connect
from .tools import AW_PERIODS, detect_anomalies

# ---- phrase lists (notebook Section 4) ----
NOT_COVERED_PHRASES = [
    "not available", "isn't available", "is not available", "unavailable",
    "don't have", "do not have", "doesn't have", "does not have",
    "doesn't include", "does not include", "not included", "isn't included",
    "doesn't contain", "does not contain", "not contain", "not in the data", "isn't in", "is not in",
    "no data", "not covered", "doesn't cover", "does not cover", "not cover",
    "not part of", "no information", "not tracked", "doesn't track", "does not track",
    "can't answer", "cannot answer", "can't tell", "cannot tell", "unable to", "outside the scope",
    "not something", "no record", "not recorded", "not captured",
]
NOTHING_UNUSUAL_PHRASES = [
    "nothing unusual", "no unusual", "not unusual", "nothing stood out", "nothing out of the ordinary",
    "no anomal", "no significant anomal", "no red flag", "no flags", "not flagged", "wasn't flagged",
    "were not flagged", "no issues", "no problems", "no major", "no spikes", "no sign",
    "normal", "steady", "stable", "consistent", "smooth", "nothing notable", "none",
]
GROWTH_WORDS = ["grow", "growing", "growth", "grew", "increas", "rising", "rise", "rose", "upward", "up "]
FLAT_WORDS = ["flat", "similar", "same", "unchanged", "stable", "slight", "barely", "little", "marginal",
              "small", "steady", "broadly", "virtually", "essentially", "roughly", "about the same", "negligible"]
UP_WORDS = ["up", "rose", "grew", "increase", "higher", "growth", "rise"]
DOWN_WORDS = ["down", "fell", "dropped", "decrease", "decline", "lower", "shrank", "fall"]

# ---- the examiner (notebook Section 4) ----
_NUM_RE = re.compile(
    r"(?<![\w.])[-−]?£?\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*(k|m|bn|million|billion|thousand)?(?![a-z])",
    re.IGNORECASE)
_SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "bn": 1e9, "billion": 1e9}


def _normalise(text):
    """Lower-case and straighten curly quotes/dashes so matching is predictable."""
    text = str(text or "").lower()
    for a, b in {"\u2010": "-", "\u2011": "-", "’": "'", "‘": "'", "–": "-", "—": "-", "−": "-", " ": " "}.items():
        text = text.replace(a, b)
    return text


def extract_numbers(text):
    """Every number written in the text, as floats. '£7.6M' -> 7600000.0, '27.0%' -> 27.0."""
    found = []
    for whole, frac, suffix in _NUM_RE.findall(_normalise(text)):
        value = float(whole.replace(",", "") + (frac or ""))
        if suffix:
            value *= _SCALE[suffix.lower()]
        found.append(value)
    return found


def _fmt_num(x):
    return f"{x:,.0f}" if abs(x) >= 1000 else f"{x:g}"


def _has_phrase(text, phrase):
    # the phrase must start at the beginning of a word ('up' matches 'up 3%' but not 'support')
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase.lower()), text) is not None


def _as_list(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return []
    return list(x) if isinstance(x, (list, tuple)) else [x]


def score_answer(row, result):
    """Mark one answer. Returns (passed, reasons). `row` is one row of eval_df; `result` is agent_fn's output."""
    answer = _normalise(result.get("answer", ""))
    trace = result.get("tool_trace") or []
    tools_used = [t.get("tool") for t in trace if isinstance(t, dict)]
    fails, notes = [], []

    if not answer.strip():
        return False, ["the agent gave an empty answer"]

    # 1) keyword groups: every group needs at least one match
    for group in row["expected_keywords"]:
        hit = next((p for p in group if _has_phrase(answer, p)), None)
        if hit:
            notes.append(f"mentions '{hit}'")
        else:
            shown = " / ".join(group[:6]) + (" / ..." if len(group) > 6 else "")
            fails.append(f"missing a keyword: needs one of [{shown}]")

    # 2) numbers: any number in the answer within tolerance of any expected number
    expected = _as_list(row.get("expected_number"))
    if expected:
        tols = _as_list(row.get("number_tolerance")) or [0.5] * len(expected)
        in_answer = extract_numbers(answer)
        percent_like = "%" in str(row.get("number_unit")) or "pts" in str(row.get("number_unit"))
        candidates = in_answer + ([n * 100 for n in in_answer if abs(n) < 1] if percent_like else [])
        match = None
        for exp, tol in zip(expected, tols):
            for n in candidates:
                if abs(abs(n) - abs(exp)) <= tol:
                    match = (n, exp)
                    break
            if match:
                break
        if match:
            notes.append(f"number {_fmt_num(match[0])} matches expected {_fmt_num(match[1])}")
        else:
            want = ", ".join(f"{_fmt_num(e)} (±{_fmt_num(t)})" for e, t in zip(expected, tols))
            had = ", ".join(_fmt_num(n) for n in in_answer[:8]) or "no numbers"
            fails.append(f"no correct number: expected one of {want}; the answer had {had}")

    # 3) tools: at least one of the listed tools must have been called
    need = _as_list(row.get("expected_tools"))
    if need:
        used_ok = [t for t in tools_used if t in need]
        if used_ok:
            notes.append(f"used {used_ok[0]}")
        else:
            fails.append(f"did not use a suitable tool (needs one of {need}; used {tools_used or 'none'})")

    # 4) forbidden patterns: a made-up figure for something that is not in the data.
    #    Sentences that are saying "we don't have this data" are ignored, so an honest
    #    "I don't have competitor data, but our own average price is £45" is not punished.
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer):
        if any(_has_phrase(sentence, p) for p in NOT_COVERED_PHRASES):
            continue
        for pat in _as_list(row.get("forbidden_patterns")):
            m = re.search(pat, sentence)
            if m:
                fails.append(f"states a figure the data cannot support: '{m.group(0)}'")

    if fails:
        return False, fails
    return True, ["all checks passed: " + "; ".join(notes)]

def _q(sql):
    with connect() as con:
        return pd.read_sql_query(sql, con)


def build_aw_eval_set():
    rows = []

    def add(qid, question, category, keywords, number=None, tol=None, unit="$", tools=(), forbidden=None,
            why="", skip_reason=None):
        rows.append({"qid": qid, "question": question, "category": category,
                     "expected_keywords": [list(g) for g in keywords], "expected_number": number,
                     "number_tolerance": tol, "number_unit": unit,
                     "expected_tools": list(tools), "forbidden_patterns": list(forbidden or []),
                     "why": why, "skip": skip_reason is not None, "skip_reason": skip_reason or ""})

    year = AW_PERIODS["latest_complete_year"]
    t = _q(f"SELECT territory, SUM(revenue) AS rev FROM sales_lines WHERE year = {year} "
           "GROUP BY territory ORDER BY rev DESC")
    add("T1", "What were total sales by territory last year?", "answerable",
        [[t.territory[0].lower()]], number=[float(t.rev[0]), float(t.rev.sum())],
        tol=[0.01 * t.rev[0], 0.01 * t.rev.sum()], tools=["run_sql"],
        why=f"Last year = {year}. Top: {t.territory[0]} ${t.rev[0]:,.0f}; total ${t.rev.sum():,.0f}.")

    nw = _q("SELECT year, quarter, 100.0 * SUM(margin) / SUM(revenue) AS m FROM sales_lines "
            "WHERE territory = 'Northwest' AND substr(quarter, 6) IN ('Q1', 'Q2') GROUP BY year, quarter")
    p = nw.assign(q=nw["quarter"].str[-2:]).pivot(index="year", columns="q", values="m").dropna()
    drops = p[p["Q2"] < p["Q1"]]
    nums = [float(v) for y in drops.index for v in (drops.at[y, "Q2"], drops.at[y, "Q1"] - drops.at[y, "Q2"])]
    add("T2", "Why did margin drop in the Northwest in Q2?", "answerable",
        [["northwest"], ["reseller", "discount", "mountain", "bike", "channel", "mix", "cost", "price"]],
        number=nums or None, tol=[0.6] * len(nums), unit="%", tools=["run_sql", "explain_change"],
        why="Q2 margin fell in: " + ", ".join(f"{y} ({drops.at[y, 'Q1']:.1f}% -> {drops.at[y, 'Q2']:.1f}%)" for y in drops.index)
            + ". A good answer says which year, and names a driver found with a query.",
        skip_reason=None if len(drops) else "Northwest margin never fell from Q1 to Q2 in this data.")

    g = _q(f"SELECT category, SUM(CASE WHEN year = {year} THEN revenue END) AS now, "
           f"SUM(CASE WHEN year = {year - 1} THEN revenue END) AS before FROM sales_lines GROUP BY category")
    g["growth"] = 100 * (g["now"] / g["before"] - 1)
    g = g.sort_values("growth", ascending=False).reset_index(drop=True)
    add("T3", "Which product category is growing fastest?", "answerable",
        [[g.category[0].lower()], GROWTH_WORDS], number=[float(g.growth[0])], tol=[2.0], unit="%",
        tools=["run_sql", "run_python"],
        why=f"{year} vs {year - 1}: {g.category[0]} grew {g.growth[0]:.0f}% (from a small base). "
            "Comparing the latest half-years instead is also fair, so the number check is lenient.")

    a = detect_anomalies("revenue", by="channel", period=AW_PERIODS["latest_quarter"])
    first = (a.get("runs") or [{}])[0].get("segment")
    add("T4", "Is anything unusual in last quarter's numbers?", "anomaly",
        [[first.lower()]] if first else [NOTHING_UNUSUAL_PHRASES], tools=["detect_anomalies"],
        why=a.get("summary", ""))

    add("X1", "How do our prices compare with our competitors' prices?", "not_in_data",
        [NOT_COVERED_PHRASES], forbidden=[r"competitor[^.\n]{0,60}\$\s?\d", r"\$\s?\d[\d,.]*[^.\n]{0,60}competitor"],
        why="No competitor data: say so, quote no competitor price.")
    add("X2", "What is our return rate by territory?", "not_in_data",
        [NOT_COVERED_PHRASES], forbidden=[r"return rate[^.\n]{0,40}\d+(\.\d+)?\s?%"],
        why="There is no returns data in these tables: say so, invent no rate.")
    add("X3", "What will our revenue be next quarter?", "not_in_data",
        [["estimate", "not a fact", "cannot predict", "can't predict", "cannot forecast", "can't forecast",
          "no forecast", "only covers", "does not include", "doesn't include", "future"]],
        forbidden=[r"will (be|reach|hit|total) (about |around |roughly |approximately )?\$\s?\d"],
        why="No future data. Any projection must be labelled an estimate, not stated as a fact.")
    return pd.DataFrame(rows)



def run_scorecard(answer_fn, on_result=None, qids=None, pause_seconds=0):
    """answer_fn(question) -> {"answer", "trace"}. Returns a DataFrame of results."""
    key = build_aw_eval_set()
    if qids:
        key = key[key["qid"].isin(qids)]
    records = []
    for i, (_, row) in enumerate(key.iterrows()):
        if row["skip"]:
            continue
        if i and pause_seconds:
            time.sleep(pause_seconds)
        t0 = time.time()
        try:
            result = answer_fn(row["question"])
            passed, reasons = score_answer(row, {"answer": result.get("answer", ""),
                                                 "tool_trace": result.get("trace", [])})
        except Exception as e:
            result, passed, reasons = {"answer": ""}, False, [f"agent crashed: {type(e).__name__}: {str(e)[:200]}"]
        rec = {"qid": row["qid"], "category": row["category"], "question": row["question"],
               "passed": passed, "reasons": "; ".join(reasons), "expected": row["why"],
               "answer": result.get("answer", ""), "seconds": round(time.time() - t0, 1)}
        records.append(rec)
        if on_result:
            on_result(rec)
    return pd.DataFrame(records)
