#!/usr/bin/env node
/**
 * Context terrain around the 2 km demo crop: a larger square of the same Mars 2020 TRN CTX
 * DTM mosaic (USGS Astrogeology / NASA, DOI family https://doi.org/10.5066/P906QQT8), on the
 * crop's local ENU frame (same centre and z offset), at a coarser cell size.
 *
 * It only gives the crop surroundings so the scene is not an island in a void. It is not part
 * of the mission map: the planner, the mission and the uncertainty layers never use it.
 *
 * Method: each output cell is the mean of a 5 x 5 grid of bilinear samples spread over its
 * footprint (box average of the 20 m source), so heights are real values averaged, not
 * interpolated detail. Cells that touch source NoData are null (no fill).
 *
 * Usage: node scripts/extract-ctx-context.mjs <ctx.tif> [out.json] [extent_m=20000] [cell_m=100]
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { fromFile } from 'geotiff';

const [, , tifPath, outArg, extentArg, cellArg] = process.argv;
if (!tifPath) {
  console.error('usage: node scripts/extract-ctx-context.mjs <ctx.tif> [out.json] [extent_m] [cell_m]');
  process.exit(1);
}
const HERE = dirname(fileURLToPath(import.meta.url));
const outPath = outArg ?? join(HERE, '..', 'public', 'replay', 'demo', 'context.json');
const EXTENT = Number(extentArg ?? 20000);
const CELL = Number(cellArg ?? 100);
const N = Math.round(EXTENT / CELL);
const SUB = 5;
const R = 3396190;
const NATIVE_M = 20;
const NODATA_LIMIT = -1e30;

const crop = JSON.parse(readFileSync(join(HERE, 'data', 'ctx_crop.json'), 'utf8'));
const lat0 = (crop.crop.centre_lat_deg * Math.PI) / 180;
const lon0 = (crop.crop.centre_lon_deg * Math.PI) / 180;
const zOffset = crop.crop.local_z_offset_m;

const bytes = readFileSync(tifPath);
const sha256 = createHash('sha256').update(bytes).digest('hex');
if (sha256 !== crop.source.sha256) throw new Error(`source hash ${sha256} differs from the crop's ${crop.source.sha256}`);

const tiff = await fromFile(tifPath);
const img = await tiff.getImage();
const W = img.getWidth();
const H = img.getHeight();
const [west, , , north] = img.getBoundingBox();
const ras = await img.readRasters({ interleave: true });

function sample(fc, fr) {
  const c = Math.floor(fc);
  const r = Math.floor(fr);
  if (c < 0 || r < 0 || c + 1 >= W || r + 1 >= H) return null;
  const tc = fc - c;
  const tr = fr - r;
  const v = (rr, cc) => ras[rr * W + cc];
  const a = v(r, c), b = v(r, c + 1), d = v(r + 1, c), e = v(r + 1, c + 1);
  if ([a, b, d, e].some((x) => !(x > NODATA_LIMIT))) return null;
  return a * (1 - tc) * (1 - tr) + b * tc * (1 - tr) + d * (1 - tc) * tr + e * tc * tr;
}

function heightAt(east, northM) {
  const lat = lat0 + northM / R;
  const lon = lon0 + east / (R * Math.cos(lat));
  return sample((R * lon - west) / NATIVE_M - 0.5, (north - R * lat) / NATIVE_M - 0.5);
}

const OX = -EXTENT / 2;
const OY = -EXTENT / 2;
const heights = new Array(N * N);
let nodata = 0;
for (let r = 0; r < N; r++) {
  for (let c = 0; c < N; c++) {
    let sum = 0;
    let ok = true;
    for (let j = 0; j < SUB && ok; j++) {
      for (let i = 0; i < SUB; i++) {
        const h = heightAt(OX + (c + (i + 0.5) / SUB) * CELL, OY + (r + (j + 0.5) / SUB) * CELL);
        if (h == null) {
          ok = false;
          break;
        }
        sum += h;
      }
    }
    if (!ok) {
      heights[r * N + c] = null;
      nodata++;
    } else {
      heights[r * N + c] = Math.round((sum / (SUB * SUB) - zOffset) * 10) / 10;
    }
  }
}

const valid = heights.filter((h) => h != null);
const out = {
  note: 'Context only: surroundings of the 2 km crop from the same CTX DTM, box-averaged to a coarser cell. Not part of the mission map; never read by the planner or mission.',
  source: { ...crop.source },
  frame: {
    centre_lat_deg: crop.crop.centre_lat_deg,
    centre_lon_deg: crop.crop.centre_lon_deg,
    origin_x_m: OX,
    origin_y_m: OY,
    resolution_m: CELL,
    rows: N,
    cols: N,
    row0: 'south',
    local_z_offset_m: zOffset,
    method: `mean of ${SUB} x ${SUB} bilinear samples per cell over the ${NATIVE_M} m source (box average); NoData cells left null`,
  },
  nodata_cells: nodata,
  min_local_m: Math.min(...valid),
  max_local_m: Math.max(...valid),
  heights,
};
writeFileSync(outPath, JSON.stringify(out) + '\n');
console.log(`written ${outPath}: ${N} x ${N} cells of ${CELL} m, ${nodata} NoData, local ${out.min_local_m}..${out.max_local_m} m`);
