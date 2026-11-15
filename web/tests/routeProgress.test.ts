import { describe, expect, it } from 'vitest';
import { densifyPath, pathLength, remainingTimeS, routeProgress } from '../src/lib/routeProgress';

const P = (x: number, y: number) => ({ x, y, z: 0 });
// An L-shaped route: 100 m east, then 50 m north.
const L = [P(0, 0), P(100, 0), P(100, 50)];

describe('route progress (display only)', () => {
  it('measures the path on the ground', () => {
    expect(pathLength(L)).toBeCloseTo(150);
    expect(routeProgress([P(0, 0)], P(0, 0))).toBeNull();
  });

  it('finds the next waypoint ahead and the distance left', () => {
    const p = routeProgress(L, P(40, 3))!;
    expect(p.nextIndex).toBe(1);
    expect(p.toNextM).toBeCloseTo(Math.hypot(60, 3));
    expect(p.remainingM).toBeCloseTo(60 + 50);
    expect(p.offRouteM).toBeCloseTo(3);
    const q = routeProgress(L, P(101, 20))!;
    expect(q.nextIndex).toBe(2);
    expect(q.remainingM).toBeCloseTo(30);
  });

  it('looks ahead when standing on a waypoint, and ends at the last one', () => {
    expect(routeProgress(L, P(100, 0))!.nextIndex).toBe(2);
    const end = routeProgress(L, P(100, 50))!;
    expect(end.nextIndex).toBe(2);
    expect(end.remainingM).toBeCloseTo(0);
  });

  it('scales the route time by the distance left, and gives none without one', () => {
    const p = routeProgress(L, P(40, 0))!;
    expect(remainingTimeS(p, 300)).toBeCloseTo(300 * (110 / 150));
    expect(remainingTimeS(p, null)).toBeNull();
  });

  it('densifies a path without moving its waypoints', () => {
    const d = densifyPath(L, 10);
    expect(d[0]).toEqual(P(0, 0));
    expect(d[d.length - 1]).toEqual(P(100, 50));
    expect(d).toContainEqual(P(100, 0));
    for (let i = 1; i < d.length; i++) expect(Math.hypot(d[i].x - d[i - 1].x, d[i].y - d[i - 1].y)).toBeLessThanOrEqual(10 + 1e-9);
  });
});
