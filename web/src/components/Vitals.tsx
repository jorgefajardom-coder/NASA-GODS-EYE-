import type { RouteDecision } from '../types/icd';
import type { Stat } from '../lib/management';
import { fmtDuration, isTrustedRoute, NOT_ESTIMATED, ROUTE_STATUS_STYLE, routeEta } from '../lib/format';
import { GlyphIcon } from './icons';
import type { Glyph } from '../lib/management';

interface Props {
  who: string;
  glyph: Glyph | null;
  stats: Stat[];
  route: RouteDecision | null;
  replanning: boolean;
}

/** Ring colours in the order of `agentStats`: oxygen, energy, time. */
const RING = ['#65CBE8', '#E8B04A', '#E8F4FF'];
const SIZE = 132;
const C = SIZE / 2;
const RADII = [58, 47, 36];
const STROKE = 7;

/** One gauge ring: a full faint track and an arc for the remaining fraction (clockwise from the top). */
function Ring({ r, fraction, color, applicable }: { r: number; fraction: number | null; color: string; applicable: boolean }) {
  const len = 2 * Math.PI * r;
  return (
    <g transform={`rotate(-90 ${C} ${C})`}>
      <circle cx={C} cy={C} r={r} stroke="rgba(255,255,255,0.12)" strokeWidth={STROKE} fill="none" strokeDasharray={applicable ? undefined : '2 5'} />
      {fraction != null && (
        <circle
          cx={C}
          cy={C}
          r={r}
          stroke={color}
          strokeWidth={STROKE}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={`${Math.max(0, Math.min(1, fraction)) * len} ${len}`}
          style={{ filter: `drop-shadow(0 0 4px ${color})`, transition: 'stroke-dasharray 0.3s linear' }}
        />
      )}
    </g>
  );
}

/**
 * Circular HUD of the selected agent (bottom left): its icon in the centre, oxygen, energy and
 * time as concentric rings, each value written once next to the ring, plus the route in force.
 * This is the only place in the interface where these three quantities are shown.
 */
export function Vitals({ who, glyph, stats, route, replanning }: Props) {
  const trusted = isTrustedRoute(route);
  const style = route ? ROUTE_STATUS_STYLE[route.status] : null;
  return (
    <section className="vitals" aria-label="Selected agent telemetry and route status">
      <div className="hud">
        <svg className="hud__dial" viewBox={`0 0 ${SIZE} ${SIZE}`} width={104} height={104} aria-hidden>
          <circle cx={C} cy={C} r={29} fill="rgba(6,14,22,0.85)" stroke="rgba(101,203,232,0.45)" />
          {stats.slice(0, 3).map((s, i) => (
            <Ring key={s.label} r={RADII[i]} fraction={s.applicable ? s.fraction : null} color={RING[i]} applicable={s.applicable} />
          ))}
        </svg>
        <div className="hud__icon">{glyph && <GlyphIcon glyph={glyph} size={32} />}</div>
        <div className="hud__readout">
          <div className="hud__who">{who}</div>
          {stats.slice(0, 3).map((s, i) => {
            const pct = s.applicable && s.fraction != null ? `${Math.round(s.fraction * 100)} %` : '';
            return (
              <div
                key={s.label}
                className={`hud__row${s.applicable ? '' : ' hud__row--na'}`}
                role="meter"
                aria-label={`${s.label} remaining`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={s.fraction == null ? undefined : Math.round(s.fraction * 100)}
                aria-valuetext={s.value}
              >
                <span className="hud__dot" style={{ background: RING[i] }} aria-hidden />
                <span className="hud__label">{s.label}</span>
                <span className="hud__pct mono">{pct}</span>
                <span className="hud__value mono">{s.value}</span>
              </div>
            );
          })}
        </div>
      </div>

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
