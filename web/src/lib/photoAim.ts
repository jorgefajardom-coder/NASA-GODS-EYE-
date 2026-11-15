/**
 * Where a real rover photo was taken towards, so the camera can turn that way when the photo is shown
 * (the person feels they are taking it). Display only.
 *
 * Perseverance's feed gives each camera's pointing in the rover frame (`camera_vector`: x forward, y
 * right, z down; or the mast azimuth and elevation). Curiosity's feed gives no pointing, so only its
 * hazard cameras (which look straight ahead or behind) are aimed. The rover frame is turned to the
 * world with the rover's published yaw at that stop (degrees clockwise from north), so the direction
 * is approximate: the replay's own rover heading is not the real one.
 */

export interface PhotoPointing {
  instrument: string;
  /** Pointing vector in the rover frame (x forward, y right, z down), or null. */
  vector: [number, number, number] | null;
  /** Mast azimuth (deg clockwise from the rover's front) and elevation (deg, negative down), or null. */
  mastAzDeg: number | null;
  mastElDeg: number | null;
}

export interface PhotoDirection {
  /** Compass azimuth, degrees clockwise from north, 0..360. */
  azimuthDeg: number;
  /** Elevation, degrees (negative = looking down). */
  pitchDeg: number;
  /** Where the direction came from, for the readout. */
  source: 'vector' | 'mast' | 'instrument';
}

/** Parses "(a,b,c)" (the feed writes vectors as text) into three numbers. */
export function parseVector(v: unknown): [number, number, number] | null {
  if (Array.isArray(v) && v.length === 3 && v.every((n) => typeof n === 'number' && Number.isFinite(n))) return v as [number, number, number];
  if (typeof v !== 'string') return null;
  const n = v.match(/-?\d+(?:\.\d+)?(?:e-?\d+)?/gi)?.map(Number);
  return n && n.length === 3 && n.every(Number.isFinite) ? (n as [number, number, number]) : null;
}

/** A number from the feed's text ("UNK" and the like give null). */
export function parseNumber(v: unknown): number | null {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
}

const wrap360 = (d: number) => ((d % 360) + 360) % 360;

/**
 * Direction of a photo in the world, or null when the feed does not say. `rover` is the mission's
 * name for the fallback rules (`Curiosity`: hazard cameras only).
 */
export function photoDirection(p: PhotoPointing, stopYawDeg: number | null | undefined, rover = 'Perseverance'): PhotoDirection | null {
  const yaw = stopYawDeg ?? 0;
  const here = (az: number, pitch: number, source: PhotoDirection['source']): PhotoDirection => ({ azimuthDeg: wrap360(yaw + az), pitchDeg: pitch, source });
  if (p.vector) {
    const [x, y, z] = p.vector;
    if (Math.hypot(x, y, z) > 0.5) return here((Math.atan2(y, x) * 180) / Math.PI, (-Math.asin(Math.max(-1, Math.min(1, z / Math.hypot(x, y, z)))) * 180) / Math.PI, 'vector');
  }
  if (p.mastAzDeg != null && p.mastElDeg != null) return here(p.mastAzDeg, p.mastElDeg, 'mast');
  if (rover === 'Curiosity') {
    if (/FHAZ/i.test(p.instrument)) return here(0, -25, 'instrument');
    if (/RHAZ/i.test(p.instrument)) return here(180, -25, 'instrument');
  }
  return null;
}

/** Signed shortest turn from one azimuth to another (degrees, -180..180, positive = clockwise). */
export function shortestTurnDeg(from: number, to: number): number {
  return ((((to - from) % 360) + 540) % 360) - 180;
}

/**
 * Request to turn the third-person camera towards a photo's direction (FollowCamera reads it each
 * frame and eases towards it). A new token is a new request. The rover's own camera does not use
 * it: the mast head is driven by the rover rig (lib/roverRig).
 */
export const aimRequest: { token: number; azimuthDeg: number | null; pitchDeg: number | null } = {
  token: 0,
  azimuthDeg: 0,
  pitchDeg: 0,
};

/** Asks the third-person camera to swing towards (azimuth, pitch); a null field is left as it is. */
export function requestAim(d: { azimuthDeg?: number | null; pitchDeg?: number | null }): void {
  aimRequest.azimuthDeg = d.azimuthDeg ?? null;
  aimRequest.pitchDeg = d.pitchDeg ?? null;
  aimRequest.token += 1;
}

/**
 * Pointing of a photo relative to the drawn rover (deg; az clockwise from its front, el negative down),
 * from its world direction and the drawn rover's compass heading, so the mast looks where NASA's camera
 * looked even though the replay's rover heading is not the real one.
 */
export function relativeToRover(dir: PhotoDirection, roverHeadingDeg: number): { azDeg: number; elDeg: number } {
  return { azDeg: shortestTurnDeg(roverHeadingDeg, dir.azimuthDeg), elDeg: dir.pitchDeg };
}
