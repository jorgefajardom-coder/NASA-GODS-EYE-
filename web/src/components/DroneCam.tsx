import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useState } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import { DroneMap } from './DroneMap';
import * as THREE from 'three';

/**
 * Drone camera window: a second view of the same scene, rendered from under the drone and looking
 * ahead along its heading, pitched down, so the ground it is flying over is visible at all times.
 * It shows the replayed pose (REPLAY, simulated), not a live video feed. Display only.
 *
 * The DOM frame (DroneCamFrame) marks where the window sits; the renderer (DroneCamRenderer, inside
 * the Canvas) draws the scene a second time into that rectangle with a scissored viewport.
 */
export const DRONE_CAM = { upM: 0.3, forwardM: 0.4, pitchDeg: -35, fovDeg: 72 };

/** The DOM element marking the window; null when the window is closed. */
export const droneCamSlot: { el: HTMLElement | null } = { el: null };

/** Pose of the drone camera from the drone's world position and heading (Three.js yaw about +y; model faces +x). */
export function droneCamPose(pos: { x: number; y: number; z: number }, heading: number) {
  const fx = Math.cos(heading);
  const fz = -Math.sin(heading);
  const p = DRONE_CAM.pitchDeg * (Math.PI / 180);
  const eye = { x: pos.x + fx * DRONE_CAM.forwardM, y: pos.y + DRONE_CAM.upM, z: pos.z + fz * DRONE_CAM.forwardM };
  const dir = { x: fx * Math.cos(p), y: Math.sin(p), z: fz * Math.cos(p) };
  return { eye, dir };
}

/** Lowest priority frame callback: renders the main view, then the drone window over it. */
const RENDER_PRIORITY = 1;

export function DroneCamRenderer({ droneName }: { droneName: string | null }) {
  const gl = useThree((s) => s.gl);
  const scene = useThree((s) => s.scene);
  const mainCamera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const cam = useMemo(() => new THREE.PerspectiveCamera(DRONE_CAM.fovDeg, 16 / 9, 0.3, 20000), []);
  const world = useMemo(() => new THREE.Vector3(), []);
  const target = useMemo(() => new THREE.Vector3(), []);

  // A positive priority takes over rendering from react-three-fiber, so the main view is drawn here too.
  useFrame(({ size }) => {
    gl.render(scene, mainCamera);
    const el = droneCamSlot.el;
    const drone = droneName ? scene.getObjectByName(droneName) : null;
    if (!el || !drone) return;
    const r = el.getBoundingClientRect();
    const c = gl.domElement.getBoundingClientRect();
    const w = Math.round(r.width);
    const h = Math.round(r.height);
    if (w < 8 || h < 8) return;
    const x = Math.round(r.left - c.left);
    const y = Math.round(c.bottom - r.bottom); // WebGL origin is bottom-left
    drone.getWorldPosition(world);
    const { eye, dir } = droneCamPose(world, drone.rotation.y);
    cam.position.set(eye.x, eye.y, eye.z);
    cam.lookAt(target.set(eye.x + dir.x, eye.y + dir.y, eye.z + dir.z));
    if (Math.abs(cam.aspect - w / h) > 1e-3 || cam.far !== mainCamera.far) {
      cam.aspect = w / h;
      cam.far = mainCamera.far;
      cam.updateProjectionMatrix();
    }
    const wasVisible = drone.visible;
    drone.visible = false; // the camera sits under the body
    gl.setViewport(x, y, w, h);
    gl.setScissor(x, y, w, h);
    gl.setScissorTest(true);
    gl.render(scene, cam);
    gl.setScissorTest(false);
    gl.setViewport(0, 0, size.width, size.height);
    drone.visible = wasVisible;
  }, RENDER_PRIORITY);

  return null;
}

/** Frame of the drone window: CAM (transparent inside, the canvas draws the drone's view) or MAP (the drone's survey map). */
export function DroneCamFrame({ droneId, onClose, className = '', bundle, view }: { droneId: string; onClose: () => void; className?: string; bundle: ReplayBundle; view: ReplayView }) {
  const [tab, setTab] = useState<'cam' | 'map'>('cam');
  // The 3D window is drawn only on the CAM tab; the MAP tab is a 2D canvas.
  useEffect(() => () => void (droneCamSlot.el = null), []);
  return (
    <div
      className={`dronecam dronecam--${tab} ${className}`}
      ref={(el) => {
        droneCamSlot.el = tab === 'cam' ? el : null;
      }}
      role="group"
      aria-label={`Drone window of ${droneId}`}
    >
      {tab === 'map' && <DroneMap bundle={bundle} view={view} droneId={droneId} />}
      <span className="dronecam__label">
        <i aria-hidden /> Drone · {droneId}
      </span>
      <span className="dronecam__tabs" role="tablist" aria-label="Drone window view">
        <button type="button" role="tab" aria-selected={tab === 'cam'} onClick={() => setTab('cam')} title="Drone camera: the replayed flight seen from the drone">
          Cam
        </button>
        <button type="button" role="tab" aria-selected={tab === 'map'} onClick={() => setTab('map')} title="Drone hazard map: steep ground and contradictions of the orbital estimate found in the drone's observations (simulated in the replay, not a LiDAR measurement)">
          Hazards
        </button>
      </span>
      <span className="dronecam__src">{tab === 'cam' ? 'Replay · simulated pose' : 'Hazard report · simulated, not LiDAR'}</span>
      {tab === 'cam' && <span className="dronecam__cross" aria-hidden />}
      <button type="button" className="dronecam__close" onClick={onClose} title="Close the drone window (C)">
        ×
      </button>
    </div>
  );
}
