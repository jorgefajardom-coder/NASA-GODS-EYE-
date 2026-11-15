import { describe, expect, it } from 'vitest';
import { GROWTH_FLAT, reliefShare, reliefTransform, zoneDelay, zoneGlow, zoneShare, ZONE_RISE_SHARE } from '../src/components/TerrainGrowth';

describe('terrain relief growth', () => {
  it('starts as a flat sheet and ends at the true relief', () => {
    expect(reliefShare(0)).toBeCloseTo(GROWTH_FLAT, 9);
    expect(reliefShare(1)).toBeCloseTo(1, 9);
    expect(reliefShare(-1)).toBeCloseTo(GROWTH_FLAT, 9);
    expect(reliefShare(2)).toBeCloseTo(1, 9);
  });

  it('rises continuously: never holds, never jumps, never overshoots', () => {
    let prev = reliefShare(0);
    for (let p = 0.01; p <= 1.0001; p += 0.01) {
      const k = reliefShare(p);
      expect(k).toBeGreaterThanOrEqual(prev - 1e-12);
      expect(k).toBeLessThanOrEqual(1 + 1e-12);
      expect(k - prev).toBeLessThan(0.0188 + 1e-9); // max slope of smootherstep is 1.875
      if (p > 0.05 && p < 0.95) expect(k - prev).toBeGreaterThan(0);
      prev = k;
    }
  });

  it('scales heights about the lowest ground, which stays in place', () => {
    const pivot = -60;
    for (const k of [GROWTH_FLAT, 0.4, 1]) {
      const { scaleY, offsetY } = reliefTransform(k, pivot);
      expect(pivot * scaleY + offsetY).toBeCloseTo(pivot, 9); // lowest ground does not move
      const peak = 40;
      expect(peak * scaleY + offsetY).toBeCloseTo(pivot + (peak - pivot) * k, 9);
    }
    const end = reliefTransform(1, pivot);
    expect(end.scaleY).toBe(1);
    expect(end.offsetY).toBeCloseTo(0, 12);
  });
});

describe('terrain growth by zones', () => {
  it('raises low ground before ridges, and every zone has finished at the end', () => {
    expect(zoneDelay(0, 0, 0)).toBeLessThan(zoneDelay(1, 0, 0));
    for (const d of [0, 0.3, 0.7, 1]) {
      expect(zoneShare(0, d)).toBeCloseTo(GROWTH_FLAT, 9);
      expect(zoneShare(1, d)).toBeCloseTo(1, 9);
      expect(zoneGlow(1, d)).toBe(0);
    }
    // Midway, the low zones stand higher than the ridges.
    expect(zoneShare(0.45, zoneDelay(0, 10, 10))).toBeGreaterThan(zoneShare(0.45, zoneDelay(1, 10, 10)));
  });

  it('rises smoothly per zone and lights only the zones that are rising', () => {
    const d = 0.5;
    let prev = zoneShare(0, d);
    for (let p = 0.005; p <= 1; p += 0.005) {
      const k = zoneShare(p, d);
      expect(k).toBeGreaterThanOrEqual(prev - 1e-12);
      prev = k;
    }
    expect(zoneGlow(0, d)).toBe(0);
    const mid = d * (1 - ZONE_RISE_SHARE) + ZONE_RISE_SHARE / 2;
    expect(zoneGlow(mid, d)).toBeCloseTo(1, 6);
  });
});
