import { describe, expect, it } from 'vitest';
import { WORLDS, worldOfRun } from '../src/data/worlds';
import { OFFERED_RUNS } from '../src/data/replayAdapter';

describe('worlds', () => {
  it('has a unique id and run per world, and every scene is an offered run', () => {
    expect(new Set(WORLDS.map((w) => w.id)).size).toBe(WORLDS.length);
    const runs = WORLDS.map((w) => w.runId).filter((r): r is string => r != null);
    expect(new Set(runs).size).toBe(runs.length);
    for (const r of runs) expect(OFFERED_RUNS.some((o) => o.id === r)).toBe(true);
  });

  it('says why a world without a scene has none', () => {
    for (const w of WORLDS.filter((x) => x.runId == null)) expect(w.note).toMatch(/^No scene/);
  });

  it('finds the world of a run and none for a test package', () => {
    expect(worldOfRun('demo')?.id).toBe('jezero');
    expect(worldOfRun('gale-demo')?.id).toBe('gale');
    expect(worldOfRun('mock-vertical-001')).toBeNull();
  });
});
