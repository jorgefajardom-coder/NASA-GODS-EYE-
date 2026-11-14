import type { ReactNode } from 'react';

/** The six options around the dial, clockwise from the top. Each turns the inner circle into its own gauge. */
export type HudOption = 'oxygen' | 'energy' | 'time' | 'route' | 'atmos' | 'dose';

export const HUD_OPTIONS: Array<{ id: HudOption; label: string }> = [
  { id: 'oxygen', label: 'Oxygen' },
  { id: 'energy', label: 'Energy' },
  { id: 'time', label: 'Time' },
  { id: 'route', label: 'Route' },
  { id: 'atmos', label: 'Atmosphere' },
  { id: 'dose', label: 'Radiation dose' },
];

/** Diameter of the inner circle: the minimap, or the gauge of the selected option (px). */
export const HUD_MAP_PX = 168;
const SIZE = 300;
const C = SIZE / 2;
const INNER_R = HUD_MAP_PX / 2;
/** Ring that carries the option buttons, and the button radius. */
const ORBIT_R = 118;
const BTN_R = 25;

/** Line icons drawn on a 24 x 24 grid (stroke only), one per option. */
export const HUD_ICON: Record<HudOption, ReactNode> = {
  // O2 molecule: two linked atoms.
  oxygen: (
    <>
      <circle cx="8" cy="11" r="4.5" />
      <circle cx="16" cy="11" r="4.5" />
      <text x="12" y="22.5" fontSize="5.5" textAnchor="middle" stroke="none" fill="currentColor">O₂</text>
    </>
  ),
  // Lightning bolt.
  energy: <path d="M13 2 5 13h6l-1 9 8-12h-6z" />,
  // Clock.
  time: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </>
  ),
  // Route between two points.
  route: (
    <>
      <circle cx="5" cy="18" r="2.2" />
      <path d="M7 17c4-1 2-6 6-7s5-3 5-5" />
      <path d="M16 3h4v4" />
    </>
  ),
  // Cloud with a ground line.
  atmos: (
    <>
      <path d="M7 15h10a4 4 0 0 0 0-8 5.5 5.5 0 0 0-10.4 1.6A3.3 3.3 0 0 0 7 15z" />
      <path d="M8 19h2M12 19h2M16 19h2" />
    </>
  ),
  // Radiation trefoil.
  dose: (
    <>
      <circle cx="12" cy="12" r="1.8" />
      {[0, 120, 240].map((r) => (
        <path key={r} d="M12 9.6 8.4 3.4a7.5 7.5 0 0 1 7.2 0z" transform={`rotate(${r} 12 12)`} />
      ))}
    </>
  ),
};

interface Props {
  /** Agent the HUD shows, for assistive technology only (no text is drawn over the dial). */
  who: string;
  /** Content of the inner circle: the minimap when no option is active, else that option's gauge. */
  center: ReactNode;
  active: HudOption | null;
  onSelect: (o: HudOption | null) => void;
  /** Options to mark with a warning ring (little left after the route, route not verified...). */
  warn: ReadonlySet<HudOption>;
  /** Short value per option for the button tooltip. */
  hints: Partial<Record<HudOption, string>>;
}

/**
 * Agent HUD: an inner circle and six option buttons on an outer ring. With no option active the
 * circle is the heading-up minimap; pressing an option turns the circle into that element's own
 * gauge (and its icon glows); pressing it again goes back to the map.
 */
export function RadialHud({ who, center, active, onSelect, warn, hints }: Props) {
  return (
    <section className="rhud" aria-label={`Agent HUD: ${who}`}>
      <div className="rhud__dial" style={{ width: SIZE, height: SIZE }}>
        <svg className="rhud__frame" viewBox={`0 0 ${SIZE} ${SIZE}`} width={SIZE} height={SIZE} aria-hidden>
          <circle cx={C} cy={C} r={ORBIT_R + 18} className="rhud__halo" />
          <circle cx={C} cy={C} r={ORBIT_R} className="rhud__orbit" />
          {HUD_OPTIONS.map((_, i) => {
            const a = ((i * 60 + 30 - 90) * Math.PI) / 180;
            return (
              <line
                key={i}
                x1={C + Math.cos(a) * (ORBIT_R - 6)}
                y1={C + Math.sin(a) * (ORBIT_R - 6)}
                x2={C + Math.cos(a) * (ORBIT_R + 6)}
                y2={C + Math.sin(a) * (ORBIT_R + 6)}
                className="rhud__tick"
              />
            );
          })}
          {HUD_OPTIONS.map((o, i) => {
            const a = ((i * 60 - 90) * Math.PI) / 180;
            return (
              <line
                key={o.id}
                x1={C + Math.cos(a) * (INNER_R + 2)}
                y1={C + Math.sin(a) * (INNER_R + 2)}
                x2={C + Math.cos(a) * (ORBIT_R - BTN_R)}
                y2={C + Math.sin(a) * (ORBIT_R - BTN_R)}
                className={`rhud__spoke${active === o.id ? ' rhud__spoke--on' : ''}`}
              />
            );
          })}
        </svg>
        <div className="rhud__map" style={{ width: HUD_MAP_PX, height: HUD_MAP_PX }}>
          {center}
        </div>
        {HUD_OPTIONS.map((o, i) => {
          const a = ((i * 60 - 90) * Math.PI) / 180;
          const on = active === o.id;
          return (
            <button
              key={o.id}
              type="button"
              className={`rhud__btn${on ? ' rhud__btn--on' : ''}${warn.has(o.id) ? ' rhud__btn--warn' : ''}`}
              style={{ left: C + Math.cos(a) * ORBIT_R - BTN_R, top: C + Math.sin(a) * ORBIT_R - BTN_R, width: BTN_R * 2, height: BTN_R * 2 }}
              aria-pressed={on}
              aria-label={o.label}
              title={hints[o.id] ? `${o.label}: ${hints[o.id]}` : o.label}
              onClick={() => onSelect(on ? null : o.id)}
            >
              <svg viewBox="0 0 24 24" width={24} height={24} fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                {HUD_ICON[o.id]}
              </svg>
            </button>
          );
        })}
      </div>
    </section>
  );
}
