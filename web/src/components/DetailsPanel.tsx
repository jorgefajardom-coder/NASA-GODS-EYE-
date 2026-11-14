import type { DetailData, Stat } from '../lib/management';
import type { Portrait } from '../lib/portraits';

/** Contextual details of the selected agent, task or route. */
export function DetailsPanel({ data, portrait }: { data: DetailData; portrait?: Portrait | null }) {
  return (
    <section className="panel details" aria-label={`Details of ${data.title}`}>
      <div className="tab">
        <span>Details</span>
      </div>

      <div className="details__head">
        {portrait && (
          // The image carries its own burned-in "AI-generated" watermark (AGENTS.md section 11).
          <img className="details__portrait" src={portrait.url} alt={portrait.alt} title="AI-generated illustration" width={80} height={80} />
        )}
        <div>
          <h2 className="details__title">{data.title}</h2>
          <p className="details__sub mono">{data.subtitle}</p>
        </div>
      </div>

      {data.stats.length > 0 && (
        <div className="stats" title="Percentages are relative to the first received sample, not to a certified budget.">
          {data.stats.map((s) => (
            <StatBar key={s.label} stat={s} />
          ))}
        </div>
      )}

      <dl className="facts">
        {data.facts.map(([k, v]) => (
          <div key={k} className="facts__row">
            <dt>{k}</dt>
            <dd className="mono">{v}</dd>
          </div>
        ))}
      </dl>

      <p className="details__body">{data.body}</p>

    </section>
  );
}

export function StatBar({ stat }: { stat: Stat }) {
  const unknown = stat.applicable && stat.fraction == null;
  return (
    <div className={`stat${stat.applicable ? '' : ' stat--na'}`}>
      <div className="stat__head">
        <span>{stat.label}</span>
        <span className="mono">{stat.applicable ? (stat.percent ?? '---') : '---'}</span>
      </div>
      <div
        className={`bar${unknown ? ' bar--unknown' : ''}`}
        role="meter"
        aria-label={`${stat.label} remaining`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={stat.fraction == null ? undefined : Math.round(stat.fraction * 100)}
        aria-valuetext={stat.value}
      >
        {stat.fraction != null && <div className="bar__fill" style={{ width: `${stat.fraction * 100}%` }} />}
      </div>
      <div className="stat__value mono">{stat.value}</div>
    </div>
  );
}
