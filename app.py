"""
Golden Cross - interactive dashboard for the "Stock Market Analysis in SQL" project.
Run locally:   streamlit run app.py
Deploy:        Streamlit Community Cloud -> main file path: app.py

Reads data/clean/*.csv (committed in the repo) and sql/sqlite/analysis_sqlite.sql.
Signals are computed with the same rules as the SQL (20/50-day averages, crossover = a change
between yesterday and today, NULL guard on the first 49 days).
"""
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
CLEAN = ROOT / "data" / "clean"
SQL_FILE = ROOT / "sql" / "sqlite" / "analysis_sqlite.sql"

STOCKS = {"Bajaj Auto": "bajaj_auto", "Eicher Motors": "eicher_motors", "Hero Motocorp": "hero_motocorp",
          "Infosys": "infosys", "TCS": "tcs", "TVS Motors": "tvs_motors"}
EVENTS = {"TCS": "2018-05-31", "Infosys": "2015-06-15"}  # 1:1 bonus issues, first ex-bonus trading day

INK, PANEL, LINE = "#0C1424", "#131E34", "#26354F"
FAST, SLOW, PRICE = "#6CB6FF", "#F2B84B", "#7F8FA9"
BUY, SELL, TEXT, MUTED = "#2EC4A6", "#FF6B6B", "#E6ECF5", "#8FA0BA"
PALETTE = ["#6CB6FF", "#F2B84B", "#2EC4A6", "#FF6B6B", "#B79CFF", "#FF9F68"]

st.set_page_config(page_title="Golden Cross | NSE stocks in SQL", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")

# ----------------------------------------------------------------------------- styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap');
html, body, .stMarkdown, .stMarkdown p, label, button, input, textarea, [data-testid="stMetric"], [data-testid="stCaptionContainer"] { font-family: 'IBM Plex Sans', Arial, sans-serif; }
[data-testid="stIconMaterial"], .material-icons, .material-symbols-rounded { font-family: 'Material Symbols Rounded' !important; }
.stApp { background:
   radial-gradient(1100px 520px at 12% -10%, rgba(108,182,255,.16), transparent 60%),
   radial-gradient(900px 480px at 100% 0%, rgba(242,184,75,.10), transparent 55%), #0C1424; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.2rem; max-width: 1280px; }
section[data-testid="stSidebar"] { background: #0F1A2E; border-right: 1px solid #1E2C45; }

/* hero */
.hero { display:grid; grid-template-columns: 1.1fr .9fr; gap: 28px; align-items:center;
  padding: 34px 38px; border-radius: 22px; border: 1px solid #22314C; position: relative; overflow: hidden;
  background: linear-gradient(135deg, rgba(19,30,52,.95), rgba(12,20,36,.9)); }
.hero::before { content:""; position:absolute; inset:-60%;
  background: conic-gradient(from 0deg, transparent 0 70%, rgba(108,182,255,.09) 80%, transparent 90%);
  animation: sweep 14s linear infinite; }
.hero > * { position: relative; z-index: 1; }
.hero h1 { font-family:'Sora',Arial,sans-serif; font-weight:800; font-size: 2.65rem; line-height:1.08;
  letter-spacing:-.02em; margin:0 0 14px; color:#F2F6FC; }
.hero h1 .fast { color:#6CB6FF; } .hero h1 .slow { color:#F2B84B; }
.hero p { color:#9FB0C9; font-size:1.02rem; line-height:1.6; max-width: 34rem; margin:0; }
.hero svg { width:100%; height:auto; display:block; }
.ln { fill:none; stroke-width:3.2; stroke-linecap:round; stroke-dasharray: 900; stroke-dashoffset: 900;
  animation: draw 2.6s cubic-bezier(.65,0,.35,1) forwards; }
.ln.slow { stroke:#F2B84B; } .ln.fast { stroke:#6CB6FF; animation-delay:.5s; filter: drop-shadow(0 0 6px rgba(108,182,255,.7)); }
.ghost { fill:none; stroke:#2A3B58; stroke-width:1.4; stroke-dasharray: 3 7; }
.pulse { fill:#2EC4A6; opacity:0; animation: pop .5s ease-out 2.9s forwards; }
.ring { fill:none; stroke:#2EC4A6; stroke-width:2; opacity:0; transform-box: fill-box; transform-origin:center;
  animation: ring 2.4s ease-out 3.1s infinite; }
.tag { opacity:0; animation: pop .6s ease-out 3.2s forwards; font: 600 13px 'IBM Plex Sans'; fill:#2EC4A6; }
@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes pop { to { opacity:1; } }
@keyframes ring { 0% { opacity:.9; transform:scale(.6);} 100% { opacity:0; transform:scale(3.4);} }
@keyframes sweep { to { transform: rotate(360deg); } }

/* KPI strip */
.kpis { display:grid; grid-template-columns: repeat(5, 1fr); gap:14px; margin: 18px 0 8px; }
.kpi { background: linear-gradient(180deg, #152239, #111C30); border:1px solid #22314C; border-radius:14px;
  padding:16px 18px; transition: border-color .25s, transform .25s, box-shadow .25s; }
.kpi:hover { border-color:#4C6A98; transform: translateY(-3px); box-shadow: 0 10px 30px rgba(0,0,0,.35); }
.kpi .lab { color:#8FA0BA; font-size:.82rem; margin-bottom:6px; }
.kpi .val { font-family:'IBM Plex Mono',monospace; font-weight:500; font-size:1.55rem; color:#F2F6FC; }
.kpi .sub { color:#8FA0BA; font-size:.78rem; margin-top:4px; }
.up { color:#2EC4A6 !important; } .down { color:#FF6B6B !important; }
.chip { display:inline-block; padding:2px 10px; border-radius:99px; font-size:.8rem; font-weight:600; }
.chip.buy { background:rgba(46,196,166,.15); color:#2EC4A6; } .chip.sell { background:rgba(255,107,107,.15); color:#FF6B6B; }

/* callouts */
.note { border-left:3px solid #F2B84B; background: rgba(242,184,75,.07); padding:14px 18px; border-radius:0 12px 12px 0;
  color:#D9E2F0; line-height:1.6; margin: 6px 0 14px; }
.note.good { border-color:#2EC4A6; background: rgba(46,196,166,.07); }
.h2 { font-family:'Sora',Arial,sans-serif; font-weight:700; font-size:1.35rem; color:#F2F6FC; margin: 6px 0 2px; }
.sub2 { color:#8FA0BA; margin-bottom: 10px; }

/* tabs */
button[data-baseweb="tab"] { font-family:'Sora',Arial,sans-serif; font-weight:700; }
div[data-testid="stTabs"] [aria-selected="true"] { color:#6CB6FF; }
.foot { color:#6F819E; font-size:.82rem; text-align:center; margin-top:30px; padding-top:16px; border-top:1px solid #1E2C45; }

@media (max-width: 900px) { .hero { grid-template-columns:1fr; padding:24px; } .hero h1 { font-size:1.9rem; }
  .kpis { grid-template-columns: repeat(2, 1fr); } }
@media (prefers-reduced-motion: reduce) { .hero::before, .ln, .ring, .pulse, .tag { animation:none !important; opacity:1; stroke-dashoffset:0; } }
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def load_prices() -> pd.DataFrame:
    frames = []
    for name, table in STOCKS.items():
        d = pd.read_csv(CLEAN / f"{table}.csv", usecols=["date", "close_price"], parse_dates=["date"])
        d["stock"] = name
        frames.append(d)
    return pd.concat(frames).sort_values(["stock", "date"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def analyse(stock: str, adjusted: bool, fast: int, slow: int) -> pd.DataFrame:
    """Close, moving averages and Buy/Sell/Hold signal (same rules as the SQL)."""
    p = load_prices()
    d = p[p.stock == stock][["date", "close_price"]].rename(columns={"close_price": "raw"}).reset_index(drop=True)
    d["price"] = d.raw
    if adjusted and stock in EVENTS:
        d.loc[d.date < pd.Timestamp(EVENTS[stock]), "price"] = d.raw / 2.0
    d["fast"] = d.price.rolling(fast).mean()          # NaN until a full window exists
    d["slow"] = d.price.rolling(slow).mean()
    pf, ps = d.fast.shift(), d.slow.shift()
    ok = d[["fast", "slow"]].notna().all(axis=1) & pf.notna() & ps.notna()
    d["signal"] = "Hold"
    d.loc[ok & (d.fast > d.slow) & (pf <= ps), "signal"] = "Buy"
    d.loc[ok & (d.fast < d.slow) & (pf >= ps), "signal"] = "Sell"
    return d


def round_trips(d: pd.DataFrame) -> pd.DataFrame:
    rows, pos = [], None
    for _, r in d[d.signal != "Hold"].iterrows():
        if r.signal == "Buy" and pos is None:
            pos = r
        elif r.signal == "Sell" and pos is not None:
            rows.append({"buy_date": pos.date, "sell_date": r.date, "buy": pos.price, "sell": r.price,
                         "return_pct": (r.price / pos.price - 1) * 100, "days": (r.date - pos.date).days})
            pos = None
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def scoreboard(adjusted: bool, fast: int, slow: int) -> pd.DataFrame:
    out = []
    for s in STOCKS:
        d = analyse(s, adjusted, fast, slow)
        t = round_trips(d)
        sig = d[d.signal != "Hold"]
        out.append({"Stock": s, "Change %": (d.price.iloc[-1] / d.price.iloc[0] - 1) * 100,
                    "Buys": int((d.signal == "Buy").sum()), "Sells": int((d.signal == "Sell").sum()),
                    "Last signal": sig.signal.iloc[-1] if len(sig) else "-",
                    "Last signal date": sig.date.iloc[-1].date() if len(sig) else None,
                    "Win rate %": (t.return_pct > 0).mean() * 100 if len(t) else np.nan,
                    "Avg trade %": t.return_pct.mean() if len(t) else np.nan,
                    "Compounded %": ((1 + t.return_pct / 100).prod() - 1) * 100 if len(t) else np.nan})
    return pd.DataFrame(out)


def show(fig):
    try:
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def show_df(df, **kw):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def style(fig, height=470, title=None):
    fig.update_layout(template="plotly_dark", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="IBM Plex Sans, Arial, sans-serif", color=TEXT), hovermode="x unified",
                      margin=dict(l=10, r=10, t=50 if title else 20, b=10),
                      legend=dict(orientation="h", y=1.08, x=0), title=dict(text=title, font=dict(family="Sora", size=16)) if title else None)
    fig.update_xaxes(gridcolor="#1B2A44", zeroline=False)
    fig.update_yaxes(gridcolor="#1B2A44", zeroline=False)
    return fig


# ----------------------------------------------------------------------------- sidebar
st.sidebar.markdown("### Controls")
stock = st.sidebar.selectbox("Stock", list(STOCKS), index=0)
adjusted = st.sidebar.toggle("Bonus-adjusted prices", value=True,
                             help="TCS and Infosys had 1:1 bonus issues. Adjusted = prices before the event divided by 2.")
fast = st.sidebar.slider("Fast average (days)", 5, 40, 20)
slow = st.sidebar.slider("Slow average (days)", 30, 120, 50)
if fast >= slow:
    st.sidebar.error("Fast average must be shorter than the slow one.")
    st.stop()
full = analyse(stock, adjusted, fast, slow)
lo, hi = full.date.min().date(), full.date.max().date()
rng = st.sidebar.slider("Date range", lo, hi, (lo, hi), format="MMM YYYY")
st.sidebar.caption("Defaults (20 / 50 days, adjusted) match the SQL project. Change them to explore.")

# ----------------------------------------------------------------------------- hero
st.markdown("""
<div class="hero">
  <div>
    <h1>When the <span class="fast">fast line</span> crosses the <span class="slow">slow one</span>.</h1>
    <p>Moving-average signals on six NSE stocks from 2015 to 2018, built entirely in SQL.
       And the two bonus-issue price cliffs that would have fooled them.</p>
  </div>
  <svg viewBox="0 0 520 230" role="img" aria-label="A fast moving average crossing above a slow one">
    <path class="ghost" d="M10 190 L510 190 M10 120 L510 120 M10 50 L510 50"/>
    <path class="ln slow" d="M10 150 C90 160 150 170 230 140 S380 70 510 60"/>
    <path class="ln fast" d="M10 190 C80 200 130 185 200 160 S300 90 360 82 S450 60 510 28"/>
    <circle class="pulse" cx="262" cy="125" r="6"/><circle class="ring" cx="262" cy="125" r="9"/>
    <text class="tag" x="276" y="150">Buy signal</text>
  </svg>
</div>
""", unsafe_allow_html=True)

view = full[(full.date.dt.date >= rng[0]) & (full.date.dt.date <= rng[1])]
chg = (view.price.iloc[-1] / view.price.iloc[0] - 1) * 100
sigs = view[view.signal != "Hold"]
last = sigs.iloc[-1] if len(sigs) else None
cls = "up" if chg >= 0 else "down"
last_html = (f'<span class="chip {last.signal.lower()}">{last.signal}</span>' if last is not None else "-")
last_sub = f"{last.date:%d %b %Y}" if last is not None else "no signals in range"
st.markdown(f"""
<div class="kpis">
  <div class="kpi"><div class="lab">{stock}: first close</div><div class="val">₹{view.price.iloc[0]:,.2f}</div><div class="sub">{view.date.iloc[0]:%d %b %Y}</div></div>
  <div class="kpi"><div class="lab">Last close</div><div class="val">₹{view.price.iloc[-1]:,.2f}</div><div class="sub">{view.date.iloc[-1]:%d %b %Y}</div></div>
  <div class="kpi"><div class="lab">Change over range</div><div class="val {cls}">{chg:+.1f}%</div><div class="sub">{'bonus-adjusted' if adjusted and stock in EVENTS else 'close to close'}</div></div>
  <div class="kpi"><div class="lab">Buy / Sell signals</div><div class="val"><span class="up">{(view.signal == 'Buy').sum()}</span> / <span class="down">{(view.signal == 'Sell').sum()}</span></div><div class="sub">{fast}-day vs {slow}-day crossover</div></div>
  <div class="kpi"><div class="lab">Latest signal</div><div class="val" style="font-size:1.3rem;padding-top:5px">{last_html}</div><div class="sub">{last_sub}</div></div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["Signals", "Replay", "Market", "Data trap", "Scoreboard", "SQL lab", "About"])


# ----------------------------------------------------------------------------- tab: signals
def signal_figure(d, upto=None):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.date, y=d.price, name="Close", line=dict(color=PRICE, width=1.3)))
    fig.add_trace(go.Scatter(x=d.date, y=d.fast, name=f"{fast}-day average", line=dict(color=FAST, width=2.2)))
    fig.add_trace(go.Scatter(x=d.date, y=d.slow, name=f"{slow}-day average", line=dict(color=SLOW, width=2.2)))
    b, s = d[d.signal == "Buy"], d[d.signal == "Sell"]
    fig.add_trace(go.Scatter(x=b.date, y=b.price, mode="markers", name="Buy",
                             marker=dict(symbol="triangle-up", size=13, color=BUY, line=dict(color="#0C1424", width=1.5))))
    fig.add_trace(go.Scatter(x=s.date, y=s.price, mode="markers", name="Sell",
                             marker=dict(symbol="triangle-down", size=13, color=SELL, line=dict(color="#0C1424", width=1.5))))
    return fig


with tabs[0]:
    st.markdown(f'<div class="h2">{stock}: price, averages and crossovers</div><div class="sub2">A Buy is the single day the fast average moves above the slow one. A Sell is the mirror image. Drag the slider under the chart to zoom.</div>', unsafe_allow_html=True)
    fig = style(signal_figure(view), 520)
    if stock in EVENTS and not adjusted and view.date.min() <= pd.Timestamp(EVENTS[stock]) <= view.date.max():
        fig.add_vline(x=pd.Timestamp(EVENTS[stock]).timestamp() * 1000, line_dash="dot", line_color=SELL)
        fig.add_annotation(x=pd.Timestamp(EVENTS[stock]), y=1, yref="paper", text="Bonus issue: the price halves overnight",
                           showarrow=False, font=dict(color=SELL), xanchor="left")
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06, bgcolor="#101A2E"))
    show(fig)
    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown('<div class="h2">Signal log</div>', unsafe_allow_html=True)
        log = sigs[["date", "signal", "price"]].rename(columns={"date": "Date", "signal": "Signal", "price": "Close (₹)"}).iloc[::-1]
        log["Date"] = log["Date"].dt.date
        show_df(log, height=300)
    with c2:
        t = round_trips(view)
        st.markdown('<div class="h2">Buy-then-sell round trips</div>', unsafe_allow_html=True)
        if len(t):
            bar = go.Figure(go.Bar(x=list(range(1, len(t) + 1)), y=t.return_pct, marker_color=np.where(t.return_pct >= 0, BUY, SELL),
                                   customdata=t.buy_date.dt.strftime("%d %b %Y"), hovertemplate="Buy on %{customdata}<br>%{y:.1f}%<extra></extra>"))
            style(bar, 300).update_layout(xaxis_title="Trade number", yaxis_title="Return %", hovermode="closest")
            show(bar)
            st.caption(f"{len(t)} trades, {int((t.return_pct > 0).sum())} profitable. Average {t.return_pct.mean():+.1f}% per trade, before brokerage and dividends.")
        else:
            st.info("No completed Buy-then-Sell trips in this range.")

# ----------------------------------------------------------------------------- tab: replay
with tabs[1]:
    st.markdown(f'<div class="h2">Watch {stock} unfold</div><div class="sub2">Press play. The signals appear only when the averages cross, exactly as they would have in real time.</div>', unsafe_allow_html=True)
    d = view.reset_index(drop=True)
    step = max(1, len(d) // 55)
    idx = list(range(max(slow + 1, step), len(d), step)) + [len(d) - 1]

    def frame(i):
        part = d.iloc[: i + 1]
        b, s = part[part.signal == "Buy"], part[part.signal == "Sell"]
        return go.Frame(data=[go.Scatter(x=part.date, y=part.price), go.Scatter(x=part.date, y=part.fast),
                              go.Scatter(x=part.date, y=part.slow), go.Scatter(x=b.date, y=b.price), go.Scatter(x=s.date, y=s.price)],
                        name=str(i), traces=[0, 1, 2, 3, 4])
    first = idx[0]
    rf = signal_figure(d.iloc[: first + 1])
    rf.frames = [frame(i) for i in idx]
    rf = style(rf, 520)
    rf.update_xaxes(range=[d.date.iloc[0], d.date.iloc[-1]])
    rf.update_yaxes(range=[float(d.price.min()) * 0.95, float(d.price.max()) * 1.05])
    rf.update_layout(updatemenus=[dict(type="buttons", direction="left", x=0, y=-0.12, bgcolor=PANEL, bordercolor=LINE, font=dict(color=TEXT),
                                       buttons=[dict(label="Play", method="animate", args=[None, dict(frame=dict(duration=90, redraw=True), transition=dict(duration=0), fromcurrent=True)]),
                                                dict(label="Pause", method="animate", args=[[None], dict(frame=dict(duration=0), mode="immediate")])])],
                     sliders=[dict(active=0, x=0.14, len=0.86, y=-0.1, currentvalue=dict(visible=False), bgcolor=LINE, activebgcolor=FAST, bordercolor=LINE,
                                   steps=[dict(method="animate", label="", args=[[str(i)], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))]) for i in idx])])
    show(rf)

# ----------------------------------------------------------------------------- tab: market
with tabs[2]:
    st.markdown('<div class="h2">All six stocks on one scale</div><div class="sub2">Every price rebased to 100 on the first day, so growth is comparable even though Eicher trades near ₹27,000 and TVS near ₹500.</div>', unsafe_allow_html=True)
    use_adj = st.radio("Prices", ["Bonus-adjusted", "Raw (shows the cliffs)"], horizontal=True) == "Bonus-adjusted"
    wide = pd.DataFrame({s: analyse(s, use_adj, fast, slow).set_index("date").price for s in STOCKS})
    wide = wide[(wide.index.date >= rng[0]) & (wide.index.date <= rng[1])]
    reb = wide / wide.iloc[0] * 100
    fig = go.Figure([go.Scatter(x=reb.index, y=reb[c], name=c, line=dict(width=2.2, color=PALETTE[i])) for i, c in enumerate(reb.columns)])
    show(style(fig, 470).update_layout(yaxis_title="Index (start = 100)"))
    c1, c2 = st.columns(2)
    with c1:
        end = (reb.iloc[-1] - 100).sort_values()
        bar = go.Figure(go.Bar(x=end.values, y=end.index, orientation="h", marker_color=np.where(end.values >= 0, BUY, SELL),
                               text=[f"{v:+.1f}%" for v in end.values], textposition="outside"))
        show(style(bar, 360, "Total change over the range").update_layout(hovermode="closest", xaxis_title="%"))
    with c2:
        corr = wide.pct_change().dropna().corr()
        heat = go.Figure(go.Heatmap(z=corr.values, x=corr.columns, y=corr.columns, zmin=-0.2, zmax=1, colorscale=[[0, "#131E34"], [.5, "#2C4C7A"], [1, "#6CB6FF"]],
                                    text=np.round(corr.values, 2), texttemplate="%{text}", showscale=False))
        show(style(heat, 360, "How closely daily returns move together").update_layout(hovermode="closest"))
    if not use_adj:
        st.markdown('<div class="note">On raw prices TCS and Infosys fall off a cliff. That is not a crash. See the Data trap tab.</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------- tab: data trap
with tabs[3]:
    st.markdown('<div class="h2">The data trap</div><div class="sub2">Two stocks appear to lose half their value in a single day. Nobody lost anything: it was a 1:1 bonus issue.</div>', unsafe_allow_html=True)
    p = load_prices().copy()
    p["move"] = p.groupby("stock").close_price.pct_change() * 100
    worst = p.loc[p.dropna().groupby("stock").move.idxmin()].sort_values("move")
    wt = worst[["stock", "date", "close_price", "move"]].rename(columns={"stock": "Stock", "date": "Date", "close_price": "Close (₹)", "move": "Worst day %"})
    wt["Date"] = wt["Date"].dt.date
    wt["Worst day %"] = wt["Worst day %"].round(1)
    show_df(wt)
    ev = st.radio("Look closer at", list(EVENTS), horizontal=True)
    raw_df = analyse(ev, False, fast, slow)
    adj_df = analyse(ev, True, fast, slow)
    evd = pd.Timestamp(EVENTS[ev])
    fig = go.Figure([go.Scatter(x=raw_df.date, y=raw_df.price, name="Raw close", line=dict(color=SELL, width=2)),
                     go.Scatter(x=adj_df.date, y=adj_df.price, name="Adjusted close", line=dict(color=BUY, width=2.4))])
    fig.add_vline(x=evd.timestamp() * 1000, line_dash="dot", line_color=MUTED)
    fig.add_annotation(x=evd, y=1, yref="paper", text=f"{evd:%d %b %Y}: 1:1 bonus", showarrow=False, xanchor="left", font=dict(color=MUTED))
    show(style(fig, 440))
    r0, r1 = raw_df.price.iloc[0], raw_df.price.iloc[-1]
    a0, a1 = adj_df.price.iloc[0], adj_df.price.iloc[-1]
    cmp_raw, cmp_adj = scoreboard(False, 20, 50).set_index("Stock").loc[ev], scoreboard(True, 20, 50).set_index("Stock").loc[ev]
    k1, k2, k3 = st.columns(3)
    k1.metric(f"{ev} change, raw", f"{(r1 / r0 - 1) * 100:+.1f}%")
    k2.metric(f"{ev} change, adjusted", f"{(a1 / a0 - 1) * 100:+.1f}%", delta=f"{((a1 / a0) - (r1 / r0)) * 100:+.0f} points")
    k3.metric("Buy / Sell signals (raw to adjusted)", f"{int(cmp_raw.Buys)}/{int(cmp_raw.Sells)} to {int(cmp_adj.Buys)}/{int(cmp_adj.Sells)}")
    st.markdown('<div class="note good"><b>Why it matters.</b> The cliff drags the 20-day average down within days, so it can fake a Sell. Raw prices say TCS lost 23.8% and Infosys 30.9%; adjusted, both gained (+52.4% and +38.2%). The winners and losers list flips.</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------- tab: scoreboard
with tabs[4]:
    st.markdown('<div class="h2">Scoreboard</div><div class="sub2">All six stocks with the current settings. Win rate and average trade assume you buy at each Buy close and sell at the next Sell close.</div>', unsafe_allow_html=True)
    sb = scoreboard(adjusted, fast, slow)
    show_df(sb.round(1), column_config={
        "Change %": st.column_config.NumberColumn(format="%+.1f%%"), "Win rate %": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100),
        "Avg trade %": st.column_config.NumberColumn(format="%+.1f%%"), "Compounded %": st.column_config.NumberColumn(format="%+.0f%%")})
    fig = go.Figure([go.Bar(x=sb.Stock, y=sb.Buys, name="Buys", marker_color=BUY), go.Bar(x=sb.Stock, y=sb.Sells, name="Sells", marker_color=SELL)])
    show(style(fig, 360, "Signals per stock").update_layout(barmode="group", hovermode="closest"))
    st.markdown(f'<div class="note">Total across all six stocks: <b>{int(sb.Buys.sum())} Buys</b> and <b>{int(sb.Sells.sum())} Sells</b>. '
                'With raw prices and the default 20/50 windows the SQL result is 56 Buys and 57 Sells. A moving-average crossover lags the price by design, so no strategy result here is a recommendation: dividends, costs and taxes are not modelled.</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------- tab: SQL lab
@st.cache_resource(show_spinner=False)
def sql_connection():
    con = sqlite3.connect(":memory:", check_same_thread=False)
    for t in STOCKS.values():
        pd.read_csv(CLEAN / f"{t}.csv").to_sql(t, con, index=False)
    return con


def split_tasks(text):
    parts = re.split(r"^-- (TASK [^\n]+)$", text, flags=re.M)
    tasks = {}
    for i in range(1, len(parts), 2):
        stmts, buf = [], ""
        for line in parts[i + 1].splitlines(keepends=True):
            if line.strip().startswith("--"):
                continue
            buf += line
            if sqlite3.complete_statement(buf):
                stmts.append(buf.strip())
                buf = ""
        tasks[parts[i]] = stmts
    return tasks


with tabs[5]:
    st.markdown('<div class="h2">SQL lab</div><div class="sub2">The real project queries, running live against the cleaned data in an in-memory SQLite database.</div>', unsafe_allow_html=True)
    con = sql_connection()
    tasks = split_tasks(SQL_FILE.read_text(encoding="utf-8")) if SQL_FILE.exists() else {}
    if tasks:
        pick = st.selectbox("Task", list(tasks), index=min(9, len(tasks) - 1))
        code = "\n\n".join(tasks[pick])
        st.code(code, language="sql")
        if st.button("Run this task", type="primary"):
            try:
                res = None
                for s in tasks[pick]:
                    cur = con.execute(s)
                    if s.lstrip().upper().startswith(("SELECT", "WITH")):
                        res = pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])
                if res is not None:
                    st.success(f"{len(res)} rows")
                    show_df(res.head(500))
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
    st.markdown('<div class="h2" style="margin-top:22px">Your own query</div>', unsafe_allow_html=True)
    q = st.text_area("Read-only (SELECT or WITH). Tables: " + ", ".join(STOCKS.values()),
                     "SELECT date, close_price\nFROM tcs\nORDER BY close_price DESC\nLIMIT 5;", height=130)
    if st.button("Run query"):
        stripped = q.strip().rstrip(";")
        if not stripped.upper().startswith(("SELECT", "WITH")) or ";" in stripped:
            st.warning("Only a single SELECT or WITH statement is allowed here.")
        else:
            try:
                cur = con.execute(stripped)
                show_df(pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description]).head(500))
            except Exception as e:  # noqa: BLE001
                st.error(str(e))

# ----------------------------------------------------------------------------- tab: about
with tabs[6]:
    st.markdown("""
<div class="h2">About this project</div>
<div class="sub2">Six NSE stocks (Bajaj Auto, Eicher Motors, Hero Motocorp, Infosys, TCS, TVS Motors), 889 trading days from 1 Jan 2015 to 31 Jul 2018.</div>

**Pipeline.** Raw CSVs are cleaned in Python (ISO dates, snake_case columns, blanks kept as NULL), loaded into SQLite and MySQL, and analysed in SQL with window functions: `AVG() OVER (ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)`, `LAG()`, `ROW_NUMBER()`, CTEs and `PARTITION BY`.

**Signal rule.** Buy on the day the 20-day average crosses above the 50-day average. Sell on the day it crosses below. Hold otherwise, including while a full window does not yet exist.

**Data quality.** `deliverable_qty` is blank on two dates across several unrelated companies, which points to exchange reporting. TCS (2018-05-31) and Infosys (2015-06-15) show -50% single-day drops caused by 1:1 bonus issues; the app and the SQL both adjust for them.

**Limits.** Prices only. No dividends, brokerage, taxes or market index. The dashboard is for learning, not investment advice.
""")

st.markdown('<div class="foot">Golden Cross dashboard. Data: NSE daily prices, 2015 to 2018. Built with SQL, Python, Streamlit and Plotly.</div>', unsafe_allow_html=True)