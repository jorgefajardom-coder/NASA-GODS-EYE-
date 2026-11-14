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

interface Props {
  agents: AgentState[];
  verticalExaggeration: number;
  showLabels: boolean;
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
export function AgentLayer({ agents, verticalExaggeration, showLabels, playing, replaySpeed, speeds, selectedId, groundHeight, trueScale }: Props) {
  return (
    <group name="agents">
      {agents.map((a) => {
        // Ground agents are snapped to the surface on screen (visual only; x and y are as received).
        // The drone keeps its true height above the drawn ground: exaggerating its absolute z with the
        // relief would bury it when it is parked (pose z below the drawn, smoothed surface).
        const p = a.pose.position;
        const ground = groundHeight(p.x, p.y);
        const agl = a.agent_kind === 'DRONE' && ground != null ? droneAgl(p.z, ground) : 0;
        const [x, gy, z] = enuToThree(ground == null ? p : { ...p, z: ground }, verticalExaggeration);
        const y = gy + agl;
        const yaw = yawFromQuaternion(a.pose.orientation);
        return (
          <SmoothedPose key={a.agent_id} position={[x, y, z]} yaw={yaw} name={`agent-${a.agent_id}`}>
            <ScaleWithDistance perMetre={1 / 80} max={trueScale ? 1 : 14}>
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
                      <VehicleModel url={ROVER_URL} lengthM={ROVER_LENGTH_M} yawOffset={Math.PI} />
                    ) : (
                      <VehicleModel url={DRONE_URL} lengthM={DRONE_ROTOR_M} spinning={playing && a.mode !== 'IDLE'} />
                    )}
                  </Suspense>
                </ModelBoundary>
              )}
              {showLabels && (
                <Html position={[0, LABEL_HEIGHT_M[a.agent_kind], 0]} center zIndexRange={[30, 0]} className={`agent-label agent-label--${a.agent_kind.toLowerCase()}`}>
                  <strong>{KIND_LABEL[a.agent_kind]}</strong> <span>{a.mode.toLowerCase()}</span>
                </Html>
              )}
            </ScaleWithDistance>
            {a.agent_kind === 'DRONE' && (
              <DroneTether heightAboveGround={agl} />
            )}
          </SmoothedPose>
        );
      })}
    </group>
  );
}

/**
 * Draws an agent at an eased copy of its pose (display only). Poses come from React at
 * the replay clock's pace, in uneven steps relative to rendering; easing them over
 * ~0.1 s removes the trembling that is visible when the camera is close. Large jumps
 * (seek, restart) are shown at once.
 */
function SmoothedPose({ position, yaw, name, children }: { position: [number, number, number]; yaw: number; name: string; children: ReactNode }) {
  const group = useRef<THREE.Group>(null);
  const target = useRef(new THREE.Vector3());
  const placed = useRef(false);
  target.current.set(position[0], position[1], position[2]);
  // Priority -2: eased before the follow camera and the distance scaling read this group.
  useFrame((_, dt) => {
    const g = group.current;
    if (!g) return;
    if (!placed.current || g.position.distanceTo(target.current) > SNAP_DISTANCE_M) {
      g.position.copy(target.current);
      g.rotation.y = yaw;
      placed.current = true;
      return;
    }
    g.position.lerp(target.current, dampFactor(dt, AGENT_POSE_TAU_S));
    g.rotation.y = dampAngle(g.rotation.y, yaw, dt, AGENT_POSE_TAU_S);
  }, -2);
  return (
    <group ref={group} name={name}>
      {children}
    </group>
  );
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

/** Vertical line from the drone to the ground so its altitude is readable. */
function DroneTether({ heightAboveGround }: { heightAboveGround: number }) {
  if (heightAboveGround <= 0.5) return null;
  return (
    <mesh position={[0, -heightAboveGround / 2, 0]}>
      <cylinderGeometry args={[0.08, 0.08, heightAboveGround, 6]} />
      <meshBasicMaterial color="#7cc7ff" transparent opacity={0.5} />
    </mesh>
  );
}
