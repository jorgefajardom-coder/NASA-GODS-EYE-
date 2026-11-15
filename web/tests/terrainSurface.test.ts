import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { BufferAttribute, BufferGeometry, DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { describe, expect, it } from 'vitest';
import { createTerrainSurface, meshSubdivision, terrainSurfaceHeight, type TerrainSurface } from '../src/lib/terrainSurface';
import { smoothHeightAt } from '../src/lib/terrainSmooth';
import { morphHeights } from '../src/components/TerrainView';

const meta = { rows: 2, cols: 2, resolution_m: 1, origin_x_m: 0, origin_y_m: 0 };

/** Independent oracle: intersect the actual Float32/index buffer used to draw. */
function rayHeight(surface: TerrainSurface, x: number, north: number, exaggeration = 1): number | null {
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(surface.positions, 3));
  geometry.setIndex(new BufferAttribute(surface.indices, 1));
  const material = new MeshBasicMaterial({ side: DoubleSide });
  const mesh = new Mesh(geometry, material);
  mesh.scale.y = exaggeration;
  mesh.updateMatrixWorld();
  const hit = new Raycaster(new Vector3(x, 10000, -north), new Vector3(0, -1, 0)).intersectObject(mesh)[0];
  geometry.dispose();
  material.dispose();
  return hit?.point.y ?? null;
}

describe('the rendered terrain surface', () => {
  it('samples the actual diagonal instead of a bilinear or bicubic patch', () => {
    const surface = createTerrainSurface(meta, [0, 0, 0, 10], 1);
    expect(smoothHeightAt(meta, surface.heights, 1, 1)).toBe(2.5);
    expect(terrainSurfaceHeight(surface, 1, 1)).toBe(0);
    expect(terrainSurfaceHeight(surface, 1, 1)).toBe(rayHeight(surface, 1, 1));
    for (const [x, north] of [[.7, .8], [1.2, 1.3]]) {
      expect(terrainSurfaceHeight(surface, x, north)).toBeCloseTo(rayHeight(surface, x, north)!, 8);
    }
  });

  it.each([1, 3])('matches Three.js triangles at subdivision %s, including negative absolute heights', (subdivision) => {
    const m = { rows: 4, cols: 4, resolution_m: 4, origin_x_m: -64, origin_y_m: -64 };
    const heights = Array.from({ length: 16 }, (_, i) => -2570 + Math.sin(i) * 3);
    const before = [...heights];
    const surface = createTerrainSurface(m, heights, subdivision);
    for (const exaggeration of [1, 3]) for (const [x, north] of [[-61.5, -60.7], [-57.1, -55.2], [-53, -52.3]]) {
      expect(terrainSurfaceHeight(surface, x, north, exaggeration)).toBeCloseTo(rayHeight(surface, x, north, exaggeration)!, 7);
    }
    expect(heights).toEqual(before);
  });

  it('has no surface where no triangle is drawn, including NoData and outside bounds', () => {
    const surface = createTerrainSurface(meta, [0, null, 0, 10], 1);
    expect(surface.indices).toHaveLength(0);
    expect(terrainSurfaceHeight(surface, 1, 1)).toBeNull();
    expect(rayHeight(surface, 1, 1)).toBeNull();
    const good = createTerrainSurface(meta, [0, 0, 0, 10], 1);
    for (const [x, north] of [[.49, 1], [1, .49], [1.51, 1], [1, 1.51]]) expect(terrainSurfaceHeight(good, x, north)).toBeNull();
  });

  it.each([1, 3])('reads the live renderer buffer throughout a paused height morph at exaggeration %s', (exaggeration) => {
    const surface = createTerrainSurface(meta, [-2571, -2570, -2572, -2568], 3);
    const target = surface.positions.slice();
    const rest = surface.restHeights.slice();
    const from = target.slice();
    for (let i = 1; i < from.length; i += 3) from[i] = -2580;
    for (const progress of [0, .2, .5, .8, 1]) {
      // Same function/buffer mutation that TerrainView performs each frame;
      // neither playback time nor a React rerender is needed by the sampler.
      morphHeights(from, target, progress, surface.positions);
      for (const [x, north] of [[.7, .8], [1.2, 1.3]]) {
        expect(terrainSurfaceHeight(surface, x, north, exaggeration)).toBeCloseTo(rayHeight(surface, x, north, exaggeration)!, 7);
      }
    }
    expect(surface.restHeights).toEqual(rest);
  });

  it('retains a drawn triangle edge next to a NoData hole without filling the hole', () => {
    const surface = createTerrainSurface({ ...meta, cols: 4 }, [0, 0, 10, null, 0, 10, 10, null], 1);
    expect(terrainSurfaceHeight(surface, 1.5, 1)).toBeCloseTo(rayHeight(surface, 1.5, 1)!, 8);
    expect(terrainSurfaceHeight(surface, 1.5, 1)).toBe(5);
    expect(terrainSurfaceHeight(surface, 1.5001, 1)).toBeNull();
  });

  it('covers the audited Gale human position with the same mesh as the renderer', () => {
    const dir = join(__dirname, '..', 'public', 'replay', 'gale-demo');
    const read = (name: string) => JSON.parse(readFileSync(join(dir, name), 'utf8'));
    const manifest = read('manifest.json'), rasters = read('rasters.json'), timeline = read('timeline.json');
    const frame = timeline.frames.find((f: { timestamp_sim_s: number }) => f.timestamp_sim_s === 2976);
    const human = frame.mission_state.agents.find((a: { agent_kind: string }) => a.agent_kind === 'HUMAN');
    const p = human.pose.position;
    const grid = rasters.versions[String(frame.mission_state.map_version)].belief;
    expect(meshSubdivision(manifest.terrain_meta)).toBe(1);
    const surface = createTerrainSurface(manifest.terrain_meta, grid);
    const actual = terrainSurfaceHeight(surface, p.x, p.y)!;
    expect(actual).toBeCloseTo(-287.6643688201904, 7);
    expect(actual).toBeCloseTo(rayHeight(surface, p.x, p.y)!, 7);
    expect(Math.abs(smoothHeightAt(manifest.terrain_meta, grid, p.x, p.y)! - actual)).toBeGreaterThan(.45);
    expect(human.pose.position).toEqual(p);
  });
});
