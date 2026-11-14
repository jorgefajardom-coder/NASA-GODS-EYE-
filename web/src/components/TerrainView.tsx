import { useThree } from '@react-three/fiber';
import { useEffect, useMemo, useState } from 'react';
import * as THREE from 'three';
import type { TerrainMeta } from '../types/icd';
import type { RasterSet } from '../types/replay';
import { elevationColor, finiteRange, heightGrid, sigmaColor, versionKey, type TerrainLayer } from '../lib/layers';
import { bilinear, upsampleGrid } from '../lib/terrainSmooth';

/** Mesh vertices per source cell interval. Source cell centres are always vertices (J-01). */
export const MESH_SUBDIVISION = 3;
export const CONTOUR_MINOR_M = 10;
export const CONTOUR_MAJOR_M = 50;

interface Props {
  meta: TerrainMeta;
  rasters: RasterSet;
  layer: TerrainLayer;
  mapVersion: number;
  verticalExaggeration: number;
  highlightObserved: boolean;
  contours: boolean;
  /** Local z = elevation - offset, so contour lines can be drawn at true elevations. */
  zOffsetM: number;
  /** Orbital image to drape on the terrain (null = height colours only). Not used on the sigma layer. */
  imagery: { url: string; extent: { origin_x_m: number; origin_y_m: number; width_m: number; height_m: number } } | null;
}

/**
 * Terrain mesh. Heights are interpolated between the source cell centres (bicubic, never
 * leaving the range of the nearest cells) so shading is smooth; the interpolation adds no
 * detail. Cell centres are exact vertices, so a marker, a mesh vertex and a waypoint at the
 * same ENU point coincide. Triangles touching NoData are not drawn. Contour lines are drawn
 * in the shader from the true height of each fragment.
 */
export function TerrainView({ meta, rasters, layer, mapVersion, verticalExaggeration, highlightObserved, contours, zOffsetM, imagery }: Props) {
  const heights = heightGrid(rasters, layer, mapVersion);
  const version = rasters.versions[versionKey(rasters, mapVersion)];
  const texture = useImageryTexture(imagery?.url ?? null);
  // Drape only once the image has loaded, so a missing image leaves the height colours.
  const draped = !!texture && layer !== 'sigma';
  const ext = imagery?.extent;

  const geometry = useMemo(() => {
    const { rows, cols } = meta;
    const f = MESH_SUBDIVISION;
    const fine = upsampleGrid(heights, rows, cols, f);
    const R = fine.rows;
    const C = fine.cols;
    const step = meta.resolution_m / f;
    const x0 = meta.origin_x_m + meta.resolution_m / 2;
    const y0 = meta.origin_y_m + meta.resolution_m / 2;
    const [lo, hi] = finiteRange(rasters.prior);
    const observed = new Set(highlightObserved && layer === 'belief' ? version.observed : []);

    const positions = new Float32Array(R * C * 3);
    const colors = new Float32Array(R * C * 3);
    const uvs = new Float32Array(R * C * 2);
    for (let r = 0; r < R; r++) {
      for (let c = 0; c < C; c++) {
        const i = r * C + c;
        const h = fine.data[i];
        // Three.js frame: x east, y up, z = -north. The vertical exaggeration is applied on the mesh scale.
        positions[i * 3] = x0 + c * step;
        positions[i * 3 + 1] = h ?? 0;
        positions[i * 3 + 2] = -(y0 + r * step);
        // Image coordinates: u east, v north (texture flipY puts image row 0, the north edge, at v = 1).
        if (ext) {
          uvs[i * 2] = (x0 + c * step - ext.origin_x_m) / ext.width_m;
          uvs[i * 2 + 1] = (y0 + r * step - ext.origin_y_m) / ext.height_m;
        }
        let rgb: [number, number, number];
        if (h == null) rgb = [0, 0, 0];
        else if (draped) rgb = [1, 1, 1]; // the image gives the colour; observed cells are still tinted below
        else if (layer === 'sigma') rgb = sigmaColor(bilinear(version.sigma, rows, cols, c / f, r / f));
        else rgb = elevationColor(h, lo, hi);
        if (observed.has(Math.round(r / f) * cols + Math.round(c / f))) rgb = [rgb[0] * 0.7 + 0.04, rgb[1] * 0.7 + 0.2, rgb[2] * 0.7 + 0.24];
        colors.set(rgb, i * 3);
      }
    }

    const index: number[] = [];
    for (let r = 0; r < R - 1; r++) {
      for (let c = 0; c < C - 1; c++) {
        const a = r * C + c;
        const b = a + 1;
        const d = a + C;
        const e = d + 1;
        if (fine.data[a] == null || fine.data[b] == null || fine.data[d] == null || fine.data[e] == null) continue;
        // Counter-clockwise seen from above (+Y in Three.js).
        index.push(a, b, d, b, e, d);
      }
    }

    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    g.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
    g.setIndex(index);
    g.computeVertexNormals();
    return g;
  }, [meta, rasters, heights, version, layer, highlightObserved, draped, ext]);

  const uniforms = useMemo(() => ({ uContour: { value: 1 }, uOffset: { value: 0 } }), []);
  useEffect(() => {
    uniforms.uContour.value = contours ? 1 : 0;
    uniforms.uOffset.value = zOffsetM;
  }, [uniforms, contours, zOffsetM]);

  const material = useMemo(() => {
    const m = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0, side: THREE.DoubleSide });
    m.onBeforeCompile = (shader) => {
      shader.uniforms.uContour = uniforms.uContour;
      shader.uniforms.uOffset = uniforms.uOffset;
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying float vRealH;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRealH = position.y;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying float vRealH;\nuniform float uContour;\nuniform float uOffset;')
        // The draped CTX image is panchromatic: map its grey level onto a basalt-to-dust ramp
        // (display only). The vertex colour (observed-cell tint) is applied next by color_fragment.
        .replace(
          '#include <map_fragment>',
          `#include <map_fragment>
          #ifdef USE_MAP
            float lum = dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114));
            diffuseColor.rgb = mix(vec3(0.05, 0.025, 0.015), vec3(0.72, 0.42, 0.24), pow(lum, 0.85));
          #endif`,
        )
        .replace(
          '#include <dithering_fragment>',
          `#include <dithering_fragment>
          {
            float h = vRealH + uOffset;
            float xm = h / ${CONTOUR_MINOR_M.toFixed(1)};
            float xM = h / ${CONTOUR_MAJOR_M.toFixed(1)};
            float dm = fwidth(xm);
            float dM = fwidth(xM);
            float lm = (1.0 - smoothstep(0.6, 1.5, abs(fract(xm - 0.5) - 0.5) / max(dm, 1e-5))) * (1.0 - smoothstep(0.12, 0.45, dm));
            float lM = (1.0 - smoothstep(0.8, 1.8, abs(fract(xM - 0.5) - 0.5) / max(dM, 1e-5))) * (1.0 - smoothstep(0.12, 0.45, dM));
            float k = uContour * max(0.22 * lm, 0.6 * lM);
            gl_FragColor.rgb = mix(gl_FragColor.rgb, vec3(0.79, 0.84, 0.87), k);
          }`,
        );
    };
    m.customProgramCacheKey = () => 'terrain-contours-v2';
    return m;
  }, [uniforms]);

  useEffect(() => {
    material.map = draped ? texture : null;
    material.needsUpdate = true;
  }, [material, texture, draped]);

  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => material.dispose(), [material]);

  return <mesh geometry={geometry} material={material} scale={[1, verticalExaggeration, 1]} name="terrain" />;
}

/** Loads the draped image once per URL (sRGB, mipmapped, sharp at grazing angles). */
function useImageryTexture(url: string | null): THREE.Texture | null {
  const gl = useThree((st) => st.gl);
  const [tex, setTex] = useState<THREE.Texture | null>(null);
  useEffect(() => {
    if (!url) {
      setTex(null);
      return;
    }
    let disposed = false;
    let loaded: THREE.Texture | null = null;
    new THREE.TextureLoader().load(
      url,
      (t) => {
        if (disposed) return t.dispose();
        t.colorSpace = THREE.SRGBColorSpace;
        t.anisotropy = gl.capabilities.getMaxAnisotropy();
        t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
        loaded = t;
        setTex(t);
      },
      undefined,
      () => !disposed && setTex(null), // no image: height colours stay
    );
    return () => {
      disposed = true;
      loaded?.dispose();
    };
  }, [url, gl]);
  return tex;
}
