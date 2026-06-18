import { useStore } from '../store';
import type { NodeSpec } from '../lib/api';

export function NodeLibrary() {
  const categories = useStore((s) => s.categories);
  const addNode = useStore((s) => s.addNode);
  const problems = useStore((s) => s.problems);

  const onDragStart = (e: React.DragEvent, type: string) => {
    e.dataTransfer.setData('application/nodefin', type);
    e.dataTransfer.effectAllowed = 'move';
  };

  const catNames = Object.keys(categories).sort();

  return (
    <aside className="panel node-library">
      <h2 className="panel-title">Node Library</h2>
      <div className="library-scroll">
        {catNames.length === 0 && <p className="muted">Loading nodes…</p>}
        {catNames.map((cat) => (
          <div className="library-category" key={cat}>
            <div className="library-category-name">{cat}</div>
            {categories[cat].map((spec: NodeSpec) => (
              <div
                key={spec.type}
                className="library-item"
                draggable
                onDragStart={(e) => onDragStart(e, spec.type)}
                onClick={() => addNode(spec.type)}
                title={spec.description}
              >
                <span className="library-item-label">{spec.label}</span>
                <span className="library-item-type">{spec.type}</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      {problems.length > 0 && (
        <div className="problems">
          <div className="problems-title">Problems ({problems.length})</div>
          <ul>
            {problems.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
