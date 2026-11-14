import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { rasterizeUnits, unitPixels, unitShares, type GeologyData } from '../src/lib/geology';

const FILE = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo', 'geology.json');
const geo = JSON.parse(readFileSync(FILE, 'utf8')) as GeologyData;

const square = (unit: string, x0: number, y0: number, x1: number, y1: number) => ({ unit, rings: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]] as Array<Array<[number, number]>> });
const toy: GeologyData = {
  ...geo,
  frame: { crs: 'test', origin_x_m: 0, origin_y_m: 0, width_m: 100, height_m: 100 },
  units: [geo.units[0], geo.units[1]],
  polygons: [square(geo.units[0].id, 0, 0, 50, 100), square(geo.units[1].id, 50, 0, 100, 50)],
};

describe('geology rasterization', () => {
  it('fills polygons at cell centres with row 0 at the south edge', () => {
    const g = rasterizeUnits(toy, 10);
    expect(g[0]).toBe(0); // south-west: unit 0
    expect(g[9]).toBe(1); // south-east: unit 1
    expect(g[9 * 10 + 9]).toBe(-1); // north-east: uncovered
    const { shares, uncovered } = unitShares(toy, g);
    expect(shares[0]).toBeCloseTo(0.5, 6);
    expect(shares[1]).toBeCloseTo(0.25, 6);
    expect(uncovered).toBeCloseTo(0.25, 6);
  });

  it('dims every unit except the selected one', () => {
    const g = rasterizeUnits(toy, 10);
    const all = unitPixels(toy, g, null);
    const sel = unitPixels(toy, g, toy.units[0].id);
    expect(sel.slice(0, 3)).toEqual(all.slice(0, 3));
    expect(sel[9 * 4]).toBeLessThan(all[9 * 4]);
  });
});

describe('SIM 3464 units of the demo crop', () => {
  it('cites the source and declares the registration offset', () => {
    expect(geo.source.doi).toBe('https://doi.org/10.3133/sim3464');
    expect(geo.source.registration_note).toMatch(/100-200 m/);
  });

  it('covers the crop with the mapped units and keeps their composition text', () => {
    const { shares, uncovered } = unitShares(geo, rasterizeUnits(geo, 200));
    expect(uncovered).toBeLessThan(0.02);
    expect(shares.every((s) => s > 0)).toBe(true);
    expect(geo.units.map((u) => u.name)).toEqual(expect.arrayContaining(['Jezero floor unit', 'Jezero fan 2 unit']));
    expect(geo.units.find((u) => u.name === 'Jezero fan 2 unit')!.characteristics).toMatch(/carbonate/i);
  });
});
