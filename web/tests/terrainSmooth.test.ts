import { describe, expect, it } from 'vitest';
import { bilinear, smoothHeight, smoothHeightAt, upsampleGrid } from '../src/lib/terrainSmooth';

const rows = 6;
const cols = 7;
const bumpy = Array.from({ length: rows * cols }, (_, i) => Math.sin(i * 1.7) * 9 + (i % 5) * 2);

describe('smooth terrain display', () => {
  it('returns exactly the source value at every cell centre', () => {
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) expect(smoothHeight(bumpy, rows, cols, c, r)).toBe(bumpy[r * cols + c]);
  });

  it('reproduces a plane exactly between cells (adds no bumps)', () => {
    const plane = Array.from({ length: rows * cols }, (_, i) => 3 + 0.5 * (i % cols) - 0.25 * Math.floor(i / cols));
    // Interior points only: at the border the missing outer neighbour is a replicated edge cell.
    for (const [fc, fr] of [[1.3, 1.7], [3.5, 2.25], [2.2, 3.4]]) {
      expect(smoothHeight(plane, rows, cols, fc, fr)).toBeCloseTo(3 + 0.5 * fc - 0.25 * fr, 9);
    }
  });

  it('never overshoots the four nearest cells, even at a sharp step', () => {
    const step = Array.from({ length: rows * cols }, (_, i) => ((i % cols) < 3 ? 0 : 40));
    for (let fc = 0; fc <= cols - 1; fc += 0.1) {
      const h = smoothHeight(step, rows, cols, fc, 2.4)!;
      expect(h).toBeGreaterThanOrEqual(0);
      expect(h).toBeLessThanOrEqual(40);
    }
  });

  it('returns null next to NoData and outside the grid, and falls back to bilinear for far neighbours', () => {
    const g: (number | null)[] = [...bumpy];
    g[2 * cols + 3] = null;
    expect(smoothHeight(g, rows, cols, 3.4, 2.4)).toBeNull(); // inner corner missing
    expect(smoothHeight(g, rows, cols, -0.1, 1)).toBeNull();
    const far: (number | null)[] = [...bumpy];
    far[2 * cols + 0] = null; // an outer neighbour of the cell at column 1
    const h = smoothHeight(far, rows, cols, 1.5, 2.5)!;
    const a = bumpy[2 * cols + 1], b = bumpy[2 * cols + 2], d = bumpy[3 * cols + 1], e = bumpy[3 * cols + 2];
    expect(h).toBeCloseTo((a + b) / 4 + (d + e) / 4, 9);
  });

  it('subdivides keeping every source cell centre', () => {
    const f = 3;
    const up = upsampleGrid(bumpy, rows, cols, f);
    expect(up.rows).toBe((rows - 1) * f + 1);
    expect(up.cols).toBe((cols - 1) * f + 1);
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) expect(up.data[r * f * up.cols + c * f]).toBe(bumpy[r * cols + c]);
  });

  it('samples in the ENU frame at the same cell-centre convention', () => {
    const meta = { origin_x_m: -100, origin_y_m: -60, resolution_m: 20, rows, cols };
    expect(smoothHeightAt(meta, bumpy, -90, -50)).toBe(bumpy[0]); // centre of cell (0,0)
    expect(smoothHeightAt(meta, bumpy, -300, 0)).toBeNull();
  });

  it('bilinear helper matches its corners', () => {
    const g = [1, 2, 3, 4];
    expect(bilinear(g, 2, 2, 0, 0)).toBe(1);
    expect(bilinear(g, 2, 2, 1, 1)).toBe(4);
    expect(bilinear(g, 2, 2, 0.5, 0.5)).toBe(2.5);
  });
});
