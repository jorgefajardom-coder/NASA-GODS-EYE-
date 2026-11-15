import { describe, expect, it } from 'vitest';
import { parseNumber, parseVector, photoDirection, shortestTurnDeg } from '../src/lib/photoAim';

const cam = (over: Partial<Parameters<typeof photoDirection>[0]> = {}) => ({ instrument: 'NAVCAM_LEFT', vector: null, mastAzDeg: null, mastElDeg: null, ...over });

describe('photo direction', () => {
  it('reads the feed text for vectors and numbers, and "UNK" as nothing', () => {
    expect(parseVector('(0.86,-0.0068,0.5097)')).toEqual([0.86, -0.0068, 0.5097]);
    expect(parseVector('UNK')).toBeNull();
    expect(parseVector(undefined)).toBeNull();
    expect(parseNumber('359.5')).toBe(359.5);
    expect(parseNumber('UNK')).toBeNull();
    expect(parseNumber('')).toBeNull();
  });

  it('turns a rover-frame vector (x forward, y right, z down) into a compass azimuth and a pitch', () => {
    const fwd = photoDirection(cam({ vector: [1, 0, 0] }), 0);
    expect(fwd?.azimuthDeg).toBeCloseTo(0, 6);
    expect(fwd?.pitchDeg).toBeCloseTo(0, 6);
    expect(photoDirection(cam({ vector: [0, 1, 0] }), 0)?.azimuthDeg).toBeCloseTo(90, 6); // to the right
    expect(photoDirection(cam({ vector: [0, 0, 1] }), 0)?.pitchDeg).toBeCloseTo(-90, 6); // straight down
    expect(photoDirection(cam({ vector: [0.86, 0, 0.51] }), 0)?.pitchDeg).toBeLessThan(0);
  });

  it('adds the rover heading at the stop and wraps the azimuth', () => {
    expect(photoDirection(cam({ vector: [0, 1, 0] }), 300)?.azimuthDeg).toBeCloseTo(30, 6);
    expect(photoDirection(cam({ vector: [-1, 0, 0] }), 90)?.azimuthDeg).toBeCloseTo(270, 6);
  });

  it('falls back to the mast angles, then to the hazard cameras of Curiosity, then to nothing', () => {
    expect(photoDirection(cam({ mastAzDeg: 180, mastElDeg: -10 }), 0)).toMatchObject({ azimuthDeg: 180, pitchDeg: -10, source: 'mast' });
    expect(photoDirection(cam({ instrument: 'FHAZ_LEFT_B' }), 90, 'Curiosity')).toMatchObject({ azimuthDeg: 90, source: 'instrument' });
    expect(photoDirection(cam({ instrument: 'RHAZ_RIGHT_B' }), 90, 'Curiosity')?.azimuthDeg).toBe(270);
    expect(photoDirection(cam({ instrument: 'MAST_LEFT' }), 90, 'Curiosity')).toBeNull();
    expect(photoDirection(cam({ instrument: 'FHAZ_LEFT_B' }), 90, 'Perseverance')).toBeNull();
  });

  it('turns the short way round', () => {
    expect(shortestTurnDeg(350, 10)).toBe(20);
    expect(shortestTurnDeg(10, 350)).toBe(-20);
    expect(shortestTurnDeg(0, 180)).toBe(-180);
  });
});
