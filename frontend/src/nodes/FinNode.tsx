import { memo } from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import { useStore } from '../store';
import { portColor, type NodeSpec } from '../lib/api';
import type { NodeData } from '../store';

function FinNodeInner({ id, data, selected }: NodeProps<NodeData>) {
  const spec: NodeSpec | undefined = useStore((s) => s.specByType[data.type]);
  const status = useStore((s) => s.nodeStatus[id]);

  const inputs = spec?.inputs ?? [];
  const outputs = spec?.outputs ?? [];

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
  const maxRows = Math.max(inputs.length, outputs.length, 1);
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
          {inputs.map((p, i) => (
            <div className="fin-port-row" key={p.name} style={{ top: i * rowHeight }}>
              <Handle
                id={p.name}
                type="target"
                position={Position.Left}
                className="fin-handle"
                style={{ background: portColor(p.kind), top: 11 }}
              />
              <span className="fin-port-label in" style={{ color: portColor(p.kind) }}>
                {p.label || p.name}
                {p.multi ? ' *' : ''}
              </span>
            </div>
          ))}
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
