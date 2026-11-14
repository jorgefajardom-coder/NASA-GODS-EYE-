import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef, type MutableRefObject, type RefObject } from 'react';
import * as THREE from 'three';

const MAX = 320;
/** Air pushed down by the rotors: spawn rate at full speed (per s), speed (m/s at true size), life (s). */
const AIR_RATE = 130;
const AIR_SPEED = 6.5;
const AIR_LIFE_S = 1.4;
/** Dust kicked up where the downwash reaches the ground: outward speed (m/s) and life (s). */
const DUST_SPEED = 3.6;
const DUST_LIFE_S = 2.4;

interface Props {
  /** Group whose world position and scale are the drone's (the vehicle model holder). */
  holder: RefObject<THREE.Group | null>;
  /** Rotor nodes, for the height and radius of the rotor disc. */
  rotors: THREE.Object3D[];
  /** Rotor radius at true size (m). */
  radiusM: number;
  /** Current rotor speed, share of full speed. */
  speed: MutableRefObject<number>;
  /** Replay running; particles freeze when false. */
  playing: boolean;
}

/**
 * Downwash of the drone's rotors (display only): invisible air parcels leave the rotor disc moving
 * down, faster and denser as the rotors speed up. Where they reach the drawn ground (the drone is
 * low: on the pad, taking off or landing) they lift dust, drawn as soft puffs spreading outward.
 * Particles live in world space; the drone's pose is never changed.
 */
export function Downwash({ holder, rotors, radiusM, speed, playing }: Props) {
  const scene = useThree((s) => s.scene);
  const points = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(MAX * 3), 3));
    g.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array(MAX), 1));
    g.setAttribute('size', new THREE.BufferAttribute(new Float32Array(MAX), 1));
    g.setAttribute('dust', new THREE.BufferAttribute(new Float32Array(MAX), 1));
    const m = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      vertexShader: `attribute float alpha; attribute float size; attribute float dust; varying float vA; varying float vD;
        void main() { vA = alpha; vD = dust; vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * 700.0 / -mv.z; gl_Position = projectionMatrix * mv; }`,
      fragmentShader: `varying float vA; varying float vD;
        void main() { vec2 q = gl_PointCoord - 0.5; float d = dot(q, q) * 4.0; if (d > 1.0) discard;
          // Soft, gaussian puff with a faint irregular edge, so overlapping puffs read as a cloud.
          float n = 0.85 + 0.15 * sin(gl_PointCoord.x * 13.0 + gl_PointCoord.y * 9.0);
          vec3 c = vec3(0.80, 0.64, 0.49);
          gl_FragColor = vec4(c, vA * exp(-d * 3.0) * n); }`,
    });
    const p = new THREE.Points(g, m);
    p.frustumCulled = false;
    p.renderOrder = 3;
    return p;
  }, []);
  useEffect(() => {
    scene.add(points);
    return () => {
      scene.remove(points);
      points.geometry.dispose();
      (points.material as THREE.Material).dispose();
    };
  }, [scene, points]);

  const parts = useRef(Array.from({ length: MAX }, () => ({ age: Infinity, life: 1, dust: false, p: new THREE.Vector3(), v: new THREE.Vector3() })));
  const next = useRef(0);
  const debt = useRef(0);
  const tmp = useMemo(() => ({ c: new THREE.Vector3(), s: new THREE.Vector3(), r: new THREE.Vector3() }), []);

  useFrame((_, dtRaw) => {
    const h = holder.current;
    if (!h) return;
    const dt = playing ? Math.min(dtRaw, 0.05) : 0;
    if (!playing && speed.current === 0) {
      // Rotors stopped while paused (e.g. after Restart): no dust is left hanging in the air.
      for (const q of parts.current) q.age = Infinity;
      debt.current = 0;
    }
    let agent: THREE.Object3D | null = h;
    while (agent && agent.userData.agl === undefined) agent = agent.parent;
    h.getWorldScale(tmp.s);
    const scale = tmp.s.y || 1;
    const agentPos = agent ? agent.getWorldPosition(tmp.c) : h.getWorldPosition(tmp.c);
    const groundY = agentPos.y - ((agent?.userData.agl as number | undefined) ?? 0);
    // Rotor disc height: the rotor nodes' mean world height.
    let discY = agentPos.y;
    if (rotors.length) {
      discY = 0;
      for (const r of rotors) discY += r.getWorldPosition(tmp.r).y / rotors.length;
    }
    const R = radiusM * scale;
    const s = speed.current;

    // Spawn air below the rotor disc, more and faster with rotor speed.
    if (dt > 0 && s > 0.25) {
      debt.current += AIR_RATE * s * s * dt;
      while (debt.current >= 1) {
        debt.current -= 1;
        const q = parts.current[next.current];
        next.current = (next.current + 1) % MAX;
        const a = Math.random() * Math.PI * 2;
        const rr = R * Math.sqrt(Math.random()) * 0.95;
        q.age = 0;
        q.life = AIR_LIFE_S;
        q.dust = false;
        q.p.set(agentPos.x + Math.cos(a) * rr, discY - 0.05 * scale, agentPos.z + Math.sin(a) * rr);
        q.v.set(Math.cos(a) * 0.3 * scale, -(AIR_SPEED * (0.6 + 0.4 * s)) * scale, Math.sin(a) * 0.3 * scale);
      }
    }

    const pos = points.geometry.getAttribute('position') as THREE.BufferAttribute;
    const alpha = points.geometry.getAttribute('alpha') as THREE.BufferAttribute;
    const size = points.geometry.getAttribute('size') as THREE.BufferAttribute;
    const dust = points.geometry.getAttribute('dust') as THREE.BufferAttribute;
    parts.current.forEach((q, i) => {
      if (q.age >= q.life) {
        alpha.setX(i, 0);
        return;
      }
      q.age += dt;
      q.p.addScaledVector(q.v, dt);
      if (!q.dust && q.p.y <= groundY + 0.05 * scale) {
        // Reached the ground: the air spreads out and lifts dust.
        q.dust = true;
        q.age = 0;
        q.life = DUST_LIFE_S;
        q.p.y = groundY + 0.05 * scale;
        const dx = q.p.x - agentPos.x;
        const dz = q.p.z - agentPos.z;
        const d = Math.hypot(dx, dz) || 1;
        q.v.set((dx / d) * DUST_SPEED * scale * (0.7 + 0.6 * Math.random()), 0.4 * scale * Math.random(), (dz / d) * DUST_SPEED * scale * (0.7 + 0.6 * Math.random()));
      }
      if (q.dust) q.v.multiplyScalar(Math.exp(-1.2 * dt)); // thin air: the dust slows quickly
      const k = q.age / q.life;
      pos.setXYZ(i, q.p.x, q.p.y, q.p.z);
      // Air itself is invisible: it only carries the downwash to the ground. What shows is the dust
      // it lifts there, as soft puffs that grow, rise a little and thin out.
      const grow = Math.sin(Math.min(1, k * 1.6) * Math.PI * 0.5);
      alpha.setX(i, q.dust ? 0.22 * (1 - k) * (1 - k) : 0);
      size.setX(i, q.dust ? (1.0 + 3.2 * grow) * scale : 0);
      dust.setX(i, q.dust ? 1 : 0);
    });
    pos.needsUpdate = alpha.needsUpdate = size.needsUpdate = dust.needsUpdate = true;
  });

  return null;
}
