"""AdventureWorks as a local, read-only SQLite database (same logic as notebook Section 6A)."""
import io
import os
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
_current = {"name": "real"}

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


def connect():
    """Open the current database READ-ONLY: any attempt to change data fails at the database level."""
    return sqlite3.connect(f"file:{DB_FILES[_current['name']]}?mode=ro", uri=True, check_same_thread=False)


build("real")
with connect() as _con:
    AW_START, AW_END = _con.execute("SELECT min(order_date), max(order_date) FROM sales_lines").fetchone()
