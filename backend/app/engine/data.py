"""Market-data access.

The platform ships with a deterministic, fully offline *sample* dataset so the
engine, templates and tests run without any network access. The sample series
are synthetic but parameterised to roughly resemble the long-run behaviour of
each asset class. Real data can be supplied via CSV files dropped in the
``data`` directory, or via Yahoo Finance when ``yfinance`` is installed and the
network policy allows it.
"""
from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Annualised (drift, vol, start_price) used to synthesise the sample history.
SAMPLE_ASSETS: dict[str, tuple[float, float, float]] = {
    "SPY": (0.110, 0.15, 30.0),
    "QQQ": (0.130, 0.22, 20.0),
    "TLT": (0.055, 0.12, 40.0),
    "GLD": (0.050, 0.17, 35.0),
    "BTC": (0.350, 0.75, 1.0),
    "CASH": (0.025, 0.001, 100.0),
}

SAMPLE_START = "1990-01-01"
SAMPLE_END = "2024-12-31"


@functools.lru_cache(maxsize=1)
def _sample_panel() -> pd.DataFrame:
    """Generate the deterministic sample price panel once and cache it."""
    dates = pd.bdate_range(SAMPLE_START, SAMPLE_END)
    n = len(dates)
    ppy = 252.0
    rng = np.random.default_rng(20240601)

    # Shared market factor gives the assets realistic cross-correlation while
    # each shock is kept at unit variance so realised vols match the targets.
    market = rng.standard_normal(n)
    cols = {}
    # Correlation of each asset's shock with the common market factor.
    rho = {"SPY": 0.95, "QQQ": 0.9, "TLT": -0.3, "GLD": 0.1, "BTC": 0.5, "CASH": 0.0}
    for name, (mu, sigma, p0) in SAMPLE_ASSETS.items():
        r = rho[name]
        idio = rng.standard_normal(n)
        shock = r * market + np.sqrt(max(1e-9, 1.0 - r * r)) * idio  # unit variance
        daily = (mu - 0.5 * sigma ** 2) / ppy + sigma / np.sqrt(ppy) * shock
        prices = p0 * np.exp(np.cumsum(daily))
        cols[name] = prices
    panel = pd.DataFrame(cols, index=dates)
    panel.index.name = "date"
    return panel


def available_sample_tickers() -> list[str]:
    return list(SAMPLE_ASSETS.keys())


def _load_csv(ticker: str) -> pd.Series | None:
    path = DATA_DIR / f"{ticker}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=[0], index_col=0)
    col = "close" if "close" in df.columns else df.columns[-1]
    s = df[col].astype(float)
    s.name = ticker
    return s


def _load_yahoo(tickers: list[str], start: str | None, end: str | None) -> pd.DataFrame:
    import yfinance as yf  # imported lazily; optional dependency

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    close = raw["Close"] if "Close" in raw else raw
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    return close.dropna(how="all")


def get_prices(
    tickers: list[str],
    source: str = "sample",
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Return a price-level panel for the requested tickers.

    ``source`` is one of ``sample`` (default, offline), ``csv`` or ``yahoo``.
    Unknown tickers fall back to the sample panel where possible.
    """
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    if not tickers:
        raise ValueError("No tickers requested.")

    if source == "yahoo":
        panel = _load_yahoo(tickers, start, end)
    elif source == "csv":
        series = {t: _load_csv(t) for t in tickers}
        missing = [t for t, s in series.items() if s is None]
        if missing:
            raise ValueError(f"No CSV data found for: {', '.join(missing)}")
        panel = pd.concat(series.values(), axis=1)
    else:  # sample
        sample = _sample_panel()
        cols = []
        for t in tickers:
            if t in sample.columns:
                cols.append(t)
            else:
                raise ValueError(
                    f"Unknown sample ticker '{t}'. Available: "
                    f"{', '.join(sample.columns)}"
                )
        panel = sample[cols].copy()

    panel = panel.sort_index()
    if start:
        panel = panel[panel.index >= pd.Timestamp(start)]
    if end:
        panel = panel[panel.index <= pd.Timestamp(end)]
    panel.index.name = "date"
    return panel.dropna(how="all").ffill().dropna()
