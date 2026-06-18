"""Leverage and price-panel transform nodes."""
from __future__ import annotations

from ..metrics import infer_periods_per_year
from .base import NodeSpec, ParamSpec, Port, register


def _exec_leverage(cfg: dict, inputs: dict) -> dict:
    """Simulate a daily-reset leveraged version of the input series.

    This is the HFEA core: each day's underlying return is multiplied, then a
    daily slice of the annual financing cost (borrow on the borrowed notional)
    and the fund expense ratio is deducted. Output columns are renamed with a
    leverage suffix unless ``rename`` is disabled.
    """
    panel = inputs.get("prices")
    if panel is None:
        raise ValueError("Leverage node requires a price input.")
    mult = float(cfg.get("multiplier", 3.0))
    borrow = float(cfg.get("borrow_rate", 0.03))
    expense = float(cfg.get("expense_ratio", 0.009))
    rename = bool(cfg.get("rename", True))

    panel = panel.sort_index().ffill().dropna(how="all")
    ppy = infer_periods_per_year(panel.index)
    daily_cost = (borrow * max(0.0, mult - 1.0) + expense) / ppy

    underlying_ret = panel.pct_change()
    lev_ret = underlying_ret * mult - daily_cost
    lev_ret.iloc[0] = 0.0
    lev_prices = (1.0 + lev_ret).cumprod()
    # Rebase to the original starting price for readability.
    lev_prices = lev_prices * panel.iloc[0]

    if rename:
        lev_prices.columns = [f"{c}_{mult:g}x" for c in lev_prices.columns]
    lev_prices.index.name = "date"
    return {"prices": lev_prices}


register(NodeSpec(
    type="leverage.daily",
    category="Leverage",
    label="Daily Leverage",
    description="Simulate a daily-reset leveraged ETF (e.g. 3x) with financing "
                "and expense costs. Use to model UPRO/TMF before inception.",
    inputs=[Port("prices", "prices", "Prices")],
    outputs=[Port("prices", "prices", "Leveraged")],
    params=[
        ParamSpec("multiplier", "number", "Leverage", default=3.0, min=1.0, max=5.0, step=0.5),
        ParamSpec("borrow_rate", "number", "Borrow rate (annual)", default=0.03, step=0.005),
        ParamSpec("expense_ratio", "number", "Expense ratio (annual)", default=0.009, step=0.001),
        ParamSpec("rename", "bool", "Rename columns", default=True),
    ],
    execute=_exec_leverage,
))
