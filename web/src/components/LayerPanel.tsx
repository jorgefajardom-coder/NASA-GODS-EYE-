import { ELEVATION_CSS_GRADIENT, LAYER_INFO, SIGMA_CSS_GRADIENT, SIGMA_SCALE_MAX_M, type TerrainLayer } from '../lib/layers';
import { ROUTE_STATUS_STYLE } from '../lib/format';

interface StripProps {
  layer: TerrainLayer;
  onLayer: (l: TerrainLayer) => void;
  evaluator: boolean;
}

/** Map layer switch with its colour scale. Always visible: the scale is part of the legend. */
export function LayerStrip({ layer, onLayer, evaluator }: StripProps) {
  const layers: TerrainLayer[] = evaluator ? ['prior', 'belief', 'sigma', 'reference'] : ['prior', 'belief', 'sigma'];
  const sigma = layer === 'sigma';
  return (
    <div className="strip">
      <div className="strip__row" role="radiogroup" aria-label="Map layer">
        {layers.map((l) => (
          <button
            key={l}
            type="button"
            role="radio"
            aria-checked={layer === l}
            className={`strip__btn${layer === l ? ' is-active' : ''}`}
            title={LAYER_INFO[l].description}
            onClick={() => onLayer(l)}
          >
            {LAYER_INFO[l].label}
          </button>
        ))}
      </div>
      <div className="strip__scale">
        <div className="strip__bar" style={{ background: sigma ? SIGMA_CSS_GRADIENT : ELEVATION_CSS_GRADIENT }} />
        <div className="strip__labels mono">
          <span>{sigma ? '0 m · certain' : 'low'}</span>
          <span>{sigma ? `≥ ${SIGMA_SCALE_MAX_M} m · uncertain` : 'high (relative height)'}</span>
        </div>
      </div>
    </div>
  );
}

interface OptionsProps {
  exaggeration: number;
  onExaggeration: (v: number) => void;
  showControlPoints: boolean;
  onShowControlPoints: (v: boolean) => void;
  showLabels: boolean;
  onShowLabels: (v: boolean) => void;
  follow: boolean;
  onFollow: (v: boolean) => void;
  contours: boolean;
  onContours: (v: boolean) => void;
}

/** View options and legend, collapsed by default so they do not cover the terrain. */
export function ViewOptions(p: OptionsProps) {
  return (
    <details className="opts">
      <summary>View options and legend</summary>
      <ul className="legend">
        <li>
          <span className="swatch" style={{ borderColor: ROUTE_STATUS_STYLE.FEASIBLE.color }} aria-hidden /> Route in force, solid = feasible
        </li>
        <li>
          <span className="swatch swatch--dashed" style={{ borderColor: ROUTE_STATUS_STYLE.FEASIBLE.color }} aria-hidden /> Return leg
        </li>
        <li>
          <span className="swatch swatch--dashed" style={{ borderColor: '#D95045' }} aria-hidden /> Invalidated route, kept for comparison
        </li>
        <li>
          <span className="swatch swatch--dashed" style={{ borderColor: ROUTE_STATUS_STYLE.UNKNOWN.color }} aria-hidden /> Route not verified, no ETA shown
        </li>
        <li>
          <span className="swatch-box swatch-box--observed" aria-hidden /> Cells observed by an agent (updated map)
        </li>
      </ul>
      <label className="row-opt">
        Vertical exaggeration
        <select value={p.exaggeration} onChange={(e) => p.onExaggeration(Number(e.target.value))}>
          {[1, 2, 3, 5].map((v) => (
            <option key={v} value={v}>
              {v}×
            </option>
          ))}
        </select>
      </label>
      {p.exaggeration !== 1 && <p className="note note--warn">Heights exaggerated {p.exaggeration}× for readability (visual only).</p>}
      <label className="check">
        <input type="checkbox" checked={p.contours} onChange={(e) => p.onContours(e.target.checked)} /> Contour lines (10 m, bold every 50 m)
      </label>
      <p className="note">The surface is smoothed between the 20 m source cells for display. This adds no detail: heights at cell centres are the source values.</p>
      <label className="check">
        <input type="checkbox" checked={p.follow} onChange={(e) => p.onFollow(e.target.checked)} /> Follow selected agent (F)
      </label>
      <label className="check">
        <input type="checkbox" checked={p.showLabels} onChange={(e) => p.onShowLabels(e.target.checked)} /> Labels in the scene
      </label>
      <label className="check">
        <input type="checkbox" checked={p.showControlPoints} onChange={(e) => p.onShowControlPoints(e.target.checked)} /> Control points (J-01)
      </label>
    </details>
  );
}
