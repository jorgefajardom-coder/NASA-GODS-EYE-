import { describe, expect, it } from 'vitest';
import { excursionDoseMsv, zoneEnvironment } from '../src/lib/zoneEnvironment';
import { WORLDS } from '../src/data/worlds';

describe('zone water and radiation context', () => {
  it('covers every zone scene', () => {
    for (const w of WORLDS) if (w.runId) expect(zoneEnvironment(w.runId), w.runId).not.toBeNull();
    expect(zoneEnvironment('mock-vertical-001')).toBeNull();
  });

  it('keeps the measured Gale value and flags extrapolations', () => {
    const gale = zoneEnvironment('gale-demo')!;
    expect(gale.radiation.measuredHere).toBe(true);
    expect(gale.radiation.doseMsvPerDay).toBeCloseTo(0.64); // MSL RAD, Hassler et al. 2014
    expect(zoneEnvironment('demo')!.radiation.measuredHere).toBe(false);
    expect(zoneEnvironment('gusev-demo')!.radiation.withinRange).toBe(false); // below RAD's measured 700-950 Pa
    expect(zoneEnvironment('meridiani-demo')!.radiation.withinRange).toBe(false);
    expect(zoneEnvironment('melas-demo')!.radiation.withinRange).toBe(true);
  });

  it('scales the daily average to an excursion, linearly', () => {
    expect(excursionDoseMsv(0.64, 24)).toBeCloseTo(0.64);
    expect(excursionDoseMsv(0.72, 4)).toBeCloseTo(0.12);
  });
});

describe('astronaut dose at each zone (HUD)', () => {
  it('accumulates the zone rate over the replay time', async () => {
    const { zoneCrewDose } = await import('../src/lib/zoneEnvironment');
    const day = zoneCrewDose('gale-demo', 86400)!;
    expect(day.usv).toBeCloseTo(640); // 0.64 mSv/day measured by MSL RAD
    expect(day.measuredHere).toBe(true);
    expect(zoneCrewDose('gale-demo', 0)!.usv).toBe(0);
    expect(zoneCrewDose('demo', 3600)!.usv).toBeCloseTo((0.69 * 1000) / 24); // Jezero uses its own rate, not Gale's
  });

  it('has no zone estimate for an unknown run', async () => {
    const { zoneCrewDose } = await import('../src/lib/zoneEnvironment');
    expect(zoneCrewDose('unknown-run', 100)).toBeNull();
  });
});
