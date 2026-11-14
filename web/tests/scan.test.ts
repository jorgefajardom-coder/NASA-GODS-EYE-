import { describe, expect, it } from 'vitest';
import { angleDiffDeg, bearingDeg, scanCells, scanClass, scanSummary, SCAN_BANDS_DEG } from '../src/lib/scan';

const meta = { origin_x_m: -100, origin_y_m: -100, resolution_m: 20, rows: 10, cols: 10 };

describe('drone scan (display only)', () => {
  it('bands the orbital slope and keeps NoData apart', () => {
    expect(scanClass(0)).toBe('gentle');
    expect(scanClass(SCAN_BANDS_DEG[0])).toBe('moderate');
    expect(scanClass(SCAN_BANDS_DEG[1])).toBe('steep');
    expect(scanClass(null)).toBe('nodata');
    expect(scanClass(Number.NaN)).toBe('nodata');
  });

  it('returns only cells within the radius, nearest first, with their own slope', () => {
    const slope = Array.from({ length: 100 }, (_, i) => (i === 55 ? null : i % 30));
    const marks = scanCells(meta, slope, 0, 0, 30);
    expect(marks.length).toBeGreaterThan(0);
    for (const m of marks) expect(m.distanceM).toBeLessThanOrEqual(30);
    for (let i = 1; i < marks.length; i++) expect(marks[i].distanceM).toBeGreaterThanOrEqual(marks[i - 1].distanceM);
    const nodata = marks.find((m) => m.x === 10 && m.y === 10);
    expect(nodata?.cls).toBe('nodata');
    const counts = scanSummary(marks);
    expect(counts.gentle + counts.moderate + counts.steep + counts.nodata).toBe(marks.length);
  });

  it('does not invent cells outside the grid', () => {
    const slope = Array(100).fill(1);
    expect(scanCells(meta, slope, 5000, 5000, 100)).toEqual([]);
  });

  it('measures bearings clockwise from north', () => {
    expect(bearingDeg(0, 0, 0, 10)).toBeCloseTo(0);
    expect(bearingDeg(0, 0, 10, 0)).toBeCloseTo(90);
    expect(bearingDeg(0, 0, -10, 0)).toBeCloseTo(270);
    expect(angleDiffDeg(350, 10)).toBeCloseTo(20);
    expect(angleDiffDeg(10, 350)).toBeCloseTo(-20);
  });
});
