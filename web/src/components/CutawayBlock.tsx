import { useEffect, useMemo } from 'react';
import * as THREE from 'three';
import type { TerrainMeta } from '../types/icd';
import { rasterizeUnits, type GeologyData } from '../lib/geology';
import { blockDepthM, columnBelow, surfaceSymbolAt } from '../lib/strata';
import { smoothHeightAt } from '../lib/terrainSmooth';
import { SURFACE_DETAIL_GLSL, MESH_SUBDIVISION } from './TerrainView';

const GEO_GRID = 400;

interface Props {
  meta: TerrainMeta;
  /** Heights of the layer on screen (same grid the terrain mesh uses). */
  heights: ReadonlyArray<number | null>;
  /** Geologic map for the schematic strata; null draws plain walls (no claim about what is below). */
  geology: GeologyData | null;
  verticalExaggeration: number;
}

/** Plain wall tone when no strata are shown: a neutral rock colour, not a measured layer. */
const PLAIN_ROCK: [number, number, number] = [0.33, 0.22, 0.16];

/**
 * Cut-away block: vertical walls along the crop edges and a base, so the terrain reads as a
 * solid piece of ground instead of a sheet. With a geologic map the walls show a SCHEMATIC
 * stratigraphic column under each edge point (surface unit from SIM 3464, then older strata;
 * thicknesses schematic, see lib/strata.ts); without one they are a single plain rock tone
 * that claims nothing about the subsurface. Display only; it never changes the terrain data.
 */
export function CutawayBlock({ meta, heights, geology, verticalExaggeration }: Props) {
  const grid = useMemo(() => (geology ? rasterizeUnits(geology, GEO_GRID) : null), [geology]);

  const geometry = useMemo(() => {
    const step = meta.resolution_m / MESH_SUBDIVISION;
    const x0 = meta.origin_x_m + meta.resolution_m / 2;
    const y0 = meta.origin_y_m + meta.resolution_m / 2;
    const x1 = meta.origin_x_m + (meta.cols - 0.5) * meta.resolution_m;
    const y1 = meta.origin_y_m + (meta.rows - 0.5) * meta.resolution_m;
    let lo = Infinity;
    for (const h of heights) if (h != null && h < lo) lo = h;
    const depth = blockDepthM(Math.max(meta.rows, meta.cols) * meta.resolution_m, !!geology);
    const bottom = lo - depth;
    const columnAt = (x: number, y: number): Array<{ thicknessM: number; rgb: [number, number, number] }> => {
      if (!geology || !grid) return [{ thicknessM: depth, rgb: PLAIN_ROCK }];
      const fx = geology.frame;
      return columnBelow(surfaceSymbolAt(geology, grid, GEO_GRID, Math.floor(((y - fx.origin_y_m) / fx.height_m) * GEO_GRID), Math.floor(((x - fx.origin_x_m) / fx.width_m) * GEO_GRID)));
    };
    const hAt = (x: number, y: number) => smoothHeightAt(meta, heights, x, y) ?? lo;

    // Edge polylines (counter-clockwise seen from above): south, east, north, west.
    const pts: Array<[number, number]> = [];
    const n = Math.round((x1 - x0) / step);
    const m = Math.round((y1 - y0) / step);
    for (let i = 0; i <= n; i++) pts.push([x0 + i * step, y0]);
    for (let j = 1; j <= m; j++) pts.push([x1, y0 + j * step]);
    for (let i = n - 1; i >= 0; i--) pts.push([x0 + i * step, y1]);
    for (let j = m - 1; j >= 0; j--) pts.push([x0, y0 + j * step]);

    const pos: number[] = [];
    const col: number[] = [];
    const quad = (ax: number, ay: number, az0: number, az1: number, bx: number, by: number, bz0: number, bz1: number, c: [number, number, number]) => {
      // Three.js: x east, y up, z = -north. az0/bz0 bottom, az1/bz1 top.
      const v = [
        [ax, az1, -ay], [ax, az0, -ay], [bx, bz0, -by],
        [ax, az1, -ay], [bx, bz0, -by], [bx, bz1, -by],
      ];
      for (const p of v) {
        pos.push(p[0], p[1], p[2]);
        col.push(c[0], c[1], c[2]);
      }
    };
    for (let k = 0; k + 1 < pts.length; k++) {
      const [ax, ay] = pts[k];
      const [bx, by] = pts[k + 1];
      const ha = hAt(ax, ay);
      const hb = hAt(bx, by);
      const layers = columnAt((ax + bx) / 2, (ay + by) / 2);
      let d = 0;
      layers.forEach((s, li) => {
        const last = li === layers.length - 1;
        const topA = ha - d, topB = hb - d;
        d += s.thicknessM;
        const botA = last ? bottom : Math.max(bottom, ha - d);
        const botB = last ? bottom : Math.max(bottom, hb - d);
        if (topA > botA || topB > botB) quad(ax, ay, botA, topA, bx, by, botB, topB, s.rgb);
      });
    }
    // Dark base plate.
    const base: [number, number, number] = [0.12, 0.09, 0.08];
    const b = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
    for (const [i, j, k] of [[0, 2, 1], [0, 3, 2]]) {
      for (const q of [b[i], b[j], b[k]]) {
        pos.push(q[0], bottom, -q[1]);
        col.push(...base);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.computeVertexNormals();
    return g;
  }, [meta, heights, geology, grid]);

  const material = useMemo(() => {
    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 0, side: THREE.DoubleSide });
    mat.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWall;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWall = position;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>\nvarying vec3 vWall;\n${SURFACE_DETAIL_GLSL}`)
        .replace(
          '#include <color_fragment>',
          `#include <color_fragment>
          {
            // Rock texture: horizontal bedding streaks, grain and dark cracks (display only).
            vec2 w = vec2(vWall.x - vWall.z, vWall.y);
            float bed = 0.82 + 0.3 * gFbm(vec2(w.x * 0.04, w.y * 1.6));
            float grain = 0.9 + 0.2 * gFbm(w * 2.5);
            float crack = smoothstep(0.035, 0.0, abs(gFbm(w * vec2(0.12, 0.5)) - 0.5)) * 0.45;
            diffuseColor.rgb *= bed * grain * (1.0 - crack);
          }`,
        );
    };
    mat.customProgramCacheKey = () => 'cutaway-strata-v6';
    return mat;
  }, []);

  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => material.dispose(), [material]);

  return <mesh geometry={geometry} material={material} scale={[1, verticalExaggeration, 1]} name="cutaway" />;
}
