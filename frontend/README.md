# nodefin — frontend

A visual, node-based portfolio-research UI for the nodefin backend. Build a graph
of data sources, portfolios and simulations on a canvas, run it, and inspect
equity curves, drawdowns, allocations, Monte Carlo fans, rolling-window sweeps
and metrics.

Stack: React 18 + TypeScript + Vite, [reactflow](https://reactflow.dev) v11 for
the canvas, [zustand](https://github.com/pmndrs/zustand) for state, and
`plotly.js-dist-min` for charts.

## Prerequisites

The Python/FastAPI backend must be running on **http://localhost:8000**. The Vite
dev server proxies all `/api/*` requests there (see `vite.config.ts`).

## Run

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api -> :8000
```

## Build

```bash
npm run build    # type-checks (tsc -b) then builds to dist/
npm run preview  # serve the production build locally
```

## Layout

- **Toolbar** — app name, template picker (loads from `/api/templates`), and
  Run / Validate / Save / Clear actions.
- **Node Library** (left) — node types grouped by category from `/api/nodes`.
  Click or drag a node onto the canvas; it is created with each param's default.
- **Canvas** (center) — reactflow graph with custom nodes. Input ports on the
  left (targets), output ports on the right (sources), color-coded by port
  `kind`. Connections are only allowed between ports of the same kind. Nodes turn
  red when their last run errored (hover for the message).
- **Inspector** (right) — editable form for the selected node's params, plus its
  description.
- **Results Dashboard** (bottom) — tabs for Equity, Drawdown, Allocation, Monte
  Carlo, Sweep and Metrics. Empty tabs show a hint about which node to add.
