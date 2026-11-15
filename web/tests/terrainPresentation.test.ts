import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PerspectiveCamera, Vector3 } from 'three';
import { describe, expect, it } from 'vitest';
import type { TerrainMeta } from '../src/types/icd';
import type { ContextTerrainData, ReplayManifest } from '../src/types/replay';
import type { GeologyData } from '../src/lib/geology';
import {
  contextMatchesRun, geologyMatchesRun, orbitalSlopeNote, priorNativeSpacing,
  terrainFraming, terrainResolutionLabel,
} from '../src/lib/terrainPresentation';

const demo = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo');
const read = <T>(name: string) => JSON.parse(readFileSync(join(demo, name), 'utf8')) as T;
const manifest = read<ReplayManifest>('manifest.json');
const canonical: TerrainMeta = {
  ...manifest.terrain_meta, dataset_id: 'jezero_mvp', rows: 32, cols: 32, resolution_m: 4,
  origin_x_m: -64, origin_y_m: -64, origin_lat_deg: 18.45, origin_lon_deg: 77.45,
  vertical_datum: 'MOLA topography / DeltaGeoid (Mars 2000 Sphere, R=3396190 m)',
  sources: ['MRO/CTX (prior): CTX_DTM [20.0m, sha256=example]', 'MGS/MOLA (regional_context): MOLA DEM native resolution 463 m'],
};

describe('framing recorded terrain without changing the datum', () => {
  it.each([1, 3])('keeps absolute Jezero ground in the initial frustum at exaggeration %s', (exaggeration) => {
    const heights = Object.freeze([-2574, -2567]);
    const before = JSON.stringify(canonical);
    const frame = terrainFraming(canonical, heights, exaggeration);
    const camera = new PerspectiveCamera(38, 16 / 9, 1, frame.far);
    camera.position.set(...frame.position);
    camera.lookAt(new Vector3(...frame.target));
    camera.updateMatrixWorld();
    for (const x of [-64, 64]) for (const north of [-64, 64]) for (const z of heights) {
      const point = new Vector3(x, z * exaggeration, -north).project(camera);
      expect(Math.abs(point.x)).toBeLessThan(1);
      expect(Math.abs(point.y)).toBeLessThan(1);
      expect(Math.abs(point.z)).toBeLessThan(1);
    }
    expect(frame.target[1]).toBe((-2574 - 2567) * exaggeration / 2);
    expect(heights).toEqual([-2574, -2567]);
    expect(JSON.stringify(canonical)).toBe(before);
  });

  it('moves only the viewpoint when a dataset has another ENU origin', () => {
    const a = terrainFraming(canonical, [20, 30]);
    const b = terrainFraming({ ...canonical, origin_x_m: 936, origin_y_m: 1936 }, [20, 30]);
    expect(b.target).toEqual([a.target[0] + 1000, a.target[1], a.target[2] - 2000]);
    expect(b.position).toEqual([a.position[0] + 1000, a.position[1], a.position[2] - 2000]);
    expect(b.far).toBe(a.far);
  });
});

describe('native information versus computational grid', () => {
  it('keeps the 20 m CTX prior distinct from the 4 m grid and 463 m MOLA context', () => {
    expect(priorNativeSpacing(canonical)).toBe(20);
    expect(terrainResolutionLabel(canonical)).toBe('Grid 4 m · source 20 m native');
    expect(orbitalSlopeNote(canonical)).toContain('12 m computational window');
    expect(orbitalSlopeNote(canonical)).toContain('resampling adds no source detail');
    expect(priorNativeSpacing({ ...canonical, sources: [canonical.sources[1]] })).toBeNull();
  });

  it('reads the demo source spacing without imposing it on an unspecified dataset', () => {
    expect(priorNativeSpacing(manifest.terrain_meta)).toBe(20);
    expect(orbitalSlopeNote(manifest.terrain_meta)).toContain('12 m computational window');
    expect(terrainResolutionLabel({ ...canonical, sources: [] })).toContain('spacing not supplied');
  });
});

describe('optional layers stay bound to their own scenario', () => {
  const context = read<ContextTerrainData>('context.json');
  const geology = read<GeologyData>('geology.json');

  it('keeps the existing demo layers available in their original frame', () => {
    expect(contextMatchesRun(context, manifest)).toBe(true);
    expect(geologyMatchesRun(geology, manifest)).toBe(true);
  });

  it('does not transfer demo geology or surroundings to the 128 m recorder scene', () => {
    const recorded = { ...manifest, run_id: 'it-execution', terrain_meta: canonical, local_z_offset_m: undefined };
    expect(contextMatchesRun(context, recorded)).toBe(false);
    expect(geologyMatchesRun(geology, recorded)).toBe(false);
  });

  it('checks a context layer planetary origin, source hash and height reference independently', () => {
    expect(contextMatchesRun({ ...context, frame: { ...context.frame, centre_lat_deg: 18.45 } }, manifest)).toBe(false);
    expect(contextMatchesRun({ ...context, source: { sha256: 'another-product' } }, manifest)).toBe(false);
    expect(contextMatchesRun({ ...context, frame: { ...context.frame, local_z_offset_m: 0 } }, manifest)).toBe(false);
  });
});
