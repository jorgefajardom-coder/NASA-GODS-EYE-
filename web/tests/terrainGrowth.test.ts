import { describe, expect, it } from 'vitest';
import { GROWTH_LAYERS, growthHeight } from '../src/components/TerrainGrowth';

describe('terrain growth front', () => {
  it('starts at the base, ends at the top and never goes down', () => {
    expect(growthHeight(0, -100, 100)).toBe(-100);
    expect(growthHeight(1, -100, 100)).toBeCloseTo(100, 9);
    let prev = -Infinity;
    for (let p = 0; p <= 1.0001; p += 0.001) {
      const h = growthHeight(p, -100, 100);
      expect(h).toBeGreaterThanOrEqual(prev - 1e-9);
      prev = h;
    }
  });

  it('builds in layers: it holds at each layer boundary before the next one rises', () => {
    const layer = 200 / GROWTH_LAYERS;
    // Late in a layer's time slot the front is already at that layer's top and holds there.
    const p = (3 + 0.9) / GROWTH_LAYERS;
    expect(growthHeight(p, -100, 100)).toBeCloseTo(-100 + 4 * layer, 6);
    expect(growthHeight(p + 0.05 / GROWTH_LAYERS, -100, 100)).toBeCloseTo(-100 + 4 * layer, 6);
  });
});
