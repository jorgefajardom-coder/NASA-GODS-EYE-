import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { fromGatewayPackage, parseJsonLines, PUBLIC_RASTERS_SCHEMA, type GatewayManifest, type PublicRasters } from '../src/data/gatewayReplay';
import { DEFAULT_ROCK_STYLE, HAZARD_ROCK_M, obstacleRocks, ROCK_ABUNDANCE_K, ROCK_DECAY_PER_M, ROCK_STYLES, ROCK_VARIANTS } from '../src/lib/obstacleRocks';

// Synthetic MOCK attachment on the pinned mock-vertical-001 package; not a recorded raster.
const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'sample', 'replay', 'mock-vertical-001');
const base = JSON.parse(readFileSync(join(DIR, 'manifest.json'), 'utf8')) as GatewayManifest;
const records = parseJsonLines(readFileSync(join(DIR, 'timeline.jsonl'), 'utf8'));
const manifest = { ...base, files: { ...base.files, public_rasters: 'public_rasters.json' } };
const used = [...new Set(fromGatewayPackage(base, records).timeline.frames.map((f) => f.mission_state.map_version))].filter((v) => v > 0);

function attachment(impassable?: unknown): PublicRasters {
  const t = manifest.terrain_meta as unknown as Record<string, unknown>;
  const { rows, cols } = manifest.terrain_meta;
  const prior = Array.from({ length: rows * cols }, () => 0);
  return {
    schema_version: PUBLIC_RASTERS_SCHEMA,
    run_id: manifest.run_id,
    dataset_id: manifest.terrain_meta.dataset_id,
    rows,
    cols,
    terrain_geometry: Object.fromEntries(['dataset_id', 'rows', 'cols', 'origin_x_m', 'origin_y_m', 'resolution_m', 'crs', 'origin_lat_deg', 'origin_lon_deg', 'vertical_datum'].map((k) => [k, t[k]])),
    prior,
    versions: Object.fromEntries(used.map((v) => [String(v), {
      belief: prior, sigma: prior.map(() => 0.5), observed: [],
      ...(impassable === undefined ? {} : { impassable }),
    }])) as PublicRasters['versions'],
  };
}

describe('impassable cells (optional public raster layer)', () => {
  it('reads them per map version and leaves them absent when not recorded', () => {
    const with_ = fromGatewayPackage(manifest, records, attachment([3, 1]));
    expect(with_.rasters.versions[String(used[0])].impassable).toEqual([3, 1]);
    const without = fromGatewayPackage(manifest, records, attachment());
    expect(without.rasters.versions[String(used[0])].impassable).toBeUndefined();
  });

  it('refuses malformed lists', () => {
    const cells = manifest.terrain_meta.rows * manifest.terrain_meta.cols;
    expect(() => fromGatewayPackage(manifest, records, attachment('x'))).toThrow(/impassable must be a list/);
    expect(() => fromGatewayPackage(manifest, records, attachment([cells]))).toThrow(/impassable holds .* outside the grid/);
    expect(() => fromGatewayPackage(manifest, records, attachment([2, 2]))).toThrow(/impassable repeats cell 2/);
  });
});

describe('obstacle rocks', () => {
  const meta = { rows: 32, cols: 32, origin_x_m: -64, origin_y_m: -64, resolution_m: 4 };

  it('draws one hazard-size rock and smaller rocks on each impassable cell', () => {
    const rocks = obstacleRocks(meta, [0, 33, 1023, 33, -1, 1024, 2.5]);
    expect([...new Set(rocks.map((r) => r.cell))]).toEqual([0, 33, 1023]);
    for (const cell of [0, 33, 1023]) {
      const cluster = rocks.filter((r) => r.cell === cell);
      const hazards = cluster.filter((r) => r.hazard);
      expect(hazards).toHaveLength(1);
      expect(cluster.length).toBeGreaterThanOrEqual(5);
      const big = Math.max(hazards[0].widthM, hazards[0].depthM) / 1.15;
      expect(big).toBeGreaterThanOrEqual(HAZARD_ROCK_M * 0.7 - 1e-9);
      expect(cluster.filter((r) => !r.hazard).every((r) => r.widthM < hazards[0].widthM * 1.3)).toBe(true);
    }
  });

  it('sizes rocks with the Golombek-Rapp law: small rocks far outnumber large ones', () => {
    const all = obstacleRocks(meta, Array.from({ length: 1024 }, (_, i) => i)).filter((r) => !r.hazard);
    const small = all.filter((r) => r.widthM < 0.5).length;
    const large = all.filter((r) => r.widthM >= 0.5).length;
    expect(ROCK_DECAY_PER_M).toBeCloseTo(1.79 + 0.152 / ROCK_ABUNDANCE_K);
    expect(small).toBeGreaterThan(large * 2);
  });

  it('styles each cell by its USGS geologic unit', () => {
    const unitAt = (cell: number) => (cell < 512 ? 'Njf' : 'Nle');
    const rocks = obstacleRocks(meta, [10, 900], unitAt);
    const floor = rocks.filter((r) => r.cell === 10);
    const etched = rocks.filter((r) => r.cell === 900);
    expect(floor.every((r) => r.style === ROCK_STYLES.Njf)).toBe(true);
    expect(etched.every((r) => r.style === ROCK_STYLES.Nle)).toBe(true);
    // Small rocks on the etched unit are flat slabs.
    expect(etched.filter((r) => !r.hazard).every((r) => r.heightM / r.widthM < 0.5)).toBe(true);
    expect(obstacleRocks(meta, [10], () => 'Xyz')[0].style).toBe(DEFAULT_ROCK_STYLE);
  });

  it('keeps every rock centre inside its cell, so none leaves the terrain', () => {
    for (const r of obstacleRocks(meta, Array.from({ length: 1024 }, (_, i) => i))) {
      const row = Math.floor(r.cell / 32);
      const col = r.cell % 32;
      expect(r.x).toBeGreaterThanOrEqual(-64 + col * 4);
      expect(r.x).toBeLessThanOrEqual(-64 + (col + 1) * 4);
      expect(r.y).toBeGreaterThanOrEqual(-64 + row * 4);
      expect(r.y).toBeLessThanOrEqual(-64 + (row + 1) * 4);
      expect(r.sinkM).toBeLessThan(r.heightM);
      expect(r.variant).toBeLessThan(ROCK_VARIANTS);
    }
  });

  it('fills continuous blocked bands with large outcrop blocks', () => {
    const band = [10 * 32 + 5, 10 * 32 + 6, 10 * 32 + 7]; // three cells in a row
    const rocks = obstacleRocks(meta, band);
    const middle = rocks.filter((r) => r.cell === band[1]);
    expect(middle.every((r) => r.section)).toBe(true);           // two blocked neighbours
    expect(rocks.filter((r) => r.cell === band[0]).some((r) => r.section)).toBe(false); // end of band
    const blocks = middle.filter((r) => r.hazard);
    expect(blocks.length).toBeGreaterThanOrEqual(2);
    for (const b of blocks) expect(Math.max(b.widthM, b.depthM)).toBeGreaterThan(HAZARD_ROCK_M);
  });

  it('is deterministic and empty without cells', () => {
    expect(obstacleRocks(meta, [5, 9])).toEqual(obstacleRocks(meta, [5, 9]));
    expect(obstacleRocks(meta, undefined)).toEqual([]);
    expect(obstacleRocks(meta, [])).toEqual([]);
  });
});

describe('public geology of the dataset', () => {
  it('matches the jezero_mvp crop exactly; the whole crop lies on the Lower etched unit (Nle)', async () => {
    const { geologyMatchesRun } = await import('../src/lib/terrainPresentation');
    const { rasterizeUnits } = await import('../src/lib/geology');
    const geology = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'geology', 'jezero_mvp.json'), 'utf8'));
    const run = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'sample', 'manifest.json'), 'utf8'));
    const meta = {
      dataset_id: run.region_id, origin_x_m: -64, origin_y_m: -64, rows: 32, cols: 32, resolution_m: 4,
      origin_lat_deg: 18.45, origin_lon_deg: 77.45, vertical_datum: run.vertical_datum,
    };
    expect(geologyMatchesRun(geology, { terrain_meta: meta } as never)).toBe(true);
    expect(geologyMatchesRun(geology, { terrain_meta: { ...meta, dataset_id: 'other' } } as never)).toBe(false);
    expect(geology.source.series).toBe('Scientific Investigations Map 3464');
    const symbols = new Set([...rasterizeUnits(geology, 32)].filter((i) => i >= 0).map((i) => geology.units[i].symbol));
    expect([...symbols]).toEqual(['Nle']);
  });
});
