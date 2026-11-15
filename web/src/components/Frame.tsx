import { LiveClocks } from './LiveClocks';
import type { ReplayManifest } from '../types/replay';
import type { AgentState } from '../types/icd';
import type { MissionAlert } from '../lib/management';
import { fmtSimTime } from '../lib/format';
import { OFFERED_RUNS, RUNS } from '../data/replayAdapter';
import { displayState } from '../lib/provenance';
import { terrainResolutionLabel } from '../lib/terrainPresentation';

export type UiMode = 'exploration' | 'geology' | 'atmos' | 'replay';

function terrainLabel(m: ReplayManifest): string {
  const t = m.terrain_meta;
  const where = t.origin_lat_deg == null || t.origin_lon_deg == null ? '' : ` · ${t.origin_lat_deg.toFixed(2)}°N ${t.origin_lon_deg.toFixed(2)}°E`;
  const name = /ctx-dtm/.test(t.dataset_id) ? 'CTX DTM' : t.dataset_id;
  return `${name} · ${terrainResolutionLabel(t)}${where}`;
}

/** Opens another saved run (full reload keeps every run's state separate). */
function openRun(id: string) {
  const url = new URL(window.location.href);
  url.searchParams.set('run', id);
  window.location.assign(url.toString());
}

/** Mission identity and run selector, top left. */
export function TitleBlock({ manifest, runId }: { manifest: ReplayManifest; runId: string }) {
  const entry = RUNS.find((run) => run.id === runId);
  return (
    <header className="title">
      <h1 className="title__main">Mission Management</h1>
      <div className="title__sub">
        {manifest.title} · {terrainLabel(manifest)}
      </div>
      {entry?.note && <p className="muted small">{entry.note} Recorded run: {manifest.run_id}.</p>}
      <label className="title__run">
        <span>Run</span>
        <select value={runId} onChange={(e) => openRun(e.target.value)} aria-label="Saved run">
          {OFFERED_RUNS.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
          {/* A run opened with ?run= that is not offered still shows its own name. */}
          {!OFFERED_RUNS.some((r) => r.id === runId) && <option value={runId}>{entry?.label ?? runId}</option>}
        </select>
      </label>
    </header>
  );
}

interface StatusProps {
  manifest: ReplayManifest;
  missionState: string;
  t: number;
  agent: AgentState | null;
  evaluator: boolean;
  /** Evaluator view requested but no reference available (production build or not generated). */
  evaluatorMissing?: boolean;
  exaggeration: number;
}

/**
 * Replay status, top right (the agent position is in the details panel). The chip, mission and sim time describe the
 * recorded replay on screen; the connection to a running ROS gateway (`?gateway=`) is shown only in its own panel.
 */
export function StatusBlock({ manifest, missionState, t, evaluator, evaluatorMissing, exaggeration }: StatusProps) {
  return (
    <section className="status" aria-label="Replay and mission status">
      <div className="status__line">
        <span className="chip-mode" title="Recorded data (REPLAY) and who produced it (source_mode, ICD §6.1)">
          {displayState({ mode: 'REPLAY', source: manifest.source_mode ?? 'UNKNOWN' }).label}
        </span>
      </div>
      <dl className="status__grid mono">
        <dt>Mission</dt>
        <dd>{missionState.toLowerCase()}</dd>
        <dt>Sim time</dt>
        <dd>{fmtSimTime(t)}</dd>
        {/* Real present time on Earth (the viewer's) and on Mars; the sim time above is the replay's. */}
        <LiveClocks lonEastDeg={manifest.terrain_meta.origin_lon_deg ?? undefined} world={manifest.world} />
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
  { id: 'atmos', label: 'Atmos', mode: 'atmos' },
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
