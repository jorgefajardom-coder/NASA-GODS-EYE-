import { WEB_SCHEMA_VERSION } from '../types/icd';
import type { RouteDecision } from '../types/icd';
import type { RasterSet, ReplayBundle, ReplayManifest, ReplayRoutes, ReplayTimeline } from '../types/replay';
import { normalizeEvents } from '../lib/replay';

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

/** ReplayAdapter: loads a saved run from static files (no ROS, no gateway, no network). */
export async function loadReplay(runDir: string): Promise<ReplayBundle> {
  const dir = runDir.replace(/\/+$/, '');
  const manifest = await getJson<ReplayManifest>(assetUrl(`${dir}/manifest.json`));
  const [rasters, timeline, routes] = await Promise.all([
    getJson<RasterSet>(assetUrl(`${dir}/${manifest.files.rasters}`)),
    getJson<ReplayTimeline>(assetUrl(`${dir}/${manifest.files.timeline}`)),
    getJson<ReplayRoutes>(assetUrl(`${dir}/${manifest.files.routes}`)),
  ]);
  return assembleBundle(manifest, rasters, timeline, routes);
}
