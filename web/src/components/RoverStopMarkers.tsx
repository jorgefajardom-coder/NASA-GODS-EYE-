import { Html } from '@react-three/drei';
import { useMemo } from 'react';
import type { AgentState } from '../types/icd';
import type { RoverStop } from '../types/replay';
import { enuToThree } from '../lib/coords';
import { LABEL_Z } from '../lib/labels';
import { STOP_ARRIVE_M, STOP_NEAR_M, stopLabel, stopsNear } from '../lib/roverStops';
import { siteKind } from '../lib/siteKinds';
import { ScaleWithDistance } from './ScaleWithDistance';
import { SiteIcon } from './SiteIcon';

const COLOR = siteKind('photo').color;
/** Icons with a label are drawn for this many stops around the selected agent; every stop keeps its ground ring. */
const LABELLED = 4;

/**
 * Real Perseverance stops (NASA waypoints) drawn on the terrain: a ground ring for each one and, for
 * the nearest few to the selected agent, the camera icon with its sol. The ring under the agent
 * brightens when it stands on a stop (its mission images open then). Display only.
 */
export function RoverStopMarkers({ stops, agent, verticalExaggeration }: { stops: RoverStop[]; agent: AgentState | null; verticalExaggeration: number }) {
  const positions = useMemo(() => stops.map((s) => enuToThree({ x: s.x_m, y: s.y_m, z: s.z_m }, verticalExaggeration)), [stops, verticalExaggeration]);
  const ax = agent?.pose.position.x ?? 0;
  const ay = agent?.pose.position.y ?? 0;
  const near = agent ? stopsNear(stops, ax, ay, STOP_NEAR_M).slice(0, LABELLED) : [];
  const nearIds = new Set(near.map((n) => n.stop.rmc));
  const under = agent ? near.find((n) => n.distM <= STOP_ARRIVE_M)?.stop.rmc : undefined;
  return (
    <group name="rover-stops">
      {stops.map((s, i) => {
        const [x, y, z] = positions[i];
        const on = s.rmc === under;
        return (
          <group key={s.rmc} position={[x, y, z]}>
            <ScaleWithDistance perMetre={1 / 140} max={8}>
              <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.25, 0]}>
                <ringGeometry args={[on ? 2.4 : 1.6, on ? 3.4 : 2.1, 24]} />
                <meshBasicMaterial color={COLOR} transparent opacity={on ? 0.95 : 0.55} />
              </mesh>
              {nearIds.has(s.rmc) && (
                <Html position={[0, 5, 0]} center zIndexRange={LABEL_Z} className="site-label site-label--photo">
                  <SiteIcon kind="photo" size={14} /> {stopLabel(s)}
                </Html>
              )}
            </ScaleWithDistance>
          </group>
        );
      })}
    </group>
  );
}
