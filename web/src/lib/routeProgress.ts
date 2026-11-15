import type { Point } from '../types/icd';

/**
 * Where an agent stands along a received route (display only; nothing is planned here).
 * Distances are on the ENU ground plane (x, y), in metres.
 */
export interface RouteProgress {
  /** Index in the path of the next waypoint ahead of the agent. */
  nextIndex: number;
  next: Point;
  /** Straight-line distance to the next waypoint (m). */
  toNextM: number;
  /** Distance still to travel along the path, from the agent's projection to the end (m). */
  remainingM: number;
  /** Length of the whole path (m). */
  totalM: number;
  /** Distance from the agent to the path (m): large values mean the agent is off the route. */
  offRouteM: number;
}

const flat = (a: Point, b: Point) => Math.hypot(b.x - a.x, b.y - a.y);

/** Length of a path on the ground plane (m). */
export function pathLength(path: ReadonlyArray<Point>): number {
  let d = 0;
  for (let i = 1; i < path.length; i++) d += flat(path[i - 1], path[i]);
  return d;
}

/**
 * Progress of `pos` along `path`: the segment closest to the agent gives its projection; the
 * next waypoint is that segment's far end. Null for a path with fewer than two points.
 */
export function routeProgress(path: ReadonlyArray<Point>, pos: Point): RouteProgress | null {
  if (path.length < 2) return null;
  let best = { i: 0, t: 0, d: Infinity };
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i];
    const b = path[i + 1];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len2 = dx * dx + dy * dy;
    const t = len2 > 0 ? Math.max(0, Math.min(1, ((pos.x - a.x) * dx + (pos.y - a.y) * dy) / len2)) : 0;
    const d = Math.hypot(pos.x - (a.x + t * dx), pos.y - (a.y + t * dy));
    // Ties go to the later segment, so an agent standing on a waypoint looks ahead.
    if (d <= best.d + 1e-9) best = { i, t, d };
  }
  const a = path[best.i];
  const b = path[best.i + 1];
  const segLen = flat(a, b);
  // At the very end of the last segment there is nothing further ahead.
  let nextIndex = best.i + 1;
  if (best.t >= 1 - 1e-9 && nextIndex < path.length - 1) nextIndex++;
  let remainingM = segLen * (1 - best.t);
  for (let i = best.i + 1; i < path.length - 1; i++) remainingM += flat(path[i], path[i + 1]);
  const next = path[nextIndex];
  return { nextIndex, next, toNextM: flat(pos, next), remainingM, totalM: pathLength(path), offRouteM: best.d };
}

/**
 * Time left on the route, scaled from the route's own estimate by the share of distance left.
 * An estimate from the received route, not a prediction; null when the route gives no time.
 */
export function remainingTimeS(progress: RouteProgress, travelTimeS: number | null | undefined): number | null {
  if (travelTimeS == null || !Number.isFinite(travelTimeS) || progress.totalM <= 0) return null;
  return travelTimeS * Math.max(0, Math.min(1, progress.remainingM / progress.totalM));
}

/** Points every `stepM` along a path (ends included), for lines draped on the drawn ground. */
export function densifyPath(path: ReadonlyArray<Point>, stepM: number): Point[] {
  if (path.length < 2) return path.slice();
  const out: Point[] = [path[0]];
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1];
    const b = path[i];
    const n = Math.max(1, Math.ceil(flat(a, b) / stepM));
    for (let k = 1; k <= n; k++) {
      const t = k / n;
      out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t });
    }
  }
  return out;
}
