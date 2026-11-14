import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

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

/** Over-the-shoulder view of an agent. */
export const AGENT_FRAMING: Framing = { distanceM: 6, heightM: 2.6, lookAtM: 1.25 };

interface Props {
  /** Name of the scene object to follow (an agent group or the base anchor), or null for the free camera. */
  target: string | null;
  framing?: Framing;
}


/**
 * Third-person follow view. It reads the drawn (already eased) agent group from the
 * scene every frame, so the camera and the agent move in the same render step and the
 * agent stays steady on screen at any zoom. It only moves the camera and the orbit
 * target; the agent pose is never changed. The user can still orbit and zoom.
 */
export function FollowCamera({ target, framing = AGENT_FRAMING }: Props) {
  const camera = useThree((s) => s.camera);
  const scene = useThree((s) => s.scene);
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null;
  const home = useRef<{ pos: THREE.Vector3; target: THREE.Vector3 } | null>(null);
  const following = useRef<string | null>(null);
  const world = useRef(new THREE.Vector3());
  const goal = useRef(new THREE.Vector3());
  const delta = useRef(new THREE.Vector3());

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

  useFrame(() => {
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
  }, FOLLOW_PRIORITY);

  return null;
}
