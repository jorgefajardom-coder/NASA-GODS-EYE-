import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import { GROWTH_BLOCK_SHARE, growthPlanes, growthRadius, setGrowthRadius } from '../src/components/TerrainGrowth';

const kept = (planes: THREE.Plane[], x: number, z: number) => planes.every((p) => p.distanceToPoint(new THREE.Vector3(x, 0, z)) >= 0);

describe('terrain growth front', () => {
  it('hides everything before the start, then grows from the centre to the full radius', () => {
    expect(growthRadius(0, 1500)).toBeLessThan(0);
    expect(growthRadius(1e-6, 1500)).toBeGreaterThanOrEqual(0);
    expect(growthRadius(1, 1500)).toBeCloseTo(1500, 6);
    let prev = -Infinity;
    for (let p = 0; p <= 1.0001; p += 0.001) {
      const r = growthRadius(p, 1500);
      expect(r).toBeGreaterThanOrEqual(prev - 1e-9);
      prev = r;
    }
  });

  it('opens the main block first, then the wider surroundings, without a jump', () => {
    expect(growthRadius(GROWTH_BLOCK_SHARE, 14000, 1450)).toBeCloseTo(1450, 6);
    expect(growthRadius(GROWTH_BLOCK_SHARE + 1e-6, 14000, 1450)).toBeCloseTo(1450, 0);
    expect(growthRadius(1, 14000, 1450)).toBeCloseTo(14000, 6);
    let prev = -Infinity;
    for (let p = 0.001; p <= 1; p += 0.001) {
      const r = growthRadius(p, 14000, 1450);
      expect(r).toBeGreaterThanOrEqual(prev - 1e-9);
      prev = r;
    }
  });

  it('keeps a disc around the centre and clips what lies beyond the front', () => {
    const cx = 500;
    const cz = -700;
    const planes = growthPlanes(cx, cz);
    // Not started: even the centre is hidden.
    expect(kept(planes, cx, cz)).toBe(false);
    setGrowthRadius(planes, cx, cz, 100);
    expect(kept(planes, cx, cz)).toBe(true);
    for (let a = 0; a < Math.PI * 2; a += 0.3) {
      expect(kept(planes, cx + 95 * Math.cos(a), cz + 95 * Math.sin(a))).toBe(true);
      expect(kept(planes, cx + 110 * Math.cos(a), cz + 110 * Math.sin(a))).toBe(false);
    }
  });
});
