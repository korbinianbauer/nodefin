import { useEffect } from 'react';
import { useStore } from './store';
import { Toolbar } from './components/Toolbar';
import { NodeLibrary } from './components/NodeLibrary';
import { Canvas } from './components/Canvas';
import { Inspector } from './components/Inspector';
import { ResultsDashboard } from './components/ResultsDashboard';

export default function App() {
  const loadCatalog = useStore((s) => s.loadCatalog);
  const loadDataCatalog = useStore((s) => s.loadDataCatalog);

  useEffect(() => {
    loadCatalog().catch((err) => {
      useStore.setState({ status: `Failed to load node catalog: ${err.message}` });
    });
    loadDataCatalog().catch((err) => {
      useStore.setState({ status: `Failed to load data catalog: ${err.message}` });
    });
  }, [loadCatalog, loadDataCatalog]);

  return (
    <div className="app">
      <Toolbar />
      <div className="app-body">
        <NodeLibrary />
        <main className="app-center">
          <Canvas />
          <ResultsDashboard />
        </main>
        <Inspector />
      </div>
    </div>
  );
}
