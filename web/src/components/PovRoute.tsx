import { Html, Line } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import type * as THREE from 'three';
import type { Line2 } from 'three-stdlib';
import { scanUniforms } from '../scanner/shaders';
import type { Point, RouteDecision } from '../types/icd';
import { LABEL_Z } from '../lib/labels';
import { ROUTE_STATUS_STYLE } from '../lib/format';
import { densifyPath, routeProgress } from '../lib/routeProgress';

/** Spacing of the draped line (m) and its lift above the drawn ground (m). */
const DRAPE_STEP_M = 3;
const LIFT_M = 0.12;
/** Height of the waypoint beacon (m). */
const BEACON_M = 7;

interface Props {
  route: RouteDecision;
  /** Agent position (ENU, as received). */
  position: Point;
  groundHeight: (x: number, y: number) => number | null;
  verticalExaggeration: number;
}

/**
 * First-person route guide: the route in force draped on the drawn ground (the part already
 * travelled dimmed, the part ahead bright) and a beacon on the next waypoint. Drawn exactly from
 * the received route; nothing is planned here.
 */
export function PovRoute({ route, position, groundHeight, verticalExaggeration }: Props) {
  const style = ROUTE_STATUS_STYLE[route.status];
  const path = route.outbound_path;
  const progress = routeProgress(path, position);
  const drape = useMemo(() => {
    const at = (p: Point): [number, number, number] => {
      const h = groundHeight(p.x, p.y);
      return [p.x, (h ?? p.z) * verticalExaggeration + LIFT_M, -p.y];
    };
    return { at, all: densifyPath(path, DRAPE_STEP_M).map(at) };
  }, [path, groundHeight, verticalExaggeration]);
  const ahead = useMemo(() => {
    if (!progress) return [];
    return densifyPath([position, ...path.slice(progress.nextIndex)], DRAPE_STEP_M).map(drape.at);
  }, [progress?.nextIndex, position, path, drape]); // eslint-disable-line react-hooks/exhaustive-deps

  const beacon = useRef<THREE.Group>(null);
  const aheadLine = useRef<Line2>(null);
  const allLine = useRef<Line2>(null);
  useFrame(({ clock }) => {
    const b = beacon.current;
    if (b) b.position.y = Math.sin(clock.elapsedTime * 1.6) * 0.15;
    // Terrain scan: the route in force is emphasised while the scan effects last.
    const glow = scanUniforms.uScanIntensity.value;
    if (aheadLine.current) aheadLine.current.material.linewidth = 4 + 3 * glow;
    if (allLine.current) allLine.current.material.opacity = 0.35 + 0.45 * glow;
  });

  if (!progress || drape.all.length < 2) return null;
  const [wx, wy, wz] = drape.at(progress.next);
  const last = progress.nextIndex === path.length - 1;
  return (
    <group name="pov-route">
      <Line ref={allLine} points={drape.all} color={style.color} lineWidth={2} transparent opacity={0.35} dashed={style.dashed} dashSize={3} gapSize={3} />
      {ahead.length > 1 && <Line ref={aheadLine} points={ahead} color={style.color} lineWidth={4} dashed={style.dashed} dashSize={3} gapSize={3} />}
      <group position={[wx, wy, wz]}>
        <group ref={beacon}>
          <mesh position={[0, BEACON_M / 2, 0]}>
            <cylinderGeometry args={[0.06, 0.06, BEACON_M, 8]} />
            <meshBasicMaterial color={style.color} transparent opacity={0.75} depthWrite={false} toneMapped={false} />
          </mesh>
          <mesh position={[0, BEACON_M + 0.5, 0]} scale={[1, 1.5, 1]}>
            <octahedronGeometry args={[0.5, 0]} />
            <meshBasicMaterial color={style.color} toneMapped={false} />
          </mesh>
        </group>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.05, 0]}>
          <ringGeometry args={[1.1, 1.4, 40]} />
          <meshBasicMaterial color={style.color} transparent opacity={0.8} depthWrite={false} toneMapped={false} />
        </mesh>
        <Html position={[0, BEACON_M + 1.6, 0]} center zIndexRange={LABEL_Z} className="pov-waypoint">
          <span>{last ? 'END' : `WP ${progress.nextIndex}`}</span>
          <b>{fmtM(progress.toNextM)}</b>
        </Html>
      </group>
    </group>
  );
}

export function fmtM(m: number): string {
  return m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${m.toFixed(0)} m`;
}
