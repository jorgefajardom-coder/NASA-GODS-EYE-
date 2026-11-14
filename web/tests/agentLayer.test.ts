import { describe, expect, it } from 'vitest';
import { droneAgl } from '../src/components/AgentLayer';

describe('drone altitude on screen', () => {
  it('is the true height above ground, never below the surface', () => {
    expect(droneAgl(-35.4, -33.0)).toBe(0); // parked pose under the drawn surface: on the ground
    expect(droneAgl(25, 5)).toBe(20);
  });
});
