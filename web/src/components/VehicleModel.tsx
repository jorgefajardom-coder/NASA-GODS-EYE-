import { useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { assetUrl } from '../data/replayAdapter';
import { Downwash } from './Downwash';
import { SHADOW_RENDER_ORDER, createProjectedShadow } from '../lib/projectedShadow';
import { ARM_DEPLOYED_DEG, ARM_STOWED_DEG, roverRig, stepRig } from '../lib/roverRig';

/**
 * Rover and drone models: official NASA/JPL-Caltech 3D models with all agency branding removed
 * (see web/scripts/blender/README.md and THIRD_PARTY_NOTICES.md). Drawn at real size; the
 * parent group gives position and heading from AgentState. Purely visual.
 */
export const ROVER_URL = assetUrl('assets/models/rover.glb');
export const DRONE_URL = assetUrl('assets/models/drone.glb');

interface Props {
  url: string;
  /** Real size of the vehicle's longest horizontal dimension (m). */
  lengthM: number;
  /** Extra turn so the model's front faces +x (east at yaw 0), radians. */
  yawOffset?: number;
  /** Replay running: rotors and wheels freeze while paused. */
  playing?: boolean;
  /** Spin rotor nodes (drone) while true; they also keep turning while the drawn drone is airborne. */
  spinning?: boolean;
  /**
   * Rover drive: wheels roll, corner wheels steer and each wheel follows the ground. The motion
   * is read from the drawn agent itself (its eased position and heading each frame).
   */
  drive?: boolean;
  /** Drawn ground height (Three.js y) at a world (x, z), for the per-wheel suspension. */
  groundAt?: (x: number, z: number) => number | null;
}

/**
 * Rover rig in the model (GLTF node names lose their dots): the mast head pans about the vertical and
 * tilts about its lateral axis; the arm has five joints (shoulder azimuth, shoulder, elbow, wrist,
 * turret). The model's front is +z, up +y, left +x. The stowed and deployed joint angles are in lib/roverRig.
 */
const ARM_JOINTS = ['arm003', 'arm002', 'arm', 'arm004'] as const;
const ARM_AXES = [new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 1)];
/** Priority between the drawn poses (-2) and the cameras (-1): the cameras read this frame's mast and arm. */
export const RIG_PRIORITY = -1.5;

interface RigNodes {
  head: THREE.Object3D;
  headRest: THREE.Quaternion;
  arm: Array<{ node: THREE.Object3D; rest: THREE.Quaternion }>;
}

function rigNodesOf(model: THREE.Object3D): RigNodes | null {
  const head = model.getObjectByName('head');
  const arm = ARM_JOINTS.map((n) => model.getObjectByName(n));
  if (!head || arm.some((a) => !a)) return null;
  return { head, headRest: head.quaternion.clone(), arm: arm.map((node) => ({ node: node!, rest: node!.quaternion.clone() })) };
}

/** Wheel meshes of the rover model (all six wheels are one mesh, split at load). */
const WHEELS = /^Wheels_objs/;
/** Drawn height above ground (m) above which the drone counts as airborne (rotors on). */
const AIRBORNE_M = 0.3;
/** Steering limit of the corner wheels (rad) and their actuator easing (s). */
const STEER_MAX = THREE.MathUtils.degToRad(70);
const STEER_TAU_S = 0.35;
/** Easing of the measured speed and turn rate (s), so frame timing does not jitter the wheels. */
const MOTION_TAU_S = 0.15;
/** Suspension travel of each wheel up or down (m at true size) and its easing (s). */
const WHEEL_TRAVEL_M = 0.15;
const SUSPENSION_TAU_S = 0.12;

interface Wheel {
  pivot: THREE.Group;
  /** Radius in the mesh's units. */
  radius: number;
  /** Axle centre at rest (mesh units): x lateral, z forward. */
  rest: THREE.Vector3;
  /** Corner wheels (front and rear) steer; the middle pair does not. */
  steers: boolean;
  steer: number;
  lift: number;
  /** Steering joint above a corner wheel (actuator and fork), turned with the wheel; in its own frame. */
  joint?: { pivot: THREE.Group; rest: THREE.Vector3; liftScale: number };
}

/** Suspension meshes of the rover model (rocker-bogie arms, steering actuators and forks). */
const SUSPENSION = /^suspension/;
/** Part of the suspension that turns with a corner wheel: within this distance of its steering axis (m). */
const JOINT_RADIUS_M = 0.3;
/** Lowest point of a joint relative to the wheel centre (m), so the hub fork is included. */
const JOINT_BELOW_M = 0.12;

/**
 * Splits the wheel meshes (the model has one mesh for all six wheels, in several parts: tyre, rim,
 * hub) into one pivot per wheel, so each wheel turns about its own axle with all its parts together.
 * The six axle centres are found once over every part: triangles are grouped by side (sign of x,
 * the model's lateral axis) and by the nearest of three axle positions along z (front, middle,
 * rear; 1-D k-means). Then each triangle of each part goes to the wheel whose centre is nearest,
 * so a tyre, its rim and its hub always share a pivot. Geometry attributes are shared; only new
 * index lists are made. Returns [] when the meshes do not look like 2 x 3 wheels.
 */
function splitWheels(meshes: THREE.Mesh[]): Wheel[] {
  type Part = { mesh: THREE.Mesh; pos: THREE.BufferAttribute; index: number[]; cx: Float32Array; cy: Float32Array; cz: Float32Array };
  const parts: Part[] = [];
  for (const mesh of meshes) {
    const pos = mesh.geometry.getAttribute('position') as THREE.BufferAttribute | undefined;
    if (!pos) continue;
    const index = mesh.geometry.index ? Array.from(mesh.geometry.index.array as ArrayLike<number>) : Array.from({ length: pos.count }, (_, i) => i);
    const tris = index.length / 3;
    const cx = new Float32Array(tris);
    const cy = new Float32Array(tris);
    const cz = new Float32Array(tris);
    for (let t = 0; t < tris; t++) {
      for (let k = 0; k < 3; k++) {
        const v = index[t * 3 + k];
        cx[t] += pos.getX(v) / 3;
        cy[t] += pos.getY(v) / 3;
        cz[t] += pos.getZ(v) / 3;
      }
    }
    parts.push({ mesh, pos, index, cx, cy, cz });
  }
  if (!parts.length) return [];
  // Axle positions along z, from every part's triangles together.
  let zMin = Infinity;
  let zMax = -Infinity;
  for (const p of parts) for (const z of p.cz) {
    if (z < zMin) zMin = z;
    if (z > zMax) zMax = z;
  }
  let centres = [zMin, (zMin + zMax) / 2, zMax];
  const nearest = (z: number) => {
    let best = 0;
    for (let c = 1; c < 3; c++) if (Math.abs(z - centres[c]) < Math.abs(z - centres[best])) best = c;
    return best;
  };
  for (let it = 0; it < 12; it++) {
    const sum = [0, 0, 0];
    const n = [0, 0, 0];
    for (const p of parts) for (const z of p.cz) {
      const c = nearest(z);
      sum[c] += z;
      n[c]++;
    }
    centres = centres.map((c, i) => (n[i] ? sum[i] / n[i] : c));
  }
  const wheelOf = (x: number, z: number) => (x < 0 ? 0 : 3) + nearest(z);
  // Axle centre and radius of each wheel from the bounds of all its triangles.
  const boxes = Array.from({ length: 6 }, () => new THREE.Box3());
  const v = new THREE.Vector3();
  const groups = parts.map((p) => {
    const ids: number[][] = Array.from({ length: 6 }, () => []);
    for (let t = 0; t < p.cx.length; t++) {
      const w = wheelOf(p.cx[t], p.cz[t]);
      for (let k = 0; k < 3; k++) {
        const i = p.index[t * 3 + k];
        ids[w].push(i);
        boxes[w].expandByPoint(v.fromBufferAttribute(p.pos, i));
      }
    }
    return ids;
  });
  if (boxes.some((b) => b.isEmpty())) return [];
  return boxes.map((box, w) => {
    const centre = box.getCenter(new THREE.Vector3());
    const pivot = new THREE.Group();
    pivot.position.copy(centre);
    pivot.rotation.order = 'YXZ'; // steer about the vertical first, then roll about the steered axle
    parts.forEach((p, k) => {
      const ids = groups[k][w];
      if (!ids.length) return;
      const geo = new THREE.BufferGeometry();
      for (const [name, attr] of Object.entries(p.mesh.geometry.attributes)) geo.setAttribute(name, attr);
      geo.setIndex(ids);
      const piece = new THREE.Mesh(geo, p.mesh.material);
      piece.castShadow = true;
      piece.receiveShadow = true;
      piece.position.copy(centre).negate();
      pivot.add(piece);
    });
    // Groups 0-2 and 3-5 are the two sides, each ordered rear, middle, front (k-means keeps order).
    return { pivot, radius: (box.max.y - box.min.y) / 2, rest: centre.clone(), steers: w % 3 !== 1, steer: 0, lift: 0 };
  });
}

let blurTex: THREE.Texture | null = null;
/**
 * Soft radial falloff for the rotor blur disc: clear at the hub, faint over the blades and fading
 * out at the tips, with light streaks, so the disc reads as motion blur rather than a solid plate.
 */
function blurTexture(): THREE.Texture | null {
  if (blurTex || typeof document === 'undefined') return blurTex;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(64, 64, 4, 64, 64, 64);
  grad.addColorStop(0, 'rgba(255,255,255,0)');
  grad.addColorStop(0.18, 'rgba(255,255,255,0.35)');
  grad.addColorStop(0.7, 'rgba(255,255,255,0.45)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  g.globalCompositeOperation = 'destination-out';
  for (let r = 20; r < 64; r += 7) {
    g.strokeStyle = 'rgba(0,0,0,0.25)';
    g.lineWidth = 2;
    g.beginPath();
    g.arc(64, 64, r, 0, Math.PI * 2);
    g.stroke();
  }
  blurTex = new THREE.CanvasTexture(c);
  blurTex.colorSpace = THREE.SRGBColorSpace;
  return blurTex;
}

/** Rotor blur discs per model clone (built once). */
const discCache = new WeakMap<THREE.Object3D, THREE.Mesh[]>();

/** Wheels already split per model clone: the split empties the original mesh, so it must run once. */
const splitCache = new WeakMap<THREE.Object3D, Wheel[]>();

/**
 * The rover's six wheel pivots, split once per model. React (StrictMode in development) may run
 * a memo twice; a second split would find the wheel mesh already emptied and return nothing,
 * leaving the first pivots on screen with nobody turning them (static, floating wheels).
 */
function wheelsOf(model: THREE.Object3D): Wheel[] {
  const cached = splitCache.get(model);
  if (cached) return cached;
  const meshes: THREE.Mesh[] = [];
  model.traverse((o) => {
    if (!WHEELS.test(o.name)) return;
    o.traverse((m) => {
      if ((m as THREE.Mesh).isMesh) meshes.push(m as THREE.Mesh);
    });
  });
  const out = splitWheels(meshes);
  if (out.length && meshes[0].parent) {
    // All parts share one frame (the parts of one glTF mesh); the pivots go in that frame.
    const frame = meshes[0].parent;
    for (const w of out) frame.add(w.pivot);
    for (const m of meshes) m.geometry = new THREE.BufferGeometry(); // the pivots draw it now
  }
  if (out.length) attachSteeringJoints(model, out);
  splitCache.set(model, out);
  return out;
}

/**
 * Only the four corner wheels of a rocker-bogie rover steer, and their steering actuators turn
 * with them. The suspension mesh triangles around each corner wheel's vertical steering axis
 * (actuator housing and fork down to the hub) are moved onto a pivot on that axis, which the
 * frame loop turns by the wheel's steering angle. Geometry attributes are shared.
 */
function attachSteeringJoints(model: THREE.Object3D, wheels: Wheel[]) {
  const meshes: THREE.Mesh[] = [];
  model.traverse((o) => {
    if (!SUSPENSION.test(o.name)) return;
    o.traverse((m) => {
      if ((m as THREE.Mesh).isMesh) meshes.push(m as THREE.Mesh);
    });
  });
  if (!meshes.length || !meshes[0].parent) return;
  model.updateMatrixWorld(true);
  const frame = meshes[0].parent;
  const corners = wheels.filter((w) => w.steers);
  // Corner wheel centres in the suspension frame.
  const axes = corners.map((w) => frame.worldToLocal(w.pivot.parent!.localToWorld(w.rest.clone())));
  const unit = new THREE.Vector3();
  frame.getWorldScale(unit);
  const wheelUnit = new THREE.Vector3();
  corners[0]?.pivot.parent!.getWorldScale(wheelUnit);
  const r = JOINT_RADIUS_M / (unit.x || 1);
  const below = JOINT_BELOW_M / (unit.y || 1);
  const picked: number[][][] = meshes.map(() => corners.map(() => []));
  meshes.forEach((m, mi) => {
    const pos = m.geometry.getAttribute('position') as THREE.BufferAttribute | undefined;
    if (!pos) return;
    const index = m.geometry.index ? Array.from(m.geometry.index.array as ArrayLike<number>) : Array.from({ length: pos.count }, (_, i) => i);
    const keep: number[] = [];
    // A triangle belongs to a joint only if all three corners are near that axis, so long arm
    // triangles that merely touch the joint stay on the fixed suspension.
    const near = (i: number, a: THREE.Vector3) => Math.hypot(pos.getX(i) - a.x, pos.getZ(i) - a.z) < r && pos.getY(i) > a.y - below;
    for (let t = 0; t < index.length; t += 3) {
      const c = axes.findIndex((a) => near(index[t], a) && near(index[t + 1], a) && near(index[t + 2], a));
      if (c >= 0) picked[mi][c].push(index[t], index[t + 1], index[t + 2]);
      else keep.push(index[t], index[t + 1], index[t + 2]);
    }
    if (keep.length !== index.length) {
      const rest = m.geometry.clone();
      rest.setIndex(keep);
      m.geometry = rest;
    }
  });
  corners.forEach((w, c) => {
    const axis = axes[c];
    const pivot = new THREE.Group();
    pivot.position.copy(axis);
    meshes.forEach((m, mi) => {
      const ids = picked[mi][c];
      if (!ids.length) return;
      const geo = new THREE.BufferGeometry();
      for (const [name, attr] of Object.entries(m.geometry.attributes)) geo.setAttribute(name, attr);
      geo.setIndex(ids);
      const piece = new THREE.Mesh(geo, m.material);
      piece.castShadow = true;
      piece.receiveShadow = true;
      // Piece vertices are in the mesh's own frame; the pivot sits in the mesh's parent frame.
      piece.position.copy(m.position).sub(axis);
      piece.quaternion.copy(m.quaternion);
      piece.scale.copy(m.scale);
      pivot.add(piece);
    });
    if (pivot.children.length) {
      frame.add(pivot);
      w.joint = { pivot, rest: axis.clone(), liftScale: (wheelUnit.y || 1) / (unit.y || 1) };
    }
  });
}

/** Rotor nodes of the drone model and their spin direction (coaxial, counter-rotating). */
const ROTORS: Array<[RegExp, number]> = [
  [/^rotors_01/, 1],
  [/^rotors_02/, -1],
];
/** Real rotor speed is about 2,500 rpm; drawn at about 525 rpm (fast, with a blur disc) so it reads as spin, not flicker. */
const ROTOR_RAD_S = 55;
/** Rotor spin-up and spin-down rates (share of full speed per second): about 4 s and 5 s. */
const ROTOR_SPINUP_PER_S = 0.25;
const ROTOR_SPINDOWN_PER_S = 0.2;

export function VehicleModel({ url, lengthM, yawOffset = 0, playing = true, spinning = false, drive = false, groundAt }: Props) {
  const gltf = useGLTF(url, false, false);
  const model = useMemo(() => cloneSkinned(gltf.scene), [gltf.scene]);
  const fit = useMemo(() => {
    model.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3());
    const scale = lengthM / (Math.max(size.x, size.z) || 1);
    const c = box.getCenter(new THREE.Vector3());
    // A wheeled vehicle turns about the middle of its wheels, not the middle of its bounding box
    // (the rover's arm reaches forward and would put the turning point ahead of the wheels, so a
    // turn on the spot would sweep an arc). Centre it horizontally on the wheel set when it has one.
    let wheelsNode: THREE.Object3D | null = null;
    model.traverse((o) => {
      if (!wheelsNode && WHEELS.test(o.name)) wheelsNode = o;
    });
    if (wheelsNode) {
      const wb = new THREE.Box3().setFromObject(wheelsNode);
      if (!wb.isEmpty()) {
        const wc = wb.getCenter(new THREE.Vector3());
        c.x = wc.x;
        c.z = wc.z;
      }
    }
    return { scale, offset: [-c.x * scale, -box.min.y * scale, -c.z * scale] as [number, number, number] };
  }, [model, lengthM]);

  useEffect(() => {
    model.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) {
        m.castShadow = true;
        m.receiveShadow = true;
      }
    });
  }, [model]);

  // Each rotor turns about the model's vertical axis through its hub. The axis is world up
  // expressed in the rotor's parent frame (in this model the parent is turned 90°, and each rotor
  // node also carries its blade angle, so the node's own y axis is tilted and spinning about it
  // made the blades tumble). The rest pose is kept and the spin is applied on top of it.
  const rotors = useMemo(() => {
    model.updateMatrixWorld(true);
    const out: Array<{ node: THREE.Object3D; dir: number; axis: THREE.Vector3; rest: THREE.Quaternion }> = [];
    model.traverse((o) => {
      for (const [re, dir] of ROTORS) {
        if (!re.test(o.name) || !o.parent) continue;
        const parentWorld = o.parent.getWorldQuaternion(new THREE.Quaternion());
        const axis = new THREE.Vector3(0, 1, 0).applyQuaternion(parentWorld.invert()).normalize();
        out.push({ node: o, dir, axis, rest: o.quaternion.clone() });
      }
    });
    return out;
  }, [model]);
  // Blur disc of each rotor: a faint disc in the rotor plane that fades in with rotor speed, so the
  // spin reads as fast motion. Sized from the rotor's own blades.
  const discs = useMemo(() => {
    const cached = discCache.get(model);
    if (cached) return cached; // built once per model (a memo may run twice in development)
    model.updateMatrixWorld(true);
    const made = rotors.map((r) => {
      const box = new THREE.Box3().setFromObject(r.node);
      const size = box.getSize(new THREE.Vector3());
      const parentScale = r.node.parent!.getWorldScale(new THREE.Vector3()).x || 1;
      const radius = Math.max(size.x, size.z) / 2 / parentScale;
      const mat = new THREE.MeshBasicMaterial({ color: '#8f989e', map: blurTexture(), transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
      const disc = new THREE.Mesh(new THREE.CircleGeometry(radius, 48), mat);
      disc.position.copy(r.node.position);
      disc.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), r.axis);
      disc.renderOrder = 2;
      r.node.parent!.add(disc);
      return disc;
    });
    discCache.set(model, made);
    return made;
  }, [model, rotors]);
  // Wheels: the combined wheel mesh is split into one pivot per wheel (emptied on this clone only).
  const wheels = useMemo(() => wheelsOf(model), [model]);
  // Projected shadow (rover and drone, like the astronaut's): every mesh gets a twin, child of the same
  // node so it follows the wheels, the suspension and the rotors, drawn flattened onto the ground along
  // the display sun. Display only.
  const shadow = useMemo(() => createProjectedShadow(0.4), []);
  useEffect(() => {
    const meshes: THREE.Mesh[] = [];
    model.traverse((o) => {
      const m = o as THREE.Mesh;
      const pos = m.isMesh ? (m.geometry?.getAttribute('position') as THREE.BufferAttribute | undefined) : undefined;
      if (m.isMesh && !m.userData.isShadow && pos && pos.count > 0 && !(m.material as THREE.Material | undefined)?.transparent) meshes.push(m);
    });
    const twins = meshes.map((m) => {
      const twin = new THREE.Mesh(m.geometry, shadow.material);
      twin.userData.isShadow = true;
      twin.renderOrder = SHADOW_RENDER_ORDER;
      twin.frustumCulled = false;
      m.add(twin);
      return twin;
    });
    return () => {
      for (const t of twins) t.removeFromParent();
    };
  }, [model, shadow, wheels]);
  useEffect(() => () => shadow.material.dispose(), [shadow]);
  // The shadow lands on the drawn ground under the vehicle (a drone in flight casts it far below itself).
  const shadowAt = useMemo(() => new THREE.Vector3(), []);
  useFrame(() => {
    const h = holder.current;
    if (!h) return;
    h.getWorldPosition(shadowAt);
    const ground = state.current.groundAt?.(shadowAt.x, shadowAt.z);
    shadow.uniforms.uGround.value = (ground ?? shadowAt.y) + 0.02;
  });


  const state = useRef({ playing, spinning, drive, groundAt });
  state.current = { playing, spinning, drive, groundAt };
  const angle = useRef(0);
  const rotorSpeed = useRef(0);
  const turn = useMemo(() => new THREE.Quaternion(), []);
  const holder = useRef<THREE.Group>(null);
  // Motion of the drawn agent, measured each frame: forward speed (m/s) and turn rate (rad/s).
  const motion = useRef<{ x: number; z: number; yaw: number; v: number; w: number } | null>(null);
  const tmp = useMemo(() => ({ a: new THREE.Vector3(), b: new THREE.Vector3(), s: new THREE.Vector3(), up: new THREE.Vector3(), q: new THREE.Quaternion() }), []);
  useFrame((_, dtRaw) => {
    const { playing: on, spinning: rotorsOn, drive: driving, groundAt: ground } = state.current;
    if (!on) {
      // Paused: the blades stand still, so there is no blur. A drone parked on the ground with no
      // flight under way (e.g. after Restart) has its rotors stopped, so they do not resume spinning.
      for (const d of discs) (d.material as THREE.MeshBasicMaterial).opacity = 0;
      if (rotors.length) {
        let parked: THREE.Object3D | null = holder.current;
        while (parked && parked.userData.agl === undefined) parked = parked.parent;
        const airborne = ((parked?.userData.agl as number | undefined) ?? 0) > AIRBORNE_M;
        if (!rotorsOn && !airborne) {
          rotorSpeed.current = 0;
          if (parked) parked.userData.rotor = 0;
        }
      }
      return;
    }
    const dt = Math.min(dtRaw, 0.05);
    if (dt <= 0) return;
    let agent: THREE.Object3D | null = holder.current;
    while (agent && agent.userData.agl === undefined) agent = agent.parent;
    if (rotors.length) {
      // Airborne: the drawn drone may still be climbing or settling after the data says IDLE.
      const airborne = ((agent?.userData.agl as number | undefined) ?? 0) > AIRBORNE_M;
      // Rotor speed ramps up before lift-off and down after touchdown (share of full speed). The
      // drawn drone only leaves the pad once it is near full speed (SmoothedPose reads userData.rotor).
      const target = rotorsOn || airborne ? 1 : 0;
      const rate = target > rotorSpeed.current ? ROTOR_SPINUP_PER_S : ROTOR_SPINDOWN_PER_S;
      rotorSpeed.current = Math.max(0, Math.min(1, rotorSpeed.current + Math.sign(target - rotorSpeed.current) * rate * dt));
      if (agent) agent.userData.rotor = rotorSpeed.current;
      for (const d of discs) (d.material as THREE.MeshBasicMaterial).opacity = 0.35 * rotorSpeed.current * rotorSpeed.current;
      if (rotorSpeed.current > 0) {
        angle.current = (angle.current + ROTOR_RAD_S * rotorSpeed.current * dt) % (2 * Math.PI);
        for (const r of rotors) {
          turn.setFromAxisAngle(r.axis, r.dir * angle.current);
          r.node.quaternion.copy(turn).multiply(r.rest);
        }
      }
    }
    if (!driving || !wheels.length || !agent) return;

    // Speed and turn rate of the drawn rover. The agent group faces +x at yaw 0 (Three.js), so its
    // forward is (cos yaw, 0, -sin yaw); positive yaw turns it to the left.
    const p = agent.position;
    const yaw = agent.rotation.y;
    const m = motion.current;
    if (!m) {
      motion.current = { x: p.x, z: p.z, yaw, v: 0, w: 0 };
      return;
    }
    const dyaw = Math.atan2(Math.sin(yaw - m.yaw), Math.cos(yaw - m.yaw));
    const vNow = ((p.x - m.x) * Math.cos(yaw) - (p.z - m.z) * Math.sin(yaw)) / dt;
    const k = 1 - Math.exp(-dt / MOTION_TAU_S);
    m.v += (vNow - m.v) * k;
    m.w += (dyaw / dt - m.w) * k;
    m.x = p.x;
    m.z = p.z;
    m.yaw = yaw;
    const moving = Math.abs(m.v) > 0.005 || Math.abs(m.w) > 0.01;

    const kSteer = 1 - Math.exp(-dt / STEER_TAU_S);
    const kLift = 1 - Math.exp(-dt / SUSPENSION_TAU_S);
    for (const w of wheels) {
      // Wheel position from the centre (m). Model frame: forward +z, left +x, up +y; a yaw rate w
      // about +y gives the wheel a velocity (w * z, 0, v - w * x) on top of the forward speed.
      const x = w.rest.x * fit.scale;
      const z = w.rest.z * fit.scale;
      const vx = m.w * z;
      const vz = m.v - m.w * x;
      let steer = 0;
      let speed = vz;
      if (w.steers && moving) {
        // Steer so the wheel rolls along its own velocity (Ackermann; in a turn on the spot the
        // corner wheels splay to face around the centre). Beyond 90 degrees it rolls backwards.
        steer = Math.atan2(vx, vz);
        speed = Math.hypot(vx, vz);
        if (steer > Math.PI / 2) {
          steer -= Math.PI;
          speed = -speed;
        } else if (steer < -Math.PI / 2) {
          steer += Math.PI;
          speed = -speed;
        }
        steer = THREE.MathUtils.clamp(steer, -STEER_MAX, STEER_MAX);
      }
      w.steer += (steer - w.steer) * kSteer;
      w.pivot.rotation.y = w.steer;
      if (w.joint) w.joint.pivot.rotation.y = w.steer; // the steering actuator turns with its wheel
      // Rolling without slipping: angle = distance / radius (metres at true size).
      w.pivot.rotation.x += (speed * dt) / (w.radius * fit.scale);

      // Suspension: lift or drop the wheel so its lowest point meets the drawn ground under it.
      if (ground) {
        const parent = w.pivot.parent!;
        parent.localToWorld(tmp.a.copy(w.rest));
        parent.getWorldQuaternion(tmp.q);
        tmp.up.set(0, 1, 0).applyQuaternion(tmp.q);
        parent.getWorldScale(tmp.s);
        const unit = tmp.s.y; // world metres per mesh unit
        const contactY = tmp.a.y - tmp.up.y * w.radius * unit;
        const g = ground(tmp.a.x, tmp.a.z);
        if (g != null && unit > 0) {
          const travel = WHEEL_TRAVEL_M / fit.scale;
          const target = THREE.MathUtils.clamp((g - contactY) / Math.max(tmp.up.y, 0.5) / unit, -travel, travel);
          w.lift += (target - w.lift) * kLift;
        }
        w.pivot.position.set(w.rest.x, w.rest.y + w.lift, w.rest.z);
        if (w.joint) w.joint.pivot.position.set(w.joint.rest.x, w.joint.rest.y + w.lift * w.joint.liftScale, w.joint.rest.z);
      }
    }
  });

  // Rover rig: steps the shared mast/zoom/arm state and poses the head and the arm on this model.
  const rigNodes = useMemo(() => (drive ? rigNodesOf(model) : null), [model, drive]);
  const rigTmp = useMemo(() => ({ a: new THREE.Quaternion(), b: new THREE.Quaternion(), x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0) }), []);
  useFrame((_, dtRaw) => {
    if (!rigNodes) return;
    // Wall time, capped only for a long pause (hidden tab): the mast and arm keep their real pace at a low frame rate.
    const dt = Math.min(Math.max(dtRaw, 0), 0.5);
    const m = motion.current;
    const stationary = !m || (Math.abs(m.v) < 0.05 && Math.abs(m.w) < 0.02);
    stepRig(roverRig, dt, stationary);
    // Head: pan (az clockwise from the front = about -y), then tilt (el up = about -x).
    rigTmp.a.setFromAxisAngle(rigTmp.y, -THREE.MathUtils.degToRad(roverRig.az));
    rigTmp.b.setFromAxisAngle(rigTmp.x, -THREE.MathUtils.degToRad(roverRig.el));
    rigNodes.head.quaternion.copy(rigNodes.headRest).multiply(rigTmp.a).multiply(rigTmp.b);
    // Arm: every joint moves together from the model's rest pose to the close-up pose, eased.
    const s = roverRig.arm;
    const e = s * s * (3 - 2 * s);
    rigNodes.arm.forEach((j, k) => {
      rigTmp.a.setFromAxisAngle(ARM_AXES[k], THREE.MathUtils.degToRad(ARM_STOWED_DEG[k] + (ARM_DEPLOYED_DEG[k] - ARM_STOWED_DEG[k]) * e));
      j.node.quaternion.copy(j.rest).multiply(rigTmp.a);
    });
  }, RIG_PRIORITY);

  return (
    <group ref={holder} rotation={[0, yawOffset, 0]}>
      <primitive object={model} scale={fit.scale} position={fit.offset} />
      {rotors.length > 0 && <Downwash holder={holder} rotors={rotors.map((r) => r.node)} radiusM={lengthM / 2} speed={rotorSpeed} playing={playing} />}
    </group>
  );
}

useGLTF.preload(ROVER_URL, false, false);
useGLTF.preload(DRONE_URL, false, false);
