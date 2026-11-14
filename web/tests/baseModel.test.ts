import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { readGlb } from '../scripts/glb.mjs';

/**
 * base.glb is the team's Blender base prepared by scripts/blender/prepare_base.py. BaseModel
 * places it whole on the drawn terrain, so it must carry no ground or rocks of its own, sit
 * on y = 0 at real scale, and stay a light, untextured web asset.
 */
const FILE = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'assets', 'models', 'base.glb');

type Vec3 = [number, number, number];
interface GltfNode {
  name: string;
  mesh?: number;
  translation?: Vec3;
  rotation?: [number, number, number, number];
  scale?: Vec3;
}
interface Gltf {
  scene?: number;
  scenes: Array<{ nodes: number[] }>;
  nodes: GltfNode[];
  meshes: Array<{ primitives: Array<{ indices?: number; attributes: Record<string, number> }> }>;
  accessors: Array<{ count: number; bufferView?: number; byteOffset?: number; componentType: number; min?: number[]; max?: number[] }>;
  bufferViews: Array<{ byteStride?: number }>;
  images?: unknown[];
  textures?: unknown[];
}
const glb = readGlb(readFileSync(FILE));
const json = glb.json as unknown as Gltf;
const roots = json.scenes[json.scene ?? 0].nodes.map((i) => json.nodes[i]);

/** Rotates v by quaternion q (x, y, z, w). */
function rotate(v: Vec3, [x, y, z, w]: [number, number, number, number]): Vec3 {
  const tx = 2 * (y * v[2] - z * v[1]);
  const ty = 2 * (z * v[0] - x * v[2]);
  const tz = 2 * (x * v[1] - y * v[0]);
  return [v[0] + w * tx + (y * tz - z * ty), v[1] + w * ty + (z * tx - x * tz), v[2] + w * tz + (x * ty - y * tx)];
}

/** Exact world bounds of the vertices of every top-level mesh node (float32 positions through its TRS). */
function bounds(): { min: Vec3; max: Vec3 } {
  const min: Vec3 = [Infinity, Infinity, Infinity];
  const max: Vec3 = [-Infinity, -Infinity, -Infinity];
  for (const n of roots) {
    if (n.mesh === undefined) continue;
    for (const p of json.meshes[n.mesh].primitives) {
      const a = json.accessors[p.attributes.POSITION];
      expect(a.componentType).toBe(5126); // FLOAT
      const view = glb.views[a.bufferView!];
      const stride = json.bufferViews[a.bufferView!].byteStride ?? 12;
      for (let i = 0; i < a.count; i++) {
        const o = (a.byteOffset ?? 0) + i * stride;
        const s = n.scale ?? [1, 1, 1];
        const v: Vec3 = [view.readFloatLE(o) * s[0], view.readFloatLE(o + 4) * s[1], view.readFloatLE(o + 8) * s[2]];
        const r = rotate(v, n.rotation ?? [0, 0, 0, 1]);
        const t = n.translation ?? [0, 0, 0];
        for (let k = 0; k < 3; k++) {
          min[k] = Math.min(min[k], r[k] + t[k]);
          max[k] = Math.max(max[k], r[k] + t[k]);
        }
      }
    }
  }
  return { min, max };
}

describe('base.glb', () => {
  it('has no ground or rocks of its own (the viewer draws the CTX terrain)', () => {
    expect(roots.length).toBeGreaterThan(10);
    expect(roots.filter((n) => /^(Terreno|Rocas)/.test(n.name))).toEqual([]);
  });

  it('sits on the ground at real scale, around the hub', () => {
    const { min, max } = bounds();
    expect(min[1]).toBeGreaterThan(-0.25); // footings may sink a few centimetres
    expect(min[1]).toBeLessThan(0.3);
    const width = max[0] - min[0];
    const depth = max[2] - min[2];
    const height = max[1] - min[1];
    for (const d of [width, depth]) {
      expect(d).toBeGreaterThan(15);
      expect(d).toBeLessThan(60);
    }
    expect(height).toBeGreaterThan(3);
    expect(height).toBeLessThan(12);
    expect(min[0]).toBeLessThan(0); // hub (origin) inside the footprint
    expect(max[0]).toBeGreaterThan(0);
  });

  it('carries no textures or images (no room for agency marks)', () => {
    expect(json.images ?? []).toHaveLength(0);
    expect(json.textures ?? []).toHaveLength(0);
  });

  it('stays a light web asset', () => {
    const tris = json.meshes
      .flatMap((m) => m.primitives)
      .reduce((sum, p) => sum + json.accessors[p.indices ?? p.attributes.POSITION].count / 3, 0);
    expect(tris).toBeLessThan(60000);
  });
});
