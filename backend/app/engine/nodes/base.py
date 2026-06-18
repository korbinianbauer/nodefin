"""Node base class, port typing and the global node registry.

Values flowing along edges are tagged with a ``kind`` so the graph validator can
reject incompatible connections. The concrete payloads are plain Python objects:

* ``prices``    -> pandas.DataFrame of price levels (columns = assets)
* ``portfolio`` -> backtester.Portfolio
* ``result``    -> dict produced by a simulation node (equity, returns, ...)
* ``metrics``   -> dict of scalar metrics
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Port:
    name: str
    kind: str
    label: str = ""
    multi: bool = False  # accept multiple inbound edges (inputs only)


@dataclass
class ParamSpec:
    name: str
    type: str  # "number" | "int" | "string" | "bool" | "select" | "weights" | "tickers"
    label: str
    default: Any = None
    options: list[str] | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    description: str = ""


@dataclass
class NodeSpec:
    type: str
    category: str
    label: str
    description: str
    inputs: list[Port]
    outputs: list[Port]
    params: list[ParamSpec]
    execute: Callable[[dict, dict], dict]

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "inputs": [vars(p) for p in self.inputs],
            "outputs": [vars(p) for p in self.outputs],
            "params": [vars(p) for p in self.params],
        }


_REGISTRY: dict[str, NodeSpec] = {}


def register(spec: NodeSpec) -> NodeSpec:
    if spec.type in _REGISTRY:
        raise ValueError(f"Duplicate node type: {spec.type}")
    _REGISTRY[spec.type] = spec
    return spec


def get_spec(node_type: str) -> NodeSpec:
    if node_type not in _REGISTRY:
        raise KeyError(f"Unknown node type: {node_type}")
    return _REGISTRY[node_type]


def all_specs() -> list[NodeSpec]:
    return list(_REGISTRY.values())


def registry() -> dict[str, NodeSpec]:
    return _REGISTRY
