import type { Point, RouteDecision } from '../types/icd';
import type { Budget } from './management';
import type { ResourceLine } from './resources';
import { routeSufficiency, type Sufficiency } from './routeSufficiency';

/**
 * First-person alert built on the route sufficiency check (lib/routeSufficiency,
 * docs/route_resource_sufficiency.md). Critical: the route in force does not fit and the agent should
 * turn back, or even walking back now uses the reserve. Low: the route can be finished only by using
 * part of the reserve. Display only; the alert orders nothing and changes no plan.
 */
export type AlertLevel = 'critical' | 'low';

export interface ResourceAlert {
  level: AlertLevel;
  key: ResourceLine['key'];
  label: string;
  /** Share of the first received sample left (0..1), or null without one. */
  share: number | null;
  /** What to do, in plain words. */
  action: string;
  /** Why it fired, in plain words. */
  reason: string;
  /** Distance the agent can still go before it must turn back (m), when known. */
  turnBackInM: number | null;
  detail: Sufficiency;
}

const SEVERITY: Record<string, number> = { return_now: 3, turn_back: 2, caution: 1 };

const amount = (v: number, key: ResourceLine['key'], unit: string) =>
  key === 'time' ? (Math.abs(v) >= 3600 ? `${(v / 3600).toFixed(1)} h` : `${Math.round(v / 60)} min`) : `${v.toFixed(v >= 100 ? 0 : 1)} ${unit}`;

/** The most severe alert for the agent, or null when every resource covers the route and the reserve. */
export function resourceAlert(lines: ResourceLine[], budget: Budget | undefined, route: RouteDecision | null, agentId: string, pos: Point): ResourceAlert | null {
  const checks = routeSufficiency(lines, route, agentId, pos, budget).filter((s) => SEVERITY[s.level]);
  if (!checks.length) return null;
  checks.sort((a, b) => SEVERITY[b.level] - SEVERITY[a.level] || (a.marginWalkBack ?? 0) - (b.marginWalkBack ?? 0));
  const s = checks[0];
  const ref = s.reserve != null ? s.reserve / 0.2 : null;
  const share = ref && s.remaining != null ? Math.max(0, s.remaining / ref) : null;
  const name = s.label.toLowerCase();
  let action: string;
  let reason: string;
  if (s.level === 'return_now') {
    action = 'Return to base now';
    reason =
      s.needWalkBack == null
        ? `${name} is inside the reserve (${amount(s.remaining ?? 0, s.key, s.unit)} left, reserve ${amount(s.reserve ?? 0, s.key, s.unit)})`
        : `walking back needs ~${amount(s.needWalkBack, s.key, s.unit)} of ${name}; only ${amount(s.remaining ?? 0, s.key, s.unit)} left with a ${amount(s.reserve ?? 0, s.key, s.unit)} reserve`;
  } else if (s.level === 'turn_back') {
    action = 'Turn back · return to base';
    reason = `finishing the route needs ~${amount(s.needFinish ?? 0, s.key, s.unit)} of ${name}, ${amount(s.remaining ?? 0, s.key, s.unit)} left; walking back now keeps the reserve`;
  } else {
    action = 'Route uses the reserve';
    reason = `finishing needs ~${amount(s.needFinish ?? 0, s.key, s.unit)} of ${name}, leaving less than the ${amount(s.reserve ?? 0, s.key, s.unit)} reserve`;
  }
  return { level: s.level === 'caution' ? 'low' : 'critical', key: s.key, label: s.label, share, action, reason, turnBackInM: s.turnBackInM, detail: s };
}
