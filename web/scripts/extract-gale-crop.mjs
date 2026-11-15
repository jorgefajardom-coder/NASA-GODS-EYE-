#!/usr/bin/env node
/**
 * Crops the NASA/USGS Mars Science Laboratory Gale crater DEM mosaic (1 m, v3) onto the viewer's
 * local ENU grid, for the Gale world (Curiosity). Same output schema as extract-ctx-crop.mjs.
 *
 * The 1 m mosaic is 3.7 GB, so only its published 8 m overview (the file's `.ovr`, tiled) is read, by
 * HTTP range requests: a few megabytes, nothing is stored but the crop. Each output cell is a cubic
 * (Catmull-Rom) sample of that 8 m overview, so with 8 m cells it adds no detail.
 *
 * Source (USGS Astrogeology, from NASA MRO HiRISE and CTX stereo, MSL Gale DEM mosaic v3):
 *   https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif
 *   (overviews in MSL_Gale_DEM_Mosaic_1m_v3.tif.ovr; level 1 is 8 m per pixel)
 *
 * Usage: GALE_LAT=-4.7253 GALE_LON=137.3865 node scripts/extract-gale-crop.mjs [out.json]
 *   Environment: GALE_LAT / GALE_LON (centre, degrees), CROP_RES (m, default 8; must match the overview),
 *   CROP_WIDTH_M / CROP_HEIGHT_M (default 3400 x 7600).
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { fromUrl } from 'geotiff';

const BASE = 'https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif';
const R = 3396190;
const RES = Number(process.env.CROP_RES ?? 8);
const WIDTH_M = Number(process.env.CROP_WIDTH_M ?? 3400);
const HEIGHT_M = Number(process.env.CROP_HEIGHT_M ?? 7600);
const COLS = Math.round(WIDTH_M / RES);
const ROWS = Math.round(HEIGHT_M / RES);
const OX = -(COLS * RES) / 2;
const OY = -(ROWS * RES) / 2;
const NODATA = -32767;
const OVERVIEW = 1; // 8 m per pixel
const lat0Deg = Number(process.env.GALE_LAT ?? -4.7253);
const lon0Deg = Number(process.env.GALE_LON ?? 137.3865);
const HERE = dirname(fileURLToPath(import.meta.url));
const outPath = process.argv[2] ?? join(HERE, 'data', 'gale', 'ctx_crop.json');

const main = await (await fromUrl(BASE)).getImage();
const [west, south, , north] = main.getBoundingBox();
const ovr = await fromUrl(`${BASE}.ovr`);
const img = await ovr.getImage(OVERVIEW);
const W = img.getWidth();
const H = img.getHeight();
const sx = main.getWidth() / W; // metres per overview pixel, east
const sy = main.getHeight() / H;
if (Math.abs(sx - RES) > 0.1 || Math.abs(sy - RES) > 0.1) throw new Error(`overview ${OVERVIEW} is ${sx} x ${sy} m per pixel, not ${RES} m`);

const rad = (d) => (d * Math.PI) / 180;
const lat0 = rad(lat0Deg);
const lon0 = rad(lon0Deg);
// Overview pixel of a projected point (x east, y north in metres on the Mars 2000 sphere).
const pxOf = (x, y) => [(x - west) / sx - 0.5, (north - y) / sy - 0.5];

// The window of overview pixels that covers the crop, with a margin for cubic sampling.
const corners = [[OX, OY], [OX + COLS * RES, OY], [OX, OY + ROWS * RES], [OX + COLS * RES, OY + ROWS * RES]].map(([e, n]) => {
  const lat = lat0 + n / R;
  const lon = lon0 + e / (R * Math.cos(lat));
  return pxOf(R * lon, R * lat);
});
const c0 = Math.max(0, Math.floor(Math.min(...corners.map((p) => p[0]))) - 3);
const c1 = Math.min(W, Math.ceil(Math.max(...corners.map((p) => p[0]))) + 4);
const r0 = Math.max(0, Math.floor(Math.min(...corners.map((p) => p[1]))) - 3);
const r1 = Math.min(H, Math.ceil(Math.max(...corners.map((p) => p[1]))) + 4);
console.log(`reading overview ${OVERVIEW} window ${c1 - c0} x ${r1 - r0} px (${(((c1 - c0) * (r1 - r0) * 4) / 1e6).toFixed(1)} MB)`);
const win = await img.readRasters({ window: [c0, r0, c1, r1], interleave: true });
const ww = c1 - c0;
const valid = (v) => v > -1e30 && v !== NODATA;

function bilinear(fc, fr) {
  const c = Math.floor(fc);
  const r = Math.floor(fr);
  if (c < c0 || r < r0 || c + 1 >= c1 || r + 1 >= r1) return null;
  const tc = fc - c;
  const tr = fr - r;
  const v = (rr, cc) => win[(rr - r0) * ww + (cc - c0)];
  const a = v(r, c), b = v(r, c + 1), d = v(r + 1, c), e = v(r + 1, c + 1);
  if (![a, b, d, e].every(valid)) return null;
  return a * (1 - tc) * (1 - tr) + b * tc * (1 - tr) + d * (1 - tc) * tr + e * tc * tr;
}
function cubic(fc, fr) {
  const c = Math.floor(fc);
  const r = Math.floor(fr);
  if (c - 1 < c0 || r - 1 < r0 || c + 2 >= c1 || r + 2 >= r1) return bilinear(fc, fr);
  const w = (t) => [(-t * t * t + 2 * t * t - t) / 2, (3 * t * t * t - 5 * t * t + 2) / 2, (-3 * t * t * t + 4 * t * t + t) / 2, (t * t * t - t * t) / 2];
  const wc = w(fc - c);
  const wr = w(fr - r);
  let sum = 0;
  for (let j = 0; j < 4; j++) {
    for (let i = 0; i < 4; i++) {
      const v = win[(r - 1 + j - r0) * ww + (c - 1 + i - c0)];
      if (!valid(v)) return bilinear(fc, fr);
      sum += wr[j] * wc[i] * v;
    }
  }
  return sum;
}

const heights = new Array(ROWS * COLS);
let nodata = 0;
for (let r = 0; r < ROWS; r++) {
  const lat = lat0 + (OY + (r + 0.5) * RES) / R;
  for (let c = 0; c < COLS; c++) {
    const lon = lon0 + (OX + (c + 0.5) * RES) / (R * Math.cos(lat));
    const [fc, fr] = pxOf(R * lon, R * lat);
    const h = cubic(fc, fr);
    if (h == null) {
      heights[r * COLS + c] = null;
      nodata++;
    } else heights[r * COLS + c] = Math.round(h * 10) / 10;
  }
}
const ok = heights.filter((h) => h != null).sort((a, b) => a - b);
if (ok.length === 0) throw new Error('the crop has no data: check GALE_LAT / GALE_LON');
const median = ok[Math.floor(ok.length / 2)];

const md5 = await fetch(`${BASE}.md5`).then((r) => (r.ok ? r.text() : '')).catch(() => '');
const crop = {
  note: 'PROVISIONAL crop made by the frontend. Heights are metres above the Mars datum of the MSL Gale DEM mosaic (v3).',
  source: {
    title: 'MSL Gale crater DEM mosaic, 1 m, v3 (MRO HiRISE and CTX stereo)',
    file: 'MSL_Gale_DEM_Mosaic_1m_v3.tif (overview level 1, 8 m per pixel, in MSL_Gale_DEM_Mosaic_1m_v3.tif.ovr)',
    url: BASE,
    product_page: 'https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_mosaic',
    provider: 'USGS Astrogeology Science Center / NASA',
    size_bytes: null,
    sha256: null,
    md5_of_full_file: md5.trim().split(/\s+/)[0] || null,
    pixels: [main.getWidth(), main.getHeight()],
    native_resolution_m: RES,
    mosaic_resolution_m: 1,
    projection: 'Equirectangular, standard parallel 0, central meridian 0, Mars 2000 sphere IAU (R = 3396190 m)',
    vertical: 'metres above the mosaic datum',
    licence: 'Not verified here: USGS-hosted NASA planetary data, see the product page for usage terms',
  },
  crop: {
    centre_pixel: { row: Math.round((north - R * lat0) / sy), col: Math.round((R * lon0 - west) / sx) },
    centre_lat_deg: Number(lat0Deg.toFixed(5)),
    centre_lon_deg: Number(lon0Deg.toFixed(5)),
    method: `bicubic (Catmull-Rom) resampling of the ${RES} m overview onto a local tangent ENU grid (east = R cos(lat) dlon, north = R dlat); ${RES} m cells, so no resolution gain`,
    origin_x_m: OX,
    origin_y_m: OY,
    resolution_m: RES,
    rows: ROWS,
    cols: COLS,
    nodata_cells: nodata,
    min_m: ok[0],
    max_m: ok[ok.length - 1],
    median_m: median,
    local_z_offset_m: Math.round(median),
  },
  heights,
};
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, JSON.stringify(crop));
console.log(`crop ${ROWS}x${COLS} at ${RES} m, centre ${crop.crop.centre_lat_deg}N ${crop.crop.centre_lon_deg}E`);
console.log(`elevation ${crop.crop.min_m}..${crop.crop.max_m} m (relief ${(crop.crop.max_m - crop.crop.min_m).toFixed(1)} m), NoData cells ${nodata}`);
console.log(`written ${outPath}`);
