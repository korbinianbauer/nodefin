"""Performance and risk metrics for equity curves and return series.

All functions accept a pandas Series of either an equity curve (price levels)
or periodic returns and annualise using an inferred number of periods per year.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def infer_periods_per_year(index: pd.Index) -> float:
    """Estimate how many observations occur per calendar year."""
    if len(index) < 3 or not isinstance(index, pd.DatetimeIndex):
        return 252.0
    span_days = (index[-1] - index[0]).days
    if span_days <= 0:
        return 252.0
    per_day = (len(index) - 1) / span_days
    obs_per_year = per_day * 365.25
    # Snap to common frequencies so labels look sane.
    for candidate in (252.0, 52.0, 12.0, 4.0, 1.0):
        if abs(obs_per_year - candidate) / candidate < 0.25:
            return candidate
    return obs_per_year


def returns_from_equity(equity: pd.Series) -> pd.Series:
    return equity.pct_change().dropna()


def equity_from_returns(returns: pd.Series, start: float = 1.0) -> pd.Series:
    return start * (1.0 + returns).cumprod()


def cagr(equity: pd.Series) -> float:
    equity = equity.dropna()
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return float("nan")
    ppy = infer_periods_per_year(equity.index)
    years = len(equity) / ppy
    if years <= 0:
        return float("nan")
    total = equity.iloc[-1] / equity.iloc[0]
    if total <= 0:
        return -1.0
    return float(total ** (1.0 / years) - 1.0)


def annual_volatility(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    ppy = infer_periods_per_year(returns.index)
    return float(returns.std(ddof=1) * np.sqrt(ppy))


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    ppy = infer_periods_per_year(returns.index)
    excess = returns - risk_free / ppy
    sd = excess.std(ddof=1)
    if sd == 0:
        return float("nan")
    return float(excess.mean() / sd * np.sqrt(ppy))


def sortino_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    ppy = infer_periods_per_year(returns.index)
    excess = returns - risk_free / ppy
    downside = excess[excess < 0]
    dd = np.sqrt((downside ** 2).mean()) if len(downside) else 0.0
    if dd == 0:
        return float("nan")
    return float(excess.mean() / dd * np.sqrt(ppy))


def drawdown_series(equity: pd.Series) -> pd.Series:
    equity = equity.dropna()
    running_max = equity.cummax()
    return equity / running_max - 1.0


def max_drawdown(equity: pd.Series) -> float:
    dd = drawdown_series(equity)
    return float(dd.min()) if len(dd) else float("nan")


def ulcer_index(equity: pd.Series) -> float:
    dd = drawdown_series(equity) * 100.0
    if len(dd) == 0:
        return float("nan")
    return float(np.sqrt((dd ** 2).mean()))


def calmar_ratio(equity: pd.Series) -> float:
    mdd = max_drawdown(equity)
    if mdd == 0 or np.isnan(mdd):
        return float("nan")
    return float(cagr(equity) / abs(mdd))


def summary(equity: pd.Series, risk_free: float = 0.0) -> dict:
    """Compute the standard metrics block for one equity curve."""
    equity = equity.dropna()
    rets = returns_from_equity(equity)
    return {
        "cagr": cagr(equity),
        "volatility": annual_volatility(rets),
        "sharpe": sharpe_ratio(rets, risk_free),
        "sortino": sortino_ratio(rets, risk_free),
        "max_drawdown": max_drawdown(equity),
        "ulcer_index": ulcer_index(equity),
        "calmar": calmar_ratio(equity),
        "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) > 1 else float("nan"),
        "start": str(equity.index[0].date()) if len(equity) else None,
        "end": str(equity.index[-1].date()) if len(equity) else None,
        "n_periods": int(len(equity)),
    }
