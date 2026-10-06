"""Builds insights/Insights_Report.pdf from stock_market.db and outputs/.
Run AFTER run_project.py:   python make_insights_pdf.py
Round-trip statistics (buy at each Buy close, sell at the next Sell close) are a
simple supplementary calculation done here in pandas; every signal itself comes
from the SQL files."""
import sqlite3
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).parent
DB = sqlite3.connect(ROOT / "stock_market.db")
CH = ROOT / "outputs" / "charts"
OUT = ROOT / "insights" / "Insights_Report.pdf"

NAMES = {"Bajaj Auto": "bajaj_auto", "Eicher Motors": "eicher_motors", "Hero Motocorp": "hero_motocorp",
         "Infosys": "infosys", "TCS": "tcs", "TVS Motors": "tvs_motors"}
EVENTS = {"TCS": "2018-05-31", "Infosys": "2015-06-15"}  # 1:1 bonus, first ex-bonus trading day


def stock_stats(name, table):
    d = pd.read_sql(f"SELECT date, close_price p FROM {table} ORDER BY date", DB)
    raw_chg = (d.p.iloc[-1] / d.p.iloc[0] - 1) * 100
    if name in EVENTS:
        d.loc[d.date < EVENTS[name], "p"] /= 2
    adj_chg = (d.p.iloc[-1] / d.p.iloc[0] - 1) * 100
    d["ma20"], d["ma50"] = d.p.rolling(20).mean(), d.p.rolling(50).mean()
    d["pm20"], d["pm50"] = d.ma20.shift(), d.ma50.shift()
    ok = d[["ma20", "ma50", "pm20", "pm50"]].notna().all(axis=1)
    d["sig"] = "Hold"
    d.loc[ok & (d.ma20 > d.ma50) & (d.pm20 <= d.pm50), "sig"] = "Buy"
    d.loc[ok & (d.ma20 < d.ma50) & (d.pm20 >= d.pm50), "sig"] = "Sell"
    s = d[d.sig != "Hold"].reset_index(drop=True)
    trips, pos = [], None
    for _, r in s.iterrows():
        if r.sig == "Buy" and pos is None:
            pos = r
        elif r.sig == "Sell" and pos is not None:
            trips.append((r.p / pos.p - 1) * 100)
            pos = None
    t = pd.Series(trips)
    gaps = pd.to_datetime(s.date).diff().dt.days
    return dict(stock=name, raw=raw_chg, adj=adj_chg, buys=int((s.sig == "Buy").sum()), sells=int((s.sig == "Sell").sum()),
                last=f"{s.sig.iloc[-1]} ({s.date.iloc[-1]})", trips=len(t), win=(t > 0).mean() * 100,
                avg=t.mean(), comp=((1 + t / 100).prod() - 1) * 100, fast=int((gaps <= 21).sum()),
                vs50=(d.p.iloc[-1] / d.ma50.iloc[-1] - 1) * 100)


S = pd.DataFrame([stock_stats(n, t) for n, t in NAMES.items()]).set_index("stock")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=17, spaceAfter=6, textColor=colors.HexColor("#14213d"))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#14213d"))
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9.4, leading=13)
SM = ParagraphStyle("SM", parent=B, fontSize=8, leading=10.5, textColor=colors.HexColor("#555555"))


def P(t, st=B):
    return Paragraph(t, st)


def table(data, widths, hdr=True):
    t = Table(data, colWidths=widths, repeatRows=1 if hdr else 0)
    st = [("FONTSIZE", (0, 0), (-1, -1), 8.3), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#c8ced6")),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")])]
    if hdr:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14213d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(st))
    return t


def claim(c, e, cav):
    return [P(f"<b>Claim:</b> {c}"), P(f"<b>Evidence:</b> {e}"), P(f"<b>Caveat:</b> {cav}"), Spacer(1, 5)]


f = lambda x, n=1: f"{x:+.{n}f}%"
st = []
st += [P("Stock Market Analysis in SQL - Insights", H1),
       P("Six NSE stocks (Bajaj Auto, Eicher Motors, Hero Motocorp, Infosys, TCS, TVS Motors), 889 trading days, "
         "1 Jan 2015 - 31 Jul 2018. Strategy studied: 20-day / 50-day moving-average 'golden cross' (Buy when MA20 crosses above MA50, "
         "Sell when it crosses below). All numbers below come from the SQL files in this project; the checkpoints from the student guide all pass "
         "(see outputs/results/99_checkpoints.csv).", B),
       P("1. Data cleaning and the two price events", H2),
       P("<b>Cleaning:</b> dates converted from '31-July-2018' to ISO dates, columns renamed to snake_case, rows sorted oldest-first, no duplicate dates, "
         "6 tables x 889 rows with identical dates (so the master-table join loses nothing). Only gap: <i>deliverable_qty</i> and <i>pct_deli_qty</i> are blank on "
         "<b>2015-12-09</b> (Eicher, Hero, TCS, TVS) and <b>2017-08-31</b> (Bajaj, Infosys) - the same two dates across several unrelated companies points to the "
         "exchange's reporting, not the companies. Blanks were kept as NULL (never as 0); close prices are complete.", B),
       P("<b>Price event 1 - TCS, 2018-05-31:</b> close falls 50.4% in one day (from 3,517.75 to 1,744.80). <b>Price event 2 - Infosys, 2015-06-15:</b> "
         "-49.9% in one day (to 991.10). Both are 1:1 bonus issues (shares double, price halves, no value lost), not crashes. "
         "I divided every close <i>before</i> the event date by 2 (task 13) and re-ran the analysis on adjusted prices. No other stock has a one-day move worse than -9.7%.", B),
       Spacer(1, 4)]

# summary table
rows = [["Stock", "Raw %", "Adj. %", "Buys", "Sells", "Last signal (adj.)", "Win rate*", "Avg trade*", "vs MA50"]]
for n, r in S.iterrows():
    rows.append([n, f(r.raw), f(r.adj), r.buys, r.sells, r.last, f"{r.win:.0f}%", f(r.avg), f(r.vs50)])
st += [P("2. Results at a glance", H2),
       table(rows, [2.4 * cm, 1.4 * cm, 1.4 * cm, 1.0 * cm, 1.0 * cm, 3.4 * cm, 1.7 * cm, 1.9 * cm, 1.6 * cm]),
       P("*Win rate / average trade: buy at each Buy-day close, sell at the next Sell-day close, ignoring costs and dividends. "
         "'vs MA50' = last close relative to its 50-day average. 'Raw %' is the first-to-last close change on unadjusted prices (task 11); 'Adj. %' uses bonus-adjusted prices (task 13; only TCS and Infosys differ). "
         "Signal counts for TCS/Infosys here are on adjusted prices; on raw prices the totals are 56 Buys and 57 Sells across all six stocks (task 10).", SM),
       Spacer(1, 6), Image(str(CH / "01_bajaj_signals.png"), width=17 * cm, height=7.2 * cm),
       P("Figure 1: Bajaj Auto with 20/50-day averages; triangles are the golden-cross signals from task 7.", SM),
       PageBreak()]

st += [P("3. Per-stock findings (claim - evidence - caveat)", H2)]
r = S.loc
st += claim(f"TVS Motors and Eicher Motors were the clear winners ({f(r['TVS Motors'].adj)} and {f(r['Eicher Motors'].adj)}), and the moving-average rule captured most of it.",
            f"Task 11/13 first-to-last closes; Eicher produced {r['Eicher Motors'].buys} Buys / {r['Eicher Motors'].sells} Sells with {r['Eicher Motors'].win:.0f}% of round trips profitable "
            f"(compounded {f(r['Eicher Motors'].comp, 0)}); TVS compounded {f(r['TVS Motors'].comp, 0)}.",
            "Only 6-8 round trips each, so a few big trends drive the result. A buy-and-hold investor would have done about as well without any signals. Both end with a Sell signal "
            "(Eicher 2018-06-06, TVS 2018-05-17) and TVS closes 9.3% below its 50-day average, but both are still far above their 2015 levels.")
st += claim(f"TCS and Infosys went from 'losers' to 'winners' once the bonus issues were handled: TCS {f(r['TCS'].raw)} raw vs {f(r['TCS'].adj)} adjusted; "
            f"Infosys {f(r['Infosys'].raw)} raw vs {f(r['Infosys'].adj)} adjusted.",
            "Task 11 versus task 13 (outputs/results). Task 12 shows the -50.4% (TCS) and -49.9% (Infosys) single-day moves; Figure 3 shows the cliff removed.",
            "Adjustment assumes exactly 1:1 bonus ratios and ignores dividends, so true total return is somewhat higher.")
st += claim("Bajaj Auto and Hero Motocorp were roughly flat, and the crossover strategy lost money on Hero.",
            f"Bajaj {f(r['Bajaj Auto'].adj)}, Hero {f(r['Hero Motocorp'].adj)} over the full period. Hero: {r['Hero Motocorp'].win:.0f}% win rate, compounded {f(r['Hero Motocorp'].comp, 0)}; "
            f"Bajaj: {r['Bajaj Auto'].win:.0f}% win rate, compounded {f(r['Bajaj Auto'].comp, 0)}.",
            "Sideways markets are exactly where moving-average crossovers whipsaw, so this is a property of the period as much as of the stocks.")
st += claim("There were clusters of rapid Buy/Sell flips (whipsaws), mainly in Bajaj Auto.",
            f"Bajaj had {r['Bajaj Auto'].fast} signals within 21 days of the previous one. Example: Buy 2015-12-28, Sell 2016-01-18 (-9.6%), and Buy 2018-02-01, Sell 2018-02-06 (-8.0%).",
            "Round-trip losses ignore brokerage and taxes, which would make frequent flipping even more expensive.")
st += claim("The latest signal does not always match the long-run trend.",
            f"Bajaj's last signal is Buy (2018-06-21) while its last close is {f(r['Bajaj Auto'].vs50)} below its 50-day average; Infosys and TCS (adjusted) both end on Buy and sit above their 50-day averages. "
            "On raw prices TCS shows a false Sell on 2018-06-05, created purely by the bonus cliff (task 14: 1 TCS signal removed by adjustment); "
            "Infosys has 4 changed signals (1 removed, 3 created) around the 2015 cliff.",
            "I would trust the long-run trend and the adjusted series over a single recent crossover: crossings lag the price, and one signal carries little information.")
st += [Spacer(1, 4), Image(str(CH / "03_tcs_infosys_adjusted.png"), width=17 * cm, height=5.8 * cm),
       P("Figure 3: raw vs bonus-adjusted close for TCS and Infosys (red = raw, green = adjusted).", SM),
       PageBreak()]

st += [P("4. Questions about the method", H2)]
st += claim("A golden cross is a lagging signal: it can only confirm a trend that has already moved.",
            "The 50-day average needs 50 trading days of history, so the first Bajaj signal was possible only after 2015-03-13; the first actual Buy was 2015-05-18. "
            "In every stock the average is made of past prices only.",
            "By the time MA20 crosses MA50 a good part of the move has usually happened; the table above shows modest or negative average trades for four of six stocks.")
st += claim("Several conclusions in the course deck change after fixing the price events.",
            "Deck: Infosys '3% decrease' - correct figures are -30.9% raw and +38.2% adjusted. Deck: TCS '23.8% decrease' - raw is correct (-23.8%) but adjusted is +52.4%, "
            "and its 'sell' call reverses (adjusted last signal is Buy, 2018-04-20). Deck TCS first close '2454.1' is Bajaj's price (TCS actually 2548.20). "
            "Eicher '82.5%' is 82.6% when rounded. Buy/Sell counts for Bajaj (12/11), Eicher (6/7), Hero (9/9), Infosys (9/9), TCS (12/13), TVS (8/8) match the raw-price results.",
            "The deck's final 'buy Bajaj and Infosys; sell Eicher, TVS, Hero, TCS' list should not be used as is: it mixes unadjusted TCS/Infosys prices with signals,.")
st += claim("This data is not enough for a real investment decision.",
            "The tables contain only daily prices and volumes for six stocks.",
            "Missing: dividends, news and earnings, brokerage/tax costs, slippage, risk measures (volatility, drawdown), comparison with the Nifty index, and any test on data outside 2015-2018.")
st += [Spacer(1, 4), Image(str(CH / "02_master_rebased_raw.png"), width=16.5 * cm, height=7 * cm),
       P("Figure 2: master table, raw closes rebased to 100 - the TCS and Infosys cliffs are visible as vertical drops.", SM)]

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                        title="Stock Market Analysis in SQL - Insights")
doc.build(st)
print("Written", OUT)
