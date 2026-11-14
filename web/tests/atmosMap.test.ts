import { describe, expect, it } from 'vitest';
import { pressureField, SCALE_HEIGHT_M } from '../src/lib/atmosMap';

describe('estimated pressure map', () => {
  it('gives the reference pressure at the mean height and less on higher ground', () => {
    const f = pressureField([0, 100, null, 200], 780)!;
    expect(f.refHeightM).toBeCloseTo(100, 9);
    expect(f.values[1]).toBeCloseTo(780, 9);
    expect(f.values[2]).toBeNull();
    expect(f.values[3]!).toBeLessThan(780);
    expect(f.values[0]!).toBeGreaterThan(780);
    expect(f.values[3]!).toBeCloseTo(780 * Math.exp(-100 / SCALE_HEIGHT_M), 9);
    expect(f.min).toBe(f.values[3]);
    expect(f.max).toBe(f.values[0]);
  });

  it('refuses to estimate without heights or a positive reference', () => {
    expect(pressureField([null, null], 780)).toBeNull();
    expect(pressureField([1, 2], 0)).toBeNull();
  });
});
