import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { RasterSet, ReplayManifest, ReplayRoutes, ReplayTimeline } from '../src/types/replay';
import { assembleBundle } from '../src/data/replayAdapter';
import { viewAt } from '../src/lib/replay';
import {
  agentStats,
  detailsFor,
  headingFromNorth,
  initialBudgets,
  managementGroups,
  missionAlert,
  resolveSelection,
} from '../src/lib/management';

const dir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo');
const read = <T>(f: string) => JSON.parse(readFileSync(join(dir, f), 'utf8')) as T;
const bundle = assembleBundle(
  read<ReplayManifest>('manifest.json'),
  read<RasterSet>('rasters.json'),
  read<ReplayTimeline>('timeline.json'),
  read<ReplayRoutes>('routes.json'),
);
const budgets = initialBudgets(bundle);
const invalidatedAt = bundle.timeline.events.find((e) => e.event_type === 'ROUTE_INVALIDATED')!.timestamp_sim_s;

describe('management list', () => {
  it('starts with three agents and nothing else known', () => {
    const g = managementGroups(viewAt(bundle, 0));
    expect(g.find((x) => x.key === 'agents')!.rows).toHaveLength(3);
    expect(g.find((x) => x.key === 'tasks')!.rows).toHaveLength(0);
    expect(g.find((x) => x.key === 'routes')!.rows).toHaveLength(0);
  });

  it('keeps the invalidated route listed as invalidated next to the new one', () => {
    const routes = managementGroups(viewAt(bundle, invalidatedAt + 10)).find((x) => x.key === 'routes')!.rows;
    expect(routes.map((r) => r.name.split(' ')[0])).toEqual(['r1', 'r2']);
    expect(routes[0].state).toBe('invalidated');
    expect(routes[0].tone).toBe('bad');
    expect(routes[1].state).toBe('feasible');
  });

  it('lists the rejected task with a bad tone', () => {
    const rows = managementGroups(viewAt(bundle, bundle.manifest.duration_s)).find((x) => x.key === 'tasks')!.rows;
    const d = rows.find((r) => r.name === 'inspect:D')!;
    expect(d.state).toBe('rejected');
    expect(d.tone).toBe('bad');
  });
});

describe('selection', () => {
  it('falls back to the primary agent when the selected route is not known yet', () => {
    const early = viewAt(bundle, 0);
    expect(resolveSelection({ kind: 'route', id: 'r2' }, early)).toEqual({ kind: 'agent', id: 'human_1' });
  });

  it('keeps a selection that still exists', () => {
    const v = viewAt(bundle, invalidatedAt + 10);
    expect(resolveSelection({ kind: 'route', id: 'r1' }, v)).toEqual({ kind: 'route', id: 'r1' });
  });
});

describe('details', () => {
  it('explains an invalidated route with the cause that was received', () => {
    const v = viewAt(bundle, invalidatedAt + 10);
    const d = detailsFor({ kind: 'route', id: 'r1' }, v, bundle, budgets)!;
    expect(d.subtitle).toBe('invalidated');
    expect(d.body).toMatch(/Invalidated at T\+/);
    expect(d.body).toMatch(/scarp/);
  });

  it('never shows an ETA or reserves for a route that is not FEASIBLE (J-03)', () => {
    const r1 = bundle.routes.get('r1')!;
    for (const status of ['UNKNOWN', 'INSUFFICIENT_BUDGET', 'NO_PATH'] as const) {
      const fake = { ...bundle, routes: new Map(bundle.routes).set('r1', { ...r1, status }) };
      const d = detailsFor({ kind: 'route', id: 'r1' }, viewAt(fake, 20), fake, budgets)!;
      const facts = Object.fromEntries(d.facts);
      expect(facts['Round trip']).toMatch(/No ETA/);
      expect(facts['Reserve time']).toBe('Not estimated');
      expect(facts['Reserve oxygen']).toBe('Not estimated');
    }
  });

  it('marks oxygen as not applicable for the drone and never invents a value', () => {
    const drone = viewAt(bundle, 30).state!.agents.find((a) => a.agent_kind === 'DRONE')!;
    const oxygen = agentStats(drone, budgets[drone.agent_id])[0];
    expect(oxygen.applicable).toBe(false);
    expect(oxygen.fraction).toBeNull();
  });

  it('shows missing estimates as Not estimated with no percentage', () => {
    const human = viewAt(bundle, 30).state!.agents.find((a) => a.agent_kind === 'HUMAN')!;
    const unknown = { ...human, oxygen_remaining_l: null, energy_remaining_wh: null, time_remaining_s: null };
    for (const s of agentStats(unknown, budgets[human.agent_id])) {
      expect(s.fraction).toBeNull();
      expect(s.percent).toBeNull();
      if (s.applicable) expect(s.value).toBe('Not estimated');
    }
  });

  it('converts an ENU yaw to a compass heading', () => {
    expect(headingFromNorth(0)).toBeCloseTo(90); // facing east
    expect(headingFromNorth(Math.PI / 2)).toBeCloseTo(0); // facing north
    expect(headingFromNorth(Math.PI)).toBeCloseTo(270); // facing west
  });
});

describe('alert banner', () => {
  it('is silent during normal operation and warns while replanning', () => {
    expect(missionAlert(viewAt(bundle, 20))).toBeNull();
    const a = missionAlert(viewAt(bundle, invalidatedAt))!;
    expect(a.tone).toBe('warn');
    expect(a.title).toMatch(/replanning/);
  });

  it('warns when the route in force is not verified', () => {
    const r1 = bundle.routes.get('r1')!;
    const fake = { ...bundle, routes: new Map(bundle.routes).set('r1', { ...r1, status: 'UNKNOWN' as const }) };
    expect(missionAlert(viewAt(fake, 20))!.title).toMatch(/not verified/);
  });
});
