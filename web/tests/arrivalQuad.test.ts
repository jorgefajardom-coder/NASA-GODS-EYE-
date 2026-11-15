import { describe, expect, it } from 'vitest';
import { applyMatrix3d, coverQuad, lerpQuad, quadMatrix3d, type Quad } from '../src/lib/arrivalQuad';

describe('zone arrival geometry', () => {
  it('covers the screen with no empty band (no black borders)', () => {
    const [[x0, y0], , [x1, y1]] = coverQuad(340, 760, 1600, 900); // portrait image, landscape screen
    expect(x0).toBeLessThanOrEqual(0);
    expect(y0).toBeLessThanOrEqual(0);
    expect(x1).toBeGreaterThanOrEqual(1600);
    expect(y1).toBeGreaterThanOrEqual(900);
    expect((x1 - x0) / (y1 - y0)).toBeCloseTo(340 / 760); // aspect kept
  });

  it('maps the image corners onto a perspective quad', () => {
    const q: Quad = [[420, 310], [880, 290], [1150, 700], [260, 760]];
    const css = quadMatrix3d(340, 760, q);
    const corners: [number, number][] = [[0, 0], [340, 0], [340, 760], [0, 760]];
    corners.forEach(([px, py], n) => {
      const [x, y] = applyMatrix3d(css, px, py);
      expect(x).toBeCloseTo(q[n][0], 4);
      expect(y).toBeCloseTo(q[n][1], 4);
    });
  });

  it('maps a rectangle affinely', () => {
    const css = quadMatrix3d(100, 200, coverQuad(100, 200, 100, 200));
    expect(applyMatrix3d(css, 50, 100)).toEqual([50, 100]);
  });

  it('interpolates between quads', () => {
    const a: Quad = [[0, 0], [10, 0], [10, 10], [0, 10]];
    const b: Quad = [[10, 10], [20, 10], [20, 20], [10, 20]];
    expect(lerpQuad(a, b, 0.5)[0]).toEqual([5, 5]);
  });
});
