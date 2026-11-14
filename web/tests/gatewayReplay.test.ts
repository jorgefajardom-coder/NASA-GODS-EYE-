import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { fromGatewayPackage, isGatewayManifest, parseJsonLines, type GatewayManifest } from '../src/data/gatewayReplay';
import { viewAt } from '../src/lib/replay';

/** The package recorded by the gateway (feat/integration), read unchanged from data/sample/replay. */
const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'sample', 'replay', 'mock-vertical-001');
const manifest = JSON.parse(readFileSync(join(DIR, 'manifest.json'), 'utf8')) as GatewayManifest;
const records = parseJsonLines(readFileSync(join(DIR, 'timeline.jsonl'), 'utf8'));

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
    expect(bundle.manifest.provenance).toEqual(['replay', 'simulated']);
    expect(bundle.rasters.prior.every((h) => h === 0)).toBe(true); // declared flat synthetic grid
    expect(bundle.rasters.reference.every((h) => h === null)).toBe(true); // no evaluator reference in the package
    expect(Object.values(bundle.rasters.versions).every((v) => v.sigma.every((s) => s === null))).toBe(true);
    expect(bundle.manifest.pois.find((p) => p.kind === 'primary_goal')!.position).toEqual({ x: 300, y: 400, z: 0 });
  });

  it('drops records of another run', () => {
    const foreign = records.map((r) => ({ ...r, run_id: 'other' }));
    expect(() => fromGatewayPackage(manifest, foreign)).toThrow(/no mission state/);
  });
});
