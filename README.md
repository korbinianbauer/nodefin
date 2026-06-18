# nodefin

> A visual lab for portfolio construction, leverage strategies and robustness
> analysis — in the spirit of **HFEA** and **Zahlgraf**, *not* a trading platform.

nodefin lets you model portfolio-research workflows as a **graph of nodes**:
load data → simulate leverage → build a portfolio → rebalance → backtest /
Monte-Carlo / start-date sweep → read the metrics. The emphasis is on
*parameter spaces, robustness and leverage modelling*, rather than single
one-off backtests.

```
┌──────────────────────────────────────────────┐
│ Toolbar (Templates · Run · Validate · Save)  │
├──────────────┬───────────────────────────────┤
│ Node Library │ Graph Canvas (React Flow)     │
│              │                               │
├──────────────┴───────────────────────────────┤
│ Results Dashboard (Equity · MC · Sweep · …)  │
└──────────────────────────────────────────────┘
```

## Architecture

```
Frontend (React + React Flow)  ──HTTP──►  FastAPI  ──►  Graph Execution Engine
                                                          (pandas / numpy)
                                                              │
                                                          Data Layer
                                                   (sample · CSV · Yahoo) + SQLite
```

The heart of the system is the **graph execution engine** (`backend/app/engine`):
the graph is validated, topologically sorted, and each node executes on pandas
data, passing typed payloads (`prices`, `portfolio`, `result`, `metrics`) along
the edges.

## Node catalogue

| Category    | Nodes |
|-------------|-------|
| Data Sources| Market Data (sample/Yahoo/CSV), Synthetic GBM |
| Portfolio   | Static Portfolio, Equal Weight, Risk Parity, Combine |
| Leverage    | Daily Leverage (simulate UPRO/TMF pre-inception, with financing + expense costs) |
| Rebalancing | Rebalance (calendar + drift threshold + transaction costs) |
| Simulation  | Backtest, Monte Carlo (block bootstrap / GBM), Start-Date Sweep |
| Metrics     | CAGR, Sharpe, Sortino, Max Drawdown, Ulcer, Calmar |
| FIRE        | Withdrawal (4% rule, inflation, depletion) |

### Strategy templates
HFEA (3x SPY/TLT), 60/40, Permanent Portfolio, Risk Parity, and a
Zahlgraf-style Start-Date Sweep + Monte Carlo — all available from the toolbar.

## Data

nodefin ships a **deterministic, fully offline synthetic sample dataset**
(SPY, QQQ, TLT, GLD, BTC, CASH; 1990–2024) so everything runs and tests pass
with no network access. The series are *synthetic* and calibrated to plausible
vols/correlations — they are **not** real market history. For real analysis:

* drop `TICKER.csv` files (with a `date` index and a `close` column) into
  `backend/app/data/` and set a node's source to `csv`, or
* install `yfinance` and set a node's source to `yahoo` (requires network).

## Running it

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API docs at http://localhost:8000/docs
```

Run the tests:

```bash
cd backend && python -m pytest -q
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to :8000
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/nodes` | Node library + parameter schemas |
| GET  | `/api/templates`, `/api/templates/{id}` | List / load strategy templates |
| POST | `/api/validate` | Validate a graph (cycles, missing inputs, type mismatches) |
| POST | `/api/run` | Execute a graph; returns per-node results & status |
| GET  | `/api/results/{run_id}` | Fetch a stored run |
| CRUD | `/api/strategy[/{id}]` | Save / load / update / delete strategies |

## Scope

**In the MVP:** node editor, portfolio & leverage nodes, rebalancing,
backtesting, Monte Carlo, start-date sweep, HFEA template, metrics, FIRE
withdrawal, strategy persistence.

**Not in scope:** live/algorithmic trading, real-time streaming, order
execution. nodefin is a *research* tool.

## Project layout

```
backend/
  app/
    main.py            FastAPI app & routes
    schemas.py         pydantic request/response models
    store.py           SQLite persistence (strategies, runs)
    templates.py       built-in strategy graphs
    engine/
      graph.py         validation · topo sort · execution · serialization
      backtester.py    core portfolio simulation loop
      metrics.py       performance & risk metrics
      data.py          market-data access (sample · csv · yahoo)
      nodes/           one module per node category (self-registering)
  tests/               pytest suite
frontend/              React + React Flow + Zustand + Plotly (Vite)
```
