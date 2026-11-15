import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { fromGatewayPackage, parseJsonLines } from '../src/data/gatewayReplay';
import { latestMapVersion, retrospectiveShapeAllowed, shapeGrid } from '../src/lib/layers';
import { viewAt } from '../src/lib/replay';
import type { RasterSet } from '../src/types/replay';

// Synthetic shape-only case: a later observation changes a valid cell, never NoData.
const rasters = {
  run_id: 'shape-test', rows: 2, cols: 2, prior: [0, null, 0, 0],
  versions: {
    1: { belief: [0, null, 0, 0], sigma: [3, null, 3, 3], observed: [] },
    2: { belief: [0, null, 0, 38], sigma: [3, null, 3, 0.5], observed: [3] },
  },
} as unknown as RasterSet;

describe('terrain shape on the updated map', () => {
  it('defaults to causal geometry for both belief and uncertainty, preserving NoData', () => {
    expect(shapeGrid(rasters, 'belief', 1)).toBe(rasters.versions['1'].belief);
    expect(shapeGrid(rasters, 'sigma', 1)).toBe(rasters.versions['1'].belief);
    expect(shapeGrid(rasters, 'belief', 2)).toBe(rasters.versions['2'].belief);
    expect(shapeGrid(rasters, 'belief', 1)[1]).toBeNull();
  });

  it('opts in only for explicitly illustrative SIMULATION manifests', () => {
    expect(retrospectiveShapeAllowed({ illustrative: true, source_mode: 'SIMULATION' })).toBe(true);
    expect(retrospectiveShapeAllowed({ illustrative: false, source_mode: 'SIMULATION' })).toBe(false);
    expect(retrospectiveShapeAllowed({ illustrative: true, source_mode: 'MOCK' })).toBe(false);
    expect(retrospectiveShapeAllowed({ illustrative: true, source_mode: 'UNKNOWN' })).toBe(false);
    expect(retrospectiveShapeAllowed({ illustrative: true })).toBe(false);
  });

  it('keeps an opted-in demo steady across both layers and times, with temporal tints and sigma unchanged', () => {
    const optIn = retrospectiveShapeAllowed({ illustrative: true, source_mode: 'SIMULATION' });
    expect(latestMapVersion(rasters)).toBe(2);
    for (const layer of ['belief', 'sigma'] as const) for (const version of [1, 2]) {
      expect(shapeGrid(rasters, layer, version, optIn)).toBe(rasters.versions['2'].belief);
      expect(shapeGrid(rasters, layer, version, optIn)[1]).toBeNull();
    }
    expect(rasters.versions['1'].observed).toEqual([]);
    expect(rasters.versions['1'].sigma).toEqual([3, null, 3, 3]);
  });

  it('keeps the orbital prior for the prior and slope layers', () => {
    for (const optIn of [false, true]) {
      expect(shapeGrid(rasters, 'prior', 2, optIn)).toBe(rasters.prior);
      expect(shapeGrid(rasters, 'slope', 2, optIn)).toBe(rasters.prior);
    }
  });

  it('does not reveal the recorder002 cell528 observation before its actual map-version transition', () => {
    const dir = join(__dirname, '..', 'public', 'replay', 'recorded-recovery-002');
    const read = (name: string) => JSON.parse(readFileSync(join(dir, name), 'utf8'));
    const bundle = fromGatewayPackage(read('manifest.json'), parseJsonLines(readFileSync(join(dir, 'timeline.jsonl'), 'utf8')),
      read('public_rasters.json'), read('snapshot.json'));
    const optIn = retrospectiveShapeAllowed(bundle.manifest);
    expect(bundle.manifest.source_mode).toBe('MOCK');
    expect(optIn).toBe(false);
    const changed = bundle.timeline.frames.find((frame) => frame.mission_state.map_version === 2)!;
    expect(changed.timestamp_sim_s).toBeGreaterThan(4);
    expect(changed.timestamp_sim_s).toBeLessThan(4.3);
    const before = viewAt(bundle, changed.timestamp_sim_s - 0.001).state!.map_version;
    const after = viewAt(bundle, changed.timestamp_sim_s).state!.map_version;
    expect(before).toBe(1);
    expect(after).toBe(2);
    for (const layer of ['belief', 'sigma'] as const) {
      expect(shapeGrid(bundle.rasters, layer, before, optIn)[528]).toBe(-2571.99755859375);
      expect(shapeGrid(bundle.rasters, layer, after, optIn)[528]).toBe(-2568.99755859375);
      expect(shapeGrid(bundle.rasters, layer, after, optIn)[528]! - shapeGrid(bundle.rasters, layer, before, optIn)[528]!).toBe(3);
    }
    expect(bundle.rasters.versions['1'].observed).toEqual([]);
    expect(bundle.rasters.versions['2'].observed).toEqual([528]);
  });
});
