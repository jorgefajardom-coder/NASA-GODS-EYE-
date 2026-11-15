import { LABEL_Z } from '../lib/labels';
import { Html } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { Suspense, useEffect, useMemo, useRef, type ReactNode } from 'react';
import * as THREE from 'three';
import { AGENT_POSE_TAU_S, dampAngle, dampFactor, SNAP_DISTANCE_M } from '../lib/smoothing';
import type { AgentState } from '../types/icd';
import { enuToThree, yawFromQuaternion } from '../lib/coords';
import { AstronautModel, ModelBoundary } from './AstronautModel';
import { DRONE_URL, ROVER_URL, VehicleModel } from './VehicleModel';
import { ScaleWithDistance } from './ScaleWithDistance';

const KIND_COLOR = { HUMAN: '#C9D7DD', DRONE: '#65CBE8', ROVER: '#D8AD66' } as const;
const KIND_LABEL = { HUMAN: 'Astronaut', DRONE: 'Drone', ROVER: 'Rover' } as const;
/** Real sizes: car-sized rover with its arm (m) and helicopter rotor span (m). */
const ROVER_LENGTH_M = 3.6;
const DRONE_ROTOR_M = 1.2;
/** Label height above each agent's origin (m, before distance scaling). */
const LABEL_HEIGHT_M = { HUMAN: 2.6, DRONE: 1.4, ROVER: 3.0 } as const;
/** Distance enlargement of the models when true scale is off (see ScaleWithDistance). */
const AGENT_SCALE_PER_M = 1 / 80;
const AGENT_SCALE_MAX = 14;
/** Largest dimension of each drawn model (m at true scale), for its size on screen. */
const AGENT_SIZE_M = { HUMAN: 1.9, DRONE: DRONE_ROTOR_M, ROVER: ROVER_LENGTH_M } as const;

interface Props {
  agents: AgentState[];
  /** Replay time (s): a jump (Restart, seek) places every agent at its new pose at once. */
  t: number;
  verticalExaggeration: number;
  showLabels: boolean;
  /** Agent whose label is hidden (seen from inside in the first-person view). */
  hideLabelFor?: string | null;
  /** Replay running; freezes the walk cycle when false. */
  playing: boolean;
  /** Replay speed multiplier and per-agent simulated ground speed, for the walk cycle rate. */
  replaySpeed: number;
  speeds: Record<string, number>;
  /** Agent highlighted in the list. */
  selectedId: string | null;
  /** Terrain height under (x, y) in the layer on screen, for the drone altitude line. */
  groundHeight: (x: number, y: number) => number | null;
  /** True size at every zoom; when false, agents are enlarged with camera distance (visual only). */
  trueScale: boolean;
}

/**
 * Each agent is drawn at the pose it is given (position and yaw from AgentState, visually
 * interpolated between two received samples by the replay state, never extrapolated).
 * Models are enlarged with camera distance so they stay readable on a 2 km map; the
 * enlargement is visual only and does not change any position.
 */
export function AgentLayer({ agents, t, verticalExaggeration, showLabels, hideLabelFor = null, playing, replaySpeed, speeds, selectedId, groundHeight, trueScale }: Props) {
  // Drawn ground height at a Three.js (x, z), for the rover's per-wheel suspension.
  const groundAtWorld = useMemo(
    () => (x: number, z: number) => {
      const h = groundHeight(x, -z);
      return h == null ? null : h * verticalExaggeration;
    },
    [groundHeight, verticalExaggeration],
  );
  return (
    <group name="agents">
      {agents.map((a) => {
        // Ground agents are snapped to the surface on screen (visual only; x and y are as received).
        // The drone keeps its true height above the drawn ground: exaggerating its absolute z with the
        // relief would bury it when it is parked (pose z below the drawn, smoothed surface).
        const p = a.pose.position;
        const ground = groundHeight(p.x, p.y);
        // Below 1 m the drone counts as landed (agl 0): its parked height comes from another terrain
        // model than the drawn one, and that small difference must not leave the legs in the air.
        const rawAgl = a.agent_kind === 'DRONE' && ground != null ? droneAgl(p.z, ground) : 0;
        const agl = rawAgl < DRONE_LANDED_M ? 0 : rawAgl;
        const [x, gy, z] = enuToThree(ground == null ? p : { ...p, z: ground }, verticalExaggeration);
        const yaw = yawFromQuaternion(a.pose.orientation);
        // A flying drone never passes through the drawn relief: it keeps a floor above the
        // highest ground around it and ramps up ahead of walls on its heading (see droneFloor).
        const airborne = a.agent_kind === 'DRONE' && a.mode !== 'IDLE';
        const floorY = airborne ? droneFloor(groundHeight, p.x, p.y, yaw, verticalExaggeration) : null;
        const y = floorY == null ? gy + agl : Math.max(gy + agl, floorY);
        return (
          <SmoothedPose
            key={a.agent_id}
            position={[x, y, z]}
            groundY={gy}
            t={t}
            floorY={floorY}
            groundAt={a.agent_kind === 'DRONE' ? groundAtWorld : undefined}
            yaw={yaw}
            name={`agent-${a.agent_id}`}
            climbMps={a.agent_kind === 'DRONE' ? DRONE_DRAWN_CLIMB_MPS : undefined}
          >
            <ScaleWithDistance perMetre={AGENT_SCALE_PER_M} max={trueScale ? 1 : AGENT_SCALE_MAX}>
              {a.agent_id === selectedId && <SelectionRing groundHeight={groundHeight} verticalExaggeration={verticalExaggeration} />}
              {a.agent_kind === 'HUMAN' ? (
                <ModelBoundary fallback={<AgentMesh kind="HUMAN" />}>
                  <Suspense fallback={<AgentMesh kind="HUMAN" />}>
                    <AstronautModel mode={a.mode} playing={playing} screenSpeedMps={(speeds[a.agent_id] ?? 0) * replaySpeed} />
                  </Suspense>
                </ModelBoundary>
              ) : (
                <ModelBoundary fallback={<AgentMesh kind={a.agent_kind} />}>
                  <Suspense fallback={<AgentMesh kind={a.agent_kind} />}>
                    {a.agent_kind === 'ROVER' ? (
                      // The model already faces +x (its front hazcams point along its local +z, turned 90 degrees).
                      <TerrainTilt groundHeight={groundHeight} verticalExaggeration={verticalExaggeration}>
                        <VehicleModel url={ROVER_URL} lengthM={ROVER_LENGTH_M} playing={playing} drive groundAt={groundAtWorld} />
                      </TerrainTilt>
                    ) : (
                      // Landed, the drone sits on its four legs: tilted to the ground under them (level in flight).
                      <TerrainTilt groundHeight={groundHeight} verticalExaggeration={verticalExaggeration} lengthM={DRONE_LEGS_M} widthM={DRONE_LEGS_M} landedOnly>
                        <VehicleModel url={DRONE_URL} lengthM={DRONE_ROTOR_M} playing={playing} spinning={a.mode !== 'IDLE'} />
                      </TerrainTilt>
                    )}
                  </Suspense>
                </ModelBoundary>
              )}
              {showLabels && a.agent_id !== hideLabelFor && (
                <Html position={[0, LABEL_HEIGHT_M[a.agent_kind], 0]} center zIndexRange={LABEL_Z} className={`agent-label agent-label--${a.agent_kind.toLowerCase()}`}>
                  <strong>{KIND_LABEL[a.agent_kind]}</strong> <span>{a.mode.toLowerCase()}</span>
                </Html>
              )}
            </ScaleWithDistance>
            <DistanceMarker kind={a.agent_kind} selected={a.agent_id === selectedId} enlarged={!trueScale} />
            {a.agent_kind === 'DRONE' && <DroneTether />}
          </SmoothedPose>
        );
      })}
    </group>
  );
}

/** Clearance the drawn drone keeps over the highest drawn ground around and ahead of it (m). */
const DRONE_CLEARANCE_M = 8;
/** Radius around the drone that must be clear (m), and how far ahead walls are looked for (m). */
const DRONE_FOOTPRINT_M = 10;
const DRONE_LOOKAHEAD_M = 80;
/** Slope of the climb ramp in front of a wall (rise per metre ahead): 0.5 = about 27 degrees. */
const DRONE_RAMP = 0.5;

/**
 * Lowest drawn height (Three.js y) the flying drone may have at ENU (x, y) with heading `yaw`:
 * the highest drawn ground within its footprint plus the clearance, and for ground ahead on its
 * heading that height minus a ramp of DRONE_RAMP per metre of distance, so the floor rises
 * gradually as a wall approaches and the drone climbs over it instead of through it. Display
 * only: the received altitude is kept whenever it is already above this floor.
 */
export function droneFloor(
  groundHeight: (x: number, y: number) => number | null,
  x: number,
  y: number,
  yaw: number,
  verticalExaggeration: number,
): number | null {
  let best = -Infinity;
  const consider = (px: number, py: number, ahead: number) => {
    const h = groundHeight(px, py);
    if (h == null) return;
    best = Math.max(best, h * verticalExaggeration + DRONE_CLEARANCE_M - ahead * DRONE_RAMP);
  };
  consider(x, y, 0);
  for (let k = 0; k < 8; k++) {
    const a = (k / 8) * Math.PI * 2;
    consider(x + Math.cos(a) * DRONE_FOOTPRINT_M, y + Math.sin(a) * DRONE_FOOTPRINT_M, 0);
  }
  const fx = Math.cos(yaw);
  const fy = Math.sin(yaw);
  for (let d = 10; d <= DRONE_LOOKAHEAD_M; d += 10) {
    consider(x + fx * d, y + fy * d, Math.max(0, d - DRONE_FOOTPRINT_M));
  }
  return best === -Infinity ? null : best;
}

/** Fastest drawn climb or descent of the drone (m/s of wall time); see SmoothedPose. */
const DRONE_DRAWN_CLIMB_MPS = 3;
/** Height above the pad (m) below which the drone may not move sideways or turn. */
const DRONE_LIFTOFF_M = 2;
/** Share of full rotor speed the drone needs before it may leave the pad. */
const ROTOR_LIFT = 0.9;
/** Vertical spring of the drone's drawn height (rad/s): sets how gently climbs start and end. */
const CLIMB_OMEGA = 1.6;

/**
 * Draws an agent at an eased copy of its pose (display only). Poses come from React at
 * the replay clock's pace, in uneven steps relative to rendering; easing them over
 * ~0.1 s removes the trembling that is visible when the camera is close. Large horizontal jumps
 * (seek, restart) are shown at once.
 *
 * With `climbMps` (the drone) the drawn height follows the data through a critically damped
 * spring limited to that vertical speed. The simulated drone goes from its pad to ~40 m above
 * ground in one 2 s sample and lands the same way; drawn as received that is a jump, so it is
 * shown lifting off and touching down gently instead, lagging the received altitude for a few
 * seconds around take-off and landing. Positions in the data are unchanged.
 * The drawn height above ground is left in userData.agl for the rotors and the tether.
 */
function SmoothedPose({
  position,
  groundY,
  yaw,
  name,
  climbMps,
  floorY = null,
  groundAt,
  t,
  children,
}: {
  position: [number, number, number];
  /** Replay time (s), to detect jumps. */
  t: number;
  /** Drawn ground height under the target (Three.js y). */
  groundY: number;
  /** Lowest drawn height allowed while flying (clearance over the relief), or null. */
  floorY?: number | null;
  /**
   * Drawn ground height at a Three.js (x, z). When given (the drone), the ground limit is read
   * under the drawn position, not under the received one: they differ while the drone is held
   * on its pad, lags its data or after a seek, and the terrain between them can be higher.
   */
  groundAt?: (x: number, z: number) => number | null;
  yaw: number;
  name: string;
  climbMps?: number;
  children: ReactNode;
}) {
  const group = useRef<THREE.Group>(null);
  const target = useRef(new THREE.Vector3());
  const placed = useRef(false);
  const vy = useRef(0);
  target.current.set(position[0], position[1], position[2]);
  const ground = useRef(groundY);
  ground.current = groundY;
  const floor = useRef(floorY);
  floor.current = floorY;
  const cruising = useRef(false);
  const time = useRef(t);
  time.current = t;
  const lastT = useRef<number | null>(null);
  // Priority -2: eased before the follow camera and the distance scaling read this group.
  useFrame((_, dtRaw) => {
    const g = group.current;
    if (!g) return;
    const dt = Math.min(dtRaw, 0.1);
    const t = target.current;
    const horizontal = Math.hypot(g.position.x - t.x, g.position.z - t.z);
    // Replay time jumped (Restart, seek backwards, or ahead by more than REPLAY_JUMP_S): the agent
    // is placed at its new pose at once instead of gliding there (a drone would descend from the air).
    const now = time.current;
    const jumped = lastT.current != null && (now < lastT.current - 1e-3 || now - lastT.current > REPLAY_JUMP_S);
    lastT.current = now;
    if (!placed.current || jumped || horizontal > SNAP_DISTANCE_M || Math.abs(g.position.y - t.y) > 4 * SNAP_DISTANCE_M) {
      g.position.copy(t);
      g.rotation.y = yaw;
      vy.current = 0;
      cruising.current = false;
      if (groundAt) {
        const h = groundAt(t.x, t.z);
        if (h != null) ground.current = h;
      }
      placed.current = true;
    } else {
      const k = dampFactor(dt, AGENT_POSE_TAU_S);
      if (groundAt) {
        const h = groundAt(g.position.x, g.position.z);
        if (h != null) ground.current = h;
      }
      // A drone on (or just above) its pad can neither move sideways nor turn: it first has to be
      // in the air. Ground agents always follow their pose.
      const pinned = !!climbMps && g.position.y - ground.current < DRONE_LIFTOFF_M;
      if (!pinned) {
        g.position.x += (t.x - g.position.x) * k;
        g.position.z += (t.z - g.position.z) * k;
      }
      if (climbMps && (g.userData.rotor ?? 1) < ROTOR_LIFT && g.position.y - ground.current < 0.5) {
        // Rotors still spinning up: the drone stays on its pad, whatever the data says.
        g.position.y = ground.current;
        vy.current = 0;
        cruising.current = false;
      } else if (climbMps) {
        const w = CLIMB_OMEGA;
        vy.current += (w * w * (t.y - g.position.y) - 2 * w * vy.current) * dt;
        vy.current = THREE.MathUtils.clamp(vy.current, -climbMps, climbMps);
        g.position.y += vy.current * dt;
        // Never below the drawn ground (landing pad). While flying, once the drone has climbed to
        // the clearance floor it is held above it: the floor rises ahead of walls, so the drone
        // goes over them at any replay speed. Before that (take-off) it rises smoothly to it.
        const f = floor.current;
        if (f == null) cruising.current = false;
        else if (g.position.y >= f - 0.05) cruising.current = true;
        const minY = cruising.current && f != null ? Math.max(ground.current, f) : ground.current;
        if (g.position.y < minY) {
          g.position.y = minY;
          vy.current = Math.max(0, vy.current);
        }
      } else {
        g.position.y += (t.y - g.position.y) * k;
      }
      if (!pinned) g.rotation.y = dampAngle(g.rotation.y, yaw, dt, AGENT_POSE_TAU_S);
    }
    g.userData.agl = Math.max(0, g.position.y - ground.current);
  }, -2);
  return (
    <group ref={group} name={name}>
      {children}
    </group>
  );
}

/** Replay-time step (s) above which a change counts as a jump (seek) rather than playback. */
const REPLAY_JUMP_S = 3;
/** Height above the drawn ground (m) below which the drone is drawn landed, legs on the surface. */
const DRONE_LANDED_M = 1;
/** Spread of the drone's landing legs (m), for the slope it rests on. */
const DRONE_LEGS_M = 0.8;
/** Rover footprint used to read the slope under it (m): wheelbase and track. */
const TILT_LENGTH_M = 2.8;
const TILT_WIDTH_M = 2.7;
/** Easing of the body tilt (s), like a suspension settling. */
const TILT_TAU_S = 0.25;

/**
 * Pitches and rolls its children to the drawn terrain under a rover-sized footprint, so the
 * vehicle sits on the slope instead of floating level over it. Heights are read from the same
 * surface the terrain mesh draws; display only.
 */
function TerrainTilt({
  groundHeight,
  verticalExaggeration,
  lengthM = TILT_LENGTH_M,
  widthM = TILT_WIDTH_M,
  landedOnly = false,
  children,
}: {
  groundHeight: (x: number, y: number) => number | null;
  verticalExaggeration: number;
  /** Footprint read for the slope (m): along and across the heading. */
  lengthM?: number;
  widthM?: number;
  /** Tilt only while on the ground (the drone); level once it is in the air. */
  landedOnly?: boolean;
  children: ReactNode;
}) {
  const group = useRef<THREE.Group>(null);
  const world = useMemo(() => new THREE.Vector3(), []);
  useFrame((_, dt) => {
    const g = group.current;
    const agent = g?.parent?.parent; // TerrainTilt < ScaleWithDistance < SmoothedPose (position, yaw)
    if (!g || !agent) return;
    agent.getWorldPosition(world);
    const yaw = agent.rotation.y;
    // Three.js -> ENU: east = x, north = -z. Forward (yaw) and left in ENU.
    const e = world.x;
    const n = -world.z;
    const fx = Math.cos(yaw);
    const fy = Math.sin(yaw);
    const at = (along: number, left: number) => groundHeight(e + fx * along - fy * left, n + fy * along + fx * left);
    const hf = at(lengthM / 2, 0);
    const hb = at(-lengthM / 2, 0);
    const hl = at(0, widthM / 2);
    const hr = at(0, -widthM / 2);
    if (hf == null || hb == null || hl == null || hr == null) return;
    // Local frame: forward +x, up +y, left -z. Nose up = +z rotation; left side up = +x rotation.
    const level = landedOnly && ((agent.userData.agl as number | undefined) ?? 0) > 0.3;
    const pitch = level ? 0 : Math.atan2((hf - hb) * verticalExaggeration, lengthM);
    const roll = level ? 0 : Math.atan2((hl - hr) * verticalExaggeration, widthM);
    const k = dampFactor(dt, TILT_TAU_S);
    g.rotation.z += (pitch - g.rotation.z) * k;
    g.rotation.x += (roll - g.rotation.x) * k;
  });
  return <group ref={group}>{children}</group>;
}

function AgentMesh({ kind }: { kind: AgentState['agent_kind'] }) {
  const color = KIND_COLOR[kind];
  if (kind === 'HUMAN') {
    // Simplified astronaut: suit body, helmet and backpack, ~2 m tall for visibility.
    return (
      <group>
        <mesh position={[0, 1.6, 0]} castShadow>
          <capsuleGeometry args={[0.9, 1.6, 6, 12]} />
          <meshStandardMaterial color={color} roughness={0.6} />
        </mesh>
        <mesh position={[0, 3.4, 0]} castShadow>
          <sphereGeometry args={[0.85, 16, 12]} />
          <meshStandardMaterial color="#d9dde3" roughness={0.3} />
        </mesh>
        <mesh position={[0.35, 3.45, 0]}>
          <sphereGeometry args={[0.6, 16, 12, 0, Math.PI]} />
          <meshStandardMaterial color="#e3a740" metalness={0.6} roughness={0.2} />
        </mesh>
        <mesh position={[-0.9, 1.9, 0]}>
          <boxGeometry args={[0.6, 1.4, 1.2]} />
          <meshStandardMaterial color="#b9bec6" />
        </mesh>
        {/* Heading indicator pointing along +x (east at yaw 0). */}
        <mesh position={[2.2, 0.3, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.6, 1.4, 12]} />
          <meshStandardMaterial color="#ff8c42" />
        </mesh>
      </group>
    );
  }
  if (kind === 'ROVER') {
    return (
      <group>
        <mesh position={[0, 1.2, 0]} castShadow>
          <boxGeometry args={[4, 1.2, 2.6]} />
          <meshStandardMaterial color={color} roughness={0.7} />
        </mesh>
        <mesh position={[0.9, 2.6, 0]}>
          <cylinderGeometry args={[0.15, 0.15, 1.8, 8]} />
          <meshStandardMaterial color="#cfd3da" />
        </mesh>
        {[-1.4, 0, 1.4].flatMap((dx) =>
          [-1.45, 1.45].map((dz) => (
            <mesh key={`${dx}${dz}`} position={[dx, 0.5, dz]} rotation={[Math.PI / 2, 0, 0]}>
              <cylinderGeometry args={[0.5, 0.5, 0.4, 12]} />
              <meshStandardMaterial color="#3a3a3a" />
            </mesh>
          )),
        )}
      </group>
    );
  }
  return (
    <group>
      <mesh castShadow>
        <octahedronGeometry args={[1.4, 0]} />
        <meshStandardMaterial color={color} roughness={0.4} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.4, 0.18, 8, 32]} />
        <meshStandardMaterial color="#9fd6ff" />
      </mesh>
    </group>
  );
}

/**
 * Model size on screen (px) below which the pin takes over: fully shown under MARKER_FULL_PX,
 * gone above MARKER_NONE_PX. Up close the rover, astronaut and drone themselves are drawn.
 */
const MARKER_FULL_PX = 2;
const MARKER_NONE_PX = 5;
/** Marker size as a fraction of the viewport height (screen size, independent of distance). */
const MARKER_SIZE = 0.028;

const markerTextures = new Map<string, THREE.Texture>();
/** Round pin texture: kind colour disc, dark outline, white core. Cached per colour. */
function markerTexture(color: string): THREE.Texture | null {
  if (typeof document === 'undefined') return null;
  const cached = markerTextures.get(color);
  if (cached) return cached;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d')!;
  g.beginPath();
  g.arc(32, 32, 27, 0, Math.PI * 2);
  g.fillStyle = 'rgba(9,13,17,0.85)';
  g.fill();
  g.beginPath();
  g.arc(32, 32, 22, 0, Math.PI * 2);
  g.fillStyle = color;
  g.fill();
  g.beginPath();
  g.arc(32, 32, 8, 0, Math.PI * 2);
  g.fillStyle = '#ffffff';
  g.fill();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  markerTextures.set(color, t);
  return t;
}

/** Height on screen (px) of an object `sizeM` tall at `distanceM` from a perspective camera. */
export function screenSizePx(sizeM: number, distanceM: number, fovDeg: number, viewportPx: number): number {
  if (!(distanceM > 0)) return Infinity;
  return (sizeM * viewportPx) / (2 * distanceM * Math.tan(THREE.MathUtils.degToRad(fovDeg) / 2));
}

/**
 * Screen-size pin at the agent's position, shown only when the model itself would be a few
 * pixels tall (a 1.9 m astronaut at true scale is lost on the map from a few hundred metres).
 * It keeps a constant size on screen, draws over the terrain and fades out as the model grows
 * readable. Display only; positions are unchanged.
 */
function DistanceMarker({ kind, selected, enlarged }: { kind: AgentState['agent_kind']; selected: boolean; enlarged: boolean }) {
  const sprite = useRef<THREE.Sprite>(null);
  const material = useMemo(
    () => new THREE.SpriteMaterial({ map: markerTexture(KIND_COLOR[kind]), sizeAttenuation: false, depthTest: false, depthWrite: false, transparent: true }),
    [kind],
  );
  const world = useMemo(() => new THREE.Vector3(), []);
  useFrame(({ camera, size }) => {
    const s = sprite.current;
    if (!s) return;
    s.getWorldPosition(world);
    const d = camera.position.distanceTo(world);
    const scale = enlarged ? THREE.MathUtils.clamp(d * AGENT_SCALE_PER_M, 1, AGENT_SCALE_MAX) : 1;
    const fov = (camera as THREE.PerspectiveCamera).fov ?? 38;
    const px = screenSizePx(AGENT_SIZE_M[kind] * scale, d, fov, size.height);
    const k = 1 - THREE.MathUtils.smoothstep(px, MARKER_FULL_PX, MARKER_NONE_PX);
    material.opacity = k;
    s.visible = k > 0.01;
    const m = MARKER_SIZE * (selected ? 1.35 : 1);
    s.scale.set(m, m, 1);
  });
  useEffect(() => () => material.dispose(), [material]);
  return <sprite ref={sprite} material={material} position={[0, 1.2, 0]} renderOrder={10} />;
}

/** Selection ring size (m at true scale) and its lift above the drawn ground. */
const RING_INNER_M = 3.4;
const RING_OUTER_M = 4;
const RING_SEGMENTS = 64;
const RING_LIFT_M = 0.12;

/**
 * Ring around the selected agent that lies on the drawn terrain: every vertex takes the ground
 * height under it (same surface as the mesh), so on slopes and bumps no part of the ring goes
 * under the ground and gets cut off. Updated each frame in the parent's frame, so it follows the
 * eased pose, the heading and the distance scaling.
 */
function SelectionRing({ groundHeight, verticalExaggeration }: { groundHeight: (x: number, y: number) => number | null; verticalExaggeration: number }) {
  const mesh = useRef<THREE.Mesh>(null);
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const n = RING_SEGMENTS;
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array((n + 1) * 2 * 3), 3));
    const index: number[] = [];
    for (let i = 0; i < n; i++) {
      const a = i * 2, b = a + 1, c = a + 2, d = a + 3; // inner/outer pairs
      index.push(a, c, b, b, c, d);
    }
    g.setIndex(index);
    return g;
  }, []);
  const center = useMemo(() => new THREE.Vector3(), []);
  const scale = useMemo(() => new THREE.Vector3(), []);
  const p = useMemo(() => new THREE.Vector3(), []);
  useFrame(() => {
    const m = mesh.current;
    const parent = m?.parent;
    if (!m || !parent) return;
    parent.updateWorldMatrix(true, false);
    parent.getWorldPosition(center);
    parent.getWorldScale(scale);
    const s = scale.x;
    const attr = geometry.getAttribute('position') as THREE.BufferAttribute;
    for (let i = 0; i <= RING_SEGMENTS; i++) {
      const t = (i / RING_SEGMENTS) * Math.PI * 2;
      for (let k = 0; k < 2; k++) {
        const r = (k === 0 ? RING_INNER_M : RING_OUTER_M) * s;
        const wx = center.x + Math.cos(t) * r;
        const wz = center.z + Math.sin(t) * r;
        // Three.js -> ENU: east = x, north = -z. Ground height is drawn with the exaggeration.
        const h = groundHeight(wx, -wz);
        const wy = (h == null ? center.y / Math.max(verticalExaggeration, 1e-6) : h) * verticalExaggeration + RING_LIFT_M * s;
        parent.worldToLocal(p.set(wx, wy, wz));
        attr.setXYZ(i * 2 + k, p.x, p.y, p.z);
      }
    }
    attr.needsUpdate = true;
    geometry.computeBoundingSphere();
  });
  useEffect(() => () => geometry.dispose(), [geometry]);
  return (
    <mesh ref={mesh} geometry={geometry} renderOrder={2} frustumCulled={false}>
      <meshBasicMaterial color="#65CBE8" transparent opacity={0.9} depthWrite={false} side={THREE.DoubleSide} polygonOffset polygonOffsetFactor={-2} polygonOffsetUnits={-2} />
    </mesh>
  );
}

/** Drone height above ground (m): never below the surface, never scaled by the relief exaggeration. */
export function droneAgl(poseZ: number, groundZ: number): number {
  return Math.max(0, poseZ - groundZ);
}

/** Vertical line from the drone to the ground so its altitude is readable (follows the drawn height). */
function DroneTether() {
  const mesh = useRef<THREE.Mesh>(null);
  useFrame(() => {
    const m = mesh.current;
    if (!m) return;
    const agl = (m.parent?.userData.agl as number | undefined) ?? 0;
    m.visible = agl > 0.5;
    m.scale.set(1, Math.max(agl, 1e-3), 1);
    m.position.y = -agl / 2;
  });
  return (
    <mesh ref={mesh} visible={false}>
      <cylinderGeometry args={[0.08, 0.08, 1, 6]} />
      <meshBasicMaterial color="#7cc7ff" transparent opacity={0.5} />
    </mesh>
  );
}
