"""Pre-built strategy templates as ready-to-run graphs.

Each template returns a graph (nodes + edges) using the same schema the frontend
produces, so the API can hand them straight to the engine or the editor.
"""
from __future__ import annotations


def _node(nid, ntype, label, x, y, config=None):
    return {
        "id": nid, "type": ntype, "label": label,
        "position": {"x": x, "y": y}, "config": config or {},
    }


def _edge(s, sp, t, tp):
    return {"id": f"{s}:{sp}->{t}:{tp}", "source": s, "sourcePort": sp,
            "target": t, "targetPort": tp}


def hfea() -> dict:
    nodes = [
        _node("data", "data.prices", "SPY + TLT", 0, 120, {"tickers": "SPY,TLT", "source": "sample"}),
        _node("lev", "leverage.daily", "3x Leverage", 280, 120,
              {"multiplier": 3.0, "borrow_rate": 0.03, "expense_ratio": 0.009, "rename": False}),
        _node("pf", "portfolio.static", "55/45", 560, 120,
              {"weights": '{"SPY": 0.55, "TLT": 0.45}'}),
        _node("reb", "rebalance", "Quarterly", 820, 120, {"frequency": "quarterly"}),
        _node("bt", "backtest", "Backtest", 1080, 120, {}),
        _node("met", "metrics", "Metrics", 1340, 120, {}),
    ]
    edges = [
        _edge("data", "prices", "lev", "prices"),
        _edge("lev", "prices", "pf", "prices"),
        _edge("pf", "portfolio", "reb", "portfolio"),
        _edge("reb", "portfolio", "bt", "portfolio"),
        _edge("bt", "result", "met", "result"),
    ]
    return {"name": "HFEA (3x SPY / TLT)", "nodes": nodes, "edges": edges}


def sixty_forty() -> dict:
    nodes = [
        _node("data", "data.prices", "SPY + TLT", 0, 120, {"tickers": "SPY,TLT", "source": "sample"}),
        _node("pf", "portfolio.static", "60/40", 280, 120, {"weights": '{"SPY": 0.6, "TLT": 0.4}'}),
        _node("reb", "rebalance", "Annual", 560, 120, {"frequency": "annual"}),
        _node("bt", "backtest", "Backtest", 840, 120, {}),
        _node("met", "metrics", "Metrics", 1100, 120, {}),
    ]
    edges = [
        _edge("data", "prices", "pf", "prices"),
        _edge("pf", "portfolio", "reb", "portfolio"),
        _edge("reb", "portfolio", "bt", "portfolio"),
        _edge("bt", "result", "met", "result"),
    ]
    return {"name": "60/40 Portfolio", "nodes": nodes, "edges": edges}


def permanent_portfolio() -> dict:
    nodes = [
        _node("data", "data.prices", "SPY/TLT/GLD/CASH", 0, 120,
              {"tickers": "SPY,TLT,GLD,CASH", "source": "sample"}),
        _node("pf", "portfolio.static", "25/25/25/25", 300, 120,
              {"weights": '{"SPY": 0.25, "TLT": 0.25, "GLD": 0.25, "CASH": 0.25}'}),
        _node("reb", "rebalance", "Annual", 600, 120, {"frequency": "annual"}),
        _node("bt", "backtest", "Backtest", 880, 120, {}),
        _node("met", "metrics", "Metrics", 1140, 120, {}),
    ]
    edges = [
        _edge("data", "prices", "pf", "prices"),
        _edge("pf", "portfolio", "reb", "portfolio"),
        _edge("reb", "portfolio", "bt", "portfolio"),
        _edge("bt", "result", "met", "result"),
    ]
    return {"name": "Permanent Portfolio", "nodes": nodes, "edges": edges}


def risk_parity() -> dict:
    nodes = [
        _node("data", "data.prices", "Multi-asset", 0, 120,
              {"tickers": "SPY,TLT,GLD", "source": "sample"}),
        _node("pf", "portfolio.risk_parity", "Risk Parity", 300, 120, {"lookback_years": 1.0}),
        _node("reb", "rebalance", "Monthly", 600, 120, {"frequency": "monthly"}),
        _node("bt", "backtest", "Backtest", 880, 120, {}),
        _node("met", "metrics", "Metrics", 1140, 120, {}),
    ]
    edges = [
        _edge("data", "prices", "pf", "prices"),
        _edge("pf", "portfolio", "reb", "portfolio"),
        _edge("reb", "portfolio", "bt", "portfolio"),
        _edge("bt", "result", "met", "result"),
    ]
    return {"name": "Risk Parity", "nodes": nodes, "edges": edges}


def zahlgraf_sweep() -> dict:
    nodes = [
        _node("data", "data.prices", "SPY + TLT", 0, 120, {"tickers": "SPY,TLT", "source": "sample"}),
        _node("lev", "leverage.daily", "3x Leverage", 280, 120,
              {"multiplier": 3.0, "rename": False}),
        _node("pf", "portfolio.static", "55/45", 560, 120, {"weights": '{"SPY": 0.55, "TLT": 0.45}'}),
        _node("reb", "rebalance", "Quarterly", 820, 60, {"frequency": "quarterly"}),
        _node("sweep", "sweep", "Start-Date Sweep", 1080, 30,
              {"start_year": 1990, "end_year": 2020, "min_horizon_years": 5}),
        _node("mc", "montecarlo", "Monte Carlo", 1080, 200,
              {"n_sims": 500, "method": "bootstrap", "horizon_years": 20}),
    ]
    edges = [
        _edge("data", "prices", "lev", "prices"),
        _edge("lev", "prices", "pf", "prices"),
        _edge("pf", "portfolio", "reb", "portfolio"),
        _edge("reb", "portfolio", "sweep", "portfolio"),
        _edge("reb", "portfolio", "mc", "portfolio"),
    ]
    return {"name": "Zahlgraf Sweep + Monte Carlo", "nodes": nodes, "edges": edges}


TEMPLATES = {
    "hfea": hfea,
    "sixty_forty": sixty_forty,
    "permanent_portfolio": permanent_portfolio,
    "risk_parity": risk_parity,
    "zahlgraf_sweep": zahlgraf_sweep,
}


def list_templates() -> list[dict]:
    return [{"id": k, "name": v()["name"]} for k, v in TEMPLATES.items()]


def get_template(template_id: str) -> dict:
    if template_id not in TEMPLATES:
        raise KeyError(f"Unknown template: {template_id}")
    return TEMPLATES[template_id]()
