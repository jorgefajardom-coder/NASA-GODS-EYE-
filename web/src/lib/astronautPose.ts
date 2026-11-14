import * as THREE from 'three';

/**
 * Posture tuning for the astronaut clips (visual only; no scientific meaning).
 *
 * The original `moon_walk` clip rocks the pelvis (about -6 to +8 degrees), sways the
 * shoulders, leans the torso 9 to 18 degrees forward and bounces the hips by 0.2 m.
 * That reads as shaking on a map viewer, especially when the replay runs fast. The
 * clip is damped here, in a copy: the file and the original clips are not modified.
 */
export interface CalmOptions {
  /** Fraction of the pelvis, spine and clavicle rotation swing that is kept (0 = fixed, 1 = original). */
  sway: number;
  /** Fraction of the hip position swing that is kept. */
  bounce: number;
  /** Forward lean left in the torso after straightening, degrees. */
  residualLeanDeg: number;
}

export const CALM: CalmOptions = { sway: 0.5, bounce: 0.5, residualLeanDeg: 4 };

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

/** Returns a calmer copy of a clip. `root` must be the model the clip animates. */
export function calmClip(root: THREE.Object3D, clip: THREE.AnimationClip, opts: CalmOptions = CALM): THREE.AnimationClip {
  const out = clip.clone();
  for (const t of out.tracks) {
    if (ROTATION_TRACK.test(t.name)) dampRotation(t, opts.sway);
    else if (HIPS_POSITION_TRACK.test(t.name)) dampPosition(t, opts.bounce);
  }
  straightenTorso(root, out, opts.residualLeanDeg);
  return out;
}
