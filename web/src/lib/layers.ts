import type { RasterSet } from '../types/replay';

export type TerrainLayer = 'prior' | 'belief' | 'sigma' | 'reference';

export const LAYER_INFO: Record<TerrainLayer, { label: string; description: string }> = {
  prior: { label: 'Orbital map', description: 'Prior from orbit. Fixed for the whole run.' },
  belief: { label: 'Updated map', description: 'Prior plus agent observations up to the current map version.' },
  sigma: { label: 'Uncertainty', description: 'One-sigma height uncertainty of the updated map.' },
  reference: { label: 'Reference (evaluator)', description: 'Hidden ground truth used only to evaluate. The planner never sees it.' },
};

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
  if (layer === 'prior') return rasters.prior;
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

export function elevationColor(h: number, lo: number, hi: number): Rgb {
  return ramp(ELEVATION, hi > lo ? (h - lo) / (hi - lo) : 0.5);
}

export function sigmaColor(s: number): Rgb {
  return ramp(SIGMA, s / SIGMA_SCALE_MAX_M);
}

export const ELEVATION_CSS_GRADIENT = `linear-gradient(90deg, ${ELEVATION.map((c) => `rgb(${c.map((v) => Math.round(v * 255)).join(',')})`).join(',')})`;
export const SIGMA_CSS_GRADIENT = `linear-gradient(90deg, ${SIGMA.map((c) => `rgb(${c.map((v) => Math.round(v * 255)).join(',')})`).join(',')})`;
