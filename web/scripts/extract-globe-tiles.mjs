#!/usr/bin/env node
/**
 * Mars globe texture for the zone selector: the 32 level-2 tiles (8 x 4 of 256 px, 0.176 degree per pixel,
 * about 10 km at the equator) of the Viking MDIM 2.1 colour mosaic from JPL Mars Trek, stored as served (JPEG). The
 * viewer stitches them into one 2048 x 1024 equirectangular image (row 0 = north, column 0 = 180 W).
 *
 * Source: JPL Mars Trek WMTS layer Mars_Viking_MDIM21_ClrMosaic_global_232m (NASA/USGS),
 *   https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/2/{row}/{col}.jpg
 *
 * Usage: node scripts/extract-globe-tiles.mjs   (writes public/zones/globe/<row>_<col>.jpg and manifest.json)
 */
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const LAYER = 'Mars_Viking_MDIM21_ClrMosaic_global_232m';
const LEVEL = 2;
const ROWS = 4;
const COLS = 8;
const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, '..', 'public', 'zones', 'globe');
mkdirSync(OUT, { recursive: true });

const all = createHash('sha256');
const tiles = [];
for (let r = 0; r < ROWS; r++) {
  for (let c = 0; c < COLS; c++) {
    const url = `https://trek.nasa.gov/tiles/Mars/EQ/${LAYER}/1.0.0/default/default028mm/${LEVEL}/${r}/${c}.jpg`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`tile ${r}/${c} answered ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    writeFileSync(join(OUT, `${r}_${c}.jpg`), buf);
    all.update(buf);
    tiles.push({ row: r, col: c, sha256: createHash('sha256').update(buf).digest('hex') });
  }
}
writeFileSync(
  join(OUT, 'manifest.json'),
  JSON.stringify(
    {
      note: 'Viking MDIM 2.1 colour mosaic, level-2 tiles as served by JPL Mars Trek; stitched by the viewer into a 2048 x 1024 equirectangular texture (row 0 north, column 0 at 180 W).',
      layer: LAYER,
      level: LEVEL,
      rows: ROWS,
      cols: COLS,
      tile_px: 256,
      credit: 'NASA/USGS (Viking MDIM 2.1), JPL Mars Trek',
      source: `https://trek.nasa.gov/tiles/Mars/EQ/${LAYER}/1.0.0/WMTSCapabilities.xml`,
      tiles_sha256: all.digest('hex'),
      retrieved: new Date().toISOString().slice(0, 10),
      tiles,
    },
    null,
    1,
  ),
);
console.log(`${tiles.length} tiles written to ${OUT}`);
