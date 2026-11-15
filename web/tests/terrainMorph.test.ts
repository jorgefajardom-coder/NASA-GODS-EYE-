import { describe, expect, it } from 'vitest';
import { morphEase, morphHeights } from '../src/components/TerrainView';

describe('terrain height morph', () => {
  it('eases from 0 to 1 with no jump at either end', () => {
    expect(morphEase(0)).toBe(0);
    expect(morphEase(1)).toBe(1);
    expect(morphEase(-1)).toBe(0);
    expect(morphEase(2)).toBe(1);
    // Starts and ends at rest: tiny steps near the ends move almost nothing.
    expect(morphEase(0.01)).toBeLessThan(1e-4);
    expect(1 - morphEase(0.99)).toBeLessThan(1e-4);
    let prev = 0;
    for (let p = 0; p <= 1; p += 0.01) {
      const k = morphEase(p);
      expect(k).toBeGreaterThanOrEqual(prev - 1e-12);
      // No step larger than a smooth curve allows (max slope of smootherstep is 1.875).
      expect(k - prev).toBeLessThan(0.0188 + 1e-9);
      prev = k;
    }
  });

  it('moves only the heights, from the shown surface to the new one', () => {
    const from = new Float32Array([1, 10, 2, 3, -5, 4]);
    const to = new Float32Array([1, 20, 2, 3, 5, 4]);
    const out = new Float32Array(6);
    morphHeights(from, to, 0, out);
    expect(Array.from(out)).toEqual([0, 10, 0, 0, -5, 0]);
    morphHeights(from, to, 1, out);
    expect(out[1]).toBeCloseTo(20);
    expect(out[4]).toBeCloseTo(5);
    morphHeights(from, to, 0.5, out);
    expect(out[1]).toBeCloseTo(15);
    expect(out[4]).toBeCloseTo(0);
  });
});
