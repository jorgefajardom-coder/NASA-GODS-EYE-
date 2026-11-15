import { describe, expect, it } from 'vitest';
import { ScanStateMachine } from '../src/scanner/ScanStateMachine';
import { classifyPoint, layoutIndicators, spacingAt } from '../src/scanner/ScanIndicators';
import { SCAN_CONFIG } from '../src/scanner/ScanConfig';

const timing = { rangeM: 50, speedMps: 25, cooldownS: 3, persistS: 5, fadeS: 2 };
const o = { x: 0, y: 0, z: 0 };

describe('ScanStateMachine', () => {
  it('is DISABLED until data is available, with the reason', () => {
    const m = new ScanStateMachine(timing);
    m.setAvailable(false, 'Follow the astronaut in first person');
    expect(m.snapshot(0).state).toBe('DISABLED');
    expect(m.snapshot(0).reason).toMatch(/astronaut/);
    expect(m.trigger(0, o)).toBe(false);
  });

  it('goes READY -> SCANNING -> COOLDOWN -> READY on its own clock', () => {
    const m = new ScanStateMachine(timing);
    m.setAvailable(true);
    expect(m.snapshot(0).state).toBe('READY');
    expect(m.trigger(1000, o)).toBe(true);
    const mid = m.snapshot(2000); // 1 s in: front at 25 m of 50
    expect(mid.state).toBe('SCANNING');
    expect(mid.radiusM).toBeCloseTo(25, 6);
    expect(mid.scanProgress).toBeCloseTo(0.5, 6);
    const cool = m.snapshot(4500); // 3.5 s: sweep 2 s done, 1.5 s of 3 s cooldown
    expect(cool.state).toBe('COOLDOWN');
    expect(cool.cooldownLeftS).toBeCloseTo(1.5, 6);
    expect(cool.cooldownProgress).toBeCloseTo(0.5, 6);
    expect(m.snapshot(6000).state).toBe('READY');
  });

  it('refuses a second scan while one runs or recharges (no simultaneous activations)', () => {
    const m = new ScanStateMachine(timing);
    m.setAvailable(true);
    expect(m.trigger(0, o)).toBe(true);
    expect(m.trigger(500, { x: 9, y: 9, z: 9 })).toBe(false);
    expect(m.trigger(4000, o)).toBe(false);
    expect(m.snapshot(500).origin).toEqual(o); // the origin stays where the scan started
    expect(m.snapshot(500).scanId).toBe(1);
  });

  it('keeps effects for persist, then fades them out', () => {
    const m = new ScanStateMachine(timing);
    m.setAvailable(true);
    m.trigger(0, o);
    expect(m.snapshot(6000).effect).toBe(1); // 2 s sweep + 4 s
    expect(m.snapshot(8000).effect).toBeCloseTo(0.5, 6); // halfway through the 2 s fade
    expect(m.snapshot(9500).effect).toBe(0);
  });
});

describe('indicator layout', () => {
  const meta = { origin_x_m: -100, origin_y_m: -100, resolution_m: 20, rows: 10, cols: 10 };
  // Column 5 (x 0..20) steep, column 6 NoData, everything else gentle.
  const slope = Array.from({ length: 100 }, (_, i) => (i % 10 === 5 ? 25 : i % 10 === 6 ? null : 3));

  it('spaces indicators from near to far spacing across the range', () => {
    expect(spacingAt(0, 50, 0.5, 2)).toBe(0.5);
    expect(spacingAt(50, 50, 0.5, 2)).toBe(2);
    expect(spacingAt(25, 50, 0.5, 2)).toBeCloseTo(1.25, 6);
  });

  it('classifies only from the slope raster and NoData of the run', () => {
    expect(classifyPoint(meta, slope, -50, 0)).toBe('traversable');
    expect(classifyPoint(meta, slope, 10, 0)).toBe('hazard');
    expect(classifyPoint(meta, slope, 30, 0)).toBe('unknown');
    expect(classifyPoint(meta, slope, 500, 0)).toBe('unknown'); // outside the grid
  });

  it('stays within range and pool size, nearest first', () => {
    const pts = layoutIndicators(meta, slope, -40, -40, { rangeM: 50, nearM: 0.5, farM: 2, max: SCAN_CONFIG.maxIndicators });
    expect(pts.length).toBeGreaterThan(1000);
    expect(pts.length).toBeLessThanOrEqual(SCAN_CONFIG.maxIndicators);
    expect(Math.max(...pts.map((p) => p.distanceM))).toBeLessThanOrEqual(50);
    for (let i = 1; i < pts.length; i++) expect(pts[i].distanceM).toBeGreaterThanOrEqual(pts[i - 1].distanceM);
    const capped = layoutIndicators(meta, slope, 0, 0, { rangeM: 50, nearM: 0.5, farM: 2, max: 100 });
    expect(capped.length).toBe(100);
  });
});
