import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { droneSurvey } from '../src/lib/droneSurvey';
import type { RasterSet } from '../src/types/replay';

const dir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo');
const rasters = JSON.parse(readFileSync(join(dir, 'rasters.json'), 'utf8')) as RasterSet;
const meta = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8')).terrain_meta;

describe('drone survey map', () => {
  it('has nothing observed before the drone publishes its map update', () => {
    const s = droneSurvey(rasters, meta, 1, 0, 0, 2000);
    expect(s.observedCount).toBe(0);
    expect(s.points.some((p) => p.observed)).toBe(false);
  });

  it("shows the drone's observed cells of map v2 and keeps the rest as prior estimate", () => {
    const s = droneSurvey(rasters, meta, 2, 0, 0, 2000);
    expect(s.observedCount).toBe(157);
    const seen = s.points.filter((p) => p.observed).length;
    expect(seen).toBeGreaterThan(0);
    expect(seen).toBeLessThanOrEqual(157);
    expect(s.points.every((p) => p.t >= 0 && p.t <= 1)).toBe(true);
  });

  it('keeps only cells within the radius', () => {
    const s = droneSurvey(rasters, meta, 2, 0, 0, 100);
    expect(s.points.every((p) => Math.hypot(p.x, p.y) <= 100)).toBe(true);
  });
});
