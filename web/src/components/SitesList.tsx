import type { PointOfInterest } from '../types/replay';
import type { Point } from '../types/icd';
import { siteKind } from '../lib/siteKinds';
import { SiteIcon } from './SiteIcon';

/** Short tag of where a site comes from; the full text is in the row's tooltip. */
const SOURCE_TAG = { nasa: 'NASA', chosen: 'chosen on NASA terrain', fictitious: 'fictitious' } as const;

const fmtDist = (m: number) => (m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${m.toFixed(0)} m`);

/**
 * Sites of the world with the same icons as the 3D markers, the compass and the minimap. Only sites
 * already revealed at replay time t are listed (a POI is not shown before an event reveals it).
 * Distances are straight lines from the selected agent. Display only.
 */
export function SitesList({ pois, t, from }: { pois: PointOfInterest[]; t: number; from: Point | null }) {
  const known = pois.filter((p) => p.revealed_at_s <= t);
  if (known.length === 0) return null;
  return (
    <section className="sites" aria-label="Sites of interest">
      <h3 className="sites__title">Sites</h3>
      <ul className="sites__list">
        {known.map((p) => (
          <li key={p.id} className="sites__row" title={`${siteKind(p.kind).title}${p.source ? ` · ${p.source.text}` : ''}${from ? ' · straight-line distance from the selected agent' : ''}`}>
            <SiteIcon kind={p.kind} size={18} />
            <span>
              {p.label}
              {p.source && <small className={`sites__src sites__src--${p.source.basis}`}>{SOURCE_TAG[p.source.basis]}</small>}
            </span>
            <em>{from ? fmtDist(Math.hypot(p.position.x - from.x, p.position.y - from.y)) : siteKind(p.kind).short}</em>
          </li>
        ))}
      </ul>
    </section>
  );
}
