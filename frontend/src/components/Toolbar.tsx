import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { api, type TemplateSummary } from '../lib/api';

export function Toolbar() {
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [selected, setSelected] = useState('');
  const run = useStore((s) => s.run);
  const validate = useStore((s) => s.validate);
  const save = useStore((s) => s.save);
  const clear = useStore((s) => s.clear);
  const loadTemplate = useStore((s) => s.loadTemplate);
  const running = useStore((s) => s.running);
  const status = useStore((s) => s.status);

  useEffect(() => {
    api
      .getTemplates()
      .then((r) => setTemplates(r.templates))
      .catch(() => setTemplates([]));
  }, []);

  const onTemplateChange = async (id: string) => {
    setSelected(id);
    if (id) await loadTemplate(id);
  };

  const onSave = async () => {
    const name = window.prompt('Strategy name:');
    if (name) await save(name);
  };

  const onClear = () => {
    if (window.confirm('Clear the canvas?')) {
      clear();
      setSelected('');
    }
  };

  return (
    <header className="toolbar">
      <div className="toolbar-left">
        <span className="brand">nodefin</span>
        <span className="brand-sub">portfolio research lab</span>
      </div>

      <div className="toolbar-center">
        <select
          className="template-select"
          value={selected}
          onChange={(e) => onTemplateChange(e.target.value)}
        >
          <option value="">Templates…</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      <div className="toolbar-right">
        <span className="status-text">{status}</span>
        <button className="btn btn-primary" onClick={run} disabled={running}>
          {running ? 'Running…' : 'Run'}
        </button>
        <button className="btn" onClick={validate}>
          Validate
        </button>
        <button className="btn" onClick={onSave}>
          Save
        </button>
        <button className="btn btn-danger" onClick={onClear}>
          Clear
        </button>
      </div>
    </header>
  );
}
