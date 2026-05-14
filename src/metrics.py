import numpy as np
import pandas as pd
import yfinance as yf

# T212 exchange code → yfinance suffix
_EXCHANGE_SUFFIX: dict[str, str] = {
    "US": "",
    "UK": ".L",
    "GER": ".DE",
    "FRA": ".PA",
    "NLD": ".AS",
    "SPA": ".MC",
    "ITA": ".MI",
    "SWE": ".ST",
    "DEN": ".CO",
    "NOR": ".OL",
    "POR": ".LS",
    "BEL": ".BR",
    "FIN": ".HE",
    "AUT": ".VI",
    "SWX": ".SW",
    "AUS": ".AX",
    "CAN": ".TO",
    "HKG": ".HK",
    "SGP": ".SI",
}


def t212_to_yf(ticker: str) -> str:
    """Convert a T212 internal ticker (e.g. AAPL_US_EQ) to a yfinance symbol."""
    parts = ticker.split("_")
    symbol = parts[0]
    exchange = parts[1] if len(parts) >= 2 else "US"
    suffix = _EXCHANGE_SUFFIX.get(exchange, "")
    return f"{symbol}{suffix}"


def get_portfolio_history(
    positions: list[dict], period: str = "1y"
) -> pd.Series:
    """
    Reconstruct daily portfolio value using current holdings × historical prices.
    Returns a Series indexed by date. Positions whose tickers fail yfinance lookup
    are silently skipped — metrics are computed on successfully resolved holdings.
    """
    mapping: dict[str, float] = {}  # yf_ticker → quantity
    for pos in positions:
        yf_ticker = t212_to_yf(pos.get("ticker", ""))
        qty = float(pos.get("quantity", 0))
        if yf_ticker and qty > 0:
            mapping[yf_ticker] = mapping.get(yf_ticker, 0) + qty

    if not mapping:
        return pd.Series(dtype=float)

    tickers = list(mapping.keys())
    try:
        raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    except Exception:
        return pd.Series(dtype=float)

    if raw.empty:
        return pd.Series(dtype=float)

    # Normalize to DataFrame of closing prices regardless of single vs multi ticker
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]].rename(columns={"Close": tickers[0]})

    portfolio = pd.Series(0.0, index=prices.index)
    for ticker, qty in mapping.items():
        if ticker in prices.columns:
            portfolio += prices[ticker].ffill() * qty

    portfolio = portfolio[portfolio > 0]
    return portfolio


def sharpe_ratio(portfolio: pd.Series, risk_free_rate: float = 0.0425) -> float:
    """Annualised Sharpe ratio from a daily portfolio value series."""
    if len(portfolio) < 2:
        return float("nan")
    daily_ret = portfolio.pct_change().dropna()
    excess = daily_ret - risk_free_rate / 252
    std = excess.std()
    if std == 0:
        return float("nan")
    return float(np.sqrt(252) * excess.mean() / std)


def max_drawdown(portfolio: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a decimal (e.g. -0.25 = -25%)."""
    if len(portfolio) < 2:
        return float("nan")
    rolling_peak = portfolio.cummax()
    dd = (portfolio - rolling_peak) / rolling_peak
    return float(dd.min())


def cagr(portfolio: pd.Series) -> float:
    """Compound Annual Growth Rate."""
    if len(portfolio) < 2:
        return float("nan")
    years = len(portfolio) / 252
    total_return = portfolio.iloc[-1] / portfolio.iloc[0] - 1
    return float((1 + total_return) ** (1 / years) - 1)


def annualised_volatility(portfolio: pd.Series) -> float:
    """Annualised volatility of daily returns."""
    if len(portfolio) < 2:
        return float("nan")
    return float(portfolio.pct_change().dropna().std() * np.sqrt(252))


def drawdown_series(portfolio: pd.Series) -> pd.Series:
    """Return the rolling drawdown series (values ≤ 0)."""
    rolling_peak = portfolio.cummax()
    return (portfolio - rolling_peak) / rolling_peak


def portfolio_beta(portfolio: pd.Series, benchmark: str = "^GSPC") -> float:
    """Beta relative to a benchmark (default: S&P 500).
    Downloads benchmark prices for the portfolio's date range.
    """
    if len(portfolio) < 30:
        return float("nan")
    try:
        start, end = portfolio.index[0], portfolio.index[-1]
        raw = yf.download(benchmark, start=start, end=end, auto_adjust=True, progress=False)
        if raw.empty:
            return float("nan")
        bench = raw["Close"].squeeze()
        port_ret = portfolio.pct_change().dropna()
        bench_ret = bench.pct_change().dropna()
        aligned = pd.concat([port_ret, bench_ret], axis=1).dropna()
        if len(aligned) < 20:
            return float("nan")
        aligned.columns = ["p", "b"]
        cov = aligned.cov().loc["p", "b"]
        var = aligned["b"].var()
        return float("nan") if var == 0 else float(cov / var)
    except Exception:
        return float("nan")


def value_at_risk(portfolio: pd.Series, confidence: float = 0.95) -> float:
    """Historical VaR as a decimal at the given confidence level.
    E.g. -0.02 means a 2% daily loss is not exceeded on 95% of trading days.
    """
    if len(portfolio) < 20:
        return float("nan")
    return float(portfolio.pct_change().dropna().quantile(1 - confidence))
