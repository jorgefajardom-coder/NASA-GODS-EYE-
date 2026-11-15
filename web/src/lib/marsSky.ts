import { ltstH, marsTime, ttMinusUtcS } from './marsClock';

/**
 * The sky over a site on Mars at an Earth instant: where the Sun and the stars are.
 *
 * - Sun: from the Mars24 algorithm (NASA GISS; Allison & McEwen 2000) already used by the viewer's
 *   clock: solar declination from Ls (step D-1) and the hour angle from local true solar time, so the
 *   Sun in the sky agrees with the "Jezero LMST/LTST" clock on screen.
 * - Stars: catalogue positions (J2000) turned into the local sky with the IAU/WGCCRE 2009 rotation
 *   model of Mars (Archinal et al. 2011, Celest. Mech. Dyn. Astr. 109, 101): north pole
 *   alpha0 = 317.68143 - 0.1061 T, delta0 = 52.88650 - 0.0609 T, prime meridian
 *   W = 176.630 + 350.89198226 d (d days, T Julian centuries from J2000 TDB, approximated by TT).
 *
 * Display only: no refraction, aberration, precession of the catalogue or proper motion
 * (well under a degree in the sky). Directions are local ENU unit vectors (east, north, up).
 */

const rad = (d: number) => (d * Math.PI) / 180;
const deg = (r: number) => (r * 180) / Math.PI;

export type Enu = [number, number, number];

export interface SunSky {
  /** Azimuth clockwise from north (deg, 0..360) and elevation above the horizon (deg). */
  azDeg: number;
  elDeg: number;
  dir: Enu;
  /** Solar declination (deg) and local true solar time (h) behind it. */
  declDeg: number;
  ltstH: number;
}

/** Local direction from azimuth (clockwise from north) and elevation, in degrees. */
export function enuFromAzEl(azDeg: number, elDeg: number): Enu {
  const a = rad(azDeg);
  const e = rad(elDeg);
  return [Math.cos(e) * Math.sin(a), Math.cos(e) * Math.cos(a), Math.sin(e)];
}

/** Azimuth/elevation (deg) of an ENU direction. */
export function azElFromEnu([e, n, u]: Enu): { azDeg: number; elDeg: number } {
  return { azDeg: (deg(Math.atan2(e, n)) + 360) % 360, elDeg: deg(Math.asin(Math.max(-1, Math.min(1, u)))) };
}

/** Sun in the local sky at an Earth instant (ms, UTC), planetographic latitude and east longitude. */
export function marsSun(ms: number, latDeg: number, lonEastDeg: number): SunSky {
  const t = marsTime(ms);
  const ls = rad(t.lsDeg);
  const decl = deg(Math.asin(0.42565 * Math.sin(ls))) + 0.25 * Math.sin(ls);
  const ltst = ltstH(t, lonEastDeg);
  const H = rad((ltst - 12) * 15);
  const phi = rad(latDeg);
  const d = rad(decl);
  const sinEl = Math.sin(phi) * Math.sin(d) + Math.cos(phi) * Math.cos(d) * Math.cos(H);
  const el = Math.asin(Math.max(-1, Math.min(1, sinEl)));
  // Azimuth from north, clockwise (east positive); morning hour angles are negative.
  const az = Math.atan2(-Math.sin(H) * Math.cos(d), Math.cos(phi) * Math.sin(d) - Math.sin(phi) * Math.cos(d) * Math.cos(H));
  const azDeg = (deg(az) + 360) % 360;
  return { azDeg, elDeg: deg(el), dir: enuFromAzEl(azDeg, deg(el)), declDeg: decl, ltstH: ltst };
}

/** Days and Julian centuries from J2000 (TT) at an Earth instant. */
function j2000(ms: number): { d: number; T: number } {
  const jdTt = ms / 86400000 + 2440587.5 + ttMinusUtcS(ms) / 86400;
  const d = jdTt - 2451545.0;
  return { d, T: d / 36525 };
}

/** Mars orientation (IAU 2009) at an instant: pole right ascension/declination and prime meridian (deg). */
export function marsOrientation(ms: number): { alpha0: number; delta0: number; W: number } {
  const { d, T } = j2000(ms);
  return { alpha0: 317.68143 - 0.1061 * T, delta0: 52.8865 - 0.0609 * T, W: (((176.63 + 350.89198226 * d) % 360) + 360) % 360 };
}

/**
 * Converter from catalogue (ICRF/J2000) right ascension and declination to the local sky of a site,
 * fixed at one instant (rebuild it as time passes; Mars turns 0.0041 deg per second).
 */
export function celestialToLocal(ms: number, latDeg: number, lonEastDeg: number): (raDeg: number, decDeg: number) => Enu {
  const { alpha0, delta0, W } = marsOrientation(ms);
  // Body-fixed = Rz(W) Rx(90 - delta0) Rz(90 + alpha0) . ICRF (frame rotations).
  const a = rad(90 + alpha0);
  const b = rad(90 - delta0);
  const w = rad(W);
  const ca = Math.cos(a), sa = Math.sin(a), cb = Math.cos(b), sb = Math.sin(b), cw = Math.cos(w), sw = Math.sin(w);
  const phi = rad(latDeg);
  const lam = rad(lonEastDeg);
  const sp = Math.sin(phi), cp = Math.cos(phi), sl = Math.sin(lam), cl = Math.cos(lam);
  return (raDeg, decDeg) => {
    const r = rad(raDeg);
    const dd = rad(decDeg);
    let x = Math.cos(dd) * Math.cos(r);
    let y = Math.cos(dd) * Math.sin(r);
    let z = Math.sin(dd);
    // Rz(a)
    [x, y] = [ca * x + sa * y, -sa * x + ca * y];
    // Rx(b)
    [y, z] = [cb * y + sb * z, -sb * y + cb * z];
    // Rz(w)
    [x, y] = [cw * x + sw * y, -sw * x + cw * y];
    // Body-fixed -> local east, north, up at (phi, lam).
    const e = -sl * x + cl * y;
    const n = -sp * cl * x - sp * sl * y + cp * z;
    const u = cp * cl * x + cp * sl * y + sp * z;
    return [e, n, u];
  };
}

/** Share of daylight in the sky (0 night .. 1 day) from the Sun's elevation: Mars twilight is long and dusty. */
export function daylight(sunElDeg: number): number {
  const x = Math.max(0, Math.min(1, (sunElDeg + 12) / 22)); // -12 deg: dark, +10 deg: full day
  return x * x * (3 - 2 * x);
}

export interface StarCatalogue {
  source: string;
  columns: string[];
  max_vmag: number;
  stars: Array<[number, number, number, number]>;
}
