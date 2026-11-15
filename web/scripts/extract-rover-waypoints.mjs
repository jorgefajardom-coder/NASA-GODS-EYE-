#!/usr/bin/env node
/**
 * Real Perseverance stops inside the demo crop, from NASA's public traverse feed (MMGIS M20
 * waypoints: one point per rover stop with its sol, site, drive, latitude and longitude).
 *
 * Only the stops that fall inside the crop are kept, converted to the crop's local ENU frame with the
 * same tangent approximation as extract-ctx-crop.mjs. Each stop is identified by its RMC
 * (`<site>_<drive>`), which is also how the raw-image feed labels where an image was taken, so the
 * viewer can ask NASA for the images of that stop when the person is standing there. No image is
 * downloaded or stored here, only the position and identifiers.
 *
 * Source: https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json (NASA/JPL-Caltech).
 *
 * Usage: node scripts/extract-rover-waypoints.mjs [out.json]
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const URL_WAYPOINTS = 'https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json';
const R = 3396190;
const HERE = dirname(fileURLToPath(import.meta.url));
const outPath = process.argv[2] ?? join(HERE, 'data', 'rover_waypoints.json');

const { crop } = JSON.parse(readFileSync(join(HERE, 'data', 'ctx_crop.json'), 'utf8'));
const lat0 = crop.centre_lat_deg;
const lon0 = crop.centre_lon_deg;
const W = crop.cols * crop.resolution_m;
const H = crop.rows * crop.resolution_m;

const res = await fetch(URL_WAYPOINTS);
if (!res.ok) throw new Error(`waypoints feed answered ${res.status}`);
const text = await res.text();
const feed = JSON.parse(text);

const rad = (d) => (d * Math.PI) / 180;
const stops = [];
for (const f of feed.features) {
  const p = f.properties;
  const [lon, lat] = f.geometry.coordinates;
  const x = R * Math.cos(rad(lat0)) * rad(lon - lon0);
  const y = R * rad(lat - lat0);
  if (x < crop.origin_x_m || x > crop.origin_x_m + W || y < crop.origin_y_m || y > crop.origin_y_m + H) continue;
  stops.push({
    rmc: p.RMC,
    site: p.site,
    drive: p.drive,
    sol: p.sol,
    lat_deg: Number(lat.toFixed(6)),
    lon_deg: Number(lon.toFixed(6)),
    x_m: Number(x.toFixed(2)),
    y_m: Number(y.toFixed(2)),
    elev_geoid_m: p.elev_geoid,
    yaw_deg: p.yaw,
    total_distance_m: p.dist_total_m,
  });
}
stops.sort((a, b) => a.sol - b.sol || a.drive - b.drive);

const out = {
  note: 'Real Perseverance stops inside the crop (position and identifiers only; no image is stored). Positions are the rover stop positions published by NASA.',
  source: {
    title: 'Mars 2020 Perseverance waypoints (MMGIS M20)',
    url: URL_WAYPOINTS,
    credit: 'NASA/JPL-Caltech',
    feed_name: feed.name,
    feed_sha256: createHash('sha256').update(text).digest('hex'),
    retrieved: new Date().toISOString().slice(0, 10),
  },
  crop: { centre_lat_deg: lat0, centre_lon_deg: lon0, origin_x_m: crop.origin_x_m, origin_y_m: crop.origin_y_m, width_m: W, height_m: H },
  stops,
};
writeFileSync(outPath, JSON.stringify(out));
console.log(`${stops.length} stops inside the crop, sols ${stops[0]?.sol}..${stops.at(-1)?.sol}`);
console.log(`written ${outPath}`);
