import { describe, expect, it } from 'vitest';
import { cellAt, cellCenter, enuToThree, sampleHeight, threeToEnu, yawFromQuaternion } from '../src/lib/coords';

const meta = { origin_x_m: -10, origin_y_m: -20, resolution_m: 2, rows: 3, cols: 4 };

describe('ENU to Three.js (ICD §1)', () => {
  it('maps east to +x, north to -z and up to +y', () => {
    expect(enuToThree({ x: 1, y: 0, z: 0 })).toEqual([1, 0, -0]);
    expect(enuToThree({ x: 0, y: 1, z: 0 })).toEqual([0, 0, -1]);
    expect(enuToThree({ x: 0, y: 0, z: 1 })).toEqual([0, 1, -0]);
  });

  it('applies vertical exaggeration only to the up axis and round-trips', () => {
    const p = { x: 12.5, y: -7, z: 3 };
    const v = enuToThree(p, 3);
    expect(v).toEqual([12.5, 9, 7]);
    expect(threeToEnu(v, 3)).toEqual(p);
  });
});

describe('grid convention', () => {
  it('cell (0,0) is the south-west cell and rows grow north', () => {
    expect(cellCenter(meta, 0, 0)).toEqual({ x: -9, y: -19 });
    expect(cellCenter(meta, 2, 3)).toEqual({ x: -3, y: -15 });
  });

  it('finds the cell and flat index of a point, null outside', () => {
    expect(cellAt(meta, -9, -19)).toEqual({ row: 0, col: 0, index: 0 });
    expect(cellAt(meta, -3.1, -15.2)).toEqual({ row: 2, col: 3, index: 11 });
    expect(cellAt(meta, -11, 0)).toBeNull();
  });

  it('samples exact heights at cell centres and interpolates between them', () => {
    const grid = [0, 1, 2, 3, 10, 11, 12, 13, 20, 21, 22, 23];
    expect(sampleHeight(meta, grid, -9, -19)).toBe(0);
    expect(sampleHeight(meta, grid, -3, -15)).toBe(23);
    expect(sampleHeight(meta, grid, -8, -18)).toBeCloseTo(5.5);
  });

  it('never invents a height next to NoData', () => {
    const grid = [0, 1, null, 3, 10, 11, 12, 13, 20, 21, 22, 23];
    expect(sampleHeight(meta, grid, -6, -18)).toBeNull();
    expect(sampleHeight(meta, grid, -100, -100)).toBeNull();
  });
});

describe('yaw', () => {
  it('reads a ROS yaw quaternion (0 = east, +90° = north)', () => {
    const q = (yaw: number) => ({ x: 0, y: 0, z: Math.sin(yaw / 2), w: Math.cos(yaw / 2) });
    expect(yawFromQuaternion(q(0))).toBeCloseTo(0);
    expect(yawFromQuaternion(q(Math.PI / 2))).toBeCloseTo(Math.PI / 2);
  });
});
