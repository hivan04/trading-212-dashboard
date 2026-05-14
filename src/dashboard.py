import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api import T212Client
from metrics import (
    annualised_volatility,
    cagr,
    drawdown_series,
    get_portfolio_history,
    max_drawdown,
    portfolio_beta,
    sharpe_ratio,
    value_at_risk,
)

st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="metric-container"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 10px;
        padding: 14px 18px;
    }
    h1, [data-testid="stCaptionContainer"] { text-align: center; }
    </style>
    """,
    unsafe_allow_html=True,
)

mode = "live"
risk_free = 0

_PERIOD_LABELS = ["1W", "6M", "1Y", "YTD"]
_PERIOD_YF = {"1W": "5d", "6M": "6mo", "1Y": "1y", "YTD": "ytd"}


# ── Cached loaders ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _summary(mode: str) -> dict:
    return T212Client(mode).account_summary()


@st.cache_data(ttl=300, show_spinner=False)
def _portfolio(mode: str) -> list:
    return T212Client(mode).portfolio()


@st.cache_data(ttl=300, show_spinner=False)
def _dividends(mode: str) -> list:
    return T212Client(mode).dividends()


@st.cache_data(ttl=3600, show_spinner=False)
def _history(positions_key: tuple, period: str) -> pd.Series:
    positions = [{"ticker": t, "quantity": q} for t, q in positions_key]
    return get_portfolio_history(positions, period)


@st.cache_data(ttl=3600, show_spinner=False)
def _risk_metrics(positions_key: tuple, period: str) -> dict:
    positions = [{"ticker": t, "quantity": q} for t, q in positions_key]
    hist = get_portfolio_history(positions, period)
    return {
        "beta": portfolio_beta(hist),
        "var95": value_at_risk(hist, 0.95),
    }



# ── Fetch core data ────────────────────────────────────────────────────────────
with st.spinner("Connecting to Trading 212…"):
    try:
        summary = _summary(mode)
        positions = _portfolio(mode)
    except Exception as exc:
        st.error(f"**Trading 212 API error:** {exc}")
        st.info("Check that your API key is valid and the account mode is correct.")
        st.stop()

# ── Helpers ────────────────────────────────────────────────────────────────────
def clean_ticker(t: str) -> str:
    return t.replace("_EQ", "")


# ── Build positions DataFrame ──────────────────────────────────────────────────
def _positions_df(positions: list) -> pd.DataFrame:
    rows = []
    for p in positions:
        qty = float(p.get("quantity", 0))
        avg = float(p.get("averagePrice", 0))
        cur = float(p.get("currentPrice", 0))
        ppl = float(p.get("ppl", 0))
        cost = qty * avg
        rows.append(
            {
                "Ticker": clean_ticker(p.get("ticker", "")),
                "T212Ticker": p.get("ticker", ""),
                "Quantity": qty,
                "Avg Price": avg,
                "Current Price": cur,
                "Value": qty * cur,
                "P&L": ppl,
                "P&L %": (ppl / cost * 100) if cost else 0.0,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["Ticker", "T212Ticker", "Quantity", "Avg Price", "Current Price", "Value", "P&L", "P&L %"])
    return pd.DataFrame(rows).sort_values("Value", ascending=False).reset_index(drop=True)


pos_df = _positions_df(positions)

# ── Account summary values ─────────────────────────────────────────────────────
currency = summary.get("currency", "")
total = float(summary.get("total", 0))
invested = float(summary.get("invested", 0))
free_cash = float(summary.get("free", 0))
result = float(summary.get("result", 0))
result_pct = (result / (total - result) * 100) if (total - result) != 0 else 0.0
total_ppl = pos_df["P&L"].sum()
cost_basis = (pos_df["Quantity"] * pos_df["Avg Price"]).sum()
total_return_pct = (total_ppl / cost_basis * 100) if cost_basis else 0.0
CURRENCY_SYM = {"GBP": "£", "USD": "$", "EUR": "€"}.get(currency, f"{currency} ")


def fmt(v: float, d: int = 2) -> str:
    return f"{CURRENCY_SYM}{v:,.{d}f}"


def fmt_compact(v: float) -> str:
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000:
        return f"{sign}{CURRENCY_SYM}{a/1_000_000:.2f}M"
    if a >= 1_000:
        return f"{sign}{CURRENCY_SYM}{a/1_000:.2f}K"
    return f"{sign}{CURRENCY_SYM}{a:.2f}"


def pct_fmt(v: float) -> str:
    return f"{v:+.2f}%"


# ── Header ─────────────────────────────────────────────────────────────────────
st.title("Portfolio Dashboard")
st.caption(f"🟢 Live account · GBP")

tab_ov, tab_perf, tab_hold, tab_div = st.tabs(
    ["📊 Overview", "📈 Performance", "💼 Holdings", "💰 Dividends"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_ov:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Portfolio", fmt(total))
    c2.metric("Invested", fmt(invested))
    c3.metric("Free Cash", fmt(free_cash))
    c4.metric("Total P&L", fmt(result), delta=pct_fmt(result_pct))
    c5.metric("Total Return", fmt_compact(total_ppl), delta=pct_fmt(total_return_pct))
    c6.metric("Active Open Positions", len(pos_df))

    st.divider()

    if pos_df.empty:
        st.info("No open positions found.")
    else:
        left, right = st.columns(2)

        with left:
            total_value = pos_df["Value"].sum()
            main = pos_df[pos_df["Value"] / total_value >= 0.01].copy()
            other_val = pos_df[pos_df["Value"] / total_value < 0.01]["Value"].sum()
            if other_val > 0:
                other_row = pd.DataFrame([{"Ticker": "Other", "Value": other_val}])
                pie_df = pd.concat([main[["Ticker", "Value"]], other_row], ignore_index=True)
            else:
                pie_df = main[["Ticker", "Value"]]

            fig_pie = go.Figure(
                go.Pie(
                    labels=pie_df["Ticker"],
                    values=pie_df["Value"],
                    hole=0.48,
                    textinfo="percent",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        f"Value: {CURRENCY_SYM}" + "%{value:,.2f}<br>"
                        "Share: %{percent}<extra></extra>"
                    ),
                )
            )
            fig_pie.update_layout(
                title="Portfolio Allocation",
                template="plotly_dark",
                legend=dict(orientation="v", x=1.02, y=0.5),
                margin=dict(l=10, r=130, t=45, b=10),
                height=580,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with right:
            main_bar = pos_df[pos_df["Value"] >= 1000].copy()
            other_bar_val = pos_df[pos_df["Value"] < 1000]["Value"].sum()
            if other_bar_val > 0:
                other_bar_row = pd.DataFrame([{"Ticker": "Other", "Value": other_bar_val, "P&L": 0}])
                bar_df = pd.concat([main_bar[["Ticker", "Value", "P&L"]], other_bar_row], ignore_index=True)
            else:
                bar_df = main_bar[["Ticker", "Value", "P&L"]]
            bar_df = bar_df.sort_values("Value", ascending=True)

            bar_colors = ["#95a5a6" if t == "Other" else ("#2ecc71" if v >= 0 else "#e74c3c")
                          for t, v in zip(bar_df["Ticker"], bar_df["P&L"])]
            fig_bar = go.Figure(
                go.Bar(
                    x=bar_df["Value"],
                    y=bar_df["Ticker"],
                    orientation="h",
                    marker_color=bar_colors,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        f"Value: {CURRENCY_SYM}" + "%{x:,.2f}<extra></extra>"
                    ),
                )
            )
            fig_bar.update_layout(
                title="Top Holdings by Value",
                template="plotly_dark",
                xaxis_title=f"Value (£)",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=10, r=10, t=45, b=10),
                height=430,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
with tab_perf:
    if pos_df.empty:
        st.info("No positions available to compute performance metrics.")
    else:
        period_label = st.radio(
            "Period",
            _PERIOD_LABELS,
            index=2,
            horizontal=True,
            label_visibility="collapsed",
        )
        lookback = _PERIOD_YF[period_label]

        positions_key = tuple(
            (row["T212Ticker"], row["Quantity"]) for _, row in pos_df.iterrows()
        )
        with st.spinner(f"Downloading {period_label} of historical prices…"):
            hist = _history(positions_key, lookback)

        if hist.empty:
            st.warning(
                "Could not download historical price data for any position. "
                "Some T212 tickers may not map to yfinance symbols."
            )
        else:
            sr = sharpe_ratio(hist, risk_free)
            md = max_drawdown(hist)
            ann_cagr = cagr(hist)
            ann_vol = annualised_volatility(hist)

            with st.spinner("Calculating beta and VaR…"):
                risk = _risk_metrics(positions_key, lookback)
            beta = risk["beta"]
            var95 = risk["var95"]
            var95_abs = abs(var95) * pos_df["Value"].sum() if not np.isnan(var95) else float("nan")

            m1, m2, m3 = st.columns(3)
            m1.metric(
                "Sharpe Ratio",
                f"{sr:.2f}" if not np.isnan(sr) else "N/A",
                help="Annualised excess return per unit of risk (>1 good, >2 excellent).",
            )
            m2.metric(
                "Max Drawdown",
                f"{md:.1%}" if not np.isnan(md) else "N/A",
                delta=f"{md:.1%}" if not np.isnan(md) else None,
                delta_color="inverse",
                help="Largest peak-to-trough decline over the lookback period.",
            )
            m3.metric(
                "CAGR",
                f"{ann_cagr:.1%}" if not np.isnan(ann_cagr) else "N/A",
                help="Compound Annual Growth Rate.",
            )

            m4, m5, m6 = st.columns(3)
            m4.metric(
                "Volatility (ann.)",
                f"{ann_vol:.1%}" if not np.isnan(ann_vol) else "N/A",
                help="Annualised standard deviation of daily returns.",
            )
            m5.metric(
                "Beta (vs S&P 500)",
                f"{beta:.2f}" if not np.isnan(beta) else "N/A",
                help="Sensitivity to S&P 500 moves. >1 = more volatile than market, <1 = less.",
            )
            m6.metric(
                "VaR 95% (daily)",
                f"{var95:.2%} / {fmt_compact(var95_abs)}" if not np.isnan(var95) else "N/A",
                delta=f"{var95:.2%}" if not np.isnan(var95) else None,
                delta_color="inverse",
                help="Historical Value at Risk: worst expected daily loss 95% of the time.",
            )

            st.divider()

            # Portfolio value line chart
            hist_df = hist.reset_index()
            hist_df.columns = ["Date", "Value"]
            fig_val = go.Figure(
                go.Scatter(
                    x=hist_df["Date"],
                    y=hist_df["Value"],
                    mode="lines",
                    line=dict(color="#00b4d8", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(0,180,216,0.07)",
                    hovertemplate="%{x|%d %b %Y}<br>"
                    + f"{CURRENCY_SYM}"
                    + "%{y:,.2f}<extra></extra>",
                )
            )
            fig_val.update_layout(
                title=f"Estimated Portfolio Value — {lookback} (current holdings)",
                template="plotly_dark",
                yaxis_title=f"Approx. Value",
                height=340,
                margin=dict(l=10, r=10, t=45, b=10),
            )
            st.plotly_chart(fig_val, use_container_width=True)

            # Drawdown chart
            dd_series = drawdown_series(hist).reset_index()
            dd_series.columns = ["Date", "Drawdown"]
            fig_dd = go.Figure(
                go.Scatter(
                    x=dd_series["Date"],
                    y=dd_series["Drawdown"] * 100,
                    mode="lines",
                    line=dict(color="#e74c3c", width=1.5),
                    fill="tozeroy",
                    fillcolor="rgba(231,76,60,0.13)",
                    hovertemplate="%{x|%d %b %Y}<br>Drawdown: %{y:.2f}%<extra></extra>",
                )
            )
            fig_dd.update_layout(
                title="Drawdown from Peak",
                template="plotly_dark",
                yaxis_title="Drawdown (%)",
                height=260,
                margin=dict(l=10, r=10, t=45, b=10),
            )
            st.plotly_chart(fig_dd, use_container_width=True)

            st.caption(
                "⚠️ Metrics assume current holdings were held for the full lookback period. "
                "Interim buys/sells are not modelled — use as directional estimates."
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — HOLDINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_hold:
    if pos_df.empty:
        st.info("No open positions found.")
    else:
        disp = pos_df.drop(columns=["T212Ticker"]).copy()
        disp["Quantity"] = disp["Quantity"].apply(
            lambda v: f"{v:,.6f}".rstrip("0").rstrip(".")
        )
        for col in ("Avg Price", "Current Price", "Value", "P&L"):
            disp[col] = disp[col].apply(lambda v: fmt(v))
        disp["P&L %"] = disp["P&L %"].apply(pct_fmt)
        disp.index = range(1, len(disp) + 1)

        st.dataframe(disp, use_container_width=True, height=600)
        st.caption(
            f"{len(pos_df)} positions · "
            f"Total value: {fmt(pos_df['Value'].sum())} · "
            f"Total P&L: {fmt(pos_df['P&L'].sum())}"
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DIVIDENDS
# ══════════════════════════════════════════════════════════════════════════════
with tab_div:
    with st.spinner("Fetching dividend history…"):
        try:
            div_raw = _dividends(mode)
        except Exception as exc:
            st.error(f"Could not load dividends: {exc}")
            div_raw = []

    if not div_raw:
        st.info("No dividend records found.")
    else:
        # Flatten nested instrument dict and build clean DataFrame
        rows = []
        for d in div_raw:
            inst = d.get("instrument", {})
            rows.append({
                "Name":               inst.get("name", d.get("ticker", "")),
                "Ticker":             clean_ticker(d.get("ticker", "")),
                "Paid On":            d.get("paidOn", ""),
                "Amount (GBP)":       float(d.get("amount", 0)),
                "Qty":                float(d.get("quantity", 0)),
                "Per Share":          float(d.get("grossAmountPerShare", 0)),
                "Currency":           d.get("currency", ""),
            })
        div_df = pd.DataFrame(rows)
        div_df["Paid On"] = pd.to_datetime(div_df["Paid On"], errors="coerce", utc=True)
        div_df = div_df.sort_values("Paid On", ascending=False).reset_index(drop=True)

        total_div = div_df["Amount (GBP)"].sum()
        ytd_div   = div_df.loc[div_df["Paid On"].dt.year == pd.Timestamp.now().year, "Amount (GBP)"].sum()
        periods   = div_df["Paid On"].dt.to_period("M").nunique()
        avg_monthly = total_div / max(periods, 1)

        d1, d2, d3 = st.columns(3)
        d1.metric("Total Dividends", fmt(total_div))
        d2.metric("YTD Dividends",   fmt(ytd_div))
        d3.metric("Avg Monthly",     fmt(avg_monthly))

        st.divider()

        monthly = (
            div_df.assign(_period=div_df["Paid On"].dt.to_period("M"))
            .groupby("_period")["Amount (GBP)"]
            .sum()
            .reset_index()
        )
        monthly["Month"] = monthly["_period"].dt.to_timestamp()
        fig_div = go.Figure(
            go.Bar(
                x=monthly["Month"],
                y=monthly["Amount (GBP)"],
                marker_color="#2ecc71",
                hovertemplate="%{x|%b %Y}<br>" + f"{CURRENCY_SYM}" + "%{y:,.2f}<extra></extra>",
            )
        )
        fig_div.update_layout(
            title="Monthly Dividends Received",
            template="plotly_dark",
            xaxis_title="Month",
            yaxis_title=f"Dividends (£)",
            height=320,
            margin=dict(l=10, r=10, t=45, b=10),
        )
        st.plotly_chart(fig_div, use_container_width=True)

        # Display table with formatted columns
        disp_div = div_df.copy()
        disp_div["Amount (GBP)"] = disp_div["Amount (GBP)"].apply(lambda v: fmt(v))
        disp_div["Per Share"]    = disp_div["Per Share"].apply(lambda v: fmt(v))
        disp_div["Qty"]          = disp_div["Qty"].apply(lambda v: f"{v:,.4f}".rstrip("0").rstrip("."))
        disp_div["Paid On"]      = disp_div["Paid On"].dt.strftime("%d %b %Y")
        disp_div.index = range(1, len(disp_div) + 1)
        st.dataframe(disp_div, use_container_width=True, height=400)
