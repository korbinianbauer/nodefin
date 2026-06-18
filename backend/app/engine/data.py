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
# Real datasets shipped with the repo live here (backend/data/).
REAL_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Real series bundled with the project, exposed via the ``csv`` source.
# Maps a ticker to (filename in REAL_DATA_DIR, column holding the price level).
# The S&P 500 file carries three levels: price-only, gross total return
# (dividends reinvested) and net total return (after withholding tax).
_SP500_FILE = "S&P 500 Indices 1885 to 2024.csv"
REAL_SERIES: dict[str, tuple[str, str]] = {
    "SPY": (_SP500_FILE, "sp500_gross"),       # total-return proxy for backtests
    "SP500": (_SP500_FILE, "sp500_price"),     # price index (no dividends)
    "SP500TR": (_SP500_FILE, "sp500_gross"),   # gross total return
    "SP500NTR": (_SP500_FILE, "sp500_net"),    # net total return
}

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


def merge_panels(panels) -> pd.DataFrame:
    """Merge one or more price panels into a single aligned asset universe.

    Series can span different histories (e.g. real S&P from 1885 vs a synthetic
    sample from 1990), so the result is restricted to the window where every
    column has data; internal gaps (calendar mismatches / holidays) are
    forward-filled.
    """
    if not isinstance(panels, list):
        panels = [panels]
    panels = [p for p in panels if p is not None]
    if not panels:
        raise ValueError("No price inputs provided.")
    merged = pd.concat(panels, axis=1)
    merged = merged.loc[:, ~merged.columns.duplicated()]
    merged = merged.sort_index()
    starts = [merged[c].first_valid_index() for c in merged.columns]
    ends = [merged[c].last_valid_index() for c in merged.columns]
    if any(s is None for s in starts):
        raise ValueError("Received an empty price series.")
    merged = merged.loc[max(starts):min(ends)].ffill().dropna(how="any")
    if merged.empty:
        raise ValueError("Input series have no overlapping date range.")
    merged.index.name = "date"
    return merged


# Human-readable labels for the ticker picker.
TICKER_LABELS: dict[str, str] = {
    "SPY": "S&P 500 — total return (gross)",
    "SP500": "S&P 500 — price index (no dividends)",
    "SP500TR": "S&P 500 — total return (gross)",
    "SP500NTR": "S&P 500 — total return (net of withholding tax)",
    "QQQ": "Nasdaq-100 proxy (synthetic)",
    "TLT": "20+yr Treasuries proxy (synthetic)",
    "GLD": "Gold proxy (synthetic)",
    "BTC": "Bitcoin proxy (synthetic)",
    "CASH": "Cash / T-bills (synthetic)",
}


def resolve_source(ticker: str) -> str:
    """Pick the data source for a single ticker: real CSV if bundled, else sample."""
    return "csv" if ticker.strip().upper() in REAL_SERIES else "sample"


def available_tickers() -> list[str]:
    """All selectable tickers: bundled real series first, then synthetic samples."""
    reals = list(REAL_SERIES.keys())
    samples = [t for t in SAMPLE_ASSETS if t not in REAL_SERIES]
    return reals + samples


def _full_series(ticker: str) -> pd.Series:
    """Load the complete (unsliced) price series for one ticker, real or sample."""
    ticker = ticker.strip().upper()
    if ticker in REAL_SERIES:
        s = _load_csv(ticker)
        if s is None:
            raise ValueError(f"Bundled data file missing for '{ticker}'.")
        return s.sort_index()
    sample = _sample_panel()
    if ticker in sample.columns:
        return sample[ticker]
    raise ValueError(f"Unknown ticker '{ticker}'.")


def _describe(ticker: str, s: pd.Series) -> dict:
    from .metrics import infer_periods_per_year

    s = s.dropna().sort_index()
    span_years = max((s.index[-1] - s.index[0]).days / 365.25, 1e-9)
    cagr = float((s.iloc[-1] / s.iloc[0]) ** (1.0 / span_years) - 1.0)
    ppy = infer_periods_per_year(s.index)
    vol = float(s.pct_change().dropna().std() * np.sqrt(ppy))
    real = ticker in REAL_SERIES
    return {
        "ticker": ticker,
        "label": TICKER_LABELS.get(ticker, ticker),
        "kind": "real" if real else "synthetic",
        "source": "csv" if real else "sample",
        "start": s.index[0].date().isoformat(),
        "end": s.index[-1].date().isoformat(),
        "rows": int(len(s)),
        "years": round(span_years, 1),
        "cagr": round(cagr, 4),
        "vol": round(vol, 4),
    }


@functools.lru_cache(maxsize=1)
def catalog() -> list[dict]:
    """Metadata for every selectable ticker (range, row count, CAGR, vol, kind)."""
    return [_describe(t, _full_series(t)) for t in available_tickers()]


def _load_csv(ticker: str) -> pd.Series | None:
    # Real datasets bundled with the repo take precedence over drop-in files.
    if ticker in REAL_SERIES:
        fname, col = REAL_SERIES[ticker]
        path = REAL_DATA_DIR / fname
        if path.exists():
            df = pd.read_csv(path, parse_dates=[0], index_col=0, na_values=["NA"])
            s = df[col].astype(float)
            s.name = ticker
            return s.dropna()

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
