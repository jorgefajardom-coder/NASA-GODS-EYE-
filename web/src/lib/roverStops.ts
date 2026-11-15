import type { AgentMode } from '../types/icd';
import type { RoverStop } from '../types/replay';

/**
 * Real Perseverance stops inside the run area (NASA MMGIS waypoints) and the rule that opens their
 * mission images: the selected agent stands on one. Display only: the stops never reach the map,
 * the planner or the replay's mission.
 */
/** An agent is "on" a stop when it is this close (m). */
export const STOP_ARRIVE_M = 25;
/** Stops listed in the compass and drawn with an icon in 3D are the ones within this range (m). */
export const STOP_NEAR_M = 250;

const STOPPED_MODES: ReadonlySet<AgentMode> = new Set<AgentMode>(['IDLE', 'WORKING', 'HALTED', 'OBSERVING']);

/** Whether the agent is standing still (not driving or walking). */
export const isStationary = (mode: AgentMode): boolean => STOPPED_MODES.has(mode);

export interface StopDistance {
  stop: RoverStop;
  distM: number;
}

/** Stops within `radiusM` of (x, y), nearest first. */
export function stopsNear(stops: readonly RoverStop[], x: number, y: number, radiusM: number): StopDistance[] {
  const out: StopDistance[] = [];
  for (const stop of stops) {
    const distM = Math.hypot(stop.x_m - x, stop.y_m - y);
    if (distM <= radiusM) out.push({ stop, distM });
  }
  return out.sort((a, b) => a.distM - b.distM);
}

/** The stop the agent is standing on, or null while it is moving or away from every stop. */
export function stopUnderAgent(stops: readonly RoverStop[], x: number, y: number, mode: AgentMode): RoverStop | null {
  if (!isStationary(mode)) return null;
  return stopsNear(stops, x, y, STOP_ARRIVE_M)[0]?.stop ?? null;
}

/**
 * Replay time of the next (dir 1) or previous (dir -1) stop of the photo tour, or null when there is
 * none. Going back from within a few seconds of an arrival jumps to the stop before it.
 */
export function tourStepTime(stops: readonly RoverStop[], t: number, dir: 1 | -1): number | null {
  const times = stops.map((s) => s.tour_arrival_s).filter((v): v is number => typeof v === 'number').sort((a, b) => a - b);
  if (dir > 0) return times.find((v) => v > t + 1) ?? null;
  const before = times.filter((v) => v < t - 5);
  return before.length ? before[before.length - 1] : null;
}

/** Short label: "sol 13 · stop 3_0". */
export const stopLabel = (s: RoverStop): string => `sol ${s.sol} · stop ${s.rmc}`;
