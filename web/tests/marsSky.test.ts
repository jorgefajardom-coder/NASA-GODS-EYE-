import { describe, expect, it } from 'vitest';
import { azElFromEnu, celestialToLocal, daylight, marsOrientation, marsSun } from '../src/lib/marsSky';
import { ltstH, marsTime } from '../src/lib/marsClock';

const LAT = 18.44;
const LON = 77.45;
const MS = Date.UTC(2026, 10, 14, 12, 0, 0);

describe('marsSun', () => {
  it('stands highest near true solar noon, to the south of Jezero when the Sun is north of the site', () => {
    // Find the instant of local true noon near MS by stepping, then check the noon geometry.
    let best = MS;
    let bestDiff = 99;
    for (let k = 0; k < 24 * 60 * 1.03; k++) {
      const ms = MS + k * 60000;
      const diff = Math.abs(ltstH(marsTime(ms), LON) - 12);
      if (diff < bestDiff) {
        bestDiff = diff;
        best = ms;
      }
    }
    const s = marsSun(best, LAT, LON);
    expect(s.elDeg).toBeCloseTo(90 - Math.abs(LAT - s.declDeg), 1);
    // Ls < 180: declination is north; Jezero (18.4 N) has the Sun to the south only if decl < lat.
    if (s.declDeg < LAT) expect(Math.abs(s.azDeg - 180)).toBeLessThan(2);
    else expect(Math.min(s.azDeg, 360 - s.azDeg)).toBeLessThan(2);
  });

  it('rises in the east and sets in the west', () => {
    const t = marsTime(MS);
    // Hours to add to reach 06:30 and 17:30 local true solar time (1 sol = 88775 s).
    const at = (h: number) => MS + (((h - ltstH(t, LON) + 24) % 24) / 24) * 88775244;
    expect(marsSun(at(6.5), LAT, LON).azDeg).toBeGreaterThan(45);
    expect(marsSun(at(6.5), LAT, LON).azDeg).toBeLessThan(135);
    expect(marsSun(at(17.5), LAT, LON).azDeg).toBeGreaterThan(225);
    expect(marsSun(at(17.5), LAT, LON).azDeg).toBeLessThan(315);
    expect(marsSun(at(0), LAT, LON).elDeg).toBeLessThan(-40);
  });
});

describe('celestialToLocal', () => {
  it("puts Mars's north celestial pole due north at the site's latitude", () => {
    const { alpha0, delta0 } = marsOrientation(MS);
    const p = azElFromEnu(celestialToLocal(MS, LAT, LON)(alpha0, delta0));
    expect(p.elDeg).toBeCloseTo(LAT, 3);
    expect(Math.min(p.azDeg, 360 - p.azDeg)).toBeLessThan(0.01);
  });

  it('turns the stars once per sidereal day (24.6229 h)', () => {
    const f0 = celestialToLocal(MS, LAT, LON)(101.287, -16.716); // Sirius
    const f1 = celestialToLocal(MS + 88642.663 * 1000, LAT, LON)(101.287, -16.716);
    for (let i = 0; i < 3; i++) expect(f1[i]).toBeCloseTo(f0[i], 3);
  });

  it('returns unit vectors', () => {
    const v = celestialToLocal(MS, LAT, LON)(213.915, 19.183);
    expect(Math.hypot(...v)).toBeCloseTo(1, 9);
  });
});

describe('daylight', () => {
  it('is dark well below the horizon and full in daytime', () => {
    expect(daylight(-20)).toBe(0);
    expect(daylight(30)).toBe(1);
    expect(daylight(0)).toBeGreaterThan(0.3);
    expect(daylight(0)).toBeLessThan(0.8);
  });
});
