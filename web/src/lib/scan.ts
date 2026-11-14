import type { TerrainMeta } from '../types/icd';
import { cellCenter } from './coords';

/**
 * Drone-camera terrain scan (display only).
 *
 * The scan does NOT create an observation: it reads the slope already computed from the orbital
 * CTX DTM prior (lib/slope, Horn 3x3 on the 20 m grid) for the cells around the drone and draws
 * them as markers. The map version, belief, sigma and routes are unchanged. The bands below are
 * display thresholds chosen for legibility, not certified traversability limits; they await
 * science approval (docs/science_decisions.md) before any operational use.
 */
export const SCAN_RADIUS_M = 160;
/** Time for the scan front to reach SCAN_RADIUS_M (s), and how long the marks stay (s). */
export const SCAN_SWEEP_S = 1.6;
export const SCAN_HOLD_S = 14;
/** Display bands of the orbital slope (deg): below the first = gentle, below the second = moderate. */
export const SCAN_BANDS_DEG = [8, 15] as const;

export type ScanClass = 'gentle' | 'moderate' | 'steep' | 'nodata';

export const SCAN_CLASS_INFO: Record<ScanClass, { label: string; color: string }> = {
  gentle: { label: `< ${SCAN_BANDS_DEG[0]}° gentle`, color: '#65cbe8' },
  moderate: { label: `${SCAN_BANDS_DEG[0]}–${SCAN_BANDS_DEG[1]}° moderate`, color: '#e3c25a' },
  steep: { label: `≥ ${SCAN_BANDS_DEG[1]}° steep`, color: '#e0583f' },
  nodata: { label: 'no slope (NoData / edge)', color: '#8a9096' },
};

export function scanClass(slopeDeg: number | null | undefined): ScanClass {
  if (slopeDeg == null || !Number.isFinite(slopeDeg)) return 'nodata';
  if (slopeDeg < SCAN_BANDS_DEG[0]) return 'gentle';
  if (slopeDeg < SCAN_BANDS_DEG[1]) return 'moderate';
  return 'steep';
}

export interface ScanMark {
  /** ENU cell centre (m). */
  x: number;
  y: number;
  /** Distance from the scan origin on the ground (m): the front reaches it at distance / radius of the sweep. */
  distanceM: number;
  slopeDeg: number | null;
  cls: ScanClass;
}

type GridMeta = Pick<TerrainMeta, 'origin_x_m' | 'origin_y_m' | 'resolution_m' | 'rows' | 'cols'>;

/** Cells whose centre lies within `radiusM` of (x, y), nearest first, with their orbital slope band. */
export function scanCells(meta: GridMeta, slope: ReadonlyArray<number | null>, x: number, y: number, radiusM = SCAN_RADIUS_M): ScanMark[] {
  const res = meta.resolution_m;
  const c0 = Math.max(0, Math.floor((x - radiusM - meta.origin_x_m) / res));
  const c1 = Math.min(meta.cols - 1, Math.floor((x + radiusM - meta.origin_x_m) / res));
  const r0 = Math.max(0, Math.floor((y - radiusM - meta.origin_y_m) / res));
  const r1 = Math.min(meta.rows - 1, Math.floor((y + radiusM - meta.origin_y_m) / res));
  const out: ScanMark[] = [];
  for (let r = r0; r <= r1; r++) {
    for (let c = c0; c <= c1; c++) {
      const p = cellCenter(meta, r, c);
      const d = Math.hypot(p.x - x, p.y - y);
      if (d > radiusM) continue;
      const s = slope[r * meta.cols + c];
      out.push({ x: p.x, y: p.y, distanceM: d, slopeDeg: s ?? null, cls: scanClass(s) });
    }
  }
  return out.sort((a, b) => a.distanceM - b.distanceM);
}

/** Count of marks per band (for the HUD readout). */
export function scanSummary(marks: ReadonlyArray<ScanMark>): Record<ScanClass, number> {
  const n: Record<ScanClass, number> = { gentle: 0, moderate: 0, steep: 0, nodata: 0 };
  for (const m of marks) n[m.cls]++;
  return n;
}

/** Bearing from (x0, y0) to (x1, y1), clockwise from north (deg, 0..360). */
export function bearingDeg(x0: number, y0: number, x1: number, y1: number): number {
  const deg = (Math.atan2(x1 - x0, y1 - y0) * 180) / Math.PI;
  return (deg + 360) % 360;
}

/** Signed smallest angle from `from` to `to` (deg, -180..180). */
export function angleDiffDeg(from: number, to: number): number {
  return ((((to - from) % 360) + 540) % 360) - 180;
}
