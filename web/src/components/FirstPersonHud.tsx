import { useEffect, useRef, type ReactNode } from 'react';
import type { AgentState, RouteDecision } from '../types/icd';
import type { PointOfInterest } from '../types/replay';
import { AGENT_NAME } from '../lib/management';
import { angleDiffDeg, bearingDeg } from '../lib/scan';
import { povState } from './FirstPersonCamera';
import { fmtM } from './PovRoute';
import type { ResourceAlert } from '../lib/resourceAlert';
import { TerrainScanButton } from './TerrainScanButton';
import { SiteIcon } from './SiteIcon';
import { siteKind } from '../lib/siteKinds';

/** Visible width of the compass tape (deg either side of the heading). */
const TAPE_HALF_DEG = 60;
const CARDINALS: Array<[number, string]> = [
  [0, 'N'], [45, 'NE'], [90, 'E'], [135, 'SE'], [180, 'S'], [225, 'SW'], [270, 'W'], [315, 'NW'],
];

interface Props {
  agent: AgentState;
  /** Mode chip text, e.g. "REPLAY · SIMULATION": never shown as a live mission. */
  sourceLabel: string;
  pois: PointOfInterest[];
  onExit: () => void;
  /** Route in force (any agent); the draped route and waypoint are drawn in the scene (PovRoute). */
  route?: RouteDecision | null;
  /** The agent dial of the third-person view (menu with resources, atmosphere, route... and the heading-up map). */
  dial: ReactNode;
  /** Resource alert of this agent (lib/resourceAlert), or null. */
  alert: ResourceAlert | null;
  /** Drone camera window (DroneCamFrame) shown in the bottom dock, or null. */
  droneCam: ReactNode;
  droneCamOn: boolean;
  canDroneCam: boolean;
  onDroneCam: () => void;
  /** Astronaut helmet lights (L). */
  helmetLight: boolean;
  canHelmetLight: boolean;
  onHelmetLight: () => void;
  /** Terrain lit as by day whatever the hour (I). */
  artificialLight: boolean;
  onArtificialLight: () => void;
  /** Camera sway on/off (B). */
  sway: boolean;
  onSway: (on: boolean) => void;
}

/**
 * First-person overlay: a quiet cartographic HUD (thin rules, one accent colour) with a compass tape
 * and site bearings, the shared agent dial (resources live in its menu), and the drone-camera scan control and readout. Every
 * value comes from the replay or from lib/scan; nothing here is a live measurement.
 */
export function FirstPersonHud({ agent, sourceLabel, pois, onExit, dial, alert, droneCam, droneCamOn, canDroneCam, onDroneCam, helmetLight, canHelmetLight, onHelmetLight, artificialLight, onArtificialLight, sway, onSway }: Props) {
  const tape = useRef<HTMLDivElement>(null);
  const readout = useRef<HTMLSpanElement>(null);
  const pitch = useRef<HTMLSpanElement>(null);
  const marks = useRef<HTMLDivElement>(null);
  const pos = agent.pose.position;
  const sites = pois.map((p) => ({ id: p.id, label: p.label, kind: p.kind, bearing: bearingDeg(pos.x, pos.y, p.position.x, p.position.y), dist: Math.hypot(p.position.x - pos.x, p.position.y - pos.y) }));
  const base = sites.find((x) => x.kind === 'base') ?? null;
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
            <span key={s.id} className={`pov__site pov__site--${s.kind}`} style={{ color: siteKind(s.kind).color }} title={`${siteKind(s.kind).title} ${s.label}: bearing ${s.bearing.toFixed(0)}°, ${s.dist.toFixed(0)} m (straight line)`}>
              <SiteIcon kind={s.kind} size={16} />
              <b>{s.label}</b>
              <em>{s.dist >= 1000 ? `${(s.dist / 1000).toFixed(2)} km` : `${s.dist.toFixed(0)} m`}</em>
            </span>
          ))}
        </div>
        <div className="pov__heading">
          <span ref={readout}>000</span>
          <small ref={pitch} />
        </div>
      </div>

      {/* The same agent dial as in third person: its menu and, at the centre, the heading-up map. */}
      <div className="pov__dial">{dial}</div>

      <div className="pov__reticle" aria-hidden>
        <span />
      </div>

      {alert && (
        <div className={`pov__alert pov__alert--${alert.level}`} role="alert">
          <strong>
            {alert.level === 'critical' ? 'Critical' : 'Low'} · {alert.label}
            {alert.share != null && <b>{Math.round(alert.share * 100)}%</b>}
          </strong>
          <span>{alert.reason}</span>
          <em>
            {alert.action}
            {alert.level === 'critical' && base ? ` · ${base.id} ${base.dist >= 1000 ? `${(base.dist / 1000).toFixed(2)} km` : `${base.dist.toFixed(0)} m`} · bearing ${base.bearing.toFixed(0).padStart(3, '0')}°` : ''}
          </em>
          {alert.level === 'low' && alert.turnBackInM != null && <span>Turn-back point in {fmtM(alert.turnBackInM)}</span>}
          <small>Route sufficiency check · 20% reserve (JZ-P06, experimental) · display only, the replay's plan is unchanged</small>
        </div>
      )}

      {/* Bottom dock: drone camera (left), every key control in one place (centre), scan readout (right). */}
      <div className="pov__dock">
        <div className="pov__dock-cam">{droneCam}</div>
        <div className="pov__keys" role="toolbar" aria-label="First-person controls">
          <div className="pov__keys-row">
            <TerrainScanButton />
            <button type="button" className="pov__key" aria-pressed={droneCamOn} onClick={onDroneCam} disabled={!canDroneCam} title={canDroneCam ? 'Drone camera window (C)' : 'No drone camera here'}>
              <kbd>C</kbd> Drone cam
            </button>
            <button type="button" className="pov__key" aria-pressed={helmetLight} onClick={onHelmetLight} disabled={!canHelmetLight} title={canHelmetLight ? "Astronaut's helmet lights (L)" : 'No astronaut in this run'}>
              <kbd>L</kbd> Lights {helmetLight ? 'on' : 'off'}
            </button>
            <button type="button" className="pov__key" aria-pressed={!artificialLight} onClick={onArtificialLight} title={artificialLight ? 'Show the terrain with the real light of the hour at the site (I)' : 'Artificial light: the terrain lit as by day whatever the hour (I)'}>
              <kbd>I</kbd> {artificialLight ? 'Real light' : 'Artificial light'}
            </button>
            <button type="button" className="pov__key" aria-pressed={sway} onClick={() => onSway(!sway)} title="Camera sway while walking or driving (display only)">
              <kbd>B</kbd> Sway {sway ? 'on' : 'off'}
            </button>
            <button type="button" className="pov__key" onClick={onExit} title="Back to the third-person view (V)">
              <kbd>V</kbd> Third person
            </button>
          </div>
          <div className="pov__hints">
            <span>Drag · look</span>
            <span>Wheel · zoom</span>
            <span>Double-click · recentre</span>
          </div>
        </div>
        {/* Right column kept empty so the keys stay centred. */}
        <div className="pov__dock-scan" />
      </div>

      {/* Power-on sequence: the screen opens like a display switching on, then a short boot log. */}
      <div className="pov__power" aria-hidden>
        <i />
      </div>
      <div className="pov__boot" aria-hidden>
        <span>MGE · HUD</span>
        <span>Power ··· ok</span>
        <span>Link · replay ({sourceLabel})</span>
        <span>Nav · compass · map ··· ok</span>
        <span>{AGENT_NAME[agent.agent_kind]} {agent.agent_id} · online</span>
      </div>
    </div>
  );
}
