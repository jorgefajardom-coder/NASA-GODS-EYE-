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

/** One received value with its time, or null where no usable neighbouring sample exists. */
type Knot = { t: number; v: number } | null;

/** Fritsch-Carlson slope at `b` from its neighbours (0 at a local extremum, so no overshoot). */
function pchipSlope(a: Knot, b: { t: number; v: number }, c: Knot): number {
  const dl = a ? (b.v - a.v) / (b.t - a.t) : null;
  const dr = c ? (c.v - b.v) / (c.t - b.t) : null;
  if (dl == null) return dr ?? 0;
  if (dr == null) return dl;
  if (dl * dr <= 0) return 0;
  const hl = b.t - a!.t;
  const hr = c!.t - b.t;
  const w1 = 2 * hr + hl;
  const w2 = hr + 2 * hl;
  return (w1 + w2) / (w1 / dl + w2 / dr);
}

/**
 * Monotone cubic (PCHIP) value between the samples `b` and `c` at time `t`. It passes through
 * every sample, never leaves the range of the two samples it joins where the data is monotone,
 * and keeps the speed continuous across samples (straight segments made the speed snap every
 * sample, which read as jolts on the drone and through a locked camera).
 */
export function pchip(a: Knot, b: { t: number; v: number }, c: { t: number; v: number }, d: Knot, t: number): number {
  const h = c.t - b.t;
  if (!(h > 0)) return b.v;
  const s = Math.max(0, Math.min(1, (t - b.t) / h));
  const m1 = pchipSlope(a, b, c);
  const m2 = pchipSlope(b, c, d);
  const s2 = s * s;
  const s3 = s2 * s;
  return (2 * s3 - 3 * s2 + 1) * b.v + (s3 - 2 * s2 + s) * h * m1 + (-2 * s3 + 3 * s2) * c.v + (s3 - s2) * h * m2;
}

/**
 * Visual interpolation between two received samples so motion is smooth.
 * It never extrapolates: after the last sample, or across a gap longer than
 * MAX_INTERPOLATION_GAP_S, the last received pose is shown unchanged.
 * Between samples the pose follows a monotone cubic through the received samples (the one
 * before `a` and after `b`, when present and close enough, only shape the curve).
 * Mode and resources are taken from the earlier sample as received.
 */
export function interpolateAgents(a: ReplayFrame, b: ReplayFrame | undefined, t: number, before?: ReplayFrame, after?: ReplayFrame): AgentState[] {
  const agents = a.mission_state.agents;
  if (!b) return agents;
  const span = b.timestamp_sim_s - a.timestamp_sim_s;
  if (span <= 0 || span > MAX_INTERPOLATION_GAP_S) return agents;
  const k = Math.max(0, Math.min(1, (t - a.timestamp_sim_s) / span));
  if (k === 0) return agents;
  const near = (f: ReplayFrame | undefined, from: ReplayFrame) =>
    f && Math.abs(f.timestamp_sim_s - from.timestamp_sim_s) > 0 && Math.abs(f.timestamp_sim_s - from.timestamp_sim_s) <= MAX_INTERPOLATION_GAP_S ? f : undefined;
  const prev = near(before, a);
  const next = near(after, b);
  return agents.map((s) => {
    const n = b.mission_state.agents.find((x) => x.agent_id === s.agent_id);
    if (!n) return s;
    const p0 = prev?.mission_state.agents.find((x) => x.agent_id === s.agent_id);
    const p3 = next?.mission_state.agents.find((x) => x.agent_id === s.agent_id);
    const ta = a.timestamp_sim_s;
    const tb = b.timestamp_sim_s;
    const axis = (get: (x: AgentState) => number) =>
      pchip(
        p0 ? { t: prev!.timestamp_sim_s, v: get(p0) } : null,
        { t: ta, v: get(s) },
        { t: tb, v: get(n) },
        p3 ? { t: next!.timestamp_sim_s, v: get(p3) } : null,
        t,
      );
    // Yaw unwrapped along the samples so a turn goes the short way round.
    const y1 = yawFromQuaternion(s.pose.orientation);
    const unwrap = (from: number, to: number) => from + Math.atan2(Math.sin(to - from), Math.cos(to - from));
    const y2 = unwrap(y1, yawFromQuaternion(n.pose.orientation));
    const y0 = p0 ? unwrap(y1, yawFromQuaternion(p0.pose.orientation)) : null;
    const y3 = p3 ? unwrap(y2, yawFromQuaternion(p3.pose.orientation)) : null;
    const yaw = pchip(y0 == null ? null : { t: prev!.timestamp_sim_s, v: y0 }, { t: ta, v: y1 }, { t: tb, v: y2 }, y3 == null ? null : { t: next!.timestamp_sim_s, v: y3 }, t);
    return {
      ...s,
      pose: {
        position: { x: axis((x) => x.pose.position.x), y: axis((x) => x.pose.position.y), z: axis((x) => x.pose.position.z) },
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
  const state = frame ? { ...frame.mission_state, agents: interpolateAgents(frame, next, t, frames[idx - 1], frames[idx + 2]) } : null;
  const events = eventsUpTo(bundle.timeline.events, t);
  const activeRoute = state ? (state.active_route ?? bundle.routes.get(state.route_id) ?? null) : null;
  const rp = replans(events);
  const previousRoutes = rp
    .map((r) => bundle.routes.get(r.invalidated.route_id))
    .filter((r): r is RouteDecision => !!r && r.route_id !== activeRoute?.route_id);
  return { t, frame, state, events, activeRoute, previousRoutes, replans: rp, tasks: taskViews(events), speeds: frame ? agentSpeeds(frame, next) : {} };
}

/** Idle lead-in kept before the first motion when the replay is restarted (s of simulated time). */
export const LEAD_IN_S = 4;

/**
 * Where playback restarts: LEAD_IN_S before the first sample in which an agent leaves IDLE
 * (0 when an agent moves from the start or none ever moves). Display convenience only.
 */
export function firstMotionTime(bundle: ReplayBundle): number {
  const frames = bundle.timeline.frames;
  const i = frames.findIndex((f) => f.mission_state.agents.some((a) => a.mode !== 'IDLE'));
  return i > 0 ? Math.max(0, frames[i].timestamp_sim_s - LEAD_IN_S) : 0;
}
