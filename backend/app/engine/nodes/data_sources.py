"""Data-source and synthetic-data nodes."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import data as data_layer
from .base import NodeSpec, ParamSpec, Port, register


def _exec_prices(cfg: dict, inputs: dict) -> dict:
    raw = cfg.get("tickers", "SPY")
    tickers = raw.split(",") if isinstance(raw, str) else list(raw)
    panel = data_layer.get_prices(
        tickers=tickers,
        source=cfg.get("source", "sample"),
        start=cfg.get("start") or None,
        end=cfg.get("end") or None,
    )
    return {"prices": panel}


register(NodeSpec(
    type="data.prices",
    category="Data Sources",
    label="Market Data",
    description="Load historical price levels for one or more tickers.",
    inputs=[],
    outputs=[Port("prices", "prices", "Prices")],
    params=[
        ParamSpec("tickers", "tickers", "Tickers", default="SPY,TLT",
                  description="Comma separated tickers (e.g. SPY,TLT,GLD)."),
        ParamSpec("source", "select", "Source", default="sample",
                  options=["sample", "yahoo", "csv"]),
        ParamSpec("start", "string", "Start date", default="",
                  description="YYYY-MM-DD (optional)."),
        ParamSpec("end", "string", "End date", default="",
                  description="YYYY-MM-DD (optional)."),
    ],
    execute=_exec_prices,
))


def _exec_gbm(cfg: dict, inputs: dict) -> dict:
    n_years = float(cfg.get("years", 30))
    ppy = 252
    n = int(n_years * ppy)
    drift = float(cfg.get("drift", 0.08))
    vol = float(cfg.get("volatility", 0.16))
    seed = int(cfg.get("seed", 42))
    p0 = float(cfg.get("start_price", 100.0))
    name = cfg.get("name", "GBM") or "GBM"

    rng = np.random.default_rng(seed)
    daily = (drift - 0.5 * vol ** 2) / ppy + vol / np.sqrt(ppy) * rng.standard_normal(n)
    prices = p0 * np.exp(np.cumsum(daily))
    idx = pd.bdate_range("2000-01-03", periods=n)
    panel = pd.DataFrame({name: prices}, index=idx)
    panel.index.name = "date"
    return {"prices": panel}


register(NodeSpec(
    type="data.synthetic_gbm",
    category="Data Sources",
    label="Synthetic GBM",
    description="Generate a Geometric Brownian Motion price path.",
    inputs=[],
    outputs=[Port("prices", "prices", "Prices")],
    params=[
        ParamSpec("name", "string", "Asset name", default="GBM"),
        ParamSpec("years", "number", "Years", default=30, min=1, max=100),
        ParamSpec("drift", "number", "Drift (annual)", default=0.08, step=0.01),
        ParamSpec("volatility", "number", "Volatility (annual)", default=0.16, step=0.01),
        ParamSpec("start_price", "number", "Start price", default=100.0),
        ParamSpec("seed", "int", "Seed", default=42),
    ],
    execute=_exec_gbm,
))
