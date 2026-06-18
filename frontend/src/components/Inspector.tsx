import { useStore, type FlowNode } from '../store';
import type { ParamSpec } from '../lib/api';

function fmtPct(x: number): string {
  return `${(x * 100).toFixed(2)}%`;
}

// Ticker picker: a single-instrument dropdown that, on selection, prefills the
// node's start/end dates with the ticker's full range and shows what data is
// available from this source.
function TickerField({ node }: { node: FlowNode }) {
  const dataCatalog = useStore((s) => s.dataCatalog);
  const updateNodeConfig = useStore((s) => s.updateNodeConfig);
  const id = `${node.id}-ticker`;
  const ticker = node.data.config.ticker == null ? '' : String(node.data.config.ticker);
  const info = dataCatalog.find((t) => t.ticker === ticker);
  const reals = dataCatalog.filter((t) => t.kind === 'real');
  const synth = dataCatalog.filter((t) => t.kind === 'synthetic');

  const onSelect = (tk: string) => {
    updateNodeConfig(node.id, 'ticker', tk);
    const meta = dataCatalog.find((t) => t.ticker === tk);
    if (meta) {
      // Prefill the available timeframe so a run uses the full history by default.
      updateNodeConfig(node.id, 'start', meta.start);
      updateNodeConfig(node.id, 'end', meta.end);
    }
  };

  return (
    <div className="param-field">
      <label htmlFor={id}>Ticker</label>
      <select id={id} value={ticker} onChange={(e) => onSelect(e.target.value)}>
        {ticker === '' && (
          <option value="" disabled>
            Select a ticker…
          </option>
        )}
        {reals.length > 0 && (
          <optgroup label="Real data">
            {reals.map((t) => (
              <option key={t.ticker} value={t.ticker}>
                {t.ticker} — {t.label}
              </option>
            ))}
          </optgroup>
        )}
        {synth.length > 0 && (
          <optgroup label="Synthetic samples">
            {synth.map((t) => (
              <option key={t.ticker} value={t.ticker}>
                {t.ticker} — {t.label}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      {info && (
        <div className={`ticker-stats ${info.kind}`}>
          <div className="ticker-stats-head">
            <span className="ticker-stats-name">{info.label}</span>
            <span className="ticker-badge">{info.kind === 'real' ? 'real' : 'synthetic'}</span>
          </div>
          <dl>
            <div>
              <dt>Available</dt>
              <dd>{info.start} → {info.end}</dd>
            </div>
            <div>
              <dt>Span</dt>
              <dd>{info.years} yr · {info.rows.toLocaleString()} pts</dd>
            </div>
            <div>
              <dt>CAGR</dt>
              <dd>{fmtPct(info.cagr)}</dd>
            </div>
            <div>
              <dt>Volatility</dt>
              <dd>{fmtPct(info.vol)}</dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}

function ParamField({
  nodeId,
  param,
  value,
  onChange,
}: {
  nodeId: string;
  param: ParamSpec;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const id = `${nodeId}-${param.name}`;
  switch (param.type) {
    case 'bool':
      return (
        <label className="param-checkbox">
          <input
            id={id}
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
          />
          <span>{param.label}</span>
        </label>
      );
    case 'select':
      return (
        <div className="param-field">
          <label htmlFor={id}>{param.label}</label>
          <select
            id={id}
            value={value === undefined || value === null ? '' : String(value)}
            onChange={(e) => onChange(e.target.value)}
          >
            {(param.options ?? []).map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      );
    case 'number':
    case 'int':
      return (
        <div className="param-field">
          <label htmlFor={id}>{param.label}</label>
          <input
            id={id}
            type="number"
            value={value === undefined || value === null ? '' : Number(value)}
            min={param.min ?? undefined}
            max={param.max ?? undefined}
            step={param.step ?? (param.type === 'int' ? 1 : 'any')}
            onChange={(e) => {
              const raw = e.target.value;
              if (raw === '') {
                onChange(null);
                return;
              }
              const num = param.type === 'int' ? parseInt(raw, 10) : parseFloat(raw);
              onChange(Number.isNaN(num) ? null : num);
            }}
          />
        </div>
      );
    // string | weights | tickers -> text input
    default:
      return (
        <div className="param-field">
          <label htmlFor={id}>{param.label}</label>
          <input
            id={id}
            type="text"
            value={value === undefined || value === null ? '' : String(value)}
            placeholder={param.type === 'tickers' ? 'AAPL, MSFT, …' : param.type === 'weights' ? '0.6, 0.4' : ''}
            onChange={(e) => onChange(e.target.value)}
          />
        </div>
      );
  }
}

// Number-of-inputs control: drives how many price connectors the node shows and
// prunes edges to connectors that disappear when the count shrinks.
function InputCountField({ node, param }: { node: FlowNode; param: ParamSpec }) {
  const spec = useStore((s) => s.specByType[node.data.type]);
  const setInputCount = useStore((s) => s.setInputCount);
  const id = `${node.id}-${param.name}`;
  const port = spec?.inputs.find((p) => p.count_param === param.name);
  const min = param.min ?? 1;
  const max = param.max ?? 99;
  const raw = node.data.config[param.name];
  const value = Number.isFinite(Number(raw)) ? Number(raw) : Number(param.default) || min;

  const commit = (n: number) => {
    const clamped = Math.max(min, Math.min(max, Math.round(n)));
    setInputCount(node.id, param.name, port?.name ?? '', clamped);
  };

  return (
    <div className="param-field">
      <label htmlFor={id}>{param.label}</label>
      <input
        id={id}
        type="number"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(e) => {
          const n = parseInt(e.target.value, 10);
          if (!Number.isNaN(n)) commit(n);
        }}
      />
    </div>
  );
}

// Per-asset weight boxes (replaces the JSON string). One numeric box per input,
// labelled with the connected asset, plus a live normalised percentage.
function WeightsField({ node }: { node: FlowNode }) {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const updateNodeConfig = useStore((s) => s.updateNodeConfig);
  const count = Math.max(1, Math.round(Number(node.data.config.n_inputs) || 1));
  const raw = Array.isArray(node.data.config.weights)
    ? (node.data.config.weights as unknown[])
    : [];
  // Weights are integer percentages (0–100).
  const weights: number[] = Array.from({ length: count }, (_, i) => {
    const v = Math.round(Number(raw[i]));
    return Number.isFinite(v) ? Math.max(0, Math.min(100, v)) : 0;
  });
  const total = weights.reduce((a, b) => a + b, 0);

  const assetName = (i: number): string => {
    const e = edges.find((ed) => ed.target === node.id && ed.targetHandle === `prices.${i}`);
    const src = e && nodes.find((n) => n.id === e.source);
    if (src) {
      if (src.data.type === 'data.prices' && src.data.config.ticker) {
        return String(src.data.config.ticker);
      }
      return src.data.label || `Asset ${i + 1}`;
    }
    return `Asset ${i + 1}`;
  };

  const setWeight = (i: number, v: number) => {
    const next = weights.slice();
    next[i] = Math.max(0, Math.min(100, Math.round(v)));
    updateNodeConfig(node.id, 'weights', next);
  };

  return (
    <div className="param-field">
      <label>Weights (%)</label>
      <div className="weights-list">
        {weights.map((w, i) => (
          <div className="weight-row" key={i}>
            <span className="weight-asset" title={assetName(i)}>{assetName(i)}</span>
            <input
              type="number"
              step={1}
              min={0}
              max={100}
              value={w}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10);
                setWeight(i, Number.isNaN(v) ? 0 : v);
              }}
            />
            <span className="weight-unit">%</span>
          </div>
        ))}
      </div>
      <div className={`weights-total${total === 100 ? '' : ' warn'}`}>
        Total: {total}%{total === 100 ? '' : ' — should be 100%'}
      </div>
    </div>
  );
}

export function Inspector() {
  const activeNodeId = useStore((s) => s.activeNodeId);
  const node = useStore((s) => s.nodes.find((n) => n.id === s.activeNodeId));
  const spec = useStore((s) => (node ? s.specByType[node.data.type] : undefined));
  const updateNodeConfig = useStore((s) => s.updateNodeConfig);
  const status = useStore((s) => (activeNodeId ? s.nodeStatus[activeNodeId] : undefined));

  if (!node || !spec) {
    return (
      <aside className="panel inspector">
        <h2 className="panel-title">Inspector</h2>
        <p className="muted">Select a node to edit its parameters.</p>
      </aside>
    );
  }

  return (
    <aside className="panel inspector">
      <h2 className="panel-title">Inspector</h2>
      <div className="inspector-scroll">
        <div className="inspector-head">
          <div className="inspector-node-label">{node.data.label}</div>
          <div className="inspector-node-type">{spec.type}</div>
        </div>
        <p className="inspector-desc">{spec.description}</p>

        {status?.status === 'error' && (
          <div className="inspector-error">Error: {status.error}</div>
        )}

        {spec.params.length === 0 && <p className="muted">No parameters.</p>}

        <div className="inspector-params">
          {spec.params.map((p) => (
            <div key={p.name} title={p.description}>
              {p.type === 'ticker' ? (
                <TickerField node={node} />
              ) : p.type === 'input_count' ? (
                <InputCountField node={node} param={p} />
              ) : p.type === 'weights' ? (
                <WeightsField node={node} />
              ) : (
                <ParamField
                  nodeId={node.id}
                  param={p}
                  value={node.data.config[p.name]}
                  onChange={(v) => updateNodeConfig(node.id, p.name, v)}
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
