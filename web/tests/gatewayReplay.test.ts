import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { fromGatewayPackage, isGatewayManifest, parseJsonLines, PUBLIC_RASTERS_SCHEMA, type GatewayManifest, type PublicRasters } from '../src/data/gatewayReplay';
import { heightGrid } from '../src/lib/layers';
import { viewAt } from '../src/lib/replay';

/** The package recorded by the gateway (feat/integration), read unchanged from data/sample/replay. */
const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'sample', 'replay', 'mock-vertical-001');
const manifest = JSON.parse(readFileSync(join(DIR, 'manifest.json'), 'utf8')) as GatewayManifest;
const records = parseJsonLines(readFileSync(join(DIR, 'timeline.jsonl'), 'utf8'));

/**
 * Synthetic public raster attachment for a package, built only inside these tests (explicitly
 * MOCK: a sloping test grid, not a recorded raster or observation). One entry per map version.
 */
function attachmentFor(m: GatewayManifest, versions: number[]): PublicRasters {
  const t = m.terrain_meta as unknown as Record<string, unknown>;
  const rows = m.terrain_meta.rows;
  const cols = m.terrain_meta.cols;
  const prior = Array.from({ length: rows * cols }, (_, i) => (i % cols) * 0.5);
  const geometry = Object.fromEntries(['dataset_id', 'rows', 'cols', 'origin_x_m', 'origin_y_m', 'resolution_m', 'crs', 'origin_lat_deg', 'origin_lon_deg', 'vertical_datum'].map((k) => [k, t[k]]));
  return {
    schema_version: PUBLIC_RASTERS_SCHEMA,
    run_id: m.run_id,
    dataset_id: m.terrain_meta.dataset_id,
    rows,
    cols,
    terrain_geometry: geometry,
    prior,
    versions: Object.fromEntries(
      versions.map((v) => [String(v), { belief: prior.map((h) => h + v), sigma: prior.map(() => 0.5), observed: v > 1 ? [0, 1] : [] }]),
    ),
  };
}

/** Source-mode scenarios change the terrain consistently in every recorded meta. */
function recordsWithTerrain(m: GatewayManifest) {
  return records.map((record) => record.type === 'terrain_meta' ? {
    ...record,
    terrain_meta: { ...m.terrain_meta, header: record.terrain_meta.header, map_version: record.terrain_meta.map_version },
  } : record);
}

describe('gateway replay package', () => {
  it('is recognised as a gateway package, not as the demo fixture', () => {
    expect(isGatewayManifest(manifest)).toBe(true);
    expect(isGatewayManifest({ files: { timeline: 'timeline.json', rasters: 'rasters.json' } })).toBe(false);
  });

  const bundle = fromGatewayPackage(manifest, records);

  it('keeps every recorded state and event, with replay time from time_start_sim_s', () => {
    expect(records).toHaveLength(manifest.record_count);
    expect(bundle.timeline.events).toHaveLength(manifest.event_count);
    expect(bundle.timeline.events.map((e) => e.seq)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
    const t = bundle.timeline.frames.map((f) => f.timestamp_sim_s);
    expect(t[0]).toBeGreaterThanOrEqual(0);
    expect([...t].sort((a, b) => a - b)).toEqual(t);
    expect(bundle.manifest.duration_s).toBeCloseTo(records[records.length - 1].timestamp_sim_s - manifest.time_start_sim_s, 6);
  });

  it('collects both published routes and the replan to map version 2', () => {
    expect([...bundle.routes.keys()].sort()).toEqual(['mock-vertical-001-r1', 'mock-vertical-001-r2']);
    expect(bundle.routes.get('mock-vertical-001-r1')!.map_version_used).toBe(1);
    expect(bundle.routes.get('mock-vertical-001-r2')!.map_version_used).toBe(2);
    const end = viewAt(bundle, bundle.manifest.duration_s);
    expect(end.state?.map_version).toBe(2);
    expect(end.state?.mission_state).toBe('READY');
    expect(end.state?.route_id).toBe('mock-vertical-001-r2');
  });

  it('labels the run as a recorded MOCK replay and invents no terrain detail', () => {
    expect(bundle.manifest.mode).toBe('REPLAY');
    expect(manifest.source_mode).toBeUndefined(); // pinned sample predates the field
    expect(bundle.manifest.source_mode).toBe('MOCK'); // read from the MOCK terrain metadata
    expect(bundle.manifest.provenance).toEqual(['replay', 'simulated']);
    expect(bundle.rasters.prior.every((h) => h === 0)).toBe(true); // declared flat synthetic grid
    expect(bundle.rasters.reference).toBeUndefined(); // no evaluator reference in the package (R05)
    expect(Object.values(bundle.rasters.versions).every((v) => v.sigma.every((s) => s === null))).toBe(true);
    expect(bundle.manifest.pois.find((p) => p.kind === 'primary_goal')!.position).toEqual({ x: 300, y: 400, z: 0 });
  });

  it('rejects records of another run instead of hiding them', () => {
    const foreign = records.map((r) => ({ ...r, run_id: 'other' }));
    expect(() => fromGatewayPackage(manifest, foreign)).toThrow(/RUN_MISMATCH/);
  });

  it('follows the declared source_mode and refuses LIVE (ICD §6.1)', () => {
    const real = { ...manifest.terrain_meta, dataset_id: 'flat-test-grid', sources: ['flat grid for tests'] };
    const simManifest = { ...manifest, source_mode: 'SIMULATION', terrain_meta: real };
    const sim = fromGatewayPackage(simManifest, recordsWithTerrain(simManifest), attachmentFor(simManifest, [1, 2]));
    expect(sim.manifest.source_mode).toBe('SIMULATION');
    expect(sim.manifest.illustrative).toBe(false);
    expect(sim.manifest.disclaimer).not.toMatch(/MOCK/);
    const unknownManifest = { ...manifest, terrain_meta: real };
    const unknown = fromGatewayPackage(unknownManifest, recordsWithTerrain(unknownManifest), attachmentFor(unknownManifest, [1, 2]));
    expect(unknown.manifest.source_mode).toBe('UNKNOWN');
    expect(unknown.manifest.provenance).toEqual(['replay']);
    // A MOCK terrain stays MOCK whatever the package declares.
    expect(fromGatewayPackage({ ...manifest, source_mode: 'SIMULATION' }, records).manifest.source_mode).toBe('MOCK');
    expect(() => fromGatewayPackage({ ...manifest, source_mode: 'LIVE' }, records)).toThrow(/source_mode "LIVE"/);
  });
});

describe('public raster attachment (files.public_rasters, JOR-03)', () => {
  const used = [...new Set(fromGatewayPackage(manifest, records).timeline.frames.map((f) => f.mission_state.map_version))].filter((v) => v > 0);
  const named = { ...manifest, files: { ...manifest.files, public_rasters: 'public_rasters.json' } };

  it('draws the recorded prior and each map version from the attachment', () => {
    const att = attachmentFor(named, used);
    const b = fromGatewayPackage(named, records, att);
    expect(b.rasters.prior).toBe(att.prior);
    for (const v of used) expect(heightGrid(b.rasters, 'belief', v)).toBe(att.versions[String(v)].belief);
    expect(b.rasters.versions['2'].observed).toEqual([0, 1]);
    expect(b.manifest.disclaimer).toMatch(/recorded public rasters/);
    expect(b.manifest.disclaimer).not.toMatch(/illustrative flat/);
  });

  it('refuses an attachment that does not match its package', () => {
    const ok = attachmentFor(named, used);
    const bad = (change: (a: PublicRasters) => void) => {
      const a = structuredClone(ok);
      change(a);
      return () => fromGatewayPackage(named, records, a);
    };
    expect(bad((a) => (a.schema_version = 'mge-public-rasters-0.9'))).toThrow(/PUBLIC_RASTERS_INVALID.*schema_version/);
    expect(bad((a) => (a.run_id = 'another-run'))).toThrow(/PUBLIC_RASTERS_INVALID.*run_id/);
    expect(bad((a) => (a.terrain_geometry.resolution_m = 99))).toThrow(/terrain_geometry.resolution_m/);
    expect(bad((a) => a.prior.pop())).toThrow(/prior must hold/);
    expect(bad((a) => delete a.versions[String(used[used.length - 1])])).toThrow(/no fallback/);
    expect(bad((a) => (a.versions['2'].sigma[0] = -1))).toThrow(/negative/);
    expect(bad((a) => (a.versions['2'].observed = [0, 0]))).toThrow(/repeats cell/);
    expect(bad((a) => (a.versions['2'].observed = [a.rows * a.cols]))).toThrow(/outside the grid/);
    expect(bad((a) => ((a as unknown as Record<string, unknown>).reference = a.prior))).toThrow(/evaluator\/reference/);
  });

  it('refuses a non-MOCK package without an attachment and keeps the flat MOCK grid as an explicit illustration', () => {
    const real = { ...manifest.terrain_meta, dataset_id: 'ctx-crop', crs: 'IAU_2015:49900', sources: ['CTX DTM'] };
    const realManifest = { ...manifest, source_mode: 'SIMULATION', terrain_meta: real };
    expect(() => fromGatewayPackage(realManifest, recordsWithTerrain(realManifest))).toThrow(/PUBLIC_RASTERS_REQUIRED/);
    const mock = fromGatewayPackage(manifest, records);
    expect(mock.manifest.disclaimer).toMatch(/illustrative flat MOCK grid/);
  });
});
