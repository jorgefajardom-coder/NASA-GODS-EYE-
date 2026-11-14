import * as THREE from 'three';

/**
 * Posture tuning for the astronaut clips (visual only; no scientific meaning).
 *
 * The original `moon_walk` clip rocks the pelvis (about -6 to +8 degrees), sways the
 * shoulders, leans the torso 9 to 18 degrees forward and bounces the hips by 0.2 m.
 * That reads as shaking and tilting on a map viewer. In a copy (the file and the original
 * clips are not modified) the pelvis, spine and clavicles are held at their mean rotation
 * and the torso is set vertical, so the astronaut walks upright with no tilt; only the
 * legs, arms, head and a reduced hip bounce stay animated.
 */
export interface CalmOptions {
  /** Fraction of the pelvis, spine and clavicle rotation swing that is kept (0 = fixed, 1 = original). */
  sway: number;
  /** Fraction of the hip position swing that is kept. */
  bounce: number;
  /** Forward lean left in the torso after straightening, degrees. */
  residualLeanDeg: number;
  /**
   * Keep the lower foot on the ground at every keyframe by moving the hips down. The source
   * clip is a lunar bounding gait with a long phase where both feet are in the air, which reads
   * as hopping; planting removes that flight phase without changing the legs.
   */
  plantFeet: boolean;
}

// bounce 0.1: the moon_walk hop is almost removed (a little is kept so the legs do not sink at full stride).
export const CALM: CalmOptions = { sway: 0, bounce: 0.1, residualLeanDeg: 0, plantFeet: true };

const ROTATION_TRACK = /^(Center|Hip|Spine_[123]|[LR]_Clevicle)\d+_\d+\.quaternion$/;
const HIPS_POSITION_TRACK = /^Center\d+_\d+\.position$/;

function findNode(root: THREE.Object3D, re: RegExp): THREE.Object3D | null {
  let found: THREE.Object3D | null = null;
  root.traverse((o) => {
    if (!found && re.test(o.name)) found = o;
  });
  return found;
}

/** Pulls every keyframe of a quaternion track toward the track's mean rotation. */
function dampRotation(track: THREE.KeyframeTrack, keep: number) {
  const v = track.values;
  const n = track.times.length;
  const first = new THREE.Quaternion().fromArray(v, 0);
  const q = new THREE.Quaternion();
  const mean = new THREE.Quaternion(0, 0, 0, 0);
  for (let i = 0; i < n; i++) {
    q.fromArray(v, i * 4);
    if (q.dot(first) < 0) q.set(-q.x, -q.y, -q.z, -q.w);
    mean.set(mean.x + q.x, mean.y + q.y, mean.z + q.z, mean.w + q.w);
  }
  mean.normalize();
  for (let i = 0; i < n; i++) {
    q.fromArray(v, i * 4);
    if (q.dot(mean) < 0) q.set(-q.x, -q.y, -q.z, -q.w);
    mean.clone().slerp(q, keep).toArray(v, i * 4);
  }
}

function dampPosition(track: THREE.KeyframeTrack, keep: number) {
  const v = track.values;
  const n = track.times.length;
  const mean = [0, 0, 0];
  for (let i = 0; i < n; i++) for (let a = 0; a < 3; a++) mean[a] += v[i * 3 + a] / n;
  for (let i = 0; i < n; i++) for (let a = 0; a < 3; a++) v[i * 3 + a] = mean[a] + (v[i * 3 + a] - mean[a]) * keep;
}

/**
 * Rotates the whole spine chain (and everything above it) so the average
 * hips-to-head direction is nearly vertical. The rotation is applied to the first
 * spine bone, so legs, feet and hips are untouched.
 */
function straightenTorso(root: THREE.Object3D, clip: THREE.AnimationClip, residualLeanDeg: number) {
  const hips = findNode(root, /^Center\d/);
  const head = findNode(root, /^head\d/);
  const spine = findNode(root, /^Spine_1\d/);
  const track = spine && clip.tracks.find((t) => t.name === `${spine.name}.quaternion`);
  if (!hips || !head || !spine || !track || !spine.parent) return;

  const mixer = new THREE.AnimationMixer(root);
  const action = mixer.clipAction(clip);
  action.play();

  const samples = 24;
  const mean = new THREE.Vector3();
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  let parentWorld = new THREE.Quaternion();
  for (let i = 0; i < samples; i++) {
    mixer.setTime((clip.duration * i) / samples);
    root.updateMatrixWorld(true);
    if (i === 0) spine.parent.getWorldQuaternion(parentWorld);
    mean.add(head.getWorldPosition(a).sub(hips.getWorldPosition(b)).normalize());
  }
  action.stop();
  mixer.uncacheClip(clip);
  mixer.uncacheRoot(root);
  mean.normalize();

  // Target: vertical, tilted forward by the residual lean along the existing lean direction.
  const lean = new THREE.Vector3(mean.x, 0, mean.z);
  if (lean.lengthSq() < 1e-9) return;
  lean.normalize();
  // residualLeanDeg = 0 gives a fully vertical torso.
  const r = THREE.MathUtils.degToRad(residualLeanDeg);
  const target = new THREE.Vector3(0, Math.cos(r), 0).addScaledVector(lean, Math.sin(r));
  const delta = new THREE.Quaternion().setFromUnitVectors(mean, target);
  // Express the world rotation in the parent bone's frame: Q = P^-1 * delta * P.
  const local = parentWorld.clone().invert().multiply(delta).multiply(parentWorld);

  const q = new THREE.Quaternion();
  for (let i = 0; i < track.times.length; i++) {
    q.fromArray(track.values, i * 4);
    local.clone().multiply(q).normalize().toArray(track.values, i * 4);
  }
}

/** Applies a world-space rotation to every key of a bone's quaternion track: Q = P^-1 * delta * P * q. */
function rotateTrackInWorld(track: THREE.KeyframeTrack, parentWorld: THREE.Quaternion, delta: THREE.Quaternion) {
  const local = parentWorld.clone().invert().multiply(delta).multiply(parentWorld);
  const q = new THREE.Quaternion();
  for (let i = 0; i < track.times.length; i++) {
    q.fromArray(track.values, i * 4);
    local.clone().multiply(q).normalize().toArray(track.values, i * 4);
  }
}

/**
 * The held clavicle pose leaves one shoulder about 4.5 degrees higher than the other
 * (the side flips between idle and moon_walk). Each clavicle is turned about its own
 * pivot so both shoulder joints sit at their mean height; the spine, neck and head
 * are untouched, so the torso stays vertical.
 */
function levelShoulders(root: THREE.Object3D, clip: THREE.AnimationClip) {
  const sides = (['L', 'R'] as const).map((s) => {
    const clav = findNode(root, new RegExp(`^${s}_Clevicle\\d`));
    const arm = findNode(root, new RegExp(`^${s}_Arm\\d`));
    const track = clav && clip.tracks.find((t) => t.name === `${clav.name}.quaternion`);
    return clav && arm && track && clav.parent ? { clav, arm, track, parent: clav.parent } : null;
  });
  if (sides.some((s) => !s)) return;
  const [l, r] = sides as NonNullable<(typeof sides)[number]>[];

  const mixer = new THREE.AnimationMixer(root);
  const action = mixer.clipAction(clip);
  action.play();
  const samples = 24;
  const mean = { lArm: new THREE.Vector3(), rArm: new THREE.Vector3(), lClav: new THREE.Vector3(), rClav: new THREE.Vector3() };
  const lParent = new THREE.Quaternion();
  const rParent = new THREE.Quaternion();
  const v = new THREE.Vector3();
  for (let i = 0; i < samples; i++) {
    mixer.setTime((clip.duration * i) / samples);
    root.updateMatrixWorld(true);
    if (i === 0) {
      l.parent.getWorldQuaternion(lParent);
      r.parent.getWorldQuaternion(rParent);
    }
    mean.lArm.add(l.arm.getWorldPosition(v));
    mean.rArm.add(r.arm.getWorldPosition(v));
    mean.lClav.add(l.clav.getWorldPosition(v));
    mean.rClav.add(r.clav.getWorldPosition(v));
  }
  action.stop();
  mixer.uncacheClip(clip);
  mixer.uncacheRoot(root);
  for (const p of Object.values(mean)) p.divideScalar(samples);

  const level = (mean.lArm.y + mean.rArm.y) / 2;
  const turn = (arm: THREE.Vector3, clav: THREE.Vector3) => {
    const from = arm.clone().sub(clav);
    const to = new THREE.Vector3(arm.x, level, arm.z).sub(clav);
    return new THREE.Quaternion().setFromUnitVectors(from.normalize(), to.normalize());
  };
  rotateTrackInWorld(l.track, lParent, turn(mean.lArm, mean.lClav));
  rotateTrackInWorld(r.track, rParent, turn(mean.rArm, mean.rClav));
}

/**
 * Moves the hips track so that, at every keyframe, the lower ankle sits at the lowest ankle
 * height of the whole cycle (the stance foot stays on the ground). A rigid vertical shift of
 * the hips moves both feet by the same amount, so one pass is exact.
 */
function plantFeet(root: THREE.Object3D, clip: THREE.AnimationClip) {
  const hips = findNode(root, /^Center\d/);
  const lAnkle = findNode(root, /^L_Ankle\d/);
  const rAnkle = findNode(root, /^R_Ankle\d/);
  const track = hips && clip.tracks.find((t) => t.name === `${hips.name}.position`);
  if (!hips || !lAnkle || !rAnkle || !track || !hips.parent) return;

  const mixer = new THREE.AnimationMixer(root);
  const action = mixer.clipAction(clip);
  action.play();
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const lowest: number[] = [];
  for (const t of track.times) {
    mixer.setTime(Math.min(t, clip.duration - 1e-6));
    root.updateMatrixWorld(true);
    lowest.push(Math.min(lAnkle.getWorldPosition(a).y, rAnkle.getWorldPosition(b).y));
  }
  // World "down" expressed in the hips' parent frame (that parent is not animated).
  const parent = hips.parent;
  const origin = parent.worldToLocal(new THREE.Vector3(0, 0, 0));
  const down = parent.worldToLocal(new THREE.Vector3(0, -1, 0)).sub(origin);
  action.stop();
  mixer.uncacheClip(clip);
  mixer.uncacheRoot(root);

  const ground = Math.min(...lowest);
  const v = track.values;
  lowest.forEach((y, i) => {
    const lift = y - ground; // world units the stance foot is off the ground
    v[i * 3] += down.x * lift;
    v[i * 3 + 1] += down.y * lift;
    v[i * 3 + 2] += down.z * lift;
  });
}

/** Returns a calmer copy of a clip. `root` must be the model the clip animates. */
export function calmClip(root: THREE.Object3D, clip: THREE.AnimationClip, opts: CalmOptions = CALM): THREE.AnimationClip {
  const out = clip.clone();
  for (const t of out.tracks) {
    if (ROTATION_TRACK.test(t.name)) dampRotation(t, opts.sway);
    else if (HIPS_POSITION_TRACK.test(t.name)) dampPosition(t, opts.bounce);
  }
  straightenTorso(root, out, opts.residualLeanDeg);
  if (opts.sway === 0) levelShoulders(root, out); // only meaningful when the clavicles are held still
  if (opts.plantFeet) plantFeet(root, out);
  return out;
}

/**
 * Ground speed the walk clip represents, in model units per second at time scale 1: the median
 * horizontal speed of the stance (lower) ankle relative to the hips. Playing the clip at
 * `groundSpeed / clipWalkSpeed` keeps the planted foot still on the ground (no skating).
 */
export function clipWalkSpeed(root: THREE.Object3D, clip: THREE.AnimationClip, samples = 200): number {
  const hips = findNode(root, /^Center\d/);
  const lAnkle = findNode(root, /^L_Ankle\d/);
  const rAnkle = findNode(root, /^R_Ankle\d/);
  if (!hips || !lAnkle || !rAnkle) return 0;
  const mixer = new THREE.AnimationMixer(root);
  const action = mixer.clipAction(clip);
  action.play();
  const dt = clip.duration / samples;
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const h = new THREE.Vector3();
  const speeds: number[] = [];
  let prev: { left: boolean; x: number; z: number } | null = null;
  for (let i = 0; i <= samples; i++) {
    mixer.setTime(Math.min(i * dt, clip.duration - 1e-6));
    root.updateMatrixWorld(true);
    lAnkle.getWorldPosition(a);
    rAnkle.getWorldPosition(b);
    hips.getWorldPosition(h);
    const left = a.y < b.y;
    const foot = left ? a : b;
    const cur = { left, x: foot.x - h.x, z: foot.z - h.z };
    if (prev && prev.left === left) speeds.push(Math.hypot(cur.x - prev.x, cur.z - prev.z) / dt);
    prev = cur;
  }
  action.stop();
  mixer.uncacheClip(clip);
  mixer.uncacheRoot(root);
  speeds.sort((x, y) => x - y);
  return speeds.length ? speeds[speeds.length >> 1] : 0;
}

/**
 * Time scale for the walk clip so the stance foot does not slide: ground speed over the clip's
 * own speed, capped at `max` (beyond it the legs would flicker; some sliding is then unavoidable).
 */
export function walkTimeScale(groundSpeedMps: number, clipSpeedMps: number, max = WALK_MAX_TIME_SCALE): number {
  if (!(clipSpeedMps > 0) || !(groundSpeedMps > 0)) return 1;
  return Math.min(max, groundSpeedMps / clipSpeedMps);
}

/** Highest walk-cycle rate drawn: about 3.5 strides per second, a fast-forward look without strobing. */
export const WALK_MAX_TIME_SCALE = 8;
