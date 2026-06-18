import { useCallback, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  useReactFlow,
  type NodeTypes,
  type ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useStore } from '../store';
import { FinNode } from '../nodes/FinNode';

const nodeTypes: NodeTypes = { finNode: FinNode };

function CanvasInner() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const onNodesChange = useStore((s) => s.onNodesChange);
  const onEdgesChange = useStore((s) => s.onEdgesChange);
  const onConnect = useStore((s) => s.onConnect);
  const onConnectStart = useStore((s) => s.onConnectStart);
  const setActiveNode = useStore((s) => s.setActiveNode);
  const specByType = useStore((s) => s.specByType);
  const setGraph = useStore((s) => s.setGraph);

  const wrapper = useRef<HTMLDivElement>(null);
  const rfRef = useRef<ReactFlowInstance | null>(null);
  const { screenToFlowPosition } = useReactFlow();

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const type = e.dataTransfer.getData('application/nodefin');
      if (!type) return;
      const spec = specByType[type];
      if (!spec) return;
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      const config: Record<string, unknown> = {};
      for (const p of spec.params) config[p.name] = p.default;
      const id = `${type}_${Date.now().toString(36)}_${Math.floor(Math.random() * 1e4)}`;
      setGraph(
        [
          ...useStore.getState().nodes,
          {
            id,
            type: 'finNode',
            position,
            data: { type: spec.type, label: spec.label, config },
          },
        ],
        useStore.getState().edges,
      );
      setActiveNode(id);
    },
    [specByType, screenToFlowPosition, setGraph, setActiveNode],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  return (
    <div className="canvas" ref={wrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onConnectStart={(_, params) => onConnectStart(params)}
        onInit={(inst) => (rfRef.current = inst)}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onPaneClick={() => setActiveNode(null)}
        onNodeClick={(_, n) => setActiveNode(n.id)}
        deleteKeyCode={['Delete', 'Backspace']}
        fitView
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{ animated: false, style: { stroke: '#6b7280', strokeWidth: 2 } }}
      >
        <Background color="#2a2f3a" gap={18} />
        <Controls />
        <MiniMap
          nodeColor="#3a4150"
          maskColor="rgba(0,0,0,0.6)"
          style={{ background: '#1a1e26' }}
        />
      </ReactFlow>
    </div>
  );
}

export function Canvas() {
  return (
    <ReactFlowProvider>
      <CanvasInner />
    </ReactFlowProvider>
  );
}
