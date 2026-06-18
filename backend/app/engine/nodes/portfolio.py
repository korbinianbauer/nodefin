"""Portfolio-construction and rebalancing nodes."""
from __future__ import annotations

import json

import numpy as np

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


def _exec_static(cfg: dict, inputs: dict) -> dict:
    panel = inputs.get("prices")
    if panel is None:
        raise ValueError("Static Portfolio requires a price input.")
    weights = _parse_weights(cfg.get("weights"))
    if not weights:
        # Default to equal weight over whatever columns exist.
        weights = {c: 1.0 for c in panel.columns}
    pf = Portfolio(prices=panel, weights=weights)
    return {"portfolio": pf}


register(NodeSpec(
    type="portfolio.static",
    category="Portfolio",
    label="Static Portfolio",
    description="Fixed target weights, e.g. {\"SPY\": 0.6, \"TLT\": 0.4}.",
    inputs=[Port("prices", "prices", "Prices")],
    outputs=[Port("portfolio", "portfolio", "Portfolio")],
    params=[
        ParamSpec("weights", "weights", "Weights", default='{"SPY": 0.6, "TLT": 0.4}',
                  description='JSON or "SPY:0.6, TLT:0.4". Auto-normalised.'),
    ],
    execute=_exec_static,
))


def _exec_equal(cfg: dict, inputs: dict) -> dict:
    panel = inputs.get("prices")
    if panel is None:
        raise ValueError("Equal Weight requires a price input.")
    weights = {c: 1.0 for c in panel.columns}
    return {"portfolio": Portfolio(prices=panel, weights=weights)}


register(NodeSpec(
    type="portfolio.equal_weight",
    category="Portfolio",
    label="Equal Weight",
    description="Equal weight across every asset in the input panel.",
    inputs=[Port("prices", "prices", "Prices")],
    outputs=[Port("portfolio", "portfolio", "Portfolio")],
    params=[],
    execute=_exec_equal,
))


def _exec_risk_parity(cfg: dict, inputs: dict) -> dict:
    """Inverse-volatility weights computed over a trailing lookback window."""
    panel = inputs.get("prices")
    if panel is None:
        raise ValueError("Risk Parity requires a price input.")
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
    inputs=[Port("prices", "prices", "Prices")],
    outputs=[Port("portfolio", "portfolio", "Portfolio")],
    params=[
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
