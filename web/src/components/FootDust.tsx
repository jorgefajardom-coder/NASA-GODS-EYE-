import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

const PUFF_PARTICLES = 14;
const MAX_PARTICLES = 420;
const MAX_PRINTS = 80;
const PUFF_LIFE_S = 1.4;
const PRINT_LIFE_S = 40;
/** Drawn model height before distance scaling (AstronautModel.ASTRONAUT_VISUAL_HEIGHT_M). */
const ASTRONAUT_HEIGHT_M = 1.9;
/** Footfalls detected since load; read by tests in the browser (window.__mgeFootfalls). */
let footfalls = 0;
if (typeof window !== 'undefined') Object.defineProperty(window, '__mgeFootfalls', { get: () => footfalls, configurable: true });

interface Props {
  /** Animated model; its toe bones are read each frame to detect footfalls. */
  model: THREE.Object3D;
  /** Walking and the replay playing: dust and prints are only made then. */
  active: boolean;
  /** Ground speed on screen (m/s of wall time). Above TRAIL_SPEED_MPS strides are far apart, so a dust trail replaces prints. */
  screenSpeedMps: number;
}

/** Above this on-screen speed (fast replay) footprints would land metres apart; a dust trail is drawn instead. */
const TRAIL_SPEED_MPS = 6;

/**
 * Cosmetic ground contact for the walking astronaut: when a boot comes down (toe bone reaches
 * its lowest height and stops descending) a small dust puff rises and a footprint is left that
 * fades over time. Display only; it reads bone positions and never changes the agent pose.
 * Particles and prints live in world space so they stay where the foot landed.
 */
export function FootDust({ model, active, screenSpeedMps }: Props) {
  const scene = useThree((s) => s.scene);
  const toes = useMemo(() => {
    const found: THREE.Object3D[] = [];
    model.traverse((o) => {
      if (/^[LR]_Toe\d/.test(o.name)) found.push(o); // the loader strips dots: L_Toe85_88
    });
    return found;
  }, [model]);

  // Dust: one Points object with a pool of particles.
  const dust = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(MAX_PARTICLES * 3), 3));
    g.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array(MAX_PARTICLES), 1));
    g.setAttribute('size', new THREE.BufferAttribute(new Float32Array(MAX_PARTICLES), 1));
    const m = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms: { uColor: { value: new THREE.Color('#e3c09a') } }, // lighter than the ground so the puff reads
      vertexShader: `attribute float alpha; attribute float size; varying float vA;
        void main() { vA = alpha; vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * 700.0 / -mv.z; gl_Position = projectionMatrix * mv; }`,
      fragmentShader: `uniform vec3 uColor; varying float vA;
        void main() { float d = length(gl_PointCoord - 0.5); if (d > 0.5) discard;
          gl_FragColor = vec4(uColor, vA * smoothstep(0.5, 0.0, d)); }`,
    });
    const p = new THREE.Points(g, m);
    p.frustumCulled = false;
    p.renderOrder = 2;
    return p;
  }, []);
  const parts = useRef(Array.from({ length: MAX_PARTICLES }, () => ({ age: Infinity, scale: 1, p: new THREE.Vector3(), v: new THREE.Vector3() })));
  const nextPart = useRef(0);

  // Footprints: an instanced dark ellipse per print.
  const prints = useMemo(() => {
    const geo = new THREE.CircleGeometry(0.5, 16);
    geo.scale(0.42, 1, 1); // boot-shaped ellipse, long axis along the step
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.MeshBasicMaterial({ color: '#1c0e07', transparent: true, opacity: 0.6, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4 });
    const mesh = new THREE.InstancedMesh(geo, mat, MAX_PRINTS);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    mesh.count = 0;
    mesh.frustumCulled = false;
    mesh.renderOrder = 1;
    return mesh;
  }, []);
  const printAges = useRef<number[]>([]);
  const printMats = useRef<THREE.Matrix4[]>([]);

  useEffect(() => {
    scene.add(dust, prints);
    return () => {
      scene.remove(dust, prints);
      dust.geometry.dispose();
      (dust.material as THREE.Material).dispose();
      prints.geometry.dispose();
      (prints.material as THREE.Material).dispose();
    };
  }, [scene, dust, prints]);

  const wasDown = useRef<boolean[]>([]);
  const w = useRef(new THREE.Vector3());
  const ground = useRef(new THREE.Vector3());
  const sc = useRef(new THREE.Vector3());
  const fwd = useRef(new THREE.Vector3());
  const q = useRef(new THREE.Quaternion());

  /** Emits `n` dust particles at a boot (sizes and speeds follow the drawn model scale). */
  const spawn = (at: THREE.Vector3, groundY: number, scale: number, n: number, strength: number) => {
    for (let k = 0; k < n; k++) {
      const part = parts.current[nextPart.current];
      nextPart.current = (nextPart.current + 1) % MAX_PARTICLES;
      const a = Math.random() * Math.PI * 2;
      const sp = (0.4 + Math.random() * 0.9) * scale * strength;
      part.age = 0;
      part.scale = scale;
      part.p.set(at.x, groundY + 0.05 * scale, at.z);
      part.v.set(Math.cos(a) * sp, (0.25 + Math.random() * 0.6) * scale * strength, Math.sin(a) * sp);
    }
  };

  useFrame((_, dtRaw) => {
    const dt = Math.min(dtRaw, 0.1);
    // Footfall: a toe coming down near the agent's ground point (relative to the drawn body height).
    const root = model.parent;
    if (root) {
      root.getWorldPosition(ground.current);
      root.getWorldScale(sc.current);
    }
    const bodyH = ASTRONAUT_HEIGHT_M * sc.current.y;
    toes.forEach((toe, i) => {
      toe.getWorldPosition(w.current);
      // Hysteresis on the toe height (it swings between ~1 % and ~10 % of body height):
      // down below 2.5 %, up again above 5.5 %.
      const h = w.current.y - ground.current.y;
      const down = wasDown.current[i] ? h < 0.055 * bodyH : h < 0.025 * bodyH;
      const landed = down && !wasDown.current[i];
      wasDown.current[i] = down;
      const fast = screenSpeedMps > TRAIL_SPEED_MPS;
      if (fast && active && down) {
        // Fast replay: a thin continuous dust trail at the boot instead of discrete prints.
        spawn(w.current, ground.current.y, sc.current.y, 2, 0.6);
        return;
      }
      if (!active || !landed) return;
      footfalls++;
      const scale = sc.current.y;
      spawn(w.current, ground.current.y, scale, PUFF_PARTICLES, 1);
      // Footprint on the ground, aligned with the body's facing.
      model.getWorldQuaternion(q.current);
      fwd.current.set(0, 0, 1).applyQuaternion(q.current);
      const yaw = Math.atan2(fwd.current.x, fwd.current.z);
      const m = new THREE.Matrix4().compose(
        new THREE.Vector3(w.current.x, ground.current.y + 0.12 * scale, w.current.z),
        new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw),
        new THREE.Vector3(0.7 * scale, 1, 0.7 * scale),
      );
      printMats.current.push(m);
      printAges.current.push(0);
      if (printMats.current.length > MAX_PRINTS) {
        printMats.current.shift();
        printAges.current.shift();
      }
    });

    // Dust update.
    const pos = dust.geometry.getAttribute('position') as THREE.BufferAttribute;
    const alpha = dust.geometry.getAttribute('alpha') as THREE.BufferAttribute;
    const size = dust.geometry.getAttribute('size') as THREE.BufferAttribute;
    parts.current.forEach((part, i) => {
      if (part.age < PUFF_LIFE_S) {
        part.age += dt;
        part.v.multiplyScalar(Math.exp(-2.2 * dt)); // drag: dust settles quickly in thin air
        part.v.y -= 0.6 * part.scale * dt; // Mars gravity pulls it back down
        part.p.addScaledVector(part.v, dt);
        const k = part.age / PUFF_LIFE_S;
        pos.setXYZ(i, part.p.x, part.p.y, part.p.z);
        alpha.setX(i, 0.85 * (1 - k) * (1 - k));
        size.setX(i, (0.35 + 1.4 * k) * part.scale);
      } else {
        alpha.setX(i, 0);
      }
    });
    pos.needsUpdate = alpha.needsUpdate = size.needsUpdate = true;

    // Footprints fade.
    const ages = printAges.current;
    for (let i = 0; i < ages.length; i++) ages[i] += dt;
    while (ages.length && ages[0] > PRINT_LIFE_S) {
      ages.shift();
      printMats.current.shift();
    }
    prints.count = printMats.current.length;
    printMats.current.forEach((m, i) => prints.setMatrixAt(i, m));
    prints.instanceMatrix.needsUpdate = true;
  });

  return null;
}
