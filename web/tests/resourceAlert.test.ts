import { describe, expect, it } from 'vitest';
import { resourceAlert } from '../src/lib/resourceAlert';
import { itineraryPosition, routeSufficiency } from '../src/lib/routeSufficiency';
import type { ResourceLine } from '../src/lib/resources';
import type { RouteDecision } from '../src/types/icd';

const p = (x: number, y = 0) => ({ x, y, z: 0 });
// 1000 m out along x and 1000 m back: the whole itinerary costs 200 Wh, so 0.1 Wh per metre.
const route = {
  route_id: 'r', agent_id: 'h', status: 'FEASIBLE',
  outbound_path: [p(0), p(1000)], return_path: [p(1000), p(0)],
  travel_time_s: 2000, energy_est_wh: 200, oxygen_est_l: 40,
} as unknown as RouteDecision;
const budget = { oxygen_l: 100, energy_wh: 300, time_s: 6000 };
const energy = (remaining: number): ResourceLine => ({ key: 'energy', label: 'Energy', unit: 'Wh', remaining, perHour: null, lastsS: null, routeNeeds: null, afterRoute: null, tone: 'ok' });

describe('itineraryPosition', () => {
  it('counts the rest of the outbound plus the whole return, and the distance travelled for the walk-back', () => {
    const w = itineraryPosition(route, p(400));
    expect(w?.phase).toBe('outbound');
    expect(w?.toGoM).toBeCloseTo(1600, 6);
    expect(w?.travelledOutM).toBeCloseTo(400, 6);
  });
});

describe('routeSufficiency', () => {
  // At 400 m out: finishing needs 160 Wh, walking back 40 Wh; reserve is 20% of 300 = 60 Wh.
  const at = (remaining: number) => routeSufficiency([energy(remaining)], route, 'h', p(400), budget)[0];

  it('is ok when finishing leaves the full reserve', () => {
    expect(at(230).level).toBe('ok');
  });
  it('warns when finishing needs part of the reserve', () => {
    expect(at(200).level).toBe('caution');
  });
  it('says turn back when the route no longer fits but the walk-back keeps the reserve', () => {
    const s = at(120);
    expect(s.level).toBe('turn_back');
    expect(s.marginWalkBack).toBeCloseTo(20, 6);
  });
  it('says return now when even walking back uses the reserve', () => {
    expect(at(90).level).toBe('return_now');
  });
  it('gives the turn-back point: going x farther costs x out and x back', () => {
    // 200 Wh left: walk-back margin 200 - 40 - 60 = 100 Wh, so 100 / (2 * 0.1) = 500 m more.
    expect(at(200).turnBackInM).toBeCloseTo(500, 6);
  });
  it('checks only the reserve without a route of this agent', () => {
    expect(routeSufficiency([energy(50)], null, 'h', p(0), budget)[0].level).toBe('return_now');
    expect(routeSufficiency([energy(200)], route, 'other', p(0), budget)[0].level).toBe('reserve_only');
  });
});

describe('resourceAlert', () => {
  it('stays quiet when the route fits with the reserve', () => {
    expect(resourceAlert([energy(230)], budget, route, 'h', p(400))).toBeNull();
  });
  it('raises a critical turn-back alert when the route does not fit', () => {
    const a = resourceAlert([energy(120)], budget, route, 'h', p(400));
    expect(a?.level).toBe('critical');
    expect(a?.action).toMatch(/Turn back/);
  });
  it('raises a low alert when the route eats into the reserve', () => {
    expect(resourceAlert([energy(200)], budget, route, 'h', p(400))?.level).toBe('low');
  });
});
