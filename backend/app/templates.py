"""Pre-built strategy templates as ready-to-run graphs.

Each template returns a graph (nodes + edges) using the same schema the frontend
produces, so the API can hand them straight to the engine or the editor.

Market Data nodes emit a single ticker each. Portfolio-construction nodes accept
multiple price inputs, so multi-asset strategies wire several source (or leverage)
nodes straight into the portfolio node.
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


def _sources(tickers, y0=40, dy=120):
    """One Market Data node per ticker. Returns (nodes, source_ids)."""
    nodes, ids = [], []
    for i, tk in enumerate(tickers):
        nid = f"src_{tk.lower()}"
        nodes.append(_node(nid, "data.prices", tk, 0, y0 + i * dy, {"ticker": tk}))
        ids.append(nid)
    return nodes, ids


def hfea() -> dict:
    src_nodes, srcs = _sources(["SPY", "TLT"])
    lev_cfg = {"multiplier": 3.0, "borrow_rate": 0.03, "expense_ratio": 0.009, "rename": False}
    levs = [_node(f"lev_{s}", "leverage.daily", "3x Leverage", 260, 40 + i * 120, dict(lev_cfg))
            for i, s in enumerate(srcs)]
    nodes = src_nodes + levs + [
        _node("pf", "portfolio.static", "55/45", 520, 100, {"n_inputs": 2, "weights": [55, 45]}),
        _node("reb", "rebalance", "Quarterly", 780, 100, {"frequency": "quarterly"}),
        _node("bt", "backtest", "Backtest", 1040, 100, {}),
        _node("met", "metrics", "Metrics", 1300, 100, {}),
    ]
    edges = (
        [_edge(s, "prices", f"lev_{s}", "prices") for s in srcs]
        + [_edge(f"lev_{s}", "prices", "pf", f"prices.{i}") for i, s in enumerate(srcs)]
        + [
            _edge("pf", "portfolio", "reb", "portfolio"),
            _edge("reb", "portfolio", "bt", "portfolio"),
            _edge("bt", "result", "met", "result"),
        ]
    )
    return {"name": "HFEA (3x SPY / TLT)", "nodes": nodes, "edges": edges}


def sixty_forty() -> dict:
    src_nodes, srcs = _sources(["SPY", "TLT"])
    nodes = src_nodes + [
        _node("pf", "portfolio.static", "60/40", 280, 100, {"n_inputs": 2, "weights": [60, 40]}),
        _node("reb", "rebalance", "Annual", 540, 100, {"frequency": "annual"}),
        _node("bt", "backtest", "Backtest", 800, 100, {}),
        _node("met", "metrics", "Metrics", 1060, 100, {}),
    ]
    edges = [_edge(s, "prices", "pf", f"prices.{i}") for i, s in enumerate(srcs)] + [
        _edge("pf", "portfolio", "reb", "portfolio"),
        _edge("reb", "portfolio", "bt", "portfolio"),
        _edge("bt", "result", "met", "result"),
    ]
    return {"name": "60/40 Portfolio", "nodes": nodes, "edges": edges}


def permanent_portfolio() -> dict:
    src_nodes, srcs = _sources(["SPY", "TLT", "GLD", "CASH"])
    nodes = src_nodes + [
        _node("pf", "portfolio.static", "25/25/25/25", 280, 220,
              {"n_inputs": 4, "weights": [25, 25, 25, 25]}),
        _node("reb", "rebalance", "Annual", 540, 220, {"frequency": "annual"}),
        _node("bt", "backtest", "Backtest", 800, 220, {}),
        _node("met", "metrics", "Metrics", 1060, 220, {}),
    ]
    edges = [_edge(s, "prices", "pf", f"prices.{i}") for i, s in enumerate(srcs)] + [
        _edge("pf", "portfolio", "reb", "portfolio"),
        _edge("reb", "portfolio", "bt", "portfolio"),
        _edge("bt", "result", "met", "result"),
    ]
    return {"name": "Permanent Portfolio", "nodes": nodes, "edges": edges}


def risk_parity() -> dict:
    src_nodes, srcs = _sources(["SPY", "TLT", "GLD"])
    nodes = src_nodes + [
        _node("pf", "portfolio.risk_parity", "Risk Parity", 280, 160, {"n_inputs": 3, "lookback_years": 1.0}),
        _node("reb", "rebalance", "Monthly", 540, 160, {"frequency": "monthly"}),
        _node("bt", "backtest", "Backtest", 800, 160, {}),
        _node("met", "metrics", "Metrics", 1060, 160, {}),
    ]
    edges = [_edge(s, "prices", "pf", f"prices.{i}") for i, s in enumerate(srcs)] + [
        _edge("pf", "portfolio", "reb", "portfolio"),
        _edge("reb", "portfolio", "bt", "portfolio"),
        _edge("bt", "result", "met", "result"),
    ]
    return {"name": "Risk Parity", "nodes": nodes, "edges": edges}


def zahlgraf_sweep() -> dict:
    src_nodes, srcs = _sources(["SPY", "TLT"])
    levs = [_node(f"lev_{s}", "leverage.daily", "3x Leverage", 260, 40 + i * 120,
                  {"multiplier": 3.0, "rename": False})
            for i, s in enumerate(srcs)]
    nodes = src_nodes + levs + [
        _node("pf", "portfolio.static", "55/45", 520, 100, {"n_inputs": 2, "weights": [55, 45]}),
        _node("reb", "rebalance", "Quarterly", 780, 100, {"frequency": "quarterly"}),
        _node("sweep", "sweep", "Start-Date Sweep", 1040, 30,
              {"start_year": 1990, "end_year": 2020, "min_horizon_years": 5}),
        _node("mc", "montecarlo", "Monte Carlo", 1040, 200,
              {"n_sims": 500, "method": "bootstrap", "horizon_years": 20}),
    ]
    edges = (
        [_edge(s, "prices", f"lev_{s}", "prices") for s in srcs]
        + [_edge(f"lev_{s}", "prices", "pf", f"prices.{i}") for i, s in enumerate(srcs)]
        + [
            _edge("pf", "portfolio", "reb", "portfolio"),
            _edge("reb", "portfolio", "sweep", "portfolio"),
            _edge("reb", "portfolio", "mc", "portfolio"),
        ]
    )
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
