import type { Point, RouteDecision } from '../types/icd';
import type { Budget } from './management';
import type { ResourceLine } from './resources';
import { pathLength, routeProgress } from './routeProgress';

/**
 * Route sufficiency check (display only): at the replay time, is what the agent has left enough to
 * finish the route in force and get back, keeping the reserve; and if not, can it still walk back
 * the way it came? Rationale and sources: docs/route_resource_sufficiency.md.
 *
 * Inputs are only received data: the route's own estimated cost of the whole itinerary
 * (`travel_time_s`, `energy_est_wh`, `oxygen_est_l`, outbound and costed return together, as the
 * planner and JZ-P06 define it), its outbound and return paths, the agent's remaining amounts and
 * the first received sample (budget). Assumptions, stated in the doc: the cost per metre is uniform
 * along the itinerary (grade effects averaged), and the walk-back retraces the outbound path already
 * travelled (ground the agent has crossed). The reserve is the project's approved experimental
 * holdback (JZ-P06), not a NASA standard. The planner and MissionManager remain the authority; this
 * check orders nothing and changes no plan.
 */
export const RESERVE_SHARE = 0.2;

export type SufficiencyLevel =
  /** Finishing the route still leaves the full reserve. */
  | 'ok'
  /** The route can be finished only by using part of the reserve. */
  | 'caution'
  /** The route cannot be finished; walking back now keeps the reserve. */
  | 'turn_back'
  /** Even walking back now uses the reserve (or nothing is left for it). */
  | 'return_now'
  /** No route of this agent in force: only the reserve itself is checked. */
  | 'reserve_only'
  | 'unknown';

export interface Sufficiency {
  key: ResourceLine['key'];
  label: string;
  unit: string;
  level: SufficiencyLevel;
  remaining: number | null;
  /** Amount held back (RESERVE_SHARE of the first received sample), or null without one. */
  reserve: number | null;
  /** Estimated need to finish the route from here, return included. */
  needFinish: number | null;
  /** Estimated need to walk back to the start of the route now, along the travelled outbound path. */
  needWalkBack: number | null;
  /** remaining - needFinish - reserve: negative = the route eats into the reserve or does not fit. */
  marginFinish: number | null;
  /** remaining - needWalkBack - reserve. */
  marginWalkBack: number | null;
  /** How much farther along the route the agent can go and still walk back with the reserve (m). */
  turnBackInM: number | null;
  phase: 'outbound' | 'return' | null;
}

const budgetOf = (b: Budget | undefined, key: ResourceLine['key']) => (b ? (key === 'oxygen' ? b.oxygen_l : key === 'energy' ? b.energy_wh : b.time_s) : null);
const costOf = (r: RouteDecision, key: ResourceLine['key']) => {
  const v = key === 'oxygen' ? r.oxygen_est_l : key === 'energy' ? r.energy_est_wh : r.travel_time_s;
  return v == null || !Number.isFinite(v) ? null : v;
};

/** Where the agent is on the itinerary: distance still to go (return included) and distance already travelled outbound. */
export function itineraryPosition(route: RouteDecision, pos: Point): { phase: 'outbound' | 'return'; toGoM: number; travelledOutM: number; totalM: number } | null {
  const out = routeProgress(route.outbound_path, pos);
  if (!out) return null;
  const retLen = route.return_path.length > 1 ? pathLength(route.return_path) : 0;
  const ret = retLen > 0 ? routeProgress(route.return_path, pos) : null;
  // On the return leg once the outbound is done, or when clearly nearer the return path.
  const onReturn = !!ret && (out.remainingM < 5 || ret.offRouteM + 5 < out.offRouteM);
  if (onReturn && ret) return { phase: 'return', toGoM: ret.remainingM, travelledOutM: ret.remainingM, totalM: out.totalM + retLen };
  return { phase: 'outbound', toGoM: out.remainingM + retLen, travelledOutM: out.totalM - out.remainingM, totalM: out.totalM + retLen };
}

/** Sufficiency of each resource line for the agent at `pos` (the route counts only when it belongs to the agent). */
export function routeSufficiency(lines: ResourceLine[], route: RouteDecision | null, agentId: string, pos: Point, budget: Budget | undefined): Sufficiency[] {
  const own = route && route.agent_id === agentId && route.outbound_path.length > 1 ? route : null;
  const where = own ? itineraryPosition(own, pos) : null;
  return lines.map((l) => {
    const ref = budgetOf(budget, l.key);
    const reserve = ref != null && ref > 0 ? ref * RESERVE_SHARE : null;
    const base: Sufficiency = { key: l.key, label: l.label, unit: l.unit, level: 'unknown', remaining: l.remaining, reserve, needFinish: null, needWalkBack: null, marginFinish: null, marginWalkBack: null, turnBackInM: null, phase: where?.phase ?? null };
    if (l.remaining == null) return base;
    const cost = own ? costOf(own, l.key) : null;
    if (!own || !where || cost == null || where.totalM <= 0) {
      return { ...base, level: reserve != null && l.remaining < reserve ? 'return_now' : 'reserve_only' };
    }
    const perM = cost / where.totalM;
    const needFinish = perM * where.toGoM;
    const needWalkBack = perM * where.travelledOutM;
    const r = reserve ?? 0;
    const marginFinish = l.remaining - needFinish - r;
    const marginWalkBack = l.remaining - needWalkBack - r;
    // Going x metres farther costs x now and x more on the way back.
    const turnBackInM = where.phase === 'outbound' && perM > 0 ? Math.max(0, marginWalkBack / (2 * perM)) : null;
    let level: SufficiencyLevel;
    if (marginFinish >= 0) level = 'ok';
    else if (l.remaining - needFinish >= 0) level = 'caution';
    else if (marginWalkBack >= 0) level = 'turn_back';
    else level = 'return_now';
    return { ...base, level, needFinish, needWalkBack, marginFinish, marginWalkBack, turnBackInM };
  });
}
