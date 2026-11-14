import type { MissionEvent } from '../types/icd';
import type { ReplayView } from '../lib/replay';
import { fmtSimTime } from '../lib/format';

interface Props {
  view: ReplayView;
  onSeek: (t: number) => void;
}

const TYPE_TEXT: Record<string, string> = {
  MISSION_STATE_CHANGED: 'Mission state',
  GOAL_ACCEPTED: 'Goal accepted',
  GOAL_REJECTED: 'Goal rejected',
  MAP_UPDATED: 'Map updated',
  ROUTE_PUBLISHED: 'Route published',
  ROUTE_INVALIDATED: 'Route invalidated',
  TASK_DISCOVERED: 'Task discovered',
  TASK_STATE_CHANGED: 'Task',
  ERROR: 'Error',
};

/**
 * Explains the latest replanning (cause → invalidation → new route) and lists
 * every received event. The explanation stays on screen until a newer one exists.
 */
export function EventInspector({ view, onSeek }: Props) {
  const latest = view.replans[view.replans.length - 1];
  const events = [...view.events].reverse();
  return (
    <section className="panel inspector" aria-label="Mission events">
      <h2>Why did the route change?</h2>
      {latest ? (
        <ol className="why">
          {latest.cause && (
            <li>
              <span className="why__step">Observed</span>
              <span>{latest.cause.detail}</span>
            </li>
          )}
          <li>
            <span className="why__step why__step--bad">Invalidated</span>
            <span>{latest.invalidated.detail}</span>
          </li>
          {latest.replacement ? (
            <li>
              <span className="why__step why__step--good">New route</span>
              <span>{latest.replacement.detail}</span>
            </li>
          ) : (
            <li>
              <span className="why__step">Pending</span>
              <span>Waiting for the planner's new decision.</span>
            </li>
          )}
        </ol>
      ) : (
        <p className="muted">No replanning so far. The route in force was planned on map v{view.state?.map_version ?? 1}.</p>
      )}

      <h3>
        Event log <small>({view.events.length})</small>
      </h3>
      <ul className="events" aria-live="polite">
        {events.map((e) => (
          <EventRow key={e.event_id} e={e} onSeek={onSeek} />
        ))}
      </ul>
    </section>
  );
}

function EventRow({ e, onSeek }: { e: MissionEvent; onSeek: (t: number) => void }) {
  const tone =
    e.event_type === 'ROUTE_INVALIDATED' || e.new_state === 'REJECTED' || e.event_type === 'ERROR'
      ? 'bad'
      : e.event_type === 'MAP_UPDATED'
        ? 'info'
        : e.new_state === 'DONE' || e.new_state === 'COMPLETE' || e.event_type === 'ROUTE_PUBLISHED'
          ? 'good'
          : 'neutral';
  return (
    <li className={`event event--${tone}`}>
      <button type="button" onClick={() => onSeek(e.timestamp_sim_s)} title="Jump to this moment">
        <span className="event__time">{fmtSimTime(e.timestamp_sim_s)}</span>
        <span className="event__type">
          {TYPE_TEXT[e.event_type] ?? e.event_type}
          {e.task_id ? ` · ${e.task_id}` : ''}
          {e.new_state ? ` → ${e.new_state.toLowerCase()}` : ''}
        </span>
        <span className="event__detail">{e.detail}</span>
        <span className="event__meta">
          #{e.seq} · map v{e.map_version}
          {e.route_id ? ` · ${e.route_id}` : ''}
          {e.reason_code ? ` · ${e.reason_code}` : ''}
        </span>
      </button>
    </li>
  );
}
