import type { RasterSet } from '../types/replay';
import type { MissionEvent, TerrainMeta } from '../types/icd';
import { versionKey } from './layers';
import { slopeDegrees } from './slope';
import { SCAN_BANDS_DEG } from './scan';
import { bearingDeg } from './scan';

/**
 * Drone hazard report (display only): what the drone's observations in the replay say is dangerous.
 * For every cell the map version in force marks as observed it reads the updated (belief) height
 * and gives:
 * - its slope (Horn 3x3 on the belief grid) in the viewer's display bands (lib/scan, pending
 *   science approval): steep = hazard, moderate = caution;
 * - its change against the orbital prior, flagged when it exceeds twice the prior's sigma (the
 *   observation contradicts the estimate, e.g. an unmapped scarp).
 * In the demo these observations are simulated; nothing here is a LiDAR measurement or a new
 * observation, and the mission and planner keep the authority.
 */
export type HazardLevel = 'hazard' | 'caution' | 'changed' | 'clear';

export interface HazardCell {
  x: number;
  y: number;
  slopeDeg: number | null;
  /** Belief minus prior height (m). */
  deltaM: number;
  changed: boolean;
  level: HazardLevel;
}

export interface HazardReport {
  mapVersion: number;
  observedCount: number;
  cells: HazardCell[];
  counts: Record<HazardLevel, number>;
  maxSlopeDeg: number | null;
  maxChangeM: number;
  /** Nearest hazard or changed cell to the drone: ground distance (m) and bearing (deg from north). */
  nearest: { distanceM: number; bearingDeg: number; level: HazardLevel } | null;
}

/** Twice the prior's sigma: a change beyond it is a contradiction of the orbital estimate. */
export const CHANGE_SIGMA_FACTOR = 2;

type GridMeta = Pick<TerrainMeta, 'origin_x_m' | 'origin_y_m' | 'resolution_m' | 'rows' | 'cols'>;

export function droneHazardReport(rasters: RasterSet, meta: GridMeta, mapVersion: number, droneX: number, droneY: number): HazardReport {
  const key = versionKey(rasters, mapVersion);
  const v = rasters.versions[key];
  const first = rasters.versions[Object.keys(rasters.versions).sort((a, b) => Number(a) - Number(b))[0]];
  const counts: Record<HazardLevel, number> = { hazard: 0, caution: 0, changed: 0, clear: 0 };
  const cells: HazardCell[] = [];
  if (!v || !v.observed.length) return { mapVersion, observedCount: 0, cells, counts, maxSlopeDeg: null, maxChangeM: 0, nearest: null };
  const slope = slopeDegrees(v.belief, meta.rows, meta.cols, meta.resolution_m);
  let maxSlope: number | null = null;
  let maxChange = 0;
  let nearest: HazardReport['nearest'] = null;
  for (const i of v.observed) {
    const h = v.belief[i];
    const p = rasters.prior[i];
    if (h == null || p == null) continue;
    const r = Math.floor(i / meta.cols);
    const c = i % meta.cols;
    const x = meta.origin_x_m + (c + 0.5) * meta.resolution_m;
    const y = meta.origin_y_m + (r + 0.5) * meta.resolution_m;
    const s = slope[i];
    const deltaM = h - p;
    const sigma = first?.sigma[i] ?? null;
    const changed = sigma != null && Math.abs(deltaM) > CHANGE_SIGMA_FACTOR * sigma;
    const level: HazardLevel = s != null && s >= SCAN_BANDS_DEG[1] ? 'hazard' : s != null && s >= SCAN_BANDS_DEG[0] ? 'caution' : changed ? 'changed' : 'clear';
    counts[level] += 1;
    if (s != null) maxSlope = maxSlope == null ? s : Math.max(maxSlope, s);
    maxChange = Math.max(maxChange, Math.abs(deltaM));
    cells.push({ x, y, slopeDeg: s, deltaM, changed, level });
    if (level === 'hazard' || changed) {
      const d = Math.hypot(x - droneX, y - droneY);
      if (!nearest || d < nearest.distanceM) nearest = { distanceM: d, bearingDeg: bearingDeg(droneX, droneY, x, y), level };
    }
  }
  return { mapVersion, observedCount: cells.length, cells, counts, maxSlopeDeg: maxSlope, maxChangeM: maxChange, nearest };
}

/** The drone's map update and what it caused, up to the replay time (for the report's status line). */
export function droneReportEvents(events: ReadonlyArray<MissionEvent>, droneId: string, t: number): { mapUpdate: MissionEvent | null; invalidated: MissionEvent | null } {
  const past = events.filter((e) => e.timestamp_sim_s <= t);
  const mapUpdate = [...past].reverse().find((e) => e.event_type === 'MAP_UPDATED' && e.agent_id === droneId) ?? null;
  const invalidated = mapUpdate ? past.find((e) => e.event_type === 'ROUTE_INVALIDATED' && e.timestamp_sim_s >= mapUpdate.timestamp_sim_s) ?? null : null;
  return { mapUpdate, invalidated };
}
