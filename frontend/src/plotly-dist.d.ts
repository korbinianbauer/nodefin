// plotly.js-dist-min ships no TypeScript types of its own, and we deliberately
// avoid pulling in the heavy @types/plotly.js dependency. This minimal ambient
// declaration covers exactly the surface we use (Plotly.react / Plotly.purge
// plus loose Data/Layout/Config aliases).
declare module 'plotly.js-dist-min' {
  namespace Plotly {
    // We intentionally keep these loose; the chart payloads are dynamic.
    type Data = Record<string, unknown>;
    type Layout = Record<string, unknown>;
    type Config = Record<string, unknown>;
  }

  function react(
    el: HTMLElement,
    data: Plotly.Data[],
    layout?: Partial<Plotly.Layout>,
    config?: Partial<Plotly.Config>,
  ): Promise<void>;

  function purge(el: HTMLElement): void;

  export { Plotly };
  export { react, purge };
  const _default: { react: typeof react; purge: typeof purge };
  export default _default;
}
