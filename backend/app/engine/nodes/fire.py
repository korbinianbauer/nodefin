"""Withdrawal / FIRE simulation node (safe-withdrawal-rate style)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import metrics as M
from ..backtester import Portfolio, run_backtest
from .base import NodeSpec, ParamSpec, Port, register


_FREQ = {"monthly": ("ME", 12.0), "quarterly": ("QE", 4.0), "annual": ("YE", 1.0)}


def _exec_savings_plan(cfg: dict, inputs: dict) -> dict:
    pf: Portfolio = inputs.get("portfolio")
    if pf is None:
        raise ValueError("Savings Plan requires a portfolio input.")
    lump = float(cfg.get("initial_lump_sum", 10_000.0) or 0.0)
    contribution = float(cfg.get("contribution", 500.0) or 0.0)
    annual_increase = float(cfg.get("annual_increase", 0.0) or 0.0)
    freq = str(cfg.get("frequency", "monthly") or "monthly").lower()
    rule, ppy = _FREQ.get(freq, _FREQ["monthly"])

    base = run_backtest(pf)
    port_ret = base["returns"]
    periodic = (1.0 + port_ret).resample(rule).prod() - 1.0
    inc_per_period = (1.0 + annual_increase) ** (1.0 / ppy) - 1.0

    value = lump
    invested = lump
    contrib = contribution
    contribs: list[float] = []
    start = pf.prices.index[0]
    dates = [start]
    values = [value]
    contributed = [invested]
    for date, r in periodic.items():
        value = value * (1.0 + r) + contrib
        invested += contrib
        contribs.append(contrib)
        dates.append(date)
        values.append(value)
        contributed.append(invested)
        contrib *= 1.0 + inc_per_period

    eq = pd.Series(values, index=pd.DatetimeIndex(dates), name="equity")
    contr = pd.Series(contributed, index=pd.DatetimeIndex(dates), name="contributed")
    profit = value - invested
    years = (eq.index[-1] - eq.index[0]).days / 365.25

    # Money-weighted return via Modified Dietz: each contribution is weighted by
    # the fraction of the horizon it stayed invested. Robust and iteration-free.
    n = len(contribs)
    weighted_contrib = sum(c * (n - i) / n for i, c in enumerate(contribs, start=1)) if n else 0.0
    avg_capital = lump + weighted_contrib
    if avg_capital > 0 and years > 0:
        dietz = profit / avg_capital
        mwr = (1.0 + dietz) ** (1.0 / years) - 1.0 if dietz > -1.0 else float("nan")
    else:
        mwr = float("nan")

    return {
        "result": {
            "kind": "savings",
            "equity": eq,
            "contributed": contr,
            "metrics": {
                "initial_lump_sum": round(lump, 2),
                "contribution": round(contribution, 2),
                "frequency": freq,
                "total_invested": round(invested, 2),
                "final_value": round(value, 2),
                "profit": round(profit, 2),
                "total_gain": profit / invested if invested else float("nan"),
                "money_weighted_return": mwr,
                "years": round(years, 1),
            },
        }
    }


register(NodeSpec(
    type="savings_plan",
    category="FIRE",
    label="Savings Plan",
    description="Accumulation: an initial lump sum plus recurring contributions "
                "(optionally rising each year). Outputs the wealth curve, total "
                "invested and money-weighted (IRR) return.",
    inputs=[Port("portfolio", "portfolio", "Portfolio")],
    outputs=[Port("result", "result", "Result")],
    params=[
        ParamSpec("initial_lump_sum", "number", "Initial lump sum", default=10_000.0, min=0,
                  description="One-off investment at the start (0 for a pure savings plan)."),
        ParamSpec("contribution", "number", "Contribution", default=500.0, min=0,
                  description="Recurring amount added each period."),
        ParamSpec("frequency", "select", "Frequency", default="monthly",
                  options=["monthly", "quarterly", "annual"]),
        ParamSpec("annual_increase", "number", "Annual increase", default=0.0, min=0, max=1, step=0.005,
                  description="Yearly step-up of the contribution (e.g. 0.03 = +3%/yr)."),
    ],
    execute=_exec_savings_plan,
))


def _exec_withdrawal(cfg: dict, inputs: dict) -> dict:
    pf: Portfolio = inputs.get("portfolio")
    if pf is None:
        raise ValueError("Withdrawal requires a portfolio input.")
    initial = float(cfg.get("initial_capital", 1_000_000.0))
    rate = float(cfg.get("withdrawal_rate", 0.04))
    inflation = float(cfg.get("inflation", 0.025))

    base = run_backtest(pf, initial_capital=initial)
    port_ret = base["returns"]
    ppy = M.infer_periods_per_year(pf.prices.index)
    monthly_factor = 12.0  # withdraw monthly
    per_period_withdrawal = initial * rate / monthly_factor
    infl_per_step = (1.0 + inflation) ** (1.0 / monthly_factor) - 1.0

    # Step through monthly to model depletion realistically.
    monthly = (1.0 + port_ret).resample("ME").prod() - 1.0
    value = initial
    withdrawal = per_period_withdrawal
    equity = []
    depleted_at = None
    for date, r in monthly.items():
        value = value * (1.0 + r) - withdrawal
        withdrawal *= 1.0 + infl_per_step * 1.0
        if value <= 0 and depleted_at is None:
            value = 0.0
            depleted_at = str(date.date())
        equity.append((date, value))

    eq = pd.Series({d: v for d, v in equity}, name="equity")
    years = len(eq) / 12.0
    return {
        "result": {
            "kind": "withdrawal",
            "equity": eq,
            "metrics": {
                "withdrawal_rate": rate,
                "final_value": float(eq.iloc[-1]) if len(eq) else 0.0,
                "depleted": depleted_at is not None,
                "depleted_at": depleted_at,
                "survived_years": round(years, 1),
                "real_terminal_multiple": float(eq.iloc[-1] / initial) if len(eq) else 0.0,
            },
        }
    }


register(NodeSpec(
    type="withdrawal",
    category="FIRE",
    label="Withdrawal (FIRE)",
    description="Model retirement withdrawals (e.g. 4% rule) with inflation "
                "adjustment and capital-depletion tracking.",
    inputs=[Port("portfolio", "portfolio", "Portfolio")],
    outputs=[Port("result", "result", "Result")],
    params=[
        ParamSpec("initial_capital", "number", "Initial capital", default=1_000_000.0),
        ParamSpec("withdrawal_rate", "number", "Withdrawal rate", default=0.04, min=0.0, max=0.2, step=0.005),
        ParamSpec("inflation", "number", "Inflation (annual)", default=0.025, step=0.005),
    ],
    execute=_exec_withdrawal,
))
