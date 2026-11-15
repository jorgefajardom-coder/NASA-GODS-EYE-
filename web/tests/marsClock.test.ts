import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { fmtHms, lmstH, ltstH, mars2020Sol, marsTime, missionSol, MSL_LANDING_MS, ttMinusUtcS } from '../src/lib/marsClock';

const atmos = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo', 'atmosphere.json'), 'utf8')) as {
  jezero_sols: Array<{ sol: number; earth_date: string; ls_deg: number | null }>;
};

describe('Mars clock (Mars24 algorithm)', () => {
  it('reproduces the published Mars24 worked example (2000-01-06 00:00 UTC)', () => {
    const t = marsTime(Date.UTC(2000, 0, 6));
    expect(ttMinusUtcS(Date.UTC(2000, 0, 6))).toBe(64.184);
    expect(t.lsDeg).toBeCloseTo(277.18758, 3);
    expect(t.msd).toBeCloseTo(44795.9998, 3);
    expect(t.mtcH).toBeCloseTo(23.9945, 2); // 23:59:39
  });

  it('agrees with the season (Ls) of the MEDA sols at Jezero', () => {
    for (const s of atmos.jezero_sols) {
      if (s.ls_deg == null) continue;
      // Ls moves about 0.65 degrees per sol, so any time on that Earth date is within a degree.
      expect(Math.abs(marsTime(Date.parse(`${s.earth_date}T12:00:00Z`)).lsDeg - s.ls_deg)).toBeLessThan(1);
    }
  });

  it('counts Perseverance sols like the MEDA summaries (sol 0 = landing)', () => {
    expect(mars2020Sol(Date.UTC(2021, 1, 18, 21))).toBe(0);
    for (const s of atmos.jezero_sols) {
      // An Earth date overlaps two sols; the summary's sol is one of them.
      const sols = [0, 12, 23].map((h) => mars2020Sol(Date.parse(`${s.earth_date}T00:00:00Z`) + h * 3600e3));
      expect(sols).toContain(s.sol);
    }
  });

  it('keeps local times on a 24 h dial', () => {
    const t = marsTime(Date.UTC(2024, 3, 27, 12));
    for (const h of [lmstH(t, 77.45), ltstH(t, 77.45)]) {
      expect(h).toBeGreaterThanOrEqual(0);
      expect(h).toBeLessThan(24);
    }
    expect(fmtHms(23.9945)).toBe('23:59:40');
    expect(fmtHms(0)).toBe('00:00:00');
  });
});


describe('mission sol of another rover', () => {
  it('counts Curiosity from its landing sol at Gale', () => {
    const gale = 137.44;
    expect(missionSol(MSL_LANDING_MS, gale, MSL_LANDING_MS)).toBe(0);
    expect(missionSol(MSL_LANDING_MS + 24.66 * 3600e3 * 10, gale, MSL_LANDING_MS)).toBeGreaterThanOrEqual(9);
    expect(missionSol(Date.UTC(2026, 10, 15), gale, MSL_LANDING_MS)).toBeGreaterThan(5000); // NASA's feed reached sol 5073 in November 2026
  });
});
