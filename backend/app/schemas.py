"""Pydantic request/response schemas for the API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NodeModel(BaseModel):
    id: str
    type: str
    label: str | None = None
    position: dict[str, float] | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class EdgeModel(BaseModel):
    id: str | None = None
    source: str
    sourcePort: str
    target: str
    targetPort: str


class GraphModel(BaseModel):
    nodes: list[NodeModel] = Field(default_factory=list)
    edges: list[EdgeModel] = Field(default_factory=list)

    def as_dicts(self) -> tuple[list[dict], list[dict]]:
        return (
            [n.model_dump() for n in self.nodes],
            [e.model_dump() for e in self.edges],
        )


class StrategyCreate(BaseModel):
    name: str
    graph: GraphModel
    description: str = ""


class StrategyModel(StrategyCreate):
    id: str
    created_at: str
    updated_at: str


class RunRequest(BaseModel):
    graph: GraphModel
    strategy_id: str | None = None
