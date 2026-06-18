"""Core portfolio simulation loop.

A portfolio is described by a panel of asset price levels, a set of target
weights, and a rebalancing rule. ``run_backtest`` walks the time axis, lets
weights drift with returns between rebalances, snaps them back to target on
rebalance dates, and accounts for transaction costs on the resulting turnover.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Portfolio:
    """A buildable portfolio: an asset price panel plus weights and a rule."""

    prices: pd.DataFrame
    weights: dict[str, float]
    rebalance: dict = field(default_factory=lambda: {"frequency": "monthly"})

    def normalized_weights(self) -> dict[str, float]:
        cols = [c for c in self.weights if c in self.prices.columns]
        w = {c: float(self.weights[c]) for c in cols}
        total = sum(w.values())
        if total <= 0:
            n = len(self.prices.columns)
            return {c: 1.0 / n for c in self.prices.columns}
        return {c: v / total for c, v in w.items()}


def _rebalance_mask(index: pd.DatetimeIndex, frequency: str) -> np.ndarray:
    """Boolean mask marking the first trading day of each rebalance period."""
    freq = (frequency or "none").lower()
    mask = np.zeros(len(index), dtype=bool)
    if freq in ("none", "never", "buy_and_hold", "buyhold"):
        return mask
    if freq == "daily":
        mask[:] = True
        return mask

    period_map = {
        "weekly": index.isocalendar().week.to_numpy(),
        "monthly": index.month.to_numpy(),
        "quarterly": index.quarter.to_numpy(),
        "annual": index.year.to_numpy(),
        "yearly": index.year.to_numpy(),
    }
    if freq not in period_map:
        freq = "monthly"
    period = period_map[freq]
    year = index.year.to_numpy()
    # Mark the row whenever (year, period) changes versus the previous row.
    key = year * 1000 + period
    changed = np.empty(len(index), dtype=bool)
    changed[0] = False  # first row handled as the initial allocation
    changed[1:] = key[1:] != key[:-1]
    return changed


def run_backtest(
    portfolio: Portfolio,
    initial_capital: float = 10_000.0,
) -> dict:
    """Simulate the portfolio and return equity, returns, drawdown and turnover."""
    prices = portfolio.prices.dropna(how="all").ffill().dropna()
    if prices.empty or len(prices) < 2:
        raise ValueError("Not enough price data to run a backtest.")

    target = portfolio.normalized_weights()
    assets = [c for c in prices.columns if c in target]
    if not assets:
        raise ValueError("Portfolio has no weights matching the price columns.")
    prices = prices[assets]
    target_vec = np.array([target[a] for a in assets], dtype=float)

    reb = portfolio.rebalance or {}
    frequency = reb.get("frequency", "monthly")
    threshold = float(reb.get("threshold", 0.0) or 0.0)
    cost_bps = float(reb.get("transaction_cost_bps", 0.0) or 0.0)

    asset_returns = prices.pct_change().fillna(0.0).to_numpy()
    index = prices.index
    scheduled = _rebalance_mask(index, frequency)

    n = len(index)
    equity = np.empty(n, dtype=float)
    turnover = np.zeros(n, dtype=float)
    weight_hist = np.empty((n, len(assets)), dtype=float)

    value = float(initial_capital)
    weights = target_vec.copy()
    equity[0] = value
    weight_hist[0] = weights

    for t in range(1, n):
        # Drift weights with the day's asset returns.
        growth = 1.0 + asset_returns[t]
        port_growth = float(weights @ growth)
        weights = weights * growth / port_growth if port_growth != 0 else weights
        value *= port_growth

        do_rebalance = scheduled[t]
        if threshold > 0:
            drift = np.abs(weights - target_vec).max()
            do_rebalance = do_rebalance or drift >= threshold

        if do_rebalance:
            trade = np.abs(target_vec - weights).sum()
            turnover[t] = trade
            value *= 1.0 - cost_bps / 10_000.0 * trade
            weights = target_vec.copy()

        equity[t] = value
        weight_hist[t] = weights

    equity_s = pd.Series(equity, index=index, name="equity")
    returns_s = equity_s.pct_change().dropna()
    running_max = equity_s.cummax()
    drawdown_s = equity_s / running_max - 1.0
    weights_df = pd.DataFrame(weight_hist, index=index, columns=assets)

    return {
        "equity": equity_s,
        "returns": returns_s,
        "drawdown": drawdown_s,
        "weights": weights_df,
        "turnover": pd.Series(turnover, index=index, name="turnover"),
    }
