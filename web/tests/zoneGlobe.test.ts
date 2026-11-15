import { describe, expect, it } from 'vitest';
import { aimAt, angleDelta, globeDir, leftArc, radialCard, rotateXY } from '../src/lib/zoneGlobe';
import { WORLDS } from '../src/data/worlds';

describe('zone globe geometry', () => {
  it('places points where an equirectangular map starting at 180 W puts them', () => {
    const [x, y, z] = globeDir(0, 0); // 0 N 0 E: the middle of the map faces +X in three.js
    expect(x).toBeCloseTo(1);
    expect(y).toBeCloseTo(0);
    expect(z).toBeCloseTo(0);
    expect(globeDir(90, 40)[1]).toBeCloseTo(1); // north pole up
  });

  it('turns the globe so every zone faces the camera', () => {
    for (const w of WORLDS) {
      const a = aimAt(w.lat, w.lon);
      const [x, y, z] = rotateXY(globeDir(w.lat, w.lon), a.x, a.y);
      expect(x).toBeCloseTo(0, 6);
      expect(y).toBeCloseTo(0, 6);
      expect(z).toBeCloseTo(1, 6);
    }
  });

  it('spins the short way round', () => {
    expect(angleDelta(3, -3)).toBeCloseTo(2 * Math.PI - 6);
    expect(Math.abs(angleDelta(0.1, 6.2))).toBeLessThan(Math.PI);
  });

  it('draws the title arc on the left side, bottom to top', () => {
    const d = leftArc(500, 300, 100, Math.PI / 4);
    const [, x0, y0] = /^M(\S+) (\S+)/.exec(d)!.map(Number);
    expect(x0).toBeLessThan(500); // left of the centre
    expect(y0).toBeGreaterThan(300); // starts below
    expect(d).toMatch(/A100\.0 100\.0 0 0 1 /);
  });

  it('fits the card to the planet with a radial left edge, inside the screen', () => {
    const c = radialCard(400, 300, 200, 320, 1280, 70);
    expect(c.intrusion).toBeGreaterThan(0);
    expect(c.left + c.width).toBeLessThanOrEqual(1280 - 70 + 1e-6);
    expect(c.edgeX).toBeCloseTo(400 + Math.sqrt(300 * 300 - 200 * 200));
    const big = radialCard(600, 700, 200, 320, 1280, 70); // zoomed in: the card is pushed back on screen
    expect(big.left + big.width).toBeLessThanOrEqual(1280 - 70 + 1e-6);
  });
});

describe('zones on the globe', () => {
  it('give every zone a centre on Mars and a short English synopsis', () => {
    for (const w of WORLDS) {
      expect(Math.abs(w.lat)).toBeLessThanOrEqual(90);
      expect(Math.abs(w.lon)).toBeLessThanOrEqual(180);
      expect(w.synopsis.length).toBeGreaterThan(40);
      expect(w.synopsis.length).toBeLessThan(220);
    }
  });
});
