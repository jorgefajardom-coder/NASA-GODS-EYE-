/**
 * Web mirror of ICD-ROS2-V1 (draft, owned by Jesús in docs/ICD.md on dev/jesus).
 *
 * Field names are the ROS field names unchanged (ICD §5). Differences that only
 * exist because of JSON:
 *  - ROS `NaN` (e.g. oxygen for non-human agents) is `null` in JSON.
 *  - `std_msgs/Header` is flattened to `timestamp_sim_s` (simulated time, s).
 *  - Points are `{ x, y, z }` in frame `map`: x east, y north, z up, metres.
 *
 * The viewer only consumes these objects. It never plans routes.
 */

export const WEB_SCHEMA_VERSION = 'mge-web-0.1-draft';

export type Mode = 'LIVE' | 'REPLAY';

/** ICD-WEB-V1 envelope proposed by the shared scaffold. Null identifiers mean no run is loaded. */
export interface RunEnvelope {
  schema_version: '1.0.0';
  run_id: string | null;
  mode: Mode | null;
  map_version: number | null;
  timestamp_sim_s: number | null;
}

export interface UnavailableResponse extends RunEnvelope {
  status: 'NOT_READY' | 'ERROR';
  reason_code: string;
}

export interface Point {
  x: number;
  y: number;
  z: number;
}

export interface Quaternion {
  x: number;
  y: number;
  z: number;
  w: number;
}

export interface Pose {
  position: Point;
  orientation: Quaternion;
}

export type AgentKind = 'HUMAN' | 'DRONE' | 'ROVER';
export type AgentMode = 'IDLE' | 'MOVING' | 'OBSERVING' | 'WORKING' | 'RETURNING' | 'HALTED';

export interface AgentState {
  timestamp_sim_s: number;
  run_id: string;
  agent_id: string;
  agent_kind: AgentKind;
  pose: Pose;
  mode: AgentMode;
  time_remaining_s: number | null;
  energy_remaining_wh: number | null;
  oxygen_remaining_l: number | null;
  confidence: number | null;
}

export type RouteStatus =
  | 'FEASIBLE'
  | 'UNKNOWN'
  | 'NO_PATH'
  | 'INSUFFICIENT_BUDGET'
  | 'STALE_MAP'
  | 'ERROR';

export type RouteMode = 'FAST' | 'EFFICIENT' | 'SAFE';

export interface RouteDecision {
  timestamp_sim_s: number;
  run_id: string;
  request_id: string;
  route_id: string;
  agent_id: string;
  mode: RouteMode;
  map_version_used: number;
  status: RouteStatus;
  reason_code: string;
  detail: string;
  outbound_path: Point[];
  return_path: Point[];
  travel_time_s: number | null;
  energy_est_wh: number | null;
  oxygen_est_l: number | null;
  min_clearance_m: number | null;
  reserve_time_s: number | null;
  reserve_wh: number | null;
  reserve_oxygen_l: number | null;
}

export type MissionStateName =
  | 'IDLE'
  | 'PLANNING'
  | 'READY'
  | 'ACTIVE'
  | 'REPLAN'
  | 'RETURNING'
  | 'COMPLETE'
  | 'BLOCKED'
  | 'ABORTED';

export type TaskState = 'DISCOVERED' | 'ELIGIBLE' | 'ASSIGNED' | 'EXECUTING' | 'DONE' | 'REJECTED' | 'BLOCKED';

export interface MissionState {
  timestamp_sim_s: number;
  run_id: string;
  last_event_seq: number;
  mission_state: MissionStateName;
  reason_code: string;
  base: Point;
  primary_goal: Point;
  primary_agent_id: string;
  active_task_id: string;
  active_task_kind: string;
  active_task_state: TaskState | '';
  map_version: number;
  route_id: string;
  /** Embedded in ROS. Replay fixtures may omit it and reference `route_id` instead. */
  active_route?: RouteDecision;
  agents: AgentState[];
}

export type MissionEventType =
  | 'MISSION_STATE_CHANGED'
  | 'GOAL_ACCEPTED'
  | 'GOAL_REJECTED'
  | 'MAP_UPDATED'
  | 'ROUTE_PUBLISHED'
  | 'ROUTE_INVALIDATED'
  | 'TASK_DISCOVERED'
  | 'TASK_STATE_CHANGED'
  | 'ERROR';

export interface MissionEvent {
  timestamp_sim_s: number;
  event_id: string;
  seq: number;
  run_id: string;
  causality_id: string;
  event_type: MissionEventType;
  task_id: string;
  agent_id: string;
  map_version: number;
  route_id: string;
  previous_state: string;
  new_state: string;
  reason_code: string;
  detail: string;
}

export interface TerrainMeta {
  run_id: string;
  dataset_id: string;
  frame_id: 'map';
  map_version: number;
  origin_x_m: number;
  origin_y_m: number;
  resolution_m: number;
  rows: number;
  cols: number;
  crs: string;
  /** null (ROS NaN) when the terrain has no georeference, e.g. a synthetic placeholder. */
  origin_lat_deg: number | null;
  origin_lon_deg: number | null;
  vertical_datum: string;
  nodata_value: number;
  sources: string[];
  checksum_sha256: string;
}
