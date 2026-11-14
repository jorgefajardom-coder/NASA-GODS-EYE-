#!/usr/bin/env node
/**
 * Atmosphere and radiation context for the demo run (public/replay/demo/atmosphere.json).
 *
 * Inputs, all public:
 *  - Mars 2020 Perseverance MEDA daily weather summary at Jezero crater, NASA Mars weather feed
 *    (category mars2020). The feed only carries the latest published sols.
 *  - MSL Curiosity REMS daily weather summary at Gale crater, same feed (category msl), every sol
 *    since landing. Used for the annual cycle only: Gale is another site (about 4.6 S, roughly
 *    1.9 km lower than Jezero), so its values are a reference, not Jezero conditions.
 *  - MSL RAD surface dose rates published by Hassler et al. (2014), Science 343, 1244797,
 *    https://doi.org/10.1126/science.1244797 (constants below, not downloaded).
 *
 * Both weather feeds are outreach summaries from Centro de Astrobiologia (CAB); its disclaimer
 * says they are for outreach purposes and points to PDS for science data. The output keeps
 * that caveat. No value is interpolated or synthesised: Jezero sols are copied, Gale sols are
 * grouped by solar longitude (Ls) into 15 degree bins with medians and counts.
 *
 * Usage: node scripts/extract-atmosphere.mjs [out.json]
 */
import { createHash } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const FEED = 'https://mars.nasa.gov/rss/api/?feed=weather&feedtype=json&category=';
const HERE = dirname(fileURLToPath(import.meta.url));
const outPath = process.argv[2] ?? join(HERE, '..', 'public', 'replay', 'demo', 'atmosphere.json');
const BIN_DEG = 15;
const UV_LEVELS = ['Low', 'Moderate', 'High', 'Very_High'];

async function getFeed(category) {
  const url = FEED + category;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  const body = Buffer.from(await res.arrayBuffer());
  return { url, sha256: createHash('sha256').update(body).digest('hex'), bytes: body.length, json: JSON.parse(body.toString('utf8')) };
}

/** Feed values are numbers, numeric strings or '--'. */
const num = (v) => {
  if (v === null || v === undefined || v === '--' || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

const median = (xs) => {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

const round = (v, d = 1) => (v == null ? null : Math.round(v * 10 ** d) / 10 ** d);

function jezeroSols(feed) {
  return feed.json.sols
    .map((s) => ({
      sol: Number(s.sol),
      earth_date: s.terrestrial_date,
      ls_deg: num(s.ls),
      season: s.season,
      min_temp_c: num(s.min_temp),
      max_temp_c: num(s.max_temp),
      pressure_pa: num(s.pressure),
      sunrise: s.sunrise,
      sunset: s.sunset,
    }))
    .sort((a, b) => a.sol - b.sol);
}

function galeSeasonal(feed) {
  const sols = feed.json.soles;
  const bins = Array.from({ length: 360 / BIN_DEG }, (_, i) => ({ min: [], max: [], p: [], uv: [], ls_from: i * BIN_DEG }));
  let first = null;
  let last = null;
  for (const s of sols) {
    const ls = num(s.ls);
    if (ls == null) continue;
    const b = bins[Math.min(bins.length - 1, Math.floor(ls / BIN_DEG))];
    const mn = num(s.min_temp);
    const mx = num(s.max_temp);
    const p = num(s.pressure);
    if (mn != null) b.min.push(mn);
    if (mx != null) b.max.push(mx);
    if (p != null) b.p.push(p);
    const uv = UV_LEVELS.indexOf(s.local_uv_irradiance_index);
    if (uv >= 0) b.uv.push(uv);
    const sol = Number(s.sol);
    if (first == null || sol < first.sol) first = { sol, date: s.terrestrial_date };
    if (last == null || sol > last.sol) last = { sol, date: s.terrestrial_date };
  }
  return {
    bin_deg: BIN_DEG,
    sols_used: sols.length,
    first_sol: first,
    last_sol: last,
    bins: bins.map((b) => {
      const uv = median(b.uv);
      return {
        ls_from: b.ls_from,
        ls_to: b.ls_from + BIN_DEG,
        n: Math.max(b.min.length, b.max.length, b.p.length),
        min_temp_c: round(median(b.min)),
        max_temp_c: round(median(b.max)),
        pressure_pa: round(median(b.p), 0),
        uv_index: uv == null ? null : UV_LEVELS[Math.round(uv)],
      };
    }),
  };
}

const meda = await getFeed('mars2020');
const rems = await getFeed('msl');
const retrieved = new Date().toISOString().slice(0, 10);
const outreach = 'Daily outreach summary from Centro de Astrobiologia (CAB); for outreach purposes, not calibrated science data (see PDS for the science archive).';

const out = {
  schema: 'mge-atmosphere/1',
  site: { name: 'Jezero crater', lat_deg: 18.44, lon_e_deg: 77.45 },
  sources: [
    {
      id: 'meda',
      title: 'Mars 2020 Perseverance MEDA daily weather summary, Jezero crater',
      url: meda.url,
      credit: 'NASA/JPL-Caltech/CAB(CSIC-INTA)',
      retrieved,
      sha256: meda.sha256,
      bytes: meda.bytes,
      note: outreach,
    },
    {
      id: 'rems',
      title: 'MSL Curiosity REMS daily weather summary, Gale crater',
      url: rems.url,
      credit: 'NASA/JPL-Caltech/CAB(CSIC-INTA)',
      retrieved,
      sha256: rems.sha256,
      bytes: rems.bytes,
      note: `${outreach} Gale is another site (about 4.6 S, roughly 1.9 km lower than Jezero, seasons opposite in latitude); used only as an annual-cycle reference.`,
    },
    {
      id: 'rad',
      title: 'Hassler et al. (2014), Mars’ surface radiation environment measured with the Mars Science Laboratory’s Curiosity rover, Science 343, 1244797',
      url: 'https://doi.org/10.1126/science.1244797',
      credit: 'MSL RAD team; NASA/JPL-Caltech/SwRI',
      note: 'Galactic cosmic ray averages over roughly the first 300 sols at Gale crater (August 2012 to June 2013, near solar maximum); solar particle events are reported separately in the paper.',
    },
  ],
  jezero_sols: jezeroSols(meda),
  gale_seasonal: galeSeasonal(rems),
  radiation: {
    source: 'rad',
    site: 'Gale crater surface',
    absorbed_mgy_per_day: 0.21,
    absorbed_sigma_mgy_per_day: 0.04,
    dose_equivalent_msv_per_day: 0.64,
    dose_equivalent_sigma_msv_per_day: 0.12,
    caveats: [
      'Galactic cosmic ray average measured at Gale; not a Jezero measurement or a local dose map.',
      'Jezero is about 1.9 km higher, with less air overhead, so its surface rate is expected to be somewhat higher; this is not quantified here.',
      'Suit, vehicle and habitat shielding and solar particle events are not modelled.',
    ],
  },
};

writeFileSync(outPath, JSON.stringify(out, null, 1) + '\n');
console.log(`wrote ${outPath}: ${out.jezero_sols.length} Jezero sols, ${out.gale_seasonal.sols_used} Gale sols`);
