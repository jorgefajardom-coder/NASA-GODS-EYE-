import ENV from '../../scripts/data/zone_environment.json';

/**
 * Water and radiation context of each zone scene, from scripts/data/zone_environment.json
 * (scripts/extract-zone-environment.mjs; sources in that file and docs/science_poi_dossier.md section 6).
 * Display only: orbital and surface-average context, not local telemetry, a dosimeter reading or a safety limit.
 */

/** Scene (run id) -> world key in zone_environment.json. */
const RUN_TO_WORLD: Record<string, string> = {
  demo: 'jezero',
  'gale-demo': 'gale',
  'gusev-demo': 'gusev',
  'insight-demo': 'insight',
  'meridiani-demo': 'meridiani',
  'melas-demo': 'melas',
};

export interface ZoneEnvironment {
  world: string;
  water: { wtPercent: number; sigma: number; cellLat: number; cellLonEast: number; depth: string; meaning: string };
  radiation: {
    doseMsvPerDay: number;
    doseSigma: number;
    absorbedMgyPerDay: number;
    pressurePa: number;
    /** Measured by MSL RAD at this site (Gale) rather than derived. */
    measuredHere: boolean;
    /** Inside RAD's measured 700-950 Pa range; outside it the dose-pressure relation is an unverified extrapolation. */
    withinRange: boolean;
    note: string;
  };
  ice: string;
}

type RawWorld = {
  water: { wt_percent: number; sigma_wt_percent: number; cell_centre_lat_deg: number; cell_centre_lon_deg_east: number; depth: string; meaning: string };
  ice: { status: string; reason?: string };
  radiation: {
    dose_equivalent_msv_per_day: number;
    dose_equivalent_sigma_msv_per_day: number;
    absorbed_mgy_per_day: number;
    pressure_pa: number;
    within_rad_pressure_range: boolean;
    elevation_vs_gale_m: number;
    note: string;
  };
};

export function zoneEnvironment(runId: string): ZoneEnvironment | null {
  const world = RUN_TO_WORLD[runId];
  const w = world ? (ENV.worlds as Record<string, RawWorld>)[world] : undefined;
  if (!world || !w) return null;
  return {
    world,
    water: {
      wtPercent: w.water.wt_percent,
      sigma: w.water.sigma_wt_percent,
      cellLat: w.water.cell_centre_lat_deg,
      cellLonEast: w.water.cell_centre_lon_deg_east,
      depth: w.water.depth,
      meaning: w.water.meaning,
    },
    radiation: {
      doseMsvPerDay: w.radiation.dose_equivalent_msv_per_day,
      doseSigma: w.radiation.dose_equivalent_sigma_msv_per_day,
      absorbedMgyPerDay: w.radiation.absorbed_mgy_per_day,
      pressurePa: w.radiation.pressure_pa,
      measuredHere: w.radiation.elevation_vs_gale_m === 0,
      withinRange: w.radiation.within_rad_pressure_range,
      note: w.radiation.note,
    },
    ice: w.ice.status,
  };
}

/** Dose equivalent (mSv) over an excursion of `hours` at a daily average rate: rate x hours / 24, no shielding. */
export function excursionDoseMsv(msvPerDay: number, hours: number): number {
  return (msvPerDay * hours) / 24;
}

/** NASA DONKI (space weather event database): solar flares and particle events are not in these averages. */
export const DONKI_URL = 'https://kauai.ccmc.gsfc.nasa.gov/DONKI/';

export interface ZoneCrewDose {
  /** Dose equivalent accumulated over `t` simulated seconds at the zone's surface rate (µSv). */
  usv: number;
  sigmaUsv: number;
  msvPerDay: number;
  measuredHere: boolean;
  withinRange: boolean;
}

/** The astronaut's dose after `t` simulated seconds outside at this zone (unshielded surface average). */
export function zoneCrewDose(runId: string, t: number): ZoneCrewDose | null {
  const env = zoneEnvironment(runId);
  if (!env) return null;
  const days = Math.max(0, t) / 86400;
  const usv = env.radiation.doseMsvPerDay * days * 1000;
  return {
    usv,
    sigmaUsv: env.radiation.doseSigma * days * 1000,
    msvPerDay: env.radiation.doseMsvPerDay,
    measuredHere: env.radiation.measuredHere,
    withinRange: env.radiation.withinRange,
  };
}
