import { TerrainView } from "./components/TerrainView";

export function App() {
  return <main>
    <header><div><p className="eyebrow">Houston, We Have a Bug!</p><h1>Mars Gods Eye</h1></div><span className="badge">SCAFFOLD · NO MISSION LOADED</span></header>
    <p className="intro">Mission viewer foundation. Terrain, routes and observations will appear here after the shared contracts are connected.</p>
    <div className="workspace">
      <section className="viewport" aria-labelledby="terrain-title">
        <h2 id="terrain-title">Local map view</h2><TerrainView />
        <p className="caption">Coordinate preview only · metres · X east, Y up, −Z north. Drag to orbit; scroll to zoom.</p>
      </section>
      <aside aria-label="Mission information">
        <section><h2>Mission</h2><dl><dt>Mode</dt><dd>Not connected</dd><dt>Objective</dt><dd>Not loaded</dd><dt>Route</dt><dd>Not evaluated</dd><dt>Return feasibility</dt><dd>Not evaluated</dd><dt>Energy / oxygen</dt><dd>Not estimated</dd><dt>Map version</dt><dd>Not loaded</dd></dl></section>
        <section><h2>Replay</h2><p>No recorded run is bundled yet. No backend connection is required to open this scaffold.</p></section>
        <section><h2>Layers &amp; events</h2><p>Prior, belief, uncertainty, previous/current route and causal events await validated data.</p></section>
      </aside>
    </div>
    <footer>No NASA terrain, mission results or certified safety estimates are included. This scaffold is not a completed competition demo.</footer>
  </main>;
}
