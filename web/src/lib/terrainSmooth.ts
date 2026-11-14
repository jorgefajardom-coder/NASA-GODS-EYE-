/**
 * Smooth display of a height grid between its cell centres.
 *
 * The source terrain has one value per cell (20 m for the CTX crop). Drawing it with one
 * vertex per cell gives a faceted surface. These helpers interpolate between cell centres
 * (Catmull-Rom bicubic) so shading is smooth. Interpolation adds no information: the value
 * at every cell centre is exactly the source value, and results never leave the range of the
 * four nearest cells, so no bumps or hollows are invented.
 */

type Grid = ReadonlyArray<number | null>;

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

function catmullRom(p0: number, p1: number, p2: number, p3: number, t: number): number {
  return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t);
}

/**
 * Height at fractional cell-centre coordinates (`fc` along columns, `fr` along rows, both in
 * cell units where integer values are cell centres). Returns null when any of the four
 * surrounding cells is NoData, so no height is invented next to missing data.
 */
export function smoothHeight(grid: Grid, rows: number, cols: number, fc: number, fr: number): number | null {
  if (fc < 0 || fr < 0 || fc > cols - 1 || fr > rows - 1) return null;
  const c1 = Math.min(cols - 1, Math.floor(fc));
  const r1 = Math.min(rows - 1, Math.floor(fr));
  const t = fc - c1;
  const u = fr - r1;
  const at = (r: number, c: number) => grid[clamp(r, 0, rows - 1) * cols + clamp(c, 0, cols - 1)];

  const a = at(r1, c1);
  const b = at(r1, c1 + 1);
  const d = at(r1 + 1, c1);
  const e = at(r1 + 1, c1 + 1);
  if (a == null || b == null || d == null || e == null) return null;

  // Bilinear on the four nearest cells: fallback and range limit.
  const bilinear = (a * (1 - t) + b * t) * (1 - u) + (d * (1 - t) + e * t) * u;
  const lo = Math.min(a, b, d, e);
  const hi = Math.max(a, b, d, e);

  const rowsV: number[] = [];
  for (let dr = -1; dr <= 2; dr++) {
    const p = [-1, 0, 1, 2].map((dc) => at(r1 + dr, c1 + dc));
    if (p.some((v) => v == null)) return bilinear; // a neighbour is NoData: stay with bilinear
    rowsV.push(catmullRom(p[0]!, p[1]!, p[2]!, p[3]!, t));
  }
  return clamp(catmullRom(rowsV[0], rowsV[1], rowsV[2], rowsV[3], u), lo, hi);
}

/** Height at a point in the local ENU frame, or null outside the grid or next to NoData. */
export function smoothHeightAt(
  meta: { origin_x_m: number; origin_y_m: number; resolution_m: number; rows: number; cols: number },
  grid: Grid,
  x: number,
  y: number,
): number | null {
  const fc = (x - meta.origin_x_m) / meta.resolution_m - 0.5;
  const fr = (y - meta.origin_y_m) / meta.resolution_m - 0.5;
  return smoothHeight(grid, meta.rows, meta.cols, fc, fr);
}

/**
 * Subdivides every cell interval by `factor`. The result has (rows - 1) * factor + 1 rows and
 * (cols - 1) * factor + 1 columns; every factor-th sample is exactly a source cell centre.
 */
export function upsampleGrid(grid: Grid, rows: number, cols: number, factor: number): { data: (number | null)[]; rows: number; cols: number } {
  const R = (rows - 1) * factor + 1;
  const C = (cols - 1) * factor + 1;
  const data: (number | null)[] = new Array(R * C);
  for (let r = 0; r < R; r++) {
    for (let c = 0; c < C; c++) data[r * C + c] = smoothHeight(grid, rows, cols, c / factor, r / factor);
  }
  return { data, rows: R, cols: C };
}

/** Plain bilinear sample for the uncertainty layer; a missing value counts as 0 (no uncertainty drawn). */
export function bilinear(grid: ReadonlyArray<number | null>, rows: number, cols: number, fc: number, fr: number): number {
  const g = (i: number) => grid[i] ?? 0;
  const c0 = clamp(Math.floor(fc), 0, cols - 1);
  const r0 = clamp(Math.floor(fr), 0, rows - 1);
  const c1 = Math.min(cols - 1, c0 + 1);
  const r1 = Math.min(rows - 1, r0 + 1);
  const t = clamp(fc - c0, 0, 1);
  const u = clamp(fr - r0, 0, 1);
  return (g(r0 * cols + c0) * (1 - t) + g(r0 * cols + c1) * t) * (1 - u) + (g(r1 * cols + c0) * (1 - t) + g(r1 * cols + c1) * t) * u;
}
