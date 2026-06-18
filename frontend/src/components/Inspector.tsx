import { useStore } from '../store';
import type { ParamSpec } from '../lib/api';

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
              <ParamField
                nodeId={node.id}
                param={p}
                value={node.data.config[p.name]}
                onChange={(v) => updateNodeConfig(node.id, p.name, v)}
              />
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
