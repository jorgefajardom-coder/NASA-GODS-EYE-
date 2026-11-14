import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

/** Window event that asks the 3D view to turn about its vertical axis; detail = angle in radians (+ = counter-clockwise seen from above). */
export const ROTATE_VIEW_EVENT = 'mge:rotate-view';
/** Step of the rotate buttons and keys. */
export const ROTATE_STEP_RAD = Math.PI / 4;
/** Duration of one eased turn (s). */
const TURN_S = 0.45;

/** Asks the 3D view to turn by `angle` radians about the vertical through its centre. */
export function rotateView(angle: number) {
  window.dispatchEvent(new CustomEvent<number>(ROTATE_VIEW_EVENT, { detail: angle }));
}

/**
 * Turns the camera about the vertical axis through the orbit target, eased, when asked through
 * ROTATE_VIEW_EVENT (rotate buttons, Q/E keys). Works in every camera mode: the follow cameras
 * keep their target and only the viewing direction turns. Display only.
 */
export function ViewRotator() {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null;
  const pending = useRef(0); // angle still to turn
  const offset = useRef(new THREE.Vector3());
  const up = useRef(new THREE.Vector3(0, 1, 0));

  useEffect(() => {
    const on = (e: Event) => {
      pending.current += (e as CustomEvent<number>).detail;
    };
    window.addEventListener(ROTATE_VIEW_EVENT, on);
    return () => window.removeEventListener(ROTATE_VIEW_EVENT, on);
  }, []);

  useFrame((_, dt) => {
    if (!controls || Math.abs(pending.current) < 1e-4) return;
    // Exponential ease: most of the turn early, settling smoothly.
    const k = 1 - Math.exp(-Math.min(dt, 0.1) / (TURN_S / 4));
    const step = Math.abs(pending.current) < 1e-3 ? pending.current : pending.current * k;
    pending.current -= step;
    offset.current.copy(camera.position).sub(controls.target).applyAxisAngle(up.current, step);
    camera.position.copy(controls.target).add(offset.current);
    camera.lookAt(controls.target);
    controls.update();
  }, -1);

  return null;
}
