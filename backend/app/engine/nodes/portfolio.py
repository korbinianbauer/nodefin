"""Portfolio-construction and rebalancing nodes."""
from __future__ import annotations

import json

import numpy as np

from .. import data as data_layer
from ..backtester import Portfolio
from ..metrics import infer_periods_per_year
from .base import NodeSpec, ParamSpec, Port, register


def _parse_weights(raw) -> dict[str, float]:
    if isinstance(raw, dict):
        return {str(k).upper(): float(v) for k, v in raw.items()}
    if not raw:
        return {}
    text = str(raw).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return {str(k).upper(): float(v) for k, v in obj.items()}
    except json.JSONDecodeError:
        pass
    # Fallback: "SPY:0.6, TLT:0.4" or "SPY 60, TLT 40"
    weights: dict[str, float] = {}
    for part in text.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        sep = ":" if ":" in part else None
        if sep is None and " " in part:
            sep = " "
        if sep:
            k, v = part.split(sep, 1) if sep != " " else part.rsplit(" ", 1)
            weights[k.strip().upper()] = float(v.strip().rstrip("%"))
    return weights


def _coerce_weights(raw, columns: list[str]) -> dict[str, float]:
    """Build a name->weight map. A list is applied positionally to the input
    assets (in connector order); a dict/string is parsed by ticker name."""
    if isinstance(raw, list):
        out: dict[str, float] = {}
        for i, col in enumerate(columns):
            if i >= len(raw):
                break
            try:
                out[col] = float(raw[i])
            except (TypeError, ValueError):
                out[col] = 0.0
        return out
    return _parse_weights(raw)


def _exec_static(cfg: dict, inputs: dict) -> dict:
    panel = data_layer.merge_panels(inputs.get("prices"))
    weights = _coerce_weights(cfg.get("weights"), list(panel.columns))
    weights = {k: v for k, v in weights.items() if v}
    if not weights:
        # Default to equal weight over whatever columns exist.
        weights = {c: 1.0 for c in panel.columns}
    pf = Portfolio(prices=panel, weights=weights)
    return {"portfolio": pf}


register(NodeSpec(
    type="portfolio.static",
    category="Portfolio",
    label="Static Portfolio",
    description="Fixed target weights per asset. Weights are auto-normalised.",
    inputs=[Port("prices", "prices", "Prices", dynamic=True, count_param="n_inputs")],
    outputs=[Port("portfolio", "portfolio", "Portfolio")],
    params=[
        ParamSpec("n_inputs", "input_count", "Number of assets", default=2, min=1, max=12,
                  description="How many price inputs this portfolio combines."),
        ParamSpec("weights", "weights", "Weights", default=[60, 40],
                  description="Target weight per asset in %, should total 100."),
    ],
    execute=_exec_static,
))


def _exec_equal(cfg: dict, inputs: dict) -> dict:
    panel = data_layer.merge_panels(inputs.get("prices"))
    weights = {c: 1.0 for c in panel.columns}
    return {"portfolio": Portfolio(prices=panel, weights=weights)}


register(NodeSpec(
    type="portfolio.equal_weight",
    category="Portfolio",
    label="Equal Weight",
    description="Equal weight across every asset in the input panel.",
    inputs=[Port("prices", "prices", "Prices", dynamic=True, count_param="n_inputs")],
    outputs=[Port("portfolio", "portfolio", "Portfolio")],
    params=[
        ParamSpec("n_inputs", "input_count", "Number of assets", default=2, min=1, max=12,
                  description="How many price inputs this portfolio combines."),
    ],
    execute=_exec_equal,
))


def _exec_risk_parity(cfg: dict, inputs: dict) -> dict:
    """Inverse-volatility weights computed over a trailing lookback window."""
    panel = data_layer.merge_panels(inputs.get("prices"))
    lookback_years = float(cfg.get("lookback_years", 1.0))
    rets = panel.pct_change().dropna()
    ppy = infer_periods_per_year(panel.index)
    window = max(20, int(lookback_years * ppy))
    vol = rets.tail(window).std(ddof=1) * np.sqrt(ppy)
    vol = vol.replace(0, np.nan).dropna()
    if vol.empty:
        raise ValueError("Could not estimate volatilities for risk parity.")
    inv = 1.0 / vol
    weights = (inv / inv.sum()).to_dict()
    return {"portfolio": Portfolio(prices=panel, weights=weights)}


register(NodeSpec(
    type="portfolio.risk_parity",
    category="Portfolio",
    label="Risk Parity",
    description="Inverse-volatility allocation across the input assets.",
    inputs=[Port("prices", "prices", "Prices", dynamic=True, count_param="n_inputs")],
    outputs=[Port("portfolio", "portfolio", "Portfolio")],
    params=[
        ParamSpec("n_inputs", "input_count", "Number of assets", default=3, min=1, max=12,
                  description="How many price inputs this portfolio combines."),
        ParamSpec("lookback_years", "number", "Lookback (years)", default=1.0, min=0.1, max=10),
    ],
    execute=_exec_risk_parity,
))


def _exec_rebalance(cfg: dict, inputs: dict) -> dict:
    pf: Portfolio = inputs.get("portfolio")
    if pf is None:
        raise ValueError("Rebalance requires a portfolio input.")
    pf.rebalance = {
        "frequency": cfg.get("frequency", "quarterly"),
        "threshold": float(cfg.get("threshold", 0.0) or 0.0),
        "transaction_cost_bps": float(cfg.get("transaction_cost_bps", 0.0) or 0.0),
    }
    return {"portfolio": pf}


register(NodeSpec(
    type="rebalance",
    category="Rebalancing",
    label="Rebalance",
    description="Set the rebalancing rule (calendar and/or drift threshold) and "
                "transaction costs for the portfolio.",
    inputs=[Port("portfolio", "portfolio", "Portfolio")],
    outputs=[Port("portfolio", "portfolio", "Portfolio")],
    params=[
        ParamSpec("frequency", "select", "Frequency", default="quarterly",
                  options=["none", "daily", "weekly", "monthly", "quarterly", "annual"]),
        ParamSpec("threshold", "number", "Drift threshold", default=0.0, min=0.0, max=1.0, step=0.01,
                  description="Rebalance when any weight drifts this far from target (0 = off)."),
        ParamSpec("transaction_cost_bps", "number", "Cost (bps)", default=0.0, min=0, max=100),
    ],
    execute=_exec_rebalance,
))
