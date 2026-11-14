import { useMemo } from 'react';
import * as THREE from 'three';
import type { ContextTerrainData } from '../types/replay';
import { useImageryTexture } from './TerrainView';

/**
 * Surroundings of the mission crop: the same CTX DTM over a larger square at a coarser cell
 * (scripts/extract-ctx-context.mjs), draped with the CTX orthomosaic of that square. Real
 * data, context only: it is never part of the mission map and is drawn slightly darker than
 * the crop. The crop's own footprint is left open so the two surfaces do not overlap.
 */
interface Props {
  data: ContextTerrainData;
  imageUrl: string | null;
  /** Footprint of the mission crop in local ENU metres; context cells inside it are not drawn. */
  hole: { origin_x_m: number; origin_y_m: number; width_m: number; height_m: number };
  verticalExaggeration: number;
}

/** Context is drawn a little darker so the mission crop stands out. */
const CONTEXT_SHADE = 0.78;

export function ContextTerrain({ data, imageUrl, hole, verticalExaggeration }: Props) {
  const texture = useImageryTexture(imageUrl);
  const geometry = useMemo(() => {
    const { rows, cols, resolution_m: res, origin_x_m: ox, origin_y_m: oy } = data.frame;
    const x0 = ox + res / 2;
    const y0 = oy + res / 2;
    const w = cols * res;
    const h = rows * res;
    const positions = new Float32Array(rows * cols * 3);
    const uvs = new Float32Array(rows * cols * 2);
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const i = r * cols + c;
        const x = x0 + c * res;
        const y = y0 + r * res;
        positions[i * 3] = x;
        positions[i * 3 + 1] = data.heights[i] ?? 0;
        positions[i * 3 + 2] = -y;
        uvs[i * 2] = (x - ox) / w;
        uvs[i * 2 + 1] = (y - oy) / h;
      }
    }
    // Leave the crop open: skip quads whose centre falls inside its footprint (shrunk by half a
    // cell so the context still reaches under the crop edge, with no gap).
    const hx0 = hole.origin_x_m + res / 2;
    const hx1 = hole.origin_x_m + hole.width_m - res / 2;
    const hy0 = hole.origin_y_m + res / 2;
    const hy1 = hole.origin_y_m + hole.height_m - res / 2;
    const index: number[] = [];
    for (let r = 0; r < rows - 1; r++) {
      for (let c = 0; c < cols - 1; c++) {
        const a = r * cols + c;
        const b = a + 1;
        const d = a + cols;
        const e = d + 1;
        if (data.heights[a] == null || data.heights[b] == null || data.heights[d] == null || data.heights[e] == null) continue;
        const cx = x0 + (c + 0.5) * res;
        const cy = y0 + (r + 0.5) * res;
        if (cx > hx0 && cx < hx1 && cy > hy0 && cy < hy1) continue;
        index.push(a, b, d, b, e, d);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    g.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
    g.setIndex(index);
    g.computeVertexNormals();
    return g;
  }, [data, hole]);

  const material = useMemo(() => {
    const m = new THREE.MeshStandardMaterial({
      color: new THREE.Color(0.55, 0.36, 0.24),
      roughness: 1,
      metalness: 0,
      map: texture,
      polygonOffset: true, // the mission crop wins where the two touch
      polygonOffsetFactor: 2,
      polygonOffsetUnits: 2,
    });
    if (texture) {
      // Same basalt-to-dust mapping of the panchromatic CTX grey level as the mission crop.
      m.color.setRGB(1, 1, 1);
      m.onBeforeCompile = (shader) => {
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <map_fragment>',
          `#include <map_fragment>
          float lum = dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114));
          diffuseColor.rgb = mix(vec3(0.05, 0.025, 0.015), vec3(0.72, 0.42, 0.24), pow(lum, 0.85)) * ${CONTEXT_SHADE.toFixed(2)};`,
        );
      };
    }
    return m;
  }, [texture]);

  return <mesh geometry={geometry} material={material} scale={[1, verticalExaggeration, 1]} name="context-terrain" receiveShadow />;
}
