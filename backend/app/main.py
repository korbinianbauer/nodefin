"""FastAPI application wiring the graph engine, templates and persistence."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import store, templates
from .engine import graph
from .engine.nodes import all_specs
from .schemas import GraphModel, RunRequest, StrategyCreate

app = FastAPI(
    title="nodefin",
    description="A visual lab for portfolio construction, leverage strategies "
                "and robustness analysis (HFEA / Zahlgraf style).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


store.init_db()


@app.on_event("startup")
def _startup() -> None:
    store.init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "node_types": len(all_specs())}


@app.get("/api/nodes")
def node_catalog() -> dict:
    """The node library: every registered node type and its parameter schema."""
    specs = [s.to_dict() for s in all_specs()]
    categories: dict[str, list] = {}
    for s in specs:
        categories.setdefault(s["category"], []).append(s)
    return {"nodes": specs, "categories": categories}


@app.get("/api/templates")
def list_templates() -> dict:
    return {"templates": templates.list_templates()}


@app.get("/api/templates/{template_id}")
def get_template(template_id: str) -> dict:
    try:
        return templates.get_template(template_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/validate")
def validate_graph(g: GraphModel) -> dict:
    nodes, edges = g.as_dicts()
    return {"problems": graph.validate(nodes, edges)}


@app.post("/api/run")
def run_graph(req: RunRequest) -> dict:
    nodes, edges = req.graph.as_dicts()
    try:
        result = graph.execute(nodes, edges)
    except graph.GraphError as e:
        raise HTTPException(status_code=400, detail=str(e))
    status = "ok" if all(
        s["status"] != "error" for s in result["node_status"].values()
    ) else "partial"
    run_id = store.save_run(req.strategy_id, status, result)
    return {"run_id": run_id, "status": status, **result}


@app.get("/api/results/{run_id}")
def get_results(run_id: str) -> dict:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# --------------------------- Strategy CRUD --------------------------------- #

@app.post("/api/strategy")
def create_strategy(payload: StrategyCreate) -> dict:
    return store.create_strategy(payload.name, payload.graph.model_dump(), payload.description)


@app.get("/api/strategy")
def list_strategies() -> dict:
    return {"strategies": store.list_strategies()}


@app.get("/api/strategy/{sid}")
def get_strategy(sid: str) -> dict:
    s = store.get_strategy(sid)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return s


@app.put("/api/strategy/{sid}")
def update_strategy(sid: str, payload: StrategyCreate) -> dict:
    s = store.update_strategy(sid, payload.name, payload.graph.model_dump(), payload.description)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return s


@app.delete("/api/strategy/{sid}")
def delete_strategy(sid: str) -> dict:
    if not store.delete_strategy(sid):
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"deleted": sid}
