import { useMemo, useState, type PointerEvent } from 'react';
import {
  barometricRatio,
  jezeroToGalePressure,
  latestJezeroSol,
  surfaceDose,
  uvLabel,
  type AtmosphereData,
  type GaleBin,
} from '../lib/atmos';
import { fmtSimTime } from '../lib/format';
import { Info } from './Info';
import { RawImagesPanel } from './RawImagesPanel';
import { DONKI_URL, excursionDoseMsv, zoneCrewDose, zoneEnvironment } from '../lib/zoneEnvironment';

/** Jezero (about -2.57 km) sits roughly 1.9 km above the REMS site in Gale crater (about -4.5 km). */
const JEZERO_ABOVE_GALE_M = 1900;

const fmt = (v: number | null, d = 0, unit = '') => (v == null ? '–' : `${v.toFixed(d)}${unit}`);

/** Length of the Marswalk used for the radiation estimate (h): a planning example, not a mission rule. */
const MARSWALK_H = 4;

/**
 * Water and radiation at this zone, shown for every zone scene: Mars Odyssey GRS water-equivalent hydrogen and the
 * MSL RAD surface dose (measured at Gale, elsewhere from RAD's dose-pressure relation). Context only: no shielding,
 * no solar particle events, not a dosimeter or a safety limit.
 */
export function ZoneEnvironmentPanel({ runId }: { runId: string }) {
  const env = zoneEnvironment(runId);
  if (!env) return null;
  const r = env.radiation;
  const walk = excursionDoseMsv(r.doseMsvPerDay, MARSWALK_H);
  return (
    <section className="atmos__zone" aria-label="Water and radiation at this zone">
      <div className="geo__head">
        <span>
          Water and radiation here{' '}
          <Info text="Water: Mars Odyssey GRS water-equivalent hydrogen in the top few tens of centimetres, 5 x 5 degree cell (Boynton et al. 2007; ice and hydrated minerals not distinguished). Radiation: MSL RAD surface dose at Gale (Hassler et al. 2014); other zones use RAD's measured dose-pressure relation (Guo et al. 2017) at their pressure. Surface averages without shielding; solar particle events are not included." />
        </span>
        <span className="mono">GRS · RAD</span>
      </div>
      <div className="atmos__now">
        <div>
          <span className="atmos__big mono">{env.water.wtPercent.toFixed(1)}</span>
          <span className="muted small"> ± {env.water.sigma.toFixed(1)} wt%</span>
          <div className="muted small">water-equivalent hydrogen (orbital)</div>
        </div>
        <div>
          <span className="atmos__big mono">{r.doseMsvPerDay.toFixed(2)}</span>
          <span className="muted small"> ± {r.doseSigma.toFixed(2)} mSv/day</span>
          <div className="muted small">surface dose equivalent{r.measuredHere ? ' (measured here)' : ' (estimate)'}</div>
        </div>
        <div className="atmos__when muted small">
          About <strong>{walk.toFixed(2)} mSv</strong> over a {MARSWALK_H} h Marswalk at {r.pressurePa} Pa, without suit or vehicle shielding.
          {!r.withinRange && ' Outside the 700–950 Pa range RAD measured: an unverified extrapolation.'} Solar storms are not included; check{' '}
          <a href={DONKI_URL} target="_blank" rel="noreferrer">
            NASA DONKI
          </a>{' '}
          space weather before going out.
        </div>
      </div>
    </section>
  );
}

/** Left panel of the Atmos tab: the latest Jezero sols and the radiation context of this run. */
export function AtmosList({ data, t, duration, runId }: { data: AtmosphereData | undefined; t: number; duration: number; runId: string }) {
  if (!data) {
    return (
      <section className="panel atmos" aria-label="Atmosphere">
        <ZoneEnvironmentPanel runId={runId} />
        <p className="muted small">No local weather feed is available for this zone.</p>
      </section>
    );
  }
  const last = latestJezeroSol(data);
  const sols = data.jezero_sols.filter((s) => s.min_temp_c != null || s.pressure_pa != null);
  // Run totals use this zone's surface rate, the same one the HUD and the zone block show; the Gale
  // measurement is the fallback for a run without zone context.
  const toDose = (s: number) => {
    const z = zoneCrewDose(runId, s);
    if (z) return { msv: z.usv / 1000, sigmaMsv: z.sigmaUsv / 1000 };
    return surfaceDose(data, s);
  };
  const now = toDose(t);
  const full = toDose(duration);
  const zoneRate = zoneCrewDose(runId, 0);
  const r = data.radiation;
  return (
    <section className="panel atmos" aria-label="Atmosphere and radiation">
      <ZoneEnvironmentPanel runId={runId} />
      <div className="geo__head">
        <span>
          Jezero weather{' '}
          <Info text="Latest Perseverance MEDA daily summaries published on the NASA Mars weather feed (outreach data from CAB, not the calibrated PDS archive). The replay has no Mars date, so these are recent site conditions, not the conditions of the simulated run." />
        </span>
        <span className="mono">MEDA</span>
      </div>
      {last ? (
        <div className="atmos__now">
          <div>
            <span className="atmos__big mono">{fmt(last.max_temp_c, 0, '°')}</span>
            <span className="muted small"> / {fmt(last.min_temp_c, 0, '°C')}</span>
            <div className="muted small">high / low air temperature</div>
          </div>
          <div>
            <span className="atmos__big mono">{fmt(last.pressure_pa, 0)}</span>
            <span className="muted small"> Pa</span>
            <div className="muted small">surface pressure</div>
          </div>
          <div className="atmos__when muted small">
            Sol {last.sol} · {last.earth_date} · Ls {fmt(last.ls_deg, 0, '°')} ({last.season}) · sun {last.sunrise?.slice(0, 5) ?? '–'}–{last.sunset?.slice(0, 5) ?? '–'}
          </div>
        </div>
      ) : (
        <p className="muted small">The feed has no readings in its latest sols.</p>
      )}
      <table className="atmos__table mono">
        <caption className="sr-only">Latest Jezero sols (MEDA daily summaries)</caption>
        <thead>
          <tr>
            <th scope="col">Sol</th>
            <th scope="col">Ls</th>
            <th scope="col">Low °C</th>
            <th scope="col">High °C</th>
            <th scope="col">Pa</th>
          </tr>
        </thead>
        <tbody>
          {sols.map((s) => (
            <tr key={s.sol}>
              <td>{s.sol}</td>
              <td>{fmt(s.ls_deg, 0)}</td>
              <td>{fmt(s.min_temp_c, 1)}</td>
              <td>{fmt(s.max_temp_c, 1)}</td>
              <td>{fmt(s.pressure_pa, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="geo__head atmos__rad-head">
        <span>
          Surface radiation{' '}
          <Info text={`Galactic cosmic ray averages measured by Curiosity's RAD at Gale crater (Hassler et al. 2014). ${r.caveats.join(' ')}`} />
        </span>
        <span className="mono">RAD</span>
      </div>
      <dl className="atmos__rad mono">
        <dt>Dose rate at Gale (RAD measured)</dt>
        <dd>
          {r.dose_equivalent_msv_per_day.toFixed(2)} ± {r.dose_equivalent_sigma_msv_per_day.toFixed(2)} mSv/day
        </dd>
        <dt>Absorbed at Gale</dt>
        <dd>
          {r.absorbed_mgy_per_day.toFixed(2)} ± {r.absorbed_sigma_mgy_per_day.toFixed(2)} mGy/day
        </dd>
        <dt>Run so far</dt>
        <dd>
          {(now.msv * 1000).toFixed(0)} ± {(now.sigmaMsv * 1000).toFixed(0)} µSv <span className="muted">({fmtSimTime(t)})</span>
        </dd>
        <dt>Whole run</dt>
        <dd>
          {(full.msv * 1000).toFixed(0)} ± {(full.sigmaMsv * 1000).toFixed(0)} µSv <span className="muted">({fmtSimTime(duration)})</span>
        </dd>
      </dl>
      <p className="muted small atmos__note">
        {zoneRate
          ? `Run totals use this zone's surface rate (${zoneRate.msvPerDay.toFixed(2)} mSv/day, ${zoneRate.measuredHere ? 'measured at Gale' : 'estimated from the Gale measurement'}), with no suit or habitat shielding.`
          : 'Run totals use the Gale surface rate, with no suit or habitat shielding.'}{' '}
        Not a dose map or a certified exposure limit.
      </p>
    </section>
  );
}

/** Right panel of the Atmos tab: annual cycle at Gale with the Jezero sols, and sources. */
export function AtmosDetails({ data }: { data: AtmosphereData | undefined }) {
  if (!data) return null;
  const g = data.gale_seasonal;
  const ratio = jezeroToGalePressure(data);
  const jezero = data.jezero_sols.filter((s) => s.ls_deg != null);
  return (
    <section className="panel details atmos-details" aria-label="Seasonal cycle and sources">
      <div className="tab">
        <span>Atmosphere</span>
      </div>
      <h2 className="details__title">Seasonal cycle</h2>
      <p className="details__sub">
        Median per {g.bin_deg}° of solar longitude, Curiosity REMS at Gale, {g.bins.reduce((a, b) => a + b.n, 0).toLocaleString('en-US')} sols ({g.first_sol?.date.slice(0, 4)}–{g.last_sol?.date.slice(0, 4)}), with the Jezero sols.
      </p>
      <div className="atmos__legend small" aria-hidden>
        <span>
          <i className="atmos__key atmos__key--gale" /> Gale (REMS, other site)
        </span>
        <span>
          <i className="atmos__key atmos__key--jez" /> Jezero (MEDA)
        </span>
      </div>
      <SeasonChart
        title="Air temperature, °C"
        bins={g.bins}
        band={(b) => [b.min_temp_c, b.max_temp_c]}
        points={jezero.flatMap((s) => [
          { ls: s.ls_deg!, v: s.max_temp_c },
          { ls: s.ls_deg!, v: s.min_temp_c },
        ])}
        tip={(b) => `Gale Ls ${b.ls_from}–${b.ls_to}°: low ${fmt(b.min_temp_c, 0)} °C, high ${fmt(b.max_temp_c, 0)} °C, UV ${uvLabel(b.uv_index)} (${b.n} sols)`}
      />
      <SeasonChart
        title="Surface pressure, Pa"
        bins={g.bins}
        line={(b) => b.pressure_pa}
        points={jezero.map((s) => ({ ls: s.ls_deg!, v: s.pressure_pa }))}
        tip={(b) => `Gale Ls ${b.ls_from}–${b.ls_to}°: ${fmt(b.pressure_pa, 0)} Pa (${b.n} sols)`}
      />
      {ratio && (
        <p className="small atmos__note">
          Jezero reads {(ratio.ratio * 100).toFixed(0)} % of Gale&apos;s pressure in the same season ({ratio.sols} sols); about 1.9 km higher, a barometric estimate gives {(barometricRatio(JEZERO_ABOVE_GALE_M) * 100).toFixed(0)} %.{' '}
          <Info text="Isothermal scale height of 11.1 km. Gale is at about 4.6° S and Jezero at 18.4° N, so their temperature seasons do not line up; the Gale curve is a reference for the shape of the year, not Jezero values." />
        </p>
      )}
      <RawImagesPanel />
      <h3 className="atmos__h3">Sources</h3>
      <ul className="atmos__sources small">
        {data.sources.map((s) => (
          <li key={s.id}>
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.title}
            </a>{' '}
            <span className="muted">
              {s.credit}
              {s.retrieved ? `, retrieved ${s.retrieved}` : ''}.
            </span>{' '}
            <Info text={`${s.note}${s.sha256 ? ` SHA-256 of the response: ${s.sha256}.` : ''}`} />
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ------------------------------------------------------------------ chart */

const W = 300;
const H = 120;
const PAD = { l: 34, r: 8, t: 8, b: 20 };

interface ChartProps {
  title: string;
  bins: GaleBin[];
  /** Gale low/high band (temperature). */
  band?: (b: GaleBin) => [number | null, number | null];
  /** Gale single line (pressure). */
  line?: (b: GaleBin) => number | null;
  points: Array<{ ls: number; v: number | null }>;
  tip: (b: GaleBin) => string;
}

/** One measure against solar longitude (0-360°). One y-axis per chart; never two measures on one. */
function SeasonChart({ title, bins, band, line, points, tip }: ChartProps) {
  const [hover, setHover] = useState<number | null>(null);
  const geo = useMemo(() => {
    const mid = (b: GaleBin) => (b.ls_from + b.ls_to) / 2;
    const vals: number[] = [];
    for (const b of bins) {
      if (band) for (const v of band(b)) if (v != null) vals.push(v);
      if (line) {
        const v = line(b);
        if (v != null) vals.push(v);
      }
    }
    for (const p of points) if (p.v != null) vals.push(p.v);
    if (!vals.length) vals.push(0); // no readings: draw an empty, finite axis
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    const step = niceStep((hi - lo) / 3);
    const y0 = Math.floor(lo / step) * step;
    const y1 = Math.ceil(hi / step) * step;
    const x = (ls: number) => PAD.l + (ls / 360) * (W - PAD.l - PAD.r);
    const y = (v: number) => PAD.t + (1 - (v - y0) / (y1 - y0 || 1)) * (H - PAD.t - PAD.b);
    const path = (f: (b: GaleBin) => number | null) =>
      bins
        .map((b) => [mid(b), f(b)] as const)
        .filter(([, v]) => v != null)
        .map(([ls, v], i) => `${i ? 'L' : 'M'}${x(ls).toFixed(1)},${y(v!).toFixed(1)}`)
        .join('');
    let area = '';
    if (band) {
      const top = bins.filter((b) => band(b)[1] != null).map((b) => `${x(mid(b)).toFixed(1)},${y(band(b)[1]!).toFixed(1)}`);
      const bot = bins.filter((b) => band(b)[0] != null).reverse().map((b) => `${x(mid(b)).toFixed(1)},${y(band(b)[0]!).toFixed(1)}`);
      area = `M${top.join('L')}L${bot.join('L')}Z`;
    }
    const ticks: number[] = [];
    for (let v = y0; v <= y1 + 1e-9; v += step) ticks.push(v);
    return { x, y, mid, area, ticks, lines: band ? [path((b) => band(b)[1]), path((b) => band(b)[0])] : [path(line!)] };
  }, [bins, band, line, points]);

  const onMove = (e: PointerEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const ls = (((e.clientX - box.left) / box.width) * W - PAD.l) / (W - PAD.l - PAD.r) * 360;
    if (ls < 0 || ls > 360) return setHover(null);
    setHover(Math.min(bins.length - 1, Math.max(0, Math.floor(ls / (360 / bins.length)))));
  };
  const hb = hover == null ? null : bins[hover];

  return (
    <figure className="atmos__chart">
      <figcaption className="small">{title}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title} by solar longitude`} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        {geo.ticks.map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={geo.y(v)} y2={geo.y(v)} className="atmos__grid" />
            <text x={PAD.l - 5} y={geo.y(v) + 3} textAnchor="end" className="atmos__tick">
              {Math.round(v)}
            </text>
          </g>
        ))}
        {[0, 90, 180, 270, 360].map((ls) => (
          <text key={ls} x={geo.x(ls)} y={H - 6} textAnchor="middle" className="atmos__tick">
            {ls === 0 ? 'Ls 0°' : `${ls}°`}
          </text>
        ))}
        {geo.area && <path d={geo.area} className="atmos__band" />}
        {geo.lines.map((d, i) => (
          <path key={i} d={d} className="atmos__line" />
        ))}
        {hb && (
          <line x1={geo.x(geo.mid(hb))} x2={geo.x(geo.mid(hb))} y1={PAD.t} y2={H - PAD.b} className="atmos__cross" />
        )}
        {points
          .filter((p) => p.v != null)
          .map((p, i) => (
            <circle key={i} cx={geo.x(p.ls)} cy={geo.y(p.v!)} r={4} className="atmos__pt" />
          ))}
      </svg>
      <div className="atmos__tip small mono" aria-live="polite">
        {hb ? tip(hb) : 'Hover the chart for the Gale median of a season.'}
      </div>
    </figure>
  );
}

function niceStep(raw: number): number {
  const p = 10 ** Math.floor(Math.log10(Math.max(raw, 1e-9)));
  const m = raw / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
}
