import type { ReplayManifest } from '../types/replay';
import type { AgentState } from '../types/icd';
import type { MissionAlert } from '../lib/management';
import { fmtSimTime } from '../lib/format';

export type UiMode = 'exploration' | 'replay';

/** Mission identity, top left. */
export function TitleBlock({ manifest }: { manifest: ReplayManifest }) {
  return (
    <header className="title">
      <div className="title__meta mono">MARS GODS EYE · {manifest.run_id}</div>
      <h1 className="title__main">Mission Management</h1>
      <div className="title__sub">
        {manifest.title} · Terrain: {manifest.terrain_meta.dataset_id}
      </div>
    </header>
  );
}

interface StatusProps {
  manifest: ReplayManifest;
  missionState: string;
  mapVersion: number;
  t: number;
  agent: AgentState | null;
  evaluator: boolean;
}

/** Link, replay and position status, top right. The live link is shown as offline: no gateway exists yet. */
export function StatusBlock({ manifest, missionState, mapVersion, t, agent, evaluator }: StatusProps) {
  const p = agent?.pose.position;
  return (
    <section className="status" aria-label="Connection and mission status">
      <div className="status__link">Offline</div>
      <div className="status__line">
        <span className="chip-mode">REPLAY</span>
        <span className="muted">live link not available</span>
      </div>
      <dl className="status__grid mono">
        <dt>Mission</dt>
        <dd>{missionState.toLowerCase()}</dd>
        <dt>Map</dt>
        <dd>v{mapVersion}</dd>
        <dt>Sim time</dt>
        <dd>{fmtSimTime(t)}</dd>
        <dt>Position</dt>
        <dd>{p ? `E ${p.x.toFixed(0)}  N ${p.y.toFixed(0)}  U ${p.z.toFixed(0)} m` : 'Not available'}</dd>
        <dt>Mars time</dt>
        <dd>Not available</dd>
      </dl>
      <div className="status__prov">
        {manifest.provenance.map((x) => (
          <span key={x}>{x}</span>
        ))}
        {manifest.illustrative && <span>illustrative</span>}
        {evaluator && <span className="status__eval">evaluator view</span>}
      </div>
    </section>
  );
}

const TABS: Array<{ id: string; label: string; mode?: UiMode; why?: string }> = [
  { id: 'exploration', label: 'Exploration', mode: 'exploration' },
  { id: 'tactical', label: 'Tactical map', why: 'Not built yet (planned for phase P1)' },
  { id: 'atmos', label: 'Atmos', why: 'No weather data delivered yet' },
  { id: 'replay', label: 'Mission replay', mode: 'replay' },
];

export function ModeTabs({ mode, onMode }: { mode: UiMode; onMode: (m: UiMode) => void }) {
  return (
    <div className="tabs" role="tablist" aria-label="Interface mode">
      {TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={t.mode === mode}
          disabled={!t.mode}
          title={t.why}
          className={`tabs__tab${t.mode === mode ? ' is-active' : ''}`}
          onClick={() => t.mode && onMode(t.mode)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function AlertBanner({ alert }: { alert: MissionAlert | null }) {
  if (!alert) return null;
  return (
    <div className={`alert alert--${alert.tone}`} role="alert">
      <strong>{alert.title}</strong>
      <span>{alert.detail}</span>
    </div>
  );
}
