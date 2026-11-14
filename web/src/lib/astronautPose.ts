import * as THREE from 'three';

/**
 * Posture tuning for the astronaut clips (visual only; no scientific meaning).
 *
 * The original `moon_walk` clip rocks the pelvis (about -6 to +8 degrees), sways the
 * shoulders, leans the torso 9 to 18 degrees forward and bounces the hips by 0.2 m.
 * That reads as shaking and tilting on a map viewer. In a copy (the file and the original
 * clips are not modified) the spine and clavicles are held at their mean rotation and the
 * torso is set vertical, so the astronaut walks upright with no tilt. While walking the legs
 * keep the pelvis turn and weight shift they were animated with (the spine is counter-rotated,
 * so the torso does not follow), and the cycle is re-timed so the planted foot does not slide.
 */
export interface CalmOptions {
  /** Fraction of the pelvis, spine and clavicle rotation swing that is kept (0 = fixed, 1 = original). */
  sway: number;
  /** Fraction of the vertical hip position swing (the hop) that is kept. */
  bounce: number;
  /**
   * Fraction of the horizontal hip position swing that is kept (weight shift over the stance
   * foot). The feet are animated with it: removing it makes each planted foot slide.
   */
  hipShift: number;
  /** Forward lean left in the torso after straightening, degrees. */
  residualLeanDeg: number;
  /**
   * Keep the lower foot on the ground at every keyframe by moving the hips down. The source
   * clip is a lunar bounding gait with a long phase where both feet are in the air, which reads
   * as hopping; planting removes that flight phase without changing the legs.
   */
  plantFeet: boolean;
  /**
   * Fraction of the leg-root ("Hip" bone) rotation and position swing that is kept. That bone
   * carries only the legs, so keeping it does not tilt the torso; the clip's feet need its swing
   * to stay planted (without it each stance foot drifts about 14 cm sideways).
   */
  legSway: number;
  /**
   * Fraction of the pelvis ("Center" bone) rotation swing kept for the legs. The first spine
   * bone is counter-rotated by the same amount, so the torso, arms and head stay as calm as
   * with `sway`; the legs keep the pelvis turn their foot placement was animated with.
   */
  pelvisSway: number;
}

// bounce 0.1: the moon_walk hop is almost removed (a little is kept so the legs do not sink at full stride).
// Used for idle: the whole body is held still.
export const CALM: CalmOptions = { sway: 0, bounce: 0.1, residualLeanDeg: 0, plantFeet: true, legSway: 0, pelvisSway: 0, hipShift: 0.1 };
/**
 * Walk: the torso, arms and head are as calm as in CALM, but the legs keep the pelvis turn and
 * the weight shift they were animated with, so each planted foot stays put (see evenStride).
 */
export const WALK_CALM: CalmOptions = { ...CALM, legSway: 1, pelvisSway: 1, hipShift: 1 };

const ROTATION_TRACK = /^(Spine_[123]|[LR]_Clevicle)\d+_\d+\.quaternion$/;
const PELVIS_ROTATION_TRACK = /^Center\d+_\d+\.quaternion$/;
const LEG_ROOT_TRACK = /^Hip\d+_\d+\.(quaternion|position)$/;
const HIPS_POSITION_TRACK = /^Center\d+_\d+\.position$/;

/** Sampler of a track with its own interpolation (createInterpolant exists at runtime but is not in the typings). */
function interpolant(track: THREE.KeyframeTrack): THREE.Interpolant {
  return (track as unknown as { createInterpolant(): THREE.Interpolant }).createInterpolant();
}

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

/**
 * Like dampPosition, but the swing along `up` (a unit vector in the track's parent frame) keeps
 * `keepUp` and the swing across it keeps `keepAcross`.
 */
function dampPositionSplit(track: THREE.KeyframeTrack, up: THREE.Vector3, keepUp: number, keepAcross: number) {
  const v = track.values;
  const n = track.times.length;
  const mean = new THREE.Vector3();
  for (let i = 0; i < n; i++) mean.add(new THREE.Vector3().fromArray(v, i * 3).divideScalar(n));
  const d = new THREE.Vector3();
  for (let i = 0; i < n; i++) {
    d.fromArray(v, i * 3).sub(mean);
    const along = up.clone().multiplyScalar(d.dot(up));
    d.sub(along).multiplyScalar(keepAcross).addScaledVector(along, keepUp);
    mean.clone().add(d).toArray(v, i * 3);
  }
}

/** World up expressed in the hips' parent frame (that parent is not animated), or null. */
function hipsParentUp(root: THREE.Object3D): THREE.Vector3 | null {
  const hips = findNode(root, /^Center\d/);
  if (!hips?.parent) return null;
  root.updateMatrixWorld(true);
  const parent = hips.parent;
  const origin = parent.worldToLocal(new THREE.Vector3(0, 0, 0));
  return parent.worldToLocal(new THREE.Vector3(0, 1, 0)).sub(origin).normalize();
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

/**
 * Splits the pelvis motion between legs and torso: the pelvis track keeps `pelvisKeep` of its
 * swing (for the legs), and the first spine bone, its direct child, is counter-rotated so the
 * spine sees a pelvis that swings only by `torsoKeep`: S' = C_i^-1 * C_torso_i * S_i.
 */
function isolatePelvis(clip: THREE.AnimationClip, torsoKeep: number, pelvisKeep: number) {
  const pelvis = clip.tracks.find((t) => PELVIS_ROTATION_TRACK.test(t.name));
  const spine = clip.tracks.find((t) => /^Spine_1\d+_\d+\.quaternion$/.test(t.name));
  if (!pelvis || !spine) return;
  const torso = pelvis.clone();
  dampRotation(torso, torsoKeep);
  dampRotation(pelvis, pelvisKeep);
  const legsAt = interpolant(pelvis);
  const torsoAt = interpolant(torso);
  const c = new THREE.Quaternion();
  const ct = new THREE.Quaternion();
  const q = new THREE.Quaternion();
  for (let i = 0; i < spine.times.length; i++) {
    c.fromArray(legsAt.evaluate(spine.times[i]));
    ct.fromArray(torsoAt.evaluate(spine.times[i]));
    q.fromArray(spine.values, i * 4);
    c.invert().multiply(ct).multiply(q).normalize().toArray(spine.values, i * 4);
  }
}

/** Returns a calmer copy of a clip. `root` must be the model the clip animates. */
export function calmClip(root: THREE.Object3D, clip: THREE.AnimationClip, opts: CalmOptions = CALM): THREE.AnimationClip {
  const out = clip.clone();
  for (const t of out.tracks) {
    if (ROTATION_TRACK.test(t.name)) dampRotation(t, opts.sway);
    else if (HIPS_POSITION_TRACK.test(t.name)) {
      const up = hipsParentUp(root);
      if (up) dampPositionSplit(t, up, opts.bounce, opts.hipShift);
      else dampPosition(t, opts.bounce);
    }
    else if (LEG_ROOT_TRACK.test(t.name)) {
      if (t.name.endsWith('.quaternion')) dampRotation(t, opts.legSway);
      else dampPosition(t, opts.legSway);
    }
  }
  // After the spine is damped: the counter-rotation must act on the calmed spine keys.
  isolatePelvis(out, opts.sway, opts.pelvisSway);
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

/**
 * Re-times a walk clip so the stance foot moves backward (relative to the hips) at a constant
 * speed. The source clip does not: its stance foot slows near contact and lift-off and stays
 * almost still while the swing foot is raised, so at any single playback rate the planted foot
 * of an agent moving at constant ground speed skated. Each step of the cycle gets a duration
 * proportional to how far the stance foot travels in it (at least `minShare` of the mean step,
 * so lifts and contacts are still drawn). Poses are unchanged; only their timing is.
 */
export function evenStride(root: THREE.Object3D, clip: THREE.AnimationClip, samples = 240, minShare = 0.05): THREE.AnimationClip {
  const hips = findNode(root, /^Center\d/);
  const lAnkle = findNode(root, /^L_Ankle\d/);
  const rAnkle = findNode(root, /^R_Ankle\d/);
  if (!hips || !lAnkle || !rAnkle) return clip;

  const mixer = new THREE.AnimationMixer(root);
  const action = mixer.clipAction(clip);
  action.play();
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const h = new THREE.Vector3();
  const feet: { left: boolean; x: number; z: number }[] = [];
  for (let i = 0; i <= samples; i++) {
    mixer.setTime(Math.min((clip.duration * i) / samples, clip.duration - 1e-6));
    root.updateMatrixWorld(true);
    lAnkle.getWorldPosition(a);
    rAnkle.getWorldPosition(b);
    hips.getWorldPosition(h);
    const left = a.y < b.y;
    const foot = left ? a : b;
    feet.push({ left, x: foot.x - h.x, z: foot.z - h.z });
  }
  action.stop();
  mixer.uncacheClip(clip);
  mixer.uncacheRoot(root);

  // Backward direction: mean displacement of the stance foot relative to the hips.
  const back = new THREE.Vector2();
  for (let i = 1; i <= samples; i++) {
    if (feet[i].left === feet[i - 1].left) back.add(new THREE.Vector2(feet[i].x - feet[i - 1].x, feet[i].z - feet[i - 1].z));
  }
  if (back.lengthSq() < 1e-12) return clip;
  back.normalize();
  const ds: (number | null)[] = [];
  let sum = 0;
  let n = 0;
  for (let i = 1; i <= samples; i++) {
    if (feet[i].left !== feet[i - 1].left) {
      ds.push(null); // stance switches: no travel to measure, gets the mean step
      continue;
    }
    const d = Math.max(0, (feet[i].x - feet[i - 1].x) * back.x + (feet[i].z - feet[i - 1].z) * back.y);
    ds.push(d);
    sum += d;
    n++;
  }
  const mean = n ? sum / n : 0;
  if (!(mean > 0)) return clip;

  // New key times: steps proportional to stance travel, keeping the clip's mean stance speed.
  const unit = clip.duration / (samples * mean);
  const times = new Float32Array(samples + 1);
  for (let i = 1; i <= samples; i++) times[i] = times[i - 1] + Math.max(ds[i - 1] ?? mean, minShare * mean) * unit;

  const tracks = clip.tracks.map((track) => {
    const interp = interpolant(track);
    const size = track.getValueSize();
    const values = new Float32Array((samples + 1) * size);
    for (let i = 0; i <= samples; i++) values.set(interp.evaluate((clip.duration * i) / samples), i * size);
    const Track = track.constructor as new (name: string, times: ArrayLike<number>, values: ArrayLike<number>) => THREE.KeyframeTrack;
    return new Track(track.name, times, values);
  });
  return new THREE.AnimationClip(clip.name, times[samples], tracks);
}
