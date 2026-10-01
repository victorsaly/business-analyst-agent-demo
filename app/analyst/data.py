"""AdventureWorks as a local, read-only SQLite database (same logic as notebook Section 6A)."""
import io
import os
import pathlib
import re
import sqlite3
import urllib.request
import zipfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
os.makedirs(DATA_DIR, exist_ok=True)

AW_URL = ("https://github.com/Microsoft/sql-server-samples/releases/download/"
          "adventureworks/AdventureWorks-oltp-install-script.zip")
AW_ZIP_LOCAL = os.path.join(DATA_DIR, "AdventureWorks-oltp-install-script.zip")
AW_TABLES = ["SalesOrderHeader", "SalesOrderDetail", "Product", "ProductSubcategory",
             "ProductCategory", "SalesTerritory", "Customer"]

# Rehearsal only: a fake problem to practise the "explain the anomaly" demo. Saved as a separate file.
AW_PLANT = {"territory": "Northwest", "month": "2024-05", "category": "Bikes", "extra_discount": 0.25}

DB_FILES = {"real": os.path.join(DATA_DIR, "adventureworks.db"),
            "planted": os.path.join(DATA_DIR, "adventureworks_planted.db")}
_current = {"name": "real", "competitors": None, "selected": None}

# Optional competitor price list, kept in its own small SQLite file and ATTACHed read-only, so the
# AdventureWorks database is never touched. "mock" = fictional demo data; "uploaded" = the user's CSV.
COMPETITOR_FILES = {"mock": os.path.join(DATA_DIR, "competitor_prices_mock.db"),
                    "uploaded": os.path.join(DATA_DIR, "competitor_prices_uploaded.db")}

# Our price for each product next to every competitor price. gap_pct > 0 means we are dearer.
# Online price only: Reseller lines are wholesale prices to bike shops, not comparable with a shop's shelf price.
PRICE_VIEW_SQL = """
CREATE TEMP VIEW price_comparison AS
WITH ours AS (
    SELECT product, MAX(category) AS category, MAX(subcategory) AS subcategory,
           SUM(CASE WHEN channel = 'Online' THEN revenue END)
             / SUM(CASE WHEN channel = 'Online' THEN qty END) AS online_price,
           SUM(qty) AS units
    FROM main.sales_lines
    WHERE order_date > date((SELECT max(order_date) FROM main.sales_lines), '-12 months')
    GROUP BY product)
SELECT c.product, COALESCE(o.category, '(not sold in last 12 months)') AS category, o.subcategory,
       ROUND(p.ListPrice, 2)                                                AS our_list_price,
       ROUND(o.online_price, 2)                                             AS our_online_price,
       COALESCE(o.units, 0)                                                 AS our_units_12m,
       c.competitor, c.competitor_price, c.observed_date,
       ROUND(100.0 * (p.ListPrice - c.competitor_price) / c.competitor_price, 1)   AS list_gap_pct,
       ROUND(100.0 * (o.online_price - c.competitor_price) / c.competitor_price, 1) AS online_gap_pct
FROM comp.competitor_prices c
JOIN main.Product p ON p.Name = c.product
LEFT JOIN ours o    ON o.product = c.product
"""

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


def _zip_bytes():
    if not os.path.exists(AW_ZIP_LOCAL):
        print("Downloading AdventureWorks (about 17 MB)...")
        with open(AW_ZIP_LOCAL, "wb") as f:
            f.write(urllib.request.urlopen(AW_URL, timeout=120).read())
    with open(AW_ZIP_LOCAL, "rb") as f:
        return f.read()


def build(name="real"):
    """Build the SQLite file from Microsoft's CSVs (only if it doesn't exist yet)."""
    path = DB_FILES[name]
    if os.path.exists(path):
        return path
    tmp = path + ".building"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    with zipfile.ZipFile(io.BytesIO(_zip_bytes())) as z:
        names = {n.split("/")[-1]: n for n in z.namelist()}
        ddl = z.read(names["instawdb.sql"]).decode("utf-8-sig", errors="ignore")
        for table in AW_TABLES:
            block = re.search(r"CREATE TABLE \[\w+\]\.\[" + table + r"\]\((.*?)\n\)", ddl, re.S).group(1)
            cols = re.findall(r"^\s{4}\[(\w+)\]", block, re.M)
            df = pd.read_csv(z.open(names[f"{table}.csv"]), sep="\t", header=None, names=cols,
                             quoting=3, dtype=str, keep_default_na=False, encoding="utf-8")
            df = df.replace("", None)
            for c in df.columns:
                as_num = pd.to_numeric(df[c], errors="coerce")
                if df[c].notna().any() and as_num.notna().sum() == df[c].notna().sum():
                    df[c] = as_num
            df.to_sql(table, con, index=False)
    con.execute(AW_VIEW_SQL)
    if name == "planted":
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
    con.commit()
    con.close()
    os.replace(tmp, path)
    return path


def use(name):
    """Switch between the real database and the rehearsal copy with a planted anomaly."""
    build(name)
    _current["name"] = name


def current():
    return _current["name"]


def use_competitors(name):
    """Which competitor price list the agent can see right now: None, "mock" or "uploaded"."""
    if name is not None and not os.path.exists(COMPETITOR_FILES[name]):
        raise LookupError(f"No {name} competitor price list yet.")
    _current["competitors"] = name


def competitors():
    return _current["competitors"]


def select_competitors(name):
    """The presenter's choice (Tools screen). Demo tracks may override it for the length of a run."""
    use_competitors(name)
    _current["selected"] = name


def selected_competitors():
    return _current["selected"]


def _read_only(path):
    """A read-only SQLite URI that works on Windows paths (C:\\...) and paths with spaces, as well as on macOS."""
    return pathlib.Path(path).resolve().as_uri() + "?mode=ro"


def connect():
    """Open the current database READ-ONLY: any attempt to change data fails at the database level.
    A competitor price list, when one is switched on, is attached read-only as well."""
    con = sqlite3.connect(_read_only(DB_FILES[_current['name']]), uri=True, check_same_thread=False)
    comp = _current["competitors"]
    if comp:
        con.execute("ATTACH DATABASE ? AS comp", (_read_only(COMPETITOR_FILES[comp]),))
        con.execute(PRICE_VIEW_SQL)
    return con


build("real")
with connect() as _con:
    AW_START, AW_END = _con.execute("SELECT min(order_date), max(order_date) FROM sales_lines").fetchone()
