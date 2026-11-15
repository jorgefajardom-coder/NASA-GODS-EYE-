import { LABEL_Z } from '../lib/labels';
import { Html } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef, type ReactNode } from 'react';
import * as THREE from 'three';
import type { ControlPoint, PointOfInterest } from '../types/replay';
import type { TaskView } from '../lib/replay';
import { enuToThree } from '../lib/coords';
import { ScaleWithDistance } from './ScaleWithDistance';
import { SiteIcon } from './SiteIcon';
import { siteColor } from '../lib/siteKinds';

interface Props {
  pois: PointOfInterest[];
  controlPoints: ControlPoint[];
  showControlPoints: boolean;
  tasks: TaskView[];
  t: number;
  verticalExaggeration: number;
}

/** Base, goal and POIs. A POI only appears once an observation event revealed it. */
export function SiteMarkers({ pois, controlPoints, showControlPoints, tasks, t, verticalExaggeration }: Props) {
  return (
    <group name="sites">
      {pois
        .filter((p) => p.revealed_at_s <= t)
        .map((p) => {
          const [x, y, z] = enuToThree(p.position, verticalExaggeration);
          const task = tasks.find((k) => k.task_id.endsWith(`:${p.id}`));
          const state = task?.state;
          const color = siteColor(p.kind, state);
          return (
            <group key={p.id} position={[x, y, z]}>
              <ScaleWithDistance perMetre={1 / 110} max={10}>
              <HideWhenClose>
                <mesh position={[0, 4, 0]}>
                  <cylinderGeometry args={[0.25, 0.25, 8, 8]} />
                  <meshStandardMaterial color="#e5e7eb" />
                </mesh>
                <mesh position={[0, 8.5, 0]}>
                  <sphereGeometry args={[1.3, 16, 12]} />
                  <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} />
                </mesh>
              </HideWhenClose>
              <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.3, 0]}>
                <ringGeometry args={[3.2, 4, 32]} />
                <meshBasicMaterial color={color} transparent opacity={0.8} />
              </mesh>
              <Html position={[0, 13, 0]} center zIndexRange={LABEL_Z} className={`site-label site-label--${p.kind}`}>
                <SiteIcon kind={p.kind} size={14} color={color} /> {p.label}
                {state ? <em> · {state.toLowerCase()}</em> : null}
              </Html>
              </ScaleWithDistance>
            </group>
          );
        })}
      {showControlPoints &&
        controlPoints.map((cp) => {
          const [x, y, z] = enuToThree(cp.position, verticalExaggeration);
          return (
            <group key={cp.id} position={[x, y, z]}>
              <mesh>
                <sphereGeometry args={[0.9, 12, 8]} />
                <meshBasicMaterial color="#00e5ff" />
              </mesh>
              <Html position={[0, 4, 0]} center zIndexRange={LABEL_Z} className="site-label site-label--cp">
                {cp.id}
              </Html>
            </group>
          );
        })}
    </group>
  );
}

/** Below this camera distance the pin mast is hidden; the ground ring and label stay (m). */
export const PIN_HIDE_DISTANCE_M = 70;

/**
 * Hides a marker's mast when the camera is close. Agents often stand on a site (the
 * astronaut starts on the base), and at close range the 8 m pole would cut through them.
 */
function HideWhenClose({ children }: { children: ReactNode }) {
  const group = useRef<THREE.Group>(null);
  const world = useRef(new THREE.Vector3());
  useFrame(({ camera }) => {
    const g = group.current;
    if (!g) return;
    g.getWorldPosition(world.current);
    g.visible = camera.position.distanceTo(world.current) > PIN_HIDE_DISTANCE_M;
  });
  return <group ref={group}>{children}</group>;
}
