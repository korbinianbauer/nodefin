import { useMemo, useState } from 'react';
import { Plot } from '../lib/Plot';
import { useStore } from '../store';
import {
  isBacktest,
  isMonteCarlo,
  isSweep,
  isWithdrawal,
  isSavings,
  isMetrics,
  type BacktestResult,
  type MonteCarloResult,
  type SweepResult,
  type WithdrawalResult,
  type SavingsResult,
  type Results,
  type MetricsValue,
} from '../lib/api';

type TabKey = 'equity' | 'drawdown' | 'allocation' | 'montecarlo' | 'sweep' | 'metrics';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'equity', label: 'Equity' },
  { key: 'drawdown', label: 'Drawdown' },
  { key: 'allocation', label: 'Allocation' },
  { key: 'montecarlo', label: 'Monte Carlo' },
  { key: 'sweep', label: 'Sweep' },
  { key: 'metrics', label: 'Metrics' },
];

// ---- collectors -------------------------------------------------------------

interface Labeled<T> {
  nodeId: string;
  port: string;
  value: T;
}

function collect<T>(
  results: Results,
  pred: (v: unknown) => v is T,
): Labeled<T>[] {
  const out: Labeled<T>[] = [];
  for (const [nodeId, ports] of Object.entries(results)) {
    for (const [port, value] of Object.entries(ports)) {
      if (pred(value)) out.push({ nodeId, port, value });
    }
  }
  return out;
}

function Empty({ msg }: { msg: string }) {
  return <div className="dash-empty">{msg}</div>;
}

const PALETTE = ['#4fc3f7', '#ab87ff', '#ffb74d', '#81c784', '#e57373', '#4dd0e1', '#f06292'];

// ---- tab panels -------------------------------------------------------------

function EquityPanel({ results }: { results: Results }) {
  const [log, setLog] = useState(false);
  const backtests = collect(results, isBacktest);
  const withdrawals = collect(results, isWithdrawal);
  const savings = collect(results, isSavings);
  const all = [...backtests, ...withdrawals, ...savings];
  if (all.length === 0)
    return <Empty msg="Run a graph with a backtest, savings plan or withdrawal node to see equity curves." />;

  const data = all.flatMap((r, i) => {
    const eq = (r.value as BacktestResult | WithdrawalResult | SavingsResult).equity;
    const color = PALETTE[i % PALETTE.length];
    const traces = [
      {
        x: eq.x,
        y: eq.y,
        type: 'scatter' as const,
        mode: 'lines' as const,
        name: `${r.nodeId}.${r.port}`,
        line: { color, width: 2 },
      },
    ];
    // Savings plans also show cumulative invested capital for comparison.
    if (isSavings(r.value)) {
      traces.push({
        x: r.value.contributed.x,
        y: r.value.contributed.y,
        type: 'scatter' as const,
        mode: 'lines' as const,
        name: `${r.nodeId} invested`,
        line: { color, width: 1, dash: 'dot' } as { color: string; width: number; dash: 'dot' },
      } as (typeof traces)[number]);
    }
    return traces;
  });

  return (
    <div className="dash-chart-wrap">
      <div className="dash-controls">
        <label className="toggle">
          <input type="checkbox" checked={log} onChange={(e) => setLog(e.target.checked)} />
          Log scale
        </label>
      </div>
      <div className="dash-chart">
        <Plot
          data={data}
          layout={{ yaxis: { type: log ? 'log' : 'linear', title: { text: 'Equity' } } }}
        />
      </div>
    </div>
  );
}

function DrawdownPanel({ results }: { results: Results }) {
  const backtests = collect(results, isBacktest);
  if (backtests.length === 0) return <Empty msg="Run a graph with a backtest node to see drawdowns." />;

  const data = backtests.map((r, i) => {
    const dd = r.value.drawdown;
    return {
      x: dd.x,
      y: dd.y,
      type: 'scatter' as const,
      mode: 'lines' as const,
      fill: 'tozeroy' as const,
      name: `${r.nodeId}.${r.port}`,
      line: { color: PALETTE[i % PALETTE.length], width: 1 },
    };
  });

  return (
    <div className="dash-chart">
      <Plot data={data} layout={{ yaxis: { title: { text: 'Drawdown' }, tickformat: '.0%' } }} />
    </div>
  );
}

function AllocationPanel({ results }: { results: Results }) {
  const backtests = collect(results, isBacktest);
  if (backtests.length === 0) return <Empty msg="Run a graph with a backtest node to see allocation over time." />;

  const bt = backtests[0].value as BacktestResult;
  const assets = Object.keys(bt.weights);
  if (assets.length === 0) return <Empty msg="The first backtest has no weight series." />;

  const data = assets.map((asset, i) => {
    const w = bt.weights[asset];
    return {
      x: w.x,
      y: w.y,
      type: 'scatter' as const,
      mode: 'lines' as const,
      stackgroup: 'one',
      name: asset,
      line: { width: 0.5, color: PALETTE[i % PALETTE.length] },
    };
  });

  return (
    <div className="dash-chart">
      <Plot
        data={data}
        layout={{
          yaxis: { title: { text: 'Weight' }, tickformat: '.0%', range: [0, 1] },
          title: { text: `Allocation — ${backtests[0].nodeId}`, font: { size: 12 } },
        }}
      />
    </div>
  );
}

function MonteCarloPanel({ results }: { results: Results }) {
  const mcs = collect(results, isMonteCarlo);
  if (mcs.length === 0) return <Empty msg="Run a graph with a Monte Carlo node to see simulated outcomes." />;

  const mc = mcs[0].value as MonteCarloResult;
  const histData = [
    {
      x: mc.cagrs,
      type: 'histogram' as const,
      marker: { color: '#4fc3f7' },
      name: 'CAGR',
      nbinsx: 40,
    },
  ];

  const pp = mc.percentile_paths;
  const xs = pp.p50.map((_, i) => i);
  const fanData = (
    [
      ['p95', '#81c784'],
      ['p75', '#4dd0e1'],
      ['p50', '#4fc3f7'],
      ['p25', '#ffb74d'],
      ['p5', '#e57373'],
    ] as const
  ).map(([k, color]) => ({
    x: xs,
    y: pp[k],
    type: 'scatter' as const,
    mode: 'lines' as const,
    name: k,
    line: { color },
  }));

  return (
    <div className="dash-split">
      <div className="dash-chart">
        <Plot
          data={histData}
          layout={{
            title: { text: `CAGR distribution (${mc.n_sims} sims, ${mc.method})`, font: { size: 12 } },
            xaxis: { title: { text: 'CAGR' }, tickformat: '.0%' },
            yaxis: { title: { text: 'Count' } },
          }}
        />
      </div>
      <div className="dash-chart">
        <Plot
          data={fanData}
          layout={{
            title: { text: 'Percentile paths', font: { size: 12 } },
            xaxis: { title: { text: 'Period' } },
            yaxis: { title: { text: 'Value' } },
          }}
        />
      </div>
    </div>
  );
}

function SweepPanel({ results }: { results: Results }) {
  const sweeps = collect(results, isSweep);
  if (sweeps.length === 0) return <Empty msg="Run a graph with a sweep node to see rolling-window outcomes." />;

  const sw = sweeps[0].value as SweepResult;
  const years = sw.table.map((r) => r.start_year);
  const cagrs = sw.table.map((r) => r.cagr);

  const data = [
    {
      x: years,
      y: cagrs,
      type: 'bar' as const,
      marker: {
        color: cagrs,
        colorscale: 'RdYlGn' as const,
        cmid: 0,
        colorbar: { title: { text: 'CAGR' } },
      },
    },
  ];

  const m = sw.metrics;
  return (
    <div className="dash-chart-wrap">
      <div className="dash-stats">
        <span>Windows: <b>{m.n_windows}</b></span>
        <span>Worst CAGR: <b>{fmtPct(m.worst_cagr)}</b></span>
        <span>Median CAGR: <b>{fmtPct(m.median_cagr)}</b></span>
        <span>Best CAGR: <b>{fmtPct(m.best_cagr)}</b></span>
        <span>Worst MaxDD: <b>{fmtPct(m.worst_max_drawdown)}</b></span>
      </div>
      <div className="dash-chart">
        <Plot
          data={data}
          layout={{
            title: { text: 'CAGR by start year', font: { size: 12 } },
            xaxis: { title: { text: 'Start year' } },
            yaxis: { title: { text: 'CAGR' }, tickformat: '.0%' },
          }}
        />
      </div>
    </div>
  );
}

function fmtPct(v: number | string | undefined): string {
  if (typeof v !== 'number' || !isFinite(v)) return '—';
  return `${(v * 100).toFixed(2)}%`;
}

function fmtVal(v: number | string): string {
  if (typeof v === 'string') return v;
  if (!isFinite(v)) return '—';
  if (Math.abs(v) < 10 && v !== 0) return v.toFixed(4);
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function MetricsPanel({ results }: { results: Results }) {
  const backtests = collect(results, isBacktest);
  const savings = collect(results, isSavings);
  const withdrawals = collect(results, isWithdrawal);
  const metricsPorts = collect<MetricsValue>(results, isMetrics);

  const rows: { source: string; metrics: Record<string, number | string> }[] = [];
  for (const b of backtests) {
    rows.push({ source: `${b.nodeId}.${b.port} (backtest)`, metrics: b.value.metrics });
  }
  for (const s of savings) {
    rows.push({ source: `${s.nodeId}.${s.port} (savings)`, metrics: s.value.metrics });
  }
  for (const w of withdrawals) {
    rows.push({ source: `${w.nodeId}.${w.port} (withdrawal)`, metrics: w.value.metrics });
  }
  for (const mp of metricsPorts) {
    rows.push({ source: `${mp.nodeId}.${mp.port}`, metrics: mp.value });
  }

  if (rows.length === 0) return <Empty msg="Run a graph with a backtest or metrics node to see metrics." />;

  // Union of all metric keys, preserving first-seen order.
  const keys: string[] = [];
  for (const r of rows) {
    for (const k of Object.keys(r.metrics)) if (!keys.includes(k)) keys.push(k);
  }

  return (
    <div className="dash-table-wrap">
      <table className="metrics-table">
        <thead>
          <tr>
            <th>Source</th>
            {keys.map((k) => (
              <th key={k}>{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="metrics-source">{r.source}</td>
              {keys.map((k) => (
                <td key={k}>{r.metrics[k] === undefined ? '—' : fmtVal(r.metrics[k])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---- container --------------------------------------------------------------

export function ResultsDashboard() {
  const results = useStore((s) => s.results);
  const warnings = useStore((s) => s.warnings);
  const [tab, setTab] = useState<TabKey>('equity');

  const hasResults = useMemo(() => Object.keys(results).length > 0, [results]);

  return (
    <section className="panel dashboard">
      <div className="dash-tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`dash-tab ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
        {warnings.length > 0 && (
          <span className="dash-warnings" title={warnings.join('\n')}>
            {warnings.length} warning(s)
          </span>
        )}
      </div>

      <div className="dash-content">
        {!hasResults && <Empty msg="No results yet. Build a graph and click Run." />}
        {hasResults && tab === 'equity' && <EquityPanel results={results} />}
        {hasResults && tab === 'drawdown' && <DrawdownPanel results={results} />}
        {hasResults && tab === 'allocation' && <AllocationPanel results={results} />}
        {hasResults && tab === 'montecarlo' && <MonteCarloPanel results={results} />}
        {hasResults && tab === 'sweep' && <SweepPanel results={results} />}
        {hasResults && tab === 'metrics' && <MetricsPanel results={results} />}
      </div>
    </section>
  );
}
