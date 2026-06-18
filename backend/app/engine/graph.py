"""Graph execution engine: validation, topological sort and execution."""
from __future__ import annotations

from collections import defaultdict, deque

import numpy as np
import pandas as pd

from .nodes import base


class GraphError(Exception):
    """Raised for structural problems (cycles, missing inputs, bad types)."""


def _index_nodes(nodes: list[dict]) -> dict[str, dict]:
    by_id = {}
    for n in nodes:
        if "id" not in n or "type" not in n:
            raise GraphError("Each node needs an 'id' and a 'type'.")
        if n["id"] in by_id:
            raise GraphError(f"Duplicate node id: {n['id']}")
        by_id[n["id"]] = n
    return by_id


def validate(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Return a list of human-readable validation warnings/errors (empty = ok)."""
    problems: list[str] = []
    by_id = _index_nodes(nodes)

    for n in nodes:
        try:
            base.get_spec(n["type"])
        except KeyError as e:
            problems.append(str(e))

    # Edge endpoints exist and ports are type-compatible.
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s not in by_id or t not in by_id:
            problems.append(f"Edge references unknown node: {e}")
            continue
        try:
            sspec = base.get_spec(by_id[s]["type"])
            tspec = base.get_spec(by_id[t]["type"])
        except KeyError:
            continue
        sport = next((p for p in sspec.outputs if p.name == e.get("sourcePort", "")), None)
        tport = next((p for p in tspec.inputs if p.name == e.get("targetPort", "")), None)
        if sport is None:
            problems.append(f"Node {s} has no output port '{e.get('sourcePort')}'.")
        if tport is None:
            problems.append(f"Node {t} has no input port '{e.get('targetPort')}'.")
        if sport and tport and sport.kind != tport.kind:
            problems.append(
                f"Incompatible connection {s}.{sport.name} ({sport.kind}) -> "
                f"{t}.{tport.name} ({tport.kind})."
            )

    # Required inputs present (a port not marked multi must have an inbound edge).
    inbound = defaultdict(list)
    for e in edges:
        inbound[(e["target"], e.get("targetPort"))].append(e)
    for n in nodes:
        try:
            spec = base.get_spec(n["type"])
        except KeyError:
            continue
        for port in spec.inputs:
            if not inbound[(n["id"], port.name)]:
                problems.append(
                    f"Node '{n.get('label', n['id'])}' ({n['type']}) is missing "
                    f"required input '{port.name}'."
                )

    # Cycle detection via topological sort attempt.
    try:
        topological_order(nodes, edges)
    except GraphError as e:
        problems.append(str(e))

    return problems


def topological_order(nodes: list[dict], edges: list[dict]) -> list[str]:
    by_id = _index_nodes(nodes)
    indeg = {nid: 0 for nid in by_id}
    adj = defaultdict(list)
    for e in edges:
        if e["source"] in by_id and e["target"] in by_id:
            adj[e["source"]].append(e["target"])
            indeg[e["target"]] += 1
    queue = deque(sorted(nid for nid, d in indeg.items() if d == 0))
    order = []
    while queue:
        nid = queue.popleft()
        order.append(nid)
        for nxt in adj[nid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(by_id):
        raise GraphError("Graph contains a cycle.")
    return order


def execute(nodes: list[dict], edges: list[dict]) -> dict:
    """Execute the graph and return per-node outputs plus error isolation info."""
    problems = validate(nodes, edges)
    fatal = [p for p in problems if "missing required input" not in p]
    if fatal:
        raise GraphError("; ".join(fatal))

    by_id = _index_nodes(nodes)
    order = topological_order(nodes, edges)

    # Map (target, port) -> list of (source, sourcePort)
    inbound = defaultdict(list)
    for e in edges:
        inbound[(e["target"], e.get("targetPort"))].append(
            (e["source"], e.get("sourcePort"))
        )

    outputs: dict[str, dict] = {}
    node_status: dict[str, dict] = {}

    for nid in order:
        node = by_id[nid]
        try:
            spec = base.get_spec(node["type"])
        except KeyError as e:
            node_status[nid] = {"status": "error", "error": str(e)}
            continue

        resolved: dict[str, object] = {}
        upstream_failed = False
        for port in spec.inputs:
            sources = inbound.get((nid, port.name), [])
            vals = []
            for src_id, src_port in sources:
                if src_id not in outputs:
                    upstream_failed = True
                    break
                vals.append(outputs[src_id].get(src_port))
            if upstream_failed:
                break
            if port.multi:
                resolved[port.name] = vals
            elif vals:
                resolved[port.name] = vals[0]

        if upstream_failed:
            node_status[nid] = {"status": "skipped", "error": "upstream node failed"}
            continue

        try:
            result = spec.execute(node.get("config", {}) or {}, resolved)
            outputs[nid] = result
            node_status[nid] = {"status": "ok"}
        except Exception as exc:  # isolate failures per node
            node_status[nid] = {"status": "error", "error": str(exc)}

    return {
        "results": {nid: serialize_outputs(out) for nid, out in outputs.items()},
        "node_status": node_status,
        "warnings": problems,
    }


# --------------------------------------------------------------------------- #
# Serialization: turn pandas/numpy payloads into compact JSON-friendly dicts.
# --------------------------------------------------------------------------- #

MAX_POINTS = 1500


def _downsample(s: pd.Series, max_points: int = MAX_POINTS) -> pd.Series:
    if len(s) <= max_points:
        return s
    step = int(np.ceil(len(s) / max_points))
    return s.iloc[::step]


def _series_to_xy(s: pd.Series) -> dict:
    s = _downsample(s.dropna())
    x = [str(i.date()) if isinstance(i, pd.Timestamp) else str(i) for i in s.index]
    return {"x": x, "y": [_clean(v) for v in s.to_numpy()]}


def _clean(v):
    f = float(v)
    if np.isnan(f) or np.isinf(f):
        return None
    return f


def serialize_outputs(out: dict) -> dict:
    serialized = {}
    for port, value in out.items():
        serialized[port] = _serialize_value(value)
    return serialized


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, pd.DataFrame):
        cols = {c: _series_to_xy(value[c]) for c in value.columns}
        return {"type": "panel", "columns": cols}
    if isinstance(value, pd.Series):
        return {"type": "series", **_series_to_xy(value)}
    if hasattr(value, "prices"):  # Portfolio
        return {
            "type": "portfolio",
            "assets": list(value.prices.columns),
            "weights": value.normalized_weights(),
            "rebalance": value.rebalance,
            "preview": {c: _series_to_xy(value.prices[c]) for c in value.prices.columns},
        }
    if isinstance(value, dict):
        return _serialize_result(value)
    if isinstance(value, np.ndarray):
        return [_clean(v) for v in value]
    return value


def _serialize_result(res: dict) -> dict:
    kind = res.get("kind")
    if kind == "backtest":
        return {
            "type": "result", "kind": "backtest",
            "equity": _series_to_xy(res["equity"]),
            "drawdown": _series_to_xy(res["drawdown"]),
            "weights": {c: _series_to_xy(res["weights"][c]) for c in res["weights"].columns},
            "metrics": _clean_dict(res["metrics"]),
        }
    if kind == "montecarlo":
        return {
            "type": "result", "kind": "montecarlo",
            "method": res["method"], "n_sims": res["n_sims"],
            "horizon_years": res["horizon_years"],
            "cagrs": [_clean(v) for v in res["cagrs"]],
            "final_values": [_clean(v) for v in res["final_values"]],
            "percentile_paths": {k: [_clean(v) for v in arr]
                                  for k, arr in res["percentile_paths"].items()},
            "metrics": _clean_dict(res["metrics"]),
        }
    if kind == "sweep":
        table = res["table"]
        return {
            "type": "result", "kind": "sweep",
            "table": [{k: _clean(v) if isinstance(v, (int, float, np.floating)) else v
                       for k, v in row.items()} for row in table.to_dict("records")],
            "metrics": _clean_dict(res["metrics"]),
        }
    if kind == "withdrawal":
        return {
            "type": "result", "kind": "withdrawal",
            "equity": _series_to_xy(res["equity"]),
            "metrics": _clean_dict(res["metrics"]),
        }
    # Generic metrics dict
    return _clean_dict(res)


def _clean_dict(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, (int, float, np.floating, np.integer)):
            out[k] = _clean(v)
        else:
            out[k] = v
    return out
