import { useMemo } from 'react';
import { rasterizeUnits, unitColor, unitShares, type GeologyData } from '../lib/geology';

/** Grid used to measure unit shares in the list (5 m cells over the 2 km crop). */
export const SHARE_GRID = 400;

/** Left panel of the Ground layers tab: the mapped units of the run area and their extent. */
export function GeologyList({ data, selected, onSelect }: { data: GeologyData | undefined; selected: string | null; onSelect: (id: string | null) => void }) {
  const shares = useMemo(() => (data ? unitShares(data, rasterizeUnits(data, SHARE_GRID)) : null), [data]);
  if (!data || !shares) {
    return (
      <section className="panel geo" aria-label="Ground layers">
        <p className="muted small">No geologic map is available for this run.</p>
      </section>
    );
  }
  const order = data.units.map((u, i) => ({ u, share: shares.shares[i] })).sort((a, b) => b.share - a.share);
  return (
    <section className="panel geo" aria-label="Ground layers">
      <div className="geo__head">
        <span>Geologic units in this area</span>
        <span className="mono">{data.units.length}</span>
      </div>
      <ul className="geo__list">
        {order.map(({ u, share }) => (
          <li key={u.id}>
            <button type="button" className={`geo__unit${selected === u.id ? ' is-selected' : ''}`} aria-pressed={selected === u.id} onClick={() => onSelect(selected === u.id ? null : u.id)}>
              <span className="geo__swatch" style={{ background: unitColor(data, u.id) }} aria-hidden />
              <span className="geo__name">{u.name}</span>
              <span className="geo__sym mono">{u.symbol}</span>
              <span className="geo__share mono">{(share * 100).toFixed(0)} %</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="note">Share of the 2 km area. Boundaries are approximate (about 100–200 m registration offset).</p>
    </section>
  );
}

/** Right panel of the Ground layers tab: what the selected unit is made of and how it formed. */
export function GeologyDetails({ data, unitId }: { data: GeologyData | undefined; unitId: string | null }) {
  if (!data) return null;
  const u = data.units.find((x) => x.id === unitId) ?? null;
  return (
    <section className="panel details geo-details" aria-label="Geologic unit details">
      <div className="tab">
        <span>Ground layer</span>
      </div>
      {u ? (
        <>
          <h2 className="details__title">
            <span className="geo__swatch" style={{ background: unitColor(data, u.id) }} aria-hidden /> {u.name}
          </h2>
          <p className="details__sub mono">Map symbol {u.symbol}</p>
          <div className="geo-details__body">
            <h3>Description</h3>
            <p>{u.description}</p>
            {u.characteristics && (
              <>
                <h3>Composition and associations</h3>
                <p>{u.characteristics}</p>
              </>
            )}
            {u.interpretation && (
              <>
                <h3>Interpretation</h3>
                <p>{u.interpretation}</p>
              </>
            )}
          </div>
        </>
      ) : (
        <p className="muted small">Select a unit to see its description, composition and interpretation.</p>
      )}
      <p className="note">
        Source:{' '}
        <a href={data.source.doi} target="_blank" rel="noreferrer">
          {data.source.authors} ({data.source.year}), {data.source.title}, {data.source.scale}
        </a>
        . {data.source.registration_note} Composition notes are orbital spectral associations reported by the map, not measurements at this site.
      </p>
    </section>
  );
}
