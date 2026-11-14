#!/usr/bin/env node
/**
 * Removes the agency marks that the Blender cleanup (scripts/blender/) missed in the exported
 * rover and drone models. Deterministic: no image is synthesised.
 *
 * - rover.glb, image `blade`: the stowed Ingenuity blade sheet still had the agency logos and
 *   the national flag. It is the same 512 × 256 texture as the drone's `blade`, which was already
 *   cleaned, so the drone's cleaned image is copied in unchanged.
 * - drone.glb, image `chopper_sp_r2` (blade roughness map): the two agency logos are filled with
 *   the map's own plain background value.
 *
 * Every other buffer view is kept byte-identical. Running it twice changes nothing.
 *
 * Usage: node scripts/strip-glb-branding.mjs [models dir]   (default: public/assets/models)
 */
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PNG } from 'pngjs';
import { decodeImage, imageView, isFlat, readGlb, writeGlb } from './glb.mjs';

/** Logo rectangle [x0, y0, x1, y1) on the drone blade roughness map and its plain background. */
export const DRONE_ROUGHNESS_LOGOS = [440, 172, 512, 256];
const ROUGHNESS_BACKGROUND = [166, 161, 157];

const dir = process.argv[2] ?? join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'assets', 'models');
const roverPath = join(dir, 'rover.glb');
const dronePath = join(dir, 'drone.glb');
const rover = readGlb(readFileSync(roverPath));
const drone = readGlb(readFileSync(dronePath));

// Drone roughness map: flat fill over the logos.
const r2 = decodeImage(drone, 'chopper_sp_r2');
if (!isFlat(r2, DRONE_ROUGHNESS_LOGOS)) {
  const [x0, y0, x1, y1] = DRONE_ROUGHNESS_LOGOS;
  for (let y = y0; y < y1; y++)
    for (let x = x0; x < x1; x++) {
      const i = (y * r2.width + x) * 4;
      [r2.data[i], r2.data[i + 1], r2.data[i + 2]] = ROUGHNESS_BACKGROUND;
    }
  drone.views[imageView(drone, 'chopper_sp_r2')] = PNG.sync.write(r2, { colorType: 2 });
}

// Rover: reuse the drone's already cleaned blade sheet.
const cleanBlade = drone.views[imageView(drone, 'blade')];
const roverBlade = decodeImage(rover, 'blade');
const droneBlade = PNG.sync.read(cleanBlade);
if (roverBlade.width !== droneBlade.width || roverBlade.height !== droneBlade.height)
  throw new Error('rover and drone blade sheets differ in size; refusing to swap');
rover.views[imageView(rover, 'blade')] = cleanBlade;

for (const [path, glb] of [[roverPath, rover], [dronePath, drone]]) {
  const out = writeGlb(glb);
  writeFileSync(path, out);
  console.log(path, out.length, 'bytes, SHA-256', createHash('sha256').update(out).digest('hex'));
}
