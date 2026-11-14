import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { RasterSet, ReplayManifest, ReplayRoutes, ReplayTimeline } from '../src/types/replay';
import { assembleBundle } from '../src/data/replayAdapter';
import { viewAt } from '../src/lib/replay';
import { initialBudgets } from '../src/lib/management';
import { LOW_AFTER_ROUTE_SHARE, resourceLines, resourceTone } from '../src/lib/resources';

const dir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo');
const read = <T>(f: string) => JSON.parse(readFileSync(join(dir, f), 'utf8')) as T;
const bundle = assembleBundle(read<ReplayManifest>('manifest.json'), read<RasterSet>('rasters.json'), read<ReplayTimeline>('timeline.json'), read<ReplayRoutes>('routes.json'));
const budgets = initialBudgets(bundle);

describe('resource management lines', () => {
  it('derives the astronaut oxygen use from the samples around t', () => {
    const view = viewAt(bundle, 30);
    const human = view.state!.agents.find((a) => a.agent_kind === 'HUMAN')!;
    const lines = resourceLines(bundle, 30, human, view.activeRoute, budgets[human.agent_id]);
    expect(lines.map((l) => l.key)).toEqual(['oxygen', 'energy', 'time']);
    const o2 = lines[0];
    expect(o2.perHour).toBeGreaterThan(0);
    expect(o2.lastsS).toBeCloseTo(o2.remaining! / (o2.perHour! / 3600), 6);
  });

  it('lists no oxygen for vehicles', () => {
    const view = viewAt(bundle, 30);
    const rover = view.state!.agents.find((a) => a.agent_kind === 'ROVER')!;
    expect(resourceLines(bundle, 30, rover, view.activeRoute, budgets[rover.agent_id]).map((l) => l.key)).toEqual(['energy', 'time']);
  });

  it('reads the route figures only for the route of that agent', () => {
    const view = viewAt(bundle, 30);
    const route = view.activeRoute!;
    const owner = view.state!.agents.find((a) => a.agent_id === route.agent_id)!;
    const other = view.state!.agents.find((a) => a.agent_id !== route.agent_id)!;
    const mine = resourceLines(bundle, 30, owner, route, budgets[owner.agent_id]).find((l) => l.key === 'energy')!;
    expect(mine.afterRoute).toBe(route.reserve_wh);
    expect(mine.routeNeeds).toBe(route.energy_est_wh);
    expect(resourceLines(bundle, 30, other, route, budgets[other.agent_id]).every((l) => l.afterRoute == null)).toBe(true);
  });

  it('flags a route that leaves little or does not fit', () => {
    expect(resourceTone(500, -1, 1000)).toBe('alert');
    expect(resourceTone(500, 1000 * LOW_AFTER_ROUTE_SHARE - 1, 1000)).toBe('warn');
    expect(resourceTone(500, 400, 1000)).toBe('ok');
    expect(resourceTone(null, 400, 1000)).toBe('unknown');
  });
});
