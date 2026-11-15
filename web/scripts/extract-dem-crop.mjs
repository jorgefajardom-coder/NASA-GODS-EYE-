#!/usr/bin/env node
/**
 * Crops a local NASA DEM GeoTIFF onto the viewer's local ENU grid, for the worlds built from JPL Mars Trek
 * DEM products (Gusev, Elysium/InSight, Meridiani/Endeavour, Valles Marineris). Same output schema as
 * extract-ctx-crop.mjs and extract-gale-crop.mjs.
 *
 * The file must be in the Mars 2000 sphere equirectangular projection (standard parallel 0, central
 * meridian 0, metres) or in geographic degrees on that sphere, which is how Trek publishes these DEMs. A source finer than the output cell is box
 * averaged to the cell size first, so a 1 m DEM gives an honest 8 m terrain (no aliasing); every output
 * cell is then a bilinear sample at its centre. Nothing is stored but the crop.
 *
 * Trek files are downloaded whole from https://trek.nasa.gov/mars/TrekWS/rest/cat/data/stream?uuid=<item>
 * (the service does not answer range requests); the item, its title and its product page are passed in.
 *
 * Usage: CROP_LAT=.. CROP_LON=.. DEM_UUID=.. DEM_TITLE=".." DEM_LABEL=.. node scripts/extract-dem-crop.mjs <dem.tif> <out.json>
 *   Optional: CROP_RES (m, default 8), CROP_WIDTH_M / CROP_HEIGHT_M (default 3400 x 7600), DEM_NOTE.
 */
import { createHash } from 'node:crypto';
import { createReadStream, mkdirSync, statSync, writeFileSync } from 'node:fs';
import { basename, dirname } from 'node:path';
import { fromFile } from 'geotiff';

const [, , tifPath, outPath] = process.argv;
if (!tifPath || !outPath || !process.env.CROP_LAT || !process.env.CROP_LON) {
  console.error('usage: CROP_LAT=.. CROP_LON=.. node scripts/extract-dem-crop.mjs <dem.tif> <out.json>');
  process.exit(1);
}
const R = 3396190;
const RES = Number(process.env.CROP_RES ?? 8);
const COLS = Math.round(Number(process.env.CROP_WIDTH_M ?? 3400) / RES);
const ROWS = Math.round(Number(process.env.CROP_HEIGHT_M ?? 7600) / RES);
const OX = -(COLS * RES) / 2;
const OY = -(ROWS * RES) / 2;
const lat0Deg = Number(process.env.CROP_LAT);
const lon0Deg = Number(process.env.CROP_LON);
const uuid = process.env.DEM_UUID ?? null;

const img = await (await fromFile(tifPath)).getImage();
const keys = img.getGeoKeys();
// Projected equirectangular (metres) or geographic (degrees): on this sphere with standard parallel 0,
// degrees times R pi / 180 are the same equirectangular metres.
const geographic = keys.GTModelTypeGeoKey === 2;
if ((!geographic && keys.ProjCoordTransGeoKey !== 17) || Math.abs((keys.GeogSemiMajorAxisGeoKey ?? R) - R) > 1) throw new Error('expected an equirectangular or geographic DEM on the Mars 2000 sphere');
const unit = geographic ? (R * Math.PI) / 180 : 1;
const [west, south, east, north] = img.getBoundingBox().map((v) => v * unit);
const W = img.getWidth();
const H = img.getHeight();
const sx = (east - west) / W;
const sy = (north - south) / H;
const nodataValue = img.getGDALNoData();
const valid = (v) => Number.isFinite(v) && v > -1e30 && v !== nodataValue && v > -32000;

const rad = (d) => (d * Math.PI) / 180;
const lat0 = rad(lat0Deg);
const lon0 = rad(lon0Deg);
const llOf = (e, n) => {
  const lat = lat0 + n / R;
  return [lat, lon0 + e / (R * Math.cos(lat))];
};
const pxOf = (lat, lon) => [(R * lon - west) / sx - 0.5, (north - R * lat) / sy - 0.5];

// Source window covering the crop plus a margin.
const corners = [[OX, OY], [-OX, OY], [OX, -OY], [-OX, -OY]].map(([e, n]) => pxOf(...llOf(e, n)));
const c0 = Math.max(0, Math.floor(Math.min(...corners.map((p) => p[0]))) - 4);
const c1 = Math.min(W, Math.ceil(Math.max(...corners.map((p) => p[0]))) + 5);
const r0 = Math.max(0, Math.floor(Math.min(...corners.map((p) => p[1]))) - 4);
const r1 = Math.min(H, Math.ceil(Math.max(...corners.map((p) => p[1]))) + 5);
if (c1 <= c0 || r1 <= r0) throw new Error('the crop is outside the DEM');
console.log(`reading window ${c1 - c0} x ${r1 - r0} px at ${sx.toFixed(2)} m`);
const raw = await img.readRasters({ window: [c0, r0, c1, r1], interleave: true });

// Box average to about the output cell when the source is finer (k source pixels per side).
const k = Math.max(1, Math.floor(RES / sx));
const gw = Math.floor((c1 - c0) / k);
const gh = Math.floor((r1 - r0) / k);
const grid = new Float64Array(gw * gh).fill(NaN);
for (let gr = 0; gr < gh; gr++) {
  for (let gc = 0; gc < gw; gc++) {
    let s = 0;
    let n = 0;
    for (let j = 0; j < k; j++) {
      const row = (gr * k + j) * (c1 - c0);
      for (let i = 0; i < k; i++) {
        const v = raw[row + gc * k + i];
        if (valid(v)) {
          s += v;
          n++;
        }
      }
    }
    if (n >= (k * k) / 2) grid[gr * gw + gc] = s / n;
  }
}
// Grid cell (fractional) of a source pixel coordinate.
const toGrid = (fc, fr) => [(fc - c0 + 0.5) / k - 0.5, (fr - r0 + 0.5) / k - 0.5];
function bilinear(gx, gy) {
  const c = Math.floor(gx);
  const r = Math.floor(gy);
  if (c < 0 || r < 0 || c + 1 >= gw || r + 1 >= gh) return null;
  const tc = gx - c;
  const tr = gy - r;
  const a = grid[r * gw + c], b = grid[r * gw + c + 1], d = grid[(r + 1) * gw + c], e = grid[(r + 1) * gw + c + 1];
  if (![a, b, d, e].every(Number.isFinite)) return null;
  return a * (1 - tc) * (1 - tr) + b * tc * (1 - tr) + d * (1 - tc) * tr + e * tc * tr;
}

const heights = new Array(ROWS * COLS);
let nodata = 0;
for (let r = 0; r < ROWS; r++) {
  for (let c = 0; c < COLS; c++) {
    const [lat, lon] = llOf(OX + (c + 0.5) * RES, OY + (r + 0.5) * RES);
    const h = bilinear(...toGrid(...pxOf(lat, lon)));
    if (h == null) {
      heights[r * COLS + c] = null;
      nodata++;
    } else heights[r * COLS + c] = Math.round(h * 10) / 10;
  }
}
const ok = heights.filter((h) => h != null).sort((a, b) => a - b);
if (ok.length === 0) throw new Error('the crop has no data: check CROP_LAT / CROP_LON');
const median = ok[Math.floor(ok.length / 2)];

const sha = await new Promise((done, fail) => {
  const h = createHash('sha256');
  createReadStream(tifPath).on('data', (d) => h.update(d)).on('end', () => done(h.digest('hex'))).on('error', fail);
});
const label = process.env.DEM_LABEL ?? basename(tifPath, '.tif');
const crop = {
  note: `PROVISIONAL crop made by the frontend. Heights are metres above the datum of the source DEM.${process.env.DEM_NOTE ? ` ${process.env.DEM_NOTE}` : ''}`,
  source: {
    title: process.env.DEM_TITLE ?? label,
    file: `${label}.tif`,
    url: uuid ? `https://trek.nasa.gov/mars/TrekWS/rest/cat/data/stream?uuid=${uuid}` : null,
    product_page: 'https://trek.nasa.gov/mars/',
    provider: 'NASA JPL Mars Trek (USGS Astrogeology / HiRISE and CTX teams)',
    size_bytes: statSync(tifPath).size,
    sha256: sha,
    pixels: [W, H],
    native_resolution_m: Math.round(sx * 100) / 100,
    projection: geographic ? 'Geographic (degrees), Mars 2000 sphere IAU (R = 3396190 m)' : 'Equirectangular, standard parallel 0, central meridian 0, Mars 2000 sphere IAU (R = 3396190 m)',
    vertical: 'metres above the DEM datum',
    licence: 'Not verified here: NASA planetary data served by JPL Mars Trek, see the Trek product page for usage terms',
  },
  crop: {
    centre_pixel: { row: Math.round((north - R * lat0) / sy), col: Math.round((R * lon0 - west) / sx) },
    centre_lat_deg: Number(lat0Deg.toFixed(5)),
    centre_lon_deg: Number(lon0Deg.toFixed(5)),
    method: `${k > 1 ? `box average of ${k} x ${k} source pixels, then ` : ''}bilinear resampling onto a local tangent ENU grid (east = R cos(lat) dlon, north = R dlat); ${RES} m cells${sx >= RES ? ' from a coarser source: no resolution gain' : ''}`,
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
