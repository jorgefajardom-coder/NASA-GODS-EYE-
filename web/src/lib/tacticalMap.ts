import type { RasterSet } from '../types/replay';
import { finiteRange, versionKey } from './layers';

/**
 * Base image of the 2D tactical map: the updated map in hypsometric blue bands, shaded by
 * relief, with the cells that agents have observed drawn brighter as coverage. Pure function
 * so it can be tested; the component only blits it to a canvas.
 */
export const MAP_BANDS = 9;

/** Dark-to-light blue steps used for the elevation bands (low = dark). */
const BAND_RGB: Array<[number, number, number]> = [
  [6, 22, 48], [9, 34, 70], [12, 47, 94], [17, 62, 120], [24, 80, 146],
  [34, 100, 170], [52, 124, 192], [80, 152, 212], [122, 186, 230],
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
  const [lo, hi] = finiteRange(rasters.prior);
  const res = 1; // shading uses relative slope only; absolute scale does not matter for the look
  const shade = hillshade(grid, rows, cols, res * Math.max(1, (hi - lo) / 40));
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
      const base = BAND_RGB[bandOf(h, lo, hi)];
      const k = 0.55 + 0.6 * shade[i];
      const lit = seen.has(i) ? 1.35 : 0.8; // coverage: observed cells glow brighter
      pixels[o] = base[0] * k * lit + (seen.has(i) ? 30 : 0);
      pixels[o + 1] = base[1] * k * lit + (seen.has(i) ? 40 : 0);
      pixels[o + 2] = base[2] * k * lit + (seen.has(i) ? 50 : 0);
      pixels[o + 3] = 255;
    }
  }
  return { pixels, width: cols, height: rows, observed: seen.size, total };
}
