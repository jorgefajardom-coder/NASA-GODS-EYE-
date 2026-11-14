import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { slopeDegrees, slopeShares } from '../src/lib/slope';

const plane = (rows: number, cols: number, res: number, gx: number, gy: number) =>
  Array.from({ length: rows * cols }, (_, i) => gx * (i % cols) * res + gy * Math.floor(i / cols) * res);

describe('slope from a DTM (Horn 3x3)', () => {
  it('is zero on flat ground', () => {
    const s = slopeDegrees(new Array(25).fill(-2500), 5, 5, 20);
    expect(s[12]).toBe(0);
  });

  it('recovers the exact angle of an inclined plane in any direction', () => {
    const rad = (deg: number) => (deg * Math.PI) / 180;
    for (const [gx, gy] of [[Math.tan(rad(10)), 0], [0, -Math.tan(rad(25))], [0.3, 0.4]]) {
      const s = slopeDegrees(plane(5, 5, 20, gx, gy), 5, 5, 20);
      expect(s[12]!).toBeCloseTo((Math.atan(Math.hypot(gx, gy)) * 180) / Math.PI, 9);
    }
  });

  it('never invents values at the border or next to NoData', () => {
    const g: (number | null)[] = plane(5, 5, 20, 0.1, 0);
    g[0] = null;
    const s = slopeDegrees(g, 5, 5, 20);
    for (let c = 0; c < 5; c++) expect(s[c]).toBeNull(); // south border
    expect(s[6]).toBeNull(); // neighbour of the NoData cell
    expect(s[12]).not.toBeNull();
  });

  it('uses the real cell spacing', () => {
    const g = plane(3, 3, 1, 1, 0); // 1 m rise per cell
    expect(slopeDegrees(g, 3, 3, 1)[4]).toBeCloseTo(45, 9);
    expect(slopeDegrees(g, 3, 3, 20)[4]).toBeCloseTo((Math.atan(1 / 20) * 180) / Math.PI, 9);
  });

  it('gives plausible slopes on the demo CTX DTM', () => {
    const file = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo', 'rasters.json');
    const r = JSON.parse(readFileSync(file, 'utf8')) as { rows: number; cols: number; prior: (number | null)[] };
    const m = JSON.parse(readFileSync(join(dirname(file), 'manifest.json'), 'utf8')) as { terrain_meta: { resolution_m: number } };
    const s = slopeDegrees(r.prior, r.rows, r.cols, m.terrain_meta.resolution_m);
    const { valid, atOrAbove } = slopeShares(s, [0, 90]);
    expect(valid).toBe((r.rows - 2) * (r.cols - 2));
    expect(atOrAbove[0]).toBe(1);
    expect(atOrAbove[1]).toBe(0);
  });
});
