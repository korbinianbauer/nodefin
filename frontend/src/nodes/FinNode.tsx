import { memo } from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import { useStore } from '../store';
import { portColor, type NodeSpec } from '../lib/api';
import type { NodeData } from '../store';

// Connector index of an indexed handle id: "prices.2" -> 2.
function handleIndex(handle: string): number {
  const suffix = handle.split('.')[1];
  const n = suffix ? parseInt(suffix, 10) : NaN;
  return Number.isNaN(n) ? 0 : n;
}

interface InSlot {
  handleId: string;
  label: string;
  kind: string;
}

function FinNodeInner({ id, data, selected }: NodeProps<NodeData>) {
  const spec: NodeSpec | undefined = useStore((s) => s.specByType[data.type]);
  const status = useStore((s) => s.nodeStatus[id]);
  const edges = useStore((s) => s.edges);

  const outputs = spec?.outputs ?? [];

  // Build the flat list of input connectors. A dynamic port expands into one
  // connector per existing connection plus a trailing empty slot, so the user
  // can keep adding inputs; every connector accepts a single edge.
  const inSlots: InSlot[] = [];
  for (const p of spec?.inputs ?? []) {
    if (p.dynamic && p.count_param) {
      // Count-driven: render exactly the configured number of connectors.
      const count = Math.max(1, Math.round(Number(data.config[p.count_param]) || 1));
      for (let k = 0; k < count; k++) {
        inSlots.push({ handleId: `${p.name}.${k}`, label: `${p.label || p.name} ${k + 1}`, kind: p.kind });
      }
    } else if (p.dynamic) {
      // Connection-driven: one connector per edge plus a trailing empty slot.
      const connected = edges
        .filter((e) => e.target === id && (e.targetHandle ?? '').split('.')[0] === p.name)
        .map((e) => e.targetHandle as string)
        .sort((a, b) => handleIndex(a) - handleIndex(b));
      connected.forEach((handleId, k) =>
        inSlots.push({ handleId, label: `${p.label || p.name} ${k + 1}`, kind: p.kind }),
      );
      const nextIndex = connected.length ? Math.max(...connected.map(handleIndex)) + 1 : 0;
      inSlots.push({
        handleId: `${p.name}.${nextIndex}`,
        label: `${p.label || p.name} ${connected.length + 1}`,
        kind: p.kind,
      });
    } else {
      inSlots.push({ handleId: p.name, label: p.label || p.name, kind: p.kind });
    }
  }

  const isError = status?.status === 'error';
  const isSkipped = status?.status === 'skipped';
  const isOk = status?.status === 'ok';

  const classes = ['fin-node'];
  if (selected) classes.push('selected');
  if (isError) classes.push('error');
  if (isSkipped) classes.push('skipped');
  if (isOk) classes.push('ok');

  const rowHeight = 22;
  const headerHeight = 40;
  const maxRows = Math.max(inSlots.length, outputs.length, 1);
  const minHeight = headerHeight + maxRows * rowHeight + 8;

  return (
    <div
      className={classes.join(' ')}
      style={{ minHeight }}
      title={isError ? status?.error : spec?.description}
    >
      <div className="fin-node-header">
        <span className="fin-node-category">{spec?.category ?? ''}</span>
        <span className="fin-node-label">{data.label}</span>
      </div>

      <div className="fin-node-body">
        <div className="fin-ports fin-ports-in">
          {inSlots.map((slot, i) => {
            const connected = edges.some(
              (e) => e.target === id && e.targetHandle === slot.handleId,
            );
            return (
              <div className="fin-port-row" key={slot.handleId} style={{ top: i * rowHeight }}>
                <Handle
                  id={slot.handleId}
                  type="target"
                  position={Position.Left}
                  className={`fin-handle${connected ? '' : ' empty'}`}
                  style={{ background: portColor(slot.kind), top: 11 }}
                />
                <span
                  className={`fin-port-label in${connected ? '' : ' empty'}`}
                  style={{ color: portColor(slot.kind) }}
                >
                  {slot.label}
                </span>
              </div>
            );
          })}
        </div>

        <div className="fin-ports fin-ports-out">
          {outputs.map((p, i) => (
            <div className="fin-port-row out" key={p.name} style={{ top: i * rowHeight }}>
              <span className="fin-port-label out" style={{ color: portColor(p.kind) }}>
                {p.label || p.name}
              </span>
              <Handle
                id={p.name}
                type="source"
                position={Position.Right}
                className="fin-handle"
                style={{ background: portColor(p.kind), top: 11 }}
              />
            </div>
          ))}
        </div>
      </div>

      {isError && <div className="fin-node-errbar" title={status?.error}>error</div>}
    </div>
  );
}

export const FinNode = memo(FinNodeInner);
