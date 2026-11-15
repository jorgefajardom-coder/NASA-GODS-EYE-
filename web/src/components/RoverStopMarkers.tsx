import { Html } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import type { Mesh } from 'three';
import type { AgentState } from '../types/icd';
import type { RoverStop } from '../types/replay';
import { enuToThree } from '../lib/coords';
import { LABEL_Z } from '../lib/labels';
import { STOP_ARRIVE_M, stopLabel, stopsNear } from '../lib/roverStops';
import { siteKind } from '../lib/siteKinds';
import { ScaleWithDistance } from './ScaleWithDistance';
import { SiteIcon } from './SiteIcon';

const COLOR = siteKind('photo').color;
/** Floating tags with text are drawn for this many stops around the selected agent, within this range (m). */
const LABELLED = 6;
const LABEL_RANGE_M = 700;
/** Height of the floating diamond above the ground (m, before distance scaling). */
const FLOAT_M = 3.4;

/** A slowly turning, gently bobbing diamond: the marker of one real rover stop. */
function Diamond({ on }: { on: boolean }) {
  const ref = useRef<Mesh>(null);
  useFrame(({ clock }) => {
    const m = ref.current;
    if (!m) return;
    m.rotation.y = clock.elapsedTime * 1.2;
    m.position.y = FLOAT_M + Math.sin(clock.elapsedTime * 1.6) * 0.12;
  });
  return (
    <mesh ref={ref} position={[0, FLOAT_M, 0]} scale={on ? [0.8, 1.1, 0.8] : [1, 1.4, 1]}>
      <octahedronGeometry args={[0.3, 0]} />
      <meshBasicMaterial color={COLOR} transparent opacity={on ? 1 : 0.85} />
    </mesh>
  );
}

/**
 * Real Perseverance stops (NASA waypoints) as game-style floating markers: a turning diamond on a thin
 * pole above every stop, and for the nearest few to the selected agent a tag with the camera icon and
 * the sol. The diamond under the agent grows when it stands on a stop (its mission images open then).
 * Display only.
 */
export function RoverStopMarkers({ stops, agent, verticalExaggeration }: { stops: RoverStop[]; agent: AgentState | null; verticalExaggeration: number }) {
  const positions = useMemo(() => stops.map((s) => enuToThree({ x: s.x_m, y: s.y_m, z: s.z_m }, verticalExaggeration)), [stops, verticalExaggeration]);
  const ax = agent?.pose.position.x ?? 0;
  const ay = agent?.pose.position.y ?? 0;
  const near = agent ? stopsNear(stops, ax, ay, LABEL_RANGE_M).slice(0, LABELLED) : [];
  const tagged = new Map(near.map((n) => [n.stop.rmc, n.distM]));
  const under = near.find((n) => n.distM <= STOP_ARRIVE_M)?.stop.rmc;
  return (
    <group name="rover-stops">
      {stops.map((s, i) => {
        const [x, y, z] = positions[i];
        const on = s.rmc === under;
        const dist = tagged.get(s.rmc);
        return (
          <group key={s.rmc} position={[x, y, z]}>
            <ScaleWithDistance perMetre={1 / 110} max={10}>
              <mesh position={[0, FLOAT_M / 2, 0]}>
                <cylinderGeometry args={[0.035, 0.035, FLOAT_M, 6]} />
                <meshBasicMaterial color={COLOR} transparent opacity={0.55} />
              </mesh>
              <Diamond on={on} />
              {dist != null && (
                <Html position={[0, FLOAT_M + 1.5, 0]} center zIndexRange={LABEL_Z} className={`stop-tag${on ? ' stop-tag--on' : ''}`}>
                  <SiteIcon kind="photo" size={14} />
                  <b>{stopLabel(s)}</b>
                  <em>{dist >= 1000 ? `${(dist / 1000).toFixed(2)} km` : `${Math.round(dist)} m`}</em>
                </Html>
              )}
            </ScaleWithDistance>
          </group>
        );
      })}
    </group>
  );
}
