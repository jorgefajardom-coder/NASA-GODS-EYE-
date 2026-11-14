import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { decodeImage, imageView, isFlat, readGlb } from '../scripts/glb.mjs';

/**
 * The delivery must carry no agency branding (AGENTS.md section 11). These are the texture
 * rectangles where the official models had logos or a flag; after cleanup each must be one
 * plain colour. See scripts/strip-glb-branding.mjs and scripts/blender/README.md.
 */
const MODELS = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'assets', 'models');
const load = (name: string) => readGlb(readFileSync(join(MODELS, name)));

/** Blade sheet: agency plate (left), flag and agency logo (right column). */
const BLADE_MARKS: Array<[number, number, number, number]> = [
  [6, 64, 90, 114],
  [444, 104, 510, 190],
  [444, 196, 510, 250],
];
/** Blade roughness map: the two agency logos. */
const ROUGHNESS_MARKS: [number, number, number, number] = [440, 172, 512, 256];

describe('NASA/JPL models carry no agency branding', () => {
  const rover = load('rover.glb');
  const drone = load('drone.glb');

  it.each([
    ['rover.glb', rover],
    ['drone.glb', drone],
  ])('%s blade sheet has the marks painted out', (_, glb) => {
    const png = decodeImage(glb, 'blade');
    for (const rect of BLADE_MARKS) expect(isFlat(png, rect), rect.join(',')).toBe(true);
  });

  it('drone blade roughness map has the logos painted out', () => {
    expect(isFlat(decodeImage(drone, 'chopper_sp_r2'), ROUGHNESS_MARKS)).toBe(true);
  });

  it('rover uses the same cleaned blade sheet as the drone', () => {
    expect(rover.views[imageView(rover, 'blade')].equals(drone.views[imageView(drone, 'blade')])).toBe(true);
  });
});
