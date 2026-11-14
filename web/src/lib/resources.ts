import type { AgentState, RouteDecision } from '../types/icd';
import type { ReplayBundle } from '../types/replay';
import type { Budget } from './management';
import { frameIndexAt, MAX_INTERPOLATION_GAP_S } from './replay';

/**
 * Resource management for the selected agent: how fast each consumable is being used, how long
 * it lasts at that rate, what the route in force needs and what it leaves. Rates are derived from
 * the two received samples around the replay time (no extrapolation beyond them). The route
 * figures are as published: `*_est` is the route's estimated cost and `reserve_*` is what remains
 * after it (budget minus cost, as the planner and mission compute it), not a required minimum.
 * Display only; nothing here changes a plan.
 */
export type ResourceTone = 'ok' | 'warn' | 'alert' | 'unknown';

export interface ResourceLine {
  key: 'oxygen' | 'energy' | 'time';
  label: string;
  unit: string;
  remaining: number | null;
  /** Use rate per hour of simulated time (L/h, Wh/h; for time, 3600 while the clock runs). */
  perHour: number | null;
  /** Simulated seconds until empty at the current rate, or null when not consuming. */
  lastsS: number | null;
  /** Estimated cost of the route in force, or null. */
  routeNeeds: number | null;
  /** What the route in force leaves at its end (its reserve_* field), or null. */
  afterRoute: number | null;
  tone: ResourceTone;
}

/** Share of the starting budget left after the route below which a resource is flagged. */
export const LOW_AFTER_ROUTE_SHARE = 0.15;

function valueOf(a: AgentState, key: ResourceLine['key']): number | null {
  const v = key === 'oxygen' ? a.oxygen_remaining_l : key === 'energy' ? a.energy_remaining_wh : a.time_remaining_s;
  return v == null || !Number.isFinite(v) ? null : v;
}

const finite = (v: number | null | undefined) => (v == null || !Number.isFinite(v) ? null : v);

/** Flag from what the route leaves: negative = does not fit, under LOW_AFTER_ROUTE_SHARE of the budget = low. */
export function resourceTone(remaining: number | null, afterRoute: number | null, budget: number | null): ResourceTone {
  if (remaining == null) return 'unknown';
  if (afterRoute == null) return 'ok';
  if (afterRoute < 0) return 'alert';
  if (budget != null && budget > 0 && afterRoute < budget * LOW_AFTER_ROUTE_SHARE) return 'warn';
  return 'ok';
}

/** Resource lines of one agent at replay time t. Oxygen is listed for the astronaut only. */
export function resourceLines(bundle: ReplayBundle, t: number, agent: AgentState, route: RouteDecision | null, budget?: Budget): ResourceLine[] {
  const frames = bundle.timeline.frames;
  const i = frameIndexAt(frames, t);
  const a = i >= 0 ? frames[i] : null;
  const b = i >= 0 ? frames[i + 1] : undefined;
  const span = a && b ? b.timestamp_sim_s - a.timestamp_sim_s : 0;
  const before = a?.mission_state.agents.find((x) => x.agent_id === agent.agent_id);
  const after = b?.mission_state.agents.find((x) => x.agent_id === agent.agent_id);
  const own = route && route.agent_id === agent.agent_id ? route : null;
  const keys: ResourceLine['key'][] = agent.agent_kind === 'HUMAN' ? ['oxygen', 'energy', 'time'] : ['energy', 'time'];
  return keys.map((key) => {
    const remaining = valueOf(agent, key);
    let perS: number | null = null;
    if (before && after && span > 0 && span <= MAX_INTERPOLATION_GAP_S) {
      const v0 = valueOf(before, key);
      const v1 = valueOf(after, key);
      if (v0 != null && v1 != null) perS = Math.max(0, (v0 - v1) / span);
    }
    const routeNeeds = !own ? null : finite(key === 'oxygen' ? own.oxygen_est_l : key === 'energy' ? own.energy_est_wh : own.travel_time_s);
    const afterRoute = !own ? null : finite(key === 'oxygen' ? own.reserve_oxygen_l : key === 'energy' ? own.reserve_wh : own.reserve_time_s);
    const start = finite(key === 'oxygen' ? budget?.oxygen_l : key === 'energy' ? budget?.energy_wh : budget?.time_s);
    return {
      key,
      label: key === 'oxygen' ? 'Oxygen' : key === 'energy' ? 'Energy' : 'Time',
      unit: key === 'oxygen' ? 'L' : key === 'energy' ? 'Wh' : 's',
      remaining,
      perHour: perS == null ? null : perS * 3600,
      lastsS: remaining != null && perS != null && perS > 1e-9 ? remaining / perS : null,
      routeNeeds,
      afterRoute,
      tone: resourceTone(remaining, afterRoute, start),
    };
  });
}

/** Remaining amount of one resource over the run up to t, for the history charts (at most `points` samples). */
export function resourceHistory(bundle: ReplayBundle, agentId: string, key: ResourceLine['key'], t: number, points = 160): Array<{ t: number; v: number }> {
  const frames = bundle.timeline.frames;
  const last = frameIndexAt(frames, t);
  if (last < 0) return [];
  const step = Math.max(1, Math.ceil((last + 1) / points));
  const out: Array<{ t: number; v: number }> = [];
  for (let i = 0; i <= last; i += step) {
    const a = frames[i].mission_state.agents.find((x) => x.agent_id === agentId);
    const v = a ? valueOf(a, key) : null;
    if (v != null) out.push({ t: frames[i].timestamp_sim_s, v });
  }
  const a = frames[last].mission_state.agents.find((x) => x.agent_id === agentId);
  const v = a ? valueOf(a, key) : null;
  if (v != null && out[out.length - 1]?.t !== frames[last].timestamp_sim_s) out.push({ t: frames[last].timestamp_sim_s, v });
  return out;
}
