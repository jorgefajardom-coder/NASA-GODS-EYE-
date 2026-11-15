import type { TerrainMeta } from '../types/icd';
import { cellAt } from '../lib/coords';
import { scanClass } from '../lib/scan';
import type { IndicatorClass } from './ScanConfig';

/**
 * Indicator layout for one scan (pure, tested): points on rings around the origin whose spacing
 * grows from `nearM` at the origin to `farM` at the edge, each classified from data the viewer
 * already has: the orbital slope of its 20 m cell (lib/scan display bands, pending science
 * approval) or NoData. Nothing is invented: no random hazards, no new observation.
 */
export interface IndicatorPoint {
  /** Local ENU position (m). */
  x: number;
  y: number;
  /** Distance from the origin on the ground (m): the front reveals the point at distance / speed. */
  distanceM: number;
  cls: IndicatorClass;
}

const CLASS_OF = { gentle: 'traversable', moderate: 'caution', steep: 'hazard', nodata: 'unknown' } as const;

/** Spacing at a distance from the origin, linear between near and far. */
export function spacingAt(distanceM: number, rangeM: number, nearM: number, farM: number): number {
  const k = Math.max(0, Math.min(1, distanceM / rangeM));
  return nearM + (farM - nearM) * k;
}

/** Class of a ground point from the slope raster of the run (NoData or outside the grid -> unknown). */
export function classifyPoint(meta: Pick<TerrainMeta, 'origin_x_m' | 'origin_y_m' | 'resolution_m' | 'rows' | 'cols'>, slope: ReadonlyArray<number | null>, x: number, y: number): IndicatorClass {
  const cell = cellAt(meta, x, y);
  if (!cell) return 'unknown';
  return CLASS_OF[scanClass(slope[cell.index])];
}

/**
 * Points within `rangeM` of (ox, oy). A small golden-angle offset per ring keeps rings from lining
 * up into spokes. At most `max` points, nearest first (the pool never grows).
 */
export function layoutIndicators(
  meta: Pick<TerrainMeta, 'origin_x_m' | 'origin_y_m' | 'resolution_m' | 'rows' | 'cols'>,
  slope: ReadonlyArray<number | null>,
  ox: number,
  oy: number,
  opts: { rangeM: number; nearM: number; farM: number; max: number },
): IndicatorPoint[] {
  const out: IndicatorPoint[] = [];
  let r = opts.nearM;
  let ring = 0;
  while (r <= opts.rangeM && out.length < opts.max) {
    const s = spacingAt(r, opts.rangeM, opts.nearM, opts.farM);
    const n = Math.max(6, Math.round((2 * Math.PI * r) / s));
    const phase = ring * 2.39996; // golden angle
    for (let k = 0; k < n && out.length < opts.max; k++) {
      const a = phase + (k / n) * Math.PI * 2;
      const x = ox + Math.cos(a) * r;
      const y = oy + Math.sin(a) * r;
      out.push({ x, y, distanceM: r, cls: classifyPoint(meta, slope, x, y) });
    }
    r += s;
    ring += 1;
  }
  return out;
}
