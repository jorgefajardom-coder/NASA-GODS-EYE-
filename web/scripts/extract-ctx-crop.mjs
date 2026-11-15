#!/usr/bin/env node
/**
 * Extracts a 2 km x 2 km crop of the Mars 2020 TRN CTX DTM mosaic and resamples it
 * onto the local ENU grid defined by ICD-ROS2-V1 (frame `map`, x east, y north,
 * row 0 = south, 20 m cells).
 *
 * This is a PROVISIONAL crop made by the frontend so the viewer can show real terrain
 * while the data owner's processed package is pending. It does not replace it.
 *
 * Usage:
 *   node scripts/extract-ctx-crop.mjs <ctx.tif> <centre_row_px> <centre_col_px> [out.json]
 *   CROP_LAT=18.444 CROP_LON=77.4455 CROP_RES=4 node scripts/extract-ctx-crop.mjs <ctx.tif> - - [out.json]
 *
 * Environment: CROP_LAT / CROP_LON (degrees, replace the centre pixel arguments when set) and
 * CROP_RES (output cell size in metres, default 20; the crop stays 2 km wide). An output cell
 * smaller than the 20 m source is a display resampling: it adds no detail.
 *
 * Source (USGS Astrogeology, NASA Mars 2020 Terrain Relative Navigation CTX DTM mosaic):
 *   https://astrogeology.usgs.gov/search/map/mars_2020_terrain_relative_navigation_ctx_dtm_mosaic
 *   https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif
 *   DOI of the CTX DTM product family: https://doi.org/10.5066/P906QQT8
 *
 * Method: Equirectangular projection on the Mars 2000 sphere (R = 3,396,190 m, standard
 * parallel 0, central meridian 0). Each target cell centre is placed with a local tangent
 * approximation (east = R cos(lat) dlon, north = R dlat) and the DEM is sampled with
 * bilinear interpolation. The native resolution is 20 m, so this adds no detail.
 */
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { fromFile } from 'geotiff';

const [, , tifPath, rowArg, colArg, outArg] = process.argv;
if (!tifPath || ((rowArg == null || colArg == null) && !process.env.CROP_LAT)) {
  console.error('usage: node scripts/extract-ctx-crop.mjs <ctx.tif> <centre_row_px> <centre_col_px> [out.json]');
  process.exit(1);
}

const R = 3396190; // Mars 2000 sphere, m
const NATIVE_M = 20;
const RES = Number(process.env.CROP_RES ?? 20); // output cell size, m (below 20 m it is a resampling: no resolution gain)
const SPAN_M = 2000;
const ROWS = Math.round(SPAN_M / RES);
const COLS = Math.round(SPAN_M / RES);
const OX = -(COLS * RES) / 2;
const OY = -(ROWS * RES) / 2;
const NODATA_LIMIT = -1e30;

const here = dirname(fileURLToPath(import.meta.url));
const outPath = outArg ?? join(here, 'data', 'ctx_crop.json');

const tiff = await fromFile(tifPath);
const img = await tiff.getImage();
const W = img.getWidth();
const H = img.getHeight();
const [west, , , north] = img.getBoundingBox();
// The centre comes from CROP_LAT / CROP_LON when set (equirectangular on the Mars 2000 sphere), else from the pixel arguments.
const rowC = process.env.CROP_LAT ? Math.round((north - (R * Number(process.env.CROP_LAT) * Math.PI) / 180) / NATIVE_M - 0.5) : Number(rowArg);
const colC = process.env.CROP_LON ? Math.round(((R * Number(process.env.CROP_LON) * Math.PI) / 180 - west) / NATIVE_M - 0.5) : Number(colArg);

// Centre of the crop in projected metres, then planetocentric lat/lon.
const xC = west + (colC + 0.5) * NATIVE_M;
const yC = north - (rowC + 0.5) * NATIVE_M;
const lat0 = yC / R;
const lon0 = xC / R;

// Read a window that surely covers the crop (plus margin for bilinear sampling).
const half = Math.ceil((COLS * RES) / 2 / NATIVE_M / Math.cos(lat0)) + 4;
const c0 = Math.max(0, colC - half);
const c1 = Math.min(W, colC + half + 1);
const r0 = Math.max(0, rowC - half);
const r1 = Math.min(H, rowC + half + 1);
const win = await img.readRasters({ window: [c0, r0, c1, r1], interleave: true });
const ww = c1 - c0;

function sample(fc, fr) {
  const c = Math.floor(fc);
  const r = Math.floor(fr);
  if (c < c0 || r < r0 || c + 1 >= c1 || r + 1 >= r1) return null;
  const tc = fc - c;
  const tr = fr - r;
  const v = (rr, cc) => win[(rr - r0) * ww + (cc - c0)];
  const a = v(r, c);
  const b = v(r, c + 1);
  const d = v(r + 1, c);
  const e = v(r + 1, c + 1);
  if ([a, b, d, e].some((x) => !(x > NODATA_LIMIT))) return null;
  return a * (1 - tc) * (1 - tr) + b * tc * (1 - tr) + d * (1 - tc) * tr + e * tc * tr;
}

const heights = new Array(ROWS * COLS);
let nodata = 0;
for (let r = 0; r < ROWS; r++) {
  const north_m = OY + (r + 0.5) * RES;
  const lat = lat0 + north_m / R;
  for (let c = 0; c < COLS; c++) {
    const east_m = OX + (c + 0.5) * RES;
    const lon = lon0 + east_m / (R * Math.cos(lat));
    const x = R * lon;
    const y = R * lat;
    const fc = (x - west) / NATIVE_M - 0.5;
    const fr = (north - y) / NATIVE_M - 0.5;
    const h = sample(fc, fr);
    if (h == null) {
      heights[r * COLS + c] = null;
      nodata++;
    } else {
      heights[r * COLS + c] = Math.round(h * 10) / 10;
    }
  }
}

const valid = heights.filter((h) => h != null).sort((a, b) => a - b);
const median = valid[Math.floor(valid.length / 2)];
const deg = (rad) => (rad * 180) / Math.PI;

const crop = {
  note: 'PROVISIONAL crop made by the frontend; the data owner delivers the processed package. Heights are metres above the MOLA areoid (DeltaGeoid product).',
  source: {
    title: 'Mars 2020 Terrain Relative Navigation CTX DTM mosaic',
    file: basename(tifPath).replace(/^.*[\\/]/, '') === 'ctx.tif' ? 'JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif' : basename(tifPath),
    url: 'https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif',
    product_page: 'https://astrogeology.usgs.gov/search/map/mars_2020_terrain_relative_navigation_ctx_dtm_mosaic',
    doi_family: 'https://doi.org/10.5066/P906QQT8',
    provider: 'USGS Astrogeology Science Center / NASA',
    size_bytes: readFileSync(tifPath).length,
    sha256: createHash('sha256').update(readFileSync(tifPath)).digest('hex'),
    pixels: [W, H],
    native_resolution_m: NATIVE_M,
    projection: 'Equirectangular, standard parallel 0, central meridian 0, Mars 2000 sphere IAU (R = 3396190 m)',
    vertical: 'metres above the MOLA areoid',
    licence: 'Not verified here: USGS-hosted NASA planetary data, see the product page for usage terms',
  },
  crop: {
    centre_pixel: { row: rowC, col: colC },
    centre_lat_deg: Number(deg(lat0).toFixed(5)),
    centre_lon_deg: Number(deg(lon0).toFixed(5)),
    method: `bilinear resampling onto a local tangent ENU grid (east = R cos(lat) dlon, north = R dlat); ${RES} m cells from a ${NATIVE_M} m source, so no resolution gain${RES < NATIVE_M ? ' (display resampling)' : ''}`,
    origin_x_m: OX,
    origin_y_m: OY,
    resolution_m: RES,
    rows: ROWS,
    cols: COLS,
    nodata_cells: nodata,
    min_m: valid[0],
    max_m: valid[valid.length - 1],
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
