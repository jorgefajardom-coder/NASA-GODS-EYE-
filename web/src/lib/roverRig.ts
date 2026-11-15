/**
 * The rover's camera rig (display only): which real camera is in use, where the mast head points,
 * the Mastcam-Z zoom and the arm. Everything moves the way the hardware can:
 *
 * - The mast head pans a full 360 deg and tilts from -90 to +90 deg (Bell et al. 2021; NASA Mars 2020
 *   instrument page). No slew rate is published in the sources checked, so the head turns at most
 *   MAST_RATE_DEG_S with a gentle acceleration (display assumption). It never jumps.
 * - Navcam and Hazcam have fixed lenses: no zoom. Only Mastcam-Z zooms, between 26 and 110 mm, at a
 *   limited motor speed (display assumption, no published rate).
 * - The Hazcams are fixed to the body: they cannot be aimed. WATSON looks from the arm's turret, so the
 *   arm must be deployed first; the arm moves only while the rover stands still.
 * - Changing camera is a cut (another camera's image), not a morph of one lens into another.
 *
 * The state is one shared object read and stepped each frame by the rover model (VehicleModel) and
 * read by the first-person camera; React components only issue requests.
 */
import { CAMERA_ORDER, ROVER_CAMERAS, type RoverCameraId, type StereoSide } from './roverCameras';

/** Mast head slew limit (deg/s) and acceleration (deg/s^2): display assumptions, see above. */
export const MAST_RATE_DEG_S = 20;
export const MAST_ACCEL_DEG_S2 = 40;
export const MAST_EL_MIN = -90;
export const MAST_EL_MAX = 90;
/** Mastcam-Z zoom motor: the whole 26-110 mm range in about 4 s (display assumption). */
export const ZOOM_MM_PER_S = 21;
/** Arm deploy or stow time in the viewer (s). The real arm takes minutes; the motion is compressed. */
export const ARM_MOVE_S = 6;
/**
 * Arm joint angles (deg, about each joint's own axis, added to the model's rest pose): shoulder azimuth,
 * shoulder, elbow, wrist. DEPLOYED puts WATSON where NASA's feed reports it during a ground close-up:
 * 2.45 m ahead, 0.77 m to the left of the rover centre and 0.16 m above the ground (camera_position of
 * a SHERLOC_WATSON frame, sol 2023), found by a forward-kinematics search over the model's own nodes.
 * STOWED folds it low across the front of the body with the turret at the corner, as the rover drives
 * with it (same search, display choice; the model's own rest pose holds the arm raised beside the mast).
 */
export const ARM_DEPLOYED_DEG = [-9.1, 0.6, -120, -147.5];
export const ARM_STOWED_DEG = [-123.4, 150, 0, 150];
/** The rig counts as settled when the head is this close to its target (deg) and nearly still. */
const SETTLE_DEG = 0.4;

export interface RigState {
  /** Camera asked for, and camera whose image is shown (a WATSON request shows the old one until the arm is out). */
  camera: RoverCameraId;
  view: RoverCameraId;
  side: StereoSide;
  /** Mast head pointing relative to the rover (deg; az clockwise from the front, el negative down) and rates. */
  az: number;
  el: number;
  azRate: number;
  elRate: number;
  targetAz: number;
  targetEl: number;
  /** Mastcam-Z focal length (mm) and its target. */
  focalMm: number;
  targetFocalMm: number;
  /** Arm deployment, 0 = stowed .. 1 = deployed, and its target. */
  arm: number;
  armTarget: 0 | 1;
  /** WATSON pointing in the rover frame (x forward, y right, z down), from the feed, or null (straight down). */
  watsonVector: [number, number, number] | null;
  /** Shot requests: the last asked for and the last one the rig reached. */
  token: number;
  readyToken: number;
  /** Bumped on every camera cut, so the view can snap instead of easing. */
  cut: number;
}

export function createRig(): RigState {
  return {
    camera: 'navcam', view: 'navcam', side: 'left',
    az: 0, el: -10, azRate: 0, elRate: 0, targetAz: 0, targetEl: -10,
    focalMm: 26, targetFocalMm: 26,
    arm: 0, armTarget: 0, watsonVector: null,
    token: 0, readyToken: 0, cut: 0,
  };
}

/** The one rover rig of the scene. */
export const roverRig: RigState = createRig();

/** Signed shortest turn (deg, -180..180). */
const turnDeg = (from: number, to: number) => ((((to - from) % 360) + 540) % 360) - 180;

/**
 * One axis of a motor with a speed and acceleration limit: it accelerates, cruises and brakes so that
 * it stops on the target without overshoot. Returns the new position and rate.
 */
export function stepAxis(pos: number, rate: number, target: number, maxRate: number, accel: number, dt: number, wrap = false): { pos: number; rate: number } {
  const err = wrap ? turnDeg(pos, target) : target - pos;
  if (Math.abs(err) < 1e-3 && Math.abs(rate) < accel * dt) return { pos: wrap ? pos + err : target, rate: 0 };
  // Highest speed from which it can still brake to a stop on the target.
  const vStop = Math.sqrt(2 * accel * Math.abs(err));
  const want = Math.sign(err) * Math.min(maxRate, vStop);
  const dv = Math.max(-accel * dt, Math.min(accel * dt, want - rate));
  let next = rate + dv;
  let step = next * dt;
  if (Math.abs(step) > Math.abs(err) && Math.sign(step) === Math.sign(err)) {
    step = err;
    next = 0;
  }
  let p = pos + step;
  if (wrap) p = ((p % 360) + 540) % 360 - 180;
  return { pos: p, rate: next };
}

/** Whether the head is on its target and still, the zoom done and the shown camera the one asked for. */
export function rigSettled(s: RigState): boolean {
  const cam = ROVER_CAMERAS[s.camera];
  const headOk = cam.mount !== 'mast' || (Math.abs(turnDeg(s.az, s.targetAz)) < SETTLE_DEG && Math.abs(s.el - s.targetEl) < SETTLE_DEG && Math.abs(s.azRate) + Math.abs(s.elRate) < 1);
  const zoomOk = s.camera !== 'mastcamz' || Math.abs(s.focalMm - s.targetFocalMm) < 0.2;
  return headOk && zoomOk && s.view === s.camera;
}

/**
 * Advances the rig by dt seconds (wall time). `stationary` is false while the rover drives: the arm
 * is then stowed, and WATSON falls back to the Navcam.
 */
export function stepRig(s: RigState, dt: number, stationary: boolean): void {
  if (!stationary && s.armTarget === 1) {
    s.armTarget = 0;
    if (s.camera === 'watson') s.camera = 'navcam';
  }
  const a = stepAxis(s.az, s.azRate, s.targetAz, MAST_RATE_DEG_S, MAST_ACCEL_DEG_S2, dt, true);
  s.az = a.pos;
  s.azRate = a.rate;
  const e = stepAxis(s.el, s.elRate, Math.max(MAST_EL_MIN, Math.min(MAST_EL_MAX, s.targetEl)), MAST_RATE_DEG_S, MAST_ACCEL_DEG_S2, dt);
  s.el = e.pos;
  s.elRate = e.rate;
  const dz = s.targetFocalMm - s.focalMm;
  s.focalMm += Math.sign(dz) * Math.min(Math.abs(dz), ZOOM_MM_PER_S * dt);
  const da = s.armTarget - s.arm;
  s.arm += Math.sign(da) * Math.min(Math.abs(da), dt / ARM_MOVE_S);
  // The shown camera follows the request; WATSON only once the arm is out, and a WATSON view ends as the arm leaves.
  const want = s.camera === 'watson' && s.arm < 1 ? (s.view === 'watson' ? 'navcam' : s.view) : s.camera;
  if (want !== s.view) {
    s.view = want;
    s.cut += 1;
  }
  if (s.token !== s.readyToken && rigSettled(s)) s.readyToken = s.token;
}

export interface ShotRequest {
  camera: RoverCameraId;
  side?: StereoSide;
  /** Mast pointing relative to the rover (deg); ignored by body cameras. */
  azDeg?: number | null;
  elDeg?: number | null;
  /** Mastcam-Z focal length (mm). */
  focalMm?: number | null;
  watsonVector?: [number, number, number] | null;
}

/** Asks the rig for a camera and pointing; returns the token that `shotReady` reports once reached. */
export function requestShot(s: RigState, r: ShotRequest): number {
  if (s.camera !== r.camera || (r.side && r.side !== s.side)) s.cut += 1;
  s.camera = r.camera;
  if (r.side) s.side = r.side;
  if (r.camera === 'watson') {
    s.armTarget = 1;
    s.watsonVector = r.watsonVector ?? null;
  }
  if (r.azDeg != null) s.targetAz = turnDeg(0, r.azDeg);
  if (r.elDeg != null) s.targetEl = Math.max(MAST_EL_MIN, Math.min(MAST_EL_MAX, r.elDeg));
  if (r.focalMm != null) {
    const [lo, hi] = ROVER_CAMERAS.mastcamz.focalMm!;
    s.targetFocalMm = Math.min(hi, Math.max(lo, r.focalMm));
  }
  s.token += 1;
  return s.token;
}

export const shotReady = (s: RigState, token: number): boolean => s.readyToken >= token;

/** Picks a camera by key (1-5 in the order of CAMERA_ORDER); the mast keeps its pointing. */
export function selectCamera(s: RigState, id: RoverCameraId): void {
  requestShot(s, { camera: id });
}

/** Stows the arm and returns to the Navcam looking ahead and slightly down. */
export function homeRig(s: RigState): number {
  s.armTarget = 0;
  return requestShot(s, { camera: 'navcam', azDeg: 0, elDeg: -10, focalMm: 26 });
}

/** Moves the mast target by a drag (deg) — only while a mast camera is in use. */
export function nudgeMast(s: RigState, dAzDeg: number, dElDeg: number): void {
  if (ROVER_CAMERAS[s.camera].mount !== 'mast') return;
  s.targetAz = turnDeg(0, s.targetAz + dAzDeg);
  s.targetEl = Math.max(MAST_EL_MIN, Math.min(MAST_EL_MAX, s.targetEl + dElDeg));
}

/** Changes the Mastcam-Z zoom target by a factor (wheel); other cameras have fixed lenses. */
export function zoomBy(s: RigState, factor: number): void {
  if (s.camera !== 'mastcamz') return;
  const [lo, hi] = ROVER_CAMERAS.mastcamz.focalMm!;
  s.targetFocalMm = Math.min(hi, Math.max(lo, s.targetFocalMm * factor));
}

export { CAMERA_ORDER };
