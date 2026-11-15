import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import type { AgentKind } from '../types/icd';
import { FOLLOW_PRIORITY } from './FollowCamera';

/**
 * Where the eye sits on each agent (m above the drawn pose, and forward along the heading), the
 * default downward look (deg) and the field of view (deg). Display choices, not instrument specs:
 * the drone view is a forward camera pitched down, the rover view sits at mast height.
 */
export const EYE: Record<AgentKind, { upM: number; forwardM: number; pitchDeg: number; fovDeg: number }> = {
  HUMAN: { upM: 1.62, forwardM: 0.25, pitchDeg: -6, fovDeg: 82 },
  ROVER: { upM: 2.0, forwardM: 0.6, pitchDeg: -10, fovDeg: 78 },
  DRONE: { upM: -0.12, forwardM: 0.15, pitchDeg: -28, fovDeg: 90 },
};

/** Look limits relative to the default pitch (deg), and the zoom range of the wheel (fov, deg). */
const PITCH_MIN_DEG = -80;
const PITCH_MAX_DEG = 45;
const FOV_MIN_DEG = 18;
const FOV_MAX_DEG = 110;
/** Render scale in first person: supersampled for the sharpest image the device allows (capped). */
const POV_DPR_SCALE = 1.5;
const POV_DPR_MAX = 3;
/** Upper pixel ratio of the map views (the Canvas dpr prop in MissionScene). */
const MAP_DPR_MAX = 1.75;
const LOOK_DEG_PER_PX = 0.18;

/** Live camera heading and pitch, read by the HUD outside React (no re-render per frame). */
export const povState = { headingDeg: 0, pitchDeg: 0, fovDeg: 70, active: false };

/** Heading of a Three.js direction measured clockwise from north (deg, 0..360). */
export function headingFromThree(dx: number, dz: number): number {
  // Three.js -> ENU: east = x, north = -z.
  const deg = THREE.MathUtils.radToDeg(Math.atan2(dx, -dz));
  return (deg + 360) % 360;
}

interface Props {
  /** Scene name of the followed agent group, or null when the view is off. */
  target: string | null;
  kind: AgentKind | null;
}

/**
 * First-person view from the followed agent: the camera sits at its eye (astronaut helmet, rover
 * mast, drone camera) and looks along its heading; dragging looks around, the wheel zooms the lens,
 * double-click recentres. The agent's own model is hidden while seen from inside. Only the camera
 * moves; no pose or data is changed. The orbit controls are disabled meanwhile (MissionScene).
 */
export function FirstPersonCamera({ target, kind }: Props) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const scene = useThree((s) => s.scene);
  const gl = useThree((s) => s.gl);
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null;
  const setDpr = useThree((s) => s.setDpr);
  const look = useRef({ yaw: 0, pitch: 0, fov: 0 });
  const hidden = useRef<THREE.Object3D | null>(null);
  const saved = useRef<{ offset: THREE.Vector3; fov: number } | null>(null);
  const world = useRef(new THREE.Vector3());
  const fwd = useRef(new THREE.Vector3());
  const aim = useRef(new THREE.Vector3());

  // Enter / leave: remember the third-person offset and the lens, restore them on exit.
  useEffect(() => {
    if (!target || !kind) return;
    const eye = EYE[kind];
    look.current = { yaw: 0, pitch: eye.pitchDeg, fov: eye.fovDeg };
    saved.current = { offset: controls ? camera.position.clone().sub(controls.target) : new THREE.Vector3(-6, 2.6, 0), fov: camera.fov };
    povState.active = true;
    // Highest quality while seen from the ground: supersample the frame (capped for the GPU).
    const device = window.devicePixelRatio || 1;
    setDpr(Math.min(POV_DPR_MAX, device * POV_DPR_SCALE));
    return () => {
      povState.active = false;
      setDpr(Math.min(MAP_DPR_MAX, Math.max(1, device)));
      if (hidden.current) hidden.current.visible = true;
      hidden.current = null;
      const s = saved.current;
      if (s) {
        if (controls) {
          camera.position.copy(controls.target).add(s.offset);
          controls.update();
        }
        camera.fov = s.fov;
        camera.updateProjectionMatrix();
      }
    };
  }, [target, kind, camera, controls, setDpr]);

  // Drag to look, wheel to zoom, double-click to recentre.
  useEffect(() => {
    if (!target || !kind) return;
    const el = gl.domElement;
    let drag: { x: number; y: number } | null = null;
    const down = (e: PointerEvent) => {
      drag = { x: e.clientX, y: e.clientY };
      el.setPointerCapture(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (!drag) return;
      const l = look.current;
      const k = LOOK_DEG_PER_PX * (l.fov / EYE[kind].fovDeg);
      l.yaw -= (e.clientX - drag.x) * k;
      l.pitch = THREE.MathUtils.clamp(l.pitch - (e.clientY - drag.y) * k, PITCH_MIN_DEG, PITCH_MAX_DEG);
      drag = { x: e.clientX, y: e.clientY };
    };
    const up = (e: PointerEvent) => {
      drag = null;
      if (el.hasPointerCapture(e.pointerId)) el.releasePointerCapture(e.pointerId);
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const l = look.current;
      l.fov = THREE.MathUtils.clamp(l.fov * Math.exp(e.deltaY * 0.001), FOV_MIN_DEG, FOV_MAX_DEG);
    };
    const reset = () => {
      look.current = { yaw: 0, pitch: EYE[kind].pitchDeg, fov: EYE[kind].fovDeg };
    };
    el.addEventListener('pointerdown', down);
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
    el.addEventListener('wheel', wheel, { passive: false });
    el.addEventListener('dblclick', reset);
    return () => {
      el.removeEventListener('pointerdown', down);
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', up);
      el.removeEventListener('pointercancel', up);
      el.removeEventListener('wheel', wheel);
      el.removeEventListener('dblclick', reset);
    };
  }, [target, kind, gl]);

  // After the poses (-2) and the follow camera (same priority, mounted before this one).
  useFrame(() => {
    if (!target || !kind) return;
    const obj = scene.getObjectByName(target);
    if (!obj) return;
    if (hidden.current !== obj) {
      if (hidden.current) hidden.current.visible = true;
      hidden.current = obj;
    }
    obj.visible = false;
    const eye = EYE[kind];
    const l = look.current;
    obj.getWorldPosition(world.current);
    const heading = obj.rotation.y; // model faces +x; yaw about +y
    fwd.current.set(Math.cos(heading), 0, -Math.sin(heading));
    camera.position.copy(world.current).addScaledVector(fwd.current, eye.forwardM);
    camera.position.y += eye.upM;
    const yaw = heading + THREE.MathUtils.degToRad(l.yaw);
    const pitch = THREE.MathUtils.degToRad(l.pitch);
    aim.current.set(Math.cos(yaw) * Math.cos(pitch), Math.sin(pitch), -Math.sin(yaw) * Math.cos(pitch));
    camera.lookAt(aim.current.add(camera.position));
    if (Math.abs(camera.fov - l.fov) > 0.01) {
      camera.fov = l.fov;
      camera.updateProjectionMatrix();
    }
    camera.getWorldDirection(aim.current);
    povState.headingDeg = headingFromThree(aim.current.x, aim.current.z);
    povState.pitchDeg = l.pitch;
    povState.fovDeg = l.fov;
  }, FOLLOW_PRIORITY);

  return null;
}
