/**
 * Frame-rate independent exponential smoothing for the display only (no data is changed).
 *
 * The replay clock updates agent poses through React, so poses arrive in uneven steps
 * relative to the render loop. At 20x replay an astronaut covers ~0.5 m per frame, and
 * when the camera is close those uneven steps read as trembling. Easing the drawn pose
 * and the camera toward their targets removes the steps without extrapolating.
 */

/** Share of the remaining distance to cover this frame for a time constant `tauS` (0 = jump). */
export function dampFactor(dtS: number, tauS: number): number {
  if (tauS <= 0) return 1;
  return 1 - Math.exp(-Math.max(0, dtS) / tauS);
}

/** Shortest signed angle from `a` to `b`, radians in (-PI, PI]. */
export function angleDelta(a: number, b: number): number {
  const d = (b - a) % (2 * Math.PI);
  if (d > Math.PI) return d - 2 * Math.PI;
  if (d <= -Math.PI) return d + 2 * Math.PI;
  return d;
}

/** Eases an angle toward a target along the shortest way. */
export function dampAngle(current: number, target: number, dtS: number, tauS: number): number {
  return current + angleDelta(current, target) * dampFactor(dtS, tauS);
}

/** Drawn agent pose easing (s). Short so the agent never visibly lags its data. */
export const AGENT_POSE_TAU_S = 0.08;
/** A jump larger than this (seek, restart, run change) is shown at once, not eased (m). */
export const SNAP_DISTANCE_M = 40;

export type CameraSmoothing = 'off' | 'soft' | 'cinematic';

/** Orbit damping for each setting. The follow cameras are always locked on their target. */
export const CAMERA_SMOOTHING: Record<CameraSmoothing, { label: string; orbitDamping: number }> = {
  off: { label: 'Off (rigid)', orbitDamping: 0.25 },
  soft: { label: 'Soft', orbitDamping: 0.08 },
  cinematic: { label: 'Cinematic', orbitDamping: 0.04 },
};
