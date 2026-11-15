#!/usr/bin/env node
/**
 * Perseverance's Three Forks sample depot (Jezero) in the demo crop's local frame: the ten sample tubes the
 * rover set down on the ground for a later retrieval, each at the rover's published position during the
 * drop (latitude, longitude, elevation, site/drive) and with the tube's measured azimuth.
 *
 * Source: PDS Geosciences Node, Mars 2020 Three Forks Sample Depot bundle
 *   (urn:nasa:pds:mars2020_sample_depot_three_forks), miscellaneous/sample_metadata/sample_tube_locations.csv
 *   https://pds-geosciences.wustl.edu/m2020/urn-nasa-pds-mars2020_sample_depot_three_forks/
 *
 * Usage: node scripts/extract-three-forks.mjs <sample_tube_locations.csv> [out.json]
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const R = 3396190;
const HERE = dirname(fileURLToPath(import.meta.url));
const [, , csvPath, outArg] = process.argv;
if (!csvPath) throw new Error('usage: node scripts/extract-three-forks.mjs <sample_tube_locations.csv> [out.json]');
const outPath = outArg ?? join(HERE, 'data', 'three_forks_depot.json');
const { crop } = JSON.parse(readFileSync(join(HERE, 'data', 'ctx_crop.json'), 'utf8'));
const rad = (d) => (d * Math.PI) / 180;

const text = readFileSync(csvPath, 'utf8');
const [head, ...rows] = text.trim().split(/\r?\n/);
const h = head.split(',');
const col = (n) => h.indexOf(n);
const tubes = rows.map((line) => {
  const f = line.split(',');
  const lat = Number(f[col('Rover Latitude')]);
  const lon = Number(f[col('Rover Longitude')]);
  return {
    designation: f[col('Sample Designation')],
    name: f[col('Sample Name')],
    dropoff_sol: Number(f[col('Dropoff Sol')]),
    rover_stop: `${Number(f[col('Site')])}_${Number(f[col('Drive')])}`,
    lat_deg: lat,
    lon_deg: lon,
    elevation_m: Number(f[col('Rover Elevation')]),
    tube_azimuth_deg: Number(f[col('Sample Tube Azimuth')]),
    x_m: Number((R * Math.cos(rad(crop.centre_lat_deg)) * rad(lon - crop.centre_lon_deg)).toFixed(2)),
    y_m: Number((R * rad(lat - crop.centre_lat_deg)).toFixed(2)),
  };
});
const out = {
  note: "Perseverance's Three Forks sample depot: rover position at each tube drop (the tube lies within about a metre or two of the rover). Positions and identifiers only.",
  source: {
    title: 'PDS Geosciences Node, Mars 2020 Three Forks Sample Depot, sample_tube_locations.csv',
    bundle: 'urn:nasa:pds:mars2020_sample_depot_three_forks',
    url: 'https://pds-geosciences.wustl.edu/m2020/urn-nasa-pds-mars2020_sample_depot_three_forks/miscellaneous/sample_metadata/sample_tube_locations.csv',
    sha256: createHash('sha256').update(text).digest('hex'),
    retrieved: new Date().toISOString().slice(0, 10),
  },
  centre: {
    x_m: Number((tubes.reduce((s, t) => s + t.x_m, 0) / tubes.length).toFixed(2)),
    y_m: Number((tubes.reduce((s, t) => s + t.y_m, 0) / tubes.length).toFixed(2)),
  },
  tubes,
};
writeFileSync(outPath, JSON.stringify(out, null, 1));
console.log(`${tubes.length} tubes, sols ${tubes[0].dropoff_sol}..${tubes.at(-1).dropoff_sol}, centre ${out.centre.x_m}, ${out.centre.y_m} m`);
