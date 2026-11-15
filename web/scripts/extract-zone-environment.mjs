#!/usr/bin/env node
/**
 * Water, ice and radiation context for each world, from NASA data, for the astronaut's sites:
 *
 *  - Water: Mars Odyssey Gamma Ray Spectrometer H2O concentration (water-equivalent hydrogen in the top few
 *    tens of centimetres), smoothed 5 x 5 degree map, PDS ODY-M-GRS-5-ELEMENTS-V1.0, H2O_SR_5X5.TAB
 *    (Boynton et al. 2007, JGR 112, E12S99). The value of the 5-degree cell holding the crop centre, with its
 *    1-sigma error. It says how much water the hydrogen would make, not whether it is ice or bound in minerals.
 *  - Ice: the Subsurface Water Ice Mapping project (SWIM 2.0, -60 to 60 N) covers these latitudes, but its
 *    server was unreachable when this was built, so no ice value is imported (recorded as such).
 *  - Radiation: MSL RAD measured at Gale 0.21 +/- 0.04 mGy/day absorbed and 0.64 +/- 0.12 mSv/day dose
 *    equivalent (Hassler et al. 2014, Science 343), with a mean quality factor <Q> = 3.05 +/- 0.3. Guo et al. 2018
 *    (JGR Planets, doi:10.1002/2016JE005206, section 3.3) fitted the measured anticorrelation of the RAD dose rate
 *    with surface pressure: -kappa = c0 + c1 * Phi, c0 = 0.28 +/- 0.03 uGy/day/Pa, c1 = -2.9 +/- 0.6 e-4
 *    uGy/day/Pa/MV, measured between about 700 and 950 Pa; at Phi = 500 MV (the period of Hassler et al.)
 *    -kappa = 0.135 uGy/day/Pa. Each world's dose rate is the Gale value plus |kappa| times the pressure
 *    difference to Gale, and its dose equivalent that times <Q>. The paper states that extrapolating the
 *    linear relation outside the measured pressures is still an open question, so worlds outside 700-950 Pa
 *    are flagged. Pressures: Gale, the annual mean of the REMS daily summaries (seasonal bins in the demo's
 *    atmosphere.json); InSight, its measured annual mean of about 700 Pa (Lange et al. 2022, JGR Planets,
 *    doi:10.1029/2022JE007190, section 2.2); the others, hydrostatic from Gale with the elevation difference
 *    and the Mars scale height of 11.1 km (NASA Mars Fact Sheet). For InSight that formula would give a value
 *    711 Pa, 1.6 % above the measured 700 Pa, which indicates its error.
 *
 * Usage: node scripts/extract-zone-environment.mjs <h2o_sr_5x5.tab> [out.json]
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const [, , tabPath, outArg] = process.argv;
if (!tabPath) throw new Error('usage: node scripts/extract-zone-environment.mjs <h2o_sr_5x5.tab> [out.json]');
const outPath = outArg ?? join(HERE, 'data', 'zone_environment.json');
const SCALE_HEIGHT_M = 11100;
const RAD = { absorbed_mgy_per_day: 0.21, absorbed_sigma_mgy_per_day: 0.04, dose_equivalent_msv_per_day: 0.64, dose_equivalent_sigma_msv_per_day: 0.12, quality_factor: 3.05, quality_factor_sigma: 0.3 };
// Guo et al. 2018, section 3.3: -kappa = c0 + c1 * Phi (uGy/day/Pa), at Phi = 500 MV.
const PHI_MV = 500;
const C0 = 0.28, C0_SIGMA = 0.03, C1 = -2.9e-4, C1_SIGMA = 0.6e-4;
const KAPPA = C0 + C1 * PHI_MV;
const KAPPA_SIGMA = Math.hypot(C0_SIGMA, C1_SIGMA * PHI_MV);
const RAD_RANGE_PA = [700, 950];
// Measured annual mean pressures where a lander measured one.
const MEASURED_PA = { insight: { pa: 700, source: 'InSight APSS annual mean, about 700 Pa (Lange et al. 2022, JGR Planets 127, e2022JE007190, section 2.2)' } };

const WORLDS = {
  jezero: 'ctx_crop.json', gale: 'gale/ctx_crop.json', gusev: 'gusev/dem_crop.json',
  meridiani: 'meridiani/dem_crop.json', insight: 'insight/dem_crop.json', melas: 'melas/dem_crop.json',
};

const text = readFileSync(tabPath, 'utf8');
const cells = new Map();
for (const line of text.trim().split(/\r?\n/)) {
  const [lat, lon, c, s] = line.trim().split(/\s+/).map(Number);
  cells.set(`${lat}|${lon}`, { c, s });
}
const cellOf = (latDeg, lonDeg) => {
  const lat = Math.floor(latDeg / 5) * 5 + 2.5;
  const lon = Math.floor((((lonDeg % 360) + 360) % 360) / 5) * 5 + 2.5;
  return { lat, lon, v: cells.get(`${lat}|${lon}`) };
};

const crops = Object.fromEntries(Object.entries(WORLDS).map(([w, f]) => [w, JSON.parse(readFileSync(join(HERE, 'data', f), 'utf8')).crop]));
const galeElev = crops.gale.median_m;
const atmos = JSON.parse(readFileSync(join(HERE, '..', 'public', 'replay', 'demo', 'atmosphere.json'), 'utf8'));
const bins = atmos.gale_seasonal.bins.filter((b) => b.pressure_pa != null);
const P_GALE = Math.round(bins.reduce((s, b) => s + b.pressure_pa * b.n, 0) / bins.reduce((s, b) => s + b.n, 0));
const worlds = {};
for (const [w, crop] of Object.entries(crops)) {
  const cell = cellOf(crop.centre_lat_deg, crop.centre_lon_deg);
  const ok = cell.v && cell.v.c < 9000;
  const dh = crop.median_m - galeElev;
  worlds[w] = {
    centre_lat_deg: crop.centre_lat_deg,
    centre_lon_deg: crop.centre_lon_deg,
    water: ok
      ? { wt_percent: cell.v.c, sigma_wt_percent: cell.v.s, cell_centre_lat_deg: cell.lat, cell_centre_lon_deg_east: cell.lon, depth: 'top few tens of centimetres', meaning: 'water-equivalent hydrogen; ice or hydrated minerals are not distinguished' }
      : null,
    ice: { status: 'not imported', reason: 'SWIM 2.0 covers -60 to 60 N, but swim.psi.edu answered HTTP 523 (origin unreachable) on 2026-11-15' },
    radiation: (() => {
      const measured = MEASURED_PA[w];
      const pa = w === 'gale' ? P_GALE : measured ? measured.pa : Math.round(P_GALE * Math.exp(-dh / SCALE_HEIGHT_M));
      const dp = P_GALE - pa;
      const absorbed = RAD.absorbed_mgy_per_day * 1000 + KAPPA * dp; // uGy/day
      const absorbedSigma = Math.hypot(RAD.absorbed_sigma_mgy_per_day * 1000, KAPPA_SIGMA * Math.abs(dp));
      // Gale keeps the values RAD measured; elsewhere the dose equivalent is the dose rate times <Q>.
      const de = w === 'gale' ? RAD.dose_equivalent_msv_per_day : (absorbed * RAD.quality_factor) / 1000; // mSv/day
      const deSigma = w === 'gale' ? RAD.dose_equivalent_sigma_msv_per_day : de * Math.hypot(absorbedSigma / absorbed, RAD.quality_factor_sigma / RAD.quality_factor);
      const inside = pa >= RAD_RANGE_PA[0] && pa <= RAD_RANGE_PA[1];
      return {
        reference: { site: 'Gale crater surface (MSL RAD)', ...RAD },
        median_elevation_m: crop.median_m,
        elevation_vs_gale_m: Math.round(dh),
        pressure_pa: pa,
        pressure_source: w === 'gale' ? `REMS daily summaries at Gale, annual mean of the seasonal bins (${P_GALE} Pa)` : measured ? measured.source : `hydrostatic from Gale's ${P_GALE} Pa with ${Math.round(dh)} m of elevation difference and an 11.1 km scale height`,
        kappa_ugy_day_pa: Number(KAPPA.toFixed(3)),
        absorbed_mgy_per_day: Number((absorbed / 1000).toFixed(3)),
        absorbed_sigma_mgy_per_day: Number((absorbedSigma / 1000).toFixed(3)),
        dose_equivalent_msv_per_day: Number(de.toFixed(2)),
        dose_equivalent_sigma_msv_per_day: Number(deSigma.toFixed(2)),
        within_rad_pressure_range: inside,
        note: w === 'gale' ? 'measured by MSL RAD here' : inside ? 'from the RAD dose-pressure relation inside its measured pressure range (Guo et al. 2018)' : 'from the RAD dose-pressure relation OUTSIDE its measured 700-950 Pa range: Guo et al. 2018 state this extrapolation is not yet verified',
      };
    })(),
  };
}
const out = {
  note: 'Water, ice and radiation context per world from NASA data; the elevations come from each scene DEM, whose datums may differ by tens of metres.',
  sources: {
    water: { title: 'Mars Odyssey GRS, H2O concentration, smoothed 5 x 5 degree map (ODY-M-GRS-5-ELEMENTS-V1.0, H2O_SR_5X5)', url: 'https://pds-geosciences.wustl.edu/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/h2o_sr_5x5.tab', sha256: createHash('sha256').update(text).digest('hex'), reference: 'Boynton et al. 2007, JGR 112, E12S99, doi:10.1029/2007JE002887' },
    ice: { title: 'Subsurface Water Ice Mapping (SWIM 2.0)', url: 'https://swim.psi.edu/SWIM2Products.php', status: 'unreachable' },
    radiation: { measurement: 'Hassler et al. 2014, Science 343, 1244797, doi:10.1126/science.1244797 (MSL RAD, Gale; <Q> = 3.05 +/- 0.3)', dependence: 'Guo et al. 2018, JGR Planets, doi:10.1002/2016JE005206, section 3.3: -kappa = 0.28 - 2.9e-4 * Phi uGy/day/Pa, measured at 700-950 Pa; Phi = 500 MV used', insight_pressure: 'Lange et al. 2022, JGR Planets 127, e2022JE007190, section 2.2', scale_height: 'NASA Mars Fact Sheet, scale height 11.1 km, https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html' },
    retrieved: new Date().toISOString().slice(0, 10),
  },
  worlds,
};
writeFileSync(outPath, JSON.stringify(out, null, 1));
for (const [w, v] of Object.entries(worlds)) console.log(`${w}: water ${v.water ? `${v.water.wt_percent} +/- ${v.water.sigma_wt_percent} wt%` : 'n/a'}; ${v.radiation.pressure_pa} Pa; ${v.radiation.absorbed_mgy_per_day} +/- ${v.radiation.absorbed_sigma_mgy_per_day} mGy/day, ${v.radiation.dose_equivalent_msv_per_day} +/- ${v.radiation.dose_equivalent_sigma_msv_per_day} mSv/day${v.radiation.within_rad_pressure_range ? '' : ' (outside RAD range)'}`);
