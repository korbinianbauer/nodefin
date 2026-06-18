"""Withdrawal / FIRE simulation node (safe-withdrawal-rate style)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import metrics as M
from ..backtester import Portfolio, run_backtest
from .base import NodeSpec, ParamSpec, Port, register


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
