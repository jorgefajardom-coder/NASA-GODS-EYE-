import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { dampFactor } from '../lib/smoothing';

interface Props {
  /** Agent to follow, or null to leave the camera free. */
  agentId: string | null;
  /** Follow time constant, s (0 = the camera is locked to the agent). */
  smoothingS: number;
}

const DISTANCE_M = 16;
const HEIGHT_M = 7;
const LOOK_AT_HEIGHT_M = 2.6;

/**
 * Third-person follow view. It reads the drawn (already eased) agent group from the
 * scene every frame, so the camera and the agent move in the same render step and the
 * agent stays steady on screen at any zoom. It only moves the camera and the orbit
 * target; the agent pose is never changed. The user can still orbit and zoom.
 */
export function FollowCamera({ agentId, smoothingS }: Props) {
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
    if (!agentId && following.current && home.current) {
      camera.position.copy(home.current.pos);
      controls.target.copy(home.current.target);
      controls.minDistance = 30;
      controls.update();
      following.current = null;
    }
  }, [agentId, controls, camera]);

  // Default priority: runs after the agent groups were eased (priority -2) in the same frame.
  useFrame((_, dt) => {
    if (!agentId || !controls) return;
    const obj = scene.getObjectByName(`agent-${agentId}`);
    if (!obj) return;
    obj.getWorldPosition(world.current);
    goal.current.set(world.current.x, world.current.y + LOOK_AT_HEIGHT_M, world.current.z);

    if (following.current !== agentId) {
      // Entering: remember the orbital view and place the camera behind the agent's shoulder.
      if (!following.current) home.current = { pos: camera.position.clone(), target: controls.target.clone() };
      const yaw = obj.rotation.y;
      controls.target.copy(goal.current);
      camera.position.set(world.current.x - Math.cos(yaw) * DISTANCE_M, world.current.y + HEIGHT_M, world.current.z + Math.sin(yaw) * DISTANCE_M);
      controls.minDistance = 6;
      controls.update();
      following.current = agentId;
      return;
    }
    // Move camera and orbit target together so the user's chosen angle and zoom are kept.
    delta.current.copy(goal.current).sub(controls.target).multiplyScalar(dampFactor(dt, smoothingS));
    controls.target.add(delta.current);
    camera.position.add(delta.current);
  });

  return null;
}
