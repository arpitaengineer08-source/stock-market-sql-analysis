"""
Stock Market Analysis in SQL - one-click runner
------------------------------------------------
Run:  python run_project.py

What it does
  1. CLEANS the raw NSE CSVs (data/raw -> data/clean):
       - converts dates like '31-July-2018' to ISO '2018-07-31'
       - renames columns to snake_case (close_price, no_of_shares, ...)
       - sorts oldest -> newest, strips whitespace, drops duplicate dates
       - empty cells become real NULLs; a data-quality report is printed/saved
  2. LOADS the six tables into a SQLite database (stock_market.db)
  3. RUNS sql/sqlite/analysis_sqlite.sql (tasks 1-14) and saves every result
     as a CSV in outputs/results/
  4. CHECKS your numbers against the checkpoints in the student guide
  5. DRAWS charts into outputs/charts/
Only needs: pandas, matplotlib  (pip install -r requirements.txt)
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
RESULTS, CHARTS = ROOT / "outputs" / "results", ROOT / "outputs" / "charts"
DB = ROOT / "stock_market.db"
SQL_FILE = ROOT / "sql" / "sqlite" / "analysis_sqlite.sql"

TABLES = {  # raw csv name -> table name
    "Bajaj_Auto.csv": "bajaj_auto",
    "Eicher_Motors.csv": "eicher_motors",
    "Hero_Motocorp.csv": "hero_motocorp",
    "Infosys.csv": "infosys",
    "TCS.csv": "tcs",
    "TVS_Motors.csv": "tvs_motors",
}
COLS = ["date", "open_price", "high_price", "low_price", "close_price", "wap",
        "no_of_shares", "no_of_trades", "total_turnover", "deliverable_qty",
        "pct_deli_qty", "spread_high_low", "spread_close_open"]


# ------------------------------------------------------------------ 1. clean
def clean_all():
    CLEAN.mkdir(parents=True, exist_ok=True)
    report = []
    for fname, table in TABLES.items():
        df = pd.read_csv(RAW / fname, skipinitialspace=True)
        df.columns = COLS  # same 13 columns, same order in every file
        raw_rows = len(df)
        df["date"] = pd.to_datetime(df["date"].astype(str).str.strip(), format="%d-%B-%Y")
        dups = int(df.duplicated("date").sum())
        df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
        for c in COLS[1:]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        for c in ("no_of_shares", "no_of_trades", "deliverable_qty"):
            df[c] = df[c].round().astype("Int64")  # whole numbers, NULL stays empty (MySQL BIGINT-safe)
        nulls = df.isna().sum()
        nulls = nulls[nulls > 0]
        bad_price = int((df[["open_price", "high_price", "low_price", "close_price"]] <= 0).any(axis=1).sum())
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")
        df.to_csv(CLEAN / f"{table}.csv", index=False)
        report.append({
            "table": table, "rows_raw": raw_rows, "rows_clean": len(df),
            "duplicate_dates": dups, "first_date": df["date"].iloc[0], "last_date": df["date"].iloc[-1],
            "null_cells": "; ".join(f"{k}={v}" for k, v in nulls.items()) or "none",
            "rows_with_nonpositive_price": bad_price,
        })
    rep = pd.DataFrame(report)
    rep.to_csv(RESULTS / "00_data_quality_report.csv", index=False)
    print("\n=== DATA QUALITY REPORT ===")
    print(rep.to_string(index=False))
    return rep


# --------------------------------------------------------------------- 2. load
def load_db():
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    for table in TABLES.values():
        pd.read_csv(CLEAN / f"{table}.csv").to_sql(table, con, index=False)
        con.execute(f"CREATE UNIQUE INDEX idx_{table}_date ON {table}(date)")
    con.commit()
    return con


# ------------------------------------------------------------------ 3. run SQL
def run_sql(con):
    text = SQL_FILE.read_text(encoding="utf-8")
    blocks = re.split(r"^-- (TASK [^\n]+)$", text, flags=re.M)
    out = {}
    for i in range(1, len(blocks), 2):
        title, body = blocks[i], blocks[i + 1]
        stmts, buf = [], ""
        for line in body.splitlines(keepends=True):
            if line.strip().startswith("--"):
                continue
            buf += line
            if sqlite3.complete_statement(buf):
                stmts.append(buf.strip())
                buf = ""
        last = None
        for s in stmts:
            cur = con.execute(s)
            if s.lstrip().upper().startswith(("SELECT", "WITH")):
                cols = [d[0] for d in cur.description]
                last = pd.DataFrame(cur.fetchall(), columns=cols)
        if last is not None:
            slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
            last.to_csv(RESULTS / f"{slug}.csv", index=False)
            out[title] = last
            print(f"\n--- {title} ({len(last)} rows) ---")
            print(last.head(8).to_string(index=False))
    con.commit()
    return out


# ------------------------------------------------------------- 4. checkpoints
def checkpoints(con, res):
    def q(sql):
        return con.execute(sql).fetchall()

    r10 = res["TASK 10: All six stocks in one query (buys, sells, last signal)"]
    tests = [
        ("T1  889 trading days, 2015-01-01 .. 2018-07-31", q("SELECT COUNT(*),MIN(date),MAX(date) FROM bajaj_auto") == [(889, "2015-01-01", "2018-07-31")]),
        ("T2  Eicher top close > 32000", q("SELECT MAX(close_price) FROM eicher_motors")[0][0] > 32000),
        ("T3  TCS 2016 avg = 2419.00", q("SELECT ROUND(AVG(close_price),2) FROM tcs WHERE date LIKE '2016%'")[0][0] == 2419.00),
        ("T4  six NULL rows, two distinct dates", (len(res["TASK 04: Find the holes (deliverable_qty IS NULL in any table)"]) == 6
                                                   and res["TASK 04: Find the holes (deliverable_qty IS NULL in any table)"]["date"].nunique() == 2)),
        ("T5  bajaj1 889 rows; first ma20 2015-01-29 = 2415.53", q("SELECT date,ma20 FROM bajaj1 WHERE ma20 IS NOT NULL ORDER BY date LIMIT 1") == [("2015-01-29", 2415.53)]),
        ("T5  first ma50 2015-03-13 = 2283.80", q("SELECT date,ma50 FROM bajaj1 WHERE ma50 IS NOT NULL ORDER BY date LIMIT 1") == [("2015-03-13", 2283.80)]),
        ("T5  ma20 on 2018-07-31 = 2918.51", q("SELECT ma20 FROM bajaj1 WHERE date='2018-07-31'") == [(2918.51,)]),
        ("T6  master_table 889 rows, 7 cols, bajaj 2700.70 / tvs 517.45", q("SELECT COUNT(*) FROM master_table") == [(889,)] and q("SELECT bajaj,tvs FROM master_table WHERE date='2018-07-31'") == [(2700.70, 517.45)]),
        ("T7  first Buy 2015-05-18, first Sell 2015-08-24", q("SELECT MIN(date) FROM bajaj2 WHERE signal='Buy'") == [("2015-05-18",)] and q("SELECT MIN(date) FROM bajaj2 WHERE signal='Sell'") == [("2015-08-24",)]),
        ("T8  counts add up to 889, |Buy-Sell| <= 1", (lambda d: sum(d.values()) == 889 and abs(d["Buy"] - d["Sell"]) <= 1)(dict(q("SELECT signal,COUNT(*) FROM bajaj2 GROUP BY signal")))),
        ("T9  2015-05-18 -> Buy, 2016-01-04 -> Hold", q("SELECT signal FROM bajaj2 WHERE date='2015-05-18'") == [("Buy",)] and q("SELECT signal FROM bajaj2 WHERE date='2016-01-04'") == [("Hold",)]),
        ("T10 totals: 56 Buys, 57 Sells", (int(r10["buys"].sum()), int(r10["sells"].sum())) == (56, 57)),
        ("T11 TVS tops list at 86.9%", (lambda r: r.iloc[0]["stock"] == "TVS Motors" and r.iloc[0]["pct_change"] == 86.9)(res["TASK 11: Who went up? (first vs last close, raw prices)"])),
    ]
    print("\n=== CHECKPOINTS (from the student guide) ===")
    ok = 0
    for name, passed in tests:
        ok += bool(passed)
        print(("PASS  " if passed else "FAIL  ") + name)
    print(f"\n{ok}/{len(tests)} checkpoints passed")
    pd.DataFrame([(n, "PASS" if p else "FAIL") for n, p in tests], columns=["checkpoint", "status"]).to_csv(
        RESULTS / "99_checkpoints.csv", index=False)


# ---------------------------------------------------------------- 5. charts
def charts(con):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    CHARTS.mkdir(parents=True, exist_ok=True)
    rd = lambda s: pd.read_sql(s, con, parse_dates=["date"])

    # 1. Bajaj price + MAs + signals
    b = rd("SELECT b1.date,b1.close_price,b1.ma20,b1.ma50,b2.signal FROM bajaj1 b1 JOIN bajaj2 b2 USING(date) ORDER BY date")
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.plot(b.date, b.close_price, color="#9aa5b1", lw=1, label="Close")
    ax.plot(b.date, b.ma20, color="#1f77b4", lw=1.6, label="20-day MA")
    ax.plot(b.date, b.ma50, color="#ff7f0e", lw=1.6, label="50-day MA")
    buy, sell = b[b.signal == "Buy"], b[b.signal == "Sell"]
    ax.scatter(buy.date, buy.close_price, marker="^", s=70, color="green", label="Buy", zorder=5)
    ax.scatter(sell.date, sell.close_price, marker="v", s=70, color="red", label="Sell", zorder=5)
    ax.set_title("Bajaj Auto - close, 20/50-day moving averages and golden-cross signals")
    ax.set_ylabel("Rupees"); ax.legend(); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(CHARTS / "01_bajaj_signals.png", dpi=140); plt.close(fig)

    # 2. All stocks rebased to 100 (RAW) - TCS and Infosys show the cliff
    m = rd("SELECT * FROM master_table ORDER BY date").set_index("date")
    reb = m / m.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(13, 5.5))
    reb.plot(ax=ax, lw=1.3)
    ax.set_title("Master table, RAW prices rebased to 100 (note the TCS and Infosys cliffs)")
    ax.set_ylabel("Index (start = 100)"); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(CHARTS / "02_master_rebased_raw.png", dpi=140); plt.close(fig)

    # 3. Raw vs adjusted for TCS and Infosys
    a = rd("SELECT * FROM adjusted_prices ORDER BY stock,date")
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
    for ax, s in zip(axes, ["TCS", "Infosys"]):
        d = a[a.stock == s]
        ax.plot(d.date, d.close_price, color="#d62728", lw=1.2, label="Raw close")
        ax.plot(d.date, d.adj_close, color="#2ca02c", lw=1.6, label="Adjusted close")
        ax.set_title(f"{s}: raw vs bonus-adjusted"); ax.legend(); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(CHARTS / "03_tcs_infosys_adjusted.png", dpi=140); plt.close(fig)

    # 4. % change raw vs adjusted
    raw = pd.read_sql("""SELECT stock, ROUND(100.0*(MAX(CASE WHEN date='2018-07-31' THEN close_price END)/
                         MAX(CASE WHEN date='2015-01-01' THEN close_price END)-1),1) AS pct
                         FROM adjusted_prices GROUP BY stock""", con).set_index("stock")["pct"]
    adj = pd.read_sql("""SELECT stock, ROUND(100.0*(MAX(CASE WHEN date='2018-07-31' THEN adj_close END)/
                         MAX(CASE WHEN date='2015-01-01' THEN adj_close END)-1),1) AS pct
                         FROM adjusted_prices GROUP BY stock""", con).set_index("stock")["pct"]
    cmp_ = pd.DataFrame({"Raw %": raw, "Adjusted %": adj})
    ax = cmp_.plot.bar(figsize=(7, 4.5), color=["#d62728", "#2ca02c"], rot=0)
    ax.set_title("TCS & Infosys: first-to-last % change, raw vs adjusted"); ax.grid(axis="y", alpha=.25)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.1f")
    plt.tight_layout(); plt.savefig(CHARTS / "04_pct_change_raw_vs_adjusted.png", dpi=140); plt.close()

    # 5. Buy/Sell counts per stock
    r = pd.read_csv(RESULTS / "task_10_all_six_stocks_in_one_query_buys_sells_last_signal.csv").set_index("stock")
    ax = r[["buys", "sells"]].plot.bar(figsize=(9, 4.5), color=["green", "red"], rot=20)
    ax.set_title("Golden-cross Buy / Sell signals per stock (raw prices)"); ax.grid(axis="y", alpha=.25)
    plt.tight_layout(); plt.savefig(CHARTS / "05_signals_per_stock.png", dpi=140); plt.close()
    print(f"\nCharts saved in {CHARTS}")


def main():
    for d in (RESULTS, CHARTS):
        d.mkdir(parents=True, exist_ok=True)
    clean_all()
    con = load_db()
    res = run_sql(con)
    checkpoints(con, res)
    charts(con)
    con.close()
    print(f"\nDone. Database: {DB.name} | results: outputs/results | charts: outputs/charts")


if __name__ == "__main__":
    main()
