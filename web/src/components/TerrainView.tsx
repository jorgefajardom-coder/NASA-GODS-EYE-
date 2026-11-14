import { useEffect, useMemo } from 'react';
import * as THREE from 'three';
import type { TerrainMeta } from '../types/icd';
import type { RasterSet } from '../types/replay';
import { cellCenter, enuToThree } from '../lib/coords';
import { elevationColor, finiteRange, heightGrid, sigmaColor, versionKey, type TerrainLayer } from '../lib/layers';

interface Props {
  meta: TerrainMeta;
  rasters: RasterSet;
  layer: TerrainLayer;
  mapVersion: number;
  verticalExaggeration: number;
  highlightObserved: boolean;
}

/**
 * Terrain mesh with one vertex per cell centre (ICD §1), so a cell, a route
 * waypoint and a marker at the same ENU point share the same 3D position (J-01).
 * Triangles touching a NoData cell are not drawn: no height is invented.
 */
export function TerrainView({ meta, rasters, layer, mapVersion, verticalExaggeration, highlightObserved }: Props) {
  const heights = heightGrid(rasters, layer, mapVersion);
  const version = rasters.versions[versionKey(rasters, mapVersion)];

  const geometry = useMemo(() => {
    const { rows, cols } = meta;
    const positions = new Float32Array(rows * cols * 3);
    const colors = new Float32Array(rows * cols * 3);
    const [lo, hi] = finiteRange(rasters.prior);
    const observed = new Set(highlightObserved && layer === 'belief' ? version.observed : []);

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const i = r * cols + c;
        const { x, y } = cellCenter(meta, r, c);
        const h = heights[i];
        const [tx, ty, tz] = enuToThree({ x, y, z: h ?? 0 }, verticalExaggeration);
        positions.set([tx, ty, tz], i * 3);
        let rgb: [number, number, number];
        if (h == null) rgb = [0, 0, 0];
        else if (layer === 'sigma') rgb = sigmaColor(version.sigma[i] ?? 0);
        else rgb = elevationColor(h, lo, hi);
        if (observed.has(i)) rgb = [rgb[0] * 0.75 + 0.06, rgb[1] * 0.75 + 0.2, rgb[2] * 0.75 + 0.22];
        colors.set(rgb, i * 3);
      }
    }

    const index: number[] = [];
    for (let r = 0; r < rows - 1; r++) {
      for (let c = 0; c < cols - 1; c++) {
        const a = r * cols + c;
        const b = a + 1;
        const d = a + cols;
        const e = d + 1;
        if (heights[a] == null || heights[b] == null || heights[d] == null || heights[e] == null) continue;
        // Counter-clockwise seen from above (+Y in Three.js).
        index.push(a, b, d, b, e, d);
      }
    }

    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    g.setIndex(index);
    g.computeVertexNormals();
    return g;
  }, [meta, rasters, heights, version, layer, verticalExaggeration, highlightObserved]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  return (
    <mesh geometry={geometry} receiveShadow name="terrain">
      <meshStandardMaterial vertexColors roughness={0.95} metalness={0} side={THREE.DoubleSide} />
    </mesh>
  );
}
