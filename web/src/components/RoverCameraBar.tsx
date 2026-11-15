import { useEffect, useRef, useState } from 'react';
import { CAMERA_ORDER, ROVER_CAMERAS, focusText, mastcamNearFocusM, type RoverCameraId } from '../lib/roverCameras';
import { ARM_MOVE_S, homeRig, requestShot, roverRig, selectCamera, shotReady } from '../lib/roverRig';

/** How long the arm close-up stays on WATSON before the rover stows the arm again (ms). */
const CLOSE_UP_HOLD_MS = 5000;

interface Snapshot {
  view: RoverCameraId;
  asked: RoverCameraId;
  side: 'left' | 'right';
  focal: number;
  az: number;
  el: number;
  arm: number;
}

const snap = (): Snapshot => ({ view: roverRig.view, asked: roverRig.camera, side: roverRig.side, focal: roverRig.focalMm, az: roverRig.az, el: roverRig.el, arm: roverRig.arm });

/**
 * The rover's camera keys in the first-person dock (numbered 1-5, the camera's name in the readout and
 * tooltip) and the arm close-up button: the rover
 * deploys its arm, looks through WATSON at the ground ahead, then stows the arm and returns to the
 * Navcam by itself. The arm only works while the rover stands still. Readout: camera, eye of the stereo
 * pair, focal length, sharp range and mast pointing. Display only; nothing reaches the mission.
 */
export function RoverCameraBar({ stationary }: { stationary: boolean }) {
  const [s, setS] = useState<Snapshot>(snap);
  const [closeUp, setCloseUp] = useState<'idle' | 'deploying' | 'imaging' | 'stowing'>('idle');
  const timers = useRef<number[]>([]);

  // Read the shared rig a few times a second (it changes every frame; no re-render per frame).
  useEffect(() => {
    const id = window.setInterval(() => setS(snap()), 150);
    return () => window.clearInterval(id);
  }, []);
  useEffect(() => () => timers.current.forEach((t) => window.clearInterval(t)), []);

  const after = (done: () => boolean, then: () => void) => {
    const id = window.setInterval(() => {
      if (!done()) return;
      window.clearInterval(id);
      then();
    }, 100);
    timers.current.push(id);
  };
  const armCloseUp = () => {
    if (!stationary || closeUp !== 'idle') return;
    setCloseUp('deploying');
    const token = requestShot(roverRig, { camera: 'watson', watsonVector: null });
    after(() => shotReady(roverRig, token) || roverRig.armTarget === 0, () => {
      if (roverRig.armTarget === 0) return setCloseUp('idle'); // the rover drove off
      setCloseUp('imaging');
      const hold = window.setTimeout(() => {
        setCloseUp('stowing');
        homeRig(roverRig);
        after(() => roverRig.arm === 0, () => setCloseUp('idle'));
      }, CLOSE_UP_HOLD_MS);
      timers.current.push(hold);
    });
  };

  const cam = ROVER_CAMERAS[s.view];
  const near = cam.id === 'mastcamz' ? mastcamNearFocusM(s.focal) : cam.focusM.nearM;
  const lens = cam.id === 'mastcamz' ? `${s.focal.toFixed(0)} mm zoom` : cam.focalMm ? `${cam.focalMm[0]} mm fixed` : cam.id === 'watson' ? 'focusable close-up lens' : 'fixed fisheye';
  const eye = cam.baselineM ? `${s.side} eye of the pair (${(cam.baselineM * 100).toFixed(1)} cm apart)` : 'single camera';
  const aim = cam.mount === 'mast' ? `mast az ${s.az.toFixed(0)}°, el ${s.el.toFixed(0)}°` : cam.mount === 'body' ? 'fixed to the body' : 'on the arm turret';
  const armText = closeUp === 'deploying' ? `deploying the arm (${Math.round(s.arm * 100)}%)` : closeUp === 'imaging' ? 'WATSON close-up' : closeUp === 'stowing' ? `stowing the arm (${Math.round((1 - s.arm) * 100)}%)` : null;

  return (
    <div className="rovercam" role="group" aria-label="Rover cameras">
      <div className="rovercam__keys">
        {CAMERA_ORDER.map((id, i) => {
          const c = ROVER_CAMERAS[id];
          const armNeeded = id === 'watson' && !stationary && s.arm < 1;
          return (
            <button
              key={id}
              type="button"
              className="rovercam__key rovercam__key--num"
              aria-label={`${i + 1}: ${c.label}`}
              aria-pressed={s.asked === id}
              disabled={armNeeded || closeUp !== 'idle'}
              onClick={() => selectCamera(roverRig, id)}
              title={`${c.label} (${i + 1}): ${c.hFovDeg} × ${c.vFovDeg}° , sharp ${focusText(c.focusM.nearM, c.focusM.farM)}${c.mount === 'body' ? ', fixed to the body' : c.mount === 'arm' ? ', deploys the arm (rover stopped)' : ', on the mast head'}`}
            >
              {i + 1}
            </button>
          );
        })}
        <button
          type="button"
          className="rovercam__key rovercam__key--arm"
          onClick={armCloseUp}
          disabled={!stationary || closeUp !== 'idle'}
          title={stationary ? `The rover deploys its arm (${ARM_MOVE_S} s here; minutes on Mars), takes a WATSON close-up of the ground ahead and stows the arm` : 'The arm works only while the rover stands still'}
        >
          Arm close-up
        </button>
      </div>
      <p className="rovercam__read mono" aria-live="polite">
        <strong>{cam.label}</strong> · {lens} · sharp {focusText(near, cam.focusM.farM)} · {eye} · {aim}
        {armText && <> · <span className="rovercam__arm">{armText}</span></>}
        {s.asked !== s.view && s.asked === 'watson' && !armText && <> · waiting for the arm</>}
      </p>
    </div>
  );
}
