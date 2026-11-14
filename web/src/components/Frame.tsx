import type { ReplayManifest } from '../types/replay';
import type { AgentState } from '../types/icd';
import type { MissionAlert } from '../lib/management';
import { fmtSimTime } from '../lib/format';
import { RUNS } from '../data/replayAdapter';

export type UiMode = 'exploration' | 'geology' | 'replay';

function terrainLabel(m: ReplayManifest): string {
  const t = m.terrain_meta;
  const where = t.origin_lat_deg == null || t.origin_lon_deg == null ? '' : ` · ${t.origin_lat_deg.toFixed(2)}°N ${t.origin_lon_deg.toFixed(2)}°E`;
  const name = /ctx-dtm/.test(t.dataset_id) ? 'CTX DTM' : t.dataset_id;
  return `${name} ${t.resolution_m} m${where}`;
}

/** Opens another saved run (full reload keeps every run's state separate). */
function openRun(id: string) {
  const url = new URL(window.location.href);
  url.searchParams.set('run', id);
  window.location.assign(url.toString());
}

/** Mission identity and run selector, top left. */
export function TitleBlock({ manifest, runId }: { manifest: ReplayManifest; runId: string }) {
  return (
    <header className="title">
      <h1 className="title__main">Mission Management</h1>
      <div className="title__sub">
        {manifest.title} · {terrainLabel(manifest)}
      </div>
      <label className="title__run">
        <span>Run</span>
        <select value={runId} onChange={(e) => openRun(e.target.value)} aria-label="Saved run">
          {RUNS.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
          {!RUNS.some((r) => r.id === runId) && <option value={runId}>{runId}</option>}
        </select>
      </label>
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
  /** Evaluator view requested but no reference available (production build or not generated). */
  evaluatorMissing?: boolean;
  exaggeration: number;
}

/** Link and replay status, top right (the agent position is in the details panel). The live link is shown as offline: the viewer does not connect to the gateway yet, it only plays recorded replays. */
export function StatusBlock({ missionState, mapVersion, t, evaluator, evaluatorMissing, exaggeration }: StatusProps) {
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
        <dt>Mars time</dt>
        <dd>Not available</dd>
        <dt>Relief</dt>
        <dd>{exaggeration === 1 ? 'true scale' : `${exaggeration}× (visual only)`}</dd>
      </dl>
      {/* Provenance is stated once, in the footer disclaimer; only the evaluator flag stays here. */}
      {evaluator && (
        <div className="status__prov">
          <span className="status__eval">{evaluatorMissing ? 'evaluator view: reference not available here' : 'evaluator view'}</span>
        </div>
      )}
    </section>
  );
}

const TABS: Array<{ id: string; label: string; mode?: UiMode; why?: string }> = [
  { id: 'exploration', label: 'Exploration', mode: 'exploration' },
  { id: 'geology', label: 'Ground layers', mode: 'geology' },
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
