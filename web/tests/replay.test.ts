import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { MissionEvent, RouteDecision } from '../src/types/icd';
import type { RasterSet, ReplayManifest, ReplayRoutes, ReplayTimeline } from '../src/types/replay';
import { assembleBundle, ReplayLoadError } from '../src/data/replayAdapter';
import { frameIndexAt, normalizeEvents, pchip, viewAt } from '../src/lib/replay';
import { isCurrentRoute, isTrustedRoute, NOT_ESTIMATED, fmtNumber, fractionRemaining, routeEta } from '../src/lib/format';
import { sampleHeight } from '../src/lib/coords';

const dir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo');
const read = <T>(f: string) => JSON.parse(readFileSync(join(dir, f), 'utf8')) as T;
const manifest = read<ReplayManifest>('manifest.json');
const rasters = read<RasterSet>('rasters.json');
const timeline = read<ReplayTimeline>('timeline.json');
const routes = read<ReplayRoutes>('routes.json');
const bundle = assembleBundle(manifest, rasters, timeline, routes);

const event = (seq: number, extra: Partial<MissionEvent> = {}): MissionEvent => ({
  timestamp_sim_s: seq, event_id: `e${seq}`, seq, run_id: 'run', causality_id: '', event_type: 'MISSION_STATE_CHANGED',
  task_id: '', agent_id: '', map_version: 1, route_id: '', previous_state: '', new_state: '', reason_code: '', detail: '', ...extra,
});

describe('event stream rules (ICD §2)', () => {
  it('drops other runs, ignores repeated event_id and orders by seq', () => {
    const out = normalizeEvents([event(3), event(1), event(2, { run_id: 'other' }), event(1)], 'run');
    expect(out.map((e) => e.seq)).toEqual([1, 3]);
  });
});

describe('ReplayAdapter contract checks', () => {
  it('rejects an unknown schema_version', () => {
    expect(() => assembleBundle({ ...manifest, schema_version: 'x' }, rasters, timeline, routes)).toThrow(ReplayLoadError);
  });

  it('rejects files from another run instead of mixing them', () => {
    expect(() => assembleBundle(manifest, rasters, { ...timeline, run_id: 'other' }, routes)).toThrow(/another|belongs/);
  });

  it('rejects rasters whose size does not match TerrainMeta', () => {
    expect(() => assembleBundle(manifest, { ...rasters, rows: 3 }, timeline, routes)).toThrow(ReplayLoadError);
  });
});

describe('demo fixture: replanning story (J-02)', () => {
  const invalidation = bundle.timeline.events.find((e) => e.event_type === 'ROUTE_INVALIDATED')!;
  const mapUpdate = bundle.timeline.events.find((e) => e.event_type === 'MAP_UPDATED')!;

  it('frame lookup returns the last state at or before t', () => {
    expect(frameIndexAt(bundle.timeline.frames, -1)).toBe(-1);
    expect(bundle.timeline.frames[frameIndexAt(bundle.timeline.frames, 10.7)].timestamp_sim_s).toBe(10);
  });

  it('before the map update only route r1 exists, planned on map v1', () => {
    const v = viewAt(bundle, mapUpdate.timestamp_sim_s - 1);
    expect(v.activeRoute?.route_id).toBe('r1');
    expect(v.previousRoutes).toHaveLength(0);
    expect(v.state?.map_version).toBe(1);
  });

  it('the invalidation is caused by MAP_UPDATED and keeps r1 as previous', () => {
    expect(invalidation.causality_id).toBe(mapUpdate.event_id);
    const v = viewAt(bundle, invalidation.timestamp_sim_s);
    expect(v.state?.mission_state).toBe('REPLAN');
    expect(v.activeRoute).toBeNull();
    expect(v.previousRoutes.map((r) => r.route_id)).toEqual(['r1']);
    expect(v.replans[0].cause?.event_type).toBe('MAP_UPDATED');
  });

  it('after replanning r2 is in force on map v2, starting at the halted astronaut pose', () => {
    const v = viewAt(bundle, invalidation.timestamp_sim_s + 10);
    expect(v.activeRoute?.route_id).toBe('r2');
    expect(v.activeRoute?.map_version_used).toBe(2);
    expect(v.previousRoutes.map((r) => r.route_id)).toEqual(['r1']);
    expect(v.replans[0].replacement?.route_id).toBe('r2');
    const halted = viewAt(bundle, invalidation.timestamp_sim_s).state!.agents.find((a) => a.agent_kind === 'HUMAN')!;
    const start = v.activeRoute!.outbound_path[0];
    expect(Math.hypot(start.x - halted.pose.position.x, start.y - halted.pose.position.y)).toBeLessThan(0.05);
  });

  it('two route versions never share a map version', () => {
    const versions = [...bundle.routes.values()].map((r) => r.map_version_used);
    expect(new Set(versions).size).toBe(versions.length);
  });

  it('one optional task is accepted and one is rejected with a reason', () => {
    const v = viewAt(bundle, manifest.duration_s);
    const c = v.tasks.find((k) => k.task_id === 'inspect:C')!;
    const d = v.tasks.find((k) => k.task_id === 'inspect:D')!;
    expect(c.state).toBe('DONE');
    expect(d.state).toBe('REJECTED');
    expect(d.reason_code).toBe('INSUFFICIENT_BUDGET');
  });

  it('a POI is only known after the observation that revealed it', () => {
    const discovered = bundle.timeline.events.filter((e) => e.event_type === 'TASK_DISCOVERED' && e.task_id.startsWith('inspect:'));
    for (const e of discovered) {
      const poi = manifest.pois.find((p) => e.task_id.endsWith(`:${p.id}`))!;
      expect(poi.revealed_at_s).toBeGreaterThanOrEqual(e.timestamp_sim_s);
    }
  });

  it('the mission ends COMPLETE with the astronaut at base', () => {
    const v = viewAt(bundle, manifest.duration_s);
    expect(v.state?.mission_state).toBe('COMPLETE');
    const human = v.state!.agents.find((a) => a.agent_kind === 'HUMAN')!;
    const base = v.state!.base;
    expect(Math.hypot(human.pose.position.x - base.x, human.pose.position.y - base.y)).toBeLessThan(1);
  });
});

describe('belief only changes inside the observation footprint', () => {
  it('cells outside the footprint keep the prior height', () => {
    const v2 = rasters.versions['2'];
    const observed = new Set(v2.observed);
    let changedOutside = 0;
    rasters.prior.forEach((p, i) => {
      if (!observed.has(i) && p !== v2.belief[i]) changedOutside++;
    });
    expect(observed.size).toBeGreaterThan(0);
    expect(changedOutside).toBe(0);
  });
});

describe('control points (J-01)', () => {
  it('each control point sits on the terrain mesh vertex of its cell', () => {
    for (const cp of manifest.control_points) {
      const h = sampleHeight(manifest.terrain_meta, rasters.prior, cp.position.x, cp.position.y);
      expect(h).not.toBeNull();
      expect(Math.abs(h! - cp.position.z)).toBeLessThan(1e-6);
    }
  });
});

describe('honest display of estimates (J-03)', () => {
  const r1 = routes.routes[0];
  const unknown: RouteDecision = { ...r1, status: 'UNKNOWN', route_id: '' };
  const budget: RouteDecision = { ...r1, status: 'INSUFFICIENT_BUDGET', route_id: '' };

  it('only FEASIBLE routes get a trusted style and an ETA', () => {
    expect(isTrustedRoute(r1)).toBe(true);
    expect(isTrustedRoute(unknown)).toBe(false);
    expect(isTrustedRoute(budget)).toBe(false);
    expect(routeEta(unknown)).toMatch(/No ETA/);
    expect(routeEta(budget)).toMatch(/No ETA/);
  });

  it('missing values read "Not estimated", never 0 or 100 %', () => {
    expect(fmtNumber(null, 'L')).toBe(NOT_ESTIMATED);
    expect(fmtNumber(Number.NaN, 'L')).toBe(NOT_ESTIMATED);
    expect(fractionRemaining(null, 1000)).toBeNull();
    expect(fractionRemaining(500, null)).toBeNull();
  });
});

describe('visual interpolation of agent poses', () => {
  const human = (t: number) => viewAt(bundle, t).state!.agents.find((a) => a.agent_kind === 'HUMAN')!.pose.position;

  it('returns the received pose exactly at a sample time', () => {
    const raw = bundle.timeline.frames.find((f) => f.timestamp_sim_s === 30)!.mission_state.agents.find((a) => a.agent_kind === 'HUMAN')!.pose.position;
    expect(human(30)).toEqual(raw);
  });

  it('lies between the two surrounding samples in between', () => {
    const a = human(30);
    const b = human(32);
    const m = human(31);
    expect(m.x).toBeCloseTo((a.x + b.x) / 2, 6);
    expect(m.y).toBeCloseTo((a.y + b.y) / 2, 6);
  });

  it('never extrapolates past the last sample', () => {
    expect(human(manifest.duration_s + 50)).toEqual(human(manifest.duration_s));
  });

  it('keeps the drone between its samples (no overshoot) and its speed continuous across a sample', () => {
    const drone = (t: number) => viewAt(bundle, t).state!.agents.find((a) => a.agent_kind === 'DRONE')!.pose.position;
    // Take-off sample pair 8 -> 10 s: the drawn altitude stays inside the received range.
    for (let t = 8; t <= 10; t += 0.25) {
      expect(drone(t).z).toBeGreaterThanOrEqual(-35.4 - 1e-6);
      expect(drone(t).z).toBeLessThanOrEqual(4.6 + 1e-6);
    }
    // Climb during the observation leg: vertical speed just before and after the 114 s sample match.
    const h = 1e-3;
    const before = (drone(114).z - drone(114 - h).z) / h;
    const after = (drone(114 + h).z - drone(114).z) / h;
    expect(Math.abs(after - before)).toBeLessThan(0.05);
  });

  it('interpolates monotonically and passes through the samples', () => {
    const a = { t: 0, v: 0 };
    const b = { t: 2, v: 0 };
    const c = { t: 4, v: 40 };
    const d = { t: 6, v: 40 };
    expect(pchip(a, b, c, d, 2)).toBe(0);
    expect(pchip(a, b, c, d, 4)).toBeCloseTo(40, 9);
    let prev = -Infinity;
    for (let t = 2; t <= 4; t += 0.1) {
      const v = pchip(a, b, c, d, t);
      expect(v).toBeGreaterThanOrEqual(prev);
      expect(v).toBeLessThanOrEqual(40 + 1e-9);
      prev = v;
    }
  });

  it('reports the walking speed from consecutive samples', () => {
    expect(viewAt(bundle, 30).speeds['human_1']).toBeCloseTo(1, 1);
    expect(viewAt(bundle, 2).speeds['human_1']).toBe(0);
  });
});

describe('stale route guard (from the shared scaffold)', () => {
  it('does not show a route for an earlier map as current', () => {
    expect(isCurrentRoute(2, 3)).toBe(false);
    expect(isCurrentRoute(3, 3)).toBe(true);
    expect(isCurrentRoute(-1, -1)).toBe(false);
  });
});
