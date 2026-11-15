#!/usr/bin/env node
/**
 * Horizon silhouette of the zone selector: two elevation profiles of the Melas Chasma scene DEM (MRO CTX stereo
 * DEM 11S291E, scripts/data/melas/dem_crop.json), smoothed and scaled to a 1600 x 220 SVG band. Two north-south
 * profiles, a quarter and three quarters across the crop (the second reversed), are the far and near layers.
 * Decorative use of real terrain; the heights are stretched to the band, not to scale.
 *
 * Usage: node scripts/extract-zone-horizon.mjs   (writes src/data/zoneHorizon.json)
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const crop = JSON.parse(readFileSync(join(HERE, 'data', 'melas', 'dem_crop.json'), 'utf8'));
const { rows: R, cols: C } = crop.crop;
const H = crop.heights;

function profile(col) {
  const v = [];
  for (let r = 0; r < R; r++) if (H[r * C + col] != null) v.push(H[r * C + col]);
  const k = 9;
  return v.map((_, i) => {
    const s = v.slice(Math.max(0, i - k), i + k + 1);
    return s.reduce((a, b) => a + b, 0) / s.length;
  });
}
function path(prof, top, bottom) {
  const lo = Math.min(...prof);
  const hi = Math.max(...prof);
  const n = 160;
  const pts = [];
  for (let j = 0; j <= n; j++) {
    const i = Math.floor((j / n) * (prof.length - 1));
    pts.push(`${((j / n) * 1600).toFixed(1)} ${(bottom - ((prof[i] - lo) / (hi - lo)) * (bottom - top)).toFixed(1)}`);
  }
  return `M0 220L${pts.join('L')}L1600 220Z`;
}

const out = {
  note: 'Decorative horizon of the zone selector: smoothed elevation profiles of the Melas Chasma scene DEM, stretched to a 1600 x 220 band (not to scale).',
  source: crop.source.title,
  far: path(profile(Math.floor(C / 4)), 70, 170),
  near: path(profile(Math.floor((3 * C) / 4)).reverse(), 120, 205),
};
writeFileSync(join(HERE, '..', 'src', 'data', 'zoneHorizon.json'), JSON.stringify(out));
console.log('written src/data/zoneHorizon.json');
