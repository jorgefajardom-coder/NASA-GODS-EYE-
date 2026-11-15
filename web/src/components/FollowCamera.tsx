import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { aimRequest } from '../lib/photoAim';
import { headingFromThree, povState } from './FirstPersonCamera';

/** Fastest swing of the camera towards a photo (rad/s, about 55 deg/s). */
const SWING_MAX_RAD_S = 0.96;

/** Where the camera sits relative to what it follows (m): behind, above, and the look-at height. */
export interface Framing {
  distanceM: number;
  heightM: number;
  lookAtM: number;
}

/**
 * Frame order (lower runs first): agent poses are eased at -2, then this camera at -1 (mounted
 * before the orbit controls, which update at -1), then the ground clamp (-1, mounted after the
 * controls), the distance scaling (-0.5) and finally the labels (drei Html, 0). Every label is
 * then placed with the camera of the same frame; placing it with the previous frame's camera
 * made the followed drone's label vibrate.
 */
export const FOLLOW_PRIORITY = -1;

/** Closest orbit distance (m) while following, and back in the free view (MissionScene). */
const FOLLOW_MIN_DISTANCE_M = 0.3;
const FREE_MIN_DISTANCE_M = 0.35; // same as MIN_ORBIT_DISTANCE_M in MissionScene

/** Photo tour: further back and higher, so more of the rover and of its surroundings is seen. */
export const TOUR_FRAMING: Framing = { distanceM: 12, heightM: 4.6, lookAtM: 1.1 };

/** Over-the-shoulder view of an agent. */
export const AGENT_FRAMING: Framing = { distanceM: 6, heightM: 2.6, lookAtM: 1.25 };

interface Props {
  /** Name of the scene object to follow (an agent group or the base anchor), or null for the free camera. */
  target: string | null;
  framing?: Framing;
  /** Write the camera heading to the first-person interface's compass (the tour shows it over this camera). */
  mirrorHud?: boolean;
}


/**
 * Third-person follow view. It reads the drawn (already eased) agent group from the
 * scene every frame, so the camera and the agent move in the same render step and the
 * agent stays steady on screen at any zoom. It only moves the camera and the orbit
 * target; the agent pose is never changed. The user can still orbit and zoom.
 */
export function FollowCamera({ target, framing = AGENT_FRAMING, mirrorHud = false }: Props) {
  const camera = useThree((s) => s.camera);
  const scene = useThree((s) => s.scene);
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null;
  const home = useRef<{ pos: THREE.Vector3; target: THREE.Vector3 } | null>(null);
  const following = useRef<string | null>(null);
  const world = useRef(new THREE.Vector3());
  const goal = useRef(new THREE.Vector3());
  const delta = useRef(new THREE.Vector3());
  // Photo direction asked for (lib/photoAim): the camera swings round the target to look that way.
  const look = useRef(new THREE.Vector3());
  const swing = useRef<{ seen: number; azimuth: number | null; pitch: number }>({ seen: aimRequest.token, azimuth: null, pitch: 0 });

  useEffect(() => {
    if (!controls) return;
    if (!target && following.current && home.current) {
      camera.position.copy(home.current.pos);
      controls.target.copy(home.current.target);
      controls.minDistance = FREE_MIN_DISTANCE_M;
      controls.update();
      following.current = null;
    }
  }, [target, controls, camera]);

  useFrame((_, dtRaw) => {
    if (!target || !controls) return;
    const obj = scene.getObjectByName(target);
    if (!obj) return;
    obj.getWorldPosition(world.current);
    goal.current.set(world.current.x, world.current.y + framing.lookAtM, world.current.z);

    if (following.current !== target) {
      // Entering (or switching target): remember the orbital view and place the camera behind the target.
      if (!following.current) home.current = { pos: camera.position.clone(), target: controls.target.clone() };
      const yaw = obj.rotation.y;
      controls.target.copy(goal.current);
      camera.position.set(world.current.x - Math.cos(yaw) * framing.distanceM, world.current.y + framing.heightM, world.current.z + Math.sin(yaw) * framing.distanceM);
      controls.minDistance = FOLLOW_MIN_DISTANCE_M;
      controls.update();
      following.current = target;
      return;
    }
    // Move camera and orbit target together so the user's chosen angle and zoom are kept.
    delta.current.copy(goal.current).sub(controls.target);
    // Locked on the target: a lagging follow let the target drift and catch up on screen, which
    // read as jumps (worst on the drone's altitude changes). Motion is already smoothed upstream
    // (monotone cubic between samples, eased drawn pose), so the lock itself is steady.
    controls.target.add(delta.current);
    camera.position.add(delta.current);

    // Swing behind the target so the view looks along the compass azimuth of the photo (eased).
    const sw = swing.current;
    if (aimRequest.token !== sw.seen) {
      sw.seen = aimRequest.token;
      sw.azimuth = aimRequest.azimuthDeg;
      sw.pitch = aimRequest.pitchDeg;
    }
    if (sw.azimuth != null) {
      const off = camera.position.clone().sub(controls.target);
      const radius = Math.hypot(off.x, off.z) || framing.distanceM;
      // Compass azimuth A looks towards (east, north) = (sin A, cos A); the camera sits on the opposite side.
      const a = (sw.azimuth * Math.PI) / 180;
      const want = Math.atan2(-Math.sin(a), -Math.cos(a)); // angle of the camera offset in the (east, north) plane
      const have = Math.atan2(-off.z, off.x); // Three.js: east = x, north = -z
      let d = want - have;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      // Eased and limited in speed, so the swing starts and ends gently (no snap to the new direction).
      const dtS = Math.min(Math.max(dtRaw, 1e-4), 0.1);
      const step = THREE.MathUtils.clamp(d * (1 - Math.exp(-dtS * 2.4)), -SWING_MAX_RAD_S * dtS, SWING_MAX_RAD_S * dtS);
      const next = have + step;
      off.x = Math.cos(next) * radius;
      off.z = -Math.sin(next) * radius;
      const wantY = Math.max(0.6, radius * Math.tan(-(sw.pitch * Math.PI) / 180) + 1.2); // looking down: camera above
      off.y += (THREE.MathUtils.clamp(wantY, 0.8, radius * 0.9) - off.y) * (1 - Math.exp(-dtS * 2.4));
      camera.position.copy(controls.target).add(off);
      if (Math.abs(d) < 0.01) sw.azimuth = null;
    }
    if (mirrorHud) {
      // The compass and pitch readout of the first-person interface follow this camera.
      camera.getWorldDirection(look.current);
      povState.headingDeg = headingFromThree(look.current.x, look.current.z);
      povState.pitchDeg = THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(look.current.y, -1, 1)));
      povState.fovDeg = (camera as THREE.PerspectiveCamera).fov;
    }
  }, FOLLOW_PRIORITY);

  return null;
}
