// Typed API client + shared TypeScript types for the nodefin backend.

// ----------------------------- Catalog types ------------------------------ //

export interface Port {
  name: string;
  kind: string;
  label: string;
  multi: boolean;
  dynamic: boolean;
  count_param: string;
}

export type ParamType =
  | 'number'
  | 'int'
  | 'string'
  | 'bool'
  | 'select'
  | 'weights'
  | 'tickers'
  | 'ticker'
  | 'input_count';

// One selectable instrument and the data available for it.
export interface TickerInfo {
  ticker: string;
  label: string;
  kind: 'real' | 'synthetic';
  source: string;
  start: string;
  end: string;
  rows: number;
  years: number;
  cagr: number;
  vol: number;
}

export interface ParamSpec {
  name: string;
  type: ParamType;
  label: string;
  default: unknown;
  options: string[] | null;
  min: number | null;
  max: number | null;
  step: number | null;
  description: string;
}

export interface NodeSpec {
  type: string;
  category: string;
  label: string;
  description: string;
  inputs: Port[];
  outputs: Port[];
  params: ParamSpec[];
}

export interface CatalogResponse {
  nodes: NodeSpec[];
  categories: Record<string, NodeSpec[]>;
}

// ------------------------------ Graph types -------------------------------- //

export interface GNode {
  id: string;
  type: string;
  label: string;
  position: { x: number; y: number };
  config: Record<string, unknown>;
}

export interface GEdge {
  id: string;
  source: string;
  sourcePort: string;
  target: string;
  targetPort: string;
}

export interface Graph {
  nodes: GNode[];
  edges: GEdge[];
}

// ----------------------------- Template types ------------------------------ //

export interface TemplateSummary {
  id: string;
  name: string;
}

export interface TemplateResponse {
  name: string;
  nodes: GNode[];
  edges: GEdge[];
}

// ----------------------------- Result types -------------------------------- //

export interface XY {
  x: string[];
  y: (number | null)[];
}

export interface PanelValue {
  type: 'panel';
  columns: Record<string, XY>;
}

export interface SeriesValue {
  type: 'series';
  x: string[];
  y: (number | null)[];
}

export interface PortfolioValue {
  type: 'portfolio';
  assets: string[];
  weights: Record<string, number>;
  rebalance: Record<string, unknown>;
  preview: Record<string, XY>;
}

export interface BacktestMetrics {
  cagr: number;
  volatility: number;
  sharpe: number;
  sortino: number;
  max_drawdown: number;
  ulcer_index: number;
  calmar: number;
  total_return: number;
  start: string;
  end: string;
  n_periods: number;
  [k: string]: number | string;
}

export interface BacktestResult {
  type: 'result';
  kind: 'backtest';
  equity: XY;
  drawdown: XY;
  weights: Record<string, XY>;
  metrics: BacktestMetrics;
}

export interface MonteCarloResult {
  type: 'result';
  kind: 'montecarlo';
  method: string;
  n_sims: number;
  horizon_years: number;
  cagrs: number[];
  final_values: number[];
  percentile_paths: {
    p5: number[];
    p25: number[];
    p50: number[];
    p75: number[];
    p95: number[];
  };
  metrics: {
    median_cagr: number;
    p5_cagr: number;
    p95_cagr: number;
    median_final: number;
    prob_loss: number;
    [k: string]: number;
  };
}

export interface SweepRow {
  start_year: number;
  cagr: number;
  max_drawdown: number;
  sharpe: number;
  calmar: number;
  final_multiple: number;
  years: number;
}

export interface SweepResult {
  type: 'result';
  kind: 'sweep';
  table: SweepRow[];
  metrics: {
    median_cagr: number;
    worst_cagr: number;
    best_cagr: number;
    worst_max_drawdown: number;
    n_windows: number;
    [k: string]: number;
  };
}

export interface WithdrawalResult {
  type: 'result';
  kind: 'withdrawal';
  equity: XY;
  metrics: Record<string, number | string>;
}

export interface SavingsResult {
  type: 'result';
  kind: 'savings';
  equity: XY;
  contributed: XY;
  metrics: Record<string, number | string>;
}

export type ResultValue =
  | BacktestResult
  | MonteCarloResult
  | SweepResult
  | WithdrawalResult
  | SavingsResult;

// A metrics port value is a plain object of scalars (no `.type`).
export type MetricsValue = Record<string, number | string>;

export type SerializedValue =
  | PanelValue
  | SeriesValue
  | PortfolioValue
  | ResultValue
  | MetricsValue
  | number[]
  | null;

export type Results = Record<string, Record<string, SerializedValue>>;

export interface NodeStatus {
  status: 'ok' | 'error' | 'skipped';
  error?: string;
}

export interface RunResponse {
  run_id: string;
  status: 'ok' | 'partial';
  results: Results;
  node_status: Record<string, NodeStatus>;
  warnings: string[];
}

export interface ValidateResponse {
  problems: string[];
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  graph: Graph;
  created_at: string;
  updated_at: string;
}

// ------------------------------- Type guards ------------------------------- //

export function isPanel(v: unknown): v is PanelValue {
  return !!v && typeof v === 'object' && !Array.isArray(v) && (v as PanelValue).type === 'panel';
}

export function isPortfolio(v: unknown): v is PortfolioValue {
  return !!v && typeof v === 'object' && !Array.isArray(v) && (v as PortfolioValue).type === 'portfolio';
}

export function isResult(v: unknown): v is ResultValue {
  return !!v && typeof v === 'object' && !Array.isArray(v) && (v as ResultValue).type === 'result';
}

export function isBacktest(v: unknown): v is BacktestResult {
  return isResult(v) && v.kind === 'backtest';
}

export function isMonteCarlo(v: unknown): v is MonteCarloResult {
  return isResult(v) && v.kind === 'montecarlo';
}

export function isSweep(v: unknown): v is SweepResult {
  return isResult(v) && v.kind === 'sweep';
}

export function isWithdrawal(v: unknown): v is WithdrawalResult {
  return isResult(v) && v.kind === 'withdrawal';
}

export function isSavings(v: unknown): v is SavingsResult {
  return isResult(v) && v.kind === 'savings';
}

// A "plain metrics" value: an object with no `.type` discriminator and only scalars.
export function isMetrics(v: unknown): v is MetricsValue {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return false;
  if ('type' in (v as Record<string, unknown>)) return false;
  return true;
}

// --------------------------------- Fetcher --------------------------------- //

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getCatalog: () => request<CatalogResponse>('/api/nodes'),
  getDataCatalog: () => request<{ tickers: TickerInfo[] }>('/api/data/catalog'),
  getTemplates: () => request<{ templates: TemplateSummary[] }>('/api/templates'),
  getTemplate: (id: string) => request<TemplateResponse>(`/api/templates/${id}`),
  validate: (graph: Graph) =>
    request<ValidateResponse>('/api/validate', {
      method: 'POST',
      body: JSON.stringify(graph),
    }),
  run: (graph: Graph) =>
    request<RunResponse>('/api/run', {
      method: 'POST',
      body: JSON.stringify({ graph }),
    }),
  saveStrategy: (name: string, graph: Graph, description = '') =>
    request<Strategy>('/api/strategy', {
      method: 'POST',
      body: JSON.stringify({ name, graph, description }),
    }),
  listStrategies: () => request<{ strategies: Strategy[] }>('/api/strategy'),
};

// ---------------------------- Port kind colors ----------------------------- //

const KIND_COLORS: Record<string, string> = {
  prices: '#4fc3f7',
  portfolio: '#ab87ff',
  result: '#ffb74d',
  metrics: '#81c784',
  series: '#4dd0e1',
};

export function portColor(kind: string): string {
  return KIND_COLORS[kind] ?? '#9e9e9e';
}
