import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PNG } from 'pngjs';
import { describe, expect, it } from 'vitest';
import type { ReplayManifest } from '../src/types/replay';

const DEMO = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo');
const manifest = JSON.parse(readFileSync(join(DEMO, 'manifest.json'), 'utf8')) as ReplayManifest;

describe('draped CTX image of the demo run', () => {
  const img = manifest.imagery!;

  it('covers exactly the terrain grid, so image and heights share one frame', () => {
    const t = manifest.terrain_meta;
    expect(img.extent).toEqual({ origin_x_m: t.origin_x_m, origin_y_m: t.origin_y_m, width_m: t.cols * t.resolution_m, height_m: t.rows * t.resolution_m });
    expect(img.row0).toBe('north');
  });

  it('is a fully covered image at the declared resolution, not finer than it claims', () => {
    const png = PNG.sync.read(readFileSync(join(DEMO, img.file)));
    expect(png.width * img.resolution_m).toBeCloseTo(img.extent.width_m, 6);
    expect(png.height * img.resolution_m).toBeCloseTo(img.extent.height_m, 6);
    expect(img.resolution_m).toBeLessThanOrEqual(img.native_resolution_m);
    // The 1st-99th percentile stretch clips about 1 % of pixels to 0; more would mean holes.
    let black = 0;
    for (let i = 0; i < png.data.length; i += 4) if (png.data[i] === 0) black++;
    expect(black / (png.width * png.height)).toBeLessThan(0.02);
  });

  it('comes from the same CTX production as the terrain and is credited', () => {
    expect(img.source).toMatch(/soc_008/);
    expect(manifest.terrain_meta.sources.join(' ')).toMatch(/ctx/i);
    expect(img.credit).toMatch(/NASA/);
  });
});
