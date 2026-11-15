import { describe, expect, it } from 'vitest';
import { droneAgl } from '../src/components/AgentLayer';

describe('drone altitude on screen', () => {
  it('is the true height above ground, never below the surface', () => {
    expect(droneAgl(-35.4, -33.0)).toBe(0); // parked pose under the drawn surface: on the ground
    expect(droneAgl(25, 5)).toBe(20);
  });
});

describe('travelYaw (astronaut faces where it walks)', () => {
  it('points along the move in Three.js axes, north being -z', async () => {
    const { travelYaw } = await import('../src/components/AgentLayer');
    expect(travelYaw({ x: 0, z: 0 }, { x: 1, z: 0 })).toBeCloseTo(0, 9); // east
    expect(travelYaw({ x: 0, z: 0 }, { x: 0, z: -1 })).toBeCloseTo(Math.PI / 2, 9); // north
    expect(Math.abs(travelYaw({ x: 0, z: 0 }, { x: -1, z: 0 }) ?? 0)).toBeCloseTo(Math.PI, 9); // west: turned round, not backwards
    expect(travelYaw({ x: 0, z: 0 }, { x: 0.01, z: 0 })).toBeNull(); // too small to tell
  });
});
