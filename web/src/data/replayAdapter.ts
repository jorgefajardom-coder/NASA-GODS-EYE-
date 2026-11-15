import { WEB_SCHEMA_VERSION } from '../types/icd';
import type { RouteDecision } from '../types/icd';
import type { GeologyData } from '../lib/geology';
import { parseAtmosphere } from '../lib/atmos';
import type { ContextTerrainData, RasterSet, ReplayBundle, ReplayManifest, ReplayRoutes, ReplayTimeline } from '../types/replay';
import { normalizeEvents } from '../lib/replay';
import { resolveSourceMode } from '../lib/provenance';
import { contextMatchesRun, geologyMatchesRun } from '../lib/terrainPresentation';
import { fromGatewayPackage, isGatewayManifest, parseJsonLines, validateGatewayManifest, type GatewaySnapshot, type PublicRasters } from './gatewayReplay';

/** Runs offered in the viewer. `dir` is relative to the site under replay/. */
export const RECORDED_RECOVERY_ENTRY = 'recorded-recovery-001';
export const DEFAULT_RUN_ENTRY = RECORDED_RECOVERY_ENTRY;
export const RUNS: ReadonlyArray<{ id: string; label: string; note?: string }> = [
  { id: RECORDED_RECOVERY_ENTRY, label: 'Recorded recovery · MOCK', note: 'Recorder output: human stop, replan and return. Rover and drone remain idle. Not a scientific COMPLETE mission.' },
  { id: 'demo', label: 'Illustrative demo · generated story' },
  { id: 'mock-vertical-001', label: 'Gateway replay mock-vertical-001 (MOCK)' },
];

/**
 * Runs offered in the selector: only the documented standard entry (DEFAULT_RUN_ENTRY). The other
 * catalogue entries stay loadable with ?run=<id> for tests and review, but are not offered.
 */
export const OFFERED_RUNS = RUNS.filter((run) => run.id === DEFAULT_RUN_ENTRY);

export class ReplayLoadError extends Error {}

/** Resolves a path relative to the deployed site, never to the domain root. */
export function assetUrl(path: string): string {
  const base = import.meta.env.BASE_URL ?? './';
  return `${base.endsWith('/') ? base : `${base}/`}${path.replace(/^\/+/, '')}`;
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new ReplayLoadError(`Could not load ${url} (HTTP ${res.status}).`);
  return (await res.json()) as T;
}

/**
 * Checks the contract rules the viewer depends on and returns a consistent bundle.
 * Objects of another run_id are rejected instead of being mixed in.
 */
export function assembleBundle(
  manifest: ReplayManifest,
  rasters: RasterSet,
  timeline: ReplayTimeline,
  routes: ReplayRoutes,
): ReplayBundle {
  if (manifest.schema_version !== WEB_SCHEMA_VERSION) {
    throw new ReplayLoadError(
      `Unsupported schema_version "${manifest.schema_version}" (viewer expects "${WEB_SCHEMA_VERSION}").`,
    );
  }
  const runId = manifest.run_id;
  for (const [name, obj] of [
    ['rasters', rasters],
    ['timeline', timeline],
    ['routes', routes],
  ] as const) {
    if (obj.run_id !== runId) throw new ReplayLoadError(`${name} belongs to run "${obj.run_id}", expected "${runId}".`);
  }
  const meta = manifest.terrain_meta;
  const source = resolveSourceMode(manifest.source_mode, meta);
  if (!source) {
    throw new ReplayLoadError(`source_mode "${String(manifest.source_mode)}" is not allowed in a recording (MOCK, SIMULATION or UNKNOWN; LIVE cannot be declared).`);
  }
  manifest = { ...manifest, source_mode: source };
  if (rasters.rows !== meta.rows || rasters.cols !== meta.cols || rasters.prior.length !== meta.rows * meta.cols) {
    throw new ReplayLoadError('Raster size does not match TerrainMeta rows × cols.');
  }
  const frames = timeline.frames
    .filter((f) => f.mission_state.run_id === runId)
    .sort((a, b) => a.timestamp_sim_s - b.timestamp_sim_s);
  const routeMap = new Map<string, RouteDecision>();
  for (const r of routes.routes) if (r.run_id === runId) routeMap.set(r.route_id, r);
  return {
    manifest,
    rasters,
    timeline: { ...timeline, frames, events: normalizeEvents(timeline.events, runId) },
    routes: routeMap,
  };
}

/**
 * Evaluator view only: asks the dev server for the run's hidden reference, kept outside the
 * public site in data/reference/ (R05). A production build has no such file, so this
 * returns null and the reference layer is not offered.
 */
export async function loadEvaluatorReference(runId: string, rows: number, cols: number): Promise<(number | null)[] | null> {
  try {
    const res = await fetch(assetUrl(`evaluator/${encodeURIComponent(runId)}/reference.json`));
    if (!res.ok || !(res.headers.get('content-type') ?? '').includes('json')) return null;
    const j = (await res.json()) as { run_id?: string; reference?: (number | null)[] };
    if (j.run_id !== runId || !Array.isArray(j.reference) || j.reference.length !== rows * cols) return null;
    return j.reference;
  } catch {
    return null;
  }
}

/** ReplayAdapter: loads a saved run from static files (no ROS, no gateway, no network). */
export async function loadReplay(runDir: string): Promise<ReplayBundle> {
  const dir = runDir.replace(/\/+$/, '');
  const raw = await getJson<unknown>(assetUrl(`${dir}/manifest.json`));
  if (isGatewayManifest(raw)) {
    validateGatewayManifest(raw);
    const url = assetUrl(`${dir}/${raw.files.timeline}`);
    const res = await fetch(url);
    if (!res.ok) throw new ReplayLoadError(`Could not load ${url} (HTTP ${res.status}).`);
    // The public raster attachment is read whenever the manifest names it (files.public_rasters).
    const named = raw.files.public_rasters;
    const rasters = named ? await getJson<PublicRasters>(assetUrl(`${dir}/${named}`)) : undefined;
    const snapshot = await getJson<GatewaySnapshot>(assetUrl(`${dir}/${raw.files.snapshot}`));
    return fromGatewayPackage(raw, parseJsonLines(await res.text()), rasters, snapshot);
  }
  const manifest = raw as ReplayManifest;
  const [rasters, timeline, routes] = await Promise.all([
    getJson<RasterSet>(assetUrl(`${dir}/${manifest.files.rasters}`)),
    getJson<ReplayTimeline>(assetUrl(`${dir}/${manifest.files.timeline}`)),
    getJson<ReplayRoutes>(assetUrl(`${dir}/${manifest.files.routes}`)),
  ]);
  const bundle = assembleBundle(manifest, rasters, timeline, routes);
  if (manifest.geology) {
    // Optional layer: the run still opens if it is missing.
    try {
      const geology = await getJson<GeologyData>(assetUrl(`${dir}/${manifest.geology.file}`));
      if (geologyMatchesRun(geology, manifest)) bundle.geology = geology;
    } catch {
      /* the Ground layers tab then says no geology is available */
    }
  }
  if (manifest.atmosphere) {
    // Optional layer: the run still opens if it is missing or malformed.
    try {
      bundle.atmosphere = parseAtmosphere(await getJson<unknown>(assetUrl(`${dir}/${manifest.atmosphere.file}`))) ?? undefined;
    } catch {
      /* the Atmos tab then says no data is available */
    }
  }
  if (manifest.context) {
    // Optional surroundings: the run still opens without them.
    try {
      const ctx = await getJson<ContextTerrainData>(assetUrl(`${dir}/${manifest.context.file}`));
      if (contextMatchesRun(ctx, manifest)) bundle.context = ctx;
    } catch {
      /* the crop is drawn alone */
    }
  }
  return bundle;
}
