import { useEffect, useId, useMemo, useRef, type ReactNode } from 'react';
import type { AgentState, RouteDecision } from '../types/icd';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import type { Budget } from '../lib/management';
import { crewDose, fmtMicroSv, latestJezeroSol, type AtmosphereData } from '../lib/atmos';
import { pressureField, SCALE_HEIGHT_M } from '../lib/atmosMap';
import { fmtDuration } from '../lib/format';
import { heightGrid } from '../lib/layers';
import { resourceLines, type ResourceLine } from '../lib/resources';
import { RESPIRATORY_QUOTIENT, co2FromOxygen, type Co2Line } from '../lib/co2';
import { NASA_CAREER_LIMIT_MSV, zoneCrewDose } from '../lib/zoneEnvironment';
import { HUD_ICON, type HudOption } from './RadialHud';

const V = 168; // drawing grid (viewBox), scaled to the circle
const R = V / 2;
const CYAN = '#65CBE8';
const AMBER = '#E8B04A';
const RED = '#E8796A';
const WHITE = '#E8F4FF';
/** Radial bar: 300 degrees around the rim, open at the bottom where its icon and value sit. */
const GAP = (60 * Math.PI) / 180;
const SWEEP = 2 * Math.PI - GAP;
const START = Math.PI + GAP / 2; // angle from straight up, clockwise (bottom-left end)
const BAR_R = R - 8;
const BAR_W = 9;

const clamp01 = (x: number | null | undefined) => Math.max(0, Math.min(1, x ?? 0));
const amount = (v: number | null | undefined, unit: string, digits = 0) => (v == null || !Number.isFinite(v) ? '–' : `${v.toFixed(digits)} ${unit}`);
const toneColor = (r: ResourceLine | null, base: string) => (!r || r.tone === 'ok' || r.tone === 'unknown' ? base : r.tone === 'warn' ? AMBER : RED);

function arc(k0: number, k1: number, r: number): string {
  const p = (k: number) => {
    const a = START + SWEEP * k;
    return [R + Math.sin(a) * r, R - Math.cos(a) * r] as const;
  };
  const [x0, y0] = p(k0);
  const [x1, y1] = p(k1);
  return `M${x0} ${y0} A${r} ${r} 0 ${SWEEP * (k1 - k0) > Math.PI ? 1 : 0} 1 ${x1} ${y1}`;
}

/**
 * Radial bar (time and radiation dose): a dark circle with a track around the rim, the filled share
 * `f` in the element's colour, tick marks every 10 %, and the element's icon large in the centre
 * with its value under it.
 */
function RadialBar({ f, color, option, value, sub, title }: { f: number | null; color: string; option: HudOption; value: string; sub?: string; title: string }) {
  const k = clamp01(f);
  return (
    <svg className="hg" viewBox={`0 0 ${V} ${V}`} role="img" aria-label={`${title}: ${value}`}>
      <title>{title}</title>
      <circle cx={R} cy={R} r={R} fill="#070c11" />
      <circle cx={R} cy={R} r={R - 24} fill={color} opacity={0.06} />
      <path d={arc(0, 1, BAR_R)} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth={BAR_W} strokeLinecap="round" />
      {f != null && k > 0.002 && (
        <path d={arc(0, k, BAR_R)} fill="none" stroke={color} strokeWidth={BAR_W} strokeLinecap="round" className="hg__bar" style={{ filter: `drop-shadow(0 0 4px ${color})` }} />
      )}
      {Array.from({ length: 11 }, (_, i) => {
        const a = START + SWEEP * (i / 10);
        return (
          <line
            key={i}
            x1={R + Math.sin(a) * (BAR_R - BAR_W / 2 - 3)}
            y1={R - Math.cos(a) * (BAR_R - BAR_W / 2 - 3)}
            x2={R + Math.sin(a) * (BAR_R - BAR_W / 2 - 8)}
            y2={R - Math.cos(a) * (BAR_R - BAR_W / 2 - 8)}
            stroke="#fff"
            strokeOpacity={i % 5 === 0 ? 0.8 : 0.35}
            strokeWidth={i % 5 === 0 ? 1.6 : 1}
          />
        );
      })}
      {/* Time has no centre icon: its button on the ring already shows the clock. */}
      {option !== 'time' && (
        <g transform={`translate(${R - 26} ${R - 50}) scale(2.15)`} fill="none" stroke={color} strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round" style={{ filter: `drop-shadow(0 0 4px ${color})` }}>
          {HUD_ICON[option]}
        </g>
      )}
      <text x={R} y={option === 'time' ? R - 1 : R + 24} textAnchor="middle" className="hg__val hg__val--big">
        {value}
      </text>
      {sub && (
        <text x={R} y={option === 'time' ? R + 16 : R + 40} textAnchor="middle" className="hg__val hg__val--sub">
          {sub}
        </text>
      )}
    </svg>
  );
}

/** Centred text lines over a gauge, outlined so they read over any fill. */
function Caption({ y, lines }: { y: number; lines: Array<[string, string?]> }) {
  return (
    <>
      {lines.map(([text, cls], i) =>
        text ? (
          <text key={i} x={R} y={y + i * 15} textAnchor="middle" className={`hg__t${cls ? ` ${cls}` : ''}`}>
            {text}
          </text>
        ) : null,
      )}
    </>
  );
}

/** Oxygen: the circle is the tank; the liquid fills it up to the share left. */
function OxygenGauge({ r, budget }: { r: ResourceLine; budget: number | null }) {
  const f = budget ? clamp01((r.remaining ?? 0) / budget) : 0;
  const color = toneColor(r, CYAN);
  const level = V * (1 - f);
  return (
    <>
      <rect x={0} y={0} width={V} height={V} fill="#06131b" />
      <rect x={0} y={level} width={V} height={V - level} fill={color} opacity={0.55} className="hg__fill" />
      <path d={`M0 ${level} q21 -6 42 0 t42 0 t42 0 t42 0 V${V} H0 Z`} fill={color} opacity={0.35} className="hg__wave" />
      {[30, 62, 104, 132].map((x, i) => (
        <circle key={x} cx={x} cy={V - 14 - (i % 2) * 18} r={2 + (i % 3)} fill="#fff" opacity={0.5} className={`hg__bubble${i % 2 ? ' hg__bubble--late' : ''}`} />
      ))}
      <Caption y={70} lines={[['O₂', 'hg__t--icon'], [amount(r.remaining, 'L'), 'hg__t--big'], [budget ? `${Math.round(f * 100)} %` : ''], [r.lastsS == null ? 'not in use' : `lasts ${fmtDuration(r.lastsS)}`]]} />
    </>
  );
}

/**
 * Exhaled CO2: the same tank as the oxygen gauge, in red, filling up as the astronaut breathes CO2 out (its full
 * scale is the CO2 the whole oxygen supply would produce). An estimate: the suit's removal capacity is not modelled.
 */
function Co2Gauge({ c }: { c: Co2Line }) {
  const f = c.budgetL ? clamp01(c.exhaledL / c.budgetL) : 0;
  const level = V * (1 - f);
  return (
    <>
      <rect x={0} y={0} width={V} height={V} fill="#1b0808" />
      <rect x={0} y={level} width={V} height={V - level} fill={RED} opacity={0.55} className="hg__fill" />
      <path d={`M0 ${level} q21 -6 42 0 t42 0 t42 0 t42 0 V${V} H0 Z`} fill={RED} opacity={0.35} className="hg__wave" />
      {[30, 62, 104, 132].map((x, i) => (
        <circle key={x} cx={x} cy={V - 14 - (i % 2) * 18} r={2 + (i % 3)} fill="#fff" opacity={0.5} className={`hg__bubble${i % 2 ? ' hg__bubble--late' : ''}`} />
      ))}
      <Caption y={70} lines={[['CO₂', 'hg__t--icon'], [amount(c.exhaledL, 'L', 1), 'hg__t--big'], [c.budgetL ? `${Math.round(f * 100)} % exhaled` : ''], [c.perHour == null || c.perHour < 1e-6 ? 'not breathing hard' : `${amount(c.perHour, 'L/h', 1)} est.`]]} />
    </>
  );
}

/** Energy: the circle is the battery; five cells stack up from the bottom to the charge left. */
function EnergyGauge({ r, budget }: { r: ResourceLine; budget: number | null }) {
  const f = budget ? clamp01((r.remaining ?? 0) / budget) : 0;
  const color = toneColor(r, AMBER);
  const cells = 5;
  const h = V / cells;
  const level = V * (1 - f);
  return (
    <>
      <rect x={0} y={0} width={V} height={V} fill="#140f05" />
      {Array.from({ length: cells }, (_, i) => {
        const y0 = V - (i + 1) * h;
        const top = Math.max(y0, level);
        const height = y0 + h - top;
        return height > 0 ? <rect key={i} x={0} y={top + 2} width={V} height={Math.max(0, height - 4)} fill={color} opacity={0.35 + 0.1 * i} className="hg__fill" /> : null;
      })}
      {Array.from({ length: cells - 1 }, (_, i) => (
        <line key={i} x1={0} x2={V} y1={(i + 1) * h} y2={(i + 1) * h} stroke="#140f05" strokeWidth={3} />
      ))}
      <path d="M92 14 52 90h28l-10 64 46-86H88z" fill="#fff" opacity={0.08} />
      <Caption y={66} lines={[['ENERGY', 'hg__t--icon'], [amount(r.remaining, 'Wh'), 'hg__t--big'], [r.perHour == null || r.perHour < 1e-6 ? 'idle' : `${amount(r.perHour, 'W')} draw`], [r.lastsS == null ? '' : `lasts ${fmtDuration(r.lastsS)}`]]} />
    </>
  );
}


function FillSvg({ title, children }: { title: string; children: ReactNode }) {
  const clip = `hg-clip-${useId().replace(/:/g, '')}`;
  return (
    <svg className="hg" viewBox={`0 0 ${V} ${V}`} role="img" aria-label={title}>
      <title>{title}</title>
      <defs>
        <clipPath id={clip}>
          <circle cx={R} cy={R} r={R} />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clip})`}>{children}</g>
    </svg>
  );
}

/** Atmosphere: the estimated pressure map of the area, agents on it, the selected one ringed. */
function AtmosMap({ bundle, view, atmosphere, size, agentId }: { bundle: ReplayBundle; view: ReplayView; atmosphere: AtmosphereData; size: number; agentId: string | null }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const sol = latestJezeroSol(atmosphere);
  const grid = heightGrid(bundle.rasters, 'belief', view.state?.map_version ?? 1);
  const field = useMemo(() => (sol?.pressure_pa != null ? pressureField(grid, sol.pressure_pa) : null), [grid, sol?.pressure_pa]);
  const meta = bundle.manifest.terrain_meta;
  useEffect(() => {
    const c = canvas.current;
    if (!c || !field) return;
    const { rows, cols } = bundle.rasters;
    const img = new ImageData(cols, rows);
    const span = field.max - field.min || 1;
    for (let r = 0; r < rows; r++) {
      for (let col = 0; col < cols; col++) {
        const v = field.values[r * cols + col];
        if (v == null) continue;
        const o = ((rows - 1 - r) * cols + col) * 4; // north up
        const k = (v - field.min) / span;
        img.data[o] = 25 + 45 * k;
        img.data[o + 1] = 55 + 125 * k;
        img.data[o + 2] = 100 + 130 * k;
        img.data[o + 3] = 255;
      }
    }
    const tmp = document.createElement('canvas');
    tmp.width = cols;
    tmp.height = rows;
    tmp.getContext('2d')!.putImageData(img, 0, 0);
    const g = c.getContext('2d')!;
    g.clearRect(0, 0, size, size);
    g.drawImage(tmp, 0, 0, size, size);
    const W = meta.cols * meta.resolution_m;
    const H = meta.rows * meta.resolution_m;
    for (const a of view.state?.agents ?? []) {
      const x = ((a.pose.position.x - meta.origin_x_m) / W) * size;
      const y = size - ((a.pose.position.y - meta.origin_y_m) / H) * size;
      const mine = a.agent_id === agentId;
      g.fillStyle = a.agent_kind === 'HUMAN' ? '#ffffff' : a.agent_kind === 'DRONE' ? CYAN : '#D8AD66';
      g.beginPath();
      g.arc(x, y, mine ? 4.5 : 3, 0, Math.PI * 2);
      g.fill();
      if (mine) {
        g.strokeStyle = '#ffffff';
        g.lineWidth = 1.5;
        g.beginPath();
        g.arc(x, y, 8, 0, Math.PI * 2);
        g.stroke();
      }
    }
  }, [field, bundle.rasters, view.state, meta, size, agentId]);
  const title = `Atmosphere, Jezero (MEDA sol ${sol?.sol ?? '–'}, ${sol?.earth_date ?? ''}): air ${amount(sol?.max_temp_c, '°C')} high, ${amount(sol?.min_temp_c, '°C')} low; ${amount(sol?.pressure_pa, 'Pa')}. Map: surface pressure estimated from that value at the area's mean height, scaled with height (scale height ${(SCALE_HEIGHT_M / 1000).toFixed(1)} km)${field ? `, ${field.min.toFixed(1)}–${field.max.toFixed(1)} Pa` : ''}. Not a measured field; recent site conditions, not those of the simulated run.`;
  return (
    <div className="hg__atmos" title={title}>
      <canvas ref={canvas} width={size} height={size} aria-label={title} />
      <svg className="hg hg__over" viewBox={`0 0 ${V} ${V}`} aria-hidden>
        {/* Two short lines well inside the circle, so nothing is clipped by its edge. */}
        <text x={R} y={V - 40} textAnchor="middle" className="hg__val">
          {amount(sol?.pressure_pa, 'Pa')}
        </text>
        <text x={R} y={V - 26} textAnchor="middle" className="hg__val hg__val--sub">
          {amount(sol?.max_temp_c, '°')} / {amount(sol?.min_temp_c, '°C')}
        </text>
      </svg>
    </div>
  );
}

interface Props {
  option: Exclude<HudOption, 'route'>;
  size: number;
  bundle: ReplayBundle;
  view: ReplayView;
  t: number;
  agent: AgentState | null;
  route: RouteDecision | null;
  budget: Budget | undefined;
  atmosphere: AtmosphereData | undefined;
  /** Scene id from the page URL (zone of the per-zone radiation rate). */
  runId: string;
}

/**
 * What the HUD's inner circle shows for the selected option, filling the whole circle: the oxygen
 * tank, the battery, radial bars for time and radiation dose, and the estimated pressure map for
 * the atmosphere. The 2D map shows only with no option or Route (see App). Display only.
 */
export function HudGauge({ option, size, bundle, view, t, agent, route, budget, atmosphere, runId }: Props) {
  if (option === 'atmos') {
    return atmosphere ? <AtmosMap bundle={bundle} view={view} atmosphere={atmosphere} size={size} agentId={agent?.agent_id ?? null} /> : null;
  }
  const lines = agent ? resourceLines(bundle, t, agent, route, budget) : [];
  const line = (k: ResourceLine['key']) => lines.find((l) => l.key === k) ?? null;
  const detail = (r: ResourceLine) =>
    `use ${r.perHour == null ? 'not estimated' : amount(r.perHour, `${r.unit}/h`, 1)}; lasts ${r.lastsS == null ? '–' : fmtDuration(r.lastsS)}; route needs ${amount(r.routeNeeds, r.unit)}, leaves ${amount(r.afterRoute, r.unit)}`;
  if (option === 'oxygen') {
    const r = line('oxygen');
    if (!r)
      return (
        <FillSvg title="Oxygen: only the astronaut breathes from a supply">
          <rect x={0} y={0} width={V} height={V} fill="#06131b" />
          <Caption y={80} lines={[['O₂ n/a', 'hg__t--big'], ['crew only']]} />
        </FillSvg>
      );
    const b = budget?.oxygen_l ?? null;
    return (
      <FillSvg title={`Oxygen ${amount(r.remaining, 'L')} of ${amount(b, 'L')}: ${detail(r)}`}>
        <OxygenGauge r={r} budget={b} />
      </FillSvg>
    );
  }
  if (option === 'co2') {
    // Exhaled CO2 from the oxygen used (respiratory quotient); the suit's removal capacity is not modelled.
    const o = line('oxygen');
    const c = o ? co2FromOxygen(o, budget?.oxygen_l ?? null) : null;
    if (!c)
      return (
        <FillSvg title="Exhaled CO2 is tracked for the astronaut only">
          <rect x={0} y={0} width={V} height={V} fill="#1b0808" />
          <Caption y={80} lines={[['CO₂ n/a', 'hg__t--big'], ['crew only']]} />
        </FillSvg>
      );
    const route = c.routeAddsL == null ? '' : `; the route in force adds ${amount(c.routeAddsL, 'L')}`;
    return (
      <FillSvg title={`CO2 exhaled ${amount(c.exhaledL, 'L', 1)} of ${amount(c.budgetL, 'L')} for the whole oxygen supply${route}. Estimate: oxygen used x respiratory quotient ${RESPIRATORY_QUOTIENT} (assumed); the suit's CO2 removal capacity is not modelled. Display only`}>
        <Co2Gauge c={c} />
      </FillSvg>
    );
  }
  if (option === 'energy') {
    const r = line('energy');
    if (!r) return null;
    const b = budget?.energy_wh ?? null;
    return (
      <FillSvg title={`Energy ${amount(r.remaining, 'Wh')} of ${amount(b, 'Wh')}: ${detail(r)}`}>
        <EnergyGauge r={r} budget={b} />
      </FillSvg>
    );
  }
  if (option === 'time') {
    const r = line('time');
    if (!r) return null;
    const b = budget?.time_s ?? null;
    return (
      <RadialBar
        f={b ? (r.remaining ?? 0) / b : null}
        color={toneColor(r, WHITE)}
        option="time"
        value={fmtDuration(r.remaining)}
        sub={r.afterRoute == null ? 'time left' : `${fmtDuration(r.afterRoute)} after route`}
        title={`Time left ${fmtDuration(r.remaining)} of ${fmtDuration(b)}; route travel ${fmtDuration(r.routeNeeds)}, ${fmtDuration(r.afterRoute)} left after it`}
      />
    );
  }
  // Radiation dose: the bar fills as the dose accumulates, on a scale up to the whole run. Each zone uses its own
  // surface rate (MSL RAD measured at Gale, estimated elsewhere); the older Gale-only average is the fallback.
  const zone = agent?.agent_kind === 'HUMAN' ? zoneCrewDose(runId, t) : null;
  if (zone) {
    const end = zoneCrewDose(runId, bundle.manifest.duration_s)!;
    const how = zone.measuredHere ? 'measured here by MSL RAD (Hassler et al. 2014)' : `estimated from RAD's dose-pressure relation (Guo et al. 2018)${zone.withinRange ? '' : ', outside the pressure range RAD measured'}`;
    return (
      <RadialBar
        f={end.usv ? zone.usv / end.usv : 0}
        color={RED}
        option="dose"
        value={`${fmtMicroSv(zone.usv)} µSv`}
        sub={`${zone.msvPerDay.toFixed(2)} mSv/day${zone.measuredHere ? '' : ' est.'}`}
        title={`Radiation dose so far ${fmtMicroSv(zone.usv)} µSv (± ${fmtMicroSv(zone.sigmaUsv)}), whole run ${fmtMicroSv(end.usv)} µSv, at ${zone.msvPerDay.toFixed(2)} mSv/day ${how}. That is ${(zone.careerShare * 100).toFixed(4)} % of NASA's ${NASA_CAREER_LIMIT_MSV} mSv career limit (NASA-STD-3001). Unshielded surface average without solar storms; an estimate, not a dosimeter reading`}
      />
    );
  }
  if (!agent || agent.agent_kind !== 'HUMAN' || !atmosphere) {
    return <RadialBar f={null} color={RED} option="dose" value={atmosphere ? 'crew only' : 'no data'} title="Radiation dose is tracked for the astronaut only" />;
  }
  const now = crewDose(atmosphere, t);
  const end = crewDose(atmosphere, bundle.manifest.duration_s);
  return (
    <RadialBar
      f={end.usv ? now.usv / end.usv : 0}
      color={RED}
      option="dose"
      value={`${fmtMicroSv(now.usv)} µSv`}
      sub={`${now.msvPerDay.toFixed(2)} mSv/day`}
      title={`Radiation dose so far ${fmtMicroSv(now.usv)} µSv (± ${fmtMicroSv(now.sigmaUsv)}), whole run ${fmtMicroSv(end.usv)} µSv, at ${now.msvPerDay.toFixed(2)} mSv/day: Curiosity RAD surface average (Gale, Hassler et al. 2014), unshielded; an estimate, not a dosimeter reading`}
    />
  );
}
