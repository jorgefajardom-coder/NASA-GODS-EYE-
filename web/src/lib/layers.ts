import type { RasterSet, ReplayManifest } from '../types/replay';

export type TerrainLayer = 'prior' | 'belief' | 'slope' | 'sigma' | 'reference';

export const LAYER_INFO: Record<TerrainLayer, { label: string; description: string }> = {
  prior: { label: 'Orbital map', description: 'Prior from orbit. Fixed for the whole run.' },
  belief: { label: 'Updated map', description: 'Recorded and unclassified runs use the current replay map version. Explicit illustrative SIMULATION demos use the final retrospective surface for visual stability; observed-cell tints still follow the current map version.' },
  slope: {
    label: 'Slope',
    description:
      'Slope derived from the public orbital prior with Horn 3×3, never from local observations or the updated belief. The computational grid and native source spacing are stated for this run. Sub-grid hazards remain unresolved; this is not a local hazard measurement.',
  },
  sigma: {
    label: 'Uncertainty',
    description:
      'One-sigma height uncertainty of the updated map. Assumed, not measured: the demo sets it by hand (1 m, 3 m on the surveyed crossing, 0.2 m once observed) and no source product supplies a per-cell error yet.',
  },
  reference: { label: 'Reference (evaluator)', description: 'Hidden ground truth used only to evaluate. The planner never sees it.' },
};

/** Highest map version available for an explicitly retrospective illustrative demo. */
export function latestMapVersion(rasters: RasterSet): number {
  return Math.max(...Object.keys(rasters.versions).map(Number));
}

/**
 * Only an explicitly illustrative simulation may use a retrospective surface.
 * Recorder and unknown sources retain their causal map history by default.
 */
export function retrospectiveShapeAllowed(manifest: Pick<ReplayManifest, 'illustrative' | 'source_mode'>): boolean {
  return manifest.illustrative === true && manifest.source_mode === 'SIMULATION';
}

/** Belief and uncertainty share one surface; their tints/values retain the current version. */
export function shapeGrid(rasters: RasterSet, layer: TerrainLayer, version: number, retrospectiveDemo = false): (number | null)[] {
  const retrospective = retrospectiveDemo && (layer === 'belief' || layer === 'sigma');
  return heightGrid(rasters, layer, retrospective ? latestMapVersion(rasters) : version);
}

/** Map version available at or before `version` (versions may skip numbers). */
export function versionKey(rasters: RasterSet, version: number): string {
  const keys = Object.keys(rasters.versions)
    .map(Number)
    .filter((v) => v <= version)
    .sort((a, b) => a - b);
  return String(keys.length ? keys[keys.length - 1] : Math.min(...Object.keys(rasters.versions).map(Number)));
}

/** Heights that shape the mesh for a layer. Sigma is drawn on the updated map. */
export function heightGrid(rasters: RasterSet, layer: TerrainLayer, version: number): (number | null)[] {
  if (layer === 'prior' || layer === 'slope') return rasters.prior; // slope is computed on the orbital map
  if (layer === 'reference' && rasters.reference) return rasters.reference;
  if (layer === 'reference') return rasters.prior; // not loaded: the layer is not offered
  return rasters.versions[versionKey(rasters, version)].belief;
}

export function finiteRange(values: ReadonlyArray<number | null>): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const v of values) {
    if (v == null || !Number.isFinite(v)) continue;
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  return Number.isFinite(lo) ? [lo, hi] : [0, 1];
}

type Rgb = [number, number, number];
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
function ramp(stops: Rgb[], t: number): Rgb {
  const x = Math.max(0, Math.min(1, t)) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(x));
  const f = x - i;
  return [lerp(stops[i][0], stops[i + 1][0], f), lerp(stops[i][1], stops[i + 1][1], f), lerp(stops[i][2], stops[i + 1][2], f)];
}

const ELEVATION: Rgb[] = [
  [0.23, 0.12, 0.08],
  [0.47, 0.24, 0.14],
  [0.7, 0.42, 0.26],
  [0.86, 0.66, 0.47],
  [0.95, 0.86, 0.72],
];
/** Sequential, colour-blind-safe-ish: dark blue (certain) to bright yellow (uncertain). */
const SIGMA: Rgb[] = [
  [0.1, 0.16, 0.36],
  [0.26, 0.3, 0.62],
  [0.62, 0.32, 0.6],
  [0.93, 0.5, 0.33],
  [0.98, 0.88, 0.3],
];

export const SIGMA_SCALE_MAX_M = 3;

/** Sequential, one hue: pale sand (gentle) to dark red-brown (steep). */
const SLOPE: Rgb[] = [
  [0.93, 0.88, 0.78],
  [0.93, 0.72, 0.48],
  [0.85, 0.48, 0.26],
  [0.66, 0.24, 0.13],
  [0.4, 0.08, 0.06],
];
export const SLOPE_SCALE_MAX_DEG = 30;

export function slopeColor(deg: number): Rgb {
  return ramp(SLOPE, deg / SLOPE_SCALE_MAX_DEG);
}

export function elevationColor(h: number, lo: number, hi: number): Rgb {
  return ramp(ELEVATION, hi > lo ? (h - lo) / (hi - lo) : 0.5);
}

export function sigmaColor(s: number): Rgb {
  return ramp(SIGMA, s / SIGMA_SCALE_MAX_M);
}

export const ELEVATION_CSS_GRADIENT = `linear-gradient(90deg, ${ELEVATION.map((c) => `rgb(${c.map((v) => Math.round(v * 255)).join(',')})`).join(',')})`;
export const SIGMA_CSS_GRADIENT = `linear-gradient(90deg, ${SIGMA.map((c) => `rgb(${c.map((v) => Math.round(v * 255)).join(',')})`).join(',')})`;
export const SLOPE_CSS_GRADIENT = `linear-gradient(90deg, ${SLOPE.map((c) => `rgb(${c.map((v) => Math.round(v * 255)).join(',')})`).join(',')})`;
