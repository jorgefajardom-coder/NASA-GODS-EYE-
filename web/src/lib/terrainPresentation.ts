import type { TerrainMeta } from '../types/icd';
import type { ReplayManifest, ContextTerrainData } from '../types/replay';
import type { GeologyData } from './geology';

/** Camera coordinates stay in the recorded datum; only the viewpoint is fitted. */
export function terrainFraming(meta: TerrainMeta, heights: ReadonlyArray<number | null>, exaggeration = 1) {
  let lo = Infinity, hi = -Infinity;
  for (const h of heights) if (h !== null && Number.isFinite(h)) {
    lo = Math.min(lo, h);
    hi = Math.max(hi, h);
  }
  if (!Number.isFinite(lo)) lo = hi = 0;
  const width = meta.cols * meta.resolution_m;
  const height = meta.rows * meta.resolution_m;
  const scale = Math.max(width, height, (hi - lo) * exaggeration, 1);
  const target: [number, number, number] = [
    meta.origin_x_m + width / 2,
    (lo + hi) * exaggeration / 2,
    -(meta.origin_y_m + height / 2),
  ];
  const position: [number, number, number] = [target[0] - .75 * scale, target[1] + 1.25 * scale, target[2] + 1.7 * scale];
  return { target, position, scale, far: scale * 12 };
}

/** Read the declared prior spacing, never a MOLA regional-context spacing. */
export function priorNativeSpacing(meta: TerrainMeta): number | null {
  for (const source of meta.sources) {
    if (/\((?:regional_context|evaluation_reference)\)/i.test(source)) continue;
    const match = /\(prior\).*?\[([\d.]+)\s*m[,\]]/i.exec(source)
      ?? /native (?:resolution|post spacing)\s*:?\s*([\d.]+)\s*m\b/i.exec(source);
    if (match) {
      const value = Number(match[1]);
      if (Number.isFinite(value) && value > 0) return value;
    }
  }
  return null;
}

export function terrainResolutionLabel(meta: TerrainMeta): string {
  const native = priorNativeSpacing(meta);
  return `Grid ${meta.resolution_m} m · source ${native === null ? 'spacing not supplied' : `${native} m native`}`;
}

export const ORBITAL_PREVIEW_LABEL = 'Orbital slope preview';
export const ORBITAL_PREVIEW_LIMIT = 'Display only: no new observation; map, uncertainty and route remain unchanged.';

export function orbitalSlopeNote(meta: TerrainMeta): string {
  return `${terrainResolutionLabel(meta)}. Horn 3×3 derivative (${3 * meta.resolution_m} m computational window); resampling adds no source detail. Not a local hazard measurement; colour bands are display thresholds.`;
}

const close = (a: number | undefined | null, b: number | undefined | null) =>
  typeof a === 'number' && typeof b === 'number' && Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) <= 1e-6;

/** The historical geology file has no independent planetary origin. Limit that
 * compatibility case to its original declared crop; new scenes need binding.
 */
export function geologyMatchesRun(data: GeologyData, manifest: ReplayManifest): boolean {
  const meta = manifest.terrain_meta;
  const f = data.frame;
  if (!close(f.origin_x_m, meta.origin_x_m) || !close(f.origin_y_m, meta.origin_y_m)
      || !close(f.width_m, meta.cols * meta.resolution_m) || !close(f.height_m, meta.rows * meta.resolution_m)) return false;
  if (f.dataset_id !== undefined) {
    return f.dataset_id === meta.dataset_id && close(f.origin_lat_deg, meta.origin_lat_deg)
      && close(f.origin_lon_deg, meta.origin_lon_deg) && f.vertical_datum === meta.vertical_datum;
  }
  return manifest.run_id === 'demo-sim-002' && meta.dataset_id === 'mars2020-trn-ctx-dtm-20m'
    && close(meta.origin_lat_deg, 18.53545) && close(meta.origin_lon_deg, 77.42382)
    && manifest.local_z_offset_m === -2495;
}

/** Context is a separate surface: require its datum, planetary origin, source
 * and coverage to match before drawing it around another run.
 */
export function contextMatchesRun(data: ContextTerrainData, manifest: ReplayManifest): boolean {
  const meta = manifest.terrain_meta;
  const f = data.frame;
  if (!close(f.local_z_offset_m, manifest.local_z_offset_m ?? 0)
      || !close(f.centre_lat_deg, meta.origin_lat_deg) || !close(f.centre_lon_deg, meta.origin_lon_deg)
      || !Number.isInteger(f.rows) || f.rows <= 0 || !Number.isInteger(f.cols) || f.cols <= 0
      || !Number.isFinite(f.resolution_m) || f.resolution_m <= 0
      || data.heights.length !== f.rows * f.cols || f.row0 !== 'south'
      || !data.heights.every((h) => h === null || (typeof h === 'number' && Number.isFinite(h)))) return false;
  const hash = data.source?.sha256;
  if (!hash || !meta.sources.some((source) => source.toLowerCase().includes(hash.toLowerCase()))) return false;
  return f.origin_x_m <= meta.origin_x_m && f.origin_y_m <= meta.origin_y_m
    && f.origin_x_m + f.cols * f.resolution_m >= meta.origin_x_m + meta.cols * meta.resolution_m
    && f.origin_y_m + f.rows * f.resolution_m >= meta.origin_y_m + meta.rows * meta.resolution_m;
}
