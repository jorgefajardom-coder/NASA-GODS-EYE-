import { describe, expect, it } from 'vitest';
import { ARM_MOVE_S, MAST_RATE_DEG_S, createRig, homeRig, nudgeMast, requestShot, rigSettled, shotReady, stepAxis, stepRig, zoomBy } from '../src/lib/roverRig';

const run = (s: ReturnType<typeof createRig>, seconds: number, stationary = true) => {
  for (let t = 0; t < seconds; t += 1 / 60) stepRig(s, 1 / 60, stationary);
};

describe('rover camera rig (display only)', () => {
  it('turns the mast head no faster than its rate limit and stops on the target without overshoot', () => {
    let p = { pos: 0, rate: 0 };
    let maxRate = 0;
    let maxPos = 0;
    for (let i = 0; i < 600; i++) {
      p = stepAxis(p.pos, p.rate, 90, MAST_RATE_DEG_S, 40, 1 / 60);
      maxRate = Math.max(maxRate, Math.abs(p.rate));
      maxPos = Math.max(maxPos, p.pos);
    }
    expect(maxRate).toBeLessThanOrEqual(MAST_RATE_DEG_S + 1e-9);
    expect(maxPos).toBeLessThanOrEqual(90 + 1e-6);
    expect(p.pos).toBeCloseTo(90, 3);
  });

  it('takes the short way round in azimuth', () => {
    // From 170 to -170 the short way is +20 deg through 180, not -340 deg.
    const p = stepAxis(170, 0, -170, 20, 40, 0.5, true);
    expect(p.rate).toBeGreaterThan(0);
    expect(p.pos > 170 || p.pos < -170).toBe(true);
  });

  it('reports a shot ready only once the head has arrived', () => {
    const s = createRig();
    const token = requestShot(s, { camera: 'mastcamz', side: 'right', azDeg: 120, elDeg: -30, focalMm: 110 });
    run(s, 1);
    expect(shotReady(s, token)).toBe(false);
    run(s, 10);
    expect(shotReady(s, token)).toBe(true);
    expect(s.view).toBe('mastcamz');
    expect(s.focalMm).toBeCloseTo(110, 1);
    expect(rigSettled(s)).toBe(true);
  });

  it('shows WATSON only after the arm is out, and stows it when the rover drives', () => {
    const s = createRig();
    requestShot(s, { camera: 'watson' });
    run(s, ARM_MOVE_S / 2);
    expect(s.view).toBe('navcam');
    run(s, ARM_MOVE_S);
    expect(s.view).toBe('watson');
    run(s, 0.2, false);
    expect(s.armTarget).toBe(0);
    expect(s.view).toBe('navcam');
  });

  it('keeps fixed lenses and body cameras still: no zoom on Navcam, no aiming of a Hazcam', () => {
    const s = createRig();
    zoomBy(s, 3);
    expect(s.targetFocalMm).toBe(26);
    requestShot(s, { camera: 'hazcam_front' });
    nudgeMast(s, 40, 10);
    expect(s.targetAz).toBe(0);
    homeRig(s);
    run(s, 8);
    expect(s.view).toBe('navcam');
    expect(s.el).toBeCloseTo(-10, 2);
  });
});
