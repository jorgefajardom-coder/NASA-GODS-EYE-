import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { barometricRatio, galeBinAt, jezeroToGalePressure, latestJezeroSol, parseAtmosphere, surfaceDose, crewDose, fmtMicroSv } from '../src/lib/atmos';

const FILE = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo', 'atmosphere.json');
const data = parseAtmosphere(JSON.parse(readFileSync(FILE, 'utf8')))!;

describe('atmosphere context', () => {
  it('loads the demo file and refuses malformed input', () => {
    expect(data).not.toBeNull();
    expect(parseAtmosphere({ schema: 'other' })).toBeNull();
    expect(parseAtmosphere({ ...data, radiation: { ...data.radiation, dose_equivalent_msv_per_day: 0 } })).toBeNull();
  });

  it('keeps sources and provenance for every input', () => {
    expect(data.sources.map((s) => s.id).sort()).toEqual(['meda', 'rad', 'rems']);
    for (const s of data.sources.filter((x) => x.id !== 'rad')) expect(s.sha256).toMatch(/^[0-9a-f]{64}$/);
  });

  it('bins the whole Gale year without gaps', () => {
    const bins = data.gale_seasonal.bins;
    expect(bins[0].ls_from).toBe(0);
    expect(bins[bins.length - 1].ls_to).toBe(360);
    for (let i = 1; i < bins.length; i++) expect(bins[i].ls_from).toBe(bins[i - 1].ls_to);
    expect(galeBinAt(data, 365)).toBe(bins[0]);
  });

  it('finds the latest Jezero reading and a pressure ratio consistent with elevation', () => {
    const last = latestJezeroSol(data)!;
    expect(last.pressure_pa).not.toBeNull();
    const r = jezeroToGalePressure(data)!;
    expect(r.ratio).toBeGreaterThan(0.7);
    expect(r.ratio).toBeLessThan(1);
    expect(barometricRatio(0)).toBe(1);
  });

  it('accumulates dose linearly with exposure and never below zero', () => {
    const day = surfaceDose(data, 86400);
    expect(day.msv).toBeCloseTo(data.radiation.dose_equivalent_msv_per_day, 9);
    expect(surfaceDose(data, 2 * 86400).msv).toBeCloseTo(2 * day.msv, 9);
    expect(surfaceDose(data, -5).msv).toBe(0);
  });

  it('gives the running crew dose in microsieverts at the RAD rate', () => {
    const run = crewDose(data, 4442); // whole demo run, about 1.23 h
    expect(run.usv).toBeCloseTo((data.radiation.dose_equivalent_msv_per_day * 1000 * 4442) / 86400, 9);
    expect(run.sigmaUsv).toBeLessThan(run.usv);
    expect(crewDose(data, 0).usv).toBe(0);
    expect(fmtMicroSv(0.123)).toBe('0.12');
    expect(fmtMicroSv(32.94)).toBe('32.9');
    expect(fmtMicroSv(640.4)).toBe('640');
  });
});
