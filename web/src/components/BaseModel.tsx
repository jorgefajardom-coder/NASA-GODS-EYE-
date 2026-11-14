import { useMemo, type ReactElement } from 'react';
import * as THREE from 'three';
import type { Point } from '../types/icd';

/**
 * Surface habitat at the base site: an original, generic layout (two horizontal habitat
 * modules, a domed hub, pressurized tunnels, storage tanks, cargo containers, a solar field
 * and a comms mast). No agency logos, flags or mission marks. Real scale in metres; it is
 * visual context only and has no effect on routes or data.
 */
interface Props {
  /** Base site in frame `map` (ENU). The cluster is built beside it so agents do not start inside a module. */
  site: Point;
  verticalExaggeration: number;
  /** Terrain height under (x, y) in the layer on screen, local metres. */
  groundHeight: (x: number, y: number) => number | null;
}

/** Offset of the habitat cluster from the site point (east, north), metres. */
const CLUSTER_OFFSET = { x: 34, y: -22 };

const WHITE = new THREE.MeshStandardMaterial({ color: '#e9e6df', roughness: 0.55, metalness: 0.05 });
const PANEL_WHITE = new THREE.MeshStandardMaterial({ color: '#d6d2c8', roughness: 0.7 });
const ORANGE = new THREE.MeshStandardMaterial({ color: '#d4692a', roughness: 0.6 });
const GREY = new THREE.MeshStandardMaterial({ color: '#7d7f84', roughness: 0.5, metalness: 0.4 });
const DARK = new THREE.MeshStandardMaterial({ color: '#2b2d31', roughness: 0.6, metalness: 0.3 });
const SOLAR = new THREE.MeshStandardMaterial({ color: '#16213a', roughness: 0.25, metalness: 0.6 });
const GLASS = new THREE.MeshStandardMaterial({ color: '#7fb3d1', roughness: 0.1, metalness: 0.8 });

/** One placed part: local east/north offset from the cluster centre and a builder. */
type Part = { e: number; n: number; yaw?: number; node: ReactElement };

function Habitat({ length = 12, radius = 2.2, bands = true }: { length?: number; radius?: number; bands?: boolean }) {
  return (
    <group>
      {/* Horizontal pressure vessel on short legs, axis along local x. */}
      <mesh position={[0, radius + 0.6, 0]} rotation={[0, 0, Math.PI / 2]} material={WHITE} castShadow receiveShadow>
        <cylinderGeometry args={[radius, radius, length, 32]} />
      </mesh>
      {[-1, 1].map((s) => (
        <mesh key={s} position={[(s * length) / 2, radius + 0.6, 0]} rotation={[0, 0, Math.PI / 2]} material={bands ? ORANGE : PANEL_WHITE}>
          <cylinderGeometry args={[radius * 1.02, radius * 1.02, 0.5, 32]} />
        </mesh>
      ))}
      {/* Ribs and a window strip. */}
      {[-length / 4, 0, length / 4].map((x) => (
        <mesh key={x} position={[x, radius + 0.6, 0]} rotation={[0, 0, Math.PI / 2]} material={PANEL_WHITE}>
          <cylinderGeometry args={[radius * 1.015, radius * 1.015, 0.18, 32]} />
        </mesh>
      ))}
      <mesh position={[0, radius + 1.2, radius * 0.86]} material={GLASS}>
        <boxGeometry args={[length * 0.55, 0.35, 0.05]} />
      </mesh>
      {[-length / 3, length / 3].map((x) => (
        <group key={x}>
          {[-1, 1].map((z) => (
            <mesh key={z} position={[x, 0.35, z * radius * 0.7]} material={GREY}>
              <boxGeometry args={[0.3, 0.7, 0.3]} />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
}

function Hub() {
  return (
    <group>
      <mesh position={[0, 1.9, 0]} material={WHITE} castShadow receiveShadow>
        <cylinderGeometry args={[3.2, 3.2, 3.8, 40]} />
      </mesh>
      <mesh position={[0, 3.8, 0]} material={WHITE} castShadow>
        <sphereGeometry args={[3.2, 40, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
      </mesh>
      <mesh position={[0, 0.6, 0]} material={ORANGE}>
        <cylinderGeometry args={[3.26, 3.26, 0.4, 40]} />
      </mesh>
      {/* Hatch facing the site. */}
      <mesh position={[-3.2, 1.4, 0]} rotation={[0, Math.PI / 2, 0]} material={DARK}>
        <boxGeometry args={[1.3, 2.0, 0.2]} />
      </mesh>
    </group>
  );
}

function Tunnel({ length }: { length: number }) {
  return (
    <mesh position={[0, 1.6, 0]} rotation={[0, 0, Math.PI / 2]} material={PANEL_WHITE} castShadow>
      <cylinderGeometry args={[0.95, 0.95, length, 20]} />
    </mesh>
  );
}

function Tank() {
  return (
    <group>
      <mesh position={[0, 2.4, 0]} material={WHITE} castShadow>
        <cylinderGeometry args={[1.5, 1.5, 4.2, 28]} />
      </mesh>
      <mesh position={[0, 4.5, 0]} material={ORANGE} castShadow>
        <sphereGeometry args={[1.5, 28, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
      </mesh>
      <mesh position={[0, 0.2, 0]} material={GREY}>
        <cylinderGeometry args={[1.6, 1.7, 0.4, 28]} />
      </mesh>
    </group>
  );
}

function Container({ color = PANEL_WHITE }: { color?: THREE.Material }) {
  return (
    <mesh position={[0, 1.1, 0]} material={color} castShadow receiveShadow>
      <boxGeometry args={[5, 2.2, 2.3]} />
    </mesh>
  );
}

function SolarField() {
  const panels: ReactElement[] = [];
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 4; c++) {
      panels.push(
        <group key={`${r}-${c}`} position={[c * 4.2, 0, r * 3.6]}>
          <mesh position={[0, 0.7, 0]} material={GREY}>
            <boxGeometry args={[0.12, 1.4, 0.12]} />
          </mesh>
          <mesh position={[0, 1.45, 0]} rotation={[-0.45, 0, 0]} material={SOLAR} castShadow>
            <boxGeometry args={[3.8, 0.06, 2.4]} />
          </mesh>
        </group>,
      );
    }
  }
  return <group>{panels}</group>;
}

function Mast() {
  return (
    <group>
      <mesh position={[0, 5, 0]} material={GREY}>
        <cylinderGeometry args={[0.12, 0.2, 10, 10]} />
      </mesh>
      <mesh position={[0.6, 9.2, 0]} rotation={[0, 0, -0.9]} material={WHITE}>
        <sphereGeometry args={[1.1, 24, 8, 0, Math.PI * 2, 0, Math.PI / 3]} />
      </mesh>
      <mesh position={[0, 10.1, 0]} material={ORANGE}>
        <sphereGeometry args={[0.18, 10, 8]} />
      </mesh>
    </group>
  );
}

const PARTS: Part[] = [
  { e: 0, n: 0, node: <Hub /> },
  { e: 11.5, n: 0, node: <Habitat length={14} /> },
  { e: -2, n: -11.5, yaw: Math.PI / 2, node: <Habitat length={12} /> },
  { e: 4.4, n: 0, node: <Tunnel length={3.2} /> },
  { e: 0, n: -4.4, yaw: Math.PI / 2, node: <Tunnel length={3.2} /> },
  { e: -5, n: 6, node: <Tank /> },
  { e: -1, n: 7.5, node: <Tank /> },
  { e: 20, n: 7, yaw: 0.2, node: <Container /> },
  { e: 21, n: 10.5, yaw: 0.2, node: <Container color={ORANGE} /> },
  { e: 8, n: -9, yaw: -0.3, node: <Container color={GREY} /> },
  { e: 26, n: -18, node: <SolarField /> },
  { e: -10, n: -4, node: <Mast /> },
];

export function BaseModel({ site, verticalExaggeration, groundHeight }: Props) {
  const placed = useMemo(
    () =>
      PARTS.map((p, i) => {
        const x = site.x + CLUSTER_OFFSET.x + p.e;
        const y = site.y + CLUSTER_OFFSET.y + p.n;
        const h = groundHeight(x, y) ?? site.z;
        // Three.js: x east, y up, z = -north. Parts sit on the drawn (exaggerated) surface but are not stretched.
        return { key: i, pos: [x, h * verticalExaggeration, -y] as [number, number, number], yaw: p.yaw ?? 0, node: p.node };
      }),
    [site, verticalExaggeration, groundHeight],
  );
  return (
    <group name="base-habitat">
      {placed.map((p) => (
        <group key={p.key} position={p.pos} rotation={[0, p.yaw, 0]}>
          {p.node}
        </group>
      ))}
    </group>
  );
}
