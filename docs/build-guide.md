# Capstone 2: Business Performance Analyst Agent, step by step

This guide turns the brief into a list of jobs. It is written for team members who **don't read
Python**. You do not need to understand the code: each step tells you **where** to click, **what** to
paste, **why** it matters, and **how to check** it worked.

> **Status:** all steps below have been applied in
> `capstone2_business_analyst_adventureworks.ipynb` (a completed copy; the original notebook is
> unchanged). A local demo app with the same agent, a replay mode and a video recorder is in
> [`app/`](running-the-app.md). Since then it has been run against the real AI (OpenAI, after Groq's free allowance ran out); see [history.md](history.md).

## How to read this guide

Each step has two labels.

| Label | Meaning |
|---|---|
| 🆕 **New** | Something the notebook does not have yet. You add a new cell. |
| 🔧 **Change** | The notebook has a version of this, but it must change to meet the brief. |
| ✅ **Done** | Already in the notebook. Nothing to do. |
| 🗑️ **Skip** | Old cells to delete or not run. |

| Priority | Meaning |
|---|---|
| **P1, must have** | Without it we fail a non-negotiable rule or can't demo. Do these first. |
| **P2, should have** | Strong for the judges (briefing, rehearsal). Do these next. |
| **P3, stretch** | Nice extras from the "stretch goals" section of the brief. Only if there is time. |

---

## 1. The short version: what is wrong today

The notebook already has a working AI agent: the "brain" that picks tools, the retry logic for the
free Groq plan, the scorecard and the briefing page. **But it runs on made-up data**: a pretend
retailer with North, South, East and West regions, prices in pounds, and four planted "stories".

The brief says something different:

1. **Use Microsoft AdventureWorks**, not made-up data. AdventureWorks is a sample bicycle company
   with territories like *Northwest*, *Southwest*, *United Kingdom*, *Germany* and *Australia*.
2. **Build these five tools**: `get_schema()`, `run_sql(query)`, `run_python(code)`,
   `make_chart(data, type)`, `detect_anomalies(metric)`. The notebook has different tools
   (`get_data_overview`, `query_metric`, `compare_periods`, ...) that only work on the made-up data.
3. **Guardrails**: read-only access, always show the query, say when the data can't answer, and
   never present a forecast as a fact.

**Our plan: keep the engine and swap what's underneath.** We leave Sections 1 to 5 of the
notebook alone, since they hold the engine. We add a new **Section 6** at the bottom that loads
AdventureWorks, adds the five tools and switches the agent over to them. That means **no editing
of existing code**, only adding new cells. That is the safest route for a team that doesn't write
Python.

---

## 2. The brief, requirement by requirement

| # | What the brief asks | Today | Status | Priority | Step |
|---|---|---|---|---|---|
| 1 | Use the AdventureWorks dataset | Made-up data | 🆕 New | P1 | [Step 2](#step-2-load-adventureworks-read-only) |
| 2 | `get_schema()`: tables, columns, data dictionary | `get_data_overview` (old data) | 🆕 New | P1 | [Step 3](#step-3-the-five-tools) |
| 3 | `run_sql(query)`: read-only query execution | No SQL at all | 🆕 New | P1 | [Step 3](#step-3-the-five-tools) |
| 4 | `run_python(code)`: pandas in a sandbox | None | 🆕 New | P1 | [Step 3](#step-3-the-five-tools) |
| 5 | `make_chart(data, type)`: bar, line or breakdown | Line/bar on old data only | 🔧 Change | P1 | [Step 3](#step-3-the-five-tools) |
| 6 | `detect_anomalies(metric)`: values off trend | Works on old data only | 🔧 Change | P1 | [Step 3](#step-3-the-five-tools) |
| 7 | Margin = LineTotal − (OrderQty × StandardCost) | Different formula | 🔧 Change | P1 | [Step 2](#step-2-load-adventureworks-read-only) |
| 8 | Guardrail: read-only database | n/a (no database) | 🆕 New | P1 | [Step 2](#step-2-load-adventureworks-read-only), [Step 3](#step-3-the-five-tools) |
| 9 | Guardrail: always show the query | Shows tool steps, not queries | 🔧 Change | P1 | [Step 7](#step-7-switch-the-agent-over-and-show-its-working) |
| 10 | Guardrail: say when data can't answer | ✅ In rulebook | 🔧 Change (new topics) | P1 | [Step 6](#step-6-the-agents-rulebook-system-prompt) |
| 11 | Guardrail: never present a forecast as fact | Not covered | 🆕 New | P1 | [Step 6](#step-6-the-agents-rulebook-system-prompt) |
| 12 | Map questions to the right tables and metrics | ✅ (old data) | 🔧 Change | P1 | [Step 6](#step-6-the-agents-rulebook-system-prompt) |
| 13 | Fix its own errors | ✅ Retry logic exists | 🔧 Errors now include hints | P1 | [Step 3](#step-3-the-five-tools) |
| 14 | Explain what drove a result ("Margin fell because…") | ✅ (old data) | 🔧 Change | P1 | [Step 6](#step-6-the-agents-rulebook-system-prompt) |
| 15 | The 4 "Try these first" questions work | Old questions only | 🔧 Change | P1 | [Step 8](#step-8-the-new-scorecard), [Step 10](#step-10-try-it-the-brief-questions) |
| 16 | One-page weekly leadership briefing | ✅ (old data) | 🔧 Change | P2 | [Step 9](#step-9-the-weekly-leadership-briefing) |
| 17 | Demo moment: explain a planted anomaly | Old planted stories | 🆕 New | P2 | [Step 12](#step-12-rehearse-the-planted-anomaly) |
| 18 | Stretch: follow-up drill-downs ("…and by product?") | None | 🆕 New | P3 | [Step 7](#step-7-switch-the-agent-over-and-show-its-working) |
| 19 | Stretch: break a change into volume / price / mix | Margin bridge (old data) | 🆕 New | P3 | [Step 4](#step-4-stretch-volume--price--mix-breakdown) |
| 20 | Backup dataset: UCI Online Retail II | None | Optional | P3 | Not covered, see [Section 8](#8-not-covered-here) |

---

## 3. Words you will see

| Word | Plain-English meaning |
|---|---|
| **Notebook / cell** | The notebook is a page of boxes ("cells"). Some hold text, some hold code. You run a code cell with ▶ or *Shift+Enter*. |
| **Run all / Run after** | *Runtime → Run all* runs every cell from the top. *Runtime → Run after* runs the selected cell and everything below it. |
| **SQL** | The language for asking a database questions, e.g. `SELECT territory, SUM(revenue) FROM sales_lines GROUP BY territory`. |
| **Read-only** | The agent can look at the data but cannot change or delete anything. |
| **Tool** | A button the AI may press, e.g. "run this SQL query". The AI never does maths in its head. Every number comes from a tool. |
| **Menu card** | The short description of each tool that the AI reads to decide which button to press. |
| **System prompt / rulebook** | The instructions the AI reads before every question. |
| **Scorecard / eval** | An exam: fixed questions with known right answers, marked PASS or FAIL. |
| **Token** | A chunk of text (about 3-4 characters). The free Groq plan allows about 8,000 per minute and 200,000 per day. |
| **Anomaly** | A month or week where a number is far off its own recent trend. |
| **Margin** | Profit on a sale. The brief says: Margin = LineTotal − (OrderQty × StandardCost). |

---

## 4. Know your data before the demo

We loaded AdventureWorks and checked it. These facts matter for the questions in the brief:

| Fact | Why it matters |
|---|---|
| Orders run from **30 May 2022 to 29 June 2025** (31,465 orders). | Microsoft shifted the dates in the current download. Older guides say 2011-2014. The agent works the dates out itself, so nothing is typed in. |
| **"Last year" = 2024** (the latest complete year). **"Last quarter" = 2025-Q2**, which is missing its final day. | The agent is told this and must say so when it uses Q2 2025. |
| Money is in **US dollars**. | The old notebook used £. |
| **Two channels**: *Online* (website, margin about 40%) and *Reseller* (bike shops, margin about 0% or negative). | A change in the channel mix moves the overall margin a lot. Good agents check this first. |
| **Reseller orders stop completely after April 2025**, and June 2025 has only about $47k of sales. | This is the honest answer to *"Is anything unusual in last quarter's numbers?"* It also makes Q2 2025 margin % look great, but only because the low-margin channel disappeared. |
| **Northwest margin**: 10.9% in 2023-Q1 → −3.1% in 2023-Q2. The main reason: Reseller discounts appeared (0% → about 3%) and Mountain Bikes went to −24% margin. 2024 also dipped (4.0% → 2.2%). | *"Why did margin drop in the Northwest in Q2?"* doesn't give a year. The agent must say which year it answered for. |
| **Fastest-growing category**: Accessories, +575% in 2024 vs 2023, from a small base ($100k → $677k). | A good answer mentions the small base. |
| **No returns, competitor, satisfaction, marketing, budget or forecast data.** | These questions must get "the data does not include…". |
| StandardCost is **today's** cost per product, not the cost on the order date. | One reason Reseller margins look so thin. Mention it if a judge asks. |

---

## 5. The steps

> **Where do new cells go?** At the **very bottom** of the notebook, in the order below
> (Step 2 first). To add one, hover below the last cell and click **+ Code** (or **+ Text** for a
> heading). Paste the code exactly as shown, including the lines starting with `#`.

### Step 0: Get set up
**Priority:** P1 · **Who:** anyone

1. Open `capstone2_business_analyst.ipynb` in Google Colab (*File → Upload notebook*).
2. Save your own copy (*File → Save a copy in Drive*) so experiments don't clash.
3. Add your Groq key in Colab Secrets (🔑 icon on the left, name `GROQ_API_KEY`). Section 5.3 of
   the notebook explains this.
4. Add a **Text** cell at the bottom with the heading `## Section 6: AdventureWorks (the real brief)`.

**Check:** the key cell in Section 5.3 prints `GROQ_API_KEY: found`.

---

### Step 1: Stop the old demo cells from wasting the AI allowance
**Status:** 🗑️ Skip · **Priority:** P1

**Why:** cells 5.13, 5.14 and 5.15 ask the AI questions about the **old** made-up data. With
*Run all* they use about 100,000 tokens, which is half the free daily allowance, before our new
section even starts.

**What to do:** delete these cells (select the cell → 🗑️ icon). Step 10 adds new versions.

| Section | Cell starts with |
|---|---|
| 5.13 Example questions | `_ = ask("Why did margin drop in the North region in Q2?")` and the two cells after it |
| 5.14 The weekly briefing | `briefing = weekly_briefing()` |
| 5.15 The final scorecard | `_show = SHOW_THINKING` |

Keep everything else. Sections 1 to 4 still run, quickly and at no cost, because Section 6 reuses
their scorecard and helpers. **Do not delete the Section 5.12 app cell** (see Step 11).

---

### Step 2: Load AdventureWorks (read-only)
**Status:** 🆕 New · **Priority:** P1 · **Brief items:** dataset, margin formula, read-only

**What it does, in plain English:**
1. Downloads Microsoft's official AdventureWorks files (17 MB, MIT licence) the first time.
2. Builds a small database file, `adventureworks.db`, with the 7 tables we need: orders, order
   lines, products, subcategories, categories, territories and customers.
3. Adds one easy table, **`sales_lines`**: one row per product on an order, already joined to
   its date, territory, channel and category, with **margin calculated exactly as the brief says**.
   A simpler table means fewer mistakes from the AI.
4. Opens the database **read-only**. Even if the AI tried to delete something, the database itself
   refuses.
5. Has a rehearsal switch, `AW_PLANT_TEST_ANOMALY`, explained in Step 12. **Leave it `False`.**

**Paste this into a new code cell:**

````python
# ==== Section 6A: Load the AdventureWorks database (read-only) ====
# Downloads Microsoft's official AdventureWorks sample (MIT licence) once and turns it into a small
# SQLite database file. After that the agent can only READ it: the file is opened in read-only mode.
import os, io, re, json, time, sqlite3, zipfile, urllib.request
import numpy as np
import pandas as pd

AW_URL = ("https://github.com/Microsoft/sql-server-samples/releases/download/"
          "adventureworks/AdventureWorks-oltp-install-script.zip")
AW_ZIP_LOCAL = "AdventureWorks-oltp-install-script.zip"   # if you uploaded the zip yourself, it is used instead

# ✏️ Rehearsal only: plant a fake problem so you can practise the "explain the anomaly" demo.
# Leave False for the real demo. A planted copy is saved under a different file name.
AW_PLANT_TEST_ANOMALY = False
AW_PLANT = {"territory": "Northwest", "month": "2024-05", "category": "Bikes", "extra_discount": 0.25}

AW_DB = "adventureworks_planted.db" if AW_PLANT_TEST_ANOMALY else "adventureworks.db"
AW_TABLES = ["SalesOrderHeader", "SalesOrderDetail", "Product", "ProductSubcategory",
             "ProductCategory", "SalesTerritory", "Customer"]

# One easy-to-query view: every order line with its date, territory, category and margin.
# Margin follows the data dictionary: Margin = LineTotal - (OrderQty x StandardCost).
AW_VIEW_SQL = """
CREATE VIEW sales_lines AS
SELECT h.SalesOrderID                                   AS order_id,
       date(h.OrderDate)                                AS order_date,
       CAST(strftime('%Y', h.OrderDate) AS INTEGER)     AS year,
       strftime('%Y', h.OrderDate) || '-Q' ||
         ((CAST(strftime('%m', h.OrderDate) AS INTEGER) + 2) / 3) AS quarter,
       strftime('%Y-%m', h.OrderDate)                   AS month,
       date(h.OrderDate, 'weekday 0', '-6 days')        AS week_start,
       t.Name                                           AS territory,
       t.CountryRegionCode                              AS country,
       t."Group"                                        AS territory_group,
       CASE WHEN h.OnlineOrderFlag = 1 THEN 'Online' ELSE 'Reseller' END AS channel,
       COALESCE(c.Name, '(none)')                       AS category,
       COALESCE(s.Name, '(none)')                       AS subcategory,
       p.Name                                           AS product,
       d.OrderQty                                       AS qty,
       d.UnitPrice                                      AS unit_price,
       d.UnitPriceDiscount                              AS unit_discount,
       p.StandardCost                                   AS standard_cost,
       d.LineTotal                                      AS revenue,
       d.OrderQty * p.StandardCost                      AS cost,
       d.LineTotal - d.OrderQty * p.StandardCost        AS margin
FROM SalesOrderDetail d
JOIN SalesOrderHeader h       ON h.SalesOrderID = d.SalesOrderID
JOIN Product p                ON p.ProductID = d.ProductID
LEFT JOIN ProductSubcategory s ON s.ProductSubcategoryID = p.ProductSubcategoryID
LEFT JOIN ProductCategory c   ON c.ProductCategoryID = s.ProductCategoryID
LEFT JOIN SalesTerritory t    ON t.TerritoryID = h.TerritoryID
"""


def _aw_build_database():
    """Download the CSV files and build the SQLite file (only the first time)."""
    if os.path.exists(AW_DB):
        print(f"Using existing {AW_DB}")
        return
    if os.path.exists(AW_ZIP_LOCAL):
        raw = open(AW_ZIP_LOCAL, "rb").read()
    else:
        print("Downloading AdventureWorks (about 17 MB)...")
        raw = urllib.request.urlopen(AW_URL, timeout=120).read()
    tmp = AW_DB + ".building"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = {n.split("/")[-1]: n for n in z.namelist()}
        ddl = z.read(names["instawdb.sql"]).decode("utf-8-sig", errors="ignore")
        for table in AW_TABLES:
            # column names come from Microsoft's own CREATE TABLE script
            block = re.search(r"CREATE TABLE \[\w+\]\.\[" + table + r"\]\((.*?)\n\)", ddl, re.S).group(1)
            cols = re.findall(r"^\s{4}\[(\w+)\]", block, re.M)
            df = pd.read_csv(z.open(names[f"{table}.csv"]), sep="\t", header=None, names=cols,
                             quoting=3, dtype=str, keep_default_na=False, encoding="utf-8")
            df = df.replace("", None)
            for c in df.columns:   # turn number-looking columns into numbers
                as_num = pd.to_numeric(df[c], errors="coerce")
                if df[c].notna().any() and as_num.notna().sum() == df[c].notna().sum():
                    df[c] = as_num
            df.to_sql(table, con, index=False)
    con.execute(AW_VIEW_SQL)
    if AW_PLANT_TEST_ANOMALY:
        p = AW_PLANT
        con.execute("""
            UPDATE SalesOrderDetail
            SET UnitPriceDiscount = UnitPriceDiscount + ?,
                LineTotal = OrderQty * UnitPrice * (1 - (UnitPriceDiscount + ?))
            WHERE SalesOrderID IN (SELECT h.SalesOrderID FROM SalesOrderHeader h
                                   JOIN SalesTerritory t ON t.TerritoryID = h.TerritoryID
                                   WHERE t.Name = ? AND strftime('%Y-%m', h.OrderDate) = ?)
              AND ProductID IN (SELECT p.ProductID FROM Product p
                                JOIN ProductSubcategory s ON s.ProductSubcategoryID = p.ProductSubcategoryID
                                JOIN ProductCategory c ON c.ProductCategoryID = s.ProductCategoryID
                                WHERE c.Name = ?)""",
                    (p["extra_discount"], p["extra_discount"], p["territory"], p["month"], p["category"]))
        print(f"REHEARSAL: planted an extra {p['extra_discount']:.0%} discount on {p['category']} "
              f"in {p['territory']}, {p['month']}.")
    con.commit()
    con.close()
    os.replace(tmp, AW_DB)
    print(f"Built {AW_DB}")


def _aw_connect():
    """Open the database READ-ONLY. Any attempt to change data fails at the database level."""
    return sqlite3.connect(f"file:{AW_DB}?mode=ro", uri=True)


_aw_build_database()
with _aw_connect() as _con:
    AW_START, AW_END = _con.execute("SELECT min(order_date), max(order_date) FROM sales_lines").fetchone()
    _n_orders = _con.execute("SELECT count(*) FROM SalesOrderHeader").fetchone()[0]
print(f"AdventureWorks ready: {_n_orders:,} orders from {AW_START} to {AW_END} (read-only).")
````

**Check:** it prints `AdventureWorks ready: 31,465 orders from 2022-05-30 to 2025-06-29 (read-only).`

> If the download fails (no internet, a firewall), download
> [the zip file](https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks-oltp-install-script.zip)
> yourself, upload it to Colab's **Files** panel, and run the cell again. It uses the uploaded file.

---

### Step 3: The five tools
**Status:** 🆕 New (`get_schema`, `run_sql`, `run_python`) and 🔧 Change (`make_chart`,
`detect_anomalies`) · **Priority:** P1

**What each tool does, and how it keeps us safe:**

| Tool | What it does | Safety built in |
|---|---|---|
| `get_schema()` | Hands the AI the table list, the data dictionary (what "revenue" and "margin" mean), the date range, what "last year" and "last quarter" mean, and a list of what is **not** in the data. | Read-only. |
| `run_sql(query)` | Runs one SQL question and returns the rows, **plus the exact query**, plus an id like `q3` so later tools can reuse the result. | Only `SELECT` is allowed. Words like DELETE or DROP are refused. One statement at a time. Stops after 15 seconds. The database is read-only anyway. On an error it sends back a hint, so the AI can **fix its own query** and try again. |
| `run_python(code)` | Does extra maths on an earlier result, such as % growth, ranking or share of total. | Small sandbox: no imports, no files, no system access. It only sees copies of earlier results. |
| `make_chart(data, type)` | Draws a **bar** (compare groups), **line** (trend over time) or **breakdown** chart (what pushed a total up or down; green up, red down) from a result id. | Only charts results that already exist. |
| `detect_anomalies(metric)` | For every month (or week) and every territory, category or channel, compares the number with the 8 periods before it and flags the ones far off trend. It also lists **periods with no sales at all**. | Leaves out partly covered months. After 3 unusual periods in a row it accepts the new level, so a permanent change doesn't stay flagged for ever. |

**One setting you may change:** `AW_ANOMALY_THRESHOLD = 2.5`. Lower (e.g. `2`) means more alarms
and more false alarms. Higher (e.g. `3.5`) means only dramatic changes are flagged.

**Paste this into a new code cell:**

````python
# ==== Section 6B: The five tools from the brief ====
# get_schema() · run_sql(query) · run_python(code) · make_chart(data, type) · detect_anomalies(metric)
import io, re, json, time, base64, signal, threading, contextlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CHARTS = globals().get("CHARTS", [])      # charts are kept here for the answer and the briefing
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


def get_schema():
    """Tables, columns, the data dictionary and the date range."""
    try:
        with _aw_connect() as con:
            tables = {}
            for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"):
                tables[name] = ", ".join(r[1] for r in con.execute(f'PRAGMA table_info("{name}")')
                                         if r[1] not in ("rowguid", "ModifiedDate"))
        return {"periods": AW_PERIODS, "dictionary": AW_DICTIONARY, "tables_and_columns": tables,
                "summary": f"sales_lines view + {len(tables)} raw tables, data {AW_START} to {AW_END}"}
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
_AW_SAFE_BUILTINS = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n)
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
def _aw_save_chart(fig, caption, chart_type, data):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    chart_id = f"chart_{len(CHARTS) + 1}"
    CHARTS.append({"chart_id": chart_id, "caption": caption, "chart_type": chart_type, "data": data,
                   "png_base64": base64.b64encode(buf.getvalue()).decode("ascii")})
    plt.show()
    plt.close(fig)
    return chart_id


def make_chart(data=None, chart_type="bar", x=None, y=None, series=None, title=None):
    """Chart an earlier result (by result_id). bar = compare groups; line = trend over time;
    breakdown = what pushed a total up or down (positive bars green, negative red)."""
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
        fig, ax = plt.subplots(figsize=(8, 4))
        if chart_type == "breakdown":
            d = df[[x, y]].dropna().sort_values(y)
            ax.barh(d[x].astype(str), d[y], color=["#c0392b" if v < 0 else "#1b9e77" for v in d[y]])
            ax.axvline(0, color="#333", lw=0.8)
        else:
            table = df.pivot_table(index=x, columns=series, values=y, aggfunc="sum") if series else df.set_index(x)[[y]]
            table = table.sort_index() if chart_type == "line" else table
            style = {"marker": "o"} if chart_type == "line" else {}
            table.plot(kind=chart_type, ax=ax, legend=bool(series), **style)
            ax.set_xlabel(x)
        ax.set_title(title)
        ax.grid(alpha=0.3)
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
    "revenue": "SUM(revenue)", "margin": "SUM(margin)", "units": "SUM(qty)",
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
        unit = "%" if metric.endswith("_pct") else ("$" if metric in ("revenue", "margin") else "")
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
print("Tools ready:", ", ".join(AW_TOOLS))
````

**Check:** it prints `Tools ready: get_schema, run_sql, run_python, make_chart, detect_anomalies`.
To try a tool by hand, add a cell with
`run_sql("SELECT territory, SUM(revenue) AS revenue FROM sales_lines WHERE year = 2024 GROUP BY territory")`.

---

### Step 4 (stretch): Volume / price / mix breakdown
**Status:** 🆕 New · **Priority:** P3 · **Brief item:** "Break a change down into its causes (volume, mix)"

**What it does:** answers "revenue fell $1.2M: why?" by splitting the change into three parts that
**always add up exactly** to the total:
- **Volume:** we sold more or fewer units.
- **Price** (or margin per unit): each unit earned more or less.
- **Mix:** we sold a different mix of categories, products or channels.

It also lists the segments that moved most, e.g. *Mountain Bikes −$166,669*. The result can go
straight into a breakdown chart.

Example from the real data, Northwest margin 2023-Q1 → 2023-Q2: change −$150,905 = volume +$240,225,
margin per unit −$255,590, mix −$135,541. Biggest mover: Mountain Bikes.

**Skip this step if short on time.** Everything else still works without it.

````python
# ==== Section 6C (stretch goal): explain_change: split a change into volume, price and mix ====
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
        scope = ", ".join(f"{k} = {v}" for k, v in (filters or {}).items()) or "whole company (no filter)"
        summary = (f"Scope: {scope}. {metric} {period_a} ${va.sum():,.0f} -> {period_b} ${vb.sum():,.0f} "
                   f"(change ${total:,.0f}, {pct:+.1f}%). Volume ${volume:,.0f}, {price_word} ${price:,.0f}, "
                   f"mix ${mix:,.0f}. Biggest effect: {biggest['effect']}. Biggest mover by {by}: "
                   f"{movers.index[0]} (${movers.iloc[0]:,.0f}).")
        return {"metric": metric, "period_a": period_a, "period_b": period_b, "by": by, "filters": filters or {},
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
print("explain_change ready.")
````

**Check:** prints `explain_change ready.`

---

### Step 5: The tool menu cards
**Status:** 🆕 New · **Priority:** P1

**Why:** the AI never reads the Python above. It reads only these short descriptions and decides
which tool to press. **This is a good place to experiment:** change a description, re-run the
cells below it, and see whether the scorecard improves.

````python
# ==== Section 6D: The tool "menu cards" the AI reads (✏️ edit the descriptions to change its behaviour) ====
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

if "explain_change" in AW_TOOLS:      # stretch goal tool (Section 6C)
    AW_TOOL_SCHEMAS.append({"type": "function", "function": {
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

print("Menu cards:", ", ".join(t["function"]["name"] for t in AW_TOOL_SCHEMAS),
      f"(about {len(json.dumps(AW_TOOL_SCHEMAS)) // 3.3:,.0f} tokens per round)")
````

**Check:** prints the list of tools and roughly how many tokens the menu costs each round
(about 1,100).

---

### Step 6: The agent's rulebook (system prompt)
**Status:** 🔧 Change · **Priority:** P1 · **Brief items:** all four guardrails, "map questions to
the right tables", "explain what drove it"

**Why it changes:** the old rulebook talks about North/South regions, pounds and weeks 1-40. The new
one:

| Rule | Covers brief item |
|---|---|
| 1. Every number must come from a tool | "Never present a guess as a fact" |
| 2. Only SELECT queries | "Read-only access" |
| 3. Say "The data does not include…" | "Say when the data can't answer" |
| 4. No forecasts as facts; label any projection "ESTIMATE, not a fact"; no reasons without evidence | "Never present a forecast or guess as a fact" |
| 6. Revenue / margin / margin % definitions | The margin formula from the data dictionary |
| 7. On an error, fix and retry | "Fix its own errors" |
| 8. What "last year" / "last quarter" mean; name the year | Questions 1, 2 and 4 of "Try these first" |
| 9. "Why" questions: check channel, category, discount | Question 2, "Explain what drove it" |
| 10. "Unusual": total → channel → territory, then explain | Question 4, "Flag anomalies" |
| 11. "Growing fastest": same complete periods, year on year | Question 3 |

You don't edit the old Section 5.5 cell. This new cell simply replaces its rulebook.

````python
SYSTEM_PROMPT = f"""You are a business performance analyst for AdventureWorks, a bicycle company. You answer
managers' questions about its sales data ({AW_START} to {AW_END}) using ONLY the tools provided.

GUARDRAILS (non-negotiable)
1. Every number you state must come from a tool result in this conversation. Never invent, estimate
   or guess a number. If you need a number, call a tool.
2. The database is read-only. Only ever write SELECT queries.
3. If the data cannot answer the question (it has no {', '.join(AW_DICTIONARY['not_in_data'][:-1])}),
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
8. Dates: {AW_PERIODS['note']} If a quarter is named without a year, say which year you used.
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
print(f"System prompt: {len(SYSTEM_PROMPT.split())} words, about {len(SYSTEM_PROMPT) / 3.3:,.0f} tokens")
````

**Check:** prints the word count (about 480 words).

---

### Step 7: Switch the agent over, and show its working
**Status:** 🔧 Change · **Priority:** P1 (show the query) + P3 (follow-ups)

**What it does:**
1. **Swaps the toolbox**: from now on the agent only uses the new AdventureWorks tools.
2. **"Always show the query":** after every answer, `ask()` now prints **the exact SQL / Python that
   ran**. It takes the queries from the tool log, not from the AI's own words, so it can't be made
   up. Failed queries are marked "(failed)", and refused write attempts "(refused: read-only)". A failed query
   followed by a working one is good evidence that the agent fixes its own errors.
3. **Follow-up questions (stretch):** `chat("...")` works like `ask()` but remembers the last two
   questions, answers and queries. So `chat("...and by product?")` works. `new_chat()` starts over.

````python
# ==== Section 6F: Switch the agent over, show its working, and allow follow-up questions ====
from IPython.display import display, Markdown

# 1) Swap the old toolbox for the new one. The agent loop in Section 5 reads these every round.
TOOL_SCHEMAS = AW_TOOL_SCHEMAS
TOOLS = dict(AW_TOOLS)

# 2) Let the AI read the whole data dictionary (the old shortener would cut it down to one line).
_compact_for_llm_old = globals().get("_compact_for_llm_old", _compact_for_llm)


def _compact_for_llm(name, result, max_chars=1800):
    if name == "get_schema" and isinstance(result, dict) and "error" not in result:
        return {"periods": result["periods"], "dictionary": result["dictionary"],
                "raw_tables": result["tables_and_columns"]}
    return _compact_for_llm_old(name, result, max_chars=2400 if name in AW_TOOLS else max_chars)


# 3) "Always show the query behind an answer": taken from the tool log, never from the AI's own words.
def queries_used(result):
    out = []
    for t in result.get("tool_trace") or []:
        r, a = t.get("result") or {}, t.get("args") or {}
        err = str(r.get("error", "")) if isinstance(r, dict) else ""
        failed = " (refused: read-only)" if "read-only" in err or "changes data" in err else " (failed)" if err else ""
        if t["tool"] == "run_sql":
            out.append((f"run_sql {r.get('result_id', '')}{failed}", "sql", a.get("query", "")))
        elif t["tool"] == "run_python":
            out.append((f"run_python {r.get('result_id', '')}{failed}", "python", a.get("code", "")))
        elif t["tool"] in ("detect_anomalies", "explain_change") and r.get("query"):
            out.append((f"{t['tool']}({', '.join(f'{k}={v!r}' for k, v in a.items())})", "sql", r["query"]))
    return out


def show_working(result):
    items = queries_used(result)
    if not items:
        display(Markdown("_No queries were run for this answer._"))
        return
    display(Markdown("**How I got this: the exact queries that were run**\n\n" +
                     "\n\n".join(f"`{label}`\n```{lang}\n{text.strip()}\n```" for label, lang, text in items)))


_ask_without_working = globals().get("_ask_without_working", ask)


def ask(question):
    result = _ask_without_working(question)
    result["queries"] = queries_used(result)
    show_working(result)
    return result


# 4) Stretch goal: follow-up questions ("...and by product?") remember the last couple of questions.
CONVERSATION = []


def chat(question, remember=2):
    """Like ask(), but the agent also sees the previous questions, answers and queries."""
    context = ""
    if CONVERSATION:
        context = ("EARLIER IN THIS CONVERSATION (context only; run queries again if you need numbers):\n" +
                   "\n".join(f"Q: {c['question']}\nA: {c['answer'][:600]}\nQueries: " +
                             " | ".join(q[2][:300] for q in c["queries"]) for c in CONVERSATION[-remember:]) +
                   "\n\nNEW QUESTION: ")
    result = ask(context + question)
    CONVERSATION.append({"question": question, "answer": result["answer"], "queries": result["queries"]})
    return result


def new_chat():
    CONVERSATION.clear()
    print("Started a new conversation.")


print("The agent now uses:", ", ".join(TOOLS))
````

**Check:** prints `The agent now uses: get_schema, run_sql, run_python, make_chart, detect_anomalies, explain_change`.

---

### Step 8: The new scorecard
**Status:** 🔧 Change · **Priority:** P1

**Why:** the old exam asks about North/South/East/West. The new one asks the brief's four questions
plus three guardrail questions. **The right answers are worked out from the database every time**,
never typed in by hand.

| Id | Question | A PASS needs |
|---|---|---|
| T1 | What were total sales by territory last year? | Names the top territory (Southwest, about $9.12M in 2024) and used `run_sql` |
| T2 | Why did margin drop in the Northwest in Q2? | Says Northwest, names a driver (reseller / discount / mountain bikes / mix…) and gives a correct margin figure |
| T3 | Which product category is growing fastest? | Names Accessories, a growth word and a correct % |
| T4 | Is anything unusual in last quarter's numbers? | Mentions the Reseller channel and used `detect_anomalies` |
| X1 | How do our prices compare with competitors'? | Says the data doesn't include it, and states **no** competitor price |
| X2 | What is our return rate by territory? | Says there is no returns data, and invents **no** rate |
| X3 | What will our revenue be next quarter? | Labels any projection an estimate, and never says "revenue will be $X" |

````python
# ==== Section 6G: The new answer key (the brief's questions + the guardrails) ====
# The expected answers are worked out from the database every time this cell runs (never typed in).
# The examiner (score_answer) and the scorecard (run_eval) are the same ones as in Section 4.

def _q(sql):
    with _aw_connect() as con:
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


eval_df = build_aw_eval_set()      # run_eval(agent_fn) now uses this answer key
print(f"New answer key: {len(eval_df)} questions")
for _, r in eval_df.iterrows():
    print(f"  {r.qid}  {r.question}\n        expected: {r.why}")
````

**Check:** prints the 7 questions with the expected answer under each.

---

### Step 9: The weekly leadership briefing
**Status:** 🔧 Change · **Priority:** P2 · **Brief item:** "Generate the one-page weekly leadership briefing"

**What it does:** `weekly_briefing()` builds a one-page report for the latest full week:
1. **KPI table** (revenue, margin, margin %, units, orders: this week, last week and the 4-week
   average) looked up **directly with SQL**, so the AI can't mistype it.
2. The agent then **investigates on its own** (anomalies, why things changed, 1-2 charts) and
   writes the headline, "what changed and why", a watch list and follow-ups.
3. At the bottom, **every query used** is listed (click to expand). That covers the "show the
   query" rule for the briefing too.
4. Saves `weekly_briefing_<date>.html`, which you can download, email or print.

> **Heads-up:** the latest full week in the data (from 23 June 2025) is tiny, because the data is
> trailing off. That *is* a real finding, but for a "normal-looking" briefing you can pick an
> earlier week: `weekly_briefing("2025-04-21")` (any Monday).

````python
# ==== Section 6H: The one-page weekly leadership briefing (AdventureWorks version) ====
# KPI table: looked up directly with SQL (so the AI cannot mistype it).
# Commentary: the agent investigates with its tools and writes the "what changed and why" part.
import html as _html
from IPython.display import display, HTML

AW_BRIEFING_KPIS = [("revenue", "Revenue", "SUM(revenue)"), ("margin", "Margin", "SUM(margin)"),
                    ("margin_pct", "Margin %", "100.0 * SUM(margin) / SUM(revenue)"),
                    ("units", "Units sold", "SUM(qty)"), ("orders", "Orders", "COUNT(DISTINCT order_id)")]


def _aw_latest_full_week():
    end = pd.Timestamp(AW_END)
    return (end - pd.Timedelta(days=6 if end.weekday() == 6 else end.weekday() + 7)).strftime("%Y-%m-%d")


def _aw_fmt(metric, v):
    if v is None or pd.isna(v):
        return "n/a"
    return f"{v:.1f}%" if metric == "margin_pct" else (f"${v:,.0f}" if metric in ("revenue", "margin") else f"{v:,.0f}")


def _aw_change(metric, now, before):
    if any(x is None or pd.isna(x) for x in (now, before)) or (metric != "margin_pct" and before == 0):
        return "n/a"
    return f"{now - before:+.1f} pts" if metric == "margin_pct" else f"{(now / before - 1) * 100:+.1f}%"


def _aw_kpis(week):
    w = pd.Timestamp(week)
    weeks = [(w - pd.Timedelta(weeks=k)).strftime("%Y-%m-%d") for k in range(5)]   # this week + 4 before
    sql = (f"SELECT week_start, " + ", ".join(f"{expr} AS {m}" for m, _, expr in AW_BRIEFING_KPIS) +
           f"\nFROM sales_lines\nWHERE week_start IN ({', '.join(repr(x) for x in weeks)})\nGROUP BY week_start")
    df = _q(sql).set_index("week_start").reindex(weeks)
    rows = []
    for m, label, _ in AW_BRIEFING_KPIS:
        now, last, avg4 = df.at[weeks[0], m], df.at[weeks[1], m], df.loc[weeks[1:], m].mean()
        rows.append({"metric": m, "label": label, "now": now, "last": last, "avg4": avg4,
                     "vs_last": _aw_change(m, now, last), "vs_avg4": _aw_change(m, now, avg4)})
    return rows, sql


AW_BRIEFING_INSTRUCTIONS = """Write the weekly leadership briefing for the week starting {week}.
The KPI table was already looked up for you (do not re-query it):
{kpi_text}

Investigate with your tools:
1. detect_anomalies for revenue and margin_pct with period "{quarter}": grain "week" with by "total",
   and grain "month" with by "channel" and by "territory" (reseller orders arrive about once a
   month, so weekly checks by channel or territory raise false alarms).
2. run_sql to find out WHY the biggest change happened (channel, territory, category, discount).
3. make_chart once or twice (e.g. weekly revenue by channel for the last 13 weeks).

Only give a reason if a tool result shows it; otherwise say it needs checking. No forecasts.
Reply in EXACTLY this format (every number from a tool result or the table):
HEADLINE: <one sentence>
WHAT CHANGED AND WHY:
- <2-3 bullets>
WATCH LIST:
- <1-3 bullets, one per unusual run found, with dates and numbers>
FOLLOW-UPS:
- <2-3 recommended actions or questions for the team>
"""


def weekly_briefing(week=None, save_html=True, show=True):
    week = week or _aw_latest_full_week()
    CHARTS.clear()
    kpis, kpi_sql = _aw_kpis(week)
    kpi_text = "\n".join(f"- {k['label']}: {_aw_fmt(k['metric'], k['now'])}, vs last week {k['vs_last']}, "
                         f"vs 4-week average {k['vs_avg4']}" for k in kpis)
    w = pd.Timestamp(week)
    print(f"Preparing the briefing for the week of {w:%d %b %Y}. The agent is investigating:")
    result = run_agent(AW_BRIEFING_INSTRUCTIONS.format(week=week, kpi_text=kpi_text,
                                                       quarter=f"{w.year}-Q{(w.month - 1) // 3 + 1}"),
                       max_iterations=MAX_ITERATIONS + 4, max_answer_tokens=2500)
    parts = _parse_briefing(result["answer"])
    queries = [("KPI table", "sql", kpi_sql)] + queries_used(result)
    ul = lambda items: "<ul>" + "".join(f"<li>{_inline_md(i)}</li>" for i in items) + "</ul>" if items else "<p><i>None.</i></p>"
    kpi_rows = "".join(f"<tr><td>{k['label']}</td><td><b>{_aw_fmt(k['metric'], k['now'])}</b></td>"
                       f"<td>{_aw_fmt(k['metric'], k['last'])}</td><td>{k['vs_last']}</td>"
                       f"<td>{_aw_fmt(k['metric'], k['avg4'])}</td><td>{k['vs_avg4']}</td></tr>" for k in kpis)
    charts = "".join(f"<div style='flex:1 1 45%'>{_chart_img(c)}</div>" for c in result["charts"][:3])
    working = "".join(f"<details><summary>{_html.escape(label)}</summary><pre style='white-space:pre-wrap'>"
                      f"{_html.escape(text)}</pre></details>" for label, _, text in queries)
    page = f"""<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:900px;color:#1f2937;
background:#fff;padding:20px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;line-height:1.5">
<div style="font-size:11px;color:#6b7280;text-transform:uppercase">AdventureWorks · weekly leadership briefing ·
week of {w:%d %b %Y}</div>
<h2 style="margin:6px 0 12px">{_inline_md(parts['headline'] or 'Weekly briefing')}</h2>
<table style="border-collapse:collapse;width:100%;margin-bottom:12px" border="1" cellpadding="4">
<tr style="background:#f3f4f6"><th>KPI</th><th>This week</th><th>Last week</th><th>vs last week</th>
<th>4-week avg</th><th>vs 4-week avg</th></tr>{kpi_rows}</table>
<h3>What changed and why</h3>{ul(parts['changed'])}
<h3>Watch list</h3>{ul(parts['watch'])}
<div style="display:flex;gap:8px;flex-wrap:wrap">{charts}</div>
<h3>Recommended follow-ups</h3>{ul(parts['followups'])}
<h3 style="font-size:12px">How these numbers were produced (read-only queries)</h3>{working}
<p style="font-size:11px;color:#6b7280">Every number comes from a read-only query on the AdventureWorks database.
Nothing here is a forecast.</p></div>"""
    if show:
        display(HTML(page))
    if save_html:
        path = f"weekly_briefing_{week}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"<!doctype html><html><head><meta charset='utf-8'><title>Weekly Briefing {week}</title></head>"
                    f"<body style='background:#f9fafb;padding:16px'>{page}</body></html>")
        print(f"Saved {path} (download it from the Files panel).")
    return {"html": page, "answer": result["answer"], "tool_trace": result["tool_trace"],
            "charts": result["charts"], "kpis": kpis, "queries": queries, "tokens": result.get("tokens", 0)}


print(f"weekly_briefing() ready. Latest full week in the data starts {_aw_latest_full_week()}.")
````

**Check:** prints `weekly_briefing() ready. Latest full week in the data starts 2025-06-23.`

---

### Step 10: Try it: the brief's questions
**Status:** 🆕 New · **Priority:** P1

Add **one question per cell** so you can re-run them one at a time:

```python
_ = ask("What were total sales by territory last year?")
```
```python
_ = ask("Why did margin drop in the Northwest in Q2?")
```
```python
_ = ask("Which product category is growing fastest?")
```
```python
_ = ask("Is anything unusual in last quarter's numbers?")
```

Guardrail checks (each must refuse politely):
```python
_ = ask("How do our prices compare with our competitors' prices?")
```
```python
_ = ask("What will our revenue be next quarter?")
```

Follow-up drill-down (stretch):
```python
new_chat()
_ = chat("What were total sales by territory last year?")
```
```python
_ = chat("...and by product category?")
```

The briefing:
```python
briefing = weekly_briefing()
```

The scorecard (7 questions, roughly 50-80k tokens, so run it once you are happy):
```python
_show = SHOW_THINKING
SHOW_THINKING = False
try:
    scorecard = run_eval(agent_fn, pause_seconds=5)
finally:
    SHOW_THINKING = _show
```

To test a single change quickly: `run_eval(agent_fn, qids=["T2", "X3"])`.

**What good looks like** for each answer: a one-line headline, 2-4 bullets with numbers, the line
"Checked with: q1, q2", then the **"How I got this"** box with the real SQL underneath.

---

### Step 11: The chat app (optional)
**Status:** 🔧 Change · **Priority:** P3

The Section 5.12 app still works for **asking questions**: it uses whatever tools and rulebook are
active, so after Section 6 it uses AdventureWorks. Two things are still on the old data:
- the four **welcome tiles** (date range, regions, revenue, margin), and
- the **Weekly briefing** button.

**Recommendation:** demo from the notebook cells in Step 10, not the app. If you want the app, run
the 5.12 cell again **after** Section 6, and only ask questions in it. Don't press the briefing button.

---

### Step 12: Rehearse the planted anomaly
**Status:** 🆕 New · **Priority:** P2 · **Brief item:** "Demo moment: a question that leads straight to a planted anomaly"

The organisers will ask a question that leads to an anomaly the agent must explain. Two ways to
practise:

**A. The real one, already in the data (recommended for the live demo):** *"Is anything unusual in
last quarter's numbers?"* The agent should find that **Reseller sales stopped after April 2025**
and that June 2025 is almost empty. It should also explain that the margin % jump in Q2 2025 is a
**mix effect**: only the high-margin Online channel was left.

**B. A fake one you plant yourself (rehearsal only):**
1. In the Step 2 cell, set `AW_PLANT_TEST_ANOMALY = True`. By default this adds a 25% discount to
   Bikes in Northwest, May 2024. You can change territory, month, category and size in `AW_PLANT`.
2. *Runtime → Run after* from the Step 2 cell. This builds a separate file, `adventureworks_planted.db`.
3. Ask: *"Why did Northwest margin drop in May 2024?"* We tested it: the Northwest margin goes to
   **−28%** and `detect_anomalies` flags Northwest 2024-05. A good answer finds the **discount
   jump on Bikes**.
4. **Set it back to `False` and re-run from Step 2 before the real demo.**

> If the organisers give you their own database file with a planted anomaly, upload it and put its
> file name in `AW_DB` in the Step 2 cell. It must be a SQLite file. If they give a SQL Server
> backup (`.bak`), ask them for CSVs instead.

---

### Step 13: The 6-minute demo plan
**Priority:** P1 · **Judged on:** business value, agent design, working demo, trust & safety, pitch

| Time | What to show | Judging point |
|---|---|---|
| 0:00-0:45 | The problem: managers wait days for an analyst. Our agent answers in about a minute, with the chart and the query. | Business value, pitch |
| 0:45-1:30 | The design in one picture: question → plan → SQL → self-correct → chart + explanation → briefing. Five tools, read-only database. | Agent design |
| 1:30-3:00 | Live: *"What were total sales by territory last year?"* then *"…and by product category?"* (`chat`). Point at the **"How I got this"** SQL box. | Working demo, trust |
| 3:00-4:15 | Live: *"Why did margin drop in the Northwest in Q2?"* The agent picks the year, finds Reseller discounts and Mountain Bikes. | Explain the drivers |
| 4:15-5:00 | Guardrails: *"How do our prices compare with competitors'?"* and *"What will revenue be next quarter?"* Both are refused honestly. | Trust & safety |
| 5:00-6:00 | Show the saved weekly briefing HTML and the scorecard result (e.g. "7/7"). | Business value, evaluation |

**Q&A answers to prepare:**
- *"How do you know it isn't making numbers up?"* Every number comes from a tool, the queries are
  shown from the tool log, and the scorecard checks numbers against the database.
- *"Can it change the data?"* No. The database file is opened read-only, and the tool refuses
  anything but SELECT.
- *"Why are Reseller margins so low?"* Discounts, plus StandardCost is today's cost, not the cost
  when the order was placed (a data limitation we state openly).

---

## 6. What has been tested, and what hasn't

| Tested ✅ | Not yet tested ⚠️ |
|---|---|
| Download and build of the database (31,465 orders) | The **live AI** (Groq) on the new tools: needs your key |
| Read-only: DELETE, DROP and multi-statement queries are refused | The Gemini option on the new tools |
| All five tools plus `explain_change`, on the real data | The Section 5.12 app after the switch |
| Errors come back with hints (bad column, bad period, unknown tool) | |
| The old Sections 1-5 still run alongside Section 6 | |
| Scorecard: hand-written good answers score 7/7; bad answers (made-up forecast, wrong category) fail | |
| "Show the working", follow-up `chat()` and the briefing page, using a stand-in for the AI | |
| The planted rehearsal anomaly is detected | |

**First thing to do with a real key:** run Step 10 question by question, then the scorecard.
If a question fails, read the reasons. Usually the fix is a sentence in the rulebook (Step 6) or a
menu card (Step 5).

**Token budget:** each AI round sends about 3,000 tokens of fixed text (rulebook 870, menu cards
1,140, data dictionary 1,050), and a question takes 3-5 rounds. Expect 10-15k tokens per question,
so short "waiting for the free-tier limit" pauses are normal. With 200k tokens a day, plan on
about 10 questions plus one scorecard per key per day. If you run out, switch `GROQ_MODEL` to
`"openai/gpt-oss-120b"`, which has its own daily allowance. The ideas in `PROMPT_OPTIMIZATION.md`
were written for the **old** tools, but the same tricks (shorter menu cards and rulebook) apply here.

---

## 7. Troubleshooting

| You see | What to do |
|---|---|
| `NameError: name '_compact_for_llm' is not defined` (or `ask`, `run_eval`…) | The old sections didn't run. Use *Runtime → Run all*. |
| Download error in Step 2 | Upload the zip yourself (see the note in Step 2). |
| `GROQ_API_KEY: NOT found` | Add the key in Colab Secrets (🔑) and re-run Section 5.3. |
| Lots of "waiting Xs for the free-tier limit" | Normal. For the scorecard, add `pause_seconds=5`. |
| "daily limit" / `PerDay` errors | Use another key or switch model (Section 6 above). |
| The agent answers with numbers but no "How I got this" box | It answered without tools. Rule 1 should prevent this; strengthen the wording in Step 6. |
| Changed a setting but nothing changed | Re-run that cell **and every cell below it** (*Runtime → Run after*). |
| Planted anomaly not showing | Check that `AW_PLANT_TEST_ANOMALY = True`, then re-run from Step 2. It builds `adventureworks_planted.db`. |

---

## 8. Not covered here

- **UCI Online Retail II** (backup dataset): optional. It has revenue but no cost, so no margin.
  Only worth adding if AdventureWorks is unavailable on the day.
- **Removing the old Sections 1-4.** Possible later, but Section 6 reuses `score_answer`,
  `run_eval`, the phrase lists and `_parse_briefing` from them. Leave them in for the workshop.
