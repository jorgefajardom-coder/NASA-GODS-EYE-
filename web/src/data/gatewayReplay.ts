import type { AgentState, MissionEvent, MissionState, Point, RouteDecision, TerrainMeta } from '../types/icd';
import type { RasterSet, ReplayBundle, ReplayManifest } from '../types/replay';
import { WEB_SCHEMA_VERSION } from '../types/icd';
import { assembleBundle, ReplayLoadError } from './replayAdapter';

/**
 * Reads a replay package written by the gateway's replay_recorder (docs/ICD.md §7,
 * e.g. data/sample/replay/mock-vertical-001) and turns it into the viewer's bundle.
 *
 * The package is used as recorded: nothing is added to the mission. What the package
 * does not contain is shown as missing, not invented:
 *  - no rasters travel in the package (ICD §7). The heights come only from the terrain
 *    declared by TerrainMeta; for the MOCK flat grid that is 0 m everywhere. Sigma and
 *    the hidden evaluator reference are NoData.
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
  recorded_from: string;
  clock_source: 'sim' | 'system';
  time_start_sim_s: number;
  record_count: number;
  event_count: number;
  terrain_meta: WithHeader<TerrainMeta> & { nodata_value: number | null };
  agents: Array<{ agent_id: string; agent_kind: string }>;
  files: { timeline: string; snapshot?: string };
}

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

export function fromGatewayPackage(manifest: GatewayManifest, records: GatewayRecord[]): ReplayBundle {
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
  const cells = meta.rows * meta.cols;
  const flat = /flat/i.test(meta.dataset_id) || meta.sources.some((s) => /flat grid/i.test(s));
  if (!flat) {
    throw new ReplayLoadError(`Terrain "${meta.dataset_id}" is not in the package (ICD §7: rasters are not recorded yet).`);
  }
  // The declared terrain is a flat synthetic grid at 0 m; nothing else is known.
  const prior = new Array<number | null>(cells).fill(0);
  const noData = new Array<number | null>(cells).fill(null);
  const versions: RasterSet['versions'] = {};
  for (const v of new Set([...metas.map((m) => m.map_version), meta.map_version, ...frames.map((f) => f.mission_state.map_version)])) {
    versions[String(v)] = { belief: prior, sigma: noData, observed: [] };
  }
  const rasters: RasterSet = { run_id: runId, rows: meta.rows, cols: meta.cols, prior, reference: noData, versions };

  const last = frames[frames.length - 1].mission_state;
  const endT = Math.max(...mine.map((r) => r.timestamp_sim_s - t0));
  const point = (p: Point): Point => ({ x: p.x, y: p.y, z: p.z });

  const viewerManifest: ReplayManifest = {
    schema_version: WEB_SCHEMA_VERSION,
    icd: 'ICD-ROS2-V1 replay package (docs/ICD.md §7)',
    run_id: runId,
    mode: 'REPLAY',
    provenance: ['replay', 'simulated'],
    illustrative: true,
    title: `Gateway replay ${runId}`,
    summary: `Recorded by the gateway replay_recorder from a ${manifest.recorded_from} run (${manifest.record_count} records, ${manifest.event_count} events).`,
    disclaimer: `Recorded replay of MOCK producers: flat synthetic grid, straight-line MOCK planner, no Mars data. Clock: ${manifest.clock_source === 'system' ? 'wall clock (no simulator)' : 'simulation'}.`,
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
