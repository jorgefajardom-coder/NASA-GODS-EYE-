import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { WORLDS, initialZoneIndex, stepZone, worldOfRun, zoneUrl } from '../src/data/worlds';
import { OFFERED_RUNS } from '../src/data/replayAdapter';

describe('zones', () => {
  it('has a unique id and run per zone, and every scene is an offered run', () => {
    expect(new Set(WORLDS.map((w) => w.id)).size).toBe(WORLDS.length);
    const runs = WORLDS.map((w) => w.runId).filter((r): r is string => r != null);
    expect(new Set(runs).size).toBe(runs.length);
    for (const r of runs) expect(OFFERED_RUNS.some((o) => o.id === r)).toBe(true);
    for (const w of WORLDS) expect(w.status === 'scene').toBe(w.runId != null);
  });

  it('says why a zone without a scene has none, and has no locked zones left', () => {
    for (const w of WORLDS.filter((x) => x.runId == null)) expect(w.note).toMatch(/^No scene/);
    expect(WORLDS.filter((w) => w.body === 'Mars').every((w) => w.status === 'scene')).toBe(true);
  });

  it('ships each scene package with its terrain, and rover stops only where a rover drove', () => {
    const dir = (w: { runId: string | null }) => join(__dirname, '..', 'public', 'replay', w.runId!);
    for (const w of WORLDS.filter((x) => x.status === 'scene')) {
      for (const f of ['manifest.json', 'rasters.json', 'timeline.json', 'routes.json', 'ctx_ortho.png']) expect(existsSync(join(dir(w), f))).toBe(true);
    }
    for (const id of ['elysium', 'melas']) expect(existsSync(join(dir(WORLDS.find((w) => w.id === id)!), 'rover_stops.json'))).toBe(false);
    for (const id of ['gusev', 'meridiani']) expect(existsSync(join(dir(WORLDS.find((w) => w.id === id)!), 'rover_stops.json'))).toBe(true);
  });

  it('shows every scene with the same orthomosaic its terrain is draped with, and every card image exists', () => {
    for (const w of WORLDS.filter((x) => x.status === 'scene')) expect(w.image).toBe(`replay/${w.runId}/ctx_ortho.png`);
    for (const w of WORLDS) if (w.image) expect(existsSync(join(__dirname, '..', 'public', w.image))).toBe(true);
  });

  it('finds the zone of a run and none for a test package', () => {
    expect(worldOfRun('demo')?.id).toBe('jezero');
    expect(worldOfRun('gale-demo')?.id).toBe('gale');
    expect(worldOfRun('melas-demo')?.id).toBe('melas');
    expect(worldOfRun('mock-vertical-001')).toBeNull();
  });

  it('opens on the current zone, wraps around and builds the travel URL', () => {
    expect(WORLDS[initialZoneIndex('gale-demo')].id).toBe('gale');
    expect(WORLDS[initialZoneIndex('mock-vertical-001')].status).toBe('scene');
    expect(stepZone(0, -1)).toBe(WORLDS.length - 1);
    expect(stepZone(WORLDS.length - 1, 1)).toBe(0);
    expect(zoneUrl('http://localhost:5173/?run=demo&lite=1', 'gale-demo')).toBe('http://localhost:5173/?run=gale-demo&lite=1');
  });

  it('says where every site comes from: NASA stops, science sites or landing sites, choices of the generator, fictitious POIs', () => {
    for (const w of WORLDS.filter((x) => x.status === 'scene')) {
      const dir = join(__dirname, '..', 'public', 'replay', w.runId!);
      const m = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8')) as { pois: { id: string; source?: { basis: string; text: string } }[] };
      for (const p of m.pois) expect(p.source?.text).toBeTruthy();
      // C and D are real NASA science sites where the mission has them (rover worlds), fictitious otherwise.
      for (const id of ['C', 'D']) expect(m.pois.find((p) => p.id === id)?.source?.basis).toBe(['elysium', 'melas'].includes(w.id) ? 'fictitious' : 'nasa');
      const hasStops = existsSync(join(dir, 'rover_stops.json'));
      for (const id of ['A', 'B']) expect(m.pois.find((p) => p.id === id)?.source?.basis).toBe(hasStops ? 'nasa' : 'chosen');
    }
  });

});
