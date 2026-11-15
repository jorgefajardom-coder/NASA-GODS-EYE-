#!/usr/bin/env node
/**
 * Real science sites inside a world's crop: where NASA's rover actually sampled, drilled or did contact
 * science. Each site is placed at the rover's own published position when it did that work, so nothing is
 * guessed from images. These replace the fictitious POIs of the simulated story where a mission exists.
 *
 *  - jezero (Perseverance): the rock, regolith and atmosphere samples listed by NASA ("Mars Rock Samples",
 *    sealed sol per sample); position = the last MMGIS M20 waypoint at or before that sol.
 *  - gale (Curiosity): the drill sites named by NASA/JPL in PIA21254 (date and sol per hole); position =
 *    the last MMGIS MSL waypoint at or before that sol.
 *  - gusev (Spirit) / meridiani (Opportunity): the PDS Geosciences Node MER Contact Science Target List
 *    (sol, feature, target, site and drive); position = the rover's position at that site and drive in the
 *    PDS corrected traverse (the target itself lies within a few metres of the rover).
 *
 * Usage: WORLD=jezero|gale|gusev|meridiani node scripts/extract-science-sites.mjs [traverse.csv] [targets.csv]
 *   The MER worlds need the PDS traverse table and the target list (downloaded whole).
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const R = 3396190;
const HERE = dirname(fileURLToPath(import.meta.url));
const rad = (d) => (d * Math.PI) / 180;
const deg = (r) => (r * 180) / Math.PI;

// NASA, "Mars Rock Samples" (Mars 2020 Perseverance), https://science.nasa.gov/mission/mars-2020-perseverance/mars-rock-samples/
// (retrieved 2026-11-15): sample, sealed sol, rock, region, type. Witness tubes are not science samples.
const M20_SAMPLES = [
  ['Roubion', 164, 'Roubion', 'Polygon Valley', 'atmospheric'],
  ['Montdenier', 194, 'Rochette', 'Artuby Ridge', 'rock core'],
  ['Montagnac', 196, 'Rochette', 'Artuby Ridge', 'rock core'],
  ['Salette', 262, 'Brac', 'South Séítah', 'rock core'],
  ['Coulettes', 271, 'Brac', 'South Séítah', 'rock core'],
  ['Robine', 298, 'Issole', 'South Séítah', 'rock core'],
  ['Malay', 337, 'Issole', 'South Séítah', 'rock core'],
  ["Ha'ahóni", 371, 'Sid', 'Octavia E. Butler Landing', 'rock core'],
  ['Atsá', 377, 'Sid', 'Octavia E. Butler Landing', 'rock core'],
  ['Swift Run', 490, 'Skinner Ridge', 'Delta Front', 'rock core'],
  ['Skyland', 495, 'Skinner Ridge', 'Delta Front', 'rock core'],
  ['Hazeltop', 509, 'Wildcat Ridge', 'Delta Front', 'rock core'],
  ['Bearwallow', 516, 'Wildcat Ridge', 'Delta Front', 'rock core'],
  ['Shuyak', 575, 'Amalik', 'Delta Front', 'rock core'],
  ['Mageik', 619, 'Amalik', 'Delta Front', 'rock core'],
  ['Kukaklek', 631, 'Hidden Harbor', 'Delta Front', 'rock core'],
  ['Atmo Mountain', 634, 'Observation Mountain', 'Delta Front', 'regolith'],
  ['Crosswind Lake', 639, 'Observation Mountain', 'Delta Front', 'regolith'],
];
// NASA/JPL PIA21254, "Curiosity's Rock or Soil Sampling Sites on Mars, Through November 2016" (drill holes, sol).
const MSL_DRILLS = [
  ['John Klein', 182], ['Cumberland', 279], ['Windjana', 621], ['Confidence Hills', 759], ['Mojave', 882],
  ['Telegraph Peak', 908], ['Buckskin', 1060], ['Big Sky', 1119], ['Greenhorn', 1137], ['Lubango', 1320],
  ['Okoruso', 1332], ['Oudam', 1361], ['Quela', 1464], ['Sebina', 1495],
];

const WORLDS = {
  jezero: { crop: 'ctx_crop.json', out: 'science_sites.json', mission: 'Perseverance', feed: 'https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json' },
  gale: { crop: 'gale/ctx_crop.json', out: 'gale/science_sites.json', mission: 'Curiosity', feed: 'https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json' },
  gusev: { crop: 'gusev/dem_crop.json', out: 'gusev/science_sites.json', mission: 'Spirit' },
  meridiani: { crop: 'meridiani/dem_crop.json', out: 'meridiani/science_sites.json', mission: 'Opportunity' },
};
const WORLD = process.env.WORLD;
const WD = WORLDS[WORLD];
if (!WD) throw new Error('set WORLD=jezero, gale, gusev or meridiani');

const { crop } = JSON.parse(readFileSync(join(HERE, 'data', WD.crop), 'utf8'));
const W = crop.cols * crop.resolution_m;
const H = crop.rows * crop.resolution_m;
const toLocal = (lat, lon) => ({ x: R * Math.cos(rad(crop.centre_lat_deg)) * rad(lon - crop.centre_lon_deg), y: R * rad(lat - crop.centre_lat_deg) });
const inside = (p) => p.x >= crop.origin_x_m && p.x <= crop.origin_x_m + W && p.y >= crop.origin_y_m && p.y <= crop.origin_y_m + H;
const sha = (t) => createHash('sha256').update(t).digest('hex');
// One CSV record, with double-quoted fields that may hold commas.
function csvRow(line) {
  const out = [];
  let cur = '';
  let q = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (q) {
      if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (ch === '"') q = false;
      else cur += ch;
    } else if (ch === '"') q = true;
    else if (ch === ',') { out.push(cur); cur = ''; }
    else cur += ch;
  }
  out.push(cur);
  return out;
}

const sites = [];
let source;
if (WORLD === 'jezero' || WORLD === 'gale') {
  const text = await (await fetch(WD.feed)).text();
  const feed = JSON.parse(text);
  const wps = feed.features.map((f) => ({ sol: f.properties.sol, rmc: f.properties.RMC, lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] })).sort((a, b) => a.sol - b.sol);
  const at = (sol) => wps.filter((w) => w.sol <= sol).at(-1) ?? null;
  const list = WORLD === 'jezero' ? M20_SAMPLES.map(([name, sol, rock, region, type]) => ({ name, sol, detail: `${type} sample of the rock ${rock}, ${region}`, kind: type === 'atmospheric' ? 'atmosphere' : 'sample' })) : MSL_DRILLS.map(([name, sol]) => ({ name, sol, detail: 'drill hole', kind: 'drill' }));
  for (const s of list) {
    const w = at(s.sol);
    if (!w) continue;
    const p = toLocal(w.lat, w.lon);
    if (!inside(p)) continue;
    sites.push({ id: s.name.toLowerCase().replace(/[^a-z0-9]+/g, '-'), name: s.name, kind: s.kind, detail: s.detail, sol: s.sol, rover_stop: w.rmc, rover_stop_sol: w.sol, lat_deg: Number(w.lat.toFixed(6)), lon_deg: Number(w.lon.toFixed(6)), x_m: Number(p.x.toFixed(2)), y_m: Number(p.y.toFixed(2)) });
  }
  source = WORLD === 'jezero'
    ? { list: 'NASA, Mars Rock Samples (Perseverance), sealed sol per sample', list_url: 'https://science.nasa.gov/mission/mars-2020-perseverance/mars-rock-samples/', position: 'Last MMGIS M20 waypoint at or before the sealed sol', position_url: WD.feed, position_sha256: sha(text) }
    : { list: "NASA/JPL PIA21254, Curiosity's Rock or Soil Sampling Sites on Mars, Through November 2016 (drill holes)", list_url: 'https://photojournal.jpl.nasa.gov/catalog/PIA21254', position: 'Last MMGIS MSL waypoint at or before the drill sol', position_url: WD.feed, position_sha256: sha(text) };
} else {
  const [, , travPath, targPath] = process.argv;
  if (!travPath || !targPath) throw new Error('MER worlds need <traverse.csv> <targets.csv>');
  const trav = readFileSync(travPath, 'utf8').trim().split(/\r?\n/);
  const th = trav[0].split(',');
  const tcol = (n) => th.indexOf(n);
  const pos = new Map();
  for (const line of trav.slice(1)) {
    const f = line.split(',');
    pos.set(`${Number(f[tcol('SITE')])}_${Number(f[tcol('DRIVE')])}`, [Number(f[tcol('CORRECTED_X')]), Number(f[tcol('CORRECTED_Y')])]);
  }
  const toLatLon = WORLD === 'gusev'
    ? (x, y) => [deg(y / R), 175.5 + deg(x / R)]
    : (x, y) => [-1.9462 + deg(y / R), -5.5266 + deg(x / (R * Math.cos(rad(-1.9462))))];
  const targText = readFileSync(targPath, 'utf8');
  const rows = targText.trim().split(/\r?\n/);
  const hh = csvRow(rows[0]);
  const col = (n) => hh.indexOf(n);
  const seen = new Set();
  for (const line of rows.slice(1)) {
    const f = csvRow(line);
    const feature = f[col('Feature')]?.trim();
    const key = `${Number(f[col('Site')])}_${Number(f[col('Drive')])}`;
    const xy = pos.get(key);
    if (!feature || !xy || seen.has(feature)) continue; // one site per feature, at its first contact-science sol
    const [lat, lon] = toLatLon(...xy);
    const p = toLocal(lat, lon);
    if (!inside(p)) continue;
    seen.add(feature);
    const type = f[col('Target Type')]?.trim().toLowerCase() || 'target';
    sites.push({ id: feature.toLowerCase().replace(/[^a-z0-9]+/g, '-'), name: feature.replace(/_/g, ' '), kind: 'contact_science', detail: `contact science on the ${type} target ${f[col('Target Name')].trim().replace(/_/g, ' ')}${f[col('Location')]?.trim() ? `, ${f[col('Location')].trim()}` : ''}`, sol: Number(f[col('Activity Sol')]), rover_stop: key, rover_stop_sol: null, lat_deg: Number(lat.toFixed(6)), lon_deg: Number(lon.toFixed(6)), x_m: Number(p.x.toFixed(2)), y_m: Number(p.y.toFixed(2)) });
  }
  source = { list: 'PDS Geosciences Node, MER Contact Science Target List (urn:nasa:pds:mer_cs_target_list), first contact-science sol per feature', list_url: `https://pds-geosciences.wustl.edu/mer/urn-nasa-pds-mer_cs_target_list/data/${WORLD === 'gusev' ? 'mera' : 'merb'}_cs_target_list.csv`, list_sha256: sha(targText), position: 'Rover position at the target\'s site and drive in the PDS corrected traverse', position_url: `https://an.rsl.wustl.edu/mera/AN/meri/MER/traverse/${WORLD === 'gusev' ? 'MERA_traverse.csv' : 'MERB_traverse_5130.csv'}`, position_sha256: sha(readFileSync(travPath, 'utf8')) };
}

const out = {
  note: `Real ${WD.mission} science sites inside the crop: where the rover sampled, drilled or did contact science, placed at the rover's own published position at the time (not the exact target, which lies a few metres away).`,
  mission: WD.mission,
  source: { ...source, retrieved: new Date().toISOString().slice(0, 10) },
  sites,
};
writeFileSync(join(HERE, 'data', WD.out), JSON.stringify(out, null, 1));
console.log(`${sites.length} real science sites inside the crop: ${sites.slice(0, 12).map((s) => `${s.name} (sol ${s.sol})`).join(', ')}${sites.length > 12 ? ', ...' : ''}`);
