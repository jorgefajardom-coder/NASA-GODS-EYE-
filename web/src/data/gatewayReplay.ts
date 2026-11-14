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

export interface GatewayManifest {
  schema_version: string;
  run_id: string;
  mode: 'REPLAY';
  map_version: number;
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

/** Public raster attachment of a recorded run (docs/REPLAY_CONTRACT.md, `mge-public-rasters-1.0.0`). */
export interface PublicRasters {
  schema_version: string;
  run_id: string;
  dataset_id: string;
  rows: number;
  cols: number;
  terrain_geometry: Record<string, unknown>;
  prior: (number | null)[];
  versions: Record<string, { belief: (number | null)[]; sigma: (number | null)[]; observed: number[] }>;
}

export const PUBLIC_RASTERS_SCHEMA = 'mge-public-rasters-1.0.0';
/** TerrainMeta fields the attachment's geometry must repeat exactly. */
const GEOMETRY_FIELDS = ['dataset_id', 'rows', 'cols', 'origin_x_m', 'origin_y_m', 'resolution_m', 'crs', 'origin_lat_deg', 'origin_lon_deg', 'vertical_datum'] as const;

type GatewayRecord =
  | { type: 'terrain_meta'; timestamp_sim_s: number; run_id: string; terrain_meta: GatewayManifest['terrain_meta'] }
  | { type: 'state'; timestamp_sim_s: number; run_id: string; state: Omit<WithHeader<MissionState>, 'agents' | 'active_route'> & { active_route?: WithHeader<RouteDecision> | null; agents: WithHeader<AgentState>[] } }
  | { type: 'event'; timestamp_sim_s: number; run_id: string; event: WithHeader<MissionEvent> };

/** A gateway package has a JSON Lines timeline and no raster file. */
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
  MOCK: 'Recorded replay of MOCK producers: flat synthetic grid, straight-line MOCK planner, no Mars data.',
  SIMULATION: 'Recorded replay of a simulation run: simulated producers, not a validated live mission.',
  UNKNOWN: 'Recorded replay; the package does not say who produced the data (source UNKNOWN). Not a validated live mission.',
};

/** True when any key, at any depth, names an evaluator or reference layer. */
function hasReferenceKey(x: unknown): boolean {
  if (!x || typeof x !== 'object') return false;
  if (Array.isArray(x)) return false; // raster arrays hold numbers only
  return Object.entries(x as Record<string, unknown>).some(([k, v]) => /reference|evaluator/i.test(k) || hasReferenceKey(v));
}

const isCell = (v: unknown) => v === null || (typeof v === 'number' && Number.isFinite(v));

/**
 * Checks the public raster attachment against its package and returns the versions to draw.
 * Throws ReplayLoadError (code PUBLIC_RASTERS_INVALID) on any mismatch; nothing is repaired.
 */
export function checkPublicRasters(att: PublicRasters, manifest: GatewayManifest, usedVersions: Iterable<number>): RasterSet['versions'] {
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
  for (const [key, layer] of Object.entries(recorded)) {
    if (!/^\d+$/.test(key)) fail(`version key "${key}" is not a map version number.`);
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
  }
  for (const v of usedVersions) {
    if (v === 0) continue; // no map received yet: no raster can exist
    if (!versions[String(v)]) fail(`map version ${v} is used by the recorded states but has no rasters (no fallback to another version).`);
  }
  return versions;
}

export function fromGatewayPackage(manifest: GatewayManifest, records: GatewayRecord[], publicRasters?: PublicRasters): ReplayBundle {
  if (manifest.mode !== 'REPLAY') throw new ReplayLoadError('A recorded package must say mode "REPLAY".');
  const runId = manifest.run_id;
  const t0 = manifest.time_start_sim_s;
  const mine = records.filter((r) => r.run_id === runId);

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
    const versions = checkPublicRasters(publicRasters, manifest, used);
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
