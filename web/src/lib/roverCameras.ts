/**
 * The real Perseverance cameras the rover's view is limited to (display only). Field of view and
 * mounting come from NASA/JPL sources; the eye positions are display choices, not measurements.
 *
 * - Navcam: mast-mounted stereo pair, 96 x 73 deg field of view, fixed focal length (19.2 mm), 360 deg
 *   panoramas. https://an.rsl.wustl.edu/help/Content/About%20the%20mission/M20/Instruments/M20%20ECAM.htm
 * - Mastcam-Z: on the mast under the Navcams, 4:1 zoom from 25.6 x 19.2 deg (26 mm) to 6.2 x 4.6 deg
 *   (110 mm). Bell et al. 2021, Space Science Reviews 217, 24, https://doi.org/10.1007/s11214-020-00755-x
 * - Hazcam: fisheye cameras fixed to the front and rear ends of the rover body, 136 x 102 deg, near field
 *   under 5 m. Same WashU page as the Navcam.
 *
 * The viewer's lens is vertical, so the vertical field of view is used (73, 19.2 to 4.6, 102 deg).
 * No fisheye distortion is modelled.
 */
export type RoverCameraId = 'navcam' | 'mastcamz' | 'hazcam';
export type CameraMount = 'mast' | 'front' | 'rear';

export interface RoverCamera {
  id: RoverCameraId;
  label: string;
  /** Vertical and horizontal field of view (deg) at the widest setting. */
  vFovDeg: number;
  hFovDeg: number;
  /** Narrowest vertical field of view (deg): only the zoom of Mastcam-Z changes it. */
  minVFovDeg: number;
  /** Mast cameras pan and tilt with the mast; the Hazcams are fixed to the body. */
  mount: 'mast' | 'body';
}

export const ROVER_CAMERAS: Record<RoverCameraId, RoverCamera> = {
  navcam: { id: 'navcam', label: 'Navcam', vFovDeg: 73, hFovDeg: 96, minVFovDeg: 73, mount: 'mast' },
  mastcamz: { id: 'mastcamz', label: 'Mastcam-Z', vFovDeg: 19.2, hFovDeg: 25.6, minVFovDeg: 4.6, mount: 'mast' },
  hazcam: { id: 'hazcam', label: 'Hazcam', vFovDeg: 102, hFovDeg: 136, minVFovDeg: 102, mount: 'body' },
};

/** The rover's own view when no photo is being taken: its Navcam. */
export const DEFAULT_ROVER_CAMERA = ROVER_CAMERAS.navcam;
/** Widest and narrowest vertical field of view any real camera of the rover gives. */
export const ROVER_FOV_RANGE_DEG = { min: ROVER_CAMERAS.mastcamz.minVFovDeg, max: ROVER_CAMERAS.hazcam.vFovDeg };

/**
 * Which real camera took a photo, from the feed's instrument name. Only Perseverance's cameras are
 * described (Curiosity's specifications were not checked here): null for anything else.
 */
export function roverCameraOf(instrument: string, mission = 'Perseverance'): RoverCamera | null {
  if (mission !== 'Perseverance') return null;
  if (/NAVCAM/i.test(instrument)) return ROVER_CAMERAS.navcam;
  if (/^MCZ|MASTCAM/i.test(instrument)) return ROVER_CAMERAS.mastcamz;
  if (/HAZCAM/i.test(instrument)) return ROVER_CAMERAS.hazcam;
  return null;
}

/** Where a body camera sits: the Hazcams are at the front or the rear end of the rover. */
export function mountOf(camera: RoverCamera | null, instrument: string, vector: [number, number, number] | null): CameraMount {
  if (!camera || camera.mount === 'mast') return 'mast';
  if (/REAR/i.test(instrument)) return 'rear';
  if (/FRONT/i.test(instrument)) return 'front';
  return vector && vector[0] < 0 ? 'rear' : 'front';
}

/** Eye offsets from the rover's centre (m): along its heading and up. Display choices for the three mounts. */
export const MOUNT_EYE: Record<CameraMount, { forwardM: number; upM: number }> = {
  mast: { forwardM: 0.6, upM: 2.0 },
  front: { forwardM: 1.5, upM: 0.75 },
  rear: { forwardM: -1.5, upM: 0.75 },
};
