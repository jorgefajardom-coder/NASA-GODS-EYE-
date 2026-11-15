import { describe, expect, it } from 'vitest';
import { STOP_ARRIVE_M, isStationary, stopLabel, stopUnderAgent, stopsNear } from '../src/lib/roverStops';
import type { RoverStop } from '../src/types/replay';

const stop = (rmc: string, x: number, y: number, sol = 13): RoverStop => {
  const [site, drive] = rmc.split('_').map(Number);
  return { rmc, site, drive, sol, lat_deg: 18.4, lon_deg: 77.4, x_m: x, y_m: y, z_m: 0 };
};
const stops = [stop('3_0', 0, 0), stop('3_110', 100, 0, 14), stop('3_386', 600, 0, 15)];

describe('rover stops', () => {
  it('lists the stops in range, nearest first', () => {
    expect(stopsNear(stops, 90, 0, 250).map((s) => s.stop.rmc)).toEqual(['3_110', '3_0']);
    expect(stopsNear(stops, 90, 0, 250)[0].distM).toBeCloseTo(10, 6);
  });

  it('is on a stop only when standing still within the arrival distance', () => {
    expect(stopUnderAgent(stops, 5, 0, 'IDLE')?.rmc).toBe('3_0');
    expect(stopUnderAgent(stops, STOP_ARRIVE_M + 1, 0, 'IDLE')).toBeNull();
    expect(stopUnderAgent(stops, 5, 0, 'MOVING')).toBeNull();
    expect(stopUnderAgent(stops, 5, 0, 'RETURNING')).toBeNull();
  });

  it('treats idle, working, halted and observing as stopped', () => {
    for (const m of ['IDLE', 'WORKING', 'HALTED', 'OBSERVING'] as const) expect(isStationary(m)).toBe(true);
    expect(isStationary('MOVING')).toBe(false);
  });

  it('labels a stop by sol and identifier', () => {
    expect(stopLabel(stops[1])).toBe('sol 14 · stop 3_110');
  });
});
