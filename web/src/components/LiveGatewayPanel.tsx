import { useEffect, useState } from 'react';
import { gatewayLive, useGatewayLive } from '../lib/gatewayLive';

/**
 * Read-only panel of a running ROS gateway (`?gateway=<url>`): connection, provenance label from the gateway's
 * source_mode (a MOCK stack shows MOCK), run, mission state, agents and the newest events. Collapsed to one line by
 * default so it does not cover the map; the toggle shows the details. It never sends goals and is separate from the
 * replay on screen. Display only; not a validated live mission.
 */
export function LiveGatewayPanel({ base }: { base: string }) {
  const s = useGatewayLive();
  const [now, setNow] = useState(() => Date.now());
  const [open, setOpen] = useState(false);
  useEffect(() => {
    gatewayLive.connect(base);
    return () => gatewayLive.disconnect();
  }, [base]);
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  const ago = s.updatedAt == null ? null : Math.max(0, Math.round((now - s.updatedAt) / 1000));
  const m = s.mission;
  const statusText =
    s.status === 'connected' ? `connected · ${s.transport ?? '…'}` : s.status === 'not_ready' ? `not ready · ${s.message ?? ''}` : s.status === 'error' ? `error · ${s.message ?? ''}` : s.status;
  const last = s.events.length ? s.events[s.events.length - 1] : null;
  const summary = s.status !== 'connected' ? statusText : m ? `${m.mission_state} · map v${m.map_version}` : 'connected';
  return (
    <section className={`live-gw live-gw--${s.status}${open ? ' live-gw--open' : ''}`} aria-label="Live ROS gateway" aria-live="polite">
      <header className="live-gw__head">
        <span className="live-gw__dot" aria-hidden />
        <strong>ROS</strong>
        <span className="chip-mode" title="Who produces the data (gateway source_mode, ICD §6.1). LIVE is reserved for a validated real source.">
          {s.status === 'connected' ? s.label : 'NOT_READY'}
        </span>
        <span className="live-gw__summary mono">{summary}</span>
        {!open && last && (
          <span className="live-gw__last muted" title={last.detail || last.event_type}>
            #{last.seq} {last.event_type}
          </span>
        )}
        <button type="button" className="live-gw__btn" aria-expanded={open} onClick={() => setOpen((v) => !v)} title={open ? 'Hide the gateway details' : 'Show the gateway details'}>
          {open ? '▴' : '▾'}
        </button>
      </header>
      {open && (
        <div className="live-gw__body">
          <p className="live-gw__line mono" title={base}>
            {statusText}
            {ago != null && s.status === 'connected' ? ` · updated ${ago} s ago` : ''}
          </p>
          {s.runId && (
            <p className="live-gw__line mono">
              run {s.runId} · {s.datasetId ?? 'no dataset'}
              {m ? ` · map v${m.map_version}` : ''}
            </p>
          )}
          {m && (
            <>
              <p className="live-gw__mission">
                Mission <strong>{m.mission_state}</strong>
                {m.reason_code ? <span className="muted"> · {m.reason_code}</span> : null}
              </p>
              <table className="live-gw__agents">
                <tbody>
                  {m.agents.map((a) => (
                    <tr key={a.agent_id}>
                      <td>{a.agent_id}</td>
                      <td className="muted">{a.mode}</td>
                      <td className="mono">
                        {a.pose.position.x.toFixed(1)}, {a.pose.position.y.toFixed(1)}
                      </td>
                      <td className="mono">{a.oxygen_remaining_l == null ? '' : `O₂ ${a.oxygen_remaining_l.toFixed(0)} L`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
          {s.events.length > 0 && (
            <ol className="live-gw__events" reversed>
              {[...s.events]
                .reverse()
                .slice(0, 5)
                .map((e) => (
                  <li key={e.seq} value={e.seq}>
                    <span className="mono muted">#{e.seq}</span> {e.detail || e.event_type}
                  </li>
                ))}
            </ol>
          )}
          <p className="live-gw__note muted small">
            Read-only view of the running stack, separate from the replay on screen. Not a validated live mission.{' '}
            <button type="button" className="live-gw__link" onClick={() => (s.status === 'off' ? gatewayLive.connect(base) : gatewayLive.disconnect())}>
              {s.status === 'off' ? 'Connect' : 'Disconnect'}
            </button>
          </p>
        </div>
      )}
    </section>
  );
}
