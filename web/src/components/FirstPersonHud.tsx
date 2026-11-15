import { useEffect, useRef } from 'react';
import type { AgentState } from '../types/icd';
import type { PointOfInterest } from '../types/replay';
import type { ResourceLine } from '../lib/resources';
import type { Budget } from '../lib/management';
import { AGENT_NAME } from '../lib/management';
import { fmtDuration } from '../lib/format';
import { angleDiffDeg, bearingDeg, SCAN_CLASS_INFO, SCAN_RADIUS_M, type ScanClass } from '../lib/scan';
import { povState } from './FirstPersonCamera';

/** Visible width of the compass tape (deg either side of the heading). */
const TAPE_HALF_DEG = 60;
const CARDINALS: Array<[number, string]> = [
  [0, 'N'], [45, 'NE'], [90, 'E'], [135, 'SE'], [180, 'S'], [225, 'SW'], [270, 'W'], [315, 'NW'],
];
const POI_LABEL: Record<string, string> = { base: 'BASE', primary_goal: 'GOAL', poi: 'POI' };

interface Props {
  agent: AgentState;
  /** Mode chip text, e.g. "REPLAY · SIMULATION": never shown as a live mission. */
  sourceLabel: string;
  pois: PointOfInterest[];
  lines: ResourceLine[];
  budget: Budget | undefined;
  /** Scan state: null before the first scan; counts per band of the last one. */
  scan: { counts: Record<ScanClass, number>; fromId: string } | null;
  canScan: boolean;
  onScan: () => void;
  onExit: () => void;
}

const budgetOf = (b: Budget | undefined, key: ResourceLine['key']) => (b ? (key === 'oxygen' ? b.oxygen_l : key === 'energy' ? b.energy_wh : b.time_s) : null);

/**
 * First-person overlay: a quiet cartographic HUD (thin rules, one accent colour) with a compass tape
 * and site bearings, the agent's resources, and the drone-camera scan control and readout. Every
 * value comes from the replay or from lib/scan; nothing here is a live measurement.
 */
export function FirstPersonHud({ agent, sourceLabel, pois, lines, budget, scan, canScan, onScan, onExit }: Props) {
  const tape = useRef<HTMLDivElement>(null);
  const readout = useRef<HTMLSpanElement>(null);
  const pitch = useRef<HTMLSpanElement>(null);
  const marks = useRef<HTMLDivElement>(null);
  const pos = agent.pose.position;
  const sites = pois.map((p) => ({ id: p.id, kind: p.kind, bearing: bearingDeg(pos.x, pos.y, p.position.x, p.position.y), dist: Math.hypot(p.position.x - pos.x, p.position.y - pos.y) }));
  const sitesRef = useRef(sites);
  sitesRef.current = sites;

  // The tape follows the camera every frame without re-rendering React.
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const h = povState.headingDeg;
      if (tape.current) {
        for (const el of Array.from(tape.current.children) as HTMLElement[]) {
          const d = angleDiffDeg(h, Number(el.dataset.deg));
          el.style.left = `${50 + (d / TAPE_HALF_DEG) * 50}%`;
          el.style.opacity = Math.abs(d) > TAPE_HALF_DEG ? '0' : String(1 - Math.abs(d) / (TAPE_HALF_DEG * 1.4));
        }
      }
      if (marks.current) {
        (Array.from(marks.current.children) as HTMLElement[]).forEach((el, i) => {
          const s = sitesRef.current[i];
          if (!s) return;
          const d = angleDiffDeg(h, s.bearing);
          const off = Math.abs(d) > TAPE_HALF_DEG;
          el.style.left = `${50 + (Math.max(-TAPE_HALF_DEG, Math.min(TAPE_HALF_DEG, d)) / TAPE_HALF_DEG) * 50}%`;
          el.dataset.off = off ? (d < 0 ? 'left' : 'right') : '';
        });
      }
      if (readout.current) readout.current.textContent = String(Math.round(h) % 360).padStart(3, '0');
      if (pitch.current) pitch.current.textContent = `${povState.pitchDeg >= 0 ? '+' : ''}${povState.pitchDeg.toFixed(0)}° · ${povState.fovDeg.toFixed(0)}° FOV`;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const ticks: number[] = [];
  for (let d = 0; d < 360; d += 15) ticks.push(d);

  return (
    <div className="pov" role="region" aria-label={`First-person view: ${AGENT_NAME[agent.agent_kind]} ${agent.agent_id}`}>
      <div className="pov__frame" aria-hidden />

      <div className="pov__compass" aria-label="Compass">
        <div className="pov__tape" ref={tape}>
          {ticks.map((d) => {
            const card = CARDINALS.find(([c]) => c === d);
            return (
              <span key={d} data-deg={d} className={`pov__tick${card ? ' pov__tick--card' : ''}`}>
                {card ? card[1] : d % 45 === 0 ? '' : String(d).padStart(3, '0')}
              </span>
            );
          })}
        </div>
        <div className="pov__sites" ref={marks}>
          {sites.map((s) => (
            <span key={s.id} className={`pov__site pov__site--${s.kind}`} title={`${POI_LABEL[s.kind] ?? s.kind} ${s.id}: bearing ${s.bearing.toFixed(0)}°, ${s.dist.toFixed(0)} m (straight line)`}>
              <i aria-hidden />
              <b>{POI_LABEL[s.kind] ?? 'SITE'} {s.id}</b>
              <em>{s.dist >= 1000 ? `${(s.dist / 1000).toFixed(2)} km` : `${s.dist.toFixed(0)} m`}</em>
            </span>
          ))}
        </div>
        <div className="pov__heading">
          <span ref={readout}>000</span>
          <small ref={pitch} />
        </div>
      </div>

      <div className="pov__id">
        <span className="pov__kicker">POV · {AGENT_NAME[agent.agent_kind]}</span>
        <strong>{agent.agent_id}</strong>
        <span className="pov__mode">{sourceLabel}</span>
        <span className="pov__state">{agent.mode}</span>
      </div>

      <div className="pov__reticle" aria-hidden>
        <span />
      </div>

      <div className="pov__vitals" aria-label="Resources">
        {lines.map((l) => {
          const b = budgetOf(budget, l.key);
          const share = l.remaining != null && b ? Math.max(0, Math.min(1, l.remaining / b)) : null;
          const text = l.remaining == null ? 'no data' : l.key === 'time' ? fmtDuration(l.remaining) : `${l.remaining.toFixed(0)} ${l.unit}`;
          return (
            <div key={l.key} className={`pov__vital pov__vital--${l.tone}`}>
              <span className="pov__vital-label">{l.label}</span>
              <span className="pov__bar" title={share == null ? 'No reference' : 'Share of the first received sample (not a certified budget)'}>
                <span style={{ width: `${(share ?? 0) * 100}%` }} />
              </span>
              <span className="pov__vital-value">{text}</span>
            </div>
          );
        })}
        {agent.agent_kind !== 'HUMAN' && <p className="pov__note">Oxygen: not applicable</p>}
      </div>

      <div className="pov__scan">
        <button type="button" className="pov__scan-btn" onClick={onScan} disabled={!canScan} title={canScan ? 'Scan the ground around the drone with its camera (R)' : 'No drone in this run'}>
          <kbd>R</kbd> Scan · drone camera
        </button>
        {scan && (
          <div className="pov__legend" aria-live="polite">
            <span className="pov__kicker">
              Scan from {scan.fromId} · r {SCAN_RADIUS_M} m
            </span>
            {(Object.keys(SCAN_CLASS_INFO) as ScanClass[]).map((c) => (
              <span key={c} className="pov__legend-row">
                <i style={{ background: SCAN_CLASS_INFO[c].color }} aria-hidden />
                {SCAN_CLASS_INFO[c].label}
                <b>{scan.counts[c]}</b>
              </span>
            ))}
            <p className="pov__note">Orbital CTX slope (prior, ~60 m smoothing) shown from the drone's position. Display only: not a new observation; map version unchanged. Bands are display thresholds pending science approval.</p>
          </div>
        )}
      </div>

      <div className="pov__hints">
        <span>Drag · look</span>
        <span>Wheel · zoom</span>
        <span>Double-click · recentre</span>
        <button type="button" className="pov__exit" onClick={onExit}>
          <kbd>V</kbd> Third person
        </button>
      </div>
    </div>
  );
}
