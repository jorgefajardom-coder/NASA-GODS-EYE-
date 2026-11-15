import type { TerrainMeta } from '../types/icd';
import { upsampleGrid } from './terrainSmooth';

type GridMeta = Pick<TerrainMeta, 'rows' | 'cols' | 'resolution_m' | 'origin_x_m' | 'origin_y_m'>;
export const MESH_SUBDIVISION = 3;
const MESH_VERTEX_BUDGET = 700_000;
export const meshSubdivision = (meta: Pick<GridMeta, 'rows' | 'cols'>): number =>
  Math.max(1, Math.min(MESH_SUBDIVISION, Math.floor(Math.sqrt(MESH_VERTEX_BUDGET / (meta.rows * meta.cols)))));

/** Display geometry only. positions is the renderer's live Float32 buffer:
 * sampling it also follows growth/morph, without modifying any received pose.
 */
export interface TerrainSurface {
  meta: GridMeta;
  heights: ReadonlyArray<number | null>;
  subdivision: number;
  fine: ReturnType<typeof upsampleGrid>;
  positions: Float32Array;
  /** Target geometry, kept separate while positions is animated. */
  restHeights: Float32Array;
  revision: number;
  indices: Uint32Array;
  quads: Uint8Array;
}

export function createTerrainSurface(meta: GridMeta, heights: ReadonlyArray<number | null>, subdivision = meshSubdivision(meta)): TerrainSurface {
  const fine = upsampleGrid(heights, meta.rows, meta.cols, subdivision);
  const positions = new Float32Array(fine.rows * fine.cols * 3);
  const restHeights = new Float32Array(fine.rows * fine.cols);
  const step = meta.resolution_m / subdivision;
  for (let r = 0; r < fine.rows; r++) for (let c = 0; c < fine.cols; c++) {
    const i = r * fine.cols + c;
    positions[i * 3] = meta.origin_x_m + meta.resolution_m / 2 + c * step;
    positions[i * 3 + 1] = fine.data[i] ?? 0;
    restHeights[i] = positions[i * 3 + 1];
    positions[i * 3 + 2] = -(meta.origin_y_m + meta.resolution_m / 2 + r * step);
  }
  const indices: number[] = [];
  const quads = new Uint8Array(Math.max(0, (fine.rows - 1) * (fine.cols - 1)));
  for (let r = 0; r < fine.rows - 1; r++) for (let c = 0; c < fine.cols - 1; c++) {
    const a = r * fine.cols + c, b = a + 1, d = a + fine.cols, e = d + 1;
    if ([a, b, d, e].some((i) => fine.data[i] == null)) continue;
    quads[r * (fine.cols - 1) + c] = 1;
    indices.push(a, b, d, b, e, d);
  }
  return { meta, heights, subdivision, fine, positions, restHeights, revision: 0, indices: Uint32Array.from(indices), quads };
}

/** ENU XY -> height of the actual drawn triangle. NoData holes stay absent.
 * Exaggeration is optional and applied exactly once to the sampled up axis.
 */
export function terrainSurfaceHeight(surface: TerrainSurface, x: number, north: number, exaggeration = 1): number | null {
  const { positions: p, fine: { rows, cols }, meta, subdivision: f, quads } = surface;
  if (!Number.isFinite(x) || !Number.isFinite(north) || rows < 2 || cols < 2) return null;
  if (x < p[0] || x > p[(cols - 1) * 3] || north < -p[2] || north > -p[(rows - 1) * cols * 3 + 2]) return null;
  let c = Math.max(0, Math.min(cols - 2, Math.floor(((x - meta.origin_x_m) / meta.resolution_m - .5) * f)));
  let r = Math.max(0, Math.min(rows - 2, Math.floor(((north - meta.origin_y_m) / meta.resolution_m - .5) * f)));
  // Actual Float32 XY can straddle the ideal fractional-cell boundary.
  while (c > 0 && x < p[c * 3]) c--;
  while (c < cols - 2 && x > p[(c + 1) * 3]) c++;
  while (r > 0 && north < -p[r * cols * 3 + 2]) r--;
  while (r < rows - 2 && north > -p[(r + 1) * cols * 3 + 2]) r++;
  if (!quads[r * (cols - 1) + c]) {
    // On a hole boundary a neighbouring drawn quad can still own the point.
    // Test its actual Float32 bounds; never extend the surface into the hole.
    let found = false;
    for (const rr of [r, r - 1, r + 1]) {
      for (const cc of [c, c - 1, c + 1]) {
        if (rr < 0 || cc < 0 || rr >= rows - 1 || cc >= cols - 1 || !quads[rr * (cols - 1) + cc]) continue;
        const a = rr * cols + cc;
        if (x >= p[a * 3] && x <= p[(a + 1) * 3]
          && north >= -p[a * 3 + 2] && north <= -p[(a + cols) * 3 + 2]) {
          r = rr; c = cc; found = true; break;
        }
      }
      if (found) break;
    }
    if (!found) return null;
  }
  const a = r * cols + c, b = a + 1, d = a + cols, e = d + 1;
  const tx = (x - p[a * 3]) / (p[b * 3] - p[a * 3]);
  const ty = (north + p[a * 3 + 2]) / (p[a * 3 + 2] - p[d * 3 + 2]);
  const A = p[a * 3 + 1], B = p[b * 3 + 1], D = p[d * 3 + 1], E = p[e * 3 + 1];
  return (tx + ty <= 1 ? A + (B - A) * tx + (D - A) * ty
    : E + (D - E) * (1 - tx) + (B - E) * (1 - ty)) * exaggeration;
}
