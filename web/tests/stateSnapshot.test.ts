import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { RasterSet, ReplayManifest, ReplayRoutes, ReplayTimeline } from '../src/types/replay';
import { assembleBundle } from '../src/data/replayAdapter';
import { viewAt } from '../src/lib/replay';
import { ABOUT_DATA, stateSnapshot } from '../src/lib/stateSnapshot';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const dir = join(web, 'public', 'replay', 'demo');
const read = <T>(f: string) => JSON.parse(readFileSync(join(dir, f), 'utf8')) as T;
const bundle = assembleBundle(read<ReplayManifest>('manifest.json'), read<RasterSet>('rasters.json'), read<ReplayTimeline>('timeline.json'), read<ReplayRoutes>('routes.json'));
const ui = { playing: false, speed: 1, tab: 'exploration', layer: 'belief', camera: 'free', firstPerson: false };

describe('machine-readable viewer state', () => {
  it('always declares a replay of the recorded run, never a live mission', () => {
    const s = stateSnapshot(bundle, viewAt(bundle, 0), ui);
    expect(s.schema).toBe('mge.viewer-state/1');
    expect(s.source.mode).toBe('REPLAY');
    expect(s.source.label).not.toMatch(/LIVE/i);
    expect(s.source.run_id).toBe(bundle.manifest.run_id);
    expect(s.source.disclaimer).toBe(bundle.manifest.disclaimer);
    expect(ABOUT_DATA).toMatch(/simulated/i);
  });

  it('reports the recorded agents, route and events at the requested time, as plain JSON', () => {
    const t = 600;
    const view = viewAt(bundle, t);
    const s = stateSnapshot(bundle, view, { ...ui, firstPerson: true, camera: 'human_1' });
    expect(s.time.sim_s).toBeCloseTo(t, 0);
    expect(s.agents.map((a) => a.id).sort()).toEqual((view.state?.agents ?? []).map((a) => a.agent_id).sort());
    for (const a of s.agents) {
      expect(a.heading_deg_from_north).toBeGreaterThanOrEqual(0);
      expect(a.heading_deg_from_north).toBeLessThan(360);
    }
    expect(s.active_route?.id ?? null).toBe(view.activeRoute?.route_id ?? null);
    expect(s.recent_events.length).toBeLessThanOrEqual(6);
    expect(s.view).toEqual({ tab: 'exploration', terrain_layer: 'belief', camera: 'human_1', first_person: true });
    expect(JSON.parse(JSON.stringify(s))).toEqual(s);
  });
});

describe('pages for language models', () => {
  it('ships llms.txt, about.html, robots.txt and a sitemap, and labels the data honestly', () => {
    for (const f of ['llms.txt', 'about.html', 'robots.txt', 'sitemap.xml']) expect(existsSync(join(web, 'public', f))).toBe(true);
    const llms = readFileSync(join(web, 'public', 'llms.txt'), 'utf8');
    expect(llms.startsWith('# ')).toBe(true);
    expect(llms).toMatch(/REPLAY of simulated data, not a live mission/);
    expect(llms).toMatch(/AI_USAGE\.md/);
    const index = readFileSync(join(web, 'index.html'), 'utf8');
    const ld = JSON.parse(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/.exec(index)![1]);
    expect(ld['@type']).toBe('WebApplication');
    expect(ld.description).toMatch(/not a live mission/);
    expect(index).toMatch(/href="\.\/llms\.txt"/);
  });
});
