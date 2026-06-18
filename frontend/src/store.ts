import { create } from 'zustand';
import {
  type Connection,
  type Edge,
  type Node,
  type EdgeChange,
  type NodeChange,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
} from 'reactflow';
import {
  api,
  type GEdge,
  type GNode,
  type NodeSpec,
  type Results,
  type NodeStatus,
  type ParamSpec,
  type TickerInfo,
} from './lib/api';

export interface NodeData {
  type: string;
  label: string;
  config: Record<string, unknown>;
}

export type FlowNode = Node<NodeData>;

interface StoreState {
  nodes: FlowNode[];
  edges: Edge[];
  nodeSpecs: NodeSpec[];
  specByType: Record<string, NodeSpec>;
  categories: Record<string, NodeSpec[]>;
  dataCatalog: TickerInfo[];
  results: Results;
  nodeStatus: Record<string, NodeStatus>;
  problems: string[];
  warnings: string[];
  activeNodeId: string | null;
  running: boolean;
  status: string;

  // actions
  loadCatalog: () => Promise<void>;
  loadDataCatalog: () => Promise<void>;
  loadTemplate: (id: string) => Promise<void>;
  setGraph: (nodes: FlowNode[], edges: Edge[]) => void;
  addNode: (type: string) => void;
  updateNodeConfig: (id: string, key: string, value: unknown) => void;
  setInputCount: (id: string, key: string, portName: string, count: number) => void;
  setActiveNode: (id: string | null) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (conn: Connection) => void;
  onConnectStart: (params: {
    nodeId?: string | null;
    handleId?: string | null;
    handleType?: 'source' | 'target' | null;
  }) => void;
  run: () => Promise<void>;
  validate: () => Promise<void>;
  save: (name: string) => Promise<void>;
  clear: () => void;
}

let idCounter = 1;
function nextId(prefix: string): string {
  return `${prefix}_${Date.now().toString(36)}_${idCounter++}`;
}

function defaultConfig(params: ParamSpec[]): Record<string, unknown> {
  const cfg: Record<string, unknown> = {};
  for (const p of params) {
    cfg[p.name] = p.default;
  }
  return cfg;
}

// Convert backend GNode/GEdge to reactflow shapes.
function toFlowNode(g: GNode): FlowNode {
  return {
    id: g.id,
    type: 'finNode',
    position: g.position ?? { x: 0, y: 0 },
    data: { type: g.type, label: g.label || g.type, config: g.config ?? {} },
  };
}

function toFlowEdge(e: GEdge): Edge {
  return {
    id: e.id || nextId('e'),
    source: e.source,
    target: e.target,
    sourceHandle: e.sourcePort,
    targetHandle: e.targetPort,
  };
}

// Convert reactflow shapes back to backend GNode/GEdge.
function toGNode(n: FlowNode): GNode {
  return {
    id: n.id,
    type: n.data.type,
    label: n.data.label,
    position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
    config: n.data.config ?? {},
  };
}

function toGEdge(e: Edge): GEdge {
  return {
    id: e.id,
    source: e.source,
    sourcePort: e.sourceHandle ?? '',
    target: e.target,
    targetPort: e.targetHandle ?? '',
  };
}

export const useStore = create<StoreState>((set, get) => ({
  nodes: [],
  edges: [],
  nodeSpecs: [],
  specByType: {},
  categories: {},
  dataCatalog: [],
  results: {},
  nodeStatus: {},
  problems: [],
  warnings: [],
  activeNodeId: null,
  running: false,
  status: '',

  loadCatalog: async () => {
    const cat = await api.getCatalog();
    const specByType: Record<string, NodeSpec> = {};
    for (const s of cat.nodes) specByType[s.type] = s;
    set({ nodeSpecs: cat.nodes, categories: cat.categories, specByType });
  },

  loadDataCatalog: async () => {
    const { tickers } = await api.getDataCatalog();
    set({ dataCatalog: tickers });
  },

  loadTemplate: async (id: string) => {
    const tmpl = await api.getTemplate(id);
    const nodes = tmpl.nodes.map(toFlowNode);
    const edges = tmpl.edges.map(toFlowEdge);
    set({
      nodes,
      edges,
      results: {},
      nodeStatus: {},
      problems: [],
      warnings: [],
      activeNodeId: null,
      status: `Loaded template "${tmpl.name}"`,
    });
  },

  setGraph: (nodes, edges) => set({ nodes, edges }),

  addNode: (type: string) => {
    const spec = get().specByType[type];
    if (!spec) return;
    const existing = get().nodes;
    // Place new nodes in a loose grid so they don't overlap.
    const offset = existing.length;
    const node: FlowNode = {
      id: nextId(type),
      type: 'finNode',
      position: { x: 120 + (offset % 4) * 60, y: 80 + offset * 40 },
      data: {
        type: spec.type,
        label: spec.label,
        config: defaultConfig(spec.params),
      },
    };
    set({ nodes: [...existing, node], activeNodeId: node.id });
  },

  updateNodeConfig: (id, key, value) => {
    set({
      nodes: get().nodes.map((n) =>
        n.id === id
          ? { ...n, data: { ...n.data, config: { ...n.data.config, [key]: value } } }
          : n,
      ),
    });
  },

  setInputCount: (id, key, portName, count) => {
    const handleIdx = (h: string | null | undefined) => {
      const s = (h ?? '').split('.')[1];
      const n = s ? parseInt(s, 10) : NaN;
      return Number.isNaN(n) ? 0 : n;
    };
    set({
      nodes: get().nodes.map((n) =>
        n.id === id
          ? { ...n, data: { ...n.data, config: { ...n.data.config, [key]: count } } }
          : n,
      ),
      // Drop edges into connectors that no longer exist after shrinking.
      edges: portName
        ? get().edges.filter(
            (e) =>
              !(
                e.target === id &&
                (e.targetHandle ?? '').split('.')[0] === portName &&
                handleIdx(e.targetHandle) >= count
              ),
          )
        : get().edges,
    });
  },

  setActiveNode: (id) => set({ activeNodeId: id }),

  onNodesChange: (changes) => {
    set({ nodes: applyNodeChanges(changes, get().nodes) as FlowNode[] });
    // Track selection -> active node.
    const sel = changes.find((c) => c.type === 'select' && c.selected);
    if (sel && 'id' in sel) set({ activeNodeId: sel.id });
    // Clear the inspector target if the active node was deleted.
    const removed = changes.some((c) => c.type === 'remove' && c.id === get().activeNodeId);
    if (removed) set({ activeNodeId: null });
  },

  onEdgesChange: (changes) => {
    set({ edges: applyEdgeChanges(changes, get().edges) });
  },

  // Pulling a new edge off an input handle clears its existing edge right away,
  // so the old connection is removed even if the drag is dropped on empty space.
  onConnectStart: ({ nodeId, handleId, handleType }) => {
    if (handleType !== 'target' || !nodeId) return;
    set({
      edges: get().edges.filter(
        (e) => !(e.target === nodeId && e.targetHandle === (handleId ?? null)),
      ),
    });
  },

  onConnect: (conn) => {
    const { specByType, nodes, edges } = get();
    const srcNode = nodes.find((n) => n.id === conn.source);
    const tgtNode = nodes.find((n) => n.id === conn.target);
    if (!srcNode || !tgtNode) return;
    const srcSpec = specByType[srcNode.data.type];
    const tgtSpec = specByType[tgtNode.data.type];
    const srcPort = srcSpec?.outputs.find((p) => p.name === conn.sourceHandle);
    // Dynamic inputs use indexed handles ("prices.0"); match them by family.
    const targetBase = (conn.targetHandle ?? '').split('.')[0];
    const tgtPort = tgtSpec?.inputs.find(
      (p) => p.name === conn.targetHandle || (p.dynamic && p.name === targetBase),
    );
    if (!srcPort || !tgtPort) {
      set({ status: 'Rejected: unknown port' });
      return;
    }
    if (srcPort.kind !== tgtPort.kind) {
      set({
        status: `Rejected connection: ${srcPort.kind} -> ${tgtPort.kind} (incompatible)`,
      });
      return;
    }
    // Each connector accepts a single edge: drop any existing edge on this
    // input handle so the new connection replaces it.
    const kept = edges.filter(
      (e) => !(e.target === conn.target && e.targetHandle === conn.targetHandle),
    );
    set({
      edges: addEdge({ ...conn, id: nextId('e') }, kept),
      status: '',
    });
  },

  run: async () => {
    const { nodes, edges } = get();
    set({ running: true, status: 'Running...' });
    try {
      const graph = { nodes: nodes.map(toGNode), edges: edges.map(toGEdge) };
      const res = await api.run(graph);
      set({
        results: res.results,
        nodeStatus: res.node_status,
        warnings: res.warnings,
        status: `Run ${res.status} (${res.run_id})`,
      });
    } catch (err) {
      set({ status: `Run failed: ${(err as Error).message}` });
    } finally {
      set({ running: false });
    }
  },

  validate: async () => {
    const { nodes, edges } = get();
    set({ status: 'Validating...' });
    try {
      const graph = { nodes: nodes.map(toGNode), edges: edges.map(toGEdge) };
      const res = await api.validate(graph);
      set({
        problems: res.problems,
        status: res.problems.length === 0 ? 'Validation: no problems' : `Validation: ${res.problems.length} problem(s)`,
      });
    } catch (err) {
      set({ status: `Validate failed: ${(err as Error).message}` });
    }
  },

  save: async (name: string) => {
    const { nodes, edges } = get();
    set({ status: 'Saving...' });
    try {
      const graph = { nodes: nodes.map(toGNode), edges: edges.map(toGEdge) };
      const s = await api.saveStrategy(name, graph);
      set({ status: `Saved strategy "${s.name}"` });
    } catch (err) {
      set({ status: `Save failed: ${(err as Error).message}` });
    }
  },

  clear: () =>
    set({
      nodes: [],
      edges: [],
      results: {},
      nodeStatus: {},
      problems: [],
      warnings: [],
      activeNodeId: null,
      status: 'Cleared',
    }),
}));
