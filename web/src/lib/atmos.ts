/**
 * Atmosphere and radiation context for the run area (scripts/extract-atmosphere.mjs).
 *
 * - Jezero: the latest public Perseverance MEDA daily summaries (site data, a few sols).
 * - Gale: Curiosity REMS daily summaries grouped by solar longitude (another site; annual-cycle
 *   reference only).
 * - Radiation: published MSL RAD surface averages at Gale (Hassler et al. 2014).
 *
 * Display context only: none of it reaches the planner, the mission or the routes, and the
 * replay has no Mars date, so nothing here claims the conditions of the simulated run.
 */
export interface AtmosSource {
  id: 'meda' | 'rems' | 'rad';
  title: string;
  url: string;
  credit: string;
  retrieved?: string;
  sha256?: string;
  bytes?: number;
  note: string;
}

export interface JezeroSol {
  sol: number;
  earth_date: string;
  ls_deg: number | null;
  season: string;
  min_temp_c: number | null;
  max_temp_c: number | null;
  pressure_pa: number | null;
  sunrise: string;
  sunset: string;
}

export type UvIndex = 'Low' | 'Moderate' | 'High' | 'Very_High';

export interface GaleBin {
  ls_from: number;
  ls_to: number;
  n: number;
  min_temp_c: number | null;
  max_temp_c: number | null;
  pressure_pa: number | null;
  uv_index: UvIndex | null;
}

export interface AtmosphereData {
  schema: 'mge-atmosphere/1';
  site: { name: string; lat_deg: number; lon_e_deg: number };
  sources: AtmosSource[];
  jezero_sols: JezeroSol[];
  gale_seasonal: {
    bin_deg: number;
    sols_used: number;
    first_sol: { sol: number; date: string } | null;
    last_sol: { sol: number; date: string } | null;
    bins: GaleBin[];
  };
  radiation: {
    source: 'rad';
    site: string;
    absorbed_mgy_per_day: number;
    absorbed_sigma_mgy_per_day: number;
    dose_equivalent_msv_per_day: number;
    dose_equivalent_sigma_msv_per_day: number;
    caveats: string[];
  };
}

/** Checks the fields the panel relies on; returns null (layer unavailable) rather than guessing. */
export function parseAtmosphere(raw: unknown): AtmosphereData | null {
  const d = raw as Partial<AtmosphereData> | null;
  if (!d || d.schema !== 'mge-atmosphere/1') return null;
  if (!Array.isArray(d.jezero_sols) || !Array.isArray(d.sources)) return null;
  const bins = d.gale_seasonal?.bins;
  if (!Array.isArray(bins) || bins.length === 0) return null;
  const r = d.radiation;
  if (!r || !(r.dose_equivalent_msv_per_day > 0) || !(r.absorbed_mgy_per_day > 0)) return null;
  return d as AtmosphereData;
}

/** Most recent Jezero sol with a temperature or pressure reading. */
export function latestJezeroSol(data: AtmosphereData): JezeroSol | null {
  const withData = data.jezero_sols.filter((s) => s.min_temp_c != null || s.max_temp_c != null || s.pressure_pa != null);
  return withData.length ? withData[withData.length - 1] : null;
}

/** Gale bin that contains a solar longitude (degrees, wrapped to 0..360). */
export function galeBinAt(data: AtmosphereData, lsDeg: number): GaleBin | null {
  const ls = ((lsDeg % 360) + 360) % 360;
  return data.gale_seasonal.bins.find((b) => ls >= b.ls_from && ls < b.ls_to) ?? null;
}

/**
 * Jezero pressure as a share of Gale's seasonal median at the same Ls, from the overlapping
 * Jezero sols. Shown next to the barometric expectation for the elevation difference.
 */
export function jezeroToGalePressure(data: AtmosphereData): { ratio: number; sols: number } | null {
  const ratios: number[] = [];
  for (const s of data.jezero_sols) {
    if (s.pressure_pa == null || s.ls_deg == null) continue;
    const b = galeBinAt(data, s.ls_deg);
    if (b?.pressure_pa) ratios.push(s.pressure_pa / b.pressure_pa);
  }
  if (!ratios.length) return null;
  return { ratio: ratios.reduce((a, b) => a + b, 0) / ratios.length, sols: ratios.length };
}

/** Barometric ratio for a height difference with an isothermal scale height (Mars ~11 km). */
export function barometricRatio(heightDiffM: number, scaleHeightM = 11100): number {
  return Math.exp(-heightDiffM / scaleHeightM);
}

/**
 * Surface galactic cosmic ray dose accumulated over an exposure, from the published Gale
 * average (dose equivalent, mSv; absorbed, mGy) with its 1-sigma spread. Unshielded beyond the
 * atmosphere; suit and habitat shielding and solar particle events are not modelled.
 */
export function surfaceDose(data: AtmosphereData, exposureS: number): { msv: number; sigmaMsv: number; mgy: number } {
  const days = Math.max(0, exposureS) / 86400;
  const r = data.radiation;
  return {
    msv: r.dose_equivalent_msv_per_day * days,
    sigmaMsv: r.dose_equivalent_sigma_msv_per_day * days,
    mgy: r.absorbed_mgy_per_day * days,
  };
}

/** Running crew dose shown beside oxygen and energy: dose equivalent so far (µSv) and its rate. */
export interface CrewDose {
  usv: number;
  sigmaUsv: number;
  msvPerDay: number;
}

/**
 * Dose equivalent accumulated by an unshielded astronaut from the start of the run to `t`
 * (simulated seconds), at the Gale surface average. An estimate that advances with the replay
 * clock, not a dosimeter reading.
 */
export function crewDose(data: AtmosphereData, t: number): CrewDose {
  const d = surfaceDose(data, t);
  return { usv: d.msv * 1000, sigmaUsv: d.sigmaMsv * 1000, msvPerDay: data.radiation.dose_equivalent_msv_per_day };
}

/** Dose in µSv with a precision that keeps the counter moving at 1x (0.01 µSv every ~1.4 s). */
export function fmtMicroSv(usv: number): string {
  return usv < 10 ? usv.toFixed(2) : usv < 100 ? usv.toFixed(1) : usv.toFixed(0);
}

/** Readable UV level. */
export function uvLabel(uv: UvIndex | null): string {
  return uv == null ? 'n/a' : uv.replace('_', ' ').toLowerCase();
}
