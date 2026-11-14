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
/** EVA boot sole, real size (m), and how far behind the toe bone its centre lies. */
const BOOT_LENGTH_M = 0.33;
const BOOT_WIDTH_M = 0.13;
const TOE_TO_SOLE_CENTRE_M = 0.1;

let soleTexture: THREE.Texture | null = null;
/**
 * Left-boot sole print drawn once on a canvas: rounded toe, narrower arch, heel, and the tread
 * lugs pressed darker into the regolith. Toe at the bottom of the canvas (+z on the ground); the
 * arch, on the canvas's left (-x), is the inner side of a left foot on a model facing +z.
 */
function bootSoleTexture(): THREE.Texture | null {
  if (soleTexture || typeof document === 'undefined') return soleTexture;
  const W = 128;
  const H = 320;
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const g = c.getContext('2d')!;
  // Outline: heel at the top, toe at the bottom, arch pinched on the canvas's left side.
  const sole = new Path2D();
  sole.moveTo(64, 10);
  sole.bezierCurveTo(104, 10, 112, 40, 110, 80); // heel, outer side
  sole.bezierCurveTo(108, 120, 112, 150, 118, 190); // outer edge
  sole.bezierCurveTo(124, 240, 116, 300, 70, 310); // toe, outer
  sole.bezierCurveTo(24, 314, 8, 280, 10, 230); // toe, inner
  sole.bezierCurveTo(12, 190, 34, 160, 34, 125); // ball to arch (inner side pinched)
  sole.bezierCurveTo(34, 95, 18, 70, 20, 45); // arch to heel
  sole.bezierCurveTo(22, 22, 40, 10, 64, 10);
  sole.closePath();
  // Compressed regolith: darker than the ground, darkest in the middle of the print.
  const fill = g.createRadialGradient(64, 170, 10, 64, 170, 170);
  fill.addColorStop(0, 'rgba(26,13,6,0.78)');
  fill.addColorStop(1, 'rgba(40,20,9,0.55)');
  g.fillStyle = fill;
  g.fill(sole);
  // Tread lugs: chevron bars on the forefoot, blocks on the heel, a plain arch between.
  g.save();
  g.clip(sole);
  g.strokeStyle = 'rgba(8,3,1,0.85)';
  g.lineWidth = 9;
  g.lineCap = 'round';
  for (let y = 175; y < 305; y += 22) {
    g.beginPath();
    g.moveTo(14, y + 10);
    g.lineTo(64, y - 4);
    g.lineTo(116, y + 10);
    g.stroke();
  }
  g.fillStyle = 'rgba(8,3,1,0.85)';
  for (let y = 22; y < 100; y += 24) {
    for (let x = 28; x < 104; x += 26) g.fillRect(x, y, 16, 14);
  }
  g.restore();
  // Raised rim of displaced soil, lighter than the ground, just outside the print.
  g.strokeStyle = 'rgba(214,170,128,0.35)';
  g.lineWidth = 4;
  g.stroke(sole);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  soleTexture = t;
  return t;
}

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

  // Footprints: an instanced boot-sole decal per print (one mesh per foot, the right one mirrored).
  const prints = useMemo(() => {
    const tex = bootSoleTexture();
    const geo = new THREE.PlaneGeometry(BOOT_WIDTH_M, BOOT_LENGTH_M);
    geo.rotateX(-Math.PI / 2); // flat on the ground, toe (texture bottom) toward +z
    const make = (mirror: boolean) => {
      const mat = new THREE.MeshBasicMaterial({
        map: tex,
        transparent: true,
        opacity: 0.85,
        depthWrite: false,
        polygonOffset: true,
        polygonOffsetFactor: -4,
        side: THREE.DoubleSide, // the right print is mirrored (negative x scale)
      });
      const mesh = new THREE.InstancedMesh(geo, mat, MAX_PRINTS);
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      mesh.count = 0;
      mesh.frustumCulled = false;
      mesh.renderOrder = 1;
      mesh.userData.mirror = mirror;
      return mesh;
    };
    const group = new THREE.Group();
    group.add(make(false), make(true));
    return group;
  }, []);
  const printAges = useRef<number[]>([]);
  const printMats = useRef<THREE.Matrix4[]>([]);
  const printLeft = useRef<boolean[]>([]);

  useEffect(() => {
    scene.add(dust, prints);
    return () => {
      scene.remove(dust, prints);
      dust.geometry.dispose();
      (dust.material as THREE.Material).dispose();
      for (const m of prints.children as THREE.InstancedMesh[]) {
        m.geometry.dispose();
        (m.material as THREE.MeshBasicMaterial).dispose();
      }
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
      // Footprint on the ground, aligned with the body's facing. The toe bone sits near the front
      // of the boot, so the sole is centred a little behind it.
      model.getWorldQuaternion(q.current);
      fwd.current.set(0, 0, 1).applyQuaternion(q.current);
      fwd.current.y = 0;
      fwd.current.normalize();
      const yaw = Math.atan2(fwd.current.x, fwd.current.z);
      const left = /^L_/.test(toe.name);
      const back = TOE_TO_SOLE_CENTRE_M * scale;
      const m = new THREE.Matrix4().compose(
        new THREE.Vector3(w.current.x - fwd.current.x * back, ground.current.y + 0.04 * scale, w.current.z - fwd.current.z * back),
        new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw),
        new THREE.Vector3(left ? scale : -scale, 1, scale), // the texture is a left sole; mirrored for the right foot
      );
      printMats.current.push(m);
      printAges.current.push(0);
      printLeft.current.push(left);
      if (printMats.current.length > MAX_PRINTS) {
        printMats.current.shift();
        printAges.current.shift();
        printLeft.current.shift();
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
      printLeft.current.shift();
    }
    for (const mesh of prints.children as THREE.InstancedMesh[]) {
      let n = 0;
      printMats.current.forEach((m, i) => {
        if (printLeft.current[i] !== mesh.userData.mirror) mesh.setMatrixAt(n++, m);
      });
      mesh.count = n;
      mesh.instanceMatrix.needsUpdate = true;
    }
  });

  return null;
}
