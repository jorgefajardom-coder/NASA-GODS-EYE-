import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef, useState, type RefObject } from 'react';
import * as THREE from 'three';
import { assetUrl } from '../data/replayAdapter';
import { celestialToLocal, daylight, marsSun, type Enu, type StarCatalogue } from '../lib/marsSky';
import { SUN_DIR, SUN_FROM } from '../lib/sun';

/**
 * Sky of the 3D view at the real present time at the site (the same instant as the "Jezero LMST"
 * clock): the Sun where Mars24 puts it, a dusty butterscotch day sky with a blue glow around the Sun
 * (forward scattering, strongest at sunrise and sunset), and at night the naked-eye stars of the
 * Yale Bright Star Catalogue placed with the IAU rotation model of Mars (lib/marsSky). The horizon
 * colour also tints the haze. Planets and Mars's moons are not drawn. The key light follows the Sun
 * (direction, warmth and strength by elevation) and blends at night to a dim overhead fill so the
 * terrain stays readable (a display choice). `?skytime=<ISO date>` shows another instant. Display only.
 */

const DAY_ZENITH = new THREE.Color('#5c4434');
const DAY_HORIZON = new THREE.Color('#6e5242'); // the viewer's haze colour
const NIGHT_ZENITH = new THREE.Color('#03050a');
const NIGHT_HORIZON = new THREE.Color('#0b0c12');
const TWILIGHT_GLOW = new THREE.Color('#6f8fae');
const SUN_HIGH = new THREE.Color('#fff1e0');
const SUN_LOW = new THREE.Color('#ffc996');
const NIGHT_FILL = new THREE.Color('#8fa3c8');
/** Night fill: from almost overhead, slightly from the east, so relief still reads. */
const NIGHT_DIR = new THREE.Vector3(0.25, 1, 0.1).normalize();
/** Artificial light: the viewer's original display direction (high, from the west-south-west). */
const ARTIFICIAL_DIR = new THREE.Vector3(-1.2, 0.55, 0.35).normalize();

/** ENU direction -> Three.js direction (x, y, z) = (east, up, -north). */
const toThree = ([e, n, u]: Enu, out: THREE.Vector3) => out.set(e, u, -n);

function skyInstant(): number | null {
  if (typeof window === 'undefined') return null;
  const p = new URLSearchParams(window.location.search).get('skytime');
  const ms = p ? Date.parse(p) : NaN;
  return Number.isFinite(ms) ? ms : null;
}

const VERT = /* glsl */ `
varying vec3 vDir;
void main() {
  vDir = normalize(position);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;

const FRAG = /* glsl */ `
uniform vec3 uSun;
uniform float uDay;
uniform vec3 uZenith;
uniform vec3 uHorizon;
uniform vec3 uGlow;
varying vec3 vDir;
void main() {
  vec3 d = normalize(vDir);
  float h = clamp(d.y, 0.0, 1.0);
  vec3 col = mix(uHorizon, uZenith, pow(h, 0.55));
  float c = dot(d, normalize(uSun));
  float sunEl = uSun.y;
  // Blue aureole around the Sun, wider and stronger when the Sun is low (or just below the horizon).
  float low = 1.0 - smoothstep(0.0, 0.5, abs(sunEl));
  float aureole = pow(max(c, 0.0), mix(18.0, 7.0, low)) * (0.35 + 0.65 * low) * smoothstep(-0.25, 0.02, sunEl);
  col = mix(col, uGlow, clamp(aureole, 0.0, 0.85));
  // Solar disc (about 0.35 deg seen from Mars, drawn a little larger) with a short halo.
  float disc = smoothstep(0.99996, 0.99999, c) * step(0.0, sunEl + 0.01);
  float halo = pow(max(c, 0.0), 900.0) * 0.6 * step(0.0, sunEl + 0.01);
  col += vec3(1.0, 0.97, 0.9) * (disc + halo);
  gl_FragColor = vec4(col, 1.0);
}`;

const STAR_VERT = /* glsl */ `
attribute float aSize;
attribute vec3 aColor;
varying vec3 vColor;
varying float vAlt;
uniform float uPx;
void main() {
  vColor = aColor;
  vAlt = normalize(position).y;
  gl_PointSize = aSize * uPx;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;

const STAR_FRAG = /* glsl */ `
uniform float uNight;
varying vec3 vColor;
varying float vAlt;
void main() {
  vec2 p = gl_PointCoord - 0.5;
  float r = length(p);
  if (r > 0.5) discard;
  float core = smoothstep(0.5, 0.0, r);
  // Fainter near the horizon (longer path through dusty air), gone below it.
  float ext = smoothstep(-0.01, 0.18, vAlt);
  gl_FragColor = vec4(vColor, core * uNight * ext);
}`;

/** Star colour from B-V (blue-white to orange), and point size from magnitude. */
function starColor(bv: number, out: THREE.Color) {
  const t = Math.max(0, Math.min(1, (bv + 0.3) / 2.0));
  return out.setRGB(0.75 + 0.25 * t, 0.82 + 0.1 * (1 - Math.abs(t - 0.35) * 2), 1.0 - 0.45 * t);
}

interface Props {
  latDeg: number;
  lonEastDeg: number;
  sunLight?: RefObject<THREE.DirectionalLight | null>;
  hemiLight?: RefObject<THREE.HemisphereLight | null>;
  /** Distance of the key light from the scene centre (m). */
  lightDistance?: number;
  /**
   * Artificial light (I): light the terrain as by day whatever the hour, from the fixed display
   * direction, while the sky keeps the real time (stars stay at night). A viewing aid, not sunlight.
   */
  artificialLight?: boolean;
}

export function SkyDome({ latDeg, lonEastDeg, sunLight, hemiLight, lightDistance = 2700, artificialLight = false }: Props) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const scene = useThree((s) => s.scene);
  const dpr = useThree((s) => s.viewport.dpr);
  const group = useRef<THREE.Group>(null);
  const [catalogue, setCatalogue] = useState<StarCatalogue | null>(null);
  const fixed = useMemo(skyInstant, []);

  useEffect(() => {
    let live = true;
    fetch(assetUrl('assets/sky/bright_stars.json'))
      .then((r) => (r.ok ? r.json() : null))
      .then((d: StarCatalogue | null) => live && d && setCatalogue(d))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);

  const skyMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: VERT,
        fragmentShader: FRAG,
        uniforms: {
          uSun: { value: new THREE.Vector3(0, 1, 0) },
          uDay: { value: 1 },
          uZenith: { value: DAY_ZENITH.clone() },
          uHorizon: { value: DAY_HORIZON.clone() },
          uGlow: { value: TWILIGHT_GLOW.clone() },
        },
        side: THREE.BackSide,
        depthWrite: false,
        depthTest: false,
        fog: false,
      }),
    [],
  );
  const starMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: STAR_VERT,
        fragmentShader: STAR_FRAG,
        uniforms: { uNight: { value: 0 }, uPx: { value: 1 } },
        transparent: true,
        depthWrite: false,
        depthTest: true, // hidden behind the terrain
        blending: THREE.AdditiveBlending,
        fog: false,
      }),
    [],
  );
  const skyGeo = useMemo(() => new THREE.SphereGeometry(1, 48, 24), []);
  const starGeo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    if (!catalogue) return g;
    const n = catalogue.stars.length;
    const size = new Float32Array(n);
    const color = new Float32Array(n * 3);
    const c = new THREE.Color();
    catalogue.stars.forEach(([, , mag, bv], i) => {
      size[i] = Math.max(1.2, 4.2 - 0.62 * mag);
      starColor(bv, c).toArray(color, i * 3);
    });
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
    g.setAttribute('aColor', new THREE.BufferAttribute(color, 3));
    return g;
  }, [catalogue]);
  useEffect(() => () => [skyMat, starMat, skyGeo].forEach((o) => o.dispose()), [skyMat, starMat, skyGeo]);
  useEffect(() => () => starGeo.dispose(), [starGeo]);

  const state = useRef({ nextSun: 0, nextStars: 0, sun: new THREE.Vector3(), key: new THREE.Vector3(), tmp: new THREE.Vector3(), zen: new THREE.Color(), hor: new THREE.Color() });

  // Apply a change of the artificial light at once instead of at the next once-a-second update.
  useEffect(() => {
    state.current.nextSun = 0;
  }, [artificialLight]);

  useFrame(({ clock }) => {
    const g = group.current;
    if (!g) return;
    g.position.copy(camera.position); // the dome always surrounds the eye
    g.scale.setScalar(Math.max(1000, camera.far * 0.9));
    const s = state.current;
    const now = clock.elapsedTime;
    const ms = fixed ?? Date.now();
    if (now >= s.nextSun) {
      s.nextSun = now + 1;
      const sun = marsSun(ms, latDeg, lonEastDeg);
      toThree(sun.dir, s.sun);
      const day = daylight(sun.elDeg);
      const u = skyMat.uniforms;
      (u.uSun.value as THREE.Vector3).copy(s.sun);
      u.uDay.value = day;
      s.zen.copy(NIGHT_ZENITH).lerp(DAY_ZENITH, day);
      s.hor.copy(NIGHT_HORIZON).lerp(DAY_HORIZON, day);
      (u.uZenith.value as THREE.Color).copy(s.zen);
      (u.uHorizon.value as THREE.Color).copy(s.hor);
      starMat.uniforms.uNight.value = Math.pow(1 - day, 1.5);
      // The haze fades to the horizon colour, so far ground meets the sky.
      if (scene.fog) (scene.fog as THREE.Fog).color.copy(s.hor);
      if (scene.background instanceof THREE.Color) scene.background.copy(s.hor);
      // Key light: the Sun by day (kept at least 3 deg up so it grazes rather than lights from below),
      // blending to the night fill as the Sun sets. The astronaut's projected shadow reads the same vectors.
      const lit = THREE.MathUtils.smoothstep(sun.elDeg, -4, 6);
      const up = Math.max(s.sun.y, Math.sin((3 * Math.PI) / 180));
      s.tmp.set(s.sun.x, 0, s.sun.z).normalize().multiplyScalar(Math.sqrt(1 - up * up)).setY(up);
      s.key.copy(NIGHT_DIR).lerp(s.tmp, lit).normalize();
      if (artificialLight) s.key.copy(ARTIFICIAL_DIR);
      SUN_FROM.copy(s.key);
      SUN_DIR.copy(s.key).negate();
      const L = sunLight?.current;
      if (L) {
        L.position.copy(s.key).multiplyScalar(lightDistance);
        if (artificialLight) {
          L.intensity = 2.6;
          L.color.copy(SUN_HIGH);
        } else {
          L.intensity = 0.7 + 1.9 * lit;
          const warm = THREE.MathUtils.smoothstep(sun.elDeg, 2, 25);
          L.color.copy(SUN_LOW).lerp(SUN_HIGH, warm).lerp(NIGHT_FILL, 1 - lit);
        }
      }
      const H = hemiLight?.current;
      if (H) H.intensity = artificialLight ? 0.4 : 0.28 + 0.12 * day;
    }
    starMat.uniforms.uPx.value = dpr;
    if (catalogue && now >= s.nextStars) {
      s.nextStars = now + 2; // Mars turns 0.008 deg in 2 s
      const f = celestialToLocal(ms, latDeg, lonEastDeg);
      const pos = starGeo.getAttribute('position') as THREE.BufferAttribute;
      catalogue.stars.forEach(([ra, dec], i) => {
        toThree(f(ra, dec), s.tmp);
        pos.setXYZ(i, s.tmp.x * 0.98, s.tmp.y * 0.98, s.tmp.z * 0.98);
      });
      pos.needsUpdate = true;
      starGeo.computeBoundingSphere();
    }
  });

  return (
    <group ref={group} name="sky" renderOrder={-10}>
      <mesh geometry={skyGeo} material={skyMat} renderOrder={-10} frustumCulled={false} />
      {catalogue && <points geometry={starGeo} material={starMat} renderOrder={-9} frustumCulled={false} />}
    </group>
  );
}
