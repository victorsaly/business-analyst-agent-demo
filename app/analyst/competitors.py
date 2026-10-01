"""Competitor price lists: a mock one for demos, or the presenter's own CSV.

AdventureWorks has no competitor data (that's a guardrail track). For demos, a price list can be
attached: it is saved as its own small SQLite file and attached read-only next to the sales database
(see data.connect), where the agent sees it as the competitor_prices table and the price_comparison view.

CSV columns: product, competitor, competitor_price (US $), observed_date (optional, YYYY-MM-DD).
Product names must match AdventureWorks names, e.g. "Road-150 Red, 62" (case and spaces don't matter).
"""
import io
import json
import os
import sqlite3
import time

import numpy as np
import pandas as pd

from . import data

MAX_UPLOAD_BYTES = 5_000_000
MAX_ROWS = 50_000
COLUMNS = ["product", "competitor", "competitor_price", "observed_date"]
ALIASES = {"product_name": "product", "name": "product", "price": "competitor_price",
           "competitor_price_usd": "competitor_price", "date": "observed_date"}

# Fictional shops. Price = our list price x a category factor x a little noise. Velo Direct
# undercuts our Road Bikes hard: that's the story a demo answer should find.
MOCK_COMPETITORS = {
    "Summit Cycles": {"default": 1.05, "noise": 0.04, "carries": 0.85},
    "Velo Direct":   {"default": 0.95, "Road Bikes": 0.82, "noise": 0.03, "carries": 0.75},
    "TrailCraft":    {"default": 1.00, "Mountain Bikes": 0.96, "Accessories": 1.10, "Clothing": 1.10,
                      "noise": 0.05, "carries": 0.70},
}
MOCK_LABEL = "MOCK demo data: 3 fictional competitors, prices generated from our list prices"


def _meta_path(name):
    return data.COMPETITOR_FILES[name].replace(".db", ".json")


def info(name):
    p = _meta_path(name)
    if os.path.exists(p) and os.path.exists(data.COMPETITOR_FILES[name]):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def status():
    return {"selected": data.selected_competitors(), "mock": info("mock"), "uploaded": info("uploaded"),
            "columns": COLUMNS}


def _products():
    with data.connect() as con:
        return pd.read_sql_query(
            "SELECT p.Name AS product, p.ListPrice AS list_price, MAX(s.category) AS category, "
            "MAX(s.subcategory) AS subcategory FROM Product p "
            "JOIN main.sales_lines s ON s.product = p.Name "
            f"WHERE s.order_date > date('{data.AW_END}', '-12 months') AND p.ListPrice > 0 "
            "GROUP BY p.Name, p.ListPrice ORDER BY p.Name", con)


def mock_prices(seed=7):
    """The mock price list as a DataFrame (also served as the downloadable CSV template)."""
    rng = np.random.default_rng(seed)
    rows = []
    for _, p in _products().iterrows():
        for name, prof in MOCK_COMPETITORS.items():
            if rng.random() > prof["carries"]:
                continue
            factor = prof.get(p.subcategory, prof.get(p.category, prof["default"]))
            price = p.list_price * factor * (1 + rng.normal(0, prof["noise"]))
            rows.append({"product": p["product"], "competitor": name,
                         "competitor_price": round(max(price, 0.99), 2), "observed_date": data.AW_END})
    return pd.DataFrame(rows, columns=COLUMNS)


def template_csv():
    return mock_prices().to_csv(index=False)


def _save(name, df, meta):
    path = data.COMPETITOR_FILES[name]
    tmp = path + ".building"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    df.to_sql("competitor_prices", con, index=False)
    con.commit()
    con.close()
    os.replace(tmp, path)
    meta = dict(meta, rows=int(len(df)), competitors=sorted(df["competitor"].unique().tolist()),
                products=int(df["product"].nunique()), loaded_at=time.strftime("%Y-%m-%d %H:%M"))
    with open(_meta_path(name), "w", encoding="utf-8") as f:
        json.dump(meta, f)
    return meta


def build_mock():
    """Create the mock list once (it's deterministic, so rebuilding gives the same prices)."""
    return info("mock") or _save("mock", mock_prices(), {"label": MOCK_LABEL, "mock": True, "unmatched": []})


def import_csv(raw, filename="competitor_prices.csv"):
    """Validate a CSV and save it as the "uploaded" list. Returns its info, or {"error": ...}."""
    if len(raw) > MAX_UPLOAD_BYTES:
        return {"error": f"File too large (max {MAX_UPLOAD_BYTES // 1_000_000} MB)."}
    try:
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except Exception as e:
        return {"error": f"Could not read the CSV: {e}"}
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns={k: v for k, v in ALIASES.items() if k in df.columns and v not in df.columns})
    missing = [c for c in COLUMNS[:3] if c not in df.columns]
    if missing:
        return {"error": f"Missing column(s): {', '.join(missing)}. Expected: {', '.join(COLUMNS)} "
                         "(observed_date is optional). Download the template to see the format."}
    if len(df) > MAX_ROWS:
        return {"error": f"Too many rows ({len(df):,}; max {MAX_ROWS:,})."}
    if "observed_date" not in df.columns:
        df["observed_date"] = ""
    df = df[COLUMNS].apply(lambda s: s.str.strip())
    df["competitor_price"] = pd.to_numeric(df["competitor_price"].str.replace(r"[$,\s]", "", regex=True), errors="coerce")
    bad = df["competitor_price"].isna() | (df["competitor_price"] <= 0) | (df["product"] == "") | (df["competitor"] == "")
    dates = pd.to_datetime(df["observed_date"].replace("", None), errors="coerce")
    df["observed_date"] = dates.dt.strftime("%Y-%m-%d").fillna("")
    # match names to AdventureWorks products, ignoring case and extra spaces
    with data.connect() as con:
        names = [n for (n,) in con.execute("SELECT Name FROM Product")]
    canon = {" ".join(n.lower().split()): n for n in names}
    df["product"] = df["product"].map(lambda n: canon.get(" ".join(n.lower().split()), n))
    unmatched = sorted(set(df.loc[~bad & ~df["product"].isin(names), "product"]))
    good = df[~bad]
    if good.empty:
        return {"error": "No usable rows: every row needs a product, a competitor and a price above 0."}
    if good["product"].isin(names).sum() == 0:
        return {"error": "None of the product names match AdventureWorks products (e.g. 'Road-150 Red, 62'). "
                         "Download the template to see the names."}
    return _save("uploaded", good, {"label": f"Your file: {os.path.basename(filename)}", "mock": False,
                                    "filename": os.path.basename(filename), "skipped_rows": int(bad.sum()),
                                    "unmatched": unmatched[:20], "unmatched_count": len(unmatched)})
