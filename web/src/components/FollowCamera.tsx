import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

interface Props {
  /** Three.js position of the followed agent, or null to leave the camera free. */
  target: [number, number, number] | null;
  /** Heading of the agent about the Three.js Y axis, radians. */
  yaw: number;
}

const DISTANCE_M = 16;
const HEIGHT_M = 7;
const LOOK_AT_HEIGHT_M = 2.6;

/**
 * Third-person follow view. It only moves the camera and the orbit target;
 * the agent pose is never changed. The user can still orbit and zoom around
 * the followed agent. Turning it off returns control to the free orbital view.
 */
export function FollowCamera({ target, yaw }: Props) {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null;
  const wasFollowing = useRef(false);
  const home = useRef<{ pos: THREE.Vector3; target: THREE.Vector3 } | null>(null);
  const goal = useRef(new THREE.Vector3());

  useEffect(() => {
    if (!controls) return;
    if (target && !wasFollowing.current) {
      // Entering: remember the orbital view and place the camera behind the agent's shoulder.
      home.current = { pos: camera.position.clone(), target: controls.target.clone() };
      const back = new THREE.Vector3(-Math.cos(yaw), 0, Math.sin(yaw)).multiplyScalar(DISTANCE_M);
      controls.target.set(target[0], target[1] + LOOK_AT_HEIGHT_M, target[2]);
      camera.position.set(target[0] + back.x, target[1] + HEIGHT_M, target[2] + back.z);
      controls.minDistance = 6;
      controls.update();
    } else if (!target && wasFollowing.current && home.current) {
      camera.position.copy(home.current.pos);
      controls.target.copy(home.current.target);
      controls.minDistance = 30;
      controls.update();
    }
    wasFollowing.current = !!target;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [!!target, controls]);

  useFrame((_, dt) => {
    if (!target || !controls) return;
    // Move camera and orbit target together so the user's chosen angle and zoom are kept.
    goal.current.set(target[0], target[1] + LOOK_AT_HEIGHT_M, target[2]);
    const delta = goal.current.clone().sub(controls.target).multiplyScalar(1 - Math.exp(-8 * dt));
    controls.target.add(delta);
    camera.position.add(delta);
  });

  return null;
}
