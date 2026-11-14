#!/usr/bin/env node
/**
 * Reads the 2 km x 2 km window of the Mars 2020 TRN HiRISE DTM mosaic that matches the CTX crop
 * (same centre, same local ENU frame) WITHOUT downloading the whole 1.8 GB file.
 *
 * The mosaic is stored as uncompressed 32-bit float rows (one strip per row, contiguous), so
 * only the bytes of the window are requested with HTTP Range, about 2,200 requests of ~9 KB.
 *
 * HiRISE is the hidden evaluator reference: the viewer shows it only in the evaluator view or
 * where an agent observation reveals it. It is never part of the orbital map the agent starts with.
 *
 * Source (USGS Astrogeology, NASA Mars 2020 Terrain Relative Navigation HiRISE DTM mosaic):
 *   https://astrogeology.usgs.gov/search/map/mars_2020_terrain_relative_navigation_hirise_dtm_mosaic
 *   https://planetarymaps.usgs.gov/mosaic/mars2020_trn/HiRISE/JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif
 *
 * Method: same projection and local tangent approximation as extract-ctx-crop.mjs. Each output
 * cell is the mean of 5 x 5 samples (bilinear) spread over the cell footprint, which keeps the
 * relief of 1 m data at the chosen cell size (default 5 m) without aliasing.
 *
 * Usage: node scripts/extract-hirise-crop.mjs [out.json] [cell_size_m]
 */
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { fromUrl } from 'geotiff';

const URL_TIF = 'https://planetarymaps.usgs.gov/mosaic/mars2020_trn/HiRISE/JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif';
const HERE = dirname(fileURLToPath(import.meta.url));
const outPath = process.argv[2] ?? join(HERE, 'data', 'hirise_crop.json');
const RES = Number(process.argv[3] ?? 5);
const R = 3396190;
const NODATA_LIMIT = -1e30;

// Same crop centre and extent as the CTX crop, so both grids share one local frame.
const ctx = JSON.parse(readFileSync(join(HERE, 'data', 'ctx_crop.json'), 'utf8'));
const lat0 = (ctx.crop.centre_lat_deg * Math.PI) / 180;
const lon0 = (ctx.crop.centre_lon_deg * Math.PI) / 180;
const EXTENT = ctx.crop.rows * ctx.crop.resolution_m; // 2000 m
const ROWS = Math.round(EXTENT / RES);
const COLS = ROWS;
const OX = ctx.crop.origin_x_m;
const OY = ctx.crop.origin_y_m;

const tiff = await fromUrl(URL_TIF, { allowFullFile: false, blockSize: 65536, cacheSize: 4 });
const img = await tiff.getImage(0);
const W = img.getWidth();
const H = img.getHeight();
const [west, south, east, north] = img.getBoundingBox();
const fd = img.getFileDirectory();
const offsets = await fd.StripOffsets;
const rowBytes = W * 4;
if (img.getSampleFormat() !== 3 || img.getBitsPerSample() !== 32 || !tiff.littleEndian) throw new Error('unexpected sample layout');
if (offsets.length !== H || offsets[1] - offsets[0] !== rowBytes) throw new Error('unexpected strip layout');

// Window in source pixels that covers the crop with a small margin.
const half = Math.ceil(EXTENT / 2 / Math.cos(lat0)) + 8;
const xC = (R * lon0 - west) / 1;
const yC = (north - R * lat0) / 1;
const c0 = Math.max(0, Math.floor(xC - half));
const c1 = Math.min(W, Math.ceil(xC + half));
const r0 = Math.max(0, Math.floor(yC - half));
const r1 = Math.min(H, Math.ceil(yC + half));
if (xC - half < 0 || yC - half < 0 || xC + half > W || yC + half > H) throw new Error('the crop window is not fully inside the HiRISE mosaic');
const ww = c1 - c0;
const hh = r1 - r0;
console.log(`window ${ww} x ${hh} px (${((ww * hh * 4) / 1e6).toFixed(1)} MB), rows ${r0}..${r1}, cols ${c0}..${c1}`);

const win = new Float32Array(ww * hh);
const hash = createHash('sha256');
let fetched = 0;
let requests = 0;
async function getRow(r) {
  const start = offsets[r] + c0 * 4;
  const end = offsets[r] + c1 * 4 - 1;
  for (let attempt = 0; ; attempt++) {
    try {
      const res = await fetch(URL_TIF, { headers: { Range: `bytes=${start}-${end}` } });
      if (res.status !== 206) throw new Error(`HTTP ${res.status}`);
      const buf = Buffer.from(await res.arrayBuffer());
      if (buf.length !== ww * 4) throw new Error(`short read ${buf.length}`);
      requests++;
      fetched += buf.length;
      return buf;
    } catch (e) {
      if (attempt >= 3) throw e;
      await new Promise((s) => setTimeout(s, 400 * (attempt + 1)));
    }
  }
}
const CONC = 12;
const rowsBuf = new Array(hh);
let next = 0;
await Promise.all(
  Array.from({ length: CONC }, async () => {
    while (next < hh) {
      const k = next++;
      rowsBuf[k] = await getRow(r0 + k);
      if (k % 400 === 0) process.stdout.write(`  row ${k}/${hh}\r`);
    }
  }),
);
for (let k = 0; k < hh; k++) {
  const b = rowsBuf[k];
  hash.update(b);
  for (let i = 0; i < ww; i++) win[k * ww + i] = b.readFloatLE(i * 4);
}
console.log(`\nfetched ${(fetched / 1e6).toFixed(1)} MB in ${requests} range requests`);

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

const SUB = [-0.4, -0.2, 0, 0.2, 0.4];
const heights = new Array(ROWS * COLS);
let nodata = 0;
for (let r = 0; r < ROWS; r++) {
  for (let c = 0; c < COLS; c++) {
    let sum = 0;
    let n = 0;
    for (const sr of SUB) {
      for (const sc of SUB) {
        const north_m = OY + (r + 0.5 + sr) * RES;
        const east_m = OX + (c + 0.5 + sc) * RES;
        const lat = lat0 + north_m / R;
        const lon = lon0 + east_m / (R * Math.cos(lat));
        const h = sample((R * lon - west) / 1 - 0.5, (north - R * lat) / 1 - 0.5);
        if (h != null) {
          sum += h;
          n++;
        }
      }
    }
    if (n === 0) {
      heights[r * COLS + c] = null;
      nodata++;
    } else {
      heights[r * COLS + c] = Math.round((sum / n) * 10) / 10;
    }
  }
}

const valid = heights.filter((h) => h != null).sort((a, b) => a - b);
const crop = {
  note: 'PROVISIONAL crop made by the frontend. HiRISE is the hidden evaluator reference; it must not reach the agent view except through an observation. Heights are metres above the MOLA areoid.',
  source: {
    title: 'Mars 2020 Terrain Relative Navigation HiRISE DTM mosaic',
    file: 'JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif',
    url: URL_TIF,
    product_page: 'https://astrogeology.usgs.gov/search/map/mars_2020_terrain_relative_navigation_hirise_dtm_mosaic',
    provider: 'USGS Astrogeology Science Center / NASA',
    size_bytes: 1839545409,
    pixels: [W, H],
    native_resolution_m: 1,
    bbox_projected_m: [west, south, east, north],
    projection: 'Equirectangular, standard parallel 0, central meridian 0, Mars 2000 sphere IAU (R = 3396190 m)',
    vertical: 'metres above the MOLA areoid',
    licence: 'Not verified here: USGS-hosted NASA planetary data, see the product page for usage terms',
    read_with: 'HTTP Range requests of the window only; the full file was not downloaded',
    window_pixels: { col0: c0, col1: c1, row0: r0, row1: r1 },
    window_bytes_fetched: fetched,
    window_sha256: hash.digest('hex'),
  },
  crop: {
    centre_lat_deg: ctx.crop.centre_lat_deg,
    centre_lon_deg: ctx.crop.centre_lon_deg,
    method: `mean of 5 x 5 bilinear samples per ${RES} m cell on a local tangent ENU grid (east = R cos(lat) dlon, north = R dlat)`,
    origin_x_m: OX,
    origin_y_m: OY,
    resolution_m: RES,
    rows: ROWS,
    cols: COLS,
    nodata_cells: nodata,
    min_m: valid[0],
    max_m: valid[valid.length - 1],
    median_m: valid[Math.floor(valid.length / 2)],
  },
  heights,
};
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, JSON.stringify(crop));
console.log(`crop ${ROWS}x${COLS} at ${RES} m, elevation ${crop.crop.min_m}..${crop.crop.max_m} m, NoData cells ${nodata}`);
console.log(`written ${outPath}`);
