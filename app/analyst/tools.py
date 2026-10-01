"""The analyst's tools (same logic as notebook Sections 6B-6D).

get_schema() · run_sql(query) · run_python(code) · make_chart(data, type) · detect_anomalies(metric)
+ explain_change (stretch goal: volume / price / mix).
"""
import base64
import contextlib
import io
import json
import os
import re
import signal
import threading
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib import font_manager
import numpy as np
import pandas as pd

from . import competitors as _comp, data as _data
from .data import AW_START, AW_END, connect as _aw_connect

CHARTS = []                               # charts are kept here for the answer and the briefing
AW_RESULTS = {}                           # every query result, by id ("q1", "q2", ...), for charts / python
AW_MAX_ROWS = 50                          # rows the AI sees per query (the full result is kept)
AW_SQL_TIMEOUT_SECONDS = 15
AW_ANOMALY_THRESHOLD = 2.5                # ✏️ edit me: lower = more alarms (and more false alarms)


def _aw_period_facts():
    """Latest complete year and the latest quarter, worked out from the data (never typed in)."""
    end = pd.Timestamp(AW_END)
    year_done = end.year if end >= pd.Timestamp(f"{end.year}-12-31") else end.year - 1
    q = (end.month - 1) // 3 + 1
    q_end = pd.Timestamp(year=end.year, month=3 * q, day=1) + pd.offsets.MonthEnd(0)
    return {"data_from": AW_START, "data_to": AW_END,
            "latest_complete_year": int(year_done),
            "latest_quarter": f"{end.year}-Q{q}",
            "latest_quarter_complete": bool(end >= q_end),
            "note": (f"'Last year' means {year_done}. 'Last quarter' means {end.year}-Q{q}"
                     + ("" if end >= q_end else f" (data stops on {AW_END}, so it is missing its last "
                        f"{(q_end - end).days} day(s); say so)") + ".")}


AW_PERIODS = _aw_period_facts()

# The data dictionary the agent reads. Plain English on purpose.
AW_DICTIONARY = {
    "dialect": "SQLite. Use strftime() for dates, LIMIT (not TOP), || to join text. Read-only.",
    "money": "US dollars ($).",
    "main_view": {
        "name": "sales_lines",
        "grain": "one row per order line (one product on one sales order)",
        "columns": {
            "order_id": "sales order number", "order_date": "YYYY-MM-DD",
            "year": "e.g. 2024", "quarter": "text like '2024-Q2'", "month": "text like '2024-05'",
            "week_start": "Monday of the order's week, YYYY-MM-DD",
            "territory": "sales territory: Northwest, Northeast, Central, Southwest, Southeast, Canada, "
                         "France, Germany, Australia, United Kingdom",
            "country": "country code (US, CA, FR, DE, AU, GB)",
            "territory_group": "North America, Europe or Pacific",
            "channel": "Online (website) or Reseller (bike shops)",
            "category": "Bikes, Components, Clothing, Accessories", "subcategory": "e.g. Road Bikes",
            "product": "product name", "qty": "units on the line", "unit_price": "price charged per unit",
            "unit_discount": "discount as a fraction (0.02 = 2%)", "standard_cost": "cost per unit",
            "revenue": "LineTotal: money for the line after discount",
            "cost": "qty x standard_cost", "margin": "revenue - cost (the data dictionary's margin)",
        },
    },
    "metrics": {
        "revenue": "SUM(revenue)", "margin": "SUM(margin)",
        "margin_pct": "100.0 * SUM(margin) / SUM(revenue)  (never average row percentages)",
        "units": "SUM(qty)", "orders": "COUNT(DISTINCT order_id)",
        "avg_discount_pct": "100.0 * SUM(unit_price * unit_discount * qty) / SUM(unit_price * qty)",
    },
    "raw_tables": "SalesOrderHeader, SalesOrderDetail, Product, ProductSubcategory, ProductCategory, "
                  "SalesTerritory, Customer (Microsoft's original column names). Prefer sales_lines.",
    "not_in_data": ["returns or refunds", "competitors or their prices", "customer satisfaction",
                    "marketing spend", "website traffic", "budgets or targets", "weather", "staff morale",
                    "any future figures (no forecasts)"],
    "caveats": ["standard_cost is today's cost for each product, not the cost at the time of the order.",
                f"The first month ({AW_START[:7]}) only has a few days of data."],
}


def competitor_dictionary():
    """What the agent is told about the attached competitor price list (None when nothing is attached)."""
    source = _data.competitors()
    meta = _comp.info(source) if source else None
    if not meta:
        return None
    return {
        "source": meta["label"],
        "is_mock": meta["mock"],
        "competitors": meta["competitors"],
        "table": "competitor_prices: product, competitor, competitor_price ($), observed_date. "
                 "product matches sales_lines.product / Product.Name.",
        "view": {"name": "price_comparison",
                 "grain": "one row per product per competitor",
                 "columns": {"product": "product name", "category": "our category", "subcategory": "our subcategory",
                             "our_list_price": "our list price (Product.ListPrice)",
                             "our_online_price": "what website customers actually paid per unit, after discounts, "
                                                 "last 12 months of data (empty if not sold online)",
                             "our_units_12m": "units we sold in the last 12 months of data",
                             "competitor": "competitor name", "competitor_price": "their price ($)",
                             "observed_date": "when their price was seen",
                             "list_gap_pct": "100 * (our_list_price - competitor_price) / competitor_price; above 0 = we are dearer",
                             "online_gap_pct": "same, using our_online_price"}},
        "rules": ["Compare the same product only (the view already does this). Average gaps with AVG(list_gap_pct) "
                  "grouped by competitor / category / subcategory.",
                  "Say which competitors and how many products the comparison covers.",
                  "Reseller prices are wholesale (to bike shops), so they are not in the view: never compare them "
                  "with competitor prices."]
                 + (["These competitor prices are MOCK demo data, not real market prices. Say so in the first line "
                     "of the answer."] if meta["mock"] else
                    [f"Source: {meta['label']}, loaded {meta['loaded_at']}. Name the source in the answer."]),
    }


def not_in_data():
    """What the data cannot answer right now (competitor prices drop out when a price list is attached)."""
    gone = {"competitors or their prices"} if competitor_dictionary() else set()
    return [x for x in AW_DICTIONARY["not_in_data"] if x not in gone]


def get_schema():
    """Tables, columns, the data dictionary and the date range."""
    try:
        with _aw_connect() as con:
            tables = {}
            for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"):
                tables[name] = ", ".join(r[1] for r in con.execute(f'PRAGMA table_info("{name}")')
                                         if r[1] not in ("rowguid", "ModifiedDate"))
        dictionary = dict(AW_DICTIONARY, not_in_data=not_in_data())
        comp = competitor_dictionary()
        if comp:
            dictionary["competitor_prices"] = comp
            tables["competitor_prices"] = "product, competitor, competitor_price, observed_date"
            tables["price_comparison (view)"] = ", ".join(comp["view"]["columns"])
        return {"periods": AW_PERIODS, "dictionary": dictionary, "tables_and_columns": tables,
                "summary": f"sales_lines view + {len(tables)} raw tables, data {AW_START} to {AW_END}"
                           + (f"; competitor prices attached ({comp['source']})" if comp else "")}
    except Exception as e:
        return {"error": f"Could not read the schema: {e}"}


_AW_BLOCKED_SQL = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|reindex)\b", re.I)


def _aw_store(df):
    rid = f"q{len(AW_RESULTS) + 1}"
    AW_RESULTS[rid] = df
    return rid


def _aw_records(df, limit):
    out = df.head(limit).copy()
    for c in out.select_dtypes("float").columns:
        out[c] = out[c].round(2)
    return json.loads(out.to_json(orient="records", date_format="iso"))


def run_sql(query, max_rows=AW_MAX_ROWS):
    """Run ONE read-only SELECT query. Returns the query itself, the rows, and a result id."""
    sql = re.sub(r"--[^\n]*|/\*.*?\*/", " ", str(query or ""), flags=re.S).strip().rstrip(";").strip()
    if not sql:
        return {"error": "Empty query."}
    if not re.match(r"^(select|with)\b", sql, re.I):
        return {"error": "Only SELECT (or WITH ... SELECT) queries are allowed. The database is read-only.", "query": sql}
    if ";" in sql:
        return {"error": "Send one query at a time (no ';').", "query": sql}
    if _AW_BLOCKED_SQL.search(sql):
        return {"error": "That query contains a word that changes data. Only reading is allowed.", "query": sql}
    try:
        con = _aw_connect()
        deadline = time.time() + AW_SQL_TIMEOUT_SECONDS
        con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 10_000)
        try:
            df = pd.read_sql_query(sql, con)
        finally:
            con.close()
    except Exception as e:
        msg = str(e)
        if "interrupted" in msg:
            msg = f"query took longer than {AW_SQL_TIMEOUT_SECONDS}s and was stopped; add filters or GROUP BY"
        return {"error": f"SQL error: {msg}", "query": sql,
                "hint": "Check names with get_schema(). This is SQLite: strftime(), LIMIT, ||. Fix the query and try again."}
    rid = _aw_store(df)
    out = {"result_id": rid, "query": sql, "columns": list(map(str, df.columns)), "row_count": int(len(df)),
           "rows": _aw_records(df, max_rows),
           "summary": f"{len(df)} row(s) [{rid}] from: {' '.join(sql.split())[:160]}"}
    if len(df) > max_rows:
        out["note"] = f"Showing the first {max_rows} of {len(df)} rows. Use GROUP BY / LIMIT for a smaller answer."
    if len(df) == 0:
        out["note"] = "No rows matched. Check the filter values (e.g. territory names, quarter format '2024-Q2')."
    return out


# ---- run_python: pandas analysis in a small sandbox ----
_AW_BLOCKED_PY = re.compile(r"__|\bimport\b|\bopen\s*\(|\beval\b|\bexec\b|\bcompile\b|\bglobals\b|\blocals\b|"
                            r"\bgetattr\b|\bsetattr\b|\bdelattr\b|\bvars\b|\bos\.|\bsys\.|subprocess|"
                            r"\.to_(csv|excel|pickle|parquet|sql|json|html|feather|hdf|stata)\b|\bread_\w+|"
                            r"np\.(load|save|fromfile|savetxt|loadtxt|genfromtxt)|\.tofile\b")
import builtins as _builtins
_AW_SAFE_BUILTINS = {n: getattr(_builtins, n)
                     for n in ["abs", "all", "any", "bool", "dict", "enumerate", "filter", "float", "int",
                               "isinstance", "len", "list", "map", "max", "min", "print", "range", "reversed",
                               "round", "set", "sorted", "str", "sum", "tuple", "zip"]}


def run_python(code, data=None):
    """Run a short pandas snippet on an earlier query result. `df` = that result; put the answer in `result`."""
    code = str(code or "")
    if _AW_BLOCKED_PY.search(code):
        return {"error": "Not allowed in the sandbox: no imports, files, system access or double underscores. "
                         "Use df, pd and np only.", "code": code}
    rid = data or (list(AW_RESULTS)[-1] if AW_RESULTS else None)
    if rid not in AW_RESULTS:
        return {"error": "No data to work on. Run run_sql first, then pass its result_id as data.",
                "available": list(AW_RESULTS)[-10:], "code": code}
    env = {"__builtins__": _AW_SAFE_BUILTINS, "pd": pd, "np": np, "df": AW_RESULTS[rid].copy(),
           "results": {k: v.copy() for k, v in list(AW_RESULTS.items())[-5:]}}
    printed = io.StringIO()
    use_alarm = threading.current_thread() is threading.main_thread() and hasattr(signal, "SIGALRM")
    try:
        if use_alarm:
            signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError("took over 10s")))
            signal.alarm(10)
        with contextlib.redirect_stdout(printed):
            exec(code, env)
    except Exception as e:
        return {"error": f"Python error: {type(e).__name__}: {e}", "code": code,
                "hint": "Fix the code and try again. The data is in `df`; put the answer in `result`."}
    finally:
        if use_alarm:
            signal.alarm(0)
    result = env.get("result")
    out = {"code": code, "input": rid, "printed": printed.getvalue()[-1500:]}
    if isinstance(result, pd.Series):
        result = result.reset_index()
    if isinstance(result, pd.DataFrame):
        new_id = _aw_store(result)
        out.update(result_id=new_id, columns=list(map(str, result.columns)), row_count=int(len(result)),
                   rows=_aw_records(result, AW_MAX_ROWS))
        out["summary"] = f"python on {rid} -> {len(result)} row(s) [{new_id}]"
    else:
        out["result"] = result if isinstance(result, (int, float, str, bool, type(None))) else str(result)[:1500]
        out["summary"] = f"python on {rid} -> {str(out['result'])[:150]}"
    return out


# ---- make_chart: bar, line or breakdown chart of a query result ----
# Chart style: the cassette J-card world (ballpoint ink on lined inlay stock). Palette validated for
# colour-blind separation and contrast (dataviz validator): ink blue, red, faded blue, pencil ochre.
_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "fonts")
for _f in ("PatrickHand-Regular.ttf", "PatrickHandSC-Regular.ttf", "CourierPrime-Regular.ttf"):
    if os.path.exists(os.path.join(_FONT_DIR, _f)):
        font_manager.fontManager.addfont(os.path.join(_FONT_DIR, _f))
_INK, _INK_SOFT, _PAPER, _RULE, _OTHER = "#1E3A8A", "#3F5A9E", "#FCFBF7", "#D3DBEE", "#8E98AE"
_SERIES = ["#2B4BB0", "#B7791F", "#6B86C5"]   # red is kept for negative values only
_NEG = "#C62828"
_HAND, _HAND_SC, _TYPED = "Patrick Hand", "Patrick Hand SC", "Courier Prime"


def _is_money(col):
    return any(w in str(col).lower() for w in ("revenue", "margin", "rev_", "amount", "cost", "sales", "value")) \
        and "pct" not in str(col).lower()


def _fmt(v, col, short=False):
    if v is None or pd.isna(v):
        return ""
    sign = "\u2212" if v < 0 else ""
    a = abs(float(v))
    if "pct" in str(col).lower() or "%" in str(col):
        return f"{sign}{a:,.0f}%" if short and a >= 10 else f"{sign}{a:,.1f}%"
    if _is_money(col):
        if short and a >= 1e6:
            return f"{sign}${a / 1e6:,.1f}M"
        if short and a >= 1e3:
            return f"{sign}${a / 1e3:,.0f}K"
        return f"{sign}${a:,.0f}"
    return f"{sign}{a:,.0f}" if a >= 100 else f"{sign}{a:,.1f}"


def _style_axes(ax, ycol, horizontal=False):
    ax.set_facecolor(_PAPER)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(_INK)
    ax.spines["bottom"].set_linewidth(1.4)
    ax.grid(axis="x" if horizontal else "y", color=_RULE, linewidth=1.0)
    ax.set_axisbelow(True)
    ax.tick_params(colors=_INK, length=0, labelsize=12, pad=6)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontfamily(_HAND)
        lab.set_fontsize(15)
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: _fmt(v, ycol, short=True))
    (ax.xaxis if horizontal else ax.yaxis).set_major_formatter(fmt)
    ax.set_xlabel("")
    ax.set_ylabel("")


def _aw_save_chart(fig, caption, chart_type, data):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=_PAPER, pad_inches=0.25)
    chart_id = f"chart_{len(CHARTS) + 1}"
    CHARTS.append({"chart_id": chart_id, "caption": caption, "chart_type": chart_type, "data": data,
                   "png_base64": base64.b64encode(buf.getvalue()).decode("ascii")})
    plt.close(fig)
    return chart_id


def make_chart(data=None, chart_type="bar", x=None, y=None, series=None, title=None):
    """Chart an earlier result (by result_id). bar = compare groups; line = trend over time;
    breakdown = what pushed a total up (blue) or down (red), each bar labelled with its signed value."""
    try:
        rid = data or (list(AW_RESULTS)[-1] if AW_RESULTS else None)
        if rid not in AW_RESULTS:
            return {"error": "Unknown data id. Run run_sql first and pass its result_id.", "available": list(AW_RESULTS)[-10:]}
        df = AW_RESULTS[rid].copy()
        chart_type = str(chart_type or "bar").lower()
        if chart_type not in ("bar", "line", "breakdown"):
            return {"error": f"chart_type '{chart_type}' is not available.", "available": ["bar", "line", "breakdown"]}
        numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        x = x or next((c for c in df.columns if c not in numeric), df.columns[0])
        y = y or next((c for c in numeric if c != x), None)
        for col in (x, y, series):
            if col is not None and col not in df.columns:
                return {"error": f"Column '{col}' is not in {rid}.", "available": list(map(str, df.columns))}
        if y is None:
            return {"error": "Need a numeric column for y.", "available": list(map(str, df.columns))}
        if len(df) == 0:
            return {"error": f"{rid} has no rows to chart."}
        title = title or f"{y} by {x}" + (f" and {series}" if series else "")
        fig, ax = plt.subplots(figsize=(9, 4.4))
        fig.patch.set_facecolor(_PAPER)
        if chart_type == "breakdown":
            d = df[[x, y]].dropna().sort_values(y)
            labels = d[x].astype(str).tolist()
            vals = d[y].astype(float).tolist()
            ax.barh(labels, vals, height=0.56, color=[_NEG if v < 0 else _SERIES[0] for v in vals])
            ax.axvline(0, color=_INK, lw=1.4)
            _style_axes(ax, y, horizontal=True)
            span = (max(vals + [0]) - min(vals + [0])) or 1
            for i, v in enumerate(vals):   # every bar labelled with its sign: never colour alone
                ax.text(v + (0.015 * span if v >= 0 else -0.015 * span), i, ("+" if v >= 0 else "") + _fmt(v, y, short=True),
                        va="center", ha="left" if v >= 0 else "right", color=_INK, fontfamily=_TYPED, fontsize=14)
            ax.set_xlim(min(vals + [0]) - 0.18 * span, max(vals + [0]) + 0.18 * span)
        else:
            if series:
                table = df.pivot_table(index=x, columns=series, values=y, aggfunc="sum")
                if table.shape[1] > 3:   # never invent a 4th colour: fold the rest into "Other"
                    keep = table.sum().sort_values(ascending=False).index[:2]
                    table = pd.concat([table[keep], table.drop(columns=keep).sum(axis=1).rename("Other")], axis=1)
            else:
                table = df.set_index(x)[[y]]
            if chart_type == "line":
                table = table.sort_index()
            idx = [str(i) for i in table.index]
            colors = [_OTHER if str(c) == "Other" else _SERIES[i % 3] for i, c in enumerate(table.columns)]
            if chart_type == "line":
                pos = range(len(idx))
                for (name, col), color in zip(table.items(), colors):
                    ax.plot(pos, col.values, color=color, lw=2.4, marker="o", ms=7, mfc=color,
                            mec=_PAPER, mew=1.6, label=str(name), solid_capstyle="round")
                    last = col.dropna()
                    if series and len(last):   # direct label at the line end
                        ax.text(idx.index(str(last.index[-1])) + 0.25, last.iloc[-1], str(name), color=_INK,
                                fontfamily=_HAND, fontsize=13, va="center")
                long_labels = max(map(len, idx)) > 7
                step = max(1, len(idx) // (5 if long_labels else 8))
                ax.set_xticks(list(pos)[::step])
                ax.set_xticklabels(idx[::step], rotation=25 if long_labels else 0, ha="right" if long_labels else "center")
                ax.set_xlim(-0.4, len(idx) - 1 + (1.6 if series else 0.4))
            else:
                n = table.shape[1]
                width = 0.62 / n
                for j, ((name, col), color) in enumerate(zip(table.items(), colors)):
                    offs = [i - 0.31 + width * (j + 0.5) for i in range(len(idx))]
                    ax.bar(offs, col.values, width=width * 0.9, color=color, label=str(name))
                tilt = len(idx) > 6 or max(map(len, idx)) > 10
                step = max(1, len(idx) // 7) if len(idx) > 10 else 1
                ax.set_xticks(list(range(len(idx)))[::step])
                ax.set_xticklabels(idx[::step], rotation=28 if tilt else 0, ha="right" if tilt else "center")
                if n == 1:   # selective direct labels: highest and lowest only
                    col = table.iloc[:, 0]
                    for i in {int(col.values.argmax()), int(col.values.argmin())}:
                        v = col.iloc[i]
                        ax.text(i, v, _fmt(v, y, short=True), ha="center", va="bottom" if v >= 0 else "top",
                                color=_INK, fontfamily=_TYPED, fontsize=14)
            _style_axes(ax, y)
            if series:
                ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=table.shape[1],
                          prop={"family": _HAND, "size": 13}, labelcolor=_INK, handlelength=1.2)
        ax.set_title(title.upper(), loc="left", fontfamily=_HAND_SC, fontsize=19, color=_INK, pad=34 if series else 12)
        caption = f"{title} ({chart_type} chart of {rid})"
        chart_id = _aw_save_chart(fig, caption, chart_type, rid)
        top = df.sort_values(y, ascending=False).head(3)
        bottom = df.sort_values(y).head(1)
        key = "; ".join(f"{r[x]}{' / ' + str(r[series]) if series else ''}: {r[y]:,.2f}" for _, r in top.iterrows())
        summary = f"{caption}. Highest: {key}. Lowest: {bottom.iloc[0][x]}: {bottom.iloc[0][y]:,.2f}."
        return {"chart_id": chart_id, "caption": caption, "summary": summary}
    except Exception as e:
        return {"error": f"Could not draw the chart: {e}"}


# ---- detect_anomalies: periods well off their own recent trend ----
_AW_METRIC_SQL = {
    "revenue": "SUM(revenue)", "margin": "SUM(margin)", "cost": "SUM(cost)", "units": "SUM(qty)",
    "orders": "COUNT(DISTINCT order_id)",
    "margin_pct": "100.0 * SUM(margin) / NULLIF(SUM(revenue), 0)",
    "avg_discount_pct": "100.0 * SUM(unit_price * unit_discount * qty) / NULLIF(SUM(unit_price * qty), 0)",
}
_AW_DIMENSIONS = ["territory", "category", "channel", "country", "territory_group", "subcategory"]


def _aw_in_period(label, period):
    """Is a month ('2024-05') or week ('2024-05-06') inside a period like 2024, 2024-Q2 or 2024-05?"""
    if period in (None, "", "all"):
        return True
    p, d = str(period).strip().upper(), pd.Timestamp(label if len(label) > 7 else label + "-01")
    if re.fullmatch(r"\d{4}", p):
        return d.year == int(p)
    m = re.fullmatch(r"(\d{4})-?Q([1-4])", p)
    if m:
        return d.year == int(m.group(1)) and (d.month - 1) // 3 + 1 == int(m.group(2))
    if re.fullmatch(r"\d{4}-\d{2}", p):
        return label[:7] == p
    raise ValueError(f"period '{period}' not understood: use 'all', '2024', '2024-Q2' or '2024-05'")


def _aw_rolling_z(vals, threshold, window=8, min_prior=4):
    """For each period: how many 'normal wobbles' is it away from the average of the periods before it?
    A flagged period is kept out of the next baselines, so a short problem can't hide itself. After 3
    flagged periods in a row the new level is accepted as normal (a lasting step change, not a blip)."""
    vals = np.asarray(vals, dtype=float)
    diffs = np.diff(vals[np.isfinite(vals)])
    typical = 1.4826 * np.median(np.abs(diffs - np.median(diffs))) / np.sqrt(2) if len(diffs) > 2 else 0.0
    floor = max(typical, 0.02 * np.nanstd(vals), 1e-9)
    base, exp, z = vals.copy(), np.full(len(vals), np.nan), np.full(len(vals), np.nan)
    streak = 0
    for i in range(len(vals)):
        prior = base[:i][np.isfinite(base[:i])][-window:]
        if len(prior) < min_prior or not np.isfinite(vals[i]):
            continue
        sd = max(prior.std(ddof=1), floor)
        exp[i], z[i] = prior.mean(), float(np.clip((vals[i] - prior.mean()) / sd, -99, 99))
        if abs(z[i]) > threshold and streak < 3:
            base[i], streak = np.nan, streak + 1
        else:
            streak = 0
    return exp, z


def detect_anomalies(metric="revenue", by="territory", grain="month", period="all", threshold=None):
    """Flag months (or weeks) where a metric is far off its own recent trend, per territory/category/channel."""
    try:
        if metric not in _AW_METRIC_SQL:
            return {"error": f"metric '{metric}' is not available.", "available": list(_AW_METRIC_SQL)}
        if by not in _AW_DIMENSIONS + ["total"]:
            return {"error": f"by '{by}' is not available.", "available": _AW_DIMENSIONS + ["total"]}
        if grain not in ("month", "week"):
            return {"error": "grain must be 'month' or 'week'."}
        _aw_in_period("2024-01", period)                   # checks the period format early
        threshold = float(threshold or AW_ANOMALY_THRESHOLD)
        col = "month" if grain == "month" else "week_start"
        seg_sql = "'All'" if by == "total" else by
        sql = (f"SELECT {col} AS period, {seg_sql} AS segment, {_AW_METRIC_SQL[metric]} AS value\n"
               f"FROM sales_lines\nGROUP BY 1, 2 ORDER BY 1, 2")
        with _aw_connect() as con:
            long = pd.read_sql_query(sql, con)
        wide = long.pivot(index="period", columns="segment", values="value").sort_index()
        additive = not metric.endswith("_pct")
        gaps = []
        for seg in wide.columns:     # a period with NO sales is news: count it as 0 (or list it, for % metrics)
            started = wide[seg].first_valid_index()
            missing = [p for p in wide.index if p > started and pd.isna(wide.at[p, seg])]
            gaps += [f"{seg} {p}" for p in missing if _aw_in_period(p, period)]
            if additive:
                wide.loc[missing, seg] = 0.0
        # leave out periods the data only partly covers (e.g. a month with only 2 days of orders)
        first, last = pd.Timestamp(AW_START), pd.Timestamp(AW_END)
        partial = []
        for label in wide.index:
            start = pd.Timestamp(label + "-01" if grain == "month" else label)
            stop = start + (pd.offsets.MonthEnd(0) if grain == "month" else pd.Timedelta(days=6))
            if (min(stop, last) - max(start, first)).days + 1 < 0.9 * ((stop - start).days + 1):
                partial.append(label)
        wide = wide.drop(index=partial)
        runs = []
        for seg in wide.columns:
            s = wide[seg].dropna()
            exp, z = _aw_rolling_z(s.values, threshold)
            current = None
            for i, label in enumerate(s.index):
                hit = np.isfinite(z[i]) and abs(z[i]) > threshold and _aw_in_period(label, period)
                direction = "high" if hit and z[i] > 0 else "low"
                if hit and current and current["direction"] == direction and current["_last"] == i - 1:
                    current.update(_last=i, to=label)              # back-to-back: same run
                    if abs(z[i]) > abs(current["z"]):
                        current.update(value=round(float(s.iloc[i]), 2), expected=round(float(exp[i]), 2), z=round(float(z[i]), 1))
                elif hit:
                    current = {"segment": str(seg), "from": label, "to": label, "direction": direction, "_last": i,
                               "value": round(float(s.iloc[i]), 2), "expected": round(float(exp[i]), 2), "z": round(float(z[i]), 1)}
                    runs.append(current)
        for r in runs:
            r.pop("_last")
            r["periods"] = r["from"] if r["from"] == r["to"] else f"{r['from']} to {r['to']}"
        runs.sort(key=lambda r: -abs(r["z"]))
        unit = "%" if metric.endswith("_pct") else ("$" if metric in ("revenue", "margin", "cost") else "")
        money = lambda v: f"${v:,.0f}" if unit == "$" else f"{v:,.1f}{unit}"
        if runs:
            bits = [f"{r['segment']} {r['periods']} {r['direction']} (peak {money(r['value'])} vs ~{money(r['expected'])} expected)"
                    for r in runs[:6]]
            summary = f"{len(runs)} unusual run(s) for {metric} by {by}, period {period}: " + "; ".join(bits)
        else:
            summary = f"Nothing unusual for {metric} by {by} in period {period} (threshold {threshold:g})."
        if gaps:
            summary += f". No sales at all for: {', '.join(gaps[:8])}"
        return {"metric": metric, "by": by, "grain": grain, "period": period, "threshold": threshold,
                "query": sql, "runs": [{k: v for k, v in r.items() if k not in ("from", "to")} for r in runs[:10]],
                "n_runs": len(runs), "no_sales_periods": gaps[:20], "checked": [str(c) for c in wide.columns],
                "partial_periods_left_out": partial, "summary": summary,
                "note": "This shows WHERE and WHEN. Use run_sql to find out WHY before giving a reason."}
    except Exception as e:
        return {"error": f"Could not check for anomalies: {e}"}


AW_TOOLS = {"get_schema": get_schema, "run_sql": run_sql, "run_python": run_python,
            "make_chart": make_chart, "detect_anomalies": detect_anomalies}


# "Revenue fell $1.2M" -> how much because we sold FEWER units (volume), because each unit sold for
# less (price), and because we sold a different MIX of products / channels (mix). The three parts
# always add up exactly to the total change.


def _aw_period_where(period):
    p = str(period).strip().upper()
    if re.fullmatch(r"\d{4}", p):
        return f"year = {int(p)}"
    m = re.fullmatch(r"(\d{4})-?Q([1-4])", p)
    if m:
        return f"quarter = '{m.group(1)}-Q{m.group(2)}'"
    if re.fullmatch(r"\d{4}-\d{2}", p):
        return f"month = '{p}'"
    raise ValueError(f"period '{period}' not understood: use '2024', '2024-Q2' or '2024-05'")


def explain_change(metric="revenue", period_a=None, period_b=None, by="category", filters=None):
    """Split the change in revenue (or margin $) between two periods into volume, price and mix effects."""
    try:
        if metric not in ("revenue", "margin"):
            return {"error": "metric must be 'revenue' or 'margin'."}
        if by not in _AW_DIMENSIONS:
            return {"error": f"by '{by}' is not available.", "available": _AW_DIMENSIONS}
        where = []
        for k, v in (filters or {}).items():
            if k not in _AW_DIMENSIONS:
                return {"error": f"filter '{k}' is not available.", "available": _AW_DIMENSIONS}
            where.append(f"{k} = '{str(v).replace(chr(39), chr(39) * 2)}'")
        pa, pb = _aw_period_where(period_a), _aw_period_where(period_b)
        sql = (f"SELECT CASE WHEN {pa} THEN 'A' ELSE 'B' END AS side, {by} AS segment,\n"
               f"       SUM(qty) AS units, SUM({metric}) AS value\n"
               f"FROM sales_lines\nWHERE (({pa}) OR ({pb}))" + "".join(f" AND {w}" for w in where) +
               "\nGROUP BY 1, 2")
        with _aw_connect() as con:
            long = pd.read_sql_query(sql, con)
        t = long.pivot(index="segment", columns="side", values=["units", "value"]).fillna(0.0)
        if "A" not in t["units"] or "B" not in t["units"] or t["units"]["A"].sum() == 0:
            return {"error": "No sales in one of the periods for these filters.", "query": sql}
        ua, ub, va, vb = t["units"]["A"], t["units"]["B"], t["value"]["A"], t["value"]["B"]
        rate_a = (va / ua.where(ua > 0)).fillna(vb / ub.where(ub > 0)).fillna(0.0)   # new segments: no price effect
        avg_a = va.sum() / ua.sum()
        volume = (ub.sum() - ua.sum()) * avg_a
        mix = (ub * rate_a).sum() - ub.sum() * avg_a
        price = vb.sum() - (ub * rate_a).sum()
        total = vb.sum() - va.sum()
        movers = (vb - va).sort_values(key=abs, ascending=False).head(5)
        price_word = "price per unit" if metric == "revenue" else "margin per unit"
        effects = pd.DataFrame({"effect": ["volume (units sold)", f"{price_word}", f"mix (which {by} sold)"],
                                "amount": [round(volume, 2), round(price, 2), round(mix, 2)]})
        rid = _aw_store(effects)
        pct = 100 * total / abs(va.sum()) if va.sum() else float("nan")
        biggest = effects.loc[effects["amount"].abs().idxmax()]
        m = lambda v: f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"
        scope = ", ".join(f"{k} = {v}" for k, v in (filters or {}).items()) or "whole company (no filter)"
        summary = (f"Scope: {scope}. {metric} {period_a} {m(va.sum())} -> {period_b} {m(vb.sum())} "
                   f"(change {m(total)}, {pct:+.1f}%). Volume {m(volume)}, {price_word} {m(price)}, "
                   f"mix {m(mix)}. Biggest effect: {biggest['effect']}. Biggest mover by {by}: "
                   f"{movers.index[0]} ({m(movers.iloc[0])}).")
        return {"scope": scope, "metric": metric, "period_a": period_a, "period_b": period_b, "by": by, "filters": filters or {},
                "value_a": round(va.sum(), 2), "value_b": round(vb.sum(), 2), "change": round(total, 2),
                "pct_change": round(pct, 1),
                "effects": dict(zip(effects["effect"], effects["amount"])),
                "units_a": int(ua.sum()), "units_b": int(ub.sum()),
                "top_movers": {str(k): round(float(v), 2) for k, v in movers.items()},
                "result_id": rid, "query": sql, "summary": summary,
                "note": f"Chart it with make_chart(data='{rid}', chart_type='breakdown')."}
    except Exception as e:
        return {"error": f"Could not explain the change: {e}"}


AW_TOOLS["explain_change"] = explain_change


_AW_PERIOD_HELP = "'all', a year '2024', a quarter '2024-Q2' or a month '2024-05'"

AW_TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_schema",
        "description": "Tables, columns, the data dictionary (how revenue and margin are calculated), the date "
                       "range, what 'last year' / 'last quarter' mean, and what the data does NOT contain. "
                       "Call this first.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "run_sql",
        "description": "Run ONE read-only SQLite SELECT query (prefer the sales_lines view) and get the rows "
                       "back with a result_id. Aggregate with GROUP BY so results are small. If it returns an "
                       "error, fix the query and try again.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "A single SELECT statement."}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "run_python",
        "description": "Run a short pandas snippet on an earlier result (e.g. % change, ranking, share of total). "
                       "The result is in `df`; pd and np are available; no imports. Put the answer in `result`.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "e.g. result = df.assign(growth_pct=df['rev_2024'] / df['rev_2023'] * 100 - 100)"},
            "data": {"type": "string", "description": "result_id to work on, e.g. 'q2'. Default: the latest."}},
            "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "make_chart",
        "description": "Draw a chart of an earlier result. 'bar' compares groups, 'line' shows a trend over "
                       "time, 'breakdown' shows what pushed a total up or down. Mention the chart_id.",
        "parameters": {"type": "object", "properties": {
            "data": {"type": "string", "description": "result_id, e.g. 'q3'."},
            "chart_type": {"type": "string", "enum": ["bar", "line", "breakdown"]},
            "x": {"type": "string", "description": "Column for the x axis / labels (optional)."},
            "y": {"type": "string", "description": "Numeric column to plot (optional)."},
            "series": {"type": "string", "description": "Column to split into one line/bar per value (optional)."},
            "title": {"type": "string"}},
            "required": ["data", "chart_type"]}}},
    {"type": "function", "function": {
        "name": "detect_anomalies",
        "description": "Flag months (or weeks) where a metric is well off its own recent trend, per territory, "
                       "category or channel ('total' = whole company). Also lists periods with no sales at all. "
                       "It says WHERE and WHEN, not why: follow up with run_sql.",
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string", "enum": list(_AW_METRIC_SQL)},
            "by": {"type": "string", "enum": _AW_DIMENSIONS + ["total"]},
            "grain": {"type": "string", "enum": ["month", "week"]},
            "period": {"type": "string", "description": "Only report flags inside this period: " + _AW_PERIOD_HELP}},
            "required": ["metric"]}}},
]

AW_TOOL_SCHEMAS.append(  # stretch goal tool
    {"type": "function", "function": {
        "name": "explain_change",
        "description": "Why did revenue or margin ($) change between two periods? Splits the change into "
                       "volume (units), price (per unit) and mix (which products / channels sold), and lists "
                       "the segments that moved most.",
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string", "enum": ["revenue", "margin"]},
            "period_a": {"type": "string", "description": "Earlier period: " + _AW_PERIOD_HELP},
            "period_b": {"type": "string", "description": "Later period, same format."},
            "by": {"type": "string", "enum": _AW_DIMENSIONS},
            "filters": {"type": "object", "description": "Optional, e.g. {\"territory\": \"Northwest\"}."}},
            "required": ["metric", "period_a", "period_b"]}}})
