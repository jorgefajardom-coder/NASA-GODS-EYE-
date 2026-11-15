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
  // The rover's view is drawn from its real cameras (lib/roverCameras, lib/roverRig); these values are only its fallback.
  ROVER: { upM: 2.0, forwardM: 0.6, pitchDeg: -10, fovDeg: 73 },
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
import { aimRequest, shortestTurnDeg } from '../lib/photoAim';
import { CAMERA_ORDER, ROVER_CAMERAS, cameraFovDeg } from '../lib/roverCameras';
import { homeRig, nudgeMast, roverRig, selectCamera, zoomBy } from '../lib/roverRig';

/** The lens sits a little ahead of the node's origin, so the camera is not inside its own housing (m). */
const LENS_AHEAD_M = { mast: 0.14, body: 0.06, arm: 0.1 } as const;
/** Stabilisation of the rover's view (s): a short low-pass on position and direction, so no shake reaches it. */
const ROVER_STAB_TAU_S = 0.15;
/** The view direction is smoothed a little more, so a pivot turn swings the view gently (position never lags). */
const ROVER_DIR_TAU_S = 0.3;
/** On a camera change the view eases to the new camera over CUT_EASE_S, with this time constant (s). */
const CUT_EASE_S = 0.35;
const CUT_TAU_S = 0.09;

export const povState = { headingDeg: 0, pitchDeg: 0, fovDeg: 70, active: false };

/** Heading of a Three.js direction measured clockwise from north (deg, 0..360). */
export function headingFromThree(dx: number, dz: number): number {
  // Three.js -> ENU: east = x, north = -z.
  const deg = THREE.MathUtils.radToDeg(Math.atan2(dx, -dz));
  return (deg + 360) % 360;
}

/** Ground speed (m/s) below which the agent counts as standing still for the sway. */
const STILL_MPS = 0.05;

/**
 * Display-only camera sway from the agent's drawn ground speed, so moving reads as walking or
 * walking: the astronaut's head bobs once per step and rolls slightly, the hovering drone drifts
 * gently; the rover's cameras stay still (they are rigidly mounted). Offsets in metres (up, side) and radians (roll);
 * `phase` advances with the step rate (see swayStepHz). No pose or data is changed.
 */
export function swayOffset(kind: AgentKind, speedMps: number, phase: number, timeS: number): { up: number; side: number; roll: number } {
  const moving = Math.max(0, Math.min(1, (speedMps - STILL_MPS) / 0.4)); // eases in from standstill
  if (kind === 'HUMAN') {
    // Two vertical dips per stride (one per foot), one side-to-side sway per stride.
    return { up: -0.035 * moving * Math.abs(Math.sin(phase)), side: 0.022 * moving * Math.sin(phase), roll: 0.006 * moving * Math.sin(phase) };
  }
  if (kind === 'ROVER') {
    // No shake: the rover's cameras are bolted to its mast, body and arm, and the real rover drives at
    // about 4 cm/s, so nothing in its images trembles. The view is also stabilised (ROVER_STAB_TAU_S).
    return { up: 0, side: 0, roll: 0 };
  }
  // Drone: a slow hover drift even when still, a little stronger in flight.
  const k = 0.4 + 0.6 * moving;
  return { up: 0.04 * k * Math.sin(timeS * 1.3), side: 0.03 * k * Math.sin(timeS * 0.9 + 1), roll: 0.004 * k * Math.sin(timeS * 1.1) };
}

/** Strides per second at a ground speed (Hz): about one per second at a 1 m/s walk. */
export function swayStepHz(speedMps: number): number {
  return speedMps < STILL_MPS ? 0 : Math.min(1.6, 0.55 + 0.5 * speedMps);
}

interface Props {
  /** Scene name of the followed agent group, or null when the view is off. */
  target: string | null;
  kind: AgentKind | null;
  /** Walking/driving sway of the camera (display only; off with reduced motion by default). */
  sway: boolean;
  /** Low-power rendering: keep pixel ratio 1 instead of supersampling. */
  lite?: boolean;
}

/**
 * First-person view from the followed agent: the camera sits at its eye (astronaut helmet, rover
 * mast, drone camera) and looks along its heading; dragging looks around, the wheel zooms the lens,
 * double-click recentres. The agent's own model is hidden while seen from inside. Only the camera
 * moves; no pose or data is changed. The orbit controls are disabled meanwhile (MissionScene).
 */
export function FirstPersonCamera({ target, kind, sway, lite = false }: Props) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const scene = useThree((s) => s.scene);
  const gl = useThree((s) => s.gl);
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null;
  const setDpr = useThree((s) => s.setDpr);
  const look = useRef({ yaw: 0, pitch: 0, fov: 0 });
  const motion = useRef<{ last: THREE.Vector3 | null; speed: number; phase: number; time: number }>({ last: null, speed: 0, phase: 0, time: 0 });
  const right = useRef(new THREE.Vector3());
  const hidden = useRef<THREE.Object3D | null>(null);
  const saved = useRef<{ offset: THREE.Vector3; fov: number } | null>(null);
  const world = useRef(new THREE.Vector3());
  const fwd = useRef(new THREE.Vector3());
  const aim = useRef(new THREE.Vector3());
  // A request to turn towards where a photo was taken (lib/photoAim): eased in, cancelled by a drag.
  const turn = useRef<{ seen: number; yaw: number | null; pitch: number | null }>({ seen: aimRequest.token, yaw: null, pitch: null });
  // The rover's view: last camera cut seen, and the stabilised eye and direction.
  const rov = useRef({ cut: -1, ease: 0, base: new THREE.Vector3(), rel: new THREE.Vector3(), tmp: new THREE.Vector3(), eye: new THREE.Vector3(), dir: new THREE.Vector3(), pos: new THREE.Vector3(), d: new THREE.Vector3(), q: new THREE.Quaternion(), side: new THREE.Vector3() });

  // Enter / leave: remember the third-person offset and the lens, restore them on exit.
  useEffect(() => {
    if (!target || !kind) return;
    const eye = EYE[kind];
    look.current = { yaw: 0, pitch: eye.pitchDeg, fov: eye.fovDeg };
    rov.current.cut = -1;
    motion.current = { last: null, speed: 0, phase: 0, time: 0 };
    saved.current = { offset: controls ? camera.position.clone().sub(controls.target) : new THREE.Vector3(-6, 2.6, 0), fov: camera.fov };
    povState.active = true;
    // Highest quality while seen from the ground: supersample the frame (capped for the GPU).
    const device = window.devicePixelRatio || 1;
    setDpr(lite ? 1 : Math.min(POV_DPR_MAX, device * POV_DPR_SCALE));
    return () => {
      povState.active = false;
      setDpr(lite ? 1 : Math.min(MAP_DPR_MAX, Math.max(1, device)));
      if (hidden.current) {
        hidden.current.visible = true;
        const ring = hidden.current.getObjectByName('selection-ring');
        if (ring) ring.visible = true;
      }
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
  }, [target, kind, camera, controls, setDpr, lite]);

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
      turn.current.yaw = null; // the person takes over the view
      const l = look.current;
      if (kind === 'ROVER') {
        // Dragging aims the mast head (it slews at its own rate); body cameras and WATSON cannot be aimed.
        const k = LOOK_DEG_PER_PX * (cameraFovDeg(ROVER_CAMERAS[roverRig.view], roverRig.focalMm) / EYE.ROVER.fovDeg);
        nudgeMast(roverRig, (e.clientX - drag.x) * k, -(e.clientY - drag.y) * k);
        drag = { x: e.clientX, y: e.clientY };
        return;
      }
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
      // The rover zooms only with Mastcam-Z (26-110 mm, at its motor's speed); Navcam and Hazcam have fixed lenses.
      if (kind === 'ROVER') {
        zoomBy(roverRig, Math.exp(-e.deltaY * 0.001));
        return;
      }
      l.fov = THREE.MathUtils.clamp(l.fov * Math.exp(e.deltaY * 0.001), FOV_MIN_DEG, FOV_MAX_DEG);
    };
    const reset = () => {
      if (kind === 'ROVER') homeRig(roverRig);
      else look.current = { yaw: 0, pitch: EYE[kind].pitchDeg, fov: EYE[kind].fovDeg };
    };
    // Rover: keys 1-5 pick its camera (Navcam, Mastcam-Z, front Hazcam, rear Hazcam, WATSON on the arm).
    const key = (e: KeyboardEvent) => {
      if (kind !== 'ROVER' || e.ctrlKey || e.metaKey || e.altKey) return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      const n = Number(e.key);
      if (n >= 1 && n <= CAMERA_ORDER.length) selectCamera(roverRig, CAMERA_ORDER[n - 1]);
    };
    window.addEventListener('keydown', key);
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
      window.removeEventListener('keydown', key);
    };
  }, [target, kind, gl]);

  /**
   * The rover's own view: the camera in use (roverRig.view) seen from its node on the model, the left
   * or right eye of its stereo pair, pointing where the mast head, the body or the arm's turret points.
   * A camera change is a cut; otherwise position and direction pass a short low-pass so no jitter of the
   * drawn pose or terrain tilt reaches the image. Returns false when the model has no such node.
   */
  const roverView = (obj: THREE.Object3D, dt: number): boolean => {
    const cam = ROVER_CAMERAS[roverRig.view];
    const node = obj.getObjectByName(cam.node);
    const head = obj.getObjectByName('head');
    // The rover body frame (the model root, parent of the head): body cameras and the arm's pointing are given in it.
    const body = head?.parent ?? node?.parent ?? null;
    if (!node || !body || (cam.mount === 'mast' && !head)) return false;
    const r = rov.current;
    node.getWorldPosition(r.pos);
    (cam.mount === 'mast' ? head! : body).getWorldQuaternion(r.q);
    // Direction in the model frame (front +z, up +y, left +x), then to the world.
    if (cam.mount === 'mast') r.d.set(0, 0, 1);
    else if (cam.mount === 'body') {
      const az = THREE.MathUtils.degToRad(cam.boresight?.azDeg ?? 0);
      const el = THREE.MathUtils.degToRad(cam.boresight?.elDeg ?? 0);
      r.d.set(-Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el));
    } else {
      const v = roverRig.watsonVector; // rover frame: x forward, y right, z down
      if (v) r.d.set(-v[1], -v[2], v[0]);
      else r.d.set(0, -1, 0.15);
    }
    r.d.normalize().applyQuaternion(r.q);
    // Eye of the stereo pair: half the baseline to the left (+x of the frame) or to the right.
    if (cam.baselineM) {
      r.side.set(1, 0, 0).applyQuaternion(r.q);
      r.pos.addScaledVector(r.side, (roverRig.side === 'left' ? 0.5 : -0.5) * cam.baselineM);
    }
    r.pos.addScaledVector(r.d, LENS_AHEAD_M[cam.mount]);
    const fov = cameraFovDeg(cam, roverRig.focalMm);
    // Entering the rover's view starts on the camera; a later camera change eases there quickly instead of
    // jumping (the photo tour switches between Navcam, Mastcam-Z and the Hazcams), then the usual stabiliser.
    let k = 1;
    let kDir = 1;
    if (r.cut !== roverRig.cut) {
      if (r.cut !== -1) r.ease = CUT_EASE_S;
      r.cut = roverRig.cut;
    }
    if (r.cut !== -1) {
      k = 1 - Math.exp(-dt / (r.ease > 0 ? CUT_TAU_S : ROVER_STAB_TAU_S));
      kDir = r.ease > 0 ? k : 1 - Math.exp(-dt / ROVER_DIR_TAU_S);
      r.ease = Math.max(0, r.ease - dt);
    }
    // The eye is smoothed relative to the rover, never in the world: a world lag fell behind a rover driving at
    // replay speed and put the camera inside its body for a moment.
    obj.getWorldPosition(r.base);
    r.tmp.copy(r.pos).sub(r.base);
    if (k >= 1) {
      r.rel.copy(r.tmp);
      r.dir.copy(r.d);
    } else {
      r.rel.lerp(r.tmp, k);
      r.dir.lerp(r.d, kDir).normalize();
    }
    r.eye.copy(r.base).add(r.rel);
    camera.position.copy(r.eye);
    camera.up.set(0, 1, 0);
    camera.lookAt(aim.current.copy(r.eye).add(r.dir));
    // The lens changes with the same easing, so a switch from a wide Hazcam to a zoomed Mastcam-Z does not jump.
    if (Math.abs(camera.fov - fov) > 0.01) {
      camera.fov = k >= 1 || Math.abs(camera.fov - fov) < 0.05 ? fov : camera.fov + (fov - camera.fov) * k;
      camera.updateProjectionMatrix();
    }
    povState.headingDeg = headingFromThree(r.dir.x, r.dir.z);
    povState.pitchDeg = THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(r.dir.y, -1, 1)));
    povState.fovDeg = fov;
    return true;
  };

  // After the poses (-2) and the follow camera (same priority, mounted before this one).
  useFrame((_, dtRaw) => {
    if (!target || !kind) return;
    const obj = scene.getObjectByName(target);
    if (!obj) return;
    const dt = Math.min(Math.max(dtRaw, 1e-4), 0.1);
    if (hidden.current !== obj) {
      if (hidden.current) hidden.current.visible = true;
      hidden.current = obj;
    }
    // The rover's camera sees parts of the rover (deck, arm, wheels), as the real photos do; the others hide their own model.
    obj.visible = kind === 'ROVER';
    // ...but not its selection ring, a map marker that would fill the bottom of its own camera's image.
    const ring = obj.getObjectByName('selection-ring');
    if (ring) ring.visible = false;
    if (kind === 'ROVER' && roverView(obj, dt)) return;
    const eye = EYE[kind];
    const l = look.current;
    obj.getWorldPosition(world.current);
    const heading = obj.rotation.y; // model faces +x; yaw about +y
    fwd.current.set(Math.cos(heading), 0, -Math.sin(heading));
    camera.position.copy(world.current).addScaledVector(fwd.current, eye.forwardM);
    camera.position.y += eye.upM;
    // Ground speed of the drawn agent (smoothed), for the sway.
    const m = motion.current;
    if (m.last) {
      const v = Math.hypot(world.current.x - m.last.x, world.current.z - m.last.z) / dt;
      m.speed += (Math.min(v, 30) - m.speed) * Math.min(1, dt * 4);
    } else m.last = new THREE.Vector3();
    m.last.copy(world.current);
    m.time += dt;
    m.phase += dt * Math.PI * 2 * swayStepHz(m.speed);
    const s = sway ? swayOffset(kind, m.speed, m.phase, m.time) : { up: 0, side: 0, roll: 0 };
    right.current.set(Math.sin(heading), 0, Math.cos(heading)); // to the agent's right
    camera.position.y += s.up;
    camera.position.addScaledVector(right.current, s.side);
    // Turn towards the last photo direction asked for (compass azimuth -> yaw relative to the agent).
    const tr = turn.current;
    if (aimRequest.token !== tr.seen) {
      tr.seen = aimRequest.token;
      tr.yaw = aimRequest.azimuthDeg;
      tr.pitch = aimRequest.pitchDeg;
    }
    // Eased and limited in speed (about 55 deg/s): the turn starts and ends gently.
    const k = 1 - Math.exp(-dt * 2.4);
    if (tr.yaw != null) {
      const headingNorthDeg = (90 - THREE.MathUtils.radToDeg(heading) + 720) % 360; // the agent's compass heading
      const dYaw = shortestTurnDeg(headingNorthDeg + -l.yaw, tr.yaw); // look.yaw grows to the left, compass to the right
      l.yaw -= THREE.MathUtils.clamp(dYaw * k, -55 * dt, 55 * dt);
      if (Math.abs(dYaw) < 0.3) tr.yaw = null;
    }
    if (tr.pitch != null) {
      l.pitch += (THREE.MathUtils.clamp(tr.pitch, PITCH_MIN_DEG, PITCH_MAX_DEG) - l.pitch) * k;
      if (Math.abs(tr.pitch - l.pitch) < 0.3) tr.pitch = null;
    }
    const yaw = heading + THREE.MathUtils.degToRad(l.yaw);
    const pitch = THREE.MathUtils.degToRad(l.pitch);
    aim.current.set(Math.cos(yaw) * Math.cos(pitch), Math.sin(pitch), -Math.sin(yaw) * Math.cos(pitch));
    camera.lookAt(aim.current.add(camera.position));
    if (s.roll) camera.rotateZ(s.roll);
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
