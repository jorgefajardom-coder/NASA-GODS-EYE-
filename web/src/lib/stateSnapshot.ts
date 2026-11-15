import type { ReplayBundle } from '../types/replay';
import { terrainResolutionLabel } from './terrainPresentation';
import type { ReplayView } from './replay';
import { displayState } from './provenance';
import { yawFromQuaternion } from './coords';
import { headingFromNorth } from './management';

/** What the viewer currently shows, in plain JSON for language models and test agents. */
export interface StateSnapshot {
  schema: 'mge.viewer-state/1';
  /** Always a replay of recorded data; never a live mission. */
  source: { mode: 'REPLAY'; label: string; run_id: string; title: string; disclaimer: string };
  time: { sim_s: number; duration_s: number; playing: boolean; speed: number };
  mission: { state: string; reason_code: string; map_version: number; primary_agent_id: string; active_task: string | null };
  agents: Array<{
    id: string;
    kind: string;
    mode: string;
    /** Local ENU metres (x east, y north, z up). */
    position_enu_m: { x: number; y: number; z: number };
    heading_deg_from_north: number;
    energy_wh: number | null;
    oxygen_l: number | null;
    time_s: number | null;
  }>;
  active_route: null | {
    id: string;
    agent_id: string;
    status: string;
    mode: string;
    map_version_used: number;
    waypoints: number;
    travel_time_s: number | null;
    energy_est_wh: number | null;
    oxygen_est_l: number | null;
  };
  invalidated_routes: string[];
  /** Last few recorded events, newest last. */
  recent_events: Array<{ t_s: number; type: string; agent_id: string; detail: string }>;
  view: { tab: string; terrain_layer: string; camera: string; first_person: boolean };
}

export interface UiState {
  playing: boolean;
  speed: number;
  tab: string;
  layer: string;
  camera: string;
  firstPerson: boolean;
}

const round = (v: number, d = 2) => Math.round(v * 10 ** d) / 10 ** d;
const RECENT_EVENTS = 6;

/** Builds the snapshot from the replay view at the current time. Pure; reads nothing else. */
export function stateSnapshot(bundle: ReplayBundle, view: ReplayView, ui: UiState): StateSnapshot {
  const m = bundle.manifest;
  const s = view.state;
  const r = view.activeRoute;
  return {
    schema: 'mge.viewer-state/1',
    source: {
      mode: 'REPLAY',
      label: displayState({ mode: 'REPLAY', source: m.source_mode ?? 'UNKNOWN' }).label,
      run_id: m.run_id,
      title: m.title,
      disclaimer: m.disclaimer,
    },
    time: { sim_s: round(view.t, 1), duration_s: m.duration_s, playing: ui.playing, speed: ui.speed },
    mission: {
      state: s?.mission_state ?? 'IDLE',
      reason_code: s?.reason_code ?? '',
      map_version: s?.map_version ?? 1,
      primary_agent_id: s?.primary_agent_id ?? '',
      active_task: s?.active_task_id ? `${s.active_task_id} (${s.active_task_kind}, ${s.active_task_state || 'no state'})` : null,
    },
    agents: (s?.agents ?? []).map((a) => ({
      id: a.agent_id,
      kind: a.agent_kind,
      mode: a.mode,
      position_enu_m: { x: round(a.pose.position.x), y: round(a.pose.position.y), z: round(a.pose.position.z) },
      heading_deg_from_north: round(headingFromNorth(yawFromQuaternion(a.pose.orientation)), 1),
      energy_wh: a.energy_remaining_wh,
      oxygen_l: a.oxygen_remaining_l,
      time_s: a.time_remaining_s,
    })),
    active_route: r
      ? {
          id: r.route_id,
          agent_id: r.agent_id,
          status: r.status,
          mode: r.mode,
          map_version_used: r.map_version_used,
          waypoints: r.outbound_path.length,
          travel_time_s: r.travel_time_s,
          energy_est_wh: r.energy_est_wh,
          oxygen_est_l: r.oxygen_est_l,
        }
      : null,
    invalidated_routes: view.previousRoutes.map((p) => p.route_id),
    recent_events: view.events.slice(-RECENT_EVENTS).map((e) => ({ t_s: round(e.timestamp_sim_s, 1), type: e.event_type, agent_id: e.agent_id, detail: e.detail })),
    view: { tab: ui.tab, terrain_layer: ui.layer, camera: ui.camera, first_person: ui.firstPerson },
  };
}

/** Plain statement of what is real and what is simulated, exposed beside the state. */
export const ABOUT_DATA =
  'REPLAY with recorded or simulated producers as declared by each package. The viewer never plans routes or creates observations. Not a live mission; not certified for real operations.';

/** Describe only this run and the layers actually loaded for it. */
export function aboutData(bundle: ReplayBundle): string {
  const m = bundle.manifest;
  const t = m.terrain_meta;
  return `${ABOUT_DATA} ${m.disclaimer} Dataset ${t.dataset_id}: ${t.cols * t.resolution_m} × ${t.rows * t.resolution_m} m. ${terrainResolutionLabel(t)}. Datum: ${t.vertical_datum}. ${
    bundle.geology ? `Geology is approximate regional context: ${bundle.geology.source.registration_note}` : 'No matched geologic layer is loaded for this run.'
  } ${bundle.context ? 'Matched orbital surroundings are display context only.' : 'No matched surrounding terrain is loaded.'} ${
    bundle.atmosphere ? 'Atmosphere and radiation are historical context, not measured conditions of this replay.' : 'No environmental layer is loaded.'
  }`;
}
