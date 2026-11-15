#!/usr/bin/env node
/**
 * Real Spirit (MER-A) or Opportunity (MER-B) stops inside a world's crop, from the PDS Geosciences Node
 * interpolated traverse tables (one record per rover drive: site, drive, sols and the science team's
 * corrected position). Same output schema as extract-rover-waypoints.mjs, thinned the same way.
 *
 * Coordinates, as the tables' PDS labels describe them:
 *  - Spirit (MERA_traverse.csv): corrected x/y in metres in the Mars equirectangular projection centred
 *    at 175.5 E, 0 N (sphere R = 3396190 m), so lat = y / R and lon = 175.5 + x / R.
 *  - Opportunity (MERB_traverse_5130.csv): corrected x (east) and y (north) in metres from the landing
 *    site, which is placed at NASA's published landing coordinates (1.9462 S, 354.4734 E). This tie is
 *    the frontend's assumption; positions may be off by tens of metres.
 *
 * MER raw images are archived in the PDS, not in NASA's raw-image feed the viewer reads, so the stops
 * carry `image_match: 'none'`: the tour visits them and says no image feed exists for this mission.
 *
 * Source: https://an.rsl.wustl.edu/mera/AN/pages/mer/mer_traverse.htm (tables under
 *   https://an.rsl.wustl.edu/mera/AN/meri/MER/traverse/), PDS Geosciences Node, Washington University.
 *
 * Usage: WORLD=gusev|meridiani node scripts/extract-mer-traverse.mjs <traverse.csv> [out.json]
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const R = 3396190;
const HERE = dirname(fileURLToPath(import.meta.url));
const BASE = 'https://an.rsl.wustl.edu/mera/AN/meri/MER/traverse/';
const WORLDS = {
  gusev: {
    file: 'MERA_traverse.csv', crop: 'gusev/dem_crop.json', out: 'gusev/rover_waypoints.json', spacing: 40,
    mission: { id: 'mer2', name: 'Spirit', raw_category: 'none', image_match: 'none' },
    title: 'Spirit (MER-A) interpolated traverse, PDS Geosciences Node',
    toLatLon: (x, y) => [((y / R) * 180) / Math.PI, 175.5 + ((x / R) * 180) / Math.PI],
  },
  meridiani: {
    file: 'MERB_traverse_5130.csv', crop: 'meridiani/dem_crop.json', out: 'meridiani/rover_waypoints.json', spacing: 80,
    mission: { id: 'mer1', name: 'Opportunity', raw_category: 'none', image_match: 'none' },
    title: 'Opportunity (MER-B) interpolated traverse, PDS Geosciences Node',
    toLatLon: (x, y) => {
      const lat0 = -1.9462;
      return [lat0 + ((y / R) * 180) / Math.PI, -5.5266 + ((x / (R * Math.cos((lat0 * Math.PI) / 180))) * 180) / Math.PI];
    },
  },
};
const WD = WORLDS[process.env.WORLD];
if (!WD) throw new Error('set WORLD=gusev or WORLD=meridiani');
const [, , csvPath, outArg] = process.argv;
if (!csvPath) throw new Error('usage: WORLD=.. node scripts/extract-mer-traverse.mjs <traverse.csv> [out.json]');
const outPath = outArg ?? join(HERE, 'data', WD.out);

const { crop } = JSON.parse(readFileSync(join(HERE, 'data', WD.crop), 'utf8'));
const lat0 = crop.centre_lat_deg;
const lon0 = crop.centre_lon_deg;
const W = crop.cols * crop.resolution_m;
const H = crop.rows * crop.resolution_m;
const rad = (d) => (d * Math.PI) / 180;

const text = readFileSync(csvPath, 'utf8');
const [head, ...lines] = text.trim().split(/\r?\n/);
const cols = head.split(',');
const at = (name) => cols.indexOf(name);
const stops = [];
let total = 0;
let lastPos = null;
for (const line of lines) {
  const f = line.split(',');
  const x = Number(f[at('CORRECTED_X')]);
  const y = Number(f[at('CORRECTED_Y')]);
  if (lastPos) total += Math.hypot(x - lastPos[0], y - lastPos[1]);
  lastPos = [x, y];
  const [lat, lon] = WD.toLatLon(x, y);
  const e = R * Math.cos(rad(lat0)) * rad(lon - lon0);
  const n = R * rad(lat - lat0);
  if (e < crop.origin_x_m || e > crop.origin_x_m + W || n < crop.origin_y_m || n > crop.origin_y_m + H) continue;
  const site = Number(f[at('SITE')]);
  const drive = Number(f[at('DRIVE')]);
  stops.push({
    rmc: `${site}_${drive}`,
    site,
    drive,
    sol: Number(f[at('END_SOL')]),
    lat_deg: Number(lat.toFixed(6)),
    lon_deg: Number(lon.toFixed(6)),
    x_m: Number(e.toFixed(2)),
    y_m: Number(n.toFixed(2)),
    total_distance_m: Math.round(total),
  });
}
const all = stops.length;
const kept = [];
for (const st of stops) {
  const last = kept.at(-1);
  if (!last || Math.hypot(st.x_m - last.x_m, st.y_m - last.y_m) >= WD.spacing) kept.push(st);
}

const out = {
  note: `Real ${WD.mission.name} stops inside the crop, thinned to at least ${WD.spacing} m apart (${kept.length} of ${all} drives in the crop) (position and identifiers only). Positions are the science team's corrected traverse, interpolated by the PDS Geosciences Node.${process.env.WORLD === 'meridiani' ? ' The traverse is tied to the published landing coordinates by the frontend: positions may be off by tens of metres.' : ''} NASA's raw-image feed has no MER images, so none is shown at these stops.`,
  mission: WD.mission,
  source: {
    title: WD.title,
    url: BASE + WD.file,
    credit: 'NASA/JPL-Caltech, PDS Geosciences Node (Washington University in St. Louis)',
    feed_name: WD.file,
    feed_sha256: createHash('sha256').update(text).digest('hex'),
    retrieved: new Date().toISOString().slice(0, 10),
  },
  crop: { centre_lat_deg: lat0, centre_lon_deg: lon0, origin_x_m: crop.origin_x_m, origin_y_m: crop.origin_y_m, width_m: W, height_m: H },
  stops: kept,
};
writeFileSync(outPath, JSON.stringify(out));
console.log(`${kept.length} stops inside the crop (of ${all}), sols ${kept[0]?.sol}..${kept.at(-1)?.sol}`);
console.log(`written ${outPath}`);
