import type { RasterSet } from '../types/replay';
import { versionKey } from './layers';

/**
 * Base image of the 2D tactical map: the updated map in hypsometric blue bands, shaded by
 * relief, with the cells that agents have observed drawn brighter as coverage. Pure function
 * so it can be tested; the component only blits it to a canvas.
 */
export const MAP_BANDS = 9;

/** Dark-to-light blue steps used for the elevation bands (low = dark). */
const BAND_RGB: Array<[number, number, number]> = [
  [14, 38, 78], [20, 54, 104], [28, 72, 132], [40, 92, 158], [58, 114, 182],
  [84, 140, 205], [118, 170, 224], [160, 200, 240], [206, 228, 250],
];

export function bandOf(h: number, lo: number, hi: number, bands = MAP_BANDS): number {
  if (!(hi > lo)) return 0;
  return Math.min(bands - 1, Math.max(0, Math.floor(((h - lo) / (hi - lo)) * bands)));
}

/** Lambert hillshade (0..1) of a row-major grid, light from the north-west at 45 degrees. */
export function hillshade(grid: ReadonlyArray<number | null>, rows: number, cols: number, res: number): Float32Array {
  const out = new Float32Array(rows * cols).fill(1);
  const az = (315 * Math.PI) / 180;
  const alt = (45 * Math.PI) / 180;
  const at = (r: number, c: number) => grid[Math.min(rows - 1, Math.max(0, r)) * cols + Math.min(cols - 1, Math.max(0, c))];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const h = at(r, c);
      if (h == null) continue;
      const e = at(r, c + 1) ?? h, w = at(r, c - 1) ?? h, n = at(r + 1, c) ?? h, s = at(r - 1, c) ?? h;
      const dzdx = (e - w) / (2 * res);
      const dzdy = (n - s) / (2 * res);
      const slope = Math.atan(Math.hypot(dzdx, dzdy));
      const aspect = Math.atan2(dzdy, -dzdx);
      out[r * cols + c] = Math.max(0, Math.cos(alt) * Math.cos(slope) + Math.sin(alt) * Math.sin(slope) * Math.cos(az - aspect));
    }
  }
  return out;
}

/** Heights at the band edges so each band holds the same share of the map (a few high points do not flatten the rest). */
export function quantileEdges(values: ReadonlyArray<number>, bands = MAP_BANDS): number[] {
  if (values.length === 0) return [];
  const sorted = [...values].sort((a, b) => a - b);
  const edges: number[] = [];
  for (let k = 1; k < bands; k++) edges.push(sorted[Math.min(sorted.length - 1, Math.floor((k / bands) * (sorted.length - 1)))]);
  return edges;
}

/** Band index of a height given the quantile edges. */
export function bandByEdges(h: number, edges: ReadonlyArray<number>): number {
  let lo = 0;
  let hi = edges.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (h >= edges[mid]) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/** Height-per-cell scale for the hillshade so the steeper tenth of the map reads about 38 degrees, whatever the relief. */
export function shadeScale(grid: ReadonlyArray<number | null>, rows: number, cols: number): number {
  const g: number[] = [];
  const at = (r: number, c: number) => grid[Math.min(rows - 1, Math.max(0, r)) * cols + Math.min(cols - 1, Math.max(0, c))];
  for (let r = 1; r < rows - 1; r += 2) {
    for (let c = 1; c < cols - 1; c += 2) {
      const e = at(r, c + 1), w = at(r, c - 1), n = at(r + 1, c), s = at(r - 1, c);
      if (e == null || w == null || n == null || s == null) continue;
      g.push(Math.hypot(e - w, n - s) / 2);
    }
  }
  if (g.length === 0) return 1;
  g.sort((a, b) => a - b);
  return Math.max(1e-6, g[Math.floor(0.9 * (g.length - 1))] / 0.8);
}

export interface TacticalBase {
  /** RGBA, row 0 = NORTH (canvas order). */
  pixels: Uint8ClampedArray;
  width: number;
  height: number;
  observed: number;
  total: number;
}

/** One pixel per terrain cell; the canvas scales it up with smoothing off for the blocky look. */
export function tacticalBase(rasters: RasterSet, mapVersion: number): TacticalBase {
  const { rows, cols } = rasters;
  const v = rasters.versions[versionKey(rasters, mapVersion)];
  const grid = v.belief;
  const edges = quantileEdges(rasters.prior.filter((h): h is number => h != null));
  // Shading uses relative slope only; its scale adapts to the relief so a flat area still shows its shape.
  const shade = hillshade(grid, rows, cols, shadeScale(grid, rows, cols));
  const seen = new Set(v.observed);
  const pixels = new Uint8ClampedArray(rows * cols * 4);
  let total = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      const o = ((rows - 1 - r) * cols + c) * 4; // flip: canvas row 0 is the north edge
      const h = grid[i];
      if (h == null) {
        pixels[o + 3] = 0;
        continue;
      }
      total++;
      const base = BAND_RGB[bandByEdges(h, edges)];
      const k = 0.5 + 0.75 * shade[i];
      const lit = seen.has(i) ? 1.3 : 0.95; // coverage: observed cells glow brighter
      pixels[o] = base[0] * k * lit + (seen.has(i) ? 30 : 0);
      pixels[o + 1] = base[1] * k * lit + (seen.has(i) ? 40 : 0);
      pixels[o + 2] = base[2] * k * lit + (seen.has(i) ? 50 : 0);
      pixels[o + 3] = 255;
    }
  }
  return { pixels, width: cols, height: rows, observed: seen.size, total };
}
