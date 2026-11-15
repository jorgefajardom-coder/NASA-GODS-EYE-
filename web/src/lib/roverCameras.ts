/**
 * The real Perseverance cameras the rover's view is limited to (display only). Each camera is drawn
 * from where it sits on the 3D model (its node), with its own field of view, focus range and stereo
 * baseline. Values and sources:
 *
 * - Navcam: mast-mounted colour stereo pair, 96 x 73 deg, fixed 19.2 mm focal length, best focus 3.5 m,
 *   depth of field 1.5 m to infinity, 42.4 cm baseline. Maki et al. 2020, The Mars 2020 Engineering
 *   Cameras and Microphone, Space Science Reviews 216, 137, https://doi.org/10.1007/s11214-020-00765-9 ;
 *   https://an.rsl.wustl.edu/help/Content/About%20the%20mission/M20/Instruments/M20%20ECAM.htm
 * - Hazcam: four front (two pairs, A and B) and two rear fisheye cameras fixed to the body, 136 x 102 deg,
 *   best focus 1.0 m, depth of field 0.8 m to infinity; baseline 25 cm (front) and 93.4 cm (rear). Same
 *   sources as the Navcam.
 * - Mastcam-Z: stereo zoom pair on the mast head, 26 mm (25.6 x 19.2 deg) to 110 mm (6.2 x 4.6 deg),
 *   24.4 cm baseline, focus 0.5 m to infinity up to about 50 mm and 1 m to infinity beyond (LPSC 2021
 *   table; the ASU tech-spec page gives 1-2 m to infinity). Bell et al. 2021, Space Science Reviews 217,
 *   24, https://doi.org/10.1007/s11214-020-00755-x ; https://mastcamz.asu.edu/cameras/tech-specs
 * - WATSON: colour close-up camera on the arm's turret (SHERLOC), focusable from 1.8 cm to infinity.
 *   Its angular field is not published in the sources checked; 35 x 27 deg is derived from the NASA
 *   abstract's example (about 17 x 13 cm seen from 27 cm). https://ntrs.nasa.gov/citations/20220000131
 *
 * Perseverance has 23 cameras in all (9 engineering cameras for surface work, 7 for entry, descent and
 * landing, and the science cameras: Mastcam-Z x2, SuperCam RMI, WATSON, SHERLOC ACI, PIXL MCC, MEDA
 * SkyCam, CacheCam). Only the five above are flown in this viewer; the others keep the Navcam view.
 *
 * The viewer's lens is vertical, so the vertical field of view is used. No fisheye distortion is drawn.
 */
export type RoverCameraId = 'navcam' | 'mastcamz' | 'hazcam_front' | 'hazcam_rear' | 'watson';
/** Mast cameras pan and tilt with the mast head; body cameras are fixed; WATSON rides on the arm. */
export type CameraMount = 'mast' | 'body' | 'arm';
export type StereoSide = 'left' | 'right';

export interface RoverCamera {
  id: RoverCameraId;
  label: string;
  /** Short name for the dock keys. */
  short: string;
  mount: CameraMount;
  /** Field of view at the widest setting (deg). */
  vFovDeg: number;
  hFovDeg: number;
  /** Focal length range (mm): a zoom has two different ends, a fixed lens two equal ones; null if unknown. */
  focalMm: readonly [number, number] | null;
  /** Height of the image sensor area used (mm), for the field of view of a zoom at a focal length. */
  sensorHeightMm: number | null;
  /** Nearest and farthest sharp distance (m; null = infinity). Mastcam-Z: at its wide end. */
  focusM: { nearM: number; farM: number | null };
  /** Distance between the two eyes of the stereo pair (m), or null for a single camera. */
  baselineM: number | null;
  /** Name of the 3D model node the camera sits on (GLTF names lose their dots). */
  node: string;
  /** Fixed pointing of a body camera relative to the rover (deg; az clockwise from the front, el negative down). */
  boresight?: { azDeg: number; elDeg: number };
}

/** Mastcam-Z sensor height used at 26 mm for 19.2 deg: 2 x 26 x tan(9.6 deg). */
const MCZ_SENSOR_MM = 2 * 26 * Math.tan((9.6 * Math.PI) / 180);

export const ROVER_CAMERAS: Record<RoverCameraId, RoverCamera> = {
  navcam: { id: 'navcam', label: 'Navcam', short: 'NAV', mount: 'mast', vFovDeg: 73, hFovDeg: 96, focalMm: [19.2, 19.2], sensorHeightMm: null, focusM: { nearM: 1.5, farM: null }, baselineM: 0.424, node: 'NavCams' },
  mastcamz: { id: 'mastcamz', label: 'Mastcam-Z', short: 'MCZ', mount: 'mast', vFovDeg: 19.2, hFovDeg: 25.6, focalMm: [26, 110], sensorHeightMm: MCZ_SENSOR_MM, focusM: { nearM: 0.5, farM: null }, baselineM: 0.244, node: 'Mastcam_Z_cams' },
  // Front Hazcam A pair: the feed's pointing is about 25 deg below the horizon, straight ahead.
  hazcam_front: { id: 'hazcam_front', label: 'Front Hazcam', short: 'FHAZ', mount: 'body', vFovDeg: 102, hFovDeg: 136, focalMm: null, sensorHeightMm: null, focusM: { nearM: 0.8, farM: null }, baselineM: 0.25, node: 'hazcams_front', boresight: { azDeg: 0, elDeg: -25 } },
  // Rear pair: the same tilt is assumed (display choice), looking back.
  hazcam_rear: { id: 'hazcam_rear', label: 'Rear Hazcam', short: 'RHAZ', mount: 'body', vFovDeg: 102, hFovDeg: 136, focalMm: null, sensorHeightMm: null, focusM: { nearM: 0.8, farM: null }, baselineM: 0.934, node: 'hazcams_rear', boresight: { azDeg: 180, elDeg: -25 } },
  watson: { id: 'watson', label: 'WATSON (arm)', short: 'ARM', mount: 'arm', vFovDeg: 27, hFovDeg: 35, focalMm: null, sensorHeightMm: null, focusM: { nearM: 0.018, farM: null }, baselineM: null, node: 'WATSON' },
};

export const CAMERA_ORDER: readonly RoverCameraId[] = ['navcam', 'mastcamz', 'hazcam_front', 'hazcam_rear', 'watson'];

/** The rover's own view when no photo is being taken: its Navcam. */
export const DEFAULT_ROVER_CAMERA = ROVER_CAMERAS.navcam;

/** Mastcam-Z vertical field of view (deg) at a focal length (mm), clamped to the zoom's ends. */
export function mastcamFovDeg(focalMm: number): number {
  const [lo, hi] = ROVER_CAMERAS.mastcamz.focalMm!;
  const f = Math.min(hi, Math.max(lo, focalMm));
  return (2 * Math.atan(MCZ_SENSOR_MM / 2 / f) * 180) / Math.PI;
}

/** Mastcam-Z nearest sharp distance (m) at a focal length: 0.5 m up to about 50 mm, 1 m beyond. */
export function mastcamNearFocusM(focalMm: number): number {
  return focalMm <= 50 ? 0.5 : 1;
}

/** Vertical field of view (deg) of a camera; Mastcam-Z at the focal length given. */
export function cameraFovDeg(cam: RoverCamera, focalMm: number | null): number {
  return cam.id === 'mastcamz' && focalMm != null ? mastcamFovDeg(focalMm) : cam.vFovDeg;
}

/**
 * Focal length of a Mastcam-Z frame from its image ID: the last field starts with the focal length
 * in tenths of a millimetre (e.g. `..._1100LMJ` = 110 mm, `..._0340LMJ` = 34 mm). Null when absent.
 */
export function mastcamFocalFromId(imageId: string): number | null {
  const m = imageId.match(/_(\d{4})[A-Z][A-Z0-9]{1,3}$/);
  if (!m) return null;
  const f = Number(m[1]) / 10;
  const [lo, hi] = ROVER_CAMERAS.mastcamz.focalMm!;
  return f >= lo - 1 && f <= hi + 1 ? Math.min(hi, Math.max(lo, f)) : null;
}

export interface CameraOfPhoto {
  camera: RoverCamera;
  /** Which eye of the stereo pair took it (Navcam, Mastcam-Z and Hazcam are pairs). */
  side: StereoSide;
}

/**
 * Which real camera, and which of its two eyes, took a photo, from the feed's instrument name
 * (e.g. NAVCAM_LEFT, MCZ_RIGHT, FRONT_HAZCAM_LEFT_A, REAR_HAZCAM_RIGHT, SHERLOC_WATSON). Only
 * Perseverance's cameras are described (Curiosity's were not checked here): null for anything else,
 * including SuperCam, SkyCam and CacheCam.
 */
export function roverCameraOf(instrument: string, mission = 'Perseverance'): CameraOfPhoto | null {
  if (mission !== 'Perseverance') return null;
  const side: StereoSide = /RIGHT/i.test(instrument) ? 'right' : 'left';
  if (/WATSON/i.test(instrument)) return { camera: ROVER_CAMERAS.watson, side: 'left' };
  if (/NAVCAM/i.test(instrument)) return { camera: ROVER_CAMERAS.navcam, side };
  if (/^MCZ|MASTCAM/i.test(instrument)) return { camera: ROVER_CAMERAS.mastcamz, side };
  if (/HAZCAM/i.test(instrument)) return { camera: /REAR/i.test(instrument) ? ROVER_CAMERAS.hazcam_rear : ROVER_CAMERAS.hazcam_front, side };
  return null;
}

/** Text of a camera's sharp range, e.g. "1.5 m – ∞" or "1.8 cm – ∞". */
export function focusText(nearM: number, farM: number | null): string {
  const near = nearM < 0.1 ? `${(nearM * 100).toFixed(1)} cm` : `${nearM.toFixed(1)} m`;
  return `${near} – ${farM == null ? '∞' : `${farM.toFixed(1)} m`}`;
}
