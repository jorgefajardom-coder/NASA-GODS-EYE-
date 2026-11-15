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

// `WORLD=jezero` (default, Perseverance) or `WORLD=gale` (Curiosity). Gale has 1,389 stops over 12 years, so
// they are thinned: a stop is kept only if it is at least `spacing` metres from the last one kept (in sol order).
const WORLD = process.env.WORLD ?? 'jezero';
const WORLDS = {
  jezero: { url: 'https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json', title: 'Mars 2020 Perseverance waypoints (MMGIS M20)', mission: { id: 'mars2020', name: 'Perseverance', raw_category: 'mars2020', image_match: 'stop' }, crop: 'ctx_crop.json', out: 'rover_waypoints.json', spacing: 0 },
  gale: { url: 'https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json', title: 'Mars Science Laboratory Curiosity waypoints (MMGIS MSL)', mission: { id: 'msl', name: 'Curiosity', raw_category: 'msl', image_match: 'sol' }, crop: 'gale/ctx_crop.json', out: 'gale/rover_waypoints.json', spacing: 80 },
};
const WD = WORLDS[WORLD];
if (!WD) throw new Error(`unknown WORLD ${WORLD}`);
const URL_WAYPOINTS = WD.url;
const R = 3396190;
const HERE = dirname(fileURLToPath(import.meta.url));
const outPath = process.argv[2] ?? join(HERE, 'data', WD.out);

const { crop } = JSON.parse(readFileSync(join(HERE, 'data', WD.crop), 'utf8'));
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
const all = stops.length;
if (WD.spacing > 0) {
  const kept = [];
  for (const st of stops) {
    const last = kept.at(-1);
    if (!last || Math.hypot(st.x_m - last.x_m, st.y_m - last.y_m) >= WD.spacing) kept.push(st);
  }
  stops.length = 0;
  stops.push(...kept);
}

const out = {
  note: `Real ${WD.mission.name} stops inside the crop${WD.spacing > 0 ? `, thinned to at least ${WD.spacing} m apart (${stops.length} of ${all} in the crop)` : ''} (position and identifiers only; no image is stored). Positions are the rover stop positions published by NASA.`,
  mission: WD.mission,
  source: {
    title: WD.title,
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
