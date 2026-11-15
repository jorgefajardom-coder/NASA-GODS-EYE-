import { describe, expect, it } from 'vitest';
import { latestMapVersion, shapeGrid } from '../src/lib/layers';
import type { RasterSet } from '../src/types/replay';

// Two-cell run: map v2 observes a scarp in cell 1 that the orbital prior does not show.
const rasters = {
  run_id: 'shape-test', rows: 1, cols: 2, prior: [0, 0],
  versions: {
    1: { belief: [0, 0], sigma: [3, 3], observed: [] },
    2: { belief: [0, 38], sigma: [3, 0.5], observed: [1] },
  },
} as unknown as RasterSet;

describe('terrain shape on the updated map', () => {
  it('draws the ground of the last map version from the start, so observed ground never rises suddenly', () => {
    expect(latestMapVersion(rasters)).toBe(2);
    expect(shapeGrid(rasters, 'belief', 1)).toEqual([0, 38]);
    expect(shapeGrid(rasters, 'belief', 2)).toEqual([0, 38]);
  });

  it('keeps the orbital prior for the prior and slope layers', () => {
    expect(shapeGrid(rasters, 'prior', 2)).toEqual([0, 0]);
    expect(shapeGrid(rasters, 'slope', 2)).toEqual([0, 0]);
  });
});
