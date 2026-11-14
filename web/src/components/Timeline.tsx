import type { MissionEvent } from '../types/icd';
import { fmtSimTime } from '../lib/format';
import { PlayIcon, RestartIcon } from './icons';

/** Replay speeds offered; capped at 10x so the agents stay readable. */
export const SPEEDS = [1, 5, 10] as const;

interface Props {
  t: number;
  duration: number;
  playing: boolean;
  speed: number;
  events: MissionEvent[];
  onPlayPause: () => void;
  onRestart: () => void;
  onSeek: (t: number) => void;
  onSpeed: (s: number) => void;
}

const KEY_EVENTS = new Set(['MAP_UPDATED', 'ROUTE_INVALIDATED', 'ROUTE_PUBLISHED', 'TASK_DISCOVERED']);

/** Replay controls. Keyboard: Space play/pause, ←/→ ±5 s, Home restart. */
export function Timeline({ t, duration, playing, speed, events, onPlayPause, onRestart, onSeek, onSpeed }: Props) {
  return (
    <section className="panel timeline" aria-label="Replay controls">
      <div className="timeline__buttons">
        <button type="button" onClick={onPlayPause} aria-label={playing ? 'Pause' : 'Play'} className="btn btn--primary">
          <PlayIcon playing={playing} /> {playing ? 'Pause' : 'Play'}
        </button>
        <button type="button" onClick={onRestart} aria-label="Restart" className="btn">
          <RestartIcon /> Restart
        </button>
        <label className="speed">
          Speed
          <select value={speed} onChange={(e) => onSpeed(Number(e.target.value))}>
            {SPEEDS.map((s) => (
              <option key={s} value={s}>
                {s}×
              </option>
            ))}
          </select>
        </label>
        <span className="clock" aria-live="off">
          {fmtSimTime(t)} <span className="muted">/ {fmtSimTime(duration)} sim</span>
        </span>
      </div>
      <div className="scrub">
        <input
          type="range"
          min={0}
          max={duration}
          step={duration < 120 ? 'any' : 1}
          value={Math.min(t, duration)}
          onChange={(e) => onSeek(Number(e.target.value))}
          aria-label="Simulated time"
          aria-valuetext={fmtSimTime(t)}
        />
        <div className="scrub__ticks" aria-hidden>
          {events
            .filter((e) => KEY_EVENTS.has(e.event_type))
            .map((e) => (
              <span
                key={e.event_id}
                className={`tick tick--${e.event_type.toLowerCase()}`}
                style={{ left: `${(e.timestamp_sim_s / duration) * 100}%` }}
                title={`${fmtSimTime(e.timestamp_sim_s)} ${e.event_type}`}
              />
            ))}
        </div>
      </div>
    </section>
  );
}
