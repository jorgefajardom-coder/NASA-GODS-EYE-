/**
 * Terrain slope from an elevation grid (row-major, row 0 = south, `null` = NoData).
 *
 * Horn (1981) 3x3 finite differences, the method used by GDAL `gdaldem slope`:
 *   dz/dx = ((c + 2f + i) - (a + 2d + g)) / (8 * res)
 *   dz/dy = ((g + 2h + i) - (a + 2b + c)) / (8 * res)   (rows increase northwards)
 * with the neighbourhood
 *   g h i   (north)
 *   d e f
 *   a b c   (south)
 * Slope = atan(sqrt(dzdx^2 + dzdy^2)), in degrees.
 *
 * Only measured heights are used: a cell is null when it, or any of its eight neighbours, is
 * NoData or outside the grid (no padding, no extrapolation). On a 20 m DTM each value
 * averages the terrain over a 60 m window, so steps shorter than that are smoothed out:
 * read the result as a lower bound for local slope, not as a hazard map.
 */
export function slopeDegrees(grid: ReadonlyArray<number | null>, rows: number, cols: number, resolutionM: number): (number | null)[] {
  if (grid.length !== rows * cols) throw new Error('grid size does not match rows x cols');
  if (!(resolutionM > 0)) throw new Error('resolution must be positive');
  const out = new Array<number | null>(rows * cols).fill(null);
  const at = (r: number, c: number) => grid[r * cols + c];
  for (let r = 1; r < rows - 1; r++) {
    for (let c = 1; c < cols - 1; c++) {
      const a = at(r - 1, c - 1), b = at(r - 1, c), cc = at(r - 1, c + 1);
      const d = at(r, c - 1), e = at(r, c), f = at(r, c + 1);
      const g = at(r + 1, c - 1), h = at(r + 1, c), i = at(r + 1, c + 1);
      if (a == null || b == null || cc == null || d == null || e == null || f == null || g == null || h == null || i == null) continue;
      const dzdx = (cc + 2 * f + i - (a + 2 * d + g)) / (8 * resolutionM);
      const dzdy = (g + 2 * h + i - (a + 2 * b + cc)) / (8 * resolutionM);
      out[r * cols + c] = (Math.atan(Math.hypot(dzdx, dzdy)) * 180) / Math.PI;
    }
  }
  return out;
}

/** Share of valid cells at or above each threshold (degrees), for the legend. */
export function slopeShares(slopes: ReadonlyArray<number | null>, thresholds: readonly number[]): { valid: number; atOrAbove: number[] } {
  const valid = slopes.filter((s): s is number => s != null);
  return {
    valid: valid.length,
    atOrAbove: thresholds.map((t) => (valid.length ? valid.filter((s) => s >= t).length / valid.length : 0)),
  };
}
