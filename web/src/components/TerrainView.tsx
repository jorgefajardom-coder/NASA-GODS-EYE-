import { useThree } from '@react-three/fiber';
import { useEffect, useMemo, useState } from 'react';
import * as THREE from 'three';
import type { TerrainMeta } from '../types/icd';
import type { RasterSet } from '../types/replay';
import { elevationColor, finiteRange, heightGrid, sigmaColor, slopeColor, versionKey, type TerrainLayer } from '../lib/layers';
import { slopeDegrees } from '../lib/slope';
import { bilinear, upsampleGrid } from '../lib/terrainSmooth';

/** Mesh vertices per source cell interval. Source cell centres are always vertices (J-01). */
export const MESH_SUBDIVISION = 3;
/** Distance (m) at which the cosmetic ground grain has faded out; the first-person view reaches farther. */
export const DETAIL_FAR_M = 180;
export const DETAIL_FAR_POV_M = 480;
export const CONTOUR_MINOR_M = 10;
export const CONTOUR_MAJOR_M = 50;

/**
 * Cosmetic regolith grain for close views. The terrain data stops at 5-20 m, so walking views
 * look flat; this adds procedural grit and pebble speckle from the ground
 * position. It is NOT measured detail: it is labelled in the view options, can be turned off,
 * and vanishes beyond ~220 m of camera distance, so it never changes the map at mission scale.
 */
export const SURFACE_DETAIL_GLSL = /* glsl */ `
// Ground metres covered by one pixel at this fragment; set before the detail functions run.
// Each detail level fades out once it is smaller than a pixel, which removes the moire at distance.
float gPx = 0.0;
float gKeep(float lo, float hi) { return 1.0 - smoothstep(lo, hi, gPx); }
float gHash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float gNoise(vec2 p) {
  vec2 i = floor(p); vec2 f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(gHash(i), gHash(i + vec2(1.0, 0.0)), u.x), mix(gHash(i + vec2(0.0, 1.0)), gHash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float gFbm(vec2 p) { float a = 0.5, s = 0.0; for (int k = 0; k < 5; k++) { s += a * gNoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s; }
// One stone per cell of a jittered grid, each with its own size, elongation, rotation,
// irregular outline and tone. Returns (coverage 0..1, tone -1..1).
vec2 gStones(vec2 p, float sizeMin, float sizeMax, float presence) {
  vec2 i = floor(p); vec2 f = fract(p); float cover = 0.0; float tone = 0.0;
  for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
    vec2 o = vec2(float(x), float(y));
    vec2 c = i + o;
    if (gHash(c + 3.1) > presence) continue;                 // not every cell has a stone
    vec2 centre = o + vec2(gHash(c), gHash(c + 31.7)) - f;
    float ang = gHash(c + 13.9) * 6.2831;
    float stretch = mix(1.0, 2.6, gHash(c + 5.3));            // round to elongated
    mat2 rot = mat2(cos(ang), -sin(ang), sin(ang), cos(ang));
    vec2 q = rot * centre; q.x /= stretch;
    float radius = mix(sizeMin, sizeMax, pow(gHash(c + 8.8), 2.2)); // many small, few big
    float wobble = (gNoise(q * 9.0 + c) - 0.5) * 0.35 * radius;     // irregular outline
    float k = 1.0 - smoothstep(radius * 0.75, radius + wobble, length(q));
    if (k > cover) { cover = k; tone = gHash(c + 21.4) * 2.0 - 1.0; }
  }
  return vec2(cover, tone);
}
// Stones at three independent scales, clustered by a low-frequency density field and sampled
// through a warped domain so neither spacing nor shape repeats. Returns (coverage, tone).
vec2 gPebbles(vec2 g) {
  vec2 w = g + vec2(gFbm(g * 0.15), gFbm(g * 0.15 + 4.7)) * 2.5;
  float density = smoothstep(0.3, 0.85, gFbm(g * 0.045 + 5.0));
  vec2 a = gStones(w * 0.9 + 17.0, 0.05, 0.42, 0.15 + 0.35 * density) * vec2(gKeep(0.12, 0.35), 1.0);
  vec2 b = gStones(w * 2.3 + 41.0, 0.06, 0.35, 0.2 + 0.5 * density) * vec2(gKeep(0.05, 0.14), 1.0);
  vec2 c = gStones(w * 5.7 + 73.0, 0.08, 0.3, 0.25 + 0.55 * density) * vec2(gKeep(0.02, 0.06), 1.0);
  vec2 best = a;
  if (b.x * 0.75 > best.x) best = vec2(b.x * 0.75, b.y);
  if (c.x * 0.5 > best.x) best = vec2(c.x * 0.5, c.y);
  return best;
}
// Relief in metres-like units: metre-scale undulation, grit, pebbles. No ripples: their
// parallel crests read as lines on the ground and alias into moire at grazing angles.
float groundHeight(vec2 g) {
  float undulation = gFbm(g * 0.3 + gFbm(g * 0.07) * 2.0) * 0.4;
  float grit = gFbm(g * 7.0) * 0.035 * gKeep(0.015, 0.05);
  return undulation + grit + gPebbles(g).x * 0.07;
}
// Brightness modulation: dust patches, darker grit, pebble speckle.
float groundAlbedo(vec2 g) {
  float patches = gFbm(g * 0.06 + gFbm(g * 0.02) * 3.0) * 0.3 + 0.86;
  float grit = mix(1.0, 0.9 + gFbm(g * 9.0) * 0.18, gKeep(0.012, 0.04));
  vec2 st = gPebbles(g);
  float pebbles = 1.0 + st.x * (st.y * 0.35 - 0.12); // some stones darker, some lighter than the dust
  return patches * grit * pebbles;
}
// Bump mapping from screen-space derivatives (same method as three.js bumpmap_pars).
vec3 groundNormal(vec3 surfPos, vec3 surfNorm, float h, float faceDir) {
  vec3 sx = dFdx(surfPos); vec3 sy = dFdy(surfPos);
  vec2 dh = vec2(dFdx(h), dFdy(h)) * 1.0;
  vec3 r1 = cross(sy, surfNorm); vec3 r2 = cross(surfNorm, sx);
  float det = dot(sx, r1) * faceDir;
  vec3 grad = sign(det) * (dh.x * r1 + dh.y * r2);
  return normalize(abs(det) * surfNorm - grad);
}
`;

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
  /** Cosmetic, unmeasured surface grain at close range (default on in the viewer). */
  surfaceDetail?: boolean;
  /** A texture shown instead of the image (e.g. the geologic map), not tinted. Wins over `imagery`. */
  overlay?: { texture: THREE.Texture; extent: { origin_x_m: number; origin_y_m: number; width_m: number; height_m: number } } | null;
  /** Distance (m) where the cosmetic grain fades out (default DETAIL_FAR_M). */
  detailFarM?: number;
}

/**
 * Terrain mesh. Heights are interpolated between the source cell centres (bicubic, never
 * leaving the range of the nearest cells) so shading is smooth; the interpolation adds no
 * detail. Cell centres are exact vertices, so a marker, a mesh vertex and a waypoint at the
 * same ENU point coincide. Triangles touching NoData are not drawn. Contour lines are drawn
 * in the shader from the true height of each fragment.
 */
export function TerrainView({ meta, rasters, layer, mapVersion, verticalExaggeration, highlightObserved, contours, zOffsetM, imagery, overlay, surfaceDetail = true, detailFarM = DETAIL_FAR_M }: Props) {
  const heights = heightGrid(rasters, layer, mapVersion);
  const version = rasters.versions[versionKey(rasters, mapVersion)];
  const imageTexture = useImageryTexture(imagery?.url ?? null);
  const texture = overlay?.texture ?? imageTexture;
  // Drape only once the image has loaded, so a missing image leaves the height colours.
  const draped = !!texture && ((layer !== 'sigma' && layer !== 'slope') || !!overlay);
  // Slope of the measured orbital DTM, computed once per run.
  const slope = useMemo(() => slopeDegrees(rasters.prior, meta.rows, meta.cols, meta.resolution_m), [rasters.prior, meta]);
  const ext = overlay?.extent ?? imagery?.extent;

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
        else if (layer === 'slope') {
          const s = slope[Math.min(rows - 1, Math.round(r / f)) * cols + Math.min(cols - 1, Math.round(c / f))];
          rgb = s == null ? [0.25, 0.25, 0.25] : slopeColor(s); // grey = border cells without a full 3x3 window
        }
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
  }, [meta, rasters, heights, version, layer, highlightObserved, draped, ext, slope]);

  const uniforms = useMemo(() => ({ uContour: { value: 1 }, uOffset: { value: 0 }, uTint: { value: 1 }, uDetail: { value: 1 }, uDetailFar: { value: DETAIL_FAR_M } }), []);
  useEffect(() => {
    uniforms.uContour.value = contours ? 1 : 0;
    uniforms.uOffset.value = zOffsetM;
    uniforms.uTint.value = overlay ? 0 : 1; // only the panchromatic image is tinted
    // Cosmetic grain only on the real-surface views, never on the geologic map or uncertainty colours.
    uniforms.uDetail.value = surfaceDetail && !overlay && layer !== 'sigma' && layer !== 'slope' ? 1 : 0;
    uniforms.uDetailFar.value = detailFarM;
  }, [uniforms, contours, zOffsetM, overlay, surfaceDetail, layer, detailFarM]);

  const material = useMemo(() => {
    const m = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0, side: THREE.DoubleSide });
    m.onBeforeCompile = (shader) => {
      shader.uniforms.uContour = uniforms.uContour;
      shader.uniforms.uOffset = uniforms.uOffset;
      shader.uniforms.uTint = uniforms.uTint;
      shader.uniforms.uDetail = uniforms.uDetail;
      shader.uniforms.uDetailFar = uniforms.uDetailFar;
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying float vRealH;\nvarying vec2 vGround;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRealH = position.y;\nvGround = position.xz;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>\nvarying float vRealH;\nvarying vec2 vGround;\nuniform float uContour;\nuniform float uOffset;\nuniform float uTint;\nuniform float uDetail;\nuniform float uDetailFar;\n${SURFACE_DETAIL_GLSL}`)
        // Cosmetic surface grain (not measured): fades in below ~200 m of camera distance.
        .replace(
          '#include <color_fragment>',
          `#include <color_fragment>
          gPx = length(fwidth(vGround));
          float detailFade = uDetail * (1.0 - smoothstep(uDetailFar * 0.28, uDetailFar, length(vViewPosition)));
          if (detailFade > 0.0) diffuseColor.rgb *= mix(1.0, groundAlbedo(vGround), detailFade);`,
        )
        .replace(
          '#include <normal_fragment_maps>',
          `#include <normal_fragment_maps>
          if (detailFade > 0.0) normal = groundNormal(-vViewPosition, normal, groundHeight(vGround) * detailFade, faceDirection);`,
        )
        // The draped CTX image is panchromatic: map its grey level onto a basalt-to-dust ramp
        // (display only). The vertex colour (observed-cell tint) is applied next by color_fragment.
        .replace(
          '#include <map_fragment>',
          `#include <map_fragment>
          #ifdef USE_MAP
            float lum = dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114));
            diffuseColor.rgb = mix(diffuseColor.rgb, mix(vec3(0.05, 0.025, 0.015), vec3(0.72, 0.42, 0.24), pow(lum, 0.85)), uTint);
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
    m.customProgramCacheKey = () => 'terrain-contours-v8';
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
export function useImageryTexture(url: string | null): THREE.Texture | null {
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
