import type { Point, TerrainMeta } from '../types/icd';

/**
 * Frame conventions (ICD §1):
 *   ROS `map` (ENU): x east, y north, z up, metres.
 *   Three.js:        x east, y up,    z = -north.
 * Vertical exaggeration is visual only and is applied to the up axis.
 */
export function enuToThree(p: Point, verticalExaggeration = 1): [number, number, number] {
  return [p.x, p.z * verticalExaggeration, -p.y];
}

export function threeToEnu(v: [number, number, number], verticalExaggeration = 1): Point {
  return { x: v[0], y: -v[2], z: v[1] / verticalExaggeration };
}

type GridMeta = Pick<TerrainMeta, 'origin_x_m' | 'origin_y_m' | 'resolution_m' | 'rows' | 'cols'>;

/** Centre of cell (row, col); row 0 = south, col 0 = west. */
export function cellCenter(meta: GridMeta, row: number, col: number): { x: number; y: number } {
  return {
    x: meta.origin_x_m + (col + 0.5) * meta.resolution_m,
    y: meta.origin_y_m + (row + 0.5) * meta.resolution_m,
  };
}

/** Cell containing (x, y), or null when outside the grid. */
export function cellAt(meta: GridMeta, x: number, y: number): { row: number; col: number; index: number } | null {
  const col = Math.floor((x - meta.origin_x_m) / meta.resolution_m);
  const row = Math.floor((y - meta.origin_y_m) / meta.resolution_m);
  if (row < 0 || col < 0 || row >= meta.rows || col >= meta.cols) return null;
  return { row, col, index: row * meta.cols + col };
}

/**
 * Bilinear height between cell centres. Returns null outside the grid or when
 * any contributing cell is NoData (no height is invented).
 */
export function sampleHeight(meta: GridMeta, grid: ReadonlyArray<number | null>, x: number, y: number): number | null {
  const fc = (x - meta.origin_x_m) / meta.resolution_m - 0.5;
  const fr = (y - meta.origin_y_m) / meta.resolution_m - 0.5;
  const c0 = Math.max(0, Math.min(meta.cols - 1, Math.floor(fc)));
  const r0 = Math.max(0, Math.min(meta.rows - 1, Math.floor(fr)));
  if (fc < -0.5 || fr < -0.5 || fc > meta.cols - 0.5 || fr > meta.rows - 0.5) return null;
  const c1 = Math.min(meta.cols - 1, c0 + 1);
  const r1 = Math.min(meta.rows - 1, r0 + 1);
  const tc = Math.max(0, Math.min(1, fc - c0));
  const tr = Math.max(0, Math.min(1, fr - r0));
  const h00 = grid[r0 * meta.cols + c0];
  const h01 = grid[r0 * meta.cols + c1];
  const h10 = grid[r1 * meta.cols + c0];
  const h11 = grid[r1 * meta.cols + c1];
  if (h00 == null || h01 == null || h10 == null || h11 == null) return null;
  const south = h00 * (1 - tc) + h01 * tc;
  const north = h10 * (1 - tc) + h11 * tc;
  return south * (1 - tr) + north * tr;
}

/** Yaw (rotation about ENU z) from a quaternion, radians, 0 = facing east. */
export function yawFromQuaternion(q: { x: number; y: number; z: number; w: number }): number {
  return Math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z));
}
