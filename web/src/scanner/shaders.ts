import * as THREE from 'three';
import { SCAN_CONFIG } from './ScanConfig';

/**
 * Shared scan uniforms: one object, read by the terrain, indicator and footprint shaders and
 * written once per frame by TerrainScanner from the scan state machine (no separate clocks).
 * Positions are Three.js world metres; the origin is the ground point (x, z) where the scan started.
 */
export const scanUniforms = {
  uScanOrigin: { value: new THREE.Vector2() },
  uScanRadius: { value: 0 },
  uScanWidth: { value: SCAN_CONFIG.widthM as number },
  uScanSpeed: { value: SCAN_CONFIG.speedMps as number },
  uScanColor: { value: new THREE.Color(SCAN_CONFIG.color) },
  uScanIntensity: { value: 0 },
  uScanTime: { value: 0 },
  uMaxDistance: { value: SCAN_CONFIG.rangeM as number },
  uFadeDuration: { value: SCAN_CONFIG.fadeS as number },
  uScanPersist: { value: SCAN_CONFIG.persistS as number },
  uScanContourStep: { value: SCAN_CONFIG.contourStepM as number },
};

export type ScanUniforms = typeof scanUniforms;

/** Adds the scan uniforms to a material shader (onBeforeCompile). */
export function attachScanUniforms(shader: { uniforms: Record<string, THREE.IUniform> }) {
  Object.assign(shader.uniforms, scanUniforms);
}

export const SCAN_PARS_GLSL = /* glsl */ `
uniform vec2 uScanOrigin;
uniform float uScanRadius;
uniform float uScanWidth;
uniform float uScanSpeed;
uniform vec3 uScanColor;
uniform float uScanIntensity;
uniform float uScanTime;
uniform float uMaxDistance;
uniform float uFadeDuration;
uniform float uScanPersist;
uniform float uScanContourStep;
// Seconds since the front passed a point at ground distance d (negative: not reached yet).
float scanSince(float d) { return uScanTime - d / uScanSpeed; }
// 1 while a swept point is kept, fading to 0 over uFadeDuration after uScanPersist.
float scanLife(float d) {
  float s = scanSince(d);
  return step(0.0, s) * (1.0 - smoothstep(uScanPersist, uScanPersist + uFadeDuration, s));
}
`;

/**
 * Terrain part (inserted after the terrain's own contours). Uses the terrain shader's vGround
 * (world x, z), vRealH (true height), uOffset, vNormal and vViewPosition. The front is measured on
 * the ground plane and drawn on the surface itself, so it climbs ridges and drops into valleys.
 * Edges: curvature of the smooth surface normal per metre of surface (a Sobel-like derivative of
 * the normal buffer computed in the fragment), which lights rims, scarps and breaks in slope.
 * A highlighted edge is a geometric discontinuity, not a scientific hazard.
 */
export const SCAN_TERRAIN_GLSL = /* glsl */ `
if (uScanIntensity > 0.001) {
  float sd = length(vGround - uScanOrigin);
  if (sd < uMaxDistance + uScanWidth * 2.0) {
    float rangeFade = 1.0 - smoothstep(uMaxDistance * 0.82, uMaxDistance, sd);
    // Bright front with a soft trailing glow.
    float df = sd - uScanRadius;
    float front = (1.0 - smoothstep(0.0, uScanWidth, abs(df))) * step(uScanRadius, uMaxDistance - 0.01);
    float wake = step(df, 0.0) * exp(df / (uScanWidth * 4.0)) * 0.35 * step(uScanRadius, uMaxDistance - 0.01);
    float life = scanLife(sd);
    // Temporary contour lines in the swept area, every uScanContourStep m of real height.
    float ch = (vRealH + uOffset) / uScanContourStep;
    float cw = fwidth(ch);
    float contour = (1.0 - smoothstep(0.5, 1.6, abs(fract(ch - 0.5) - 0.5) / max(cw, 1e-5))) * (1.0 - smoothstep(0.25, 0.6, cw));
    // Discontinuities: change of the smooth normal per metre of surface.
    vec3 sn = normalize(vNormal);
    float curv = length(fwidth(sn)) / max(length(fwidth(vViewPosition)), 1e-4);
    float edge = smoothstep(0.03, 0.12, curv);
    float k = front * 1.6 + wake + life * (0.45 * contour + 0.9 * edge + 0.06);
    gl_FragColor.rgb += uScanColor * k * rangeFade * uScanIntensity;
  }
}
`;

/** Indicator vertex/fragment shaders (instanced; per-instance ground distance aDist). */
export const INDICATOR_VERT = /* glsl */ `
${SCAN_PARS_GLSL}
attribute float aDist;
varying float vAlpha;
void main() {
  float since = scanSince(aDist);
  float shown = step(0.0, since) * scanLife(aDist);
  float pop = 1.0 + 0.8 * (1.0 - smoothstep(0.0, 0.25, since)); // brief pop as the front passes
  float edgeFade = 1.0 - smoothstep(uMaxDistance * 0.85, uMaxDistance, aDist);
  vAlpha = shown * edgeFade * uScanIntensity;
  vec3 p = position * pop;
  gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(p, 1.0);
}`;

export const INDICATOR_FRAG = /* glsl */ `
uniform vec3 uColor;
varying float vAlpha;
void main() {
  if (vAlpha < 0.01) discard;
  gl_FragColor = vec4(uColor, vAlpha * 0.95);
}`;
