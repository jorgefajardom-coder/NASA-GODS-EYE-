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
}

export const CALM: CalmOptions = { sway: 0, bounce: 0.5, residualLeanDeg: 0 };

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

/** Returns a calmer copy of a clip. `root` must be the model the clip animates. */
export function calmClip(root: THREE.Object3D, clip: THREE.AnimationClip, opts: CalmOptions = CALM): THREE.AnimationClip {
  const out = clip.clone();
  for (const t of out.tracks) {
    if (ROTATION_TRACK.test(t.name)) dampRotation(t, opts.sway);
    else if (HIPS_POSITION_TRACK.test(t.name)) dampPosition(t, opts.bounce);
  }
  straightenTorso(root, out, opts.residualLeanDeg);
  if (opts.sway === 0) levelShoulders(root, out); // only meaningful when the clavicles are held still
  return out;
}
