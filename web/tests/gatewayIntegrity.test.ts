/** Recorder-package contract regressions, using the unchanged public MOCK recording. */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  fromGatewayPackage, parseJsonLines, PUBLIC_RASTERS_SCHEMA, validateGatewayPackage,
  type GatewayManifest, type GatewayRecord, type GatewaySnapshot, type PublicRasters,
} from '../src/data/gatewayReplay';
import { loadReplay } from '../src/data/replayAdapter';

const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'sample', 'replay', 'mock-vertical-001');

function packageAt(directory = DIR) {
  return {
    manifest: JSON.parse(readFileSync(join(directory, 'manifest.json'), 'utf8')) as GatewayManifest,
    records: parseJsonLines(readFileSync(join(directory, 'timeline.jsonl'), 'utf8')),
    snapshot: JSON.parse(readFileSync(join(directory, 'snapshot.json'), 'utf8')) as GatewaySnapshot,
  };
}

type Package = ReturnType<typeof packageAt>;

function attachment(manifest: GatewayManifest): PublicRasters {
  const meta = manifest.terrain_meta;
  const keys = ['dataset_id', 'rows', 'cols', 'origin_x_m', 'origin_y_m', 'resolution_m', 'crs', 'origin_lat_deg', 'origin_lon_deg', 'vertical_datum'];
  const prior = Array(meta.rows * meta.cols).fill(0);
  return {
    schema_version: PUBLIC_RASTERS_SCHEMA, run_id: manifest.run_id, dataset_id: meta.dataset_id,
    rows: meta.rows, cols: meta.cols,
    terrain_geometry: Object.fromEntries(keys.map((key) => [key, (meta as unknown as Record<string, unknown>)[key]])),
    prior,
    versions: Object.fromEntries([1, 2].map((version) => [String(version), { belief: prior, sigma: prior, observed: [] }])),
  };
}

function firstState(records: GatewayRecord[]) {
  const record = records.find((r) => r.type === 'state' && r.state.route_id);
  if (!record || record.type !== 'state') throw new Error('Missing active-route fixture');
  return record;
}

describe('canonical recorded-package integrity', () => {
  it('accepts the unchanged historical recording and its final snapshot', () => {
    const { manifest, records, snapshot } = packageAt();
    expect(() => validateGatewayPackage(manifest, records, snapshot)).not.toThrow();
    const bundle = fromGatewayPackage(manifest, records, undefined, snapshot);
    expect(bundle.timeline.frames).toHaveLength(records.filter((r) => r.type === 'state').length);
    expect(bundle.timeline.events).toHaveLength(manifest.event_count);
  });

  const invalid: Array<[string, (p: Package) => void]> = [
    ['RECORD_COUNT_MISMATCH', (p) => { p.manifest.record_count += 1; }],
    ['EVENT_COUNT_MISMATCH', (p) => { p.manifest.event_count += 1; }],
    ['UNSUPPORTED_SCHEMA', (p) => { p.manifest.schema_version = 'mge-web-0.1-draft'; }],
    ['REPLAY_MODE_REQUIRED', (p) => { (p.manifest as unknown as Record<string, unknown>).mode = 'LIVE'; }],
    ['RUN_MISMATCH', (p) => { p.records[0].run_id = 'other'; }],
    ['RUN_MISMATCH', (p) => { p.snapshot.run_id = 'other'; }],
    ['CLOCK_REGRESSION', (p) => { p.records[p.records.length - 1].timestamp_sim_s = 0; }],
    ['ENVELOPE_MAP_REGRESSION', (p) => { p.records[p.records.length - 1].map_version = 0; }],
    ['SNAPSHOT_EVENTS_MISMATCH', (p) => { p.snapshot.events = []; }],
    ['SNAPSHOT_STATE_MISMATCH', (p) => { p.snapshot.mission_state = null; }],
    ['FINAL_CLOCK_MISMATCH', (p) => { p.snapshot.timestamp_sim_s += 1; }],
    ['FINAL_MAP_MISMATCH', (p) => { p.snapshot.map_version += 1; }],
    ['UNSUPPORTED_FILE_LAYOUT', (p) => { p.manifest.files.timeline = '../private.jsonl'; }],
    ['EVALUATOR_REFERENCE_FORBIDDEN', (p) => { Object.assign(p.manifest, { extra: [{ reference: [1] }] }); }],
    ['NON_JSON_NUMBER', (p) => { p.manifest.timestamp_sim_s = Infinity; }],
    ['INVALID_MAP_VERSION', (p) => { (p.records[0] as unknown as Record<string, unknown>).map_version = true; }],
    ['STALE_ROUTE', (p) => { firstState(p.records).state.active_route!.map_version_used = 0; }],
    ['ACTIVE_ROUTE_NOT_FEASIBLE', (p) => { firstState(p.records).state.active_route!.status = 'UNKNOWN'; }],
    ['AGENT_RUN_MISMATCH', (p) => { firstState(p.records).state.agents[0].run_id = 'other'; }],
    ['STATE_AHEAD_OF_MAP', (p) => { firstState(p.records).state.map_version = 99; }],
    ['INVALID_FRAME', (p) => { firstState(p.records).state.header!.frame_id = 'odom'; }],
    ['GEOMETRY_CHANGE_REQUIRES_NEW_DATASET', (p) => {
      const record = p.records.find((r) => r.type === 'terrain_meta' && r.terrain_meta.map_version === 2);
      if (record?.type === 'terrain_meta') record.terrain_meta.resolution_m += 1;
    }],
    ['DUPLICATE_EVENT_ID', (p) => {
      const events = p.records.filter((r) => r.type === 'event');
      events[1].event.event_id = events[0].event.event_id;
    }],
    ['DUPLICATE_EVENT_SEQ', (p) => {
      const events = p.records.filter((r) => r.type === 'event');
      events[1].event.seq = events[0].event.seq;
    }],
    ['INVALID_EVENT_SEQ', (p) => {
      const event = p.records.find((r) => r.type === 'event');
      if (event?.type === 'event') event.event.seq = 0;
    }],
  ];
  it.each(invalid)('rejects %s without repairing input', (reason, change) => {
    const p = packageAt();
    change(p);
    expect(() => validateGatewayPackage(p.manifest, p.records, p.snapshot)).toThrow(reason);
  });

  it.each(['energy_est_wh', 'outbound_path'] as const)('rejects route ID reuse with conflicting %s', (field) => {
    const { manifest, records } = packageAt();
    const original = firstState(records);
    const duplicate = structuredClone(original);
    if (field === 'energy_est_wh') duplicate.state.active_route!.energy_est_wh! += 1;
    else duplicate.state.active_route!.outbound_path[0].x += 1;
    records.splice(records.indexOf(original) + 1, 0, duplicate);
    manifest.record_count = records.length;
    expect(() => fromGatewayPackage(manifest, records)).toThrow('ROUTE_ID_REUSED');
  });

  it('accepts a repeated route whose header refreshes but content stays immutable', () => {
    const { manifest, records, snapshot } = packageAt();
    const original = firstState(records);
    const duplicate = structuredClone(original);
    duplicate.state.active_route!.header!.stamp!.nanosec += 1;
    records.splice(records.indexOf(original) + 1, 0, duplicate);
    manifest.record_count = records.length;
    expect(() => validateGatewayPackage(manifest, records, snapshot)).not.toThrow();
  });

  it('accepts a state lagging the newest map, including version 0 before any map', () => {
    const { manifest, records, snapshot } = packageAt();
    const meta2 = records.findIndex((r) => r.type === 'terrain_meta' && r.terrain_meta.map_version === 2);
    const state = structuredClone(records.slice(0, meta2).filter((r) => r.type === 'state').at(-1)!);
    if (state.type !== 'state') throw new Error('Missing state');
    state.map_version = 2;
    state.timestamp_sim_s = records[meta2].timestamp_sim_s;
    records.splice(meta2 + 1, 0, state);
    manifest.record_count = records.length;
    expect(() => validateGatewayPackage(manifest, records, snapshot)).not.toThrow();
    const initial = structuredClone(records.find((r) => r.type === 'state')!);
    if (initial.type !== 'state') throw new Error('Missing state');
    initial.state.map_version = 0;
    initial.map_version = 0;
    initial.timestamp_sim_s = manifest.time_start_sim_s;
    records.unshift(initial);
    manifest.record_count = records.length;
    const bundle = fromGatewayPackage(manifest, records, attachment(manifest), snapshot);
    expect(bundle.rasters.versions['0'].belief).toBe(bundle.rasters.prior);
  });

  it('preserves late event arrival while validating snapshot history in sequence order', () => {
    const { manifest, records, snapshot } = packageAt();
    const first = records.findIndex((r) => r.type === 'event');
    const [late] = records.splice(first, 1);
    const second = records.findIndex((r) => r.type === 'event');
    late.timestamp_sim_s = records[second].timestamp_sim_s;
    late.map_version = records[second].map_version;
    records.splice(second + 1, 0, late);
    expect(() => validateGatewayPackage(manifest, records, snapshot)).not.toThrow();
    const bundle = fromGatewayPackage(manifest, records, undefined, snapshot);
    expect(bundle.timeline.events).toHaveLength(manifest.event_count);
  });

  it('rejects an attachment version with no recorded TerrainMeta', () => {
    const { manifest, records } = packageAt();
    const rasters = attachment(manifest);
    rasters.versions['999'] = structuredClone(rasters.versions['2']);
    expect(() => fromGatewayPackage(manifest, records, rasters)).toThrow(/no recorded TerrainMeta/);
  });

  it('describes MOCK providers without claiming the terrain or planner is synthetic', () => {
    const { manifest, records } = packageAt();
    const bundle = fromGatewayPackage(manifest, records, attachment(manifest));
    expect(bundle.manifest.disclaimer).toMatch(/MOCK providers/);
    expect(bundle.manifest.disclaimer).toMatch(/recorded public rasters/);
    expect(bundle.manifest.disclaimer).not.toMatch(/straight-line MOCK planner|no Mars data|flat synthetic grid/);
  });
});

describe('file loader validates the closing snapshot', () => {
  afterEach(() => vi.unstubAllGlobals());

  function serve(p: Package, missingSnapshot = false) {
    const fetch = vi.fn(async (url: string) => {
      const filename = url.split('/').pop();
      if (filename === 'manifest.json') return new Response(JSON.stringify(p.manifest));
      if (filename === 'timeline.jsonl') return new Response(p.records.map((r) => JSON.stringify(r)).join('\n'));
      if (filename === 'snapshot.json' && !missingSnapshot) return new Response(JSON.stringify(p.snapshot));
      return new Response('', { status: 404 });
    });
    vi.stubGlobal('fetch', fetch);
    return fetch;
  }

  it('loads the recorded snapshot as well as the manifest and timeline', async () => {
    const p = packageAt();
    const fetch = serve(p);
    const bundle = await loadReplay('replay/test');
    expect(fetch.mock.calls.map(([url]) => url)).toContainEqual(expect.stringContaining('/snapshot.json'));
    expect(bundle.manifest.run_id).toBe(p.manifest.run_id);
  });

  it('rejects a missing snapshot instead of presenting an incomplete recording', async () => {
    serve(packageAt(), true);
    await expect(loadReplay('replay/test')).rejects.toThrow(/snapshot.json.*404/);
  });

  it('rejects a closing snapshot that disagrees with the recorded timeline', async () => {
    const p = packageAt();
    p.snapshot.events = [];
    serve(p);
    await expect(loadReplay('replay/test')).rejects.toThrow('SNAPSHOT_EVENTS_MISMATCH');
  });
});

const recordedDirectory = process.env.MGE_REPLAY_PACKAGE;
it.skipIf(!recordedDirectory)('consumes an explicitly supplied recorder package with its unchanged public rasters', () => {
  const { manifest, records, snapshot } = packageAt(recordedDirectory!);
  const rasters = JSON.parse(readFileSync(join(recordedDirectory!, manifest.files.public_rasters!), 'utf8')) as PublicRasters;
  const bundle = fromGatewayPackage(manifest, records, rasters, snapshot);
  expect(bundle.manifest.run_id).toBe(manifest.run_id);
  expect(bundle.timeline.frames).toHaveLength(records.filter((record) => record.type === 'state').length);
  expect(bundle.timeline.events).toHaveLength(manifest.event_count);
  expect(bundle.rasters.prior).toEqual(rasters.prior);
  for (const record of records) {
    if (record.type === 'state' && record.state.map_version !== 0) {
      expect(bundle.rasters.versions[String(record.state.map_version)]).toEqual(rasters.versions[String(record.state.map_version)]);
    }
  }
});
