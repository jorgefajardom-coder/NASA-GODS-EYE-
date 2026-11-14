import type { RouteDecision } from '../types/icd';
import type { Stat } from '../lib/management';
import { fmtDuration, isTrustedRoute, NOT_ESTIMATED, ROUTE_STATUS_STYLE, routeEta } from '../lib/format';

interface Props {
  who: string;
  stats: Stat[];
  route: RouteDecision | null;
  replanning: boolean;
}

/** Telemetry of the selected agent plus the state of the route in force (HUD, bottom left). */
export function Vitals({ who, stats, route, replanning }: Props) {
  const trusted = isTrustedRoute(route);
  const style = route ? ROUTE_STATUS_STYLE[route.status] : null;
  return (
    <section className="vitals" aria-label="Selected agent telemetry and route status">
      <div className="vitals__who">{who}</div>
      {stats.map((s) => {
        const unknown = s.applicable && s.fraction == null;
        return (
          <div key={s.label} className={`vital${s.applicable ? '' : ' vital--na'}`}>
            <span className="vital__label">{s.label}</span>
            <div
              className={`vital__bar${unknown ? ' vital__bar--unknown' : ''}`}
              role="meter"
              aria-label={`${s.label} remaining`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={s.fraction == null ? undefined : Math.round(s.fraction * 100)}
              aria-valuetext={s.value}
            >
              {s.fraction != null && <div className="vital__fill" style={{ width: `${s.fraction * 100}%` }} />}
            </div>
            <span className="vital__value mono">{s.value}</span>
          </div>
        );
      })}

      <div className="vitals__route">
        <div className="vitals__routehead">
          <span>Route</span>
          <span className={`mono tone-${replanning ? 'warn' : route ? (trusted ? 'ok' : 'warn') : 'unknown'}`}>
            {replanning ? 'invalidated · replanning' : route ? `${route.route_id} · ${style!.label.toLowerCase()}` : 'none'}
          </span>
        </div>
        <div className="vitals__routehead">
          <span>Round trip</span>
          <span className="mono">{replanning || !route ? NOT_ESTIMATED : routeEta(route)}</span>
        </div>
        <div className="vitals__routehead">
          <span>Returnability</span>
          <span className="mono">
            {trusted && route!.return_path.length > 1 ? `planned, reserve ${fmtDuration(route!.reserve_time_s)}` : 'not guaranteed'}
          </span>
        </div>
      </div>
    </section>
  );
}
