import { describe, expect, it } from 'vitest';
import { bandOf, hillshade, tacticalBase, MAP_BANDS } from '../src/lib/tacticalMap';
import type { RasterSet } from '../src/types/replay';

describe('tactical map base', () => {
  it('splits the height range into bands, clamping the ends', () => {
    expect(bandOf(0, 0, 90)).toBe(0);
    expect(bandOf(89.9, 0, 90)).toBe(MAP_BANDS - 1);
    expect(bandOf(500, 0, 90)).toBe(MAP_BANDS - 1);
    expect(bandOf(-5, 0, 90)).toBe(0);
  });

  it('shades a flat grid uniformly', () => {
    const s = hillshade(new Array(16).fill(10), 4, 4, 20);
    expect(new Set(Array.from(s, (v) => v.toFixed(6))).size).toBe(1);
  });

  it('draws observed cells brighter and flips rows so north is up', () => {
    const rows = 4, cols = 4;
    const ramp = Array.from({ length: rows * cols }, (_, i) => Math.floor(i / cols) * 10); // rises to the north
    const r: RasterSet = { run_id: 't', rows, cols, prior: ramp, versions: { 1: { belief: ramp, sigma: ramp.map(() => null), observed: [5] } } };
    const b = tacticalBase(r, 1);
    expect(b.observed).toBe(1);
    expect(b.total).toBe(16);
    const px = (row: number, col: number) => b.pixels[((rows - 1 - row) * cols + col) * 4 + 2];
    expect(px(1, 1)).toBeGreaterThan(px(1, 2)); // cell 5 (row 1, col 1) observed
    expect(b.pixels[2]).toBeGreaterThan(b.pixels[(3 * cols) * 4 + 2]); // top canvas row = highest (north) band
  });
});
