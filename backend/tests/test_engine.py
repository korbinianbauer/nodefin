import numpy as np
import pandas as pd
import pytest

from app.engine import graph, metrics
from app.engine.backtester import Portfolio, run_backtest
from app.engine.data import get_prices
from app.engine.nodes import all_specs
from app import templates


def test_node_registry_nonempty():
    types = {s.type for s in all_specs()}
    for required in {"data.prices", "leverage.daily", "portfolio.static",
                     "rebalance", "backtest", "montecarlo", "sweep", "metrics"}:
        assert required in types


def test_sample_data_offline():
    panel = get_prices(["SPY", "TLT"], source="sample")
    assert list(panel.columns) == ["SPY", "TLT"]
    assert len(panel) > 5000
    assert panel.isna().sum().sum() == 0


def test_metrics_on_known_series():
    idx = pd.bdate_range("2000-01-01", periods=252 * 4)
    eq = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    assert metrics.cagr(eq) > 0
    assert metrics.max_drawdown(eq) <= 0
    s = metrics.summary(eq)
    assert set(["cagr", "sharpe", "max_drawdown", "calmar"]).issubset(s)


def test_backtest_static_portfolio():
    panel = get_prices(["SPY", "TLT"], source="sample")
    pf = Portfolio(panel, {"SPY": 0.6, "TLT": 0.4}, {"frequency": "monthly"})
    res = run_backtest(pf)
    assert res["equity"].iloc[0] == pytest.approx(10_000.0)
    assert res["equity"].iloc[-1] > 0
    assert (res["weights"].sum(axis=1) - 1.0).abs().max() < 1e-6


def test_rebalance_threshold_creates_turnover():
    panel = get_prices(["SPY", "TLT"], source="sample")
    pf = Portfolio(panel, {"SPY": 0.5, "TLT": 0.5},
                   {"frequency": "none", "threshold": 0.05})
    res = run_backtest(pf)
    assert res["turnover"].sum() > 0


def test_leverage_amplifies_moves():
    from app.engine.nodes.transforms import _exec_leverage
    panel = get_prices(["SPY"], source="sample")
    lev = _exec_leverage({"multiplier": 3.0, "borrow_rate": 0.0,
                          "expense_ratio": 0.0, "rename": True}, {"prices": panel})["prices"]
    base_ret = panel["SPY"].pct_change().dropna()
    lev_ret = lev.iloc[:, 0].pct_change().dropna()
    # Leveraged daily vol should be roughly 3x.
    assert lev_ret.std() / base_ret.std() == pytest.approx(3.0, rel=0.05)


def test_graph_execution_hfea_template():
    t = templates.hfea()
    out = graph.execute(t["nodes"], t["edges"])
    assert all(s["status"] == "ok" for s in out["node_status"].values()), out["node_status"]
    met = out["results"]["met"]["metrics"]
    assert met["cagr"] is not None
    bt = out["results"]["bt"]["result"]
    assert bt["kind"] == "backtest"
    assert len(bt["equity"]["x"]) > 10


def test_graph_cycle_detected():
    nodes = [
        {"id": "a", "type": "rebalance"},
        {"id": "b", "type": "backtest"},
    ]
    edges = [
        {"source": "a", "sourcePort": "portfolio", "target": "b", "targetPort": "portfolio"},
        {"source": "b", "sourcePort": "result", "target": "a", "targetPort": "portfolio"},
    ]
    with pytest.raises(graph.GraphError):
        graph.topological_order(nodes, edges)


def test_validate_reports_type_mismatch():
    nodes = [
        {"id": "d", "type": "data.prices"},
        {"id": "bt", "type": "backtest"},
    ]
    # prices output into a portfolio input is a type mismatch
    edges = [{"source": "d", "sourcePort": "prices", "target": "bt", "targetPort": "portfolio"}]
    problems = graph.validate(nodes, edges)
    assert any("Incompatible" in p for p in problems)


def test_montecarlo_node():
    t = templates.zahlgraf_sweep()
    out = graph.execute(t["nodes"], t["edges"])
    mc = out["results"]["mc"]["result"]
    assert mc["kind"] == "montecarlo"
    assert len(mc["cagrs"]) == 500
    sweep = out["results"]["sweep"]["result"]
    assert sweep["kind"] == "sweep"
    assert sweep["metrics"]["n_windows"] > 0
