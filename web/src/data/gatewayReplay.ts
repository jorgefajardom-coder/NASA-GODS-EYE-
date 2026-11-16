import type { AgentState, MissionEvent, MissionState, Point, RouteDecision, TerrainMeta } from '../types/icd';
import type { RasterSet, ReplayBundle, ReplayManifest } from '../types/replay';
import { WEB_SCHEMA_VERSION } from '../types/icd';
import { assembleBundle, ReplayLoadError } from './replayAdapter';
import { resolveSourceMode, type SourceMode } from '../lib/provenance';

/**
 * Reads a replay package written by the gateway's replay_recorder (docs/ICD.md §7,
 * e.g. data/sample/replay/mock-vertical-001) and turns it into the viewer's bundle.
 *
 * The package is used as recorded: nothing is added to the mission. What the package
 * does not contain is shown as missing, not invented:
 *  - rasters come from the optional public attachment named by `files.public_rasters`
 *    (`mge-public-rasters-1.0.0`, docs/REPLAY_CONTRACT.md): the public prior and, per map
 *    version, belief, sigma and observed cells. It is checked against the package (run,
 *    dataset, geometry, sizes, every map version the states used) and refused on any
 *    mismatch; no version falls back to another. Map version 0 (no map received yet) has
 *    no raster by contract, so the public prior is drawn for it, with sigma as NoData.
 *  - without the attachment, only a MOCK package over a declared flat grid may be drawn,
 *    as an explicit illustrative choice: 0 m everywhere, sigma NoData. Any other package
 *    is refused with PUBLIC_RASTERS_REQUIRED.
 *  - the evaluator reference never travels in a package; an attachment carrying one is refused.
 *  - no POIs, control points or local elevation offset exist; base and goal come from
 *    MissionState.
 */

interface Header {
  stamp?: { sec: number; nanosec: number };
  frame_id?: string;
}

type WithHeader<T> = Omit<T, 'timestamp_sim_s'> & { header?: Header };

interface GatewayEnvelope {
  schema_version: string;
  run_id: string;
  mode: 'REPLAY';
  map_version: number;
  timestamp_sim_s: number;
}

export interface GatewayManifest extends GatewayEnvelope {
  /** `recorded_from: LIVE` only says the records came off a running graph; this says who produced them (ICD §6.1). Absent in older packages. */
  recorded_from: string;
  source_mode?: string;
  clock_source: 'sim' | 'system';
  time_start_sim_s: number;
  record_count: number;
  event_count: number;
  terrain_meta: WithHeader<TerrainMeta> & { nodata_value: number | null };
  agents: Array<{ agent_id: string; agent_kind: string }>;
  files: { timeline: string; snapshot?: string; public_rasters?: string };
}

type WireMissionState = Omit<WithHeader<MissionState>, 'agents' | 'active_route'> & {
  active_route?: WithHeader<RouteDecision> | null;
  agents: WithHeader<AgentState>[];
};

export interface GatewaySnapshot extends GatewayEnvelope {
  mission_state: WireMissionState | null;
  events: WithHeader<MissionEvent>[];
  terrain_meta: GatewayManifest['terrain_meta'] | null;
}

/** Public raster attachment of a recorded run (docs/REPLAY_CONTRACT.md, `mge-public-rasters-1.0.0`). */
export interface PublicRasters {
  schema_version: string;
  run_id: string;
  dataset_id: string;
  rows: number;
  cols: number;
  terrain_geometry: Record<string, unknown>;
  prior: (number | null)[];
  versions: Record<string, { belief: (number | null)[]; sigma: (number | null)[]; observed: number[]; impassable?: number[] }>;
}

export const PUBLIC_RASTERS_SCHEMA = 'mge-public-rasters-1.0.0';
/** TerrainMeta fields the attachment's geometry must repeat exactly. */
const GEOMETRY_FIELDS = ['dataset_id', 'rows', 'cols', 'origin_x_m', 'origin_y_m', 'resolution_m', 'crs', 'origin_lat_deg', 'origin_lon_deg', 'vertical_datum'] as const;

export type GatewayRecord = GatewayEnvelope & (
  | { type: 'terrain_meta'; terrain_meta: GatewayManifest['terrain_meta'] }
  | { type: 'state'; state: WireMissionState }
  | { type: 'event'; event: WithHeader<MissionEvent> }
);

/** A gateway package has a JSON Lines timeline and an optional public attachment. */
export function isGatewayManifest(m: unknown): m is GatewayManifest {
  const x = m as Partial<GatewayManifest> & { files?: Record<string, string> };
  return !!x && typeof x.time_start_sim_s === 'number' && typeof x.files?.timeline === 'string' && x.files.timeline.endsWith('.jsonl');
}

export function parseJsonLines(text: string): GatewayRecord[] {
  return text
    .split(/\r?\n/)
    .filter((l) => l.trim() !== '')
    .map((l, i) => {
      try {
        return JSON.parse(l) as GatewayRecord;
      } catch {
        throw new ReplayLoadError(`timeline line ${i + 1} is not valid JSON.`);
      }
    });
}

const stampToS = (h: Header | undefined, fallback: number) => (h?.stamp ? h.stamp.sec + h.stamp.nanosec * 1e-9 : fallback);

function terrainMeta(t: GatewayManifest['terrain_meta']): TerrainMeta {
  const { header, ...rest } = t;
  // A MOCK grid has no georeference: its 0/0 origin must not be shown as 0°N 0°E.
  const mock = /^MOCK$/i.test(rest.crs);
  return {
    ...rest,
    frame_id: 'map',
    origin_lat_deg: mock ? null : rest.origin_lat_deg,
    origin_lon_deg: mock ? null : rest.origin_lon_deg,
  };
}

/** An empty route (no route yet) is recorded with an empty route_id. */
function route(r: WithHeader<RouteDecision> | null | undefined, t0: number, fallback: number): RouteDecision | undefined {
  if (!r || !r.route_id) return undefined;
  const { header, ...rest } = r;
  return { ...rest, timestamp_sim_s: stampToS(header, fallback) - t0 };
}

/** What the viewer may say about a recording, by who produced it. None of them is a live mission. */
const SOURCE_DISCLAIMER: Record<SourceMode, string> = {
  MOCK: 'Recorded replay with MOCK providers; agent execution or mission authority may be simulated. Not a validated live mission.',
  SIMULATION: 'Recorded replay of a simulation run: simulated producers, not a validated live mission.',
  UNKNOWN: 'Recorded replay; the package does not say who produced the data (source UNKNOWN). Not a validated live mission.',
};

/** True when any key, at any depth, names an evaluator or reference layer. */
function hasReferenceKey(x: unknown): boolean {
  if (!x || typeof x !== 'object') return false;
  if (Array.isArray(x)) return x.some(hasReferenceKey);
  return Object.entries(x as Record<string, unknown>).some(([k, v]) => /reference|evaluator/i.test(k) || hasReferenceKey(v));
}

const isCell = (v: unknown) => v === null || (typeof v === 'number' && Number.isFinite(v));

function need(condition: unknown, code: string): asserts condition {
  if (!condition) throw new ReplayLoadError(code);
}

const isObject = (x: unknown): x is Record<string, unknown> => !!x && typeof x === 'object' && !Array.isArray(x);
const finite = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x);
const uint = (x: unknown): x is number => typeof x === 'number' && Number.isSafeInteger(x) && x >= 0;

/** Equality ignores object-key order, never array order or missing fields. */
function equal(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (Array.isArray(a) || Array.isArray(b)) {
    return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((v, i) => equal(v, b[i]));
  }
  if (!isObject(a) || !isObject(b)) return false;
  const keys = Object.keys(a);
  return keys.length === Object.keys(b).length && keys.every((key) => Object.hasOwn(b, key) && equal(a[key], b[key]));
}

function publicJson(value: unknown): void {
  need(!hasReferenceKey(value), 'EVALUATOR_REFERENCE_FORBIDDEN');
  const visit = (x: unknown): void => {
    if (typeof x === 'number') need(Number.isFinite(x), 'NON_JSON_NUMBER');
    else if (Array.isArray(x)) x.forEach(visit);
    else if (isObject(x)) Object.values(x).forEach(visit);
  };
  visit(value);
}

function envelope(value: unknown, run: string): asserts value is GatewayEnvelope {
  need(isObject(value), 'ENVELOPE_OBJECT_REQUIRED');
  need(value.schema_version === '1.0.0', 'UNSUPPORTED_SCHEMA');
  need(typeof run === 'string' && run.length > 0 && value.run_id === run, 'RUN_MISMATCH');
  need(value.mode === 'REPLAY', 'REPLAY_MODE_REQUIRED');
  need(finite(value.timestamp_sim_s), 'INVALID_CLOCK');
  need(uint(value.map_version), 'INVALID_MAP_VERSION');
}

/** Fixed recorder filenames prevent a manifest from fetching outside its package. */
export function validateGatewayManifest(manifest: GatewayManifest): void {
  need(isObject(manifest), 'ENVELOPE_OBJECT_REQUIRED');
  publicJson(manifest);
  envelope(manifest, manifest.run_id);
  const files = manifest.files;
  need(isObject(files) && files.timeline === 'timeline.jsonl' && files.snapshot === 'snapshot.json'
    && (files.public_rasters === undefined || files.public_rasters === 'public_rasters.json')
    && Object.keys(files).every((key) => ['timeline', 'snapshot', 'public_rasters'].includes(key)), 'UNSUPPORTED_FILE_LAYOUT');
  need(finite(manifest.time_start_sim_s), 'INVALID_START_TIME');
  need(uint(manifest.record_count) && uint(manifest.event_count), 'INVALID_RECORD_COUNT');
  need(manifest.source_mode === undefined || ['MOCK', 'SIMULATION', 'UNKNOWN'].includes(manifest.source_mode),
    `INVALID_SOURCE_MODE: source_mode "${String(manifest.source_mode)}"`);
}

/** Mirrors the Python recorder oracle. Snapshot is mandatory in the file loader;
 * callers converting in-memory records can omit it, without bypassing timeline checks.
 * Late events and states lagging a newer map are valid; corrupt records are rejected.
 */
export function validateGatewayPackage(manifest: GatewayManifest, records: GatewayRecord[], snapshot?: GatewaySnapshot): void {
  validateGatewayManifest(manifest);
  need(Array.isArray(records), 'INVALID_RECORD_TYPE');
  publicJson(records);
  const run = manifest.run_id;
  need(manifest.record_count === records.length, 'RECORD_COUNT_MISMATCH');
  const events: WithHeader<MissionEvent>[] = [];
  const ids = new Set<string>();
  const seqs = new Set<number>();
  const routes = new Map<string, unknown>();
  let lastTime = -Infinity, stateSeq = -1, stateMap = -1, mapVersion = -1;
  let state: WireMissionState | null = null;
  let meta: GatewayManifest['terrain_meta'] | null = null;
  let geometry: unknown = null;
  for (const record of records) {
    envelope(record, run);
    need(record.timestamp_sim_s >= lastTime, 'CLOCK_REGRESSION');
    need(record.map_version >= mapVersion, 'ENVELOPE_MAP_REGRESSION');
    lastTime = record.timestamp_sim_s;
    mapVersion = record.map_version;
    need(['state', 'event', 'terrain_meta'].includes(record.type), 'INVALID_RECORD_TYPE');
    const body = record.type === 'terrain_meta' ? record.terrain_meta : record.type === 'event' ? record.event : record.state;
    need(isObject(body), 'INVALID_RECORD_TYPE');
    need(body.run_id === run, 'PAYLOAD_RUN_MISMATCH');
    if (record.type === 'terrain_meta') {
      const current = record.terrain_meta;
      need(current.header?.frame_id === 'map', 'INVALID_FRAME');
      need(current.map_version === record.map_version, 'META_MAP_MISMATCH');
      const key = GEOMETRY_FIELDS.map((field) => current[field]);
      need(geometry === null || equal(key, geometry), 'GEOMETRY_CHANGE_REQUIRES_NEW_DATASET');
      geometry = key;
      meta = current;
    } else if (record.type === 'event') {
      const event = record.event;
      need(typeof event.event_id === 'string' && event.event_id.length > 0 && !ids.has(event.event_id), 'DUPLICATE_EVENT_ID');
      need(uint(event.seq) && event.seq > 0, 'INVALID_EVENT_SEQ');
      need(!seqs.has(event.seq), 'DUPLICATE_EVENT_SEQ');
      ids.add(event.event_id);
      seqs.add(event.seq);
      events.push(event);
    } else {
      const current = record.state;
      need(uint(current.last_event_seq) && current.last_event_seq >= stateSeq, 'STATE_SEQ_REGRESSION');
      need(uint(current.map_version) && current.map_version >= stateMap, 'STATE_MAP_REGRESSION');
      need(current.map_version <= record.map_version, 'STATE_AHEAD_OF_MAP');
      need(current.header?.frame_id === 'map', 'INVALID_FRAME');
      need(Array.isArray(current.agents), 'INVALID_AGENT_STATE');
      for (const agent of current.agents) {
        need(agent.run_id === run, 'AGENT_RUN_MISMATCH');
        need(['HUMAN', 'ROVER', 'DRONE'].includes(agent.agent_kind), 'INVALID_AGENT_KIND');
        need(agent.agent_kind === 'HUMAN' || agent.oxygen_remaining_l === null, 'NON_HUMAN_OXYGEN_MUST_BE_NULL');
      }
      if (current.route_id) {
        const route = current.active_route;
        need(isObject(route) && route.run_id === run, 'ROUTE_RUN_MISMATCH');
        need(route.route_id === current.route_id, 'ROUTE_ID_MISMATCH');
        need(route.map_version_used === current.map_version, 'STALE_ROUTE');
        need(route.status === 'FEASIBLE', 'ACTIVE_ROUTE_NOT_FEASIBLE');
        const { header: _header, ...content } = route;
        need(!routes.has(current.route_id) || equal(routes.get(current.route_id), content), 'ROUTE_ID_REUSED');
        routes.set(current.route_id, content);
      }
      stateSeq = current.last_event_seq;
      stateMap = current.map_version;
      state = current;
    }
  }
  need(manifest.event_count === events.length, 'EVENT_COUNT_MISMATCH');
  need(equal(manifest.terrain_meta, meta), 'SNAPSHOT_META_MISMATCH');
  need(manifest.map_version === mapVersion, 'FINAL_MAP_MISMATCH');
  need(manifest.timestamp_sim_s === lastTime, 'FINAL_CLOCK_MISMATCH');
  if (snapshot !== undefined) {
    publicJson(snapshot);
    envelope(snapshot, run);
    need(equal(snapshot.mission_state, state), 'SNAPSHOT_STATE_MISMATCH');
    need(equal(snapshot.events, [...events].sort((a, b) => a.seq - b.seq)), 'SNAPSHOT_EVENTS_MISMATCH');
    need(equal(snapshot.terrain_meta, meta), 'SNAPSHOT_META_MISMATCH');
    need(snapshot.map_version === mapVersion, 'FINAL_MAP_MISMATCH');
    need(snapshot.timestamp_sim_s === lastTime, 'FINAL_CLOCK_MISMATCH');
  }
}

/**
 * Checks the public raster attachment against its package and returns the versions to draw.
 * Throws ReplayLoadError (code PUBLIC_RASTERS_INVALID) on any mismatch; nothing is repaired.
 */
export function checkPublicRasters(att: PublicRasters, manifest: GatewayManifest, usedVersions: Iterable<number>, recordedVersions: Iterable<number>): RasterSet['versions'] {
  const fail = (why: string): never => {
    throw new ReplayLoadError(`PUBLIC_RASTERS_INVALID: ${why}`);
  };
  if (!att || typeof att !== 'object') fail('the attachment is not a JSON object.');
  if (att.schema_version !== PUBLIC_RASTERS_SCHEMA) fail(`schema_version is "${String(att.schema_version)}", expected "${PUBLIC_RASTERS_SCHEMA}".`);
  if (hasReferenceKey(att)) fail('it carries an evaluator/reference layer, which a public package must never contain.');
  if (att.run_id !== manifest.run_id) fail(`run_id "${att.run_id}" is not the package run "${manifest.run_id}".`);
  const meta = manifest.terrain_meta as unknown as Record<string, unknown>;
  if (att.dataset_id !== meta.dataset_id) fail(`dataset "${att.dataset_id}" is not the package terrain "${String(meta.dataset_id)}".`);
  if (att.rows !== meta.rows || att.cols !== meta.cols) fail(`grid ${att.rows} x ${att.cols} differs from the package terrain ${String(meta.rows)} x ${String(meta.cols)}.`);
  const geo = att.terrain_geometry ?? {};
  for (const k of GEOMETRY_FIELDS) {
    if (geo[k] !== meta[k]) fail(`terrain_geometry.${k} (${String(geo[k])}) differs from the package TerrainMeta (${String(meta[k])}).`);
  }
  const cells = att.rows * att.cols;
  const grid = (name: string, a: unknown, sigma = false) => {
    if (!Array.isArray(a) || a.length !== cells) fail(`${name} must hold ${cells} cells.`);
    for (const v of a as unknown[]) {
      if (!isCell(v)) fail(`${name} holds a value that is neither a finite number nor null.`);
      if (sigma && typeof v === 'number' && v < 0) fail(`${name} holds a negative value.`);
    }
  };
  grid('prior', att.prior);
  const versions: RasterSet['versions'] = {};
  const recorded = att.versions ?? {};
  const recordedKeys = new Set([...recordedVersions].map(String));
  if (!isObject(recorded)) fail('versions must be a JSON object.');
  for (const [key, layer] of Object.entries(recorded)) {
    if (!recordedKeys.has(key)) fail(`map version ${key} has no recorded TerrainMeta.`);
    grid(`versions.${key}.belief`, layer?.belief);
    grid(`versions.${key}.sigma`, layer?.sigma, true);
    const obs = layer?.observed;
    if (!Array.isArray(obs)) fail(`versions.${key}.observed must be a list of cell indices.`);
    const seen = new Set<number>();
    for (const i of obs) {
      if (!Number.isInteger(i) || i < 0 || i >= cells) fail(`versions.${key}.observed holds ${String(i)}, outside the grid.`);
      if (seen.has(i)) fail(`versions.${key}.observed repeats cell ${i}.`);
      seen.add(i);
    }
    versions[key] = { belief: layer.belief, sigma: layer.sigma, observed: obs };
    // Optional addition to 1.0.0: impassable cells of the same map batch (obstacles, too steep).
    if (layer.impassable !== undefined) {
      const blocked = layer.impassable;
      if (!Array.isArray(blocked)) fail(`versions.${key}.impassable must be a list of cell indices.`);
      const hit = new Set<number>();
      for (const i of blocked) {
        if (!Number.isInteger(i) || i < 0 || i >= cells) fail(`versions.${key}.impassable holds ${String(i)}, outside the grid.`);
        if (hit.has(i)) fail(`versions.${key}.impassable repeats cell ${i}.`);
        hit.add(i);
      }
      versions[key].impassable = blocked;
    }
  }
  for (const v of usedVersions) {
    if (v === 0) continue; // no map received yet: no raster can exist
    if (!versions[String(v)]) fail(`map version ${v} is used by the recorded states but has no rasters (no fallback to another version).`);
  }
  return versions;
}

export function fromGatewayPackage(manifest: GatewayManifest, records: GatewayRecord[], publicRasters?: PublicRasters, snapshot?: GatewaySnapshot): ReplayBundle {
  validateGatewayPackage(manifest, records, snapshot);
  const runId = manifest.run_id;
  const t0 = manifest.time_start_sim_s;
  const mine = records;

  const frames: Array<{ timestamp_sim_s: number; mission_state: MissionState }> = [];
  const events: MissionEvent[] = [];
  const routes = new Map<string, RouteDecision>();
  const metas: TerrainMeta[] = [];

  for (const r of mine) {
    const t = r.timestamp_sim_s - t0;
    if (r.type === 'terrain_meta') metas.push(terrainMeta(r.terrain_meta));
    else if (r.type === 'event') {
      const { header, ...e } = r.event;
      events.push({ ...e, timestamp_sim_s: t });
    } else if (r.type === 'state') {
      const { header, active_route, agents, ...s } = r.state;
      const active = route(active_route, t0, r.timestamp_sim_s);
      if (active) routes.set(active.route_id, active);
      frames.push({
        timestamp_sim_s: t,
        mission_state: {
          ...s,
          timestamp_sim_s: t,
          active_route: active,
          agents: agents.map(({ header: h, ...a }) => ({ ...a, timestamp_sim_s: stampToS(h, r.timestamp_sim_s) - t0 })),
        },
      });
    }
  }
  if (frames.length === 0) throw new ReplayLoadError(`The package of run "${runId}" has no mission state.`);

  const meta = terrainMeta(manifest.terrain_meta);
  const source = resolveSourceMode(manifest.source_mode, meta);
  if (!source) {
    throw new ReplayLoadError(`The package says source_mode "${String(manifest.source_mode)}"; a recording may only say MOCK, SIMULATION or UNKNOWN.`);
  }
  const cells = meta.rows * meta.cols;
  const noData = new Array<number | null>(cells).fill(null);
  const used = new Set(frames.map((f) => f.mission_state.map_version));
  let rasters: RasterSet;
  let illustrativeFlat = false;
  if (publicRasters) {
    const versions = checkPublicRasters(publicRasters, manifest, used, metas.map((m) => m.map_version));
    // Version 0 has no raster by contract; the public prior is drawn until the first map arrives.
    if (used.has(0) && !versions['0']) versions['0'] = { belief: publicRasters.prior, sigma: noData, observed: [] };
    rasters = { run_id: runId, rows: meta.rows, cols: meta.cols, prior: publicRasters.prior, versions };
  } else {
    // No attachment: only a MOCK package over a declared flat grid may be drawn, as an explicit
    // illustrative choice (0 m everywhere, sigma NoData). It is not a recorded raster.
    const flat = /flat/i.test(meta.dataset_id) || meta.sources.some((s) => /flat grid/i.test(s));
    if (source !== 'MOCK' || !flat) {
      throw new ReplayLoadError(
        `PUBLIC_RASTERS_REQUIRED: terrain "${meta.dataset_id}" has no public raster attachment (manifest files.public_rasters), so it cannot be drawn.`,
      );
    }
    illustrativeFlat = true;
    const prior = new Array<number | null>(cells).fill(0);
    const versions: RasterSet['versions'] = {};
    for (const v of new Set([...metas.map((m) => m.map_version), meta.map_version, ...used])) {
      versions[String(v)] = { belief: prior, sigma: noData, observed: [] };
    }
    rasters = { run_id: runId, rows: meta.rows, cols: meta.cols, prior, versions };
  }

  const last = frames[frames.length - 1].mission_state;
  const endT = Math.max(...mine.map((r) => r.timestamp_sim_s - t0));
  const point = (p: Point): Point => ({ x: p.x, y: p.y, z: p.z });

  const viewerManifest: ReplayManifest = {
    schema_version: WEB_SCHEMA_VERSION,
    icd: 'ICD-ROS2-V1 replay package (docs/ICD.md §7)',
    run_id: runId,
    mode: 'REPLAY',
    source_mode: source,
    provenance: source === 'UNKNOWN' ? ['replay'] : ['replay', 'simulated'],
    illustrative: source === 'MOCK',
    title: `Gateway replay ${runId}`,
    summary: `Recorded by the gateway replay_recorder from a ${manifest.recorded_from} run (${manifest.record_count} records, ${manifest.event_count} events).`,
    disclaimer: `${SOURCE_DISCLAIMER[source]} ${
      illustrativeFlat
        ? 'Terrain: illustrative flat MOCK grid (no raster attachment in the package).'
        : `Terrain: recorded public rasters (${PUBLIC_RASTERS_SCHEMA}).`
    } Clock: ${manifest.clock_source === 'system' ? 'wall clock (no simulator)' : 'simulation'}.`,
    duration_s: Math.max(endT, 1),
    terrain_meta: meta,
    vertical_exaggeration_default: 1,
    control_points: [],
    pois: [
      { id: 'base', label: 'Base', kind: 'base', position: point(last.base), revealed_at_s: 0 },
      { id: 'goal', label: 'Goal', kind: 'primary_goal', position: point(last.primary_goal), revealed_at_s: 0 },
    ],
    files: { rasters: '', timeline: manifest.files.timeline, routes: '' },
  };

  return assembleBundle(
    viewerManifest,
    rasters,
    { schema_version: WEB_SCHEMA_VERSION, run_id: runId, frames, events },
    { run_id: runId, routes: [...routes.values()] },
  );
}
