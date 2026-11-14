import type { AgentState, MissionEvent, MissionState, RouteDecision, TaskState } from '../types/icd';
import { yawFromQuaternion } from './coords';
import type { ReplayBundle, ReplayFrame } from '../types/replay';

/** Index of the last frame with timestamp <= t, or -1 before the first frame. */
export function frameIndexAt(frames: ReadonlyArray<ReplayFrame>, t: number): number {
  let lo = 0;
  let hi = frames.length - 1;
  let found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].timestamp_sim_s <= t) {
      found = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return found;
}

/**
 * Applies the ICD ordering rules to a raw event stream: drop other runs,
 * ignore repeated event_id, order by seq.
 */
export function normalizeEvents(events: ReadonlyArray<MissionEvent>, runId: string): MissionEvent[] {
  const seen = new Set<string>();
  const out: MissionEvent[] = [];
  for (const e of events) {
    if (e.run_id !== runId || seen.has(e.event_id)) continue;
    seen.add(e.event_id);
    out.push(e);
  }
  return out.sort((a, b) => a.seq - b.seq);
}

export function eventsUpTo(events: ReadonlyArray<MissionEvent>, t: number): MissionEvent[] {
  return events.filter((e) => e.timestamp_sim_s <= t);
}

export interface TaskView {
  task_id: string;
  state: TaskState;
  agent_id: string;
  reason_code: string;
  detail: string;
  updated_at_s: number;
}

/** Task table rebuilt only from received events (never from the hidden scenario list). */
export function taskViews(events: ReadonlyArray<MissionEvent>): TaskView[] {
  const tasks = new Map<string, TaskView>();
  for (const e of events) {
    if (e.event_type !== 'TASK_DISCOVERED' && e.event_type !== 'TASK_STATE_CHANGED') continue;
    tasks.set(e.task_id, {
      task_id: e.task_id,
      state: (e.new_state || 'DISCOVERED') as TaskState,
      agent_id: e.agent_id,
      reason_code: e.reason_code,
      detail: e.detail,
      updated_at_s: e.timestamp_sim_s,
    });
  }
  return [...tasks.values()];
}

export interface Replan {
  invalidated: MissionEvent;
  /** The MAP_UPDATED (or other) event named in causality_id, when present. */
  cause: MissionEvent | null;
  replacement: MissionEvent | null;
}

/** Every route invalidation up to now with its cause and the route that replaced it. */
export function replans(events: ReadonlyArray<MissionEvent>): Replan[] {
  const byId = new Map(events.map((e) => [e.event_id, e]));
  const out: Replan[] = [];
  for (const e of events) {
    if (e.event_type !== 'ROUTE_INVALIDATED') continue;
    const replacement =
      events.find((n) => n.event_type === 'ROUTE_PUBLISHED' && n.seq > e.seq && n.causality_id === e.event_id) ?? null;
    out.push({ invalidated: e, cause: byId.get(e.causality_id) ?? null, replacement });
  }
  return out;
}

/** Longest gap between two samples that is still bridged visually. */
export const MAX_INTERPOLATION_GAP_S = 2;

/**
 * Visual interpolation between two received samples so motion is smooth.
 * It never extrapolates: after the last sample, or across a gap longer than
 * MAX_INTERPOLATION_GAP_S, the last received pose is shown unchanged.
 * Mode and resources are taken from the earlier sample as received.
 */
export function interpolateAgents(a: ReplayFrame, b: ReplayFrame | undefined, t: number): AgentState[] {
  const agents = a.mission_state.agents;
  if (!b) return agents;
  const span = b.timestamp_sim_s - a.timestamp_sim_s;
  if (span <= 0 || span > MAX_INTERPOLATION_GAP_S) return agents;
  const k = Math.max(0, Math.min(1, (t - a.timestamp_sim_s) / span));
  if (k === 0) return agents;
  return agents.map((s) => {
    const n = b.mission_state.agents.find((x) => x.agent_id === s.agent_id);
    if (!n) return s;
    const p = s.pose.position;
    const q = n.pose.position;
    const y0 = yawFromQuaternion(s.pose.orientation);
    let dy = yawFromQuaternion(n.pose.orientation) - y0;
    dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    const yaw = y0 + dy * k;
    return {
      ...s,
      pose: {
        position: { x: p.x + (q.x - p.x) * k, y: p.y + (q.y - p.y) * k, z: p.z + (q.z - p.z) * k },
        orientation: { x: 0, y: 0, z: Math.sin(yaw / 2), w: Math.cos(yaw / 2) },
      },
    };
  });
}

/** Ground speed of each agent between the two samples around t, m/s of simulated time. */
export function agentSpeeds(a: ReplayFrame, b: ReplayFrame | undefined): Record<string, number> {
  const out: Record<string, number> = {};
  const span = b ? b.timestamp_sim_s - a.timestamp_sim_s : 0;
  for (const s of a.mission_state.agents) {
    const n = b?.mission_state.agents.find((x) => x.agent_id === s.agent_id);
    out[s.agent_id] =
      n && span > 0 && span <= MAX_INTERPOLATION_GAP_S
        ? Math.hypot(n.pose.position.x - s.pose.position.x, n.pose.position.y - s.pose.position.y) / span
        : 0;
  }
  return out;
}

export interface ReplayView {
  t: number;
  frame: ReplayFrame | null;
  state: MissionState | null;
  events: MissionEvent[];
  activeRoute: RouteDecision | null;
  /** Routes that were in force earlier and were invalidated, oldest first. */
  previousRoutes: RouteDecision[];
  replans: Replan[];
  tasks: TaskView[];
  /** Ground speed per agent_id derived from consecutive samples, m/s (simulated). */
  speeds: Record<string, number>;
}

export function viewAt(bundle: ReplayBundle, t: number): ReplayView {
  const frames = bundle.timeline.frames;
  const idx = frameIndexAt(frames, t);
  const frame = idx >= 0 ? frames[idx] : null;
  const next = idx >= 0 ? frames[idx + 1] : undefined;
  const state = frame ? { ...frame.mission_state, agents: interpolateAgents(frame, next, t) } : null;
  const events = eventsUpTo(bundle.timeline.events, t);
  const activeRoute = state ? (state.active_route ?? bundle.routes.get(state.route_id) ?? null) : null;
  const rp = replans(events);
  const previousRoutes = rp
    .map((r) => bundle.routes.get(r.invalidated.route_id))
    .filter((r): r is RouteDecision => !!r && r.route_id !== activeRoute?.route_id);
  return { t, frame, state, events, activeRoute, previousRoutes, replans: rp, tasks: taskViews(events), speeds: frame ? agentSpeeds(frame, next) : {} };
}
