import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/**
 * context.json: surroundings of the crop from the same CTX DTM (extract-ctx-context.mjs).
 * It must be the same product and height reference as the crop, so the two surfaces meet.
 */
const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'replay', 'demo');
const read = <T,>(f: string) => JSON.parse(readFileSync(join(DIR, f), 'utf8')) as T;

interface Context {
  source: { sha256: string };
  frame: { origin_x_m: number; origin_y_m: number; resolution_m: number; rows: number; cols: number; local_z_offset_m: number };
  heights: (number | null)[];
}
const ctx = read<Context>('context.json');
const manifest = read<{ local_z_offset_m: number; terrain_meta: { origin_x_m: number; origin_y_m: number; resolution_m: number; rows: number; cols: number } }>('manifest.json');
const rasters = read<{ rows: number; cols: number; prior: (number | null)[] }>('rasters.json');
const crop = JSON.parse(readFileSync(join(DIR, '..', '..', '..', 'scripts', 'data', 'ctx_crop.json'), 'utf8')) as { source: { sha256: string } };

describe('context terrain', () => {
  it('comes from the same CTX DTM file as the crop, on the same height reference', () => {
    expect(ctx.source.sha256).toBe(crop.source.sha256);
    expect(ctx.frame.local_z_offset_m).toBe(manifest.local_z_offset_m);
    expect(ctx.heights).toHaveLength(ctx.frame.rows * ctx.frame.cols);
  });

  it('surrounds the crop, centred on it', () => {
    const f = ctx.frame;
    const t = manifest.terrain_meta;
    expect(f.origin_x_m).toBeLessThan(t.origin_x_m);
    expect(f.origin_y_m).toBeLessThan(t.origin_y_m);
    expect(f.origin_x_m + f.cols * f.resolution_m).toBeGreaterThan(t.origin_x_m + t.cols * t.resolution_m);
    expect(f.origin_x_m + (f.cols * f.resolution_m) / 2).toBeCloseTo(0, 6);
  });

  it('agrees with the crop where they overlap (same measured surface)', () => {
    const f = ctx.frame;
    const t = manifest.terrain_meta;
    const diffs: number[] = [];
    for (let r = 0; r < f.rows; r++) {
      for (let c = 0; c < f.cols; c++) {
        const x = f.origin_x_m + (c + 0.5) * f.resolution_m;
        const y = f.origin_y_m + (r + 0.5) * f.resolution_m;
        const ci = Math.floor((x - t.origin_x_m) / t.resolution_m);
        const ri = Math.floor((y - t.origin_y_m) / t.resolution_m);
        if (ci < 0 || ri < 0 || ci >= t.cols || ri >= t.rows) continue;
        const a = ctx.heights[r * f.cols + c];
        const b = rasters.prior[ri * rasters.cols + ci];
        if (a != null && b != null) diffs.push(a - b);
      }
    }
    expect(diffs.length).toBeGreaterThan(100);
    const mean = diffs.reduce((s, d) => s + d, 0) / diffs.length;
    expect(Math.abs(mean)).toBeLessThan(0.5); // box average vs point sample of the same DTM
    expect(Math.max(...diffs.map(Math.abs))).toBeLessThan(10);
  });
});
