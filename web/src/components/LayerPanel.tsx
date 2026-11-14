import { ELEVATION_CSS_GRADIENT, LAYER_INFO, SIGMA_CSS_GRADIENT, SIGMA_SCALE_MAX_M, SLOPE_CSS_GRADIENT, SLOPE_SCALE_MAX_DEG, type TerrainLayer } from '../lib/layers';
import { ROUTE_STATUS_STYLE } from '../lib/format';
import { CAMERA_SMOOTHING, type CameraSmoothing } from '../lib/smoothing';
import { Info } from './Info';

interface StripProps {
  layer: TerrainLayer;
  onLayer: (l: TerrainLayer) => void;
  evaluator: boolean;
}

/** Map layer switch with its colour scale. Always visible: the scale is part of the legend. */
export function LayerStrip({ layer, onLayer, evaluator }: StripProps) {
  const layers: TerrainLayer[] = evaluator ? ['prior', 'belief', 'slope', 'sigma', 'reference'] : ['prior', 'belief', 'slope', 'sigma'];
  const sigma = layer === 'sigma';
  const slope = layer === 'slope';
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
        <div className="strip__bar" style={{ background: sigma ? SIGMA_CSS_GRADIENT : slope ? SLOPE_CSS_GRADIENT : ELEVATION_CSS_GRADIENT }} />
        <div className="strip__labels mono">
          <span>{sigma ? '0 m · certain' : slope ? '0° · flat' : 'low'}</span>
          <span>{sigma ? `≥ ${SIGMA_SCALE_MAX_M} m · uncertain` : slope ? `≥ ${SLOPE_SCALE_MAX_DEG}° · steep (CTX, 60 m window)` : 'high (relative height)'}</span>
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
  cameraSmoothing: CameraSmoothing;
  onCameraSmoothing: (v: CameraSmoothing) => void;
  /** The run's orbital image, if it has one. */
  imagery: { title: string; resolutionM: number } | null;
  showImagery: boolean;
  onShowImagery: (v: boolean) => void;
  surfaceDetail: boolean;
  onSurfaceDetail: (v: boolean) => void;
  trueScale: boolean;
  onTrueScale: (v: boolean) => void;
  /** Surroundings toggle; null when the run has none. */
  surroundings: boolean | null;
  onSurroundings: (v: boolean) => void;
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
        Vertical exaggeration <Info text="Heights are exaggerated for readability only; distances and data are unchanged." />
        <select value={p.exaggeration} onChange={(e) => p.onExaggeration(Number(e.target.value))}>
          {[1, 2, 3, 5].map((v) => (
            <option key={v} value={v}>
              {v}×
            </option>
          ))}
        </select>
      </label>

      {p.imagery && (
        <label className="check">
          <input type="checkbox" checked={p.showImagery} onChange={(e) => p.onShowImagery(e.target.checked)} /> CTX image <Info text={`Real CTX orthomosaic, ${p.imagery.resolutionM} m, contrast-stretched and tinted for display. Not drawn on the uncertainty layer.`} />
        </label>
      )}
      <label className="check">
        <input type="checkbox" checked={p.surfaceDetail} onChange={(e) => p.onSurfaceDetail(e.target.checked)} /> Ground grain <Info text="Cosmetic close-range detail (ripples, grit, stones). Not measured: the terrain data stops at 5-20 m." />
      </label>
      {p.surroundings != null && (
        <label className="check">
          <input type="checkbox" checked={p.surroundings} onChange={(e) => p.onSurroundings(e.target.checked)} /> Surroundings (20 km){' '}
          <Info text="The same CTX DTM and orthomosaic around the mission area, averaged to 100 m and 40 m. Real data, context only: not part of the mission map. Off: the area is drawn as a solid block." />
        </label>
      )}
      <label className="check">
        <input type="checkbox" checked={p.trueScale} onChange={(e) => p.onTrueScale(e.target.checked)} /> True-size agents{' '}
        <Info text="Astronaut 1.9 m, rover 4.1 m, drone 1.2 m rotor span, base at real size. Off: agents are enlarged with camera distance (up to 14x) so they stay visible on the 2 km map; visual only." />
      </label>
      <label className="check">
        <input type="checkbox" checked={p.contours} onChange={(e) => p.onContours(e.target.checked)} /> Contours <Info text="Every 10 m, bold every 50 m, at true elevation." />
      </label>
      <label className="check">
        <input type="checkbox" checked={p.follow} onChange={(e) => p.onFollow(e.target.checked)} /> Follow selected agent (F)
      </label>
      <label className="row-opt">
        Camera smoothing
        <select value={p.cameraSmoothing} onChange={(e) => p.onCameraSmoothing(e.target.value as CameraSmoothing)}>
          {(Object.keys(CAMERA_SMOOTHING) as CameraSmoothing[]).map((k) => (
            <option key={k} value={k}>
              {CAMERA_SMOOTHING[k].label}
            </option>
          ))}
        </select>
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
