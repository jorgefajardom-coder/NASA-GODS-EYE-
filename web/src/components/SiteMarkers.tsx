import { Html } from '@react-three/drei';
import type { ControlPoint, PointOfInterest } from '../types/replay';
import type { TaskView } from '../lib/replay';
import { enuToThree } from '../lib/coords';
import { ScaleWithDistance } from './ScaleWithDistance';

interface Props {
  pois: PointOfInterest[];
  controlPoints: ControlPoint[];
  showControlPoints: boolean;
  tasks: TaskView[];
  t: number;
  verticalExaggeration: number;
}

const KIND_COLOR = { base: '#65CBE8', primary_goal: '#E8F4FF', poi: '#C9D7DD' } as const;

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
          const color = state === 'REJECTED' ? '#D95045' : state === 'DONE' ? '#65CBE8' : KIND_COLOR[p.kind];
          return (
            <group key={p.id} position={[x, y, z]}>
              <ScaleWithDistance perMetre={1 / 110} max={10}>
              <mesh position={[0, 4, 0]}>
                <cylinderGeometry args={[0.25, 0.25, 8, 8]} />
                <meshStandardMaterial color="#e5e7eb" />
              </mesh>
              <mesh position={[0, 8.5, 0]}>
                <sphereGeometry args={[1.3, 16, 12]} />
                <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} />
              </mesh>
              <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.3, 0]}>
                <ringGeometry args={[3.2, 4, 32]} />
                <meshBasicMaterial color={color} transparent opacity={0.8} />
              </mesh>
              <Html position={[0, 13, 0]} center zIndexRange={[25, 0]} className={`site-label site-label--${p.kind}`}>
                {p.label}
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
              <Html position={[0, 4, 0]} center className="site-label site-label--cp">
                {cp.id}
              </Html>
            </group>
          );
        })}
    </group>
  );
}
