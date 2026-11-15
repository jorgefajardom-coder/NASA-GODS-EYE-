import type { MissionEvent, MissionState, Point, RouteDecision, TerrainMeta } from './icd';
import type { GeologyData } from '../lib/geology';
import type { SourceMode } from '../lib/provenance';
import type { AtmosphereData } from '../lib/atmos';

/**
 * Replay fixture layout (proposal for Jesús; the gateway snapshot format is not frozen).
 * Files live next to each other under public/replay/<run>/ and are fetched with
 * relative URLs, so the same build works without ROS, Gazebo or a network.
 */

/** Provenance of the data shown, displayed to the user. */
export type Provenance = 'simulated' | 'replay' | 'nasa' | 'fictitious';

export interface ControlPoint {
  id: string;
  /** Frame `map` (ENU). `z` is the expected terrain height in metres. */
  position: Point;
  description: string;
}

export interface PointOfInterest {
  id: string;
  label: string;
  kind: 'base' | 'primary_goal' | 'poi' | 'science' | 'landmark' | 'landing';
  position: Point;
  /** Simulated time at which the POI becomes known. Base and goal are known from t=0. */
  revealed_at_s: number;
}

export interface ReplayManifest {
  schema_version: string;
  icd: string;
  run_id: string;
  mode: 'REPLAY';
  /**
   * Who produced the data (ICD §6.1). Optional in JSON 1.0.0: older manifests lack it and are
   * shown as UNKNOWN unless their terrain says MOCK. assembleBundle always fills it in.
   */
  source_mode?: SourceMode;
  provenance: Provenance[];
  illustrative: boolean;
  /** Where AI assistance was used in this fixture (competition transparency rule). */
  ai_disclosure?: { ai_assisted: boolean; scope: string; tool: string; observational_data: string };
  title: string;
  summary: string;
  disclaimer: string;
  duration_s: number;
  /** Local z = source elevation - this offset (m). Lets the viewer draw contour lines at true elevations. */
  local_z_offset_m?: number;
  terrain_meta: TerrainMeta;
  /** Orbital image draped on the terrain (part of the orbital prior). Image row 0 = north edge. */
  imagery?: {
    file: string;
    title: string;
    source: string;
    credit: string;
    native_resolution_m: number;
    resolution_m: number;
    extent: { origin_x_m: number; origin_y_m: number; width_m: number; height_m: number };
    row0: 'north';
    /** How the stored image was derived from the source, shown in the credits. */
    processing: string;
  };
  /** Geologic units of the run area (USGS SIM 3464), drawn in the Ground layers tab. */
  geology?: { file: string };
  /** Atmosphere and radiation context (scripts/extract-atmosphere.mjs), drawn in the Atmos tab. */
  atmosphere?: { file: string };
  /** Surroundings of the crop from the same DTM, coarser (scripts/extract-ctx-context.mjs). Context only. */
  context?: { file: string; image?: string };
  /** Real Perseverance stops inside the crop (scripts/extract-rover-waypoints.mjs): position and identifiers only. */
  rover_stops?: { file: string };
  vertical_exaggeration_default: number;
  control_points: ControlPoint[];
  pois: PointOfInterest[];
  files: {
    rasters: string;
    timeline: string;
    routes: string;
  };
}

/** Flat row-major grids, row 0 = south (ICD §1). `null` = NoData. */
export interface RasterSet {
  run_id: string;
  rows: number;
  cols: number;
  prior: (number | null)[];
  /**
   * Hidden reference DEM. Never part of a public fixture (R05): only the dev server's
   * evaluator view attaches it, from the repository's ignored data/reference/ boundary.
   */
  reference?: (number | null)[];
  /** One belief/sigma pair per map_version. */
  versions: Record<string, { belief: (number | null)[]; sigma: (number | null)[]; observed: number[] }>;
}

export interface ReplayFrame {
  timestamp_sim_s: number;
  mission_state: MissionState;
}

export interface ReplayTimeline {
  schema_version: string;
  run_id: string;
  frames: ReplayFrame[];
  events: MissionEvent[];
}

export interface ReplayRoutes {
  run_id: string;
  routes: RouteDecision[];
}

export interface ReplayBundle {
  manifest: ReplayManifest;
  rasters: RasterSet;
  timeline: ReplayTimeline;
  routes: Map<string, RouteDecision>;
  /** Present when the manifest declares a geology file and it loaded. */
  geology?: GeologyData;
  /** Present when the manifest declares an atmosphere file and it loaded and validated. */
  atmosphere?: AtmosphereData;
  /** Present when the manifest declares a context terrain and it loaded. */
  context?: ContextTerrainData;
  /** Present when the manifest declares rover stops and they loaded. */
  roverStops?: RoverStops;
}

/** A real Perseverance stop (NASA MMGIS waypoint) in the run's local ENU frame. `rmc` is `<site>_<drive>`. */
export interface RoverStop {
  rmc: string;
  site: number;
  drive: number;
  sol: number;
  lat_deg: number;
  lon_deg: number;
  x_m: number;
  y_m: number;
  z_m: number;
}

export interface RoverStops {
  note: string;
  source: { title: string; url: string; credit: string; retrieved?: string };
  base_stop: string | null;
  goal_stop: string | null;
  stops: RoverStop[];
}

/** Context terrain around the crop: local ENU heights (row 0 = south, null = NoData). */
export interface ContextTerrainData {
  note: string;
  source?: { sha256?: string };
  frame: { origin_x_m: number; origin_y_m: number; resolution_m: number; rows: number; cols: number; local_z_offset_m: number; centre_lat_deg?: number; centre_lon_deg?: number; row0?: string };
  heights: (number | null)[];
}
