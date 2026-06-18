import { useEffect, useRef } from 'react';
// plotly.js-dist-min ships a prebuilt bundle; no peer-dep juggling needed.
import Plotly, { type Plotly as PlotlyNS } from 'plotly.js-dist-min';

interface PlotProps {
  data: PlotlyNS.Data[];
  layout?: Partial<PlotlyNS.Layout>;
  config?: Partial<PlotlyNS.Config>;
  className?: string;
}

const DARK_LAYOUT: Partial<PlotlyNS.Layout> = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#d8dee9', family: 'Inter, system-ui, sans-serif', size: 12 },
  margin: { l: 56, r: 24, t: 28, b: 44 },
  legend: { orientation: 'h', y: -0.2 },
  xaxis: { gridcolor: '#2a2f3a', zerolinecolor: '#2a2f3a' },
  yaxis: { gridcolor: '#2a2f3a', zerolinecolor: '#2a2f3a' },
};

export function Plot({ data, layout, config, className }: PlotProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const merged: Partial<PlotlyNS.Layout> = {
      ...DARK_LAYOUT,
      ...layout,
      xaxis: { ...(DARK_LAYOUT.xaxis as object), ...(layout?.xaxis as object) },
      yaxis: { ...(DARK_LAYOUT.yaxis as object), ...(layout?.yaxis as object) },
    };
    Plotly.react(el, data, merged, {
      responsive: true,
      displaylogo: false,
      ...config,
    });
  }, [data, layout, config]);

  useEffect(() => {
    const el = ref.current;
    return () => {
      if (el) Plotly.purge(el);
    };
  }, []);

  return <div ref={ref} className={className} style={{ width: '100%', height: '100%' }} />;
}
