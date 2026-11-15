/**
 * Current time on Mars from an Earth instant, by the Mars24 algorithm of NASA GISS
 * (Allison & McEwen 2000, Planet. Space Sci. 48, 215; Allison 1997, Geophys. Res. Lett. 24, 1967;
 * https://www.giss.nasa.gov/tools/mars24/help/algorithm.html). Gives the Mars Sol Date, Mars
 * Coordinated Time (mean solar time at the prime meridian), local mean and true solar time at a
 * site, the areocentric solar longitude Ls and the Mars 2020 (Perseverance) mission sol.
 *
 * It is the real present time on Mars for the viewer's clock, independent of the replay's
 * simulated mission time.
 */

/** TT - UTC (s) from the leap-second table: 32.184 s plus the accumulated leap seconds. */
const LEAP_STEPS: Array<[number, number]> = [
  [Date.UTC(1999, 0, 1), 64.184],
  [Date.UTC(2006, 0, 1), 65.184],
  [Date.UTC(2009, 0, 1), 66.184],
  [Date.UTC(2012, 6, 1), 67.184],
  [Date.UTC(2015, 6, 1), 68.184],
  [Date.UTC(2017, 0, 1), 69.184],
];

export function ttMinusUtcS(ms: number): number {
  let v = 63.184;
  for (const [from, s] of LEAP_STEPS) if (ms >= from) v = s;
  return v;
}

/** Perturbations of the Mars orbit by the planets (Mars24, step B-5): amplitude deg, period yr, phase deg. */
const PBS: Array<[number, number, number]> = [
  [0.0071, 2.2353, 49.409],
  [0.0057, 2.7543, 168.173],
  [0.0039, 1.1177, 191.837],
  [0.0037, 15.7866, 21.736],
  [0.0021, 2.1354, 15.704],
  [0.002, 2.4694, 95.528],
  [0.0018, 32.8493, 49.095],
];

const rad = (d: number) => (d * Math.PI) / 180;
const wrap = (x: number, m: number) => ((x % m) + m) % m;

export interface MarsTime {
  /** Mars Sol Date (sols since 29 December 1873, Mars24). */
  msd: number;
  /** Mars Coordinated Time, hours 0..24. */
  mtcH: number;
  /** Areocentric solar longitude (season), degrees 0..360. */
  lsDeg: number;
  /** Equation of time, degrees (true minus mean solar time, times 15 deg/h). */
  eotDeg: number;
}

/** Mars time at an Earth instant (milliseconds since 1970, UTC). */
export function marsTime(ms: number): MarsTime {
  const jdUt = ms / 86400000 + 2440587.5;
  const jdTt = jdUt + ttMinusUtcS(ms) / 86400;
  const dt = jdTt - 2451545.0; // days since J2000 (TT)
  const M = rad(19.3871 + 0.52402073 * dt); // mean anomaly
  const alphaFms = 270.3871 + 0.524038496 * dt; // fictitious mean sun
  let pbs = 0;
  for (const [a, tau, phi] of PBS) pbs += a * Math.cos(rad((0.985626 * dt) / tau + phi));
  const nuM = (10.691 + 3.0e-7 * dt) * Math.sin(M) + 0.623 * Math.sin(2 * M) + 0.05 * Math.sin(3 * M) + 0.005 * Math.sin(4 * M) + 0.0005 * Math.sin(5 * M) + pbs;
  const ls = wrap(alphaFms + nuM, 360);
  const lsR = rad(ls);
  const eot = 2.861 * Math.sin(2 * lsR) - 0.071 * Math.sin(4 * lsR) + 0.002 * Math.sin(6 * lsR) - nuM;
  const msd = (jdTt - 2405522.0028779) / 1.0274912517;
  return { msd, mtcH: wrap(24 * msd, 24), lsDeg: ls, eotDeg: eot };
}

/** Local mean solar time (hours) at an east longitude (degrees). */
export function lmstH(t: MarsTime, lonEastDeg: number): number {
  return wrap(t.mtcH + lonEastDeg / 15, 24);
}

/** Local true solar time (hours, sundial time) at an east longitude (degrees). */
export function ltstH(t: MarsTime, lonEastDeg: number): number {
  return wrap(lmstH(t, lonEastDeg) + t.eotDeg / 15, 24);
}

/** Mars Science Laboratory landing (Curiosity, Gale crater, Bradbury Landing): 6 August 2012, about 05:17 UTC; that local sol is sol 0. */
export const MSL_LANDING_MS = Date.UTC(2012, 7, 6, 5, 17);

/** Mars 2020 landing (Perseverance, Jezero): 18 February 2021, 20:55 UTC; that local sol is sol 0. */
export const MARS2020_LANDING_MS = Date.UTC(2021, 1, 18, 20, 55);
export const JEZERO_LON_E_DEG = 77.45;

/** Local Mars sol number at an east longitude (whole sols since the MSD epoch, in local time). */
function localSol(ms: number, lonEastDeg: number): number {
  return Math.floor(marsTime(ms).msd + lonEastDeg / 360);
}

/** Perseverance mission sol at an Earth instant (sol 0 = landing sol, counted in Jezero local time). */
export function mars2020Sol(ms: number, lonEastDeg = JEZERO_LON_E_DEG): number {
  return localSol(ms, lonEastDeg) - localSol(MARS2020_LANDING_MS, lonEastDeg);
}

/** Mission sol at an Earth instant for any rover: whole local sols since its landing sol (sol 0). */
export function missionSol(ms: number, lonEastDeg: number, landingMs: number): number {
  return localSol(ms, lonEastDeg) - localSol(landingMs, lonEastDeg);
}

/** Site clocks of the worlds: the name shown, the mission and its landing instant. */
export const SITE_CLOCKS: Record<string, { place: string; mission: string; landingMs: number }> = {
  jezero: { place: 'Jezero', mission: 'Perseverance', landingMs: MARS2020_LANDING_MS },
  gale: { place: 'Gale', mission: 'Curiosity', landingMs: MSL_LANDING_MS },
};

/** "HH:MM:SS" for hours 0..24. */
export function fmtHms(hours: number): string {
  const s = Math.floor(wrap(hours, 24) * 3600);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(Math.floor(s / 3600))}:${p(Math.floor((s % 3600) / 60))}:${p(s % 60)}`;
}

/** Mars season name in the northern hemisphere from Ls (Jezero is at 18.4 N). */
export function northernSeason(lsDeg: number): string {
  const ls = wrap(lsDeg, 360);
  return ls < 90 ? 'northern spring' : ls < 180 ? 'northern summer' : ls < 270 ? 'northern autumn' : 'northern winter';
}
