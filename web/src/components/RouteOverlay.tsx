import { Html, Line } from '@react-three/drei';
import type { Point, RouteDecision } from '../types/icd';
import { enuToThree } from '../lib/coords';
import { ROUTE_STATUS_STYLE } from '../lib/format';

/** Lift above the surface so lines are not hidden inside the mesh (visual only). */
const LIFT_M = 0.8;
const INVALIDATED_COLOR = '#D95045';

function toThree(points: Point[], exaggeration: number): [number, number, number][] {
  return points.map((p) => {
    const [x, y, z] = enuToThree(p, exaggeration);
    return [x, y + LIFT_M, z];
  });
}

interface Props {
  active: RouteDecision | null;
  previous: RouteDecision[];
  verticalExaggeration: number;
}

/**
 * Draws routes exactly as received; nothing is computed here (no path search in JS).
 * Previous (invalidated) routes stay visible, dashed, so before/after can be compared.
 */
export function RouteOverlay({ active, previous, verticalExaggeration }: Props) {
  return (
    <group name="routes">
      {previous.map((r) => (
        <group key={r.route_id}>
          <Line
            points={toThree(r.outbound_path, verticalExaggeration)}
            color={INVALIDATED_COLOR}
            lineWidth={3}
            dashed
            dashSize={6}
            gapSize={5}
            transparent
            opacity={0.9}
          />
          <RouteLabel point={r.outbound_path[Math.floor(r.outbound_path.length / 2)]} exaggeration={verticalExaggeration} tone="invalid">
            {r.route_id} · invalidated (map v{r.map_version_used})
          </RouteLabel>
        </group>
      ))}
      {active && active.outbound_path.length > 1 && <ActiveRoute route={active} exaggeration={verticalExaggeration} />}
    </group>
  );
}

function ActiveRoute({ route, exaggeration }: { route: RouteDecision; exaggeration: number }) {
  const style = ROUTE_STATUS_STYLE[route.status];
  return (
    <group>
      <Line
        points={toThree(route.outbound_path, exaggeration)}
        color={style.color}
        lineWidth={style.dashed ? 3 : 5}
        dashed={style.dashed}
        dashSize={4}
        gapSize={4}
      />
      {route.return_path.length > 1 && (
        <Line points={toThree(route.return_path, exaggeration)} color={style.color} lineWidth={2} dashed dashSize={2} gapSize={3} transparent opacity={0.7} />
      )}
      <RouteLabel point={route.outbound_path[Math.floor(route.outbound_path.length / 2)]} exaggeration={exaggeration} tone={style.dashed ? 'warn' : 'ok'}>
        {route.route_id} · {style.label.toLowerCase()} (map v{route.map_version_used})
      </RouteLabel>
    </group>
  );
}

function RouteLabel({
  point,
  exaggeration,
  tone,
  children,
}: {
  point: Point | undefined;
  exaggeration: number;
  tone: 'ok' | 'warn' | 'invalid';
  children: React.ReactNode;
}) {
  if (!point) return null;
  const [x, y, z] = enuToThree(point, exaggeration);
  return (
    <Html position={[x, y + 10, z]} center zIndexRange={[20, 0]} className={`route-label route-label--${tone}`}>
      {children}
    </Html>
  );
}
