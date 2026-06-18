"""Simulation nodes: backtest, Monte Carlo, start-date sweep and metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import metrics as M
from ..backtester import Portfolio, run_backtest
from .base import NodeSpec, ParamSpec, Port, register


def _exec_backtest(cfg: dict, inputs: dict) -> dict:
    pf: Portfolio = inputs.get("portfolio")
    if pf is None:
        raise ValueError("Backtest requires a portfolio input.")
    result = run_backtest(pf, initial_capital=float(cfg.get("initial_capital", 10_000.0)))
    result["kind"] = "backtest"
    result["metrics"] = M.summary(result["equity"])
    return {"result": result}


register(NodeSpec(
    type="backtest",
    category="Simulation",
    label="Backtest",
    description="Run the portfolio over history; outputs equity curve, drawdown "
                "and summary metrics.",
    inputs=[Port("portfolio", "portfolio", "Portfolio")],
    outputs=[Port("result", "result", "Result")],
    params=[
        ParamSpec("initial_capital", "number", "Initial capital", default=10_000.0),
    ],
    execute=_exec_backtest,
))


def _block_bootstrap_returns(returns: pd.DataFrame, n: int, block: int, rng) -> pd.DataFrame:
    """Stationary-ish block bootstrap that preserves cross-asset structure."""
    m = len(returns)
    if m == 0:
        raise ValueError("No returns to bootstrap.")
    idx = []
    while len(idx) < n:
        start = rng.integers(0, m)
        idx.extend(range(start, min(start + block, m)))
    idx = idx[:n]
    sampled = returns.to_numpy()[idx]
    return pd.DataFrame(sampled, columns=returns.columns)


def _exec_montecarlo(cfg: dict, inputs: dict) -> dict:
    pf: Portfolio = inputs.get("portfolio")
    if pf is None:
        raise ValueError("Monte Carlo requires a portfolio input.")
    n_sims = int(cfg.get("n_sims", 500))
    method = cfg.get("method", "bootstrap")
    horizon_years = float(cfg.get("horizon_years", 20))
    block = int(cfg.get("block_size", 21))
    seed = int(cfg.get("seed", 7))
    initial = float(cfg.get("initial_capital", 10_000.0))

    prices = pf.prices.dropna(how="all").ffill().dropna()
    target = pf.normalized_weights()
    assets = [c for c in prices.columns if c in target]
    prices = prices[assets]
    w = np.array([target[a] for a in assets])

    asset_rets = prices.pct_change().dropna()
    ppy = M.infer_periods_per_year(prices.index)
    horizon = int(horizon_years * ppy)
    rng = np.random.default_rng(seed)

    if method == "gbm":
        mu = asset_rets.mean().to_numpy()
        cov = asset_rets.cov().to_numpy()
        chol = np.linalg.cholesky(cov + 1e-12 * np.eye(len(assets)))

    finals = np.empty(n_sims)
    cagrs = np.empty(n_sims)
    paths = np.empty((n_sims, horizon + 1))
    years = horizon / ppy
    for i in range(n_sims):
        if method == "gbm":
            z = rng.standard_normal((horizon, len(assets)))
            sim = mu + z @ chol.T
        else:
            sim = _block_bootstrap_returns(asset_rets, horizon, block, rng).to_numpy()
        port_ret = sim @ w
        equity = initial * np.cumprod(np.concatenate([[1.0], 1.0 + port_ret]))
        paths[i] = equity
        finals[i] = equity[-1]
        cagrs[i] = (equity[-1] / initial) ** (1.0 / years) - 1.0 if years > 0 else np.nan

    pct = [5, 25, 50, 75, 95]
    percentile_paths = {f"p{p}": np.percentile(paths, p, axis=0) for p in pct}
    return {
        "result": {
            "kind": "montecarlo",
            "method": method,
            "n_sims": n_sims,
            "horizon_years": horizon_years,
            "final_values": finals,
            "cagrs": cagrs,
            "percentile_paths": percentile_paths,
            "metrics": {
                "median_cagr": float(np.nanmedian(cagrs)),
                "p5_cagr": float(np.nanpercentile(cagrs, 5)),
                "p95_cagr": float(np.nanpercentile(cagrs, 95)),
                "median_final": float(np.nanmedian(finals)),
                "prob_loss": float(np.mean(finals < initial)),
            },
        }
    }


register(NodeSpec(
    type="montecarlo",
    category="Simulation",
    label="Monte Carlo",
    description="Resample returns (block bootstrap or parametric GBM) to build a "
                "distribution of outcomes.",
    inputs=[Port("portfolio", "portfolio", "Portfolio")],
    outputs=[Port("result", "result", "Result")],
    params=[
        ParamSpec("n_sims", "int", "Simulations", default=500, min=50, max=5000),
        ParamSpec("method", "select", "Method", default="bootstrap",
                  options=["bootstrap", "gbm"]),
        ParamSpec("horizon_years", "number", "Horizon (years)", default=20, min=1, max=60),
        ParamSpec("block_size", "int", "Block size (days)", default=21, min=1, max=252),
        ParamSpec("initial_capital", "number", "Initial capital", default=10_000.0),
        ParamSpec("seed", "int", "Seed", default=7),
    ],
    execute=_exec_montecarlo,
))


def _exec_sweep(cfg: dict, inputs: dict) -> dict:
    """Run the backtest from a range of start years (Zahlgraf-style sweep)."""
    pf: Portfolio = inputs.get("portfolio")
    if pf is None:
        raise ValueError("Start-Date Sweep requires a portfolio input.")
    prices = pf.prices.dropna(how="all").ffill().dropna()
    if prices.empty:
        raise ValueError("No price data for sweep.")
    first_year = int(cfg.get("start_year", prices.index[0].year))
    last_year = int(cfg.get("end_year", prices.index[-1].year - 1))
    min_years = float(cfg.get("min_horizon_years", 3))

    rows = []
    for yr in range(first_year, last_year + 1):
        window = prices[prices.index >= pd.Timestamp(year=yr, month=1, day=1)]
        if len(window) < 2:
            continue
        span_years = (window.index[-1] - window.index[0]).days / 365.25
        if span_years < min_years:
            continue
        sub = Portfolio(prices=window, weights=pf.weights, rebalance=pf.rebalance)
        try:
            res = run_backtest(sub)
        except ValueError:
            continue
        m = M.summary(res["equity"])
        rows.append({
            "start_year": yr,
            "cagr": m["cagr"],
            "max_drawdown": m["max_drawdown"],
            "sharpe": m["sharpe"],
            "calmar": m["calmar"],
            "final_multiple": float(res["equity"].iloc[-1] / res["equity"].iloc[0]),
            "years": round(span_years, 1),
        })
    if not rows:
        raise ValueError("Sweep produced no valid windows (try a smaller min horizon).")
    table = pd.DataFrame(rows)
    cagrs = table["cagr"].to_numpy()
    return {
        "result": {
            "kind": "sweep",
            "table": table,
            "metrics": {
                "median_cagr": float(np.nanmedian(cagrs)),
                "worst_cagr": float(np.nanmin(cagrs)),
                "best_cagr": float(np.nanmax(cagrs)),
                "worst_max_drawdown": float(table["max_drawdown"].min()),
                "n_windows": int(len(table)),
            },
        }
    }


register(NodeSpec(
    type="sweep",
    category="Simulation",
    label="Start-Date Sweep",
    description="Backtest the portfolio from many different start years to assess "
                "regime/start-date sensitivity.",
    inputs=[Port("portfolio", "portfolio", "Portfolio")],
    outputs=[Port("result", "result", "Result")],
    params=[
        ParamSpec("start_year", "int", "First start year", default=1990),
        ParamSpec("end_year", "int", "Last start year", default=2020),
        ParamSpec("min_horizon_years", "number", "Min horizon (years)", default=3, min=1, max=30),
    ],
    execute=_exec_sweep,
))


def _exec_metrics(cfg: dict, inputs: dict) -> dict:
    res = inputs.get("result")
    if res is None:
        raise ValueError("Metrics requires a result input.")
    if "metrics" in res:
        return {"metrics": res["metrics"]}
    if "equity" in res:
        return {"metrics": M.summary(res["equity"])}
    raise ValueError("Result has no equity curve to compute metrics from.")


register(NodeSpec(
    type="metrics",
    category="Metrics",
    label="Metrics",
    description="Compute CAGR, Sharpe, Sortino, max drawdown, Ulcer and Calmar.",
    inputs=[Port("result", "result", "Result")],
    outputs=[Port("metrics", "metrics", "Metrics")],
    params=[],
    execute=_exec_metrics,
))
