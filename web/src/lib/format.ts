import type { RouteDecision, RouteStatus } from '../types/icd';

export const NOT_ESTIMATED = 'Not estimated';

/** Formats an estimate; missing values are never shown as 0 or 100 %. */
export function fmtNumber(value: number | null | undefined, unit: string, digits = 0): string {
  if (value == null || !Number.isFinite(value)) return NOT_ESTIMATED;
  return `${value.toFixed(digits)} ${unit}`;
}

export function fmtDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return NOT_ESTIMATED;
  const s = Math.max(0, Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  return h > 0 ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m ${String(r).padStart(2, '0')}s`;
}

export function fmtSimTime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `T+${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

/** Only a FEASIBLE route may show a "safe" style and an ETA (J-03). */
export function isTrustedRoute(route: RouteDecision | null | undefined): boolean {
  return !!route && route.status === 'FEASIBLE';
}

export function routeEta(route: RouteDecision | null | undefined): string {
  if (!isTrustedRoute(route)) return 'No ETA (route not verified)';
  return fmtDuration(route!.travel_time_s);
}

export interface StatusStyle {
  label: string;
  color: string;
  dashed: boolean;
  description: string;
}

export const ROUTE_STATUS_STYLE: Record<RouteStatus, StatusStyle> = {
  FEASIBLE: { label: 'Feasible', color: '#65CBE8', dashed: false, description: 'Admissible under the current map and budgets (model estimate).' },
  UNKNOWN: { label: 'Unknown', color: '#D8AD66', dashed: true, description: 'Not enough information to verify the route. Not a safe route.' },
  NO_PATH: { label: 'No path', color: '#D95045', dashed: true, description: 'No admissible path exists under the current map.' },
  INSUFFICIENT_BUDGET: { label: 'Insufficient budget', color: '#D95045', dashed: true, description: 'A path exists but resources or return would not be guaranteed.' },
  STALE_MAP: { label: 'Stale map', color: '#78828D', dashed: true, description: 'Computed on an older map version; discarded.' },
  ERROR: { label: 'Error', color: '#D95045', dashed: true, description: 'The planner reported an error.' },
};

/** Fraction remaining, or null when either value is missing. */
export function fractionRemaining(remaining: number | null | undefined, budget: number | null | undefined): number | null {
  if (remaining == null || budget == null || !Number.isFinite(remaining) || !Number.isFinite(budget) || budget <= 0) return null;
  return Math.max(0, Math.min(1, remaining / budget));
}
