#!/usr/bin/env node
/**
 * Builds the terrain texture: the controlled Mars 2020 TRN CTX orthomosaic of Jezero
 * (6 m, same `soc_008` production as the CTX DTM crop) resampled onto the crop's local ENU
 * grid, so the image drapes on the terrain without re-registration.
 *
 * Source: JPL Mars Trek WMTS layer JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0
 * (https://trek.nasa.gov/mars/, layer catalogue https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars).
 * Tiles are equirectangular (EPSG::104905), 256 px; level 13 is about 5.1 m/px, the closest
 * level to the native 6 m. Each output pixel is a bilinear sample at its centre. Resampling
 * adds no resolution.
 *
 * Usage: node scripts/extract-ctx-ortho.mjs [out.png] [pixels]
 *   default: public/replay/demo/ctx_ortho.png, 400 px over the 2 km crop (5 m/px)
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PNG } from 'pngjs';

const LAYER = 'JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0';
const BASE = `https://trek.nasa.gov/tiles/Mars/EQ/${LAYER}/1.0.0`;
const LEVEL = 13;
const TILE = 256;
const R = 3396190;
const HERE = dirname(fileURLToPath(import.meta.url));
const outPath = process.argv[2] ?? join(HERE, '..', 'public', 'replay', 'demo', 'ctx_ortho.png');
const N = Number(process.argv[3] ?? 400);

const crop = JSON.parse(readFileSync(join(HERE, 'data', 'ctx_crop.json'), 'utf8')).crop;
const lat0 = (crop.centre_lat_deg * Math.PI) / 180;
const lon0 = (crop.centre_lon_deg * Math.PI) / 180;
const extentX = crop.cols * crop.resolution_m;
const extentY = crop.rows * crop.resolution_m;

// Tile matrix of the default028mm set: level 0 is 2 x 1 tiles from (-180, 90).
const degPerPx = 180 / (TILE * 2 ** LEVEL);
const toPx = (latDeg, lonDeg) => ({ x: (lonDeg + 180) / degPerPx, y: (90 - latDeg) / degPerPx });

function enuToLatLon(east, north) {
  const lat = lat0 + north / R;
  const lon = lon0 + east / (R * Math.cos(lat));
  return { lat: (lat * 180) / Math.PI, lon: (lon * 180) / Math.PI };
}

// Source pixel window covering the crop, with a one-pixel margin for bilinear sampling.
const corners = [
  [crop.origin_x_m, crop.origin_y_m],
  [crop.origin_x_m + extentX, crop.origin_y_m],
  [crop.origin_x_m, crop.origin_y_m + extentY],
  [crop.origin_x_m + extentX, crop.origin_y_m + extentY],
].map(([e, n]) => { const g = enuToLatLon(e, n); return toPx(g.lat, g.lon); });
const px0 = Math.floor(Math.min(...corners.map((c) => c.x))) - 1;
const px1 = Math.ceil(Math.max(...corners.map((c) => c.x))) + 1;
const py0 = Math.floor(Math.min(...corners.map((c) => c.y))) - 1;
const py1 = Math.ceil(Math.max(...corners.map((c) => c.y))) + 1;
const tc0 = Math.floor(px0 / TILE), tc1 = Math.floor(px1 / TILE);
const tr0 = Math.floor(py0 / TILE), tr1 = Math.floor(py1 / TILE);

const W = (tc1 - tc0 + 1) * TILE;
const H = (tr1 - tr0 + 1) * TILE;
const mosaic = new Float32Array(W * H).fill(NaN);
const hash = createHash('sha256');
let tiles = 0;
for (let tr = tr0; tr <= tr1; tr++) {
  for (let tc = tc0; tc <= tc1; tc++) {
    const url = `${BASE}/default/default028mm/${LEVEL}/${tr}/${tc}.png`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${url}: HTTP ${res.status} (no coverage?)`);
    const buf = Buffer.from(await res.arrayBuffer());
    hash.update(buf);
    const png = PNG.sync.read(buf);
    for (let y = 0; y < png.height; y++) {
      for (let x = 0; x < png.width; x++) {
        const i = (y * png.width + x) * 4;
        if (png.data[i + 3] === 0) continue; // transparent = no data
        // The orthomosaic is panchromatic; take the luminance of the stored pixel.
        const v = 0.299 * png.data[i] + 0.587 * png.data[i + 1] + 0.114 * png.data[i + 2];
        mosaic[((tr - tr0) * TILE + y) * W + (tc - tc0) * TILE + x] = v;
      }
    }
    tiles++;
  }
}
console.log(`level ${LEVEL}: ${tiles} tiles (${tc1 - tc0 + 1} x ${tr1 - tr0 + 1}), ${(degPerPx * (Math.PI / 180) * R).toFixed(2)} m/px at the equator`);

function sample(x, y) {
  const fx = x - tc0 * TILE - 0.5;
  const fy = y - tr0 * TILE - 0.5;
  const c = Math.floor(fx), r = Math.floor(fy);
  if (c < 0 || r < 0 || c + 1 >= W || r + 1 >= H) return NaN;
  const tx = fx - c, ty = fy - r;
  const v = (rr, cc) => mosaic[rr * W + cc];
  return v(r, c) * (1 - tx) * (1 - ty) + v(r, c + 1) * tx * (1 - ty) + v(r + 1, c) * (1 - tx) * ty + v(r + 1, c + 1) * tx * ty;
}

// Sample every output pixel first; row 0 = north edge (image convention).
const values = new Float32Array(N * N);
let missing = 0;
for (let j = 0; j < N; j++) {
  const north = crop.origin_y_m + extentY - ((j + 0.5) / N) * extentY;
  for (let i = 0; i < N; i++) {
    const east = crop.origin_x_m + ((i + 0.5) / N) * extentX;
    const g = enuToLatLon(east, north);
    const p = toPx(g.lat, g.lon);
    const v = sample(p.x, p.y);
    if (!Number.isFinite(v)) missing++;
    values[j * N + i] = v;
  }
}
if (missing > 0) throw new Error(`${missing} output pixels have no source data; the crop is not fully covered`);

// Display contrast: linear stretch between the 1st and 99th percentile of this crop.
// A monotonic grey-level mapping only; it adds no spatial detail.
const sorted = Float32Array.from(values).sort();
const P_LO = sorted[Math.floor(0.01 * (sorted.length - 1))];
const P_HI = sorted[Math.floor(0.99 * (sorted.length - 1))];
const out = new PNG({ width: N, height: N, colorType: 0, inputColorType: 0, bitDepth: 8 });
out.data = Buffer.alloc(N * N * 4);
for (let k = 0; k < N * N; k++) {
  const v = Math.round(Math.min(255, Math.max(0, ((values[k] - P_LO) / (P_HI - P_LO)) * 255)));
  out.data[k * 4] = out.data[k * 4 + 1] = out.data[k * 4 + 2] = v;
  out.data[k * 4 + 3] = 255;
}
console.log(`contrast stretch: source grey ${P_LO.toFixed(1)}..${P_HI.toFixed(1)} -> 0..255 (1st-99th percentile)`);
const png = PNG.sync.write(out, { colorType: 0 });
writeFileSync(outPath, png);
console.log(`written ${outPath}: ${N} x ${N} px, ${(extentX / N).toFixed(2)} m/px, ${png.length} bytes`);
console.log(`tiles sha256 ${hash.digest('hex')}`);
console.log(`image sha256 ${createHash('sha256').update(png).digest('hex')}`);
