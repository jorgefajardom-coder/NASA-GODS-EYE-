import { describe, expect, it } from 'vitest';
import { swayOffset, swayStepHz } from '../src/components/FirstPersonCamera';

describe('first-person sway (display only)', () => {
  it('keeps the astronaut and rover cameras still when they stand still', () => {
    for (const phase of [0, 1, 2.5]) {
      for (const kind of ['HUMAN', 'ROVER'] as const) {
        const s = swayOffset(kind, 0, phase, phase * 3);
        expect(Math.abs(s.up) + Math.abs(s.side) + Math.abs(s.roll)).toBe(0);
      }
    }
    expect(swayStepHz(0)).toBe(0);
  });

  it('stays small: a few centimetres and under half a degree', () => {
    for (const kind of ['HUMAN', 'ROVER', 'DRONE'] as const) {
      for (let p = 0; p < 20; p += 0.37) {
        const s = swayOffset(kind, 2, p, p);
        expect(Math.abs(s.up)).toBeLessThanOrEqual(0.05);
        expect(Math.abs(s.side)).toBeLessThanOrEqual(0.05);
        expect(Math.abs(s.roll)).toBeLessThanOrEqual(0.0087);
      }
    }
  });

  it('steps about once per second at a 1 m/s walk, never frantically', () => {
    expect(swayStepHz(1)).toBeCloseTo(1.05, 2);
    expect(swayStepHz(50)).toBeLessThanOrEqual(1.6);
  });
});
