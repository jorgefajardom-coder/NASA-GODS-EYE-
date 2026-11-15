import type { RasterSet } from '../types/replay';
import type { TerrainMeta } from '../types/icd';
import { finiteRange, versionKey } from './layers';

/**
 * Drone survey map (display only): what the replay says the drone has mapped so far. It reads the
 * map version in force at the replay time: its belief heights and the cells marked observed. In the
 * demo these observations are simulated (the drone's survey of the corridor publishes map v2);
 * the viewer draws them in a point-cloud style but they are not a LiDAR measurement.
 */
export interface SurveyPoint {
  /** Local ENU cell centre (m). */
  x: number;
  y: number;
  /** Belief height (m) and its 0..1 share of the height range of the area. */
  h: number;
  t: number;
  observed: boolean;
}

export interface DroneSurvey {
  mapVersion: number;
  observedCount: number;
  totalCount: number;
  points: SurveyPoint[];
}

/** Cells within `radiusM` of (cx, cy) with their belief height and whether the drone has observed them. */
export function droneSurvey(rasters: RasterSet, meta: Pick<TerrainMeta, 'origin_x_m' | 'origin_y_m' | 'resolution_m' | 'rows' | 'cols'>, mapVersion: number, cx: number, cy: number, radiusM: number): DroneSurvey {
  const v = rasters.versions[versionKey(rasters, mapVersion)];
  const seen = new Set(v?.observed ?? []);
  const [lo, hi] = finiteRange(rasters.prior);
  const span = hi > lo ? hi - lo : 1;
  const res = meta.resolution_m;
  const points: SurveyPoint[] = [];
  const c0 = Math.max(0, Math.floor((cx - radiusM - meta.origin_x_m) / res));
  const c1 = Math.min(meta.cols - 1, Math.floor((cx + radiusM - meta.origin_x_m) / res));
  const r0 = Math.max(0, Math.floor((cy - radiusM - meta.origin_y_m) / res));
  const r1 = Math.min(meta.rows - 1, Math.floor((cy + radiusM - meta.origin_y_m) / res));
  for (let r = r0; r <= r1; r++) {
    for (let c = c0; c <= c1; c++) {
      const i = r * meta.cols + c;
      const h = v?.belief[i] ?? null;
      if (h == null || !Number.isFinite(h)) continue; // NoData stays empty
      const x = meta.origin_x_m + (c + 0.5) * res;
      const y = meta.origin_y_m + (r + 0.5) * res;
      if (Math.hypot(x - cx, y - cy) > radiusM) continue;
      points.push({ x, y, h, t: Math.max(0, Math.min(1, (h - lo) / span)), observed: seen.has(i) });
    }
  }
  return { mapVersion, observedCount: seen.size, totalCount: meta.rows * meta.cols, points };
}
