import { describe, expect, it } from 'vitest';
import { angleDelta, CAMERA_SMOOTHING, dampAngle, dampFactor } from '../src/lib/smoothing';

describe('display smoothing', () => {
  it('is frame-rate independent: two half steps equal one full step', () => {
    const tau = 0.2;
    const one = dampFactor(1 / 30, tau);
    const half = dampFactor(1 / 60, tau);
    expect(1 - (1 - half) * (1 - half)).toBeCloseTo(one, 10);
  });

  it('jumps straight to the target when smoothing is off', () => {
    expect(dampFactor(1 / 60, 0)).toBe(1);
  });

  it('never overshoots', () => {
    for (const dt of [0, 0.001, 0.016, 0.1, 5]) {
      const k = dampFactor(dt, 0.1);
      expect(k).toBeGreaterThanOrEqual(0);
      expect(k).toBeLessThanOrEqual(1);
    }
  });

  it('turns the short way round across +-180 degrees', () => {
    expect(angleDelta(Math.PI - 0.1, -Math.PI + 0.1)).toBeCloseTo(0.2, 10);
    expect(angleDelta(-Math.PI + 0.1, Math.PI - 0.1)).toBeCloseTo(-0.2, 10);
    const a = dampAngle(Math.PI - 0.1, -Math.PI + 0.1, 1, 0.01);
    expect(Math.abs(angleDelta(a, -Math.PI + 0.1))).toBeLessThan(1e-6);
  });

  it('orders the settings from rigid to cinematic', () => {
    expect(CAMERA_SMOOTHING.off.orbitDamping).toBeGreaterThan(CAMERA_SMOOTHING.soft.orbitDamping);
    expect(CAMERA_SMOOTHING.soft.orbitDamping).toBeGreaterThan(CAMERA_SMOOTHING.cinematic.orbitDamping);
  });
});
